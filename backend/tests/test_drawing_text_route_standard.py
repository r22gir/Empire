"""Text-measurement drawing routing, sketch auto-follow, multi-PDF email, status block."""
import importlib
from datetime import date
from pathlib import Path

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
ROMAN_WINDOW_MSG = (
    "window 36 in W x 60 in H, inside mount, flat fold, 6 in folds"
)
TEST_ONLY_PREFIX = (
    "TEST ONLY: do not create quotes, invoices, contacts, or send any email. "
)
U_BANQUETTE_FRESH = (
    "Draw a U-shaped banquette: back wall 120 in, two returns 72 in each, "
    "seat depth 20, seat height 18, back 18 above seat, 2in foam, plain backs"
)
BENCH_TUFTED_MSG = (
    "straight bench 84 in long, 18 deep, 18 high, tufted back 16 in tall, "
    "front + side elevation"
)
FORBIDDEN_UL_PDF_MARKERS = (
    "EST-2026-272",
    "Dave Romero",
    "Marley",
    "Marleys",
    "107.750",
    "48.875",
    "Nelma TBD",
    "COM / Nelma",
    "shells already built",
    "Devon",
    "Willard",
    "Hillary",
)


def test_text_measurement_messages_route_as_drawing_intent():
    for msg in (U_BANQUETTE, BENCH_MSG, ROMAN_MSG, ROMAN_WINDOW_MSG, BENCH_TUFTED_MSG):
        assert is_drawing_intent(msg) is True
        handoff = build_drawing_handoff(msg)
        assert handoff.is_drawing_intent is True
        assert handoff.ready is True
        assert handoff.b1_product_type


def test_negated_finance_phrase_does_not_block_drawing_intent():
    msg = TEST_ONLY_PREFIX + U_BANQUETTE_FRESH
    assert is_drawing_intent(msg) is True
    handoff = build_drawing_handoff(msg)
    assert handoff.ready is True
    assert handoff.b1_product_type == "banquette"
    max_router = importlib.import_module("app.routers.max.router")
    routed = max_router._handoff_to_render_shop_tool_call(handoff)
    assert routed and routed["tool"] == "render_shop_drawing"


def _pdf_text(pdf_path: str) -> str:
    for mod_name in ("pypdf", "PyPDF2"):
        try:
            PdfReader = importlib.import_module(mod_name).PdfReader
        except ImportError:
            continue
        return "\n".join(
            page.extract_text() or "" for page in PdfReader(pdf_path).pages
        )
    return Path(pdf_path).read_bytes().decode("latin-1", errors="ignore")


def test_u_pack_default_empire_branding_and_single_job_line():
    from app.services.drawing.banquette_branding import (
        normalize_banquette_job_label,
        resolve_banquette_branding,
    )
    head, sub, drawn = resolve_banquette_branding({})
    assert head == "EMPIRE WORKROOM"
    assert "NELMA" not in head
    assert drawn == "MAX AI"
    job = normalize_banquette_job_label("U-Banquette Upholstery", "u_shape", "")
    assert job == "U-Banquette Upholstery"
    assert "—" not in job or job.count("U-Banquette") == 1


def test_roman_fold_spacing_and_render_date():
    from app.services.drawing.templates.roman import fold_descriptor, roman_slat_layout
    from app.services.drawing.templates.b2_renderers import _spec_render_date

    assert roman_slat_layout(60.0, 6.0) == (10, 6.0, None)
    assert "6" in fold_descriptor("flat_fold", 60.0, slat_height=6.0)
    assert "10" in fold_descriptor("flat_fold", 60.0, slat_height=6.0)
    today = date.today().strftime("%m/%d/%Y")
    assert _spec_render_date({}) == today


def test_bench_side_elevation_svg_has_depth_and_back_dims():
    from app.services.vision.bench_renderer import render_straight
    from app.services.vision.bench_svg_layout import validate_bench_svg_layout
    from app.services.drawing.quote_sheet_layout import idea_sheet_regions

    layout = idea_sheet_regions(title_rows=12)
    svg = render_straight(
        "Straight Bench",
        84,
        depth_in=18,
        seat_h_in=18,
        back_h_in=16,
        panel_style="tufted",
        include_side_elevation=True,
        sheet_kind="shop",
    )
    assert "SHOP DRAWING" in svg
    assert 'data-panel="side-elev"' in svg
    assert 'data-panel="front-elev"' in svg
    assert '18"' in svg or "18" in svg
    assert "16" in svg
    validate_bench_svg_layout(svg, layout)


def test_fresh_u_banquette_pdf_has_no_marley_fixture_strings():
    max_router = importlib.import_module("app.routers.max.router")
    handoff = build_drawing_handoff(U_BANQUETTE_FRESH)
    assert handoff.ready
    routed = max_router._handoff_to_render_shop_tool_call(handoff)
    result = execute_tool(routed)
    assert result.success, result.error
    pdf_path = (result.result or {}).get("pdf_path")
    assert pdf_path and Path(pdf_path).is_file()
    try:
        from pypdf import PdfReader
        reader = PdfReader(pdf_path)
        blob = "\n".join(
            (page.extract_text() or "") for page in reader.pages
        ).lower()
    except ImportError:
        blob = _pdf_text(pdf_path).lower()
    for marker in FORBIDDEN_UL_PDF_MARKERS:
        assert marker.lower() not in blob, f"unexpected fixture text {marker!r} in PDF"
    assert "empire workroom" in blob
    assert "nelma's workroom" not in blob
    assert "u-banquette upholstery — u-banquette upholstery" not in blob


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
