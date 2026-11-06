"""Keyless web search + page reading, used when Gemini's Google Search grounding
is not available (e.g. free-tier keys have no grounding quota on Gemini 3 models).

Candidate pages come from three places:
* URLs the model proposes (specific official docs / specs / textbooks it knows),
* the Wikipedia and MDN search APIs (free, no key),
* Tavily web search, if TAVILY_API_KEY is set (free tier available).
Every candidate is then *fetched*: pages that don't exist or have no relevant
text are dropped (so an invented URL can never become a source). Candidates are
ranked by source authority + topic-term overlap, the main text is extracted and
only the most relevant paragraphs are kept. The model then works from these
excerpts and must cite them by id, so every fact stays traceable to a real page.

(Scraping consumer search engines was tried and rejected: they serve CAPTCHAs or
degrade results for scripts.)
"""
from __future__ import annotations

import base64
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.parse import parse_qs, urlparse

import requests
from bs4 import BeautifulSoup

from .research import HEADERS, classify_domain, domain_of

TRUST_WEIGHT = {"high": 3.0, "medium": 1.5, "unknown": 0.5, "low": 0.0}
SKIP_HOSTS = ("google.com", "bing.com", "youtube.com", "facebook.com", "twitter.com", "x.com",
              "instagram.com", "pinterest.", "amazon.", "tiktok.com")
STOP = set("the a an and or of to in for on with is are be how what why when which this that from by as at "
           "it its into vs between explain create use using".split())


def terms(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z0-9]+", text.lower()) if w not in STOP and len(w) > 1}


API_HEADERS = {"User-Agent": "LessonForge/1.0 (educational lesson-research tool)"}


def wikipedia_search(query: str, timeout: float, s: requests.Session, n: int = 3) -> list[dict]:
    r = s.get("https://en.wikipedia.org/w/api.php", headers=API_HEADERS, timeout=timeout, params={
        "action": "query", "list": "search", "srsearch": query, "format": "json", "srlimit": n})
    r.raise_for_status()
    return [{"title": x["title"], "snippet": re.sub(r"<[^>]+>", "", x.get("snippet", "")), "origin": "wikipedia",
             "url": "https://en.wikipedia.org/wiki/" + x["title"].replace(" ", "_")}
            for x in r.json().get("query", {}).get("search", [])]


def mdn_search(query: str, timeout: float, s: requests.Session, n: int = 3) -> list[dict]:
    r = s.get("https://developer.mozilla.org/api/v1/search", headers=API_HEADERS, timeout=timeout,
              params={"q": query, "locale": "en-US", "size": n})
    r.raise_for_status()
    return [{"title": d["title"], "snippet": d.get("summary", ""), "origin": "mdn",
             "url": "https://developer.mozilla.org" + d["mdn_url"]} for d in r.json().get("documents", [])]


def tavily_search(query: str, api_key: str, timeout: float, s: requests.Session, n: int = 5) -> list[dict]:
    r = s.post("https://api.tavily.com/search", timeout=timeout, json={
        "api_key": api_key, "query": query, "max_results": n, "search_depth": "basic"})
    r.raise_for_status()
    return [{"title": x.get("title", ""), "url": x["url"], "snippet": x.get("content", "")[:300],
             "origin": "tavily"} for x in r.json().get("results", [])]


def discover(queries: list[str], proposed: list[dict], timeout: float, tavily_key: str = "",
             session: requests.Session | None = None) -> tuple[list[dict], list[str]]:
    """Collect candidate pages from proposals + search APIs. Returns (candidates, notes)."""
    s = session or requests.Session()
    notes: list[str] = []
    cands = [{"title": p.get("title") or "", "url": p["url"], "snippet": p.get("why", ""), "origin": "proposed"}
             for p in proposed if str(p.get("url", "")).startswith("http")]
    jobs = []
    for q in queries[:5]:
        jobs.append(("Wikipedia", wikipedia_search, (q, timeout, s)))
        jobs.append(("MDN", mdn_search, (q, timeout, s)))
        if tavily_key:
            jobs.append(("Tavily", tavily_search, (q, tavily_key, timeout, s)))
    with ThreadPoolExecutor(max_workers=6) as ex:
        futures = [(name, q_args[0], ex.submit(fn, *q_args)) for name, fn, q_args in jobs]
        for name, q, f in futures:
            try:
                cands += f.result()
            except (requests.RequestException, ValueError, KeyError) as exc:
                notes.append(f"{name} search failed for '{q}': {type(exc).__name__}")
    return cands, notes


def core_match(core: set[str], text: str) -> bool:
    """True if the text mentions enough core terms: two of them when the core has two or
    more (one stray word like 'branch' in a WebAssembly page is not enough), with crude
    stemming ('branching' ~ 'branch')."""
    words = terms(text)
    hits = sum(1 for w in core
               if w in words or (len(w) >= 5 and any(x.startswith(w[:5]) for x in words)))
    return hits >= min(2, len(core))


def rank(candidates: list[dict], topic: str, core: str = "") -> list[dict]:
    """Relevance first, authority second.

    `core` (usually the lesson title) acts as a gate: a candidate must mention at least
    one core term, so a high-authority but off-topic page (e.g. MDN's JavaScript
    `switch` page for a Git lesson) cannot outrank relevant ones.
    """
    want = terms(topic)
    core_terms = terms(core)
    seen, ranked = set(), []
    for c in candidates:
        host = domain_of(c["url"])
        norm = c["url"].split("#")[0].rstrip("/")
        if norm in seen or any(h in host for h in SKIP_HOSTS) or c["url"].lower().endswith(".pdf"):
            continue
        seen.add(norm)
        label, trust = classify_domain(c["url"])
        path = urlparse(c["url"]).path.replace("-", " ").replace("_", " ").replace("/", " ")
        text = f"{c['title']} {c['snippet']} {path}"
        if core_terms and not core_match(core_terms, text):
            continue
        overlap = len(want & terms(text)) / (len(want) or 1)
        bonus = 2.0 if c.get("origin") in ("proposed", "tavily") else 0.0
        c = {**c, "source_type": label, "trust": trust,
             "score": 8 * overlap + TRUST_WEIGHT[trust] + bonus}
        ranked.append(c)
    return sorted(ranked, key=lambda x: -x["score"])


def extract_text(html: str) -> tuple[str, list[str]]:
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else ""
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "form", "noscript", "svg", "button"]):
        tag.decompose()
    root = soup.find("main") or soup.find("article") or soup.body or soup
    paras = []
    for el in root.find_all(["p", "li", "pre", "td", "h2", "h3", "dd", "dt"]):
        t = re.sub(r"\s+", " ", el.get_text(" ", strip=True))
        if len(t) >= 40 or (el.name == "pre" and t):
            paras.append(t[:1200])
    # drop duplicates (nested li/p)
    seen, uniq = set(), []
    for p in paras:
        if p not in seen:
            seen.add(p)
            uniq.append(p)
    return title, uniq


def best_passages(paras: list[str], topic: str, max_chars: int) -> str:
    want = terms(topic)
    scored = [(len(want & terms(p)) + (0.5 if any(ch.isdigit() for ch in p) else 0), i, p)
              for i, p in enumerate(paras)]
    keep, total = [], 0
    for sc, i, p in sorted(scored, key=lambda x: (-x[0], x[1])):
        if sc <= 0 or total + len(p) > max_chars:
            continue
        keep.append((i, p))
        total += len(p)
    return "\n".join(p for _, p in sorted(keep))


def read_page(url: str, topic: str, timeout: float, max_chars: int = 2500,
              session: requests.Session | None = None) -> dict | None:
    s = session or requests.Session()
    try:
        r = s.get(url, headers=HEADERS, timeout=timeout)
        if r.status_code >= 400 or "html" not in r.headers.get("Content-Type", ""):
            return None
        r.encoding = r.encoding or r.apparent_encoding
        title, paras = extract_text(r.text)
        excerpt = best_passages(paras, topic, max_chars)
        if len(excerpt) < 300:
            return None
        return {"url": r.url, "title": title, "excerpt": excerpt, "status": r.status_code, "paras": paras}
    except requests.RequestException:
        return None


def evidence_for_claims(pages: list[dict], claims: list[str], per_claim: int = 3,
                        max_len: int = 700) -> list[dict]:
    """Pick, for every claim, the paragraphs (across all fetched pages) that best match it.

    Returns evidence items [{"id": "E1", "url", "title", "text", "claims": [1, 4]}]. Matching
    per claim (instead of one topic-wide excerpt per page) means a specific claim such as
    "`git switch -` returns to the previous branch" gets the paragraph that discusses it.
    """
    items: dict[tuple[int, int], dict] = {}
    for ci, claim in enumerate(claims, 1):
        want = terms(claim)
        code = [c.lower() for c in re.findall(r"`([^`]{3,})`", claim)]
        scored = []
        for pi, page in enumerate(pages):
            for ki, para in enumerate(page.get("paras") or [page["excerpt"]]):
                low = para.lower()
                sc = len(want & terms(para)) / (len(want) or 1) + sum(2 for c in code if c in low)
                if sc >= 0.34:
                    scored.append((sc, pi, ki, para))
        for sc, pi, ki, para in sorted(scored, key=lambda x: -x[0])[:per_claim]:
            item = items.setdefault((pi, ki), {"url": pages[pi]["url"], "title": pages[pi]["title"],
                                               "text": para[:max_len], "claims": []})
            item["claims"].append(ci)
    out = sorted(items.values(), key=lambda x: min(x["claims"]))
    for i, it in enumerate(out, 1):
        it["id"] = f"E{i}"
    return out


def read_best(candidates: list[dict], topic: str, timeout: float, max_pages: int = 8,
              max_chars: int = 2500, core: str = "", per_domain: int = 3) -> list[dict]:
    """Rank candidates and fetch them until `max_pages` readable, relevant pages are found.

    At most `per_domain` pages per site, so one large site cannot crowd out others."""
    s = requests.Session()
    ranked = rank(candidates, topic, core)
    core_terms = terms(core)
    pages: list[dict] = []
    per: dict[str, int] = {}
    for i in range(0, min(len(ranked), max_pages * 4), max_pages):
        batch = ranked[i:i + max_pages]
        with ThreadPoolExecutor(max_workers=8) as ex:
            results = list(ex.map(lambda c: read_page(c["url"], topic, timeout, max_chars, s), batch))
        for c, page in zip(batch, results):
            if not page or len(pages) >= max_pages or page["url"] in {p["url"] for p in pages}:
                continue
            if core_terms and not core_match(core_terms, page["title"] + " " + page["excerpt"][:1500]):
                continue  # page text turned out to be off-topic
            host = domain_of(page["url"])
            if per.get(host, 0) >= per_domain:
                continue
            per[host] = per.get(host, 0) + 1
            pages.append({**c, **page, "title": page["title"] or c["title"]})
        if len(pages) >= max_pages:
            break
    return pages
