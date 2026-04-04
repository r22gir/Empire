"""
Quotes v2 Router — SQL-backed CRUD for unified business system.
Supplements the original quotes.py router which handles QIS pipeline.
These endpoints operate on quotes_v2 table (SQL).
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.services import quote_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/quotes-v2", tags=["quotes-v2"])


# ── List / Search / Stats ──────────────────────────────────────

@router.get("")
async def list_quotes(
    status: Optional[str] = None,
    business_unit: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    """List all SQL-backed quotes with pagination and filtering."""
    return quote_service.list_quotes(status=status, business_unit=business_unit,
                                     search=search, limit=limit, offset=offset)


@router.get("/search")
async def search_quotes(q: str = Query(..., min_length=1), limit: int = 20):
    """Full-text search across quotes."""
    results = quote_service.search_quotes(q, limit=limit)
    return {"results": results, "count": len(results), "query": q}


@router.get("/stats")
async def quote_stats():
    """Quote statistics — counts, values, by status."""
    return quote_service.get_quote_stats()


# ── CRUD ─────────��─────────────────────────────────────────────

@router.post("")
async def create_quote(body: dict):
    """Create a new quote in SQL."""
    if not body.get("customer_name"):
        raise HTTPException(400, "customer_name required")
    result = quote_service.create_quote(body)
    return {"status": "created", "quote": result}


@router.get("/{quote_id}")
async def get_quote(quote_id: str):
    """Get a single quote with line items and photos."""
    q = quote_service.get_quote(quote_id)
    if not q:
        raise HTTPException(404, f"Quote {quote_id} not found")
    return q


@router.patch("/{quote_id}")
async def update_quote(quote_id: str, body: dict):
    """Update quote fields."""
    result = quote_service.update_quote(quote_id, body)
    if not result:
        raise HTTPException(404, f"Quote {quote_id} not found")
    return {"status": "updated", "quote": result}


@router.delete("/{quote_id}")
async def delete_quote(quote_id: str):
    """Delete a quote and its line items."""
    if not quote_service.delete_quote(quote_id):
        raise HTTPException(404, f"Quote {quote_id} not found")
    return {"status": "deleted", "id": quote_id}


# ── Line Item CRUD ─────────────────────────────────────────────

@router.post("/{quote_id}/items")
async def add_item(quote_id: str, body: dict):
    """Add a line item to a quote."""
    result = quote_service.add_line_item(quote_id, body)
    if not result:
        raise HTTPException(404, f"Quote {quote_id} not found")
    return {"status": "added", "quote": result}


@router.patch("/{quote_id}/items/{item_id}")
async def update_item(quote_id: str, item_id: int, body: dict):
    """Update a line item."""
    result = quote_service.update_line_item(quote_id, item_id, body)
    if not result:
        raise HTTPException(404, "Quote or item not found")
    return {"status": "updated", "quote": result}


@router.delete("/{quote_id}/items/{item_id}")
async def delete_item(quote_id: str, item_id: int):
    """Delete a line item."""
    result = quote_service.delete_line_item(quote_id, item_id)
    if not result:
        raise HTTPException(404, "Quote not found")
    return {"status": "deleted", "quote": result}


# ── Auto-Calculate ───��─────────────────────────────────────────

@router.post("/{quote_id}/calculate")
async def calculate_totals(quote_id: str):
    """Force recalculate totals from line items."""
    from app.db.database import get_db
    from app.services.quote_service import _recalculate_totals
    with get_db() as conn:
        q = conn.execute("SELECT id FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
        if not q:
            raise HTTPException(404, f"Quote {quote_id} not found")
        _recalculate_totals(conn, quote_id, 'api')
    return quote_service.get_quote(quote_id)


# ── Status Transitions ─────────────────────────────────────────

@router.post("/{quote_id}/send")
async def send_quote(quote_id: str):
    """Mark quote as sent."""
    try:
        return quote_service.transition_quote(quote_id, 'sent', 'api')
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{quote_id}/approve")
async def approve_quote(quote_id: str):
    """Mark quote as approved."""
    try:
        return quote_service.transition_quote(quote_id, 'approved', 'api')
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/{quote_id}/order")
async def order_quote(quote_id: str):
    """Mark quote as ordered (deposit confirmed)."""
    try:
        return quote_service.transition_quote(quote_id, 'ordered', 'api')
    except ValueError as e:
        raise HTTPException(400, str(e))


# ── Cross-entity creation (Block 4 lifecycle) ──────────────────

@router.post("/{quote_id}/to-work-order")
async def quote_to_work_order(quote_id: str):
    """Create a work order from an approved/ordered quote."""
    try:
        from app.services.work_order_service import create_work_order_from_quote
        wo = create_work_order_from_quote(quote_id)
        return {"status": "created", "work_order": wo}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


@router.post("/{quote_id}/to-invoice")
async def quote_to_invoice(quote_id: str):
    """Create an invoice from a completed quote."""
    try:
        from app.services.lifecycle_service import create_invoice_from_quote
        inv = create_invoice_from_quote(quote_id)
        return {"status": "created", "invoice": inv}
    except ValueError as e:
        raise HTTPException(400, str(e))
    except Exception as e:
        raise HTTPException(500, str(e))


# ── PDF Generation (Block 6) ──────────────────────────────────

@router.get("/{quote_id}/pdf")
async def get_quote_pdf(quote_id: str):
    """Generate and return quote PDF."""
    try:
        from app.services.quote_pdf_service import generate_quote_pdf
        from fastapi.responses import Response
        pdf_bytes = generate_quote_pdf(quote_id)
        q = quote_service.get_quote(quote_id)
        filename = f"{q.get('quote_number', quote_id)}.pdf"
        return Response(content=pdf_bytes, media_type="application/pdf",
                       headers={"Content-Disposition": f'attachment; filename="{filename}"'})
    except FileNotFoundError:
        raise HTTPException(404, f"Quote {quote_id} not found")
    except Exception as e:
        raise HTTPException(500, str(e))
