"""Task status lifecycle: failed/escalated allowed, retry cap with backoff.

SQLite CHECK on tasks.status historically blocked 'failed'/'escalated', so
desk failures were silently rewritten to 'todo' or vanished. This module
rebuilds the constraint and tracks retry_count / next_retry_at.
"""
from __future__ import annotations

import json
import logging
import os
import re
import shutil
import sqlite3
from datetime import datetime, timedelta
from typing import Any, Iterable, Optional

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


def _sqlite_file_path(conn) -> Optional[str]:
    try:
        row = conn.execute("PRAGMA database_list").fetchone()
    except Exception:
        return None
    if not row:
        return None
    path = row[2] if len(row) > 2 else ""
    if not path or path == ":memory:":
        return None
    return path


def backup_tasks_db(conn) -> Optional[str]:
    """Copy the SQLite file before a destructive tasks-table rebuild.

    Returns the backup path, or None when the db is in-memory / unnamed
    (tests) or the copy failed. Never raises.
    """
    src = _sqlite_file_path(conn)
    if not src or not os.path.isfile(src):
        logger.info("tasks migration: skip backup (no on-disk sqlite file)")
        return None
    ts = datetime.utcnow().strftime("%Y%m%d-%H%M%S")
    dest = f"{src}.tasks-mig-{ts}.bak"
    try:
        dest_conn = sqlite3.connect(dest)
        try:
            conn.backup(dest_conn)
        finally:
            dest_conn.close()
        logger.info("tasks migration backup: %s", dest)
        return dest
    except Exception as exc:
        try:
            shutil.copy2(src, dest)
            logger.info("tasks migration backup (copy2): %s", dest)
            return dest
        except Exception as exc2:
            logger.warning("tasks migration backup failed: %s / %s", exc, exc2)
            return None


def tasks_status_check_migrated(conn) -> bool:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='tasks'"
    ).fetchone()
    sql = (row[0] if row else "") or ""
    return "'failed'" in sql and "'escalated'" in sql


def migrate_task_status_constraint(conn) -> None:
    """Allow failed/escalated on tasks.status. Backup first. Idempotent."""
    if tasks_status_check_migrated(conn):
        _ensure_retry_columns(conn)
        return
    cols = [r[1] for r in conn.execute("PRAGMA table_info(tasks)").fetchall()]
    if not cols:
        _ensure_retry_columns(conn)
        return
    backup_tasks_db(conn)
    try:
        _rebuild_tasks_status_check(conn, cols)
    except Exception as exc:
        logger.warning("tasks.status CHECK rebuild failed: %s", exc)
    _ensure_retry_columns(conn)


def _rebuild_tasks_status_check(conn, cols: list[str]) -> None:
    row = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='tasks'"
    ).fetchone()
    sql = (row[0] if row else "") or ""
    new_sql = re.sub(
        r"CHECK\s*\(\s*status\s+IN\s*\([^)]*\)\s*\)",
        "CHECK (status IN ('todo', 'in_progress', 'waiting', 'done', 'cancelled', 'failed', 'escalated'))",
        sql,
        count=1,
        flags=re.I,
    )
    if new_sql == sql:
        raise RuntimeError("tasks.status CHECK clause not found")
    new_sql = re.sub(
        r"CREATE\s+TABLE\s+(IF\s+NOT\s+EXISTS\s+)?(\"?tasks\"?)",
        "CREATE TABLE tasks_status_mig",
        new_sql,
        count=1,
        flags=re.I,
    )
    col_list = ", ".join(f'"{c}"' for c in cols)
    conn.execute("PRAGMA foreign_keys=OFF")
    conn.execute(new_sql)
    conn.execute(f"INSERT INTO tasks_status_mig ({col_list}) SELECT {col_list} FROM tasks")
    conn.execute("DROP TABLE tasks")
    conn.execute("ALTER TABLE tasks_status_mig RENAME TO tasks")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_desk ON tasks(desk)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
    for idx_sql in (
        "CREATE INDEX IF NOT EXISTS idx_tasks_due ON tasks(due_date)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_assigned ON tasks(assigned_to)",
        "CREATE INDEX IF NOT EXISTS idx_tasks_pipeline ON tasks(pipeline_id)",
    ):
        try:
            conn.execute(idx_sql)
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


def parse_task_metadata(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return dict(raw)
    if not raw:
        return {}
    try:
        data = json.loads(raw)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def metadata_allows_auto_execute(raw: Any) -> bool:
    """False when the task is still held for a founder tap."""
    meta = parse_task_metadata(raw)
    if meta.get("approval_required") and not meta.get("approval_granted"):
        return False
    if meta.get("auto_execute") is False and not meta.get("approval_granted"):
        return False
    return True


def approve_waiting_task(conn, task_id: str, *, approved_by: str = "founder") -> dict[str, Any]:
    """Founder tap: waiting → todo so the worker can resume.

    Clears the hold flags, records approval_granted, and resolves the
    matching founder_inbox row. Does not itself send/invoice/deploy —
    desks still refuse restricted outbound actions.
    """
    _ensure_retry_columns(conn)
    row = conn.execute(
        "SELECT id, status, metadata, desk, title FROM tasks WHERE id=?",
        (task_id,),
    ).fetchone()
    if not row:
        return {"ok": False, "error": "not_found", "task_id": task_id}
    keys = row.keys() if hasattr(row, "keys") else None
    status = row["status"] if keys else row[1]
    raw_meta = row["metadata"] if keys else row[2]
    desk = row["desk"] if keys else row[3]
    title = row["title"] if keys else ""
    if status != "waiting":
        return {"ok": False, "error": "not_waiting", "status": status, "task_id": task_id}
    meta = parse_task_metadata(raw_meta)
    meta["approval_required"] = False
    meta["auto_execute"] = True
    meta["approval_granted"] = True
    meta["approved_by"] = approved_by
    meta["approved_at"] = datetime.utcnow().isoformat()
    conn.execute(
        "UPDATE tasks SET status='todo', metadata=?, updated_at=datetime('now') WHERE id=?",
        (json.dumps(meta), task_id),
    )
    try:
        from . import founder_inbox
        founder_inbox.resolve(task_id, conn)
    except Exception as exc:
        logger.debug("founder_inbox resolve after approve failed: %s", exc)
    return {
        "ok": True,
        "task_id": task_id,
        "status": "todo",
        "desk": desk,
        "title": title,
        "approved_by": approved_by,
        "resumed": True,
    }
