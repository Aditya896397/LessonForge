# QC Layer 2: Instructional Quality Audit

**Lesson:** Git Branching and Merging  
**Lesson version audited:** v2  
**Model:** gemini-3.5-flash  
**Date:** 2026-11-06T17:32:53+00:00  
**Overall score:** 87/100 (70% rubric, 20% objective coverage, 10% automatic checks)

## Summary

This lesson provides a solid introduction to Git branching, merging, and conflict resolution with clear explanations and a hands-on activity. However, several core sections suffer from severe time-allocation padding where the designated minutes vastly exceed the actual reading content. Addressing these pacing discrepancies and expanding the conceptual sections will ensure a balanced and robust learning experience.

## Learning objective alignment

| Objective component | Coverage | Evidence | Gap |
|---|---|---|---|
| Create and switch between Git branches | **full** | Section 2 provides detailed conceptual explanations and commands (git switch -c) for branch creation and switching, reinforced by the practice exercise in Section 6. |  |
| Merge a feature branch into main | **full** | Section 3 explains fast-forward and three-way merges with ASCII diagrams and step-by-step instructions, and Section 5 demonstrates the merge workflow. |  |
| Resolve a simple merge conflict | **full** | Section 4 covers conflict markers and resolution steps, Section 5 walks through an end-to-end conflict scenario, and Section 6 gives learners hands-on practice. |  |

## Rubric

| Criterion | Score (1-5) | Rationale |
|---|---|---|
| Objective alignment | 5 | Every component of the learning objective is thoroughly addressed through dedicated conceptual explanations, worked examples, and practical activities. |
| Clarity | 4 | The technical explanations of Git internals and pointers are generally clear, though some sections feel overly sparse for the allocated time. |
| Structure and flow | 5 | The lesson follows a logical sequence from hook to concepts, worked examples, hands-on practice, and knowledge checks. |
| Relevance and engagement | 4 | The introductory book-writing analogy creates a strong relatable hook, and the command-line examples are highly practical for developers. |
| Examples and practical application | 5 | The walkthrough in Section 5 and the hands-on exercise in Section 6 give concrete opportunities to apply and test the commands. |
| Assessment quality | 5 | The knowledge check features five well-crafted multiple-choice questions that directly align with the core concepts taught in the lesson. |
| Timing feasibility | 2 | Sections 2, 3, and 4 suffer from severe timing inflation, declaring 8 or 7 minutes of time while containing only 1.5 to 2.2 minutes of readable text. |

## Time budget (45-minute check)

Fits the 45-min budget on paper, but these sections have far less text than their minutes suggest (thin content or padded timing): 2. Creating and Switching Git Branches; 3. Merging Branches and Handling Three-Way Merges; 4. Resolving Simple Merge Conflicts.

Declared: 43 min · Estimated reading: 11.2 min · Estimated total: 43.0 min · Within budget: yes

| Section | Type | Declared | Words | Reading time | Flag |
|---|---|---|---|---|---|
| 1. The Parallel Universe Problem | hook | 3 | 128 | 0.8 |  |
| 2. Creating and Switching Git Branches | concept | 8 | 371 | 2.2 | thin/padded |
| 3. Merging Branches and Handling Three-Way Merges | concept | 8 | 300 | 1.8 | thin/padded |
| 4. Resolving Simple Merge Conflicts | concept | 7 | 256 | 1.5 | thin/padded |
| 5. End-to-End Workflow Walkthrough | worked_example | 6 | 363 | 2.1 |  |
| 6. Hands-On Conflict Resolution Practice | activity | 7 | 174 | 1.0 |  |
| 7. Knowledge Check | knowledge_check | 2 | 231 | 1.4 |  |
| 8. Summary and Next Steps | summary | 2 | 75 | 0.4 |  |

## Automatic structure checks

- PASS: Opens with a hook
- PASS: Has concept explanation sections (3 found)
- PASS: Has a worked example
- PASS: Has a hands-on activity
- PASS: Has a knowledge check with >= 4 questions (5 questions)
- PASS: Ends with a summary
- PASS: Fits the time budget (Fits the 45-min budget on paper, but these sections have far less text than their minutes suggest (thin content or padded timing): 2. Creating and Switching Git Branches; 3. Merging Branches and Handling Three-Way Merges; 4. Resolving Simple Merge Conflicts.)
- PASS: No truncated sections
- FAIL: Section times match their content (2. Creating and Switching Git Branches: 8 min for ~2.2 min of text; 3. Merging Branches and Handling Three-Way Merges: 8 min for ~1.8 min of text; 4. Resolving Simple Merge Conflicts: 7 min for ~1.5 min of text)
- PASS: Concept/example sections cite sources
- PASS: Includes supplementary YouTube videos
- PASS: Includes a reference list

## Issues and suggested improvements

### QC2-1 · MAJOR · structure check
- **Where:** Whole lesson
- **Problem:** Automatic check failed: Section times match their content. 2. Creating and Switching Git Branches: 8 min for ~2.2 min of text; 3. Merging Branches and Handling Three-Way Merges: 8 min for ~1.8 min of text; 4. Resolving Simple Merge Conflicts: 7 min for ~1.5 min of text
- **Suggestion:** Adjust section minutes so they add up to the budget.

### QC2-2 · MAJOR · Timing feasibility · APPLIED
- **Where:** 2. Creating and Switching Git Branches
- **Text:** "Creating and Switching Git Branches (8 min)"
- **Problem:** The allocated time of 8 minutes is heavily padded for only ~2.2 minutes of reading text, leading to potential learner pacing issues.
- **Suggestion:** Either reduce the section time to 3 minutes or expand the text with deeper explanations of commit hashes and interactive terminal check-ins.

### QC2-3 · MAJOR · Timing feasibility · APPLIED
- **Where:** 3. Merging Branches and Handling Three-Way Merges
- **Text:** "Merging Branches and Handling Three-Way Merges (8 min)"
- **Problem:** An 8-minute time allocation for approximately 1.8 minutes of reading text leaves a significant pacing gap.
- **Suggestion:** Adjust the time allocation downward to match the content length or add guided practice prompts within the section.

### QC2-4 · MAJOR · Timing feasibility · APPLIED
- **Where:** 4. Resolving Simple Merge Conflicts
- **Text:** "Resolving Simple Merge Conflicts (7 min)"
- **Problem:** The declared 7-minute duration contains only about 1.5 minutes of text, creating an imbalance between expected time and actual reading content.
- **Suggestion:** Scale down the timer for this section to 3 minutes or add more detailed troubleshooting instructions for complex conflict scenarios.

