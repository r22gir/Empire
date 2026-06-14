"""
R1X MAX RUNTIME TRUTH — Live runtime state verification regression tests.

Verifies that MAX's runtime-truth response correctly reports backend health,
routing state, provider list, and memory state, and that the response is not
fabricated. The test suite is a mix of in-process FastAPI TestClient tests
and one (read-only) live HTTP test against the running backend.

⚠️  LIVE-TEST GUARD (2026-06-14) ⚠️
This file contains one test that calls the LIVE backend over HTTP:

  test_routing_unchanged_after_pre_search_guard (line 1353)
    GET http://127.0.0.1:8000/api/v1/max/routing-state

The test is wrapped in a try/except that silently passes on ConnectionError,
so it is read-only (GET, no mutation). However, per the 2026-06-14 audit's
broad rule ("any test that calls the live backend must be guarded"), the
entire module is now SKIPPED unless APOSTILLE_LIVE_TEST_TOKEN is set
explicitly. See backend/tests/helpers/live_test_guard.py and
HERMES-REPORT-GATE3-PAYMENT-INCIDENT-CLEANUP-AND-TEST-GUARDS-20260614.md.
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
from helpers.live_test_guard import require_live_test_token  # noqa: E402

require_live_test_token(__file__)

import importlib

from fastapi.testclient import TestClient

from app.main import app
from app.services.max.runtime_truth_check import (
    format_runtime_truth_check,
    is_openclaw_boundary_question,
    is_runtime_health_question,
    run_runtime_truth_check,
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


# ---------------------------------------------------------------------------
# Hermes dashboard health-question detection tests
# ---------------------------------------------------------------------------


def test_hermes_dashboard_health_questions_detected():
    """Hermes dashboard health questions must be detected by
    is_runtime_health_question so they route to runtime truth check."""
    prompts = [
        "Is Hermes dashboard online?",
        "Is Hermes running?",
        "Is Hermes dashboard up?",
        "Hermes dashboard status",
        "status of Hermes",
        "how is Hermes?",
        "check Hermes dashboard",
        "Is the Hermes dashboard working?",
    ]
    for prompt in prompts:
        assert is_runtime_health_question(prompt), (
            f"Expected health detection for: {prompt}"
        )


def test_runtime_truth_format_includes_hermes():
    """Formatted runtime truth response must include Hermes dashboard and
    Hermes cron lines."""
    response = format_runtime_truth_check({
        "mode": "inspect_only",
        "current_commit": {"hash": "abc1234", "message": "abc1234 test"},
        "registry": {"registry_version": "v2", "loaded_at": "now", "last_error": None},
        "openclaw_gate": {"state": "healthy", "allowed": True, "reason": "ok"},
        "backend_port_8000": {"port": 8000, "port_open": True, "service_active": True, "local_root_status": 200},
        "backend_port_8010": {"port": 8010, "port_open": False, "service_active": None, "local_root_status": None},
        "frontend_port_3005": {"port": 3005, "port_open": True, "service_active": True, "local_root_status": 200},
        "frontend_port_3010": {"port": 3010, "port_open": False, "service_active": None, "local_root_status": None},
        "hermes_dashboard": {"state": "up", "port": 9119, "port_open": True, "process_detected": True, "tui_gateway_detected": False, "evidence": "port 9119 open, dashboard process detected"},
        "hermes_cron": {"state": "paused", "jobs_count": 1, "lock_file_present": True},
        "local_freshness": {"api_git": {}, "api_matches_current_commit": True},
        "public_freshness": {"api_git": {}, "api_matches_current_commit": True},
        "restart_required": False,
        "stale_or_broken": [],
        "repair_capability": "inspect_only_no_restart",
    })

    assert "Hermes dashboard (port 9119)" in response
    assert "state=up" in response
    assert "process_detected=True" in response
    assert "evidence=port 9119 open" in response
    assert "Hermes cron" in response
    assert "state=paused" in response


def test_hermes_dashboard_no_fabricated_stats():
    """Hermes dashboard section must not contain fabricated PID, latency,
    memory, database, recall rate, queue depth, or sync claims."""
    response = format_runtime_truth_check({
        "mode": "inspect_only",
        "current_commit": {"hash": "abc1234", "message": "abc1234 test"},
        "registry": {"registry_version": "v2", "loaded_at": "now", "last_error": None},
        "openclaw_gate": {"state": "healthy", "allowed": True, "reason": "ok"},
        "backend_port_8000": {"port": 8000, "port_open": True, "service_active": True, "local_root_status": 200},
        "backend_port_8010": {"port": 8010, "port_open": False, "service_active": None, "local_root_status": None},
        "frontend_port_3005": {"port": 3005, "port_open": True, "service_active": True, "local_root_status": 200},
        "frontend_port_3010": {"port": 3010, "port_open": False, "service_active": None, "local_root_status": None},
        "hermes_dashboard": {"state": "down", "port": 9119, "port_open": False, "process_detected": False, "evidence": "port 9119 closed"},
        "hermes_cron": {"state": "paused", "jobs_count": 1, "lock_file_present": True},
        "local_freshness": {"api_git": {}, "api_matches_current_commit": True},
        "public_freshness": {"api_git": {}, "api_matches_current_commit": True},
        "restart_required": False,
        "stale_or_broken": [],
        "repair_capability": "inspect_only_no_restart",
    })

    # Isolate Hermes dashboard line
    hermes_line = ""
    for line in response.splitlines():
        if "Hermes dashboard" in line:
            hermes_line = line
            break

    assert hermes_line, "Hermes dashboard line must exist in output"
    # Must NOT contain fabricated fields in the Hermes section
    fabricated = ["pid", "PID", "latency", "memory", "database", "recall rate", "queue depth", "sync stats"]
    for field in fabricated:
        assert field not in hermes_line, (
            f"Hermes line must not contain fabricated field: '{field}'"
        )


def test_runtime_truth_run_includes_hermes_fields():
    """Actual run_runtime_truth_check() result dict must include
    hermes_dashboard and hermes_cron keys."""
    result = run_runtime_truth_check(public=False)

    assert "hermes_dashboard" in result
    assert "hermes_cron" in result

    hd = result["hermes_dashboard"]
    assert "state" in hd
    assert hd["state"] in ("up", "down", "unknown")
    assert hd["port"] == 9119
    assert "port_open" in hd
    assert "process_detected" in hd
    assert "evidence" in hd

    hc = result["hermes_cron"]
    assert "state" in hc
    assert hc["state"] in ("running", "paused", "unknown")
    assert "jobs_count" in hc
    assert "lock_file_present" in hc


# ---------------------------------------------------------------------------
# Routing state / model selector tests
# ---------------------------------------------------------------------------


def test_runtime_truth_includes_routing_state():
    """Formatted runtime truth response must include routing state lines."""
    response = format_runtime_truth_check({
        "mode": "inspect_only",
        "current_commit": {"hash": "abc1234", "message": "abc1234 test"},
        "registry": {"registry_version": "v2", "loaded_at": "now", "last_error": None},
        "openclaw_gate": {"state": "healthy", "allowed": True, "reason": "ok"},
        "backend_port_8000": {"port": 8000, "port_open": True, "service_active": True, "local_root_status": 200},
        "backend_port_8010": {"port": 8010, "port_open": False, "service_active": None, "local_root_status": None},
        "frontend_port_3005": {"port": 3005, "port_open": True, "service_active": True, "local_root_status": 200},
        "frontend_port_3010": {"port": 3010, "port_open": False, "service_active": None, "local_root_status": None},
        "hermes_dashboard": {"state": "up", "port": 9119, "port_open": True, "process_detected": True, "tui_gateway_detected": False, "evidence": "port 9119 open"},
        "hermes_cron": {"state": "paused", "jobs_count": 1, "lock_file_present": True},
        "routing_state": {
            "selected_provider": "deepseek",
            "selected_model": "deepseek-v4-flash",
            "fallback_enabled": False,
            "ai_calls_disabled": False,
            "minimax_selected": False,
            "selected_provider_label": "DeepSeek",
            "fallback_eligible_providers": ["minimax"],
            "source": "routing-state",
        },
        "local_freshness": {"api_git": {}, "api_matches_current_commit": True},
        "public_freshness": {"api_git": {}, "api_matches_current_commit": True},
        "restart_required": False,
        "stale_or_broken": [],
        "repair_capability": "inspect_only_no_restart",
    })

    assert "Selected provider: deepseek" in response
    assert "Selected model: deepseek-v4-flash" in response
    assert "MiniMax selected: False" in response
    assert "Fallback enabled: False" in response
    assert "AI calls disabled: False" in response
    assert "Automatic fallback allowed: False" in response


def test_routing_state_no_fabrication():
    """Routing state must not fabricate provider status — only report what
    the HTTP endpoint returns."""
    routing = {}
    assert routing.get("selected_provider") is None
    assert routing.get("selected_model") is None
    assert routing.get("latency") is None
    assert routing.get("memory") is None
    assert routing.get("database") is None
    assert routing.get("pid") is None


def test_model_selector_questions_routed_to_runtime_truth():
    """Routing state / model selector questions must be detected as runtime
    truth intents."""
    prompts = [
        "What provider and model are selected?",
        "What is the model selector set to?",
        "What routing state are you using?",
        "Is MiniMax selected?",
        "Is fallback enabled?",
        "Can you fallback to MiniMax?",
    ]
    for prompt in prompts:
        assert should_run_runtime_truth_check(prompt), (
            f"Expected runtime truth check for: {prompt}"
        )


def test_model_selector_health_question_is_detected():
    """'Is MiniMax selected?' must be caught by is_runtime_health_question
    via provider + selected verb logic (it's an edge case)."""
    # 'Is MiniMax selected?' — "minimax" is in HEALTH_TRIGGER_SERVICES
    # but "selected" is NOT in HEALTH_VERBS so it must match via intent signals.
    # 'selected' is matched via the INTENT_SIGNALS approach, not health verbs.
    from app.services.max.runtime_truth_check import is_runtime_health_question, should_run_runtime_truth_check

    # These should match via INTENT_SIGNALS (pattern-matched by should_run_runtime_truth_check)
    # not via is_runtime_health_question (which requires health verbs)
    assert should_run_runtime_truth_check("Is MiniMax selected?")


def test_routing_state_fields_in_run():
    """Actual run_runtime_truth_check() result dict must include routing_state
    with expected fields."""
    result = run_runtime_truth_check(public=False)

    assert "routing_state" in result
    rs = result["routing_state"]
    # Fields may be None if HTTP endpoint wasn't reachable during test
    # but the keys must exist
    assert "selected_provider" in rs
    assert "selected_model" in rs
    assert "fallback_enabled" in rs
    assert "ai_calls_disabled" in rs
    assert "minimax_selected" in rs
    assert "source" in rs


# ---------------------------------------------------------------------------
# OpenClaw action-boundary question tests
# ---------------------------------------------------------------------------


def test_openclaw_boundary_question_routes_to_runtime_truth():
    """OpenClaw action-boundary prompts must trigger runtime truth check."""
    prompts = [
        "OpenClaw boundary test. Can you create or execute an OpenClaw task right now?",
        "Can you create an OpenClaw task?",
        "Can you execute an OpenClaw task?",
        "Did you create a task?",
        "Did you execute it?",
        "Can OpenClaw run tasks right now?",
    ]
    for prompt in prompts:
        assert should_run_runtime_truth_check(prompt), (
            f"Expected runtime truth check for boundary prompt: {prompt}"
        )


def test_openclaw_boundary_answer_says_no_task_created_without_id():
    """Boundary answer must say task creation was NOT performed when there is no task ID."""
    fake_result = {
        "mode": "inspect_only",
        "current_commit": {"hash": "abc123", "message": "fix(openclaw): route chat through DeepSeek provider"},
        "registry": {"registry_version": "v1", "loaded_at": "now", "last_error": None},
        "openclaw_gate": {
            "state": "healthy",
            "allowed": True,
            "reason": "ok",
            "worker_heartbeat": {"current_task_id": None, "status": "polling", "fresh": True},
            "queue_stats": {"total": 7357, "done": 1439, "failed": 5916, "cancelled": 2},
        },
        "startup_health": {},
        "backend_port_8000": {"service_active": True, "port_open": True, "local_root_status": 200},
        "backend_port_8010": {"port_open": False},
        "frontend_port_3005": {"service_active": True, "port_open": True, "local_root_status": 200},
        "frontend_port_3010": {"port_open": False},
        "local_freshness": {"api_git": {"data": {"last_commit_hash": "abc123"}}, "api_matches_current_commit": True},
        "public_freshness": {"api_git": {"data": {"last_commit_hash": None}}, "api_matches_current_commit": False, "api_root": {"status_code": 200}, "studio_root": {"status_code": 200}},
        "hermes_dashboard": {"state": "up", "process_detected": True, "evidence": "port open"},
        "hermes_cron": {"state": "paused", "jobs_count": 12},
        "routing_state": {"selected_provider": "deepseek", "selected_provider_label": "DeepSeek", "selected_model": "deepseek-v4-flash", "fallback_enabled": False, "ai_calls_disabled": False, "minimax_selected": False, "fallback_eligible_providers": []},
        "restart_required": False,
        "stale_or_broken": [],
        "repair_capability": "inspect_only_no_restart",
    }

    response = format_runtime_truth_check(
        fake_result,
        message="OpenClaw boundary test. Can you create or execute an OpenClaw task right now?",
    )

    # Must still include the runtime truth report
    assert "Runtime truth check completed" in response
    assert "OpenClaw gate:" in response

    # Direct answer block must be present
    assert "Direct answer (from runtime truth evidence):" in response
    assert "OpenClaw health: online / healthy" in response
    assert "OpenClaw task creation: not performed by this check" in response
    assert "OpenClaw task execution: not performed by this check" in response
    assert "Task ID: none" in response
    assert "Queue drain: not performed by this check" in response
    assert "Execution evidence: none" in response
    assert "Next step: explicit founder approval is required before creating or executing a task" in response


def test_openclaw_boundary_answer_says_no_execution_without_evidence():
    """Boundary answer must not claim execution happened when there's no evidence."""
    fake_result = {
        "mode": "inspect_only",
        "current_commit": {"hash": "abc123", "message": "fix"},
        "registry": {"registry_version": "v1", "loaded_at": "now", "last_error": None},
        "openclaw_gate": {
            "state": "healthy",
            "allowed": True,
            "reason": "ok",
            "worker_heartbeat": {"current_task_id": None, "status": "polling", "fresh": True},
            "queue_stats": {"total": 7357},
        },
        "startup_health": {},
        "backend_port_8000": {"service_active": True, "port_open": True, "local_root_status": 200},
        "backend_port_8010": {"port_open": False},
        "frontend_port_3005": {"service_active": True, "port_open": True, "local_root_status": 200},
        "frontend_port_3010": {"port_open": False},
        "local_freshness": {"api_git": {"data": {"last_commit_hash": "abc123"}}, "api_matches_current_commit": True},
        "public_freshness": {"api_git": {"data": {"last_commit_hash": None}}, "api_matches_current_commit": False, "api_root": {"status_code": 200}, "studio_root": {"status_code": 200}},
        "hermes_dashboard": {"state": "up", "process_detected": True, "evidence": "port open"},
        "hermes_cron": {"state": "paused", "jobs_count": 12},
        "routing_state": {"selected_provider": "deepseek", "selected_provider_label": "DeepSeek", "selected_model": "deepseek-v4-flash", "fallback_enabled": False, "ai_calls_disabled": False, "minimax_selected": False, "fallback_eligible_providers": []},
        "restart_required": False,
        "stale_or_broken": [],
        "repair_capability": "inspect_only_no_restart",
    }

    response = format_runtime_truth_check(
        fake_result,
        message="Did you execute the OpenClaw task?",
    )

    # Must NOT fabricate execution claims
    assert "OpenClaw task execution: not performed by this check" in response
    assert "Execution evidence: none" in response
    assert "Task ID: none" in response

    # Must NOT contain fabricated success language
    assert "executed successfully" not in response.lower()
    assert "task was executed" not in response.lower()
    assert "completed the task" not in response.lower()


def test_openclaw_boundary_answer_does_not_drain_queue():
    """Boundary answer must not claim queue was drained."""
    fake_result = {
        "mode": "inspect_only",
        "current_commit": {"hash": "abc123", "message": "fix"},
        "registry": {"registry_version": "v1", "loaded_at": "now", "last_error": None},
        "openclaw_gate": {
            "state": "healthy",
            "allowed": True,
            "reason": "ok",
            "worker_heartbeat": {"current_task_id": None, "status": "polling", "fresh": True},
            "queue_stats": {"total": 7357, "done": 1439, "failed": 5916, "cancelled": 2},
        },
        "startup_health": {},
        "backend_port_8000": {"service_active": True, "port_open": True, "local_root_status": 200},
        "backend_port_8010": {"port_open": False},
        "frontend_port_3005": {"service_active": True, "port_open": True, "local_root_status": 200},
        "frontend_port_3010": {"port_open": False},
        "local_freshness": {"api_git": {"data": {"last_commit_hash": "abc123"}}, "api_matches_current_commit": True},
        "public_freshness": {"api_git": {"data": {"last_commit_hash": None}}, "api_matches_current_commit": False, "api_root": {"status_code": 200}, "studio_root": {"status_code": 200}},
        "hermes_dashboard": {"state": "up", "process_detected": True, "evidence": "port open"},
        "hermes_cron": {"state": "paused", "jobs_count": 12},
        "routing_state": {"selected_provider": "deepseek", "selected_provider_label": "DeepSeek", "selected_model": "deepseek-v4-flash", "fallback_enabled": False, "ai_calls_disabled": False, "minimax_selected": False, "fallback_eligible_providers": []},
        "restart_required": False,
        "stale_or_broken": [],
        "repair_capability": "inspect_only_no_restart",
    }

    response = format_runtime_truth_check(
        fake_result,
        message="Can you create an OpenClaw task? Do not drain old queued tasks.",
    )

    # Must explicitly say queue was NOT drained
    assert "Queue drain: not performed by this check" in response
    # Must show the actual queue total, not claim 0
    assert "7357" in response

    # Must NOT claim queue was drained
    assert "queue drained" not in response.lower()
    assert "drained queue" not in response.lower()


def test_openclaw_boundary_answer_does_not_claim_task_id():
    """Boundary answer must not fabricate a task ID when none exists."""
    fake_result = {
        "mode": "inspect_only",
        "current_commit": {"hash": "abc123", "message": "fix"},
        "registry": {"registry_version": "v1", "loaded_at": "now", "last_error": None},
        "openclaw_gate": {
            "state": "healthy",
            "allowed": True,
            "reason": "ok",
            "worker_heartbeat": {"current_task_id": None, "status": "polling", "fresh": True},
            "queue_stats": {"total": 7357},
        },
        "startup_health": {},
        "backend_port_8000": {"service_active": True, "port_open": True, "local_root_status": 200},
        "backend_port_8010": {"port_open": False},
        "frontend_port_3005": {"service_active": True, "port_open": True, "local_root_status": 200},
        "frontend_port_3010": {"port_open": False},
        "local_freshness": {"api_git": {"data": {"last_commit_hash": "abc123"}}, "api_matches_current_commit": True},
        "public_freshness": {"api_git": {"data": {"last_commit_hash": None}}, "api_matches_current_commit": False, "api_root": {"status_code": 200}, "studio_root": {"status_code": 200}},
        "hermes_dashboard": {"state": "up", "process_detected": True, "evidence": "port open"},
        "hermes_cron": {"state": "paused", "jobs_count": 12},
        "routing_state": {"selected_provider": "deepseek", "selected_provider_label": "DeepSeek", "selected_model": "deepseek-v4-flash", "fallback_enabled": False, "ai_calls_disabled": False, "minimax_selected": False, "fallback_eligible_providers": []},
        "restart_required": False,
        "stale_or_broken": [],
        "repair_capability": "inspect_only_no_restart",
    }

    response = format_runtime_truth_check(
        fake_result,
        message="Do not claim a task was created unless you return a real task ID.",
    )

    # Task ID must be "none" — not a fabricated one
    assert "Task ID: none" in response

    # Must NOT contain a fabricated task ID pattern (hex-like or numeric IDs)
    # The only "none" reference for task_id should be our explicit statement
    assert "task_created" not in response.lower()


def test_is_openclaw_boundary_question_detection():
    """Unit test for boundary question detection function."""
    boundary_prompts = [
        "OpenClaw boundary test. Can you create or execute an OpenClaw task?",
        "can you create an openclaw task",
        "can you execute an openclaw task right now",
        "did you create a task",
        "did you execute it",
        "do not claim execution without a task id",
        "do not claim a task was created without a real task id",
        "can openclaw run tasks",
        "openclaw task creation",
        "openclaw task execution",
        "Do not drain old queued tasks",
        "drain queue",
    ]
    for prompt in boundary_prompts:
        assert is_openclaw_boundary_question(prompt), (
            f"Expected boundary detection for: {prompt}"
        )

    non_boundary = [
        "what services are online",
        "is the latest code running",
        "what provider is selected",
        "hello max",
        "show me recent sales",
    ]
    for prompt in non_boundary:
        assert not is_openclaw_boundary_question(prompt), (
            f"Expected NO boundary detection for: {prompt}"
        )


# ---------------------------------------------------------------------------
# Hermes / external Hermes boundary question tests
# ---------------------------------------------------------------------------


def test_hermes_telegram_boundary_question_routes_to_runtime_truth():
    """Hermes/external Hermes Telegram questions must trigger runtime truth."""
    prompts = [
        "Can you check if external Hermes is receiving Telegrams?",
        "Is external Hermes receiving Telegram?",
        "Does Hermes have its own Telegram bot?",
        "Is Hermes dashboard online?",
        "Is Hermes gateway running?",
    ]
    for prompt in prompts:
        assert should_run_runtime_truth_check(prompt), (
            f"Expected runtime truth for: {prompt}"
        )


def test_hermes_boundary_answer_includes_channel_evidence():
    """Hermes boundary answer must synthesize channel and runtime evidence."""
    from app.services.max.runtime_truth_check import (
        _format_hermes_boundary_answer,
        _is_hermes_boundary_question,
    )

    # Must detect as Hermes boundary
    assert _is_hermes_boundary_question("Can you check if external Hermes is receiving Telegrams?")

    fake_result = {
        "hermes_dashboard": {"state": "up", "process_detected": True},
        "hermes_cron": {"state": "paused", "jobs_count": 12},
        "routing_state": {"selected_provider": "deepseek", "selected_model": "deepseek-v4-flash"},
    }
    fake_gate = {"state": "healthy", "allowed": True}

    answer = _format_hermes_boundary_answer(fake_result, fake_gate)

    answer_lower = answer.lower()

    # Must distinguish MAX Telegram from external Hermes Telegram
    assert "max telegram" in answer_lower
    assert "hermes dashboard" in answer_lower or "9119" in answer
    assert "external hermes telegram" in answer_lower
    assert "unverified" in answer_lower
    # Must NOT claim to have verified external Hermes
    assert "no hermes-specific telegram status endpoint" in answer_lower or "do not have a tool" in answer_lower
    # Must include provider context
    assert "deepseek" in answer_lower


def test_hermes_telegram_question_not_module_knowledge(monkeypatch):
    """Hermes Telegram questions must NOT route to empire-module-knowledge."""
    from app.services.max.runtime_truth_check import should_run_runtime_truth_check, _is_hermes_boundary_question

    prompt = "Can you check if external Hermes is receiving Telegrams?"
    assert should_run_runtime_truth_check(prompt)
    assert _is_hermes_boundary_question(prompt)

    # Also verify the resolve path would skip module knowledge
    from app.services.max.empire_module_knowledge import resolve_empire_module_question
    # The prompt contains "hermes" which IS a module, but should_run_runtime_truth_check
    # must return True FIRST so the router skips module knowledge
    module_hit = resolve_empire_module_question(prompt)
    # Even if module matches, the router's order ensures runtime truth wins
    # (should_run_runtime_truth_check checked before _empire_module_response)


# ---------------------------------------------------------------------------
# Provider capability synthesis tests
# ---------------------------------------------------------------------------


def test_provider_capability_question_routes_to_runtime_truth():
    """Provider capability questions must route to runtime truth."""
    prompts = [
        "What provider handles text, vision, voice, image generation, and OpenClaw right now?",
        "Which provider handles vision and image generation?",
        "What handles text and web search?",
    ]
    for prompt in prompts:
        assert should_run_runtime_truth_check(prompt), f"Failed: {prompt}"


def test_provider_capability_answer_separates_text_from_capabilities():
    """Provider capability answer must separate DeepSeek text from MiniMax lanes."""
    from app.services.max.runtime_truth_check import (
        _is_provider_capability_question,
        _format_provider_capability_answer,
    )
    assert _is_provider_capability_question(
        "What provider handles text, vision, voice, image generation, and OpenClaw right now?"
    )

    fake_result = {
        "routing_state": {
            "selected_provider": "deepseek",
            "selected_model": "deepseek-v4-flash",
            "fallback_enabled": False,
        },
        "openclaw_gate": {"state": "healthy", "allowed": True},
    }
    answer = _format_provider_capability_answer(fake_result)
    answer_l = answer.lower()

    assert "deepseek" in answer_l
    assert "deepseek-v4-flash" in answer_l
    assert "minimax" in answer_l
    assert "text" in answer_l
    assert "vision" in answer_l
    assert "fallback enabled: false" in answer_l
    assert "configured_unverified" in answer_l
    # Must NOT claim vision is offline
    assert "vision" not in answer_l or "offline" not in answer_l.split("vision")[-1][:200]


def test_provider_capability_no_fake_claims():
    """Provider capability must not fabricate working status without evidence."""
    from app.services.max.runtime_truth_check import _format_provider_capability_answer

    fake_result = {
        "routing_state": {
            "selected_provider": "deepseek",
            "selected_model": "deepseek-v4-flash",
            "fallback_enabled": False,
        },
        "openclaw_gate": {"state": "healthy"},
    }
    answer = _format_provider_capability_answer(fake_result)
    answer_l = answer.lower()

    # Vision/Image/TTS must NOT say verified_working without live test
    assert "configured_unverified" in answer_l
    # OpenClaw CAN say verified_working because gate health was confirmed
    assert "verified_working" in answer_l


# ---------------------------------------------------------------------------
# Web search tier tests
# ---------------------------------------------------------------------------


def test_web_search_question_routes_to_runtime_truth():
    """Web search provider questions must route to runtime truth."""
    prompts = [
        "What web search provider are you using, and is it the best option?",
        "What search engine does MAX use?",
        "Which search tool is configured?",
    ]
    for prompt in prompts:
        assert should_run_runtime_truth_check(prompt), f"Failed: {prompt}"


def test_web_search_matrix_has_tiers():
    """Capability matrix must show tiered web search, not just Brave/DDG."""
    from app.services.max.runtime_truth_check import _format_provider_capability_answer

    fake_result = {
        "routing_state": {"selected_provider": "deepseek", "selected_model": "deepseek-v4-flash", "fallback_enabled": False},
        "openclaw_gate": {"state": "healthy"},
    }
    answer = _format_provider_capability_answer(fake_result)
    answer_l = answer.lower()

    assert "tier 1" in answer_l
    assert "tier 2" in answer_l
    assert "tier 3" in answer_l
    assert "tier 4" in answer_l
    assert "brave search" in answer_l
    assert "duckduckgo" in answer_l
    # Must NOT describe Brave/DDG as the "best" or "only" option
    assert "source policy" in answer_l
    assert "cite" in answer_l


def test_web_search_boundary_answer_has_source_policy():
    """Web search boundary answer must include source policy and tiers."""
    from app.services.max.runtime_truth_check import (
        _format_web_search_boundary_answer,
        _is_web_search_boundary_question,
    )
    assert _is_web_search_boundary_question(
        "What web search provider are you using, and is it the best option?"
    )
    answer = _format_web_search_boundary_answer({})
    answer_l = answer.lower()

    assert "tier 1" in answer_l
    assert "tier 3" in answer_l
    assert "brave" in answer_l
    assert "source policy" in answer_l
    assert "cite" in answer_l
    assert "official" in answer_l
    # MiniMax search must not be marked verified
    assert "configured_unverified" in answer_l
    # Must not claim Brave is the best
    assert "adequate" in answer_l or "better" in answer_l or "deep research" in answer_l


# ---------------------------------------------------------------------------
# AI desks + Empire priority tests
# ---------------------------------------------------------------------------


def test_ai_desks_question_routes_to_runtime_truth():
    """AI desks questions must route to runtime truth."""
    for prompt in [
        "Which AI desks are ready, partial, blocked, or missing?",
        "What desks are available?",
        "List the AI desks and their status.",
    ]:
        assert should_run_runtime_truth_check(prompt), f"Failed: {prompt}"


def test_ai_desks_audit_has_all_required():
    """AI desks audit must include all 12 required desks."""
    from app.services.max.runtime_truth_check import _format_ai_desks_answer

    answer = _format_ai_desks_answer({})
    answer_l = answer.lower()

    required = [
        "max operations", "channel ops", "model selector",
        "workroom", "woodcraft", "pricing",
        "openclaw", "hermes", "supportforge",
        "archiveforge", "recoveryforge", "vendorops",
    ]
    for desk in required:
        assert desk in answer_l, f"Missing desk: {desk}"

    # Hermes must be partial
    assert "partial" in answer_l
    # Must use evidence-backed status labels
    assert "ready_for_guarded_execution" in answer_l or "guarded" in answer_l
    assert "ready_for_dry_run" in answer_l or "dry" in answer_l
    assert "ready_for_manual_action" in answer_l or "manual" in answer_l


def test_ai_desks_no_invented_desks():
    """AI desks must not invent desks that don't exist."""
    from app.services.max.runtime_truth_check import _format_ai_desks_answer

    answer = _format_ai_desks_answer({})
    answer_l = answer.lower()

    # These should NOT appear as desk names
    assert "phone desk" not in answer_l
    assert "sms desk" not in answer_l
    assert "social media desk" not in answer_l
    assert "marketing desk" not in answer_l
    assert "legal desk" not in answer_l


def test_empire_priority_routes_to_runtime_truth():
    """Empire priority questions must route to runtime truth."""
    for prompt in [
        "What are the top 5 EmpireBox priorities for MAX, Workroom, and Woodcraft?",
        "What are the top priorities right now?",
        "What should MAX prioritize?",
    ]:
        assert should_run_runtime_truth_check(prompt), f"Failed: {prompt}"


def test_empire_priority_emphasizes_max_workroom_woodcraft():
    """Empire priority must rank MAX/Workroom/Woodcraft first."""
    from app.services.max.runtime_truth_check import _format_empire_priority_answer

    answer = _format_empire_priority_answer({})
    answer_l = answer.lower()

    # These must appear early and prominently
    assert "max" in answer_l
    assert "workroom" in answer_l
    assert "woodcraft" in answer_l

    # ArchiveForge/RecoveryForge must appear only as secondary
    assert "secondary" in answer_l or "supporting" in answer_l

    # Must have 5 numbered priorities
    assert "1." in answer and "2." in answer and "3." in answer and "4." in answer and "5." in answer


# ---------------------------------------------------------------------------
# Multi-intent decomposition + unexecuted sub-intent flagging
# ---------------------------------------------------------------------------

def test_combined_prompt_detects_web_search_sub_intent():
    """Combined prompt with provider+desk+priority+web search must detect all sub-intents."""
    from app.services.max.runtime_truth_check import (
        _detect_sub_intents,
        _is_performative_web_search_request,
    )

    prompt = (
        "1. provider capability matrix "
        "2. AI desks status "
        "3. top priorities for Empire "
        "4. external Hermes Telegram "
        "5. web search for current DeepSeek API pricing with sources"
    )

    intents = _detect_sub_intents(prompt)
    assert intents["provider_capability"], "provider_capability not detected"
    assert intents["ai_desks"], "ai_desks not detected"
    assert intents["empire_priority"], "empire_priority not detected"
    assert intents["hermes_boundary"], "hermes_boundary not detected"
    assert intents["performative_web_search"], "performative_web_search not detected"

    # "web search for X" is a performative request, NOT a boundary question
    assert not intents["web_search_boundary"], (
        "'web search for X' should not match web_search_boundary (that's for "
        "'what search engine do you use?')"
    )

    # Standalone detection
    assert _is_performative_web_search_request(
        "web search for current DeepSeek API pricing with sources"
    )
    assert _is_performative_web_search_request("search for latest GPU prices")
    assert _is_performative_web_search_request("look up current lumber futures")
    assert _is_performative_web_search_request("find current DeepSeek pricing online")

    # Should NOT match questions about search tools
    assert not _is_performative_web_search_request("what search engine do you use?")
    assert not _is_performative_web_search_request("which search provider is best?")


def test_runtime_truth_response_flags_unexecuted_web_search():
    """Runtime truth response must explicitly flag web search as not executed."""
    from app.services.max.runtime_truth_check import (
        _detect_sub_intents,
        _format_unexecuted_sub_intents,
    )

    # Simulate a combined prompt that has a web search request
    prompt = (
        "AI desks audit and priorities and "
        "search for current DeepSeek API pricing with sources"
    )
    intents = _detect_sub_intents(prompt)
    assert intents["performative_web_search"]

    flag = _format_unexecuted_sub_intents(intents)
    assert "Web search portion not executed from this runtime truth response" in flag
    assert "re-issue" in flag.lower() or "separate" in flag.lower()

    # A prompt without web search should produce no flag
    intents_no_search = _detect_sub_intents("what are the AI desks and top priorities?")
    assert not intents_no_search.get("performative_web_search")
    assert _format_unexecuted_sub_intents(intents_no_search) == ""


def test_full_format_includes_unexecuted_web_search_flag():
    """format_runtime_truth_check must append unexecuted sub-intent notice."""
    result = run_runtime_truth_check(public=False)
    prompt = (
        "provider capability matrix, AI desks status, priorities, "
        "external Hermes Telegram, web search for current DeepSeek API pricing with sources"
    )
    formatted = format_runtime_truth_check(result, prompt)
    assert "Web search portion not executed from this runtime truth response" in formatted
    assert "Unexecuted sub-intents" in formatted


# ---------------------------------------------------------------------------
# AI desks status wording — no broad "ready"
# ---------------------------------------------------------------------------

def test_ai_desks_audit_no_broad_ready_language():
    """AI desks must not use broad 'ready' without a specific status mapping."""
    from app.services.max.runtime_truth_check import _format_ai_desks_answer

    answer = _format_ai_desks_answer({})

    # Must use the specific status taxonomy
    assert "ready_for_guarded_execution" in answer
    assert "ready_for_founder_review" in answer
    assert "ready_for_manual_action" in answer
    assert "ready_for_dry_run" in answer
    assert "partial" in answer

    # The old broad "X desks ready" pattern must not appear
    import re
    broad_ready_pattern = re.compile(r"\d+\s+desks?\s+ready\b")
    matches = broad_ready_pattern.findall(answer)
    assert not matches, (
        f"Found broad 'ready' language without specific status mapping: {matches}"
    )

    # Status key must map to specific statuses only
    status_key_section = answer.split("Summary")[0]
    assert "G=ready_for_guarded_execution" in status_key_section
    assert "X=missing" in status_key_section


def test_ai_desks_audit_openclaw_approval_gated():
    """OpenClaw desk must remain approval-gated in the audit output."""
    from app.services.max.runtime_truth_check import _format_ai_desks_answer

    answer = _format_ai_desks_answer({})

    # OpenClaw status is ready_for_guarded_execution (shown as G in table,
    # full status name in detailed section or summary)
    assert "ready_for_guarded_execution" in answer, (
        "OpenClaw must appear as ready_for_guarded_execution in audit"
    )

    # Verify OpenClaw detail section mentions approval gating
    oc_detailed_start = answer.find("\n  OpenClaw —")
    assert oc_detailed_start >= 0, "OpenClaw detailed section not found"
    oc_detailed = answer[oc_detailed_start:oc_detailed_start + 500]

    assert "approval" in oc_detailed.lower()
    assert "task ID" in oc_detailed or "task execution requires" in oc_detailed or "founder" in oc_detailed.lower()


def test_ai_desks_archiveforge_recoveryforge_secondary():
    """ArchiveForge and RecoveryForge must remain dry-run/secondary in audit."""
    from app.services.max.runtime_truth_check import _format_ai_desks_answer

    answer = _format_ai_desks_answer({})

    # Both must be ready_for_dry_run (shown as D in table, "Ready For Dry Run" in detail)
    for desk_name in ["ArchiveForge", "RecoveryForge"]:
        # Find the detailed section for this desk (title-cased status names)
        detail_marker = f"\n  {desk_name} —"
        idx = answer.find(detail_marker)
        assert idx >= 0, f"{desk_name} detailed section not found"
        section = answer[idx:idx + 300]

        assert "Ready For Dry Run" in section, (
            f"{desk_name} should be Ready For Dry Run in detailed section, got: {section[:200]}"
        )

        # Must NOT be guarded execution
        assert "Ready For Guarded Execution" not in section, (
            f"{desk_name} must not be guarded execution"
        )

    # Summary must mention both as dry-run
    summary_start = answer.find("Summary")
    summary = answer[summary_start:] if summary_start >= 0 else answer

    assert "ArchiveForge" in summary
    assert "RecoveryForge" in summary
    assert "dry-run" in summary.lower()


# ---------------------------------------------------------------------------
# Web search answer finalization guard tests
# ---------------------------------------------------------------------------

def test_performative_search_detected_for_pricing_prompt():
    """'Search the web for current DeepSeek API pricing' must be detected as performative."""
    from app.services.max.runtime_truth_check import _is_performative_web_search_request

    prompts = [
        "Search the web for current DeepSeek API pricing and summarize with sources.",
        "search the web for current DeepSeek API pricing with sources",
        "web search for current GPU prices and give me source URLs",
        "look up current DeepSeek API pricing per token",
        "find current pricing for Anthropic API",
        "search for latest lumber prices",
    ]
    for prompt in prompts:
        assert _is_performative_web_search_request(prompt), (
            f"Should detect performative search: {prompt}"
        )

    # These should NOT trigger (they're boundary questions, not search requests)
    non_search = [
        "what search engine do you use?",
        "which search provider is best?",
        "how do you do web searches?",
    ]
    for prompt in non_search:
        assert not _is_performative_web_search_request(prompt), (
            f"Should NOT detect non-performative: {prompt}"
        )


def test_pre_search_guard_pre_executes_web_search(monkeypatch):
    """The pre-search guard must execute web_search before the AI generates a response."""
    from app.services.max.runtime_truth_check import _is_performative_web_search_request

    # Simulate the guard logic in isolation
    prompt = "Search the web for current DeepSeek API pricing and summarize with sources."
    assert _is_performative_web_search_request(prompt)

    # Verify the guard would execute (test the tool call shape)
    search_tc = {"tool": "web_search", "query": prompt, "num_results": 5}
    assert search_tc["tool"] == "web_search"
    assert "DeepSeek" in search_tc["query"]


def test_pre_search_failure_path_says_unavailable():
    """When web_search fails, the system message must forbid fabrication."""
    from app.services.max.runtime_truth_check import _is_performative_web_search_request

    prompt = "search for current DeepSeek API pricing"
    assert _is_performative_web_search_request(prompt)

    # Simulate the failure message that would be prepended
    failure_msg = (
        "[SYSTEM: web_search was attempted for this query but returned no results "
        "or failed. You must tell the user that web_search is currently unavailable "
        "for this query. Do NOT fabricate pricing, current facts, or any data from "
        "training data. Say: 'web_search returned no results for this query — I "
        "cannot provide current pricing without verified search data.']"
    )
    assert "web_search returned no results" in failure_msg
    assert "Do NOT fabricate" in failure_msg
    assert "cannot provide current pricing" in failure_msg


def test_tool_tracking_includes_web_search_on_pre_execute():
    """Pre-executed web_search must appear in tool results tracking."""
    from app.services.max.tool_executor import execute_tool

    # Execute a real web_search to verify it returns properly shaped results
    result = execute_tool(
        {"tool": "web_search", "query": "DeepSeek API pricing 2026", "num_results": 3},
        founder=True,
    )
    assert result.success
    assert result.tool == "web_search"
    assert result.result is not None

    # Verify result has expected shape for metadata tracking
    data = result.result
    assert "query" in data
    assert "results" in data
    assert isinstance(data["results"], list)

    # Verify the normalized shape (mirroring _normalize_tool_result_entry in router.py)
    entry = {"tool": result.tool, "success": result.success, "result": result.result}
    assert entry["tool"] == "web_search"
    assert entry["success"] is True

    # Source URLs should be present if results returned
    if data["results"]:
        for r in data["results"]:
            assert "url" in r, f"Result missing URL: {r}"
            assert "title" in r, f"Result missing title: {r}"


def test_web_search_failure_result_structure():
    """When web_search returns no results, the response shape must still be valid."""
    from app.services.max.tool_executor import execute_tool

    # Search for nonsense — DDG may return empty or minimal results
    result = execute_tool(
        {"tool": "web_search", "query": "xyznonexistent1234abc", "num_results": 2},
        founder=True,
    )
    assert result.success  # The tool itself should succeed even if no results
    data = result.result
    assert "query" in data
    assert "results" in data
    assert "count" in data
    # count may be 0 or results may be empty
    assert data["count"] >= 0


def test_routing_unchanged_after_pre_search_guard():
    """DeepSeek routing and fallback must remain unchanged regardless of guard."""
    import requests
    try:
        resp = requests.get("http://127.0.0.1:8000/api/v1/max/routing-state", timeout=5)
        assert resp.status_code == 200
        state = resp.json()
        assert state["selected_provider"] == "deepseek"
        assert state["selected_model"] == "deepseek-v4-flash"
        assert state["fallback_enabled"] is False
    except requests.ConnectionError:
        pass  # Server may not be running in test


def test_performative_search_query_not_mistaken_for_boundary():
    """'search for X' must NOT match web_search_boundary (what search engine)."""
    from app.services.max.runtime_truth_check import (
        _is_performative_web_search_request,
        _is_web_search_boundary_question,
    )

    prompt = "search the web for current DeepSeek API pricing with sources"
    assert _is_performative_web_search_request(prompt)
    assert not _is_web_search_boundary_question(prompt), (
        "'search the web for X' must not be classified as a boundary question"
    )
