import importlib

from fastapi.testclient import TestClient

from app.main import app
from app.services.max.runtime_truth_check import (
    format_runtime_truth_check,
    is_runtime_health_question,
    should_run_runtime_truth_check,
)
from app.services.max.tool_executor import ToolResult, execute_tool


client = TestClient(app)
max_router_module = importlib.import_module("app.routers.max.router")


def test_runtime_truth_intent_signals_are_detected():
    prompts = [
        "is this live?",
        "why don't I see the fix?",
        "website not loading",
        "did the new build deploy?",
        "is the latest code running?",
        "nothing changed",
        "still seeing old version",
        "is studio/api current?",
        "did it restart?",
        "did the update go live?",
        "what's new Max",
        "what’s new Max",
        "whats new Max",
        "current status",
        "is it broken?",
        "is it fixed?",
        "did that push?",
    ]
    for prompt in prompts:
        assert should_run_runtime_truth_check(prompt)

    assert not should_run_runtime_truth_check("what quotes are due today?")


# ---------------------------------------------------------------------------
# is_runtime_health_question unit tests
# ---------------------------------------------------------------------------


def test_is_runtime_health_question_detects_health_queries():
    """Health questions about known services should be detected."""
    prompts = [
        "Is OpenClaw online right now?",
        "Is OpenClaw running?",
        "Is Hermes running?",
        "Is Hermes dashboard online?",
        "Are MiniMax and DeepSeek working?",
        "Is the backend healthy?",
        "Is RecoveryForge running?",
        "Is the queue active?",
        "Is v10 online?",
        "Is the worker available?",
        "Is OpenClaw reachable?",
        "How is OpenClaw?",
        "check on the worker",
        "OpenClaw status",
        "status of Hermes",
        "Are the workers running?",
        "Is the queue up?",
    ]
    for prompt in prompts:
        assert is_runtime_health_question(prompt), (
            f"Expected health detection for: {prompt}"
        )


def test_is_runtime_health_question_rejects_non_health():
    """Non-health questions should NOT be detected as health questions."""
    prompts = [
        "what is ArchiveForge?",
        "tell me about OpenClaw",
        "what features does Hermes have?",
        "what is OpenClaw doing right now?",
        "define the backend",
        "when will ArchiveForge publish?",
        "what's the update on RecoveryForge?",
    ]
    for prompt in prompts:
        assert not is_runtime_health_question(prompt), (
            f"Expected no health detection for: {prompt}"
        )


def test_is_runtime_health_question_excludes_openclaw_gate_phrases():
    """Only imperative 'check openclaw' phrases must be excluded from health
    detection (they route through the dedicated OpenClaw gate).
    Interrogative phrases like 'is openclaw healthy' are NOT excluded —
    they route to the runtime truth check which includes OpenClaw gate state."""
    from app.services.max.runtime_truth_check import is_runtime_health_question

    # Imperative "check openclaw" is excluded (routes to gate)
    assert not is_runtime_health_question("check openclaw")
    assert not is_runtime_health_question("check open claw")

    # Interrogative "is openclaw healthy" is NOT excluded (routes to runtime truth)
    assert is_runtime_health_question("is openclaw healthy")
    assert is_runtime_health_question("is open claw healthy")

    # "openclaw health" — not matched by any health pattern, returns False
    # (falls through to gate check in router.py)
    assert not is_runtime_health_question("openclaw health")


def test_is_runtime_health_question_detects_patterns_2_thru_5():
    """All five detection patterns should fire for their respective prompts."""
    from app.services.max.runtime_truth_check import is_runtime_health_question

    # Pattern 2: <service> status / status of <service>
    assert is_runtime_health_question("OpenClaw status")
    assert is_runtime_health_question("status of Hermes")
    # Pattern 3: check [on] [the] <service>
    assert is_runtime_health_question("check worker")
    assert is_runtime_health_question("check on the queue")
    # Pattern 4: how is|are [the] <service>
    assert is_runtime_health_question("how is OpenClaw")
    assert is_runtime_health_question("how are the workers")
    # Pattern 5: are [the] <serviceA> and <word> <health_verb>
    assert is_runtime_health_question("Are MiniMax and DeepSeek working?")
    assert is_runtime_health_question("are openclaw and hermes running?")


def test_should_run_runtime_truth_check_includes_health_questions():
    """should_run_runtime_truth_check must also catch health questions now
    that is_runtime_health_question is integrated."""
    prompts = [
        "Is OpenClaw online?",
        "Is Hermes running?",
        "Is the backend healthy?",
    ]
    for prompt in prompts:
        assert should_run_runtime_truth_check(prompt), (
            f"Expected runtime truth check for: {prompt}"
        )


def test_runtime_truth_tool_is_callable(monkeypatch):
    def fake_check(public=True):
        return {
            "skill": "empire-runtime-truth-check",
            "callable": "empire_runtime_truth_check",
            "mode": "inspect_only",
            "current_commit": {"hash": "abc1234", "message": "abc1234 test"},
            "backend_status": {"service": {"active": True}, "port_8000_open": True, "local_root": {"status_code": 200}},
            "frontend_status": {"service": {"active": True}, "port_3005_open": True, "local_root": {"status_code": 200}},
            "local_freshness": {"api_git": {"data": {"last_commit_hash": "abc1234"}}, "api_matches_current_commit": True},
            "public_freshness": {"api_git": {"data": {"last_commit_hash": "abc1234"}}, "api_matches_current_commit": True, "api_root": {"status_code": 200}, "studio_root": {"status_code": 200}},
            "restart_required": False,
            "stale_or_broken": [],
            "repair_capability": "inspect_only_no_restart",
        }

    monkeypatch.setattr("app.services.max.runtime_truth_check.run_runtime_truth_check", fake_check)
    result = execute_tool({"tool": "empire_runtime_truth_check", "public": True}, founder=True)

    assert result.success is True
    assert result.result["callable"] == "empire_runtime_truth_check"
    assert result.result["mode"] == "inspect_only"
    assert result.result["restart_required"] is False
    assert "Runtime truth check completed" in format_runtime_truth_check(result.result)


def test_runtime_truth_format_labels_stale_startup_memory():
    response = format_runtime_truth_check(
        {
            "mode": "inspect_only",
            "current_commit": {"hash": "new1234", "message": "new1234 current"},
            "startup_health": {"running_commit_hash": "old9999"},
            "registry": {"registry_version": "operating-registry-v2", "loaded_at": "now", "last_error": None},
            "openclaw_gate": {"state": "healthy", "allowed": True, "reason": "ok"},
            "backend_status": {"service": {"active": True}, "port_8000_open": True, "local_root": {"status_code": 200}},
            "frontend_status": {"service": {"active": True}, "port_3005_open": True, "local_root": {"status_code": 200}},
            "local_freshness": {"api_git": {"data": {"last_commit_hash": "new1234"}}, "api_matches_current_commit": True},
            "public_freshness": {"api_git": {"data": {"last_commit_hash": "new1234"}}, "api_matches_current_commit": True, "api_root": {"status_code": 200}, "studio_root": {"status_code": 200}},
            "restart_required": False,
            "stale_or_broken": [],
            "repair_capability": "inspect_only_no_restart",
        }
    )

    assert "prior startup commit old9999 differs from live commit new1234" in response
    assert "live runtime truth wins" in response


def test_continuity_audit_tool_is_callable():
    result = execute_tool({"tool": "empire_max_continuity_audit", "channel": "mobile_browser"}, founder=True)

    assert result.success is True
    assert result.result["callable"] == "empire_max_continuity_audit"
    assert result.result["surface"]["canonical_channel"] == "web_chat"
    assert "registry_version" in result.result
    assert result.result["supermemory_status"] in {"secondary_recall_scaffold", "unavailable_secondary_recall"}


def test_founder_continuity_audit_prompt_routes_to_callable():
    res = client.post(
        "/api/v1/max/chat",
        json={"message": "is MAX current on this device?", "channel": "mobile_browser"},
    )

    assert res.status_code == 200
    data = res.json()
    assert data["model_used"] == "empire-max-continuity-audit"
    assert data["metadata"]["skill_used"] == "empire_max_continuity_audit"
    assert "Continuity audit completed" in data["response"]
    assert "web_chat" in data["response"]


def test_founder_prompt_auto_routes_to_runtime_truth_hook(monkeypatch):
    def fake_execute_tool(tool_call, desk=None, access_context=None, founder=False):
        assert tool_call == {"tool": "empire_runtime_truth_check", "public": True}
        return ToolResult(
            tool="empire_runtime_truth_check",
            success=True,
            result={
                "skill": "empire-runtime-truth-check",
                "callable": "empire_runtime_truth_check",
                "mode": "inspect_only",
                "current_commit": {"hash": "abc1234", "message": "abc1234 test"},
                "backend_status": {"service": {"active": True}, "port_8000_open": True, "local_root": {"status_code": 200}},
                "frontend_status": {"service": {"active": True}, "port_3005_open": True, "local_root": {"status_code": 200}},
                "local_freshness": {"api_git": {"data": {"last_commit_hash": "abc1234"}}, "api_matches_current_commit": True},
                "public_freshness": {"api_git": {"data": {"last_commit_hash": "abc1234"}}, "api_matches_current_commit": True, "api_root": {"status_code": 200}, "studio_root": {"status_code": 200}},
                "restart_required": False,
                "stale_or_broken": [],
                "repair_capability": "inspect_only_no_restart",
            },
        )

    monkeypatch.setattr(max_router_module, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(max_router_module, "_save_runtime_truth_exchange", lambda *args, **kwargs: "runtime-test")

    res = client.post("/api/v1/max/chat", json={"message": "is the latest code running?", "channel": "web"})

    assert res.status_code == 200
    data = res.json()
    assert data["model_used"] == "empire-runtime-truth-check"
    assert data["tool_results"][0]["tool"] == "empire_runtime_truth_check"
    assert "Runtime truth check completed" in data["response"]
    assert data["metadata"]["registry_version"]
    assert data["metadata"]["surface"] == "Founder/Web MAX"
    assert data["metadata"]["skill_used"] == "empire_runtime_truth_check"


def test_whats_new_max_auto_routes_to_runtime_truth_hook(monkeypatch):
    def fake_execute_tool(tool_call, desk=None, access_context=None, founder=False):
        assert tool_call == {"tool": "empire_runtime_truth_check", "public": True}
        return ToolResult(
            tool="empire_runtime_truth_check",
            success=True,
            result={
                "skill": "empire-runtime-truth-check",
                "callable": "empire_runtime_truth_check",
                "mode": "inspect_only",
                "current_commit": {"hash": "new1234", "message": "new1234 current"},
                "startup_health": {"running_commit_hash": "old9999"},
                "registry": {"registry_version": "operating-registry-v2", "loaded_at": "now", "last_error": None},
                "backend_status": {"service": {"active": True}, "port_8000_open": True, "local_root": {"status_code": 200}},
                "frontend_status": {"service": {"active": True}, "port_3005_open": True, "local_root": {"status_code": 200}},
                "local_freshness": {"api_git": {"data": {"last_commit_hash": "new1234"}}, "api_matches_current_commit": True},
                "public_freshness": {"api_git": {"data": {"last_commit_hash": "new1234"}}, "api_matches_current_commit": True, "api_root": {"status_code": 200}, "studio_root": {"status_code": 200}},
                "restart_required": False,
                "stale_or_broken": [],
                "repair_capability": "inspect_only_no_restart",
            },
        )

    monkeypatch.setattr(max_router_module, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(max_router_module, "_save_runtime_truth_exchange", lambda *args, **kwargs: "runtime-test")

    res = client.post("/api/v1/max/chat", json={"message": "what's new Max", "channel": "web"})

    assert res.status_code == 200
    data = res.json()
    assert data["model_used"] == "empire-runtime-truth-check"
    assert data["tool_results"][0]["tool"] == "empire_runtime_truth_check"
    assert "Current repo commit: new1234" in data["response"]
    assert "prior startup commit old9999 differs from live commit new1234" in data["response"]
    assert data["metadata"]["skill_used"] == "empire_runtime_truth_check"


def test_founder_compaction_command_routes_to_handoff_writer(monkeypatch, tmp_path):
    monkeypatch.setattr("app.services.max.continuity_compaction.HANDOFF_PATH", tmp_path / "handoff.json")
    monkeypatch.setattr(
        "app.services.max.continuity_compaction._runtime_truth",
        lambda: {
            "current_commit": {"hash": "handoff123"},
            "restart_required": False,
            "openclaw_gate": {"state": "healthy"},
        },
    )
    monkeypatch.setattr(
        "app.services.max.continuity_compaction._active_task_state",
        lambda: {"openclaw_tasks": [], "max_tasks": [{"id": "t1"}]},
    )
    monkeypatch.setattr("app.services.max.continuity_compaction._latest_score", lambda: {"overall_score": 0.98})
    monkeypatch.setattr(
        "app.services.max.supermemory_recall.write_handoff_memory_from_packet",
        lambda packet: {"written": True, "memory_id": "test"},
    )

    res = client.post("/api/v1/max/chat", json={"message": "save state", "channel": "web"})

    assert res.status_code == 200
    data = res.json()
    assert data["model_used"] == "session-handoff"
    assert "Session handoff refreshed" in data["response"]
    assert "handoff123" in data["response"]
    assert data["metadata"]["skill_used"] == "session_handoff"


def test_self_assessment_invokes_continuity_audit_when_scores_low(monkeypatch):
    monkeypatch.setattr(
        "app.services.max.evaluation_loop_v1.get_recent_scores",
        lambda limit=5: [{"overall_score": 0.4} for _ in range(limit)],
    )
    monkeypatch.setattr(
        "app.services.max.continuity_compaction.audit_continuity_state",
        lambda channel="web": {"callable": "empire_max_continuity_audit", "surface": {"canonical_channel": "web_chat"}},
    )

    res = client.get("/api/v1/max/self-assessment?channel=web&limit=5")

    assert res.status_code == 200
    data = res.json()
    assert data["average_score"] == 0.4
    assert data["should_run_continuity_audit"] is True
    assert data["skill_used"] == "empire_max_continuity_audit"
    assert "Running a continuity check" in data["message"]
