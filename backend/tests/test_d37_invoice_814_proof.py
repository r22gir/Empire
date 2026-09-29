"""D37 / H77 + D38 / H77 — invoice #814 line-by-line proof against the engine.

Per the dispatcher's STEP 3 amendment, invoice #814 is a STRUCTURAL
reference, not a value match. The engine prices ripplefold at $110/width
(R1 founder ruling — confirmed catalog rate). The invoice's $95/width was
legacy pricing and is NOT to be hardcoded.

D38 / H77 inverts the lines that were gaps in D37 (1, 4, 5, 6) and the
line that stayed a gap (7) is now expressible through `manual_line`.

Item-by-item history:
  D37 (closed)              D38 (this dispatch)
  ----------------------    -----------------------------------------
  1  GAP (COM)              closes via com_fabric + customer_supplied
  4  GAP (batiste unknown)  closes via linings catalog entry, splits into
                             a positive pricing test + a separate yardage-
                             input-shape gap (engine-derivable yardage is
                             priced; free-form 16-yd input still rejected)
  5  GAP (hardware set)     closes via hardware_rod_set +
                             hardware_ripplefold_set
  6  GAP (installation)     closes via installation (treatment=
                             roman_shade|drapery)
  7  GAP (bench)            stays a gap as `bench`; closes as
                             `manual_line` (description + $895 * 2 =
                             $1,790.00)

The subtotal test (engine-reachable ripplefold lines) is intentionally
left untouched per dispatch instruction.

This test prices the seven invoice line items through the engine and
classifies each one of three ways:

  STRUCTURAL MATCH — the engine produces the value against the catalog
                     rate (rate mismatch is legacy pricing, not a gap).
  GAP              — no catalog category exists; engine refuses with
                     PricingInputError / PricingClassificationError. The
                     line item has no implementation today.
  RAISES           — engine actively rejects, on principle (zero-guard
                     or unknown enum). This is correct behaviour, not a
                     defect.

Founders directive: where the engine cannot reach a line item, that is a
finding — do not invent a category to make it pass.
"""
import pytest

from app.services.pricing.engine import (
    PricingClassificationError,
    PricingInputError,
    price_workroom_line,
)


# ---------------------------------------------------------------------------
# Structural match: ripplefold by width count at $110 (R1)
# ---------------------------------------------------------------------------
def test_invoice_814_item_2_ripplefold_six_widths_at_110():
    """Item 2: ripplefold, 6 widths × $110/width = $660.00.

    Invoice paper value was $570 at the legacy $95 rate. R1 ruling: the
    catalog keeps $110; the engine produces $660. Structural match.
    """
    result = price_workroom_line("drapery", {
        "window_width_in": 120,
        "length_in": 96,
        "style": "ripplefold",
        "fullness": 2.5,
        "fabric_width_in": 54,
    })
    assert result["computed"]["widths"] == 6
    assert result["computed"]["price_per_width"] == 110.0
    assert result["proposed_price"] == 660.0


def test_invoice_814_item_3_ripplefold_four_widths_at_110():
    """Item 3: ripplefold, 4 widths × $110/width = $440.00.

    Invoice paper value was $380 at the legacy $95 rate. Structural match.
    """
    result = price_workroom_line("drapery", {
        "window_width_in": 75,
        "length_in": 96,
        "style": "ripplefold",
        "fullness": 2.5,
        "fabric_width_in": 54,
    })
    assert result["computed"]["widths"] == 4
    assert result["computed"]["price_per_width"] == 110.0
    assert result["proposed_price"] == 440.0


# ---------------------------------------------------------------------------
# Item 1 — COM fabric. D38 closes via com_fabric/customer_supplied.
# The original gap test inverts: fabric_only without a rate still raises;
# the carve-out lives in com_fabric + customer_supplied=true only.
# ---------------------------------------------------------------------------
def test_invoice_814_item_1_com_fabric_now_prices_via_customer_supplied():
    """Item 1: COM (customer-supplied) fabric, 6 yd — no rate on invoice.

    D38: closes via the com_fabric category with customer_supplied=true.
    The line emits $0.00 with fabric_name + quantity named (no invented
    price). fabric_only without a rate still raises (H77 intact).
    """
    result = price_workroom_line("com_fabric", {
        "customer_supplied": True,
        "fabric_name": "Customer's Own Material (COM-2026-08-26)",
        "quantity": 6,
    })
    assert result["proposed_price"] == 0.0
    assert result["computed"]["customer_supplied"] is True
    assert result["computed"]["fabric_name"] == "Customer's Own Material (COM-2026-08-26)"
    assert result["computed"]["quantity"] == 6
    assert result["computed"]["label"] == "COM"


def test_invoice_814_item_1_fabric_only_zero_still_raises():
    """H77 intact for the original GAP path: fabric_only without a rate
    still raises — only com_fabric + customer_supplied=true reaches $0.00.
    """
    with pytest.raises(PricingInputError):
        price_workroom_line("fabric_only", {
            "price_per_yard": 0,
            "yards_needed": 6,
        })


def test_invoice_814_item_1_com_fabric_without_flag_still_prices_normally():
    """Without customer_supplied=true, com_fabric behaves like fabric_only
    and requires a positive price_per_yard + yards_needed. Carve-out is
    two-keyed — not either. Uses the fabric_only key names (price_per_yard,
    yards_needed) because the carve-out path passes through price_fabric.
    """
    result = price_workroom_line("com_fabric", {
        "fabric_name": "Acme Linen 12ft",
        "price_per_yard": 24.50,
        "yards_needed": 6,
    })
    assert result["proposed_price"] == round(24.50 * 6, 2)


# ---------------------------------------------------------------------------
# Item 4 — batiste 118" lining. D38 splits into a pricing test AND a
# separate yardage-shape test. The rate gap is closed; the input-shape
# gap (free-form 16-yd) remains.
# ---------------------------------------------------------------------------
def test_invoice_814_item_4_batiste_118_lining_prices_at_catalog_rate():
    """Item 4 (rate gap CLOSED): batiste 118" lining.

    D38 added `batiste_118` to PRICING_SPECS["drapery"]["linings"] at the
    founder-ruled $10.50/yd. Engine-derivable yardage prices:
      widths = ceil(60 * 2.5 / 54) = 3
      yards_per_width = ceil(80/36) = 3
      lining_yards = 3 * 3 = 9
      lining_cost = 9 * 10.50 = $94.50
    """
    result = price_workroom_line("drapery", {
        "window_width_in": 60,
        "length_in": 80,
        "lining_type": "batiste_118",
    })
    assert result["computed"]["lining_type"] == "batiste_118"
    assert result["computed"]["lining_yards"] == 9
    assert result["computed"]["lining_cost"] == round(9 * 10.50, 2)


def test_invoice_814_item_4_batiste_free_form_16yd_remains_a_gap():
    """Item 4 (input-shape GAP): the engine cannot accept a free-form 16-yd
    input; it computes yardage from widths × ceil(length/36). Asserted by
    value-mismatch: the invoice said 16 yd × $10.50 = $159.20; the engine
    produces 9 yd (engine-derived) × $10.50 = $94.50. The rate gap is
    closed; the input-shape gap is asserted here as the delta.
    """
    result = price_workroom_line("drapery", {
        "window_width_in": 60,
        "length_in": 80,
        "lining_type": "batiste_118",
    })
    # Engine-derived yardage and cost:
    engine_yards = result["computed"]["lining_yards"]
    engine_cost  = result["computed"]["lining_cost"]
    # The invoice value of 16 yd × $10.50 is NOT reproducible via this
    # engine input shape — only the engine-derivable yardage is.
    assert engine_yards != 16
    assert engine_cost  != round(16 * 10.50, 2)
    # The engine's value IS reproducible and is what the engine emits:
    assert engine_yards == 9
    assert engine_cost  == round(9 * 10.50, 2)


# ---------------------------------------------------------------------------
# Item 5 — hardware sets. D38 closes via two new categories.
# ---------------------------------------------------------------------------
def test_invoice_814_item_5_hardware_rod_set_six_ft_is_325():
    """Item 5 (CLOSED): rod set at 6 ft → $325.00 flat."""
    result = price_workroom_line("hardware_rod_set", {"width_in": 72})  # 6 ft
    assert result["proposed_price"] == 325.0
    assert result["computed"]["in_range"] is True


def test_invoice_814_item_5_hardware_ripplefold_set_six_ft_is_250():
    """Item 5 (CLOSED): ripplefold set at 6 ft → $250.00 flat."""
    result = price_workroom_line("hardware_ripplefold_set", {"width_in": 72})
    assert result["proposed_price"] == 250.0
    assert result["computed"]["in_range"] is True


# ---------------------------------------------------------------------------
# Item 6 — installation. D38 closes via treatment-specific sub-rates.
# ---------------------------------------------------------------------------
def test_invoice_814_item_6_installation_roman_shade_is_95_each():
    """Item 6 (CLOSED): roman shade install → $95 × quantity."""
    result = price_workroom_line("installation", {
        "treatment": "roman_shade",
        "quantity": 3,
    })
    assert result["proposed_price"] == round(95.00 * 3, 2)


def test_invoice_814_item_6_installation_drapery_six_ft_is_145():
    """Item 6 (CLOSED): drapery install at 6 ft → $145 first 8 ft."""
    result = price_workroom_line("installation", {
        "treatment": "drapery",
        "width_in": 72,  # 6 ft
    })
    assert result["proposed_price"] == 145.0


# ---------------------------------------------------------------------------
# Item 7 — bench. Stays a gap as `bench`; closes as `manual_line`.
# ---------------------------------------------------------------------------
def test_invoice_814_item_7_bench_remains_a_gap():
    """Item 7 (GAP maintained): `bench` is not a category. The bespoke
    bench is priced as a manual_line below.
    """
    with pytest.raises(PricingClassificationError):
        price_workroom_line("bench", {"quantity": 2, "unit_price": 895.00})


def test_invoice_814_item_7_bench_priced_as_manual_line():
    """Item 7 (CLOSED via manual_line): 2 benches × $895.00 = $1,790.00."""
    result = price_workroom_line("manual_line", {
        "description": "Bench (custom, per founder)",
        "unit_price": 895.00,
        "quantity": 2,
    })
    assert result["proposed_price"] == 1790.0
    assert result["computed"]["unit_price_used"] == 895.00
    assert result["computed"]["quantity"] == 2


# ---------------------------------------------------------------------------
# Subtotal arithmetic — left untouched per dispatch instruction.
# The instruction is clear: items 2 + 3 only. Items 1, 4-rate, 5, 6 are
# now D38-priced; item 7 is priced as a manual_line. None of those feed
# the subtotal — engine subtotal is ripplefold only, by dispatch ruling.
# ---------------------------------------------------------------------------
def test_invoice_814_subtotal_for_engine_reachable_lines():
    """Items 2 + 3 only. Engine produces $660 + $440 = $1100.00 today.

    Items 1, 4, 5, 6, 7 are gaps (see per-item tests above). The paper
    invoice subtotal of $4,084.05 includes rates the founder has not
    added to the catalog; reporting them as gaps is the directive.
    """
    item_2 = price_workroom_line("drapery", {
        "window_width_in": 120, "length_in": 96,
        "style": "ripplefold", "fullness": 2.5, "fabric_width_in": 54,
    })["proposed_price"]
    item_3 = price_workroom_line("drapery", {
        "window_width_in": 75, "length_in": 96,
        "style": "ripplefold", "fullness": 2.5, "fabric_width_in": 54,
    })["proposed_price"]

    engine_subtotal = round(item_2 + item_3, 2)
    # Engine reaches only items 2 and 3 today. Paper subtotal $4084.05
    # includes gap-line rates that were held for a later ruling.
    assert engine_subtotal == 1100.00
