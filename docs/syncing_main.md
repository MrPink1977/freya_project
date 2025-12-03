# Syncing Local Changes to Main

Use this checklist to make sure new changes are recorded locally and merged into `main` cleanly.

## 1. Verify current branch and status
```bash
git status -sb
git branch -vv
```
Confirm you are on the feature branch with uncommitted work and note the upstream tracking branch.

## 2. Fetch the latest remote updates
```bash
git fetch origin
```
This updates your local view of `origin/main` and any remote feature branches.

## 3. Rebase or merge `main` onto your branch
Prefer rebasing for a linear history:
```bash
git rebase origin/main
```
If conflicts appear, resolve them, then continue:
```bash
git status
# edit files to resolve conflicts
git add <resolved-files>
git rebase --continue
```
If rebase is not desired, you can merge instead:
```bash
git merge origin/main
```

## 4. Run validations on your branch
Execute the minimal checks relevant to your change (examples):
```bash
python3 -m compileall freya freya_mcp
pytest
```
Update this list as your project’s required checks evolve.

## 5. Commit your work
Stage only the intended files and write a concise message:
```bash
git add <files>
git commit -m "<summary of changes>"
```

## 6. Push the branch to the remote
```bash
git push -u origin $(git branch --show-current)
```
The `-u` flag sets upstream tracking for future pushes/pulls.

## 7. Open a pull request into `main`
Create a PR from your branch targeting `origin/main`. Ensure the PR description summarizes the changes and test results.

## 8. Merge the PR
After reviews and CI pass, merge the PR (squash or merge commit). Pull the updated `main` locally:
```bash
git checkout main
git pull origin main
```

## 9. Clean up
Optionally delete the remote and local feature branch:
```bash
git push origin --delete <branch>
git branch -d <branch>
```
