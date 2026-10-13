"""Fixture-only tests for Workroom quote/invoice commerce.

Never opens the live empire.db. Stripe is a fake client.
"""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.services import workroom_quote_commerce as wqc

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "workroom_quote_commerce"


def _load(name: str) -> dict:
    return json.loads((FIXTURE_DIR / name).read_text())


class FakePaymentLink:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.id = "plink_test_nonexpiring"
        self.url = "https://buy.stripe.com/test_workroom_deposit"


class FakeStripe:
    class PaymentLink:
        last_create = None

        @classmethod
        def create(cls, **kwargs):
            cls.last_create = kwargs
            return FakePaymentLink(**kwargs)


@pytest.fixture
def store(tmp_path):
    path = tmp_path / "workroom-commerce-fixture.db"
    store = wqc.FixtureStore(db_path=str(path), stripe_client=FakeStripe, review_url="https://g.page/r/fixture-review")
    store.init()
    return store


def test_fraction_measurements_round_trip():
    assert wqc.parse_fraction_inches("84 1/2") == 84.5
    assert wqc.parse_fraction_inches("96 3/8") == pytest.approx(96.375)
    assert wqc.parse_fraction_inches('3 1/4"') == 3.25
    assert wqc.parse_fraction_inches("1/2") == 0.5
    assert wqc.parse_fraction_inches(36.5) == 36.5
    assert wqc.format_fraction_inches(84.5) == "84 1/2"
    assert wqc.format_fraction_inches(96.375) == "96 3/8"
    assert wqc.format_fraction_inches(3.25) == "3 1/4"
    assert wqc.format_measurement_triple("84 1/2", "96 3/8", "3 1/4") == '84 1/2" x 96 3/8" x 3 1/4"'


def test_selected_addons_update_total_and_deposit_live():
    quote = _load("estimate.json")
    baseline = wqc.compute_estimate_totals(
        line_items=quote["line_items"],
        addons=quote["addons"],
        tax_rate=quote["tax_rate"],
        deposit_percent=quote["deposit_percent"],
    )
    assert baseline["addon_total"] == 0
    assert baseline["subtotal"] == 2400
    assert baseline["total"] == 2544.00
    assert baseline["deposit_amount"] == 1272.00

    selected = []
    for addon in quote["addons"]:
        row = dict(addon)
        row["selected"] = True
        selected.append(row)

    live = wqc.compute_estimate_totals(
        line_items=quote["line_items"],
        addons=selected,
        tax_rate=quote["tax_rate"],
        deposit_percent=quote["deposit_percent"],
    )
    assert live["addon_total"] == 525.00
    assert live["subtotal"] == 2925.00
    assert live["tax_amount"] == 175.50
    assert live["total"] == 3100.50
    assert live["deposit_amount"] == 1550.25
    assert live["deposit_amount"] != baseline["deposit_amount"]


def test_unselected_optional_addons_do_not_change_totals():
    quote = _load("estimate.json")
    totals = wqc.apply_totals_to_quote(dict(quote))
    assert all(not a["selected"] for a in totals["addons"])
    assert totals["addon_total"] == 0
    assert totals["deposit"]["deposit_amount"] == 1272.00


def test_payment_link_params_are_non_expiring():
    quote = wqc.apply_totals_to_quote(_load("estimate.json"))
    params = wqc.build_deposit_payment_link_params(quote)
    wqc.assert_non_expiring_payment_link(params)
    assert "expires_at" not in params
    assert params["inactive"] is False
    assert params["line_items"][0]["price_data"]["unit_amount"] == 127200
    assert params["metadata"]["flow"] == "workroom_deposit"


def test_approve_and_pay_requires_esignature_and_returns_payment_link():
    quote = wqc.apply_totals_to_quote(_load("estimate.json"))
    with pytest.raises(ValueError, match="signer_name"):
        wqc.approve_and_pay_deposit(quote, "", "data:image/png;base64,abc12345")
    with pytest.raises(ValueError, match="signature_data"):
        wqc.approve_and_pay_deposit(quote, "Ada Workroom", "")

    result = wqc.approve_and_pay_deposit(
        quote,
        "Ada Workroom",
        "data:image/png;base64,iVBORw0KGgoAAAANSUhEUg",
        stripe_client=FakeStripe,
        ip_address="203.0.113.10",
    )
    assert result["success"] is True
    assert result["status"] == "approved"
    assert result["esignature"]["signature_captured"] is True
    assert result["esignature_record"]["signer_name"] == "Ada Workroom"
    assert result["payment_link"]["created"] is True
    assert result["payment_link"]["expires_at"] is None
    assert result["payment_url"].startswith("https://buy.stripe.com/")
    assert FakeStripe.PaymentLink.last_create["inactive"] is False
    assert "expires_at" not in FakeStripe.PaymentLink.last_create


def test_followups_default_off_and_never_send_without_owner_opt_in(store):
    quote = store.put_quote(_load("estimate.json"))
    store.put_invoice(_load("invoice_open.json"))
    now = datetime(2026, 4, 12, tzinfo=timezone.utc)

    # No prefs saved — defaults are OFF.
    result = store.run_due_followups(now)
    assert result["sent_count"] == 0
    assert result["blocked_count"] >= 1
    assert all(item["blocked_reason"] == "owner_opt_in_required" for item in result["blocked"])
    assert store.load_prefs("cust-ada")["quote_reminders_enabled"] is False
    assert store.load_prefs("cust-blocked")["invoice_reminders_enabled"] is False

    sent = []

    def sender(draft):
        sent.append(draft)
        return {"channel": "fixture", "ok": True}

    store.sender = sender
    still_blocked = store.run_due_followups(now)
    assert still_blocked["sent_count"] == 0
    assert sent == []

    store.save_prefs(wqc.set_followup_prefs("cust-ada", quote_reminders_enabled=True, enabled_by="owner"))
    opted = store.run_due_followups(now)
    assert opted["sent_count"] == 1
    assert opted["sent"][0]["document_id"] == quote["id"]
    assert opted["sent"][0]["kind"] == "quote_followup"
    # The other client still has reminders off.
    assert any(item["customer_id"] == "cust-blocked" and item["status"] == "blocked_no_opt_in" for item in opted["blocked"])


def test_review_request_requires_owner_approval_before_send(store):
    unpaid = dict(_load("invoice_open.json"))
    with pytest.raises(ValueError, match="after an invoice is paid"):
        wqc.queue_review_request_after_paid(unpaid)

    paid = store.put_invoice(_load("invoice_paid.json"))
    queued = store.mark_invoice_paid(paid["id"])
    request = queued["review_request"]
    assert request["status"] == "pending_owner_approval"
    assert request["sendable"] is False

    premature = wqc.send_review_request(request, sender=lambda r: {"ok": True})
    assert premature["sent"] is False
    assert premature["reason"] == "owner_approval_required"

    approved = wqc.owner_approve_review_request(request, approved_by="owner")
    store.save_review_request(approved)
    delivered = []
    sent = wqc.send_review_request(approved, sender=lambda r: delivered.append(r) or {"ok": True})
    assert sent["sent"] is True
    assert sent["status"] == "sent"
    assert delivered[0]["review_url"].startswith("https://g.page/")


def test_fixture_store_does_not_use_live_empire_db(store, tmp_path):
    assert Path(store.db_path).is_relative_to(tmp_path)
    assert "empire.db" not in store.db_path
    assert Path(store.db_path).name == "workroom-commerce-fixture.db"
