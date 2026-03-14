---
name: empire-git
description: Git operations for the Empire repo. Commit, push, branch management, conflict resolution. Use for any version control task.
version: 1.0.0
metadata:
  openclaw:
    emoji: "🔀"
    requires:
      bins:
        - git
---

# Empire Git Operations

## Repo Info
- Path: ~/empire-repo
- Remote: github.com/r22gir/Empire (private)
- Branch: main (always work on main unless told otherwise)
- GitHub user: r22gir

## Before Any Git Operation
```bash
cd ~/empire-repo
git status
git log --oneline -5
```

## Commit Convention
Format: `type: short description`

Types:
- `feat:` new feature
- `fix:` bug fix
- `clean:` data cleanup, remove test data
- `wire:` connecting pages/routes/navigation
- `social:` social media related
- `refactor:` code restructuring
- `docs:` documentation

Examples:
- `fix: remove test customers from workroom DB`
- `feat: wire CraftForge dashboard to backend endpoints`
- `wire: connect SocialForge content calendar to API`
- `clean: purge fake quote data, reset sequences`

## Common Operations

### Stage and commit specific files
```bash
cd ~/empire-repo
git add path/to/changed/files
git commit -m "type: description"
git push origin main
```

### Stage all changes
```bash
cd ~/empire-repo
git add -A
git commit -m "type: description"
git push origin main
```

### Check what's uncommitted
```bash
cd ~/empire-repo
git status --short
git diff --stat
```

## Rules
- NEVER force push (`git push -f`)
- NEVER rebase main
- Commit related changes together, not everything at once
- Write clear commit messages — the founder reads these
- If there are merge conflicts, STOP and report them
