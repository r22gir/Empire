"""HOTFIX 2026-07-16 — truth-gate hardening batch.

Per-item regression tests for the four hardening items:

  (a) Post-generation quote-number guard
      runtime_truth_failures now extracts every EST-YYYY-NNN from the
      MAX reply text and verifies each one resolves in quotes_v2.
      A fabricated quote_number MUST trigger a hard-block failure.

  (b) Theater-detector shape coverage
      The Phase-A regex matched only `{"tool": "...", ...}`. The
      Anthropic function-call shape `{"name": "...", ...}` slipped
      through. Now covered alongside the OpenAI `{"function": {"name":
      "..."}}` wrapper.

  (c) Hard rule: founder PIN only via the portal approval flow
      The system prompt carries an explicit PIN hard-rule block. The
      runtime truth gate blocks any reply that asks the founder for
      a PIN in chat.

  (d) Outbound email recipient allowlist (enforcement at the executor)
      send_email and send_quote_email now REFUSE any recipient not in
      the allowlist (FOUNDER_EMAIL / WORKROOM_EMAIL / WOODCRAFT_EMAIL
      + MAX_EMAIL_ALLOWED_RECIPIENTS). No tool call may email a
      client / customer address under any circumstances.

Each item is its own test class so the per-item report is clean.
"""
from __future__ import annotations

import os
import re
import socket
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest


_BACKEND = Path(__file__).resolve().parents[1]
import sys
sys.path.insert(0, str(_BACKEND))


# ───────────────────────────────────────────────────────────────────
# (a) Post-generation quote-number guard
# ───────────────────────────────────────────────────────────────────


class TestQuoteNumberGuard:
    """Item (a)."""

    def _insert(self, marker: str) -> str:
        """Insert a canonical quote via the service; return its
        quote_number."""
        from app.services.quote_service import create_quote
        result = create_quote({
            "customer_name": f"TruthGuard {marker}",
            "business_unit": "workroom",
            "line_items": [{"category": "", "description": "x",
                             "quantity": 1, "unit_price": 1.0}],
            "tax_rate": 0.0,
            "project_name": f"truth-guard {marker}",
        })
        return result["quote_number"]

    def test_extracts_quote_numbers_from_text(self, isolated_empire_db):
        from app.services.max.runtime_truth_enforcer import (
            _extract_quote_numbers,
        )
        text = "EST-2026-110 is real. EST-2026-114 was a test. EST-2026-110 again."
        out = _extract_quote_numbers(text)
        assert out == ["EST-2026-110", "EST-2026-114"], (
            f"distinct quote_numbers in source order; got {out}"
        )
        assert _extract_quote_numbers("no quote here") == []
        assert _extract_quote_numbers("") == []

    def test_real_quote_passes_the_guard(self, isolated_empire_db):
        """If MAX's reply quotes a CANONICAL row, the guard does NOT
        fail. The gate is permissive on real numbers."""
        from app.services.quote_service import create_quote
        from app.services.max.runtime_truth_enforcer import (
            runtime_truth_failures,
        )
        qn = self._insert(uuid.uuid4().hex[:6])
        failures, _warns = runtime_truth_failures(
            tool_results=[],
            response_text=f"I updated {qn} just now — total $2,900.",
        )
        quote_failures = [f for f in failures if qn in f]
        assert not quote_failures, (
            f"real quote_number should NOT trip the guard; got {quote_failures}"
        )

    def test_fabricated_quote_blocks_the_response(self, isolated_empire_db):
        """The exact transcript bug. EST-2026-114 (Phase 1 test artifact,
        since deleted) was cited as if it existed. The guard must HARD-
        BLOCK — failures non-empty — so the founder sees a truth-
        failure message instead of a fabricated claim."""
        from app.services.max.runtime_truth_enforcer import (
            runtime_truth_failures,
        )
        # EST-2026-114 was the freshly-deleted Phase 1 test quote. We
        # rely on the conftest having wiped data; if a row by that
        # number exists, the guard passes and the test is wrong.
        from app.services.quote_service import get_quote_by_number
        assert get_quote_by_number("EST-2026-114") is None, (
            "test premise: EST-2026-114 must be absent"
        )
        failures, _ = runtime_truth_failures(
            tool_results=[],
            response_text=(
                "I updated EST-2026-114 — total $1,200. Quote was sent."
            ),
        )
        joined = "\n".join(failures)
        assert "EST-2026-114" in joined
        assert "fabricat" in joined.lower() or "does not exist" in joined.lower(), (
            f"failure must explain the fabrication; got: {joined}"
        )

    def test_enforce_runtime_truth_response_replaces_response(self,
                                                              isolated_empire_db):
        """enforce_runtime_truth_response uses the guard. With a
        fabricated quote_number the response_text is REPLACED by the
        truth-failure message before it's returned to the founder."""
        from app.services.max.runtime_truth_enforcer import (
            enforce_runtime_truth_response,
        )
        new_text, _warns = enforce_runtime_truth_response(
            user_message="update quote",
            response_text="Quote EST-2026-114 is now $1,200.",
            tool_results=[],
        )
        assert "EST-2026-114" in new_text
        assert "have not run" in new_text.lower() or "does not exist" in new_text.lower(), (
            f"response was not replaced by a truth-failure: {new_text!r}"
        )
        assert new_text != "Quote EST-2026-114 is now $1,200.", (
            "fabricated response was passed through verbatim — guard bypassed"
        )

    def test_pin_pattern_does_not_block_clean_response(self,
                                                       isolated_empire_db):
        """Sanity: an unrelated reply must still pass through."""
        from app.services.max.runtime_truth_enforcer import (
            enforce_runtime_truth_response,
        )
        text = "Sure, I pulled the latest balances from ForgeCRM. The customer pays on the 15th."
        new_text, warns = enforce_runtime_truth_response(
            user_message="show balances",
            response_text=text,
            tool_results=[],
        )
        assert new_text == text, "clean text must not be replaced"
        assert "fabricat" not in " ".join(warns).lower()


# ───────────────────────────────────────────────────────────────────
# (b) Theater-detector shape coverage
# ───────────────────────────────────────────────────────────────────


class TestTheaterDetectorShapeCoverage:
    """Item (b). Recognized shapes:
    - {"tool": "<name>", ...}             (Phase A)
    - {"name": "<name>", ...}             (Anthropic) — the bug
    - {"function": {"name": "<name>"}}    (OpenAI)
    """

    def test_phase_a_tool_key_still_fires(self):
        from app.services.max.theater_detector import detect_fabricated_tool_text
        assert detect_fabricated_tool_text(
            'Result: {"tool": "db_query", "table": "leads"}', []
        ) is not None

    def test_anthropic_name_key_now_fires(self):
        """The exact shape from the live weather transcript bug report."""
        from app.services.max.theater_detector import detect_fabricated_tool_text
        text = (
            "Here's the weather data I fetched: "
            '{"name": "mcp__fetch", "parameters": {"url": "x"}}'
        )
        warning = detect_fabricated_tool_text(text, [])
        assert warning is not None, (
            "Anthropic function-call shape must be detected; "
            "this is the bug report — pre-fix it slipped through."
        )
        assert "mcp__fetch" in warning

    def test_openai_function_name_shape_fires(self):
        from app.services.max.theater_detector import detect_fabricated_tool_text
        text = (
            "Tool call: "
            '{"function": {"name": "shell", "arguments": {"cmd": "ls"}}}'
        )
        warning = detect_fabricated_tool_text(text, [])
        assert warning is not None
        assert "shell" in warning

    def test_executed_tool_name_is_not_flagged(self):
        """If MAX legitimately executed a tool, its name in the prose
        is NOT fabrication (e.g. MAX echoes the tool doc)."""
        from app.services.max.theater_detector import detect_fabricated_tool_text
        text = (
            "Result: "
            '{"tool": "send_email", "sent_to": "x@y.com"}'
        )
        # Tool name 'send_email' IS in executed list — must not flag.
        assert detect_fabricated_tool_text(text, ["send_email"]) is None, (
            "executed tool name must not be flagged as fabrication"
        )

    def test_mixed_real_and_fabricated_only_flags_fabricated(self):
        """A response that mentions a real tool (send_email) and a
        fabricated one (db_query) should flag ONLY the fabricated."""
        from app.services.max.theater_detector import detect_fabricated_tool_text
        text = (
            "I sent it: "
            '{"tool": "send_email", "to": "founder@x"} — '
            'and queried: {"tool": "db_query"}'
        )
        warning = detect_fabricated_tool_text(text, ["send_email"])
        assert warning is not None
        assert "db_query" in warning
        assert "send_email" not in (warning or "")

    def test_clean_text_returns_none(self):
        from app.services.max.theater_detector import detect_fabricated_tool_text
        assert detect_fabricated_tool_text("No JSON here.", []) is None
        assert detect_fabricated_tool_text("", []) is None


# ───────────────────────────────────────────────────────────────────
# (c) PIN hard rule + chat-channel guard
# ───────────────────────────────────────────────────────────────────


class TestPinHardRule:
    """Item (c)."""

    def test_system_prompt_contains_pin_hard_rule(self):
        from app.services.max.system_prompt import get_system_prompt
        prompt = get_system_prompt()
        assert "PIN ONLY VIA PORTAL APPROVAL FLOW" in prompt
        # The hard rule section names the PORTAL approval flow surfaces.
        assert "/api/v1/quotes-v2" in prompt
        assert "founder_pin" in prompt

    def test_pin_request_pattern_blocks_response(self, isolated_empire_db):
        """If MAX's reply asks 'what's the pin?' it must be replaced
        by a truth-failure message (gate hard-blocks the response)."""
        from app.services.max.runtime_truth_enforcer import (
            enforce_runtime_truth_response, runtime_truth_failures,
        )
        # Various phrasings the audit called out as fabrications.
        for phrasing in [
            "What's the founder PIN? I'll need it to approve the quote.",
            "please enter your pin",
            "tell me the OTP",
            "send me the verification code",
            "give me the founder pin now",
        ]:
            new_text, _ = enforce_runtime_truth_response(
                user_message="approve",
                response_text=phrasing,
                tool_results=[],
            )
            assert new_text != phrasing, (
                f"phrasing not blocked: {phrasing!r} -> {new_text!r}"
            )
            assert "portal approval flow" in new_text.lower(), (
                f"replacement must point at portal; got {new_text!r}"
            )

    def test_run_with_clean_response_unaffected(self, isolated_empire_db):
        """A clean reply (no quote_numbers, no PIN ask) must NOT be
        replaced. Construct the text so it doesn't trip any of (a)/(b)/(c)."""
        from app.services.max.runtime_truth_enforcer import (
            enforce_runtime_truth_response,
        )
        # Note: no EST-YYYY-NNN and no PIN/OTP phrasing — any of those
        # would (correctly) trip the new guards.
        text = "Sure, I pulled the latest balances from ForgeCRM. The customer pays on the 15th. I'll defer approval to the portal."
        new_text, warns = enforce_runtime_truth_response(
            user_message="check balance",
            response_text=text,
            tool_results=[],
        )
        assert new_text == text, (
            f"clean response must NOT be replaced; got {new_text!r}"
        )

    def test_pin_pattern_finder(self, isolated_empire_db):
        from app.services.max.runtime_truth_enforcer import _find_pin_request
        assert _find_pin_request("What's the founder PIN?") is not None
        assert _find_pin_request("send me the OTP code") is not None
        assert _find_pin_request("share the verification code please") is not None
        # Negative cases
        assert _find_pin_request("What's the password?") is None, (
            "non-PIN phrases must not match"
        )
        assert _find_pin_request("") is None
        assert _find_pin_request(None) is None


# ───────────────────────────────────────────────────────────────────
# (d) Email recipient allowlist (executor-level enforcement)
# ───────────────────────────────────────────────────────────────────


class TestEmailRecipientWhitelist:
    """Item (d). No tool call may email a client / customer address."""

    def test_default_internal_addresses_allowed(self, monkeypatch):
        """FOUNDER_EMAIL / WORKROOM_EMAIL / WOODCRAFT_EMAIL (or their
        hardcoded defaults) are always authorized."""
        from app.services.max.email_recipient_whitelist import (
            authorize_email_recipient,
        )
        # Hardcoded fallbacks are always present.
        for ok in [
            "empirebox2026@gmail.com",
            "workroom@empirebox.store",
            "woodcraft@empirebox.store",
        ]:
            v = authorize_email_recipient(ok)
            assert v["recipient_authorized"], (
                f"{ok!r} must be allowlisted; got {v}"
            )
            assert v["blocked_reason"] is None

    def test_external_address_blocked(self, monkeypatch):
        from app.services.max.email_recipient_whitelist import (
            authorize_email_recipient,
        )
        for blocked in [
            "client@example.com",
            "customer@gmail.com",
            "attacker@evil.com",
            "randomuser@yahoo.com",
        ]:
            v = authorize_email_recipient(blocked)
            assert not v["recipient_authorized"], (
                f"{blocked!r} must be refused; got {v}"
            )
            assert v["blocked_reason"] == "recipient_not_in_whitelist"

    def test_empty_recipient_blocked(self):
        from app.services.max.email_recipient_whitelist import (
            authorize_email_recipient,
        )
        v = authorize_email_recipient("")
        assert not v["recipient_authorized"]
        assert v["blocked_reason"] == "recipient_missing"

    def test_extra_env_address_passes_through(self, monkeypatch):
        """MAX_EMAIL_ALLOWED_RECIPIENTS adds additional ALLOWED
        addresses — but never removes the defaults. Negative test:
        a non-listed address stays blocked."""
        monkeypatch.setenv(
            "MAX_EMAIL_ALLOWED_RECIPIENTS",
            "partner@trusted-vendor.com,backup@ops.com",
        )
        from app.services.max.email_recipient_whitelist import (
            authorize_email_recipient,
        )
        assert authorize_email_recipient("partner@trusted-vendor.com")["recipient_authorized"]
        assert authorize_email_recipient("backup@ops.com")["recipient_authorized"]
        # Still rejected
        v = authorize_email_recipient("attacker@evil.com")
        assert not v["recipient_authorized"]

    def test_send_email_blocks_client_address(self, isolated_empire_db, monkeypatch):
        """End-to-end: the executor's _send_email tool rejects a
        client/custom address with a structured tool result. We use
        unittest.mock to short-circuit the email service so no real
        SMTP is invoked — the test is about the allowlist, not email
        delivery."""
        from app.services.max.tool_executor import execute_tool

        # Patch the email service to a known stub so we don't depend
        # on SMTP env. The allowlist check happens BEFORE svc.send.
        class _StubSMTP:
            def send(self, **kwargs):
                raise AssertionError(
                    "svc.send must NOT be reached for non-allowlisted recipient"
                )

        with patch(
            "app.services.max.email_service.EmailService",
            return_value=_StubSMTP(),
        ):
            res = execute_tool({
                "tool": "send_email",
                "to": "client@example.com",
                "subject": "Estimate attached",
                "body": "<p>See attached.</p>",
            })
        assert not res.success, (
            f"non-allowlisted recipient must fail; got {res}"
        )
        assert "recipient_not_in_whitelist" in res.error, (
            f"error must surface the allowlist refusal; got {res.error!r}"
        )
        # Sensitive default: NOT echoing the address back in the error
        # message — only the structured reason.
        assert "client@example.com" not in res.error, (
            "error message must not leak the rejected address"
        )

    def test_send_email_allows_founder_address(self, isolated_empire_db,
                                                monkeypatch):
        """Positive path: send to a founder address passes the allowlist
        and reaches the email service. We mock the SMTP layer to
        avoid real network I/O."""
        from app.services.max.tool_executor import execute_tool

        called = {"hit": False}

        class _StubSMTP:
            def is_configured(self):
                return True
            def send(self, **kwargs):
                called["hit"] = True
                return True

        with patch(
            "app.services.max.email_service.EmailService",
            return_value=_StubSMTP(),
        ):
            res = execute_tool({
                "tool": "send_email",
                "to": "empirebox2026@gmail.com",
                "subject": "Daily summary",
                "body": "<p>3 quotes sent today.</p>",
            })
        assert res.success, (
            f"founder email must succeed through allowlist; got {res.error!r}"
        )
        assert called["hit"], "allowlist passed but svc.send was never reached"

    def test_send_email_rejects_cc_with_external_address(
            self, isolated_empire_db, monkeypatch):
        """Even if `to=ok`, a `cc=client@x.com` is rejected."""
        from app.services.max.tool_executor import execute_tool

        class _StubSMTP:
            def send(self, **kwargs):
                raise AssertionError("svc.send must not run on bad cc")

        with patch(
            "app.services.max.email_service.EmailService",
            return_value=_StubSMTP(),
        ):
            res = execute_tool({
                "tool": "send_email",
                "to": "empirebox2026@gmail.com",
                "subject": "x",
                "body": "y",
                "cc": "client@example.com,partner@trusted-vendor.com",
            })
        assert not res.success
        assert "cc contains" in res.error


# ───────────────────────────────────────────────────────────────────
# Cross-check: regression — none of the new guards break existing
# (Phase A + HOTFIX 3 + 4 + 5) enforcer tests
# ───────────────────────────────────────────────────────────────────


def test_regression_existing_truth_enforcer_tests_still_pass(isolated_empire_db):
    from app.services.max.runtime_truth_enforcer import (
        enforce_runtime_truth_response,
    )
    # Plain response with proof — must NOT be replaced.
    new_text, warns = enforce_runtime_truth_response(
        user_message="weather",
        response_text="It's 75°F in Hyattsville.",
        tool_results=[{"tool": "web_search",
                       "result": {"answer": "75°F"}}],
    )
    assert new_text.startswith("It's 75°F")
    assert not warns
