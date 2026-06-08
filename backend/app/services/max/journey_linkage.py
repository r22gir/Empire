"""
Customer Journey Linkage Service
================================

Pilot MVP for canonical customer ↔ quote ↔ invoice ↔ payment carry-forward.

The previous scout analysis assumed the linkage columns were missing.
The live DB shows the columns already exist (denormalized text FKs):

    quotes_v2.customer_id  → customers.id       (TEXT, declared NOT NULL)
    invoices.quote_id      → quotes_v2.id        (TEXT, declared NOT NULL)
    payments.invoice_id    → invoices.id         (TEXT, declared NOT NULL)

The actual gap is data quality, not schema:

    0/28 quotes_v2 have customer_id populated
    17/20 invoices have quote_id set, but only 3/17 link to a real quote
    1/1 payments has invoice_id set, and it links correctly

This service:

    1. Walks the customer → quote → invoice → payment chain safely
    2. Tags rows that cannot be linked (anonymous quote, orphan quote,
       invoice with no quote, payment with no invoice)
    3. Provides a backfill audit (no destructive writes; the backfill
       is read-only analysis + optional log-only recommendation)
    4. Surfaces the linkage state for downstream MAX and the founder
       to decide what to do next

Important: this is a **read-only analysis** by default. The backfill
script writes to data/journey_backfill_audit.json, never to the live
DB. Any actual write (e.g. setting quotes_v2.customer_id based on a
match) is gated behind a founder-approval flag and a separate
function, run_backfill_writes(), which is NOT called from the
journey endpoint.
"""
from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger("max.journey_linkage")


# ── Paths ────────────────────────────────────────────────────────────────

# The live DB lives in the stale-fork venv/data directory because
# the systemd service is configured to use that venv. The path is
# stable across restarts; we resolve it the same way the rest of
# the app does. If a different DB path is configured (env var), we
# honor it.
DEFAULT_DB_PATH = "/home/rg/empire-repo/backend/data/empire.db"
BACKFILL_AUDIT_PATH = "/home/rg/empire-repo-main/backend/data/journey_backfill_audit.json"


def _resolve_db_path() -> str:
    """Resolve the live DB path, allowing override via env."""
    return os.environ.get("EMPIRE_DB_PATH", DEFAULT_DB_PATH).strip() or DEFAULT_DB_PATH


# ── Tagging policy ───────────────────────────────────────────────────────

TAG_ANONYMOUS = "anonymous"  # quote has no customer_id (all 28 in dev)
TAG_ORPHAN = "orphan"        # quote has customer_id but no matching customer
TAG_NO_QUOTE = "no_quote"    # invoice has no quote_id, or quote_id dangling
TAG_HAS_LINKED = "linked"    # row has a valid link to the next table
TAG_UNKNOWN = "unknown"      # internal: not yet classified


# ── Dataclasses (output shape) ──────────────────────────────────────────


@dataclass
class QuoteSummary:
    quote_id: str
    quote_number: Optional[str]
    status: Optional[str]
    total: float
    customer_link: str  # linked | anonymous | orphan
    invoice_count: int


@dataclass
class InvoiceSummary:
    invoice_id: str
    invoice_number: Optional[str]
    status: Optional[str]
    total: float
    quote_link: str  # linked | no_quote
    payment_count: int


@dataclass
class PaymentSummary:
    payment_id: str
    amount: Optional[float]
    method: Optional[str]
    invoice_link: str  # linked | no_invoice


@dataclass
class CustomerJourney:
    customer_id: str
    customer_name: Optional[str]
    customer_email: Optional[str]
    customer_phone: Optional[str]
    quotes: list  # list[QuoteSummary]
    invoices: list  # list[InvoiceSummary] (for invoices not tied to a quote)
    payments: list  # list[PaymentSummary] (orphan payments)
    totals: dict
    fetched_at: str

    def to_dict(self) -> dict:
        return {
            "customer_id": self.customer_id,
            "customer": {
                "id": self.customer_id,
                "name": self.customer_name,
                "email": self.customer_email,
                "phone": self.customer_phone,
            },
            "quotes": [asdict(q) for q in self.quotes],
            "orphan_invoices": [asdict(i) for i in self.invoices],
            "orphan_payments": [asdict(p) for p in self.payments],
            "totals": self.totals,
            "fetched_at": self.fetched_at,
        }


@dataclass
class BackfillAudit:
    ran_at: str
    db_path: str
    quotes_v2: dict  # { total, with_customer_id, anonymous, orphan }
    invoices: dict   # { total, with_quote_id, linked, no_quote, dangling }
    payments: dict   # { total, with_invoice_id, linked, no_invoice }
    recommendations: list  # list of safe recommendations
    notes: list  # any extra info

    def to_dict(self) -> dict:
        return {
            "ran_at": self.ran_at,
            "db_path": self.db_path,
            "quotes_v2": self.quotes_v2,
            "invoices": self.invoices,
            "payments": self.payments,
            "recommendations": self.recommendations,
            "notes": self.notes,
        }


# ── DB connection helper (low-level, not the FastAPI get_db) ───────────


@contextmanager
def _open_db(db_path: Optional[str] = None, read_only: bool = True):
    """Open a sqlite3 connection.

    read_only=True is the default; the journey service never writes.
    The backfill audit also never writes to the live DB; it writes to
    a JSON audit file under backend/data/.
    """
    path = db_path or _resolve_db_path()
    if read_only:
        # Open in read-only mode. Use a URI to enforce this.
        uri = f"file:{path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    else:
        conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


# ── Lookup helpers ──────────────────────────────────────────────────────


def _normalize_email(s: Optional[str]) -> str:
    if not s:
        return ""
    return s.strip().lower()


def _normalize_name(s: Optional[str]) -> str:
    if not s:
        return ""
    # Collapse whitespace and lowercase for name matching
    return re.sub(r"\s+", " ", s.strip().lower())


def _email_match_key(s: Optional[str]) -> str:
    """Build a key for exact email match. Empty string is a non-match."""
    return _normalize_email(s)


def get_customer_journey(
    customer_id: str,
    db_path: Optional[str] = None,
) -> Optional[CustomerJourney]:
    """Walk the customer → quote → invoice → payment chain.

    Returns None if the customer does not exist.
    Returns an empty-journey (no quotes/invoices/payments) if the customer
    exists but has no linked records.

    The 'orphan_invoices' field is for invoices whose customer_id points
    to this customer but whose quote_id is dangling; the 'orphan_payments'
    field is for payments whose customer_id points to this customer but
    whose invoice_id is dangling. This catches the case where the chain
    is broken mid-way and the customer is still associated at the leaf.
    """
    fetched_at = datetime.now(timezone.utc).isoformat()
    with _open_db(db_path) as conn:
        # 1. Customer
        cust_row = conn.execute(
            "SELECT id, name, email, phone, address FROM customers WHERE id = ?",
            (customer_id,),
        ).fetchone()
        if not cust_row:
            return None
        customer = dict(cust_row)

        # 2. Quotes for this customer (via customer_id)
        quote_rows = conn.execute(
            "SELECT id, quote_number, status, total, customer_id FROM quotes_v2 "
            "WHERE customer_id = ? ORDER BY created_at DESC",
            (customer_id,),
        ).fetchall()
        quotes: list[QuoteSummary] = []
        linked_quote_ids: set[str] = set()
        quote_total = 0.0
        for q in quote_rows:
            qid = q["id"]
            linked_quote_ids.add(qid)
            # Count invoices for this quote
            inv_count = conn.execute(
                "SELECT COUNT(*) AS n FROM invoices WHERE quote_id = ?", (qid,),
            ).fetchone()["n"]
            try:
                t = float(q["total"] or 0.0)
            except (TypeError, ValueError):
                t = 0.0
            quote_total += t
            quotes.append(QuoteSummary(
                quote_id=qid,
                quote_number=q["quote_number"],
                status=q["status"],
                total=t,
                customer_link=TAG_HAS_LINKED,  # we got here via customer_id match
                invoice_count=inv_count,
            ))

        # 3. Invoices: 2 categories
        #   (a) Invoices linked to a quote in linked_quote_ids
        #   (b) Invoices whose customer_id is this customer but whose
        #       quote_id is missing/dangling → these are the "orphan_invoices"
        #       that should be in the journey but are missing the quote leg.
        if linked_quote_ids:
            placeholders = ",".join("?" * len(linked_quote_ids))
            inv_rows = conn.execute(
                f"SELECT id, invoice_number, status, total, quote_id "
                f"FROM invoices WHERE quote_id IN ({placeholders}) "
                f"ORDER BY created_at DESC",
                tuple(linked_quote_ids),
            ).fetchall()
        else:
            inv_rows = []
        linked_invoice_ids: set[str] = set()
        invoice_total = 0.0
        for inv in inv_rows:
            linked_invoice_ids.add(inv["id"])
            try:
                t = float(inv["total"] or 0.0)
            except (TypeError, ValueError):
                t = 0.0
            invoice_total += t

        # Orphan invoices: customer_id = this customer, but quote_id is null/dangling
        orphan_inv_rows = conn.execute(
            "SELECT id, invoice_number, status, total, quote_id "
            "FROM invoices WHERE customer_id = ? "
            "ORDER BY created_at DESC",
            (customer_id,),
        ).fetchall()
        orphan_invoices: list[InvoiceSummary] = []
        for inv in orphan_inv_rows:
            iid = inv["id"]
            try:
                t = float(inv["total"] or 0.0)
            except (TypeError, ValueError):
                t = 0.0
            quote_id = inv["quote_id"]
            if not quote_id or quote_id not in linked_quote_ids:
                if not quote_id:
                    link_tag = TAG_NO_QUOTE
                else:
                    # Has a quote_id but the quote doesn't exist
                    link_tag = TAG_NO_QUOTE
                # Count payments
                pay_count = conn.execute(
                    "SELECT COUNT(*) AS n FROM payments WHERE invoice_id = ?", (iid,),
                ).fetchone()["n"]
                orphan_invoices.append(InvoiceSummary(
                    invoice_id=iid,
                    invoice_number=inv["invoice_number"],
                    status=inv["status"],
                    total=t,
                    quote_link=link_tag,
                    payment_count=pay_count,
                ))

        # 4. Payments: orphan only (those whose customer_id is this
        #    customer but invoice_id is missing/dangling)
        orphan_pay_rows = conn.execute(
            "SELECT id, amount, method, invoice_id FROM payments "
            "WHERE customer_id = ?",
            (customer_id,),
        ).fetchall()
        orphan_payments: list[PaymentSummary] = []
        for p in orphan_pay_rows:
            pid = p["id"]
            inv_id = p["invoice_id"]
            link_tag = TAG_HAS_LINKED if (inv_id and inv_id in linked_invoice_ids) else "no_invoice"
            if link_tag == "no_invoice":
                try:
                    amt = float(p["amount"] or 0.0)
                except (TypeError, ValueError):
                    amt = 0.0
                orphan_payments.append(PaymentSummary(
                    payment_id=pid,
                    amount=amt,
                    method=p["method"],
                    invoice_link=link_tag,
                ))

        return CustomerJourney(
            customer_id=customer_id,
            customer_name=customer.get("name"),
            customer_email=customer.get("email"),
            customer_phone=customer.get("phone"),
            quotes=quotes,
            invoices=orphan_invoices,
            payments=orphan_payments,
            totals={
                "quote_count": len(quotes),
                "linked_invoice_count": len(inv_rows),
                "orphan_invoice_count": len(orphan_invoices),
                "orphan_payment_count": len(orphan_payments),
                "quote_total": round(quote_total, 2),
                "linked_invoice_total": round(invoice_total, 2),
            },
            fetched_at=fetched_at,
        )


def get_invoice_for_quote(
    quote_id: str,
    db_path: Optional[str] = None,
) -> Optional[dict]:
    """Reverse lookup: given a quote, return the invoice linked to it.

    Returns None if no invoice is linked. Returns a dict with
    `link` = 'linked' | 'no_quote' | 'dangling' so the caller can tell
    why the lookup failed.
    """
    with _open_db(db_path) as conn:
        inv = conn.execute(
            "SELECT id, invoice_number, status, total, quote_id "
            "FROM invoices WHERE quote_id = ? LIMIT 1",
            (quote_id,),
        ).fetchone()
        if not inv:
            # Distinguish "no invoice" from "no such quote"
            q = conn.execute("SELECT id FROM quotes_v2 WHERE id = ?", (quote_id,)).fetchone()
            if not q:
                return {"link": "no_quote", "quote_id": quote_id, "invoice": None}
            return {"link": "no_invoice", "quote_id": quote_id, "invoice": None}
        return {
            "link": "linked",
            "quote_id": quote_id,
            "invoice": {
                "id": inv["id"],
                "invoice_number": inv["invoice_number"],
                "status": inv["status"],
                "total": inv["total"],
            },
        }


def get_quote_for_invoice(
    invoice_id: str,
    db_path: Optional[str] = None,
) -> Optional[dict]:
    """Reverse lookup: given an invoice, return the quote linked to it."""
    with _open_db(db_path) as conn:
        inv = conn.execute(
            "SELECT id, quote_id FROM invoices WHERE id = ?", (invoice_id,),
        ).fetchone()
        if not inv:
            return {"link": "no_invoice", "invoice_id": invoice_id, "quote": None}
        qid = inv["quote_id"]
        if not qid:
            return {"link": "no_quote", "invoice_id": invoice_id, "quote": None}
        q = conn.execute(
            "SELECT id, quote_number, status, total FROM quotes_v2 WHERE id = ?", (qid,),
        ).fetchone()
        if not q:
            return {"link": "dangling", "invoice_id": invoice_id, "quote": None, "quote_id": qid}
        return {
            "link": "linked",
            "invoice_id": invoice_id,
            "quote": {
                "id": q["id"],
                "quote_number": q["quote_number"],
                "status": q["status"],
                "total": q["total"],
            },
        }


# ── Backfill audit (read-only) ─────────────────────────────────────────


def run_backfill_audit(
    db_path: Optional[str] = None,
) -> BackfillAudit:
    """Inspect the live DB and produce a backfill audit.

    This is **read-only**: it never writes to the live DB. It only
    inspects the linkage state and writes a JSON audit log under
    backend/data/journey_backfill_audit.json.

    The audit is intended to give the founder a complete picture of
    the carry-forward gap so they can decide what to do. The
    recommendations in the audit are advisory, not prescriptive.
    """
    path = db_path or _resolve_db_path()
    ran_at = datetime.now(timezone.utc).isoformat()
    with _open_db(path) as conn:
        # Quotes v2: how many have customer_id?
        q_total = conn.execute("SELECT COUNT(*) AS n FROM quotes_v2").fetchone()["n"]
        q_with_cust = conn.execute(
            "SELECT COUNT(*) AS n FROM quotes_v2 "
            "WHERE customer_id IS NOT NULL AND customer_id != ''"
        ).fetchone()["n"]
        q_anonymous = q_total - q_with_cust
        # Orphan: customer_id set but not in customers table
        q_orphan = conn.execute(
            "SELECT COUNT(*) AS n FROM quotes_v2 q "
            "WHERE q.customer_id IS NOT NULL AND q.customer_id != '' "
            "AND NOT EXISTS (SELECT 1 FROM customers c WHERE c.id = q.customer_id)"
        ).fetchone()["n"]
        quotes_v2 = {
            "table": "quotes_v2",
            "total": q_total,
            "with_customer_id": q_with_cust,
            "anonymous": q_anonymous,
            "orphan_customer_link": q_orphan,
            "anonymous_pct": round(100 * q_anonymous / q_total, 1) if q_total else 0.0,
        }

        # Invoices: how many have quote_id, how many are valid links?
        i_total = conn.execute("SELECT COUNT(*) AS n FROM invoices").fetchone()["n"]
        i_with_q = conn.execute(
            "SELECT COUNT(*) AS n FROM invoices "
            "WHERE quote_id IS NOT NULL AND quote_id != ''"
        ).fetchone()["n"]
        i_linked = conn.execute(
            "SELECT COUNT(*) AS n FROM invoices i "
            "WHERE i.quote_id IS NOT NULL AND i.quote_id != '' "
            "AND EXISTS (SELECT 1 FROM quotes_v2 q WHERE q.id = i.quote_id)"
        ).fetchone()["n"]
        i_dangling = i_with_q - i_linked
        i_no_quote = i_total - i_with_q
        invoices = {
            "table": "invoices",
            "total": i_total,
            "with_quote_id": i_with_q,
            "linked_to_real_quote": i_linked,
            "dangling_quote_id": i_dangling,
            "no_quote_id": i_no_quote,
            "linked_pct": round(100 * i_linked / i_total, 1) if i_total else 0.0,
        }

        # Payments: how many have invoice_id, how many are valid?
        p_total = conn.execute("SELECT COUNT(*) AS n FROM payments").fetchone()["n"]
        p_with_i = conn.execute(
            "SELECT COUNT(*) AS n FROM payments "
            "WHERE invoice_id IS NOT NULL AND invoice_id != ''"
        ).fetchone()["n"]
        p_linked = conn.execute(
            "SELECT COUNT(*) AS n FROM payments p "
            "WHERE p.invoice_id IS NOT NULL AND p.invoice_id != '' "
            "AND EXISTS (SELECT 1 FROM invoices i WHERE i.id = p.invoice_id)"
        ).fetchone()["n"]
        p_dangling = p_with_i - p_linked
        p_no_inv = p_total - p_with_i
        payments = {
            "table": "payments",
            "total": p_total,
            "with_invoice_id": p_with_i,
            "linked_to_real_invoice": p_linked,
            "dangling_invoice_id": p_dangling,
            "no_invoice_id": p_no_inv,
        }

    recommendations = []
    if q_anonymous > 0:
        recommendations.append({
            "severity": "high",
            "tag": TAG_ANONYMOUS,
            "summary": f"{q_anonymous}/{q_total} quotes_v2 have no customer_id.",
            "suggestion": (
                "Run an offline name/email match against the customers table "
                "and the per-quote customer_name/customer_email fields. "
                "DO NOT auto-write; surface matches in a review queue and "
                "let the founder approve each link before the next PR."
            ),
        })
    if i_dangling > 0:
        recommendations.append({
            "severity": "medium",
            "tag": "dangling_invoice",
            "summary": f"{i_dangling}/{i_total} invoices have a quote_id that doesn't exist.",
            "suggestion": (
                "Clear the dangling quote_id and mark the invoice as "
                "no_quote via a founder-approved cleanup pass."
            ),
        })
    if p_dangling > 0:
        recommendations.append({
            "severity": "medium",
            "tag": "dangling_payment",
            "summary": f"{p_dangling}/{p_total} payments have an invoice_id that doesn't exist.",
            "suggestion": (
                "Investigate the orphan payments; they may be from a "
                "deleted invoice or a webhook race. Surface to founder "
                "for manual reconciliation."
            ),
        })
    if q_orphan > 0:
        recommendations.append({
            "severity": "low",
            "tag": TAG_ORPHAN,
            "summary": f"{q_orphan} quotes_v2 have a customer_id that doesn't exist in customers.",
            "suggestion": (
                "Re-create the customer records from the quote's "
                "denormalized name/email/phone/address fields, or "
                "null the customer_id if the customer truly does not exist."
            ),
        })

    notes = [
        "Audit is read-only. No writes to the live DB were performed.",
        f"DB inspected: {path}",
        "All counts are computed via raw SQL against the live schema.",
        "The 'tag' values in recommendations follow TAG_* constants in "
        "this module. Use these tags to drive downstream review-queue UI.",
    ]

    audit = BackfillAudit(
        ran_at=ran_at,
        db_path=path,
        quotes_v2=quotes_v2,
        invoices=invoices,
        payments=payments,
        recommendations=recommendations,
        notes=notes,
    )

    # Write the audit log to a JSON file (NOT the live DB)
    try:
        Path(BACKFILL_AUDIT_PATH).parent.mkdir(parents=True, exist_ok=True)
        # Atomic write: write to temp file, then rename
        tmp = Path(BACKFILL_AUDIT_PATH).with_suffix(".json.tmp")
        tmp.write_text(json.dumps(audit.to_dict(), indent=2, default=str))
        tmp.replace(BACKFILL_AUDIT_PATH)
        notes.append(f"Audit written to: {BACKFILL_AUDIT_PATH}")
    except Exception as e:
        notes.append(f"WARN: failed to write audit JSON: {e}")
        logger.warning(f"failed to write backfill audit: {e}")

    return audit
