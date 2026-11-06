import pytest

from lessonforge.generator import render_markdown, sanitize_draft
from lessonforge.llm import InvalidJSONError, LLMError, extract_json, parse_model, with_retries
from lessonforge.models import ClaimCheck, ExtractedClaims, ResearchBundle, Source, Video
from lessonforge.pipeline import validate_inputs
from lessonforge.qc import accuracy_score, structure_checks
from lessonforge.research import (classify_domain, insert_citations, parse_duration_text, parse_iso_duration,
                                  parse_youtube_results, split_notes_and_extras)
from lessonforge.timing import analyse_timing, fit_minutes, parse_sections
from tests.fakes import make_draft


def bundle():
    return ResearchBundle(notes="n", sources=[Source(id="S1", title="RFC 9110", url="https://www.rfc-editor.org/rfc/rfc9110")],
                          videos=[Video(id="V1", video_id="abc", title="HTTP explained",
                                        url="https://www.youtube.com/watch?v=abc")])


# ---- llm helpers -------------------------------------------------------------
def test_extract_json_variants():
    assert extract_json('```json\n{"a": 1}\n```') == '{"a": 1}'
    assert extract_json('Sure! {"a": 1} hope that helps') == '{"a": 1}'
    with pytest.raises(ValueError):
        extract_json("no json here")


def test_parse_model_tolerates_trailing_comma():
    m = parse_model('{"claims": [{"claim": "x", "location": "y"},]}', ExtractedClaims)
    assert m.claims[0].claim == "x"


def test_with_retries_retries_then_succeeds(monkeypatch):
    monkeypatch.setattr("lessonforge.llm.time.sleep", lambda s: None)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("503 UNAVAILABLE")
        return "ok"
    assert with_retries(flaky, max_retries=3) == "ok"
    assert calls["n"] == 3


def test_with_retries_gives_friendly_error(monkeypatch):
    monkeypatch.setattr("lessonforge.llm.time.sleep", lambda s: None)

    def bad_key():
        raise RuntimeError("400 API key not valid")
    with pytest.raises(LLMError, match="API key"):
        with_retries(bad_key, max_retries=3)

    def bad_json():
        raise InvalidJSONError("nope")
    with pytest.raises(LLMError, match="malformed"):
        with_retries(bad_json, max_retries=1)


# ---- input validation --------------------------------------------------------
def test_validate_inputs():
    assert validate_inputs("", "") == ["Lesson title is required.", "Learning objective is required."]
    assert any("too short" in e for e in validate_inputs("HTTP", "Explain"))
    assert validate_inputs("HTTP Requests", "Explain GET and POST methods") == []


# ---- research helpers ----------------------------------------------------------
def test_classify_domain():
    assert classify_domain("https://www.rfc-editor.org/rfc/rfc9110")[1] == "high"
    assert classify_domain("https://developer.mozilla.org/x")[0] == "official documentation"
    assert classify_domain("https://medium.com/@x/y")[1] == "low"
    assert classify_domain("https://cs.stanford.edu/x")[0] == "university"


def test_split_notes_and_extras():
    notes, extras = split_notes_and_extras('brief text\n```json\n{"video_search_queries": ["a"]}\n```')
    assert notes == "brief text" and extras["video_search_queries"] == ["a"]
    assert split_notes_and_extras("just text") == ("just text", {})


def test_insert_citations():
    out = insert_citations("GET is safe. POST is not.", [{"text": "GET is safe.", "source_indices": [0, 2]}],
                           {0: "S1", 2: "S3"})
    assert out == "GET is safe. [S1, S3] POST is not."


def test_youtube_parsing():
    html = ('<script>var ytInitialData = {"contents": {"x": [{"videoRenderer": {"videoId": "abc123",'
            '"title": {"runs": [{"text": "HTTP explained"}]}, "ownerText": {"runs": [{"text": "Chan"}]},'
            '"lengthText": {"simpleText": "12:05"}}}]}};</script>')
    vids = parse_youtube_results(html)
    assert vids[0]["video_id"] == "abc123" and vids[0]["duration_seconds"] == 725
    assert parse_duration_text("1:02:03") == 3723 and parse_duration_text("LIVE") is None
    assert parse_iso_duration("PT12M5S") == 725


# ---- timing ------------------------------------------------------------------
def test_fit_minutes():
    assert sum(fit_minutes([10, 20, 30], 45)) == 45
    assert fit_minutes([5, 5], 45) == [5, 5]


def test_timing_analysis():
    md = ("# T\n\n## 1. Intro (3 min)\n<!-- kind: hook -->\n" + "word " * 100 +
          "\n## 2. Practice (10 min)\n<!-- kind: activity -->\n" + "word " * 2000 + "\n## Key takeaways\n- x\n")
    secs = parse_sections(md)
    assert [s["kind"] for s in secs] == ["hook", "activity"]
    t = analyse_timing(md, 45)
    assert t.declared_minutes == 13 and t.within_budget  # activity reading time is not added
    long_md = md.replace("hook -->\n", "hook -->\n" + "word " * 9000, 1)  # ~53 min of reading
    assert not analyse_timing(long_md, 45).within_budget


# ---- generation / rendering ---------------------------------------------------
def test_sanitize_and_render():
    draft = make_draft(minutes=(4, 11, 11, 8, 9, 5, 2), bad_cite=True)  # 50 min, invented S99 / V9
    notes = sanitize_draft(draft, bundle(), 45)
    assert sum(s.minutes for s in draft.sections) == 45
    assert all("S99" not in s.content_markdown and "S99" not in s.source_ids for s in draft.sections)
    assert [v.video_ref for v in draft.recommended_videos] == ["V1"]
    assert notes
    md = render_markdown(draft, bundle(), 45)
    assert "## References" in md and "rfc9110" in md and "youtube.com/watch?v=abc" in md
    assert analyse_timing(md, 45).declared_minutes == 45
    checks = {c["check"]: c["passed"] for c in structure_checks(md, bundle(), 45)}
    assert all(checks.values()), checks


def test_accuracy_score():
    assert accuracy_score([ClaimCheck(claim="a", verdict="supported"),
                           ClaimCheck(claim="b", verdict="incorrect")]) == 50
    assert accuracy_score([]) == 0


def test_book_matches():
    from lessonforge.research import book_matches
    assert book_matches("HTTP: The Definitive Guide", "David Gourley", "HTTP", "David Gourley, Brian Totty")
    assert not book_matches("RESTful Web Services", "Leonard Richardson", "RESTful Web APIs", "Leonard Richardson")
    assert not book_matches("Pro Git", "Scott Chacon", "Pro Git", "Someone Else")


def test_padded_sections_are_flagged():
    md = "".join(f"## {i}. S{i} (8 min)\n<!-- kind: concept -->\n" + "word " * 150 + "\n" for i in range(1, 4))
    t = analyse_timing(md, 45)
    assert all(p["padded"] for p in t.per_section) and "padded" in t.note


def test_rank_gates_off_topic_high_authority_pages():
    from lessonforge.websearch import rank
    cands = [{"title": "switch - JavaScript | MDN", "snippet": "The switch statement",
              "url": "https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Statements/switch", "origin": "mdn"},
             {"title": "Git - Basic Branching and Merging", "snippet": "",
              "url": "https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging", "origin": "proposed"}]
    ranked = rank(cands, "Git Branching and Merging create switch branches merge conflict", core="Git Branching and Merging")
    assert [c["url"] for c in ranked] == [cands[1]["url"]]


def test_daily_quota_falls_back_to_next_model(monkeypatch):
    from types import SimpleNamespace
    from lessonforge.config import Settings
    from lessonforge.llm import GeminiClient
    from google.genai import types
    monkeypatch.setattr("lessonforge.llm.time.sleep", lambda s: None)
    GeminiClient._exhausted.clear()
    calls = []

    def fake_generate(model, contents, config):
        calls.append(model)
        if model == "big":
            raise RuntimeError("429 RESOURCE_EXHAUSTED quotaId GenerateRequestsPerDayPerProjectPerModel-FreeTier")
        return SimpleNamespace(text="hello", candidates=[])
    c = object.__new__(GeminiClient)
    c._types, c.settings = types, Settings(gemini_api_key="x", model="big", fallback_models=("small",))
    c.client = SimpleNamespace(models=SimpleNamespace(generate_content=fake_generate))
    assert c.generate("p", "s") == "hello"
    assert calls == ["big", "small"]  # no wasted retries on the exhausted model
    assert c.generate("p", "s") == "hello" and calls[-1] == "small"  # remembered
    GeminiClient._exhausted.clear()
