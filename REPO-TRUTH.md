# REPO-TRUTH.md — EmpireBox Production Layout (as of 2026-06-07)

> **READ THIS FIRST** before doing any work on EmpireBox. Every agent (Hermes, OpenCode, MAX, OpenClaw, Claude Code, Codex) MUST consult this file before reading source, running code, or making changes.

## ⚠️ TL;DR — Canonical layout

| Component | Canonical path | Notes |
|---|---|---|
| **Live backend code** | `/home/rg/empire-repo-main/backend` | FastAPI `app/main.py`, all routers, services |
| **Live frontend code** | `/home/rg/empire-repo-main/empire-command-center` | Next.js 16 app |
| **Live Python venv** | `/home/rg/empire-repo/backend/venv` | (yes, cross-repo — odd but it works) |
| **Live database** | `/home/rg/empire-repo/backend/data/empire.db` | SQLite, also referenced from venv path |
| **Live processes** | `uvicorn` (port 8000), `next-server` (port 3005) | Both running, do NOT restart without coordinating |

## Production truth (verified 2026-06-07)

```bash
# Backend (uvicorn :8000)
cwd: /home/rg/empire-repo-main/backend
cmd: /home/rg/empire-repo/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000
pid: 2122733
imports from: /home/rg/empire-repo-main/backend/app/main.py (md5: 3d5c501ecae83d08d5b22d4f5b3da660)

# Frontend (next-server :3005)
cwd: /home/rg/empire-repo-main/empire-command-center
cmd: next-server (v16.1.6)
pid: 1795744
```

**The live `app/main.py` is in `empire-repo-main`, NOT in `empire-repo`.** The two files have different md5s and different content. Do not assume the older `empire-repo` is in sync with production.

## What is NOT canonical

| Path | Status | Why |
|---|---|---|
| `/home/rg/empire-repo` | **STALE FORK** (kept for venv + DB only) | Different `app/main.py`, no live processes from here. Do NOT edit code in this repo. |
| `/home/rg/empire-repo-v10` | **TEST LANE — DEPRECATED 2026-06-07** | Sandboxed test copy. Archived to `~/archive/empire-repo-v10-DEPRECATED-2026-06-07.tar.gz` (sha256: `8a3da8157f143439f0d6f6612a98eaccc10f42b5ccd37b5b3bf6ee00b761dda7`). See `DEPRECATED.md` in that directory. |
| `/home/rg/empire-repo-stable` | **ARCHIVED — pre-production lane** | Last commit 2026-04-29 ("docs(ops): finalize stable and v10 lane separation"). No unique production work. Archived separately. |
| `/home/rg/empire-repo-feature` | **ARCHIVED — feature branch fork** | Branched off the same line as `empire-repo`. No unique production work. Archived separately. |

## Repo status table (verified 2026-06-07)

| Repo | HEAD | Last touched | Unique commits vs main | Untracked files |
|---|---|---|---|---|
| `empire-repo-main` | (see git log) | 2026-06-01 | — (this IS main) | 0 |
| `empire-repo` | `b7dcb6b` | 2026-06-07 12:38 (heartbeat) | divergent stale fork | 0 |
| `empire-repo-v10` | `da2cbd9` | 2026-05-31 | test-only, no production value | 0 |
| `empire-repo-stable` | `d403372` | 2026-04-29 | none (no shared ancestor with main) | 0 |
| `empire-repo-feature` | `a991a3c` | 2026-05-25 | none (branched from empire-repo lineage) | 0 |

## Rules of engagement

### DO

1. **Read `/home/rg/REPO-TRUTH.md` first** in any new session
2. Default OpenCode cwd is `/home/rg/empire-repo-main` (canonical source)
3. Edit code in `empire-repo-main/backend` and `empire-repo-main/empire-command-center`
4. Reference DB at `/home/rg/empire-repo/backend/data/empire.db` (read-only by default)
5. Restart live services only after coordinating with the user — they may be in active use

### DO NOT

1. ❌ Edit code in `/home/rg/empire-repo` — it is a stale fork, edits will be lost
2. ❌ Touch `/home/rg/empire-repo-v10` — deprecated, archived
3. ❌ Treat `empire-repo/backend/app/main.py` as production truth — it isn't
4. ❌ Move or rename `empire-repo/backend/venv` or `empire-repo/backend/data` — live processes depend on those exact paths
5. ❌ Start new uvicorn/next-server from `empire-repo` paths — collision with live processes
6. ❌ Run `git pull` in `empire-repo` thinking it will update production — it won't

## What "production-critical" runtime pieces are in the stale fork

The `empire-repo` directory still contains:

- `/home/rg/empire-repo/backend/venv/` — the Python venv used by the live uvicorn process
- `/home/rg/empire-repo/backend/data/empire.db` — the live SQLite DB

**These two are production-critical** even though the rest of `empire-repo` is stale. They are kept in `empire-repo` purely as a side-effect of the original venv location. Consolidation (moving the venv + DB to `empire-repo-main`) is **on hold** until you approve it.

## How to update this file

Edit `/home/rg/REPO-TRUTH.md` whenever the production layout changes (e.g., after consolidating `empire-repo-main` ↔ `empire-repo`, or after v10 / stable / feature are removed entirely). Mirror to `/home/rg/empire-repo-main/REPO-TRUTH.md` and `/home/rg/empire-repo/REPO-TRUTH.md`.

## See also

- `/home/rg/empire-repo-v10/DEPRECATED.md` — explicit deprecation marker in v10
- `/home/rg/empire-repo/REPO-TRUTH.md` — copy of this file
- `~/.hermes/context/active-sessions.md` — live session state across all agent surfaces
- `~/.hermes/skills/active-sessions-context/SKILL.md` — how to keep the session dump current
