# PROBE · STALE BADGE / OPENCLAW COMPLETION

**Date:** 2026-09-03
**Repo:** `~/empire-repo-main` · branch `feature/drawing-standard`
**HEAD verified:** `9a931ad` (not `c6a073d` as the dispatch expected — one documentation commit landed after the dispatch was written, per founder note)
**Mode:** READ-ONLY. No fixes. No restarts. No commits other than this file.

---

## Summary

| # | Task | Verdict |
|---|---|---|
| 1 | Stale commit badge | The truth bar's `Commit` value is read **live** via `git rev-parse --short HEAD` from the running backend's CWD. The bar shows the current on-disk HEAD (now `9a931ad`). The dispatch's observation that the bar read `a21fc0f` was either from an earlier session or a stale screenshot — `/max/status` returns the live commit, not a cached one. **However**, the more important finding underneath: the running Python process started at `2026-08-31 23:00:17 EDT` when HEAD was `a21fc0f`, and uvicorn has no `--reload`. **The H81 Phase 2 + 2B fixes are not live in the running process** — they shipped via commits df7ac67/68a532f/dd72de8/a2a5f42/f13b0f4/c6a073d/9a931ad which modified `.py` files *after* process start. `tool_executor.py` / `tool_audit.py` / `guardrails.py` / `router.py` / `runtime_truth_enforcer.py` in the running interpreter are still the `a21fc0f` snapshot. `/max/memory-status` confirms with a freshness warning. **Founder decides when to restart.** |
| 2 | TTS task `4206aecd` | **NO DELIVERABLE EXISTS.** The `result_summary` column for the task contains the literal output of `git status`, not TTS research. The task transitioned `todo → done` in **9 seconds** (not "roughly two minutes" as the dispatch narrative states). No file was written to disk in the 9-second window — the filesystem is clean across repo, memory/, reports/, OpenClaw output dirs, LabDesk output store, Downloads, .claude. The only activity row is `created`; there is no `completed` audit. The task id appears in neither `openclaw_tasks` nor `atlas_tasks` nor `code_mode_tasks` — "OpenClaw auto-executing" was the in-band `auto_executing` flag returned by `create_task` (which only means `_auto_execute_new_task` was scheduled as a background coroutine, not that OpenClaw itself ran). |
| 3 | `✅ Verified` / `✅ High confidence` badges | Neither badge exists as a labelled UI component in the current Command Center source. They are plain text emitted in the model's streamed prose and rendered as part of the chat bubble content. `parseToolBlocks` (the H82 prose-path bug) only fires on ```tool``` fenced blocks, not on `✅ …` patterns. H82 Option α (server-side `strip_tool_blocks` at the four SSE yield sites in `router.py`) **is NOT shipped** — verified by reading `router.py` lines 3653/3701/3799/3805: each yields `safe_chunk` (post-`sanitize_output_streaming`, pre-`strip_tool_blocks`) as-is. Tool blocks still arrive in `msg.content` and the frontend still renders "Tool: <name>" badges per H82 prose path. |

---

## TASK 1 · The stale commit badge

### 1a · Current HEAD

```
$ git rev-parse --short HEAD
9a931ad
$ git log --oneline -8
9a931ad H81 phase 2B: mirror H81 and H82 from agent home to repo memory/
c6a073d H81 phase 2B close: mirror H83/H84/H85 + commit Task B purge report
a2a5f42 H81 phase 2B founder correction: channel grant must be reversed
f13b0f4 H81 phase 2B task D: documentation only, no source
dd72de8 H81 task 3: scan founder input, log detections, never block
68a532f H81 task 2: dangerous-tool execution now auditable
df7ac67 H81 task 1: founder no longer bypasses dangerous-tools PIN gate
581d78d H81 phase 1 map: founder flag /chat/stream divergence
```

Dispatch's expected `c6a073d` is one commit behind `9a931ad`. The mirror-only commit `9a931ad` landed after the dispatch was written.

### 1b · Where the bar value comes from

The truth bar's `Commit ${currentCommit}` pill is rendered in `empire-command-center/app/components/ContinuityPanel.tsx:211`:

```tsx
<Pill label={`Commit ${currentCommit || 'unknown'}`} tone={currentCommit ? 'ok' : 'warn'} />
```

`currentCommit` is set at line 96 from `status?.current_commit?.hash`. `status` is fetched at line 54:

```tsx
const statusRes = await fetch(API + '/max/status', { cache: 'no-store' });
```

The fetch uses `cache: 'no-store'`, so there is no browser-side caching.

The backend endpoint is `GET /api/v1/max/status` at `backend/app/routers/max/router.py:4578`. At line 4594 it calls:

```python
current_commit = _git_commit()
```

`_git_commit` is defined in `backend/app/services/max/runtime_truth_check.py:372`:

```python
def _git_commit() -> dict[str, Any]:
    short   = _run(["git", "rev-parse", "--short", "HEAD"])
    branch  = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    message = _run(["git", "log", "--oneline", "-1"])
    return {"hash": short.get("stdout", ""), ...}
```

`_run` is a `subprocess.run(...)` wrapper. **The commit hash is computed at request time, not at process start, not from a cached file.** When `/max/status` is hit, it shells out `git rev-parse --short HEAD` from the process CWD, which walks up to `~/empire-repo-main/` and reads the current `HEAD`.

### 1c · Is the running process executing pre-H81 code? — **YES**

This is the load-bearing question.

| Signal | Value |
|---|---|
| systemd unit `WorkingDirectory` | `/home/rg/empire-repo-main/backend` |
| systemd unit `ExecStart` | `/home/rg/empire-repo-main/backend/venv/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --timeout-keep-alive 65` (no `--reload`) |
| `ActiveEnterTimestamp` | `Mon 2026-08-31 23:00:17 EDT` |
| `MainPID` | `2145077` |
| Process age | `255,372 s` ≈ **71 hours**, still `active`/`running` |
| Process cwd | `/home/rg/empire-repo-main/backend` (`/proc/2145077/cwd` symlink) |
| Process exe | `/usr/bin/python3.12` (the venv's python, invoked via the unit's full path) |
| `startup_health.json.running_commit_hash` | `a21fc0f` (captured at process start, `recorded_at: 2026-09-01T03:00:23.294468+00:00`) |

The H81 Phase 2 + 2B commits modify backend `.py` source:

```
df7ac67 H81 task 1:  tool_executor.py (+ tests)
68a532f H81 task 2:  tool_audit.py, tool_executor.py
dd72de8 H81 task 3:  guardrails.py (+ tests)
a2a5f42 H81 phase 2B founder correction: docs only
f13b0f4 H81 phase 2B task D: docs only
c6a073d H81 phase 2B close: mirror + purge report
9a931ad H81 phase 2B mirror: memory/ files only
```

`git diff --name-only a21fc0f HEAD -- '*.py'` returns:

```
backend/app/routers/max/router.py
backend/app/services/max/guardrails.py
backend/app/services/max/runtime_truth_enforcer.py
backend/app/services/max/tool_audit.py
backend/app/services/max/tool_executor.py
backend/tests/test_founder_pin_failclosed_hotfix4_2.py
backend/tests/test_h74_empty_channel_default_d45.py
```

All seven `.py` changes touched live modules. **uvicorn was launched with no `--reload`.** Python imports are cached on first load; subsequent `git pull` or new commits do not reload `.py` files into the running interpreter. The 71-hour-old process has the `a21fc0f` bytecode of these modules in memory.

The on-disk `.pyc` for `tool_executor.py` is dated `2026-09-01 12:17` — this is because Python regenerated the `.pyc` when the `.py` mtime advanced, but the running process does not consult the `.pyc` again. The `.bak` file `tool_executor.py.bak-20260831-221952` has md5 `46398db5…`; the current `.py` has md5 `f035a4b3…` — different code, but the running interpreter is still on the `.bak` snapshot.

Live confirmation: `/max/memory-status` reports:

```json
{
  "handoff_freshness": {
    "startup_commit": "a21fc0f",
    "startup_recorded_at": "2026-09-01T03:00:23.294468+00:00",
    "current_commit": "9a931ad",
    "matches": false,
    "warning": "Startup commit does not match current runtime commit (a git pull/fast-forward has happened since startup)."
  }
}
```

This is the load-bearing finding: the running backend has the bypass-stripped PIN gate (post-`df7ac67`), the audit logging (post-`68a532f`), and the founder-input scanning (post-`dd72de8`) — **but only as files on disk**. The actual executing interpreter is the pre-fix code. The dispatch said "if the running process predates those commits, the backend is executing pre-H81 code and none of yesterday's fixes are live." **That condition holds.**

The dispatch narrative said "a Command Center session on 2026-09-03 showed a truth bar reading `Commit a21fc0f`." That value is impossible from a fresh fetch of the live `/max/status` endpoint today — the live endpoint returns `9a931ad`. Possibilities: the observation came from an older session (the bar would have shown whatever HEAD was at that moment), or the screenshot captured a moment before the post-2026-09-01 commits were pushed, or the bar was rendered from a different data path. The current bar reads `9a931ad`; the dispatch's trigger narrative appears to describe a state that has since been superseded.

The founder controls the restart. This probe deliberately does not restart.

### 1d · Working directory and interpreter of the running process

Both confirmed via `/proc/2145077/{cwd,exe}` and the systemd unit `cat`:

- CWD: `/home/rg/empire-repo-main/backend`
- Interpreter: `/home/rg/empire-repo-main/backend/venv/bin/python3` (resolves to `/usr/bin/python3.12`)
- Cmdline: `/home/rg/empire-repo-main/backend/venv/bin/python3 -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --timeout-keep-alive 65`

This matches the canonical-paths guidance. Note also the runtime lane value reported by `/max/status`:

```json
"runtime_lane": {
  "lane": "unknown",
  "branch": "feature/drawing-standard",
  "backend_port": null,
  "frontend_expected_port": null,
  "worktree": "/home/rg/empire-repo-main/backend"
}
```

`lane: "unknown"` and the ports null are odd; `EMPIRE_LANE` and the port env vars should be in scope from the systemd unit. The fallback parser likely just doesn't echo them back in this payload shape.

---

## TASK 2 · The TTS task — does the deliverable exist?

### 2a · The task row

```
DB: /home/rg/empire-data/empire.db
table: tasks
id:          4206aecd
title:       Research TTS setup for EmpireDell
description: Founder wants text-to-speech (voice-out) configured for MAX. Current registry has no
             TTS capability — present tool explicitly excludes TTS/avatar narration. Voice-in is
             working, voice-out is not.

             Scope: research options (Piper / Coqui / OpenAI TTS / ElevenLabs), recommend stack
             for local EmpireDell (Xeon, no GPU for heavy inference), and prep an implementation
             plan.

             Status: research phase. Atlas (CodeForge) can implement once stack is chosen.
status:      done
priority:    low
desk:        lab
assigned_to: NULL
created_by:  max
channel:     system
created_at:  2026-09-03T23:05:14.888911
updated_at:  2026-09-03 23:05:23           ← SQLite CURRENT_TIMESTAMP format (no T, no µs)
completed_at:2026-09-03T23:05:23.866812
result_summary: (see 2a.1)
acceptance_criteria: NULL
tags:        []
metadata:    {}
```

#### 2a.1 · result_summary (full content)

```
On branch feature/drawing-standard
Your branch is ahead of 'origin/feature/drawing-standard' by 8 commits.
  (use "git push" to publish your local commits)

Changes not staged for commit:
  (use "git add <file>..." to update what will be committed)
  (use "git restore <file>..." to discard changes in working directory)
	modified:   max/memory.md

Untracked files:
  (use "git add <file>..." to include in what will be committed)
	backend/app/services/max/runtime_truth_enforcer.py.bak-20260831-225728
	backend/app/services/max/tool_executor.py.bak-20260831-221952
	reference/recovered/r6_woodwork/client_change_order.py.bak-20260830-160109
	reference/recovered/r6_woodwork/invoice_change_order.py.bak-20260830-160229
	reports/2026-08-31_r6_invoice_phase7.md
	reports/2026-08-31_r6_invoice_phase7.png
	uploads/EST-2026-261-mock.pdf

no changes added to commit (use "git add" and/or "git commit" -a)
```

Length: 900 chars. Identical to running `git status` from the backend CWD right now. **This is not a TTS research output. It is the literal stdout of `git status`.**

The `result_summary` schema is `TEXT` — there is no separate deliverable artifact table; whatever string lives in this column IS the deliverable, for tasks created via the desk system. Schema confirmed by `PRAGMA table_info(tasks)`; column 23 is `result_summary TEXT`.

### 2b · What changed status to `done`, and when

| Source | Value |
|---|---|
| `created_at` → `completed_at` | `2026-09-03T23:05:14.888911` → `2026-09-03T23:05:23.866812` = **8.978 seconds elapsed** |
| `task_activity` rows for `4206aecd` | **One row only:** `(id=476, actor='max', action='created', detail='Created by MAX via lab desk chat', created_at='2026-09-03T23:05:14.888911')` |
| `task_activity` total rows in DB | 476. Most recent prior row is id 475 from 2026-08-26 — i.e. this is the only task_activity write in 8 days |
| OpenClaw `openclaw_tasks` row | **No row with id=4206aecd** |
| Atlas `atlas_tasks` row | **No row with id=4206aecd** |
| Code-mode `code_mode_tasks` row in window | **None** (`SELECT … BETWEEN '2026-09-03T23:05:00' AND '2026-09-03T23:06:00'` returned empty) |
| Latest `openclaw_tasks` overall | id `7394`, completed 2026-08-20 — no recent activity at all |

The dispatch narrative said the task returned `done` "roughly two minutes later." Actual elapsed: **9 seconds**. The narrative's wall-clock estimate is off by an order of magnitude.

There is no audit row capturing the `todo → done` transition. `task_activity` got the `created` event but nothing for completion. The single writer of `result_summary` in the live code paths is `_sync_task_to_db` in `backend/app/services/max/desks/desk_manager.py:149-184`, which `UPDATE`s `tasks` directly without inserting into `task_activity`. The pipeline path at `task_pipeline.py:331-335` does write to `task_activity` — but it was not taken (no `pipeline` actor row exists for `4206aecd`).

### 2c · Filesystem writes during the 9-second window

Scan over `/home/rg/empire-repo-main`, `/home/rg/empire-data`, `/home/rg/Empire`, `/home/rg/Reports`, `/home/rg/reports`, `/home/rg/.claude`, `/tmp`, `/home/rg/Downloads` (skipping `.git`, `node_modules`, `venv`, `__pycache__`, `.next`, `public`, `data/drawings`), looking for `mtime ∈ [created_at − 60s, completed_at + 60s]`:

```
window: 1788491114.888911 → 1788491123.866812 (9.0s)
(0 files matched)
```

**Nothing was written to disk in the window.** The result_summary lives only in the SQLite `tasks` table. There is no report file, no MD file, no markdown note, no OpenClaw output artifact, no LabDesk output. The TTS research (option matrix, recommendation, implementation plan) that the task description explicitly requested was never produced.

### 2d · OpenClaw, mechanically

| Signal | Value |
|---|---|
| Port | `7878` |
| Live health probe | `GET http://127.0.0.1:7878/health` → `{"status":"ok","service":"openclaw","version":"1.0.0"}` |
| Backend OpenClaw broker endpoint | `GET /api/v1/openclaw/health` → inlines worker heartbeat + queue stats; gate state `healthy` |
| Queue stats (cumulative) | `{"cancelled": 2, "done": 1443, "failed": 5945, "total": 7390}` — i.e. **7390 is the lifetime total**, not pending items. Pending = `7390 − 1443 − 5945 − 2 = 0`. The dispatch's interpretation of "7390 queued" as pending is incorrect; it is the lifetime cumulative count. |
| Worker heartbeat | `polling`, `age_seconds: 22.293`, `fresh: true`, no current task |
| "OpenClaw auto-executing" provenance | The phrase traces to the `auto_executing` flag returned by the `create_task` tool at `backend/app/services/max/tool_executor.py:735-750`. It is set to `True` when `asyncio.get_running_loop().create_task(_auto_execute_new_task(...))` succeeds — i.e. when the FastAPI handler could schedule a background coroutine. **It does not mean OpenClaw itself executed anything.** The background coroutine calls `desk_manager.submit_task`, which routes to an in-process desk (e.g. LabDesk) and writes the result back via `_sync_task_to_db`. The `:7878` OpenClaw service is not on this code path. |
| `_auto_execute_new_task` → `desk_manager.submit_task` → desk handler | `backend/app/services/max/tool_executor.py:754-801` — calls `desk_manager.submit_task(...)` with a 60s timeout, then `desk_manager._sync_task_to_db(result, desk_id)` writes `status`, `result_summary`, `completed_at` back to `tasks` |
| LabDesk handler for the task | Title contains "Research"; description contains "registry" (substr `try`); `_handle_task` checks `any(w in combined for w in ["experiment","test","try","prototype"])` → `try in "registry"` → **True**, routes to `_handle_experiment`. `_handle_experiment` returns a hardcoded template `f"Experiment started: {task.title}. Sandbox mode — no production impact. Details: {task.description[:200]}. Total experiments: {len(self.experiments)}."`. That template is what should have been stored as `result_summary`. |

Two open questions this probe does not resolve:
1. Why is the actual `result_summary` the literal output of `git status` when neither `_handle_experiment` nor `_handle_general` nor `_handle_voice_test` (which would not match — "experiment"/"test"/"try"/"prototype" check fires first) emits that text? The only `result_summary` writers found in source are `desk_manager._sync_task_to_db` (line 168), `task_pipeline` (lines 331/359/409), and `maintenance_manager` (lines 450/463/489/725). None of them produce `git status` output. There is no code path in the current source that would write `git status` output to `result_summary`. The mismatch between expected template text and observed `git status` text is unexplained by source alone.
2. Whether the running process at `2026-09-03 23:05` had a different code shape than current `lab_desk.py` (process started at `a21fc0f`, but `lab_desk.py` at `a21fc0f` and at `9a931ad` are identical — verified with `git show a21fc0f:backend/app/services/max/desks/lab_desk.py`).

Both are reported, neither is resolved.

### 2e · Does a deliverable exist anywhere? — **NO**

The only artifact associated with task `4206aecd` is the `result_summary` row, which contains `git status` output. The task description explicitly asked for an option matrix (Piper / Coqui / OpenAI TTS / ElevenLabs), a recommendation for EmpireDell's Xeon/no-GPU profile, and an implementation plan. None of that exists. The 9-second elapsed time is consistent with a placeholder completion, not a research artifact.

This matches the dispatch's flagged shape: "a completion claim with no locatable artifact."

---

## TASK 3 · The `✅` badges

### 3a · Where do `✅ Verified` and `✅ High confidence` come from?

Searched the Command Center source for the literal badge labels:

```
$ grep -rn "'Verified'\|'High confidence'" empire-command-center/app/
(no matches in app/components)
```

```
$ grep -rn '"Verified"\|"High confidence"' empire-command-center/app/components
(no matches)
```

The only `✅` occurrences in `ChatScreen.tsx` are:

- Line 223: `setVoiceStatus('✅ Review, then tap Send')` — voice-input status text, not a chat bubble badge
- Line 796: code-mode status — `codeTask.state === 'completed' ? 'Verified / Done' : ...` — code-mode specific, not chat-message prose

Other `✅` patterns:
- `RightPanel.tsx:658`: `✅ {(metrics.verified || 0) + (metrics.high || 0)}` — count, not a per-message label
- `landing/_data.ts:526/540/554`: hardcoded marketing text for the landing page, not chat
- `NotesImporter.tsx:343`: `✅` or `🟡` for customer-match confidence — business-quotes feature, not chat

**Conclusion: `✅ Verified` and `✅ High confidence` are not rendered by any chat-UI badge component. They are plain text emitted by the model inside its streamed response.** They appear inside `cleanContent` (the part of `msg.content` left after `parseToolBlocks` strips ```tool``` blocks) and render as ordinary chat-bubble text. The `✅` emoji and short capitalized label make them *look* like badges, but structurally they are model prose.

### 3b · Are either computed from a real signal?

Neither is computed. There is no `verification_status` or `confidence` SSE event in the streaming response. The only structured events the backend emits are `text`, `tool_call`, `tool_result`, and similar — verified by reading `router.py` yield sites 3653/3701/3799/3805 and the broader SSE emission patterns in `tool_executor.py` and `router.py`. The `✅ Verified` / `✅ High confidence` strings come from the model's output text and inherit zero signal from the backend's tool-execution truth state.

The H80 / H82 doctrine ("no success claims without a real tool result / proof object") applies: a model writing `✅ Verified` after a `db_query` failure has no signal backing that text.

### 3c · Current state of H82 Option α

**Not shipped.** Verified by reading the four SSE yield sites in `router.py`:

| Line | Path | What it yields |
|---|---|---|
| `3653` | Main chat-stream text chunk from `ai_router.chat_stream` | `safe_chunk` (post-`sanitize_output_streaming`, **pre-`strip_tool_blocks`**) |
| `3701` | Tool-block-error recovery text path | `full_response` (no strip) |
| `3799` | Text gap emitted before followup stream | literal `"\n\n"` (no strip needed) |
| `3805` | Followup stream text chunks | `safe_chunk` (post-`sanitize_output_streaming`, **pre-`strip_tool_blocks`**) |

`strip_tool_blocks` exists at `backend/app/services/max/tool_executor.py:353` and IS applied at:

- `router.py:1295` inside `_sanitize_internal_leakage_text` (response post-processing)
- `router.py:2942, 3078, 3096, 3793, 3817, 3827, 3896` for `conversation_tracker.add_message` writes (history persistence)

**None** of the four SSE `text` event yield sites call `strip_tool_blocks(safe_chunk)` before yielding. The frontend's `parseToolBlocks(msg.content)` (ChatScreen.tsx:601-602) therefore still finds tool blocks in `msg.content` for every chat message, and the "Tool: <name>" badge still renders per the H82 prose path. H82 Option α remains a Phase 3 candidate.

---

## Files referenced

### Source
- `backend/app/services/max/runtime_truth_check.py:372` — `_git_commit`
- `backend/app/services/max/control_plane.py:67-69` — `_repo_root` (resolves to `~/empire-repo-main`)
- `backend/app/services/max/control_plane.py:107-114` — broker reads git + ports
- `backend/app/services/max/startup_health.py:46-77` — startup record writers
- `backend/app/routers/max/router.py:4578-4624` — `/max/status` endpoint
- `backend/app/routers/max/router.py:6017-6030` — `/max/memory-status` endpoint
- `backend/app/routers/max/router.py:3653, 3701, 3799, 3805` — SSE text yield sites (H82 Option α not applied)
- `backend/app/services/max/tool_executor.py:735-801` — `_auto_execute_new_task` (the "auto-executing" path)
- `backend/app/services/max/desks/desk_manager.py:86-184` — `submit_task` + `_sync_task_to_db` (only result_summary writer in the desk path)
- `backend/app/services/max/desks/lab_desk.py:36-138` — LabDesk handlers (the TTS task should have produced a template string)
- `backend/app/services/max/tool_executor.py:4172-4250` — `_enforce_deliverable_gate` (H76 gate; passed for the TTS task because its `result_summary` is non-empty and not a "No available provider" string)
- `backend/app/services/max/openclaw_gate.py` — OpenClaw broker (port `:7878`)
- `backend/app/services/openclaw_worker.py:346-369` — `_git_changed_files` (uses `git status --porcelain`, not full `git status`)

### Frontend
- `empire-command-center/app/components/ContinuityPanel.tsx:54, 96, 211` — bar's commit pill
- `empire-command-center/app/components/screens/ChatScreen.tsx:601-668` — `parseToolBlocks` + tool-card rendering

### Systemd
- `~/.config/systemd/user/empire-backend.service` — `WorkingDirectory=/home/rg/empire-repo-main/backend`, ExecStart with full venv path, no `--reload`

### DB
- `/home/rg/empire-data/empire.db` — `tasks`, `task_activity`, `openclaw_tasks`, `atlas_tasks`, `code_mode_tasks`
- `/home/rg/empire-data/tool_audit.db` — `tool_executions`

### Live evidence
- `startup_health.json`: `running_commit_hash=a21fc0f`, `recorded_at=2026-09-01T03:00:23.294468+00:00`
- `/max/memory-status`: warning `"Startup commit does not match current runtime commit (a git pull/fast-forward has happened since startup)."`
- `/proc/2145077`: cwd `/home/rg/empire-repo-main/backend`, exe `/usr/bin/python3.12`, etimes `255372s`

---

## Findings the founder should see first

1. **The running backend is executing pre-H81-fix code** even though the disk is at post-fix `9a931ad`. uvicorn has no `--reload`; process started `2026-08-31 23:00:17 EDT` and has been running 71 hours continuously through all seven H81 Phase 2 + 2B commits. A restart is needed to activate the bypass-stripped PIN gate, the dangerous-tool audit, and the founder-input scanning. `/max/memory-status` reports the mismatch explicitly. Founder decides when.

2. **TTS task `4206aecd` is a fabrication-shape completion**: 9-second elapsed, no filesystem writes, no audit row beyond `created`, no entry in `openclaw_tasks`/`atlas_tasks`/`code_mode_tasks`. The `result_summary` column contains the literal output of `git status`, not TTS research. The source code path that *should* have produced this task (`create_task` → `_auto_execute_new_task` → `desk_manager.submit_task` → LabDesk → `_sync_task_to_db`) does not contain any code that emits `git status` output. The mismatch between expected template string and observed `git status` text is real and unexplained by source alone — worth a follow-up dispatch to determine which code path wrote the result_summary column.

3. **`✅ Verified` and `✅ High confidence` are model prose, not signal-backed badges.** They render as ordinary text inside the chat bubble. The H80 / H82 doctrine already flags that model-emitted confidence claims without proof objects are unsafe; this is the surface where that failure shows up in the UI. Fixing the *display* requires H82 Option α (server-side `strip_tool_blocks` at the four SSE yield sites in `router.py`) to be shipped — confirmed still un-shipped. Fixing the *claim* requires the deliverable gate / truth gate to inspect prose for `Verified` / `High confidence` claims and downgrade them when no proof object backs them — that is its own design decision and is out of scope for this probe.
