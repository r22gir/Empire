"""Task status lifecycle: failed/escalated allowed, retry cap with backoff.

SQLite CHECK on tasks.status historically blocked 'failed'/'escalated', so
desk failures were silently rewritten to 'todo' or vanished. This module
rebuilds the constraint and tracks retry_count / next_retry_at.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Iterable

logger = logging.getLogger("max.desks.lifecycle")

ALLOWED_STATUSES = (
    "todo", "in_progress", "waiting", "done", "cancelled", "failed", "escalated",
)
DEFAULT_MAX_RETRIES = 3
# Backoff after timeout n (1-indexed): 1 min, 4 min, 16 min
BACKOFF_MINUTES = (1, 4, 16)
RETRY_COLUMNS = (
    ("retry_count", "INTEGER DEFAULT 0"),
    ("next_retry_at", "TEXT"),
    ("max_retries", "INTEGER DEFAULT 3"),
    ("source", "TEXT"),
    ("conversation_id", "TEXT"),
    ("follow_up_date", "TEXT"),
    ("recurrence", "TEXT"),
)


def allowed_status(status: str) -> str:
    s = (status or "todo").strip().lower()
    return s if s in ALLOWED_STATUSES else "todo"


def backoff_minutes(retry_count: int) -> int:
    if retry_count <= 0:
        return BACKOFF_MINUTES[0]
    idx = min(retry_count - 1, len(BACKOFF_MINUTES) - 1)
    return BACKOFF_MINUTES[idx]


def next_retry_iso(retry_count: int, now: datetime | None = None) -> str:
    now = now or datetime.utcnow()
    return (now + timedelta(minutes=backoff_minutes(retry_count))).strftime("%Y-%m-%d %H:%M:%S")


def migrate_task_status_constraint(conn) -> None:
    """Allow failed/escalated on tasks.status. Safe to re-run."""
    _ensure_retry_columns(conn)
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='tasks'"
    ).fetchone()
    sql = (row[0] if row else "") or ""
    if "'failed'" in sql and "'escalated'" in sql:
        return
    cols = [r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    if not cols:
        return
    try:
        _rebuild_tasks_status_check(conn, cols)
    except Exception as exc:
        logger.warning("tasks.status CHECK rebuild failed (retry columns still added): %s", exc)


def _rebuild_tasks_status_check(conn, cols: list[str]) -> None:
    col_list = ", ".join(f'"{c}"' for c in cols)
    # Rebuild with the expanded CHECK. Keep every existing column.
    create_cols = []
    for name, typ, notnull, default, pk in (
        (r[1], r[2], r[3], r[4], r[5]) for r in conn.execute("PRAGMA table_info(tasks)")
    ):
        piece = f'"{name}" {typ or "TEXT"}'
        if name == "status":
            piece = (
                "status TEXT NOT NULL DEFAULT 'todo' "
                "CHECK (status IN ('todo','in_progress','waiting','done','cancelled','failed','escalated'))"
            )
        else:
            if pk:
                piece += " PRIMARY KEY"
            if notnull and name != "id" and name != "status":
                piece += " NOT NULL"
            if default is not None and name != "status":
                piece += f" DEFAULT {default}"
        create_cols.append(piece)
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute(f"CREATE TABLE tasks_status_mig ({', '.join(create_cols)})")
    conn.execute(f"INSERT INTO tasks_status_mig ({col_list}) SELECT {col_list} FROM tasks")
    conn.execute("DROP TABLE tasks")
    conn.execute("ALTER TABLE tasks_status_mig RENAME TO tasks")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_desk ON tasks(desk)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to)")
    try:
        conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_pipeline ON tasks(pipeline_id)")
    except Exception:
        pass
    conn.execute("PRAGMA foreign_keys=ON")
    logger.info("Migrated tasks.status CHECK to include failed/escalated")


def _ensure_retry_columns(conn) -> None:
    have = {r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()}
    for name, typ in RETRY_COLUMNS:
        if name not in have:
            try:
                conn.execute(f"ALTER TABLE tasks ADD COLUMN {name} {typ}")
            except Exception:
                pass


def record_timeout_retry(conn, task_id: str, *, max_retries: int = DEFAULT_MAX_RETRIES) -> dict:
    """On timeout: increment retry, set next_retry_at, or mark failed when cap is hit.

    Returns {"status", "retry_count", "capped"}.
    """
    _ensure_retry_columns(conn)
    row = conn.execute(
        "SELECT retry_count, max_retries FROM tasks WHERE id=?", (task_id,)
    ).fetchone()
    if not row:
        return {"status": "missing", "retry_count": 0, "capped": False}
    current = int(row[0] or 0)
    cap = int(row[1] or max_retries or DEFAULT_MAX_RETRIES)
    nxt = current + 1
    if nxt > cap:
        conn.execute(
            """UPDATE tasks SET status='failed', retry_count=?,
               result_summary=COALESCE(result_summary, '') || ' [retry cap reached]',
               updated_at=datetime('now'), completed_at=datetime('now')
               WHERE id=?""",
            (current, task_id),
        )
        return {"status": "failed", "retry_count": current, "capped": True}
    when = next_retry_iso(nxt)
    conn.execute(
        """UPDATE tasks SET status='todo', retry_count=?, next_retry_at=?,
           updated_at=datetime('now') WHERE id=?""",
        (nxt, when, task_id),
    )
    return {"status": "todo", "retry_count": nxt, "capped": False, "next_retry_at": when}


def due_for_retry(now: datetime | None = None) -> str:
    """SQL-friendly 'now' for next_retry_at comparison."""
    now = now or datetime.utcnow()
    return now.strftime("%Y-%m-%d %H:%M:%S")


def retry_where_clause() -> tuple[str, tuple]:
    """Pick todo tasks whose backoff has elapsed (or never set)."""
    return (
        "(next_retry_at IS NULL OR next_retry_at <= ?)",
        (due_for_retry(),),
    )


def apply_status_update(conn, task_id: str, status: str, result_summary: str | None = None) -> None:
    status = allowed_status(status)
    if result_summary is None:
        conn.execute(
            "UPDATE tasks SET status=?, updated_at=datetime('now') WHERE id=?",
            (status, task_id),
        )
    else:
        conn.execute(
            """UPDATE tasks SET status=?, result_summary=?, updated_at=datetime('now'),
               completed_at=CASE WHEN ? IN ('done','failed','escalated','cancelled')
                                 THEN datetime('now') ELSE completed_at END
               WHERE id=?""",
            (status, result_summary[:2000], status, task_id),
        )
