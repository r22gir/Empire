import asyncio
import importlib

from fastapi import BackgroundTasks, Response


def test_drawing_intent_requires_structured_inputs_for_bare_drawing():
    from app.services.max.drawing_intent import build_drawing_handoff

    handoff = build_drawing_handoff("drawing")

    assert handoff.is_drawing_intent is True
    assert handoff.ready is False
    assert "subject/item" in handoff.missing
    assert "dimensions or source image" in handoff.missing
    assert "Missing:" in handoff.response


def test_four_view_items_identified_does_not_fabricate_without_source():
    from app.services.max.drawing_intent import build_drawing_handoff

    handoff = build_drawing_handoff("4-view plan/isometric/elevation of items identified")

    assert handoff.is_drawing_intent is True
    assert handoff.ready is False
    assert handoff.views[:4] == ["plan", "front_elevation", "side_elevation", "isometric"]
    assert "subject/item" in handoff.missing
    assert handoff.tool_payload is None


def test_bare_drawing_with_source_image_still_requires_extracted_dimensions():
    from app.services.max.drawing_intent import build_drawing_handoff

    handoff = build_drawing_handoff("drawing", image_filename="uploaded-photo.jpg")

    assert handoff.is_drawing_intent is True
    assert handoff.ready is False
    assert handoff.source_image == "uploaded-photo.jpg"
    assert "real extracted dimensions" in handoff.missing
    assert handoff.tool_payload is None
    assert handoff.response.startswith("Image detected in the current request")


def test_missing_response_omits_source_image_when_no_active_image():
    import importlib
    from app.services.max.drawing_intent import build_drawing_handoff

    max_router = importlib.import_module("app.routers.max.router")
    handoff = build_drawing_handoff("drawing")
    response = max_router._drawing_missing_response(handoff)

    assert '"source_image"' not in response
    assert "Missing: confirmed item type and real dimensions, or attach a source image." in response


def test_bench_drawing_with_dimensions_builds_tool_payload():
    from app.services.max.drawing_intent import build_drawing_handoff

    handoff = build_drawing_handoff(
        'Create a straight bench drawing 96" wide 22" deep with 18" seat height and 18" back height'
    )

    assert handoff.ready is True
    assert handoff.item_type == "bench"
    assert handoff.tool_payload["item_type"] == "bench"
    assert handoff.tool_payload["shape"] == "straight"
    assert handoff.tool_payload["dimensions"]["width"] == '96"'
    assert handoff.tool_payload["dimensions"]["depth"] == '22"'
    assert handoff.tool_payload["dimensions"]["seat_height"] == '18"'
    assert handoff.tool_payload["dimensions"]["back_height"] == '18"'


def test_max_chat_intercepts_drawing_before_ai_router(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("drawing intent should not reach generic AI router")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(message="drawing", history=[], channel="web")
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "drawing-router"
    assert "Structured drawing handoff" in response.response
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
                "svg": "<svg><text>bench proof</text></svg>",
                "pdf_url": "/api/v1/drawings/files/proof.pdf",
                "item_type": "bench",
            },
        )

    monkeypatch.setattr(max_router, "execute_tool", fake_execute_tool)

    request = max_router.ChatRequest(
        message='Create a straight bench drawing 96" wide 22" deep with 18" seat height and 18" back height',
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "drawing-router"
    assert response.tool_results[0]["tool"] == "sketch_to_drawing"
    assert response.tool_results[0]["success"] is True
    assert calls[0]["item_type"] == "bench"
    assert calls[0]["dimensions"]["width"] == '96"'
