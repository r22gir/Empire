"""
Empire Client Portal Service — Secure token-based portal for customers
to view quotes, production status, invoices, and approve/pay.
"""
import os
import secrets
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.db.database import get_db, dict_row, dict_rows

logger = logging.getLogger(__name__)

PORTAL_BASE_URL = os.getenv("PORTAL_BASE_URL", "https://studio.empirebox.store")


# ── Table Init ──────────────────────────────────────────────────────

def init_portal_tables():
    """Create client_portal_tokens table if it doesn't exist."""
    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS client_portal_tokens (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                token           TEXT    UNIQUE NOT NULL,
                customer_id     TEXT    NOT NULL,
                job_id          TEXT,
                quote_id        TEXT,
                can_view_photos     INTEGER DEFAULT 1,
                can_view_drawings   INTEGER DEFAULT 1,
                can_view_production INTEGER DEFAULT 1,
                can_view_invoice    INTEGER DEFAULT 1,
                can_pay             INTEGER DEFAULT 1,
                can_approve_quote   INTEGER DEFAULT 1,
                can_message         INTEGER DEFAULT 0,
                is_active       INTEGER DEFAULT 1,
                expires_at      TEXT,
                last_accessed_at TEXT,
                access_count    INTEGER DEFAULT 0,
                created_at      TEXT DEFAULT (datetime('now'))
            );

            CREATE INDEX IF NOT EXISTS idx_portal_token
                ON client_portal_tokens(token);
            CREATE INDEX IF NOT EXISTS idx_portal_customer
                ON client_portal_tokens(customer_id);
        """)
    logger.info("client_portal_tokens table ready")


# ── Generate Link ───────────────────────────────────────────────────

def generate_portal_link(
    customer_id: str,
    job_id: Optional[str] = None,
    quote_id: Optional[str] = None,
    expires_days: int = 30,
) -> dict:
    """Create a new portal token for a customer and return the link."""
    token = secrets.token_urlsafe(32)
    expires_at = (datetime.utcnow() + timedelta(days=expires_days)).isoformat()

    with get_db() as conn:
        conn.execute(
            """
            INSERT INTO client_portal_tokens
                (token, customer_id, job_id, quote_id, expires_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (token, customer_id, job_id, quote_id, expires_at),
        )

    url = f"{PORTAL_BASE_URL}/portal/{token}"
    return {"token": token, "url": url, "customer_id": customer_id}


# ── Portal Data (main read) ────────────────────────────────────────

def get_portal_data(token: str) -> dict:
    """
    Validate a portal token and return all data the customer is
    permitted to see: quote, production, invoice, payments.
    """
    with get_db() as conn:
        # ── Validate token ──────────────────────────────────────
        row = conn.execute(
            "SELECT * FROM client_portal_tokens WHERE token = ?", (token,)
        ).fetchone()

        if not row:
            return {"valid": False, "error": "Invalid portal link"}

        tok = dict(row)

        if not tok["is_active"]:
            return {"valid": False, "error": "This portal link has been revoked"}

        if tok["expires_at"]:
            if datetime.fromisoformat(tok["expires_at"]) < datetime.utcnow():
                return {"valid": False, "error": "This portal link has expired"}

        # ── Update access stats ─────────────────────────────────
        conn.execute(
            """
            UPDATE client_portal_tokens
            SET access_count = access_count + 1,
                last_accessed_at = datetime('now')
            WHERE token = ?
            """,
            (token,),
        )

        customer_id = tok["customer_id"]
        job_id = tok.get("job_id")
        quote_id = tok.get("quote_id")

        result = {
            "valid": True,
            "token": token,
            "customer": None,
            "quote": None,
            "production": None,
            "production_timeline": None,
            "invoice": None,
            "payments": None,
            "can_pay": bool(tok["can_pay"]),
            "can_approve_quote": bool(tok["can_approve_quote"]),
        }

        # ── Customer info ───────────────────────────────────────
        cust = conn.execute(
            "SELECT id, name, email, phone, address, company FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()
        if cust:
            result["customer"] = dict(cust)

        # ── Quote + line items ──────────────────────────────────
        if quote_id and tok["can_view_invoice"]:
            quote = conn.execute(
                "SELECT * FROM quotes_v2 WHERE id = ?", (quote_id,)
            ).fetchone()
            if quote:
                q = dict(quote)
                q.pop("internal_notes", None)
                line_items = conn.execute(
                    "SELECT * FROM quote_line_items WHERE quote_id = ?",
                    (quote_id,),
                ).fetchall()
                q["line_items"] = dict_rows(line_items)
                result["quote"] = q

        # ── Production status ───────────────────────────────────
        if tok["can_view_production"]:
            wo_where, wo_params = _build_wo_filter(customer_id, job_id, quote_id)
            work_orders = conn.execute(
                f"SELECT * FROM work_orders WHERE {wo_where} ORDER BY due_date",
                wo_params,
            ).fetchall()

            production = []
            wo_ids = []
            for wo in work_orders:
                wo_dict = dict(wo)
                wo_id = wo_dict["id"]
                wo_ids.append(wo_id)
                items = conn.execute(
                    "SELECT * FROM work_order_items WHERE work_order_id = ?",
                    (wo_id,),
                ).fetchall()
                wo_dict["items"] = dict_rows(items)
                production.append(wo_dict)

            result["production"] = production

            # ── Production timeline ─────────────────────────────
            if wo_ids:
                placeholders = ",".join("?" * len(wo_ids))
                timeline = conn.execute(
                    f"""
                    SELECT * FROM production_log
                    WHERE work_order_id IN ({placeholders})
                    ORDER BY created_at DESC
                    """,
                    wo_ids,
                ).fetchall()
                result["production_timeline"] = dict_rows(timeline)
            else:
                result["production_timeline"] = []

        # ── Invoice + payments ──────────────────────────────────
        if tok["can_view_invoice"]:
            inv_where, inv_params = _build_inv_filter(customer_id, job_id, quote_id)
            invoices = conn.execute(
                f"""
                SELECT id, total, amount_paid, balance_due, status,
                       customer_id, quote_id, job_id
                FROM invoices WHERE {inv_where}
                ORDER BY rowid DESC
                """,
                inv_params,
            ).fetchall()
            inv_list = dict_rows(invoices)

            # Attach payments to each invoice
            for inv in inv_list:
                payments = conn.execute(
                    """
                    SELECT id, amount, payment_method, status, payment_date
                    FROM payments_v2 WHERE invoice_id = ?
                    """,
                    (inv["id"],),
                ).fetchall()
                inv["payments"] = dict_rows(payments)

            result["invoice"] = inv_list
            result["payments"] = [
                p for inv in inv_list for p in inv.get("payments", [])
            ]

    return result


# ── List Links ──────────────────────────────────────────────────────

def list_portal_links(active_only: bool = True) -> list:
    """Return all portal tokens, optionally filtered to active only."""
    with get_db() as conn:
        if active_only:
            sql = """
                SELECT t.*, c.name AS customer_name
                FROM client_portal_tokens t
                LEFT JOIN customers c ON c.id = t.customer_id
                WHERE t.is_active = 1
                ORDER BY t.created_at DESC
            """
        else:
            sql = """
                SELECT t.*, c.name AS customer_name
                FROM client_portal_tokens t
                LEFT JOIN customers c ON c.id = t.customer_id
                ORDER BY t.created_at DESC
            """
        rows = conn.execute(sql).fetchall()
    return dict_rows(rows)


# ── Revoke Link ─────────────────────────────────────────────────────

def revoke_portal_link(token: str) -> bool:
    """Deactivate a portal token. Returns True if a row was updated."""
    with get_db() as conn:
        cur = conn.execute(
            "UPDATE client_portal_tokens SET is_active = 0 WHERE token = ?",
            (token,),
        )
    return cur.rowcount > 0


# ── Approve Quote ───────────────────────────────────────────────────

def approve_quote_via_portal(token: str) -> dict:
    """
    Customer approves their quote through the portal.
    Validates permissions and updates quote status.
    """
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM client_portal_tokens WHERE token = ?", (token,)
        ).fetchone()

        if not row:
            return {"success": False, "error": "Invalid portal link"}

        tok = dict(row)

        if not tok["is_active"]:
            return {"success": False, "error": "This portal link has been revoked"}

        if tok["expires_at"]:
            if datetime.fromisoformat(tok["expires_at"]) < datetime.utcnow():
                return {"success": False, "error": "This portal link has expired"}

        if not tok["can_approve_quote"]:
            return {"success": False, "error": "Quote approval not permitted on this link"}

        quote_id = tok.get("quote_id")
        if not quote_id:
            return {"success": False, "error": "No quote associated with this portal link"}

        quote = conn.execute(
            "SELECT id, status FROM quotes_v2 WHERE id = ?", (quote_id,)
        ).fetchone()

        if not quote:
            return {"success": False, "error": "Quote not found"}

        if dict(quote)["status"] == "approved":
            return {"success": True, "message": "Quote was already approved"}

        conn.execute(
            "UPDATE quotes_v2 SET status = 'approved' WHERE id = ?",
            (quote_id,),
        )

    return {"success": True, "quote_id": quote_id, "message": "Quote approved"}


# ── Internal helpers ────────────────────────────────────────────────

def _build_wo_filter(customer_id: str, job_id: Optional[str], quote_id: Optional[str]):
    """Build WHERE clause for work_orders lookup."""
    clauses = ["customer_id = ?"]
    params = [customer_id]
    if job_id:
        clauses.append("job_id = ?")
        params.append(job_id)
    if quote_id:
        clauses.append("quote_id = ?")
        params.append(quote_id)
    return " AND ".join(clauses), params


def _build_inv_filter(customer_id: str, job_id: Optional[str], quote_id: Optional[str]):
    """Build WHERE clause for invoices lookup."""
    clauses = ["customer_id = ?"]
    params = [customer_id]
    if job_id:
        clauses.append("job_id = ?")
        params.append(job_id)
    if quote_id:
        clauses.append("quote_id = ?")
        params.append(quote_id)
    return " AND ".join(clauses), params
