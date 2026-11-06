# Git Branching and Merging

**Learning objective:** Create and switch between Git branches, merge a feature branch into main, and resolve a simple merge conflict.  
**Duration:** 43 minutes (budget 45) · **Format:** self-paced or instructor-led  
**Audience:** Beginner developers and learners who know basic Git commands (like git init, git add, and git commit) and want to learn parallel workflows.
**Prerequisites:** Basic familiarity with the command line; Understanding of basic Git tracking, staging, and committing

## What you will be able to do

- You can create a new Git branch and switch between branches using modern and traditional commands.
- You can merge a separate feature branch back into the main branch.
- You can identify, manually resolve, and finalize a merge conflict using conflict markers.

## Lesson plan

| # | Section | Type | Minutes |
|---|---|---|---|
| 1 | The Parallel Universe Problem | Hook | 3 |
| 2 | Creating and Switching Git Branches | Concept | 8 |
| 3 | Merging Branches and Handling Three-Way Merges | Concept | 8 |
| 4 | Resolving Simple Merge Conflicts | Concept | 7 |
| 5 | End-to-End Workflow Walkthrough | Worked example | 6 |
| 6 | Hands-On Conflict Resolution Practice | Activity | 7 |
| 7 | Knowledge Check | Knowledge check | 2 |
| 8 | Summary and Next Steps | Summary | 2 |
| | **Total** | | **43** |

## 1. The Parallel Universe Problem (3 min)
<!-- kind: hook -->

### Imagine Working on a Shared Book

Imagine you and a co-author are writing a book together. If both of you write directly on the exact same master manuscript at the same time, chaos ensues. Words get overwritten, paragraphs clash, and nobody knows which version is correct. In software development, working directly on the primary line of code (`main`) for every new feature or bug fix creates that exact chaos.

Git solves this with **branches**. Instead of modifying your stable project directly, you can spin off into a separate parallel universe—a branch—where you can experiment safely. Once your feature is complete and working, you bring it back together. Let's learn how to manage these parallel worlds without breaking your project [S4, S5].

*Sources: [S4], [S5]*

## 2. Creating and Switching Git Branches (8 min)
<!-- kind: concept -->

### What is a Git Branch?

A common misconception is that a Git branch is a heavy directory or a physical copy of your project files [S5]. In reality, a **Git branch** is simply a lightweight, movable pointer to a specific commit [S5]. When you create a branch, Git does not duplicate your files; it just places a tiny new sticky note pointing to the current commit history [S1, S5].

### The HEAD Pointer

Your repository always maintains a special reference called **HEAD** [S4]. **HEAD** is a pointer pointing to the current branch or commit you have checked out in your working directory [S4]. When you switch branches, HEAD moves to point to the new branch.

### Commit History and HEAD Deep-Dive

To visualize how Git manages history, imagine a chain of commits represented by their unique SHA-1 hashes (e.g., `a1b2c3d` -> `e4f5g6h`). When you create a new branch pointer using `git branch <branch-name>`, Git creates a file containing the target commit hash without altering the working directory or moving HEAD [S2]. When you switch branches, HEAD updates to point to the new branch reference, and your working directory updates to match the snapshot of the commit pointed to by HEAD [S3]. If you commit new work while on this branch, the branch pointer advances to the new commit, leaving the parent commit behind in the commit graph history [S1].

### Commands for Creation and Switching

To create a branch without switching to it, use `git branch <branch-name>` [S2].
To switch to an existing branch, or create and switch in one go, you can use git switch or `git switch -c <new-branch-name>` [S3].
Alternatively, traditional commands include `git checkout` [S1].

### Example

Suppose you have initialized a repository and made your first commit. To create and switch to a feature branch called `iss53` [S1, S3]:
```bash
git switch -c iss53
```
This instantly creates the pointer and moves your HEAD to `iss53` [S1, S3].

### Common Mistake

* **Misconception:** Switching branches modifies files without needing a clean working state.
* **Correct understanding:** Git normally refuses to switch if your uncommitted changes or staging area modifications conflict with the target branch, protecting your work from accidental overwrites [S1, S3].

*Sources: [S1], [S2], [S3], [S4], [S5]*

## 3. Merging Branches and Handling Three-Way Merges (8 min)
<!-- kind: concept -->

### Bringing Work Together

Once you finish developing a feature on your isolated branch, you need to integrate those changes back into your main line of development (`main`). This process is called **merging** [S4].

### Fast-Forward vs. Three-Way Merges

When you merge two branches, Git chooses one of two strategies depending on their commit history divergence.

#### Fast-Forward Merge
If you merge a branch and its history is a direct linear descendant of your current branch (meaning `main` has had no new commits since you branched off), Git performs a **fast-forward** merge [S1]. Instead of creating a new merge commit, Git simply moves the target branch pointer forward to match the tip of the feature branch [S1].

ASCII representation of a fast-forward scenario:
```
C1 --- C2 (main)
        \
         C3 --- C4 (feature)

After fast-forward merge of feature into main:
C1 --- C2 --- C3 --- C4 (main, feature)
```

#### Three-Way Merge
When the histories of your branches have diverged—meaning `main` has moved forward with other commits while your feature branch has also moved forward—Git cannot simply slide a pointer forward [S1]. Instead, Git performs a **three-way merge** [S1]. A three-way merge utilizes two branch tips and their closest common ancestor commit to synthesize a new commit containing the combined work [S1].

ASCII representation of a three-way merge scenario:
```
        C3 --- C4 (feature)
       /
C1 --- C2 (main)
       \
        C5 (main divergence)

After three-way merge:
        C3 --- C4 (feature)
       /         \
C1 --- C2         C6 (main, merge commit)
       \\         /
        C5 ------/
```

### Example Workflow

To merge a feature branch into `main` [S1, S4]:
1. Switch to your destination branch (`main`):
   ```bash
   git switch main
   ```
2. Run the merge command targeting your feature branch:
   ```bash
   git merge iss53
   ```
Git will automatically combine non-overlapping changes and create a new merge commit if histories have diverged [S1, S4].

*Sources: [S1], [S4]*

## 4. Resolving Simple Merge Conflicts (7 min)
<!-- kind: concept -->

### What is a Merge Conflict?

A **merge conflict** occurs when two separate branches have modified the exact same part or lines of a file in different ways, and Git cannot automatically determine which version is correct [S1, S4]. Beyond simple single-file line collisions, conflicts can span multiple files simultaneously across a pull or merge operation if corresponding files were independently modified on both branches.

### Using Diff Tools and Diagnostic Commands

When a conflict arises, diagnostic utilities help you understand the state of your workspace [S1, S4]:
- `git status`: Lists all unmerged files and paths requiring resolution [S1, S4].
- `git diff`: Displays detailed line-by-line differences between your working tree and staging area, helping isolate what changed in conflicted files.

### Conflict Resolution Markers

When a conflict happens, Git pauses the merge process, marks the affected file as unmerged, and injects standard **conflict resolution markers** directly into the code [S1, S4]:
- `<<<<<<< HEAD`: Designates the changes present in your current local branch.
- `=======`: The dividing line separating your changes from the incoming branch.
- `>>>>>>> iss53`: Designates the changes coming from the incoming branch being merged.

### The Resolution Steps

1. Open the conflicted file in your text editor.
2. Locate and edit out the conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`), choosing which code to keep or combining them [S1, S4].
3. Stage the resolved file using `git add <filename>` [S1, S4].
4. Complete the merge by committing: `git commit` [S1, S4].

If you ever get stuck during a conflict, you can completely cancel the merge operation using `git merge --abort` [S4].

*Sources: [S1], [S4]*

## 5. End-to-End Workflow Walkthrough (6 min)
<!-- kind: worked_example -->

### Putting It All Together

Let's walk through a complete end-to-end scenario involving branch creation, parallel edits, a merge conflict, and its resolution, noting what happens behind the scenes in Git's object database.

#### Step 1: Initialize and Create Base File
```bash
mkdir git-demo && cd git-demo
git init
echo "initial content" > merge.txt
git add merge.txt
git commit -m "initial commit"
```
*Behind the scenes:* Git creates a blob object for `merge.txt`, a tree object capturing directory structure, and a commit object pointing to that tree, storing everything inside the `.git/objects` directory.

#### Step 2: Create a Conflict on Main
We stay on `main` and modify `merge.txt` [S4]:
```bash
echo "content to append on main" >> merge.txt
git commit -am "appended content to merge.txt on main"
```
*Behind the scenes:* A new commit object is added to `main`, updating the `refs/heads/main` file to point to the new commit hash.

#### Step 3: Create a Branch and Create a Conflicting Edit
We switch to a new branch and edit that exact same line differently [S4]:
```bash
git switch -c feature-branch
echo "totally different content on feature" > merge.txt
git commit -am "edited content to cause a conflict"
```
*Behind the scenes:* Git creates a new reference file `refs/heads/feature-branch` pointing to the current commit, then updates HEAD to point to this new reference before recording the new feature commit.

#### Step 4: Merge and Encounter Conflict
We switch back to `main` and attempt to merge `feature-branch` [S1, S4]:
```bash
git switch main
git merge feature-branch
```
Git reports an automatic merge failure, writes MERGE_HEAD and index state files into `.git`, and marks `merge.txt` as unmerged [S1, S4].

#### Step 5: Resolve and Commit
Opening `merge.txt` reveals the markers. We edit the file to keep our desired text, save it, stage it, and commit [S1, S4]:
```bash
git add merge.txt
git commit -m "resolved merge conflict"
```
*Behind the scenes:* Staging clears the conflict flags in the index, and committing writes a new merge commit object referencing both parent commits into the object database. Our repository is now clean and fully updated.

*Sources: [S1], [S4]*

## 6. Hands-On Conflict Resolution Practice (7 min)
<!-- kind: activity -->

### Practice Exercise

Perform the following steps locally to practice creating branches and resolving conflicts:

1. Create a new directory, run `git init`, create a file called `hello.txt` containing the text `Hello World`, and make your first commit [S1].
2. Create and switch to a new branch called `update-greeting` [S1, S3].
3. Modify `hello.txt` to read `Hello Git Branching` and commit the change [S1].
4. Switch back to `main` [S1]. Verify that `hello.txt` reverts back to `Hello World`.
5. Modify `hello.txt` on `main` to read `Hello Main Branch` and commit [S1, S4].
6. Merge `update-greeting` into `main` to trigger a conflict [S1, S4].
7. Use `git status` to find the conflicted file, open it, remove the conflict markers, view the file contents (e.g., using cat hello.txt) to verify that the final text is correct, stage the file with `git add`, and finish with `git commit` [S1, S4].

**Expected Result:** A successful commit resolving the conflict, with `hello.txt` containing your final edited text.

*Sources: [S1], [S3], [S4]*

## 7. Knowledge Check (2 min)
<!-- kind: knowledge_check -->

Answer the following questions to test your understanding of Git branching, merging, and conflict resolution.

**Q1.** What is a Git branch fundamentally?

- A) A heavy directory container that duplicates your project files
- B) A lightweight, movable pointer to a commit
- C) A remote server backup of your code history
- D) An automated testing environment

**Q2.** Which command creates a new branch and switches to it simultaneously?

- A) git branch new-feature
- B) git switch -c new-feature
- C) git checkout main new-feature
- D) git merge new-feature

**Q3.** When does Git perform a three-way merge?

- A) When three different developers are working on the same file
- B) When development histories have diverged from a common ancestor commit
- C) Whenever you run git status
- D) When a merge conflict is successfully resolved and committed

**Q4.** What do the conflict resolution markers like `<<<<<<<` and `>>>>>>>` indicate in a file?

- A) Syntax errors introduced by programming language compilers
- B) Encrypted security signatures for code verification
- C) Conflicting blocks of code between your local branch (HEAD) and the incoming branch
- D) Temporary backup files created automatically by your text editor

**Q5.** You encounter a complex merge conflict and want to completely cancel the merge process and return to safety. What command should you run?

- A) git reset --hard
- B) git branch -D
- C) git merge --abort
- D) git checkout --clean

*Sources: [S1], [S4], [S5]*

## 8. Summary and Next Steps (2 min)
<!-- kind: summary -->

### Lesson Recap

You have successfully learned how to create and switch between Git branches, merge independent work streams using three-way merges, and manually resolve merge conflicts using conflict resolution markers [S1, S4, S5]. These skills form the backbone of safe, collaborative software development.

### Next Step

Practice publishing your branches to a remote repository like GitHub using `git push -u origin <branch-name>` to collaborate with other developers in remote environments.

*Sources: [S1], [S4], [S5]*

## Key takeaways

- A Git branch is a lightweight, movable pointer to a specific commit, not a duplicate file container.
- The HEAD reference points to your currently active branch or commit.
- Modern commands like `git switch -c` allow you to create and jump into a new branch instantly.
- Diverged branches require a three-way merge combining branch tips and their common ancestor.
- Merge conflicts require manual intervention to clear out conflict markers (`<<<<<<<`, `=======`, `>>>>>>>`) before staging and committing.

## Answer key

1. **B**: Git branches are ultra-lightweight pointers to individual commits rather than duplicate directories or physical file containers.
2. **B**: The `git switch -c <new-branch>` command (along with the older `git checkout -b`) creates a new branch and checks it out immediately.
3. **B**: A three-way merge is used when branch histories have diverged, utilizing the two branch tips and their common ancestor.
4. **C**: Git inserts these markers to visibly designate and separate conflicting edits between the local HEAD and the incoming branch.
5. **C**: The `git merge --abort` command safely stops the merge process and restores your working tree back to its pre-merge state.

## Supplementary videos (optional, outside the 45 minutes)

- **[Never fear merge conflicts again - git merge/pull tutorial](https://www.youtube.com/watch?v=DloR0BOGNU0)** (Philomatics, 5:12). *When:* after. *Why:* Provides a clear visual walkthrough of how merge and pull operations work alongside conflict handling. [V1]
- **[Git & GitHub Tutorial for Beginners #8 - Branches](https://www.youtube.com/watch?v=QV0kVNvkMxc)** (Net Ninja, 10:07). *When:* before. *Why:* Offers a beginner-friendly breakdown of branch concepts and switching mechanics for extra reinforcement. [V5]

## References

### Websites

- [S1] Git - Basic Branching and Merging. git-scm.com. <https://git-scm.com/book/en/v2/Git-Branching-Basic-Branching-and-Merging>
- [S2] Git - git-branch Documentation. git-scm.com. <https://git-scm.com/docs/git-branch>
- [S3] Git - git-switch Documentation. git-scm.com. <https://git-scm.com/docs/git-switch>
- [S4] How to Resolve Merge Conflicts in Git? | Atlassian Git Tutorial. atlassian.com. <https://www.atlassian.com/git/tutorials/using-branches/merge-conflicts>
- [S5] How to Create a Branch in Git? | Atlassian Git Tutorial. atlassian.com. <https://www.atlassian.com/git/tutorials/using-branches>
- [S6] Git - Glossary | MDN. developer.mozilla.org. <https://developer.mozilla.org/en-US/docs/Glossary/Git>
- [S7] loop: Wasm text instruction - WebAssembly | MDN. developer.mozilla.org. <https://developer.mozilla.org/en-US/docs/WebAssembly/Reference/Control_flow/loop>
- [S8] block: Wasm text instruction - WebAssembly | MDN. developer.mozilla.org. <https://developer.mozilla.org/en-US/docs/WebAssembly/Reference/Control_flow/block>

### Books

- [B1] *Pro Git*. Scott Chacon, Ben Straub · Springer · 2009. <https://openlibrary.org/works/OL16310859W>
- [B2] *Git: Pocket Guide*. Richard E. Silverman · O'Reilly Media · 2013. <https://openlibrary.org/works/OL19548227W>

### Videos

- [V1] Never fear merge conflicts again - git merge/pull tutorial. Philomatics, YouTube. <https://www.youtube.com/watch?v=DloR0BOGNU0>
- [V5] Git & GitHub Tutorial for Beginners #8 - Branches. Net Ninja, YouTube. <https://www.youtube.com/watch?v=QV0kVNvkMxc>
