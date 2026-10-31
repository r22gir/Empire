"""Client-estimate and share/export gates. Stage 4 must be approved."""
from __future__ import annotations

import json
import re
from typing import Any

from app.db.database import dict_row, get_db
from app.services.job_stages.catalog import (
    GATE_STAGE_KEY,
    MAX_APPROVE_BLOCKLIST,
    RAFAEL_ACTORS,
    RAFAEL_SEND_PHRASES,
    STAGE_WORKROOM,
    STATUS_APPROVED,
    STATUS_DONE,
    WORKROOM_APPROVERS,
    stage_definition,
)
from app.services.job_stages.schema import get_gate_cutover_at, init_job_stages_schema

GATE_CODE = "WORKROOM_APPROVAL_REQUIRED"
SEND_GATE_CODE = "RAFAEL_EXPRESS_SEND_REQUIRED"
APPROVAL_DENIED_CODE = "STAGE_APPROVAL_DENIED"


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


class StageApprovalDenied(Exception):
    """Stage 4 approval is limited to Rafael or the workroom. Max cannot approve."""

    def __init__(self, message: str, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.payload = payload or {}
        self.status_code = 403

    def as_dict(self) -> dict[str, Any]:
        body = {
            "error": APPROVAL_DENIED_CODE,
            "detail": self.message,
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
    """Load a job without assuming every deploy has gate_enforced yet."""
    try:
        return conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    except Exception:
        return None


def job_is_gate_enforced(job: dict[str, Any] | None, conn=None) -> bool:
    """Stage 4 gate applies only to jobs created after the deploy cutover.

    Explicit jobs.gate_enforced wins. Missing/deleted jobs are never gated.
    """
    if not job:
        return False
    flag = job.get("gate_enforced")
    if flag is not None and str(flag) != "":
        try:
            return int(flag) == 1
        except (TypeError, ValueError):
            pass
    created = str(job.get("created_at") or "")
    cutover = get_gate_cutover_at(conn) if conn is not None else None
    if not created or not cutover:
        return False
    return created >= str(cutover)


def workroom_approval_state(job_id: str) -> dict[str, Any]:
    from app.services.job_stages.service import ensure_job_stages, get_stage

    with get_db() as conn:
        init_job_stages_schema(conn)
        job = _row(conn, job_id)
        if not job:
            return {
                "job_id": job_id,
                "found": False,
                "job_missing": True,
                "gate_enforced": False,
                "allowed": True,
                "grandfathered": False,
                "stage_key": STAGE_WORKROOM,
                "status": None,
                "approved": False,
            }
        job_dict = dict_row(job) if not isinstance(job, dict) else job
        enforced = job_is_gate_enforced(job_dict, conn)
        ensure_job_stages(conn, job_id)
        stage = get_stage(conn, job_id, STAGE_WORKROOM)
    status = (stage or {}).get("status") or "not_started"
    approved = status in {STATUS_APPROVED, STATUS_DONE}
    definition = stage_definition(STAGE_WORKROOM)
    return {
        "job_id": job_id,
        "found": True,
        "job_title": job_dict.get("title"),
        "stage_key": STAGE_WORKROOM,
        "stage_title": definition["title"],
        "status": status,
        "approved": approved,
        "approved_by": (stage or {}).get("approved_by"),
        "approved_at": (stage or {}).get("approved_at"),
        "gate_enforced": enforced,
        "grandfathered": not enforced,
        "allowed": (not enforced) or approved,
    }


def assert_client_estimate_allowed(job_id: str) -> dict[str, Any]:
    """No client estimate generation or share/export until stage 4 is approved.

    Jobs created before the cutover (gate_enforced=0), and quotes whose job
    was deleted, are allowed through.
    """
    state = workroom_approval_state(job_id)
    if state.get("allowed"):
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
            "gate_enforced": True,
            "next_step": (
                "Workroom must approve the 3-page approval document "
                "before any estimate goes to the client."
            ),
        },
    )


def assert_share_export_allowed(job_id: str) -> dict[str, Any]:
    return assert_client_estimate_allowed(job_id)


def resolve_job_id_for_quote(quote_id: str | None) -> str | None:
    """Return a live job id for this quote, or None if unlinked / job deleted."""
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
        stale_id = qrow["job_id"] if qrow and qrow["job_id"] else None
        if not stale_id:
            return None
        exists = conn.execute("SELECT id FROM jobs WHERE id = ?", (stale_id,)).fetchone()
        if not exists:
            return None
        return stale_id


def assert_client_estimate_allowed_for_quote(quote_id: str | None) -> dict[str, Any] | None:
    """Gate quote PDF / share when the quote is linked to a live, post-cutover job.

    Unlinked quotes and quotes whose job was deleted pass.
    """
    job_id = resolve_job_id_for_quote(quote_id)
    if not job_id:
        return None
    return assert_client_estimate_allowed(job_id)


def can_approve_workroom_stage(actor: str | None) -> bool:
    name = (actor or "").strip().lower()
    if not name:
        return False
    if name in MAX_APPROVE_BLOCKLIST or name.startswith("max"):
        return False
    return name in WORKROOM_APPROVERS


def assert_can_approve_workroom_stage(actor: str | None) -> str:
    name = (actor or "").strip()
    if can_approve_workroom_stage(name):
        return name
    raise StageApprovalDenied(
        "Only Rafael or the workroom can approve stage 4. Max cannot approve.",
        {"actor": actor, "stage_key": STAGE_WORKROOM, "allowed": False},
    )


def client_estimate_gate_http_response(exc: ClientEstimateGateError):
    """The single FastAPI conversion of the gate error to HTTP 409."""
    from fastapi.responses import JSONResponse
    return JSONResponse(status_code=409, content=exc.as_dict())


def register_job_stage_exception_handlers(app) -> None:
    """Register once so no quote_pdf_service caller surfaces a 500."""
    from fastapi import Request
    from fastapi.responses import JSONResponse

    @app.exception_handler(ClientEstimateGateError)
    async def _gate_409(_request: Request, exc: ClientEstimateGateError):
        return client_estimate_gate_http_response(exc)

    @app.exception_handler(StageApprovalDenied)
    async def _approve_403(_request: Request, exc: StageApprovalDenied):
        return JSONResponse(status_code=403, content=exc.as_dict())


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
