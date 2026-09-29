# REPO-TRUTH.md — EmpireBox Production Layout (as of 2026-06-07)

> **READ THIS FIRST** before doing any work on EmpireBox. Every agent (Hermes, OpenCode, MAX, OpenClaw, Claude Code, Codex) MUST consult this file before reading source, running code, or making changes.

## ⚠ CORRECTION NOTICE (2026-08-24) — READ BEFORE THE LAYOUT BELOW

The layout sections below describe `~/empire-repo` as a stale fork. That
description is **wrong** as of 2026-08-24. The corrected picture:

`~/empire-repo` is the main worktree (not a stale fork). It owns the shared
git object store at `~/empire-repo/.git`, the live venv at
`~/empire-repo/backend/venv/`, and the live OpenClaw service on port 7878 —
all of which still receive data writes. The sibling checkout
`~/empire-repo-main` is on the same `feature/drawing-standard` branch.

Two open items make this unsafe to act on:
- **H72** — data writes still land in `~/empire-repo/backend/data/` while the
  backend runs from `~/empire-repo-main`. H57 Phase 3 claimed closure at
  `59d356d`/`3b34a86`; D23 shows writes continuing. Cross-reference H57; do not
  reopen.
- **H73** — `backend/app/services/drawing/canonical_path.py:133-152` hardcodes
  `home/"empire-repo"` as a `bad_roots` entry and refuses every sub-path of the
  tree that owns the object store. Live hazard. Code lane, not this dispatch.

The two-repo comparison table further down still encodes the wrong framing
and needs its own correction lane. **Neutralised lines below are minimum
safety edits, not the final state.**

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
| `/home/rg/empire-repo` | **MAIN WORKTREE** (was mislabelled "stale fork" pre-2026-08-24; correction is the notice at top of file) | Owns the shared git object store, the live venv, and the live OpenClaw service. Acting on it as if it were a stale tree destroys every local branch, lane and stash. See H72/H73. |
| `/home/rg/empire-repo-v10` | **TEST LANE — DEPRECATED 2026-06-07** | Sandboxed test copy. Archived to `~/archive/empire-repo-v10-DEPRECATED-2026-06-07.tar.gz` (sha256: `8a3da8157f143439f0d6f6612a98eaccc10f42b5ccd37b5b3bf6ee00b761dda7`). See `DEPRECATED.md` in that directory. |
| `/home/rg/empire-repo-stable` | **ARCHIVED — pre-production lane** | Last commit 2026-04-29 ("docs(ops): finalize stable and v10 lane separation"). No unique production work. Archived separately. |
| `/home/rg/empire-repo-feature` | **ARCHIVED — feature branch fork** | Branched off the same line as `empire-repo`. No unique production work. Archived separately. |

## Repo status table (verified 2026-06-07)

| Repo | HEAD | Last touched | Unique commits vs main | Untracked files |
|---|---|---|---|---|
| `empire-repo-main` | (see git log) | 2026-06-01 | — (this IS main) | 0 |
| `empire-repo` | `b7dcb6b` | 2026-06-07 12:38 (heartbeat) | shared git object store (the "main worktree" — pre-2026-08-24 misdiagnosis as "divergent stale fork" was wrong) | 0 |
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

1. ❌ Edit code in `/home/rg/empire-repo` — it is the **main worktree**, and edits
   there are NOT lost (it owns the shared git object store); however, the active
   branch is `feature/drawing-standard` and the canonical checkout for new work
   is `~/empire-repo-main` (sibling). Edits in `~/empire-repo` will be visible
   to `~/empire-repo-main` because they share the object store — but they will
   also be visible to every other linked worktree on the box, which is the
   actual reason to prefer `empire-repo-main` for code edits. (Pre-2026-08-24
   read of this rule said "edits will be lost" — wrong; the reason is shared-
   visibility, not loss.)
2. ❌ Touch `/home/rg/empire-repo-v10` — deprecated, archived
3. ❌ Treat `empire-repo/backend/app/main.py` as production truth — it isn't
4. ❌ Move or rename `empire-repo/backend/venv` or `empire-repo/backend/data` — live processes depend on those exact paths
5. ❌ Start new uvicorn/next-server from `empire-repo` paths — collision with live processes
6. ❌ Run `git pull` in `empire-repo` thinking it will update production — it won't

## What production-critical runtime pieces are in the main worktree

The `empire-repo` directory (which IS the main worktree, not a stale fork — see
correction notice at top of file) currently hosts:

- `/home/rg/empire-repo/backend/venv/` — the Python venv used by the live uvicorn process
- `/home/rg/empire-repo/backend/data/empire.db` — the live SQLite DB
- `/home/rg/empire-repo/.git/` — the shared git object store that every
  linked worktree on the box (including `empire-repo-main`) reads from

These are production-critical **because they own the runtime**, not because
they are leftovers. Migration of the venv + DB to `empire-repo-main` is the
remedy for the data-writes-still-landing finding (H72); removal of the tree is
**not** on the table and would destroy the object store.

## How to update this file

Edit `/home/rg/REPO-TRUTH.md` whenever the production layout changes (e.g., after consolidating `empire-repo-main` ↔ `empire-repo`, or after v10 / stable / feature are removed entirely). Mirror to `/home/rg/empire-repo-main/REPO-TRUTH.md` and `/home/rg/empire-repo/REPO-TRUTH.md`.

## See also

- `/home/rg/empire-repo-v10/DEPRECATED.md` — explicit deprecation marker in v10
- `/home/rg/empire-repo/REPO-TRUTH.md` — copy of this file
- `~/.hermes/context/active-sessions.md` — live session state across all agent surfaces
- `~/.hermes/skills/active-sessions-context/SKILL.md` — how to keep the session dump current
