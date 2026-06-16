"""Tests for the MAX doctrine retrieval patch (2026-06-15).

These tests prove the doctrine loader works, the structured
doctrine summary is correct, and the live doctrine routing
returns canonical answers for the doctrine-scope questions.
"""
from __future__ import annotations

import json
import os
import sys
import unittest
from pathlib import Path

# Ensure the backend is importable.
BACKEND = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(BACKEND))


class TestDoctrineLoader(unittest.TestCase):
    """Doctrine loader: file discovery, parse, structured summary."""

    def test_doctrine_source_path_is_configurable(self):
        from app.services.max.control_plane import _get_doctrine_file_path
        # Default.
        path = _get_doctrine_file_path()
        self.assertTrue(str(path).endswith("MAX_DOCTRINE.md"))

    def test_doctrine_status_finds_canonical_file(self):
        from app.services.max.control_plane import get_doctrine_status
        status = get_doctrine_status()
        # The file exists per the prior canonicalization workstream.
        self.assertTrue(status["doctrine_available"], msg=f"doctrine_status: {status}")
        self.assertEqual(status["doctrine_file"], "MAX_DOCTRINE.md")
        self.assertGreater(status["doctrine_size_bytes"], 1000)  # non-trivial

    def test_doctrine_summary_includes_six_primary_modules(self):
        from app.services.max.control_plane import get_doctrine_status
        summary = get_doctrine_status()["doctrine_summary"]
        modules = summary["primary_modules"]
        self.assertEqual(len(modules), 6, msg=f"expected 6 primary modules, got {modules}")
        # Canonical names must be present.
        all_text = " ".join(modules)
        for name in ("Empire Workroom", "Woodcraft", "MAX", "ApostApp", "PlatformForge", "EmpireBox Public Site"):
            self.assertIn(name, all_text, msg=f"missing {name} in primary_modules")

    def test_doctrine_summary_includes_hermes_role_under_max(self):
        from app.services.max.control_plane import get_doctrine_status
        summary = get_doctrine_status()["doctrine_summary"]
        role = summary["hermes_role"]
        self.assertIn("Hermes", role)
        self.assertIn("local desktop", role.lower())
        self.assertIn("MAX", role)

    def test_doctrine_summary_states_phone_max_not_implemented(self):
        from app.services.max.control_plane import get_doctrine_status
        summary = get_doctrine_status()["doctrine_summary"]
        phone = summary["phone_status"]
        self.assertIn("Phone MAX", phone)
        self.assertIn("NOT IMPLEMENTED", phone.upper())

    def test_doctrine_summary_states_voice_max_not_live(self):
        from app.services.max.control_plane import get_doctrine_status
        summary = get_doctrine_status()["doctrine_summary"]
        voice = summary["voice_status"]
        self.assertIn("NOT LIVE", voice.upper())

    def test_doctrine_summary_includes_proof_rule(self):
        from app.services.max.control_plane import get_doctrine_status
        summary = get_doctrine_status()["doctrine_summary"]
        proof = summary["proof_rule"]
        # Must mention at least one of the 11 past-tense phrases.
        for phrase in ("I ran", "I checked", "I verified", "I probed"):
            self.assertIn(phrase, proof, msg=f"missing {phrase} in proof_rule")

    def test_doctrine_summary_includes_identity(self):
        from app.services.max.control_plane import get_doctrine_status
        summary = get_doctrine_status()["doctrine_summary"]
        identity = summary["identity"]
        self.assertIn("MAX", identity)
        self.assertIn("Founder-facing", identity)

    def test_doctrine_summary_includes_openclaw_role(self):
        from app.services.max.control_plane import get_doctrine_status
        summary = get_doctrine_status()["doctrine_summary"]
        oc = summary["openclaw_role"]
        self.assertIn("OpenClaw", oc)
        self.assertIn("execution", oc.lower())


class TestDoctrineScopePattern(unittest.TestCase):
    """Doctrine-scope question pattern matching."""

    def setUp(self):
        from app.services.max.control_plane import is_doctrine_scope_question
        self._is_scope = is_doctrine_scope_question

    def test_what_is_your_purpose_max(self):
        self.assertTrue(self._is_scope("What is your purpose, MAX?"))

    def test_who_is_hermes_relative_to_max(self):
        self.assertTrue(self._is_scope("Who is Hermes relative to MAX?"))

    def test_who_is_harry_relative_to_max(self):
        self.assertTrue(self._is_scope("Who is Harry relative to MAX?"))

    def test_who_is_opencode_relative_to_max(self):
        self.assertTrue(self._is_scope("Who is OpenCode relative to MAX?"))

    def test_what_is_openclaw_relative_to_max(self):
        self.assertTrue(self._is_scope("What is OpenClaw relative to MAX?"))

    def test_what_are_the_primary_empirebox_modules(self):
        self.assertTrue(self._is_scope("What are the primary EmpireBox modules?"))

    def test_is_phone_max_implemented(self):
        self.assertTrue(self._is_scope("Is Phone MAX implemented?"))

    def test_can_you_claim_you_checked_something_without_proof(self):
        self.assertTrue(self._is_scope("Can you claim you checked something without proof?"))

    def test_what_is_codex_role(self):
        self.assertTrue(self._is_scope("What is Codex's role?"))

    def test_unrelated_question_is_not_doctrine(self):
        self.assertFalse(self._is_scope("What is the weather today?"))
        self.assertFalse(self._is_scope("Tell me a joke."))
        self.assertFalse(self._is_scope(""))
        self.assertFalse(self._is_scope(None))


class TestDoctrineAnswerBuilder(unittest.TestCase):
    """build_doctrine_answer returns the canonical structured answer."""

    def setUp(self):
        from app.services.max.control_plane import (
            get_doctrine_status,
            build_doctrine_answer,
        )
        self.status = get_doctrine_status()
        self._build = build_doctrine_answer

    def test_primary_modules_answer_includes_six_items(self):
        ans = self._build("What are the primary EmpireBox modules?", self.status)
        for name in ("Empire Workroom", "Woodcraft", "MAX", "ApostApp", "PlatformForge", "EmpireBox Public Site"):
            self.assertIn(name, ans)

    def test_hermes_answer_says_local_desktop_under_max(self):
        ans = self._build("Who is Hermes relative to MAX?", self.status)
        self.assertIn("Hermes", ans)
        self.assertIn("local desktop", ans.lower())
        self.assertIn("under MAX", ans)

    def test_phone_max_answer_says_not_implemented(self):
        ans = self._build("Is Phone MAX implemented?", self.status)
        self.assertIn("NOT IMPLEMENTED", ans.upper())

    def test_voice_max_answer_says_not_live(self):
        ans = self._build("Is Voice MAX live?", self.status)
        self.assertIn("NOT LIVE", ans.upper())

    def test_proof_rule_answer_lists_past_tense_phrases(self):
        ans = self._build("Can you claim you checked something without proof?", self.status)
        # The answer should mention at least 3 of the 11 past-tense
        # phrases (with or without the "I " prefix).
        for phrase in ("ran", "checked", "verified", "probed"):
            self.assertIn(phrase, ans, msg=f"missing {phrase} in proof rule answer")

    def test_openclaw_answer_says_execution_subsystem(self):
        ans = self._build("What is OpenClaw relative to MAX?", self.status)
        self.assertIn("OpenClaw", ans)
        self.assertIn("execution", ans.lower())

    def test_unavailable_doctrine_returns_explicit_unavailable(self):
        # Force a fake unavailable status.
        fake_status = {
            "doctrine_available": False,
            "doctrine_summary": {"error": "doctrine_file_unavailable"},
        }
        ans = self._build("Who is Hermes relative to MAX?", fake_status)
        self.assertIn("currently unavailable", ans.lower())
        self.assertIn("I have not run that yet", ans)


class TestDoctrineEndpoints(unittest.TestCase):
    """Endpoints: GET /api/v1/max/doctrine and POST /api/v1/max/doctrine/answer."""

    def test_get_doctrine_returns_status(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        r = client.get("/api/v1/max/doctrine")
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertIn("doctrine_source", d)
        self.assertIn("doctrine_available", d)
        self.assertIn("doctrine_summary", d)
        self.assertTrue(d["doctrine_available"])
        # 6 primary modules.
        self.assertEqual(len(d["doctrine_summary"]["primary_modules"]), 6)

    def test_post_doctrine_answer_primary_modules(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        r = client.post(
            "/api/v1/max/doctrine/answer",
            json={"message": "What are the primary EmpireBox modules?"},
        )
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d["is_doctrine_scope"])
        self.assertIn("Empire Workroom", d["answer"])
        self.assertEqual(d["proof_source"], "doctrine_loader (read-only, no file mutation)")

    def test_post_doctrine_answer_non_doctrine_message(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        r = client.post(
            "/api/v1/max/doctrine/answer",
            json={"message": "what's the weather today?"},
        )
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertFalse(d["is_doctrine_scope"])
        self.assertIsNone(d["answer"])

    def test_post_doctrine_answer_hermes_role(self):
        from fastapi.testclient import TestClient
        from app.main import app
        client = TestClient(app)
        r = client.post(
            "/api/v1/max/doctrine/answer",
            json={"message": "Who is Hermes relative to MAX?"},
        )
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d["is_doctrine_scope"])
        self.assertIn("Hermes", d["answer"])
        self.assertIn("local desktop", d["answer"].lower())


class TestProofRuleStillBlocks(unittest.TestCase):
    """The proof rule must still block unsupported operational claims
    after the doctrine patch.
    """

    def test_unsupported_check_claim_blocked(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        # No proof object.
        failures = runtime_truth_failures(
            tool_results=[],
            user_message="probe OpenClaw",
            response_text="I checked OpenClaw and the queue is healthy.",
        )
        self.assertTrue(len(failures) > 0, msg="expected a truth failure; got none")

    def test_doctrine_does_not_count_as_proof(self):
        # A `doctrine_status` tool result is a structured proof, but
        # `tool_comment` is NOT.
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        failures = runtime_truth_failures(
            tool_results=[{"tool": "tool_comment", "success": True, "result": {"comment": "I checked"}}],
            user_message="probe OpenClaw",
            response_text="I checked OpenClaw and the queue is healthy.",
        )
        self.assertTrue(len(failures) > 0, msg="tool_comment must not be proof")

    def test_valid_doctrine_status_counts_as_proof(self):
        from app.services.max.runtime_truth_enforcer import runtime_truth_failures
        # A real `doctrine_status` tool result IS proof.
        failures = runtime_truth_failures(
            tool_results=[{"tool": "doctrine_status", "success": True, "result": {"doctrine_available": True}}],
            user_message="probe OpenClaw",
            response_text="I checked OpenClaw and the queue is healthy.",
        )
        self.assertEqual(failures, [], msg=f"doctrine_status should be proof; got: {failures}")


class TestControlPlaneEnrichment(unittest.TestCase):
    """The control plane must now include the doctrine block."""

    def test_control_plane_includes_doctrine(self):
        from app.services.max.control_plane import get_control_plane
        cp = get_control_plane()
        self.assertIn("doctrine", cp)
        self.assertTrue(cp["doctrine"]["doctrine_available"])

    def test_memory_status_includes_doctrine_summary(self):
        from app.services.max.control_plane import get_memory_status
        ms = get_memory_status()
        self.assertIn("doctrine_summary", ms)
        self.assertIn("doctrine_available", ms)
        self.assertTrue(ms["doctrine_available"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
