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
    but did not. The runtime_truth_enforcer module already had the
    'verification failed' pattern. These tests verify that the enforcer
    still works correctly.

    The 2026-06-15 proof-receipt enforcement patch added generic claim
    detection: past-tense operational claims (e.g., "I checked OpenClaw")
    must be backed by a structured proof object in tool_results. Future-
    tense / conditional / safe phrases (e.g., "I will check", "I have
    not run that yet") are explicitly allowed.
    """

    def test_runtime_truth_enforcer_fails_on_empty_tool_results(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        # With a past-tense claim in the response and no tool results,
        # we MUST get a truth failure. This is the core 2026-06-15 fix.
        failures = runtime_truth_failures(
            [],
            user_message="probe OpenClaw",
            response_text="I checked OpenClaw and the queue is healthy.",
        )
        self.assertTrue(
            len(failures) > 0,
            "Empty tool_results + past-tense claim MUST produce a truth failure",
        )

    def test_empty_tool_results_no_claim_passes(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        # If the response has NO past-tense claim, no failure is needed
        # (the tool just wasn't called, but MAX didn't claim it was).
        failures = runtime_truth_failures(
            [],
            user_message="probe OpenClaw",
            response_text="I have not run that yet. If you want, I can check after approval.",
        )
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

    # ------------------------------------------------------------------
    # NEW: 2026-06-15 proof-receipt enforcement tests
    # ------------------------------------------------------------------

    def test_claim_I_checked_with_no_proof_fails(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        # "I checked OpenClaw" with no proof object MUST fail.
        failures = runtime_truth_failures(
            [],
            user_message="what is the queue?",
            response_text="I checked OpenClaw and it has 72 tasks queued.",
        )
        self.assertTrue(len(failures) > 0)
        # The failure must mention the claim phrase or the lack of proof.
        joined = " ".join(failures).lower()
        self.assertTrue(
            "i checked" in joined or "proof" in joined,
            f"failure should mention the claim or lack of proof, got: {failures}",
        )

    def test_claim_I_probed_with_no_proof_fails(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        failures = runtime_truth_failures(
            [],
            user_message="probe localhost",
            response_text="I probed localhost and the backend is healthy.",
        )
        self.assertTrue(len(failures) > 0)

    def test_claim_I_searched_with_no_proof_fails(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        failures = runtime_truth_failures(
            [],
            user_message="search the web",
            response_text="I searched the web and found relevant articles.",
        )
        self.assertTrue(len(failures) > 0)

    def test_claim_I_confirmed_with_no_proof_fails(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        failures = runtime_truth_failures(
            [],
            user_message="is the queue healthy?",
            response_text="I confirmed the queue is healthy.",
        )
        self.assertTrue(len(failures) > 0)

    def test_claim_I_verified_with_no_proof_fails(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        failures = runtime_truth_failures(
            [],
            user_message="verify the build",
            response_text="I verified the build is correct.",
        )
        self.assertTrue(len(failures) > 0)

    def test_claim_I_fetched_with_no_proof_fails(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        failures = runtime_truth_failures(
            [],
            user_message="fetch the file",
            response_text="I fetched the file from the repository.",
        )
        self.assertTrue(len(failures) > 0)

    def test_claim_I_read_with_no_proof_fails(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        failures = runtime_truth_failures(
            [],
            user_message="read the file",
            response_text="I read the file and it contains the secret.",
        )
        self.assertTrue(len(failures) > 0)

    def test_claim_I_called_with_no_proof_fails(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        failures = runtime_truth_failures(
            [],
            user_message="call the api",
            response_text="I called the API and got a 200 response.",
        )
        self.assertTrue(len(failures) > 0)

    def test_claim_I_inspected_with_no_proof_fails(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        failures = runtime_truth_failures(
            [],
            user_message="inspect the logs",
            response_text="I inspected the logs and found no errors.",
        )
        self.assertTrue(len(failures) > 0)

    def test_claim_I_looked_up_with_no_proof_fails(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        failures = runtime_truth_failures(
            [],
            user_message="look up the user",
            response_text="I looked up the user and they are active.",
        )
        self.assertTrue(len(failures) > 0)

    def test_claim_I_ran_with_no_proof_fails(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        failures = runtime_truth_failures(
            [],
            user_message="run the script",
            response_text="I ran the script and it completed successfully.",
        )
        self.assertTrue(len(failures) > 0)

    def test_claim_with_valid_proof_passes(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        # Same claim as the failing test, but with a valid proof object.
        # The proof tool name must be a known proof prefix.
        tool_results = [
            {"tool": "openclaw_status", "success": True, "result": {"queue_stats": {"queued": 72}}}
        ]
        failures = runtime_truth_failures(
            tool_results,
            user_message="what is the queue?",
            response_text="I checked OpenClaw and it has 72 tasks queued.",
        )
        self.assertEqual(failures, [])

    def test_safe_future_tense_phrases_pass(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        # Future-tense / conditional / safe phrases must NOT fail.
        safe_responses = [
            "I have not run that yet. I need a real tool result.",
            "I can check after approval.",
            "I will run the script when you say go.",
            "I would need to see the file first.",
            "I have not checked the queue yet.",
            "I haven't run that yet.",
            "I can probe the system if you approve.",
        ]
        for response_text in safe_responses:
            failures = runtime_truth_failures(
                [],
                user_message="check the queue",
                response_text=response_text,
            )
            self.assertEqual(
                failures, [],
                f"Safe phrase should not fail: {response_text!r} got {failures}",
            )

    def test_response_with_no_claim_phrase_passes(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        # A response that makes no operational claim must not fail.
        # (This is the natural case for non-tool responses.)
        safe_responses = [
            "Here is the onboarding plan you asked for.",
            "The MAX system is designed to coordinate chat, voice, image, and document analysis.",
            "I am MAX, your command center. How can I help?",
        ]
        for response_text in safe_responses:
            failures = runtime_truth_failures(
                [],
                user_message="tell me about MAX",
                response_text=response_text,
            )
            self.assertEqual(
                failures, [],
                f"Non-claim response should not fail: {response_text!r} got {failures}",
            )

    def test_enforce_runtime_truth_response_replaces_claim(self):
        from app.services.max.runtime_truth_enforcer import enforce_runtime_truth_response
        # If the response has an unsupported claim, the function MUST
        # replace it with a truth-failure message.
        original = "I checked OpenClaw and the queue has 72 tasks."
        result = enforce_runtime_truth_response("what is the queue?", original, [])
        self.assertNotEqual(result, original)
        # The result must contain a truth-failure indicator.
        self.assertTrue(
            "have not run" in result.lower() or "verification failed" in result.lower(),
            f"result should be a truth-failure message: {result!r}",
        )

    def test_enforce_runtime_truth_response_passes_valid_claim(self):
        from app.services.max.runtime_truth_enforcer import enforce_runtime_truth_response
        # A claim with valid proof must be passed through unchanged.
        original = "I checked OpenClaw and it has 72 tasks queued."
        tool_results = [
            {"tool": "openclaw_status", "success": True, "result": {"queue_stats": {"queued": 72}}}
        ]
        result = enforce_runtime_truth_response("what is the queue?", original, tool_results)
        self.assertEqual(result, original)

    def test_enforce_runtime_truth_response_passes_safe_phrase(self):
        from app.services.max.runtime_truth_enforcer import enforce_runtime_truth_response
        # Future-tense / safe phrases must pass through unchanged.
        original = "I have not run that yet. I can check after approval."
        result = enforce_runtime_truth_response("what is the queue?", original, [])
        self.assertEqual(result, original)

    def test_failed_tool_result_is_not_proof(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        # A tool result with success=False is NOT proof (failed call).
        tool_results = [
            {"tool": "openclaw_status", "success": False, "error": "timeout"}
        ]
        failures = runtime_truth_failures(
            tool_results,
            user_message="check the queue",
            response_text="I checked OpenClaw and it has 72 tasks queued.",
        )
        # Should fail: the only tool result was a failure, not proof.
        self.assertTrue(len(failures) > 0)

    def test_old_api_no_response_text_still_works(self):
        # Backwards compatibility: calling runtime_truth_failures WITHOUT
        # response_text (the old signature) should still work — it just
        # only checks for tool verification failures.
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        # With no response_text, no claim check is performed.
        failures = runtime_truth_failures(
            [],
            user_message="check",
        )
        self.assertEqual(failures, [])

    def test_old_api_with_response_text_enforces_claim(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        # With response_text, the new claim detection fires.
        failures = runtime_truth_failures(
            [],
            user_message="check",
            response_text="I checked it.",
        )
        self.assertTrue(len(failures) > 0)

    def test_should_halt_after_tool_failure_with_claim(self):
        from app.services.max.runtime_truth_enforcer import should_halt_after_tool_failure
        # The halt function should also detect the unsupported claim.
        self.assertTrue(
            should_halt_after_tool_failure(
                [],
                user_message="check",
                response_text="I checked it.",
            )
        )


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
