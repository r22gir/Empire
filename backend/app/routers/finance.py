"""
Empire Finance System — Invoices, Payments, Expenses, P&L Dashboard.
"""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional, List
import json
import os
import sqlite3
from pathlib import Path
from datetime import datetime, date

from app.db.database import get_db, dict_row, dict_rows
from app.middleware.rate_limiter import limiter

router = APIRouter(prefix="/finance", tags=["finance"])

# ── Business name normalisation ─────────────────────────────────────
# The customers table stores short keys like "workroom", "woodcraft", "empire".
# Quotes store full names like "Empire Workroom".  This map bridges both worlds.

_BUSINESS_ALIASES: dict[str, str] = {
    "empire workroom": "workroom",
    "workroom":        "workroom",
    "woodcraft":       "woodcraft",
    "wood craft":      "woodcraft",
    "empire":          "empire",     # catch-all / unspecified
}

_BUSINESS_DISPLAY: dict[str, str] = {
    "workroom":  "Empire Workroom",
    "woodcraft": "WoodCraft",
    "empire":    "Empire",
}


def _normalise_business(raw: str | None) -> str:
    """Return the canonical short key for a business name, or 'all' if None."""
    if not raw:
        return "all"
    return _BUSINESS_ALIASES.get(raw.strip().lower(), raw.strip().lower())


def _quote_business_key(quote: dict) -> str:
    business = _normalise_business(
        quote.get("business_unit") or quote.get("business_name") or "workroom"
    )
    return "workroom" if business == "all" else business

QUOTES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "quotes"


# ── Schemas ──────────────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    customer_id: Optional[str] = None
    quote_id: Optional[str] = None
    customer_name: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_address: Optional[str] = None
    business_unit: Optional[str] = "workroom"
    subtotal: float = 0
    tax_rate: float = 0.06
    line_items: Optional[List[dict]] = None
    notes: Optional[str] = None
    terms: str = "Net 30"
    due_date: Optional[str] = None


class InvoiceUpdate(BaseModel):
    customer_id: Optional[str] = None
    status: Optional[str] = None
    subtotal: Optional[float] = None
    tax_rate: Optional[float] = None
    line_items: Optional[List[dict]] = None
    notes: Optional[str] = None
    terms: Optional[str] = None
    due_date: Optional[str] = None


class PaymentCreate(BaseModel):
    amount: float
    method: str = "check"
    reference: Optional[str] = None
    notes: Optional[str] = None
    payment_date: Optional[str] = None


class ExpenseCreate(BaseModel):
    category: str
    vendor: Optional[str] = None
    description: Optional[str] = None
    amount: float
    receipt_path: Optional[str] = None
    expense_date: Optional[str] = None
    date: Optional[str] = None
    business: Optional[str] = None
    business_unit: Optional[str] = None


# ── Helpers ──────────────────────────────────────────────────────────

def _next_invoice_number(conn) -> str:
    """Generate next invoice number like INV-2026-001."""
    year = datetime.now().year
    row = conn.execute(
        "SELECT invoice_number FROM invoices WHERE invoice_number LIKE ? ORDER BY invoice_number DESC LIMIT 1",
        (f"INV-{year}-%",)
    ).fetchone()
    if row:
        last_num = int(row["invoice_number"].split("-")[-1])
        return f"INV-{year}-{last_num + 1:03d}"
    return f"INV-{year}-001"


def _recalc_invoice(conn, invoice_id: str):
    """Recalculate invoice totals from subtotal, tax, and payments."""
    inv = dict_row(conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone())
    if not inv:
        return

    subtotal = inv["subtotal"] or 0
    tax_rate = inv["tax_rate"] or 0
    tax_amount = round(subtotal * tax_rate, 2)
    discount_raw = inv.get("discount_amount") or 0
    if inv.get("discount_type") == "percent" and discount_raw > 0:
        applied_discount = round(subtotal * (discount_raw / 100), 2)
    else:
        applied_discount = discount_raw
    total = round(subtotal + tax_amount - applied_discount, 2)

    # Sum all payments for this invoice
    paid_row = conn.execute(
        "SELECT COALESCE(SUM(amount), 0) as total_paid FROM payments WHERE invoice_id = ?",
        (invoice_id,)
    ).fetchone()
    amount_paid = paid_row["total_paid"]
    balance_due = round(total - amount_paid, 2)

    # Determine status based on payment
    status = inv["status"]
    if amount_paid >= total and total > 0:
        status = "paid"
    elif amount_paid > 0 and amount_paid < total:
        status = "partial"

    paid_at = None
    if status == "paid":
        paid_at = datetime.now().isoformat()

    conn.execute(
        """UPDATE invoices SET tax_amount = ?, total = ?, amount_paid = ?,
           balance_due = ?, status = ?, paid_at = COALESCE(paid_at, ?),
           updated_at = datetime('now') WHERE id = ?""",
        (tax_amount, total, amount_paid, balance_due, status, paid_at, invoice_id)
    )


def _enrich_invoice(inv: dict) -> dict:
    """Parse JSON fields in an invoice row."""
    if inv:
        inv["line_items"] = json.loads(inv["line_items"]) if inv.get("line_items") else []
        customer_name = inv.get("customer_name") or inv.get("client_name")
        if customer_name:
            inv["customer_name"] = customer_name
        inv["amount"] = inv.get("total") or 0
        inv["balance"] = inv.get("balance_due") or 0
    return inv


def _safe_alter(conn, table: str, column: str, col_type: str, default=None):
    try:
        dflt = f" DEFAULT {default}" if default is not None else ""
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {col_type}{dflt}")
    except sqlite3.OperationalError:
        pass


def _ensure_finance_extensions(conn):
    """Keep legacy finance endpoints safe when jobs_unified has not run first."""
    inv_cols = {
        "job_id": "TEXT",
        "client_name": "TEXT",
        "client_email": "TEXT",
        "client_phone": "TEXT",
        "client_address": "TEXT",
        "billing_address": "TEXT",
        "business_unit": "TEXT DEFAULT 'workroom'",
        "discount_amount": "REAL DEFAULT 0",
        "discount_type": "TEXT DEFAULT 'flat'",
        "deposit_required": "REAL DEFAULT 0",
        "deposit_received": "REAL DEFAULT 0",
        "payment_status": "TEXT DEFAULT 'unpaid'",
        "invoice_date": "TEXT",
        "sent_date": "TEXT",
    }
    for col, ctype in inv_cols.items():
        parts = ctype.split(" DEFAULT ")
        _safe_alter(conn, "invoices", col, parts[0], parts[1] if len(parts) > 1 else None)


def _ensure_expense_extensions(conn):
    _safe_alter(conn, "expenses", "business_unit", "TEXT", "'workroom'")


def _normalise_expense_category(raw: str | None) -> str:
    category = (raw or "other").strip().lower()
    aliases = {
        "materials": "hardware",
        "cnc_supplies": "tools",
        "cnc supplies": "tools",
        "supplies": "other",
    }
    category = aliases.get(category, category)
    allowed = {
        "fabric", "hardware", "labor", "shipping", "rent", "utilities",
        "marketing", "tools", "vehicle", "insurance", "other",
    }
    return category if category in allowed else "other"


def _find_or_create_customer_for_invoice(
    conn,
    name: str | None,
    email: str | None,
    phone: str | None,
    address: str | None,
    business_unit: str | None,
) -> Optional[str]:
    customer_name = (name or "").strip()
    customer_email = (email or "").strip()
    customer_phone = (phone or "").strip()
    customer_address = (address or "").strip()
    business_key = _normalise_business(business_unit or "workroom")
    if business_key == "all":
        business_key = "workroom"

    customer_id = None
    if customer_email:
        cust = conn.execute(
            "SELECT id FROM customers WHERE lower(email) = lower(?)",
            (customer_email,),
        ).fetchone()
        if cust:
            customer_id = cust["id"]

    if not customer_id and customer_name:
        cust = conn.execute(
            "SELECT id FROM customers WHERE lower(name) = lower(?)",
            (customer_name,),
        ).fetchone()
        if cust:
            customer_id = cust["id"]

    if customer_id:
        conn.execute(
            """UPDATE customers
               SET email = COALESCE(NULLIF(email, ''), ?),
                   phone = COALESCE(NULLIF(phone, ''), ?),
                   address = COALESCE(NULLIF(address, ''), ?),
                   business = CASE WHEN business IS NULL OR business = '' OR business = 'empire'
                                   THEN ? ELSE business END,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (
                customer_email or None,
                customer_phone or None,
                customer_address or None,
                business_key,
                customer_id,
            ),
        )
        return customer_id

    if not customer_name:
        return None

    conn.execute(
        """INSERT INTO customers
           (name, email, phone, address, type, tags, notes, total_revenue,
            lifetime_quotes, source, business)
           VALUES (?, ?, ?, ?, 'residential', '[]', NULL, 0, 0, 'invoice', ?)""",
        (
            customer_name,
            customer_email or None,
            customer_phone or None,
            customer_address or None,
            business_key,
        ),
    )
    cust = conn.execute(
        """SELECT id FROM customers
           WHERE name = ? AND COALESCE(email, '') = COALESCE(?, '')
           ORDER BY created_at DESC LIMIT 1""",
        (customer_name, customer_email or None),
    ).fetchone()
    return cust["id"] if cust else None


def _find_or_create_customer_for_quote(conn, quote: dict, business_unit: str) -> Optional[str]:
    """Return a CRM customer id for quote-origin invoices without sending mail."""
    customer_name = (quote.get("customer_name") or "").strip()
    customer_email = (quote.get("customer_email") or "").strip()
    customer_phone = (quote.get("customer_phone") or "").strip()
    customer_address = (quote.get("customer_address") or "").strip()

    customer_id = None
    if customer_email:
        cust = conn.execute(
            "SELECT id FROM customers WHERE lower(email) = lower(?)",
            (customer_email,),
        ).fetchone()
        if cust:
            customer_id = cust["id"]

    if not customer_id and customer_name:
        cust = conn.execute(
            "SELECT id FROM customers WHERE lower(name) = lower(?)",
            (customer_name,),
        ).fetchone()
        if cust:
            customer_id = cust["id"]

    if customer_id:
        conn.execute(
            """UPDATE customers
               SET email = COALESCE(NULLIF(email, ''), ?),
                   phone = COALESCE(NULLIF(phone, ''), ?),
                   address = COALESCE(NULLIF(address, ''), ?),
                   business = CASE WHEN business IS NULL OR business = '' OR business = 'empire'
                                   THEN ? ELSE business END,
                   lifetime_quotes = COALESCE(lifetime_quotes, 0) + 1,
                   updated_at = datetime('now')
               WHERE id = ?""",
            (
                customer_email or None,
                customer_phone or None,
                customer_address or None,
                business_unit,
                customer_id,
            ),
        )
        return customer_id

    if not customer_name:
        return None

    conn.execute(
        """INSERT INTO customers
           (name, email, phone, address, type, tags, notes, total_revenue,
            lifetime_quotes, source, business)
           VALUES (?, ?, ?, ?, 'residential', '[]', ?, 0, 1, 'quote', ?)""",
        (
            customer_name,
            customer_email or None,
            customer_phone or None,
            customer_address or None,
            quote.get("project_description") or quote.get("notes"),
            business_unit,
        ),
    )
    cust = conn.execute(
        """SELECT id FROM customers
           WHERE name = ? AND COALESCE(email, '') = COALESCE(?, '')
           ORDER BY created_at DESC LIMIT 1""",
        (customer_name, customer_email or None),
    ).fetchone()
    return cust["id"] if cust else None


# ── Dashboard ────────────────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get("/dashboard")
def finance_dashboard(request: Request):
    """P&L summary: revenue MTD/YTD, expenses MTD/YTD, outstanding invoices, AR aging."""
    now = datetime.now()
    month_start = now.strftime("%Y-%m-01")
    year_start = f"{now.year}-01-01"

    with get_db() as conn:
        _ensure_finance_extensions(conn)
        # Revenue MTD
        rev_mtd = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE payment_date >= ?",
            (month_start,)
        ).fetchone()["total"]

        # Revenue YTD
        rev_ytd = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE payment_date >= ?",
            (year_start,)
        ).fetchone()["total"]

        # Expenses MTD
        exp_mtd = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE expense_date >= ?",
            (month_start,)
        ).fetchone()["total"]

        # Expenses YTD
        exp_ytd = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM expenses WHERE expense_date >= ?",
            (year_start,)
        ).fetchone()["total"]

        # Outstanding invoices
        outstanding = conn.execute(
            """SELECT COALESCE(SUM(balance_due), 0) as total, COUNT(*) as count
               FROM invoices WHERE status NOT IN ('paid', 'cancelled')"""
        ).fetchone()

        # AR aging
        today = now.strftime("%Y-%m-%d")
        aging_rows = conn.execute(
            """SELECT
                 SUM(CASE WHEN julianday(?) - julianday(due_date) <= 30 THEN balance_due ELSE 0 END) as current_30,
                 SUM(CASE WHEN julianday(?) - julianday(due_date) > 30 AND julianday(?) - julianday(due_date) <= 60 THEN balance_due ELSE 0 END) as days_31_60,
                 SUM(CASE WHEN julianday(?) - julianday(due_date) > 60 AND julianday(?) - julianday(due_date) <= 90 THEN balance_due ELSE 0 END) as days_61_90,
                 SUM(CASE WHEN julianday(?) - julianday(due_date) > 90 THEN balance_due ELSE 0 END) as days_90_plus
               FROM invoices
               WHERE status NOT IN ('paid', 'cancelled', 'draft') AND due_date IS NOT NULL""",
            (today, today, today, today, today, today)
        ).fetchone()

        aging = {
            "0_30": round(aging_rows["current_30"] or 0, 2),
            "31_60": round(aging_rows["days_31_60"] or 0, 2),
            "61_90": round(aging_rows["days_61_90"] or 0, 2),
            "90_plus": round(aging_rows["days_90_plus"] or 0, 2),
        }

        # Recent invoices
        recent_invoices = dict_rows(conn.execute(
            """SELECT i.*, COALESCE(NULLIF(i.client_name, ''), c.name) as customer_name
               FROM invoices i
               LEFT JOIN customers c ON c.id = i.customer_id
               ORDER BY i.created_at DESC LIMIT 5"""
        ).fetchall())
        for inv in recent_invoices:
            inv["line_items"] = json.loads(inv["line_items"]) if inv.get("line_items") else []

        # Expense breakdown by category MTD
        expense_breakdown = dict_rows(conn.execute(
            "SELECT category, SUM(amount) as total FROM expenses WHERE expense_date >= ? GROUP BY category ORDER BY total DESC",
            (month_start,)
        ).fetchall())

        top_customers = dict_rows(conn.execute(
            """SELECT name, COALESCE(total_revenue, 0) as revenue
               FROM customers
               ORDER BY COALESCE(total_revenue, 0) DESC, updated_at DESC
               LIMIT 5"""
        ).fetchall())

        aging_list = [
            {"label": "0-30 days", "amount": aging["0_30"]},
            {"label": "31-60 days", "amount": aging["31_60"]},
            {"label": "61-90 days", "amount": aging["61_90"]},
            {"label": "90+ days", "amount": aging["90_plus"]},
        ]
        rev_mtd = round(rev_mtd, 2)
        rev_ytd = round(rev_ytd, 2)
        exp_mtd = round(exp_mtd, 2)
        exp_ytd = round(exp_ytd, 2)
        net_mtd = round(rev_mtd - exp_mtd, 2)
        net_ytd = round(rev_ytd - exp_ytd, 2)
        outstanding_total = round(outstanding["total"], 2)

        return {
            "revenue": {
                "mtd": rev_mtd,
                "ytd": rev_ytd,
            },
            "expenses": {
                "mtd": exp_mtd,
                "ytd": exp_ytd,
                "breakdown_mtd": expense_breakdown,
            },
            "net_profit": {
                "mtd": net_mtd,
                "ytd": net_ytd,
            },
            "outstanding": {
                "total": outstanding_total,
                "count": outstanding["count"],
            },
            "accounts_receivable_aging": aging,
            "recent_invoices": recent_invoices,
            "revenue_mtd": rev_mtd,
            "revenue_trend": 0,
            "expenses_mtd": exp_mtd,
            "expenses_trend": 0,
            "net_profit_mtd": net_mtd,
            "outstanding_total": outstanding_total,
            "profit_trend": 0,
            "aging": aging_list,
            "top_customers": top_customers,
        }


# ── Profit & Loss ────────────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get("/pnl")
def profit_and_loss(
    request: Request,
    business: Optional[str] = Query(None, description="Filter by business: Empire Workroom, WoodCraft, etc."),
    period: str = Query("month", description="month, quarter, or year"),
    start_date: Optional[str] = Query(None, description="Start date YYYY-MM-DD (overrides period)"),
    end_date: Optional[str] = Query(None, description="End date YYYY-MM-DD (overrides period)"),
):
    """
    Profit & Loss report, optionally filtered by business.

    Revenue comes from the *payments* table (joined to customers for business filtering).
    Expenses come from the *expenses* table (no business column — returns all expenses
    unless a future migration adds one).
    Quote stats are read from the JSON files in data/quotes/.
    """
    biz_key = _normalise_business(business)
    now = datetime.now()

    # ── Resolve date range ──────────────────────────────────────────
    if start_date and end_date:
        dt_start = start_date
        dt_end = end_date
        period_label = f"{start_date} to {end_date}"
    elif period == "year":
        dt_start = f"{now.year}-01-01"
        dt_end = now.strftime("%Y-%m-%d")
        period_label = str(now.year)
    elif period == "quarter":
        q = (now.month - 1) // 3
        q_start_month = q * 3 + 1
        dt_start = f"{now.year}-{q_start_month:02d}-01"
        dt_end = now.strftime("%Y-%m-%d")
        period_label = f"{now.year}-Q{q + 1}"
    else:  # month (default)
        dt_start = now.strftime("%Y-%m-01")
        dt_end = now.strftime("%Y-%m-%d")
        period_label = now.strftime("%Y-%m")

    with get_db() as conn:
        # ── Revenue (payments) ──────────────────────────────────────
        if biz_key != "all":
            rev_rows = dict_rows(conn.execute(
                """SELECT p.method AS category, COALESCE(SUM(p.amount), 0) AS total
                   FROM payments p
                   LEFT JOIN customers c ON p.customer_id = c.id
                   WHERE p.payment_date >= ? AND p.payment_date <= ?
                     AND (c.business = ? OR (c.business IS NULL AND ? = 'empire'))
                   GROUP BY p.method""",
                (dt_start, dt_end, biz_key, biz_key),
            ).fetchall())

            rev_total_row = conn.execute(
                """SELECT COALESCE(SUM(p.amount), 0) AS total
                   FROM payments p
                   LEFT JOIN customers c ON p.customer_id = c.id
                   WHERE p.payment_date >= ? AND p.payment_date <= ?
                     AND (c.business = ? OR (c.business IS NULL AND ? = 'empire'))""",
                (dt_start, dt_end, biz_key, biz_key),
            ).fetchone()
        else:
            rev_rows = dict_rows(conn.execute(
                """SELECT method AS category, COALESCE(SUM(amount), 0) AS total
                   FROM payments
                   WHERE payment_date >= ? AND payment_date <= ?
                   GROUP BY method""",
                (dt_start, dt_end),
            ).fetchall())

            rev_total_row = conn.execute(
                "SELECT COALESCE(SUM(amount), 0) AS total FROM payments WHERE payment_date >= ? AND payment_date <= ?",
                (dt_start, dt_end),
            ).fetchone()

        revenue_total = round(rev_total_row["total"], 2)
        revenue_by_cat = {r["category"]: round(r["total"], 2) for r in rev_rows}

        # ── Expenses ────────────────────────────────────────────────
        # expenses table has no business column, so we return all expenses
        # regardless of business filter (noted in the response).
        exp_rows = dict_rows(conn.execute(
            """SELECT category, COALESCE(SUM(amount), 0) AS total
               FROM expenses
               WHERE expense_date >= ? AND expense_date <= ?
               GROUP BY category ORDER BY total DESC""",
            (dt_start, dt_end),
        ).fetchall())

        exp_total_row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) AS total FROM expenses WHERE expense_date >= ? AND expense_date <= ?",
            (dt_start, dt_end),
        ).fetchone()

        expenses_total = round(exp_total_row["total"], 2)
        expenses_by_cat = {r["category"]: round(r["total"], 2) for r in exp_rows}

        # ── Invoice stats ───────────────────────────────────────────
        if biz_key != "all":
            inv_paid = conn.execute(
                """SELECT COUNT(*) AS cnt FROM invoices i
                   LEFT JOIN customers c ON i.customer_id = c.id
                   WHERE i.status = 'paid'
                     AND i.paid_at >= ? AND i.paid_at <= ?
                     AND (c.business = ? OR (c.business IS NULL AND ? = 'empire'))""",
                (dt_start, dt_end, biz_key, biz_key),
            ).fetchone()["cnt"]

            inv_outstanding = conn.execute(
                """SELECT COUNT(*) AS cnt, COALESCE(SUM(i.balance_due), 0) AS total
                   FROM invoices i
                   LEFT JOIN customers c ON i.customer_id = c.id
                   WHERE i.status NOT IN ('paid', 'cancelled')
                     AND (c.business = ? OR (c.business IS NULL AND ? = 'empire'))""",
                (biz_key, biz_key),
            ).fetchone()
        else:
            inv_paid = conn.execute(
                "SELECT COUNT(*) AS cnt FROM invoices WHERE status = 'paid' AND paid_at >= ? AND paid_at <= ?",
                (dt_start, dt_end),
            ).fetchone()["cnt"]

            inv_outstanding = conn.execute(
                """SELECT COUNT(*) AS cnt, COALESCE(SUM(balance_due), 0) AS total
                   FROM invoices WHERE status NOT IN ('paid', 'cancelled')"""
            ).fetchone()

    # ── Quote stats (from JSON files) ───────────────────────────────
    quotes_sent = 0
    quotes_accepted = 0

    if QUOTES_DIR.exists():
        for qf in QUOTES_DIR.iterdir():
            if not qf.name.endswith(".json") or qf.name.endswith("_verification.json"):
                continue
            try:
                qdata = json.loads(qf.read_text())
            except Exception:
                continue

            # Filter by business if requested
            if biz_key != "all":
                q_biz = _normalise_business(qdata.get("business_name"))
                if q_biz != biz_key and q_biz != "all":
                    continue

            # Filter by date range (use created_at or sent_at)
            q_date = (qdata.get("sent_at") or qdata.get("created_at") or "")[:10]
            if q_date and (q_date < dt_start or q_date > dt_end):
                continue

            q_status = qdata.get("status", "")
            if q_status in ("sent", "accepted", "proposal"):
                quotes_sent += 1
            if q_status == "accepted":
                quotes_accepted += 1

    conversion_rate = round(quotes_accepted / quotes_sent * 100, 1) if quotes_sent > 0 else 0.0

    display_name = _BUSINESS_DISPLAY.get(biz_key, business or "All Businesses")

    return {
        "business": display_name,
        "period": period_label,
        "revenue": {
            "total": revenue_total,
            "by_category": revenue_by_cat,
        },
        "expenses": {
            "total": expenses_total,
            "by_category": expenses_by_cat,
            "_note": "Expenses are not yet segmented by business" if biz_key != "all" else None,
        },
        "net_profit": round(revenue_total - expenses_total, 2),
        "invoices_paid": inv_paid,
        "invoices_outstanding": {
            "count": inv_outstanding["cnt"],
            "balance": round(inv_outstanding["total"], 2),
        },
        "quotes_sent": quotes_sent,
        "quotes_accepted": quotes_accepted,
        "conversion_rate": conversion_rate,
    }


# ── Transactions (combined payments + expenses) ──────────────────────

@limiter.limit("30/minute")
@router.get("/transactions")
def list_transactions(
    request: Request,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
):
    """Recent transactions: payments (income) + expenses combined, sorted by date."""
    clauses_p = []
    clauses_e = []
    params_p = []
    params_e = []

    if date_from:
        clauses_p.append("payment_date >= ?")
        params_p.append(date_from)
        clauses_e.append("expense_date >= ?")
        params_e.append(date_from)
    if date_to:
        clauses_p.append("payment_date <= ?")
        params_p.append(date_to)
        clauses_e.append("expense_date <= ?")
        params_e.append(date_to)

    where_p = (" WHERE " + " AND ".join(clauses_p)) if clauses_p else ""
    where_e = (" WHERE " + " AND ".join(clauses_e)) if clauses_e else ""

    with get_db() as conn:
        payments = dict_rows(conn.execute(
            f"""SELECT id, 'income' as type, amount, method as category,
                       reference as description, payment_date as date, invoice_id, customer_id,
                       created_at
                FROM payments{where_p}
                ORDER BY payment_date DESC LIMIT ?""",
            params_p + [limit]
        ).fetchall())

        expenses = dict_rows(conn.execute(
            f"""SELECT id, 'expense' as type, amount, category,
                       description, expense_date as date, NULL as invoice_id, NULL as customer_id,
                       created_at
                FROM expenses{where_e}
                ORDER BY expense_date DESC LIMIT ?""",
            params_e + [limit]
        ).fetchall())

        # Merge and sort by date descending
        transactions = sorted(
            payments + expenses,
            key=lambda t: t.get("date") or t.get("created_at") or "",
            reverse=True,
        )[:limit]

        return {"transactions": transactions, "total": len(transactions)}


# ── Invoices ─────────────────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get("/invoices")
def list_invoices(
    request: Request,
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    business: Optional[str] = None,
    business_unit: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List invoices with optional filters."""
    clauses = []
    params = []

    if status:
        clauses.append("i.status = ?")
        params.append(status)
    if customer_id:
        clauses.append("i.customer_id = ?")
        params.append(customer_id)
    biz_filter = _normalise_business(business_unit or business)
    if biz_filter != "all":
        clauses.append("i.business_unit = ?")
        params.append(biz_filter)
    if date_from:
        clauses.append("i.created_at >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("i.created_at <= ?")
        params.append(date_to)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params_count = list(params)
    params.extend([limit, offset])

    with get_db() as conn:
        _ensure_finance_extensions(conn)
        rows = conn.execute(
            f"""SELECT i.*, COALESCE(NULLIF(i.client_name, ''), c.name) as customer_name
                FROM invoices i
                LEFT JOIN customers c ON c.id = i.customer_id
                {where} ORDER BY i.created_at DESC LIMIT ? OFFSET ?""",
            params
        ).fetchall()

        total = conn.execute(
            f"SELECT COUNT(*) FROM invoices i {where}", params_count
        ).fetchone()[0]

        invoices = [_enrich_invoice(dict_row(r)) for r in rows]
        return {"invoices": invoices, "items": invoices, "total": total, "limit": limit, "offset": offset}


@limiter.limit("30/minute")
@router.post("/invoices")
def create_invoice(request: Request, invoice: InvoiceCreate):
    """Create a new invoice."""
    with get_db() as conn:
        _ensure_finance_extensions(conn)
        business_unit = _normalise_business(invoice.business_unit or "workroom")
        if business_unit == "all":
            business_unit = "workroom"
        customer_id = invoice.customer_id
        if not customer_id and invoice.customer_name:
            customer_id = _find_or_create_customer_for_invoice(
                conn,
                invoice.customer_name,
                invoice.customer_email,
                invoice.customer_phone,
                invoice.customer_address,
                business_unit,
            )

        inv_number = _next_invoice_number(conn)
        tax_amount = round(invoice.subtotal * invoice.tax_rate, 2)
        total = round(invoice.subtotal + tax_amount, 2)

        # Calculate due date if not provided
        due = invoice.due_date
        if not due:
            from datetime import timedelta
            days = 30
            if invoice.terms and invoice.terms.startswith("Net "):
                try:
                    days = int(invoice.terms.split(" ")[1])
                except (IndexError, ValueError):
                    pass
            due = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

        conn.execute(
            """INSERT INTO invoices
               (id, invoice_number, customer_id, quote_id, status, subtotal, tax_rate,
                tax_amount, total, amount_paid, balance_due, line_items, notes, terms, due_date,
                client_name, client_email, client_phone, client_address, business_unit,
                invoice_date, payment_status)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, 'draft', ?, ?, ?, ?, 0, ?, ?, ?, ?, ?,
                       ?, ?, ?, ?, ?,
                       ?, 'unpaid')""",
            (
                inv_number,
                customer_id,
                invoice.quote_id,
                invoice.subtotal,
                invoice.tax_rate,
                tax_amount,
                total,
                total,  # balance_due = total initially
                json.dumps(invoice.line_items) if invoice.line_items else None,
                invoice.notes,
                invoice.terms,
                due,
                invoice.customer_name,
                invoice.customer_email,
                invoice.customer_phone,
                invoice.customer_address,
                business_unit,
                date.today().isoformat(),
            )
        )

        row = conn.execute(
            """SELECT i.*, COALESCE(NULLIF(i.client_name, ''), c.name) as customer_name
               FROM invoices i
               LEFT JOIN customers c ON c.id = i.customer_id
               WHERE i.invoice_number = ?""",
            (inv_number,)
        ).fetchone()
        return {"invoice": _enrich_invoice(dict_row(row))}


@limiter.limit("30/minute")
@router.get("/invoices/{invoice_id}")
def get_invoice(request: Request, invoice_id: str):
    """Get invoice detail with payments."""
    with get_db() as conn:
        _ensure_finance_extensions(conn)
        row = conn.execute(
            """SELECT i.*, COALESCE(NULLIF(i.client_name, ''), c.name) as customer_name
               FROM invoices i
               LEFT JOIN customers c ON c.id = i.customer_id
               WHERE i.id = ?""",
            (invoice_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Invoice not found")

        invoice = _enrich_invoice(dict_row(row))

        # Get payments for this invoice
        payments = dict_rows(conn.execute(
            "SELECT * FROM payments WHERE invoice_id = ? ORDER BY payment_date DESC",
            (invoice_id,)
        ).fetchall())

        # Get customer info if linked
        customer = None
        if invoice.get("customer_id"):
            cust_row = conn.execute(
                "SELECT * FROM customers WHERE id = ?", (invoice["customer_id"],)
            ).fetchone()
            if cust_row:
                customer = dict_row(cust_row)

        invoice["payments"] = payments
        invoice["customer"] = customer
        return {"invoice": invoice}


@limiter.limit("30/minute")
@router.post("/invoices/{invoice_id}/send")
def mark_invoice_sent(request: Request, invoice_id: str):
    """Mark an invoice as sent without sending outbound email."""
    now = datetime.now().isoformat()
    with get_db() as conn:
        _ensure_finance_extensions(conn)
        row = conn.execute("SELECT id FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Invoice not found")

        conn.execute(
            """UPDATE invoices
               SET status = 'sent',
                   sent_at = COALESCE(sent_at, ?),
                   sent_date = COALESCE(sent_date, ?),
                   updated_at = datetime('now')
               WHERE id = ?""",
            (now, now, invoice_id),
        )
        updated = conn.execute(
            """SELECT i.*, COALESCE(NULLIF(i.client_name, ''), c.name) as customer_name
               FROM invoices i
               LEFT JOIN customers c ON c.id = i.customer_id
               WHERE i.id = ?""",
            (invoice_id,),
        ).fetchone()
        return {"invoice": _enrich_invoice(dict_row(updated)), "status": "sent"}


@limiter.limit("30/minute")
@router.patch("/invoices/{invoice_id}")
def update_invoice(request: Request, invoice_id: str, update: InvoiceUpdate):
    """Update an invoice."""
    with get_db() as conn:
        existing = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Invoice not found")

        data = update.model_dump(exclude_none=True)
        if not data:
            raise HTTPException(status_code=400, detail="No fields to update")

        fields = []
        values = []
        for key, val in data.items():
            if key == "line_items":
                val = json.dumps(val)
            fields.append(f"{key} = ?")
            values.append(val)

        fields.append("updated_at = datetime('now')")
        values.append(invoice_id)

        conn.execute(
            f"UPDATE invoices SET {', '.join(fields)} WHERE id = ?", values
        )

        # Recalculate if subtotal or tax_rate changed
        if "subtotal" in data or "tax_rate" in data:
            _recalc_invoice(conn, invoice_id)

        # Mark sent_at if status changed to sent
        if data.get("status") == "sent":
            conn.execute(
                "UPDATE invoices SET sent_at = COALESCE(sent_at, datetime('now')) WHERE id = ?",
                (invoice_id,)
            )

        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        return {"invoice": _enrich_invoice(dict_row(row))}


@limiter.limit("30/minute")
@router.delete("/invoices/{invoice_id}")
def cancel_invoice(request: Request, invoice_id: str):
    """Cancel an invoice (soft delete)."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Invoice not found")

        conn.execute(
            "UPDATE invoices SET status = 'cancelled', updated_at = datetime('now') WHERE id = ?",
            (invoice_id,)
        )
        return {"status": "cancelled", "invoice_id": invoice_id}


@limiter.limit("30/minute")
@router.post("/invoices/{invoice_id}/payment")
def record_payment(request: Request, invoice_id: str, payment: PaymentCreate):
    """Record a payment against an invoice."""
    with get_db() as conn:
        inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not inv:
            raise HTTPException(status_code=404, detail="Invoice not found")

        inv_dict = dict_row(inv)
        pay_date = payment.payment_date or date.today().isoformat()

        conn.execute(
            """INSERT INTO payments
               (id, invoice_id, customer_id, amount, method, reference, notes, payment_date)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?)""",
            (
                invoice_id,
                inv_dict.get("customer_id"),
                payment.amount,
                payment.method,
                payment.reference,
                payment.notes,
                pay_date,
            )
        )

        # Recalculate invoice totals
        _recalc_invoice(conn, invoice_id)

        # Update customer total_revenue if linked
        if inv_dict.get("customer_id"):
            conn.execute(
                """UPDATE customers SET total_revenue = (
                     SELECT COALESCE(SUM(amount), 0) FROM payments WHERE customer_id = ?
                   ), updated_at = datetime('now') WHERE id = ?""",
                (inv_dict["customer_id"], inv_dict["customer_id"])
            )

        updated_inv = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        return {"invoice": _enrich_invoice(dict_row(updated_inv))}


@limiter.limit("30/minute")
@router.post("/invoices/from-quote/{quote_id}")
def create_invoice_from_quote(request: Request, quote_id: str):
    """Create an invoice from an existing quote JSON file."""
    quote_file = QUOTES_DIR / f"{quote_id}.json"
    if not quote_file.exists():
        raise HTTPException(status_code=404, detail=f"Quote file not found: {quote_id}")

    with open(quote_file) as f:
        quote = json.load(f)

    # Extract line items from tiers (furniture quotes), rooms/windows (drapery), or flat line_items
    line_items = []
    selected_tier = quote.get("selected_tier") or "A"  # Default to tier A if none selected

    # Strategy 1: Tiered pricing (furniture/upholstery quotes)
    tiers = quote.get("tiers") or {}
    tier_data = tiers.get(selected_tier) or tiers.get("A") or tiers.get("B") or tiers.get("C")
    if tier_data and tier_data.get("items"):
        for tier_item in tier_data["items"]:
            for li in tier_item.get("line_items", []):
                line_items.append({
                    "description": li.get("description", "Item"),
                    "quantity": li.get("quantity", 1),
                    "unit_price": li.get("amount", 0),
                    "total": li.get("amount", 0),
                })

    # Strategy 2: Rooms with windows (drapery quotes)
    if not line_items:
        for room in (quote.get("rooms") or []):
            room_name = room.get("name", "Room")
            for window in room.get("windows", []):
                item_total = window.get("total") or window.get("price") or 0
                line_items.append({
                    "description": f"{room_name} - {window.get('name', 'Window')} - {window.get('treatment_type', 'Treatment')}",
                    "quantity": 1,
                    "unit_price": item_total,
                    "total": item_total,
                })

    # Strategy 3: Flat line_items array
    if not line_items:
        for item in (quote.get("line_items") or []):
            qty = item.get("quantity", 1)
            rate = item.get("rate", item.get("unit_price", 0))
            amt = item.get("amount", qty * rate)
            line_items.append({
                "description": item.get("description", "Item"),
                "quantity": qty,
                "unit_price": rate,
                "total": amt,
            })

    # Calculate subtotal: tier data > quote field > proposal_totals > sum of line items
    subtotal = 0
    if tier_data:
        subtotal = tier_data.get("subtotal", 0) or 0
    if not subtotal:
        subtotal = quote.get("subtotal", 0) or 0
    if not subtotal:
        proposal_totals = quote.get("proposal_totals", {})
        if proposal_totals:
            subtotal = proposal_totals.get("A", 0) or proposal_totals.get("B", 0) or proposal_totals.get("C", 0)
    if not subtotal:
        subtotal = sum(item.get("total", 0) for item in line_items)

    tax_rate = quote.get("tax_rate", 0.06)

    customer_name = quote.get("customer_name", "")
    customer_email = quote.get("customer_email", "")
    business_unit = _quote_business_key(quote)

    with get_db() as conn:
        customer_id = _find_or_create_customer_for_quote(conn, quote, business_unit)

        inv_number = _next_invoice_number(conn)
        tax_amount = round(subtotal * tax_rate, 2)
        discount_raw = quote.get("discount_amount", 0) or 0
        discount_type = quote.get("discount_type", "dollar") or "dollar"
        if discount_type == "percent" and discount_raw > 0:
            applied_discount = round(subtotal * (discount_raw / 100), 2)
        else:
            applied_discount = discount_raw
        total = round(subtotal + tax_amount - applied_discount, 2)
        deposit = quote.get("deposit") or {}
        deposit_required = deposit.get("deposit_amount") or 0
        if not deposit_required and deposit.get("deposit_percent"):
            deposit_required = round(total * (deposit.get("deposit_percent") or 0) / 100, 2)
        deposit_received = (
            deposit.get("deposit_received")
            or deposit.get("amount_received")
            or deposit.get("paid_amount")
            or 0
        )

        from datetime import timedelta
        due = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        conn.execute(
            """INSERT INTO invoices
               (id, invoice_number, customer_id, quote_id, status, subtotal, tax_rate,
                tax_amount, total, amount_paid, balance_due, line_items, notes, terms, due_date,
                client_name, client_email, client_phone, client_address,
                business_unit, deposit_required, deposit_received,
                discount_amount, discount_type)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, 'draft', ?, ?, ?, ?, 0, ?, ?, ?, ?,
                       ?, ?, ?, ?,
                       ?, ?, ?,
                       ?, ?, ?)""",
            (
                inv_number,
                customer_id,
                quote_id,
                subtotal,
                tax_rate,
                tax_amount,
                total,
                total,
                json.dumps(line_items),
                quote.get("notes") or f"Generated from quote {quote.get('quote_number', quote_id)}",
                quote.get("terms") or "Net 30",
                due,
                customer_name,
                customer_email,
                quote.get("customer_phone", ""),
                quote.get("customer_address", ""),
                business_unit,
                deposit_required,
                deposit_received,
                discount_raw,
                discount_type,
            )
        )

        row = conn.execute(
            "SELECT * FROM invoices WHERE invoice_number = ?", (inv_number,)
        ).fetchone()
        return {"invoice": _enrich_invoice(dict_row(row)), "quote_id": quote_id}


@limiter.limit("10/minute")
@router.post("/invoices/from-job/{job_id}")
def create_invoice_from_job(request: Request, job_id: str):
    """Create an invoice from a completed job. Pulls data from job + linked quote."""
    with get_db() as conn:
        job = dict_row(conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone())
        if not job:
            raise HTTPException(status_code=404, detail=f"Job not found: {job_id}")

        # Get line items from linked quote if available
        line_items = []
        quote_id = job.get("quote_id")
        subtotal = 0

        if quote_id:
            quote_file = QUOTES_DIR / f"{quote_id}.json"
            if quote_file.exists():
                with open(quote_file) as f:
                    quote = json.load(f)
                # Try rooms structure first
                for room in (quote.get("rooms") or []):
                    room_name = room.get("name", "Room")
                    for window in room.get("windows", []):
                        item_total = window.get("total", 0)
                        line_items.append({
                            "description": f"{room_name} - {window.get('name', 'Window')} - {window.get('treatment_type', 'Treatment')}",
                            "quantity": 1,
                            "unit_price": item_total,
                            "total": item_total,
                        })
                # Fallback: use flat line_items if no rooms
                if not line_items:
                    for item in (quote.get("line_items") or []):
                        qty = item.get("quantity", 1)
                        rate = item.get("rate", item.get("unit_price", 0))
                        amt = item.get("amount", qty * rate)
                        line_items.append({
                            "description": item.get("description", "Item"),
                            "quantity": qty,
                            "unit_price": rate,
                            "total": amt,
                        })
                subtotal = quote.get("subtotal", 0) or sum(i.get("total", 0) for i in line_items)

        # Add labor + materials from job
        if job.get("labor_cost") and job["labor_cost"] > 0:
            line_items.append({"description": "Labor", "quantity": 1, "unit_price": job["labor_cost"], "total": job["labor_cost"]})
            subtotal += job["labor_cost"]
        if job.get("materials_cost") and job["materials_cost"] > 0:
            line_items.append({"description": "Materials", "quantity": 1, "unit_price": job["materials_cost"], "total": job["materials_cost"]})
            subtotal += job["materials_cost"]

        if subtotal == 0:
            subtotal = sum(i.get("total", 0) for i in line_items)

        tax_rate = 0.06
        tax_amount = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax_amount, 2)

        from datetime import timedelta
        due = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")
        inv_number = _next_invoice_number(conn)

        conn.execute(
            """INSERT INTO invoices
               (id, invoice_number, customer_id, quote_id, status, subtotal, tax_rate,
                tax_amount, total, amount_paid, balance_due, line_items, notes, terms, due_date)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, 'draft', ?, ?, ?, ?, 0, ?, ?, ?, 'Net 30', ?)""",
            (
                inv_number,
                job.get("customer_id"),
                quote_id,
                subtotal,
                tax_rate,
                tax_amount,
                total,
                total,
                json.dumps(line_items),
                f"Generated from job {job['title']}",
                due,
            )
        )

        # Link invoice to job
        row = conn.execute("SELECT * FROM invoices WHERE invoice_number = ?", (inv_number,)).fetchone()
        inv = _enrich_invoice(dict_row(row))
        if inv:
            conn.execute("UPDATE jobs SET invoice_id = ? WHERE id = ?", (inv["id"], job_id))

        return {"invoice": inv, "job_id": job_id}


# ── Invoice PDF ──────────────────────────────────────────────────────

@router.get("/invoices/{invoice_id}/pdf")
def invoice_pdf(request: Request, invoice_id: str):
    """Generate a branded PDF for an invoice."""
    import weasyprint
    import json as _json

    # Determine which business config to use (resolved after loading invoice below)
    _config_dir = Path(__file__).resolve().parent.parent / "config"

    with get_db() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Invoice not found")

        invoice = _enrich_invoice(dict_row(row))

        # Get customer info
        customer = None
        if invoice.get("customer_id"):
            cust_row = conn.execute(
                "SELECT * FROM customers WHERE id = ?", (invoice["customer_id"],)
            ).fetchone()
            if cust_row:
                customer = dict_row(cust_row)

    # Detect WoodCraft/CraftForge invoices for correct branding
    _is_woodcraft = False
    _notes = invoice.get("notes", "") or ""
    if "WoodCraft" in _notes or "CraftForge" in _notes:
        _is_woodcraft = True
    elif invoice.get("quote_id"):
        _cf_design_path = Path(__file__).resolve().parent.parent.parent / "data" / "craftforge" / "designs" / f"{invoice['quote_id']}.json"
        if _cf_design_path.exists():
            _is_woodcraft = True
    if not _is_woodcraft and customer and customer.get("business") == "woodcraft":
        _is_woodcraft = True

    if _is_woodcraft:
        _biz_cfg_path = _config_dir / "woodcraft_business.json"
    else:
        _biz_cfg_path = _config_dir / "business.json"

    try:
        _biz_cfg = _json.loads(_biz_cfg_path.read_text())
    except Exception:
        _biz_cfg = {}
    _biz_name = _biz_cfg.get("business_name", "Empire Workroom")
    _biz_tagline = _biz_cfg.get("business_tagline", "Custom Window Treatments & Upholstery")
    _biz_phone = _biz_cfg.get("business_phone", "")
    _biz_email = _biz_cfg.get("business_email", "")
    _biz_address = _biz_cfg.get("business_address", "")
    _biz_website = _biz_cfg.get("business_website", "")

    # Set brand colors based on business
    if _is_woodcraft:
        _accent_color = "#d4a636"
        _header_bg = "#3d2e1a"
    else:
        _accent_color = "#b8960c"
        _header_bg = "#2c2416"

    # Build line items table
    items_html = ""
    for item in invoice.get("line_items") or []:
        desc = item.get("description", "")
        qty = item.get("quantity", 1)
        unit_price = item.get("unit_price", item.get("rate", 0))
        total = item.get("total", item.get("amount", 0))
        items_html += f"""<tr>
            <td style="padding:10px 12px;border-bottom:1px solid #e8e4dd">{desc}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8e4dd;text-align:center">{qty}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8e4dd;text-align:right">${unit_price:,.2f}</td>
            <td style="padding:10px 12px;border-bottom:1px solid #e8e4dd;text-align:right">${total:,.2f}</td>
        </tr>"""

    if not items_html:
        items_html = f"""<tr>
            <td style="padding:10px 12px" colspan="3">Services as quoted</td>
            <td style="padding:10px 12px;text-align:right">${invoice.get('subtotal', 0):,.2f}</td>
        </tr>"""

    customer_name = customer["name"] if customer else "Customer"
    customer_email = customer.get("email", "") if customer else ""
    customer_phone = customer.get("phone", "") if customer else ""
    customer_address = customer.get("address", "") if customer else ""

    customer_block = f"<strong>{customer_name}</strong>"
    if customer_email:
        customer_block += f"<br>{customer_email}"
    if customer_phone:
        customer_block += f"<br>{customer_phone}"
    if customer_address:
        customer_block += f"<br>{customer_address}"

    status_color = {"draft": "#888", "sent": "#2563eb", "partial": "#d97706", "paid": "#16a34a", "overdue": "#dc2626", "cancelled": "#6b7280"}.get(invoice.get("status", "draft"), "#888")

    html = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  @page {{ size: letter; margin: 0.75in; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; color: #1a1a2e; font-size: 11pt; line-height: 1.5; }}
  .header {{ display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 30px; padding-bottom: 20px; border-bottom: 3px solid {_accent_color}; }}
  .logo {{ font-size: 24pt; font-weight: 800; color: #1a1a2e; }}
  .logo span {{ color: {_accent_color}; }}
  .invoice-title {{ text-align: right; }}
  .invoice-title h1 {{ margin: 0; font-size: 28pt; color: {_accent_color}; letter-spacing: 2px; }}
  .invoice-number {{ font-size: 11pt; color: #666; margin-top: 4px; }}
  .status {{ display: inline-block; padding: 3px 12px; border-radius: 12px; font-size: 9pt; font-weight: 600; text-transform: uppercase; color: white; background: {status_color}; }}
  .info-grid {{ display: flex; justify-content: space-between; margin: 24px 0; }}
  .info-box {{ flex: 1; }}
  .info-box h3 {{ margin: 0 0 6px; font-size: 9pt; text-transform: uppercase; color: {_accent_color}; letter-spacing: 1px; }}
  table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
  thead {{ background: #f5f3ef; }}
  th {{ padding: 10px 12px; text-align: left; font-size: 9pt; text-transform: uppercase; color: #666; letter-spacing: 0.5px; border-bottom: 2px solid {_accent_color}; }}
  .totals {{ margin-left: auto; width: 280px; }}
  .totals tr td {{ padding: 6px 12px; }}
  .totals .total-row {{ font-size: 14pt; font-weight: 700; color: #1a1a2e; border-top: 2px solid {_accent_color}; }}
  .footer {{ margin-top: 40px; padding-top: 16px; border-top: 1px solid #e8e4dd; font-size: 9pt; color: #888; text-align: center; }}
</style></head><body>

<div class="header">
  <div>
    <div class="logo">{_biz_name.split()[0]} <span>{' '.join(_biz_name.split()[1:])}</span></div>
    <div style="font-size:9pt;color:#666;margin-top:4px">{_biz_tagline}</div>
    <div style="font-size:8pt;color:#888;margin-top:6px;line-height:1.6">
      {_biz_phone}<br>{_biz_email}<br>{_biz_address}
    </div>
  </div>
  <div class="invoice-title">
    <h1>INVOICE</h1>
    <div class="invoice-number">{invoice.get('invoice_number', '')}</div>
    <div style="margin-top:6px"><span class="status">{invoice.get('status', 'draft')}</span></div>
  </div>
</div>

<div class="info-grid">
  <div class="info-box">
    <h3>Bill To</h3>
    <p>{customer_block}</p>
  </div>
  <div class="info-box" style="text-align:right">
    <h3>Invoice Details</h3>
    <p>
      <strong>Date:</strong> {invoice.get('created_at', '')[:10]}<br>
      <strong>Due:</strong> {invoice.get('due_date', 'N/A')}<br>
      <strong>Terms:</strong> {invoice.get('terms', 'Net 30')}
    </p>
  </div>
</div>

<table>
  <thead><tr>
    <th>Description</th>
    <th style="text-align:center">Qty</th>
    <th style="text-align:right">Unit Price</th>
    <th style="text-align:right">Amount</th>
  </tr></thead>
  <tbody>{items_html}</tbody>
</table>

<table class="totals">
  <tr><td>Subtotal</td><td style="text-align:right">${invoice.get('subtotal', 0):,.2f}</td></tr>
  <tr><td>Tax ({invoice.get('tax_rate', 0)*100:.1f}%)</td><td style="text-align:right">${invoice.get('tax_amount', 0):,.2f}</td></tr>
  <tr class="total-row"><td>Total</td><td style="text-align:right">${invoice.get('total', 0):,.2f}</td></tr>
  <tr><td>Paid</td><td style="text-align:right">${invoice.get('amount_paid', 0):,.2f}</td></tr>
  <tr style="font-weight:700;color:{_accent_color}"><td>Balance Due</td><td style="text-align:right">${invoice.get('balance_due', 0):,.2f}</td></tr>
</table>

{"<div style='margin:20px 0;padding:12px;background:#f5f3ef;border-radius:8px;font-size:10pt'><strong>Notes:</strong> " + invoice.get('notes', '') + "</div>" if invoice.get('notes') else ""}

<div class="footer">
  {_biz_name} &mdash; Thank you for your business<br>
  {_biz_phone} &bull; {_biz_email} &bull; {_biz_website}
</div>

</body></html>"""

    pdf_bytes = weasyprint.HTML(string=html).write_pdf()

    # Save PDF
    pdf_dir = Path(__file__).resolve().parent.parent.parent / "data" / "invoices" / "pdf"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = pdf_dir / f"{invoice['invoice_number']}.pdf"
    with open(pdf_path, "wb") as f:
        f.write(pdf_bytes)

    from fastapi.responses import Response as FastResponse
    return FastResponse(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{invoice["invoice_number"]}.pdf"'},
    )


# ── Payments ─────────────────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get("/payments")
def list_payments(
    request: Request,
    invoice_id: Optional[str] = None,
    customer_id: Optional[str] = None,
    method: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List all payments with optional filters."""
    clauses = []
    params = []

    if invoice_id:
        clauses.append("invoice_id = ?")
        params.append(invoice_id)
    if customer_id:
        clauses.append("customer_id = ?")
        params.append(customer_id)
    if method:
        clauses.append("method = ?")
        params.append(method)
    if date_from:
        clauses.append("payment_date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("payment_date <= ?")
        params.append(date_to)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params_count = list(params)
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM payments{where} ORDER BY payment_date DESC LIMIT ? OFFSET ?",
            params
        ).fetchall()

        total = conn.execute(
            f"SELECT COUNT(*) FROM payments{where}", params_count
        ).fetchone()[0]

        payments = dict_rows(rows)
        return {"payments": payments, "items": payments, "total": total, "limit": limit, "offset": offset}


# ── Expenses ─────────────────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get("/expenses")
def list_expenses(
    request: Request,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    vendor: Optional[str] = None,
    business: Optional[str] = None,
    business_unit: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List expenses with optional filters."""
    clauses = []
    params = []

    if category:
        clauses.append("category = ?")
        params.append(_normalise_expense_category(category))
    biz_filter = _normalise_business(business_unit or business)
    if biz_filter != "all":
        clauses.append("business_unit = ?")
        params.append(biz_filter)
    if date_from:
        clauses.append("expense_date >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("expense_date <= ?")
        params.append(date_to)
    if vendor:
        clauses.append("vendor LIKE ?")
        params.append(f"%{vendor}%")

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params_count = list(params)
    params.extend([limit, offset])

    with get_db() as conn:
        _ensure_expense_extensions(conn)
        rows = conn.execute(
            f"SELECT * FROM expenses{where} ORDER BY expense_date DESC LIMIT ? OFFSET ?",
            params
        ).fetchall()

        total = conn.execute(
            f"SELECT COUNT(*) FROM expenses{where}", params_count
        ).fetchone()[0]

        expenses = dict_rows(rows)
        for exp in expenses:
            exp["date"] = exp.get("expense_date")
        return {"expenses": expenses, "items": expenses, "total": total, "limit": limit, "offset": offset}


@limiter.limit("30/minute")
@router.post("/expenses")
def create_expense(request: Request, expense: ExpenseCreate):
    """Create a new expense."""
    with get_db() as conn:
        _ensure_expense_extensions(conn)
        exp_date = expense.expense_date or expense.date or date.today().isoformat()
        business_unit = _normalise_business(expense.business_unit or expense.business or "workroom")
        if business_unit == "all":
            business_unit = "workroom"
        category = _normalise_expense_category(expense.category)
        conn.execute(
            """INSERT INTO expenses
               (id, category, vendor, description, amount, receipt_path, expense_date, business_unit)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?, ?)""",
            (
                category,
                expense.vendor,
                expense.description,
                expense.amount,
                expense.receipt_path,
                exp_date,
                business_unit,
            )
        )

        row = conn.execute(
            "SELECT * FROM expenses ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        result = dict_row(row)
        result["date"] = result.get("expense_date")
        return {"expense": result}


@limiter.limit("30/minute")
@router.delete("/expenses/{expense_id}")
def delete_expense(request: Request, expense_id: str):
    """Delete an expense."""
    with get_db() as conn:
        existing = conn.execute("SELECT id FROM expenses WHERE id = ?", (expense_id,)).fetchone()
        if not existing:
            raise HTTPException(status_code=404, detail="Expense not found")

        conn.execute("DELETE FROM expenses WHERE id = ?", (expense_id,))
        return {"status": "deleted", "expense_id": expense_id}


# ── Revenue ──────────────────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get("/revenue")
def revenue_breakdown(
    request: Request,
    period: str = Query("monthly", description="monthly, weekly, or yearly"),
    year: Optional[int] = None,
):
    """Revenue breakdown by period, customer, and type."""
    target_year = year or datetime.now().year

    with get_db() as conn:
        # Revenue by period
        if period == "monthly":
            period_rows = dict_rows(conn.execute(
                """SELECT strftime('%Y-%m', payment_date) as period,
                          SUM(amount) as total, COUNT(*) as count
                   FROM payments
                   WHERE strftime('%Y', payment_date) = ?
                   GROUP BY period ORDER BY period""",
                (str(target_year),)
            ).fetchall())
        elif period == "weekly":
            period_rows = dict_rows(conn.execute(
                """SELECT strftime('%Y-W%W', payment_date) as period,
                          SUM(amount) as total, COUNT(*) as count
                   FROM payments
                   WHERE strftime('%Y', payment_date) = ?
                   GROUP BY period ORDER BY period""",
                (str(target_year),)
            ).fetchall())
        else:  # yearly
            period_rows = dict_rows(conn.execute(
                """SELECT strftime('%Y', payment_date) as period,
                          SUM(amount) as total, COUNT(*) as count
                   FROM payments
                   GROUP BY period ORDER BY period"""
            ).fetchall())

        # Revenue by customer (top 10)
        by_customer = dict_rows(conn.execute(
            """SELECT c.name as customer_name, c.id as customer_id,
                      SUM(p.amount) as total, COUNT(p.id) as payment_count
               FROM payments p
               LEFT JOIN customers c ON p.customer_id = c.id
               WHERE strftime('%Y', p.payment_date) = ?
               GROUP BY p.customer_id
               ORDER BY total DESC LIMIT 10""",
            (str(target_year),)
        ).fetchall())

        # Revenue by payment method
        by_method = dict_rows(conn.execute(
            """SELECT method, SUM(amount) as total, COUNT(*) as count
               FROM payments
               WHERE strftime('%Y', payment_date) = ?
               GROUP BY method ORDER BY total DESC""",
            (str(target_year),)
        ).fetchall())

        # Total
        total_row = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) as total FROM payments WHERE strftime('%Y', payment_date) = ?",
            (str(target_year),)
        ).fetchone()

        return {
            "year": target_year,
            "period_type": period,
            "by_period": period_rows,
            "by_customer": by_customer,
            "by_method": by_method,
            "total": round(total_row["total"], 2),
        }


# ── Revenue by Category (Drill-Down) ─────────────────────────────────

@router.get("/revenue-by-category")
def revenue_by_category(
    request: Request,
    category: Optional[str] = None,
):
    """Revenue grouped by item type (drapery, upholstery, etc.).
    If category specified, returns job-level detail for that category."""
    with get_db() as conn:
        if category:
            # Drill into a specific category — show individual jobs
            rows = dict_rows(conn.execute("""
                SELECT q.id as quote_id, q.quote_number, q.customer_name,
                       q.total, q.status, q.created_at,
                       i.item_type, i.description, i.subtotal as item_subtotal
                FROM quote_line_items i
                JOIN quotes_v2 q ON q.id = i.quote_id
                WHERE LOWER(i.item_type) LIKE ? OR LOWER(i.description) LIKE ?
                ORDER BY q.created_at DESC
            """, (f"%{category.lower()}%", f"%{category.lower()}%")).fetchall())
            return {"category": category, "items": rows, "count": len(rows)}

        # Summary by category
        rows = dict_rows(conn.execute("""
            SELECT
                COALESCE(NULLIF(i.item_type, ''), 'other') as category,
                COUNT(DISTINCT q.id) as quote_count,
                SUM(i.subtotal) as total_value,
                COUNT(i.id) as item_count
            FROM quote_line_items i
            JOIN quotes_v2 q ON q.id = i.quote_id
            WHERE q.status NOT IN ('cancelled', 'rejected')
            GROUP BY COALESCE(NULLIF(i.item_type, ''), 'other')
            ORDER BY total_value DESC
        """).fetchall())
        grand_total = sum(r.get("total_value", 0) or 0 for r in rows)
        return {"categories": rows, "grand_total": round(grand_total, 2)}


# ── Revenue by Client (Drill-Down) ───────────────────────────────────

@router.get("/revenue-by-client")
def revenue_by_client(
    request: Request,
    customer_id: Optional[str] = None,
):
    """Client revenue. If customer_id specified, shows full history."""
    with get_db() as conn:
        if customer_id:
            # Specific client detail
            customer = dict_row(conn.execute(
                "SELECT * FROM customers WHERE id = ?", (customer_id,)
            ).fetchone()) if conn.execute("SELECT 1 FROM customers WHERE id = ?", (customer_id,)).fetchone() else None

            quotes = dict_rows(conn.execute("""
                SELECT id, quote_number, customer_name, total, status, created_at
                FROM quotes_v2 WHERE customer_id = ?
                ORDER BY created_at DESC
            """, (customer_id,)).fetchall())

            invoices = dict_rows(conn.execute("""
                SELECT id, invoice_number, total, amount_paid, balance_due, status, created_at
                FROM invoices WHERE customer_id = ?
                ORDER BY created_at DESC
            """, (customer_id,)).fetchall())

            payments = dict_rows(conn.execute("""
                SELECT amount, method, payment_date, notes
                FROM payments WHERE customer_id = ?
                ORDER BY payment_date DESC
            """, (customer_id,)).fetchall())

            lifetime = sum(p.get("amount", 0) or 0 for p in payments)
            return {
                "customer": customer,
                "quotes": quotes,
                "invoices": invoices,
                "payments": payments,
                "lifetime_value": round(lifetime, 2),
            }

        # Top clients summary
        rows = dict_rows(conn.execute("""
            SELECT c.id, c.name, c.total_revenue,
                   COUNT(DISTINCT q.id) as quote_count,
                   (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE customer_id = c.id) as actual_revenue
            FROM customers c
            LEFT JOIN quotes_v2 q ON q.customer_id = c.id
            GROUP BY c.id
            ORDER BY actual_revenue DESC
            LIMIT 20
        """).fetchall())
        return {"top_clients": rows}


# ── AR Aging Detail ─���────────────────────────────────────────────────

@router.get("/ar-aging")
def ar_aging_detail(request: Request):
    """Detailed accounts receivable aging report with individual invoices."""
    with get_db() as conn:
        today = datetime.now().strftime("%Y-%m-%d")
        rows = dict_rows(conn.execute("""
            SELECT i.id, i.invoice_number, i.total, i.balance_due, i.due_date, i.status,
                   COALESCE(i.client_name, c.name) as customer_name,
                   c.email as customer_email,
                   CAST(julianday(?) - julianday(i.due_date) AS INTEGER) as days_overdue
            FROM invoices i
            LEFT JOIN customers c ON c.id = i.customer_id
            WHERE i.status NOT IN ('paid', 'cancelled', 'draft')
              AND i.balance_due > 0
              AND i.due_date IS NOT NULL
            ORDER BY i.due_date ASC
        """, (today,)).fetchall())

        buckets = {"0_30": [], "31_60": [], "61_90": [], "90_plus": []}
        for r in rows:
            d = r.get("days_overdue", 0)
            if d <= 30:
                buckets["0_30"].append(r)
            elif d <= 60:
                buckets["31_60"].append(r)
            elif d <= 90:
                buckets["61_90"].append(r)
            else:
                buckets["90_plus"].append(r)

        totals = {k: round(sum(i.get("balance_due", 0) for i in v), 2) for k, v in buckets.items()}
        return {
            "buckets": buckets,
            "totals": totals,
            "grand_total": round(sum(totals.values()), 2),
            "invoice_count": len(rows),
        }


# ── Job Profitability ────────────────────────────────────────────────

@router.get("/job-profitability/{job_id}")
def job_profitability(request: Request, job_id: str):
    """Revenue vs costs for a single job."""
    with get_db() as conn:
        job = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if not job:
            raise HTTPException(404, f"Job {job_id} not found")
        job = dict_row(job)

        # Revenue from payments
        revenue = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE invoice_id IN (SELECT id FROM invoices WHERE job_id = ?)",
            (job_id,)
        ).fetchone()[0]

        # Expenses linked to this job
        expenses = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE job_id = ?",
            (job_id,)
        ).fetchone()[0]

        # Quote value
        quoted = job.get("quoted_amount", 0) or 0

        profit = round(revenue - expenses, 2)
        margin = round((profit / revenue * 100), 1) if revenue > 0 else 0

        return {
            "job_id": job_id,
            "job_number": job.get("job_number"),
            "customer": job.get("client_name"),
            "quoted_amount": quoted,
            "revenue": round(revenue, 2),
            "expenses": round(expenses, 2),
            "profit": profit,
            "margin_pct": margin,
            "status": job.get("status"),
        }


# ── Monthly Comparison ───────────────────────────────────────────────

@router.get("/monthly-comparison")
def monthly_comparison(request: Request, months: int = Query(6, ge=2, le=24)):
    """Month-over-month revenue/expenses with % change."""
    with get_db() as conn:
        rows = dict_rows(conn.execute("""
            SELECT
                strftime('%Y-%m', payment_date) as month,
                SUM(amount) as revenue
            FROM payments
            GROUP BY month
            ORDER BY month DESC
            LIMIT ?
        """, (months,)).fetchall())
        rows.reverse()

        exp_rows = dict_rows(conn.execute("""
            SELECT
                strftime('%Y-%m', expense_date) as month,
                SUM(amount) as expenses
            FROM expenses
            GROUP BY month
            ORDER BY month DESC
            LIMIT ?
        """, (months,)).fetchall())
        exp_map = {r["month"]: r["expenses"] for r in exp_rows}

        result = []
        for i, r in enumerate(rows):
            rev = r.get("revenue", 0) or 0
            exp = exp_map.get(r["month"], 0) or 0
            profit = round(rev - exp, 2)
            prev_rev = rows[i - 1].get("revenue", 0) if i > 0 else 0
            pct_change = round((rev - prev_rev) / prev_rev * 100, 1) if prev_rev > 0 else 0

            result.append({
                "month": r["month"],
                "revenue": round(rev, 2),
                "expenses": round(exp, 2),
                "profit": profit,
                "revenue_change_pct": pct_change,
            })

        return {"months": result, "count": len(result)}
