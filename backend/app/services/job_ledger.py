"""Job-aware invoice ledger: estimate -> invoices -> payments.

One payments table is the source of truth: ``payments`` (the table the Finance
module, dashboard, P&L, AR aging, customer ledger and Command Center read).
Manual payment entry, the jobs API and the Stripe webhook all write through
``record_payment`` below.  Older Stripe rows that only exist in ``payments_v2``
are still read (de-duplicated) so history is never lost.

Rules
- A payment belongs to the invoice it was paid on.  Later invoices for the same
  job (change orders, progress, final) list it as a credit; they never copy it.
- Credits are payments only, never "amounts invoiced" -> no double counting.
- Voided/refunded payments and cancelled/void invoices are ignored.
- A final invoice bills the current contract total less every payment received
  on the job; when another payment lands on an earlier invoice in the job, the
  final invoice balance is recalculated.
"""
from __future__ import annotations

import json
import re
import uuid
from datetime import date, datetime
from typing import Iterable, Optional

VOID_INVOICE = {"cancelled", "canceled", "void", "voided"}
VOID_PAYMENT = {"void", "voided", "refunded", "failed", "cancelled", "canceled", "reversed"}
_INV_NO = re.compile(r"INV-\d{4}-\d{3,5}")
_CENT = 0.005
_METHODS = {"cash", "check", "card", "zelle", "venmo", "wire", "other"}  # payments.method CHECK


def _r(x) -> float:
    try:
        return round(float(x or 0) + 0.0, 2)
    except (TypeError, ValueError):
        return 0.0


def _row(r) -> Optional[dict]:
    return dict(r) if r is not None else None


def _cols(conn, table: str) -> set:
    try:
        return {r[1] for r in conn.execute(f"PRAGMA table_info({table})").fetchall()}
    except Exception:
        return set()


def _add_col(conn, table: str, col: str, decl: str) -> None:
    if col in _cols(conn, table):
        return
    try:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {decl}")
    except Exception:
        pass


def ensure_ledger_schema(conn) -> None:
    """Additive only: status/void/stripe columns on payments, supersede link on invoices."""
    if _cols(conn, "payments"):
        _add_col(conn, "payments", "status", "TEXT DEFAULT 'completed'")
        _add_col(conn, "payments", "stripe_session_id", "TEXT")
        _add_col(conn, "payments", "source", "TEXT")
        _add_col(conn, "payments", "voided_at", "TEXT")
        _add_col(conn, "payments", "void_reason", "TEXT")
    if _cols(conn, "invoices"):
        for col, decl in (("supersedes_invoice_id", "TEXT"), ("payment_status", "TEXT DEFAULT 'unpaid'"),
                          ("paid_at", "TEXT"), ("updated_at", "TEXT"), ("invoice_stage", "TEXT"),
                          ("deposit_required", "REAL DEFAULT 0"), ("deposit_received", "REAL DEFAULT 0"),
                          ("pricing_snapshot_json", "TEXT"), ("quote_id", "TEXT"), ("job_id", "TEXT"),
                          ("source_type", "TEXT"), ("source_id", "TEXT"), ("sent_at", "TEXT")):
            _add_col(conn, "invoices", col, decl)


def _snapshot(inv: dict) -> dict:
    snap = inv.get("pricing_snapshot_json") or {}
    if isinstance(snap, str):
        try:
            snap = json.loads(snap)
        except (TypeError, ValueError):
            snap = {}
    return snap if isinstance(snap, dict) else {}


def _settlement(inv: dict) -> dict:
    s = _snapshot(inv).get("final_settlement")
    return s if isinstance(s, dict) else {}


def _is_void_invoice(inv: dict) -> bool:
    return str(inv.get("status") or "").strip().lower() in VOID_INVOICE


# ── payments ────────────────────────────────────────────────────────────────

def invoice_payments(conn, invoice_ids: Iterable[str]) -> list[dict]:
    """Every live payment on these invoices, from the canonical table plus any
    payments_v2-only Stripe rows (deduped by session id / reference)."""
    ids = [i for i in dict.fromkeys(invoice_ids) if i]
    if not ids:
        return []
    ensure_ledger_schema(conn)
    q = ",".join("?" * len(ids))
    pcols = _cols(conn, "payments")
    out: list[dict] = []
    seen_sessions: set = set()
    seen_refs: set = set()
    if pcols:
        status_sql = "COALESCE(status,'completed')" if "status" in pcols else "'completed'"
        rows = conn.execute(
            f"SELECT *, {status_sql} AS _status FROM payments WHERE invoice_id IN ({q}) "
            f"ORDER BY payment_date, created_at", ids).fetchall()
        for r in rows:
            d = dict(r)
            if str(d.get("_status") or "").lower() in VOID_PAYMENT:
                continue
            sess = d.get("stripe_session_id") or ""
            ref = str(d.get("reference") or "")
            notes = str(d.get("notes") or "")
            for m in re.findall(r"cs_(?:live|test)_[A-Za-z0-9]+", ref + " " + notes):
                seen_sessions.add(m)
            if sess:
                seen_sessions.add(sess)
            if ref:
                seen_refs.add(ref)
            out.append({
                "id": d.get("id"), "table": "payments", "invoice_id": d.get("invoice_id"),
                "amount": _r(d.get("amount")), "method": d.get("method") or "",
                "reference": ref, "payment_date": str(d.get("payment_date") or d.get("created_at") or "")[:10],
                "notes": notes, "stripe_session_id": sess or None,
            })
    v2cols = _cols(conn, "payments_v2")
    if v2cols:
        rows = conn.execute(f"SELECT * FROM payments_v2 WHERE invoice_id IN ({q})", ids).fetchall()
        for r in rows:
            d = dict(r)
            if str(d.get("status") or "completed").lower() in VOID_PAYMENT:
                continue
            sess = d.get("stripe_session_id") or ""
            ref = str(d.get("payment_reference") or "")
            if (sess and sess in seen_sessions) or (ref and ref in seen_refs):
                continue
            out.append({
                "id": f"v2:{d.get('id')}", "table": "payments_v2", "invoice_id": d.get("invoice_id"),
                "amount": _r(d.get("amount")), "method": d.get("payment_method") or "",
                "reference": ref, "payment_date": str(d.get("payment_date") or "")[:10],
                "notes": d.get("notes") or "", "stripe_session_id": sess or None,
            })
    return out


def paid_on_invoice(conn, invoice_id: str) -> float:
    return _r(sum(p["amount"] for p in invoice_payments(conn, [invoice_id])))


def session_already_recorded(conn, stripe_session_id: str) -> bool:
    if not stripe_session_id:
        return False
    ensure_ledger_schema(conn)
    if conn.execute("SELECT 1 FROM payments WHERE stripe_session_id = ? LIMIT 1", (stripe_session_id,)).fetchone():
        return True
    if _cols(conn, "payments_v2") and conn.execute(
            "SELECT 1 FROM payments_v2 WHERE stripe_session_id = ? LIMIT 1", (stripe_session_id,)).fetchone():
        return True
    return False


def record_payment(conn, invoice_id: str, amount: float, *, method: str = "other", reference: str = "",
                   notes: str = "", payment_date: Optional[str] = None, stripe_session_id: Optional[str] = None,
                   source: str = "manual", payment_id: Optional[str] = None) -> dict:
    """The single writer for invoice payments. Idempotent on stripe_session_id."""
    ensure_ledger_schema(conn)
    amount = _r(amount)
    if amount <= 0:
        raise ValueError("Payment amount must be positive")
    inv = _row(conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone())
    if not inv:
        raise LookupError(f"Invoice not found: {invoice_id}")
    if stripe_session_id and session_already_recorded(conn, stripe_session_id):
        row = _row(conn.execute("SELECT * FROM payments WHERE stripe_session_id = ? LIMIT 1",
                                (stripe_session_id,)).fetchone())
        return {"payment": row, "duplicate": True, "invoice": recalc_invoice(conn, invoice_id)}
    pid = payment_id or uuid.uuid4().hex[:16]
    method = (method or "other").strip().lower()
    if method not in _METHODS:
        notes = f"{notes} (method: {method})".strip() if method else notes
        method = "other"
    customer_id = inv.get("customer_id")
    if customer_id and not conn.execute("SELECT 1 FROM customers WHERE id = ?", (customer_id,)).fetchone():
        customer_id = None  # keep the payment; the FK would reject an orphan customer id
    conn.execute(
        """INSERT INTO payments (id, invoice_id, customer_id, amount, method, reference, notes,
                                 payment_date, status, stripe_session_id, source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed', ?, ?)""",
        (pid, invoice_id, customer_id, amount, method, reference or "", notes or "",
         payment_date or date.today().isoformat(), stripe_session_id, source),
    )
    updated = recalc_invoice(conn, invoice_id)
    recalc_job_finals(conn, invoice_id)
    _refresh_customer_revenue(conn, inv.get("customer_id"))
    row = _row(conn.execute("SELECT * FROM payments WHERE id = ?", (pid,)).fetchone())
    return {"payment": row, "duplicate": False, "invoice": updated}


def void_payment(conn, payment_id: str, reason: str = "") -> dict:
    ensure_ledger_schema(conn)
    p = _row(conn.execute("SELECT * FROM payments WHERE id = ?", (payment_id,)).fetchone())
    if not p:
        raise LookupError(f"Payment not found: {payment_id}")
    conn.execute("UPDATE payments SET status = 'voided', voided_at = ?, void_reason = ? WHERE id = ?",
                 (datetime.now().isoformat(timespec="seconds"), reason or "", payment_id))
    inv = recalc_invoice(conn, p["invoice_id"]) if p.get("invoice_id") else None
    if p.get("invoice_id"):
        recalc_job_finals(conn, p["invoice_id"])
    _refresh_customer_revenue(conn, p.get("customer_id"))
    return {"payment_id": payment_id, "status": "voided", "invoice": inv}


def _refresh_customer_revenue(conn, customer_id: Optional[str]) -> None:
    if not customer_id or "total_revenue" not in _cols(conn, "customers"):
        return
    conn.execute(
        """UPDATE customers SET total_revenue = (
             SELECT COALESCE(SUM(amount), 0) FROM payments
             WHERE customer_id = ? AND lower(COALESCE(status,'completed')) NOT IN
               ('void','voided','refunded','failed','cancelled','canceled','reversed')
           ), updated_at = datetime('now') WHERE id = ?""",
        (customer_id, customer_id),
    )


# ── job grouping ────────────────────────────────────────────────────────────

def _credit_refs(inv: dict) -> list[str]:
    co = _snapshot(inv).get("change_order")
    refs = []
    if isinstance(co, dict):
        refs += _INV_NO.findall(str(co.get("credit_ref") or ""))
    return refs


def related_invoices(conn, invoice_id: str) -> list[dict]:
    """All invoices of the same job: same quote, same job, supersede links, or a change
    order's credit reference.  Kept to one customer when customer ids are present."""
    ensure_ledger_schema(conn)
    start = _row(conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone())
    if not start:
        return []
    cust = start.get("customer_id")
    seen: dict[str, dict] = {start["id"]: start}
    queue = [start]
    while queue:
        cur = queue.pop()
        cands = []
        for col, val in (("quote_id", cur.get("quote_id")), ("source_id", cur.get("source_id")),
                         ("job_id", cur.get("job_id")), ("id", cur.get("supersedes_invoice_id")),
                         ("supersedes_invoice_id", cur.get("id"))):
            if val:
                cands += conn.execute(f"SELECT * FROM invoices WHERE {col} = ?", (val,)).fetchall()
        for num in _credit_refs(cur):
            cands += conn.execute("SELECT * FROM invoices WHERE invoice_number = ?", (num,)).fetchall()
        if cur.get("invoice_number"):
            cands += conn.execute(
                "SELECT * FROM invoices WHERE pricing_snapshot_json LIKE ?",
                (f"%{cur['invoice_number']}%",)).fetchall()
        for r in cands:
            d = dict(r)
            if d["id"] in seen:
                continue
            if cust and d.get("customer_id") and d.get("customer_id") != cust:
                continue
            if d["id"] != cur["id"] and d.get("invoice_number") and cur.get("invoice_number") \
                    and d["id"] != cur.get("supersedes_invoice_id") and cur["id"] != d.get("supersedes_invoice_id") \
                    and d["invoice_number"] not in _credit_refs(cur) and cur["invoice_number"] not in _credit_refs(d) \
                    and not ((d.get("quote_id") and d.get("quote_id") == cur.get("quote_id"))
                             or (d.get("job_id") and d.get("job_id") == cur.get("job_id"))
                             or (d.get("source_id") and d.get("source_id") in (cur.get("source_id"), cur.get("quote_id")))):
                continue  # LIKE match that is not a real credit reference
            seen[d["id"]] = d
            queue.append(d)
    return sorted(seen.values(), key=lambda d: (str(d.get("created_at") or ""), str(d.get("invoice_number") or "")))


def _superseded_ids(group: list[dict]) -> set:
    out = set()
    by_no = {g.get("invoice_number"): g["id"] for g in group}
    for g in group:
        if _is_void_invoice(g):
            continue
        if g.get("supersedes_invoice_id"):
            out.add(g["supersedes_invoice_id"])
        for num in _credit_refs(g):
            if num in by_no:
                out.add(by_no[num])
        for sid in _settlement(g).get("supersedes", []) or []:
            out.add(sid)
    for g in group:
        if str(g.get("payment_status") or "").lower() == "superseded":
            out.add(g["id"])
    return out


# ── balances ────────────────────────────────────────────────────────────────

def carried_credit(inv: dict) -> float:
    """Deposit carried in from an earlier invoice (change-order style, recorded on the
    invoice as deposit_received with a change_order.credit_ref)."""
    co = _snapshot(inv).get("change_order")
    if isinstance(co, dict) and co.get("credit_ref"):
        return _r(inv.get("deposit_received"))
    return 0.0


def recalc_invoice(conn, invoice_id: str) -> Optional[dict]:
    """amount_paid / balance_due / status from the ledger (payments + credits)."""
    ensure_ledger_schema(conn)
    inv = _row(conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone())
    if not inv or _is_void_invoice(inv):
        return inv
    total = _r(inv.get("total"))
    own = paid_on_invoice(conn, invoice_id)
    settle = _settlement(inv)
    if settle:
        credits = _r(sum(c["amount"] for c in final_credits(conn, inv)))
        due = _r(total - credits - own)
    else:
        credit = carried_credit(inv)
        stage = str(inv.get("invoice_stage") or "").lower()
        required = _r(inv.get("deposit_required"))
        if stage == "deposit" and credit > 0 and 0 < required < total:
            due = _r(required - credit - own)
        else:
            due = _r(total - credit - own)
    group_superseded = False
    if not settle:
        if str(inv.get("payment_status") or "").lower() == "superseded":
            group_superseded = True
        elif inv.get("invoice_number"):
            group = related_invoices(conn, invoice_id)
            group_superseded = len(group) > 1 and invoice_id in _superseded_ids(group)
    status = inv.get("status") or "draft"
    pay_status = inv.get("payment_status") or "unpaid"
    if group_superseded:
        due = 0.0
    elif due <= _CENT and (own > 0 or total > 0) and (own > 0 or (settle and credits > 0) or carried_credit(inv) > 0):
        status, pay_status = "paid", "paid"
    elif own > 0:
        status, pay_status = "partial", "partial"
    elif str(status).lower() in ("paid", "partial") and conn.execute(
            "SELECT 1 FROM payments WHERE invoice_id = ? AND lower(COALESCE(status,'')) IN "
            "('void','voided','refunded','reversed') LIMIT 1", (invoice_id,)).fetchone():
        # a payment was voided/refunded: back to an open invoice
        status = "sent" if inv.get("sent_at") else "draft"
        pay_status = "unpaid"
    paid_at = datetime.now().isoformat() if status == "paid" else None
    conn.execute(
        """UPDATE invoices SET amount_paid = ?, balance_due = ?, status = ?, payment_status = ?,
               paid_at = CASE WHEN ? IS NOT NULL THEN COALESCE(paid_at, ?) ELSE paid_at END,
               updated_at = datetime('now') WHERE id = ?""",
        (own, max(due, 0.0), status, pay_status, paid_at, paid_at, invoice_id),
    )
    return _row(conn.execute("SELECT * FROM invoices WHERE id = ?", (invoice_id,)).fetchone())


def recalc_job_finals(conn, invoice_id: str) -> None:
    for g in related_invoices(conn, invoice_id):
        if g["id"] != invoice_id and _settlement(g) and not _is_void_invoice(g):
            recalc_invoice(conn, g["id"])


def _credit_label(inv: dict, pay: dict, group: list[dict]) -> str:
    stage = str(inv.get("invoice_stage") or "").lower()
    co = _snapshot(inv).get("change_order")
    if isinstance(co, dict) and co.get("number"):
        kind = f"Change Order {co.get('number')} payment"
    elif stage == "deposit" or _r(inv.get("deposit_required")) > 0 and _r(pay["amount"]) <= _r(inv.get("deposit_required")) + _CENT:
        kind = "Deposit received"
    elif stage == "progress":
        kind = "Progress payment"
    else:
        kind = "Payment received"
    return kind


def final_credits(conn, final_inv: dict) -> list[dict]:
    """Payments received on the other invoices of the job (one line per payment)."""
    group = related_invoices(conn, final_inv["id"])
    others = [g for g in group if g["id"] != final_inv["id"] and not _is_void_invoice(g)]
    by_id = {g["id"]: g for g in others}
    credits = []
    for p in invoice_payments(conn, by_id.keys()):
        inv = by_id[p["invoice_id"]]
        credits.append({
            "label": _credit_label(inv, p, group),
            "invoice_id": inv["id"], "invoice_number": inv.get("invoice_number"),
            "payment_id": p["id"], "amount": p["amount"], "payment_date": p["payment_date"],
            "method": p["method"], "reference": p["reference"],
        })
    return credits


def job_ledger(conn, invoice_id: str) -> dict:
    group = related_invoices(conn, invoice_id)
    sup = _superseded_ids(group)
    pays = invoice_payments(conn, [g["id"] for g in group if not _is_void_invoice(g)])
    paid_by_inv: dict[str, float] = {}
    for p in pays:
        paid_by_inv[p["invoice_id"]] = _r(paid_by_inv.get(p["invoice_id"], 0) + p["amount"])
    return {
        "invoices": [{
            "id": g["id"], "invoice_number": g.get("invoice_number"), "status": g.get("status"),
            "stage": g.get("invoice_stage"), "total": _r(g.get("total")), "paid": paid_by_inv.get(g["id"], 0.0),
            "balance_due": _r(g.get("balance_due")), "superseded": g["id"] in sup, "void": _is_void_invoice(g),
            "quote_id": g.get("quote_id"), "created_at": g.get("created_at"),
        } for g in group],
        "payments": pays,
        "total_paid": _r(sum(p["amount"] for p in pays)),
    }


# ── final invoice ───────────────────────────────────────────────────────────

def _contract_invoice(group: list[dict], sup: set) -> Optional[dict]:
    """The invoice that carries the current full contract: newest live, not superseded,
    not a final, preferring change orders / full-contract invoices over pure deposits."""
    live = [g for g in group if not _is_void_invoice(g) and g["id"] not in sup and not _settlement(g)]
    if not live:
        return None
    def full(g):
        return not (str(g.get("invoice_stage") or "").lower() == "deposit"
                    and _r(g.get("deposit_required")) >= _r(g.get("total")) - _CENT)
    fulls = [g for g in live if full(g)]
    pool = fulls or live
    return pool[-1]


def build_final_settlement(conn, invoice_id: str) -> dict:
    """Pure read: the math for a final invoice of this job."""
    group = related_invoices(conn, invoice_id)
    if not group:
        raise LookupError(f"Invoice not found: {invoice_id}")
    sup = _superseded_ids(group)
    contract = _contract_invoice(group, sup)
    if not contract:
        raise ValueError("No live contract invoice in this job")
    contract_total = _r(contract.get("total"))
    pays = invoice_payments(conn, [g["id"] for g in group if not _is_void_invoice(g)])
    by_id = {g["id"]: g for g in group}
    credits = [{
        "label": _credit_label(by_id[p["invoice_id"]], p, group),
        "invoice_id": p["invoice_id"], "invoice_number": by_id[p["invoice_id"]].get("invoice_number"),
        "payment_id": p["id"], "amount": p["amount"], "payment_date": p["payment_date"],
        "method": p["method"], "reference": p["reference"],
    } for p in pays]
    credit_total = _r(sum(c["amount"] for c in credits))
    balance = _r(contract_total - credit_total)
    prior = [{
        "invoice_number": g.get("invoice_number"), "status": g.get("status"), "total": _r(g.get("total")),
        "paid": _r(sum(p["amount"] for p in pays if p["invoice_id"] == g["id"])),
        "superseded": g["id"] in sup or g["id"] == contract["id"], "void": _is_void_invoice(g),
    } for g in group]
    return {
        "contract_invoice_id": contract["id"], "contract_invoice_number": contract.get("invoice_number"),
        "quote_id": contract.get("quote_id"), "contract_total": contract_total,
        "credits": credits, "credit_total": credit_total,
        "balance_due": max(balance, 0.0), "credit_balance": max(-balance, 0.0),
        "prior_invoices": prior,
        "supersedes": [g["id"] for g in group if not _is_void_invoice(g) and not _settlement(g)],
    }


def create_final_invoice(conn, invoice_id: str, *, invoice_number: Optional[str] = None,
                         notes: Optional[str] = None, due_date: Optional[str] = None) -> dict:
    """Persist a draft final invoice for the job and close the earlier open invoices
    (their balance moves onto the final; their payments stay where they were paid)."""
    ensure_ledger_schema(conn)
    s = build_final_settlement(conn, invoice_id)
    contract = _row(conn.execute("SELECT * FROM invoices WHERE id = ?", (s["contract_invoice_id"],)).fetchone())
    snap = _snapshot(contract)
    snap = {k: v for k, v in snap.items() if k != "change_order"}
    snap["final_settlement"] = {k: s[k] for k in ("contract_invoice_id", "contract_invoice_number",
                                                     "contract_total", "supersedes")}
    if not invoice_number:
        year = datetime.now().year
        row = conn.execute("SELECT invoice_number FROM invoices WHERE invoice_number LIKE ? "
                           "ORDER BY invoice_number DESC LIMIT 1", (f"INV-{year}-%",)).fetchone()
        last = int(str(row[0]).split("-")[-1]) if row else 0
        invoice_number = f"INV-{year}-{last + 1:03d}"
    new_id = uuid.uuid4().hex[:16]
    cols = _cols(conn, "invoices")
    data = {
        "id": new_id, "invoice_number": invoice_number, "customer_id": contract.get("customer_id"),
        "quote_id": contract.get("quote_id"), "job_id": contract.get("job_id"), "status": "draft",
        "subtotal": contract.get("subtotal"), "tax_rate": contract.get("tax_rate"),
        "tax_amount": contract.get("tax_amount"), "total": s["contract_total"], "amount_paid": 0,
        "balance_due": s["balance_due"], "line_items": contract.get("line_items"),
        "notes": notes if notes is not None else "Final invoice. Payments received on this job are applied above.",
        "terms": "Final balance due on completion", "due_date": due_date or date.today().isoformat(),
        "client_name": contract.get("client_name"), "client_email": contract.get("client_email"),
        "client_phone": contract.get("client_phone"), "client_address": contract.get("client_address"),
        "billing_address": contract.get("billing_address"), "business_unit": contract.get("business_unit"),
        "discount_amount": contract.get("discount_amount"), "discount_type": contract.get("discount_type"),
        "deposit_required": 0, "deposit_received": 0, "payment_status": "unpaid",
        "invoice_date": date.today().isoformat(), "source_type": contract.get("source_type") or "invoice",
        "source_id": contract.get("source_id") or contract["id"], "invoice_stage": "final",
        "pricing_snapshot_json": json.dumps(snap, default=str), "billed_by": contract.get("billed_by"),
        "supersedes_invoice_id": contract["id"], "created_at": datetime.now().isoformat(timespec="seconds"),
    }
    data = {k: v for k, v in data.items() if k in cols}
    conn.execute(f"INSERT INTO invoices ({', '.join(data)}) VALUES ({', '.join('?' * len(data))})",
                 list(data.values()))
    for sid in s["supersedes"]:
        conn.execute(
            """UPDATE invoices SET balance_due = 0, payment_status = 'superseded',
                   updated_at = datetime('now') WHERE id = ? AND lower(COALESCE(status,'')) != 'paid'""",
            (sid,))
    final = recalc_invoice(conn, new_id)
    return {"invoice": final, "settlement": s}
