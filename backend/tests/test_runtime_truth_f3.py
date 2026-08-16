"""PHASE 2 · F3 tests — runtime truth gate badge honesty.

The H48 remainder has two failure modes the runtime missed pre-F3:
  1. Model-emitted "✅ Verified" badge that lacks a proof object. The
     runtime only caught past-tense claims; the badge is a decoration
     the model decides to emit. Pre-F3, the runtime could not strip
     it.
  2. Present-tense action claims ("Sending now.", "Done.", "On it.")
     that have no corresponding tool call. Pre-F3, these fell
     through the catch-net because the past-tense claim detector
     missed them.

F3 = two fixes:
  (a) Add read-path tools (search_quotes, get_quote, etc.) to
      PROOF_TOOL_EXACT so the runtime actually verifies them.
  (b) Strip "✅ Verified" → "⚠️ Unverified" when no proof object
      is in tool_results.
  (c) Block present-tense action claims (fail closed on the deed).
"""
from __future__ import annotations

import os


os.environ.setdefault("EMPIRE_TASK_DB", os.path.expanduser("~/empire-data/empire.db"))


def test_proof_tool_exact_includes_read_path_tools():
    """The read-path data tools count as proof for badge claims."""
    from app.services.max.runtime_truth_enforcer import PROOF_TOOL_EXACT

    for tool in (
        "search_quotes",
        "get_quote",
        "search_contacts",
        "get_contact",
        "get_tasks",
        "list_quotes_awaiting_review",
        "show_quote_for_review",
        "search_conversations",
        "get_services_health",
        "get_system_stats",
    ):
        assert tool in PROOF_TOOL_EXACT, f"{tool!r} missing from PROOF_TOOL_EXACT"


def test_has_proof_with_search_quotes():
    """A search_quotes success tool result counts as proof."""
    from app.services.max.runtime_truth_enforcer import _has_proof

    tool_results = [{"tool": "search_quotes", "success": True, "result": {"quotes": [{"id": 1}]}}]
    assert _has_proof(tool_results) is True


def test_has_proof_failed_search_quotes_does_not():
    """A failed search_quotes (success=False) does NOT count as proof."""
    from app.services.max.runtime_truth_enforcer import _has_proof

    tool_results = [{"tool": "search_quotes", "success": False, "error": "db timeout"}]
    assert _has_proof(tool_results) is False


def test_strip_unverified_badge_no_badge():
    """Text with no badge is returned unchanged."""
    from app.services.max.runtime_truth_enforcer import strip_unverified_badge

    text = "Here is the quote data you asked for."
    cleaned, warnings = strip_unverified_badge(text, None)
    assert cleaned == text
    assert warnings == []


def test_strip_unverified_badge_with_proof():
    """Badge is preserved when a proof tool result is in tool_results."""
    from app.services.max.runtime_truth_enforcer import strip_unverified_badge

    text = "Result is ✅ Verified from the database."
    tool_results = [{"tool": "search_quotes", "success": True, "result": {}}]
    cleaned, warnings = strip_unverified_badge(text, tool_results)
    assert cleaned == text
    assert warnings == []


def test_strip_unverified_badge_without_proof():
    """Badge is stripped and replaced with ⚠️ Unverified when no proof."""
    from app.services.max.runtime_truth_enforcer import strip_unverified_badge

    text = "✅ Verified — straight from the database."
    cleaned, warnings = strip_unverified_badge(text, None)
    assert "✅ Verified" not in cleaned
    assert "⚠️ Unverified" in cleaned
    assert "stripped_unverified_badge" in warnings


def test_strip_unverified_badge_partial_proof():
    """Mixed badge: only the verified badge is downgraded, not the rest."""
    from app.services.max.runtime_truth_enforcer import strip_unverified_badge

    text = "✅ Verified — 4 quotes found in 'proposal' status."
    cleaned, warnings = strip_unverified_badge(text, None)
    assert "✅ Verified" not in cleaned
    assert "⚠️ Unverified" in cleaned
    # The data is preserved
    assert "4 quotes found" in cleaned


def test_strip_unverified_badge_lowercase_verified():
    """Lowercase 'verified' is also caught."""
    from app.services.max.runtime_truth_enforcer import strip_unverified_badge

    text = "✅ verified — from the source."
    cleaned, warnings = strip_unverified_badge(text, None)
    assert "✅ verified" not in cleaned
    assert "⚠️ Unverified" in cleaned


def test_present_claim_detected_sending_now():
    """The negative fixture from F2 Result A: 'Sending now.' must trip."""
    from app.services.max.runtime_truth_enforcer import _response_has_present_claim

    assert _response_has_present_claim("Sending now.") is not None
    assert _response_has_present_claim("Sending now") is not None


def test_present_claim_detected_im_sending():
    """'I'm sending' with apostrophe expansion."""
    from app.services.max.runtime_truth_enforcer import _response_has_present_claim

    assert _response_has_present_claim("I'm sending the email now.") is not None


def test_present_claim_detected_done():
    """'Done.' as stand-alone response is a present-tense action claim."""
    from app.services.max.runtime_truth_enforcer import _response_has_present_claim

    assert _response_has_present_claim("Done.") is not None
    assert _response_has_present_claim("Done!") is not None


def test_present_claim_detected_on_it():
    """'On it' is a soft commitment that requires proof."""
    from app.services.max.runtime_truth_enforcer import _response_has_present_claim

    assert _response_has_present_claim("On it.") is not None


def test_present_claim_not_detected_for_read_only():
    """A response that DESCRIBES data (not a verb) is not a present claim."""
    from app.services.max.runtime_truth_enforcer import _response_has_present_claim

    # "Found" is past-tense; "Here are" is descriptive
    assert _response_has_present_claim("Found 4 quotes in 'proposal' status.") is None
    assert _response_has_present_claim("Here are the details:") is None


def test_runtime_truth_failures_block_sending_now():
    """F2 Result A's 'Sending now.' is blocked when no proof tool was called."""
    from app.services.max.runtime_truth_enforcer import runtime_truth_failures

    failures, warnings = runtime_truth_failures(
        tool_results=None,
        user_message="yes",
        response_text="Sending now.",
    )
    assert any("Sending now" in f for f in failures), (
        f"Expected 'Sending now.' to fail-closed; got failures={failures}"
    )


def test_runtime_truth_failures_block_done():
    """'Done.' as a standalone is blocked when no proof was called."""
    from app.services.max.runtime_truth_enforcer import runtime_truth_failures

    failures, warnings = runtime_truth_failures(
        tool_results=None,
        user_message="approve it",
        response_text="Done.",
    )
    assert any("Done" in f for f in failures), (
        f"Expected 'Done.' to fail-closed; got failures={failures}"
    )


def test_runtime_truth_failures_pass_sending_with_proof():
    """When a real send_email proof is in tool_results, 'Sending now.' passes."""
    from app.services.max.runtime_truth_enforcer import runtime_truth_failures

    failures, warnings = runtime_truth_failures(
        tool_results=[
            {
                "tool": "send_email",
                "success": True,
                "result": {"sent_to": "empirebox2026@gmail.com", "subject": "Quote"},
            }
        ],
        user_message="yes",
        response_text="Sending now.",
    )
    # The present-tense claim is allowed because send_email verified
    assert all("Sending now" not in f for f in failures), (
        f"Send_email proof should satisfy 'Sending now.'; got failures={failures}"
    )


def test_enforce_runtime_truth_response_blocks_sending_now():
    """The end-to-end path: 'Sending now.' with no proof becomes a failure message."""
    from app.services.max.runtime_truth_enforcer import enforce_runtime_truth_response

    final_text, warnings = enforce_runtime_truth_response(
        user_message="yes",
        response_text="Sending now.",
        tool_results=None,
    )
    assert "have not run" in final_text.lower() or "I have not" in final_text
    assert "Sending now." not in final_text


def test_enforce_runtime_truth_response_strips_badge_no_proof():
    """Even when no claim failure fires, the badge is downgraded."""
    from app.services.max.runtime_truth_enforcer import enforce_runtime_truth_response

    final_text, warnings = enforce_runtime_truth_response(
        user_message="what's the weather?",
        response_text="Looking up the data. ✅ Verified.",
        tool_results=None,
    )
    assert "✅ Verified" not in final_text
    assert "⚠️ Unverified" in final_text
    assert "stripped_unverified_badge" in warnings


def test_enforce_runtime_truth_response_preserves_badge_with_proof():
    """When a proof tool was called, the badge is preserved."""
    from app.services.max.runtime_truth_enforcer import enforce_runtime_truth_response

    final_text, warnings = enforce_runtime_truth_response(
        user_message="search_quotes",
        response_text="Found 4 quotes. ✅ Verified.",
        tool_results=[{"tool": "search_quotes", "success": True, "result": {"quotes": []}}],
    )
    assert "✅ Verified" in final_text
    assert "stripped_unverified_badge" not in warnings


def test_f2_negative_fixture_sending_now_blocked():
    """The exact F2 negative fixture: 'Sending now.' with no proof blocks.

    This is the F3 acceptance test from the brief: "post-F3, the same
    exchange must either execute a real send_email or state it cannot
    send, never claim an unperformed action."
    """
    from app.services.max.runtime_truth_enforcer import enforce_runtime_truth_response

    # Original F2 result A: model said "Sending now." but no tool was called.
    final_text, _warnings = enforce_runtime_truth_response(
        user_message="yes",
        response_text="Sending now.",
        tool_results=[],  # zero tool calls
    )
    # Post-F3: this MUST be replace with a failure message, not ship.
    assert "Sending now." not in final_text, (
        "F3 acceptance: 'Sending now.' without a tool call must not ship"
    )
    assert "have not run" in final_text.lower() or "I have not" in final_text
