"""
Customer Journey Linkage Routes
================================

Read-only endpoints for the customer ↔ quote ↔ invoice ↔ payment
carry-forward pilot.

Endpoints:
    GET  /api/v1/customers/{id}/journey                — full chain
    GET  /api/v1/quotes/{id}/invoice                  — reverse lookup (quote → invoice)
    GET  /api/v1/invoices/{id}/quote                  — reverse lookup (invoice → quote)
    POST /api/v1/journey/backfill-audit                — run a read-only backfill audit
    GET  /api/v1/journey/review-queue                  — list proposed matches
    GET  /api/v1/journey/review-queue/{proposal_id}    — one proposal with evidence
    POST /api/v1/journey/review-queue/{proposal_id}/approve
                                                       — RESERVED (live writes disabled)

These routes are read-only. The backfill-audit endpoint inspects
the live DB and writes a JSON audit file under backend/data/; it
never writes to the live DB.

The review-queue endpoints return proposed matches that the founder
can review. The apply-approval endpoint is RESERVED for a future
founder-approved pass; this pass ships it disabled.
"""
from fastapi import APIRouter, HTTPException, Request, Query
from typing import Optional

from app.services.max.journey_linkage import (
    get_customer_journey,
    get_invoice_for_quote,
    get_quote_for_invoice,
    run_backfill_audit,
)
from app.services.max.journey_review_queue import (
    generate_review_queue,
    write_review_queue_snapshot,
    apply_approval_enabled,
    REVIEW_QUEUE_PATH,
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


@router.get("/journey/review-queue")
async def journey_review_queue(
    request: Request,
    min_confidence: str = Query(
        "low",
        description="Minimum confidence band: 'low' (all), 'medium' (medium+high), or 'high' (only high).",
        pattern="^(low|medium|high)$",
    ),
    write_snapshot: bool = Query(
        False,
        description="If true, also write a JSON snapshot of the queue under backend/data/.",
    ),
    source_type: Optional[str] = Query(
        None,
        description="Filter by source type: 'quote', 'invoice', or 'payment'.",
    ),
):
    """List proposed customer ↔ quote ↔ invoice ↔ payment links.

    Read-only. Every proposal is for founder review only; nothing
    is applied. Use min_confidence to filter, source_type to narrow
    to one type, and write_snapshot=true to persist the queue.
    """
    proposals = generate_review_queue(min_confidence=min_confidence)
    if source_type:
        proposals = [p for p in proposals if p.source_type == source_type]

    if write_snapshot:
        snapshot_path = write_review_queue_snapshot(proposals)
    else:
        snapshot_path = None

    return {
        "count": len(proposals),
        "by_confidence": {
            "high":   sum(1 for p in proposals if p.confidence == "high"),
            "medium": sum(1 for p in proposals if p.confidence == "medium"),
            "low":    sum(1 for p in proposals if p.confidence == "low"),
        },
        "by_source_type": {
            "quote":   sum(1 for p in proposals if p.source_type == "quote"),
            "invoice": sum(1 for p in proposals if p.source_type == "invoice"),
            "payment": sum(1 for p in proposals if p.source_type == "payment"),
        },
        "snapshot_path": snapshot_path,
        "snapshot_exists": (
            __import__("os").path.exists(REVIEW_QUEUE_PATH) if snapshot_path is None
            else bool(snapshot_path)
        ),
        "proposals": [p.to_dict() for p in proposals],
    }


@router.get("/journey/review-queue/{proposal_id}")
async def journey_review_queue_proposal(proposal_id: str, request: Request):
    """Return one proposal by id, with full evidence.

    Read-only. Returns the full Proposal dict including source and
    target summaries, match reasons, risks, and confidence score.
    """
    proposals = generate_review_queue()
    for p in proposals:
        if p.proposal_id == proposal_id:
            return p.to_dict()
    raise HTTPException(status_code=404, detail=f"Proposal {proposal_id} not found")


@router.post("/journey/review-queue/{proposal_id}/approve")
async def journey_review_queue_approve(proposal_id: str, request: Request):
    """RESERVED — live writes disabled in this pass.

    This endpoint is reserved for a future founder-approved pass.
    In the current pass, the live DB write path is disabled by
    default. To enable it, set the JOURNEY_REVIEW_APPLY_ENABLED
    env var and ship a separate PR that implements the apply logic.

    For now, this endpoint always returns:
        {"status": "reserved", "detail": "..."}
    so the founder can confirm the route exists and is wired.
    """
    if not apply_approval_enabled():
        return {
            "status": "reserved",
            "apply_enabled": False,
            "proposal_id": proposal_id,
            "detail": (
                "approval endpoint reserved; live writes disabled. "
                "Set JOURNEY_REVIEW_APPLY_ENABLED=1 and ship a separate "
                "founder-approved pass to enable this endpoint."
            ),
        }
    # When the apply path is implemented, it must:
    #   1. Look up the proposal
    #   2. Open the live DB in read-write mode
    #   3. Verify the founder approval signature/token
    #   4. Apply the change (set quotes_v2.customer_id, clear a
    #      dangling invoice.quote_id, etc.) within a single transaction
    #   5. Re-run the audit and log the result
    return {
        "status": "reserved",
        "apply_enabled": True,
        "proposal_id": proposal_id,
        "detail": "apply path enabled but not implemented in this pass; "
                  "ship a separate founder-approved PR to wire it.",
    }

