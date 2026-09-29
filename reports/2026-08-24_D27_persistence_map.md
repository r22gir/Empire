# D27 · Code-Task Persistence Map

**Date:** 2026-08-24
**Branch:** feature/drawing-standard @ 367b6f6 (HEAD)
**Mode:** READ-ONLY MAP. No code edits, no config edits, no migrations, no writes
outside this report. No fix lane. VERIFIED/INFERRED tags on every claim.
**Inheritance:** This dispatch acts on R11 §13 persistence scoping
(`reports/2026-08-22_214238_R11_validator_blindspot_8a34569d.md:833-895`).

---

## 1 · R11 §13 — WHAT IT SAID, THEN SET ASIDE

Quoted from `reports/2026-08-22_214238_R11_validator_blindspot_8a34569d.md:833-895`:

> "The API path (`POST /api/v1/max/code-task`) keeps state in
> `code_task_runner._tasks` only — a process-local dict. Every backend
> restart loses every API-path task. R9 Phase 3's trivial task
> (`32c030a1-45a`) is now 404. The corpus of in-memory task records is
> **silently lost on every restart**."   [R11:833-839]

> "No DB write in `code_task_runner` today. The runner only mutates
> `self._tasks: dict[str, CodeTask]`. Adding an INSERT to `openclaw_tasks`
> would couple the runner to the openclaw schema."   [R11:847-849]

> "`openclaw_tasks` has the columns `title, description, desk, priority,
> source, status, result, error, files_modified, commit_hash, retry_count,
> max_retries, parent_task_id, started_at, completed_at, created_at`
> (init_db.py:308-328)."   [R11:852-854]

> "A `CodeTask` carries `id, prompt, working_dir, execution_mode,
> provider_used, model_used, executed_tool_calls, files_changed,
> files_inspected, verified_test_runs, verified_commit_hash,
> verification_notes, log, last_response_text, last_function_calls_summary,
> last_parse_outcome`. They overlap on `id, result/error, files_modified,
> commit_hash, started_at, completed_at, created_at` (the `CodeTask.id` is
> a 12-char uuid prefix; `openclaw_tasks.id` is INTEGER AUTOINCREMENT —
> schema conflict)."   [R11:856-862]

> "**Estimated scope:** 1 file (`code_task_persistence.py`, ~80 lines),
> 1 test file (~5 tests), 1 small refactor to call the writer on terminal
> state, 1 commit."   [R11:885-889]

R11 framed this as a deliverable: own round, not part of R11, target schema
`openclaw_tasks`, single thin writer, ~80 lines.

**Setting R11 aside for the rest of this report.** Every claim below is
established from the live code; §7 reconciles back to R11.

---

## 2 · STATE INVENTORY — `code_task_runner._tasks`

### 2.1 Where the dict is declared (VERIFIED)

`backend/app/services/max/code_task_runner.py:767-769`:

```python
class CodeTaskRunner:
    """Manages async code tasks executed by CodeForge/Atlas."""

    def __init__(self):
        self._tasks: dict[str, CodeTask] = {}
        self._running: dict[str, asyncio.Task] = {}
```

- `self._tasks` is an **instance attribute** on `CodeTaskRunner`, NOT
  module-level. The module-level singleton is constructed one line below
  (`code_task_runner.py:1202`: `code_task_runner = CodeTaskRunner()`), and
  it is **imported by name** at:
  - `backend/app/routers/max/router.py:4634` — `from
    app.services.max.code_task_runner import code_task_runner`
  - `backend/app/routers/max/router.py:5175` — same import
  - `backend/app/routers/max/router.py:5198` — same import
  - `backend/app/services/openclaw_worker.py:786` — same import

  (VERIFIED via Grep on the live files. R11 §13.1 said the runner "is a
  module-level singleton" — that holds via `code_task_runner =
  CodeTaskRunner()`; the dict itself is instance-level, which is the same
  thing in practice because there is exactly one instance. R11's phrasing
  was loose but the conclusion is correct.)
- `self._running` is a **sibling dict** holding `asyncio.Task` handles —
  one per currently-executing task. Cleared at end of `_execute()`'s
  `finally:` block (`code_task_runner.py:1198`). **R11 §13 did not
  mention `self._running`.** INFERRED: this matters because a restart
  mid-execution loses both the *metadata* (`_tasks`) AND the *handle*
  (`_running`); the asyncio task is implicitly cancelled when its
  process dies. The on-disk effect of any half-done tool call is what
  the user actually sees (see §3).

### 2.2 Where the dict is WRITTEN (VERIFIED)

Exactly one site:

`backend/app/services/max/code_task_runner.py:802`:

```python
        self._tasks[task.id] = task
        # Start execution in background
        self._running[task.id] = asyncio.create_task(self._execute(task))
```

Both writes happen in `submit()` immediately after construction
(`code_task_runner.py:795-806`).

### 2.3 Where the dict is READ (VERIFIED)

Exactly two sites:

1. `backend/app/services/max/code_task_runner.py:771-772` — `get_task`:

```python
    def get_task(self, task_id: str) -> Optional[CodeTask]:
        return self._tasks.get(task_id)
```

   Called by `routers/max/router.py:5200`
   (`code_task_runner.get_task(task_id)` in
   `GET /api/v1/max/code-task/{task_id}/status`).

2. `backend/app/routers/max/router.py:4635` — `ai-desks/status`:

```python
        from app.services.max.code_task_runner import code_task_runner
        tasks = list(code_task_runner._tasks.values())
        active_tasks = [t for t in tasks if t.state.value in ("queued", "running")]
```

   Used to populate the `recent_tasks` payload of the Code Mode status
   surface.

### 2.4 Where the dict is DELETED from or CLEARED (VERIFIED)

**No deletion of `self._tasks` occurs anywhere in the live codebase.**

Searched with `Bash "find backend/app -name "*.py" | xargs grep -l
"code_task_runner\._" 2>/dev/null"` → only `routers/max/router.py` (read
only). Inside `code_task_runner.py`, only the sibling `_running` is
popped (`code_task_runner.py:1198`):

```python
        finally:
            self._running.pop(task.id, None)
```

**Consequence (VERIFIED):** once a task is submitted, its entry in
`self._tasks` lives forever (until the backend process exits). Restart
is the ONLY way these entries get cleared. There is no TTL, no LRU, no
max-size cap, no admin endpoint.

### 2.5 Key type and value shape (VERIFIED)

- Key type: `str` — `CodeTask.id` is `str(uuid.uuid4())[:12]`
  (`code_task_runner.py:796`).
- Value type: `CodeTask` dataclass (`code_task_runner.py:678-761`).
  Construction site: `code_task_runner.py:795-801`.

#### CodeTask fields actually present in the live dataclass

(Quoting the dataclass at `code_task_runner.py:681-722`.)

| # | Field | Type | Default | Origin |
|---|---|---|---|---|
| 1 | `id` | `str` | required | constructor (`code_task_runner.py:796`) |
| 2 | `prompt` | `str` | required | constructor |
| 3 | `working_dir` | `str` | `""` (REJECTED at submit if empty — see line 782) | **R11 added** |
| 4 | `execution_mode` | `str` | `"auto"` | existing |
| 5 | `provider_used` | `Optional[str]` | `None` | existing |
| 6 | `model_used` | `Optional[str]` | `None` | existing |
| 7 | `supports_tool_calls` | `Optional[bool]` | `None` | existing |
| 8 | `prompt_attempts` | `int` | `0` | existing |
| 9 | `failure_reason` | `Optional[str]` | `None` | existing |
| 10 | `execution_protocol` | `str` | `"json-tool-action"` | existing |
| 11 | `founder` | `bool` | `False` | existing |
| 12 | `state` | `CodeTaskState` | `QUEUED` | existing |
| 13 | `created_at` | `str` (ISO) | now() | existing |
| 14 | `started_at` | `Optional[str]` | `None` | existing |
| 15 | `completed_at` | `Optional[str]` | `None` | existing |
| 16 | `result` | `Optional[str]` | `None` | existing |
| 17 | `error` | `Optional[str]` | `None` | existing |
| 18 | `files_changed` | `list[str]` | `[]` | existing |
| 19 | `files_inspected` | `list[str]` | `[]` | existing |
| 20 | `executed_tool_calls` | `list[dict]` | `[]` | existing |
| 21 | `verified_test_runs` | `list[dict]` | `[]` | existing |
| 22 | `verified_commit_hash` | `Optional[str]` | `None` | existing |
| 23 | `verification_notes` | `list[str]` | `[]` | existing |
| 24 | `log` | `list[CodeTaskLog]` | `[]` | existing |
| 25 | `last_response_text` | `Optional[str]` | `None` | **F2 evidence** (line 711) |
| 26 | `last_function_calls_summary` | `Optional[str]` | `None` | **F2 evidence** |
| 27 | `last_parse_outcome` | `Optional[str]` | `None` | **F2 evidence** |
| 28 | `files_snapshot_before` | `set[str]` | `set()` | **R11 added** (line 718) |
| 29 | `files_snapshot_ground_truth` | `bool` | `False` | **R11 added** (line 722) |

29 fields. R11 §13.2 listed 17 — the dataclass has grown since.

**State machine** (from `code_task_runner.py:678` enum + transitions
observed):

| State | Set at | File:line |
|---|---|---|
| `QUEUED` | `_execute()` entry default | dataclass default |
| `RUNNING` | `_execute()` after baseline capture | `code_task_runner.py:838` |
| `COMPLETED` | success terminal | `code_task_runner.py:1173` |
| `ERROR` | exception / timeout / validator terminal | `code_task_runner.py:1084, 1100, 1116, 1180, 1189` |

**No `AWAITING_DECISION`, `PAUSED`, or `PARKED` state exists.** (VERIFIED
via Grep — `code_task_runner.py` has no `pause`, `interrupt`, `awaiting`,
`clarification`, `decision_required`, `confirm_needed`, or `park` token.)
The dispatch's "park and ask" question (§6) describes work that has NOT
been built.

### 2.6 State that already lives elsewhere (VERIFIED)

`code_task_runner.py` performs zero DB writes. Confirmed with:

```
Grep "DELETE|UPDATE openclaw_tasks|INSERT INTO openclaw_tasks" in code_task_runner.py → No matches found
Grep "save|persist|write|INSERT" in code_task_runner.py → no DB-related hits (only "write your ## Summary" prompt text)
```

Path A (openclaw bridge via `openclaw_worker._execute_code_task`,
`openclaw_worker.py:784-`) DOES write `openclaw_tasks`, but it writes
the *bridge-side* record, not the in-process `CodeTask`. The bridge
submits a prompt to `code_task_runner.submit()` (`openclaw_worker.py:802`)
and **polls the runner's in-memory state** at `openclaw_worker.py:814`
(`while _state_value(code_task.state) in {QUEUED.value,
RUNNING.value}`) without itself owning the dict.

---

## 3 · WHAT A RESTART ACTUALLY LOSES — CONCRETE

### 3.1 The single ownership dict (recap)

`self._tasks` contains the **only** persisted view of a Path-B task
(API submission). Nothing about the task exists outside this dict once
`submit()` returns.

### 3.2 Tasks in three states at restart

**State A: queued, never started.** `submit()` does
`self._tasks[task.id] = task` then `asyncio.create_task(self._execute(task))`.
The created asyncio task is itself stored in `self._running`. If the
process dies before `_execute()` reaches `task.state = RUNNING` at
`code_task_runner.py:838`, the task is silently dropped. No log line,
no DB row, no `/code-task/{id}/status` response (404).

**State B: mid-execution.** `_execute()` is awaiting one of:
- `await _request_code_response(...)` (`code_task_runner.py:876`, with a
  90s `asyncio.wait_for`).
- `await asyncio.get_event_loop().run_in_executor(None, lambda t=tc:
  execute_tool(...))` (`code_task_runner.py:976`).

When the process dies, the asyncio task is cancelled at the OS level.
Whatever `execute_tool` was running in the thread pool mid-call (a
shell command, a file write, a test run) is also killed. The in-memory
`task.state` mid-execution is whatever the loop last set it to
(`RUNNING` if past line 838, `QUEUED` otherwise). On restart, the row
is gone.

**User-visible consequence:** the task ID returned at submit is 404
forever. The UI's `/code-task/{id}/status` poll fails. Any files the
task wrote to disk *before* the restart are still on disk (e.g. a
`shell_execute` that wrote `/tmp/codetask_*.txt` survives; see
`/tmp/codetask_r9_evidence.txt` referenced in R11). But the runner's
record of having done so is lost.

**State C: awaiting a decision.** **Does not exist as code.**
The runner has no path that yields control to the founder mid-task.
Searched `Grep "awaiting|interrupt|wait_for_input|confirm_needed|decision_required"`
across `backend/app` → 16 files match, none in `code_task_runner.py`.
The nearest analog is `app/services/max/drawing_pending.py` — a
different module that parks drawing-flow state, not code-task state.
(See §6 for the field list.)

### 3.3 Reconciliation or orphan sweep at startup? (VERIFIED)

**None.**

Read `backend/app/main.py:357-450` (`@app.on_event("startup")` →
`start_background_services`). Every service that is started is either:
- a Telegram bot (line 391)
- a scheduler (lines 400-401, 407-415)
- a monitor (line 419)
- the openclaw bridge (line 428) — which polls `openclaw_tasks` and
  cleans zombies (`openclaw_worker.py:473-489`: `_cleanup_zombies()`)
  on the **`openclaw_tasks` table, NOT the in-memory dict.**
- vendor ops, task auto-worker, startup probes

No call anywhere in startup paths reads `code_task_runner._tasks`,
rehydrates it from a durable store, marks "lost" rows, or emits a
"this task was running when the backend died" notification.

The runner's only "sweep" is the per-task `self._running.pop(task.id,
None)` in the `finally:` block (`code_task_runner.py:1198`), which
removes the handle, not the entry.

### 3.4 What survives for the same task (VERIFIED)

Three classes of residue may exist for a path-B task even after restart:

1. **Files on disk.** Any file the task wrote via `file_write`,
   `file_edit`, `file_append`, `shell_execute`, `project_scaffold`, or
   `package_manager` survives the restart. The runner's view of
   `files_changed` does not.
2. **Git state.** If the task ran `git_ops commit`, a commit is in the
   repo. The runner's `verified_commit_hash` does not survive.
3. **Backend logs (stdout → journal).** Anything the runner logged at
   `logger.info` / `logger.error` is in journalctl. The structured
   `task.log` (CodeTaskLog entries, `add_log()` calls at lines 825-836,
   840, 852, 887, 893, etc.) is **NOT** separately journaled. Only
   the textual `logger` calls (`logger.error(f"Code task {task.id} ...
   failed: {e}")` at line 1195, etc.) reach journal.

**No DB row.** No telemetry entry. No `atlas_tasks` row (the runner
does not call `_log_async_task`; `_log_async_task` invocations in
`tool_executor.py:3962-3986` are only from `delegate_to_atlas`). The
`manual-code-task` rows in `openclaw_tasks` (21 rows in live DB) are
Path-A bridge rows, not Path-B API rows.

**Key consequence (INFERRED but tight):** a Path-B task that
crashes the backend mid-run is gone *as a record* but its
*side-effects* (files, commits) are durable. The shape of any
persistence fix should reflect that: the minimum is "the metadata
survives," not "the side-effects survive" (the side-effects already
do, because they hit disk).

---

## 4 · CONCURRENCY AND OWNERSHIP

### 4.1 Process ownership (VERIFIED)

```
$ systemctl --user show empire-backend -p ExecStart
ExecStart={ ... argv[]=/home/rg/empire-repo-main/backend/venv/bin/python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --timeout-keep-alive 65 ... pid=1251889 }
```

- `uvicorn app.main:app` with **no `--workers` flag**. Single uvicorn
  process is the dict's sole owner.
- `ps -ef | grep uvicorn` (live): exactly one row, PID 1251889. The
  systemd unit PID matches.
- `ss -tlnp | grep :8000`: single listener on PID 1251889.

**The dict is not split across workers today.** Adding `--workers N`
later would create N independent dicts and lose consistency — but
that is a future concern, not a current one.

**Secondary-worker guard exists** (`backend/app/main.py:334-354`,
`_acquire_primary_worker_lock` uses `fcntl.flock`). The check is for
the background services (Telegram, scheduler, openclaw bridge); it
does not gate the API surface or the runner. INFERRED: a future
multi-worker deployment would need the runner on a single primary OR
a shared store.

### 4.2 Is the dict touched from async tasks, threads, or a background scheduler? (VERIFIED)

**Async tasks only.** Specifically:

- `submit()` (called from request handlers) writes both dicts:
  `code_task_runner.py:802-804`.
- `_execute()` is `async def` (line 808). It is the only coroutine that
  mutates `task.state`, `task.executed_tool_calls`, `task.log`, etc.
- `_execute()` calls `await asyncio.get_event_loop().run_in_executor(
  None, lambda t=tc: execute_tool(t, desk="codeforge",
  founder=task.founder))` at `code_task_runner.py:976`. The
  `execute_tool` runs on the default thread pool; the **dict mutation
  is on the event-loop side of the `await`** (line 979:
  `executed_tool_calls.append(_tool_record(...))` is after the await
  yields control and resumes on the event-loop thread).
- The scheduler (`max_scheduler`, `desk_scheduler`) does not touch
  `code_task_runner._tasks`. (VERIFIED — Grep on `code_task_runner` in
  the scheduler module returns nothing.)
- The router read at `routers/max/router.py:4635` runs inside a FastAPI
  request handler (`async def`). It is also event-loop-bound.

### 4.3 Locks (VERIFIED)

`Grep "Lock|RLock|asyncio\.Lock|threading\.Lock|with\s+self\._lock|self\._lock\s*="` in
`code_task_runner.py` → **no matches**. **The dict is unguarded.**

**Why this is safe today (INFERRED):** the only thread that mutates
the dict is the event-loop thread for that single uvicorn worker.
CPython's asyncio is cooperative within a single event loop; an
`await` point is the only place another coroutine runs. The
`run_in_executor` calls hand work to a worker thread but the mutation
of the dict is on the event-loop side of the await. So concurrent
mutation of `_tasks` is impossible in the current code.

**Why this would become unsafe if anything changed (INFERRED):** any
future addition that mutates `task.executed_tool_calls` or
`task.files_changed` from inside the executor thread (e.g. a thread
that updates progress without going through `await`) would race. The
fact that there is no lock is a *current* property, not a guarantee.

---

## 5 · DURABLE STORAGE THAT ALREADY EXISTS

The DB split on this system is real and not to be guessed. Inventory:

### 5.1 `~/empire-data/empire.db` (the "raw SQL" DB) (VERIFIED)

- Connection: `backend/app/db/database.py:10-13` —
  `DB_PATH = os.getenv("EMPIRE_TASK_DB", str(Path.home() / "empire-data" / "empire.db"))`.
- Writers/readers using `get_db()`:
  - `backend/app/services/openclaw_worker.py:26` (constant
    `DB_PATH`) and `:74` (`_get_db()`), via `sqlite3` directly (NOT
    SQLAlchemy). Used by `_cleanup_zombies` (line 478), the queue
    polling loop (line 86), task updates (line 105), and many more.
  - `backend/app/routers/openclaw_tasks.py:13`
    (`from app.db.database import get_db, dict_row, dict_rows`). The
    OpenClaw Tasks HTTP surface (POST/GET/PUT/DELETE under
    `/api/v1/openclaw/tasks`).
  - `backend/app/db/unified_business_migration.py:24` (raw `str(Path.home()
    / "empire-data" / "empire.db")`).
  - `backend/app/services/max/tool_executor.py:3967` (`db_path =
    str(dp.db_path())` — delegates to the data-paths module). Used
    by `_log_async_task` to write to `atlas_tasks`.
  - `backend/app/services/max/drawing_pending.py:22` — same default;
    the existing `pending_drawing_jobs` table.
- Tables relevant to this dispatch (live counts from
  `sqlite3 ~/empire-data/empire.db`):
  - `openclaw_tasks` — 7,390 rows. Schema at
    `backend/app/db/init_db.py:308-328`. Live columns (from
    `PRAGMA table_info(openclaw_tasks)`):
    `id INTEGER PK, title TEXT, description TEXT, desk TEXT, priority INTEGER, status TEXT, source TEXT, created_at TIMESTAMP, started_at TIMESTAMP, completed_at TIMESTAMP, assigned_to TEXT, result TEXT, error TEXT, files_modified TEXT, commit_hash TEXT, retry_count INTEGER, max_retries INTEGER, parent_task_id INTEGER`. CHECK constraint allows
    `queued | running | done | failed | paused | cancelled`.
  - `atlas_tasks` — 132 rows. Schema at `tool_executor.py:3969-3977`:
    `id TEXT PK, title TEXT, status TEXT, result TEXT, error TEXT, created_at TEXT, updated_at TEXT`. **Different ID space** (8-char hash prefixes,
    not 12-char uuid prefixes).
  - `pending_drawing_jobs` — 0 rows today. Schema at
    `drawing_pending.py:56-66`:
    `id INTEGER PK, conversation_id TEXT NOT NULL, channel TEXT NOT NULL, handoff_json TEXT, missing_json TEXT, created_at TEXT, updated_at TEXT, UNIQUE(conversation_id, channel)`. With index
    `idx_pending_jobs_age` and TTL_HOURS=24 sweep inside
    `ensure_table()`.
  - `tasks` — 2,016 rows. A separate todo-tasks system (used by the
    `_task_auto_worker` in `main.py:453`). Schema includes
    `resume_state TEXT` (line 23) — relevant for park-and-ask as it
    suggests a "resume from a snapshot" primitive already exists
    elsewhere.

**The code-task path today has no connection to this DB.** `Grep
"empire\.db|EMPIRE_TASK_DB" in code_task_runner.py` → no matches. The
runner is read-only with respect to durable storage.

### 5.2 `~/empire-repo-main/backend/empirebox.db` (the SQLAlchemy DB) (VERIFIED)

- Connection: `backend/app/database.py:12-18` —
  `DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///" + ... +
  "empirebox.db")`. With default `EMPIRE_DATA_DIR` unset, resolves to
  `~/empire-repo-main/backend/empirebox.db` (file exists, 254KB,
  modified 2026-05-25).
- The dispatch footnote about `/home/rg/empire-data/empirebox.db` (278KB,
  mtime 2026-06-25) refers to a different artifact — likely stale, given
  the cwd resolution above.
- Used for: SQLAlchemy ORM models (`backend/app/models/business.py`),
  chat_backup async tables, OpenAPI schemas. **Not connected to
  code_task_runner.**

### 5.3 `/home/rg/.hermes/state.db` (the Hermes DB) (VERIFIED)

- `ls -la /home/rg/.hermes/state.db`: 3.0 GB, mtime 2026-08-17 13:59.
  Tables (live): `sessions`, `messages`, `messages_fts*` (FTS indexes),
  `async_delegations`, `delivery_obligations`, `gateway_hygiene_state`,
  `gateway_routing`, `session_model_usage`, `session_turn_leases`,
  `system_prompts`, `compression_locks`, `state_meta`, `schema_version`.
- `Grep "/.hermes/state.db" in backend/app` → **no matches**. The
  Empire backend does not touch this database. It is owned by the
  opencode-remote.service / hermes stack (per BACKLOG_UPDATE_2026-08-19.md:168,
  which mentions `.hermes/state.db` as a housekeeping item but not as
  an Empire-backend artifact).
- **Out of scope for path-B persistence.** Bringing the runner into
  this DB would require reading the Hermes schema as authoritative.

### 5.4 Other stores in `~/empire-data/` (INFERRED from directory listing)

- `amp.db` (131KB), `intake.db` (467KB), `craftforge/` directory,
  `brain/` directory. **None of these are referenced by
  `code_task_runner.py`** (Grep confirms no `amp.db`, `intake.db`,
  `craftforge` mention in the runner or its router).

### 5.5 Storage options for the code-task persistence layer

Three concrete options, with their trade-offs. **No recommendation —
founder's ruling.**

#### Option A — Write into the existing `openclaw_tasks` table

- Closest to existing code: the runner already has path-A rows there
  (via `openclaw_worker`), and `openclaw_tasks` carries the closest
  shape (status, result, error, files_modified, commit_hash).
- Row would look roughly like:
  ```sql
  INSERT INTO openclaw_tasks
    (title, description, desk, priority, source, status, result, error,
     files_modified, commit_hash, started_at, completed_at, assigned_to)
  VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
  ```
  with `title=prompt[:N]`, `description=prompt`, `source='code-mode-api'`,
  `assigned_to='code_task_runner'`, `desk='codeforge'`.
- **Trade-off A1 (the ID conflict R11 §13.2 named):** live
  `openclaw_tasks.id` is `INTEGER AUTOINCREMENT`; `CodeTask.id` is a
  12-char uuid prefix. Either (i) the writer chooses the bridge
  record's auto id and ignores `CodeTask.id`, breaking the
  `/api/v1/max/code-task/{task_id}/status` round-trip; or (ii) we add
  a side-table mapping uuid → integer; or (iii) we extend
  `openclaw_tasks.id` to TEXT (schema migration touching path-A).
- **Trade-off A2 (path-A path-B contention):** path-A
  (`openclaw_worker`) writes to `openclaw_tasks` for the openclaw
  bridge; path-B would too. Without coordination, two writers can
  step on each other. The schema CHECK constraint
  `('queued','running','done','failed','paused','cancelled')` does not
  include 'awaiting_decision' or 'parked', so park-and-ask (see §6)
  cannot land on this column without a migration.
- **Trade-off A3 (inverted ownership):** path-A bridge rows are
  *tasks enqueued for openclaw to pick up*; path-B rows would be
  *tasks already running in the backend process*. The semantic of
  the table is muddied.
- **Trade-off A4 (R11 caveats still apply):** the `parent_task_id`
  schema column is live `INTEGER` (init_db.py says `TEXT`); drift has
  already happened, so a "trust the schema in init_db.py" approach
  is no longer safe.

#### Option B — New side-table `code_mode_tasks` in `~/empire-data/empire.db`

- Closest analog in the existing codebase: `pending_drawing_jobs` —
  same DB, same `sqlite3` access pattern, JSON-blob columns, TTL
  sweep in `ensure_table()`, idempotent CREATE.
- Row would look roughly like:
  ```sql
  CREATE TABLE code_mode_tasks (
      id TEXT PRIMARY KEY,                -- CodeTask.id (12-char uuid)
      prompt TEXT,
      working_dir TEXT,
      execution_mode TEXT,
      founder INTEGER,                     -- 0/1
      state TEXT NOT NULL,                -- queued|running|completed|error|awaiting_decision|paused
      provider_used TEXT, model_used TEXT, supports_tool_calls INTEGER,
      prompt_attempts INTEGER, failure_reason TEXT,
      created_at TEXT, started_at TEXT, completed_at TEXT,
      result TEXT, error TEXT,
      files_changed TEXT,                 -- JSON array
      files_inspected TEXT,               -- JSON array
      executed_tool_calls TEXT,           -- JSON array
      verified_test_runs TEXT,            -- JSON array
      verified_commit_hash TEXT, verification_notes TEXT,  -- JSON array
      log TEXT,                           -- JSON array
      last_response_text TEXT,
      last_function_calls_summary TEXT,
      last_parse_outcome TEXT,
      files_snapshot_before TEXT,         -- JSON array
      files_snapshot_ground_truth INTEGER,
      pending_question TEXT,              -- NEW for park-and-ask (§6)
      pending_options TEXT,               -- NEW (JSON array)
      updated_at TEXT DEFAULT (datetime('now'))
  );
  CREATE INDEX idx_code_mode_state ON code_mode_tasks(state);
  CREATE INDEX idx_code_mode_updated ON code_mode_tasks(updated_at);
  ```
- **Trade-off B1 (DB coupling):** adds a second writer to
  `empire.db`. There is precedent (`atlas_tasks`, `pending_drawing_jobs`),
  so this is consistent, not novel.
- **Trade-off B2 (write frequency):** the runner currently mutates
  `task.log`, `task.executed_tool_calls`, etc. on every tool call
  (`code_task_runner.py:887, 972, 979, 1063`). Persisting every
  mutation = high write rate. Persisting on terminal state only = lose
  mid-run history. A `journal` row inserted once per tool call + an
  UPSERT on terminal state is one option; an outbox pattern another.
- **Trade-off B3 (zombie interaction with `openclaw_tasks`):** the
  existing zombie sweep at `openclaw_worker.py:473-489` only touches
  `openclaw_tasks` rows in 'running' state for ≥ ZOMBIE_TIMEOUT_MINUTES
  (10 min). Path-B has no equivalent. If path-B adopts a side-table,
  it needs its own sweep.
- **Trade-off B4 (in-flight handling):** a backend crash mid-task
  leaves a row at `state='running'` with no process attached. The
  next startup must reconcile. (See §3.3 — no such reconciliation
  exists today.)

#### Option C — Extend the in-process dict with a local file journal

- A JSON-lines file like `~/empire-data/code_mode_tasks.journal`,
  appended on every state transition. On startup, the runner
  rehydrates from the file.
- **Trade-off C1 (no SQL queryability):** no joins, no indexing, no
  migrations, no portal buttons reading it directly.
- **Trade-off C2 (no FD-evidence schema alignment):** everything else
  in the empire backend lives in SQLite. A JSONL sidecar is a new
  pattern.
- **Trade-off C3 (truncation / corruption handling):** a partial
  write at crash time is recoverable only by ignoring the last line.
  No precedent for that pattern in this codebase.
- **Trade-off C4 (does not help with multi-worker consistency):**
  if `--workers` is added later, two processes writing the same
  file = corruption.

---

## 6 · PARK-AND-ASK — WHAT PERSISTENCE MUST CARRY

This section scopes only. No design.

### 6.1 Current state (VERIFIED)

- The runner has no `awaiting_decision` / `paused` state
  (`code_task_runner.py` has no such enum value; CHECK constraint
  on `openclaw_tasks` does not allow one either).
- No code path stops a task and waits for founder input.
- The closest analog is `drawing_pending.py:pending_drawing_jobs` — a
  different module that parks drawing-flow state (handoff JSON +
  missing dims + conversation_id+channel key) and resumes when the
  next founder message matches the resume heuristic.

### 6.2 What must survive between "task asks a question" and "founder answers"

If the runner gained a park-and-ask primitive tomorrow, the
persistence layer for it would need to carry, between
*`state='awaiting_decision'`* and *`state='answer_received'`*:

| Field | Why | Source analog |
|---|---|---|
| `id` (`CodeTask.id`) | re-identify the task on resume | `code_task_runner.py:796` |
| `state` | distinguish parked from running | `code_task_runner.py:696` enum |
| `prompt` | the original request context | `code_task_runner.py:797` |
| `working_dir` | so resume can re-attach git baseline | **R11** field, `code_task_runner.py:687` |
| `execution_mode`, `founder` | resume with same execution parameters | `code_task_runner.py:688, 695` |
| `started_at`, `created_at` | audit trail | `code_task_runner.py:697, 839` |
| `executed_tool_calls` | re-feed the model the history it had when it asked | `code_task_runner.py:704` |
| `files_changed`, `files_inspected`, `verified_commit_hash` | don't double-credit files on resume | `code_task_runner.py:702-706` |
| `last_response_text`, `last_function_calls_summary`, `last_parse_outcome` | F2 evidence — what the model saw when it asked | `code_task_runner.py:711-713` |
| `log` | the append-only event log | `code_task_runner.py:708` |
| `pending_question` | what the task asked the founder | NEW — no current field |
| `pending_options` | structured choices if offered | NEW — JSON list |
| `decision_deadline` | TTL on the parked row | NEW — analogous to `pending_drawing_jobs` TTL |
| `updated_at` | for sweep queries | standard SQLite timestamp |

**`provider_used`, `model_used`, `prompt_attempts`** may also need
persistence so resume doesn't reset the retry counter.

### 6.3 Scope note (INFERRED)

Whether the park-and-ask feature is built at all is a separate
founder decision. The persistence layer should not presuppose it.
The minimal viable persistence (Option B above without
`pending_question` / `pending_options` / `decision_deadline`) is
sufficient to close the restart-loss gap; park-and-ask fields can
be added later without re-architecting.

---

## 7 · R11 AGREEMENT AND DIVERGENCE

### 7.1 What R11 §13 got right

| Claim | Live state | Verdict |
|---|---|---|
| Path B state is in `code_task_runner._tasks` only | `_tasks` is the only Path-B store | **STILL TRUE** |
| Every backend restart loses every Path-B task | Confirmed: no rehydrate, no sweep | **STILL TRUE** |
| The runner does not write to any DB | Confirmed: zero DB writes in `code_task_runner.py` | **STILL TRUE** |
| `openclaw_tasks` is path-A durable | 7,390 rows, path-A bridge writes here | **STILL TRUE** |
| `CodeTask.id` conflicts with `openclaw_tasks.id` | TEXT 12-char prefix vs INTEGER AUTOINCREMENT | **STILL TRUE** |
| R9 Phase 3 task `32c030a1-45a` is 404 | Logical: in-memory dict, no DB row | **STILL TRUE** |

### 7.2 Where R11 §13 no longer matches the live code

| R11 claim | Live state | Verdict |
|---|---|---|
| "`code_task_runner` is a module-level singleton" (`§13.1`, `code_task_runner.py:1073`) | The dict is instance-level (`code_task_runner.py:768`); the singleton line moved from `:1073` to `:1202` after R11's commit | **STALE — line numbers shifted, prose still essentially correct** |
| "`openclaw_tasks` has the columns ... `title, description, desk, priority, source, status, result, error, files_modified, commit_hash, retry_count, max_retries, parent_task_id, started_at, completed_at, created_at`" (`§13.2`) | Live columns: `id, title, description, desk, priority, status, source, created_at, started_at, completed_at, assigned_to, result, error, files_modified, commit_hash, retry_count, max_retries, parent_task_id`. R11 omitted `id` and `assigned_to`. R11 says `parent_task_id TEXT` (per `init_db.py`); live is `INTEGER` | **STALE — schema drifted** |
| "A `CodeTask` carries `id, prompt, working_dir, execution_mode, provider_used, model_used, executed_tool_calls, files_changed, files_inspected, verified_test_runs, verified_commit_hash, verification_notes, log, last_response_text, last_function_calls_summary, last_parse_outcome`" (`§13.2`) | Live has 29 fields; R11 listed 17. Omitted from R11: `founder, state, created_at, started_at, completed_at, result, error, supports_tool_calls, prompt_attempts, failure_reason, execution_protocol`. R11's own changes (`files_snapshot_before`, `files_snapshot_ground_truth`, F2 evidence fields) are in the live dataclass but absent from R11's enumeration | **STALE — R11 itself grew the dataclass, then failed to update §13.2** |
| "They overlap on `id, result/error, files_modified, commit_hash, started_at, completed_at, created_at`" (`§13.2`) | Now also overlap on `provider_used, model_used, execution_mode`. New non-overlapping fields: `working_dir, files_snapshot_before, files_snapshot_ground_truth, last_response_text, last_function_calls_summary, last_parse_outcome, log, verification_notes, verified_test_runs, files_inspected, executed_tool_calls, failure_reason, supports_tool_calls, prompt_attempts, execution_protocol, founder` | **STALE — field count grew** |
| "~80 lines" (`§13.2.6`) | R11 underestimated because: (a) the CodeTask field count is now 29, not 17 — JSON serialization alone is longer; (b) schema alignment must absorb drift in `openclaw_tasks` (assigned_to, parent_task_id type); (c) the runner must thread the new write on terminal state **and** on every state transition if mid-run history is to survive; (d) a zombie / startup-reconcile sweep is missing from R11's scope; (e) park-and-ask fields (§6) are not in R11's scope at all and would push the writer further | **STALE — estimate is now ~150-250 lines for a minimally-correct writer including startup-reconcile, with no park-and-ask fields; ~250-400 with park-and-ask.** INFERRED range, not measured. |
| "1 small refactor to call the writer on terminal state" (`§13.2.6`) | The runner's `_execute()` has at least 5 terminal paths (`code_task_runner.py:1084, 1100, 1116, 1173, 1180, 1189`). Each needs to call the writer, OR the writer needs a single-call hook (e.g. a context manager or callback registration). The latter is cleaner but adds design | **STALE — silent under-counting of touch points** |
| "Migration of in-memory tasks at restart. Out of scope" (`§13.2.5`) | R11 says in-memory tasks created before the round are still lost. INFERRED: this is a deliberate scoping call, not a divergence — but combined with the lack of any startup rehydrate (§3.3), the implication is that the round does not address *backwards* durability, only forward durability. Any founder expecting "save all existing tasks" is wrong | **STILL TRUE — but the implication is sharper** |
| "the dispatch's path-doctrine debate (REPO_DIR vs canonical) is deferred" (`§8.3`) | `openclaw_worker.py:802` still passes `working_dir=REPO_DIR`. `REPO_DIR = "~/empire-repo"` (openclaw_worker.py:1174). Canonical is `~/empire-repo-main` (per H73 / CLAUDE.md / D23). Status: unchanged. | **STILL TRUE — same as R11** |
| "On subprocess / API path. The openclaw bridge path already writes" (`§13.2.3`) | The openclaw bridge writes the *bridge* record, then submits to `code_task_runner`. The runner is downstream of the bridge — it has no separate write path | **STILL TRUE but imprecise wording** |

### 7.3 What R11 missed entirely

1. **Sibling dict `self._running`** (`code_task_runner.py:769`). Holds
   `asyncio.Task` handles. R11 §13 never named it. INFERRED: a
   persistence writer that ignores `_running` is fine (handles are
   process-scoped by definition) but a startup-reconcile step that
   treats `_running` as the source of "currently running" tasks
   would need to rebuild it from durable state.
2. **No deletion of `_tasks` anywhere.** R11's discussion assumed
   the dict was a per-task lifecycle (submit → execute → evict). It
   is not: tasks live forever in `_tasks` until restart. INFERRED:
   if persistence includes an in-DB cap / TTL, the dict-vs-DB
   eviction strategies must align.
3. **Zombie sweep exists for `openclaw_tasks`, not for `_tasks`.**
   `openclaw_worker.py:473-489` (`_cleanup_zombies`) marks
   `openclaw_tasks` rows as `failed` after 10 minutes in 'running'
   state. The runner has no equivalent. A persistent path-B
   implementation must adopt one.
4. **No startup reconciliation.** `main.py:357-450` startup paths
   start services but never ask "is there a task that was running
   before the crash?". R11's "out of scope" footnote understates
   this: it is the only way to make "the row says running but no
   process owns it" resolvable.
5. **`atlas_tasks` is a separate ID space.** R11 does not mention
   it. The schema is `id TEXT PK` but populated only by
   `delegate_to_atlas` (`tool_executor.py:3962-3986`), never by the
   runner. INFERRED: confusing the two would create duplicate-id
   collisions if a writer tried to reuse the table.
6. **Park-and-ask feature is not built and R11 §13 does not include
   it in scope.** §6 above enumerates the field list a future
   primitive would need from persistence. Any writer shipped
   without these fields will need a schema migration when
   park-and-ask is added.

### 7.4 Whether the ~80-line estimate holds now

**No.** (INFERRED — the count is not measured; it is what the
shape-change implies.)

Bumping from ~80 to a defensible range requires:

- Field-by-field JSON (de)serialization across 29 CodeTask fields
  (not 17): +30 lines minimum.
- Schema alignment absorbing live `openclaw_tasks` drift
  (`assigned_to`, `parent_task_id INTEGER`): +10-20 lines.
- 5 terminal-path hook calls in `_execute()` (or one context manager
  that wraps the whole `_execute`): +20-40 lines.
- Startup-reconcile pass that walks durable state and either
  re-queues or marks 'failed' the rows whose owner died: +30-60
  lines.
- Optional park-and-ask fields (§6): +30-50 lines.
- Tests: the same factor applies. R11 estimated ~5 tests; live
  shape (5 terminal paths × ~3 paths-through-each × 3 startup
  reconcile cases) implies 15-25 tests at minimum.

Realistic line counts for the writer + tests together, with no
park-and-ask:
- Conservative: ~150-200 lines writer, ~150-300 lines tests.
- With park-and-ask: +50-100 lines writer, +50-100 lines tests.

**The estimate carried forward from R11 is too low by roughly 2-3x.**
A founder who is making a go/no-go decision should round up.

---

## 8 · ARTIFACT COMMIT

This report file only. No code edits, no config edits, no migrations.

---

## STOP

State inventory (§2), concrete restart losses (§3), concurrency answer
(§4), storage options with trade-offs and no recommendation (§5),
park-and-ask field list (§6), R11 divergences (§7) — reported. No fix
lane started. Awaiting founder ruling on Option A / B / C (§5.5) and
on whether to scope park-and-ask into the same round or defer.
