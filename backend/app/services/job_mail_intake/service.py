"""Run read-only job-mail intake. Never sends email or WhatsApp."""

from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime, timedelta
from typing import Optional

from app.db.database import get_db
from app.services.job_mail_intake.match import match_message
from app.services.job_mail_intake.readers import (
    OUTBOUND_POLICY,
    TEST_INBOX,
    JobMailFetchError,
    connected_accounts,
    fetch_raw_messages,
    intake_enabled,
)
from app.services.job_mail_intake.schema import ensure_schema

logger = logging.getLogger("job_mail_intake")

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

SCAN_ROW = "default"
MAX_BACKOFF_MINUTES = 120


def _new_id() -> str:
    return uuid.uuid4().hex[:16]


def _account(msg: dict) -> str:
    return (msg.get("account") or "").strip() or (
        "personal" if (msg.get("source") or "") == "gmail_personal" else "business"
    )


def _rfc_message_id(msg: dict) -> str:
    raw = (
        msg.get("rfc_message_id")
        or msg.get("internetMessageId")
        or ""
    )
    raw = str(raw).strip()
    if raw:
        return raw.strip("<>").strip().lower()
    return ""


def _fingerprint(msg: dict) -> str:
    rfc = _rfc_message_id(msg)
    if rfc:
        raw = f"msgid|{rfc}"
    else:
        raw = "|".join(
            str(msg.get(k) or "")
            for k in ("from", "subject", "date")
        )
        raw = f"fallback|{raw}"
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()


def _already(conn, fingerprint: str, rfc_id: str = "") -> bool:
    row = conn.execute(
        "SELECT 1 FROM jmi_processed WHERE fingerprint = ?", (fingerprint,)
    ).fetchone()
    if row:
        return True
    row = conn.execute(
        "SELECT 1 FROM jmi_review_queue WHERE fingerprint = ?", (fingerprint,)
    ).fetchone()
    if row:
        return True
    if rfc_id:
        row = conn.execute(
            "SELECT 1 FROM jmi_processed WHERE rfc_message_id = ?", (rfc_id,)
        ).fetchone()
        if row:
            return True
        row = conn.execute(
            "SELECT 1 FROM jmi_review_queue WHERE rfc_message_id = ?", (rfc_id,)
        ).fetchone()
        if row:
            return True
    return False


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
           (id, source, account, message_id, rfc_message_id, fingerprint, subject, from_addr,
            matched_job_id, matched_customer_id, match_reason, kind, status, sent)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'processed', 0)""",
        (
            _new_id(),
            msg.get("source") or "",
            _account(msg),
            str(msg.get("message_id") or ""),
            _rfc_message_id(msg) or None,
            _fingerprint(msg),
            msg.get("subject") or "",
            match.get("from_email") or "",
            match.get("job_id"),
            match.get("customer_id"),
            match.get("reason") or "",
            kind,
        ),
    )


def _scan_state(conn) -> dict:
    ensure_schema(conn)
    row = conn.execute("SELECT * FROM jmi_scan_state WHERE id = ?", (SCAN_ROW,)).fetchone()
    return dict(row) if row else {}


def _upsert_scan(conn, **fields) -> None:
    ensure_schema(conn)
    existing = _scan_state(conn)
    payload = {
        "last_success_at": existing.get("last_success_at"),
        "backoff_until": existing.get("backoff_until"),
        "fail_count": existing.get("fail_count") or 0,
        "last_error_type": existing.get("last_error_type"),
    }
    payload.update(fields)
    conn.execute(
        """INSERT INTO jmi_scan_state
           (id, last_success_at, backoff_until, fail_count, last_error_type, updated_at)
           VALUES (?, ?, ?, ?, ?, datetime('now'))
           ON CONFLICT(id) DO UPDATE SET
             last_success_at = excluded.last_success_at,
             backoff_until = excluded.backoff_until,
             fail_count = excluded.fail_count,
             last_error_type = excluded.last_error_type,
             updated_at = datetime('now')""",
        (
            SCAN_ROW,
            payload.get("last_success_at"),
            payload.get("backoff_until"),
            int(payload.get("fail_count") or 0),
            payload.get("last_error_type"),
        ),
    )


def _in_backoff(conn) -> Optional[str]:
    state = _scan_state(conn)
    until = state.get("backoff_until")
    if not until:
        return None
    try:
        if datetime.fromisoformat(str(until)) > datetime.utcnow():
            return str(until)
    except ValueError:
        return None
    return None


def _record_fetch_error(conn, exc: BaseException) -> dict:
    error_type = getattr(exc, "error_type", None) or type(exc).__name__
    status = getattr(exc, "status_code", None)
    state = _scan_state(conn)
    fails = int(state.get("fail_count") or 0) + 1
    if status == 429 or error_type in {"TooManyRequests", "HttpError"} and status == 429:
        minutes = min(15 * (2 ** min(fails - 1, 3)), MAX_BACKOFF_MINUTES)
    else:
        minutes = min(5 * fails, 30)
    until = (datetime.utcnow() + timedelta(minutes=minutes)).isoformat(timespec="seconds")
    _upsert_scan(conn, fail_count=fails, backoff_until=until, last_error_type=error_type)
    logger.error("Job-mail intake fetch failed: %s", error_type)
    return {
        "read_only": True,
        "sent": False,
        "outbound_policy": OUTBOUND_POLICY,
        "error_type": error_type,
        "backoff_until": until,
        "scanned": 0,
        "matched": 0,
        "unmatched": 0,
        "duplicates": 0,
        "results": [],
    }


def _record_success(conn) -> None:
    _upsert_scan(
        conn,
        last_success_at=datetime.utcnow().isoformat(timespec="seconds"),
        backoff_until=None,
        fail_count=0,
        last_error_type=None,
    )


def _process_one(conn, msg: dict) -> dict:
    fp = _fingerprint(msg)
    rfc_id = _rfc_message_id(msg)
    account = _account(msg)
    if not msg.get("message_id") and not rfc_id:
        return {"status": "skipped", "reason": "no_message_id", "sent": False}
    if not msg.get("message_id"):
        msg = dict(msg)
        msg["message_id"] = rfc_id or fp[:16]
    if _already(conn, fp, rfc_id):
        return {"status": "duplicate", "fingerprint": fp, "sent": False}

    match = match_message(conn, msg)
    facts = match.get("facts") or {}
    subject = (msg.get("subject") or "(no subject)").strip()
    preview = (msg.get("preview") or msg.get("body") or "")[:400]
    who = match.get("from_name") or match.get("from_email") or "unknown"
    summary = f"Email from {who}: {subject}"
    personal = account == "personal"

    if not match.get("matched") or not match.get("job_id"):
        conn.execute(
            """INSERT OR IGNORE INTO jmi_review_queue
               (id, source, account, message_id, rfc_message_id, fingerprint, subject,
                from_name, from_addr, preview, received_at, status, sent)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'unmatched', 0)""",
            (
                _new_id(),
                msg.get("source") or "",
                account,
                str(msg.get("message_id") or ""),
                rfc_id or None,
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
            "account": account,
            "sent": False,
        }

    job_id = match["job_id"]
    note_id = _new_id()
    conn.execute(
        """INSERT INTO jmi_timeline_notes
           (id, job_id, source, account, message_id, rfc_message_id, fingerprint,
            summary, excerpt, sent)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
        (
            note_id, job_id, msg.get("source"), account,
            str(msg.get("message_id") or ""), rfc_id or None, fp, summary, preview,
        ),
    )
    # Personal mail previews stay out of job_events unless the founder turns
    # that copy on later. Account is still stored on the jmi note.
    if not personal:
        _add_job_event(
            conn,
            job_id,
            "email_note",
            summary,
            {
                "source": msg.get("source"),
                "account": account,
                "message_id": msg.get("message_id"),
                "rfc_message_id": rfc_id,
                "subject": subject,
                "from": msg.get("from"),
                "sent": False,
            },
        )

    calendar_ids = []
    for prop in facts.get("proposed_dates") or []:
        cid = _new_id()
        conn.execute(
            """INSERT OR IGNORE INTO jmi_calendar_proposals
               (id, job_id, customer_id, source, account, message_id, rfc_message_id,
                fingerprint, title, proposed_date, kind, excerpt, status, sent)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', 0)""",
            (
                cid,
                job_id,
                match.get("customer_id"),
                msg.get("source"),
                account,
                str(msg.get("message_id") or ""),
                rfc_id or None,
                fp,
                f"{prop['kind'].title()} — {subject}"[:160],
                prop["date"],
                prop["kind"],
                prop.get("excerpt") or "",
            ),
        )
        row = conn.execute(
            "SELECT id FROM jmi_calendar_proposals WHERE fingerprint = ? AND proposed_date = ? AND kind = ?",
            (fp, prop["date"], prop["kind"]),
        ).fetchone()
        if row:
            calendar_ids.append(dict(row)["id"] if not isinstance(row, str) else row[0])

    supplier_ids = []
    if facts.get("is_supplier_order") or facts.get("tracking_numbers") or facts.get("order_numbers"):
        tracks = facts.get("tracking_numbers") or [None]
        orders = facts.get("order_numbers") or [None]
        event_type = "tracking" if facts.get("tracking_numbers") else "order_confirmation"
        sid = _new_id()
        conn.execute(
            """INSERT OR IGNORE INTO jmi_supplier_order_events
               (id, job_id, source, account, message_id, rfc_message_id, fingerprint,
                event_type, tracking_number, order_number, supplier_name, excerpt, sent)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)""",
            (
                sid,
                job_id,
                msg.get("source"),
                account,
                str(msg.get("message_id") or ""),
                rfc_id or None,
                fp,
                event_type,
                (tracks[0] if tracks and tracks[0] else None),
                (orders[0] if orders and orders[0] else None),
                who,
                preview if not personal else None,
            ),
        )
        row = conn.execute(
            "SELECT id FROM jmi_supplier_order_events WHERE fingerprint = ?", (fp,)
        ).fetchone()
        if row:
            supplier_ids.append(dict(row)["id"] if not isinstance(row, str) else row[0])
        if not personal:
            _add_job_event(
                conn,
                job_id,
                "supplier_order",
                f"Supplier {event_type}: {tracks[0] or orders[0] or subject}",
                {
                    "account": account,
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
        "account": account,
        "calendar_proposals": calendar_ids,
        "supplier_events": supplier_ids,
        "reason": match.get("reason"),
        "sent": False,
    }


def run_intake(*, messages: Optional[list] = None, conn=None) -> dict:
    """Read inboxes (or injected messages) and attach notes. Never sends."""
    owns = conn is None
    if owns:
        ctx = get_db()
        conn = ctx.__enter__()
    try:
        ensure_schema(conn)
        if messages is None and not intake_enabled():
            return {
                "read_only": True,
                "sent": False,
                "outbound_policy": OUTBOUND_POLICY,
                "disabled": True,
                "scanned": 0,
                "matched": 0,
                "unmatched": 0,
                "duplicates": 0,
                "results": [],
            }
        if messages is None:
            until = _in_backoff(conn)
            if until:
                return {
                    "read_only": True,
                    "sent": False,
                    "outbound_policy": OUTBOUND_POLICY,
                    "backoff_until": until,
                    "scanned": 0,
                    "matched": 0,
                    "unmatched": 0,
                    "duplicates": 0,
                    "results": [],
                }
        since = None
        if messages is None:
            since = (_scan_state(conn) or {}).get("last_success_at")
        try:
            injected = messages if messages is not None else fetch_raw_messages(since=since)
        except JobMailFetchError as exc:
            return _record_fetch_error(conn, exc)
        except Exception as exc:
            return _record_fetch_error(conn, JobMailFetchError(type(exc).__name__))

        results = []
        for msg in injected:
            if not isinstance(msg, dict):
                continue
            results.append(_process_one(conn, msg))
        if messages is None:
            _record_success(conn)
        return {
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


def approve_calendar_proposal(proposal_id: str, *, conn=None, approved_by: str = "founder") -> dict:
    """Mark a proposed date approved. Writes a local Organizer draft only.

    Never talks to Google Calendar, never emails, never WhatsApps.
    If the Organizer insert fails the proposal stays pending.
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
            if not organizer_item_id:
                raise RuntimeError("insert_item returned no id")
        except Exception:
            pending = dict(conn.execute(
                "SELECT * FROM jmi_calendar_proposals WHERE id = ?", (proposal_id,)
            ).fetchone())
            return {
                "ok": False,
                "sent": False,
                "status": "pending",
                "proposal": pending,
                "error_type": "OrganizerInsertError",
                "message": "Calendar proposal left pending; organizer insert failed.",
            }

        who = (approved_by or "founder").strip() or "founder"
        conn.execute(
            """UPDATE jmi_calendar_proposals
               SET status = 'approved', approved_at = datetime('now'), approved_by = ?, sent = 0
               WHERE id = ?""",
            (who, proposal_id),
        )
        _add_job_event(
            conn,
            prop.get("job_id"),
            "calendar_approved",
            f"Calendar {prop.get('kind')} approved for {prop.get('proposed_date')}",
            {
                "proposal_id": proposal_id,
                "organizer_item_id": organizer_item_id,
                "approved_by": who,
                "sent": False,
            },
        )
        updated = dict(conn.execute(
            "SELECT * FROM jmi_calendar_proposals WHERE id = ?", (proposal_id,)
        ).fetchone())
        return {
            "ok": True,
            "sent": False,
            "status": "approved",
            "proposal": updated,
            "approved_by": who,
            "organizer_item_id": organizer_item_id,
            "outbound_policy": OUTBOUND_POLICY,
            "message": "Approved locally. Nothing was emailed or synced outbound.",
        }
    finally:
        if owns:
            ctx.__exit__(None, None, None)
