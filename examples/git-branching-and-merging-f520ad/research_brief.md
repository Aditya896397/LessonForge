# Research brief: Git Branching and Merging

## 1. Objective breakdown
- Create Git branches [S5].
- Switch between Git branches [S1].
- Merge a feature branch into main [S4].
- Resolve a simple merge conflict [S1, S4].

## 2. Core definitions and facts
- **Git branch:** A lightweight, movable pointer to a commit, rather than a container for commits or a directory copy [S5]. It represents an independent line of development [S5].
- **HEAD:** A reference pointing to the current branch or commit you have checked out [S4].
- **Merge conflict:** Occurs when two separate branches have modified the same part or lines of a file differently, and Git cannot automatically determine what is correct [S1, S4].
- **Conflict resolution markers:** Standard markers added by Git (`<<<<<<<`, `=======`, `>>>>>>>`) to designate conflicting blocks between the local branch (HEAD) and the incoming branch [S1, S4].
- **Three-way merge:** A merge process used by Git when development histories have diverged from a common ancestor, utilizing two branch tips and their common ancestor [S1].

## 3. Detailed notes per objective component
- **Create Git branches:** Branches in Git are pointers to a commit [S5]. Creating a branch only creates a new pointer and does not alter the repository or working directory in any other way [S1, S5]. Commands like `git branch <branch>` create a branch, while `git switch -c <new-branch>` or `git checkout -b <branch>` create and switch to it simultaneously [S1, S3].
- **Switch between Git branches:** Switching branches updates the working directory to match the snapshot of the target branch's last commit [S1]. Git automatically adds, removes, and modifies files to match that state [S1]. Git normally refuses to switch if uncommitted changes or staging area modifications conflict with the target branch [S1, S3].
- **Merge a feature branch into main:** Merging combines separate branches and resolves conflicting edits [S4]. When histories have diverged, Git performs a three-way merge using the two branch tips and their common ancestor [S1]. 
- **Resolve a simple merge conflict:** When a merge fails due to conflicting edits on the same lines, Git pauses the process and marks the files as unmerged [S1, S4]. The developer must open the conflicted file, edit or remove the conflict resolution markers (`<<<<<<<`, `=======`, `>>>>>>>`), choose or combine the code changes, stage the resolved file using `git add`, and complete the merge with `git commit` [S1, S4]. A merge can be aborted using `git merge --abort` [S4].

## 4. Worked example ideas
- **Example 1: Creating and Switching Branches**
  - Initialize a repo and make an initial commit:
    ```bash
    mkdir git-demo && cd git-demo
    git init
    echo "initial content" > index.html
    git add index.html
    git commit -m "initial commit"
    ```
  - Create and switch to a new feature branch using `git switch`:
    ```bash
    git switch -c iss53
    ```
- **Example 2: Simulating and Resolving a Merge Conflict**
  - On `main`, append content to `merge.txt` and commit [S4]:
    ```bash
    git checkout main
    echo "content to append" >> merge.txt
    git commit -am "appended content to merge.txt"
    ```
  - On a separate branch (`new_branch_to_merge_later`), edit the same line differently and commit [S4]:
    ```bash
    git checkout new_branch_to_merge_later
    echo "totally different content to merge later" > merge.txt
    git commit -am "edited content to cause a conflict"
    ```
  - Attempt to merge `new_branch_to_merge_later` into `main`, observe the conflict, view status, inspect markers, resolve manually, stage, and commit [S1, S4].

## 5. Practical, real-world applications
- **Feature isolation:** Allowing multiple developers or teams to work on isolated features or bug fixes in parallel without contaminating the stable `main` codebase [S4, S5].
- **Safe experimentation:** Testing new ideas or risky changes on a separate branch before deciding whether to merge or discard them [S5].

## 6. Common misconceptions and pitfalls
- **Misconception:** Branches are heavy directories or containers that duplicate project files [S5].
  - *Correct understanding:* Git branches are ultra-lightweight pointers to individual commits [S5].
- **Misconception:** Switching branches modifies files without needing a clean working state.
  - *Correct understanding:* Git prevents switching when uncommitted changes conflict with the target branch to protect your work [S1, S3].
- **Misconception:** Git automatically resolves all overlapping line edits during a merge.
  - *Correct understanding:* When identical lines are modified differently, Git halts the merge, adds conflict markers, and requires manual intervention [S1, S4].

## 7. Hands-on activity ideas
- **Activity 1: Branch Creation and Context Switching (10 minutes)**
  - Task: Create a repository, add a file named `hello.txt`, create a new branch named `feature`, switch to it, add a new line to `hello.txt`, commit it, switch back to `main`, verify the file reverts to its original state, and then merge `feature` into `main` [S1].
- **Activity 2: Conflict Resolution Challenge (10 minutes)**
  - Task: Create a merge conflict by editing the same line of a text file in two different branches, run `git merge`, use `git status` to locate the unmerged file, manually clear the conflict markers by choosing the correct code block, stage the file, and commit the resolution [S1, S4].

## 8. Nuances and points of disagreement
- The source excerpts do not detail advanced conflict resolution tools beyond mentioning `git mergetool` [S1] and basic text editor conflict markers [S1, S4], nor do they deeply contrast older commands (`git checkout`) with modern ones (`git switch` / `git restore`), though both are referenced [S1, S2, S3].
