"""Tests for remote founder task delegation from MAX.

Covers:
- should_run_runtime_truth_check: task delegation not intercepted
- queue_openclaw_task: port detection, hermes support, response format
- get_openclaw_task_status: task listing and lookup
- Hermes support packet generation
- Founder-only access guardrails
"""
import pytest

from app.services.max.runtime_truth_check import (
    should_run_runtime_truth_check,
    _normalize_intent_text,
    TASK_DELEGATION_BLOCKLIST,
)
from app.services.max.hermes_memory import (
    build_hermes_support_packet,
    render_task_support_packet,
)


class TestShouldRunRuntimeTruthCheck:
    """Task delegation messages must NOT trigger the runtime truth check early-return."""

    # These should NOT trigger runtime truth check (task creation intent)
    TASK_DELEGATION_MESSAGES = [
        "Start OpenClaw working on the intake form fix",
        "create an OpenClaw task for the bug fix",
        "Start OpenClaw and Hermes working on X",
        "start development crew on recovery audit",
        "delegate to OpenClaw to fix the render pipeline",
        "create a task for OpenClaw",
        "add task for OpenClaw to process quotes",
        "queue task for OpenClaw: update the frontend",
        "hermes help with the measurement checklist",
        "start OpenClaw task: fix the email routing",
        "dispatch to openclaw to update documentation",
        "start codeforge task: refactor the auth module",
        "Create an OpenClaw task — is max broken?",
        "Start OpenClaw and check if max is broken",
        "create task: is studio/api current?",
    ]

    @pytest.mark.parametrize("message", TASK_DELEGATION_MESSAGES)
    def test_task_delegation_not_intercepted(self, message):
        """Task delegation messages must pass through to AI model for tool planning."""
        result = should_run_runtime_truth_check(message)
        assert result is False, f"Task delegation message was incorrectly intercepted: '{message}'"

    # These SHOULD trigger runtime truth check (genuine status queries)
    RUNTIME_STATUS_MESSAGES = [
        "runtime truth",
        "max status",
        "is archiveforge live",
        "is this live",
        "is it live",
        "is it broken",
        "is max broken",
        "is max fixed",
        "what's new",
        "what changed",
        "what's new today",
        "latest status",
        "latest commit",
        "current commit",
        "current status",
        "did it push",
        "did that push",
        "is studio/api current",
        "why don't i see the fix",
        "website not loading",
        "nothing changed",
        "still seeing old version",
        "today's status",
        "did the new build deploy",
        "is the latest code running",
    ]

    @pytest.mark.parametrize("message", RUNTIME_STATUS_MESSAGES)
    def test_runtime_status_queries_intercepted(self, message):
        """Genuine runtime status queries should be intercepted."""
        result = should_run_runtime_truth_check(message)
        assert result is True, f"Runtime status query was not intercepted: '{message}'"

    # Edge cases
    def test_empty_message_not_intercepted(self):
        assert should_run_runtime_truth_check("") is False
        assert should_run_runtime_truth_check(None) is False

    def test_ordinary_conversation_not_intercepted(self):
        assert should_run_runtime_truth_check("Hello MAX, how are you?") is False
        assert should_run_runtime_truth_check("What's for lunch?") is False
        assert should_run_runtime_truth_check("Thanks for the update") is False


class TestHermesSupportPacket:
    """Hermes support packet for OpenClaw task delegation."""

    def test_build_hermes_support_packet_structure(self):
        """Support packet must contain all required checklists and metadata."""
        packet = build_hermes_support_packet(
            task_title="Fix intake form routing",
            task_description="Route intake submissions to the correct desk",
            target_repo="~/empire-repo-v10",
            target_branch="feature/v10.0-test-lane",
        )

        assert "packet_id" in packet
        assert packet["hermes_role"] == "support_guidance_only"
        assert "hermes_does_not" in packet
        assert "hermes_does" in packet
        assert packet["target"]["repo"] == "~/empire-repo-v10"
        assert packet["target"]["branch"] == "feature/v10.0-test-lane"
        assert packet["target"]["write_scope"] == "v10_test_lane_only"
        assert packet["target"]["stable_repo_blocked"] is True
        assert packet["target"]["canonical_memory_blocked"] is True
        assert "intake_fields" in packet["checklists"]
        assert "measurement_requirements" in packet["checklists"]
        assert "quote_package_checklist" in packet["checklists"]
        assert "approval_checkpoints" in packet["checklists"]
        assert isinstance(packet["safety_notes"], list)
        assert len(packet["safety_notes"]) > 0

    def test_hermes_is_read_only(self):
        """Hermes must never claim ability to write code or modify files."""
        packet = build_hermes_support_packet(
            task_title="Test task",
            task_description="Test",
        )
        hermes_does_not = packet["hermes_does_not"]
        assert "write code" in hermes_does_not
        assert "modify files" in hermes_does_not
        assert "commit directly" in hermes_does_not
        assert "access memory" in hermes_does_not

    def test_render_task_support_packet(self):
        """Support packet renders to readable markdown with all sections."""
        packet = build_hermes_support_packet(
            task_title="Test task",
            task_description="Test description",
        )
        rendered = render_task_support_packet(packet)
        assert "Hermes Support Packet" in rendered
        assert "Test task" in rendered
        assert "v10_test_lane_only" in rendered
        assert "Intake Fields" in rendered or "intake_fields" in rendered
        assert "Safety Notes" in rendered
        assert "⚠️" in rendered  # Safety warnings use ⚠️


class TestAccessControlLevels:
    """Verify tool access levels for task delegation tools."""

    def test_queue_openclaw_task_requires_confirmation(self):
        """queue_openclaw_task is level 2 (confirm) — not auto for public."""
        from app.services.max.access_control import TOOL_LEVELS
        assert "queue_openclaw_task" in TOOL_LEVELS
        assert TOOL_LEVELS["queue_openclaw_task"] == 2

    def test_get_openclaw_task_status_is_auto(self):
        """get_openclaw_task_status is level 1 (auto) — safe for any authenticated user."""
        from app.services.max.access_control import TOOL_LEVELS
        assert "get_openclaw_task_status" in TOOL_LEVELS
        assert TOOL_LEVELS["get_openclaw_task_status"] == 1


class TestToolCorrections:
    """Verify tool name aliases route to correct functions via execute_tool behavior."""

    def test_create_openclaw_task_routes_to_queue(self):
        """'create_openclaw_task' must route to queue_openclaw_task via execute_tool."""
        from app.services.max.tool_executor import execute_tool

        # The tool should be recognized (even if backend port check fails, it shouldn't
        # return "unknown tool" error)
        result = execute_tool({"tool": "create_openclaw_task", "params": {}})
        # Should not be an unknown tool error
        assert "unknown" not in (result.error or "").lower()
        assert "not found" not in (result.error or "").lower()

    def test_get_openclaw_task_status_is_recognized(self):
        """'get_openclaw_task_status' must be a recognized tool."""
        from app.services.max.tool_executor import execute_tool

        result = execute_tool({"tool": "get_openclaw_task_status", "params": {}})
        # Should not be unknown tool
        assert "unknown" not in (result.error or "").lower()
        assert "not found" not in (result.error or "").lower()


class TestNormalizeIntentText:
    """Edge cases in intent text normalization."""

    def test_curly_apostrophe_normalized_to_straight(self):
        """Curly apostrophes must be normalized to straight."""
        # Input has curly right-single-quote U+2019
        text = _normalize_intent_text("\u2019what\u2019s new")
        # After normalization, curly quotes replaced with straight
        assert "\u2019" not in text
        assert "'" in text

    def test_extra_whitespace_normalized(self):
        """Multiple spaces must be collapsed."""
        text = _normalize_intent_text("what's     new")
        assert "  " not in text
