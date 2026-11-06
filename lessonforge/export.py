"""Export: lesson (Markdown / standalone HTML), references, QC reports, ZIP bundle."""
from __future__ import annotations

import io
import json
import re
import zipfile

import markdown as md_lib

from .generator import render_references
from .models import LessonProject, QC1Report, QC2Report, QCIssue

CSS = """
body{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:860px;margin:2rem auto;
padding:0 1rem;line-height:1.6;color:#1f2328}
h1{border-bottom:2px solid #e5484d;padding-bottom:.3rem}h2{margin-top:2rem;border-bottom:1px solid #ddd}
code{background:#f3f3f3;padding:.1rem .3rem;border-radius:4px}
pre{background:#f6f8fa;padding:1rem;overflow:auto;border-radius:6px}pre code{background:none;padding:0}
table{border-collapse:collapse;margin:1rem 0}td,th{border:1px solid #ccc;padding:.35rem .6rem;text-align:left}
th{background:#f6f8fa}blockquote{border-left:4px solid #ddd;margin:0;padding-left:1rem;color:#555}
@media print{body{margin:0}a{color:inherit}}
"""


def _esc(s: str) -> str:
    return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def to_html(markdown_text: str, title: str) -> str:
    body = md_lib.markdown(markdown_text, extensions=["tables", "fenced_code", "sane_lists"])
    return (f"<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>{_esc(title)}</title>"
            f"<meta name='viewport' content='width=device-width,initial-scale=1'><style>{CSS}</style>"
            f"</head><body>{body}</body></html>")


def _cell(s) -> str:
    return re.sub(r"\s+", " ", str(s or "")).replace("|", "\\|")


def issues_markdown(issues: list[QCIssue], applied: set[str] | None = None) -> list[str]:
    applied = applied or set()
    out = ["## Issues and suggested improvements", ""]
    if not issues:
        return out + ["No issues found."]
    order = {"critical": 0, "major": 1, "minor": 2}
    for i in sorted(issues, key=lambda x: order.get(x.severity, 3)):
        status = " · APPLIED" if i.id in applied else ""
        out += [f"### {i.id} · {i.severity.upper()} · {i.category}{status}",
                f"- **Where:** {i.location or 'n/a'}"]
        if i.quote:
            out.append(f"- **Text:** \"{i.quote}\"")
        out += [f"- **Problem:** {i.problem}", f"- **Suggestion:** {i.suggestion}", ""]
    return out


def qc1_markdown(r: QC1Report, title: str, applied: set[str] | None = None) -> str:
    out = ["# QC Layer 1: Research & Factual Accuracy Audit", "",
           f"**Lesson:** {title}  ", f"**Lesson version audited:** v{r.lesson_version}  ",
           f"**Model:** {r.model}  ", f"**Date:** {r.created_at}  ",
           f"**Verification method:** {r.verification_method}  ",
           f"**Accuracy score:** {r.accuracy_score}/100 (computed from claim verdicts)", "",
           "## Summary", "", r.summary, ""]
    counts: dict[str, int] = {}
    for c in r.claims:
        counts[c.verdict] = counts.get(c.verdict, 0) + 1
    out += ["## Claim verification", "",
            "Verdict counts: " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())), "",
            "| # | Claim | Section | Verdict | Explanation | Correction | Evidence |",
            "|---|---|---|---|---|---|---|"]
    for i, c in enumerate(r.claims, 1):
        ev = _cell(c.evidence) + "".join(f" <{u}>" for u in c.evidence_urls)
        out.append(f"| {i} | {_cell(c.claim)} | {_cell(c.location)} | **{c.verdict}** | "
                   f"{_cell(c.explanation)} | {_cell(c.correction)} | {ev} |")
    out += ["", "## Source reliability and relevance", "",
            "| Id | Source | Reliability | Relevance | Reachable | Cited | Note |",
            "|---|---|---|---|---|---|---|"]
    for s in r.sources:
        reach = "yes" if s.reachable else ("no" if s.reachable is False else "?")
        out.append(f"| {s.source_id} | [{_cell(s.title)}]({s.url}) | {s.reliability} | {s.relevance} | "
                   f"{reach} | {'yes' if s.cited_in_lesson else 'no'} | {_cell(s.note)} |")
    out += ["", *issues_markdown(r.issues, applied)]
    if r.verification_queries:
        out += ["", "## Verification searches run", ""] + [f"- {q}" for q in r.verification_queries]
    if r.verification_sources:
        out += ["", "## Pages consulted during verification", ""]
        out += [f"- {e['title']}: <{e['url']}>" for e in r.verification_sources]
    return "\n".join(out) + "\n"


def qc2_markdown(r: QC2Report, title: str, applied: set[str] | None = None) -> str:
    out = ["# QC Layer 2: Instructional Quality Audit", "",
           f"**Lesson:** {title}  ", f"**Lesson version audited:** v{r.lesson_version}  ",
           f"**Model:** {r.model}  ", f"**Date:** {r.created_at}  ",
           f"**Overall score:** {r.overall_score}/100 (70% rubric, 20% objective coverage, 10% automatic checks)",
           "", "## Summary", "", r.summary, "", "## Learning objective alignment", "",
           "| Objective component | Coverage | Evidence | Gap |", "|---|---|---|---|"]
    for o in r.objective_coverage:
        out.append(f"| {_cell(o.component)} | **{o.coverage}** | {_cell(o.evidence)} | {_cell(o.gap)} |")
    out += ["", "## Rubric", "", "| Criterion | Score (1-5) | Rationale |", "|---|---|---|"]
    out += [f"| {_cell(x.criterion)} | {x.score} | {_cell(x.rationale)} |" for x in r.rubric]
    if r.timing:
        t = r.timing
        out += ["", f"## Time budget ({t.budget_minutes}-minute check)", "", t.note, "",
                f"Declared: {t.declared_minutes} min · Estimated reading: {t.estimated_reading_minutes} min · "
                f"Estimated total: {t.estimated_total_minutes} min · "
                f"Within budget: {'yes' if t.within_budget else 'no'}", "",
                "| Section | Type | Declared | Words | Reading time | Flag |", "|---|---|---|---|---|---|"]
        out += [f"| {_cell(p['section'])} | {p['kind']} | {p['declared_min']:g} | {p['words']} | "
                f"{p['reading_min']} | {'too long' if p['over'] else ('thin/padded' if p.get('padded') else '')} |"
                for p in t.per_section]
    out += ["", "## Automatic structure checks", ""]
    out += [f"- {'PASS' if c['passed'] else 'FAIL'}: {c['check']}" + (f" ({c['detail']})" if c["detail"] else "")
            for c in r.structure_checks]
    out += ["", *issues_markdown(r.issues, applied)]
    return "\n".join(out) + "\n"


def references_markdown(p: LessonProject) -> str:
    if not p.research:
        return "# References\n\n(no research yet)\n"
    return "\n".join([f"# References: {p.title}", "", *render_references(p.research, p.draft)]) + "\n"


def build_zip(p: LessonProject) -> bytes:
    applied = set(p.applied_issue_ids)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        lesson = p.current_markdown
        z.writestr("lesson.md", lesson)
        z.writestr("lesson.html", to_html(lesson, p.title))
        z.writestr("references.md", references_markdown(p))
        if p.research:
            z.writestr("research_brief.md", f"# Research brief: {p.title}\n\n{p.research.notes}\n")
        if p.qc1:
            z.writestr("qc1_research_accuracy_report.md", qc1_markdown(p.qc1, p.title, applied))
        if p.qc2:
            z.writestr("qc2_instructional_quality_report.md", qc2_markdown(p.qc2, p.title, applied))
        z.writestr("qc_reports.json", json.dumps({
            "qc1": p.qc1.model_dump() if p.qc1 else None,
            "qc2": p.qc2.model_dump() if p.qc2 else None,
            "applied_issue_ids": p.applied_issue_ids}, indent=2))
        z.writestr("project.json", p.model_dump_json(indent=2))
    return buf.getvalue()
