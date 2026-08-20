import asyncio
import importlib

from fastapi import BackgroundTasks, Response


def test_drawing_intent_requires_structured_inputs_for_strong_pattern():
    """H57 FIX (2026-08-19): bare 'drawing' does NOT route — too
    broad. Use a strong draw pattern ('draw me', 'draw a') OR an
    item+dims pattern."""
    from app.services.max.drawing_intent import build_drawing_handoff

    # Bare 'drawing' alone: no intent context → does NOT route.
    handoff = build_drawing_handoff("drawing")
    assert handoff.is_drawing_intent is False, (
        "bare 'drawing' must NOT route (H57) — 'drawing' alone is "
        "a mention, not a request"
    )

    # Strong pattern: "draw me a …" routes → missing-fields response.
    handoff = build_drawing_handoff("draw me a bench")
    assert handoff.is_drawing_intent is True
    assert handoff.ready is False
    # HOTFIX 4.0b: missing list is now template-truth keys
    # (bench template requires width/height/depth).
    assert "width" in handoff.missing
    assert "Missing:" in handoff.response


def test_four_view_items_identified_does_not_fabricate_without_source():
    from app.services.max.drawing_intent import build_drawing_handoff

    handoff = build_drawing_handoff("4-view plan/isometric/elevation of items identified")

    assert handoff.is_drawing_intent is True
    assert handoff.ready is False
    assert handoff.views[:4] == ["plan", "front_elevation", "side_elevation", "isometric"]
    assert "subject/item" in handoff.missing
    assert handoff.tool_payload is None


def test_bare_drawing_with_source_image_no_longer_routes_h57():
    """H57 FIX: bare 'drawing' no longer routes, even with a source
    image. The dispatch principle: a message that merely MENTIONS
    a drawing is not a request for one. Use a strong pattern
    ('draw me', 'draw a') OR item+dims to route."""
    from app.services.max.drawing_intent import build_drawing_handoff

    handoff = build_drawing_handoff("drawing", image_filename="uploaded-photo.jpg")
    assert handoff.is_drawing_intent is False, (
        "bare 'drawing' must NOT route (H57) — even with image"
    )

    # Strong pattern with image: routes correctly. Missing list is
    # template-truth (HOTFIX 4.0b) — bench needs width/height/depth.
    handoff = build_drawing_handoff("draw me a bench from this",
                                    image_filename="uploaded-photo.jpg")
    assert handoff.is_drawing_intent is True
    assert handoff.source_image == "uploaded-photo.jpg"
    assert "width" in handoff.missing
    assert "depth" in handoff.missing


def test_missing_response_omits_source_image_when_no_active_image():
    import importlib
    from app.services.max.drawing_intent import build_drawing_handoff

    max_router = importlib.import_module("app.routers.max.router")
    # H57 FIX: bare 'drawing' no longer routes, so the handoff is
    # not a drawing intent — build_drawing_handoff returns the
    # "no drawing intent" path. Use a strong pattern instead.
    handoff = build_drawing_handoff("draw me a bench")
    response = max_router._drawing_missing_response(handoff)

    assert '"source_image"' not in response
    assert "Missing: confirmed item type and real dimensions, or attach a source image." in response


def test_bench_drawing_with_dimensions_builds_tool_payload():
    """Pre-H57: routed via bare 'drawing' keyword. Post-H57: routes
    via strong 'Create a ' pattern. Template-truth missing check
    now applies — bench template requires 'height' (overall)."""
    from app.services.max.drawing_intent import build_drawing_handoff

    handoff = build_drawing_handoff(
        'Create a straight bench drawing 96" wide 22" deep 36" high '
        'with 18" seat height and 18" back height'
    )

    assert handoff.is_drawing_intent is True
    assert handoff.item_type == "bench"
    assert handoff.ready is True
    assert handoff.tool_payload["item_type"] == "bench"
    assert handoff.tool_payload["shape"] == "straight"
    assert handoff.tool_payload["dimensions"]["width"] == '96"'
    assert handoff.tool_payload["dimensions"]["depth"] == '22"'
    assert handoff.tool_payload["dimensions"]["height"] == '36"'
    assert handoff.tool_payload["dimensions"]["seat_height"] == '18"'
    assert handoff.tool_payload["dimensions"]["back_height"] == '18"'


def test_max_chat_intercepts_drawing_before_ai_router(monkeypatch):
    """H57 FIX: bare 'drawing' no longer routes. Use a strong
    pattern ('draw me a X') to trigger the interceptor. Pre-fix
    'drawing' alone worked — post-fix it must reach MAX, not the
    router. This test asserts the router intercepts a STRONG
    pattern before MAX."""
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("drawing intent should not reach generic AI router")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message="draw me a bench 96 wide 22 deep", history=[], channel="web"
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "drawing-router"
    assert "Missing:" in response.response or "Structured" in response.response
    assert response.tool_results is None


def test_max_chat_routes_dimensioned_bench_to_drawing_tool(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    from app.services.max.tool_executor import ToolResult

    calls = []

    def fake_execute_tool(tool_call, **kwargs):
        calls.append(tool_call)
        return ToolResult(
            tool="sketch_to_drawing",
            success=True,
                result={
                    "svg": "<svg><text>PLAN</text><text>ISOMETRIC</text><text>FRONT ELEVATION</text><text>96</text><text>22</text><text>18</text></svg>",
                    "pdf_url": "/api/v1/drawings/files/proof.pdf",
                    "item_type": "bench",
                },
        )

    monkeypatch.setattr(max_router, "execute_tool", fake_execute_tool)

    request = max_router.ChatRequest(
        message='Create a straight bench drawing 96" wide 22" deep 36" high '
                'with 18" seat height and 18" back height',
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "drawing-router"
    assert response.tool_results[0]["tool"] == "sketch_to_drawing"
    assert response.tool_results[0]["success"] is True
    assert calls[0]["item_type"] == "bench"
    assert calls[0]["dimensions"]["width"] == '96"'


def test_do_not_use_drawing_router_blocks_drawing_intercept(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    from app.services.max.ai_router import AIResponse

    async def fake_ai_router(*args, **kwargs):
        return AIResponse(content="IMAGE_NOT_AVAILABLE", model_used="test-vision")

    def fail_execute_tool(*args, **kwargs):
        raise AssertionError("drawing-router must not execute")

    monkeypatch.setattr(max_router.ai_router, "chat", fake_ai_router)
    monkeypatch.setattr(max_router, "execute_tool", fail_execute_tool)

    request = max_router.ChatRequest(
        message="Analyze this image. Do not use drawing-router. Return five sections.",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "test-vision"
    assert response.model_used != "drawing-router"


def test_unavailable_image_returns_exact_contract(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("unavailable image must not reach AI router")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message="Extract text from this image. Do not use drawing-router.",
        image_filename="missing-proof.jpg",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.response == "IMAGE_NOT_AVAILABLE"
    assert response.model_used == "image-availability-check"
    assert response.tool_results == []


def test_drawing_quality_gate_blocks_placeholder_svg():
    import importlib
    from app.services.max.drawing_intent import build_drawing_handoff
    from app.services.max.tool_executor import ToolResult

    max_router = importlib.import_module("app.routers.max.router")
    handoff = build_drawing_handoff(
        'Create a straight bench drawing 96" wide 22" deep with 18" seat height and 18" back height'
    )
    result = ToolResult(
        tool="sketch_to_drawing",
        success=True,
        result={
            "item_type": "generic",
            "svg": "<svg><text>MEASUREMENT DIAGRAM</text></svg>",
            "pdf_url": "/api/v1/drawings/files/fake.pdf",
        },
    )

    gated = max_router._quality_gate_drawing_result(handoff, result)

    assert gated.success is False
    assert "placeholder" in gated.error
    assert gated.result["quality_gate"]["passed"] is False


def test_drawing_quality_gate_passes_grounded_bench_svg():
    import importlib
    from app.services.max.drawing_intent import build_drawing_handoff
    from app.services.max.tool_executor import ToolResult

    max_router = importlib.import_module("app.routers.max.router")
    handoff = build_drawing_handoff(
        'Create a straight bench drawing 96" wide 22" deep with 18" seat height and 18" back height'
    )
    result = ToolResult(
        tool="sketch_to_drawing",
        success=True,
        result={
            "item_type": "bench",
            "svg": "<svg><text>PLAN</text><text>ISOMETRIC</text><text>FRONT ELEVATION</text><text>96</text><text>22</text><text>18</text></svg>",
            "pdf_url": "/api/v1/drawings/files/bench.pdf",
        },
    )

    gated = max_router._quality_gate_drawing_result(handoff, result)

    assert gated.success is True
    assert gated.result["quality_gate"]["passed"] is True
    assert "no_placeholder_measurement_diagram" in gated.result["quality_gate"]["checks"]
