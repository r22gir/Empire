"""
Customer Journey Linkage Routes
================================

Read-only endpoints for the customer ↔ quote ↔ invoice ↔ payment
carry-forward pilot.

Endpoints:
    GET /api/v1/customers/{id}/journey       — full chain
    GET /api/v1/quotes/{id}/invoice         — reverse lookup (quote → invoice)
    GET /api/v1/invoices/{id}/quote         — reverse lookup (invoice → quote)
    POST /api/v1/journey/backfill-audit     — run a read-only backfill audit

These routes are read-only. The backfill-audit endpoint inspects
the live DB and writes a JSON audit file under backend/data/; it
never writes to the live DB.
"""
from fastapi import APIRouter, HTTPException, Request
from typing import Optional

from app.services.max.journey_linkage import (
    get_customer_journey,
    get_invoice_for_quote,
    get_quote_for_invoice,
    run_backfill_audit,
)

router = APIRouter(tags=["journey"])


@router.get("/customers/{customer_id}/journey")
async def customer_journey(customer_id: str, request: Request):
    """Full customer → quote → invoice → payment chain.

    Read-only. Returns:
        - customer (id, name, email, phone)
        - quotes: list of quotes linked to this customer
        - orphan_invoices: invoices whose customer_id is this customer
          but whose quote_id is missing or dangling
        - orphan_payments: payments whose customer_id is this customer
          but whose invoice_id is missing or dangling
        - totals: counts and sums
    """
    journey = get_customer_journey(customer_id)
    if journey is None:
        raise HTTPException(status_code=404, detail=f"Customer {customer_id} not found")
    return journey.to_dict()


@router.get("/quotes/{quote_id}/invoice")
async def quote_invoice(quote_id: str, request: Request):
    """Reverse lookup: given a quote, return the invoice linked to it.

    Returns:
        - link: "linked" | "no_invoice" | "no_quote"
        - quote_id
        - invoice (dict if linked, else null)
    """
    result = get_invoice_for_quote(quote_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Quote {quote_id} not found")
    return result


@router.get("/invoices/{invoice_id}/quote")
async def invoice_quote(invoice_id: str, request: Request):
    """Reverse lookup: given an invoice, return the quote linked to it.

    Returns:
        - link: "linked" | "no_quote" | "dangling" | "no_invoice"
        - invoice_id
        - quote (dict if linked, else null)
        - quote_id (if dangling, the dangling id)
    """
    result = get_quote_for_invoice(invoice_id)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Invoice {invoice_id} not found")
    return result


@router.post("/journey/backfill-audit")
async def journey_backfill_audit(request: Request):
    """Run a read-only backfill audit.

    Inspects quotes_v2, invoices, payments for linkage gaps. Writes
    a JSON audit file under backend/data/journey_backfill_audit.json
    and returns the audit summary.

    The audit is non-destructive: it never writes to the live DB.
    The recommendations are advisory; the founder must approve any
    actual data writes.
    """
    audit = run_backfill_audit()
    return audit.to_dict()
