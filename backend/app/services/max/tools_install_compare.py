"""Max tool: compare_install_prices — past install $/window and $/LF vs a new quote.

Registered into tool_executor.TOOL_REGISTRY on import.
Read-only comparison. Writes a PDF to the job's documents.
Sending is OFF by default (no Telegram, email, WhatsApp).
Never uses the `present` tool path.
"""
from __future__ import annotations

from typing import Optional

from app.services.max.tool_executor import ToolResult, tool

_T = "compare_install_prices"


def _as_list(value) -> list[str]:
    if value is None or value == "":
        return []
    if isinstance(value, (list, tuple, set)):
        return [str(v).strip() for v in value if str(v).strip()]
    text = str(value).strip()
    if "," in text:
        return [p.strip() for p in text.split(",") if p.strip()]
    return [text]


@tool(_T)
def _compare_install_prices(params: dict, desk: Optional[str] = None) -> ToolResult:
    params = params or {}
    quote_numbers = _as_list(
        params.get("quote_numbers") or params.get("quotes") or params.get("quote_number")
    )
    job_ids = _as_list(params.get("job_ids") or params.get("jobs") or params.get("job_id"))
    new_quote = params.get("new_quote") or params.get("new_quote_number")
    if not quote_numbers and not job_ids:
        return ToolResult(
            tool=_T,
            success=False,
            error="Give quote_numbers (EST-xxxx or legacy 812-C / 838 / 897 / 909 / 803-A) and/or job_ids, plus new_quote.",
        )
    if not new_quote:
        return ToolResult(
            tool=_T,
            success=False,
            error="Give new_quote (EST-xxxx or quote id) to compare against the past install lines.",
        )
    try:
        from app.services.install_price_compare import compare_install_prices
        result = compare_install_prices(params=params)
    except Exception as exc:  # noqa: BLE001
        return ToolResult(tool=_T, success=False, error=f"{type(exc).__name__}: {exc}")
    return ToolResult(tool=_T, success=True, result=result)


INSTALL_COMPARE_TOOLS_DOC = """
### Install price comparison (read-only; PDF saved to the job)
- **compare_install_prices** — Use this whenever Rafael asks to compare install prices across jobs or against a new quote. Examples: "compare my install prices for Willard and Le Midi against EST-xxxx", "what did we charge per window / per linear foot to install on 838 and 812-C vs this estimate". Pulls installation lines (item_type=installation, plus descriptions like install / removal and installation / remove existing track and install / hourly install) from quotes AND imported historical docs (legacy numbers 812-C, 838, 897, 909, 803-A). Returns per-line and aggregated $/window and $/LF (avg/min/max) and flags lines that lack window count or LF. Writes a branded Empire Workroom PDF table to the job's documents. Sending is OFF: do NOT email, Telegram, or WhatsApp it, and do NOT call `present`. Only send if Rafael explicitly asks to send.
  `{"tool": "compare_install_prices", "quote_numbers": ["Willard", "Le Midi"], "new_quote": "EST-2026-0400"}`
  `{"tool": "compare_install_prices", "job_ids": ["job-willard", "job-midi"], "new_quote": "EST-2026-0400"}`
  `{"tool": "compare_install_prices", "quote_numbers": ["812-C", "838", "897"], "new_quote": "EST-2026-0400"}`
  Report only numbers from the tool result. Say the PDF path / job document. Do not claim it was sent.
"""
