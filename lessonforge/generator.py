"""Lesson generation: research bundle -> structured LessonDraft -> Markdown."""
from __future__ import annotations

import re

from . import prompts
from .config import Settings
from .llm import LLMClient, LLMError
from .models import LessonDraft, ResearchBundle
from .timing import fit_minutes

KIND_LABELS = {
    "hook": "Hook", "concept": "Concept", "worked_example": "Worked example",
    "activity": "Activity", "knowledge_check": "Knowledge check", "summary": "Summary",
}
CITE_RE = re.compile(r"\[((?:[SB]\d+)(?:\s*,\s*[SB]\d+)*)\]")


def format_sources(bundle: ResearchBundle) -> str:
    lines = []
    for s in bundle.all_sources():
        reach = "" if s.reachable is not False else " | NOT REACHABLE"
        lines.append(f"{s.id} | {s.title} | {s.publisher} | {s.source_type}{reach} | {s.url}")
    return "\n".join(lines) or "(no sources)"


def format_videos(bundle: ResearchBundle) -> str:
    return "\n".join(f"{v.id} | {v.title} | {v.channel} | {v.duration_text or '?'}"
                     for v in bundle.videos) or "(none found)"


def _clean_citations(text: str, valid: set[str]) -> str:
    """Drop citation ids the model invented (not in the source list)."""
    def repl(m: re.Match) -> str:
        ids = [i.strip() for i in m.group(1).split(",") if i.strip() in valid]
        return f"[{', '.join(ids)}]" if ids else ""
    return CITE_RE.sub(repl, text)


def sanitize_draft(draft: LessonDraft, bundle: ResearchBundle, budget: int) -> list[str]:
    """Fix structural problems in-place; return notes about what was changed."""
    notes: list[str] = []
    valid = set(bundle.source_by_id())
    for sec in draft.sections:
        bad = [i for i in sec.source_ids if i not in valid]
        if bad:
            notes.append(f"Removed unknown source ids {bad} from '{sec.heading}'")
        sec.source_ids = [i for i in sec.source_ids if i in valid]
        cleaned = _clean_citations(sec.content_markdown, valid)
        if cleaned != sec.content_markdown:
            notes.append(f"Removed invented inline citations in '{sec.heading}'")
            sec.content_markdown = cleaned
        sec.minutes = max(1, int(sec.minutes))
        # The model sometimes repeats the heading at the top of the content.
        sec.content_markdown = re.sub(r"^\s*#{1,3}\s*" + re.escape(sec.heading) + r"\s*\n", "",
                                      sec.content_markdown).strip()
    total = sum(s.minutes for s in draft.sections)
    if total > budget:
        new = fit_minutes([s.minutes for s in draft.sections], budget)
        for s, m in zip(draft.sections, new):
            s.minutes = m
        notes.append(f"Section minutes summed to {total}; scaled to {budget}.")
    videos = bundle.video_by_id()
    kept = [v for v in draft.recommended_videos if v.video_ref in videos]
    if len(kept) != len(draft.recommended_videos):
        notes.append("Dropped video picks that were not in the verified candidate list.")
    draft.recommended_videos = kept
    for q in draft.quiz:
        if not (0 <= q.correct_option_index < len(q.options)):
            notes.append(f"Quiz question had an invalid answer index: '{q.question[:60]}'")
            q.correct_option_index = 0
    return notes


def generate_draft(title: str, objective: str, bundle: ResearchBundle, llm: LLMClient,
                   settings: Settings) -> tuple[LessonDraft, list[str]]:
    budget = settings.lesson_minutes
    prompt = prompts.GENERATE_PROMPT.format(
        title=title, objective=objective, minutes=budget, min_minutes=budget - 5,
        notes=bundle.notes, sources=format_sources(bundle), videos=format_videos(bundle))
    draft = llm.structured(prompt, LessonDraft, system=prompts.GENERATE_SYSTEM,
                           model=settings.model, temperature=0.5)
    if not draft.sections:
        raise LLMError("The model returned a lesson with no sections. Press Retry.")
    notes = sanitize_draft(draft, bundle, budget)

    # Self-check: one repair attempt if the draft has truncated or too-thin sections.
    problems = draft_problems(draft, bundle, budget)
    if problems:
        feedback = ("\n\nIMPORTANT: a previous draft had these problems. Avoid them:\n- "
                    + "\n- ".join(problems))
        try:
            retry = llm.structured(prompt + feedback, LessonDraft, system=prompts.GENERATE_SYSTEM,
                                   model=settings.model, temperature=0.5)
            retry_notes = sanitize_draft(retry, bundle, budget) if retry.sections else ["empty"]
            retry_problems = draft_problems(retry, bundle, budget) if retry.sections else problems + ["empty"]
            if len(retry_problems) < len(problems):
                draft, notes, problems = retry, retry_notes, retry_problems
                notes.append("Regenerated once after self-check")
        except LLMError:
            pass  # keep the first draft; QC will report the problems
        if problems:
            notes.append("Self-check problems remaining: " + "; ".join(problems))
    return draft, notes


def is_truncated(text: str) -> bool:
    """Heuristic: unbalanced code fences / inline backticks, or ending mid-sentence."""
    t = text.rstrip()
    if not t:
        return True
    if t.count("```") % 2:
        return True
    last = t.splitlines()[-1].strip()
    if last.count("`") % 2:
        return True
    if last.startswith(("|", "-", "*", ">", "#", "```")) or re.match(r"^\d+[.)]\s", last):
        return False  # lists, tables, headings and fences don't need end punctuation
    return t[-1] not in ".!?:)]*`|>\"'"


def draft_problems(draft: LessonDraft, bundle: ResearchBundle, budget: int) -> list[str]:
    from .timing import analyse_timing  # local import avoids a cycle at module load
    problems = [f"Section '{s.heading}' is cut off mid-sentence; write it completely."
                for s in draft.sections if is_truncated(s.content_markdown)]
    t = analyse_timing(render_markdown(draft, bundle, budget), budget)
    for p in t.per_section:
        if p.get("padded"):
            target = int(p["declared_min"] * 140)
            problems.append(f"Section '{p['section'].split('. ', 1)[-1]}' has only {p['words']} words for "
                            f"{p['declared_min']:g} minutes; expand it to about {target} words with more "
                            "explanation, examples and a short check, or reduce its minutes.")
    return problems


# --------------------------------------------------------------------------- #
# Markdown rendering
# --------------------------------------------------------------------------- #
LETTERS = "ABCDEFGH"


def render_markdown(draft: LessonDraft, bundle: ResearchBundle, budget: int = 45) -> str:
    sources = bundle.source_by_id()
    videos = bundle.video_by_id()
    total = sum(s.minutes for s in draft.sections)
    out: list[str] = [f"# {draft.title}", ""]
    out += [f"**Learning objective:** {draft.learning_objective}  ",
            f"**Duration:** {total} minutes (budget {budget}) · **Format:** self-paced or instructor-led  ",
            f"**Audience:** {draft.target_audience}  "]
    if draft.prerequisites:
        out.append(f"**Prerequisites:** {'; '.join(draft.prerequisites)}")
    out += ["", "## What you will be able to do", ""]
    out += [f"- {c}" for c in draft.success_criteria]
    out += ["", "## Lesson plan", "", "| # | Section | Type | Minutes |", "|---|---|---|---|"]
    for i, s in enumerate(draft.sections, 1):
        out.append(f"| {i} | {s.heading} | {KIND_LABELS.get(s.kind.value, s.kind.value)} | {s.minutes} |")
    out.append(f"| | **Total** | | **{total}** |")

    for i, s in enumerate(draft.sections, 1):
        out += ["", f"## {i}. {s.heading} ({s.minutes} min)", f"<!-- kind: {s.kind.value} -->", "",
                s.content_markdown.strip()]
        if s.kind.value == "knowledge_check" and draft.quiz:
            for qi, q in enumerate(draft.quiz, 1):
                out += ["", f"**Q{qi}.** {q.question}", ""]
                out += [f"- {LETTERS[oi]}) {opt}" for oi, opt in enumerate(q.options)]
        if s.source_ids:
            out += ["", "*Sources: " + ", ".join(f"[{sid}]" for sid in s.source_ids) + "*"]

    out += ["", "## Key takeaways", ""] + [f"- {t}" for t in draft.key_takeaways]

    if draft.quiz:
        out += ["", "## Answer key", ""]
        for qi, q in enumerate(draft.quiz, 1):
            letter = LETTERS[q.correct_option_index]
            out.append(f"{qi}. **{letter}**: {q.explanation}")

    out += ["", f"## Supplementary videos (optional, outside the {budget} minutes)", ""]
    if draft.recommended_videos:
        for pick in draft.recommended_videos:
            v = videos[pick.video_ref]
            dur = f", {v.duration_text}" if v.duration_text else ""
            out.append(f"- **[{v.title}]({v.url})** ({v.channel}{dur}). "
                       f"*When:* {pick.when_to_watch}. *Why:* {pick.why_watch}")
    else:
        out.append("- No verified videos were found for this topic.")

    out += ["", "## References", ""]
    out += render_references(bundle, draft)
    return "\n".join(out).strip() + "\n"


def render_references(bundle: ResearchBundle, draft: LessonDraft | None = None) -> list[str]:
    out: list[str] = []
    if bundle.sources:
        out += ["### Websites", ""]
        for s in bundle.sources:
            flag = " *(was not reachable when checked)*" if s.reachable is False else ""
            out.append(f"- [{s.id}] {s.title}. {s.publisher}. <{s.url}>{flag}")
        out.append("")
    if bundle.books:
        out += ["### Books", ""]
        out += [f"- [{b.id}] *{b.title}*. {b.publisher}. <{b.url}>" for b in bundle.books]
        out.append("")
    picked = {p.video_ref for p in draft.recommended_videos} if draft else set()
    vids = [v for v in bundle.videos if not picked or v.id in picked]
    if vids:
        out += ["### Videos", ""]
        out += [f"- [{v.id}] {v.title}. {v.channel}, YouTube. <{v.url}>" for v in vids]
    return out
