"""
Email API router — send branded workroom emails (quotes, invoices, receipts).
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, Literal
from datetime import datetime
import logging

from app.config.business_config import biz
from app.services.email.templates import (
    render_quote_sent,
    render_invoice_sent,
    render_payment_received,
)
from app.services.email.sender import send_email
from app.services.max.response_quality_engine import quality_engine, Channel

logger = logging.getLogger("empire.email.router")
router = APIRouter()


# ── Request models ─────────────────────────────────────────────────

class QuoteEmailRequest(BaseModel):
    to_email: EmailStr
    customer_name: str
    quote_number: str
    project_description: Optional[str] = ""
    line_items: list = []
    total: float = 0.0
    quote_url: str = "#"


class InvoiceEmailRequest(BaseModel):
    to_email: EmailStr
    customer_name: str
    invoice_number: str
    due_date: str
    line_items: list = []
    total: float = 0.0
    balance_due: Optional[float] = None
    payment_url: str = "#"
    payment_methods: Optional[str] = "Check, Zelle, Cash, Credit Card, Crypto (USDT/BTC)"


class PaymentReceiptRequest(BaseModel):
    to_email: EmailStr
    customer_name: str
    reference_number: str
    amount_paid: float
    payment_method: str = ""
    payment_date: str = ""
    receipt_url: str = "#"


# ── Notification helper ───────────────────────────────────────────

def _log_notification(source: str, title: str, message: str, context: dict = None):
    """Log email event to the notification system (not Telegram)."""
    try:
        import importlib
        notif_mod = importlib.import_module("app.routers.notifications")
        notif_db = getattr(notif_mod, "notifications_db", None)
        if notif_db is not None:
            import uuid
            notif_db.append({
                "id": str(uuid.uuid4()),
                "source": source,
                "type": "business_event",
                "title": title,
                "message": message,
                "priority": "low",
                "context": context or {},
                "timestamp": datetime.utcnow().isoformat(),
                "read": False,
            })
    except Exception as e:
        logger.warning("Could not log notification: %s", e)


# ── Endpoints ──────────────────────────────────────────────────────

@router.post("/emails/send-quote")
async def send_quote_email(req: QuoteEmailRequest):
    """Send a branded quote email to a customer."""
    html = render_quote_sent(req.model_dump())

    # Quality gate: validate email content
    qr = quality_engine.validate(
        html,
        channel=Channel.EMAIL,
        context={
            "recipient": req.to_email,
            "customer_name": req.customer_name,
            "subject": f"Quote #{req.quote_number}",
            "quote_data": {"quote_number": req.quote_number, "total": req.total},
        },
    )
    if qr.blocked:
        return {
            "status": "blocked",
            "message": "Email blocked by quality engine",
            "issues": [{"check": i.check, "severity": i.severity.value, "message": i.message} for i in qr.issues],
        }
    if qr.fixed_count > 0:
        html = qr.cleaned  # Use auto-fixed version

    subject = f"Your Quote #{req.quote_number} from Empire Workroom"

    sent = await send_email(req.to_email, subject, html)

    _log_notification(
        "Business",
        f"Quote email sent: #{req.quote_number}",
        f"Quote email to {req.customer_name} ({req.to_email}) — {'delivered' if sent else 'SMTP not configured, skipped'}",
        {"quote_number": req.quote_number, "to_email": req.to_email, "sent": sent},
    )

    return {
        "status": "sent" if sent else "skipped",
        "to": req.to_email,
        "quote_number": req.quote_number,
        "message": "Email delivered" if sent else "SMTP not configured — email not sent",
    }


@router.post("/emails/send-invoice")
async def send_invoice_email(req: InvoiceEmailRequest):
    """Send a branded invoice email with payment link."""
    data = req.model_dump()
    if data.get("balance_due") is None:
        data["balance_due"] = data["total"]
    html = render_invoice_sent(data)
    subject = f"Invoice #{req.invoice_number} from Empire Workroom"

    sent = await send_email(req.to_email, subject, html)

    _log_notification(
        "Business",
        f"Invoice email sent: #{req.invoice_number}",
        f"Invoice email to {req.customer_name} ({req.to_email}) — {'delivered' if sent else 'SMTP not configured, skipped'}",
        {"invoice_number": req.invoice_number, "to_email": req.to_email, "sent": sent},
    )

    return {
        "status": "sent" if sent else "skipped",
        "to": req.to_email,
        "invoice_number": req.invoice_number,
        "message": "Email delivered" if sent else "SMTP not configured — email not sent",
    }


@router.post("/emails/send-receipt")
async def send_receipt_email(req: PaymentReceiptRequest):
    """Send a branded payment receipt email."""
    html = render_payment_received(req.model_dump())
    subject = f"Payment Received — Thank You, {req.customer_name}!"

    sent = await send_email(req.to_email, subject, html)

    _log_notification(
        "Business",
        f"Receipt email sent: #{req.reference_number}",
        f"Payment receipt to {req.customer_name} ({req.to_email}) — {'delivered' if sent else 'SMTP not configured, skipped'}",
        {"reference_number": req.reference_number, "to_email": req.to_email, "sent": sent},
    )

    return {
        "status": "sent" if sent else "skipped",
        "to": req.to_email,
        "reference_number": req.reference_number,
        "message": "Email delivered" if sent else "SMTP not configured — email not sent",
    }


@router.post("/emails/preview/{template}")
async def preview_template(template: Literal["quote", "invoice", "receipt"]):
    """Preview a template with sample data. Returns raw HTML."""
    sample_items = [
        {"description": "Custom Roman Shades (4 windows)", "qty": 4, "unit_price": 285.00, "total": 1140.00},
        {"description": "Premium Lining — Blackout", "qty": 4, "unit_price": 45.00, "total": 180.00},
        {"description": "Professional Installation", "qty": 1, "unit_price": 340.00, "total": 340.00},
    ]

    if template == "quote":
        html = render_quote_sent({
            "customer_name": "Jane Doe",
            "quote_number": "Q-2026-0042",
            "project_description": "Custom roman shades for living room — 4 windows, blackout lining",
            "line_items": sample_items,
            "total": 1660.00,
            "quote_url": "https://studio.empirebox.store/quotes/Q-2026-0042",
        })
    elif template == "invoice":
        html = render_invoice_sent({
            "customer_name": "Jane Doe",
            "invoice_number": "INV-2026-0078",
            "due_date": "April 15, 2026",
            "line_items": sample_items,
            "total": 1660.00,
            "balance_due": 830.00,
            "payment_url": "https://studio.empirebox.store/pay/INV-2026-0078",
            "payment_methods": "Check, Zelle, Cash, Credit Card, Crypto (USDT/BTC)",
        })
    else:
        html = render_payment_received({
            "customer_name": "Jane Doe",
            "reference_number": "INV-2026-0078",
            "amount_paid": 830.00,
            "payment_method": "Zelle",
            "payment_date": "March 14, 2026",
            "receipt_url": "https://studio.empirebox.store/receipts/RCP-2026-0078",
        })

    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html)
