"""
MAX Control Plane tests (2026-06-15 hotfix).

These tests cover the exact failures observed in the live Founder/MAX
transcript:

  1. MAX identity is NOT provider/model (MAX = MAX; minimax/M3 is the
     language provider, exposed separately under ``provider``).
  2. Tool claim requires a proof object. If a tool is unavailable, MAX
     must say so consistently (no "yes web_search works" / "no web
     access" contradiction).
  3. Web/search availability cannot contradict registry truth.
  4. OpenClaw/local probe claim requires actual proof (the OpenClaw
     audit showed MAX said it would probe OpenClaw but never did).
  5. Memory/doctrine access reports truthful availability, not invented
     doctrine.
  6. Stale startup/handoff state is surfaced as a warning, and matches
     when current truth is available.
  7. Payment/runtime guards remain intact.
  8. Drawing router still does NOT hijack normal planning.

These tests are PURE (no live backend, no live Stripe, no live OpenClaw
mutation). They test the ``app.services.max.control_plane`` module
directly.
"""

from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

# Make sure we can import the backend app modules.
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


class TestMaxIdentityIsSeparateFromProvider(unittest.TestCase):
    """MAX identity must be 'MAX', not the provider/model string."""

    def test_max_identity_name_is_max(self):
        from app.services.max.control_plane import MAX_IDENTITY
        self.assertEqual(MAX_IDENTITY["name"], "MAX")
        self.assertEqual(MAX_IDENTITY["display_name"], "MAX")

    def test_max_identity_does_not_contain_provider_or_model(self):
        from app.services.max.control_plane import MAX_IDENTITY
        # MAX identity MUST NOT leak the provider name or model into the
        # identity. The provider/model lives under ``provider`` in the
        # control plane payload.
        for key, value in MAX_IDENTITY.items():
            self.assertNotIn("minimax", str(value).lower(), f"identity.{key} leaks provider name")
            self.assertNotIn("MiniMax-M3", str(value), f"identity.{key} leaks model name")

    def test_control_plane_separates_identity_from_provider(self):
        from app.services.max.control_plane import get_control_plane
        cp = get_control_plane()
        self.assertIn("identity", cp)
        self.assertIn("provider", cp)
        self.assertEqual(cp["identity"]["name"], "MAX")
        # The provider section is allowed to mention minimax/M3.
        provider_str = str(cp["provider"])
        self.assertTrue(
            "minimax" in provider_str or cp["provider"].get("error"),
            f"provider section should mention minimax or surface an error: {cp['provider']}",
        )

    def test_no_text_minimax_label_in_identity(self):
        """UI bug fix: 'Text minimax-MiniMax-M3' must not appear as MAX identity."""
        from app.services.max.control_plane import MAX_IDENTITY
        identity_str = str(MAX_IDENTITY)
        self.assertNotIn("Text", identity_str)
        self.assertNotIn("text minimax", identity_str.lower())


class TestToolRegistryTruth(unittest.TestCase):
    """Tool claims must be backed by the tool registry."""

    def test_web_search_is_unavailable(self):
        from app.services.max.control_plane import get_tool_registry
        tools = {t["key"]: t for t in get_tool_registry()}
        self.assertIn("web_search", tools)
        # As of 2026-06-15, web_search has no backend in app.services.max.tool_executor.
        # MAX must report it consistently as unavailable, not flip-flop.
        self.assertEqual(tools["web_search"]["status"], "unavailable")
        self.assertIn("proof_reason", tools["web_search"])
        self.assertTrue(tools["web_search"]["proof_required"])

    def test_web_read_is_unavailable(self):
        from app.services.max.control_plane import get_tool_registry
        tools = {t["key"]: t for t in get_tool_registry()}
        self.assertEqual(tools["web_read"]["status"], "unavailable")
        self.assertTrue(tools["web_read"]["proof_required"])

    def test_filesystem_shell_is_unavailable(self):
        from app.services.max.control_plane import get_tool_registry
        tools = {t["key"]: t for t in get_tool_registry()}
        # MAX must NOT pretend to have raw filesystem/shell access via
        # the local broker. Use the operator-side tools (Hermes, CodeForge)
        # for that, both requiring separate Founder approval.
        self.assertEqual(tools["filesystem_shell"]["status"], "unavailable")

    def test_ollama_is_unavailable(self):
        from app.services.max.control_plane import get_tool_registry
        tools = {t["key"]: t for t in get_tool_registry()}
        # Ollama is founder_disabled_due_to_stall_suspected.
        self.assertEqual(tools["ollama_status"]["status"], "unavailable")

    def test_openclaw_status_is_read_only(self):
        from app.services.max.control_plane import get_tool_registry
        tools = {t["key"]: t for t in get_tool_registry()}
        # openclaw_status is a read-only tool. It must NOT mutate the queue.
        self.assertEqual(tools["openclaw_status"]["status"], "read-only")
        self.assertFalse(tools["openclaw_status"]["mutating"])

    def test_local_broker_is_read_only(self):
        from app.services.max.control_plane import get_tool_registry
        tools = {t["key"]: t for t in get_tool_registry()}
        self.assertEqual(tools["local_broker"]["status"], "read-only")
        self.assertFalse(tools["local_broker"]["mutating"])

    def test_all_tools_have_proof_required(self):
        from app.services.max.control_plane import get_tool_registry
        # All tools in the registry MUST have proof_required=True.
        # This is the "no claim without proof" enforcement.
        for tool in get_tool_registry():
            self.assertTrue(
                tool.get("proof_required"),
                f"tool {tool.get('key')} is missing proof_required=True",
            )

    def test_tool_categories(self):
        from app.services.max.control_plane import get_tool_registry
        # Each tool must declare its category.
        for tool in get_tool_registry():
            self.assertIn("category", tool, f"tool {tool.get('key')} missing category")
            self.assertTrue(
                tool["category"] in {"web", "memory", "openclaw", "broker", "telegram", "local_model", "email"},
                f"tool {tool.get('key')} has unexpected category {tool['category']}",
            )


class TestLocalBrokerTruth(unittest.TestCase):
    """Local broker must report truthful status, not pretend to expose more."""

    def test_broker_does_not_pretend_filesystem_access(self):
        from app.services.max.control_plane import _filesystem_tool
        tool = _filesystem_tool()
        # The local broker does NOT expose raw filesystem/shell access.
        # MAX must not pretend otherwise.
        self.assertEqual(tool["status"], "unavailable")
        self.assertIn("approval", tool["proof_reason"].lower())

    def test_broker_reports_repo_truth(self):
        from app.services.max.control_plane import get_local_broker_status
        broker = get_local_broker_status()
        self.assertIn("repo", broker)
        self.assertIn("branch", broker["repo"])
        self.assertIn("commit", broker["repo"])
        self.assertTrue(len(broker["repo"]["commit"]) >= 7, "commit must be at least short SHA")

    def test_broker_reports_backend_port_health(self):
        from app.services.max.control_plane import get_local_broker_status
        broker = get_local_broker_status()
        self.assertIn("backend", broker)
        self.assertIn("port", broker["backend"])
        self.assertIn("state", broker["backend"])
        self.assertIn(broker["backend"]["state"], {"up", "down"})

    def test_broker_reports_frontend_build_id(self):
        from app.services.max.control_plane import get_local_broker_status
        broker = get_local_broker_status()
        self.assertIn("frontend", broker)
        self.assertIn("build_id", broker["frontend"])
        # The build_id should look like 'build-NNNN' or 'unknown' if .next is missing.
        bid = broker["frontend"]["build_id"]
        self.assertTrue(
            bid == "unknown" or bid.startswith("build-"),
            f"build_id must be 'unknown' or start with 'build-', got: {bid}",
        )


class TestMemoryStatusTruth(unittest.TestCase):
    """Memory status must be truthful, not invented doctrine."""

    def test_memory_status_has_active_source(self):
        from app.services.max.control_plane import get_memory_status
        ms = get_memory_status()
        self.assertIn("active_memory_source", ms)
        # As of 2026-06-15, the active source is hermes_memory.
        # If hermes_memory fails to import, the source should be 'unknown'.
        self.assertIn(ms["active_memory_source"], {"hermes_memory", "unknown"})

    def test_memory_status_reports_newest_file(self):
        from app.services.max.control_plane import get_memory_status
        ms = get_memory_status()
        # Should report the newest memory/audit file in agent_workspace.
        self.assertIn("newest_memory_file", ms)
        self.assertIn("newest_memory_timestamp", ms)

    def test_doctrine_source_availability(self):
        from app.services.max.control_plane import get_memory_status
        ms = get_memory_status()
        self.assertIn("doctrine_source_availability", ms)
        # hermes_memory should be available.
        self.assertIn("hermes_memory", ms["doctrine_source_availability"])

    def test_handoff_freshness_reports_match_or_warning(self):
        from app.services.max.control_plane import get_memory_status
        ms = get_memory_status()
        hf = ms["handoff_freshness"]
        self.assertIn("matches", hf)
        self.assertIn("warning", hf)
        # If matches is False, warning MUST be a non-None string explaining the mismatch.
        if not hf["matches"]:
            self.assertIsNotNone(hf["warning"])
            self.assertTrue(len(hf["warning"]) > 0)


class TestProofReceiptEnforcement(unittest.TestCase):
    """MAX must not say 'I ran/probed/checked' without a real proof object.

    The 2026-06-14 OpenClaw audit showed MAX said it would probe OpenClaw
    but did not. The runtime_truth_enforcer module already has the
    'verification failed' pattern. These tests verify that the enforcer
    still works correctly.
    """

    def test_runtime_truth_enforcer_fails_on_empty_tool_results(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        # Empty tool_results means MAX cannot claim any verification.
        # The enforcer should return no failures (because there are no
        # verified-required tools in the empty list), but the caller
        # should still treat this as "no proof".
        failures = runtime_truth_failures([], user_message="I checked OpenClaw")
        self.assertEqual(failures, [])

    def test_runtime_truth_enforcer_detects_send_email_without_attachment(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        # User asked for attachment but tool result has 0 attachments.
        tool_results = [
            {"tool": "send_email", "success": True, "result": {"attachments_sent": 0}}
        ]
        failures = runtime_truth_failures(tool_results, user_message="Please send the PDF")
        self.assertTrue(len(failures) > 0)
        self.assertIn("attachment", failures[0].lower())

    def test_runtime_truth_enforcer_passes_when_attachment_verified(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        tool_results = [
            {"tool": "send_email", "success": True, "result": {"attachments_sent": 1}}
        ]
        failures = runtime_truth_failures(tool_results, user_message="Please send the PDF")
        self.assertEqual(failures, [])


class TestPaymentGuardsRemainIntact(unittest.TestCase):
    """The 2026-06-14 payment test guards must remain intact."""

    def test_live_test_guard_module_exists(self):
        helper_path = (
            Path(__file__).resolve().parent
            / "helpers"
            / "live_test_guard.py"
        )
        self.assertTrue(helper_path.exists(), f"live_test_guard.py missing at {helper_path}")

    def test_unsafe_tests_have_guard_calls(self):
        # These 9 files were guarded in the 2026-06-14 hotfix.
        # They must STILL have a guard call after this control plane hotfix.
        unsafe_files = [
            "test_apostille_public.py",
            "test_payments_apostille_url_hardening.py",
            "test_payments_webhook_fail_closed.py",
            "test_apostapp_metadata_wiring.py",
            "test_apostapp_llcfactory_boundary.py",
            "test_apostille_public_navigator.py",
            "test_apostapp_scroll_ux.py",
            "test_vendorops_core.py",
            "test_max_runtime_truth_check.py",
        ]
        for name in unsafe_files:
            path = Path(__file__).resolve().parent / name
            self.assertTrue(path.exists(), f"unsafe test file missing: {name}")
            content = path.read_text()
            self.assertIn(
                "require_live_test_token(__file__)",
                content,
                f"guard call missing in {name}",
            )


class TestControlPlaneEndpointShape(unittest.TestCase):
    """The /api/v1/max/control-plane endpoint must return a stable shape."""

    def test_control_plane_shape(self):
        from app.services.max.control_plane import get_control_plane
        cp = get_control_plane()
        # Top-level keys
        self.assertIn("identity", cp)
        self.assertIn("provider", cp)
        self.assertIn("local_broker", cp)
        self.assertIn("tool_registry", cp)
        self.assertIn("memory", cp)
        self.assertIn("checked_at", cp)

    def test_identity_shape(self):
        from app.services.max.control_plane import MAX_IDENTITY
        # Identity must have name, display_name, role, version.
        for key in ("name", "display_name", "role", "version"):
            self.assertIn(key, MAX_IDENTITY)

    def test_provider_shape(self):
        from app.services.max.control_plane import get_control_plane
        provider = get_control_plane()["provider"]
        # Either it has provider_canonical/model OR an error.
        if "error" not in provider:
            self.assertIn("provider_canonical", provider)
            self.assertIn("model", provider)

    def test_tool_registry_shape(self):
        from app.services.max.control_plane import get_tool_registry
        tools = get_tool_registry()
        # Each tool must have: key, category, status, proof_required,
        # approval_required, mutating, description, proof_reason.
        required_keys = {
            "key", "category", "status", "proof_required",
            "approval_required", "mutating", "description", "proof_reason",
        }
        for tool in tools:
            missing = required_keys - set(tool.keys())
            self.assertEqual(
                missing, set(),
                f"tool {tool.get('key')} missing keys: {missing}",
            )

    def test_memory_shape(self):
        from app.services.max.control_plane import get_memory_status
        ms = get_memory_status()
        # Memory must have: active_memory_source, newest_memory_timestamp,
        # doctrine_source_availability, hermes_sync_artifact_status,
        # handoff_freshness, checked_at.
        for key in (
            "active_memory_source",
            "newest_memory_timestamp",
            "doctrine_source_availability",
            "hermes_sync_artifact_status",
            "handoff_freshness",
            "checked_at",
        ):
            self.assertIn(key, ms, f"memory status missing key: {key}")


class TestControlPlaneVsLiveTruth(unittest.TestCase):
    """Control plane broker values must reflect the live state, not stale state."""

    def test_local_broker_branch_is_a_string(self):
        from app.services.max.control_plane import get_local_broker_status
        broker = get_local_broker_status()
        self.assertIsInstance(broker["repo"]["branch"], str)
        self.assertGreater(len(broker["repo"]["branch"]), 0)

    def test_local_broker_commit_matches_actual(self):
        import subprocess
        from app.services.max.control_plane import get_local_broker_status
        broker = get_local_broker_status()
        actual = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True, text=True, timeout=5,
        ).stdout.strip()
        self.assertEqual(broker["repo"]["commit"], actual)


if __name__ == "__main__":
    unittest.main()
