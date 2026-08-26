"""D39 / H77 — line override generalisation + no_charge carve-out + provenance.

Continues H77. Three things land in STEP 1 of the dispatch:

  1. Every workroom line pricer accepts an optional `override_price`.
     When supplied > 0, it becomes proposed_price. computed records
     computed_price (what the engine would have said), override_price,
     and override_used=True. Override is general — any category, any
     width, always available — not only when out of range.

  2. Explicit no-charge carve-out. `no_charge: True` PLUS a non-empty
     `no_charge_reason` produces proposed_price=0.00 with the reason
     recorded. Without the reason it RAISES. This is the second
     permitted zero (alongside com_fabric + customer_supplied=true from
     D38). Both reachable only by explicit flag; a missing key
     resolving to 0 is still the defect H77 closed.

  3. Issued-document provenance. A quote records issued_document
     (e.g. "NELMA-814"). Per-line, the rate_source: "catalog" or
     "issued:<doc>". The engine does not enforce this — it records
     it. A future session reading the quote can see the rates are
     historical by intent, not by drift.

This file asserts every dispatch demo + the anti-bypass lockdown for
the second carve-out, plus the provenance persistence through
quote_service.create_quote.
"""
import importlib
import json
import os

import pytest

from app.services.pricing.engine import (
    PricingClassificationError,
    PricingInputError,
    price_workroom_line,
)
from app.services.quote_service import _price_line_item, create_quote


# ---------------------------------------------------------------------------
# D33 cross-test pollution guard — tests that touch the DB through
# create_quote may run AFTER tests that reload app.db.database with a
# different EMPIRE_TASK_DB path (notably test_canonical_pricing_engine's
# _load_finance / _load_craftforge fixtures). monkeypatch restores the
# env var on teardown, but importlib.reload() captured DB_PATH at reload
# time and never undoes it. Without re-rebinding, the next get_db() call
# targets a now-deleted tmp file. This fixture re-binds DB_PATH to the
# conftest's pre-collected path before each create_quote-touching test.
# ---------------------------------------------------------------------------
@pytest.fixture(autouse=False)
def _rebind_db_path(isolated_empire_db):
    """Re-import app.db.database with the conftest's pre-collected path
    so subsequent get_db() calls target the test DB. No-op on environments
    where DB_PATH already points at the test DB."""
    import app.db.database as dbmod
    if dbmod.DB_PATH != isolated_empire_db:
        os.environ["EMPIRE_TASK_DB"] = isolated_empire_db
        importlib.reload(dbmod)
    yield


# ===========================================================================
# 1. General override_price — any category, any width, always available
# ===========================================================================
def test_drapery_with_override_price_95_records_both_numbers():
    """Dispatch demo: drapery with override_price=95 → proposed=95,
    computed_price shown (what engine would have said)."""
    result = price_workroom_line("drapery", {
        "window_width_in": 60,
        "length_in": 80,
        "style": "ripplefold",
        "override_price": 95.00,
    })
    assert result["proposed_price"] == 95.0
    assert result["final_price"] == 95.0
    assert result["computed"]["override_used"] is True
    assert result["computed"]["override_price"] == 95.0
    # Engine would have said $330.00 for these inputs without override
    assert result["computed"]["computed_price"] == 330.0


def test_drapery_without_override_returns_catalog_rate():
    """Dispatch demo: same line without override → catalog $330/width
    (ripplefold under 120")."""
    result = price_workroom_line("drapery", {
        "window_width_in": 60,
        "length_in": 80,
        "style": "ripplefold",
    })
    assert result["proposed_price"] == 330.0
    assert result["computed"].get("override_used") in (None, False)
    assert "computed_price" not in result["computed"]
    assert "override_price" not in result["computed"]


def test_override_price_zero_raises_not_an_override():
    """Dispatch demo: override_price=0 → RAISES. That is the defect H77
    closed. A zero override is a missing input, not an override."""
    with pytest.raises(PricingInputError) as exc:
        price_workroom_line("drapery", {
            "window_width_in": 60,
            "length_in": 80,
            "style": "ripplefold",
            "override_price": 0,
        })
    msg = str(exc.value)
    assert "drapery" in msg
    assert "override_price must be > 0" in msg
    assert "0.00" in msg


def test_override_price_negative_raises():
    with pytest.raises(PricingInputError) as exc:
        price_workroom_line("drapery", {
            "window_width_in": 60,
            "length_in": 80,
            "style": "ripplefold",
            "override_price": -10.0,
        })
    assert "must be > 0" in str(exc.value)


def test_override_price_non_numeric_raises():
    with pytest.raises(PricingInputError) as exc:
        price_workroom_line("drapery", {
            "window_width_in": 60,
            "length_in": 80,
            "style": "ripplefold",
            "override_price": "nope",
        })
    assert "must be numeric" in str(exc.value)


@pytest.mark.parametrize("category,inputs", [
    # Override works for any category, not just drapery
    ("roman_shade",   {"width_in": 30, "height_in": 60, "override_price": 250.00}),
    ("valance",       {"width_in": 72, "override_price": 75.00}),
    ("cornice",       {"width_in": 72, "override_price": 95.00}),
    ("fabric_only",   {"price_per_yard": 30, "yards_needed": 4, "override_price": 200.0}),
    ("labor",         {"hours": 4, "rate_per_hour": 65, "override_price": 300.0}),
    ("pillow",        {"unit_price": 30, "quantity": 2, "override_price": 100.0}),
    ("cover",         {"unit_price": 50, "quantity": 1, "override_price": 75.0}),
    ("hardware_rod_1_1_8",       {"width_in": 72, "override_price": 300.0}),
    ("hardware_ripplefold_track", {"width_in": 72, "override_price": 250.0}),
    ("hardware_rings",            {"packs": 4, "override_price": 175.0}),
    ("hardware_brackets",         {"width_in": 72, "override_price": 95.0}),
])
def test_override_price_works_on_every_category(category, inputs):
    """Every workroom line pricer accepts override_price; any category,
    any width, always available. Out-of-range rescue is a special case;
    in-range override also works (no need to leave the engine's range)."""
    result = price_workroom_line(category, inputs)
    expected = inputs["override_price"]
    assert result["proposed_price"] == expected
    assert result["computed"]["override_used"] is True
    assert result["computed"]["override_price"] == expected


def test_override_price_in_range_hardware_rod_set_records_computed_price():
    """In-range hardware_rod_set (6 ft → catalog $325) with founder
    override $400 records both: computed_price=325, override_price=400,
    override_used=True."""
    result = price_workroom_line("hardware_rod_set", {
        "width_in": 72,                 # 6 ft, in range
        "override_price": 400.00,      # founder says $400 instead of $325
    })
    assert result["proposed_price"] == 400.0
    assert result["computed"]["computed_price"] == 325.0
    assert result["computed"]["override_price"] == 400.0
    assert result["computed"]["override_used"] is True


# ===========================================================================
# 2. Explicit no-charge carve-out — second permitted zero, two-keyed
# ===========================================================================
def test_no_charge_with_reason_emits_zero_with_reason_recorded():
    """Dispatch demo: no_charge=True + reason → $0.00 with reason."""
    result = price_workroom_line("drapery", {
        "window_width_in": 60,
        "length_in": 80,
        "style": "ripplefold",
        "no_charge": True,
        "no_charge_reason": "complimentary per founder",
    })
    assert result["proposed_price"] == 0.0
    assert result["final_price"] == 0.0
    assert result["computed"]["no_charge"] is True
    assert result["computed"]["no_charge_reason"] == "complimentary per founder"


def test_no_charge_without_reason_raises():
    """Dispatch demo: no_charge=True without reason → RAISES."""
    with pytest.raises(PricingInputError) as exc:
        price_workroom_line("drapery", {
            "window_width_in": 60,
            "length_in": 80,
            "style": "ripplefold",
            "no_charge": True,
        })
    msg = str(exc.value)
    assert "drapery" in msg
    assert "no_charge_reason" in msg
    assert "non-empty" in msg


def test_no_charge_with_empty_reason_raises():
    """Whitespace-only reason is treated as missing."""
    with pytest.raises(PricingInputError):
        price_workroom_line("drapery", {
            "window_width_in": 60,
            "length_in": 80,
            "style": "ripplefold",
            "no_charge": True,
            "no_charge_reason": "   ",
        })


def test_no_charge_with_none_reason_raises():
    with pytest.raises(PricingInputError):
        price_workroom_line("drapery", {
            "window_width_in": 60,
            "length_in": 80,
            "style": "ripplefold",
            "no_charge": True,
            "no_charge_reason": None,
        })


def test_no_charge_records_computed_price_for_audit():
    """Audit trail: when no_charge emits $0, the would-be price is still
    recorded so a future reader sees what the engine would have said."""
    result = price_workroom_line("drapery", {
        "window_width_in": 60,
        "length_in": 80,
        "style": "ripplefold",
        "no_charge": True,
        "no_charge_reason": "shipping included",
    })
    assert result["computed"]["computed_price"] == 330.0
    assert result["computed"]["no_charge_reason"] == "shipping included"


@pytest.mark.parametrize("category,inputs", [
    ("roman_shade",   {"width_in": 30, "height_in": 60}),
    ("valance",       {"width_in": 72}),
    ("cornice",       {"width_in": 72}),
    ("fabric_only",   {"price_per_yard": 30, "yards_needed": 4}),
    ("labor",         {"hours": 4, "rate_per_hour": 65}),
    ("pillow",        {"unit_price": 30, "quantity": 2}),
    ("cover",         {"unit_price": 50, "quantity": 1}),
    ("hardware_rod_set", {"width_in": 72}),
    ("installation",  {"treatment": "roman_shade", "quantity": 1}),
    ("manual_line",   {"description": "x", "unit_price": 50, "quantity": 1}),
])
def test_no_charge_works_on_every_category(category, inputs):
    """no_charge is on the dispatch, not in any single pricer; any
    category may be flagged no_charge with a reason. Engine records,
    does not compute beyond the flag."""
    inputs = dict(inputs)
    inputs["no_charge"] = True
    inputs["no_charge_reason"] = "test reason"
    result = price_workroom_line(category, inputs)
    assert result["proposed_price"] == 0.0
    assert result["computed"]["no_charge"] is True
    assert result["computed"]["no_charge_reason"] == "test reason"


# ===========================================================================
# 3. quote_service accepts both zeros — anti-bypass lockdown
# ===========================================================================
def test_quote_service_accepts_no_charge_zero():
    """Dispatch demo: quote_service accepts the no_charge zero. The
    service-layer carve-out is the second flag, gated on BOTH
    conditions: computed.no_charge is True AND computed.no_charge_reason
    is non-empty."""
    out = _price_line_item(
        category="drapery",
        inputs={
            "window_width_in": 60, "length_in": 80, "style": "ripplefold",
            "no_charge": True,
            "no_charge_reason": "founder complimentary",
        },
        business_unit="workroom",
        legacy={},
    )
    assert out["proposed_price"] == 0.0
    assert out["final_price"] == 0.0
    assert out["subtotal"] == 0.0


def test_quote_service_rejects_bare_zero_after_com_fabric_carve_out():
    """Dispatch demo: quote_service still rejects a bare $0.00. The
    carve-outs are TWO paths and only those two paths. A bare zero
    (no com_fabric flag, no no_charge+reason) is rejected."""
    # fabric_only with unit_price=0 and yards_needed=0 → engine raises
    # at the engine layer via _require_positive.
    with pytest.raises((PricingInputError, PricingClassificationError)):
        _price_line_item(
            category="fabric_only",
            inputs={"price_per_yard": 0, "yards_needed": 0},
            business_unit="workroom",
            legacy={},
        )


def test_quote_service_rejects_no_charge_flag_without_reason():
    """The no_charge carve-out is two-keyed. Flag without reason → raised
    at the engine layer before the service sees it."""
    with pytest.raises(PricingInputError) as exc:
        _price_line_item(
            category="drapery",
            inputs={
                "window_width_in": 60, "length_in": 80, "style": "ripplefold",
                "no_charge": True,
                # no no_charge_reason
            },
            business_unit="workroom",
            legacy={},
        )
    assert "no_charge_reason" in str(exc.value)


@pytest.mark.parametrize("category,inputs", [
    ("roman_shade",   {"width_in": 0, "height_in": 60}),
    ("cover",         {"unit_price": 0, "quantity": 2}),
    ("pillow",        {"unit_price": 0, "quantity": 1}),
    ("labor",         {"hours": 0, "rate_per_hour": 65}),
    ("valance",       {"width_in": 0}),
    ("cornice",       {"width_in": 0}),
])
def test_quote_service_rejects_zero_on_other_categories(category, inputs):
    """No path other than com_fabric+customer_supplied AND no_charge+reason
    emits $0.00 through the service layer."""
    with pytest.raises((PricingInputError, PricingClassificationError)):
        _price_line_item(
            category=category,
            inputs=inputs,
            business_unit="workroom",
            legacy={},
        )


def test_quote_service_no_charge_engine_result_carries_reason():
    """The engine's no_charge result carries the reason in computed;
    quote_service threads it through into the row."""
    out = _price_line_item(
        category="drapery",
        inputs={
            "window_width_in": 60, "length_in": 80, "style": "ripplefold",
            "no_charge": True,
            "no_charge_reason": "founder waived",
        },
        business_unit="workroom",
        legacy={},
    )
    assert "no_charge" in out["computed_json"]
    parsed = json.loads(out["computed_json"])
    assert parsed["no_charge"] is True
    assert parsed["no_charge_reason"] == "founder waived"


# ===========================================================================
# 4. Issued-document provenance — quote records issued_document;
#    per-line, the rate_source
# ===========================================================================
def test_create_quote_with_issued_document_persists_on_quote_and_lines(_rebind_db_path):
    """Dispatch demo: a quote with issued_document="NELMA-814" persists
    the document on the quote AND tags every line with rate_source=
    "issued:NELMA-814" unless the line carries its own.

    Uses the session-level isolated_empire_db (D33) so the module-level
    DB_PATH captures resolve to a tmp path; the per-test truncate fixture
    wipes data tables before/after this test runs.
    """
    # Build the Becky-shape quote (one item) with issued_document
    payload = {
        "customer_name": "Becky (test)",
        "customer_address": "4600 Fieldstone",
        "project_name": "Becky test",
        "business_unit": "workroom",
        "issued_document": "NELMA-814",
        "line_items": [
            {
                "category": "manual_line",
                "description": "test line",
                "quantity": 1,
                "inputs": {
                    "description": "test line",
                    "unit_price": 100.00,
                    "quantity": 1,
                },
            },
        ],
    }
    quote = create_quote(payload)
    assert quote["issued_document"] == "NELMA-814"
    assert len(quote["line_items"]) == 1
    item = quote["line_items"][0]
    assert item["rate_source"] == "issued:NELMA-814"


def test_create_quote_without_issued_document_defaults_lines_to_catalog(_rebind_db_path):
    """A quote with no issued_document tags every line rate_source='catalog'."""
    payload = {
        "customer_name": "Catalog Test",
        "business_unit": "workroom",
        "line_items": [
            {
                "category": "manual_line",
                "description": "catalog line",
                "quantity": 1,
                "inputs": {
                    "description": "catalog line",
                    "unit_price": 50.00,
                    "quantity": 1,
                },
            },
        ],
    }
    quote = create_quote(payload)
    assert quote["issued_document"] is None
    assert len(quote["line_items"]) == 1
    item = quote["line_items"][0]
    assert item["rate_source"] == "catalog"


def test_create_quote_line_rate_source_override_wins(_rebind_db_path):
    """Caller-supplied li['rate_source'] overrides the issued_document
    default — useful when one line is governed by a different doc than
    the rest of the quote."""
    payload = {
        "customer_name": "Per-line test",
        "business_unit": "workroom",
        "issued_document": "NELMA-814",
        "line_items": [
            {
                "category": "manual_line",
                "description": "covered by NELMA-814",
                "quantity": 1,
                "rate_source": "issued:NELMA-814",
                "inputs": {
                    "description": "covered by NELMA-814",
                    "unit_price": 100.0,
                    "quantity": 1,
                },
            },
            {
                "category": "manual_line",
                "description": "covered by NELMA-815",
                "quantity": 1,
                "rate_source": "issued:NELMA-815",
                "inputs": {
                    "description": "covered by NELMA-815",
                    "unit_price": 50.0,
                    "quantity": 1,
                },
            },
        ],
    }
    quote = create_quote(payload)
    assert quote["issued_document"] == "NELMA-814"
    items = sorted(quote["line_items"], key=lambda x: x["description"])
    # "covered by NELMA-814" sorts before "covered by NELMA-815" lexically
    assert items[0]["description"] == "covered by NELMA-814"
    assert items[0]["rate_source"] == "issued:NELMA-814"
    assert items[1]["description"] == "covered by NELMA-815"
    assert items[1]["rate_source"] == "issued:NELMA-815"


# ===========================================================================
# 5. Anti-bypass — the third carve-out argument
# ===========================================================================
def test_third_carve_out_cannot_appear_silently():
    """The dispatch argument: a third $0.00 path cannot appear without
    touching quote_service._price_line_item. The 11 categories D37 wired
    through _require_positive still raise on empty/missing inputs —
    no silent-zero regression. Plus the D38 new categories all gate their
    required inputs the same way."""
    # Categories whose required inputs are _require_positive-protected.
    # Empty inputs (or inputs that don't include the protected key) raise.
    cases = [
        ("roman_shade",             {}),
        ("valance",                 {}),
        ("cornice",                 {}),
        ("fabric_only",             {}),
        ("hardware_rod_1_1_8",      {}),
        ("hardware_ripplefold_track", {}),
        ("hardware_rings",          {}),
        ("hardware_brackets",       {}),
        ("labor",                   {}),
        ("pillow",                  {}),
        ("cover",                   {}),
        ("hardware_rod_set",        {"width_in": 0}),
        ("hardware_ripplefold_set", {"width_in": 0}),
        ("installation",            {"treatment": "roman_shade", "quantity": 0}),
        ("manual_line",             {}),
    ]
    for category, inputs in cases:
        with pytest.raises((PricingInputError, PricingClassificationError)):
            price_workroom_line(category, inputs)

    # The two carve-outs BOTH pass with their flags. They are the
    # ONLY paths that emit $0.00.
    com = price_workroom_line("com_fabric", {
        "customer_supplied": True,
        "fabric_name": "Acme COM",
        "quantity": 6,
    })
    assert com["proposed_price"] == 0.0

    nc = price_workroom_line("drapery", {
        "window_width_in": 60, "length_in": 80, "style": "ripplefold",
        "no_charge": True, "no_charge_reason": "test",
    })
    assert nc["proposed_price"] == 0.0
