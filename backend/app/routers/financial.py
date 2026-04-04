"""
Financial API Router — Payments, P&L, revenue, AR aging, dashboard.
"""
from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import logging

from app.services.financial_service import (
    create_payment, list_payments,
    get_chart_of_accounts,
    generate_pl, get_revenue_summary,
    get_outstanding, get_financial_dashboard,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/finance", tags=["finance-v2"])


# ── Payments ───────────────────────────────────────────────────

@router.post("/payments")
async def record_payment(body: dict):
    """Record a payment (deposit, progress, final, refund)."""
    try:
        result = create_payment(body)
        return {"status": "recorded", "payment": result}
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/payments")
async def payments_list(
    customer_id: Optional[str] = None,
    invoice_id: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
):
    return list_payments(customer_id=customer_id, invoice_id=invoice_id,
                        limit=limit, offset=offset)


# ── Chart of Accounts ──────────────────────────────────────────

@router.get("/chart-of-accounts")
@router.get("/accounts")
async def chart_of_accounts():
    return {"accounts": get_chart_of_accounts()}


# ── P&L ────────────────────────────────────────────────────────

@router.get("/pl")
async def profit_and_loss(
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    business_unit: Optional[str] = None,
):
    """Profit & Loss report. Revenue - COGS - OpEx = Net Profit."""
    return generate_pl(start_date, end_date, business_unit)


# ── Revenue Summary ────────────────────────────────────────────

@router.get("/revenue-summary")
async def revenue_summary(period: str = "month"):
    """Revenue summary by period (month, quarter, year)."""
    return get_revenue_summary(period)


# ── Outstanding (AR Aging) ─────────────────────────────────────

@router.get("/outstanding")
async def outstanding_ar():
    """Accounts receivable aging report."""
    return get_outstanding()


# ── Expenses Summary ──────────────────────────────────────────

@router.get("/expenses-summary")
async def expenses_summary():
    """Expense breakdown by category."""
    from app.db.database import get_db
    with get_db() as conn:
        rows = conn.execute("""
            SELECT category, COALESCE(SUM(amount), 0) as total, COUNT(*) as count
            FROM expenses GROUP BY category ORDER BY total DESC
        """).fetchall()
        total = sum(r[1] for r in rows)
        return {
            "total_expenses": round(total, 2),
            "categories": [{"category": r[0], "total": round(r[1], 2), "count": r[2]} for r in rows],
        }


# ── Dashboard ──────────────────────────────────────────────────

@router.get("/dashboard")
async def financial_dashboard():
    """Financial overview — totals, pipeline, net position."""
    return get_financial_dashboard()
