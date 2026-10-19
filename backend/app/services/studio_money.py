"""Read-only Studio Money figures from existing invoice / payment / quote rows.

No writes. No Stripe or other external calls. Used by GET /finance/studio-money.
"""
from __future__ import annotations

from datetime import date
from typing import Any, Iterable

CLOSED_INVOICE = frozenset({"paid", "cancelled", "canceled", "void"})
OVERDUE_STATUSES = frozenset({"sent", "partial", "overdue", "pending"})
APPROVED_QUOTE = frozenset({"accepted", "approved", "won"})


def _amount(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _iso_day(value: Any) -> str:
    return str(value or "")[:10]


def compute_studio_money(
    invoices: Iterable[dict],
    payments: Iterable[dict],
    quotes: Iterable[dict],
    *,
    today: date,
    invoices_connected: bool = True,
    payments_connected: bool = True,
    quotes_connected: bool = True,
) -> dict:
    """Compute to-collect, deposits due, and paid MTD from mocked or live rows."""
    today_s = today.isoformat()
    month_start = today.replace(day=1).isoformat()

    to_collect = 0.0
    for inv in invoices:
        status = str(inv.get("status") or "").lower()
        if status not in OVERDUE_STATUSES:
            continue
        due = _iso_day(inv.get("due_date"))
        if due and due < today_s:
            to_collect += _amount(inv.get("balance_due") if inv.get("balance_due") is not None else inv.get("balance"))

    paid_mtd = 0.0
    for pay in payments:
        paid_on = _iso_day(pay.get("payment_date") or pay.get("created_at"))
        if paid_on and paid_on >= month_start:
            paid_mtd += _amount(pay.get("amount"))

    deposits_due = 0.0
    deposit_quote_ids: set[str] = set()
    for inv in invoices:
        stage = str(inv.get("invoice_stage") or inv.get("invoice_type") or "").lower()
        if stage != "deposit":
            continue
        quote_id = str(inv.get("quote_id") or inv.get("source_id") or "")
        if quote_id:
            deposit_quote_ids.add(quote_id)
        status = str(inv.get("status") or "").lower()
        if status in CLOSED_INVOICE:
            continue
        remaining = _amount(inv.get("balance_due") if inv.get("balance_due") is not None else inv.get("balance"))
        if remaining <= 0:
            remaining = max(
                0.0,
                _amount(inv.get("deposit_required"))
                - _amount(inv.get("deposit_received") if inv.get("deposit_received") is not None else inv.get("amount_paid")),
            )
        deposits_due += remaining

    if quotes_connected:
        for quote in quotes:
            status = str(quote.get("status") or "").lower()
            if status not in APPROVED_QUOTE:
                continue
            quote_id = str(quote.get("id") or "")
            if quote_id and quote_id in deposit_quote_ids:
                continue
            remaining = max(0.0, _amount(quote.get("deposit_required")) - _amount(quote.get("deposit_paid")))
            deposits_due += remaining

    deposits_connected = invoices_connected or quotes_connected
    return {
        "to_collect": round(to_collect, 2) if invoices_connected else None,
        "deposits_due": round(deposits_due, 2) if deposits_connected else None,
        "paid_mtd": round(paid_mtd, 2) if payments_connected else None,
        "connected": {
            "to_collect": invoices_connected,
            "deposits_due": deposits_connected,
            "paid_mtd": payments_connected,
        },
        "as_of": today_s,
        "sources": {
            "to_collect": "invoices.balance_due where status is open and due_date is past",
            "deposits_due": "open deposit invoices plus approved quotes with unpaid deposit and no deposit invoice",
            "paid_mtd": "payments.amount with payment_date in the current month",
        },
    }
