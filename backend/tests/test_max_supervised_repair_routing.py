import asyncio
import importlib

from fastapi import BackgroundTasks, Response

from app.services.max.ai_router import AIResponse


def _preflight_payload():
    return {
        "lane": "v10-test",
        "branch": "feature/v10.0-test-lane",
        "commit": "cb0eb5f",
        "backend_port": 8010,
        "frontend_port": 3010,
        "git_freshness_status": "ok",
        "hermes_artifact_layer_enabled": True,
        "safe_to_create_bounded_openclaw_task": True,
        "note": "no task created yet",
        "endpoint_checks": {
            "max_status": {"ok": True, "status_code": 200},
            "git_status": {"ok": True, "status_code": 200},
            "hermes_artifacts_status": {"ok": True, "status_code": 200},
        },
    }


def test_supervised_preflight_overrides_module_knowledge(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    monkeypatch.setattr(
        max_router,
        "_build_supervised_v10_repair_preflight_result",
        _preflight_payload,
    )
    monkeypatch.setattr(
        max_router,
        "resolve_empire_module_question",
        lambda message: {"module": "OpenClaw", "response": "OpenClaw is an Empire module/product."},
    )

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("Supervised preflight should not reach generic AI routing")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message=(
            "MAX, this is an execution/supervision command, not a module-knowledge question. "
            "Do not use empire-module-knowledge. Run v10 supervised repair PREFLIGHT ONLY."
        ),
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "supervised-v10-repair-preflight"
    assert "lane: v10-test" in response.response
    assert "branch: feature/v10.0-test-lane" in response.response
    assert "commit: cb0eb5f" in response.response
    assert "backend_port: 8010" in response.response
    assert "frontend_port: 3010" in response.response
    assert "git_freshness_status: ok" in response.response
    assert "hermes_artifact_layer_enabled: True" in response.response
    assert "safe_to_create_bounded_openclaw_task: True" in response.response
    assert "note: no task created yet" in response.response


def test_openclaw_plus_preflight_only_routes_to_supervised_preflight(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    monkeypatch.setattr(
        max_router,
        "_build_supervised_v10_repair_preflight_result",
        _preflight_payload,
    )

    request = max_router.ChatRequest(
        message=(
            "OpenClaw supervised repair mode preflight only. "
            "Check /api/v1/max/status and /api/v1/git before any task."
        ),
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "supervised-v10-repair-preflight"
    assert response.tool_results[0]["tool"] == "supervised_v10_repair_preflight"


def test_openclaw_definition_question_still_routes_to_module_knowledge(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("Module knowledge should handle 'What is OpenClaw?' directly")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message="What is OpenClaw?",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "empire-module-knowledge"


def test_runtime_truth_prompt_still_routes_to_runtime_truth_check(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    def fake_execute_tool(tool_call, founder=False):
        assert tool_call["tool"] == "empire_runtime_truth_check"
        return max_router.ToolResult(
            tool="empire_runtime_truth_check",
            success=True,
            result={"git_freshness": {"freshness_status": "ok"}},
        )

    monkeypatch.setattr(max_router, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(max_router, "format_runtime_truth_check", lambda result, message: "runtime preflight ok")

    request = max_router.ChatRequest(
        message="what services are online?",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "empire-runtime-truth-check"
    assert response.response == "runtime preflight ok"


def test_artifact_memory_prompt_still_routes_to_hermes_artifact_memory(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    def fake_execute_tool(tool_call, founder=False):
        tool = tool_call.get("tool")
        if tool == "hermes_artifact_search":
            return max_router.ToolResult(
                tool=tool,
                success=True,
                result={
                    "results": [
                        {
                            "id": "ha_demo_1",
                            "title": "ArchiveForge Decision",
                            "module": "archiveforge",
                            "approval_status": "approved",
                            "updated_at": "2026-05-16T01:00:00+00:00",
                            "provenance": {"source_agent": "max"},
                        }
                    ]
                },
            )
        if tool == "hermes_artifact_get":
            return max_router.ToolResult(
                tool=tool,
                success=True,
                result={
                    "metadata": {
                        "id": "ha_demo_1",
                        "module": "archiveforge",
                        "approval_status": "approved",
                        "updated_at": "2026-05-16T01:00:00+00:00",
                        "is_current": True,
                        "latest_attestation_level": "session_verified",
                        "latest_attestation_hash_short": "abcd1234ef56",
                        "approval_confidence": "session_verified",
                        "provenance": {"source_agent": "max"},
                        "source_agent": "max",
                    },
                    "summary": "Approved ArchiveForge plan",
                    "is_current": True,
                    "requires_reattestation": False,
                },
            )
        raise AssertionError(f"Unexpected tool call: {tool_call}")

    monkeypatch.setattr(max_router, "execute_tool", fake_execute_tool)

    request = max_router.ChatRequest(
        message="What did we decide about ArchiveForge?",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "hermes-artifact-memory"
    assert "Artifact memory used" in response.response


def test_preflight_only_does_not_create_openclaw_task(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    blocked_tools = {"queue_openclaw_task", "dispatch_to_openclaw", "create_openclaw_task"}
    seen_tools: list[str] = []

    monkeypatch.setattr(
        max_router,
        "_build_supervised_v10_repair_preflight_result",
        _preflight_payload,
    )

    def fake_execute_tool(tool_call, founder=False):
        tool = str(tool_call.get("tool"))
        seen_tools.append(tool)
        if tool in blocked_tools:
            raise AssertionError(f"Preflight must not create tasks ({tool})")
        return max_router.ToolResult(tool=tool, success=True, result={})

    async def fail_ai_router(*args, **kwargs):
        raise AssertionError("Supervised preflight should not reach generic AI routing")

    monkeypatch.setattr(max_router, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)

    request = max_router.ChatRequest(
        message=(
            "MAX run supervised repair preflight only for v10. "
            "Do not touch stable/main. Wait for founder approval."
        ),
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "supervised-v10-repair-preflight"
    assert not any(tool in blocked_tools for tool in seen_tools)
