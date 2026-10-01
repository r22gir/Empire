"""Deterministic local-db prefetch for finance readiness / totals questions."""
from __future__ import annotations

import re
from typing import Any, Callable, Awaitable

# (label shown to model, SQL table name)
FINANCE_COUNT_TABLES: tuple[tuple[str, str], ...] = (
    ("quotes", "quotes_v2"),
    ("invoices", "invoices"),
    ("payments", "payments"),
    ("expenses", "expenses"),
    ("chart_of_accounts", "chart_of_accounts"),
    ("customers", "customers"),
    ("contacts", "contacts"),
    ("jobs", "jobs"),
    ("inventory_items", "inventory_items"),
    ("leads", "leads"),
    ("vendors", "vendors"),
)

# Read-only aggregates — column names verified against init_db / quotes_v2 schema.
FINANCE_SUM_QUERIES: tuple[tuple[str, str], ...] = (
    (
        "quotes_dollar_total",
        "SELECT COALESCE(SUM(total), 0) AS sum_total FROM quotes_v2",
    ),
    (
        "invoices_dollar_total",
        "SELECT COALESCE(SUM(total), 0) AS sum_total FROM invoices WHERE status != 'cancelled'",
    ),
    (
        "payments_dollar_total",
        "SELECT COALESCE(SUM(amount), 0) AS sum_total FROM payments",
    ),
    (
        "expenses_dollar_total",
        "SELECT COALESCE(SUM(amount), 0) AS sum_total FROM expenses",
    ),
    (
        "invoices_balance_due_total",
        "SELECT COALESCE(SUM(balance_due), 0) AS sum_total FROM invoices WHERE status NOT IN ('cancelled', 'paid')",
    ),
    (
        "ar_outstanding_balance_due",
        "SELECT COALESCE(SUM(balance_due), 0) AS ar_outstanding FROM invoices WHERE balance_due > 0",
    ),
)

_TOTAL_MARKERS = (
    "total",
    "totals",
    "sum",
    "dollar",
    "amount",
    "$",
    "outstanding",
    "revenue",
    "ar ",
    "accounts receivable",
)


def is_local_finance_readiness_request(message: str | None) -> bool:
    text = (message or "").lower()
    finance_markers = ("finance", "quickbooks", "accounts", "invoice", "payment", "expense")
    table_markers = (
        "quotes",
        "customers",
        "contacts",
        "jobs",
        "inventory",
        "leads",
        "vendors",
        "records",
        "count",
    )
    return any(marker in text for marker in finance_markers) and any(
        marker in text for marker in table_markers
    )


def finance_request_wants_dollar_totals(message: str | None) -> bool:
    text = (message or "").lower()
    if not text:
        return False
    if any(marker in text for marker in _TOTAL_MARKERS):
        return True
    return "readiness" in text and "report" in text


def finance_system_preamble(*, include_totals: bool) -> str:
    lines = [
        "Verified local finance data is below. Use these exact counts and dollar totals in labeled tables.",
        "Do not ask permission for follow-up SUM queries — the aggregates are already provided.",
        "Then provide the QuickBooks feature-gap analysis and phased migration plan with concrete steps under each phase.",
        "Do not call web_search for this local-data request.",
    ]
    if include_totals:
        lines.insert(
            1,
            "Report AR/outstanding using ar_outstanding_balance_due (sum of invoice balance_due) and cross-check against payments.",
        )
    return " ".join(lines)


async def prefetch_finance_readiness_entries(
    execute_async: Callable[..., Awaitable[Any]],
    *,
    message: str | None,
    include_counts: bool = True,
) -> list[dict[str, Any]]:
    """Run COUNT (+ optional SUM) db_query tools; return normalized tool result dicts."""
    include_totals = finance_request_wants_dollar_totals(message)
    entries: list[dict[str, Any]] = []

    async def _run_query(label: str, query: str) -> dict[str, Any]:
        result = await execute_async({"tool": "db_query", "query": query})
        entry = result if isinstance(result, dict) else getattr(result, "to_dict", lambda: {})()
        if not isinstance(entry, dict):
            entry = {"success": False, "tool": "db_query", "error": "invalid tool result"}
        if entry.get("success") and isinstance(entry.get("result"), dict):
            entry["result"]["requested_name"] = label
        if "tool" not in entry:
            entry["tool"] = "db_query"
        return entry

    if include_counts:
        for label, table in FINANCE_COUNT_TABLES:
            entries.append(
                await _run_query(label, f"SELECT COUNT(*) AS record_count FROM {table}")
            )

    if include_totals:
        for label, query in FINANCE_SUM_QUERIES:
            entries.append(await _run_query(label, query))

    return entries


def format_finance_context(entries: list[dict[str, Any]], *, dumps: Callable[..., str], limit: int = 800) -> str:
    lines = []
    for entry in entries:
        if not entry.get("success"):
            continue
        name = (entry.get("result") or {}).get("requested_name", "?")
        lines.append(f"[{name}] {dumps(entry.get('result', {}), default=str)[:limit]}")
    return "\n".join(lines)


def resolve_display_model_used(model_used: str | None, explicit_model: str | None = None) -> str:
    """Avoid surfacing literal 'unknown' to clients when routing succeeded."""
    used = (model_used or "").strip()
    if used and used.lower() not in {"unknown", "none", ""}:
        return used
    if explicit_model and explicit_model.strip().lower() not in {"auto", "unknown", "none", ""}:
        return explicit_model.strip()
    return "MAX auto"
