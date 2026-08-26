"""D37 / H77 — pricing engine zero-guard.

Every workroom line pricer that could previously return $0.00 silently for
zero/missing inputs now raises PricingInputError naming the category and the
missing input. This is the same defect class as H76 — defense lives at the
engine layer so the silent-zero failure mode is unreachable regardless of
caller.

Founders rule per dispatch 2026-08-26:
  - roman_shade    : width_in AND height_in required
  - fabric_only    : price_per_yard AND yards_needed required
  - cover          : unit_price required
  - valance        : width_in required
  - cornice        : width_in required
  - labor          : hours required
  - pillow         : unit_price required
  - hardware_rod   : width_in required
  - hardware_ripplefold_track : width_in required
  - hardware_rings : packs required
  - hardware_brackets : width_in OR explicit count required
"""
import pytest

from app.services.pricing.engine import (
    PricingInputError,
    price_workroom_line,
)


# ---------------------------------------------------------------------------
# ZERO-PATH — each pricer refuses to price when required inputs are absent
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("category", [
    "roman_shade", "fabric_only", "cover", "valance", "cornice",
    "labor", "pillow",
    "hardware_rod_1_1_8", "hardware_ripplefold_track",
    "hardware_rings", "hardware_brackets",
])
def test_pricer_raises_on_empty_inputs(category):
    """Every workroom line pricer raises PricingInputError on empty inputs."""
    with pytest.raises(PricingInputError) as exc:
        price_workroom_line(category, {})
    # The error names the category AND tells the founder what's missing.
    msg = str(exc.value)
    assert category in msg, f"error message must name category '{category}': got {msg!r}"
    assert "refusing to price to 0.00" in msg, (
        f"error message must include the zero-guard intent: got {msg!r}"
    )


@pytest.mark.parametrize("category,key", [
    ("roman_shade", "width_in"),
    ("roman_shade", "height_in"),
    ("fabric_only", "price_per_yard"),
    ("fabric_only", "yards_needed"),
    ("cover", "unit_price"),
    ("valance", "width_in"),
    ("cornice", "width_in"),
    ("labor", "hours"),
    ("pillow", "unit_price"),
    ("hardware_rod_1_1_8", "width_in"),
    ("hardware_ripplefold_track", "width_in"),
    ("hardware_rings", "packs"),
])
def test_pricer_raises_on_missing_specific_key(category, key):
    """When only the named key is missing, the error names that key."""
    # Give the pricer a complete input set, then drop the key under test.
    full = _complete_inputs(category)
    full.pop(key, None)
    with pytest.raises(PricingInputError) as exc:
        price_workroom_line(category, full)
    msg = str(exc.value)
    assert category in msg
    assert key in msg, f"error must name key '{key}': got {msg!r}"


@pytest.mark.parametrize("category,key", [
    ("roman_shade", "width_in"),
    ("roman_shade", "height_in"),
    ("fabric_only", "price_per_yard"),
    ("fabric_only", "yards_needed"),
    ("cover", "unit_price"),
    ("valance", "width_in"),
    ("cornice", "width_in"),
    ("labor", "hours"),
    ("pillow", "unit_price"),
    ("hardware_rod_1_1_8", "width_in"),
    ("hardware_ripplefold_track", "width_in"),
    ("hardware_rings", "packs"),
])
def test_pricer_raises_when_supplied_input_is_zero(category, key):
    """A supplied-but-zero value does NOT slip through to a $0.00 output.

    This closes the caller-side hole at quote_service.py:73-87 — even with
    another non-zero key (e.g. quantity=1) the engine itself refuses.
    """
    full = _complete_inputs(category)
    full[key] = 0
    with pytest.raises(PricingInputError) as exc:
        price_workroom_line(category, full)
    msg = str(exc.value)
    assert category in msg
    assert key in msg


# ---------------------------------------------------------------------------
# DRAPERY — unknown lining still raises (existing behaviour preserved)
# ---------------------------------------------------------------------------
def test_drapery_unknown_lining_type_raises():
    """batiste_118 is absent from the catalog; passing it as lining_type raises
    rather than pricing at 0.00. Same behaviour as any unknown lining key."""
    with pytest.raises(PricingInputError) as exc:
        price_workroom_line("drapery", {
            "window_width_in": 60,
            "length_in": 80,
            "lining_type": "batiste_118",
        })
    assert "batiste_118" in str(exc.value)


def test_drapery_known_lining_premiere_satin_prices():
    """premiere_satin ($9.95/yd) is in the catalog and still prices."""
    result = price_workroom_line("drapery", {
        "window_width_in": 60,
        "length_in": 80,  # < 120" → no over-floor escalation
        "style": "regular",
        "lining_type": "premiere_satin",
    })
    assert result["proposed_price"] > 0
    assert result["computed"]["lining_type"] == "premiere_satin"
    assert result["computed"]["lining_cost"] > 0


# ---------------------------------------------------------------------------
# POSITIVE — confirmed rates still produce the rate the founder ruled
# ---------------------------------------------------------------------------
def test_ripplefold_prices_by_width_count_at_110_per_width():
    """Founder R1 ruling: ripplefold base rate stays at $110.00/width
    (NOT the legacy invoice #814 rate of $95.00). The engine prices drapery
    as widths × $/width; invoice #814 is a STRUCTURAL reference, not a
    value match. At $110/width, 6 widths = $660 and 4 widths = $440."""
    six_widths = price_workroom_line("drapery", {
        "window_width_in": 120,  # ceil(120*2.5/54) = 6
        "length_in": 96,         # < 120" — base rate applies
        "style": "ripplefold",
        "fullness": 2.5,
        "fabric_width_in": 54,
    })
    four_widths = price_workroom_line("drapery", {
        "window_width_in": 75,   # ceil(75*2.5/54) = 4
        "length_in": 96,
        "style": "ripplefold",
        "fullness": 2.5,
        "fabric_width_in": 54,
    })
    assert six_widths["computed"]["widths"] == 6
    assert four_widths["computed"]["widths"] == 4
    assert six_widths["computed"]["price_per_width"] == 110.0
    assert four_widths["computed"]["price_per_width"] == 110.0
    # Structural rate, not legacy invoice match — values diverge from $570/$380.
    assert six_widths["proposed_price"] == 660.0
    assert four_widths["proposed_price"] == 440.0


def test_roman_shade_prices_at_19_95_per_sqft():
    """PRICING_SPECS["roman_shade"]["base_rate"] is 19.95."""
    result = price_workroom_line("roman_shade", {"width_in": 30, "height_in": 60})
    assert result["computed"]["rate_per_sqft"] == 19.95
    assert result["proposed_price"] == round(30 * 60 / 144 * 19.95, 2)


def test_cover_with_founder_supplied_unit_price():
    result = price_workroom_line("cover", {"unit_price": 150, "quantity": 2})
    assert result["proposed_price"] == 300.0


def test_fabric_only_with_founder_supplied_rate_and_yards():
    result = price_workroom_line("fabric_only", {"price_per_yard": 30, "yards_needed": 4})
    assert result["proposed_price"] == 120.0


# ---------------------------------------------------------------------------
# HELD CATEGORIES — batiste_118, hardware_set, installation, bench, COM
# are NOT in the catalog and the engine refuses to price them.
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("category", [
    "batiste_118",
    "hardware_set",
    "installation",
    "bench",
    "customer_supplied",
    "com",
])
def test_held_category_unknown_to_engine(category):
    """Founder R3, R6, R7, R8, R9, R13: these categories stay absent. The
    engine must not silently swallow them and produce a $0.00 fallback."""
    with pytest.raises(Exception) as exc:
        price_workroom_line(category, {"unit_price": 100, "quantity": 1})
    # PricingClassificationError is what price_workroom_line raises for
    # unknown categories; PricingInputError is what it raises for known
    # categories with missing inputs. Either is acceptable — what matters
    # is that the engine never returns 0.00.
    assert not isinstance(exc.value, AssertionError)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _complete_inputs(category: str) -> dict:
    """Return a complete set of inputs for *category* — used so a per-key
    drop test only isolates the key under test."""
    if category == "roman_shade":
        return {"width_in": 30, "height_in": 60}
    if category == "fabric_only":
        return {"price_per_yard": 30, "yards_needed": 4}
    if category == "cover":
        return {"unit_price": 150, "quantity": 2}
    if category == "valance":
        return {"width_in": 96}
    if category == "cornice":
        return {"width_in": 96}
    if category == "labor":
        return {"hours": 2, "rate_per_hour": 65}
    if category == "pillow":
        return {"unit_price": 35, "quantity": 1}
    if category == "hardware_rod_1_1_8":
        return {"width_in": 96}
    if category == "hardware_ripplefold_track":
        return {"width_in": 96}
    if category == "hardware_rings":
        return {"widths": 4, "packs": 4}
    if category == "hardware_brackets":
        return {"width_in": 96}
    raise AssertionError(f"unknown category {category!r}")
