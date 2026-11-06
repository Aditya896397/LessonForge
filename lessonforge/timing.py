"""Deterministic time-budget analysis of a lesson's Markdown.

Works on the Markdown (not the original draft) so it stays correct after
instructor edits. Each timed section looks like:

    ## 2. GET vs POST (8 min)
    <!-- kind: concept -->
"""
from __future__ import annotations

import re

from .models import TimingCheck

READING_WPM = 170  # comfortable reading speed for technical material
HEADING_RE = re.compile(r"^##\s+(?P<title>.+?)\s*\((?P<min>\d+(?:\.\d+)?)\s*min(?:utes)?\)\s*$",
                        re.IGNORECASE | re.MULTILINE)
KIND_RE = re.compile(r"<!--\s*kind:\s*(\w+)\s*-->")
DOING_KINDS = {"activity", "knowledge_check"}  # time is spent doing, not reading


def _words(text: str) -> int:
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    return len(re.findall(r"[A-Za-z0-9_]+", text))


def parse_sections(markdown: str) -> list[dict]:
    matches = list(HEADING_RE.finditer(markdown))
    sections = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        body = markdown[start:end]
        nxt = re.search(r"^##\s", body, re.MULTILINE)  # untimed ## section ends the body
        if nxt:
            body = body[:nxt.start()]
        kind_m = KIND_RE.search(body)
        sections.append({
            "heading": m.group("title").strip(),
            "kind": kind_m.group(1) if kind_m else "unknown",
            "minutes": float(m.group("min")),
            "words": _words(body),
            "body": body,
        })
    return sections


def analyse_timing(markdown: str, budget: int = 45) -> TimingCheck:
    sections = parse_sections(markdown)
    per_section = []
    declared = 0.0
    reading_total = 0.0
    est_total = 0.0
    for s in sections:
        reading = s["words"] / READING_WPM
        # For reading sections the realistic time is max(declared, reading time).
        # For doing sections the declared time already includes reading the task.
        est = s["minutes"] if s["kind"] in DOING_KINDS else max(s["minutes"], reading)
        declared += s["minutes"]
        reading_total += reading
        est_total += est
        per_section.append({"section": s["heading"], "kind": s["kind"], "declared_min": s["minutes"],
                            "words": s["words"], "reading_min": round(reading, 1),
                            "estimated_min": round(est, 1),
                            "over": s["kind"] not in DOING_KINDS and reading > s["minutes"] * 1.25,
                            # a reading section with far fewer words than its minutes suggest
                            "padded": s["kind"] not in DOING_KINDS and s["minutes"] >= 4
                            and reading < s["minutes"] * 0.3})
    within = bool(sections) and declared <= budget and est_total <= budget * 1.1
    if not sections:
        note = "No timed sections found (headings must end with '(N min)')."
    elif declared > budget:
        note = f"Declared section times add up to {declared:g} min, over the {budget}-min budget."
    elif est_total > budget * 1.1:
        note = (f"Text is longer than the declared times allow: estimated {est_total:.0f} min "
                f"against a {budget}-min budget. Trim the sections marked as over.")
    elif sum(p["padded"] for p in per_section) >= 2:
        padded = [p["section"] for p in per_section if p["padded"]]
        note = (f"Fits the {budget}-min budget on paper, but these sections have far less text than "
                f"their minutes suggest (thin content or padded timing): {'; '.join(padded)}.")
    elif declared < budget * 0.8:
        note = f"Only {declared:g} of {budget} minutes are used; there is room for more practice."
    else:
        note = f"Fits the budget: {declared:g} min declared, about {est_total:.0f} min estimated."
    return TimingCheck(budget_minutes=budget, declared_minutes=int(round(declared)),
                       estimated_reading_minutes=round(reading_total, 1),
                       estimated_total_minutes=round(est_total, 1), within_budget=within,
                       per_section=per_section, note=note)


def fit_minutes(minutes: list[int], budget: int) -> list[int]:
    """Scale section minutes down proportionally so they sum to `budget` (largest remainder)."""
    total = sum(minutes)
    if total <= budget or total == 0:
        return minutes
    raw = [m * budget / total for m in minutes]
    floored = [max(1, int(r)) for r in raw]
    remainder = budget - sum(floored)
    order = sorted(range(len(raw)), key=lambda i: raw[i] - int(raw[i]), reverse=True)
    for i in order:
        if remainder <= 0:
            break
        floored[i] += 1
        remainder -= 1
    # if the max(1, ...) floor pushed us over, take from the largest sections
    while sum(floored) > budget:
        floored[floored.index(max(floored))] -= 1
    return floored
