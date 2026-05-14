import asyncio
import importlib

from fastapi import BackgroundTasks, Response

from app.services.max.tool_executor import ToolResult


def _assert_no_internal_leakage(text: str) -> None:
    lowered = text.lower()
    assert "```tool" not in lowered
    assert "i should check" not in lowered
    assert "runtime check required" not in lowered
    assert "delegation check required" not in lowered


def test_archiveforge_question_routes_to_module_knowledge(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("ArchiveForge module question should not hit generic AI chat path")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message="max whats going on with Archive Forge?",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "empire-module-knowledge"
    assert "ArchiveForge is the Empire module for archive and magazine workflows" in response.response
    assert "stable/live core workflow is complete" in response.response
    assert "internal/staged only" in response.response
    _assert_no_internal_leakage(response.response)


def test_archiveforge_done_response_includes_publish_gating(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("ArchiveForge module question should not hit generic AI chat path")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message="is ArchiveForge done?",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "empire-module-knowledge"
    assert "stable/live core workflow is complete" in response.response
    assert "approval_confirmed=true is required" in response.response
    assert "marketforge_category_id" in response.response
    assert "marketforge_ships_from_zip" in response.response
    _assert_no_internal_leakage(response.response)


def test_service_health_question_routes_to_runtime_truth(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("Service health question should not hit generic AI chat path")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)
    monkeypatch.setattr(
        max_router,
        "execute_tool",
        lambda *args, **kwargs: ToolResult(tool="empire_runtime_truth_check", success=True, result={"ok": True}),
    )
    monkeypatch.setattr(
        max_router,
        "format_runtime_truth_check",
        lambda result, message: "SERVICE_HEALTH_SENTINEL: stable=online v10=online",
    )

    request = max_router.ChatRequest(
        message="what services are online?",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "empire-runtime-truth-check"
    assert "SERVICE_HEALTH_SENTINEL" in response.response
    assert "ArchiveForge is the Empire module" not in response.response
    _assert_no_internal_leakage(response.response)


def test_current_events_question_routes_to_live_lookup(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("Current-events question should not hit generic AI chat path")

    def fake_execute_tool(tool_call, *args, **kwargs):
        assert tool_call["tool"] == "web_search"
        return ToolResult(
            tool="web_search",
            success=True,
            result={
                "results": [
                    {
                        "title": "Iran updates",
                        "snippet": "Latest developments from multiple reports.",
                        "url": "https://example.com/iran-updates",
                    }
                ]
            },
        )

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)
    monkeypatch.setattr(max_router, "execute_tool", fake_execute_tool)

    request = max_router.ChatRequest(
        message="what happened in Iran today?",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "live-lookup-router"
    assert "Live Lookup summary for: what happened in Iran today?" in response.response
    assert "https://example.com/iran-updates" in response.response
    assert "SERVICE_HEALTH_SENTINEL" not in response.response
    _assert_no_internal_leakage(response.response)
