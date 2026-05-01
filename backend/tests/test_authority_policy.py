"""Tests for MAX v10 Test-Lane Authority Policy.

Covers:
- environment detection (canonical vs v10_test)
- memory write guardrails
- filesystem write guardrails
- git branch commit guardrails
- promotion report generation
- founder channel authorization
"""
import os
from pathlib import Path

import pytest

# Test the authority module in isolation (no FastAPI needed)
from app.services.max.authority import (
    EnvironmentType,
    EnvironmentPolicy,
    get_current_policy,
    format_environment_status,
    MemoryGuardrails,
    WriteGuardrails,
    check_memory_write,
    check_write_allowed,
    FOUNDER_CHANNELS,
)


# ── Environment Policy Tests ─────────────────────────────────────────

class TestEnvironmentPolicy:
    def test_canonical_environment_detection_from_cwd(self):
        """When cwd is ~/empire-repo, environment should be CANONICAL."""
        policy = EnvironmentPolicy()
        assert policy.environment == EnvironmentType.CANONICAL
        assert policy.is_canonical is True
        assert policy.is_v10_test is False

    def test_canonical_properties(self):
        """Canonical environment should have correct properties."""
        policy = EnvironmentPolicy()
        assert policy.environment_name == "canonical"
        assert policy.memory_mode == "read_write"
        assert policy.write_scope == "canonical"
        assert policy.canonical_memory_write_allowed is True
        assert policy.founder_approval_required is True

    def test_allowed_git_branches_canonical(self):
        """Canonical should be able to write to feature/v10.0, main."""
        policy = EnvironmentPolicy()
        assert "feature/v10.0" in policy.allowed_git_branches
        assert "main" in policy.allowed_git_branches
        assert "feature/v10.0-test-lane" not in policy.allowed_git_branches

    def test_blocked_git_branches_canonical(self):
        """Canonical should not have blocked branches."""
        policy = EnvironmentPolicy()
        assert len(policy.blocked_git_branches) == 0

    def test_get_status_returns_all_fields(self):
        """get_status() should return complete environment status."""
        policy = EnvironmentPolicy()
        status = policy.get_status()
        required_fields = [
            "environment_name", "is_canonical", "is_v10_test",
            "repo_root", "branch", "current_commit",
            "memory_mode", "write_scope",
            "canonical_memory_write_allowed", "founder_approval_required",
            "allowed_git_branches", "blocked_git_branches",
            "memory_source", "can_promote",
        ]
        for field in required_fields:
            assert field in status, f"Missing field: {field}"

    def test_format_environment_status_human_readable(self):
        """format_environment_status() should produce readable output."""
        policy = EnvironmentPolicy()
        output = format_environment_status(policy)
        assert "Environment: canonical" in output
        assert "Repo:" in output
        assert "Branch:" in output
        assert "Commit:" in output
        assert "Memory: read_write" in output
        assert "Write scope: canonical" in output


class TestMemoryGuardrails:
    def test_canonical_can_write_with_founder_channel(self):
        """Canonical MAX with founder channel should be allowed to write memory."""
        for channel in FOUNDER_CHANNELS:
            allowed, reason = MemoryGuardrails.can_write(channel=channel)
            assert allowed is True, f"canonical should allow write via {channel}: {reason}"

    def test_canonical_cannot_write_without_channel(self):
        """Canonical MAX without channel should be blocked from memory write."""
        allowed, reason = MemoryGuardrails.can_write(channel=None)
        assert allowed is False
        assert "founder channel" in reason.lower()

    def test_canonical_cannot_write_with_unknown_channel(self):
        """Canonical MAX with non-founder channel should be blocked."""
        allowed, reason = MemoryGuardrails.can_write(channel="unknown")
        assert allowed is False
        assert "founder channel" in reason.lower()

    def test_canonical_can_read(self):
        """Both environments should be able to read memory."""
        allowed, reason = MemoryGuardrails.can_read()
        assert allowed is True

    def test_create_memory_proposal_v10_test(self, monkeypatch):
        """v10_test should be able to create memory proposals."""
        # Patch get_current_policy to return a v10_test policy
        v10_policy = EnvironmentPolicy(environment=EnvironmentType.V10_TEST)
        monkeypatch.setattr(
            "app.services.max.authority.memory_guardrails.get_current_policy",
            lambda: v10_policy,
        )
        proposal = MemoryGuardrails.create_memory_proposal(
            category="test_category",
            subject="test subject",
            content="test content",
            tags=["test"],
            importance=7,
            channel=None,
        )
        assert "proposal_id" in proposal
        assert proposal["type"] == "memory_patch"
        assert proposal["environment"] == "v10_test"
        assert proposal["status"] == "pending_review"
        assert "review_required_from" in proposal


class TestWriteGuardrails:
    def test_canonical_can_write_to_empire_repo(self):
        """Canonical MAX should be allowed to write to ~/empire-repo."""
        allowed, reason = WriteGuardrails.check_path_write(
            os.path.expanduser("~/empire-repo/backend/app/test_file.py")
        )
        assert allowed is True

    def test_canonical_can_write_to_tmp(self):
        """Canonical MAX should be allowed to write to /tmp."""
        allowed, reason = WriteGuardrails.check_path_write("/tmp/empire_test.txt")
        assert allowed is True

    def test_check_git_branch_canonical(self):
        """Canonical should allow commits to feature/v10.0 and main."""
        for branch in ["feature/v10.0", "main", "master"]:
            allowed, reason = WriteGuardrails.check_git_branch(branch)
            assert allowed is True, f"canonical should allow {branch}: {reason}"

    def test_canonical_rejects_unknown_branch(self):
        """Canonical should block commits to unknown branches."""
        allowed, reason = WriteGuardrails.check_git_branch("feature/unknown")
        assert allowed is False

    def test_get_promotion_report_structure(self):
        """Promotion report should have all required fields."""
        report = WriteGuardrails.get_promotion_report(
            files_changed=["backend/app/test.py"],
            tests_passed=True,
            risk_level="low",
            memory_implications=["brain memory count may change"],
            canonical_memory_needs_update=False,
        )
        required_fields = [
            "promotion_id", "environment", "branch", "commit",
            "files_changed", "tests_passed", "risk_level",
            "memory_implications", "canonical_memory_needs_update",
            "promotion_eligible", "approval_required_from",
            "steps_to_promote", "if_rejected",
        ]
        for field in required_fields:
            assert field in report, f"Missing field: {field}"

    def test_get_promotion_report_eligible_when_tests_pass_and_risk_low(self):
        """Promotion eligible when tests passed and risk is not high."""
        report = WriteGuardrails.get_promotion_report(
            files_changed=["backend/app/test.py"],
            tests_passed=True,
            risk_level="low",
            memory_implications=[],
            canonical_memory_needs_update=False,
        )
        assert report["promotion_eligible"] is True

    def test_get_promotion_report_not_eligible_when_tests_fail(self):
        """Promotion not eligible when tests fail."""
        report = WriteGuardrails.get_promotion_report(
            files_changed=["backend/app/test.py"],
            tests_passed=False,
            risk_level="low",
            memory_implications=[],
            canonical_memory_needs_update=False,
        )
        assert report["promotion_eligible"] is False

    def test_get_promotion_report_not_eligible_when_risk_high(self):
        """Promotion not eligible when risk is high."""
        report = WriteGuardrails.get_promotion_report(
            files_changed=["backend/app/test.py"],
            tests_passed=True,
            risk_level="high",
            memory_implications=[],
            canonical_memory_needs_update=False,
        )
        assert report["promotion_eligible"] is False


class TestCheckWriteAllowed:
    def test_check_write_allowed_shorthand(self):
        """check_write_allowed should be equivalent to WriteGuardrails.check_path_write."""
        allowed, reason = check_write_allowed(os.path.expanduser("~/empire-repo/test.txt"))
        assert allowed is True


class TestFounderChannels:
    def test_founder_channels_defined(self):
        """FOUNDER_CHANNELS should contain expected channels."""
        assert "web_cc" in FOUNDER_CHANNELS
        assert "telegram" in FOUNDER_CHANNELS
        assert "email" in FOUNDER_CHANNELS
        assert "founder" in FOUNDER_CHANNELS
        assert len(FOUNDER_CHANNELS) == 4


class TestSingletonPolicy:
    def test_get_current_policy_returns_same_instance(self):
        """get_current_policy() should return the same policy instance."""
        policy1 = get_current_policy()
        policy2 = get_current_policy()
        assert policy1 is policy2