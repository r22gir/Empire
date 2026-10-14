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
    """Full intake → CRM → dims → Pricing Studio → DRAFT. Never sends."""
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
### QuoteIQ job chain (intake → CRM → dims → Pricing Studio → DRAFT)
When a job request arrives (WhatsApp or chat) with a client/item/dims, call **quoteiq_chain** in that same turn. It runs the five tools below as multi-step calls and forwards every field — never ask Rafael to re-type a name, email, phone, or measurement already in the message. Result is a DRAFT quote only. Never email it. Never WhatsApp it to a client.
- **quoteiq_chain** — full chain. `{"tool": "quoteiq_chain", "message": "Quote for Maggie. Straight bench 48 inches long, 12 inch channels."}`
- **quoteiq_intake** — parse the inbound job text (client, item, dims, channel).
- **quoteiq_crm_upsert** — lookup/upsert the client in ForgeCRM from intake fields.
- **quoteiq_parse_dimensions** — shop fractions only (26 3/4"), never decimals. Channels list wood_cut / foam_cut (same, true size) and fabric_cut separately.
- **quoteiq_price** — price from Pricing Studio rate cards / engine.
- **quoteiq_draft_quote** — persist quotes_v2 status=draft. sent=false always.
"""
