"""Persisted founder inbox — unrouted / escalated desk tasks survive process restart."""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

logger = logging.getLogger("max.desks.inbox")

SCHEMA = """
CREATE TABLE IF NOT EXISTS founder_inbox (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    priority TEXT DEFAULT 'normal',
    reason TEXT,
    source TEXT DEFAULT 'max',
    customer_name TEXT,
    conversation_id TEXT,
    desk TEXT,
    status TEXT NOT NULL DEFAULT 'open',
    created_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT
);
CREATE INDEX IF NOT EXISTS idx_founder_inbox_status ON founder_inbox(status);
"""


def _conn():
    from app.db.database import get_db
    return get_db()


def ensure_schema(conn=None) -> None:
    own = conn is None
    if own:
        with _conn() as c:
            c.executescript(SCHEMA)
        return
    conn.executescript(SCHEMA)


def _parse_ts(raw: str | None) -> Optional[datetime]:
    text = (raw or "").strip()
    if not text:
        return None
    try:
        dt = datetime.fromisoformat(text.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.astimezone(timezone.utc)
    except ValueError:
        pass
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S"):
        try:
            return datetime.strptime(text[:19], fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None


def _recently_resolved(row: dict[str, Any], hours: int) -> bool:
    if (row.get("status") or "") != "resolved":
        return False
    when = _parse_ts(row.get("resolved_at"))
    if when is None:
        return True
    return datetime.now(timezone.utc) - when <= timedelta(hours=max(1, int(hours or 24)))


def get(task_id: str) -> Optional[dict[str, Any]]:
    ensure_schema()
    with _conn() as conn:
        row = conn.execute("SELECT * FROM founder_inbox WHERE id=?", (task_id,)).fetchone()
    return dict(row) if row else None


def count_by_source_since(source: str, since: str) -> int:
    ensure_schema()
    with _conn() as conn:
        n = conn.execute(
            "SELECT COUNT(*) FROM founder_inbox WHERE source=? AND created_at>=?",
            (source, since),
        ).fetchone()[0]
    return int(n or 0)


def add(
    *,
    task_id: str,
    title: str,
    description: str = "",
    priority: str = "normal",
    reason: str = "",
    source: str = "max",
    customer_name: Optional[str] = None,
    conversation_id: Optional[str] = None,
    desk: Optional[str] = None,
    skip_existing: bool = False,
    recent_resolved_hours: int = 24,
) -> dict[str, Any]:
    """Insert an inbox row.

    Default: INSERT OR REPLACE (desk_manager._persist_inbox semantics).
    skip_existing=True (cascade only): leave an open or recently-resolved
    row untouched. Older resolved rows are replaced.
    """
    ensure_schema()
    with _conn() as conn:
        if skip_existing:
            existing = conn.execute(
                "SELECT * FROM founder_inbox WHERE id=?", (task_id,)
            ).fetchone()
            if existing:
                row = dict(existing)
                if (row.get("status") or "") == "open":
                    row["skipped"] = "open"
                    return row
                if _recently_resolved(row, recent_resolved_hours):
                    row["skipped"] = "recently_resolved"
                    return row
                # Older than the window: fall through to INSERT OR REPLACE.
        conn.execute(
            """INSERT OR REPLACE INTO founder_inbox
               (id, title, description, priority, reason, source, customer_name,
                conversation_id, desk, status, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'open', datetime('now'))""",
            (task_id, title, description, priority, reason, source,
             customer_name, conversation_id, desk),
        )
        row = conn.execute("SELECT * FROM founder_inbox WHERE id=?", (task_id,)).fetchone()
    return dict(row) if row else {"id": task_id, "title": title, "status": "open"}


def list_open(limit: int = 50) -> list[dict[str, Any]]:
    ensure_schema()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM founder_inbox WHERE status='open' ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [dict(r) for r in rows]


def count_open() -> int:
    ensure_schema()
    with _conn() as conn:
        n = conn.execute("SELECT COUNT(*) FROM founder_inbox WHERE status='open'").fetchone()[0]
    return int(n or 0)


def resolve(task_id: str, conn=None) -> bool:
    ensure_schema(conn)
    if conn is not None:
        cur = conn.execute(
            "UPDATE founder_inbox SET status='resolved', resolved_at=datetime('now') WHERE id=?",
            (task_id,),
        )
        return cur.rowcount > 0
    with _conn() as c:
        cur = c.execute(
            "UPDATE founder_inbox SET status='resolved', resolved_at=datetime('now') WHERE id=?",
            (task_id,),
        )
        return cur.rowcount > 0
