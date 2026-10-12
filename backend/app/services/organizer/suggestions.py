"""Suggested-to-do tray. Harvest only. Nothing is created until the owner taps Accept."""

from __future__ import annotations

import json
from typing import Optional

from app.services.organizer.constants import OUTBOUND_POLICY
from app.services.organizer.edition import can_read_workroom_jobs, edition_sql, process_edition
from app.services.organizer.parse import infer_space
from app.services.organizer.store import insert_item, new_id, now_iso

# Tests assign extra harvest rows here (never live connectors).
TEST_EXTRA: Optional[list] = None


def _upsert(conn, row: dict) -> dict:
    edition = process_edition()
    existing = conn.execute(
        """SELECT * FROM organizer_suggestions
           WHERE edition = ? AND source = ? AND source_ref = ?""",
        (edition, row["source"], row["source_ref"]),
    ).fetchone()
    stamp = now_iso()
    if existing:
        data = dict(existing)
        if data.get("status") != "pending":
            return data
        return data
    sid = new_id()
    conn.execute(
        """INSERT INTO organizer_suggestions
           (id, edition, source, source_ref, title, body, kind, space_id, job_id,
            quote_id, capture_id, status, payload_json, created_at, updated_at)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending', ?, ?, ?)""",
        (
            sid, edition, row["source"], row["source_ref"], row["title"],
            row.get("body"), row.get("kind") or "todo", row.get("space_id"),
            row.get("job_id"), row.get("quote_id"), row.get("capture_id"),
            json.dumps(row.get("payload") or {}), stamp, stamp,
        ),
    )
    return dict(conn.execute("SELECT * FROM organizer_suggestions WHERE id = ?", (sid,)).fetchone())


def harvest(conn) -> list[dict]:
    """Read pending mail, WhatsApp/voice captures, approved estimates. No items written."""
    created: list[dict] = []
    try:
        from app.services.organizer.mail import list_pending
        mail = list_pending(conn, limit=40)
        for msg in mail.get("items") or []:
            title = (msg.get("subject") or "Incoming mail").strip() or "Incoming mail"
            created.append(_upsert(conn, {
                "source": "email",
                "source_ref": msg.get("id") or f"{msg.get('source')}:{msg.get('message_id')}",
                "title": f"Follow up: {title}",
                "body": msg.get("preview") or msg.get("from_name") or "",
                "kind": "todo",
                "space_id": msg.get("space_id") or infer_space(title),
                "job_id": msg.get("job_id"),
                "payload": {"from": msg.get("from_name"), "open_href": msg.get("open_href")},
            }))
    except Exception:
        pass

    clause, params = edition_sql()
    try:
        caps = conn.execute(
            f"""SELECT * FROM organizer_captures WHERE {clause}
                AND (source LIKE '%whatsapp%' OR source LIKE '%voice%' OR source LIKE '%note%')
                ORDER BY created_at DESC LIMIT 40""",
            params,
        ).fetchall()
        for cap in caps:
            data = dict(cap)
            src = (data.get("source") or "").lower()
            kind_src = "whatsapp" if "whatsapp" in src else "voice"
            created.append(_upsert(conn, {
                "source": kind_src,
                "source_ref": data["id"],
                "title": data.get("caption") or data.get("filename") or ("Voice note" if kind_src == "voice" else "WhatsApp note"),
                "body": data.get("caption") or "",
                "kind": "todo",
                "space_id": data.get("space_id") or infer_space(data.get("caption") or ""),
                "job_id": data.get("job_id"),
                "capture_id": data["id"],
            }))
    except Exception:
        pass

    if can_read_workroom_jobs():
        try:
            quotes = conn.execute(
                """SELECT id, quote_number, customer_name, project_name, status, job_id
                   FROM quotes_v2
                   WHERE lower(COALESCE(status,'')) IN ('approved','accepted','won')
                   ORDER BY updated_at DESC LIMIT 20"""
            ).fetchall()
            for q in quotes:
                data = dict(q)
                created.append(_upsert(conn, {
                    "source": "estimate",
                    "source_ref": data["id"],
                    "title": f"Start job from {data.get('quote_number') or 'estimate'} — {data.get('customer_name') or data.get('project_name') or 'client'}",
                    "body": "Approved estimate. Accept to make a to-do. Nothing is created until you tap.",
                    "kind": "todo",
                    "space_id": "workroom",
                    "job_id": data.get("job_id"),
                    "quote_id": data["id"],
                }))
        except Exception:
            pass

    for extra in TEST_EXTRA or []:
        created.append(_upsert(conn, extra))
    return created


def list_suggestions(conn, *, status: str = "pending") -> list[dict]:
    harvest(conn)
    clause, params = edition_sql()
    rows = conn.execute(
        f"""SELECT * FROM organizer_suggestions
            WHERE {clause} AND status = ?
            ORDER BY created_at DESC LIMIT 80""",
        (*params, status),
    ).fetchall()
    return [dict(r) for r in rows]


def accept_suggestion(conn, suggestion_id: str) -> dict:
    clause, params = edition_sql()
    row = conn.execute(
        f"SELECT * FROM organizer_suggestions WHERE id = ? AND {clause}",
        (suggestion_id, *params),
    ).fetchone()
    if not row:
        return {"ok": False, "created": False, "sent": False, "message": "Suggestion not found"}
    data = dict(row)
    if data.get("status") != "pending":
        return {"ok": True, "created": False, "sent": False, "suggestion": data, "message": "Already handled"}
    item = insert_item(conn, {
        "kind": data.get("kind") or "todo",
        "title": data["title"],
        "notes": data.get("body"),
        "space_id": data.get("space_id"),
        "job_id": data.get("job_id"),
        "quote_id": data.get("quote_id"),
        "capture_id": data.get("capture_id"),
        "created_by": "max",
        "status": "open",
    })
    conn.execute(
        "UPDATE organizer_suggestions SET status = 'accepted', updated_at = ? WHERE id = ?",
        (now_iso(), suggestion_id),
    )
    return {
        "ok": True,
        "created": True,
        "sent": False,
        "item": item,
        "outbound_policy": OUTBOUND_POLICY,
        "message": "To-do saved. Nothing was sent.",
    }


def dismiss_suggestion(conn, suggestion_id: str) -> dict:
    clause, params = edition_sql()
    conn.execute(
        f"UPDATE organizer_suggestions SET status = 'dismissed', updated_at = ? WHERE id = ? AND {clause}",
        (now_iso(), suggestion_id, *params),
    )
    return {"ok": True, "created": False, "sent": False, "message": "Dismissed. Nothing was created."}
