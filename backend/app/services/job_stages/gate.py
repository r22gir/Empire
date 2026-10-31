"""Client-estimate and share/export gates. Stage 4 must be approved."""
from __future__ import annotations

import json
import re
from typing import Any

from app.db.database import get_db
from app.services.job_stages.catalog import (
    GATE_STAGE_KEY,
    RAFAEL_ACTORS,
    RAFAEL_SEND_PHRASES,
    STAGE_WORKROOM,
    STATUS_APPROVED,
    STATUS_DONE,
    stage_definition,
)
from app.services.job_stages.schema import init_job_stages_schema

GATE_CODE = "WORKROOM_APPROVAL_REQUIRED"
SEND_GATE_CODE = "RAFAEL_EXPRESS_SEND_REQUIRED"


class ClientEstimateGateError(Exception):
    """Raised when a client estimate or share/export is blocked."""

    def __init__(self, message: str, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.payload = payload or {}
        self.status_code = 409

    def as_dict(self) -> dict[str, Any]:
        body = {
            "error": GATE_CODE,
            "detail": self.message,
            "gate": GATE_STAGE_KEY,
        }
        body.update(self.payload)
        return body


class SquareSendGateError(Exception):
    """Square invoices stay draft until Rafael expressly says send."""

    def __init__(self, message: str, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.payload = payload or {}
        self.status_code = 409

    def as_dict(self) -> dict[str, Any]:
        body = {
            "error": SEND_GATE_CODE,
            "detail": self.message,
            "sent": False,
            "auto_send": False,
        }
        body.update(self.payload)
        return body


def _row(conn, job_id: str):
    return conn.execute(
        """SELECT id, title, client_name, quote_id, metadata, current_revision
           FROM jobs WHERE id = ?""",
        (job_id,),
    ).fetchone()


def workroom_approval_state(job_id: str) -> dict[str, Any]:
    from app.services.job_stages.service import ensure_job_stages, get_stage

    with get_db() as conn:
        init_job_stages_schema(conn)
        job = _row(conn, job_id)
        if not job:
            raise ClientEstimateGateError(
                f"Job {job_id} not found.",
                {"job_id": job_id, "found": False},
            )
        ensure_job_stages(conn, job_id)
        stage = get_stage(conn, job_id, STAGE_WORKROOM)
    status = (stage or {}).get("status") or "not_started"
    approved = status in {STATUS_APPROVED, STATUS_DONE}
    definition = stage_definition(STAGE_WORKROOM)
    return {
        "job_id": job_id,
        "job_title": job["title"] if job else None,
        "stage_key": STAGE_WORKROOM,
        "stage_title": definition["title"],
        "status": status,
        "approved": approved,
        "approved_by": (stage or {}).get("approved_by"),
        "approved_at": (stage or {}).get("approved_at"),
        "allowed": approved,
    }


def assert_client_estimate_allowed(job_id: str) -> dict[str, Any]:
    """No client estimate generation or share/export until stage 4 is approved."""
    state = workroom_approval_state(job_id)
    if state["allowed"]:
        return state
    raise ClientEstimateGateError(
        "Workroom approval (stage 4) must be approved before a client "
        "estimate can be generated, shared, or exported.",
        {
            "job_id": job_id,
            "required_stage": STAGE_WORKROOM,
            "required_status": STATUS_APPROVED,
            "current_status": state["status"],
            "blocked": True,
            "next_step": (
                "Workroom must approve the 3-page approval document "
                "before any estimate goes to the client."
            ),
        },
    )


def assert_share_export_allowed(job_id: str) -> dict[str, Any]:
    return assert_client_estimate_allowed(job_id)


def resolve_job_id_for_quote(quote_id: str | None) -> str | None:
    if not quote_id:
        return None
    with get_db() as conn:
        row = conn.execute(
            "SELECT id FROM jobs WHERE quote_id = ? ORDER BY created_at DESC LIMIT 1",
            (quote_id,),
        ).fetchone()
        if row:
            return row["id"]
        try:
            qrow = conn.execute(
                "SELECT job_id FROM quotes_v2 WHERE id = ? OR quote_number = ?",
                (quote_id, quote_id),
            ).fetchone()
        except Exception:
            qrow = None
        if qrow and qrow["job_id"]:
            return qrow["job_id"]
    return None


def assert_client_estimate_allowed_for_quote(quote_id: str | None) -> dict[str, Any] | None:
    """Gate quote PDF / share when the quote is linked to a job. Unlinked quotes pass."""
    job_id = resolve_job_id_for_quote(quote_id)
    if not job_id:
        return None
    return assert_client_estimate_allowed(job_id)


def rafael_expressly_said_send(
    *,
    authorized_by: str | None = None,
    express_send: bool = False,
    send_phrase: str | None = None,
) -> bool:
    """True only when Rafael expressly authorized a send. Never inferred."""
    actor = (authorized_by or "").strip().lower()
    phrase = (send_phrase or "").strip().lower()
    if actor not in RAFAEL_ACTORS:
        return False
    if express_send and phrase:
        return any(token in phrase for token in RAFAEL_SEND_PHRASES) or phrase in {
            "send", "please send", "send it", "send the invoice",
        }
    if express_send:
        return True
    if phrase and any(token in phrase for token in RAFAEL_SEND_PHRASES):
        return True
    return False


def assert_square_send_allowed(
    *,
    authorized_by: str | None = None,
    express_send: bool = False,
    send_phrase: str | None = None,
) -> dict[str, Any]:
    if rafael_expressly_said_send(
        authorized_by=authorized_by,
        express_send=express_send,
        send_phrase=send_phrase,
    ):
        return {
            "allowed": True,
            "authorized_by": authorized_by,
            "express_send": True,
            "auto_send": False,
        }
    raise SquareSendGateError(
        "Square invoice stays a draft until Rafael expressly says send. "
        "Nothing was sent.",
        {
            "allowed": False,
            "status": "draft",
            "authorized_by": authorized_by,
            "express_send": False,
        },
    )


_JOB_MENTION = re.compile(
    r"\b(?:job|jobs)\b.{0,40}\b([A-Za-z0-9][A-Za-z0-9 '&._-]{1,40})\b"
    r"|\b([A-Za-z][A-Za-z0-9 '&._-]{1,40})\b.{0,20}\bjob\b",
    re.I,
)


_STOP = {
    "status", "stage", "checklist", "progress", "where", "is", "this",
    "the", "a", "an", "please", "now", "at", "on", "with", "for",
}


def extract_job_query(message: str | None) -> str | None:
    """Pull a job name / number out of a 'where is this job' question."""
    text = (message or "").strip()
    if not text:
        return None
    numbered = re.search(r"\b(JOB-\d{4}-\d+)\b", text, re.I)
    if numbered:
        return numbered.group(1)
    hex_id = re.search(r"\b([a-f0-9]{12,})\b", text, re.I)
    if hex_id:
        return hex_id.group(1)
    after = re.search(
        r"\b(?:this\s+)?(?:the\s+)?job\s+(?:called\s+|named\s+|for\s+|—\s*|-\s*)?"
        r"([A-Za-z0-9][A-Za-z0-9 '&._-]{1,40})",
        text,
        re.I,
    )
    if after:
        token = after.group(1).strip(" ?.,:—-")
        if token.lower() not in _STOP:
            return token
    match = _JOB_MENTION.search(text)
    if match:
        token = (match.group(1) or match.group(2) or "").strip(" ?.,")
        if token.lower() not in _STOP:
            return token
    return None
