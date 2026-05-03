"""
Finance Corridor: wires quote → invoice → payment flow through Hermes.
Part of the MAX→Hermes→OpenClaw triad for financial operations.
"""
from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Optional

logger = logging.getLogger(__name__)

# In-memory store for MVP. In production this would use the empire.db via SQLAlchemy.
_finance_store: dict = {}


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ── Quote → Invoice ──────────────────────────────────────────────────────────

def create_quote_from_intake(
    intake_id: str,
    client_id: str,
    line_items: list[dict],
    notes: Optional[str] = None,
) -> dict:
    """
    Create a quote from an intake form.
    In production: writes to quotes table, assembles Hermes context.
    """
    quote_id = f"quote_{uuid.uuid4().hex[:12]}"
    quote = {
        "id": quote_id,
        "intake_id": intake_id,
        "client_id": client_id,
        "line_items": line_items,
        "notes": notes,
        "status": "draft",
        "created_at": _now_iso(),
        "version": "v1_finance_corridor",
    }
    _finance_store[quote_id] = quote
    logger.info(f"[FinanceCorridor] Created quote {quote_id} from intake {intake_id}")
    return quote


def convert_quote_to_invoice(
    quote_id: str,
    due_days: int = 30,
    payment_terms: Optional[str] = None,
) -> dict:
    """
    Convert an approved quote to an invoice.
    In production: creates invoice record, triggers Hermes approval gate.
    """
    quote = _finance_store.get(quote_id)
    if not quote:
        return {"error": f"Quote {quote_id} not found"}

    if quote.get("status") == "invoiced":
        return {"error": f"Quote {quote_id} already invoiced"}

    invoice_id = f"inv_{uuid.uuid4().hex[:12]}"
    invoice = {
        "id": invoice_id,
        "quote_id": quote_id,
        "client_id": quote["client_id"],
        "line_items": quote["line_items"],
        "notes": quote.get("notes"),
        "status": "issued",
        "due_date": due_days,
        "payment_terms": payment_terms or f"net_{due_days}",
        "issued_at": _now_iso(),
        "version": "v1_finance_corridor",
    }
    quote["status"] = "invoiced"
    _finance_store[invoice_id] = invoice
    logger.info(f"[FinanceCorridor] Converted quote {quote_id} → invoice {invoice_id}")
    return invoice


def record_payment(
    invoice_id: str,
    amount: float,
    method: str = "unknown",
    reference: Optional[str] = None,
) -> dict:
    """
    Record a payment against an invoice.
    In production: updates invoice status, logs to Hermes.
    """
    invoice = _finance_store.get(invoice_id)
    if not invoice:
        return {"error": f"Invoice {invoice_id} not found"}

    payment_id = f"pay_{uuid.uuid4().hex[:12]}"
    payment = {
        "id": payment_id,
        "invoice_id": invoice_id,
        "amount": amount,
        "method": method,
        "reference": reference,
        "recorded_at": _now_iso(),
        "version": "v1_finance_corridor",
    }
    _finance_store[payment_id] = payment

    # Update invoice status
    invoice["status"] = "paid"
    invoice["paid_at"] = _now_iso()

    logger.info(f"[FinanceCorridor] Recorded payment {payment_id} for invoice {invoice_id}")
    return payment


def get_quote(quote_id: str) -> dict:
    """Get a quote by ID."""
    return _finance_store.get(quote_id, {"error": f"Quote {quote_id} not found"})


def get_invoice(invoice_id: str) -> dict:
    """Get an invoice by ID."""
    return _finance_store.get(invoice_id, {"error": f"Invoice {invoice_id} not found"})
