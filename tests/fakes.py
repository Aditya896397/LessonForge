"""A deterministic stand-in for Gemini so the whole pipeline can be tested offline."""
from __future__ import annotations

from lessonforge.llm import GroundedResult, LLMError
from lessonforge.models import (ClaimCheckLLM, ExtractedClaim, ExtractedClaims, FactCheckLLM,
                                InstructionalReviewLLM, LessonDraft, LessonSection, ObjectiveCoverageLLM,
                                ProposedSource, QCIssueLLM, QuizQuestion, RevisionLLM, RubricScoreLLM,
                                SourceAssessmentLLM, SourcePlan, SourceReviewLLM, VerifyPlan, VideoPick)

RESEARCH_TEXT = """## 1. Objective breakdown
- Explain GET and POST
- Distinguish 2xx, 4xx and 5xx

## 2. Core definitions and facts
GET requests retrieve a representation of a resource and are defined as safe and idempotent.
POST requests submit data to be processed by the target resource.
Status codes in the 2xx class indicate success, 4xx indicate client errors and 5xx indicate server errors.

## 3. Detailed notes
More detail here so the brief is long enough to pass the minimum length check of the research step.

```json
{"book_suggestions": [{"title": "HTTP: The Definitive Guide", "author": "David Gourley"}],
 "video_search_queries": ["http methods explained"]}
```
"""


def make_draft(minutes=(3, 10, 10, 8, 9, 5, 2), bad_cite=False) -> LessonDraft:
    kinds = ["hook", "concept", "concept", "worked_example", "activity", "knowledge_check", "summary"]
    sections = []
    for i, (k, m) in enumerate(zip(kinds, minutes)):
        cite = " [S1]" + (" [S99]" if bad_cite and i == 1 else "")
        sections.append(LessonSection(heading=f"Section {i + 1}", kind=k, minutes=m,
                                      content_markdown=("GET is safe and idempotent." + cite + " ") * (m * 25),
                                      source_ids=["S1"] + (["S99"] if bad_cite and i == 1 else [])))
    quiz = [QuizQuestion(question=f"Q{i}?", options=["a", "b", "c", "d"], correct_option_index=1,
                         explanation="because") for i in range(5)]
    return LessonDraft(title="HTTP Requests and Responses", learning_objective="Explain GET and POST",
                       target_audience="Beginners", prerequisites=["Basic web use"],
                       success_criteria=["You can explain GET"], sections=sections, quiz=quiz,
                       key_takeaways=["GET reads"], recommended_videos=[
                           VideoPick(video_ref="V1", why_watch="clear", when_to_watch="after"),
                           VideoPick(video_ref="V9", why_watch="made up", when_to_watch="after")])


class FakeLLM:
    def __init__(self, fail_on: set[str] | None = None):
        self.fail_on = fail_on or set()
        self.calls: list[str] = []

    def grounded(self, prompt, system, model=None, temperature=0.2, retries=None):
        kind = "verify" if "Verify each claim" in prompt else "research"
        self.calls.append(kind)
        if "grounding" in self.fail_on:
            raise LLMError("Gemini rate limit / quota exceeded. Wait a minute and press Retry.")
        if kind in self.fail_on:
            raise LLMError(f"simulated {kind} failure")
        if kind == "research":
            seg = "GET requests retrieve a representation of a resource and are defined as safe and idempotent."
            return GroundedResult(text=RESEARCH_TEXT, sources=[{"title": "rfc-editor.org", "uri": "https://www.rfc-editor.org/rfc/rfc9110"},
                                                               {"title": "developer.mozilla.org", "uri": "https://developer.mozilla.org/en-US/docs/Web/HTTP/Status"}],
                                  queries=["http get post"], supports=[{"text": seg, "source_indices": [0, 1]}])
        text = ('```json\n{"claims": [{"claim": "GET is safe and idempotent", "location": "Section 2", '
                '"verdict": "supported", "explanation": "RFC 9110 says so", "correction": "", "evidence": "RFC 9110"},'
                '{"claim": "POST is idempotent", "location": "Section 3", "verdict": "incorrect", '
                '"explanation": "POST is not idempotent", "correction": "POST is not idempotent.", "evidence": "RFC 9110"}]}\n```')
        return GroundedResult(text=text, sources=[{"title": "rfc", "uri": "https://www.rfc-editor.org/rfc/rfc9110"}],
                              queries=["is GET idempotent"], supports=[{"text": "RFC 9110 says so", "source_indices": [0]}])

    def generate(self, prompt, system, model=None, temperature=0.3):
        self.calls.append("generate-text")
        return RESEARCH_TEXT.replace("safe and idempotent.", "safe and idempotent [S1].")

    def structured(self, prompt, schema, system, model=None, temperature=0.3):
        self.calls.append(schema.__name__)
        if schema.__name__ in self.fail_on:
            raise LLMError(f"simulated {schema.__name__} failure")
        if schema is LessonDraft:
            return make_draft(bad_cite=True)
        if schema is ExtractedClaims:
            return ExtractedClaims(claims=[ExtractedClaim(claim="GET is safe and idempotent", location="Section 2"),
                                           ExtractedClaim(claim="POST is idempotent", location="Section 3")])
        if schema is FactCheckLLM and "=== EVIDENCE ===" not in prompt:
            return FactCheckLLM(claims=[ClaimCheckLLM(claim="x", location="y", verdict="supported", explanation="",
                                                      correction="", evidence="")])
        if schema is SourceReviewLLM:
            return SourceReviewLLM(sources=[SourceAssessmentLLM(source_id="S1", reliability="high", relevance="high", note="RFC")],
                                   issues=[QCIssueLLM(severity="minor", category="gap", location="Section 2", quote="",
                                                      problem="No mention of PUT", suggestion="Mention PUT briefly")],
                                   summary="Good sources.")
        if schema is InstructionalReviewLLM:
            return InstructionalReviewLLM(summary="Solid.", objective_components=[
                ObjectiveCoverageLLM(component="Explain GET and POST", coverage="full", evidence="s2", gap=""),
                ObjectiveCoverageLLM(component="Distinguish status classes", coverage="partial", evidence="s3", gap="needs practice")],
                rubric=[RubricScoreLLM(criterion="Clarity", score=4, rationale="clear")],
                issues=[QCIssueLLM(severity="major", category="practice", location="Section 5", quote="",
                                   problem="No status code practice", suggestion="Add a sorting exercise")])
        if schema in (SourcePlan, VerifyPlan):
            return schema(search_queries=["HTTP methods"], proposed_sources=[ProposedSource(
                url="https://www.rfc-editor.org/rfc/rfc9110", title="RFC 9110", why="spec")])
        if schema is FactCheckLLM and "=== EVIDENCE ===" in prompt:
            return FactCheckLLM(claims=[
                ClaimCheckLLM(claim="GET is safe and idempotent", location="Section 2", verdict="supported",
                              explanation="E1 confirms", correction="", evidence="[E1] RFC 9110 says GET is safe"),
                ClaimCheckLLM(claim="POST is idempotent", location="Section 3", verdict="incorrect",
                              explanation="not idempotent", correction="POST is not idempotent.", evidence="[E1]")])
        if schema is RevisionLLM:
            md = prompt.split("=== LESSON (Markdown) ===", 1)[1].split("Return the complete revised lesson")[0].strip()
            return RevisionLLM(revised_markdown=md.replace("GET is safe", "GET is safe (RFC 9110)"),
                               change_log=["Section 2: added RFC reference"])
        raise AssertionError(f"unexpected schema {schema}")
