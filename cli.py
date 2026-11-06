"""Headless runner: generate a lesson + both QC reports and export them.

Examples:
    python cli.py --sample http
    python cli.py --title "Git Branching and Merging" --objective "Create and switch ..."
    python cli.py --resume <project-id>        # retry failed steps of a saved project
"""
from __future__ import annotations

import argparse
import logging
import sys
import zipfile
from io import BytesIO
from pathlib import Path

from lessonforge.config import get_settings
from lessonforge.export import build_zip
from lessonforge.pipeline import Pipeline, validate_inputs
from lessonforge.storage import ProjectStore

SAMPLES = {
    "http": ("HTTP Requests and Responses",
             "Explain GET and POST methods and distinguish between 2xx, 4xx, and 5xx response status categories."),
    "git": ("Git Branching and Merging",
            "Create and switch between Git branches, merge a feature branch into main, and resolve a simple "
            "merge conflict."),
}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--sample", choices=SAMPLES)
    ap.add_argument("--title")
    ap.add_argument("--objective")
    ap.add_argument("--resume", help="project id to continue")
    ap.add_argument("--out", default="examples", help="folder for the exported files")
    args = ap.parse_args()
    logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

    settings = get_settings()
    store = ProjectStore(settings.data_dir)
    pl = Pipeline(store, settings)

    if args.resume:
        project = store.load(args.resume)
    else:
        title, objective = SAMPLES[args.sample] if args.sample else (args.title, args.objective)
        errors = validate_inputs(title or "", objective or "")
        if errors:
            print("\n".join(errors), file=sys.stderr)
            return 2
        project = store.create(title, objective)
    print(f"Project: {project.id}")

    ok = pl.run_all(project, lambda step, state: print(f"  [{state:^7}] {step}", flush=True))
    for step, stt in project.steps.items():
        if stt.status == "failed":
            print(f"  {step} failed: {stt.error}", file=sys.stderr)

    if project.versions:
        out = Path(args.out) / project.id
        out.mkdir(parents=True, exist_ok=True)
        zipfile.ZipFile(BytesIO(build_zip(project))).extractall(out)
        print(f"Exported to {out}")
        if project.qc1:
            print(f"  QC1 accuracy score: {project.qc1.accuracy_score}/100, {len(project.qc1.issues)} issues")
        if project.qc2:
            print(f"  QC2 instructional score: {project.qc2.overall_score}/100, {len(project.qc2.issues)} issues")
    if not ok:
        print(f"Some steps failed. Retry with: python cli.py --resume {project.id}", file=sys.stderr)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
