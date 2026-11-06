# QC Layer 2: Instructional Quality Audit

**Lesson:** HTTP Requests and Responses  
**Lesson version audited:** v1  
**Model:** gemini-3.5-flash  
**Date:** 2026-11-06T17:16:45+00:00  
**Overall score:** 90/100 (70% rubric, 20% objective coverage, 10% automatic checks)

## Summary

This lesson is well-structured, clearly written, and highly aligned with its learning objective. It effectively combines conceptual explanations, code-level worked examples, and a scenario-based practice matrix. To make it even stronger, the lesson should include explicit examples of 5xx status codes (e.g., 500 Internal Server Error) in the walkthrough and replace an overly detailed quiz question on HTTP Date header specifications with one aligned to distinguishing response categories.

## Learning objective alignment

| Objective component | Coverage | Evidence | Gap |
|---|---|---|---|
| Explain GET and POST methods | **full** | Section 2 provides detailed coverage of GET and POST (purpose, body, safety, idempotency, cacheability) with a comparison table and analogy. Section 4 shows raw HTTP request/response cycles for both methods, and Section 5 and 6 test learner understanding. |  |
| Distinguish between 2xx, 4xx, and 5xx response status categories | **full** | Section 3 defines 2xx, 4xx, and 5xx categories with standard examples (200, 201, 401, 410) and a summary table. Section 4 provides worked examples across 2xx and 4xx, and Section 5 requires learners to select correct status categories for scenarios. |  |

## Rubric

| Criterion | Score (1-5) | Rationale |
|---|---|---|
| Objective alignment | 5 | Every section, walkthrough example, and activity directly targets explaining GET/POST and categorizing 2xx, 4xx, and 5xx HTTP responses. |
| Clarity | 4 | Concepts like safety and idempotency are clearly defined using accessible analogies like the public bulletin board versus drop box. |
| Structure and flow | 5 | The progression moves logically from an intuitive hook to concepts, concrete HTTP message walkthroughs, active scenario practice, assessment, and wrap-up. |
| Relevance and engagement | 4 | Real-world web interactions (online shopping, form submission, missing authentication) ground abstract HTTP protocol rules in practical developer contexts. |
| Examples and practical application | 4 | Walkthroughs show complete, realistic HTTP request and response message headers and bodies, though a 5xx server error example is missing from the walkthrough. |
| Assessment quality | 4 | The knowledge check features strong situational multiple-choice items, though one question focuses on obscure RFC Date header rules rather than core objective concepts. |
| Timing feasibility | 5 | The 45-minute breakdown gives generous room for reading, inspecting HTTP code blocks, and working through the decision matrix activity. |

## Time budget (45-minute check)

Fits the budget: 45 min declared, about 45 min estimated.

Declared: 45 min · Estimated reading: 16.0 min · Estimated total: 45.0 min · Within budget: yes

| Section | Type | Declared | Words | Reading time | Too long? |
|---|---|---|---|---|---|
| 1. What Happens When You Click a Link? | hook | 3 | 168 | 1.0 |  |
| 2. HTTP Request Methods: GET vs. POST | concept | 10 | 589 | 3.5 |  |
| 3. HTTP Response Status Categories: 2xx, 4xx, and 5xx | concept | 10 | 425 | 2.5 |  |
| 4. Walkthrough: Request and Response Cycles in Action | worked_example | 8 | 504 | 3.0 |  |
| 5. Hands-on Decision Matrix & Scenario Analysis | activity | 8 | 336 | 2.0 |  |
| 6. Test Your Understanding | knowledge_check | 4 | 513 | 3.0 |  |
| 7. Lesson Wrap-Up and Next Steps | summary | 2 | 191 | 1.1 |  |

## Automatic structure checks

- PASS: Opens with a hook
- PASS: Has concept explanation sections (2 found)
- PASS: Has a worked example
- PASS: Has a hands-on activity
- PASS: Has a knowledge check with >= 4 questions (6 questions)
- PASS: Ends with a summary
- PASS: Fits the time budget (Fits the budget: 45 min declared, about 45 min estimated.)
- PASS: Concept/example sections cite sources
- PASS: Includes supplementary YouTube videos
- PASS: Includes a reference list

## Issues and suggested improvements

### QC2-2 · MAJOR · weak example
- **Where:** 4. Walkthrough: Request and Response Cycles in Action
- **Text:** "## 4. Walkthrough: Request and Response Cycles in Action (8 min)"
- **Problem:** The walkthrough provides concrete code blocks for 2xx (200 OK, 201 Created) and 4xx (401 Unauthorized, 410 Gone) responses, but completely omits a 5xx response code walkthrough example, leaving the 5xx objective component incompletely illustrated in practice.
- **Suggestion:** Add a Scenario 5 showing an HTTP exchange for a server failure (e.g., 'Scenario 5: Database Connection Failure (500 Internal Server Error)' with a sample HTTP 500 response block).

### QC2-3 · MAJOR · misaligned assessment item
- **Where:** 6. Test Your Understanding
- **Text:** "Q4. According to RFC 9110, which rule correctly describes the generation of the Date header field by origin servers with a clock?"
- **Problem:** Question 4 tests niche specification rules about when the Date header MUST vs MAY be generated across status classes, which is outside the main learning objective of explaining GET/POST and distinguishing 2xx, 4xx, and 5xx categories.
- **Suggestion:** Replace Q4 with a scenario-based question asking learners to distinguish a server error (5xx class, e.g., 500) from a client error (4xx class, e.g., 404 or 401) when an API request fails.

### QC2-1 · MINOR · missing explanation
- **Where:** 3. HTTP Response Status Categories: 2xx, 4xx, and 5xx
- **Text:** "The 5xx (Server Error) status category indicates that the server encountered an internal failure or error condition that prevented it from fulfilling a valid request [S6]. The error lies entirely on the server side [S6]."
- **Problem:** Unlike 2xx (200, 201) and 4xx (401, 410), the 5xx section does not provide specific status code examples (such as 500 Internal Server Error or 503 Service Unavailable), making it harder for learners to concrete memory anchors for 5xx.
- **Suggestion:** Add brief bullet points under 5xx for '500 Internal Server Error' (generic server failure) and '503 Service Unavailable' (server temporarily overloaded or under maintenance).

