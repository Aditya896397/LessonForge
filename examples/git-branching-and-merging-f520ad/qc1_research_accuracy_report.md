# QC Layer 1: Research & Factual Accuracy Audit

**Lesson:** Git Branching and Merging  
**Lesson version audited:** v2  
**Model:** gemini-3.5-flash  
**Date:** 2026-11-06T17:33:06+00:00  
**Verification method:** web-retrieval  
**Accuracy score:** 88/100 (computed from claim verdicts)

## Summary

The lesson exhibits high research quality, utilizing official Git documentation and reputable tutorials to support core concepts like branching, merging, and conflict resolution. Claims are generally well-backed by citations, though minor unsupported commands like git merge --abort and git diff appear without explicit source coverage in the provided excerpts. Addressing these minor citation gaps will ensure complete traceability across all diagnostic commands.

## Claim verification

Verdict counts: supported: 9, unsupported: 3

| # | Claim | Section | Verdict | Explanation | Correction | Evidence |
|---|---|---|---|---|---|---|
| 1 | [Creating and Switching Git Branches] A Git branch is simply a lightweight, movable pointer to a specific commit. | [Creating and Switching Git Branches] | **supported** | The evidence explicitly confirms that a branch in Git is a lightweight movable pointer to a commit. |  | [E1] Git - Branches in a Nutshell states that a branch in Git is simply a lightweight movable pointer to one of these commits. <https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell> |
| 2 | [Creating and Switching Git Branches] HEAD is a pointer pointing to the current branch or commit you have checked out in your working directory. | [Creating and Switching Git Branches] | **supported** | The evidence verifies that HEAD is a special pointer pointing to the local branch or commit you currently have checked out. |  | [E4][E18] Git documentation notes that HEAD points to the branch you have checked out. <https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging> <https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell> |
| 3 | [Creating and Switching Git Branches] To create a branch without switching to it, use git branch <branch-name>. | [Creating and Switching Git Branches] | **supported** | The evidence states that the git branch command creates a new branch without switching to it. |  | [E17][E18] Git - Branches in a Nutshell states that the git branch command only created a new branch and didn't switch to it. <https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell> |
| 4 | [Creating and Switching Git Branches] To switch to an existing branch, or create and switch in one go, you can use git switch or git switch -c <new-branch-name>. | [Creating and Switching Git Branches] | **supported** | The evidence confirms that git switch is used for switching to an existing branch and git switch -c is used to create and switch to a new branch. |  | [E9] Git - Branches in a Nutshell lists git switch for switching and git switch -c for creating and switching. <https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell> |
| 5 | [Merging Branches and Handling Three-Way Merges] If you merge a branch and its history is a direct linear descendant of your current branch, Git performs a fast-forward merge. | [Merging Branches and Handling Three-Way Merges] | **supported** | The evidence states that when a commit can be reached by following the first commit's history (directly ahead), Git performs a fast-forward merge by moving the pointer forward. |  | [E2] Git - Basic Branching and Merging describes a fast-forward merge when a commit is directly ahead. <https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging> |
| 6 | [Merging Branches and Handling Three-Way Merges] A three-way merge utilizes two branch tips and their closest common ancestor commit to synthesize a new commit containing the combined work. | [Merging Branches and Handling Three-Way Merges] | **supported** | The evidence notes that a three-way merge uses the two snapshots pointed to by the branch tips and the common ancestor of the two. |  | [E12] Git - Basic Branching and Merging explains that Git does a simple three-way merge using the two snapshots pointed to by branch tips and their common ancestor. <https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging> |
| 7 | [Resolving Simple Merge Conflicts] A merge conflict occurs when two separate branches have modified the exact same part or lines of a file in different ways, and Git cannot automatically determine which version is correct. | [Resolving Simple Merge Conflicts] | **supported** | The evidence states that changing the same part of the same file differently in two merging branches causes a merge conflict where Git cannot merge them cleanly. |  | [E13] Git - Basic Branching and Merging notes that changing the same part of the same file differently results in a merge conflict. <https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging> |
| 8 | [Resolving Simple Merge Conflicts] git status lists all unmerged files and paths requiring resolution. | [Resolving Simple Merge Conflicts] | **supported** | The evidence shows that git status lists unmerged paths and files that require fixing conflicts and running git commit or git add. |  | [E14][E16] Git - Basic Branching and Merging demonstrates git status output showing unmerged paths. <https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging> |
| 9 | [Resolving Simple Merge Conflicts] git diff displays detailed line-by-line differences between your working tree and staging area. | [Resolving Simple Merge Conflicts] | **unsupported** | The provided text excerpts do not mention git diff or its functionality. | git status is shown in the text to list unmerged paths, but git diff is not covered by the evidence. | [E5][E7] The provided evidence does not mention git diff. <https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging> <https://git-scm.com/docs/git-switch> |
| 10 | [Resolving Simple Merge Conflicts] If you ever get stuck during a conflict, you can completely cancel the merge operation using git merge --abort. | [Resolving Simple Merge Conflicts] | **unsupported** | The provided evidence excerpts do not mention git merge --abort. | The text does not mention git merge --abort for canceling merges. | [E5][E10][E13] The provided evidence does not contain information about git merge --abort. <https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging> <https://git-scm.com/docs/git-switch> |
| 11 | [Answer key] The git switch -c <new-branch> command creates a new branch and checks it out immediately. | [Answer key] | **supported** | The evidence explicitly states that git switch -c creates a new branch and switches to it. |  | [E9] Git - Branches in a Nutshell states: 'Create a new branch and switch to it: git switch -c new-branch'. <https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell> |
| 12 | [Answer key] The git merge --abort command safely stops the merge process and restores your working tree back to its pre-merge state. | [Answer key] | **unsupported** | None of the provided evidence excerpts mention git merge --abort. | The provided text does not contain references to git merge --abort. | [E5][E7][E12][E19] The evidence does not discuss git merge --abort. <https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging> <https://git-scm.com/docs/git-switch> |

## Source reliability and relevance

| Id | Source | Reliability | Relevance | Reachable | Cited | Note |
|---|---|---|---|---|---|---|
| S1 | [Git - Basic Branching and Merging](https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging) | high | high | yes | yes | Official Git documentation (Pro Git book) providing reliable coverage of branching and merging. |
| S2 | [Git - git-branch Documentation](https://git-scm.com/docs/git-branch) | high | high | yes | yes | Official Git reference documentation for git-branch. |
| S3 | [Git - git-switch Documentation](https://git-scm.com/docs/git-switch) | high | high | yes | yes | Official Git reference documentation for git-switch. |
| S4 | [How to Resolve Merge Conflicts in Git? \| Atlassian Git Tutorial](https://www.atlassian.com/git/tutorials/using-branches/merge-conflicts) | high | high | yes | yes | Atlassian Git tutorial offering clear guidance on merge conflicts. |
| S5 | [How to Create a Branch in Git? \| Atlassian Git Tutorial](https://www.atlassian.com/git/tutorials/using-branches) | high | high | yes | yes | Atlassian Git tutorial explaining branch creation fundamentals. |
| S6 | [Git - Glossary \| MDN](https://developer.mozilla.org/en-US/docs/Glossary/Git) | high | low | yes | no | MDN Git glossary, valid source but not cited in the lesson. |
| S7 | [loop: Wasm text instruction - WebAssembly \| MDN](https://developer.mozilla.org/en-US/docs/WebAssembly/Reference/Control_flow/loop) | high | low | yes | no | MDN WebAssembly reference, completely irrelevant to Git. |
| S8 | [block: Wasm text instruction - WebAssembly \| MDN](https://developer.mozilla.org/en-US/docs/WebAssembly/Reference/Control_flow/block) | high | low | yes | no | MDN WebAssembly reference, completely irrelevant to Git. |
| B1 | [Pro Git](https://openlibrary.org/works/OL16310859W) | high | medium | yes | no | Pro Git book text, highly authoritative book source. |
| B2 | [Git: Pocket Guide](https://openlibrary.org/works/OL19548227W) | high | medium | yes | no | Git Pocket Guide, authoritative reference book. |

## Issues and suggested improvements

### QC1-1 · MAJOR · claim unsupported · APPLIED
- **Where:** [Resolving Simple Merge Conflicts]
- **Text:** "[Resolving Simple Merge Conflicts] git diff displays detailed line-by-line differences between your working tree and staging area."
- **Problem:** The provided text excerpts do not mention git diff or its functionality.
- **Suggestion:** git status is shown in the text to list unmerged paths, but git diff is not covered by the evidence.

### QC1-2 · MAJOR · claim unsupported · APPLIED
- **Where:** [Resolving Simple Merge Conflicts]
- **Text:** "[Resolving Simple Merge Conflicts] If you ever get stuck during a conflict, you can completely cancel the merge operation using git merge --abort."
- **Problem:** The provided evidence excerpts do not mention git merge --abort.
- **Suggestion:** The text does not mention git merge --abort for canceling merges.

### QC1-3 · MAJOR · claim unsupported
- **Where:** [Answer key]
- **Text:** "[Answer key] The git merge --abort command safely stops the merge process and restores your working tree back to its pre-merge state."
- **Problem:** None of the provided evidence excerpts mention git merge --abort.
- **Suggestion:** The provided text does not contain references to git merge --abort.

### QC1-4 · MINOR · unsupported claim
- **Where:** 4. Resolving Simple Merge Conflicts
- **Text:** "git diff: Displays detailed line-by-line differences between your working tree and staging area, helping isolate what changed in conflicted files."
- **Problem:** The text discusses git diff in the context of merge conflicts, but the independent evidence notes that git diff and git merge --abort lack direct citation coverage from the primary S1-S5 sources.
- **Suggestion:** Add explicit citations or ensure git diff explanation focuses on standard conflict-state usage supported by existing sources.


## Verification searches run

- git branch pointer commit documentation
- git switch command documentation
- git merge fast forward three way
- git merge abort documentation

## Pages consulted during verification

- Git - Branches in a Nutshell: <https://git-scm.com/book/en/v2/Git-Branching-Branches-in-a-Nutshell>
- Git - git-switch Documentation: <https://git-scm.com/docs/git-switch>
- Git - Basic Branching and Merging: <https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging>
- Git - Glossary | MDN: <https://developer.mozilla.org/en-US/docs/Glossary/Git>
- Data Version Control (software) - Wikipedia: <https://en.wikipedia.org/wiki/Data_Version_Control_(software)>
