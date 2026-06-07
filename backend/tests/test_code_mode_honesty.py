"""Tests for code-mode honesty guardrail.

MAX must distinguish:
    (A) "I can draft code in chat"   (always available, just text)
    (B) "I have verified write access to this repo"  (only via /code-task)

When MAX's text says "I just wrote the file" without a real code-task ID,
the file on disk is unchanged. The guardrail flags this as
UNVERIFIED_WRITE_CLAIM.
"""
from app.services.max.code_mode_honesty import (
    check_code_mode_honesty,
    format_code_mode_banner,
)


def test_bare_write_claim_is_flagged():
    out = check_code_mode_honesty("I just wrote the file for you.")
    assert out["flagged"] is True
    assert out["reason_code"] == "UNVERIFIED_WRITE_CLAIM"
    assert "wrote" in out["matched_claim"].lower()


def test_claim_with_code_task_id_is_not_flagged():
    text = "I wrote the file. Task ID: ct-abc123def."
    out = check_code_mode_honesty(text)
    assert out["flagged"] is False


def test_claim_with_tool_result_code_task_is_not_flagged():
    text = "I just wrote the file for you."
    tool_results = [{"tool": "code_task_runner", "result": {"task_id": "task-xyz789"}}]
    out = check_code_mode_honesty(text, tool_results=tool_results)
    assert out["flagged"] is False


def test_draft_phrase_suppresses_flag():
    text = "Here is a draft of the function — you can paste this into your file."
    out = check_code_mode_honesty(text)
    assert out["flagged"] is False


def test_suggestion_phrase_suppresses_flag():
    text = "You would write something like: def foo(): pass"
    out = check_code_mode_honesty(text)
    assert out["flagged"] is False


def test_no_claim_is_not_flagged():
    out = check_code_mode_honesty("Here is what the file currently looks like:\n```\nfoo\n```")
    assert out["flagged"] is False


def test_empty_response_is_not_flagged():
    out = check_code_mode_honesty("")
    assert out["flagged"] is False


def test_format_banner_when_flagged():
    out = check_code_mode_honesty("I just wrote the file.")
    banner = format_code_mode_banner(out)
    assert "Code-mode honesty guardrail" in banner
    assert "UNVERIFIED_WRITE_CLAIM" in banner


def test_format_banner_when_not_flagged():
    out = check_code_mode_honesty("I can draft code for you.")
    assert format_code_mode_banner(out) == ""


def test_commit_claim_is_flagged():
    out = check_code_mode_honesty("I have committed the change to the repo.")
    assert out["flagged"] is True
    assert out["reason_code"] == "UNVERIFIED_WRITE_CLAIM"


def test_passive_voice_claim_is_flagged():
    """Passive constructions like 'the file has been written' are flagged."""
    out = check_code_mode_honesty("The file has been written to disk.")
    assert out["flagged"] is True
    assert out["reason_code"] == "UNVERIFIED_WRITE_CLAIM"
