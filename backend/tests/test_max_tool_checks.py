"""Code-level sanity checks on Max tool results (Loud Failures, Quiet Failures).

Each check has a passing case and a failing case. Failed checks must
escalate to Rafael and must not silently proceed. Measurement copy is
fractions only — never decimal inches.
"""
from __future__ import annotations

import re

import pytest

from app.services.max.tool_checks import (
    FABRIC_CUT_ALLOWANCE,
    FAILED_CHECK,
    attach_cut_sheet,
    check_deposit_balance,
    check_fabric_cuts,
    check_quickbooks_totals,
    expected_fabric_cut,
    fabric_allowance_for_foam,
    format_measure,
    gate_tool_result,
    user_facing_failure_text,
    validate_tool_payload,
)
from app.services.max.tool_executor import ToolResult, run_checked_handler

_DECIMAL_INCH = re.compile(r"\d+\.\d+\s*[\"″]")


def _assert_fraction_copy(*texts: str) -> None:
    for text in texts:
        hit = _DECIMAL_INCH.search(text or "")
        assert hit is None, f"decimal inch {hit.group(0)!r} in {text!r}"


# ── 1. QuickBooks / line-item totals ────────────────────────────────


def test_quickbooks_totals_pass_when_lines_sum_to_total():
    failures = check_quickbooks_totals({
        "TotalAmt": 150.00,
        "Line": [
            {"Amount": 50.00, "DetailType": "SalesItemLineDetail"},
            {"Amount": 100.00, "DetailType": "SalesItemLineDetail"},
        ],
    })
    assert failures == []


def test_quickbooks_totals_fail_when_total_is_quietly_wrong():
    failures = check_quickbooks_totals({
        "TotalAmt": 175.00,  # believable, but 50+100=150
        "Line": [
            {"Amount": 50.00, "DetailType": "SalesItemLineDetail"},
            {"Amount": 100.00, "DetailType": "SalesItemLineDetail"},
        ],
    })
    assert len(failures) == 1
    assert failures[0].check == "quickbooks_totals"
    assert failures[0].expected == 150.00
    assert failures[0].actual == 175.00


def test_quickbooks_totals_allow_one_cent_rounding():
    failures = check_quickbooks_totals({
        "total": 10.01,
        "line_items": [
            {"amount": 3.335},
            {"amount": 3.335},
            {"amount": 3.34},
        ],
    })
    assert failures == []


def test_quickbooks_query_response_invoice_is_checked():
    payload = {
        "QueryResponse": {
            "Invoice": [{
                "TotalAmt": 90.00,
                "Line": [
                    {"Amount": 40.00, "DetailType": "SalesItemLineDetail"},
                    {"Amount": 50.00, "DetailType": "SalesItemLineDetail"},
                ],
            }]
        }
    }
    assert validate_tool_payload(payload, tool_name="quickbooks_read").passed
    payload["QueryResponse"]["Invoice"][0]["TotalAmt"] = 99.00
    check = validate_tool_payload(payload, tool_name="quickbooks_read")
    assert not check.passed
    assert any(f.check == "quickbooks_totals" for f in check.failures)


def test_invoice_deposit_due_plus_balance_due():
    assert check_deposit_balance({
        "total": 800.00,
        "deposit_due": 400.00,
        "balance_due": 400.00,
    }) == []
    failures = check_deposit_balance({
        "total": 800.00,
        "deposit_due": 250.00,
        "balance_due": 400.00,
    })
    assert failures[0].check == "deposit_balance"


def test_quickbooks_totals_add_tax_when_present():
    failures = check_quickbooks_totals({
        "TotalAmt": 108.00,
        "TxnTaxDetail": {"TotalTax": 8.00},
        "Line": [{"Amount": 100.00, "DetailType": "SalesItemLineDetail"}],
    })
    assert failures == []
    failures = check_quickbooks_totals({
        "TotalAmt": 100.00,
        "tax_amount": 8.00,
        "line_items": [{"total": 100.00}],
    })
    assert failures[0].check == "quickbooks_totals"


# ── 2. Deposit + balance == total ───────────────────────────────────


def test_deposit_balance_pass_on_half_and_half_estimate():
    failures = check_deposit_balance({
        "total": 4759.96,
        "deposit": 2379.98,
        "balance": 2379.98,
    })
    assert failures == []


def test_deposit_balance_fail_when_deposit_is_quietly_wrong():
    failures = check_deposit_balance({
        "total": 1000.00,
        "deposit": 400.00,
        "balance": 500.00,  # 900 != 1000
    })
    assert len(failures) == 1
    assert failures[0].check == "deposit_balance"
    assert failures[0].expected == 1000.00
    assert failures[0].actual == 900.00


def test_deposit_required_is_not_treated_as_the_schedule_split():
    """AR balance_due + deposit_required is not the client 50/50 split."""
    failures = check_deposit_balance({
        "total": 1000.00,
        "deposit_required": 500.00,
        "balance_due": 1000.00,
    })
    assert failures == []


# ── 3. Fabric / wood / foam cuts ────────────────────────────────────


def test_fabric_allowance_table_covers_workroom_foam():
    assert fabric_allowance_for_foam(2) == 4.5
    assert fabric_allowance_for_foam("1-1/2") == 4.0
    assert expected_fabric_cut(36, 2) == 45.0
    assert 2.0 in FABRIC_CUT_ALLOWANCE


def test_fabric_cuts_pass_when_fabric_is_wood_plus_two_allowances():
    # 36" wood, 2" foam → 4-1/2" each side → fabric 45"
    failures = check_fabric_cuts({
        "wood_cut": 36,
        "foam_cut": 36,
        "fabric_cut": 45,
        "foam_thickness": 2,
    })
    assert failures == []


def test_fabric_cuts_fail_when_fabric_is_quietly_short():
    failures = check_fabric_cuts({
        "wood_cut": 36,
        "foam_cut": 36,
        "fabric_cut": 40,  # should be 45
        "foam_thickness": 2,
    })
    assert any(f.check == "fabric_cut" for f in failures)
    text = user_facing_failure_text(validate_tool_payload({
        "wood_cut": 36,
        "foam_cut": 36,
        "fabric_cut": 40,
        "foam_thickness": 2,
    }))
    assert "45" in text or '45"' in text
    _assert_fraction_copy(text, failures[0].message)
    assert "40.0" not in text
    assert "4.5" not in text


def test_foam_cut_must_equal_wood_cut():
    failures = check_fabric_cuts({
        "wood_cut": 36,
        "foam_cut": 38,
        "fabric_cut": 45,
        "foam_thickness": 2,
    })
    assert any(f.check == "foam_equals_wood" for f in failures)
    _assert_fraction_copy(*(f.message for f in failures))


def test_cut_sheet_displays_fractions_only():
    sheet = attach_cut_sheet(36.5, 1.5)
    assert sheet["wood_cut_display"] == '36-1/2"'
    assert sheet["allowance_display"] == '4"'
    assert sheet["fabric_cut_display"] == '44-1/2"'
    for value in sheet.values():
        if isinstance(value, str):
            _assert_fraction_copy(value)


def test_format_measure_never_prints_decimal_inches():
    assert format_measure(14.5) == '14-1/2"'
    assert format_measure(6.25) == '6-1/4"'
    assert "14.5" not in format_measure(14.5)


# ── Gate: do not silently proceed ───────────────────────────────────


def test_gate_marks_failed_check_and_does_not_act(monkeypatch):
    escalations = []
    monkeypatch.setattr(
        "app.services.max.tool_checks.escalate_to_rafael",
        lambda tool, check, payload=None: escalations.append((tool, check)) or {
            "escalated_to": "rafael",
            "acted": False,
            "shadow_confidence": {"confidence": 0.0, "shadow": "test"},
        },
    )
    original = ToolResult(
        tool="draft_estimate_and_presentation",
        success=True,
        result={"total": 1000, "deposit": 100, "balance": 100, "line_items": [{"amount": 1000}]},
    )
    gated = gate_tool_result("draft_estimate_and_presentation", original)
    assert gated.success is False
    assert gated.result["failed_check"] is True
    assert gated.result["check_status"] == FAILED_CHECK
    assert gated.result["acted"] is False
    assert gated.result["escalated_to"] == "rafael"
    assert escalations
    assert original.success is True  # caller result is not reused for acting


def test_gate_passes_a_balanced_estimate():
    original = ToolResult(
        tool="draft_estimate_and_presentation",
        success=True,
        result={
            "total": 1000,
            "deposit": 500,
            "balance": 500,
            "line_items": [{"amount": 1000}],
            "check_status": "ok",
        },
    )
    gated = gate_tool_result("draft_estimate_and_presentation", original)
    assert gated.success is True
    assert gated.result["check_status"] == "ok"


# ── Real execute_tool path (mock documents only) ────────────────────


def test_execute_tool_escalates_mismatched_estimate(monkeypatch):
    from app.services.max import tool_executor as te

    captured = []

    def fake_notify(source, type, title, message, priority="medium", context=None):
        captured.append({
            "source": source, "type": type, "title": title,
            "message": message, "priority": priority, "context": context or {},
        })
        return {"id": "notif-estimate-mock"}

    monkeypatch.setattr("app.routers.notifications.notify_founder", fake_notify)

    def fake_draft(params, desk=None):
        return ToolResult(
            tool="draft_estimate_and_presentation",
            success=True,
            result={
                "status": "draft",
                "sent": False,
                "total": 2000.00,
                "deposit": 500.00,
                "balance": 500.00,  # 1000 != 2000
                "line_items": [{"description": "Mock upholstered bench", "amount": 2000}],
            },
        )

    monkeypatch.setitem(te.TOOL_REGISTRY, "draft_estimate_and_presentation", fake_draft)
    result = run_checked_handler(
        "draft_estimate_and_presentation",
        fake_draft,
        {"tool": "draft_estimate_and_presentation",
         "openings": [{"room": "Mock Room", "width": 36, "height": 18}]},
    )
    assert result.success is False
    assert result.result["failed_check"] is True
    assert result.result["acted"] is False
    assert result.result["escalated_to"] == "rafael"
    assert captured, "failed check must escalate to Rafael"
    assert captured[0]["source"] == "MAX"
    assert "did not act" in captured[0]["message"].lower()
    assert any(f["check"] == "deposit_balance" for f in result.result["failures"])
    print("\n=== PROOF: mock estimate with mismatched deposit/balance ===")
    print(captured[0]["message"])
    print("escalation:", result.result["escalation"])


def test_execute_tool_escalates_wrong_fabric_cut(monkeypatch):
    from app.services.max import tool_executor as te

    captured = []

    def fake_notify(source, type, title, message, priority="medium", context=None):
        captured.append({"title": title, "message": message, "context": context or {}})
        return {"id": "notif-cut-mock"}

    monkeypatch.setattr("app.routers.notifications.notify_founder", fake_notify)

    def fake_draw(params, desk=None):
        return ToolResult(
            tool="render_shop_drawing",
            success=True,
            result={
                "product_type": "bench",
                "drawing_engine": "mock",
                "cuts": {
                    "wood_cut": 36,
                    "foam_cut": 36,
                    "fabric_cut": 40,  # 2" foam → should be 45"
                    "foam_thickness": 2,
                },
            },
        )

    monkeypatch.setitem(te.TOOL_REGISTRY, "render_shop_drawing", fake_draw)
    result = run_checked_handler(
        "render_shop_drawing",
        fake_draw,
        {
            "tool": "render_shop_drawing",
            "product_type": "bench",
            "dims": {
                "width": 36,
                "wood_cut": 36,
                "foam_cut": 36,
                "fabric_cut": 40,
                "foam_thickness": 2,
            },
        },
    )
    assert result.success is False
    assert result.result["failed_check"] is True
    assert result.result["acted"] is False
    assert captured, "wrong fabric cut must escalate to Rafael"
    text = captured[0]["message"]
    _assert_fraction_copy(text)
    assert "36" in text
    assert any(f["check"] == "fabric_cut" for f in result.result["failures"])
    print("\n=== PROOF: mock cut sheet with wrong fabric cut ===")
    print(text)
    print("escalation:", result.result["escalation"])


def test_execute_tool_passes_balanced_mock_estimate(monkeypatch):
    from app.services.max import tool_executor as te

    def fake_draft(params, desk=None):
        return ToolResult(
            tool="draft_estimate_and_presentation",
            success=True,
            result={
                "total": 2000.00,
                "deposit": 1000.00,
                "balance": 1000.00,
                "line_items": [{"description": "Mock line", "amount": 2000}],
            },
        )

    monkeypatch.setitem(te.TOOL_REGISTRY, "draft_estimate_and_presentation", fake_draft)
    result = run_checked_handler(
        "draft_estimate_and_presentation",
        fake_draft,
        {"tool": "draft_estimate_and_presentation",
         "openings": [{"room": "Mock Room", "width": 36, "height": 18}]},
    )
    assert result.success is True
    assert result.result.get("failed_check") is not True
    assert result.result.get("check_status") == "ok"


def test_real_workroom_packet_passes_deposit_and_line_sum():
    from app.services.estimates.workroom_packet import build_packet, sample_phase1
    from app.services.pricing.workroom_rules import reset_rules

    reset_rules()
    packet = build_packet(sample_phase1())
    assert packet["deposit"] + packet["balance"] == pytest.approx(packet["total"])
    check = validate_tool_payload(packet, tool_name="draft_estimate_and_presentation")
    assert check.passed, [f.message for f in check.failures]


def test_quality_gate_flags_failed_check():
    from app.services.max.quality_gate import FAILED, validate_response

    quality = validate_response(
        "Here is the estimate.",
        tool_results=[{
            "tool": "draft_estimate_and_presentation",
            "success": False,
            "error": "failed-check: deposit + balance != total",
            "result": {"failed_check": True, "acted": False},
        }],
    )
    assert quality.level == FAILED
    assert any("failed_check" in w for w in quality.warnings)

    action = validate_response(
        "Sent the estimate.",
        tool_results=[{
            "tool": "send_email",
            "success": False,
            "error": "failed-check: deposit + balance != total",
            "result": {"failed_check": True, "acted": False},
        }],
        is_action=True,
    )
    assert action.level == FAILED
