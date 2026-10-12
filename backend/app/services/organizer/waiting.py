"""Waiting-on status + draft nudges. Never sends."""

from __future__ import annotations

from datetime import date, timedelta

from app.services.organizer.constants import OUTBOUND_POLICY
from app.services.organizer.edition import edition_sql
from app.services.organizer.store import now_iso


def set_waiting(conn, item_id: str, *, who: str, nudge_after_days: int = 3) -> dict:
    days = max(1, min(int(nudge_after_days or 3), 90))
    stamp = now_iso()
    conn.execute(
        """UPDATE organizer_items
           SET status = 'waiting_on', waiting_on = ?, nudge_after_days = ?,
               last_moved_at = ?, updated_at = ?
           WHERE id = ?""",
        (who.strip(), days, stamp, stamp, item_id),
    )
    row = conn.execute("SELECT * FROM organizer_items WHERE id = ?", (item_id,)).fetchone()
    return {
        "item": dict(row) if row else {"id": item_id, "waiting_on": who, "nudge_after_days": days},
        "sent": False,
        "outbound_policy": OUTBOUND_POLICY,
    }


def due_nudges(conn, *, today: str | None = None) -> list[dict]:
    today = today or date.today().isoformat()
    clause, params = edition_sql()
    rows = conn.execute(
        f"""SELECT * FROM organizer_items
            WHERE {clause} AND status = 'waiting_on' AND waiting_on IS NOT NULL""",
        params,
    ).fetchall()
    due = []
    for r in rows:
        item = dict(r)
        start = (item.get("last_nudge_at") or item.get("last_moved_at") or item.get("updated_at") or item.get("created_at") or "")[:10]
        if not start:
            continue
        days = int(item.get("nudge_after_days") or 3)
        ready = (date.fromisoformat(start) + timedelta(days=days)).isoformat()
        if ready <= today:
            due.append(item)
    return due


def dispatch_waiting_nudges(conn, *, today: str | None = None) -> dict:
    """Prepare draft nudges for Rafael. Nothing is sent."""
    due = due_nudges(conn, today=today)
    drafts = []
    for item in due:
        who = item.get("waiting_on") or "them"
        body = (
            f"Hi {who}, just checking in about {item.get('title')}. "
            f"No rush — wanted this on Rafael's desk to review."
        )
        draft = {
            "item_id": item["id"],
            "title": f"Nudge {who}",
            "body": body,
            "channel": "max",
            "sent": False,
        }
        try:
            from app.services.leadforge.growth import enqueue
            approval = enqueue(
                channel="email",
                body=body,
                source="organizer_waiting",
                source_ref=item["id"],
                kind="followup",
                title=draft["title"],
                to_name=who,
                created_by="organizer",
            )
            draft["approval_id"] = approval.get("id")
        except Exception:
            draft["approval_id"] = None
        conn.execute(
            "UPDATE organizer_items SET last_nudge_at = ?, reminder_draft = ?, updated_at = ? WHERE id = ?",
            (now_iso(), body, now_iso(), item["id"]),
        )
        drafts.append(draft)
    return {
        "dispatched": len(drafts),
        "drafts": drafts,
        "sent": False,
        "outbound_sent": False,
        "outbound_policy": OUTBOUND_POLICY,
        "message": "Draft nudges only. Nothing was sent.",
    }
