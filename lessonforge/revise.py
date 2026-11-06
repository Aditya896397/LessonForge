"""Apply selected QC recommendations (or a free-text instructor request) to a lesson."""
from __future__ import annotations

import difflib

from . import prompts
from .config import Settings
from .generator import format_sources
from .llm import LLMClient, LLMError
from .models import QCIssue, ResearchBundle, RevisionLLM
from .timing import parse_sections


def describe_issue(i: QCIssue) -> str:
    parts = [f"[{i.id}] ({i.severity}, {i.category}) in section \"{i.location or 'whole lesson'}\""]
    if i.quote:
        parts.append(f"  Text: \"{i.quote}\"")
    parts.append(f"  Problem: {i.problem}")
    parts.append(f"  Change to make: {i.suggestion}")
    return "\n".join(parts)


def revise_lesson(markdown: str, issues: list[QCIssue], instruction: str, bundle: ResearchBundle | None,
                  llm: LLMClient, settings: Settings) -> RevisionLLM:
    changes = [describe_issue(i) for i in issues]
    if instruction.strip():
        changes.append(f"[Instructor request] {instruction.strip()}")
    if not changes:
        raise ValueError("Select at least one recommendation or type an instruction.")
    result = llm.structured(
        prompts.REVISE_PROMPT.format(changes="\n\n".join(changes), minutes=settings.lesson_minutes,
                                     sources=format_sources(bundle) if bundle else "(none)",
                                     lesson=markdown),
        RevisionLLM, system=prompts.REVISE_SYSTEM, model=settings.model, temperature=0.2)
    # Guard against truncated / structure-breaking rewrites.
    revised = result.revised_markdown.strip() + "\n"
    if len(revised) < 0.6 * len(markdown):
        raise LLMError("The revision came back much shorter than the lesson (likely truncated). "
                       "Try applying fewer recommendations at once.")
    if len(parse_sections(revised)) < len(parse_sections(markdown)) - 1:
        raise LLMError("The revision lost lesson sections. Try applying fewer recommendations at once.")
    result.revised_markdown = revised
    return result


def unified_diff(old: str, new: str) -> str:
    return "".join(difflib.unified_diff(old.splitlines(keepends=True), new.splitlines(keepends=True),
                                        fromfile="current", tofile="revised", n=2))
