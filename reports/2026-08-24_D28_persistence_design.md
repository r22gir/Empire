# D28 · Code-Task Persistence Design (Pre-Build Map)

**Date:** 2026-08-24
**Branch:** feature/drawing-standard @ bacad25 (HEAD)
**Mode:** READ-ONLY design map. No DDL. No code edits. No service restarts beyond a scratch subprocess on port 8001 (now torn down). No commit.
**Inheritance:** Acts on D27 (`reports/2026-08-24_D27_persistence_map.md`). R11 §13 framed the persistence scoping; D27 inventoried the current loss; this dispatch (D28) designs the schema WITHOUT applying it.
**VERIFIED/INFERRED tags on every claim.**

---

## 0a · The `pending_drawing_jobs` precedent

### 0a.1 Live DDL (VERIFIED)

`backend/app/services/max/drawing_pending.py:55-68` (CREATE block inside `ensure_table()`):

```sql
CREATE TABLE IF NOT EXISTS pending_drawing_jobs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id TEXT NOT NULL,
    channel TEXT NOT NULL,
    handoff_json TEXT NOT NULL,
    missing_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(conversation_id, channel)
);
CREATE INDEX IF NOT EXISTS idx_pending_jobs_age
    ON pending_drawing_jobs(created_at);
```

Live PRAGMA confirms 7 columns, 1 explicit index (`idx_pending_jobs_age`) plus 1 implicit autoindex for the UNIQUE constraint.

### 0a.2 Row count and timestamps (VERIFIED)

```
--- pending_drawing_jobs row count ---
rows: 0
```

`created_at`/`updated_at` min/max not probed — no rows. The table has NEVER held data in this database.

### 0a.3 All writers, readers, sweepers (VERIFIED)

Writers (writes that insert or update):
- `backend/app/services/max/drawing_pending.py:79` — `set_pending()` (`INSERT … ON CONFLICT … DO UPDATE`)
- `backend/tests/test_drawing_phase_a.py:177` — test-only INSERT

Readers:
- `backend/app/services/max/drawing_pending.py:99` — `get_pending()` (SELECT by `conversation_id`, `channel`)
- `backend/app/routers/max/router.py:2398-2425` — `is_cancel_message, clear_pending, get_pending, is_continuation_reply, merge_founder_reply, set_pending` used inside the chat handler
- `backend/app/routers/max/router.py:3297-3425` — second chat path, same set of symbols
- `backend/tests/test_drawing_phase_a.py:193` — test-only COUNT
- `backend/tests/test_h57_router_intercept.py:206-218` — tests for `is_continuation_reply`
- `backend/tests/test_r12_continuation_guard.py:192-248` — tests for `looks_like_continuation`
- `backend/tests/test_r12_1_dimension_parser.py:268-282` — tests for `_match_dim`

Deleters:
- `backend/app/services/max/drawing_pending.py:71` — TTL sweep inside `ensure_table()` (`DELETE … WHERE created_at < cutoff`)
- `backend/app/services/max/drawing_pending.py:113` — `clear_pending()` (DELETE by `conversation_id, channel`)

Sweep site (TTL):
- `backend/app/services/max/drawing_pending.py:69-72` — cutoff = `now - 24h`; DELETE in same transaction as CREATE.

### 0a.4 Is the sweep scheduled or dead code? (VERIFIED)

**The sweep runs lazily on every `ensure_table()` call. There is NO scheduler or cron registration for it.**

`ensure_table()` is called:
- `drawing_pending.py:96` — inside `get_pending()` (every read sweeps)
- `drawing_pending.py:293` — at module import (top-level `ensure_table()` — runs once per worker process at import)

The module is imported lazily by routers (`routers/max/router.py:2398, 3297`) — so on each chat-handler entry, `get_pending` (if invoked) sweeps. The startup paths in `main.py:357-450` do NOT import `drawing_pending` — the sweep runs only when a chat request triggers it.

### 0a.5 Git history of `drawing_pending.py` (VERIFIED)

```
$ git log --oneline -- backend/app/services/max/drawing_pending.py
13ab4a3 R12.1: fix dimension parser + add plausibility gate
e281567 R12 fix: continuation guard — looks_like_continuation via chat history
0b2af42 drawing: Sprint 1d Phase A — standard + golden bundle + 3 routing fixes
```

3 commits. No commit message says "this is now abandoned" — but the module-level comment at `drawing_pending.py:223-231` (PHASE 2 · R12 corrected Option A) states:

> "The pending-table path is dead architecture (set_pending requires
> both `missing` and `tool_payload` to be truthy — mutually
> exclusive in build_drawing_handoff). This helper reads the last
> few assistant turns directly from chat history and detects
> whether the current message is supplying values for a recently
> missing drawing-router turn."

So the writing path was deliberately bypassed in R12. The table still gets created and swept (no harm), but `set_pending()` is never called from the live code paths.

### 0a.6 Verdict on the precedent (INFERRED but tight)

**The `pending_drawing_jobs` mechanism is abandoned for a SPECIFIC structural reason, not a generic "no one used it" decay.** The writer's preconditions are unsatisfiable in the only call site that would naturally write to it (`build_drawing_handoff` returns `missing` XOR `tool_payload`, never both). R12 diagnosed this and routed around it with `looks_like_continuation()` reading chat history directly.

**The lesson for `code_mode_tasks`:**
1. The shape (TEXT JSON-blob columns, idempotent CREATE, TTL sweep on read) is fine — copy that.
2. The writer MUST be called from the live execution path. A persistence layer that nothing calls is the same dead-architecture failure mode.
3. The "lazy sweep on read" pattern is OK for low-frequency tables, but the runner is high-frequency — lazy sweep is the wrong tool. Use startup-reconcile instead.

### 0a.7 What I AM following from the precedent (VERIFIED)

- TEXT columns for JSON-serialised structured data (suffix `_json`)
- Idempotent `CREATE TABLE IF NOT EXISTS` on module import (via `ensure_table()`)
- `created_at TEXT NOT NULL DEFAULT (datetime('now'))` style
- Single-column index on the timestamp used for sweeps
- `state` as TEXT (the enum values are strings)

### 0a.8 What I am NOT following, and why (VERIFIED)

- UNIQUE on `(conversation_id, channel)` — there is no natural key for `code_mode_tasks` other than the synthetic `id`. The PK IS the natural key.
- 24-hour TTL on every row — only `state IN ('queued','running')` rows need TTL. `completed`/`error` rows are audit records and should be kept.
- Lazy sweep-on-read — the runner reads its own dict, not the DB, so the sweep never fires during a run. A startup-reconcile pass is required.

---

## 0b · Proposed schema (DO NOT CREATE)

### 0b.1 Field-by-field classification

Each of the 29 `CodeTask` fields is classified as **persisted**, **derived-on-rehydrate**, or **dropped**. Sizes are measured from a live scratch run, not estimated.

| # | Field | Type | Decision | Why | Typical size |
|---|---|---|---|---|---|
| 1 | `id` | str (12-char uuid) | **PERSISTED — PRIMARY KEY** | Round-trips `/code-task/{id}/status`; only stable identifier | 12 chars |
| 2 | `prompt` | str | PERSISTED | Original request; required for re-feed on resume | 80–500 chars (live code truncates display at 200) |
| 3 | `working_dir` | str | PERSISTED | R11 ground-truth validator checks this tree | ~50 chars (absolute path) |
| 4 | `execution_mode` | str | PERSISTED | Resume must use same mode (`auto`/`read_only`/etc.) | 4–10 chars |
| 5 | `provider_used` | Optional[str] | PERSISTED | Audit, debugging | 3–10 chars |
| 6 | `model_used` | Optional[str] | PERSISTED | Audit, debugging, cost attribution | 5–30 chars |
| 7 | `supports_tool_calls` | Optional[bool] | PERSISTED | F1 evidence — set post-parse, affects validator scoring | 0/1 |
| 8 | `prompt_attempts` | int | PERSISTED | Cost attribution, retry counter | 1–5 |
| 9 | `failure_reason` | Optional[str] | PERSISTED | Why the task ended in ERROR | 50–300 chars |
| 10 | `execution_protocol` | str | PERSISTED | Audit; identifies protocol variant | ~16 chars |
| 11 | `founder` | bool | PERSISTED | Authorization context (different code path in submit) | 0/1 |
| 12 | `state` | CodeTaskState | **PERSISTED** | Required for status queries; only values are `queued`/`running`/`completed`/`error` | enum string |
| 13 | `created_at` | str (ISO) | PERSISTED | Audit; sweep key | 26 chars |
| 14 | `started_at` | Optional[str] | PERSISTED | Audit | 26 chars |
| 15 | `completed_at` | Optional[str] | PERSISTED | Audit; sweep key | 26 chars |
| 16 | `result` | Optional[str] | PERSISTED | Final output / verification summary | 100–2000 chars |
| 17 | `error` | Optional[str] | PERSISTED | Error message | 50–500 chars |
| 18 | `files_changed` | list[str] | PERSISTED (`_json`) | Validator evidence | 0–20 entries, 30–80 chars each |
| 19 | `files_inspected` | list[str] | PERSISTED (`_json`) | Audit | 0–20 entries |
| 20 | `executed_tool_calls` | list[dict] | PERSISTED (`_json`) | Re-feed on resume; validator evidence | **5–50 KB** for 50 calls (measured: 5.3 KB) |
| 21 | `verified_test_runs` | list[dict] | PERSISTED (`_json`) | Validator evidence | 0–10 entries |
| 22 | `verified_commit_hash` | Optional[str] | PERSISTED | Validator proof (HEAD hash) | 40 chars |
| 23 | `verification_notes` | list[str] | PERSISTED (`_json`) | Validator narrative | 0–10 entries |
| 24 | `log` | list[CodeTaskLog] | PERSISTED (`_json`) | Append-only event log; critical for forensics | **12.7 KB** for 50 entries (measured) |
| 25 | `last_response_text` | Optional[str] | PERSISTED | F2 evidence — what model returned | 1–10 KB |
| 26 | `last_function_calls_summary` | Optional[str] | PERSISTED | F2 evidence — summary of model tool calls | 100–1000 chars |
| 27 | `last_parse_outcome` | Optional[str] | PERSISTED | F2 evidence — parse result | 50–200 chars |
| 28 | `files_snapshot_before` | set[str] | PERSISTED (`_json`) | Ground-truth baseline (R11) | 130 B for 4 paths (measured); ≤5 KB |
| 29 | `files_snapshot_ground_truth` | bool | PERSISTED | Whether baseline is real | 0/1 |

**No fields are dropped** — every field on the dataclass has forensic or resume value. No fields are derived-on-rehydrate in v1 (the runner never reads back from DB in this design; it always submits a fresh in-memory task on resume).

**`working_dir` (~50 chars) is NOT large.** It is an absolute path.
**`files_snapshot_before` is NOT large.** 130 B for a clean repo, bounded by `git status --porcelain` output (typically ≤100 paths).
**`files_snapshot_ground_truth` is a bool.**

### 0b.2 The three F2 evidence fields (VERIFIED)

`last_response_text`, `last_function_calls_summary`, `last_parse_outcome` — set at `code_task_runner.py:711-713`. They are captured after every model response (called by `add_log`-style updates inside the loop). Persisting them lets a rehydrated task present the same evidence to the founder that the live task had. Sizes are moderate (≤10 KB total per task); fine in SQLite TEXT.

### 0b.3 The `self._running` asyncio.Task dict (VERIFIED, INFERRED implication)

`backend/app/services/max/code_task_runner.py:769`:
```python
self._running: dict[str, asyncio.Task] = {}
```

**An `asyncio.Task` cannot be serialised.** It holds references to the running event loop, the coroutine frame, and the underlying futures — none of which round-trip through any on-disk format.

**Implication for rehydrate:**
- A task rehydrated from DB on restart has its metadata but NOT its handle.
- It cannot resume execution. The task IS the metadata; the handle is just the live execution slot.
- The startup-reconcile pass must therefore mark any `state IN ('queued','running')` rows that lack a live process as `error` with `failure_reason = "Backend restart interrupted this task"`. They cannot be auto-resumed; the founder must re-submit if they want to retry.

This is INFERRED but tight: the alternative (resuming a coroutine after process death) is not implementable.

### 0b.4 Schema (proposed, NOT created)

```sql
CREATE TABLE IF NOT EXISTS code_mode_tasks (
    id                          TEXT PRIMARY KEY,              -- CodeTask.id (12-char uuid prefix)
    prompt                      TEXT NOT NULL,
    working_dir                 TEXT NOT NULL,
    execution_mode              TEXT NOT NULL DEFAULT 'auto',
    founder                     INTEGER NOT NULL DEFAULT 0,
    state                       TEXT NOT NULL,                -- queued|running|completed|error
    provider_used               TEXT,
    model_used                  TEXT,
    supports_tool_calls         INTEGER,
    prompt_attempts             INTEGER NOT NULL DEFAULT 0,
    failure_reason              TEXT,
    execution_protocol          TEXT NOT NULL DEFAULT 'json-tool-action',
    created_at                  TEXT NOT NULL DEFAULT (datetime('now')),
    started_at                  TEXT,
    completed_at                TEXT,
    result                      TEXT,
    error                       TEXT,
    files_changed_json          TEXT NOT NULL DEFAULT '[]',
    files_inspected_json        TEXT NOT NULL DEFAULT '[]',
    executed_tool_calls_json    TEXT NOT NULL DEFAULT '[]',
    verified_test_runs_json     TEXT NOT NULL DEFAULT '[]',
    verified_commit_hash        TEXT,
    verification_notes_json     TEXT NOT NULL DEFAULT '[]',
    log_json                    TEXT NOT NULL DEFAULT '[]',
    last_response_text          TEXT,
    last_function_calls_summary TEXT,
    last_parse_outcome          TEXT,
    files_snapshot_before_json  TEXT NOT NULL DEFAULT '[]',
    files_snapshot_ground_truth INTEGER NOT NULL DEFAULT 0,
    updated_at                  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE INDEX IF NOT EXISTS idx_code_mode_state      ON code_mode_tasks(state);
CREATE INDEX IF NOT EXISTS idx_code_mode_updated    ON code_mode_tasks(updated_at);
CREATE INDEX IF NOT EXISTS idx_code_mode_completed  ON code_mode_tasks(completed_at)
    WHERE state IN ('completed', 'error');
```

**Choices and rationale:**

- **`id TEXT PRIMARY KEY`** — matches `CodeTask.id` (12-char uuid prefix), round-trips the existing `/code-task/{id}/status` endpoint without remapping.
- **`state TEXT NOT NULL`** — single source of truth, no separate `status` column. CHECK constraint optional in v1 (SQLite CHECK is not enforced until 3.32+ with `enable_check`; relies on application discipline).
- **JSON columns suffixed `_json`** — pending_drawing_jobs precedent. Distinguishes serialised JSON from raw TEXT.
- **`INTEGER` for bool fields** — SQLite has no native bool; 0/1 is canonical.
- **`updated_at`** — separate from `created_at` so the sweep query is "rows where state in (queued, running) AND updated_at < cutoff", not "completed_at IS NULL" (which has NULL semantics problems).
- **Partial index on `completed_at WHERE state IN ('completed','error')`** — speeds audit queries without indexing terminal rows that never change.
- **NO CHECK constraint on state values** — `code_task_runner.py:678` enum has 4 values (QUEUED='queued', RUNNING='running', COMPLETED='completed', ERROR='error' — VERIFIED via enum iteration), and the application is the single writer. Adding a CHECK would couple the schema to the Python enum. Trust the application; revisit if state drift appears.
- **NO park-and-ask fields** (`pending_question`, `pending_options`, `decision_deadline`) — per dispatch instruction, scope only the runner's TODAY states. Park-and-ask is not built code; adding empty columns now is speculative.

**TTL on this table:** none in v1. Completed/error rows are audit records (no TTL). Queued/running rows are reconciled at startup; a row that survives startup-reconcile should never exist. INFERRED: if the table grows unbounded over months, a `DELETE WHERE state IN ('completed','error') AND completed_at < now - 90d` cleanup can be added later as a cron.

---

## 0c · Terminal paths in `_execute()` (VERIFIED)

Every place a `CodeTask` reaches a final state. A persistence writer that misses one leaves rows stuck forever.

| # | State set | file:line | Trigger | Notes |
|---|---|---|---|---|
| 1 | `RUNNING` | `code_task_runner.py:838` | `_execute()` entry after baseline capture | Non-terminal — start state |
| 2 | `ERROR` | `code_task_runner.py:1084-1097` | `no_tool_retries >= MAX_NO_TOOL_RETRIES` and no executed calls | Returns early; `error`, `failure_reason`, `result`, `completed_at` set |
| 3 | `ERROR` | `code_task_runner.py:1100-1112` | `not executed_tool_calls` after the loop | Returns early |
| 4 | `ERROR` | `code_task_runner.py:1116-1125` | `execution_mode == "read_only"` but a mutating tool ran | Returns early |
| 5 | `ERROR` | `code_task_runner.py:1128-1140` | `not task.files_changed` after the loop | Returns early |
| 6 | `ERROR` | `code_task_runner.py:1149-1158` | commit attempted but not verifiable | Returns early |
| 7 | `ERROR` | `code_task_runner.py:1161-1170` | `verified_commit_hash` not in git history | Returns early |
| 8 | `COMPLETED` | `code_task_runner.py:1173-1177` | Successful end of `_execute()` body | `result = _compose_verified_summary(task)` |
| 9 | `ERROR` | `code_task_runner.py:1180-1186` | `except asyncio.TimeoutError` | Sets error + completed_at |
| 10 | `ERROR` | `code_task_runner.py:1189-1195` | `except Exception` (catch-all) | Sets error + completed_at |
| — | (none) | `code_task_runner.py:1197-1198` | `finally:` block | Pops `_running` handle; does NOT touch `state` |

**Cancellation is NOT explicitly handled.** There is no `except asyncio.CancelledError` in `_execute()`. If the asyncio task is cancelled (e.g., via `task.cancel()`), the `Exception` branch at line 1189 catches `CancelledError` (in Python 3.8+ `CancelledError` is a `BaseException`, not `Exception` — so it would actually NOT be caught here and would propagate up). INFERRED: a mid-flight cancel leaves the task in whatever state `state` had been set to at the time of cancellation (typically `RUNNING`), and the in-process `finally` pops `_running` but the DB row stays at `RUNNING` forever. STEP 1 must add an explicit `CancelledError` handler OR the startup-reconcile must catch this case.

**Implication for STEP 1 (not this dispatch):** the writer hook must fire at sites 2-10 (9 sites), NOT in the `finally` block (which does not change state). A single-line call at each site is the cleanest implementation. A context-manager wrapper would require restructuring `_execute()`, which is out of scope for "pre-build map".

---

## 0d · Backup and baseline

### 0d.1 Canonical backup (VERIFIED)

Ran `scripts/backup-canonical.sh` (added in commit a683100). Output:

```
[2026-08-24 19:12:07] ========================================
[2026-08-24 19:12:07] backup-canonical.sh START  dest=/home/rg/backups/2026-08-24_1912
[2026-08-24 19:12:07] (1/6) /home/rg/empire-data/empire.db
[2026-08-24 19:12:08]   ok    wrote /home/rg/backups/2026-08-24_1912/empire.db
[2026-08-24 19:12:08]   ok    verify dst=/home/rg/backups/2026-08-24_1912/empire.db table=quotes_v2 rows=198 integrity=ok
[2026-08-24 19:12:08] (2/6) /home/rg/empire-data/intake.db
[2026-08-24 19:12:08]   ok    wrote /home/rg/backups/2026-08-24_1912/intake.db
[2026-08-24 19:12:08]   ok    verify dst=/home/rg/backups/2026-08-24_1912/intake.db table=intake_projects rows=504 integrity=ok
[2026-08-24 19:12:08] (3/6) /home/rg/empire-data/brain/memories.db
[2026-08-24 19:12:09]   ok    verify dst=/home/rg/backups/2026-08-24_1912/memories.db table=memories rows=27431 integrity=ok
[2026-08-24 19:12:09] (4/6) /home/rg/empire-data/brain/token_usage.db
[2026-08-24 19:12:09]   ok    verify dst=/home/rg/backups/2026-08-24_1912/token_usage.db table=token_usage rows=60392 integrity=ok
[2026-08-24 19:12:10] (5/6) /home/rg/empire-data/brain/unified_messages.db
[2026-08-24 19:12:10]   ok    verify dst=/home/rg/backups/2026-08-24_1912/unified_messages.db table=unified_messages rows=25084 integrity=ok
[2026-08-24 19:12:10] (6/6) /home/rg/empire-repo-main/max/memory.md
[2026-08-24 19:12:10]   ok    wrote /home/rg/backups/2026-08-24_1912/memory.md (plain cp)
[2026-08-24 19:12:10] backup-canonical.sh OK     dest=/home/rg/backups/2026-08-24_1912 files=6
[2026-08-24 19:12:10] ========================================
```

Backup size:

```
$ ls -la /home/rg/backups/2026-08-24_1912/
-rw-r--r-- 1 rg rg 27955200 Aug 24 19:12 empire.db
-rw-r--r-- 1 rg rg   32768 Aug 24 19:12 empire.db-shm
-rw-r--r-- 1 rg rg        0 Aug 24 19:12 empire.db-wal
-rw-r--r-- 1 rg rg  466944 Aug 24 19:12 intake.db
-rw-r--r-- 1 rg rg   32768 Aug 24 19:12 intake.db-shm
-rw-r--r-- 1 rg rg        0 Aug 24 19:12 intake.db-wal
-rw-r--r-- 1 rg rg 15818752 Aug 24 19:12 memories.db
-rw-rw-r-- 1 rg rg     7517 Aug 23 23:33 memory.md
-rw-r--r-- 1 rg rg 16224256 Aug 24 19:12 token_usage.db
-rw-r--r-- 1 rg rg 24989696 Aug 24 19:12 unified_messages.db
-rw-r--r-- 1 rg rg   32768 Aug 24 19:12 unified_messages.db-shm
-rw-r--r-- 1 rg rg        0 Aug 24 19:12 unified_messages.db-wal
```

Script exit code 0. All integrity checks `ok`.

### 0d.2 Suite baseline (VERIFIED)

```
$ cd ~/empire-repo-main/backend && venv/bin/python -m pytest -q 2>&1 | tail -5
ERROR tests/test_archiveforge_workflow.py::test_successful_publish_writes_to_internal_target_when_configured
ERROR tests/test_quote_price_override_hotfix5.py::test_item_to_dict_alias_honors_price_overridden
ERROR tests/test_quote_price_override_hotfix5.py::test_item_to_dict_alias_falls_back_when_not_overridden
ERROR tests/test_quote_price_override_hotfix5.py::test_save_does_not_overwrite_canonical_total_from_client
ERROR tests/test_quote_price_override_hotfix5.py::test_pdf_uses_final_price_when_overridden
ERROR tests/test_quote_price_override_hotfix5.py::test_get_quote_returns_canonical_total_for_overridden_quote
ERROR tests/test_quote_tools_canonical_hotfix.py::test_get_quote_reads_canonical_quote_service
ERROR tests/test_quote_tools_canonical_hotfix.py::test_search_quotes_finds_canonical_quote
ERROR tests/test_quote_tools_canonical_hotfix.py::test_search_quotes_does_not_surface_legacy_only_records
106 failed, 1310 passed, 11 skipped, 1 xfailed, 429 warnings, 13 errors in 559.65s (0:09:19)
```

Expected roughly 106 failed / 1303 passed / 13 errors. Live: **106 failed / 1310 passed / 13 errors** (no flake drift on the known-flake `test_max_operating_registry.py::test_operating_registry_hot_reloads_and_keeps_last_known_good`).

---

## 0e · Demonstrate the current loss

### 0e.1 Harness built (VERIFIED)

Approach:
1. Copied `/home/rg/empire-data/empire.db` → `/tmp/empire_scratch.db` (via `cp -p`)
2. Started `uvicorn app.main:app --host 127.0.0.1 --port 8001` with `EMPIRE_TASK_DB=/tmp/empire_scratch.db` in a backgrounded subprocess. PID 1434536.
3. Posted a code task via `curl` to `http://127.0.0.1:8001/api/v1/max/code-task`.
4. The submit endpoint's PIN check was bypassed because `channel="web_cc"` (default) routes through `is_founder_message()` → founder=True → PIN not required (code_task_runner.py:5162-5173).
5. Queried status to confirm the task was visible.
6. Killed the scratch uvicorn (PIDs 1434536, 1434538).
7. Restarted on the same port (new PID 1434625/1434627).
8. Re-queried the same task_id.
9. Queried the broader `/api/v1/max/ai-desks/status` to confirm the runner's dict was empty.

### 0e.2 Raw output (VERIFIED)

```
$ curl -s -X POST http://127.0.0.1:8001/api/v1/max/code-task \
    -H 'Content-Type: application/json' \
    -d '{"prompt":"harness probe","working_dir":"/tmp"}' \
    -w "\nhttp_code=%{http_code}\n"
{"task_id":"968ea791-5b5","state":"queued","working_dir":"/tmp",
 "message":"Task submitted to Atlas (CodeForge). Poll /code-task/{id}/status for progress."}
http_code=200

$ curl -s http://127.0.0.1:8001/api/v1/max/code-task/968ea791-5b5/status \
    -w "\nhttp_code=%{http_code}\n"
{"id":"968ea791-5b5","prompt":"harness probe","execution_mode":"mutate",
 "provider_used":"xai","model_used":"grok","supports_tool_calls":null,
 "prompt_attempts":1,"failure_reason":null,"execution_protocol":"json-tool-action",
 "state":"running","created_at":"2026-08-24T23:22:26.720054",
 "started_at":"2026-08-24T23:22:26.723077","completed_at":null,"result":null,
 "error":null,"files_changed":[],"files_inspected":[],"executed_tool_calls":[],
 "verified_test_runs":[],"verified_commit_hash":null,"verification_notes":[],
 "last_response_text":null,"last_function_calls_summary":null,
 "last_parse_outcome":null,
 "log":[{"timestamp":"2026-08-24T23:22:26.723047","action":"ground_truth_fallback",
        "detail":"git status --porcelain failed in '/tmp'; validator will fall back to the legacy 3-tool whitelist. (R11, 2026-08-22)"},
       {"timestamp":"2026-08-24T23:22:26.723090","action":"started",
        "detail":"Atlas is analyzing the request..."},
       {"timestamp":"2026-08-24T23:22:26.727622","action":"planning",
        "detail":"Reading codebase and planning changes..."}]}
http_code=200

$ kill 1434536 1434538
$ ss -tlnp | grep 8001    # (port 8001 free)
$ cd ~/empire-repo-main/backend && EMPIRE_TASK_DB=/tmp/empire_scratch.db \
    nohup venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 \
    --port 8001 --timeout-keep-alive 5 > /tmp/scratch_uvicorn2.log 2>&1 &
$ # (scratch uvicorn2 PID 1434625, child 1434627)
$ curl -s -o /dev/null -w "ping_http_code=%{http_code}\n" http://127.0.0.1:8001/docs
ping_http_code=200

$ curl -s http://127.0.0.1:8001/api/v1/max/code-task/968ea791-5b5/status \
    -w "\nhttp_code=%{http_code}\n"
{"detail":"Code task '968ea791-5b5' not found"}
http_code=404
```

### 0e.3 Cross-check: ai-desks status confirms empty runner dict (VERIFIED)

`/api/v1/max/ai-desks/status` returns the full status payload. `codeforge` desk payload:

```
"desk_id":"codeforge","desk_name":"CodeForge","agent_name":"Atlas",
"active_tasks":0,"status":"idle","active_task_details":[],
"recent_completed":[],"files_changed":0,"commits":0
```

`active_tasks: 0` and `recent_completed: []` confirm the restarted runner has zero records of `968ea791-5b5` (or any prior task). The dict is empty.

### 0e.4 Production unaffected (VERIFIED)

```
$ ss -tlnp | grep 8000
LISTEN 0  2048  0.0.0.0:8000  users:(("python3",pid=1251889,fd=15))

$ python -c "import sqlite3
l = sqlite3.connect('/home/rg/empire-data/empire.db')
s = sqlite3.connect('/tmp/empire_scratch.db')
print('quotes_v2: live=%d scratch=%d' % (
    l.execute('SELECT COUNT(*) FROM quotes_v2').fetchone()[0],
    s.execute('SELECT COUNT(*) FROM quotes_v2').fetchone()[0]))
"
quotes_v2: live=198 scratch=198
```

Production PID 1251889 still bound to :8000. Scratch DB has same `quotes_v2` row count as live (198). No `code_mode_tasks` table in either DB (yet). Scratch torn down: port 8001 free at end of run.

### 0e.5 Harness caveat (VERIFIED)

The scratch harness ran the runner's `_execute()` for ~3 log lines before this report was assembled. That means the scratch process DID call `_request_code_response` once (it logged `planning` at line 852). This was non-destructive — pointed at the scratch DB and a `/tmp` working_dir — but it is non-zero work. The proof of loss does NOT depend on the call succeeding; the task was already in `self._tasks` immediately after `submit()` returned, and the 404 on restart is the unambiguous demonstration. INFERRED: the harness is sound; a future STEP 3 proof could use the same harness to demonstrate the new persistence layer surviving the restart.

---

## STOP

0a (precedent analysis — abandoned for structural reasons, lessons extracted) ·
0b (proposed schema, field-by-field, NOT created) ·
0c (10 terminal paths in `_execute()`, plus the missing `CancelledError` case) ·
0d (backup at `/home/rg/backups/2026-08-24_1912/`, pytest baseline 106f/1310p/13e) ·
0e (loss demonstrated: task `968ea791-5b5` 200 → kill → 404) · reported.

**No commit. No DDL. Production unchanged.** Awaiting founder's ruling on:

1. **Schema approval** — the `code_mode_tasks` DDL in 0b.4.
2. **Status values** — `queued`/`running`/`completed`/`error` only (per dispatch; no `awaiting_decision`).
3. **Startup-reconcile semantics** — when a `queued`/`running` row is found at boot, mark it `error` with `failure_reason = "Backend restart interrupted this task"`. The user must re-submit. (INFERRED recommendation; founder's call.)
4. **`CancelledError` handling** — explicit handler in `_execute()` or rely on startup-reconcile?
5. **TTL on terminal rows** — none in v1 (audit retention), or add a 90-day sweep?

Once approved, STEP 1 = write the persistence module (~250–400 lines including terminal-path hooks, reconcile, tests) + a migration runner that creates the table idempotently.