"""Workroom Studio quotes/invoices commerce routes.

Add-on totals, portal Approve & Pay Deposit, owner-opt-in follow-ups,
and owner-approved Google review requests.

Uses EMPIRE_TASK_DB (the same helper as other routers). Tests must point
that env at a fixture database — this router does not open a hardcoded
live path of its own.
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from typing import Any, Optional

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from app.db.database import DB_PATH
from app.services import workroom_quote_commerce as wqc

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/workroom/quotes-commerce", tags=["workroom-quotes-commerce"])


def _store(stripe_client: Any = None) -> wqc.FixtureStore:
    review_url = os.getenv("GOOGLE_REVIEW_URL", "")
    store = wqc.FixtureStore(
        db_path=DB_PATH,
        stripe_client=stripe_client if stripe_client is not None else _stripe_client(),
        review_url=review_url,
    )
    store.init()
    return store


def _stripe_client():
    secret = os.getenv("STRIPE_SECRET_KEY", "").strip()
    if not secret:
        return None
    try:
        import stripe
        stripe.api_key = secret
        return stripe
    except Exception:
        logger.warning("stripe package unavailable for workroom payment links")
        return None


class AddonPreviewRequest(BaseModel):
    line_items: list[dict] = Field(default_factory=list)
    addons: list[dict] = Field(default_factory=list)
    tax_rate: float = 0
    discount_amount: float = 0
    discount_type: str = "dollar"
    deposit_percent: float = 50
    deposit_paid: float = 0


class FollowupPrefsUpdate(BaseModel):
    quote_reminders_enabled: bool = False
    invoice_reminders_enabled: bool = False
    enabled_by: str = "owner"


class ApprovePayRequest(BaseModel):
    signer_name: str
    signature_data: str
    quote: Optional[dict] = None
    success_url: Optional[str] = None


class ReviewApproveRequest(BaseModel):
    approved_by: str = "owner"


class ReviewSendRequest(BaseModel):
    confirm: bool = False


@router.post("/preview-totals")
def preview_totals(body: AddonPreviewRequest):
    """Live estimate totals including selected optional add-ons."""
    return wqc.compute_estimate_totals(
        line_items=body.line_items,
        addons=body.addons,
        tax_rate=body.tax_rate,
        discount_amount=body.discount_amount,
        discount_type=body.discount_type,
        deposit_percent=body.deposit_percent,
        deposit_paid=body.deposit_paid,
    )


@router.post("/measurements/parse")
def parse_measurement(body: dict):
    value = body.get("value", "")
    inches = wqc.parse_fraction_inches(value)
    return {
        "input": value,
        "inches": inches,
        "display": wqc.format_fraction_inches(inches),
    }


@router.get("/clients/{customer_id}/followup-prefs")
def get_followup_prefs(customer_id: str):
    store = _store()
    return store.load_prefs(customer_id)


@router.put("/clients/{customer_id}/followup-prefs")
def put_followup_prefs(customer_id: str, body: FollowupPrefsUpdate):
    """Owner opt-in. Both reminder types stay OFF unless explicitly enabled."""
    store = _store()
    prefs = wqc.set_followup_prefs(
        customer_id,
        quote_reminders_enabled=body.quote_reminders_enabled,
        invoice_reminders_enabled=body.invoice_reminders_enabled,
        enabled_by=body.enabled_by,
    )
    return store.save_prefs(prefs)


def _load_documents_readonly() -> tuple[list[dict], list[dict]]:
    """Read quotes/invoices for follow-up scans. Does not write business rows."""
    from app.db.database import get_db

    quotes: list[dict] = []
    invoices: list[dict] = []
    with get_db() as conn:
        try:
            quotes = [dict(r) for r in conn.execute("SELECT * FROM quotes_v2").fetchall()]
        except Exception:
            logger.info("quotes_v2 not available for follow-up scan")
        try:
            invoices = [dict(r) for r in conn.execute("SELECT * FROM invoices").fetchall()]
        except Exception:
            logger.info("invoices not available for follow-up scan")
    return quotes, invoices


@router.post("/followups/run")
def run_followups(body: Optional[dict] = None):
    """Collect and dispatch due follow-ups. Sends only for opted-in clients."""
    store = _store()
    payload = body or {}
    now = datetime.now(timezone.utc)
    if payload.get("now"):
        now = wqc._parse_dt(payload["now"]) or now
    quotes = payload.get("quotes")
    invoices = payload.get("invoices")
    if quotes is None and invoices is None:
        quotes, invoices = _load_documents_readonly()
    for quote in quotes or []:
        if quote.get("id"):
            store.put_quote(quote)
    for invoice in invoices or []:
        if invoice.get("id"):
            store.put_invoice(invoice)
    return store.run_due_followups(now)


@router.post("/portal/{token}/approve-and-pay")
def portal_approve_and_pay(token: str, body: ApprovePayRequest, request: Request):
    """Client portal: e-sign + approve + non-expiring Stripe Payment Link."""
    from app.services.client_portal_service import get_portal_data, approve_quote_via_portal

    data = get_portal_data(token)
    if not data.get("valid"):
        raise HTTPException(status_code=403, detail=data.get("error", "Access denied"))
    if not data.get("can_approve_quote"):
        raise HTTPException(status_code=403, detail="Quote approval not permitted on this link")

    quote = body.quote or data.get("quote")
    if not quote:
        raise HTTPException(status_code=404, detail="No quote associated with this portal link")

    try:
        result = wqc.approve_and_pay_deposit(
            quote,
            body.signer_name,
            body.signature_data,
            ip_address=request.client.host if request.client else "",
            user_agent=request.headers.get("user-agent", ""),
            stripe_client=_stripe_client(),
            success_url=body.success_url,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    store = _store()
    store.save_esignature(result["esignature_record"])
    amount_cents = int(round(float(result["deposit_amount"]) * 100))
    store.save_payment_link(str(result.get("quote_id") or ""), result["payment_link"], amount_cents)

    try:
        approve_quote_via_portal(token)
    except Exception:
        logger.exception("portal quote status update failed after e-sign")

    public = {
        "success": True,
        "status": "approved",
        "quote_id": result["quote_id"],
        "deposit_amount": result["deposit_amount"],
        "total": result["total"],
        "payment_url": result["payment_url"],
        "payment_link_created": result["payment_link"]["created"],
        "payment_link_expires_at": None,
        "esignature": result["esignature"],
        "consent_text": wqc.CONSENT_TEXT,
        "message": result["message"],
    }
    if not result["payment_link"]["created"]:
        public["payment_link_reason"] = result["payment_link"].get("reason")
    return public


@router.get("/review-requests")
def list_review_requests(status: Optional[str] = None):
    return {"items": _store().list_review_requests(status=status)}


@router.post("/invoices/{invoice_id}/queue-review")
def queue_review(invoice_id: str, body: Optional[dict] = None):
    """Queue a Google review request after an invoice is marked paid. Does not send."""
    store = _store()
    invoice = (body or {}).get("invoice")
    if not invoice:
        raise HTTPException(status_code=400, detail="invoice payload required (fixture or caller-supplied)")
    invoice = dict(invoice)
    invoice.setdefault("id", invoice_id)
    store.put_invoice(invoice)
    try:
        result = store.mark_invoice_paid(invoice_id, paid_at=invoice.get("paid_at"))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return result


@router.post("/review-requests/{request_id}/approve")
def approve_review(request_id: str, body: ReviewApproveRequest):
    store = _store()
    request = store.get_review_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Review request not found")
    approved = wqc.owner_approve_review_request(request, approved_by=body.approved_by)
    return store.save_review_request(approved)


@router.post("/review-requests/{request_id}/send")
def send_review(request_id: str, body: ReviewSendRequest):
    store = _store()
    request = store.get_review_request(request_id)
    if not request:
        raise HTTPException(status_code=404, detail="Review request not found")
    if not body.confirm:
        raise HTTPException(status_code=400, detail="Owner confirm=true is required to send")
    result = wqc.send_review_request(request, sender=None)
    if result["sent"]:
        request["status"] = "sent"
        request["sent_at"] = datetime.now(timezone.utc).isoformat()
        store.save_review_request(request)
    return result
