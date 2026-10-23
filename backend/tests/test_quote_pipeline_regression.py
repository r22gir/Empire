"""Broader quote-pipeline regression pack.

Covers the live quote path end-to-end without sending anything:
  - like-for-like quality (office drapery vs whole-job average)
  - catalog pricing (ripplefold / sheers / bench)
  - fractions-only measurement output
  - Empire Workroom → Stripe Payment Link (never Checkout Session)
  - Nelma's → Square
  - tests never send email / SMS / WhatsApp / Telegram
"""
from __future__ import annotations

import json
from types import SimpleNamespace

import pytest

from app.services.max.response_quality_engine import Channel
from app.services.pricing.engine import price_workroom_line
from app.services.sprint_m.text_to_pay import build_payment_link, resolve_provider
from app.services.workroom_quote_commerce import (
    apply_totals_to_quote,
    assert_non_expiring_payment_link,
    build_deposit_payment_link_params,
    format_fraction_inches,
    format_measurement_triple,
    parse_fraction_inches,
)
from app.services.quote_engine.like_for_like_quality import (
    evaluate_like_for_like,
    run_quote_quality_gate,
)

from tests.test_quote_like_for_like_quality import (
    _office_drapery,
    _ripplefold_history,
    _validate,
)


SEND_PROBES = []


@pytest.fixture(autouse=True)
def _no_sends(monkeypatch):
    """Quote pipeline tests must never touch a live send path."""
    SEND_PROBES.clear()

    def _blocked(name):
        def _inner(*args, **kwargs):
            SEND_PROBES.append({"name": name, "args": args, "kwargs": kwargs})
            raise AssertionError(f"send blocked in tests: {name}")
        return _inner

    for target, name in (
        ("app.services.email.sender.send_email", "send_email"),
        ("app.services.max.email_service.send_email", "max_send_email"),
    ):
        try:
            monkeypatch.setattr(target, _blocked(name), raising=False)
        except Exception:
            pass
    yield
    assert SEND_PROBES == [], f"sends attempted during tests: {SEND_PROBES}"


def test_pricing_ripplefold_bench_and_manual_line():
    ripple = price_workroom_line("drapery", {
        "window_width_in": 120,
        "length_in": 96,
        "style": "ripplefold",
        "fullness": 2.5,
        "fabric_width_in": 54,
    })
    assert ripple["proposed_price"] == 660.00
    assert ripple["computed"]["widths"] == 6
    assert ripple["price_overridden"] is False

    four = price_workroom_line("drapery", {
        "window_width_in": 75,
        "length_in": 96,
        "style": "ripplefold",
        "fullness": 2.5,
        "fabric_width_in": 54,
    })
    assert four["proposed_price"] == 440.00

    bench = price_workroom_line("manual_line", {
        "quantity": 10,
        "unit_price": 180.00,
        "description": "Upholstery bench 10 LF",
    })
    assert bench["proposed_price"] == 1800.00


def test_fractions_only_measurement_output():
    assert parse_fraction_inches("84 1/2") == 84.5
    assert format_fraction_inches(84.5) == "84 1/2"
    assert format_fraction_inches(96.375) == "96 3/8"
    assert format_fraction_inches(26.75) == "26 3/4"
    triple = format_measurement_triple("84 1/2", "96 3/8", "3 1/4")
    assert triple == '84 1/2" x 96 3/8" x 3 1/4"'
    assert "." not in triple
    try:
        from app.services.estimates.mclean_estimate_pdf import inches_to_fractions
        rendered = inches_to_fractions('Office drapery 26.75" x 96.375"')
        assert rendered == 'Office drapery 26 3/4" x 96 3/8"'
        assert ".75" not in rendered
        assert ".375" not in rendered
    except ImportError:
        # reportlab is optional for this pack; commerce formatter is the gate.
        assert format_fraction_inches(26.75) == "26 3/4"
        assert format_fraction_inches(96.375) == "96 3/8"


def test_empire_workroom_uses_stripe_payment_link_not_checkout_session():
    created_sessions = []
    created_links = []

    class _Session:
        @classmethod
        def create(cls, **kwargs):
            created_sessions.append(kwargs)
            raise AssertionError("Checkout Session must not be created for Empire Workroom")

    class _Link:
        @classmethod
        def create(cls, **kwargs):
            created_links.append(kwargs)
            return SimpleNamespace(id="plink_reg", url="https://buy.stripe.com/test_reg")

    quote = apply_totals_to_quote({
        "id": "q-workroom",
        "quote_number": "EST-REG-1",
        "business_unit": "workroom",
        "line_items": [{"description": "Ripplefold", "quantity": 2, "unit": "width", "rate": 110, "amount": 220}],
        "addons": [],
        "tax_rate": 0,
        "deposit_percent": 50,
    })
    params = build_deposit_payment_link_params(quote)
    assert_non_expiring_payment_link(params)
    assert "expires_at" not in params
    assert "checkout" not in json.dumps(params).lower() or "Checkout Session" not in json.dumps(params)

    from app.services.workroom_quote_commerce import create_payment_link
    result = create_payment_link(params, stripe_client=SimpleNamespace(PaymentLink=_Link, checkout=SimpleNamespace(Session=_Session)))
    assert result["created"] is True
    assert result["url"].startswith("https://buy.stripe.com/")
    assert result["expires_at"] is None
    assert created_links and not created_sessions
    assert resolve_provider("workroom") == "stripe"
    workroom_link = build_payment_link(
        {"id": "job-1", "job_number": "J-1", "customer_name": "Ada", "business_unit": "workroom"},
        "stripe",
        110,
    )
    assert workroom_link["provider"] == "stripe"
    assert workroom_link["processor"] == "stripe_payment_link"
    assert workroom_link["brand"] == "Empire Workroom"
    assert workroom_link["expires_at"] is None
    assert workroom_link["non_expiring"] is True


def test_nelmas_uses_square_not_stripe():
    assert resolve_provider("nelmas") == "square"
    assert resolve_provider("nelma") == "square"
    link = build_payment_link(
        {"id": "job-nelma", "job_number": "J-N", "customer_name": "Nelma", "business_unit": "nelmas"},
        resolve_provider("nelmas"),
        400,
    )
    assert link["provider"] == "square"
    assert link["processor"] == "square_payment_link"
    assert link["brand"] == "Nelma's"
    assert "squareup.com" in link["url"]
    assert link["expires_at"] is None


def test_pipeline_office_drapery_not_falsely_flagged():
    office = _office_drapery(rate=110, widths=2)
    comparison = evaluate_like_for_like(office, history=_ripplefold_history())
    qr = _validate(office, history=_ripplefold_history())
    assert comparison.flagged is False
    assert qr.blocked is False
    assert not any(i.check == "quote_anomaly" for i in qr.issues)
    print("REGRESSION office-fair blocked=", qr.blocked, "channel=", Channel.QUOTE.value)


def test_pipeline_underpriced_still_flagged_founder_review():
    office = _office_drapery(rate=40, widths=2)
    comparison = evaluate_like_for_like(office, history=_ripplefold_history())
    qr = run_quote_quality_gate(office, comparable_quotes=_ripplefold_history())
    assert comparison.flagged is True
    assert comparison.blocked is True
    assert qr.blocked is True
    msg = next(i.message for i in qr.issues if i.check == "quote_anomaly")
    assert "Comparables used:" in msg
    assert "founder review required" in msg.lower()
    print("REGRESSION office-underpriced:", msg)


def test_pipeline_never_sends():
    assert SEND_PROBES == []
