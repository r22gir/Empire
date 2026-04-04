"""
Lifecycle Service — Wires the full business flow:
  Prospect → Customer → Quote → Job → Work Order → Invoice → Payment

Each transition creates/links records across tables and logs to audit.
"""
import json
import uuid
import logging
from datetime import datetime
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


# ── 4A: Prospect → Customer ──────────────────────────────────

def convert_prospect_to_customer(prospect_id: int, changed_by: str = "system") -> dict:
    """When a prospect responds/converts: create a customer record from prospect data."""
    with get_db() as conn:
        p = conn.execute("SELECT * FROM prospects WHERE id = ?", (prospect_id,)).fetchone()
        if not p:
            raise ValueError(f"Prospect {prospect_id} not found")
        p = dict(p)

        # Check if customer already exists (by email or phone)
        existing = None
        if p.get('email'):
            existing = conn.execute(
                "SELECT id FROM customers WHERE email = ?", (p['email'],)
            ).fetchone()
        if not existing and p.get('phone'):
            existing = conn.execute(
                "SELECT id FROM customers WHERE phone = ?", (p['phone'],)
            ).fetchone()

        if existing:
            customer_id = existing[0]
            _audit_log(conn, 'prospect', str(prospect_id), 'linked_to_customer',
                       'customer_id', None, customer_id, changed_by,
                       'Existing customer found by email/phone')
        else:
            customer_id = str(uuid.uuid4())[:8]
            now = datetime.now().isoformat()
            conn.execute("""
                INSERT INTO customers (id, name, email, phone, address, company, source, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                customer_id,
                p.get('name', p.get('business_name', '')),
                p.get('email', ''),
                p.get('phone', ''),
                f"{p.get('address', '')} {p.get('city', '')} {p.get('state', '')} {p.get('zip', '')}".strip(),
                p.get('business_name', ''),
                f"leadforge-{p.get('source', 'prospect')}",
                f"Converted from prospect #{prospect_id}. {p.get('card_summary', '')}",
                now, now,
            ))
            _audit_log(conn, 'customer', customer_id, 'created_from_prospect',
                       'prospect_id', None, prospect_id, changed_by)

        # Update prospect status
        conn.execute("UPDATE prospects SET status = 'converted' WHERE id = ?", (prospect_id,))
        _audit_log(conn, 'prospect', str(prospect_id), 'converted',
                   'status', p.get('status'), 'converted', changed_by)

        return {"customer_id": customer_id, "prospect_id": prospect_id,
                "is_new": existing is None}


# ── 4B: Quote → Job ─────────────────────────────────────────

def create_job_from_quote(quote_id: str, changed_by: str = "system") -> dict:
    """On quote approval: create a job if not linked, set quote.job_id."""
    with get_db() as conn:
        q = conn.execute("SELECT * FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
        if not q:
            raise ValueError(f"Quote {quote_id} not found")
        q = dict(q)

        # If already linked, return existing job
        if q.get('job_id'):
            job = conn.execute("SELECT * FROM jobs WHERE id = ?", (q['job_id'],)).fetchone()
            if job:
                return dict(job)

        # Generate job number
        year = datetime.now().year
        row = conn.execute(
            "SELECT job_number FROM jobs WHERE job_number LIKE ? ORDER BY job_number DESC LIMIT 1",
            (f"JOB-{year}-%",)
        ).fetchone()
        if row:
            try:
                last_seq = int(row[0].split('-')[-1])
            except (ValueError, IndexError):
                last_seq = 0
        else:
            last_seq = 0
        job_number = f"JOB-{year}-{last_seq + 1:03d}"

        job_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        conn.execute("""
            INSERT INTO jobs (
                id, job_number, title, customer_id, quote_id, status, job_type,
                priority, client_name, client_email, client_phone, client_address,
                business_unit, description, quoted_amount, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            job_id, job_number,
            q.get('project_name', f"Job for {q.get('customer_name', 'Customer')}"),
            q.get('customer_id'),
            quote_id,
            'quoted',
            q.get('business_unit', 'workroom'),
            'normal',
            q.get('customer_name', ''),
            q.get('customer_email', ''),
            q.get('customer_phone', ''),
            q.get('customer_address', ''),
            q.get('business_unit', 'workroom'),
            q.get('project_description', ''),
            q.get('total', 0),
            now, now,
        ))

        # Link quote to job
        conn.execute("UPDATE quotes_v2 SET job_id = ?, updated_at = ? WHERE id = ?",
                     (job_id, now, quote_id))

        _audit_log(conn, 'job', job_id, 'created_from_quote',
                   'quote_id', None, quote_id, changed_by)
        _audit_log(conn, 'quote', quote_id, 'linked_to_job',
                   'job_id', None, job_id, changed_by)

        return {"id": job_id, "job_number": job_number, "quote_id": quote_id,
                "status": "quoted", "title": q.get('project_name', '')}


# ── 4C: Quote → Work Order ─────────────────────────────────

def create_work_order_from_approved_quote(quote_id: str, changed_by: str = "system") -> dict:
    """On order (deposit confirmed): create WO, update statuses."""
    from app.services.work_order_service import create_work_order_from_quote
    wo = create_work_order_from_quote(quote_id)

    with get_db() as conn:
        # Update job status if linked
        q = conn.execute("SELECT job_id FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
        if q and q[0]:
            conn.execute("UPDATE jobs SET status = 'in_production', updated_at = ? WHERE id = ?",
                        (datetime.now().isoformat(), q[0]))
            _audit_log(conn, 'job', q[0], 'status_change', 'status', 'quoted', 'in_production',
                       changed_by, f'WO created from quote {quote_id}')

    return wo


# ── 4D: Work Order → Invoice ──────────────────────────────

def create_invoice_from_quote(quote_id: str, changed_by: str = "system") -> dict:
    """On WO completion: generate invoice from quote totals minus deposit."""
    with get_db() as conn:
        q = conn.execute("SELECT * FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
        if not q:
            raise ValueError(f"Quote {quote_id} not found")
        q = dict(q)

        # Generate invoice number
        year = datetime.now().year
        row = conn.execute(
            "SELECT invoice_number FROM invoices WHERE invoice_number LIKE ? ORDER BY invoice_number DESC LIMIT 1",
            (f"INV-{year}-%",)
        ).fetchone()
        if row:
            try:
                last_seq = int(row[0].split('-')[-1])
            except (ValueError, IndexError):
                last_seq = 0
        else:
            last_seq = 0
        inv_number = f"INV-{year}-{last_seq + 1:03d}"

        inv_id = str(uuid.uuid4())[:8]
        now = datetime.now().isoformat()

        # Get line items for the invoice
        items = conn.execute(
            "SELECT description, quantity, unit_price, subtotal, category FROM quote_line_items WHERE quote_id = ?",
            (quote_id,)
        ).fetchall()
        line_items_json = json.dumps([dict(i) for i in items], default=str)

        deposit_paid = q.get('deposit_paid', 0) or 0
        balance = round((q.get('total', 0) or 0) - deposit_paid, 2)

        conn.execute("""
            INSERT INTO invoices (
                id, invoice_number, customer_id, quote_id, job_id, status,
                subtotal, tax_rate, tax_amount, total, amount_paid, balance_due,
                line_items, terms, client_name, client_email, client_phone,
                client_address, business_unit, deposit_required, deposit_received,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            inv_id, inv_number,
            q.get('customer_id'), quote_id, q.get('job_id'),
            'draft',
            q.get('subtotal', 0), q.get('tax_rate', 0), q.get('tax_amount', 0),
            q.get('total', 0), deposit_paid, balance,
            line_items_json,
            q.get('terms', 'Net 30'),
            q.get('customer_name', ''), q.get('customer_email', ''),
            q.get('customer_phone', ''), q.get('customer_address', ''),
            q.get('business_unit', 'workroom'),
            q.get('deposit_required', 0), deposit_paid,
            now, now,
        ))

        # Update job status
        if q.get('job_id'):
            conn.execute("UPDATE jobs SET status = 'invoiced', invoice_id = ?, invoiced_amount = ?, invoiced_date = ?, updated_at = ? WHERE id = ?",
                        (inv_id, q.get('total', 0), now, now, q['job_id']))

        _audit_log(conn, 'invoice', inv_id, 'created_from_quote',
                   'quote_id', None, quote_id, changed_by,
                   f'Total: ${q.get("total", 0)}, Deposit: ${deposit_paid}, Balance: ${balance}')

        return {
            "id": inv_id, "invoice_number": inv_number,
            "quote_id": quote_id, "total": q.get('total', 0),
            "deposit_paid": deposit_paid, "balance_due": balance,
        }


# ── Full Lifecycle Status ─────────────────────────────────────

def get_lifecycle_status(quote_id: str) -> dict:
    """Get full lifecycle status for a quote — all linked records."""
    with get_db() as conn:
        q = conn.execute("SELECT * FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
        if not q:
            return None
        q = dict(q)

        result = {
            "quote": {
                "id": q['id'], "quote_number": q['quote_number'],
                "status": q['status'], "total": q['total'],
            },
            "job": None,
            "work_order": None,
            "invoice": None,
            "payments": [],
        }

        if q.get('job_id'):
            job = conn.execute("SELECT id, job_number, status, pipeline_stage FROM jobs WHERE id = ?",
                              (q['job_id'],)).fetchone()
            if job:
                result['job'] = dict(job)

        wo = conn.execute("SELECT id, work_order_number, status FROM work_orders WHERE quote_id = ?",
                         (quote_id,)).fetchone()
        if wo:
            result['work_order'] = dict(wo)

        inv = conn.execute("SELECT id, invoice_number, status, balance_due FROM invoices WHERE quote_id = ?",
                          (quote_id,)).fetchone()
        if inv:
            result['invoice'] = dict(inv)
            payments = conn.execute(
                "SELECT id, amount, payment_method, status, payment_date FROM payments_v2 WHERE invoice_id = ?",
                (inv['id'],)
            ).fetchall()
            result['payments'] = [dict(p) for p in payments]

        return result
