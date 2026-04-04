"""
Financial Service — Payments, Chart of Accounts, P&L, and financial dashboard.
"""
import json
import logging
from datetime import datetime, date
from typing import Optional
from app.db.database import get_db

logger = logging.getLogger(__name__)


def _audit_log(conn, entity_type, entity_id, action, field=None, old=None, new=None, by="system", reason=None):
    conn.execute("""
        INSERT INTO financial_audit_log
        (entity_type, entity_id, action, field_name, old_value, new_value, changed_by, reason)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (entity_type, entity_id, action, field,
          str(old) if old is not None else None,
          str(new) if new is not None else None, by, reason))


# ── Payment Number ─────────────────────────────────────────────

def _next_payment_number(conn) -> str:
    year = datetime.now().year
    row = conn.execute(
        "SELECT payment_number FROM payments_v2 WHERE payment_number LIKE ? ORDER BY payment_number DESC LIMIT 1",
        (f"PMT-{year}-%",)
    ).fetchone()
    if row:
        try:
            last_seq = int(row[0].split('-')[-1])
        except (ValueError, IndexError):
            last_seq = 0
    else:
        last_seq = 0
    return f"PMT-{year}-{last_seq + 1:03d}"


# ── Payments CRUD ───────────────────────────────────────��──────

def create_payment(data: dict) -> dict:
    with get_db() as conn:
        pmt_number = _next_payment_number(conn)
        now = datetime.now().isoformat()

        amount = float(data.get('amount', 0))
        if amount <= 0:
            raise ValueError("Payment amount must be positive")

        conn.execute("""
            INSERT INTO payments_v2 (
                payment_number, invoice_id, customer_id, quote_id, amount,
                payment_method, payment_reference, payment_type, status,
                account_code, notes, payment_date, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            pmt_number,
            data.get('invoice_id'),
            data.get('customer_id'),
            data.get('quote_id'),
            amount,
            data.get('payment_method', 'check'),
            data.get('payment_reference', ''),
            data.get('payment_type', 'payment'),
            'completed',
            data.get('account_code', '1000'),  # Default: Cash
            data.get('notes', ''),
            data.get('payment_date', now),
            now, now,
        ))

        pmt_id = conn.execute("SELECT last_insert_rowid()").fetchone()[0]

        # Update invoice balance if linked
        if data.get('invoice_id'):
            inv = conn.execute("SELECT total, amount_paid FROM invoices WHERE id = ?",
                              (data['invoice_id'],)).fetchone()
            if inv:
                new_paid = round((inv[1] or 0) + amount, 2)
                new_balance = round((inv[0] or 0) - new_paid, 2)
                conn.execute("""
                    UPDATE invoices SET amount_paid = ?, balance_due = ?,
                    payment_status = CASE WHEN ? <= 0 THEN 'paid' ELSE 'partial' END,
                    updated_at = ?
                    WHERE id = ?
                """, (new_paid, new_balance, new_balance, now, data['invoice_id']))

                if new_balance <= 0:
                    conn.execute("UPDATE invoices SET status = 'paid', paid_at = ? WHERE id = ?",
                                (now, data['invoice_id']))

        # Update quote deposit_paid if this is a deposit
        if data.get('payment_type') == 'deposit' and data.get('quote_id'):
            conn.execute("""
                UPDATE quotes_v2 SET deposit_paid = deposit_paid + ?,
                balance_due = balance_due - ?, updated_at = ?
                WHERE id = ?
            """, (amount, amount, now, data['quote_id']))

        _audit_log(conn, 'payment', str(pmt_id), 'created', 'amount', None, amount,
                   data.get('changed_by', 'api'),
                   f'{data.get("payment_type", "payment")} via {data.get("payment_method", "check")}')

        return {"id": pmt_id, "payment_number": pmt_number, "amount": amount,
                "status": "completed"}


def list_payments(customer_id: str = None, invoice_id: str = None,
                  limit: int = 50, offset: int = 0) -> dict:
    with get_db() as conn:
        where, params = [], []
        if customer_id:
            where.append("customer_id = ?")
            params.append(customer_id)
        if invoice_id:
            where.append("invoice_id = ?")
            params.append(invoice_id)

        where_sql = f"WHERE {' AND '.join(where)}" if where else ""
        total = conn.execute(f"SELECT COUNT(*) FROM payments_v2 {where_sql}", params).fetchone()[0]
        rows = conn.execute(
            f"SELECT * FROM payments_v2 {where_sql} ORDER BY created_at DESC LIMIT ? OFFSET ?",
            params + [limit, offset]
        ).fetchall()

        return {"payments": [dict(r) for r in rows], "total": total}


# ── Chart of Accounts ──────────────────────────────────────────

def get_chart_of_accounts() -> list:
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM chart_of_accounts ORDER BY code"
        ).fetchall()
        return [dict(r) for r in rows]


# ── P&L Report ─────────────────────────────────────────────────

def generate_pl(start_date: str = None, end_date: str = None,
                business_unit: str = None) -> dict:
    """Generate Profit & Loss report.
    Revenue (payments completed) - COGS (5xxx) - OpEx (6xxx) = Net Profit.
    """
    with get_db() as conn:
        if not start_date:
            start_date = f"{datetime.now().year}-01-01"
        if not end_date:
            end_date = datetime.now().strftime("%Y-%m-%d")

        # Revenue: completed payments
        rev_sql = """
            SELECT COALESCE(SUM(amount), 0) FROM payments_v2
            WHERE status = 'completed' AND payment_type != 'refund'
            AND payment_date >= ? AND payment_date <= ?
        """
        rev_params = [start_date, end_date]

        total_revenue = conn.execute(rev_sql, rev_params).fetchone()[0]

        # Revenue breakdown by payment type
        rev_by_type = {}
        for row in conn.execute("""
            SELECT payment_type, COALESCE(SUM(amount), 0) as total
            FROM payments_v2
            WHERE status = 'completed' AND payment_type != 'refund'
            AND payment_date >= ? AND payment_date <= ?
            GROUP BY payment_type
        """, rev_params).fetchall():
            rev_by_type[row[0]] = round(row[1], 2)

        # Refunds
        refunds = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM payments_v2
            WHERE payment_type = 'refund' AND payment_date >= ? AND payment_date <= ?
        """, [start_date, end_date]).fetchone()[0]

        # COGS (5xxx expenses)
        cogs = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM expenses
            WHERE category LIKE '5%' OR category IN ('fabric', 'lining', 'hardware', 'materials', 'subcontractor', 'shipping')
            AND created_at >= ? AND created_at <= ?
        """, [start_date, end_date]).fetchone()[0]

        # OpEx (6xxx expenses)
        opex = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM expenses
            WHERE (category LIKE '6%' OR category IN ('rent', 'utilities', 'insurance', 'vehicle', 'marketing', 'software', 'office', 'professional'))
            AND created_at >= ? AND created_at <= ?
        """, [start_date, end_date]).fetchone()[0]

        # Expense breakdown
        expense_breakdown = {}
        for row in conn.execute("""
            SELECT category, COALESCE(SUM(amount), 0) as total
            FROM expenses WHERE created_at >= ? AND created_at <= ?
            GROUP BY category
        """, [start_date, end_date]).fetchall():
            expense_breakdown[row[0]] = round(row[1], 2)

        net_revenue = round(total_revenue - refunds, 2)
        gross_profit = round(net_revenue - cogs, 2)
        net_profit = round(gross_profit - opex, 2)
        margin = round((net_profit / net_revenue * 100), 1) if net_revenue > 0 else 0

        return {
            "period": {"start": start_date, "end": end_date},
            "business_unit": business_unit or "all",
            "revenue": {
                "gross": round(total_revenue, 2),
                "refunds": round(refunds, 2),
                "net": net_revenue,
                "by_type": rev_by_type,
            },
            "cogs": round(cogs, 2),
            "gross_profit": gross_profit,
            "operating_expenses": round(opex, 2),
            "expense_breakdown": expense_breakdown,
            "net_profit": net_profit,
            "profit_margin_pct": margin,
            "generated_at": datetime.now().isoformat(),
        }


# ── Revenue Summary ────────────────────────────────────────────

def get_revenue_summary(period: str = "month") -> dict:
    with get_db() as conn:
        now = datetime.now()
        if period == "year":
            start = f"{now.year}-01-01"
        elif period == "quarter":
            q = (now.month - 1) // 3
            start = f"{now.year}-{q * 3 + 1:02d}-01"
        else:  # month
            start = f"{now.year}-{now.month:02d}-01"

        end = now.strftime("%Y-%m-%d")

        total = conn.execute("""
            SELECT COALESCE(SUM(amount), 0) FROM payments_v2
            WHERE status = 'completed' AND payment_type != 'refund'
            AND payment_date >= ? AND payment_date <= ?
        """, (start, end)).fetchone()[0]

        count = conn.execute("""
            SELECT COUNT(*) FROM payments_v2
            WHERE status = 'completed' AND payment_date >= ? AND payment_date <= ?
        """, (start, end)).fetchone()[0]

        return {"period": period, "start": start, "end": end,
                "total_revenue": round(total, 2), "payment_count": count}


# ── Outstanding (AR Aging) ─────────────────────────────────────

def get_outstanding() -> dict:
    with get_db() as conn:
        rows = conn.execute("""
            SELECT id, invoice_number, client_name, total, balance_due,
                   created_at, due_date, status
            FROM invoices
            WHERE balance_due > 0 AND status NOT IN ('paid', 'cancelled')
            ORDER BY created_at ASC
        """).fetchall()

        invoices = [dict(r) for r in rows]
        current, past_30, past_60, past_90 = 0, 0, 0, 0
        today = date.today()

        for inv in invoices:
            due = inv.get('due_date') or inv.get('created_at', '')
            if due:
                try:
                    due_date = date.fromisoformat(due[:10])
                    days = (today - due_date).days
                    bal = inv.get('balance_due', 0)
                    if days <= 0:
                        current += bal
                    elif days <= 30:
                        past_30 += bal
                    elif days <= 60:
                        past_60 += bal
                    else:
                        past_90 += bal
                    inv['days_outstanding'] = days
                except (ValueError, TypeError):
                    current += inv.get('balance_due', 0)

        total = round(current + past_30 + past_60 + past_90, 2)

        return {
            "total_outstanding": total,
            "aging": {
                "current": round(current, 2),
                "1_30_days": round(past_30, 2),
                "31_60_days": round(past_60, 2),
                "over_60_days": round(past_90, 2),
            },
            "invoices": invoices,
        }


# ── Financial Dashboard ───────────────────────────────────────

def get_financial_dashboard() -> dict:
    with get_db() as conn:
        # Quick stats
        total_quotes = conn.execute("SELECT COALESCE(SUM(total), 0) FROM quotes_v2").fetchone()[0]
        total_invoiced = conn.execute("SELECT COALESCE(SUM(total), 0) FROM invoices").fetchone()[0]
        total_paid = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM payments_v2 WHERE status = 'completed'"
        ).fetchone()[0]
        total_outstanding = conn.execute(
            "SELECT COALESCE(SUM(balance_due), 0) FROM invoices WHERE balance_due > 0"
        ).fetchone()[0]
        total_expenses = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses").fetchone()[0]

        # Pipeline
        quotes_draft = conn.execute("SELECT COUNT(*) FROM quotes_v2 WHERE status = 'draft'").fetchone()[0]
        quotes_sent = conn.execute("SELECT COUNT(*) FROM quotes_v2 WHERE status = 'sent'").fetchone()[0]
        quotes_approved = conn.execute("SELECT COUNT(*) FROM quotes_v2 WHERE status IN ('approved', 'ordered')").fetchone()[0]
        wos_active = conn.execute("SELECT COUNT(*) FROM work_orders WHERE status NOT IN ('complete', 'delivered', 'cancelled')").fetchone()[0]

        return {
            "totals": {
                "quoted": round(total_quotes, 2),
                "invoiced": round(total_invoiced, 2),
                "collected": round(total_paid, 2),
                "outstanding": round(total_outstanding, 2),
                "expenses": round(total_expenses, 2),
                "net_position": round(total_paid - total_expenses, 2),
            },
            "pipeline": {
                "quotes_draft": quotes_draft,
                "quotes_sent": quotes_sent,
                "quotes_approved": quotes_approved,
                "work_orders_active": wos_active,
            },
            "generated_at": datetime.now().isoformat(),
        }
