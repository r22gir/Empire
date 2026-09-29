"""Persistence layer for CodeTaskRunner (D28 · STEP 1).

Persists CodeTask state to ~/empire-data/empire.db so that path-B
code tasks survive a backend restart. Idempotent CREATE on import;
lazy migration runs the first time the module is touched.

Design notes (D28 §0b):
  - 29 CodeTask fields persisted. JSON-blob columns suffixed `_json`.
  - state values: queued | running | completed | error.
  - No awaiting_decision (park-and-ask is not built).
  - No TTL on terminal rows (audit retention). Reconciliation at startup
    is the only mechanism that ever touches queued/running rows post-restart.
  - Single uvicorn worker (no --workers flag per D27 §4) means no
    inter-process locking is required. If a second worker is ever added,
    this module needs a UNIQUE-writer lock or move to a remote DB.

Failure mode (D28 §1b):
  - Persistence failures MUST NOT kill the in-flight task. Every write
    is wrapped in try/except; failures log at WARNING and continue. The
    in-memory dict remains authoritative for the lifetime of THIS process.
  - This is asymmetric to the dataclass: a write that fails leaves the
    in-memory state ahead of the DB. Transient failures of NON-TERMINAL
    transitions (queued->running, and queued->queued self-write)
    self-heal on the next update_task() because that call upserts the
    full row and carries the latest in-memory state forward.
  - TERMINAL transitions have NO next update. A failed write at the
    COMPLETED hook (site :1173 in code_task_runner.py) or at any
    error hook leaves the row reading 'running' (or 'queued')
    permanently in the DB until the next boot. Recovery for those is
    sweep_stranded_tasks() at startup (D28 0b founder ruling):
    reconcile to state='error' with
    failure_reason="Backend restart interrupted this task". There is no
    auto-resume - model context, tool state, and partial outputs are
    gone with the dead asyncio.Task.

D27 §0a lesson applied:
  - The dead `pending_drawing_jobs` precedent failed because nothing on
    a live path called the writer. Every terminal site in
    `code_task_runner._execute()` (D28 §0c) now calls update_task();
    tests prove the call lands by inspecting the DB after the run.
"""
import json
import logging
import os
import sqlite3
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from app.services.max.code_task_runner import CodeTask

logger = logging.getLogger("max.code_task_persistence")

# D28 2b-1 — per-call resolution of the DB path.
#
# Bug history (D28 STEP 2b probe, 2026-08-24):
#   - This module captured DB_PATH at import time as a module-level
#     constant bound to `os.getenv("EMPIRE_TASK_DB") or prod`.
#   - Module-level capture defeats the test fixture (conftest's
#     `isolated_empire_db`) because pytest collection imports test
#     files BEFORE session-scope fixtures run. Any test file with a
#     module-level `from app.services.max import code_task_runner`
#     pulled this module in at collection time, captured DB_PATH to
#     prod (EMPIRE_TASK_DB was unset), and bound it for the rest of
#     the session. Result: persistence tests wrote to the production
#     empire.db. 10 fixture-shaped rows were recovered from prod.
#
# Fix:
#   - _resolved_db_path() reads EMPIRE_TASK_DB at CALL TIME, every
#     call. The fixture's env-var flip is honoured the moment it
#     lands, regardless of import order.
#   - DB_PATH is retained as a read-only fallback constant for
#     monkeypatchability (tests patch `ctp.DB_PATH` to simulate
#     unreachable paths). It is no longer the resolver.
#   - _connect() routes through _resolved_db_path(). No reader in
#     this module touches DB_PATH directly any more.
DEFAULT_DB_PATH = os.path.expanduser("~/empire-data/empire.db")
# Backwards-compat alias — older code/tests reference DB_PATH.
# New code should use _resolved_db_path() or _DEFAULT_DB_PATH.
DB_PATH = DEFAULT_DB_PATH


def _resolved_db_path() -> str:
    """Read EMPIRE_TASK_DB at call time. Per-call, never captured."""
    return os.getenv("EMPIRE_TASK_DB") or DB_PATH


def _connect_raw() -> sqlite3.Connection:
    """Bare sqlite3 connection with no schema bootstrap.

    Internal use only. _connect() and ensure_table() both route through
    this helper so the cycle ``_connect() -> ensure_table() -> _connect()``
    cannot form. Do NOT call ensure_table() from here.

    D28 STEP 2e: previous draft had ensure_table() at module scope, then
    moved the call into _connect() — which turned _connect() and
    ensure_table() into a mutual-recursion pair. The lazy ``_table_ready``
    flag tried to break it; both the module-global flag and the per-path
    set broke the multi-DB / drop-then-recreate tests. A raw helper that
    does nothing but open the connection breaks the cycle at the source.
    """
    conn = sqlite3.connect(_resolved_db_path())
    conn.row_factory = sqlite3.Row
    return conn


def _connect() -> sqlite3.Connection:
    # Lazy schema bootstrap (D28 STEP 2d): import-time is no-write. The
    # first connection in this process pays the cost of
    # ``ensure_table()``; every subsequent connection re-runs the cheap
    # ``CREATE TABLE IF NOT EXISTS`` no-op. See comment on ``ensure_table()``.
    ensure_table()
    return _connect_raw()


SCHEMA_DDL = """
CREATE TABLE IF NOT EXISTS code_mode_tasks (
    id                          TEXT PRIMARY KEY,
    prompt                      TEXT NOT NULL,
    working_dir                 TEXT NOT NULL,
    execution_mode              TEXT NOT NULL DEFAULT 'auto',
    founder                     INTEGER NOT NULL DEFAULT 0,
    state                       TEXT NOT NULL,
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
"""


def ensure_table() -> None:
    """Create code_mode_tasks + indexes if absent. Idempotent at the
    SQL level — every call issues ``CREATE TABLE IF NOT EXISTS`` plus
    the index DDL, which is a no-op when the table is already there.

    MUST be invoked via the lazy hook in ``_connect()`` below. The
    historical pattern of calling ``ensure_table()`` at module scope
    is what made test collection leak rows to prod: any test file
    with a module-level ``from app.services.max import code_task_runner``
    pulled this module in at collection time, when ``EMPIRE_TASK_DB``
    was unset and ``_resolved_db_path()`` returned the prod fallback.
    Importing the module must do NOTHING — no connection, no path
    resolution, no write — so the production DB cannot be touched
    by anything that merely imports the persistence layer.

    Earlier drafts tried to memo-ise: a module-global ``_table_ready``
    flag (broke multi-DB tests where ``EMPIRE_TASK_DB`` legitimately
    flips between two files mid-test), then a per-path set (broke
    the test that drops the table and expects the next call to
    re-create it). Both removed; the SQL is already idempotent and
    cheap. Repeat calls are a single ``CREATE TABLE IF NOT EXISTS``
    no-op plus three ``CREATE INDEX IF NOT EXISTS`` no-ops.

    D28 STEP 2e: the previous draft routed through ``_connect()``
    here — which itself called ``ensure_table()`` first, producing
    a ``_connect() -> ensure_table() -> _connect() -> ...`` mutual
    recursion. The bare ``except Exception`` swallowed the resulting
    ``RecursionError`` as a WARNING for two dispatches and a
    production deploy. The fix is structural (``_connect_raw()`` is
    the non-recursing entry point both this and ``_connect()`` use),
    and the handler below is narrowed to ``sqlite3.Error`` so any
    programmer error in this module surfaces immediately.
    """
    try:
        with _connect_raw() as conn:
            conn.executescript(SCHEMA_DDL)
            conn.commit()
    except sqlite3.Error as exc:
        # Only genuine DB conditions are tolerated here. A missing
        # file, locked DB, corrupt page, or permission error all
        # bubble up as ``sqlite3.Error`` subclasses — the runtime
        # process should keep working and the next call retries.
        # Programming errors (``RecursionError``, ``AttributeError``,
        # ``KeyError``, etc.) must NOT be swallowed: they are bugs in
        # this module and need to crash loud so the test suite
        # catches them. Step 4b of the D28 STEP 2e directive proves
        # the guard catches.
        logger.warning(f"code_task_persistence.ensure_table failed: {exc}")


def _task_row(task: "CodeTask") -> dict[str, Any]:
    """Serialize a CodeTask into a dict ready for INSERT/UPDATE.

    All JSON-blob columns are encoded here so callers stay simple.
    """
    return {
        "id": task.id,
        "prompt": task.prompt,
        "working_dir": task.working_dir,
        "execution_mode": task.execution_mode,
        "founder": 1 if task.founder else 0,
        "state": task.state.value,
        "provider_used": task.provider_used,
        "model_used": task.model_used,
        "supports_tool_calls": (
            1 if task.supports_tool_calls is True
            else 0 if task.supports_tool_calls is False
            else None
        ),
        "prompt_attempts": task.prompt_attempts,
        "failure_reason": task.failure_reason,
        "execution_protocol": task.execution_protocol,
        "created_at": task.created_at,
        "started_at": task.started_at,
        "completed_at": task.completed_at,
        "result": task.result,
        "error": task.error,
        "files_changed_json": json.dumps(task.files_changed, default=str),
        "files_inspected_json": json.dumps(task.files_inspected, default=str),
        "executed_tool_calls_json": json.dumps(task.executed_tool_calls, default=str),
        "verified_test_runs_json": json.dumps(task.verified_test_runs, default=str),
        "verified_commit_hash": task.verified_commit_hash,
        "verification_notes_json": json.dumps(task.verification_notes, default=str),
        "log_json": json.dumps(
            [
                {"timestamp": l.timestamp, "action": l.action, "detail": l.detail}
                for l in task.log
            ],
            default=str,
        ),
        "last_response_text": task.last_response_text,
        "last_function_calls_summary": task.last_function_calls_summary,
        "last_parse_outcome": task.last_parse_outcome,
        "files_snapshot_before_json": json.dumps(
            sorted(task.files_snapshot_before), default=str
        ),
        "files_snapshot_ground_truth": 1 if task.files_snapshot_ground_truth else 0,
    }


def insert_task(task: "CodeTask") -> bool:
    """Insert a fresh task row. Called once per submit().

    Returns True on success, False on failure (logged, never raised).
    """
    row = _task_row(task)
    try:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO code_mode_tasks (
                    id, prompt, working_dir, execution_mode, founder, state,
                    provider_used, model_used, supports_tool_calls,
                    prompt_attempts, failure_reason, execution_protocol,
                    created_at, started_at, completed_at, result, error,
                    files_changed_json, files_inspected_json,
                    executed_tool_calls_json, verified_test_runs_json,
                    verified_commit_hash, verification_notes_json,
                    log_json, last_response_text,
                    last_function_calls_summary, last_parse_outcome,
                    files_snapshot_before_json, files_snapshot_ground_truth
                ) VALUES (
                    :id, :prompt, :working_dir, :execution_mode, :founder, :state,
                    :provider_used, :model_used, :supports_tool_calls,
                    :prompt_attempts, :failure_reason, :execution_protocol,
                    :created_at, :started_at, :completed_at, :result, :error,
                    :files_changed_json, :files_inspected_json,
                    :executed_tool_calls_json, :verified_test_runs_json,
                    :verified_commit_hash, :verification_notes_json,
                    :log_json, :last_response_text,
                    :last_function_calls_summary, :last_parse_outcome,
                    :files_snapshot_before_json, :files_snapshot_ground_truth
                )
                """,
                row,
            )
            conn.commit()
        return True
    except sqlite3.IntegrityError:
        # Row already exists (e.g., retry after partial failure). Treat as success —
        # the next update_task() will reconcile any drift.
        logger.debug(f"code_task_persistence.insert_task: row {task.id} already exists")
        return True
    except sqlite3.Error as exc:
        logger.warning(
            f"code_task_persistence.insert_task({task.id}) failed: {exc} "
            "— in-memory state is authoritative for this process."
        )
        return False
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            f"code_task_persistence.insert_task({task.id}) unexpected error: {exc} "
            "— in-memory state is authoritative for this process."
        )
        return False


def update_task(task: "CodeTask") -> bool:
    """Upsert the full row for an existing task.

    Called from every terminal site in _execute() and from the RUNNING
    transition at :838. A row written on creation and never updated reads
    as a running task forever — that is worse than no row at all (D28 §1b).

    Returns True on success, False on failure (logged, never raised).
    """
    row = _task_row(task)
    # Carry updated_at forward to NOW so reconcile queries see the latest
    # touch. We do NOT touch created_at (immutable).
    try:
        with _connect() as conn:
            conn.execute(
                """
                INSERT INTO code_mode_tasks (
                    id, prompt, working_dir, execution_mode, founder, state,
                    provider_used, model_used, supports_tool_calls,
                    prompt_attempts, failure_reason, execution_protocol,
                    created_at, started_at, completed_at, result, error,
                    files_changed_json, files_inspected_json,
                    executed_tool_calls_json, verified_test_runs_json,
                    verified_commit_hash, verification_notes_json,
                    log_json, last_response_text,
                    last_function_calls_summary, last_parse_outcome,
                    files_snapshot_before_json, files_snapshot_ground_truth
                ) VALUES (
                    :id, :prompt, :working_dir, :execution_mode, :founder, :state,
                    :provider_used, :model_used, :supports_tool_calls,
                    :prompt_attempts, :failure_reason, :execution_protocol,
                    :created_at, :started_at, :completed_at, :result, :error,
                    :files_changed_json, :files_inspected_json,
                    :executed_tool_calls_json, :verified_test_runs_json,
                    :verified_commit_hash, :verification_notes_json,
                    :log_json, :last_response_text,
                    :last_function_calls_summary, :last_parse_outcome,
                    :files_snapshot_before_json, :files_snapshot_ground_truth
                )
                ON CONFLICT(id) DO UPDATE SET
                    state = excluded.state,
                    provider_used = excluded.provider_used,
                    model_used = excluded.model_used,
                    supports_tool_calls = excluded.supports_tool_calls,
                    prompt_attempts = excluded.prompt_attempts,
                    failure_reason = excluded.failure_reason,
                    started_at = excluded.started_at,
                    completed_at = excluded.completed_at,
                    result = excluded.result,
                    error = excluded.error,
                    files_changed_json = excluded.files_changed_json,
                    files_inspected_json = excluded.files_inspected_json,
                    executed_tool_calls_json = excluded.executed_tool_calls_json,
                    verified_test_runs_json = excluded.verified_test_runs_json,
                    verified_commit_hash = excluded.verified_commit_hash,
                    verification_notes_json = excluded.verification_notes_json,
                    log_json = excluded.log_json,
                    last_response_text = excluded.last_response_text,
                    last_function_calls_summary = excluded.last_function_calls_summary,
                    last_parse_outcome = excluded.last_parse_outcome,
                    files_snapshot_before_json = excluded.files_snapshot_before_json,
                    files_snapshot_ground_truth = excluded.files_snapshot_ground_truth,
                    updated_at = datetime('now')
                """,
                row,
            )
            conn.commit()
        return True
    except sqlite3.Error as exc:
        logger.warning(
            f"code_task_persistence.update_task({task.id}) failed: {exc} "
            "— in-memory state is authoritative for this process."
        )
        return False
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            f"code_task_persistence.update_task({task.id}) unexpected error: {exc} "
            "— in-memory state is authoritative for this process."
        )
        return False


def fetch_task(task_id: str) -> dict[str, Any] | None:
    """Read a task row by id. Returns None if absent. For tests + reconcilers."""
    try:
        with _connect() as conn:
            row = conn.execute(
                "SELECT * FROM code_mode_tasks WHERE id = ?", (task_id,)
            ).fetchone()
        if not row:
            return None
        return dict(row)
    except sqlite3.Error as exc:
        logger.warning(f"code_task_persistence.fetch_task({task_id}) failed: {exc}")
        return None


def count_tasks(state: str | None = None) -> int:
    """Count rows, optionally filtered by state. For tests."""
    try:
        with _connect() as conn:
            if state is None:
                row = conn.execute("SELECT COUNT(*) FROM code_mode_tasks").fetchone()
            else:
                row = conn.execute(
                    "SELECT COUNT(*) FROM code_mode_tasks WHERE state = ?", (state,)
                ).fetchone()
        return int(row[0])
    except sqlite3.Error:
        return 0


def sweep_stranded_tasks() -> int:
    """Reconcile rows stranded in 'queued'/'running' by a backend restart.

    D28 0b founder ruling: a task whose asyncio.Task died with the
    process can never resume - model context, tool state, and partial
    outputs are gone with it. Mark such rows as state='error' /
    failure_reason="Backend restart interrupted this task" so the user
    sees them as failed rather than stuck 'running' or 'queued' forever.

    Mirrors the shape of openclaw_worker.py:473-489 (sweep
    _cleanup_zombies) but does NOT carve out an active-task filter
    because Path B has no live writer to protect - the previous
    process is dead by definition.

    Returns the number of rows swept. Never raises - the backend
    starting matters more than reconciliation succeeding (D28 2b).
    """
    try:
        with _connect() as conn:
            result = conn.execute(
                """UPDATE code_mode_tasks
                   SET state = 'error',
                       failure_reason = 'Backend restart interrupted this task',
                       completed_at = COALESCE(completed_at, datetime('now')),
                       updated_at = datetime('now')
                   WHERE state IN ('queued', 'running')"""
            )
            swept = result.rowcount or 0
            if swept > 0:
                logger.warning(
                    f"code_task_persistence.sweep_stranded_tasks: "
                    f"reconciled {swept} stranded row(s) to state='error' "
                    f"(Backend restart interrupted this task)"
                )
            conn.commit()
            return int(swept)
    except sqlite3.Error as exc:
        logger.warning(
            f"code_task_persistence.sweep_stranded_tasks failed: {exc} "
            "- stranded rows will be visible to next sweep."
        )
        return 0
    except Exception as exc:  # noqa: BLE001 - must not crash startup
        logger.warning(
            f"code_task_persistence.sweep_stranded_tasks unexpected error: {exc}"
        )
        return 0


def _row_to_task(row: dict[str, Any]) -> "CodeTask":
    """Deserialize a code_mode_tasks row into a CodeTask dataclass.

    The returned CodeTask has NO asyncio.Task behind it (D27 4). It is
    history-only: read via runner.get_task(), inspect to_dict(), and
    never submitted to _execute. Caller is responsible for NOT adding
    it to CodeTaskRunner._running (see code_task_runner.rehydrate()).
    """
    from app.services.max.code_task_runner import (
        CodeTask, CodeTaskLog, CodeTaskState,
    )

    supports = row["supports_tool_calls"]
    if supports == 1:
        supports_decoded: bool | None = True
    elif supports == 0:
        supports_decoded = False
    else:
        supports_decoded = None

    return CodeTask(
        id=row["id"],
        prompt=row["prompt"],
        working_dir=row["working_dir"],
        execution_mode=row["execution_mode"],
        founder=bool(row["founder"]),
        state=CodeTaskState(row["state"]),
        provider_used=row["provider_used"],
        model_used=row["model_used"],
        supports_tool_calls=supports_decoded,
        prompt_attempts=row["prompt_attempts"],
        failure_reason=row["failure_reason"],
        execution_protocol=row["execution_protocol"],
        created_at=row["created_at"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        result=row["result"],
        error=row["error"],
        files_changed=json.loads(row["files_changed_json"]),
        files_inspected=json.loads(row["files_inspected_json"]),
        executed_tool_calls=json.loads(row["executed_tool_calls_json"]),
        verified_test_runs=json.loads(row["verified_test_runs_json"]),
        verified_commit_hash=row["verified_commit_hash"],
        verification_notes=json.loads(row["verification_notes_json"]),
        log=[
            CodeTaskLog(
                timestamp=entry["timestamp"],
                action=entry["action"],
                detail=entry["detail"],
            )
            for entry in json.loads(row["log_json"])
        ],
        last_response_text=row["last_response_text"],
        last_function_calls_summary=row["last_function_calls_summary"],
        last_parse_outcome=row["last_parse_outcome"],
        files_snapshot_before=set(json.loads(row["files_snapshot_before_json"])),
        files_snapshot_ground_truth=bool(row["files_snapshot_ground_truth"]),
    )


def fetch_all_tasks() -> list[Any]:
    """Read every row from code_mode_tasks into CodeTask instances.

    Used by code_task_runner.rehydrate() at startup (D28 2a) to restore
    the in-memory dict from a previous process's writes. Order is
    created_at ASC so newer rows overwrite older ones if duplicates
    somehow accumulate (PK is the natural key so this should never
    happen, but the upsert is harmless).

    Best-effort: returns [] on any error (logged). The backend
    starting matters more than rehydration succeeding.
    """
    try:
        with _connect() as conn:
            rows = conn.execute(
                "SELECT * FROM code_mode_tasks ORDER BY created_at ASC, id ASC"
            ).fetchall()
        return [_row_to_task(dict(r)) for r in rows]
    except sqlite3.Error as exc:
        logger.warning(
            f"code_task_persistence.fetch_all_tasks failed: {exc} - "
            "in-memory _tasks will be empty for this process."
        )
        return []
    except Exception as exc:  # noqa: BLE001 - must not crash startup
        logger.warning(
            f"code_task_persistence.fetch_all_tasks unexpected error: {exc}"
        )
        return []


# Import-time is intentionally a no-op (D28 STEP 2d, founder-ruled
# option (a) from the import-time-side-effects probe). Historical
# design had a bare ``ensure_table()`` here that ran on every module
# import — including during pytest collection, before the
# ``isolated_empire_db`` fixture had a chance to set
# ``EMPIRE_TASK_DB``. That made the per-call resolver return the prod
# fallback, ``sqlite3.connect(prod)`` opened the production DB from
# the test process, and every full-suite run leaked test-shaped
# rows to ``~/empire-data/empire.db`` (10 confirmed by the D28 STEP
# 2b probe; 56 more after 2c despite the guard).
#
# Lazy bootstrap now lives inside ``_connect()``. Importing this
# module does NOTHING — no connection, no path resolution, no
# write. The conftest guard remains as a backstop, not as the
# mechanism: if anything ever imports the module and calls
# ``_connect()`` under a prod path, it is caught; but the import
# itself cannot touch prod.
#
# Cited precedent for the OLD design — ``drawing_pending.py:293`` —
# was never a working model. Per D28 §0a, the pending_drawing_jobs
# table has never held a row, and its writer's preconditions are
# unsatisfiable. Removed from this comment.