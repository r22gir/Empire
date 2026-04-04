"""
Lifecycle API Router — Cross-entity business flow operations.
Prospect → Customer → Quote → Job → Work Order → Invoice → Payment
"""
from fastapi import APIRouter, HTTPException
import logging

from app.services.lifecycle_service import (
    convert_prospect_to_customer,
    create_job_from_quote,
    create_work_order_from_approved_quote,
    create_invoice_from_quote,
    get_lifecycle_status,
    execute_cascade,
    get_daily_actions,
    get_quick_stats,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/lifecycle", tags=["lifecycle"])


@router.post("/prospect/{prospect_id}/convert")
async def convert_prospect(prospect_id: int):
    """Convert a prospect to a customer."""
    try:
        result = convert_prospect_to_customer(prospect_id, "api")
        return {"status": "converted", **result}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/quote/{quote_id}/create-job")
async def create_job(quote_id: str):
    """Create a job from an approved quote."""
    try:
        result = create_job_from_quote(quote_id, "api")
        return {"status": "created", "job": result}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/quote/{quote_id}/create-work-order")
async def create_wo(quote_id: str):
    """Create a work order from an approved/ordered quote."""
    try:
        result = create_work_order_from_approved_quote(quote_id, "api")
        return {"status": "created", "work_order": result}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/quote/{quote_id}/create-invoice")
async def create_invoice(quote_id: str):
    """Create an invoice from a completed quote/WO."""
    try:
        result = create_invoice_from_quote(quote_id, "api")
        return {"status": "created", "invoice": result}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/quote/{quote_id}/status")
async def lifecycle_status(quote_id: str):
    """Get full lifecycle status — quote, job, WO, invoice, payments."""
    result = get_lifecycle_status(quote_id)
    if not result:
        raise HTTPException(404, f"Quote {quote_id} not found")
    return result


@router.post("/cascade")
async def trigger_cascade(body: dict):
    """Execute a status cascade (e.g. quote_approved, deposit_paid).
    Body: {trigger: str, quote_id: str, customer_id?: str, job_id?: str}"""
    trigger = body.get("trigger")
    if not trigger:
        raise HTTPException(400, "trigger required")
    result = execute_cascade(trigger, body)
    return result


@router.get("/daily-actions")
async def daily_actions():
    """Get today's action items for the founder dashboard."""
    return get_daily_actions()


@router.get("/quick-stats")
async def quick_stats():
    """Quick stats for dashboard header."""
    return get_quick_stats()
