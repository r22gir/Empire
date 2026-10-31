"""Square invoices are always drafts until Rafael expressly says send."""
from __future__ import annotations

from typing import Any

from app.db.database import dict_row, get_db
from app.services.job_stages.catalog import STAGE_INVOICE, STATUS_DRAFTED, STATUS_DONE
from app.services.job_stages.gate import SquareSendGateError, assert_square_send_allowed
from app.services.job_stages.schema import init_job_stages_schema
from app.services.job_stages.service import (
    ensure_job_stages,
    register_document,
    set_stage_status,
)


def create_square_invoice_draft(
    job_id: str,
    *,
    amount: float | None = None,
    notes: str | None = None,
) -> dict[str, Any]:
    """Record a draft Square invoice. Does not call Square. Does not send."""
    with get_db() as conn:
        init_job_stages_schema(conn)
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            raise ValueError(f"Job {job_id} not found")
        ensure_job_stages(conn, job_id)
        set_stage_status(conn, job_id, STAGE_INVOICE, STATUS_DRAFTED, notes=notes or "square draft")
        doc = register_document(
            conn,
            job_id=job_id,
            document_type="square_invoice",
            url=f"draft://square/{job_id}",
            audience="client",
            visible_to_client=False,
            stage_key=STAGE_INVOICE,
            area=dict_row(job).get("room") or "Job",
            client=dict_row(job).get("client_name") or dict_row(job).get("title"),
            extension="json",
        )
    return {
        "job_id": job_id,
        "status": "draft",
        "sent": False,
        "auto_send": False,
        "amount": amount,
        "document": doc,
        "note": "Draft only. Nothing was sent. Rafael must expressly say send.",
    }


def send_square_invoice(
    job_id: str,
    *,
    authorized_by: str | None = None,
    express_send: bool = False,
    send_phrase: str | None = None,
) -> dict[str, Any]:
    """Refuse unless Rafael expressly said send. Still performs no outbound send."""
    assert_square_send_allowed(
        authorized_by=authorized_by,
        express_send=express_send,
        send_phrase=send_phrase,
    )
    # Authorization passed — still no network call. Mark the local stage done
    # so the checklist records the express instruction. Outbound Square send
    # is founder-manual outside this service.
    with get_db() as conn:
        init_job_stages_schema(conn)
        set_stage_status(
            conn, job_id, STAGE_INVOICE, STATUS_DONE,
            actor=authorized_by, notes="express send authorized; no auto-send performed",
        )
    return {
        "job_id": job_id,
        "status": "authorized_draft",
        "sent": False,
        "auto_send": False,
        "authorized_by": authorized_by,
        "note": (
            "Rafael authorized send. This service does not transmit the "
            "invoice. Send remains founder-manual."
        ),
    }


def refuse_auto_send(job_id: str) -> dict[str, Any]:
    raise SquareSendGateError(
        "Square invoice is always a draft until Rafael expressly says send. "
        "Auto-send is disabled.",
        {"job_id": job_id, "sent": False, "auto_send": False, "status": "draft"},
    )
