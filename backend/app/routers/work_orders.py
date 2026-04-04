"""
Work Orders API Router — Production tracking and management.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.services.work_order_service import (
    create_work_order_from_quote, create_work_order,
    get_work_order, list_work_orders,
    advance_item_stage, get_production_board, get_overdue_items,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/work-orders", tags=["work-orders"])


@router.post("")
async def create_wo(body: dict):
    """Create a work order. If quote_id provided, creates from quote."""
    try:
        if body.get("quote_id") and body.get("from_quote"):
            wo = create_work_order_from_quote(body["quote_id"], body.get("assigned_to"))
        else:
            wo = create_work_order(body)
        return {"status": "created", "work_order": wo}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("")
async def list_wos(
    status: Optional[str] = None,
    business_unit: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    return list_work_orders(status=status, business_unit=business_unit,
                           limit=limit, offset=offset)


@router.get("/production-board")
async def production_board(business_unit: Optional[str] = None):
    """Kanban view — items grouped by production stage."""
    return get_production_board(business_unit)


@router.get("/overdue")
async def overdue_items():
    """Get all overdue production items."""
    items = get_overdue_items()
    return {"overdue_items": items, "count": len(items)}


@router.get("/{wo_id}")
async def get_wo(wo_id: int):
    wo = get_work_order(wo_id)
    if not wo:
        raise HTTPException(404, f"Work order {wo_id} not found")
    return wo


@router.post("/{wo_id}/items/{item_id}/advance")
async def advance_item(wo_id: int, item_id: int, body: dict = None):
    """Advance an item to the next production stage."""
    body = body or {}
    try:
        wo = advance_item_stage(
            wo_id, item_id,
            changed_by=body.get("changed_by", "api"),
            notes=body.get("notes", ""),
            photo_path=body.get("photo_path"),
        )
        return {"status": "advanced", "work_order": wo}
    except ValueError as e:
        raise HTTPException(400, str(e))
