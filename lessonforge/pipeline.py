"""Step orchestration with per-step status, persistence and retry.

Each step (research -> generate -> qc1 / qc2) records its own status, error and
attempt count on the project, and the project is saved before and after every
step. A failed step can be retried on its own; earlier results and instructor
edits are never discarded.
"""
from __future__ import annotations

import logging
import traceback
from concurrent.futures import ThreadPoolExecutor
from typing import Callable

from .config import Settings
from .generator import generate_draft, render_markdown
from .llm import GeminiClient, LLMClient, LLMError
from .models import LessonProject, now_iso
from .qc import run_qc1, run_qc2
from .research import run_research
from .storage import ProjectStore, add_version

log = logging.getLogger(__name__)
Progress = Callable[[str, str], None]  # (step, message)

TITLE_MAX, OBJECTIVE_MAX = 200, 800


class StepError(RuntimeError):
    pass


def validate_inputs(title: str, objective: str) -> list[str]:
    errors = []
    title, objective = (title or "").strip(), (objective or "").strip()
    if not title:
        errors.append("Lesson title is required.")
    elif len(title) < 3:
        errors.append("Lesson title is too short.")
    elif len(title) > TITLE_MAX:
        errors.append(f"Lesson title must be under {TITLE_MAX} characters.")
    if not objective:
        errors.append("Learning objective is required.")
    elif len(objective.split()) < 4:
        errors.append("Learning objective is too short. Describe what learners should be able to do, "
                      "e.g. 'Explain ... and distinguish between ...'.")
    elif len(objective) > OBJECTIVE_MAX:
        errors.append(f"Learning objective must be under {OBJECTIVE_MAX} characters.")
    return errors


class Pipeline:
    def __init__(self, store: ProjectStore, settings: Settings,
                 llm_factory: Callable[[Settings], LLMClient] = GeminiClient):
        self.store = store
        self.settings = settings
        self._llm_factory = llm_factory
        self._llm: LLMClient | None = None

    @property
    def llm(self) -> LLMClient:
        if self._llm is None:
            self._llm = self._llm_factory(self.settings)
        return self._llm

    # ------------------------------------------------------------------ #
    def _check_ready(self, project: LessonProject, step: str) -> None:
        if step == "generate" and not project.research:
            raise StepError("Run research first.")
        if step in ("qc1", "qc2") and not project.versions:
            raise StepError("Generate the lesson first.")
        if step == "qc1" and not project.research:
            raise StepError("QC1 needs the research sources. Run research first.")

    def _execute(self, project: LessonProject, step: str) -> None:
        s = self.settings
        if step == "research":
            project.research = run_research(project.title, project.objective, self.llm, s)
            # a lesson built on the old research is now out of date
            if project.steps["generate"].status == "done":
                project.steps["generate"].status = "stale"
        elif step == "generate":
            draft, notes = generate_draft(project.title, project.objective, project.research, self.llm, s)
            project.draft = draft
            md = render_markdown(draft, project.research, s.lesson_minutes)
            add_version(project, md, "generated", "; ".join(notes))
        elif step == "qc1":
            project.qc1 = run_qc1(project.current_markdown, project.title, project.objective,
                                  project.research, self.llm, s, project.current_version)
        elif step == "qc2":
            project.qc2 = run_qc2(project.current_markdown, project.title, project.objective,
                                  self.llm, s, project.research, project.current_version)
        else:
            raise StepError(f"Unknown step {step}")

    def run_step(self, project: LessonProject, step: str) -> bool:
        """Run one step and persist the result. Returns True on success. Never raises."""
        ok = self._run_step_nosave(project, step)
        self.store.save(project)
        return ok

    def run_qc(self, project: LessonProject) -> dict[str, bool]:
        """Run both QC layers in parallel on the current version (independent calls)."""
        results: dict[str, bool] = {}
        # Each thread works on the same project object but touches different fields.
        try:
            _ = self.llm  # create the client once, in this thread
        except LLMError as exc:
            for step in ("qc1", "qc2"):
                project.steps[step].status, project.steps[step].error = "failed", str(exc)
            self.store.save(project)
            return {"qc1": False, "qc2": False}
        with ThreadPoolExecutor(max_workers=2) as ex:
            futures = {step: ex.submit(self._run_step_nosave, project, step) for step in ("qc1", "qc2")}
            for step, f in futures.items():
                results[step] = f.result()
        self.store.save(project)
        return results

    def _run_step_nosave(self, project: LessonProject, step: str) -> bool:
        state = project.steps[step]
        state.status, state.error, state.started_at = "running", "", now_iso()
        state.attempts += 1
        try:
            self._check_ready(project, step)
            self._execute(project, step)
            state.status = "done"
            return True
        except Exception as exc:  # noqa: BLE001
            if not isinstance(exc, (LLMError, StepError, ValueError)):
                log.error("step %s failed:\n%s", step, traceback.format_exc())
            state.status, state.error = "failed", str(exc)
            return False
        finally:
            state.finished_at = now_iso()

    def run_all(self, project: LessonProject, progress: Progress | None = None) -> bool:
        """Run every step that is not done yet, stopping at the first failure."""
        progress = progress or (lambda step, msg: None)
        for step in ("research", "generate"):
            if project.steps[step].status == "done":
                continue
            progress(step, "running")
            if not self.run_step(project, step):
                progress(step, "failed")
                return False
            progress(step, "done")
        todo = [s for s in ("qc1", "qc2") if project.steps[s].status != "done"]
        if todo:
            progress("qc", "running")
            if len(todo) == 2:
                res = self.run_qc(project)
            else:
                res = {todo[0]: self.run_step(project, todo[0])}
            progress("qc", "done" if all(res.values()) else "failed")
            return all(res.values())
        return True
