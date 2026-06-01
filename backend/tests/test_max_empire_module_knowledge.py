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


# ---------------------------------------------------------------------------
# Runtime health routing integration tests
# Ensure health questions route to runtime truth, NOT module knowledge.
# ---------------------------------------------------------------------------


def _patch_runtime_truth(monkeypatch, max_router):
    """Common monkeypatches for health-question integration tests:
    - Prevent AI router chat (should not be reached)
    - Mock execute_tool to return a fake runtime truth result
    - Mock format_runtime_truth_check to return a sentinel
    """

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("Health question should not hit AI chat path")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)
    monkeypatch.setattr(
        max_router,
        "execute_tool",
        lambda *args, **kwargs: ToolResult(
            tool="empire_runtime_truth_check",
            success=True,
            result={
                "mode": "inspect_only",
                "current_commit": {"hash": "abc1234", "message": "live"},
                "openclaw_gate": {"state": "unavailable", "allowed": False, "reason": "connection refused"},
                "backend_port_8000": {"port_open": True, "service_active": True},
                "frontend_port_3005": {"port_open": True, "service_active": True},
                "backend_port_8010": {"port_open": False, "service_active": False},
                "frontend_port_3010": {"port_open": False, "service_active": False},
                "local_freshness": {"api_matches_current_commit": True},
                "public_freshness": {"api_matches_current_commit": True},
                "restart_required": False,
                "stale_or_broken": [],
                "startup_health": {},
                "registry": {},
            },
        ),
    )
    monkeypatch.setattr(
        max_router,
        "format_runtime_truth_check",
        lambda result, message: "RUNTIME_TRUTH_SENTINEL: check completed",
    )


def test_openclaw_online_routes_to_runtime_truth_not_module_knowledge(monkeypatch):
    """'Is OpenClaw online?' must route to runtime truth, not module knowledge."""
    max_router = importlib.import_module("app.routers.max.router")
    _patch_runtime_truth(monkeypatch, max_router)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message="Is OpenClaw online right now?", history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )

    assert response.model_used == "empire-runtime-truth-check", (
        f"Expected empire-runtime-truth-check, got {response.model_used}"
    )
    assert "RUNTIME_TRUTH_SENTINEL" in response.response
    assert "ArchiveForge is the Empire module" not in response.response
    assert "deepseek" not in response.model_used


def test_hermes_running_routes_to_runtime_truth(monkeypatch):
    """'Is Hermes running?' must route to runtime truth."""
    max_router = importlib.import_module("app.routers.max.router")
    _patch_runtime_truth(monkeypatch, max_router)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message="Is Hermes running?", history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )

    assert response.model_used == "empire-runtime-truth-check"
    assert "RUNTIME_TRUTH_SENTINEL" in response.response
    assert "module" not in response.model_used


def test_minimax_deepseek_working_routes_to_runtime_truth(monkeypatch):
    """'Are MiniMax and DeepSeek working?' must route to runtime truth."""
    max_router = importlib.import_module("app.routers.max.router")
    _patch_runtime_truth(monkeypatch, max_router)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(
                message="Are MiniMax and DeepSeek working?", history=[], channel="web"
            ),
            BackgroundTasks(),
            Response(),
        )
    )

    assert response.model_used == "empire-runtime-truth-check"
    assert "RUNTIME_TRUTH_SENTINEL" in response.response


def test_backend_healthy_routes_to_runtime_truth(monkeypatch):
    """'Is the backend healthy?' must route to runtime truth."""
    max_router = importlib.import_module("app.routers.max.router")
    _patch_runtime_truth(monkeypatch, max_router)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message="Is the backend healthy?", history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )

    assert response.model_used == "empire-runtime-truth-check"
    assert "RUNTIME_TRUTH_SENTINEL" in response.response


def test_openclaw_gate_check_still_routes_to_gate(monkeypatch):
    """'check openclaw' must still route to OpenClaw gate (regression)."""
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("Should not hit AI chat path")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)
    monkeypatch.setattr(
        "app.services.max.openclaw_gate.check_openclaw_gate",
        lambda force=True: type("GateResult", (), {
            "to_dict": lambda self: {
                "state": "unavailable",
                "allowed": False,
                "reason": "connection refused",
                "checked_at": "2026-06-01T00:00:00",
                "founder_message": "OpenClaw unavailable - will delegate when service restores.",
            }
        })(),
    )

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message="check openclaw", history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )

    assert response.model_used == "openclaw-gate-check", (
        f"Expected openclaw-gate-check, got {response.model_used}"
    )
    assert "OpenClaw gate check completed" in response.response
    assert "unavailable" in response.response
    assert "connection refused" in response.response


def test_openclaw_healthy_does_not_route_module_knowledge(monkeypatch):
    """'Is OpenClaw healthy?' must NOT route to module knowledge.
    Routes to runtime truth (which includes OpenClaw gate status)."""
    max_router = importlib.import_module("app.routers.max.router")
    _patch_runtime_truth(monkeypatch, max_router)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message="Is OpenClaw healthy?", history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )

    assert response.model_used != "empire-module-knowledge", (
        "Is OpenClaw healthy? must NOT route to module knowledge"
    )
    assert "ArchiveForge is the Empire module" not in response.response
    # No fabricated metrics
    assert "pid" not in response.response.lower()
    assert "uptime" not in response.response.lower()
    assert "memory" not in response.response.lower()


def test_openclaw_online_does_not_trigger_cloud_provider_call(monkeypatch):
    """Health questions must be handled deterministically by the router,
    NOT trigger cloud provider calls (deepseek-v4-flash)."""
    max_router = importlib.import_module("app.routers.max.router")
    _patch_runtime_truth(monkeypatch, max_router)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message="Is OpenClaw online?", history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )

    # Must be handled by pre-chat routing, not by AI model
    assert response.model_used != "deepseek-v4-flash"
    assert response.model_used == "empire-runtime-truth-check"
