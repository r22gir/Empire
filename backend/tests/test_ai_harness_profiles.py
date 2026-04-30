"""
Tests for AI Harness Profiles service and endpoints.
"""
import pytest
from app.services.ai_harness_profiles import (
    registry,
    AIHarnessProfile,
    AIHarnessProfileRegistry,
    ALL_TASK_TYPES,
    TASK_TYPE_CODE_PATCH,
    TASK_TYPE_EMERGENCY_REPAIR,
    TASK_TYPE_MAX_CHAT,
    TASK_TYPE_REPO_AUDIT,
    TASK_TYPE_OPENCLAW_TASK,
    log_routing_decision,
    get_recent_routing_decisions,
)


class TestProfileRegistry:
    """Test the profile registry loads and returns valid data."""

    def test_list_profiles_returns_profiles(self):
        profiles = registry.list_profiles(enabled_only=True)
        assert len(profiles) > 0
        assert all(p.enabled for p in profiles)

    def test_all_profiles_have_required_fields(self):
        profiles = registry.list_profiles(enabled_only=False)
        for p in profiles:
            assert p.id
            assert p.display_name
            assert p.provider
            assert p.model
            assert isinstance(p.task_types, list)
            assert len(p.task_types) > 0
            assert p.description
            assert p.priority >= 0
            assert p.risk_level in {"safe", "low", "medium", "high", "critical"}
            assert p.tool_policy in {"default", "strict", "permissive", "disabled"}
            assert p.file_access_policy in {"read_only", "read_write", "none"}
            assert p.approval_policy in {"none", "founder", "review"}
            assert p.testing_policy in {"none", "verify", "required"}
            assert p.cost_tier in {"free", "low", "medium", "high"}
            assert p.speed_tier in {"fast", "medium", "slow"}
            assert p.quality_tier in {"standard", "high", "maximum"}
            assert p.reliability_tier in {"experimental", "standard", "high"}

    def test_task_types_are_valid(self):
        for task_type in ALL_TASK_TYPES:
            assert isinstance(task_type, str)
            assert len(task_type) > 0

    def test_get_profile_valid_id(self):
        profile = registry.get_profile("claude_repo_audit_profile")
        assert profile is not None
        assert profile.id == "claude_repo_audit_profile"

    def test_get_profile_invalid_id(self):
        profile = registry.get_profile("nonexistent_profile")
        assert profile is None


class TestTaskTypeMapping:
    """Test task type maps to expected default profile."""

    def test_code_patch_has_default(self):
        default = registry.get_default_for_task(TASK_TYPE_CODE_PATCH)
        assert default is not None
        assert TASK_TYPE_CODE_PATCH in default.task_types

    def test_repo_audit_has_default(self):
        default = registry.get_default_for_task(TASK_TYPE_REPO_AUDIT)
        assert default is not None
        assert TASK_TYPE_REPO_AUDIT in default.task_types

    def test_emergency_repair_has_default(self):
        default = registry.get_default_for_task(TASK_TYPE_EMERGENCY_REPAIR)
        assert default is not None
        assert TASK_TYPE_EMERGENCY_REPAIR in default.task_types


class TestExplicitProviderSelection:
    """Test explicit provider selection chooses matching provider profile."""

    def test_request_openai_provider(self):
        profile, routing = registry.select_profile(
            task_type=TASK_TYPE_CODE_PATCH,
            requested_provider="openai",
        )
        assert profile is not None
        assert profile.provider == "openai"
        assert routing.selected_provider == "openai"

    def test_request_anthropic_provider(self):
        profile, routing = registry.select_profile(
            task_type=TASK_TYPE_REPO_AUDIT,
            requested_provider="anthropic",
        )
        assert profile is not None
        assert profile.provider == "anthropic"


class TestEmergencyOverride:
    """Test emergency Grok override chooses grok_emergency_repair_profile."""

    def test_emergency_override_selects_grok_profile(self):
        profile, routing = registry.select_profile(
            task_type=TASK_TYPE_MAX_CHAT,
            emergency_override=True,
        )
        assert profile is not None
        assert profile.id == "grok_emergency_repair_profile"
        assert routing.emergency_override is True
        assert routing.selected_profile_id == "grok_emergency_repair_profile"


class TestDisabledProfiles:
    """Test disabled profiles are not selected."""

    def test_disabled_profile_not_returned_as_default(self):
        # Temporarily disable claude_repo_audit_profile
        original = registry.get_profile("claude_repo_audit_profile")
        assert original is not None
        original_enabled = original.enabled

        try:
            original.enabled = False
            default = registry.get_default_for_task(TASK_TYPE_REPO_AUDIT)
            # Should fall back to something else or None
            assert default is None or default.id != "claude_repo_audit_profile"
        finally:
            original.enabled = original_enabled


class TestFallbackSelection:
    """Test fallback profile is selected when primary unavailable."""

    def test_fallback_to_budget_when_no_match(self):
        # Request a task type with no default, should fall back
        profile, routing = registry.select_profile(
            task_type=TASK_TYPE_MAX_CHAT,
            requested_provider="nonexistent_provider",
            requested_model="nonexistent_model",
        )
        # Should still return something (either fallback or default chat)
        assert routing is not None
        assert routing.task_type == TASK_TYPE_MAX_CHAT


class TestSelectionResponse:
    """Test selection response includes routing explanation."""

    def test_routing_explanation_fields(self):
        profile, routing = registry.select_profile(
            task_type=TASK_TYPE_CODE_PATCH,
        )
        assert routing.selected_profile_id
        assert routing.selected_provider
        assert routing.selected_model
        assert routing.task_type == TASK_TYPE_CODE_PATCH
        assert routing.reason
        assert isinstance(routing.fallback_used, bool)

    def test_policy_summary_builds(self):
        summary = registry.build_policy_summary("claude_repo_audit_profile")
        assert "Profile:" in summary
        assert "Provider:" in summary
        assert "Risk level:" in summary

    def test_system_instruction_block_builds(self):
        block = registry.build_system_instruction_block(
            "grok_emergency_repair_profile",
            TASK_TYPE_EMERGENCY_REPAIR,
        )
        assert "Harness Profile:" in block
        assert "Task:" in block
        assert "System Instructions" in block


class TestTelemetry:
    """Test telemetry logging is safe and functional."""

    def test_log_routing_decision_no_crash(self):
        # Should not raise — even with bad inputs
        log_routing_decision(
            channel="test",
            task_type=TASK_TYPE_MAX_CHAT,
            selected_provider="xai",
            selected_model="grok-4-fast-non-reasoning",
            selected_harness_profile="max_default_chat_profile",
            fallback_used=False,
            fallback_reason="",
            emergency_override=False,
        )

    def test_get_recent_routing_decisions_returns_list(self):
        entries = get_recent_routing_decisions(limit=5)
        assert isinstance(entries, list)


class TestStarterProfilesExist:
    """Test all required starter profiles exist."""

    def test_claude_repo_audit_profile(self):
        p = registry.get_profile("claude_repo_audit_profile")
        assert p is not None
        assert p.provider == "anthropic"
        assert p.priority == 20

    def test_openai_codex_patch_profile(self):
        p = registry.get_profile("openai_codex_patch_profile")
        assert p is not None
        assert p.provider == "openai"

    def test_grok_emergency_repair_profile(self):
        p = registry.get_profile("grok_emergency_repair_profile")
        assert p is not None
        assert p.provider == "xai"
        assert p.emergency_only is True
        assert p.priority == 5  # highest

    def test_gemini_research_visual_profile(self):
        p = registry.get_profile("gemini_research_visual_profile")
        assert p is not None
        assert p.provider == "google"

    def test_qwen_local_coding_profile(self):
        p = registry.get_profile("qwen_local_coding_profile")
        assert p is not None
        assert p.local_only is True

    def test_minimax_visual_quote_profile(self):
        p = registry.get_profile("minimax_visual_quote_profile")
        assert p is not None
        assert p.provider == "minimax"

    def test_ollama_budget_fallback_profile(self):
        p = registry.get_profile("ollama_budget_fallback_profile")
        assert p is not None
        assert p.local_only is True
        assert p.cost_tier == "free"

    def test_opencode_repo_execution_profile(self):
        p = registry.get_profile("opencode_repo_execution_profile")
        assert p is not None
        assert TASK_TYPE_OPENCLAW_TASK in p.task_types
