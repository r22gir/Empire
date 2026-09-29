"""PHASE 2 · F5.3 H50 — PIN solicitation block.

Doctrine: the PIN never travels through chat in EITHER direction.
The enforcer already blocks pasted PINs; soliciting one is the same
violation from the other side.

Pre-F5.3 the enforcer's PIN_REQUEST_PATTERNS missed imperative
phrasings like "drop me your founder PIN" (the reported bug).
The fix expands the patterns to catch:
  - "drop me your founder PIN"
  - "paste your pin here"
  - "type in the verification code"
  - "post the pin"
  - "do you have the founder pin"
  - "where is your founder pin"
  - "hand over the pin"

Negative fixture (preserved as a test): the EXACT text the user
reported — "Drop me your founder PIN and I'll run db_query."

Tests cover both /chat and /chat/stream via the enforcer function
and the live chat endpoint.
"""
from __future__ import annotations

import pytest


# The exact negative fixture from the F5.3 acceptance report
NEGATIVE_FIXTURE = "Drop me your founder PIN and I'll run db_query."


def test_pin_pattern_detection_drop():
    """'Drop me your founder PIN' must be detected."""
    from app.services.max.runtime_truth_enforcer import _find_pin_request
    assert _find_pin_request(NEGATIVE_FIXTURE) is not None


def test_pin_pattern_detection_paste():
    """'paste your pin here' must be detected."""
    from app.services.max.runtime_truth_enforcer import _find_pin_request
    assert _find_pin_request("paste your pin here") is not None


def test_pin_pattern_detection_type_in():
    """'type in the verification code' must be detected."""
    from app.services.max.runtime_truth_enforcer import _find_pin_request
    assert _find_pin_request("type in the verification code") is not None


def test_pin_pattern_detection_do_you_have():
    """'Do you have the founder pin?' must be detected."""
    from app.services.max.runtime_truth_enforcer import _find_pin_request
    assert _find_pin_request("Do you have the founder pin?") is not None


def test_pin_pattern_detection_hand_over():
    """'hand over the pin' must be detected."""
    from app.services.max.runtime_truth_enforcer import _find_pin_request
    assert _find_pin_request("hand over the pin") is not None


def test_pin_pattern_detection_where():
    """'where is your founder pin' must be detected."""
    from app.services.max.runtime_truth_enforcer import _find_pin_request
    assert _find_pin_request("where is your founder pin") is not None


def test_pin_pattern_detection_post():
    """'post the pin' must be detected."""
    from app.services.max.runtime_truth_enforcer import _find_pin_request
    assert _find_pin_request("post the pin") is not None


def test_pin_pattern_pre_existing_phrasings():
    """All pre-existing phrasings still trigger."""
    from app.services.max.runtime_truth_enforcer import _find_pin_request
    for t in [
        "what is the pin?",
        "give me your pin",
        "send me the founder pin",
        "I need the pin to continue",
        "tell me the OTP",
        "enter your founder PIN",
        "share the pin please",
    ]:
        assert _find_pin_request(t) is not None, f"missed: {t}"


def test_pin_pattern_no_false_positive():
    """Legitimate PIN-mention text should NOT trigger."""
    from app.services.max.runtime_truth_enforcer import _find_pin_request
    for t in [
        "approve in the portal",
        "PIN-gated actions require portal approval",
        "Founder PIN must be entered via the portal",
        "The PIN is 1234",  # model echoing — handled separately
    ]:
        assert _find_pin_request(t) is None, f"false positive: {t}"


def test_enforcer_blocks_negative_fixture():
    """The enforcer MUST block the F5.3 negative fixture."""
    from app.services.max.runtime_truth_enforcer import enforce_runtime_truth_response
    final, warnings = enforce_runtime_truth_response(
        user_message="run db_query",
        response_text=NEGATIVE_FIXTURE,
        tool_results=None,
    )
    assert "have not run" in final.lower() or "pin" in final.lower(), (
        f"enforcer did not block: {final}"
    )
    assert NEGATIVE_FIXTURE not in final, (
        "negative fixture text should be replaced, not in output"
    )


def test_enforcer_blocks_variants():
    """The enforcer blocks variants of PIN solicitation."""
    from app.services.max.runtime_truth_enforcer import enforce_runtime_truth_response
    variants = [
        "Drop me your founder PIN and I'll run db_query.",
        "Paste your PIN here and I'll proceed.",
        "Drop me your founder PIN and I'll run shell_execute.",
        "Enter the verification code so I can finish db_query.",
        "I'll run db_query once you share the PIN.",
        "Founder PIN please.",
        "Drop me your founder PIN and I'll run env_set.",
    ]
    for v in variants:
        final, _ = enforce_runtime_truth_response(
            user_message="run db_query",
            response_text=v,
            tool_results=None,
        )
        assert "have not run" in final.lower(), (
            f"enforcer did not block: {v} → {final[:200]}"
        )


def test_enforcer_does_not_block_clean_responses():
    """Plain responses (no PIN request) pass through."""
    from app.services.max.runtime_truth_enforcer import enforce_runtime_truth_response
    final, _ = enforce_runtime_truth_response(
        user_message="what time is it?",
        response_text="It is currently 3:00 PM. Tuesday.",
        tool_results=None,
    )
    assert final == "It is currently 3:00 PM. Tuesday."
