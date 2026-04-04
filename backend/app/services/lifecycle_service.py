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


# ── Status Cascade Definitions ────────────────────────────────

STATUS_CASCADES = {
    "quote_approved": [
        "create_job_from_quote",
        "send_portal_link_if_email",
    ],
    "deposit_paid": [
        "update_quote_to_ordered",
        "create_work_order_from_approved_quote",
    ],
    "work_order_complete": [
        "create_invoice_from_quote",
    ],
    "invoice_paid": [
        "update_job_to_complete",
        "update_customer_lifetime_value",
    ],
}


def execute_cascade(trigger: str, context: dict) -> dict:
    """Execute all cascade actions for a given trigger."""
    actions = STATUS_CASCADES.get(trigger, [])
    results = []

    for action_name in actions:
        try:
            fn = globals().get(action_name) or _cascade_actions.get(action_name)
            if fn:
                result = fn(context.get("quote_id", ""), context.get("changed_by", "cascade"))
                results.append({"action": action_name, "status": "ok", "result": str(result)})
            else:
                results.append({"action": action_name, "status": "skipped", "error": "function not found"})
        except Exception as e:
            logger.warning(f"Cascade {action_name} failed: {e}")
            results.append({"action": action_name, "status": "error", "error": str(e)})

    return {"trigger": trigger, "actions_run": len(results), "results": results}


def _cascade_update_job_to_complete(quote_id: str, changed_by: str = "cascade") -> str:
    with get_db() as conn:
        q = conn.execute("SELECT job_id FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
        if q and q[0]:
            conn.execute("UPDATE jobs SET status = 'complete', updated_at = ? WHERE id = ?",
                         (datetime.now().isoformat(), q[0]))
            return f"job {q[0]} → complete"
    return "no job linked"


def _cascade_update_customer_lifetime_value(quote_id: str, changed_by: str = "cascade") -> str:
    with get_db() as conn:
        q = conn.execute("SELECT customer_id FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
        if q and q[0]:
            conn.execute("""
                UPDATE customers SET
                    total_revenue = (SELECT COALESCE(SUM(amount), 0) FROM payments WHERE customer_id = ?),
                    updated_at = ?
                WHERE id = ?
            """, (q[0], datetime.now().isoformat(), q[0]))
            return f"customer {q[0]} LTV updated"
    return "no customer linked"


def _cascade_send_portal_link_if_email(quote_id: str, changed_by: str = "cascade") -> str:
    with get_db() as conn:
        q = conn.execute("SELECT customer_id FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
        if not q or not q[0]:
            return "no customer linked"
        c = conn.execute("SELECT email FROM customers WHERE id = ?", (q[0],)).fetchone()
        if not c or not c[0]:
            return "customer has no email"
        from app.services.client_portal_service import generate_portal_link
        link = generate_portal_link(q[0], quote_id=quote_id)
        return f"portal: {link['url']}"


def _cascade_update_quote_to_ordered(quote_id: str, changed_by: str = "cascade") -> str:
    with get_db() as conn:
        conn.execute("UPDATE quotes_v2 SET status = 'ordered', updated_at = ? WHERE id = ?",
                     (datetime.now().isoformat(), quote_id))
    return "quote → ordered"


_cascade_actions = {
    "update_job_to_complete": _cascade_update_job_to_complete,
    "update_customer_lifetime_value": _cascade_update_customer_lifetime_value,
    "send_portal_link_if_email": _cascade_send_portal_link_if_email,
    "update_quote_to_ordered": _cascade_update_quote_to_ordered,
}


# ── Daily Actions ─────────────────────────────────────────────

def get_daily_actions() -> dict:
    """Get today's action items for the founder's dashboard."""
    now = datetime.now()
    today = now.strftime("%Y-%m-%d")
    actions = []

    with get_db() as conn:
        # 1. Drafts with items ready to send
        drafts = conn.execute("""
            SELECT q.id, q.quote_number, q.customer_name, q.total,
                   COUNT(i.id) as item_count
            FROM quotes_v2 q
            JOIN quote_line_items i ON i.quote_id = q.id
            WHERE q.status = 'draft'
            GROUP BY q.id HAVING item_count > 0
            ORDER BY q.updated_at DESC LIMIT 10
        """).fetchall()
        for d in drafts:
            d = dict(d)
            actions.append({
                "type": "send_quote", "icon": "📧", "priority": "medium",
                "label": f"Send quote to {d['customer_name']}",
                "detail": f"{d['quote_number']} — ${d.get('total', 0):,.2f}",
                "entity_type": "quote", "entity_id": d["id"],
            })

        # 2. Approved quotes needing deposit
        approved = conn.execute("""
            SELECT q.id, q.quote_number, q.customer_name, q.total
            FROM quotes_v2 q
            WHERE q.status = 'approved'
              AND (q.deposit_paid IS NULL OR q.deposit_paid = 0)
        """).fetchall()
        for a in approved:
            a = dict(a)
            actions.append({
                "type": "collect_deposit", "icon": "💰", "priority": "high",
                "label": f"Collect deposit from {a['customer_name']}",
                "detail": f"${round(a.get('total', 0) * 0.5, 2):,.2f} on {a['quote_number']}",
                "entity_type": "quote", "entity_id": a["id"],
            })

        # 3. Approved quotes without work orders
        no_wo = conn.execute("""
            SELECT q.id, q.quote_number, q.customer_name
            FROM quotes_v2 q
            WHERE q.status IN ('approved', 'ordered')
              AND NOT EXISTS (SELECT 1 FROM work_orders wo WHERE wo.quote_id = q.id)
        """).fetchall()
        for n in no_wo:
            n = dict(n)
            actions.append({
                "type": "create_work_order", "icon": "🔧", "priority": "high",
                "label": f"Create work order for {n['customer_name']}",
                "detail": n["quote_number"],
                "entity_type": "quote", "entity_id": n["id"],
            })

        # 4. Overdue invoices
        overdue = conn.execute("""
            SELECT i.id, i.invoice_number, i.balance_due, i.due_date,
                   COALESCE(i.client_name, c.name) as customer_name
            FROM invoices i
            LEFT JOIN customers c ON c.id = i.customer_id
            WHERE i.balance_due > 0 AND i.due_date IS NOT NULL AND i.due_date < ?
              AND i.status NOT IN ('paid', 'cancelled')
        """, (today,)).fetchall()
        for o in overdue:
            o = dict(o)
            actions.append({
                "type": "send_reminder", "icon": "⚠️", "priority": "urgent",
                "label": f"Overdue: {o.get('customer_name', 'Unknown')}",
                "detail": f"Invoice #{o.get('invoice_number')} — ${o.get('balance_due', 0):,.2f}",
                "entity_type": "invoice", "entity_id": o["id"],
            })

        # 5. Complete work orders ready for invoicing
        complete_wos = conn.execute("""
            SELECT wo.id, wo.work_order_number, wo.customer_name, wo.quote_id
            FROM work_orders wo
            WHERE wo.status = 'complete'
              AND NOT EXISTS (SELECT 1 FROM invoices inv WHERE inv.quote_id = wo.quote_id)
        """).fetchall()
        for c in complete_wos:
            c = dict(c)
            actions.append({
                "type": "create_invoice", "icon": "✅", "priority": "high",
                "label": f"Invoice {c['customer_name']} — work complete",
                "detail": c["work_order_number"],
                "entity_type": "work_order", "entity_id": c["id"],
            })

    # Sort by priority
    prio = {"urgent": 0, "high": 1, "medium": 2, "low": 3}
    actions.sort(key=lambda a: prio.get(a["priority"], 9))

    return {
        "date": today, "actions": actions, "count": len(actions),
        "summary": {p: sum(1 for a in actions if a["priority"] == p) for p in ("urgent", "high", "medium")},
    }


# ── Quick Stats ───────────────────────────────────────────────

def get_quick_stats() -> dict:
    """Quick stats for the founder dashboard header."""
    with get_db() as conn:
        now = datetime.now()
        month_start = now.strftime("%Y-%m-01")

        rev = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM payments WHERE payment_date >= ?", (month_start,)
        ).fetchone()[0]
        rev2 = conn.execute(
            "SELECT COALESCE(SUM(amount), 0) FROM payments_v2 WHERE payment_date >= ? AND status = 'completed'",
            (month_start,)
        ).fetchone()[0]

        active_jobs = conn.execute(
            "SELECT COUNT(*) FROM jobs WHERE status IN ('approved', 'in_production', 'ordered')"
        ).fetchone()[0]
        pending_quotes = conn.execute(
            "SELECT COUNT(*) FROM quotes_v2 WHERE status IN ('draft', 'sent')"
        ).fetchone()[0]
        pipeline = conn.execute(
            "SELECT COALESCE(SUM(total), 0) FROM quotes_v2 WHERE status NOT IN ('cancelled', 'rejected', 'expired')"
        ).fetchone()[0]
        in_production = conn.execute(
            "SELECT COUNT(*) FROM work_orders WHERE status = 'in_progress'"
        ).fetchone()[0]

        return {
            "revenue_mtd": round(rev + rev2, 2),
            "active_jobs": active_jobs,
            "pending_quotes": pending_quotes,
            "pipeline_value": round(pipeline, 2),
            "in_production": in_production,
        }
