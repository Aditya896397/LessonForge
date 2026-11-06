"""The two independent Quality Control layers.

QC1 - Research & factual accuracy (evidence-based)
    1. Extract the key checkable claims from the lesson (structured call).
    2. Verify each claim with a *fresh* Google-Search-grounded call that never saw
       the original research, so it cannot simply agree with itself.
    3. Audit sources (reliability / relevance, plus automatic reachability and
       source-type checks) and look for uncited claims, gaps and inconsistencies.
    The accuracy score is computed from verdicts, not asked from the model.

QC2 - Instructional quality
    Deterministic checks (time budget, required section types, quiz size,
    citations, references) + a rubric review by a separate "senior instructional
    designer" prompt that sees only the lesson and objective (no research, no QC1
    output), so the two layers stay independent.

Both layers return issues with location, quote, problem and suggestion. The
instructor picks which to apply (see ``revise.py``).
"""
from __future__ import annotations

import re
from concurrent.futures import ThreadPoolExecutor

from . import prompts
from .config import Settings
from .generator import CITE_RE, format_sources
from .llm import LLMClient, parse_model
from .models import (ClaimCheck, ExtractedClaims, FactCheckLLM, InstructionalReviewLLM, QC1Report,
                     QC2Report, QCIssue, ResearchBundle, SourceAssessment, SourceReviewLLM, VerifyPlan)
from .llm import LLMError
from .research import grounding_failed, resolve_redirect, use_grounding
from .timing import analyse_timing, parse_sections

VERDICT_WEIGHT = {"supported": 1.0, "partially_supported": 0.6, "unsupported": 0.5,
                  "misleading": 0.25, "incorrect": 0.0}
VERDICT_SEVERITY = {"incorrect": "critical", "misleading": "major", "unsupported": "major",
                    "partially_supported": "minor"}


def accuracy_score(claims: list[ClaimCheck]) -> int:
    if not claims:
        return 0
    return round(100 * sum(VERDICT_WEIGHT.get(c.verdict, 0.5) for c in claims) / len(claims))


def cited_ids(markdown: str) -> set[str]:
    ids: set[str] = set()
    for m in CITE_RE.finditer(markdown):
        ids.update(i.strip() for i in m.group(1).split(","))
    return ids


def _lesson_body(markdown: str) -> str:
    """Lesson text without the reference list (keeps prompts focused)."""
    return re.split(r"^## References\s*$", markdown, flags=re.MULTILINE)[0]


# --------------------------------------------------------------------------- #
# QC1
# --------------------------------------------------------------------------- #
def _resolved_sources(ver, timeout: float) -> list[dict]:
    with ThreadPoolExecutor(max_workers=8) as ex:
        urls = list(ex.map(lambda s: resolve_redirect(s["uri"], timeout), ver.sources))
    return [{"title": s.get("title", ""), "url": u} for s, u in zip(ver.sources, urls)]


def _dedupe_evidence(resolved: list[dict]) -> list[dict]:
    out, seen = [], set()
    for e in resolved:
        if e["url"] not in seen:
            seen.add(e["url"])
            out.append(e)
    return out


def attach_evidence(fc: FactCheckLLM, ver, resolved: list[dict]) -> list[ClaimCheck]:
    """Link each verdict to the web pages that grounded it.

    Grounding supports point at text segments of the verifier's response. Each
    claim occupies a span of that response (from where its text appears to where
    the next claim starts); supports whose segment falls inside the span belong
    to that claim.
    """
    text = ver.text
    starts = []
    for c in fc.claims:
        pos = text.find(c.claim[:60])
        starts.append(pos if pos >= 0 else None)
    out = []
    for idx, c in enumerate(fc.claims):
        urls: list[str] = []
        start = starts[idx]
        if start is not None:
            later = [p for p in starts[idx + 1:] if p is not None and p > start]
            end = min(later) if later else len(text)
            for sup in ver.supports:
                seg = sup.get("text", "")
                pos = text.find(seg) if seg else -1
                if start <= pos < end:
                    urls += [resolved[i]["url"] for i in sup["source_indices"] if i < len(resolved)]
        out.append(ClaimCheck(**c.model_dump(), evidence_urls=list(dict.fromkeys(urls))[:4]))
    return out


def _verify_grounded(claims_txt: str, llm: LLMClient, settings: Settings):
    retries = 0 if settings.search_backend == "auto" else None
    ver = llm.grounded(prompts.QC1_VERIFY_PROMPT.format(claims=claims_txt),
                       system=prompts.QC1_VERIFY_SYSTEM, model=settings.qc_model, temperature=0.0,
                       retries=retries)
    try:
        fc = parse_model(ver.text, FactCheckLLM)
    except Exception:  # noqa: BLE001 - fall back to a structuring call (no tools)
        fc = llm.structured("Convert this fact-check report into the JSON schema. Keep every "
                            "claim and verdict exactly as written.\n\n" + ver.text,
                            FactCheckLLM, system="You convert text to JSON faithfully.",
                            model=settings.qc_model, temperature=0.0)
    resolved = _resolved_sources(ver, settings.http_timeout) if ver.sources else []
    return attach_evidence(fc, ver, resolved), _dedupe_evidence(resolved), ver.queries


def _verify_by_retrieval(claim_list, claims_txt: str, llm: LLMClient, settings: Settings, title: str = ""):
    """Fresh, independent evidence: a separate call (seeing only the claims) decides where
    to look; pages are fetched; the verdicts must cite evidence excerpt ids [E#]."""
    from .websearch import discover, evidence_for_claims, read_best

    plan = llm.structured(prompts.QC1_VERIFY_PLAN_PROMPT.format(claims=claims_txt), VerifyPlan,
                          system=prompts.QC1_VERIFY_PLAN_SYSTEM, model=settings.qc_model, temperature=0.0)
    topic = " ".join(c.claim for c in claim_list)
    cands, _notes = discover(plan.search_queries, [p.model_dump() for p in plan.proposed_sources],
                             settings.http_timeout, settings.tavily_api_key)
    pages = read_best(cands, topic, settings.http_timeout, max_pages=10, max_chars=2500, core=title)
    if not pages:
        raise LLMError("QC1 could not retrieve any evidence pages. Press Retry.")
    items = evidence_for_claims(pages, [c.claim for c in claim_list])
    if not items:  # nothing matched claim-by-claim: fall back to page excerpts
        items = [{"id": f"E{i + 1}", "url": p["url"], "title": p["title"], "text": p["excerpt"], "claims": []}
                 for i, p in enumerate(pages)]
    ev_txt = "\n\n".join(
        f"[{it['id']}] {it['title']} ({it['url']})"
        + (f" (retrieved for claims {', '.join(map(str, it['claims']))})" if it["claims"] else "")
        + f"\n{it['text']}" for it in items)
    fc = llm.structured(prompts.QC1_VERIFY_EVIDENCE_PROMPT.format(evidence=ev_txt, claims=claims_txt),
                        FactCheckLLM, system=prompts.QC1_VERIFY_SYSTEM, model=settings.qc_model,
                        temperature=0.0)
    by_id = {it["id"]: it["url"] for it in items}
    claims = []
    for c in fc.claims:
        ids = re.findall(r"\[(E\d+)\]", c.evidence)
        urls = [by_id[i] for i in dict.fromkeys(ids) if i in by_id]
        claims.append(ClaimCheck(**c.model_dump(), evidence_urls=list(dict.fromkeys(urls))[:4]))
    evidence = [{"title": p["title"], "url": p["url"]} for p in pages]
    return claims, evidence, plan.search_queries


def run_qc1(markdown: str, title: str, objective: str, bundle: ResearchBundle, llm: LLMClient,
            settings: Settings, version: int = 0, n_claims: int = 12) -> QC1Report:
    body = _lesson_body(markdown)

    # 1. claims
    extracted = llm.structured(prompts.QC1_EXTRACT_PROMPT.format(n=n_claims, lesson=body),
                               ExtractedClaims, system=prompts.QC1_EXTRACT_SYSTEM,
                               model=settings.qc_model, temperature=0.0)
    claim_list = extracted.claims[:n_claims + 3]
    claims_txt = "\n".join(f"{i + 1}. [{c.location}] {c.claim}" for i, c in enumerate(claim_list))

    # 2. independent verification: Google Search grounding, or direct web retrieval
    claims = evidence = queries = None
    method = "gemini-grounding"
    if use_grounding(settings):
        try:
            claims, evidence, queries = _verify_grounded(claims_txt, llm, settings)
        except LLMError as exc:
            if not grounding_failed(settings, exc):
                raise
    if claims is None:
        method = "web-retrieval"
        claims, evidence, queries = _verify_by_retrieval(claim_list, claims_txt, llm, settings, title)

    # 3. source audit + gaps/inconsistencies
    used = cited_ids(body)
    src_lines = []
    for s in bundle.all_sources():
        src_lines.append(f"{s.id} | {s.title} | {s.url} | type: {s.source_type} | "
                         f"reachable: {s.reachable} | cited in lesson: {s.id in used}")
    fc_txt = "\n".join(f"- [{c.verdict}] {c.claim} :: {c.explanation}" for c in claims)
    review = llm.structured(prompts.QC1_REVIEW_PROMPT.format(
        title=title, objective=objective, sources="\n".join(src_lines) or "(none)",
        factcheck=fc_txt, lesson=body), SourceReviewLLM, system=prompts.QC1_REVIEW_SYSTEM,
        model=settings.qc_model, temperature=0.1)

    by_id = bundle.source_by_id()
    assessments = []
    rated = {a.source_id: a for a in review.sources}
    for sid, s in by_id.items():
        a = rated.get(sid)
        assessments.append(SourceAssessment(
            source_id=sid, title=s.title, url=s.url, kind=s.kind,
            reliability=a.reliability if a else s.trust_hint,
            relevance=a.relevance if a else "unknown", reachable=s.reachable,
            cited_in_lesson=sid in used, note=a.note if a else "Not rated by the reviewer."))

    issues: list[QCIssue] = []
    for c in claims:
        if c.verdict in VERDICT_SEVERITY:
            issues.append(QCIssue(
                id=f"QC1-{len(issues) + 1}", layer="QC1", severity=VERDICT_SEVERITY[c.verdict],
                category=f"claim {c.verdict.replace('_', ' ')}", location=c.location, quote=c.claim,
                problem=c.explanation,
                suggestion=c.correction or "Add an authoritative citation or remove the claim."))
    for s in bundle.all_sources():
        if s.reachable is False and s.id in used:
            issues.append(QCIssue(
                id=f"QC1-{len(issues) + 1}", layer="QC1", severity="minor", category="source unreachable",
                location="References", quote=s.url, problem=f"{s.id} could not be loaded when checked.",
                suggestion=f"Replace {s.id} with a reachable authoritative source or remove the citation."))
    for i in review.issues:
        issues.append(QCIssue(id=f"QC1-{len(issues) + 1}", layer="QC1", **i.model_dump()))

    return QC1Report(summary=review.summary, accuracy_score=accuracy_score(claims), claims=claims,
                     sources=assessments, issues=issues, verification_queries=queries, verification_method=method,
                     verification_sources=evidence, lesson_version=version, model=settings.qc_model)


# --------------------------------------------------------------------------- #
# QC2
# --------------------------------------------------------------------------- #
def _section_text(body: str) -> str:
    """Section body without the kind comment, the trailing '*Sources: ...*' line and quiz options."""
    body = re.sub(r"<!--.*?-->", "", body).strip()
    body = re.sub(r"\n\*Sources:[^\n]*\*\s*$", "", body).strip()
    return body


def structure_checks(markdown: str, bundle: ResearchBundle | None, budget: int) -> list[dict]:
    sections = parse_sections(markdown)
    kinds = [s["kind"] for s in sections]
    n_quiz = len(re.findall(r"^\*\*Q\d+\.\*\*", markdown, re.MULTILINE))
    timing = analyse_timing(markdown, budget)
    uncited = [s["heading"] for s in sections
               if s["kind"] in ("concept", "worked_example") and not CITE_RE.search(s["body"])]
    has_refs = bool(re.search(r"^## References", markdown, re.MULTILINE))
    from .generator import is_truncated
    truncated = [s["heading"] for s in sections
                 if is_truncated(_section_text(s["body"]))]
    has_videos = bool(re.search(r"youtube\.com/watch", markdown))
    checks = [
        ("Opens with a hook", "hook" in kinds, ""),
        ("Has concept explanation sections", kinds.count("concept") >= 1, f"{kinds.count('concept')} found"),
        ("Has a worked example", "worked_example" in kinds, ""),
        ("Has a hands-on activity", "activity" in kinds, ""),
        ("Has a knowledge check with >= 4 questions", "knowledge_check" in kinds and n_quiz >= 4,
         f"{n_quiz} questions"),
        ("Ends with a summary", bool(kinds) and kinds[-1] == "summary", ""),
        ("Fits the time budget", timing.within_budget, timing.note),
        ("No truncated sections", not truncated, ("Cut off: " + "; ".join(truncated)) if truncated else ""),
        ("Section times match their content", not any(p["padded"] for p in timing.per_section),
         "; ".join(f"{p['section']}: {p['declared_min']:g} min for ~{p['reading_min']} min of text"
                   for p in timing.per_section if p["padded"])),
        ("Concept/example sections cite sources", not uncited,
         ("Uncited: " + "; ".join(uncited)) if uncited else ""),
        ("Includes supplementary YouTube videos", has_videos, ""),
        ("Includes a reference list", has_refs, ""),
    ]
    return [{"check": c, "passed": bool(p), "detail": d} for c, p, d in checks]


def run_qc2(markdown: str, title: str, objective: str, llm: LLMClient, settings: Settings,
            bundle: ResearchBundle | None = None, version: int = 0) -> QC2Report:
    budget = settings.lesson_minutes
    body = _lesson_body(markdown)
    timing = analyse_timing(markdown, budget)
    checks = structure_checks(markdown, bundle, budget)
    auto = "\n".join(f"- [{'PASS' if c['passed'] else 'FAIL'}] {c['check']} {c['detail']}" for c in checks)
    auto += "\n- Per-section timing: " + "; ".join(
        f"{p['section']}: declared {p['declared_min']:g} min, ~{p['reading_min']} min of reading"
        + (" (TOO LONG)" if p["over"] else "") + (" (THIN / PADDED)" if p["padded"] else "")
        for p in timing.per_section)

    review = llm.structured(prompts.QC2_PROMPT.format(title=title, objective=objective, minutes=budget,
                                                      auto_checks=auto, lesson=body),
                            InstructionalReviewLLM, system=prompts.QC2_SYSTEM,
                            model=settings.model, temperature=0.1)

    issues: list[QCIssue] = []
    for c in checks:
        if not c["passed"]:
            issues.append(QCIssue(id=f"QC2-{len(issues) + 1}", layer="QC2",
                                  severity="major" if "time" in c["check"].lower() or "knowledge" in c["check"].lower() else "minor",
                                  category="structure check", location="Whole lesson",
                                  problem=f"Automatic check failed: {c['check']}. {c['detail']}".strip(),
                                  suggestion=_fix_for_check(c["check"], timing)))
    for i in review.issues:
        issues.append(QCIssue(id=f"QC2-{len(issues) + 1}", layer="QC2", **i.model_dump()))

    # Score: 70% rubric, 20% objective coverage, 10% automatic checks.
    rub = [max(1, min(5, r.score)) for r in review.rubric] or [3]
    rubric_pct = (sum(rub) / len(rub) - 1) / 4
    cov_map = {"full": 1.0, "partial": 0.5, "missing": 0.0}
    cov = [cov_map[o.coverage] for o in review.objective_components] or [0.5]
    checks_pct = sum(c["passed"] for c in checks) / len(checks)
    score = round(100 * (0.7 * rubric_pct + 0.2 * sum(cov) / len(cov) + 0.1 * checks_pct))

    return QC2Report(summary=review.summary, overall_score=score,
                     objective_coverage=review.objective_components, rubric=review.rubric,
                     timing=timing, structure_checks=checks, issues=issues,
                     lesson_version=version, model=settings.model)


def _fix_for_check(check: str, timing) -> str:
    if "time" in check.lower():
        over = [p["section"] for p in timing.per_section if p["over"]]
        return ("Shorten the text of: " + ", ".join(over)) if over else \
            "Adjust section minutes so they add up to the budget."
    return f"Add or fix the lesson so that it satisfies: {check}."


def run_both(markdown: str, title: str, objective: str, bundle: ResearchBundle, llm: LLMClient,
             settings: Settings, version: int = 0):
    """Run QC1 and QC2 in parallel. Returns (qc1_result_or_exc, qc2_result_or_exc)."""
    with ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(run_qc1, markdown, title, objective, bundle, llm, settings, version)
        f2 = ex.submit(run_qc2, markdown, title, objective, llm, settings, bundle, version)
        out = []
        for f in (f1, f2):
            try:
                out.append(f.result())
            except Exception as exc:  # noqa: BLE001
                out.append(exc)
    return tuple(out)


__all__ = ["run_qc1", "run_qc2", "run_both", "structure_checks", "accuracy_score", "format_sources"]
