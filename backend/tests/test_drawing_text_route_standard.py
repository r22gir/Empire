"""Text-measurement drawing routing, sketch auto-follow, multi-PDF email, status block."""
import importlib

import pytest

from app.services.max.drawing_intent import build_drawing_handoff, is_drawing_intent
from app.services.max.founder_action_continuation import (
    finalize_founder_action_reply,
    format_founder_status_block,
)
from app.services.max.guardrails import founder_action_tools_remaining
from app.services.max.tool_executor import (
    ToolResult,
    _send_quote_email,
    execute_tool,
    parse_tool_blocks_with_errors,
)


U_BANQUETTE = (
    "Draw a U-shaped banquette: back wall 120 in, returns 72 in each, "
    "seat depth 20, seat height 18, back 18 above seat, 2in foam, plain large "
    "back panels; plan + front elevation with dimensions"
)
BENCH_MSG = "Straight bench 84x18x18 with 16in tufted back, front+side elevations"
ROMAN_MSG = "Roman shade 36W x 60H inside mount flat fold 6in folds"


def test_text_measurement_messages_route_as_drawing_intent():
    for msg in (U_BANQUETTE, BENCH_MSG, ROMAN_MSG):
        assert is_drawing_intent(msg) is True
        handoff = build_drawing_handoff(msg)
        assert handoff.is_drawing_intent is True
        assert handoff.ready is True
        assert handoff.b1_product_type


def test_u_banquette_render_shop_drawing_produces_pdf():
    max_router = importlib.import_module("app.routers.max.router")
    handoff = build_drawing_handoff(U_BANQUETTE)
    assert handoff.ready
    dims, shape, construction = max_router._dims_for_render_shop(handoff)
    params = {
        "tool": "render_shop_drawing",
        "product_type": handoff.b1_product_type,
        "dims": dims,
        "shape": shape,
    }
    if construction:
        params["construction"] = construction
    result = execute_tool(params)
    assert result.success, result.error
    pdf_path = (result.result or {}).get("pdf_path")
    assert pdf_path
    assert str(pdf_path).endswith(".pdf")


def test_sketch_to_drawing_text_only_refuses_with_reroute_hint():
    result = execute_tool({
        "tool": "sketch_to_drawing",
        "shape": "straight",
        "width": 84,
    })
    assert not result.success
    assert "render_shop_drawing" in (result.error or "")


def test_coerce_sketch_to_render_shop_drawing():
    max_router = importlib.import_module("app.routers.max.router")
    tc = max_router._coerce_drawing_tool_call(
        {"tool": "sketch_to_drawing", "shape": "straight"},
        BENCH_MSG,
        None,
    )
    assert tc["tool"] == "render_shop_drawing"
    assert tc.get("product_type") == "bench"


@pytest.mark.asyncio
async def test_auto_follow_render_shop_after_sketch_refusal(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    calls = []

    async def fake_exec(tool_call, **kwargs):
        calls.append(tool_call)
        if tool_call.get("tool") == "sketch_to_drawing":
            return ToolResult(
                tool="sketch_to_drawing",
                success=False,
                error="Use render_shop_drawing with explicit dims",
                result={"reroute_to": "render_shop_drawing"},
            )
        return ToolResult(
            tool="render_shop_drawing",
            success=True,
            result={"pdf_path": "/tmp/follow.pdf"},
        )

    monkeypatch.setattr(max_router, "_execute_tool_nonblocking", fake_exec)
    sketch = ToolResult(
        tool="sketch_to_drawing",
        success=False,
        error="sketch_to_drawing: text-only with no dimensions. Use render_shop_drawing",
    )
    follow, _ = await max_router._maybe_auto_follow_render_shop(
        {"tool": "sketch_to_drawing"},
        sketch,
        BENCH_MSG,
        None,
        None,
        None,
        True,
    )
    assert follow.success
    assert calls and calls[-1]["tool"] == "render_shop_drawing"


def test_email_body_lines_not_parsed_as_tool_blocks():
    prose = """Hi Sarah,

Please find the estimates attached.

Best,
MAX
"""
    actions, errors = parse_tool_blocks_with_errors(prose)
    assert actions == []
    assert errors == []


def test_founder_status_existing_est_numbers_skip_create_quote():
    msg = (
        "Email PDFs for EST-2026-294 and EST-2026-295 to me in one email"
    )
    remaining = founder_action_tools_remaining(msg, [])
    assert "create_engine_quote" not in remaining
    assert "send_quote_email" in remaining


def test_founder_status_ignores_web_search_in_done_block():
    msg = "Create estimates and email PDFs"
    tool_results = [
        {"tool": "web_search", "success": True, "result": {"hits": 1}},
        {"tool": "create_engine_quote", "success": True, "result": {"quote_id": "q-1", "quote_number": "EST-2026-1"}},
    ]
    block = format_founder_status_block(msg, tool_results, "Working on it")
    assert "web_search" not in block
    assert "create_engine_quote" in block or "Created" in block


def test_send_quote_email_accepts_multiple_quote_ids(monkeypatch, tmp_path):
    pdfs = []
    for qid in ("q-a", "q-b"):
        p = tmp_path / f"{qid}.pdf"
        p.write_bytes(b"%PDF-1.4 test")
        pdfs.append(str(p))

    quotes = {
        "q-a": {"id": "q-a", "quote_number": "EST-2026-294", "customer_name": "A", "total": 100},
        "q-b": {"id": "q-b", "quote_number": "EST-2026-295", "customer_name": "A", "total": 200},
    }
    pdf_iter = iter(pdfs)

    def resolve(qid):
        return quotes.get(qid)

    sent_attachments = []

    class FakeSvc:
        is_configured = True

        def send(self, **kwargs):
            sent_attachments.extend(kwargs.get("attachments") or [])
            return True

    monkeypatch.setattr("app.services.quote_service.resolve_quote", resolve)
    monkeypatch.setattr(
        "app.services.max.tool_executor._run_async",
        lambda _coro: next(pdf_iter),
    )
    monkeypatch.setattr(
        "app.services.max.tool_executor.dp.quote_pdf_dir",
        lambda: tmp_path,
    )
    monkeypatch.setattr(
        "app.services.max.email_recipient_whitelist.authorize_email_recipient",
        lambda _to: {"recipient_authorized": True},
    )
    monkeypatch.setattr(
        "app.services.max.email_service.EmailService",
        FakeSvc,
    )

    result = _send_quote_email({
        "quote_ids": ["q-a", "q-b"],
        "to": "founder@example.com",
    })
    assert result.success, result.error
    assert result.result.get("attachments_sent") == 2
    assert len(sent_attachments) == 2
