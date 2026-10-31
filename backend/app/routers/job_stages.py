"""Job document-set checklist, naming, estimate gate, and Square draft endpoints."""
from __future__ import annotations

import base64
from typing import Optional

from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.services.job_stages.backfill import backfill_all_jobs, backfill_job_stages
from app.services.job_stages.catalog import STAGES, infer_stage_key
from app.services.job_stages.estimates import generate_estimate_copies
from app.services.job_stages.gate import (
    ClientEstimateGateError,
    SquareSendGateError,
    StageApprovalDenied,
    assert_client_estimate_allowed,
    assert_share_export_allowed,
)
from app.services.job_stages.max_answer import locate_job
from app.services.job_stages.naming import build_standard_name, next_revision
from app.services.job_stages.schema import init_job_stages_schema
from app.services.job_stages.service import (
    approve_stage,
    ensure_job_stages,
    get_checklist,
    job_location,
    register_document,
    set_stage_status,
)
from app.services.job_stages.square_invoice import (
    create_square_invoice_draft,
    refuse_auto_send,
    send_square_invoice,
)
from app.services.job_stages.workroom_approval import render_workroom_approval_pdf

router = APIRouter(tags=["job-stages"])


class StatusBody(BaseModel):
    status: str
    actor: Optional[str] = None
    notes: Optional[str] = None


class ApproveBody(BaseModel):
    approved_by: str = Field(..., min_length=1)


class NamePreviewBody(BaseModel):
    client: Optional[str] = None
    area: Optional[str] = None
    document_type: str
    stage_key: Optional[str] = None
    internal: bool = False
    extension: Optional[str] = None
    revision: Optional[int] = None


class RegisterDocumentBody(BaseModel):
    document_type: str
    url: str
    filename: Optional[str] = None
    item_key: Optional[str] = None
    route_to: Optional[str] = None
    visible_to_client: bool = False
    audience: Optional[str] = None
    stage_key: Optional[str] = None
    area: Optional[str] = None
    client: Optional[str] = None
    extension: Optional[str] = None


class EstimateBody(BaseModel):
    lines: list[dict] = Field(default_factory=list)
    area: Optional[str] = None
    client_name: Optional[str] = None
    job_number: Optional[str] = None
    terms: Optional[str] = None
    square_pay_url: Optional[str] = None
    audience: str = "client"


class WorkroomApprovalBody(BaseModel):
    client_name: Optional[str] = None
    area: Optional[str] = None
    job_number: Optional[str] = None
    title: Optional[str] = None
    measurements: Optional[dict] = None
    measurement_lines: Optional[list[str]] = None
    lines: list[dict] = Field(default_factory=list)
    terms: Optional[str] = None
    elevation_path: Optional[str] = None
    site_photo_path: Optional[str] = None


class SquareDraftBody(BaseModel):
    amount: Optional[float] = None
    notes: Optional[str] = None


class SquareSendBody(BaseModel):
    authorized_by: Optional[str] = None
    express_send: bool = False
    send_phrase: Optional[str] = None


def _gate_response(exc: ClientEstimateGateError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content=exc.as_dict())


def _job_or_404(job_id: str) -> None:
    with get_db() as conn:
        init_job_stages_schema(conn)
        row = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Job not found")


@router.get("/job-stages/catalog")
def stage_catalog():
    return {"stages": list(STAGES)}


@router.get("/jobs/{job_id}/stages")
def get_job_stages(job_id: str):
    _job_or_404(job_id)
    return get_checklist(job_id)


@router.post("/jobs/{job_id}/stages/ensure")
def ensure_stages(job_id: str):
    _job_or_404(job_id)
    with get_db() as conn:
        stages = ensure_job_stages(conn, job_id)
    return {"job_id": job_id, "stages": stages}


@router.post("/jobs/{job_id}/stages/backfill")
def backfill_one_job(job_id: str):
    _job_or_404(job_id)
    with get_db() as conn:
        result = backfill_job_stages(conn, job_id)
        result["location"] = job_location(conn, job_id)
    return result


@router.post("/jobs/stages/backfill")
def backfill_every_job():
    with get_db() as conn:
        return backfill_all_jobs(conn)


@router.patch("/jobs/{job_id}/stages/{stage_key}")
def patch_stage(job_id: str, stage_key: str, body: StatusBody):
    _job_or_404(job_id)
    try:
        with get_db() as conn:
            stage = set_stage_status(
                conn, job_id, stage_key, body.status,
                actor=body.actor, notes=body.notes,
            )
    except StageApprovalDenied as exc:
        return JSONResponse(status_code=403, content=exc.as_dict())
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"stage": stage}


@router.post("/jobs/{job_id}/stages/{stage_key}/approve")
def approve_job_stage(job_id: str, stage_key: str, body: ApproveBody):
    _job_or_404(job_id)
    try:
        with get_db() as conn:
            stage = approve_stage(conn, job_id, stage_key, body.approved_by)
    except StageApprovalDenied as exc:
        return JSONResponse(status_code=403, content=exc.as_dict())
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"stage": stage, "gate_open": stage_key == "workroom_approval"}


@router.post("/jobs/{job_id}/documents/standard")
def register_standard_document(job_id: str, body: RegisterDocumentBody):
    _job_or_404(job_id)
    try:
        with get_db() as conn:
            document = register_document(
                conn,
                job_id=job_id,
                document_type=body.document_type,
                url=body.url,
                filename=body.filename,
                item_key=body.item_key,
                route_to=body.route_to,
                visible_to_client=body.visible_to_client,
                audience=body.audience,
                stage_key=body.stage_key or infer_stage_key(body.document_type, body.filename),
                area=body.area,
                client=body.client,
                extension=body.extension,
            )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return {"document": document}


@router.post("/jobs/{job_id}/documents/name")
def preview_standard_name(job_id: str, body: NamePreviewBody):
    _job_or_404(job_id)
    with get_db() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        rows = conn.execute(
            "SELECT filename, standard_name FROM job_documents WHERE job_id = ?",
            (job_id,),
        ).fetchall()
    names = [row["standard_name"] or row["filename"] or "" for row in rows]
    revision = body.revision or next_revision(names, internal=body.internal)
    name = build_standard_name(
        client=body.client or (job["client_name"] if job else None) or (job["title"] if job else None),
        area=body.area or (job["room"] if job else None),
        doc_type=body.document_type,
        revision=revision,
        internal=body.internal,
        extension=body.extension,
        stage_key=body.stage_key,
    )
    return {"filename": name, "revision": revision, "internal": body.internal}


@router.get("/jobs/{job_id}/where")
def where_is_job(job_id: str):
    _job_or_404(job_id)
    with get_db() as conn:
        location = job_location(conn, job_id)
    location["answer"] = locate_job(job_id=job_id)["answer"]
    return location


@router.post("/jobs/{job_id}/workroom-approval")
def create_workroom_approval(job_id: str, body: WorkroomApprovalBody):
    _job_or_404(job_id)
    with get_db() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    packet = body.model_dump()
    packet.setdefault("client_name", job["client_name"] if job else None)
    packet.setdefault("area", job["room"] if job else None)
    packet.setdefault("job_number", job["job_number"] if job else None)
    packet.setdefault("title", job["title"] if job else None)
    pdf = render_workroom_approval_pdf(packet)
    with get_db() as conn:
        document = register_document(
            conn,
            job_id=job_id,
            document_type="workroom_approval",
            url=f"local://workroom-approval/{job_id}",
            audience="internal",
            stage_key="workroom_approval",
            area=packet.get("area"),
            client=packet.get("client_name"),
            extension="pdf",
        )
    return {
        "document": document,
        "pages": 3,
        "bytes": len(pdf),
        "pdf_base64": base64.b64encode(pdf).decode("ascii"),
        "sent": False,
    }


@router.post("/jobs/{job_id}/estimates/client")
def generate_client_estimate(job_id: str, body: EstimateBody):
    _job_or_404(job_id)
    try:
        with get_db() as conn:
            job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        packet = body.model_dump()
        packet.setdefault("client_name", job["client_name"] if job else None)
        packet.setdefault("area", job["room"] if job else None)
        packet.setdefault("job_number", job["job_number"] if job else None)
        copies = generate_estimate_copies(job_id, packet)
        with get_db() as conn:
            client_doc = register_document(
                conn,
                job_id=job_id,
                document_type="estimate",
                url=f"local://estimate/{job_id}/client",
                audience="client",
                visible_to_client=True,
                stage_key="estimate",
                area=packet.get("area"),
                client=packet.get("client_name"),
                extension="pdf",
            )
            internal_doc = register_document(
                conn,
                job_id=job_id,
                document_type="estimate",
                url=f"local://estimate/{job_id}/internal",
                audience="internal",
                visible_to_client=False,
                stage_key="estimate",
                area=packet.get("area"),
                client=packet.get("client_name"),
                extension="pdf",
            )
        return {
            "sent": False,
            "gate": copies["gate"],
            "layout": copies["layout"],
            "grouping": copies["grouping"],
            "client_document": client_doc,
            "internal_document": internal_doc,
            "client_bytes": len(copies["client_pdf"]),
            "internal_bytes": len(copies["internal_pdf"]),
            "client_pdf_base64": base64.b64encode(copies["client_pdf"]).decode("ascii"),
            "internal_pdf_base64": base64.b64encode(copies["internal_pdf"]).decode("ascii"),
        }
    except ClientEstimateGateError as exc:
        return _gate_response(exc)


@router.post("/jobs/{job_id}/estimates/share")
def share_client_estimate(job_id: str):
    _job_or_404(job_id)
    try:
        gate = assert_share_export_allowed(job_id)
    except ClientEstimateGateError as exc:
        return _gate_response(exc)
    return {
        "allowed": True,
        "sent": False,
        "gate": gate,
        "detail": "Share/export unlocked. Nothing was sent.",
    }


@router.post("/jobs/{job_id}/estimates/export")
def export_client_estimate(job_id: str):
    return share_client_estimate(job_id)


@router.get("/jobs/{job_id}/estimates/gate")
def estimate_gate(job_id: str):
    _job_or_404(job_id)
    try:
        gate = assert_client_estimate_allowed(job_id)
        return {"allowed": True, "gate": gate}
    except ClientEstimateGateError as exc:
        return _gate_response(exc)


@router.post("/jobs/{job_id}/square-invoice")
def draft_square_invoice(job_id: str, body: SquareDraftBody):
    _job_or_404(job_id)
    return create_square_invoice_draft(job_id, amount=body.amount, notes=body.notes)


@router.post("/jobs/{job_id}/square-invoice/send")
def send_job_square_invoice(job_id: str, body: SquareSendBody):
    _job_or_404(job_id)
    try:
        if not body.express_send and not body.send_phrase:
            refuse_auto_send(job_id)
        return send_square_invoice(
            job_id,
            authorized_by=body.authorized_by,
            express_send=body.express_send,
            send_phrase=body.send_phrase,
        )
    except SquareSendGateError as exc:
        return JSONResponse(status_code=exc.status_code, content=exc.as_dict())
