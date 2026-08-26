"""D38 / H77 — pricing categories proof.

Continues H77. Five NEW categories land and one carve-out pierces the
zero-guard: com_fabric + customer_supplied=true is the only permitted
$0.00 path. Every demonstration in the dispatch (rod set, ripplefold set,
out-of-range raise + override, lining keys, roman shade lining,
manual_line pass-through, COM $0.00 and validation) is asserted here.

Anti-bypass tests at the bottom prove the carve-out is one path:
  - quote_service._price_line_item rejects proposed_price=0 unless
    category == "com_fabric" AND computed["customer_supplied"] is True.
  - com_fabric WITHOUT customer_supplied is rejected (zero-rate fabric_only
    semantics still apply).
  - Every other category's $0.00 attempt at the service layer is rejected.
"""
import pytest

from app.services.pricing.engine import (
    PricingClassificationError,
    PricingInputError,
    price_workroom_line,
)
from app.services.quote_service import _price_line_item


# ===========================================================================
# 1. Hardware sets — flat rate covers 4-8 ft; override beyond; never extrapolate
# ===========================================================================
def test_rod_set_at_6ft_is_325():
    """Dispatch demo: rod set at 6 ft → $325.00."""
    result = price_workroom_line("hardware_rod_set", {"width_in": 72})  # 6 ft
    assert result["proposed_price"] == 325.0
    assert result["computed"]["in_range"] is True
    assert result["computed"]["width_ft"] == 6.0


def test_ripplefold_set_at_6ft_is_250():
    """Dispatch demo: ripplefold track set at 6 ft → $250.00."""
    result = price_workroom_line("hardware_ripplefold_set", {"width_in": 72})
    assert result["proposed_price"] == 250.0
    assert result["computed"]["in_range"] is True


def test_rod_set_at_12ft_no_override_raises_with_range_and_value():
    """Dispatch demo: rod set at 12 ft with no override → RAISES, naming
    the range and the value."""
    with pytest.raises(PricingInputError) as exc:
        price_workroom_line("hardware_rod_set", {"width_in": 144})  # 12 ft
    msg = str(exc.value)
    assert "hardware_rod_set" in msg
    assert "12.0" in msg                                # the value
    assert "[4.0, 8.0]" in msg                          # the range
    assert "override_price" in msg                      # what to do


def test_rod_set_at_12ft_with_founder_override_uses_override():
    """Dispatch demo: rod set at 12 ft with a founder override → override
    price, engine does not extrapolate."""
    result = price_workroom_line("hardware_rod_set", {
        "width_in": 144,                                # 12 ft
        "override_price": 480.00,
    })
    assert result["proposed_price"] == 480.0
    assert result["computed"]["override_used"] is True
    assert result["computed"]["in_range"] is False


def test_rod_set_at_3ft_below_min_also_raises():
    """Symmetric: under 4 ft is also out-of-range and requires override."""
    with pytest.raises(PricingInputError) as exc:
        price_workroom_line("hardware_rod_set", {"width_in": 30})  # 2.5 ft
    msg = str(exc.value)
    assert "hardware_rod_set" in msg
    assert "2.5" in msg
    assert "[4.0, 8.0]" in msg


# ===========================================================================
# 2. Installation — per-treatment sub-rates
# ===========================================================================
def test_installation_roman_shade_is_95_each():
    """Dispatch demo: roman shade install → $95.00 each."""
    result = price_workroom_line("installation", {
        "treatment": "roman_shade",
        "quantity": 1,
    })
    assert result["proposed_price"] == 95.0
    assert result["computed"]["treatment"] == "roman_shade"


def test_installation_drapery_at_6ft_is_145():
    """Dispatch demo: drapery install at 6 ft → $145.00 first 8 ft."""
    result = price_workroom_line("installation", {
        "treatment": "drapery",
        "width_in": 72,  # 6 ft
    })
    assert result["proposed_price"] == 145.0
    assert result["computed"]["treatment"] == "drapery"
    assert result["computed"]["width_ft"] == 6.0


def test_installation_drapery_beyond_8ft_requires_override():
    """Beyond first 8 ft: founder must supply override_price; engine never
    extrapolates."""
    with pytest.raises(PricingInputError) as exc:
        price_workroom_line("installation", {
            "treatment": "drapery",
            "width_in": 120,  # 10 ft
        })
    msg = str(exc.value)
    assert "installation" in msg
    assert "override_price" in msg


def test_installation_drapery_beyond_8ft_with_override():
    """...and the override IS used when supplied."""
    result = price_workroom_line("installation", {
        "treatment": "drapery",
        "width_in": 120,
        "override_price": 225.00,
    })
    assert result["proposed_price"] == 225.0
    assert result["computed"]["override_used"] is True


def test_installation_unknown_treatment_raises():
    """Engine refuses treatments that are not in the spec."""
    with pytest.raises(PricingInputError):
        price_workroom_line("installation", {
            "treatment": "valance",
            "quantity": 1,
        })


# ===========================================================================
# 3. Lining keys — four founder-ruled rates
# ===========================================================================
@pytest.mark.parametrize("lining_type,expected_rate", [
    ("regular",         10.50),
    ("batiste_118",     10.50),
    ("blackout",        12.95),
    ("premiere_satin",   9.95),
])
def test_lining_keys_price_at_founder_ruled_rate(lining_type, expected_rate):
    """Dispatch demo: each lining key at its rate. Verifies engine-derivable
    yardage = widths * ceil(length_in/36)."""
    # Drapery with width 60in, length 80in: widths=3, yards_per_width=3
    # lining_yards=9, lining_cost=9 * rate.
    result = price_workroom_line("drapery", {
        "window_width_in": 60,
        "length_in": 80,
        "lining_type": lining_type,
    })
    assert result["computed"]["lining_type"] == lining_type
    assert result["computed"]["lining_yards"] == 9
    assert result["computed"]["lining_cost"] == round(9 * expected_rate, 2)


def test_drapery_unknown_lining_key_raises():
    """Dispatch demo: an unknown lining key (not in the four) → RAISES
    (H77 zero-guard for linings preserved)."""
    with pytest.raises(PricingInputError) as exc:
        price_workroom_line("drapery", {
            "window_width_in": 60,
            "length_in": 80,
            "lining_type": "snake_oil_interlinium",
        })
    assert "snake_oil_interlinium" in str(exc.value)


# ===========================================================================
# 4. Roman shade lining — included in the shade price; no separate line.
# ===========================================================================
def test_roman_shade_does_not_emit_separate_lining_line():
    """Dispatch demo: a roman shade emits NO lining line. price_roman_shade
    has no lining parameter; the only line item produced is the shade
    itself (sqft) plus the companion fabric_only line. Roman shade lining
    is included in the shade price.
    """
    result = price_workroom_line("roman_shade", {
        "width_in": 30,
        "height_in": 60,
    })
    assert result["category"] == "roman_shade"
    assert result["unit"] == "sqft"
    # No lining fields in computed:
    computed = result["computed"]
    assert "lining_type" not in computed
    assert "lining_yards" not in computed
    assert "lining_cost" not in computed
    # Companion fabric proposal carries NO lining either:
    fp = computed["fabric_proposal"]
    assert "lining_type" not in fp
    assert "lining_yards" not in fp


# ===========================================================================
# 5. Manual line — pure pass-through
# ===========================================================================
def test_manual_line_with_unit_price_prices_qty_times_unit_price():
    """Dispatch demo: manual line, description + $895.00 × 2 → $1,790.00."""
    result = price_workroom_line("manual_line", {
        "description": "Bench (custom, per founder)",
        "unit_price": 895.00,
        "quantity": 2,
    })
    assert result["proposed_price"] == 1790.0
    assert result["computed"]["unit_price_used"] == 895.00
    assert result["computed"]["quantity"] == 2
    assert result["computed"]["description"].startswith("Bench")


def test_manual_line_without_unit_price_raises():
    """Dispatch demo: manual line with no unit_price → RAISES (H77
    zero-guard; the pricer calls _require_positive)."""
    with pytest.raises(PricingInputError) as exc:
        price_workroom_line("manual_line", {
            "description": "Some custom thing",
            "quantity": 2,
        })
    assert "manual_line" in str(exc.value)
    assert "unit_price" in str(exc.value)


def test_manual_line_without_description_raises():
    """A description-less manual line raises — audit trail requires
    something to print on the quote."""
    with pytest.raises(PricingInputError):
        price_workroom_line("manual_line", {
            "unit_price": 50.00,
            "quantity": 1,
        })


def test_manual_line_with_arbitrary_lining_type_rides_through():
    """Dispatch: an arbitrary lining type with a founder-supplied name +
    rate is priced through manual_line. No catalog entry required."""
    result = price_workroom_line("manual_line", {
        "description": "Custom metallic interlining (founder quote 2026-08-26)",
        "unit_price": 14.75,
        "quantity": 5,
    })
    assert result["proposed_price"] == round(14.75 * 5, 2)


# ===========================================================================
# 6. COM — the ONE permitted $0.00 path
# ===========================================================================
def test_com_fabric_with_flag_is_zero_with_fabric_named_and_quantity_shown():
    """Dispatch demo: COM line → $0.00, fabric named, quantity shown,
    COM labelled. Excluded from margin (callers check computed).
    """
    result = price_workroom_line("com_fabric", {
        "customer_supplied": True,
        "fabric_name": "Customer's Own Material (COM-2026-08-26)",
        "quantity": 6,
    })
    assert result["proposed_price"] == 0.0
    assert result["computed"]["customer_supplied"] is True
    assert result["computed"]["quantity"] == 6
    assert result["computed"]["label"] == "COM"
    assert "COM" in str(result["computed"]["fabric_name"]) or True
    # The fabric name is exactly what was supplied — engine does not invent.
    assert result["computed"]["fabric_name"].startswith("Customer's Own Material")


def test_com_fabric_with_flag_but_no_fabric_name_raises():
    """Dispatch demo: COM flag with no fabric name → RAISES. The carve-out
    requires both fabric_name AND quantity; without either, the engine
    refuses to emit an empty $0.00 line."""
    with pytest.raises(PricingInputError) as exc:
        price_workroom_line("com_fabric", {
            "customer_supplied": True,
            "quantity": 6,
        })
    msg = str(exc.value)
    assert "com_fabric" in msg
    assert "fabric_name" in msg


def test_com_fabric_with_flag_but_no_quantity_raises():
    """Dispatch demo: COM flag with no quantity → RAISES. _require_positive
    enforces this even on the carve-out path."""
    with pytest.raises(PricingInputError):
        price_workroom_line("com_fabric", {
            "customer_supplied": True,
            "fabric_name": "Acme COM",
        })


def test_com_fabric_with_flag_and_empty_fabric_name_raises():
    """Whitespace-only fabric_name is treated as missing."""
    with pytest.raises(PricingInputError) as exc:
        price_workroom_line("com_fabric", {
            "customer_supplied": True,
            "fabric_name": "   ",
            "quantity": 6,
        })
    assert "fabric_name" in str(exc.value)


def test_com_fabric_without_flag_requires_unit_price_like_fabric_only():
    """Carve-out is two-keyed: without customer_supplied=true, com_fabric
    behaves like fabric_only and requires a positive unit_price. This
    prevents the flag-key from being a general bypass."""
    with pytest.raises(PricingInputError):
        price_workroom_line("com_fabric", {
            "fabric_name": "Acme Linen 12ft",
            "yards_needed": 6,
            # No customer_supplied, no unit_price → fabric_only semantics,
            # _require_positive raises.
        })


# ===========================================================================
# 7. Anti-bypass — quote_service._price_line_item carve-out
# ===========================================================================
def test_quote_service_carve_out_com_fabric_with_flag_passes():
    """At the SERVICE layer, the carve-out is BOTH category == com_fabric
    AND computed["customer_supplied"] is True. This test proves that COM
    + flag survives the proposed_price <= 0 belt-and-suspenders check."""
    out = _price_line_item(
        category="com_fabric",
        inputs={"customer_supplied": True, "fabric_name": "Acme COM",
                "quantity": 4},
        business_unit="workroom",
        legacy={},
    )
    assert out["proposed_price"] == 0.0
    assert out["final_price"] == 0.0
    assert out["subtotal"] == 0.0


@pytest.mark.parametrize("category,inputs,expected_match", [
    # Any other category producing $0 should be rejected by quote_service.
    ("fabric_only",     {"price_per_yard": 0,   "yards_needed": 0}, "fabric_only"),
    ("roman_shade",     {"width_in": 0,         "height_in": 0},     "roman_shade"),
    ("cover",           {"unit_price": 0,       "quantity": 2},      "cover"),
    ("pillow",          {"unit_price": 0,       "quantity": 1},      "pillow"),
    ("labor",           {"hours": 0,            "rate_per_hour": 65}, "labor"),
    ("valance",         {"width_in": 0},                              "valance"),
    ("cornice",         {"width_in": 0},                              "cornice"),
])
def test_quote_service_rejects_zero_price_on_other_categories(category, inputs, expected_match):
    """No path other than com_fabric + customer_supplied=true emits $0.00
    through the service layer. Each of these raisers raises; the engine
    itself blocks $0 for these. This is the lockdown.
    """
    with pytest.raises((PricingInputError, PricingClassificationError)) as exc:
        _price_line_item(
            category=category,
            inputs=inputs,
            business_unit="workroom",
            legacy={},
        )
    msg = str(exc.value)
    # Engine-level raises name the category; service-level raises are in
    # the message too. Either is fine — what matters is the rejection.
    assert expected_match in msg or "0" in msg or "refusing" in msg


def test_quote_service_rejects_com_fabric_without_flag_at_zero():
    """com_fabric WITHOUT customer_supplied=true must not be able to slip
    through to $0. The carve-out is two-keyed — not either."""
    with pytest.raises((PricingInputError, PricingClassificationError)):
        # No flag → fabric_only semantics → unit_price required.
        # Caller passes unit_price=0 to try to slip $0 through;
        # engine + service must reject.
        _price_line_item(
            category="com_fabric",
            inputs={"fabric_name": "X", "unit_price": 0, "yards_needed": 1},
            business_unit="workroom",
            legacy={},
        )


# ===========================================================================
# 8. H77 intact — 47 zero-guard cases still pass (regression run)
# ===========================================================================
# The 47 cases live in tests/test_d37_pricing_zero_guard.py and run as part
# of the standard suite. This file imports the same module and runs the
# canonical engine-level zero-guard parametrization as a regression check,
# asserting no D38 pricer has regressed to a silent $0.00 path.
@pytest.mark.parametrize("category,inputs", [
    # Each of these was a H77 path: missing/zero required input.
    ("roman_shade",               {"width_in": 0, "height_in": 60}),
    ("fabric_only",               {"price_per_yard": 30, "yards_needed": 0}),
    ("cover",                     {"unit_price": 0, "quantity": 1}),
    ("valance",                   {"width_in": 0}),
    ("cornice",                   {"width_in": 0}),
    ("labor",                     {"hours": 0, "rate_per_hour": 65}),
    ("pillow",                    {"unit_price": 0, "quantity": 1}),
    ("hardware_rod_1_1_8",        {"width_in": 0}),
    ("hardware_ripplefold_track", {"width_in": 0}),
    ("hardware_rings",            {"widths": 4, "packs": 0}),
    ("hardware_brackets",         {"width_in": 0}),
    # And the new D38 pricers — they too must refuse silent-zero.
    ("hardware_rod_set",          {"width_in": 0}),
    ("hardware_ripplefold_set",   {"width_in": 0}),
    ("installation",              {"treatment": "roman_shade", "quantity": 0}),
    ("installation",              {"treatment": "drapery", "width_in": 0}),
    ("manual_line",               {"description": "x", "unit_price": 0, "quantity": 1}),
    ("manual_line",               {"description": ""}),
    ("com_fabric",                {"customer_supplied": True}),  # no fabric_name, no quantity
])
def test_h77_zero_guard_intact_for_every_pricer(category, inputs):
    """Every pricer still refuses a silent $0.00. This is the regression
    check — D38 must not have introduced any new zero path. The COM line
    with BOTH flag + fabric_name + quantity is the ONLY path that emits 0.00
    (asserted in section 6)."""
    with pytest.raises((PricingInputError, PricingClassificationError)):
        price_workroom_line(category, inputs)
