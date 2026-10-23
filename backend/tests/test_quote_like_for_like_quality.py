"""Like-for-like quote quality: category + size-normalized, never whole-job avg.

The live bug compared a scoped estimate (Le Midi Phase 2 office drapery)
against an unrelated average (Phase 1 whole house, or every quote total)
and blocked it as "50% below average".

These tests drive the same validate() call create_quote / send_quote use.
"""
from __future__ import annotations

import json

import pytest

from app.services.quote_engine.like_for_like_quality import (
    BELOW_AVERAGE_THRESHOLD,
    MIN_COMPARABLES,
    classify_scope,
    evaluate_like_for_like,
    extract_scope_rates,
    extract_size,
    run_quote_quality_gate,
)


def _item(description, *, qty=1, unit="width", rate=110, amount=None, **extra):
    row = {
        "description": description,
        "quantity": qty,
        "unit": unit,
        "rate": rate,
        "amount": amount if amount is not None else round(qty * rate, 2),
    }
    row.update(extra)
    return row


def _quote(qid, project, items, *, total=None, customer="Le Midi", **extra):
    amounts = [i.get("amount") or 0 for i in items]
    subtotal = round(sum(amounts), 2)
    quote = {
        "id": qid,
        "quote_number": f"EST-{qid}",
        "customer_name": customer,
        "project_name": project,
        "status": "sent",
        "line_items": items,
        "subtotal": subtotal,
        "tax_amount": 0,
        "discount_amount": 0,
        "total": total if total is not None else subtotal,
    }
    quote.update(extra)
    return quote


def _phase1_whole_house():
    """Unrelated whole-job ticket: drapery + bench + banquette, huge total."""
    return _quote(
        "phase1",
        "Le Midi Phase 1 — whole house",
        [
            _item("Living room ripplefold drapery, 8 widths", qty=8, unit="width", rate=110),
            _item("Dining sheers, 4 widths", qty=4, unit="width", rate=85),
            _item("Upholstery bench 10 LF", qty=10, unit="lf", rate=180),
            _item("Banquette 14 LF", qty=14, unit="lf", rate=220),
        ],
        total=18400,
    )


def _ripplefold_history():
    """Three like-for-like drapery ripplefold jobs at ~$110/width."""
    return [
        _phase1_whole_house(),
        _quote(
            "rf-a",
            "River Rd living ripplefold",
            [_item("Ripplefold drapery, 6 widths", qty=6, unit="width", rate=115)],
            customer="River",
        ),
        _quote(
            "rf-b",
            "Chevy Chase ripplefold",
            [_item("Ripplefold panels, 4 widths", qty=4, unit="width", rate=105)],
            customer="Chase",
        ),
        _quote(
            "wood-big",
            "WoodCraft conference table",
            [_item("White oak conference table", qty=1, unit="ea", rate=25000)],
            total=25000,
            customer="Oak Buyer",
        ),
    ]


def _office_drapery(*, rate=110, widths=2, qid="phase2-office"):
    return _quote(
        qid,
        "Le Midi Phase 2 — office only",
        [_item(f"Office ripplefold drapery, {widths} widths", qty=widths, unit="width", rate=rate)],
    )


def _validate(quote, history=None, quotes_dir=None, founder_override=False):
    """The production quote-create / quote-send quality door."""
    return run_quote_quality_gate(
        quote,
        comparable_quotes=history,
        quotes_dir=quotes_dir,
        founder_override=founder_override,
    )


def test_classify_scope_is_product_specific():
    assert classify_scope(_item("Office ripplefold drapery")) == "drapery_ripplefold"
    assert classify_scope(_item("Dining sheers")) == "sheers"
    assert classify_scope(_item("Upholstery bench 8 LF")) == "upholstery_bench"
    assert classify_scope(_item("U-shaped banquette")) == "banquette"
    assert classify_scope(_item("White oak table")) is None


def test_phase1_mixed_job_extracts_per_category_not_whole_total():
    scopes = extract_scope_rates(_phase1_whole_house())
    assert scopes["drapery_ripplefold"]["unit_rate"] == 110.0
    assert scopes["drapery_ripplefold"]["size"] == 8
    assert scopes["sheers"]["unit_rate"] == 85.0
    assert scopes["upholstery_bench"]["unit_rate"] == 180.0
    assert scopes["banquette"]["unit_rate"] == 220.0
    # Whole-job $18,400 must not become the drapery unit rate.
    assert scopes["drapery_ripplefold"]["amount"] == 880.0
    assert scopes["drapery_ripplefold"]["amount"] != 18400


def test_extract_size_from_widths_and_lf():
    assert extract_size(_item("x", qty=6, unit="width"), "drapery_ripplefold") == 6
    assert extract_size(
        {"description": "Ripplefold 6 widths", "amount": 660},
        "drapery_ripplefold",
    ) == 6
    assert extract_size(_item("bench", qty=10, unit="lf", rate=180), "upholstery_bench") == 10


def test_office_drapery_is_not_flagged_against_phase1_whole_job():
    """Fair office-only ripplefold vs a huge Phase 1 mixed ticket — no false flag."""
    office = _office_drapery(rate=110, widths=2)
    result = evaluate_like_for_like(office, history=_ripplefold_history())
    assert result.flagged is False
    assert result.blocked is False
    drapery = next(c for c in result.comparisons if c.category == "drapery_ripplefold")
    assert drapery.unit_rate == 110.0
    assert drapery.average_unit_rate is not None
    assert abs(drapery.unit_rate - drapery.average_unit_rate) / drapery.average_unit_rate < 0.15
    assert len(drapery.comparables) >= MIN_COMPARABLES
    # Comparables are drapery unit rates, not the $18,400 Phase 1 total.
    assert all(row.unit_rate < 1000 for row in drapery.comparables)


def test_truly_underpriced_office_drapery_is_flagged_with_comparables():
    office = _office_drapery(rate=40, widths=2)
    result = evaluate_like_for_like(office, history=_ripplefold_history())
    assert result.flagged is True
    assert result.blocked is True
    assert result.never_auto_unblocks() is True
    assert BELOW_AVERAGE_THRESHOLD == 0.50
    text = " ".join(result.reasons)
    assert "50%" in text or "64%" in text or "below like-for-like" in text
    assert "founder review required" in text.lower()
    assert "Comparables used:" in text
    assert "EST-phase1" in text
    assert "ripplefold" in text.lower()
    # Must not claim the average is the whole-job $18,400.
    assert "18,400" not in text
    assert "$18400" not in text


def test_insufficient_history_does_not_flag():
    office = _office_drapery(rate=40, widths=2)
    result = evaluate_like_for_like(office, history=[_phase1_whole_house()])
    assert result.flagged is False
    drapery = next(c for c in result.comparisons if c.category == "drapery_ripplefold")
    assert drapery.skip_reason and drapery.skip_reason.startswith("insufficient_history")


def test_sheers_are_not_compared_to_ripplefold_or_benches():
    sheers = _quote(
        "sheers-1",
        "Office sheers",
        [_item("Office sheers, 2 widths", qty=2, unit="width", rate=20)],
    )
    result = evaluate_like_for_like(sheers, history=_ripplefold_history())
    # History has only one sheers scope (Phase 1 dining) — not enough.
    assert result.flagged is False
    sheer = next(c for c in result.comparisons if c.category == "sheers")
    assert all(row.category == "sheers" for row in sheer.comparables)


def test_real_quote_path_office_drapery_not_blocked():
    office = _office_drapery(rate=110, widths=2)
    qr = _validate(office, history=_ripplefold_history())
    anomaly = [i for i in qr.issues if i.check == "quote_anomaly"]
    assert anomaly == []
    assert qr.blocked is False
    print("PROOF office-fair:", {"blocked": qr.blocked, "issues": [i.message for i in qr.issues]})


def test_real_quote_path_underpriced_blocked_with_comparables():
    office = _office_drapery(rate=40, widths=2)
    qr = _validate(office, history=_ripplefold_history())
    anomaly = [i for i in qr.issues if i.check == "quote_anomaly"]
    assert len(anomaly) == 1
    assert qr.blocked is True
    assert qr.passed is False
    assert "Comparables used:" in anomaly[0].message
    assert "founder review required" in anomaly[0].message.lower()
    print("PROOF office-underpriced:", {"blocked": qr.blocked, "message": anomaly[0].message})


def test_founder_override_does_not_auto_unblock_quote_anomaly():
    office = _office_drapery(rate=40, widths=2)
    qr = _validate(office, history=_ripplefold_history(), founder_override=True)
    assert qr.blocked is True
    assert any(i.check == "quote_anomaly" for i in qr.issues)


def test_history_loaded_from_quotes_dir_not_hardcoded_empire_repo(tmp_path):
    history_dir = tmp_path / "quotes"
    history_dir.mkdir()
    for past in _ripplefold_history():
        (history_dir / f"{past['id']}.json").write_text(json.dumps(past))
    office = _office_drapery(rate=110, widths=2)
    qr_ok = _validate(office, quotes_dir=str(history_dir))
    assert qr_ok.blocked is False
    cheap = _office_drapery(rate=40, widths=2, qid="phase2-cheap")
    qr_bad = _validate(cheap, quotes_dir=str(history_dir))
    assert qr_bad.blocked is True


def test_create_quote_path_office_passes_underpriced_blocks(tmp_path):
    """create_quote / send_quote both call run_quote_quality_gate."""
    history_dir = tmp_path / "quotes"
    history_dir.mkdir()
    for past in _ripplefold_history():
        (history_dir / f"{past['id']}.json").write_text(json.dumps(past))

    fair = _office_drapery(rate=110, widths=2)
    cheap = _office_drapery(rate=40, widths=2, qid="phase2-cheap")
    qr_fair = run_quote_quality_gate(fair, quotes_dir=str(history_dir))
    qr_cheap = run_quote_quality_gate(cheap, quotes_dir=str(history_dir))

    assert qr_fair.blocked is False
    assert qr_cheap.blocked is True
    # Same 422 payload create_quote raises when qr.blocked.
    detail = {
        "message": "Quote blocked by quality engine",
        "issues": [
            {"check": i.check, "severity": i.severity.value, "message": i.message}
            for i in qr_cheap.issues
        ],
    }
    anomaly = [i for i in detail["issues"] if i["check"] == "quote_anomaly"]
    assert anomaly
    assert "Comparables used:" in anomaly[0]["message"]
    print("PROOF create_quote-gate fair blocked=", qr_fair.blocked)
    print("PROOF create_quote-gate underpriced 422:", anomaly[0]["message"])
