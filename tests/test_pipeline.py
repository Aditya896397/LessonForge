import io
import zipfile

import pytest

from lessonforge.config import Settings
from lessonforge.export import build_zip
from lessonforge.pipeline import Pipeline
from lessonforge.revise import revise_lesson
from lessonforge.storage import ProjectStore, add_version
from tests.fakes import FakeLLM

OBJ = "Explain GET and POST methods and distinguish 2xx/4xx/5xx"


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """No network in tests: stub every HTTP-touching research helper."""
    monkeypatch.setattr("lessonforge.research.resolve_redirect", lambda url, timeout, session=None: url)
    monkeypatch.setattr("lessonforge.qc.resolve_redirect", lambda url, timeout, session=None: url)
    monkeypatch.setattr("lessonforge.research.probe_page",
                        lambda url, timeout, session=None: {"url": url, "status": 200, "reachable": True,
                                                            "title": "Page"})
    monkeypatch.setattr("lessonforge.research.search_books", lambda sugs, q, timeout, limit=4, api_key="": (
        [{"title": "HTTP: The Definitive Guide", "publisher": "OReilly", "url": "https://books.google.com/x",
          "snippet": "", "verified_suggestion": True}], []))
    monkeypatch.setattr("lessonforge.research._grounding_available", None)
    monkeypatch.setattr("lessonforge.research._marker", lambda settings: settings.data_dir / ".grounding_marker")
    page = {"url": "https://www.rfc-editor.org/rfc/rfc9110", "title": "RFC 9110: HTTP Semantics", "status": 200,
            "excerpt": "GET is safe and idempotent. POST is not idempotent. " * 10, "origin": "proposed",
            "source_type": "standard / specification", "trust": "high"}
    monkeypatch.setattr("lessonforge.websearch.discover", lambda *a, **k: ([page], []))
    page2 = {**page, "url": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Methods", "title": "MDN"}
    monkeypatch.setattr("lessonforge.websearch.read_best", lambda *a, **k: [page, page2])
    monkeypatch.setattr("lessonforge.research.search_videos", lambda queries, settings, limit=6: (
        [{"video_id": "abc", "title": "HTTP explained", "channel": "Chan", "duration_text": "10:00",
          "duration_seconds": 600, "views_text": "", "verified": True}], []))


def make(tmp_path, llm):
    settings = Settings(gemini_api_key="test", data_dir=tmp_path)
    store = ProjectStore(tmp_path)
    return store, Pipeline(store, settings, llm_factory=lambda s: llm), settings


def test_full_pipeline_and_export(tmp_path):
    llm = FakeLLM()
    store, pl, _ = make(tmp_path, llm)
    p = store.create("HTTP Requests and Responses", OBJ)
    assert pl.run_all(p)
    p = store.load(p.id)  # everything persisted
    assert all(s.status == "done" for s in p.steps.values())
    assert p.research.sources[0].id == "S1" and "[S1, S2]" in p.research.notes
    assert p.current_version == 1 and "## References" in p.current_markdown
    assert "[S99]" not in p.current_markdown  # invented citation removed
    # QC1: incorrect claim becomes a critical issue, score computed from verdicts
    assert p.qc1.accuracy_score == 50
    assert any(i.severity == "critical" and "POST" in i.quote for i in p.qc1.issues)
    assert p.qc1.claims[0].evidence_urls  # verdict linked to grounding evidence
    # QC2 independent review + deterministic checks
    assert p.qc2.timing.within_budget and p.qc2.overall_score > 0
    assert any(i.layer == "QC2" for i in p.qc2.issues)
    names = zipfile.ZipFile(io.BytesIO(build_zip(p))).namelist()
    for f in ("lesson.md", "lesson.html", "references.md", "qc1_research_accuracy_report.md",
              "qc2_instructional_quality_report.md", "qc_reports.json"):
        assert f in names


def test_failed_step_preserves_work_and_can_be_retried(tmp_path):
    llm = FakeLLM(fail_on={"LessonDraft"})
    store, pl, _ = make(tmp_path, llm)
    p = store.create("HTTP Requests and Responses", OBJ)
    assert not pl.run_all(p)
    p = store.load(p.id)
    assert p.steps["research"].status == "done" and p.research is not None
    assert p.steps["generate"].status == "failed" and "simulated" in p.steps["generate"].error
    assert p.steps["qc1"].status == "pending"
    llm.fail_on.clear()
    research_calls = llm.calls.count("research")
    assert pl.run_all(p)  # retry continues from the failed step
    assert llm.calls.count("research") == research_calls  # research not repeated
    assert store.load(p.id).steps["generate"].attempts == 2


def test_one_qc_layer_failing_does_not_block_the_other(tmp_path):
    llm = FakeLLM(fail_on={"verify"})
    store, pl, _ = make(tmp_path, llm)
    p = store.create("HTTP Requests and Responses", OBJ)
    assert not pl.run_all(p)
    p = store.load(p.id)
    assert p.steps["qc1"].status == "failed" and p.steps["qc2"].status == "done" and p.qc2


def test_missing_api_key_is_reported_not_crashing(tmp_path):
    from lessonforge.llm import GeminiClient
    settings = Settings(gemini_api_key="", data_dir=tmp_path)
    store = ProjectStore(tmp_path)
    pl = Pipeline(store, settings, llm_factory=GeminiClient)
    p = store.create("HTTP Requests and Responses", OBJ)
    assert not pl.run_all(p)
    assert "GEMINI_API_KEY" in store.load(p.id).steps["research"].error


def test_edits_create_versions_and_mark_qc_stale(tmp_path):
    llm = FakeLLM()
    store, pl, settings = make(tmp_path, llm)
    p = store.create("HTTP Requests and Responses", OBJ)
    pl.run_all(p)
    original = p.current_markdown
    add_version(p, original + "\nExtra note.\n", "instructor edit")
    assert p.current_version == 2 and p.versions[0].markdown == original
    assert p.steps["qc1"].status == "stale" and p.steps["qc2"].status == "stale"
    assert add_version(p, p.current_markdown, "noop") is None  # unchanged text is not a new version
    # apply a QC recommendation
    issue = p.qc1.issues[0]
    rev = revise_lesson(p.current_markdown, [issue], "", p.research, llm, settings)
    assert "RFC 9110" in rev.revised_markdown and rev.change_log


def test_falls_back_to_web_retrieval_when_grounding_has_no_quota(tmp_path):
    llm = FakeLLM(fail_on={"grounding"})
    store, pl, _ = make(tmp_path, llm)
    p = store.create("HTTP Requests and Responses", OBJ)
    assert pl.run_all(p), {k: v.error for k, v in p.steps.items()}
    p = store.load(p.id)
    assert p.research.method == "web-retrieval"
    assert p.research.sources[0].url.endswith("rfc9110") and "[S1]" in p.research.notes
    assert any("not available" in w for w in p.research.warnings)
    assert p.qc1.verification_method == "web-retrieval"
    assert p.qc1.claims[0].evidence_urls == ["https://www.rfc-editor.org/rfc/rfc9110"]
    assert p.qc1.accuracy_score == 50
    assert llm.calls.count("research") == 1  # grounding not retried after it is known to be unavailable
