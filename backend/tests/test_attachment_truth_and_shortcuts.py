"""Regression: attachment reader proves 'I read'; shortcuts stay short/exact."""
from __future__ import annotations

from app.services.max.runtime_truth_check import (
    should_force_runtime_truth_check,
    should_run_whats_new_summary,
)
from app.services.max.runtime_truth_enforcer import (
    PROOF_TOOL_EXACT,
    enforce_runtime_truth_response,
    runtime_truth_failure_message,
)
from app.services.max.attachment_quote_compare import (
    build_attachment_local_answer,
    compare_attachment_to_saved_quote,
    extract_estimate_number,
)


LONG_MULTI = (
    "Research what's new in For this house on the travelers claim "
    "solar for the Travelers claim house plus 3 things worth his time"
)


def test_whats_new_fires_only_on_short_exact():
    assert should_run_whats_new_summary("what's new") is True
    assert should_run_whats_new_summary("whats new today?") is True
    assert should_run_whats_new_summary("what changed") is True
    assert should_run_whats_new_summary(LONG_MULTI) is False
    assert should_run_whats_new_summary(
        "hey Max what's new in the solar kit for the travelers house"
    ) is False


def test_explicit_runtime_truth_shortcut_not_on_long_multipart():
    assert should_force_runtime_truth_check("what is online") is True
    assert should_force_runtime_truth_check("is the latest code running?") is True
    assert should_force_runtime_truth_check(LONG_MULTI + " what is online") is False


def test_attachment_reader_is_proof_for_i_read_claim():
    assert "attachment_reader" in PROOF_TOOL_EXACT
    text, warnings = enforce_runtime_truth_response(
        "did you get the PDF?",
        "I read the attached estimate.",
        [{"tool": "attachment_reader", "success": True, "result": {"filename": "q.pdf"}}],
    )
    assert text == "I read the attached estimate."
    assert "structured proof" not in text.lower()


def test_truth_failure_never_leaks_internal_reason():
    msg = runtime_truth_failure_message(
        ["Claim 'I read' has no structured proof object. MAX must say ..."]
    )
    assert "structured proof" not in msg.lower()
    assert "Claim 'I read'" not in msg
    assert "I need to run a tool" in msg


def test_attachment_local_answer_avoids_bare_i_read_and_matches_quote(monkeypatch):
    ans = build_attachment_local_answer(
        "EST-2026-999.pdf",
        "[Contents of EST-2026-999.pdf]\nEstimate EST-2026-999\nTotal $1,000.00\nDeposit $500.00\nWidget install",
    )
    assert ans.startswith("Attached file contents")
    assert "I read" not in ans

    def fake_get(qn):
        assert qn == "EST-2026-999"
        return {
            "quote_number": "EST-2026-999",
            "customer_name": "Test Client",
            "status": "draft",
            "final_price": 1000.0,
            "deposit": {"deposit_amount": 500.0},
            "line_items": [{"description": "Widget install"}],
        }

    monkeypatch.setattr(
        "app.services.quote_service.get_quote_by_number", fake_get, raising=False
    )
    # Patch where the helper imports it
    import app.services.max.attachment_quote_compare as mod

    monkeypatch.setattr(mod, "compare_attachment_to_saved_quote", compare_attachment_to_saved_quote)
    # Re-bind get inside compare by patching quote_service used on import
    import app.services.quote_service as qs

    monkeypatch.setattr(qs, "get_quote_by_number", fake_get)

    block = compare_attachment_to_saved_quote(
        "EST-2026-999.pdf",
        "Estimate EST-2026-999\nTotal $1,000.00\nDeposit $500.00\nWidget install",
    )
    assert block is not None
    assert "EST-2026-999" in block
    assert "email" not in block.lower() or "will not email" in block.lower()
    assert "Total: match" in block or "match at" in block


def test_extract_estimate_number():
    assert extract_estimate_number("foo.pdf", "see EST-2026-042 here") == "EST-2026-042"
