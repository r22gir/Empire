"""
Empire Finance System — Invoices, Payments, Expenses, P&L Dashboard.
"""
from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel
from typing import Optional, List
import json
import os
from pathlib import Path
from datetime import datetime, date

from app.db.database import get_db, dict_row, dict_rows
from app.middleware.rate_limiter import limiter

router = APIRouter(prefix="/finance", tags=["finance"])

QUOTES_DIR = Path(__file__).resolve().parent.parent.parent / "data" / "quotes"


# ── Schemas ──────────────────────────────────────────────────────────

class InvoiceCreate(BaseModel):
    customer_id: Optional[str] = None
    quote_id: Optional[str] = None
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
    total = round(subtotal + tax_amount, 2)

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
    return inv


# ── Dashboard ────────────────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get("/dashboard")
def finance_dashboard(request: Request):
    """P&L summary: revenue MTD/YTD, expenses MTD/YTD, outstanding invoices, AR aging."""
    now = datetime.now()
    month_start = now.strftime("%Y-%m-01")
    year_start = f"{now.year}-01-01"

    with get_db() as conn:
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
            "SELECT * FROM invoices ORDER BY created_at DESC LIMIT 5"
        ).fetchall())
        for inv in recent_invoices:
            inv["line_items"] = json.loads(inv["line_items"]) if inv.get("line_items") else []

        # Expense breakdown by category MTD
        expense_breakdown = dict_rows(conn.execute(
            "SELECT category, SUM(amount) as total FROM expenses WHERE expense_date >= ? GROUP BY category ORDER BY total DESC",
            (month_start,)
        ).fetchall())

        return {
            "revenue": {
                "mtd": round(rev_mtd, 2),
                "ytd": round(rev_ytd, 2),
            },
            "expenses": {
                "mtd": round(exp_mtd, 2),
                "ytd": round(exp_ytd, 2),
                "breakdown_mtd": expense_breakdown,
            },
            "net_profit": {
                "mtd": round(rev_mtd - exp_mtd, 2),
                "ytd": round(rev_ytd - exp_ytd, 2),
            },
            "outstanding": {
                "total": round(outstanding["total"], 2),
                "count": outstanding["count"],
            },
            "accounts_receivable_aging": aging,
            "recent_invoices": recent_invoices,
        }


# ── Invoices ─────────────────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get("/invoices")
def list_invoices(
    request: Request,
    status: Optional[str] = None,
    customer_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List invoices with optional filters."""
    clauses = []
    params = []

    if status:
        clauses.append("status = ?")
        params.append(status)
    if customer_id:
        clauses.append("customer_id = ?")
        params.append(customer_id)
    if date_from:
        clauses.append("created_at >= ?")
        params.append(date_from)
    if date_to:
        clauses.append("created_at <= ?")
        params.append(date_to)

    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    params_count = list(params)
    params.extend([limit, offset])

    with get_db() as conn:
        rows = conn.execute(
            f"SELECT * FROM invoices{where} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params
        ).fetchall()

        total = conn.execute(
            f"SELECT COUNT(*) FROM invoices{where}", params_count
        ).fetchone()[0]

        invoices = [_enrich_invoice(dict_row(r)) for r in rows]
        return {"invoices": invoices, "total": total, "limit": limit, "offset": offset}


@limiter.limit("30/minute")
@router.post("/invoices")
def create_invoice(request: Request, invoice: InvoiceCreate):
    """Create a new invoice."""
    with get_db() as conn:
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
                tax_amount, total, amount_paid, balance_due, line_items, notes, terms, due_date)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, 'draft', ?, ?, ?, ?, 0, ?, ?, ?, ?, ?)""",
            (
                inv_number,
                invoice.customer_id,
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
            )
        )

        row = conn.execute(
            "SELECT * FROM invoices WHERE invoice_number = ?", (inv_number,)
        ).fetchone()
        return {"invoice": _enrich_invoice(dict_row(row))}


@limiter.limit("30/minute")
@router.get("/invoices/{invoice_id}")
def get_invoice(request: Request, invoice_id: str):
    """Get invoice detail with payments."""
    with get_db() as conn:
        row = conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone()
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

    # Extract line items from rooms
    line_items = []
    for room in (quote.get("rooms") or []):
        room_name = room.get("name", "Room")
        for window in room.get("windows", []):
            line_items.append({
                "description": f"{room_name} - {window.get('name', 'Window')} - {window.get('treatment_type', 'Treatment')}",
                "quantity": 1,
                "unit_price": window.get("total", 0),
                "total": window.get("total", 0),
            })

    subtotal = quote.get("subtotal", 0)
    # If subtotal is 0, try proposal_totals option A or sum line items
    if subtotal == 0:
        proposal_totals = quote.get("proposal_totals", {})
        if proposal_totals:
            # Use option A (budget) as default
            subtotal = proposal_totals.get("A", 0) or proposal_totals.get("B", 0) or proposal_totals.get("C", 0)
        if subtotal == 0:
            subtotal = sum(item.get("total", 0) for item in line_items)

    tax_rate = quote.get("tax_rate", 0.06)

    # Try to find or create customer
    customer_name = quote.get("customer_name", "")
    customer_email = quote.get("customer_email", "")
    customer_id = None

    with get_db() as conn:
        # Look up customer
        if customer_email:
            cust = conn.execute(
                "SELECT id FROM customers WHERE email = ?", (customer_email,)
            ).fetchone()
            if cust:
                customer_id = cust["id"]
        if not customer_id and customer_name:
            cust = conn.execute(
                "SELECT id FROM customers WHERE name = ?", (customer_name,)
            ).fetchone()
            if cust:
                customer_id = cust["id"]

        inv_number = _next_invoice_number(conn)
        tax_amount = round(subtotal * tax_rate, 2)
        total = round(subtotal + tax_amount, 2)

        from datetime import timedelta
        due = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d")

        conn.execute(
            """INSERT INTO invoices
               (id, invoice_number, customer_id, quote_id, status, subtotal, tax_rate,
                tax_amount, total, amount_paid, balance_due, line_items, notes, terms, due_date)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, 'draft', ?, ?, ?, ?, 0, ?, ?, ?, 'Net 30', ?)""",
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
                f"Generated from quote {quote.get('quote_number', quote_id)}",
                due,
            )
        )

        row = conn.execute(
            "SELECT * FROM invoices WHERE invoice_number = ?", (inv_number,)
        ).fetchone()
        return {"invoice": _enrich_invoice(dict_row(row)), "quote_id": quote_id}


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

        return {"payments": dict_rows(rows), "total": total, "limit": limit, "offset": offset}


# ── Expenses ─────────────────────────────────────────────────────────

@limiter.limit("30/minute")
@router.get("/expenses")
def list_expenses(
    request: Request,
    category: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    vendor: Optional[str] = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """List expenses with optional filters."""
    clauses = []
    params = []

    if category:
        clauses.append("category = ?")
        params.append(category)
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
        rows = conn.execute(
            f"SELECT * FROM expenses{where} ORDER BY expense_date DESC LIMIT ? OFFSET ?",
            params
        ).fetchall()

        total = conn.execute(
            f"SELECT COUNT(*) FROM expenses{where}", params_count
        ).fetchone()[0]

        return {"expenses": dict_rows(rows), "total": total, "limit": limit, "offset": offset}


@limiter.limit("30/minute")
@router.post("/expenses")
def create_expense(request: Request, expense: ExpenseCreate):
    """Create a new expense."""
    with get_db() as conn:
        exp_date = expense.expense_date or date.today().isoformat()
        conn.execute(
            """INSERT INTO expenses
               (id, category, vendor, description, amount, receipt_path, expense_date)
               VALUES (lower(hex(randomblob(8))), ?, ?, ?, ?, ?, ?)""",
            (
                expense.category,
                expense.vendor,
                expense.description,
                expense.amount,
                expense.receipt_path,
                exp_date,
            )
        )

        row = conn.execute(
            "SELECT * FROM expenses ORDER BY created_at DESC LIMIT 1"
        ).fetchone()
        return {"expense": dict_row(row)}


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
