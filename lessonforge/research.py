"""Research stage: websites, books and YouTube videos.

Design principle: *the LLM proposes, real APIs verify.*

1. Websites - Gemini with the Google Search tool writes a research brief.
   The pages it actually used come from the grounding metadata (not from the
   model's text), are resolved to their real URLs, fetched to confirm they are
   reachable, and classified by source type.
2. Books - Gemini suggests well-known books; each suggestion is looked up in the
   Google Books API (Open Library as fallback) and kept only if title and author
   match a real catalogue record (no invented titles).
3. YouTube - Gemini suggests search queries; videos are found via the YouTube
   Data API (if a key is set) or the public results page, then confirmed with
   YouTube's oEmbed endpoint.

Books and videos are "best effort": if they fail, the research step still
succeeds and records a warning. Web research failing is fatal for the step
(the lesson must be grounded in sources).
"""
from __future__ import annotations

import html
import json
import logging
import re
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable
from urllib.parse import quote_plus, urlparse

import requests

from . import prompts
from .config import Settings
from .llm import LLMClient, LLMError, extract_json
from .models import ResearchBundle, Source, Video

log = logging.getLogger(__name__)
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
HEADERS = {"User-Agent": UA, "Accept-Language": "en-US,en;q=0.9"}


# --------------------------------------------------------------------------- #
# Source classification (heuristic prior; QC1 makes the final judgment)
# --------------------------------------------------------------------------- #
_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (("rfc-editor.org", "ietf.org", "w3.org", "whatwg.org", "iso.org", "ecma-international.org",
      "nist.gov", "ieee.org"), "standard / specification", "high"),
    (("developer.mozilla.org", "docs.python.org", "learn.microsoft.com", "developer.apple.com",
      "developers.google.com", "cloud.google.com", "web.dev", "docs.oracle.com", "kubernetes.io",
      "nodejs.org", "react.dev", "postgresql.org", "aws.amazon.com", "docs.github.com",
      "git-scm.com", "docs.docker.com", "kotlinlang.org", "go.dev", "rust-lang.org", "typescriptlang.org"),
     "official documentation", "high"),
    (("khanacademy.org", "coursera.org", "edx.org", "britannica.com", "nature.com",
      "sciencedirect.com", "springer.com", "acm.org", "arxiv.org", "ncbi.nlm.nih.gov"),
     "academic / educational", "high"),
    (("wikipedia.org",), "encyclopedia (community edited)", "medium"),
    (("cloudflare.com", "ibm.com", "redhat.com", "oracle.com", "microsoft.com", "google.com",
      "mozilla.org", "digitalocean.com", "atlassian.com", "github.blog"), "vendor learning centre", "medium"),
    (("freecodecamp.org", "geeksforgeeks.org", "w3schools.com", "tutorialspoint.com",
      "javatpoint.com", "programiz.com", "realpython.com", "baeldung.com", "stackoverflow.com"),
     "tutorial site", "medium"),
    (("medium.com", "dev.to", "hashnode", "blogspot.", "wordpress.com", "substack.com",
      "quora.com", "reddit.com", "linkedin.com"), "blog / user-generated", "low"),
]


def classify_domain(url: str) -> tuple[str, str]:
    host = (urlparse(url).hostname or "").lower()
    for domains, label, trust in _RULES:
        if any(host == d or host.endswith("." + d) or d in host for d in domains):
            return label, trust
    if host.endswith(".gov") or ".gov." in host:
        return "government", "high"
    if host.endswith(".edu") or ".edu." in host or ".ac." in host:
        return "university", "high"
    return "unknown", "unknown"


def domain_of(url: str) -> str:
    host = urlparse(url).hostname or ""
    return host[4:] if host.startswith("www.") else host


# --------------------------------------------------------------------------- #
# HTTP helpers
# --------------------------------------------------------------------------- #
def _session() -> requests.Session:
    s = requests.Session()
    s.headers.update(HEADERS)
    return s


def resolve_redirect(url: str, timeout: float, session: requests.Session | None = None) -> str:
    """Gemini grounding URIs are redirect links; follow one hop to the real page."""
    if "grounding-api-redirect" not in url and "vertexaisearch" not in url:
        return url
    s = session or _session()
    try:
        r = s.get(url, allow_redirects=False, timeout=timeout)
        loc = r.headers.get("Location")
        if loc:
            return loc
        r = s.get(url, allow_redirects=True, timeout=timeout, stream=True)
        r.close()
        return r.url
    except requests.RequestException:
        return url


_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.IGNORECASE | re.DOTALL)


def probe_page(url: str, timeout: float, session: requests.Session | None = None) -> dict:
    """Check that a page loads and read its <title>. Never raises."""
    s = session or _session()
    out = {"url": url, "status": None, "reachable": None, "title": ""}
    try:
        r = s.get(url, timeout=timeout, stream=True, allow_redirects=True)
        out["status"] = r.status_code
        out["url"] = r.url
        # 401/403/429 usually mean "bot blocked", not "page missing"
        out["reachable"] = r.status_code < 400 or r.status_code in (401, 403, 429)
        if r.status_code < 400 and "html" in r.headers.get("Content-Type", ""):
            chunk = r.raw.read(150_000, decode_content=True).decode(r.encoding or "utf-8", "ignore")
            m = _TITLE_RE.search(chunk)
            if m:
                out["title"] = html.unescape(re.sub(r"\s+", " ", m.group(1))).strip()[:200]
        r.close()
    except requests.RequestException as exc:
        out["reachable"] = False
        out["error"] = type(exc).__name__
    return out


# --------------------------------------------------------------------------- #
# Citation helpers
# --------------------------------------------------------------------------- #
def split_notes_and_extras(text: str) -> tuple[str, dict]:
    """The research prompt asks for a trailing JSON block with book & video ideas."""
    m = None
    for m in re.finditer(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL):
        pass  # keep the last one
    if not m:
        return text.strip(), {}
    try:
        extras = json.loads(m.group(1))
    except json.JSONDecodeError:
        try:
            extras = json.loads(extract_json(m.group(0)))
        except Exception:  # noqa: BLE001
            extras = {}
    notes = (text[:m.start()] + text[m.end():]).strip()
    return notes, extras if isinstance(extras, dict) else {}


def insert_citations(notes: str, supports: list[dict], chunk_to_sid: dict[int, str]) -> str:
    """Append [S#] markers after the sentences Gemini says are supported by a source."""
    for sup in supports:
        seg = (sup.get("text") or "").strip()
        sids = sorted({chunk_to_sid[i] for i in sup.get("source_indices", []) if i in chunk_to_sid},
                      key=lambda x: int(x[1:]))
        if not seg or not sids:
            continue
        pos = notes.find(seg)
        if pos == -1:
            continue
        end = pos + len(seg)
        marker = " [" + ", ".join(sids) + "]"
        if notes[end:end + len(marker)] == marker:
            continue
        notes = notes[:end] + marker + notes[end:]
    return notes


# --------------------------------------------------------------------------- #
# Books (Google Books API, no key required for light use)
# --------------------------------------------------------------------------- #
def _book_from_item(item: dict) -> dict | None:
    info = item.get("volumeInfo", {})
    title = info.get("title")
    if not title:
        return None
    if info.get("subtitle"):
        title = f"{title}: {info['subtitle']}"
    authors = ", ".join(info.get("authors", [])[:3])
    year = (info.get("publishedDate") or "")[:4]
    publisher = info.get("publisher", "")
    meta = " · ".join(x for x in (authors, publisher, year) if x)
    link = info.get("canonicalVolumeLink") or info.get("infoLink") or ""
    return {"title": title, "publisher": meta, "url": link.replace("http://", "https://"),
            "snippet": (info.get("description") or "")[:400], "authors": authors}


def _norm_words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


def book_matches(sug_title: str, sug_author: str, title: str, authors: str) -> bool:
    """Accept a lookup hit only if it is plausibly the suggested book (guards against
    a search engine returning *something* for an invented title)."""
    want = [w for w in _norm_words(sug_title.split(":")[0]) if len(w) > 2] or _norm_words(sug_title)
    have = set(_norm_words(title))
    title_ok = bool(want) and sum(w in have for w in want) / len(want) >= 0.75
    surname = (_norm_words(sug_author.split(",")[0]) or [""])[-1]
    author_ok = not surname or surname in _norm_words(authors)
    return title_ok and author_ok


def _google_books(s: requests.Session, q: str, n: int, timeout: float, api_key: str) -> list[dict]:
    params = {"q": q, "maxResults": n, "printType": "books", "langRestrict": "en"}
    if api_key:
        params["key"] = api_key
    r = s.get("https://www.googleapis.com/books/v1/volumes", params=params, timeout=timeout)
    r.raise_for_status()
    return [b for b in (_book_from_item(i) for i in r.json().get("items", [])) if b]


def _open_library(s: requests.Session, title: str, author: str, timeout: float) -> list[dict]:
    q = " ".join(_norm_words(title.split(":")[0]) + ((_norm_words(author.split(",")[0]) or [""])[-1:] if author else []))
    r = s.get("https://openlibrary.org/search.json", timeout=timeout, params={
        "q": q, "limit": 3, "fields": "key,title,subtitle,author_name,first_publish_year,publisher"})
    r.raise_for_status()
    out = []
    for d in r.json().get("docs", []):
        authors = ", ".join(d.get("author_name", [])[:3])
        full = d["title"] + (f": {d['subtitle']}" if d.get("subtitle") else "")
        meta = " · ".join(str(x) for x in (authors, (d.get("publisher") or [""])[0], d.get("first_publish_year") or "") if x)
        out.append({"title": full, "authors": authors, "publisher": meta,
                    "url": f"https://openlibrary.org{d['key']}", "snippet": ""})
    return out


def search_books(suggestions: list[dict], topic_query: str, timeout: float, limit: int = 4,
                 api_key: str = "") -> tuple[list[dict], list[str]]:
    """Verify model-suggested books in Google Books, falling back to Open Library
    (Google's anonymous quota is shared and often exhausted)."""
    s = _session()
    found: list[dict] = []
    notes: list[str] = []
    seen: set[str] = set()
    google_ok = True

    def add(book: dict, verified_suggestion: bool, provider: str) -> None:
        key = book["title"].lower()[:60]
        if key in seen or len(found) >= limit:
            return
        seen.add(key)
        book["verified_suggestion"] = verified_suggestion
        book["provider"] = provider
        found.append(book)

    for sug in suggestions[:5]:
        title, author = (sug.get("title") or "").strip(), (sug.get("author") or "").strip()
        if not title:
            continue
        hit = None
        if google_ok:
            surname = (_norm_words(author.split(",")[0]) or [""])[-1] if author else ""
            q = f'intitle:"{title.split(":")[0]}"' + (f" inauthor:{surname}" if surname else "")
            try:
                hit = next((b for b in _google_books(s, q, 3, timeout, api_key)
                            if book_matches(title, author, b["title"], b["authors"])), None)
                provider = "Google Books"
            except requests.RequestException as exc:
                google_ok = False  # quota/outage: stop hammering it
                notes.append(f"Google Books unavailable ({type(exc).__name__}); using Open Library.")
        if hit is None:
            try:
                hit = next((b for b in _open_library(s, title, author, timeout)
                            if book_matches(title, author, b["title"], b["authors"])), None)
                provider = "Open Library"
            except requests.RequestException as exc:
                notes.append(f"Open Library lookup failed for '{title}': {type(exc).__name__}")
                continue
        if hit:
            add(hit, True, provider)
        else:
            notes.append(f"Dropped book suggestion that could not be verified: '{title}' ({author})")
    if len(found) < 2 and topic_query and google_ok:
        try:
            for b in _google_books(s, topic_query, 4, timeout, api_key):
                add(b, False, "Google Books")
        except requests.RequestException as exc:
            notes.append(f"Google Books topic search failed: {type(exc).__name__}")
    return found, notes


# --------------------------------------------------------------------------- #
# YouTube
# --------------------------------------------------------------------------- #
def parse_duration_text(text: str) -> int | None:
    """'12:34' -> 754, '1:02:03' -> 3723."""
    if not text or not re.fullmatch(r"\d+(:\d{1,2}){1,2}", text.strip()):
        return None
    secs = 0
    for part in text.strip().split(":"):
        secs = secs * 60 + int(part)
    return secs


def parse_iso_duration(iso: str) -> int | None:
    m = re.fullmatch(r"P(?:\d+D)?T?(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?", iso or "")
    if not m:
        return None
    h, mi, s = (int(x) if x else 0 for x in m.groups())
    return h * 3600 + mi * 60 + s


def _walk(obj, key: str) -> Iterable[dict]:
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == key and isinstance(v, dict):
                yield v
            else:
                yield from _walk(v, key)
    elif isinstance(obj, list):
        for v in obj:
            yield from _walk(v, key)


def _runs_text(node: dict | None) -> str:
    if not node:
        return ""
    if "simpleText" in node:
        return node["simpleText"]
    return "".join(r.get("text", "") for r in node.get("runs", []))


def parse_youtube_results(page_html: str) -> list[dict]:
    m = re.search(r"var ytInitialData\s*=\s*(\{.*?\});\s*</script>", page_html, re.DOTALL)
    if not m:
        return []
    try:
        data = json.loads(m.group(1))
    except json.JSONDecodeError:
        return []
    out = []
    for vr in _walk(data, "videoRenderer"):
        vid = vr.get("videoId")
        if not vid:
            continue
        length = _runs_text(vr.get("lengthText"))
        out.append({
            "video_id": vid,
            "title": _runs_text(vr.get("title")),
            "channel": _runs_text(vr.get("ownerText")),
            "duration_text": length,
            "duration_seconds": parse_duration_text(length),
            "views_text": _runs_text(vr.get("viewCountText")),
        })
    return out


def _yt_scrape(query: str, timeout: float, s: requests.Session) -> list[dict]:
    url = f"https://www.youtube.com/results?search_query={quote_plus(query)}&sp=EgIQAQ%253D%253D"
    r = s.get(url, timeout=timeout, cookies={"CONSENT": "YES+1", "SOCS": "CAI"})
    r.raise_for_status()
    return parse_youtube_results(r.text)


def _yt_api(query: str, api_key: str, timeout: float, s: requests.Session) -> list[dict]:
    r = s.get("https://www.googleapis.com/youtube/v3/search", timeout=timeout, params={
        "part": "snippet", "q": query, "type": "video", "maxResults": 6,
        "relevanceLanguage": "en", "safeSearch": "strict", "key": api_key})
    r.raise_for_status()
    items = r.json().get("items", [])
    ids = [i["id"]["videoId"] for i in items if i.get("id", {}).get("videoId")]
    if not ids:
        return []
    d = s.get("https://www.googleapis.com/youtube/v3/videos", timeout=timeout, params={
        "part": "contentDetails,statistics", "id": ",".join(ids), "key": api_key}).json()
    details = {v["id"]: v for v in d.get("items", [])}
    out = []
    for i in items:
        vid = i["id"].get("videoId")
        if not vid:
            continue
        det = details.get(vid, {})
        secs = parse_iso_duration(det.get("contentDetails", {}).get("duration", ""))
        out.append({
            "video_id": vid, "title": html.unescape(i["snippet"]["title"]),
            "channel": i["snippet"].get("channelTitle", ""),
            "duration_seconds": secs,
            "duration_text": f"{secs // 60}:{secs % 60:02d}" if secs else "",
            "views_text": f"{int(det.get('statistics', {}).get('viewCount', 0)):,} views" if det else "",
            "verified": True,
        })
    return out


def _oembed_ok(video_id: str, timeout: float, s: requests.Session) -> dict | None:
    try:
        r = s.get("https://www.youtube.com/oembed", timeout=timeout, params={
            "url": f"https://www.youtube.com/watch?v={video_id}", "format": "json"})
        return r.json() if r.status_code == 200 else None
    except (requests.RequestException, ValueError):
        return None


def _video_score(v: dict, rank: int) -> float:
    secs = v.get("duration_seconds") or 0
    score = -rank  # search relevance
    if 180 <= secs <= 1200:  # 3-20 min is ideal as a supplement
        score += 5
    elif secs > 2400 or (0 < secs < 90):
        score -= 5  # very long lectures / shorts
    return score


def search_videos(queries: list[str], settings: Settings, limit: int = 6) -> tuple[list[dict], list[str]]:
    s = _session()
    notes: list[str] = []
    pool: dict[str, tuple[float, dict]] = {}
    for q in queries[:3]:
        try:
            results = (_yt_api(q, settings.youtube_api_key, settings.http_timeout, s)
                       if settings.youtube_api_key else _yt_scrape(q, settings.http_timeout, s))
        except (requests.RequestException, ValueError, KeyError) as exc:
            notes.append(f"YouTube search failed for '{q}': {type(exc).__name__}")
            continue
        for rank, v in enumerate(results[:6]):
            sc = _video_score(v, rank)
            if v["video_id"] not in pool or pool[v["video_id"]][0] < sc:
                pool[v["video_id"]] = (sc, v)
    ranked = [v for _, v in sorted(pool.values(), key=lambda x: -x[0])]

    verified: list[dict] = []
    with ThreadPoolExecutor(max_workers=6) as ex:
        checks = list(ex.map(lambda v: (v, v.get("verified") or _oembed_ok(v["video_id"], settings.http_timeout, s)),
                             ranked[: limit * 2]))
    for v, ok in checks:
        if not ok:
            notes.append(f"Dropped unverifiable video {v['video_id']}")
            continue
        if isinstance(ok, dict):
            v["title"] = ok.get("title") or v.get("title", "")
            v["channel"] = ok.get("author_name") or v.get("channel", "")
        v["verified"] = True
        verified.append(v)
        if len(verified) >= limit:
            break
    return verified, notes


# --------------------------------------------------------------------------- #
# Orchestration
# --------------------------------------------------------------------------- #
# Memo for SEARCH_BACKEND=auto: once a key is known to have no grounding quota,
# go straight to web retrieval. Kept in memory and in a small marker file (valid
# for the current day) so new processes don't spend a request rediscovering it.
_grounding_available: bool | None = None


def _marker(settings: Settings):
    return settings.data_dir.parent / ".grounding_unavailable"


def use_grounding(settings: Settings) -> bool:
    global _grounding_available
    if settings.search_backend == "web":
        return False
    if settings.search_backend == "gemini":
        return True
    if _grounding_available is None:
        try:
            from datetime import date
            m = _marker(settings)
            if m.exists() and m.read_text(encoding="utf-8").strip() == date.today().isoformat():
                _grounding_available = False
        except OSError:
            pass
    return _grounding_available is not False


def grounding_failed(settings: Settings, exc: Exception) -> bool:
    """Decide whether a grounded-call failure should trigger the retrieval fallback."""
    global _grounding_available
    if settings.search_backend != "auto":
        return False
    msg = str(exc).lower()
    if any(k in msg for k in ("quota", "rate limit", "429", "not supported", "google_search", "tool")):
        _grounding_available = False
        try:
            from datetime import date
            _marker(settings).parent.mkdir(parents=True, exist_ok=True)
            _marker(settings).write_text(date.today().isoformat(), encoding="utf-8")
        except OSError:
            pass
        return True
    return False


def _web_grounded(title: str, objective: str, llm: LLMClient, settings: Settings):
    prompt = prompts.RESEARCH_PROMPT.format(title=title, objective=objective,
                                            minutes=settings.lesson_minutes)
    retries = 0 if settings.search_backend == "auto" else None  # fail fast so the fallback kicks in
    result = llm.grounded(prompt, system=prompts.RESEARCH_SYSTEM, model=settings.model, retries=retries)
    notes, extras = split_notes_and_extras(result.text)
    if len(notes) < 200:
        raise LLMError("Research returned too little content. Press Retry.")
    warnings: list[str] = []

    s = _session()
    with ThreadPoolExecutor(max_workers=8) as ex:
        resolved = list(ex.map(lambda src: resolve_redirect(src["uri"], settings.http_timeout, s),
                               result.sources))
    chunk_to_sid: dict[int, str] = {}
    unique: dict[str, int] = {}  # normalized url -> index into `pages`
    pages: list[dict] = []
    for idx, (src, url) in enumerate(zip(result.sources, resolved)):
        norm = url.split("#")[0].rstrip("/")
        if norm not in unique:
            unique[norm] = len(pages)
            pages.append({"url": url, "grounding_title": src.get("title", "")})
        chunk_to_sid[idx] = f"S{unique[norm] + 1}"
    with ThreadPoolExecutor(max_workers=8) as ex:
        probes = list(ex.map(lambda p: probe_page(p["url"], settings.http_timeout, s), pages))

    sources: list[Source] = []
    for i, (page, probe) in enumerate(zip(pages, probes)):
        url = probe["url"] if probe.get("status") and probe["status"] < 400 else page["url"]
        label, trust = classify_domain(url)
        sources.append(Source(
            id=f"S{i + 1}", kind="web", url=url,
            title=probe.get("title") or page["grounding_title"] or domain_of(url),
            publisher=domain_of(url), reachable=probe.get("reachable"),
            http_status=probe.get("status"), source_type=label, trust_hint=trust,
            snippet=" ".join(sup["text"] for sup in result.supports
                             if any(chunk_to_sid.get(j) == f"S{i + 1}" for j in sup["source_indices"]))[:600],
        ))
    if not sources:
        warnings.append("Google Search grounding returned no web sources; claims in the lesson "
                        "could not be tied to pages. QC1 will verify them independently.")
    unreachable = [s_.id for s_ in sources if s_.reachable is False]
    if unreachable:
        warnings.append(f"Sources not reachable when checked: {', '.join(unreachable)}")
    notes = insert_citations(notes, result.supports, chunk_to_sid)
    return notes, extras, sources, result.queries, warnings


def _web_retrieval(title: str, objective: str, llm: LLMClient, settings: Settings):
    from .models import SourcePlan
    from .websearch import discover, read_best

    plan = llm.structured(prompts.SOURCE_PLAN_PROMPT.format(title=title, objective=objective),
                          SourcePlan, system=prompts.SOURCE_PLAN_SYSTEM, model=settings.model,
                          temperature=0.2)
    proposed = [p.model_dump() for p in plan.proposed_sources]
    cands, warnings = discover(plan.search_queries + [title], proposed, settings.http_timeout,
                               settings.tavily_api_key)
    pages = read_best(cands, f"{title} {objective}", settings.http_timeout, max_pages=8, max_chars=4500,
                      core=title)
    if len(pages) < 2:
        raise LLMError("Could not retrieve enough readable source pages for this topic. Press Retry, "
                       "or set TAVILY_API_KEY for full web search.")
    excerpts = "\n\n".join(f"[S{i + 1}] {p['title']} ({p['url']})\n{p['excerpt']}"
                            for i, p in enumerate(pages))
    text = llm.generate(prompts.RESEARCH_FROM_EXCERPTS_PROMPT.format(
        excerpts=excerpts, title=title, objective=objective, minutes=settings.lesson_minutes),
        system=prompts.RESEARCH_FROM_EXCERPTS_SYSTEM, model=settings.model, temperature=0.2)
    notes, extras = split_notes_and_extras(text)
    if len(notes) < 200:
        raise LLMError("Research returned too little content. Press Retry.")
    sources = [Source(id=f"S{i + 1}", kind="web", url=p["url"], title=p["title"] or domain_of(p["url"]),
                      publisher=domain_of(p["url"]), reachable=True, http_status=p.get("status"),
                      source_type=p["source_type"], trust_hint=p["trust"], snippet=p["excerpt"][:1500])
               for i, p in enumerate(pages)]
    origins: dict[str, int] = {}
    for p in pages:
        origins[p.get("origin", "?")] = origins.get(p.get("origin", "?"), 0) + 1
    warnings.append("Sources were found by fetching pages directly (model-proposed pages + Wikipedia/MDN"
                    + ("/Tavily" if settings.tavily_api_key else "") + " search), not Google Search grounding. "
                    + "Pages used by origin: " + ", ".join(f"{k}: {v}" for k, v in origins.items()) + ".")
    n_dropped = len(proposed) - origins.get("proposed", 0)
    if n_dropped > 0:
        warnings.append(f"{n_dropped} of {len(proposed)} model-proposed URLs were not used "
                        "(missing, unreadable or less relevant than other pages).")
    return notes, extras, sources, plan.search_queries, warnings


def run_research(title: str, objective: str, llm: LLMClient, settings: Settings) -> ResearchBundle:
    pre_warnings: list[str] = []
    method = "gemini-grounding"
    if use_grounding(settings):
        try:
            notes, extras, sources, queries, warnings = _web_grounded(title, objective, llm, settings)
        except LLMError as exc:
            if not grounding_failed(settings, exc):
                raise
            pre_warnings.append("Google Search grounding is not available for this API key "
                                f"({str(exc)[:80]}). Switched to direct web retrieval.")
            method = "web-retrieval"
            notes, extras, sources, queries, warnings = _web_retrieval(title, objective, llm, settings)
    else:
        method = "web-retrieval"
        notes, extras, sources, queries, warnings = _web_retrieval(title, objective, llm, settings)
    warnings = pre_warnings + warnings

    # --- books & videos in parallel (best effort) -----------------------------
    book_sugs = extras.get("book_suggestions") or []
    video_queries = [q for q in (extras.get("video_search_queries") or []) if isinstance(q, str)]
    if not video_queries:
        video_queries = [f"{title} explained", f"{title} tutorial for beginners"]
    with ThreadPoolExecutor(max_workers=2) as ex:
        fb = ex.submit(search_books, book_sugs, title, settings.http_timeout, 4, settings.google_books_api_key)
        fv = ex.submit(search_videos, video_queries, settings)
        try:
            books_raw, book_notes = fb.result()
        except Exception as exc:  # noqa: BLE001
            books_raw, book_notes = [], [f"Book search failed: {exc}"]
        try:
            videos_raw, video_notes = fv.result()
        except Exception as exc:  # noqa: BLE001
            videos_raw, video_notes = [], [f"Video search failed: {exc}"]
    warnings += book_notes + video_notes
    if not books_raw:
        warnings.append("No books could be verified for this topic.")
    if not videos_raw:
        warnings.append("No YouTube videos could be found/verified. You can retry research later.")

    books = [Source(id=f"B{i + 1}", kind="book", title=b["title"], url=b["url"],
                    publisher=b["publisher"], snippet=b["snippet"], reachable=True,
                    source_type=(f"book (verified in {b.get('provider', 'catalogue')})"
                                 if b.get("verified_suggestion") else "book (Google Books topic search)"),
                    trust_hint="medium")
             for i, b in enumerate(books_raw)]
    videos = [Video(id=f"V{i + 1}", url=f"https://www.youtube.com/watch?v={v['video_id']}",
                    **{k: v[k] for k in ("video_id", "title", "channel", "duration_text",
                                         "duration_seconds", "views_text", "verified")
                       if v.get(k) is not None})
              for i, v in enumerate(videos_raw)]

    return ResearchBundle(notes=notes, search_queries=queries, method=method, sources=sources,
                          books=books, videos=videos, warnings=warnings)
