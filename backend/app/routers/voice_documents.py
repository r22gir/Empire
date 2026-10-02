"""Web chat and ConstructionForge forms share the voice-to-document borrador."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel

from app.services.voice_doc import (
    approve_draft,
    channel_report,
    close_session,
    get_draft,
    ingest_structured,
    ingest_transcript,
    send_draft,
)
from app.services.voice_doc.deals import DealError, confirm_reservation, overdue_payments
from app.services.voice_doc.templates import list_slots, mark_lawyer_approved, save_uploaded_template

router = APIRouter(tags=["voice-documents"])


class IngestBody(BaseModel):
    transcript: str = ""
    session_id: Optional[str] = None
    channel: str = "web"
    language: Optional[str] = None
    choice_id: Optional[str] = None


class StructuredBody(BaseModel):
    session_id: Optional[str] = None
    lot_number: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_email: str = ""
    buyer_phone: str = ""
    price: Optional[float] = None
    separacion: Optional[float] = None
    cuota_inicial_pct: Optional[float] = None
    installments: Optional[int] = None
    balloon: Optional[float] = None
    house_type: Optional[str] = None
    finishes: Optional[str] = None
    product_name: Optional[str] = None
    product_kind: Optional[str] = None
    transcript: str = ""


class SendBody(BaseModel):
    confirm: bool = False
    channel: str = ""


class ConfirmDealBody(BaseModel):
    draft_id: str
    confirm: bool = False
    lot_status: Optional[str] = None
    payment: Optional[dict] = None


class LawyerBody(BaseModel):
    aprobado_por_abogado: bool = False


def _draft_or_404(draft_id: str) -> dict:
    draft = get_draft(draft_id)
    if draft is None:
        raise HTTPException(404, "Borrador no encontrado")
    return draft


@router.get("/voice/documents/channels")
def voice_channels():
    return channel_report()


@router.post("/voice/documents/ingest")
def voice_ingest(body: IngestBody):
    return ingest_transcript(
        body.transcript,
        session_id=body.session_id,
        channel=body.channel,
        language=body.language,
        choice_id=body.choice_id,
    )


@router.post("/voice/documents/sessions/{session_id}/close")
def voice_close(session_id: str):
    try:
        return close_session(session_id)
    except KeyError:
        raise HTTPException(404, "Sesión no encontrada")


@router.get("/voice/documents/drafts/{draft_id}")
def voice_draft(draft_id: str):
    draft = _draft_or_404(draft_id)
    return {
        "id": draft["id"],
        "status": draft["status"],
        "doc_type": draft["doc_type"],
        "sent": False,
        "auto_send": False,
        "payload": draft["payload"],
    }


@router.get("/voice/documents/drafts/{draft_id}/preview", response_class=HTMLResponse)
def voice_preview(draft_id: str):
    draft = _draft_or_404(draft_id)
    return HTMLResponse(draft["html"] or "<p>DRAFT</p>")


@router.get("/voice/documents/drafts/{draft_id}/preview.pdf")
def voice_preview_pdf(draft_id: str):
    from app.services.voice_doc.store import render_draft_pdf

    draft = _draft_or_404(draft_id)
    payload = draft["payload"]
    notes = [payload.get("transcript") or ""]
    pdf = render_draft_pdf(payload, notes)
    return Response(content=pdf, media_type="application/pdf")


@router.post("/voice/documents/drafts/{draft_id}/approve")
def voice_approve(draft_id: str):
    try:
        draft = approve_draft(draft_id)
    except KeyError:
        raise HTTPException(404, "Borrador no encontrado")
    return {"id": draft["id"], "status": draft["status"], "sent": False, "auto_send": False}


@router.post("/voice/documents/drafts/{draft_id}/send")
def voice_send(draft_id: str, body: SendBody):
    try:
        return send_draft(draft_id, confirm=body.confirm, channel=body.channel)
    except KeyError:
        raise HTTPException(404, "Borrador no encontrado")


@router.post("/construction/reservations/preview")
def reservation_preview(body: StructuredBody):
    view = ingest_structured(body.model_dump(), channel="form", session_id=body.session_id)
    return view


@router.post("/construction/reservations/confirm")
def reservation_confirm(body: ConfirmDealBody):
    draft = _draft_or_404(body.draft_id)
    payload = draft["payload"]
    schedule = payload.get("schedule")
    if not schedule:
        raise HTTPException(400, "El borrador no tiene un plan de pagos. Indica el precio y di listo.")
    try:
        result = confirm_reservation(
            fields=payload.get("fields") or {},
            schedule=schedule,
            draft_id=draft["id"],
            confirm=body.confirm,
            lot_status=body.lot_status,
            payment=body.payment,
        )
    except DealError as exc:
        raise HTTPException(400, str(exc))
    result["sent"] = False
    result["auto_send"] = False
    if result.get("recibo"):
        payload = dict(payload)
        payload["recibo"] = result["recibo"]
        from app.services.voice_doc.store import render_draft_html

        notes = payload.get("fields", {}).get("raw") or ""
        result["preview_html"] = render_draft_html(payload, [notes] if isinstance(notes, str) else [])
    return result


@router.get("/construction/payments/overdue")
def construction_overdue():
    try:
        rows = overdue_payments()
    except Exception:
        rows = []
    return {"payments": rows, "count": len(rows)}


@router.get("/construction/legal-templates")
def legal_templates():
    return {"slots": list_slots(), "watermark": "BORRADOR – requiere revisión de abogado"}


@router.post("/construction/legal-templates/{slot}")
async def upload_legal_template(slot: str, file: UploadFile = File(...)):
    data = await file.read()
    if not data:
        raise HTTPException(400, "El archivo está vacío")
    try:
        return save_uploaded_template(slot, file.filename or "plantilla", data)
    except KeyError:
        raise HTTPException(404, "Ese tipo de documento no existe")


@router.post("/construction/legal-templates/{slot}/aprobado")
def approve_legal_template(slot: str, body: LawyerBody):
    if not body.aprobado_por_abogado:
        raise HTTPException(400, "Marca aprobado por abogado para registrar la revisión.")
    try:
        return mark_lawyer_approved(slot, True)
    except KeyError:
        raise HTTPException(404, "Ese tipo de documento no existe")
