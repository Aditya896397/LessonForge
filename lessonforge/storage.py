"""File-based persistence: one JSON file per lesson project.

Every pipeline step writes its result to disk as soon as it finishes, so a
failure in a later step (or a closed browser tab) never loses earlier work.
Instructor edits are stored as new *versions*; nothing is ever overwritten.
Writes are atomic (temp file + rename) so a crash cannot corrupt a project.
"""
from __future__ import annotations

import os
import re
import tempfile
import uuid
from pathlib import Path

from .models import LessonProject, LessonVersion, now_iso


def slugify(text: str, max_len: int = 40) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return (slug[:max_len].rstrip("-")) or "lesson"


class ProjectStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, project_id: str) -> Path:
        if not re.fullmatch(r"[a-z0-9-]+", project_id):
            raise ValueError(f"invalid project id: {project_id!r}")
        return self.root / f"{project_id}.json"

    def create(self, title: str, objective: str) -> LessonProject:
        pid = f"{slugify(title)}-{uuid.uuid4().hex[:6]}"
        project = LessonProject(id=pid, title=title.strip(), objective=objective.strip())
        self.save(project)
        return project

    def save(self, project: LessonProject) -> None:
        project.updated_at = now_iso()
        path = self._path(project.id)
        fd, tmp = tempfile.mkstemp(dir=self.root, prefix=".tmp-", suffix=".json")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(project.model_dump_json(indent=2))
            os.replace(tmp, path)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def load(self, project_id: str) -> LessonProject:
        return LessonProject.model_validate_json(self._path(project_id).read_text(encoding="utf-8"))

    def list(self) -> list[LessonProject]:
        projects = []
        for p in self.root.glob("*.json"):
            try:
                projects.append(LessonProject.model_validate_json(p.read_text(encoding="utf-8")))
            except Exception:  # noqa: BLE001 - skip unreadable files, never crash the UI
                continue
        return sorted(projects, key=lambda x: x.updated_at, reverse=True)

    def delete(self, project_id: str) -> None:
        self._path(project_id).unlink(missing_ok=True)


def add_version(project: LessonProject, markdown: str, origin: str, note: str = "") -> LessonVersion | None:
    """Append a new lesson version. Returns None if the text did not change."""
    if project.versions and project.versions[-1].markdown == markdown:
        return None
    version = LessonVersion(number=project.current_version + 1, markdown=markdown,
                            origin=origin, note=note)
    project.versions.append(version)
    # QC reports describe a specific version; mark them stale when the text changes.
    for step in ("qc1", "qc2"):
        if project.steps[step].status == "done":
            project.steps[step].status = "stale"
    return version
