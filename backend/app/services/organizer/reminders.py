"""Due-date reminders persisted in SQLite and delivered through Max notifications."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from app.services.organizer.edition import edition_sql, process_edition
from app.services.organizer.schema import migrate_organizer_tables
from app.services.organizer.store import new_id, now_iso


def _ensure(conn) -> None:
    migrate_organizer_tables(conn)


def schedule_reminder(
    conn,
    *,
    item_id: Optional[str],
    due_at: Optional[str],
    title: str,
    body: Optional[str] = None,
    event_id: Optional[str] = None,
    channel: str = "max",
) -> Optional[dict]:
    """Save a reminder row. Delivery happens later via dispatch_due_reminders."""
    if not due_at:
        return None
    _ensure(conn)
    rid = new_id()
    stamp = now_iso()
    conn.execute(
        """
        INSERT INTO organizer_reminders
            (id, edition, item_id, event_id, due_at, title, body, channel, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
        """,
        (
            rid,
            process_edition(),
            item_id,
            event_id,
            due_at,
            (title or "Reminder").strip()[:200],
            (body or "").strip()[:2000] or None,
            (channel or "max")[:32],
            stamp,
            stamp,
        ),
    )
    row = conn.execute("SELECT * FROM organizer_reminders WHERE id = ?", (rid,)).fetchone()
    return dict(row) if row else {"id": rid, "item_id": item_id, "due_at": due_at, "status": "pending"}


def list_reminders(conn, *, status: Optional[str] = None, limit: int = 80) -> list[dict]:
    _ensure(conn)
    clause, params = edition_sql()
    query = f"SELECT * FROM organizer_reminders WHERE {clause}"
    args: list = list(params)
    if status:
        query += " AND status = ?"
        args.append(status)
    query += " ORDER BY due_at ASC LIMIT ?"
    args.append(limit)
    return [dict(r) for r in conn.execute(query, args).fetchall()]


def dispatch_due_reminders(conn, now: Optional[str] = None) -> list[dict]:
    """Fire pending reminders whose due_at has arrived. Uses notify_founder; never sends outbound."""
    _ensure(conn)
    stamp = now or now_iso()
    clause, params = edition_sql()
    rows = [
        dict(r)
        for r in conn.execute(
            f"""
            SELECT * FROM organizer_reminders
             WHERE {clause} AND status = 'pending' AND due_at <= ?
             ORDER BY due_at ASC
            """,
            (*params, stamp),
        ).fetchall()
    ]
    dispatched = []
    if not rows:
        return dispatched
    try:
        from app.routers.notifications import notify_founder
    except Exception:
        notify_founder = None
    for row in rows:
        href = f"/?screen=calendar&item={row.get('item_id') or ''}"
        title = row.get("title") or "Organizer reminder"
        message = row.get("body") or f"{title} is due."
        notification_id = None
        if notify_founder:
            try:
                entry = notify_founder(
                    "MAX",
                    "business_event",
                    title,
                    message,
                    "medium",
                    {
                        "item_id": row.get("item_id"),
                        "reminder_id": row.get("id"),
                        "href": href,
                        "source": "organizer",
                    },
                )
                notification_id = (entry or {}).get("id")
            except Exception:
                notification_id = None
        conn.execute(
            """
            UPDATE organizer_reminders
               SET status = 'notified', notified_at = ?, notification_id = ?, updated_at = ?
             WHERE id = ?
            """,
            (stamp, notification_id, stamp, row["id"]),
        )
        dispatched.append({**row, "status": "notified", "notification_id": notification_id})
    return dispatched


def due_iso_from_now() -> str:
    return datetime.now().isoformat(timespec="seconds")
