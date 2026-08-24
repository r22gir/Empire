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
    in-memory state ahead of the DB. On the next state transition we
    upsert the full row, so a transient failure self-heals.

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

DB_PATH = (
    os.getenv("EMPIRE_TASK_DB")
    or os.path.expanduser("~/empire-data/empire.db")
)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


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
    """Create code_mode_tasks + indexes if absent. Idempotent."""
    try:
        with _connect() as conn:
            conn.executescript(SCHEMA_DDL)
            conn.commit()
    except sqlite3.Error as exc:
        logger.warning(f"code_task_persistence.ensure_table failed: {exc}")
    except Exception as exc:  # noqa: BLE001 — must not crash callers
        logger.warning(f"code_task_persistence.ensure_table unexpected error: {exc}")


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


# Run idempotent CREATE at import time. Mirrors the pending_drawing_jobs
# pattern (drawing_pending.py:293). If the table is already there this is a
# no-op; if it isn't, we create it before the first submit() lands.
ensure_table()