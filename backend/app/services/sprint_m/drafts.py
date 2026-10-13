"""Outbound messages are drafts only. Max never sends to clients."""

from __future__ import annotations

import json
import uuid
from app.services.sprint_m.store import audit, get_store, now_iso, row_to_dict

MAX_NEVER_SENDS = "Max never sends to clients. Owner must approve, then send the draft from their own device."


class DraftSendForbidden(PermissionError):
    def __init__(self, message: str = MAX_NEVER_SENDS):
        super().__init__(message)


def _parse(value, default):
    if value is None:
        return default
    if isinstance(value, (list, dict)):
        return value
    try:
        return json.loads(value)
    except (TypeError, json.JSONDecodeError):
        return default


def create_draft(
    *,
    channel: str,
    body: str,
    job_id: str | None = None,
    customer_id: str | None = None,
    to_address: str | None = None,
    subject: str | None = None,
    source: str = "owner",
    rule_id: str | None = None,
    metadata: dict | None = None,
    actor: str = "system",
) -> dict:
    draft_id = str(uuid.uuid4())[:12]
    now = now_iso()
    with get_store() as conn:
        conn.execute(
            """INSERT INTO sm_drafts (
                id, job_id, customer_id, channel, to_address, subject, body,
                status, approval_required, source, rule_id, metadata_json, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'draft', 1, ?, ?, ?, ?, ?)""",
            (
                draft_id,
                job_id,
                customer_id,
                channel,
                to_address,
                subject,
                body,
                source,
                rule_id,
                json.dumps(metadata or {}),
                now,
                now,
            ),
        )
        audit(conn, "draft", draft_id, "created", actor, channel)
    return get_draft(draft_id)


def get_draft(draft_id: str) -> dict:
    with get_store() as conn:
        row = conn.execute("SELECT * FROM sm_drafts WHERE id = ?", (draft_id,)).fetchone()
        if not row:
            raise KeyError(f"Draft {draft_id} not found")
        draft = row_to_dict(row)
        draft["metadata"] = _parse(draft.pop("metadata_json", "{}"), {})
        draft["max_sends_to_clients"] = False
        draft["send_policy"] = MAX_NEVER_SENDS
        return draft


def list_drafts(status: str | None = None, job_id: str | None = None) -> list[dict]:
    clauses = []
    params: list = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if job_id:
        clauses.append("job_id = ?")
        params.append(job_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with get_store() as conn:
        rows = conn.execute(
            f"SELECT * FROM sm_drafts {where} ORDER BY created_at DESC",
            params,
        ).fetchall()
    out = []
    for row in rows:
        draft = row_to_dict(row)
        draft["metadata"] = _parse(draft.pop("metadata_json", "{}"), {})
        draft["max_sends_to_clients"] = False
        out.append(draft)
    return out


def approve_draft(draft_id: str, *, actor: str = "owner") -> dict:
    if actor not in {"owner", "founder", "rafael"}:
        raise PermissionError("Only the owner can approve outbound drafts")
    now = now_iso()
    with get_store() as conn:
        row = conn.execute("SELECT id, status FROM sm_drafts WHERE id = ?", (draft_id,)).fetchone()
        if not row:
            raise KeyError(f"Draft {draft_id} not found")
        conn.execute(
            """UPDATE sm_drafts
               SET status = 'approved', approved_by = ?, approved_at = ?, updated_at = ?
               WHERE id = ?""",
            (actor, now, now, draft_id),
        )
        audit(conn, "draft", draft_id, "approved", actor, "owner_approved_not_sent")
    return get_draft(draft_id)


def reject_send(draft_id: str | None = None) -> None:
    """Hard block. Max has no send path for client drafts."""
    raise DraftSendForbidden()
