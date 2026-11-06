# LessonForge: AI-Powered Lesson Creation Tool

LessonForge turns a **Lesson Title** and a **Learning Objective** into a well-researched,
**45-minute lesson**. It researches websites, books and YouTube videos, writes structured lesson
content, and checks it with **two independent Quality Control layers**. Instructors can then
review, edit, apply QC fixes, preview and export the lesson.

Built for the Kalvium AI Research Intern task.

---

## Features

| Requirement | How it is implemented |
|---|---|
| Inputs: title + objective | Validated form (empty, too-short and too-long inputs are rejected with clear messages) |
| Research: websites | **Two backends, chosen automatically.** (a) Gemini with the **Google Search grounding tool** writes a research brief. The pages it used come from the API's grounding metadata, so they are real search results and not URLs the model typed. Each page is resolved, fetched to check it is reachable, and classified (spec, official docs, university, blog…). (b) If the API key has no grounding quota (common on free keys), the tool switches to **direct web retrieval**: Gemini proposes specific authoritative pages and search terms, candidates also come from the Wikipedia and MDN search APIs (plus Tavily if `TAVILY_API_KEY` is set), every page is **fetched** (invented URLs simply fail and are dropped), the most relevant passages are extracted, and the brief is written only from those cited excerpts |
| Research: books | Gemini suggests books. Each one is **verified** in Google Books (Open Library as fallback) and kept only if the title *and* author match a real catalogue record |
| Research: YouTube | Gemini suggests search queries. Videos are found via the YouTube Data API (optional key) or the public results page, **confirmed with YouTube oEmbed**, and ranked toward 3–20 minute explainers |
| Structured, engaging lesson | Pydantic-schema output: hook → one concept section per objective component → worked example → hands-on activity → knowledge check (5–6 MCQs with explanations) → summary. Each section carries inline `[S#]` citations |
| 45-minute design | Every section has a time budget. Totals over 45 are scaled down deterministically, and a **word-count reading-time estimator** checks that the text actually fits |
| Supplementary videos + references | 2–3 verified videos with "why / when to watch", and a reference list (websites, books, videos) at the end |
| **QC 1: research & factual accuracy** | (1) extract key claims → (2) **re-verify each claim against freshly retrieved evidence** (a new Google-Search-grounded call, or in retrieval mode a separate call that sees only the claims picks where to look, the pages are fetched and every verdict must cite evidence excerpts `[E#]`), never the original research → verdicts *supported / partially supported / unsupported / incorrect / misleading*, with corrections and evidence links → (3) source reliability/relevance audit plus gaps, uncited claims and inconsistencies. The accuracy score is **computed from the verdicts**, not invented by the model |
| **QC 2: instructional quality** | Objective decomposed into components with coverage (full/partial/missing), a 7-criterion rubric, **deterministic structure checks** (hook, examples, activity, quiz size, summary, citations, references) and the **time-budget check**. QC 2 sees only the lesson and the objective (no research and no QC 1 output), so the two layers stay independent |
| Separate audit reports | Each layer has its own report (UI tab plus Markdown export) listing issues with location, quote, problem and suggested fix |
| Review, edit, save | Markdown editor with a live time-budget check. Every save is a **new version**; the Versions tab can restore any earlier one |
| Apply QC recommendations | Pick issues (or type your own instruction). The AI makes only those edits, and you see a **diff + preview** and accept or discard. Applied issues are tracked |
| Preview | Rendered lesson plus embedded videos |
| Export | ZIP with `lesson.md`, `lesson.html` (print to PDF), `references.md`, `research_brief.md`, both QC reports (`.md`) and `qc_reports.json`, or each file on its own |
| Error handling | Per-step status (pending / running / done / failed / stale) with a **Retry** button per step. Results are saved to disk after every step, so failures never lose earlier work. Instructor edits are never overwritten (regenerating creates a new version). Gemini calls use exponential back-off on rate limits and 5xx errors, and malformed JSON is re-sampled. Book and video failures downgrade to warnings instead of failing the run |

## Architecture

```
            ┌──────────────┐     Google Search grounding      ┌─────────────────────┐
 title ───▶ │  1. Research │ ───────────────────────────────▶ │ research brief +    │
 objective  │  research.py │  Google Books / Open Library     │ S# web sources,     │
            └──────────────┘  YouTube search + oEmbed         │ B# books, V# videos │
                                                              └──────────┬──────────┘
            ┌──────────────┐  JSON schema (LessonDraft)                  │
            │ 2. Generate  │ ◀───────────────────────────────────────────┘
            │ generator.py │ ─▶ sanitize (drop invented citations, fit 45 min) ─▶ Markdown v1
            └──────┬───────┘
                   │ (run in parallel, independent prompts)
         ┌─────────┴──────────┐
 ┌───────▼────────┐   ┌───────▼─────────┐
 │ 3a. QC 1       │   │ 3b. QC 2        │
 │ claims ─▶ fresh│   │ timing + struct │
 │ grounded check │   │ checks + rubric │
 │ + source audit │   │ + obj. coverage │
 └───────┬────────┘   └───────┬─────────┘
         └─────────┬──────────┘
          ┌────────▼─────────┐     ┌──────────────┐     ┌───────────┐
          │ 4. Instructor:   │ ──▶ │ revise.py    │ ──▶ │ export.py │
          │ edit / apply QC  │     │ diff, accept │     │ md/html/  │
          │ fixes / versions │     │ → new version│     │ zip       │
          └──────────────────┘     └──────────────┘     └───────────┘
```

| File | Responsibility |
|---|---|
| `app.py` | Streamlit UI |
| `cli.py` | Headless runner (generate and export without the UI) |
| `lessonforge/llm.py` | Gemini wrapper: grounded vs structured calls, retries, JSON repair, friendly errors |
| `lessonforge/prompts.py` | All prompts in one place |
| `lessonforge/research.py` | Web/books/YouTube research and verification |
| `lessonforge/generator.py` | Lesson draft → sanitised → Markdown |
| `lessonforge/timing.py` | Deterministic 45-minute analysis on the Markdown (works after edits too) |
| `lessonforge/qc.py` | QC 1 and QC 2 |
| `lessonforge/revise.py` | Apply selected QC recommendations, diff |
| `lessonforge/pipeline.py` | Step orchestration, status, retry, persistence |
| `lessonforge/storage.py` | Atomic JSON persistence, versioning |
| `lessonforge/export.py` | Markdown/HTML/ZIP export and report rendering |

## Setup

Requirements: **Python 3.10–3.12** (3.11 recommended) and a free **Gemini API key** from
<https://aistudio.google.com/apikey>.

```bash
python -m venv .venv
# Windows:  .venv\Scripts\activate      macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # Windows: copy .env.example .env
# open .env and set GEMINI_API_KEY=...
streamlit run app.py
```

The app opens at <http://localhost:8501>. Click **"Use: HTTP Requests and Responses"** to load the
sample input from the brief, then **Research & generate** (takes about 1–3 minutes).

### Headless (CLI)

```bash
python cli.py --sample http          # sample from the brief
python cli.py --sample git           # second test topic
python cli.py --title "..." --objective "..."
python cli.py --resume <project-id>  # retry failed steps of a saved project
```

Outputs go to `examples/<project-id>/` (same files as the ZIP export).

### Tests

```bash
pytest -q
```

The 25 tests run **offline**: a deterministic fake LLM and stubbed HTTP. They cover the full pipeline,
the grounding → web-retrieval fallback, the per-model daily-quota fallback, relevance gating of off-topic sources, thin-section detection, failure and retry behaviour (a failed step keeps earlier work and retries without repeating
research), one QC layer failing without blocking the other, the missing-API-key path, versioning
and stale QC reports, revision, export contents, citation sanitising, timing maths, YouTube
parsing, book verification and a Streamlit UI smoke test.

## Example outputs (real runs)

`examples/` holds full exports from real runs with a free-tier Gemini key. Google Search grounding
had no quota, so the direct-retrieval backend was used:

| Topic | Sources found | QC 1 accuracy | QC 2 instructional | Notes |
|---|---|---|---|---|
| HTTP Requests and Responses (sample from the brief) | MDN (status codes, methods, GET, POST, overview) + RFC 9110 | 88/100 | 90/100 | Both layers independently flagged the missing 5xx examples. QC 1 caught the "GET must not have a body" overstatement (MDN says "should not") |
| Git Branching and Merging (own topic) | git-scm.com book + docs, Atlassian tutorials | 89 → 88 after fixes | 84 → 87 after fixes | Shows the **apply-QC-fixes** loop: v1 → selected fixes applied → v2 → both QC layers re-run. QC 1 then flagged the new claims the expansion introduced |

How the outputs shaped the design (worth showing in the demo):
- A first Git run picked off-topic MDN pages (the JavaScript `switch` statement) because "switch" matched
  and MDN counts as a high-trust domain. QC 1 scored it 62 and QC 2 scored it 57. Fix: relevance gating on
  the lesson title's core terms, relevance weighted above authority, and at most 3 pages per domain.
- A lite-model draft cut off mid-sentence. Fix: a self-check after generation (truncated or too-thin
  sections trigger one regeneration with specific feedback) plus a deterministic "No truncated
  sections" check in QC 2.
- QC 1 originally matched evidence to the topic as a whole, so true but specific claims came out
  "unsupported". Fix: evidence paragraphs are now selected **per claim** across all fetched pages.

## Technical decisions

- **Gemini 3.5 Flash** (configurable via `GEMINI_MODEL` / `GEMINI_QC_MODEL`). It has a free tier. A
  stronger model can be set for QC 1 alone. Free-tier quotas are **per model per day** (about 20
  requests for Flash), so when one model's daily quota runs out the client switches automatically to
  `GEMINI_FALLBACK_MODELS` (default: `gemini-3.5-flash-lite`, `gemini-3.1-flash-lite`). One full
  lesson plus both QC layers takes roughly 9–10 requests.
- **Research never relies on the model's memory alone.** With Google Search grounding, facts come
  from live search results. Free-tier keys often have no grounding quota, so `SEARCH_BACKEND=auto`
  detects the quota error once and switches to direct retrieval: fetched pages, extracted passages,
  and a brief that must cite them. Scraping consumer search engines was tried and rejected: they
  serve CAPTCHAs or degrade results for scripts. Keyless sources are the Wikipedia and MDN APIs plus
  model-proposed pages that must load; `TAVILY_API_KEY` adds full web search.
- **Grounded calls and structured calls are kept separate.** Gemini cannot combine the search tool
  with a JSON response schema, so search-based steps return text plus grounding metadata, and the
  generation and review steps use strict Pydantic schemas.
- **"LLM proposes, APIs verify."** Sources come from grounding metadata, books from catalogue
  lookups, and videos from YouTube itself. Citations the model invents (`[S99]`) and unverified
  video picks are removed before the lesson is saved.
- **Two independent QC layers.** QC 1 re-searches each claim in a new context, so it is not
  re-reading the research it was built from. QC 2 never sees the research or QC 1. They run in
  parallel.
- **Scores are computed, not asked for.** The QC 1 accuracy score is a weighted average of claim
  verdicts. The QC 2 score is 70% rubric, 20% objective coverage and 10% automatic checks.
  Timing is pure code.
- **Markdown is the source of truth after generation**, so timing and structure checks keep working
  on instructor-edited text. Section headings carry their budget: `## 2. GET vs POST (8 min)`.
- **Nothing is overwritten.** Every edit, applied fix, regeneration or restore creates a version.
  QC reports record which version they audited and are marked *stale* when the text changes.
- **No pandas/pyarrow in the UI.** Tables are rendered as Markdown, so the app also runs on
  Windows machines where Application Control blocks those native DLLs.

## Limitations

- Without grounding or a Tavily key, retrieval covers model-proposed pages plus Wikipedia/MDN.
  That works well for technical topics, but niche topics may get fewer sources. The research tab
  shows how each source was found.
- Fact-checking is only as good as the evidence retrieved. "Unsupported" means no
  authoritative evidence was found, not that the claim is wrong. Instructors should still review
  critical/major findings.
- Searching YouTube without an API key relies on the public results page. Set `YOUTUBE_API_KEY` for
  the official API.
- The anonymous Google Books quota is shared and often exhausted. The tool then falls back to Open
  Library automatically, or you can set `GOOGLE_BOOKS_API_KEY`.
- PDF export is done by opening `lesson.html` and printing to PDF (this keeps dependencies light).

## Acknowledgements

Google Gemini API and the `google-genai` SDK (generation, Google Search grounding) · Wikipedia and MDN search APIs · Tavily (optional) · BeautifulSoup · Streamlit ·
Pydantic · Requests · Python-Markdown · Google Books API · Open Library Search API · YouTube
(search results / Data API v3 and oEmbed). AI coding assistants were used during development. The
design and implementation are explained above and in code comments.
