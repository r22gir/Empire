"""Max tools for QuoteIQ-style job-request chaining.

Registered into tool_executor.TOOL_REGISTRY on import. Each step is a
real tool; quoteiq_chain runs them in order and forwards outputs so the
founder is never asked to re-enter data already in the inbound message.
"""
from __future__ import annotations

from app.services.max import quoteiq_chain as qiq
from app.services.max.tool_executor import ToolResult, tool


def _ok(name: str, payload: dict) -> ToolResult:
    if payload.get("ok") is False:
        return ToolResult(tool=name, success=False, error=payload.get("error") or f"{name} failed")
    return ToolResult(tool=name, success=True, result=payload)


@tool("quoteiq_intake")
def _quoteiq_intake(params: dict, desk=None) -> ToolResult:
    return _ok("quoteiq_intake", qiq.intake_job_request(params))


@tool("quoteiq_crm_upsert")
def _quoteiq_crm_upsert(params: dict, desk=None) -> ToolResult:
    return _ok("quoteiq_crm_upsert", qiq.lookup_or_upsert_client(params))


@tool("quoteiq_parse_dimensions")
def _quoteiq_parse_dimensions(params: dict, desk=None) -> ToolResult:
    return _ok("quoteiq_parse_dimensions", qiq.parse_job_dimensions(params))


@tool("quoteiq_price")
def _quoteiq_price(params: dict, desk=None) -> ToolResult:
    return _ok("quoteiq_price", qiq.price_with_studio(params))


@tool("quoteiq_draft_quote")
def _quoteiq_draft_quote(params: dict, desk=None) -> ToolResult:
    return _ok("quoteiq_draft_quote", qiq.draft_quote_only(params))


@tool("quoteiq_chain")
def _quoteiq_chain(params: dict, desk=None) -> ToolResult:
    """Full intake → dims → Pricing Studio → CRM → DRAFT. Never sends."""
    result = qiq.run_quoteiq_chain(params)
    if not result.get("ok"):
        return ToolResult(
            tool="quoteiq_chain",
            success=False,
            error=result.get("error") or "chain failed",
            result=result,
        )
    return ToolResult(tool="quoteiq_chain", success=True, result=result)


QUOTEIQ_TOOLS_DOC = """
### QuoteIQ job chain (intake → dims → Pricing Studio → CRM → DRAFT)
Founder-only. Trigger needs a quote/estimate/cotización/price/how much phrase AND an item AND at least one dimension. Bare W x H and casual chat do not run. Call **quoteiq_chain** in that same turn. CRM + draft run only after a real Pricing Studio catalog price. Result is a DRAFT (Empire Workroom brand) only. Never email it. Never WhatsApp it to a client.
- **quoteiq_chain** — full chain. `{"tool": "quoteiq_chain", "message": "Quote 3 roman shades 34 1/2 x 60 for kitchen"}`
- **quoteiq_intake** — parse the inbound job text (client, item, dims, channel).
- **quoteiq_parse_dimensions** — shop fractions only (26 3/4"), never decimals. Wood/board = true size, foam = wood, fabric labeled separately. Leftover channel width is reported.
- **quoteiq_price** — real Pricing Studio catalog price only. No labor_rate placeholder.
- **quoteiq_crm_upsert** — email or last-10 phone match, fill empty fields only, never name-only, no customer without a real name.
- **quoteiq_draft_quote** — persist quotes_v2 status=draft, billed_by=empire_workroom. sent=false always. 24h dedupe.
"""
