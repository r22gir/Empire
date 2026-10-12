"""Read-only money on a job card: deposit, paid, balance, margin from quotes/invoices."""

from __future__ import annotations

from typing import Optional

from app.services.organizer.edition import can_read_workroom_jobs


def _num(value) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _fraction(done: float, total: float) -> str:
    if total <= 0:
        return "0/0"
    # Keep a small integer fraction for collected vs total.
    return f"{int(round(done))}/{int(round(total))}" if total <= 20 else f"{int(round(100 * done / total))}/100"


def job_money(conn, job_id: Optional[str]) -> Optional[dict]:
    if not job_id or not can_read_workroom_jobs():
        return None
    quote = None
    invoice = None
    try:
        row = conn.execute(
            """SELECT * FROM quotes_v2 WHERE job_id = ? ORDER BY updated_at DESC LIMIT 1""",
            (job_id,),
        ).fetchone()
        quote = dict(row) if row else None
    except Exception:
        quote = None
    try:
        row = conn.execute(
            """SELECT * FROM invoices WHERE quote_id = ? OR id IN (
                   SELECT invoice_id FROM jobs WHERE id = ?
               ) ORDER BY updated_at DESC LIMIT 1""",
            ((quote or {}).get("id"), job_id),
        ).fetchone()
        invoice = dict(row) if row else None
    except Exception:
        try:
            row = conn.execute(
                "SELECT * FROM invoices WHERE quote_id = ? ORDER BY updated_at DESC LIMIT 1",
                ((quote or {}).get("id"),),
            ).fetchone()
            invoice = dict(row) if row else None
        except Exception:
            invoice = None

    if not quote and not invoice:
        return None

    deposit = 0.0
    if quote is not None and quote.get("deposit_required") not in (None, ""):
        deposit = _num(quote.get("deposit_required"))
    elif quote is not None and _num(quote.get("deposit_percent")) and _num(quote.get("total")):
        deposit = round(_num(quote.get("total")) * _num(quote.get("deposit_percent")) / 100.0, 2)
    paid = _num((invoice or {}).get("amount_paid")) + _num((quote or {}).get("deposit_paid"))
    total = _num((invoice or {}).get("total")) or _num((quote or {}).get("total"))
    balance = _num((invoice or {}).get("balance_due"))
    if not balance and total:
        balance = max(0.0, total - paid)
    cost = _num((quote or {}).get("materials_cost")) + _num((quote or {}).get("cost"))
    try:
        if job_id:
            job = conn.execute("SELECT materials_cost, labor_cost FROM jobs WHERE id = ?", (job_id,)).fetchone()
            if job:
                data = dict(job)
                cost = cost or (_num(data.get("materials_cost")) + _num(data.get("labor_cost")))
    except Exception:
        pass
    margin = round(total - cost, 2) if total else None
    collected = paid if total else 0
    return {
        "job_id": job_id,
        "deposit": deposit,
        "paid": paid,
        "balance": balance,
        "margin": margin,
        "total": total,
        "collected_fraction": _fraction(collected, total) if total else "0/0",
        "quote_id": (quote or {}).get("id"),
        "invoice_id": (invoice or {}).get("id"),
        "quote_href": f"/?screen=quote&id={quote['id']}" if quote else None,
        "invoice_href": f"/?screen=invoice&id={invoice['id']}" if invoice else None,
        "read_only": True,
    }
