"""Smoke-test the Streamlit UI with an offline-generated project (no API key needed)."""
from pathlib import Path

import pytest

from streamlit.testing.v1 import AppTest

from lessonforge.config import Settings
from lessonforge.pipeline import Pipeline
from lessonforge.storage import ProjectStore
from tests.fakes import FakeLLM
from tests.test_pipeline import offline  # noqa: F401  (reuse the network stubs)

APP = str(Path(__file__).resolve().parent.parent / "app.py")


@pytest.fixture
def project(tmp_path, monkeypatch):
    monkeypatch.setenv("LESSONFORGE_DATA_DIR", str(tmp_path))
    store = ProjectStore(tmp_path)
    p = store.create("HTTP Requests and Responses", "Explain GET and POST methods and distinguish 2xx/4xx/5xx")
    Pipeline(store, Settings(gemini_api_key="x", data_dir=tmp_path), llm_factory=lambda s: FakeLLM()).run_all(p)
    return p


def test_new_lesson_page_validates_empty_input(tmp_path, monkeypatch):
    monkeypatch.setenv("LESSONFORGE_DATA_DIR", str(tmp_path))
    at = AppTest.from_file(APP, default_timeout=30).run()
    assert not at.exception
    at.button(key="FormSubmitter:new-🚀 Research & generate").click().run()
    assert any("required" in e.value for e in at.error)


def test_project_page_renders_all_tabs(project):
    at = AppTest.from_file(APP, default_timeout=30)
    at.session_state["pid"] = project.id
    at.run()
    assert not at.exception, at.exception
    labels = [t.label for t in at.tabs]
    assert any("QC 1" in label for label in labels) and any("Export" in label for label in labels)
    assert any("Accuracy score" in m.label for m in at.metric)
    assert any("Instructional score" in m.label for m in at.metric)
