"""
Accounting connector routes.

QuickBooks Online (Studio/Empire) — sandbox pull of invoices/payments.
Alegra/Siigo (Maxine) — DIAN e-invoicing stub, local drafts only.
"""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from app.db.database import get_db
from app.services.accounting import alegra_siigo, qbo
from app.services.accounting.guards import LiveWriteBlocked, SandboxOnlyError
from app.services.feature_flags import flag_status

router = APIRouter(prefix="/accounting", tags=["accounting"])


class DianDraftCreate(BaseModel):
    provider: str = Field(..., description="alegra or siigo")
    customer_name: str = Field(..., min_length=1, max_length=200)
    amount: float = Field(..., ge=0)
    currency: str = "COP"
    document_type: str = "invoice"


def _raise(exc: Exception) -> None:
    status = getattr(exc, "status_code", 400)
    message = getattr(exc, "message", str(exc))
    raise HTTPException(status_code=status, detail=message)


@router.get("/status")
def accounting_status():
    return {
        "flags": flag_status(),
        "live_data_writes": False,
        "sandbox_credentials_only": True,
        "reads_client_aliases": False,
        "reads_business_json": False,
    }


@router.post("/qbo/sync")
def qbo_sync():
    """Pull QBO sandbox invoices + payments into local staging. No outbound writes."""
    try:
        with get_db() as conn:
            return qbo.sync_invoices_and_payments(conn)
    except (SandboxOnlyError, LiveWriteBlocked) as exc:
        _raise(exc)


@router.get("/qbo/invoices")
def qbo_invoices():
    try:
        qbo.require_enabled()
        with get_db() as conn:
            return {"invoices": qbo.list_staged_invoices(conn), "live_writes": False}
    except SandboxOnlyError as exc:
        _raise(exc)


@router.get("/qbo/payments")
def qbo_payments():
    try:
        qbo.require_enabled()
        with get_db() as conn:
            return {"payments": qbo.list_staged_payments(conn), "live_writes": False}
    except SandboxOnlyError as exc:
        _raise(exc)


@router.post("/qbo/push-invoice")
def qbo_push_invoice_blocked():
    try:
        qbo.push_invoice_to_qbo({})
    except (SandboxOnlyError, LiveWriteBlocked) as exc:
        _raise(exc)


@router.get("/dian/status")
def dian_status():
    try:
        return alegra_siigo.status_payload()
    except SandboxOnlyError as exc:
        _raise(exc)


@router.post("/dian/draft")
def dian_local_draft(payload: DianDraftCreate):
    try:
        with get_db() as conn:
            return alegra_siigo.create_local_draft(
                conn,
                provider=payload.provider,
                customer_name=payload.customer_name,
                amount=payload.amount,
                currency=payload.currency,
                document_type=payload.document_type,
            )
    except (SandboxOnlyError, LiveWriteBlocked) as exc:
        _raise(exc)


@router.get("/dian/drafts")
def dian_drafts():
    try:
        alegra_siigo.require_enabled()
        with get_db() as conn:
            return {"drafts": alegra_siigo.list_drafts(conn), "live_submitted": False}
    except SandboxOnlyError as exc:
        _raise(exc)


@router.post("/dian/submit")
def dian_submit_blocked(draft_id: Optional[str] = None):
    try:
        alegra_siigo.submit_to_dian(draft_id or "")
    except (SandboxOnlyError, LiveWriteBlocked) as exc:
        _raise(exc)
