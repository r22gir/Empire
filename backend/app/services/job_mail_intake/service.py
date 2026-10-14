"""Run read-only job-mail intake. Never sends email or WhatsApp."""

from __future__ import annotations

import hashlib
import json
import uuid
from typing import Optional

from app.db.database import get_db
from app.services.job_mail_intake.match import match_message
from app.services.job_mail_intake.readers import (
    OUTBOUND_POLICY,
    TEST_INBOX,
    connected_accounts,
    fetch_raw_messages,
)
from app.services.job_mail_intake.schema import ensure_schema

# Re-export for tests / scheduler.
__all__ = [
    "OUTBOUND_POLICY",
    "TEST_INBOX",
    "approve_calendar_proposal",
    "list_calendar_proposals",
    "list_review_queue",
    "list_supplier_events",
    "list_timeline_notes",
    "run_intake",
]


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


def _fingerprint(msg: dict) -> str:
    raw = "|".join(
        str(msg.get(k) or "")
        for k in ("source", "message_id", "subject", "from", "date")
    )
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()


def _already(conn, fingerprint: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM jmi_processed WHERE fingerprint = ?", (fingerprint,)
    ).fetchone()
    if row:
        return True
    row = conn.execute(
        "SELECT 1 FROM jmi_review_queue WHERE fingerprint = ?", (fingerprint,)
    ).fetchone()
    return bool(row)


def _add_job_event(conn, job_id: str, event_type: str, summary: str, metadata: Optional[dict] = None) -> None:
    if not job_id:
        return
    try:
        conn.execute(
            """INSERT INTO job_events (id, job_id, event_type, actor, summary, metadata)
               VALUES (?, ?, ?, 'job_mail_intake', ?, ?)""",
            (
                _new_id(),
                job_id,
                event_type,
                summary,
                json.dumps(metadata, default=str) if metadata else None,
            ),
        )
    except Exception:
        pass


def _record_processed(conn, msg: dict, match: dict, kind: str) -> None:
    conn.execute(
        """INSERT OR IGNORE INTO jmi_processed
           (id, source, message_id, fingerprint, subject, from_addr,
            matched_job_id, matched_customer_id, match_reason, kind, status, sent)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'processed', 0)""",
        (
            _new_id(),
            msg.get("source") or "",
            str(msg.get("message_id") or ""),
            _fingerprint(msg),
            msg.get("subject") or "",
            match.get("from_email") or "",
            match.get("job_id"),
            match.get("customer_id"),
            match.get("reason") or "",
            kind,
        ),
    )


def _process_one(conn, msg: dict) -> dict:
    fp = _fingerprint(msg)
    if not msg.get("message_id"):
        return {"status": "skipped", "reason": "no_message_id", "sent": False}
    if _already(conn, fp):
        return {"status": "duplicate", "fingerprint": fp, "sent": False}

    match = match_message(conn, msg)
    facts = match.get("facts") or {}
    subject = (msg.get("subject") or "(no subject)").strip()
    preview = (msg.get("preview") or msg.get("body") or "")[:400]
    who = match.get("from_name") or match.get("from_email") or "unknown"
    summary = f"Email from {who}: {subject}"

    if not match.get("matched") or not match.get("job_id"):
        conn.execute(
            """INSERT OR IGNORE INTO jmi_review_queue
               (id, source, message_id, fingerprint, subject, from_name, from_addr,
                preview, received_at, status, sent)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'unmatched', 0)""",
            (
                _new_id(),
                msg.get("source") or "",
                str(msg.get("message_id") or ""),
                fp,
                subject,
                match.get("from_name") or "",
                match.get("from_email") or "",
                preview,
                msg.get("date"),
            ),
        )
        _record_processed(conn, msg, match, "unmatched")
        return {
            "status": "unmatched",
            "review": True,
            "reason": match.get("reason"),
            "sent": False,
        }

    job_id = match["job_id"]
    note_id = _new_id()
    conn.execute(
        """INSERT INTO jmi_timeline_notes
           (id, job_id, source, message_id, fingerprint, summary, excerpt, sent)
           VALUES (?, ?, ?, ?, ?, ?, ?, 0)""",
        (note_id, job_id, msg.get("source"), str(msg.get("message_id") or ""), fp, summary, preview),
    )
    _add_job_event(
        conn,
        job_id,
        "email_note",
        summary,
        {
            "source": msg.get("source"),
            "message_id": msg.get("message_id"),
            "subject": subject,
            "from": msg.get("from"),
            "sent": False,
        },
    )

    calendar_ids = []
    for prop in facts.get("proposed_dates") or []:
        cid = _new_id()
        conn.execute(
            """INSERT INTO jmi_calendar_proposals
               (id, job_id, customer_id, source, message_id, fingerprint,
                title, proposed_date, kind, excerpt, status, sent)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0)""",
            (
                cid,
                job_id,
                match.get("customer_id"),
                msg.get("source"),
                str(msg.get("message_id") or ""),
                fp,
                f"{prop['kind'].title()} — {subject}"[:160],
                prop["date"],
                prop["kind"],
                prop.get("excerpt") or "",
            ),
        )
        calendar_ids.append(cid)

    supplier_ids = []
    if facts.get("is_supplier_order") or facts.get("tracking_numbers") or facts.get("order_numbers"):
        tracks = facts.get("tracking_numbers") or [None]
        orders = facts.get("order_numbers") or [None]
        event_type = "tracking" if facts.get("tracking_numbers") else "order_confirmation"
        sid = _new_id()
        conn.execute(
            """INSERT INTO jmi_supplier_order_events
               (id, job_id, source, message_id, fingerprint, event_type,
                tracking_number, order_number, supplier_name, excerpt, sent)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (
                sid,
                job_id,
                msg.get("source"),
                str(msg.get("message_id") or ""),
                fp,
                event_type,
                (tracks[0] if tracks and tracks[0] else None),
                (orders[0] if orders and orders[0] else None),
                who,
                preview,
            ),
        )
        supplier_ids.append(sid)
        _add_job_event(
            conn,
            job_id,
            "supplier_order",
            f"Supplier {event_type}: {tracks[0] or orders[0] or subject}",
            {
                "tracking_numbers": facts.get("tracking_numbers"),
                "order_numbers": facts.get("order_numbers"),
                "sent": False,
            },
        )

    _record_processed(conn, msg, match, "matched")
    return {
        "status": "matched",
        "job_id": job_id,
        "note_id": note_id,
        "calendar_proposals": calendar_ids,
        "supplier_events": supplier_ids,
        "reason": match.get("reason"),
        "sent": False,
    }


def run_intake(*, messages: Optional[list] = None, conn=None) -> dict:
    """Read inboxes (or injected messages) and attach notes. Never sends."""
    injected = messages if messages is not None else fetch_raw_messages()
    owns = conn is None
    if owns:
        ctx = get_db()
        conn = ctx.__enter__()
    try:
        ensure_schema(conn)
        results = []
        for msg in injected:
            if not isinstance(msg, dict):
                continue
            results.append(_process_one(conn, msg))
        summary = {
            "read_only": True,
            "sent": False,
            "outbound_policy": OUTBOUND_POLICY,
            "accounts": connected_accounts(),
            "scanned": len(injected),
            "matched": sum(1 for r in results if r.get("status") == "matched"),
            "unmatched": sum(1 for r in results if r.get("status") == "unmatched"),
            "duplicates": sum(1 for r in results if r.get("status") == "duplicate"),
            "results": results,
        }
        return summary
    finally:
        if owns:
            ctx.__exit__(None, None, None)


def list_review_queue(conn=None, *, status: str = "unmatched", limit: int = 50) -> dict:
    owns = conn is None
    if owns:
        ctx = get_db()
        conn = ctx.__enter__()
    try:
        ensure_schema(conn)
        rows = conn.execute(
            "SELECT * FROM jmi_review_queue WHERE status = ? ORDER BY created_at DESC LIMIT ?",
            (status, limit),
        ).fetchall()
        return {
            "count": len(rows),
            "items": [dict(r) for r in rows],
            "read_only": True,
            "sent": False,
        }
    finally:
        if owns:
            ctx.__exit__(None, None, None)


def list_calendar_proposals(conn=None, *, status: str = "pending", limit: int = 50) -> dict:
    owns = conn is None
    if owns:
        ctx = get_db()
        conn = ctx.__enter__()
    try:
        ensure_schema(conn)
        rows = conn.execute(
            "SELECT * FROM jmi_calendar_proposals WHERE status = ? ORDER BY proposed_date ASC LIMIT ?",
            (status, limit),
        ).fetchall()
        return {
            "count": len(rows),
            "items": [dict(r) for r in rows],
            "read_only": True,
            "sent": False,
            "note": "Founder must approve before any calendar write.",
        }
    finally:
        if owns:
            ctx.__exit__(None, None, None)


def list_supplier_events(conn=None, *, job_id: Optional[str] = None, limit: int = 50) -> dict:
    owns = conn is None
    if owns:
        ctx = get_db()
        conn = ctx.__enter__()
    try:
        ensure_schema(conn)
        if job_id:
            rows = conn.execute(
                "SELECT * FROM jmi_supplier_order_events WHERE job_id = ? ORDER BY created_at DESC LIMIT ?",
                (job_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM jmi_supplier_order_events ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return {"count": len(rows), "items": [dict(r) for r in rows], "sent": False}
    finally:
        if owns:
            ctx.__exit__(None, None, None)


def list_timeline_notes(conn=None, *, job_id: Optional[str] = None, limit: int = 50) -> dict:
    owns = conn is None
    if owns:
        ctx = get_db()
        conn = ctx.__enter__()
    try:
        ensure_schema(conn)
        if job_id:
            rows = conn.execute(
                "SELECT * FROM jmi_timeline_notes WHERE job_id = ? ORDER BY created_at DESC LIMIT ?",
                (job_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT * FROM jmi_timeline_notes ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return {"count": len(rows), "items": [dict(r) for r in rows], "sent": False}
    finally:
        if owns:
            ctx.__exit__(None, None, None)


def approve_calendar_proposal(proposal_id: str, *, conn=None) -> dict:
    """Mark a proposed date approved. Writes a local Organizer draft only.

    Never talks to Google Calendar, never emails, never WhatsApps.
    """
    owns = conn is None
    if owns:
        ctx = get_db()
        conn = ctx.__enter__()
    try:
        ensure_schema(conn)
        row = conn.execute(
            "SELECT * FROM jmi_calendar_proposals WHERE id = ?", (proposal_id,)
        ).fetchone()
        if not row:
            return {"ok": False, "sent": False, "message": "proposal not found"}
        prop = dict(row)
        if prop.get("status") == "approved":
            return {"ok": True, "sent": False, "status": "already_approved", "proposal": prop}

        organizer_item_id = None
        try:
            from app.services.organizer.store import insert_item
            created = insert_item(conn, {
                "kind": prop.get("kind") or "deadline",
                "title": prop.get("title"),
                "job_id": prop.get("job_id"),
                "customer_id": prop.get("customer_id"),
                "start_time": prop.get("proposed_date"),
                "notes": f"Approved from job-mail intake. {prop.get('excerpt') or ''}",
                "status": "open",
                "source": "job_mail_intake",
            })
            organizer_item_id = (created or {}).get("id")
        except Exception:
            organizer_item_id = None

        conn.execute(
            """UPDATE jmi_calendar_proposals
               SET status = 'approved', approved_at = datetime('now'), sent = 0
               WHERE id = ?""",
            (proposal_id,),
        )
        _add_job_event(
            conn,
            prop.get("job_id"),
            "calendar_approved",
            f"Calendar {prop.get('kind')} approved for {prop.get('proposed_date')}",
            {"proposal_id": proposal_id, "organizer_item_id": organizer_item_id, "sent": False},
        )
        updated = dict(conn.execute(
            "SELECT * FROM jmi_calendar_proposals WHERE id = ?", (proposal_id,)
        ).fetchone())
        return {
            "ok": True,
            "sent": False,
            "status": "approved",
            "proposal": updated,
            "organizer_item_id": organizer_item_id,
            "outbound_policy": OUTBOUND_POLICY,
            "message": "Approved locally. Nothing was emailed or synced outbound.",
        }
    finally:
        if owns:
            ctx.__exit__(None, None, None)
