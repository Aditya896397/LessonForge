"""Data models.

Two families of models live here:

* ``*LLM`` / draft models are sent to Gemini as ``response_schema``. They have
  no default values because Gemini's schema dialect does not support them.
* Everything else is application state (persisted as JSON) and may use defaults.
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal, Optional

from pydantic import BaseModel, Field


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# --------------------------------------------------------------------------- #
# Research
# --------------------------------------------------------------------------- #
class Source(BaseModel):
    id: str  # "S1", "B1" ... stable id the lesson cites
    kind: Literal["web", "book"] = "web"
    title: str
    url: str
    publisher: str = ""  # domain for web pages, authors/publisher for books
    snippet: str = ""
    reachable: Optional[bool] = None
    http_status: Optional[int] = None
    source_type: str = "unknown"  # heuristic class: spec / official docs / education / ...
    trust_hint: Literal["high", "medium", "low", "unknown"] = "unknown"


class Video(BaseModel):
    id: str  # "V1" ...
    video_id: str
    title: str
    url: str
    channel: str = ""
    duration_text: str = ""
    duration_seconds: Optional[int] = None
    views_text: str = ""
    verified: bool = False  # confirmed to exist via YouTube oEmbed / Data API


class ResearchBundle(BaseModel):
    notes: str  # markdown research brief with [S#] citations
    search_queries: list[str] = Field(default_factory=list)
    method: str = "gemini-grounding"  # or "web-retrieval"
    sources: list[Source] = Field(default_factory=list)
    books: list[Source] = Field(default_factory=list)
    videos: list[Video] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    created_at: str = Field(default_factory=now_iso)

    def all_sources(self) -> list[Source]:
        return [*self.sources, *self.books]

    def source_by_id(self) -> dict[str, Source]:
        return {s.id: s for s in self.all_sources()}

    def video_by_id(self) -> dict[str, Video]:
        return {v.id: v for v in self.videos}


class ProposedSource(BaseModel):
    url: str
    title: str
    why: str


class SourcePlan(BaseModel):
    """Used when search grounding is unavailable: the model proposes search queries
    and specific authoritative pages; every page is fetched and verified before use."""
    search_queries: list[str]
    proposed_sources: list[ProposedSource]


# --------------------------------------------------------------------------- #
# Lesson draft (Gemini structured output)
# --------------------------------------------------------------------------- #
class SectionKind(str, Enum):
    hook = "hook"
    concept = "concept"
    worked_example = "worked_example"
    activity = "activity"
    knowledge_check = "knowledge_check"
    summary = "summary"


class LessonSection(BaseModel):
    heading: str
    kind: SectionKind
    minutes: int
    content_markdown: str
    source_ids: list[str]


class QuizQuestion(BaseModel):
    question: str
    options: list[str]
    correct_option_index: int
    explanation: str


class VideoPick(BaseModel):
    video_ref: str  # "V#" id from the research bundle
    why_watch: str
    when_to_watch: str


class LessonDraft(BaseModel):
    title: str
    learning_objective: str
    target_audience: str
    prerequisites: list[str]
    success_criteria: list[str]  # measurable "By the end you can..." statements
    sections: list[LessonSection]
    quiz: list[QuizQuestion]
    key_takeaways: list[str]
    recommended_videos: list[VideoPick]


# --------------------------------------------------------------------------- #
# QC Layer 1 - research & factual accuracy
# --------------------------------------------------------------------------- #
Severity = Literal["critical", "major", "minor"]
Rating = Literal["high", "medium", "low"]


class ExtractedClaim(BaseModel):
    claim: str
    location: str  # section heading


class ExtractedClaims(BaseModel):
    claims: list[ExtractedClaim]


class ClaimCheckLLM(BaseModel):
    claim: str
    location: str
    verdict: Literal["supported", "partially_supported", "unsupported", "incorrect", "misleading"]
    explanation: str
    correction: str  # empty string when no correction is needed
    evidence: str  # short description of what the evidence says


class SourceAssessmentLLM(BaseModel):
    source_id: str
    reliability: Rating
    relevance: Rating
    note: str


class QCIssueLLM(BaseModel):
    severity: Severity
    category: str
    location: str
    quote: str
    problem: str
    suggestion: str


class FactCheckLLM(BaseModel):
    claims: list[ClaimCheckLLM]


class VerifyPlan(BaseModel):
    search_queries: list[str]
    proposed_sources: list[ProposedSource]


class SourceReviewLLM(BaseModel):
    sources: list[SourceAssessmentLLM]
    issues: list[QCIssueLLM]  # gaps / inconsistencies / unsupported content
    summary: str


class QCIssue(BaseModel):
    id: str
    layer: Literal["QC1", "QC2"]
    severity: Severity
    category: str
    location: str = ""
    quote: str = ""
    problem: str
    suggestion: str


class ClaimCheck(BaseModel):
    claim: str
    location: str = ""
    verdict: str
    explanation: str = ""
    correction: str = ""
    evidence: str = ""
    evidence_urls: list[str] = Field(default_factory=list)


class SourceAssessment(BaseModel):
    source_id: str
    title: str = ""
    url: str = ""
    kind: str = "web"
    reliability: str = "unknown"
    relevance: str = "unknown"
    reachable: Optional[bool] = None
    cited_in_lesson: bool = False
    note: str = ""


class QC1Report(BaseModel):
    summary: str
    accuracy_score: int  # 0-100, computed from claim verdicts
    claims: list[ClaimCheck] = Field(default_factory=list)
    sources: list[SourceAssessment] = Field(default_factory=list)
    issues: list[QCIssue] = Field(default_factory=list)
    verification_queries: list[str] = Field(default_factory=list)
    verification_sources: list[dict] = Field(default_factory=list)  # [{title, url}]
    verification_method: str = "gemini-grounding"
    lesson_version: int = 0
    model: str = ""
    created_at: str = Field(default_factory=now_iso)


# --------------------------------------------------------------------------- #
# QC Layer 2 - instructional quality
# --------------------------------------------------------------------------- #
class RubricScoreLLM(BaseModel):
    criterion: str
    score: int  # 1-5
    rationale: str


class ObjectiveCoverageLLM(BaseModel):
    component: str
    coverage: Literal["full", "partial", "missing"]
    evidence: str
    gap: str


class InstructionalReviewLLM(BaseModel):
    summary: str
    objective_components: list[ObjectiveCoverageLLM]
    rubric: list[RubricScoreLLM]
    issues: list[QCIssueLLM]


class TimingCheck(BaseModel):
    budget_minutes: int
    declared_minutes: int
    estimated_reading_minutes: float
    estimated_total_minutes: float
    within_budget: bool
    per_section: list[dict] = Field(default_factory=list)
    note: str = ""


class QC2Report(BaseModel):
    summary: str
    overall_score: int  # 0-100
    objective_coverage: list[ObjectiveCoverageLLM] = Field(default_factory=list)
    rubric: list[RubricScoreLLM] = Field(default_factory=list)
    timing: Optional[TimingCheck] = None
    structure_checks: list[dict] = Field(default_factory=list)  # [{check, passed, detail}]
    issues: list[QCIssue] = Field(default_factory=list)
    lesson_version: int = 0
    model: str = ""
    created_at: str = Field(default_factory=now_iso)


# --------------------------------------------------------------------------- #
# Revision
# --------------------------------------------------------------------------- #
class RevisionLLM(BaseModel):
    revised_markdown: str
    change_log: list[str]


# --------------------------------------------------------------------------- #
# Project state
# --------------------------------------------------------------------------- #
StepName = Literal["research", "generate", "qc1", "qc2"]
STEP_ORDER: list[str] = ["research", "generate", "qc1", "qc2"]
STEP_LABELS = {
    "research": "Research (web, books, YouTube)",
    "generate": "Lesson generation",
    "qc1": "QC 1: research & factual accuracy",
    "qc2": "QC 2: instructional quality",
}


class StepState(BaseModel):
    status: Literal["pending", "running", "done", "failed", "stale"] = "pending"
    error: str = ""
    attempts: int = 0
    started_at: str = ""
    finished_at: str = ""


class LessonVersion(BaseModel):
    number: int
    markdown: str
    origin: str  # "generated", "instructor edit", "applied QC fixes", ...
    note: str = ""
    created_at: str = Field(default_factory=now_iso)


class LessonProject(BaseModel):
    id: str
    title: str
    objective: str
    created_at: str = Field(default_factory=now_iso)
    updated_at: str = Field(default_factory=now_iso)
    steps: dict[str, StepState] = Field(default_factory=lambda: {s: StepState() for s in STEP_ORDER})
    research: Optional[ResearchBundle] = None
    draft: Optional[LessonDraft] = None
    versions: list[LessonVersion] = Field(default_factory=list)
    qc1: Optional[QC1Report] = None
    qc2: Optional[QC2Report] = None
    applied_issue_ids: list[str] = Field(default_factory=list)
    dismissed_issue_ids: list[str] = Field(default_factory=list)

    @property
    def current_markdown(self) -> str:
        return self.versions[-1].markdown if self.versions else ""

    @property
    def current_version(self) -> int:
        return self.versions[-1].number if self.versions else 0
