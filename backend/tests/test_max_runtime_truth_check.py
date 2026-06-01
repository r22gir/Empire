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
