"""D37 / H77 — invoice #814 line-by-line proof against the engine.

Per the dispatcher's STEP 3 amendment, invoice #814 is a STRUCTURAL
reference, not a value match. The engine prices ripplefold at $110/width
(R1 founder ruling — confirmed catalog rate). The invoice's $95/width was
legacy pricing and is NOT to be hardcoded.

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
# GAP — no catalog category
# ---------------------------------------------------------------------------
def test_invoice_814_item_4_batiste_118_lining_is_a_gap():
    """Item 4: batiste 118" lining, 16 yd at $9.95/yd.

    Two reasons this is a gap:
      (a) `batiste_118` is absent from PRICING_SPECS["drapery"]["linings"].
          The drapery engine raises on unknown lining keys (engine.py:651).
      (b) Even if batiste_118 were a key, the engine computes lining
          yardage as widths × ceil(length_in/36) — it does not accept a
          free-form 16 yd input.

    R3 and R6 were HELD — do not add a category to close this gap.
    """
    with pytest.raises(PricingInputError, match="batiste_118"):
        price_workroom_line("drapery", {
            "window_width_in": 60,
            "length_in": 80,
            "lining_type": "batiste_118",
        })


def test_invoice_814_item_5_hardware_set_is_a_gap():
    """Item 5: hardware, 3 sets at $249.95/set.

    No `hardware_set` category exists in PRICING_SPECS or
    WORKROOM_LINE_PRICERS. The four `hardware_*` categories compute
    run/pack/bracket counts from window width — none accepts a flat
    "sets × $/set" structure.

    R7 was HELD.
    """
    with pytest.raises(PricingClassificationError):
        price_workroom_line("hardware_set", {"sets": 3, "rate_per_set": 249.95})


def test_invoice_814_item_6_installation_is_a_gap():
    """Item 6: installation, 3 sets at $145.00/set.

    No `installation` line pricer exists. `price_workroom_item` accepts
    `install_cost` as a sub-component inside its inputs dict, but there
    is no line-level pricer that prices "3 sets at $145/set" as a
    standalone output.

    R8 was HELD.
    """
    with pytest.raises(PricingClassificationError):
        price_workroom_line("installation", {"sets": 3, "rate_per_set": 145.00})


def test_invoice_814_item_7_bench_is_a_gap():
    """Item 7: benches, 2 each at $895.00/each.

    No `bench` category in WORKROOM_LINE_PRICERS. The legacy
    `upholstery` alias routes through `price_workroom_item`'s composite
    formula (fabric + labor + materials), not as a flat $/each.

    R9 was HELD.
    """
    with pytest.raises(PricingClassificationError):
        price_workroom_line("bench", {"quantity": 2, "unit_price": 895.00})


def test_invoice_814_item_1_com_fabric_is_a_gap():
    """Item 1: COM (customer-supplied) fabric, 6 yd — no rate on invoice.

    The engine has no concept of "customer supplied material". A `price_fabric`
    line with price_per_yard=0 would now raise (zero-guard), which is the
    desired behaviour — a $0.00 fabric line reaching a client is exactly the
    defect the zero-guard prevents.

    R13 was HELD. Do not add a customer_supplied flag to close this gap.
    """
    with pytest.raises(PricingInputError):
        price_workroom_line("fabric_only", {
            "price_per_yard": 0,
            "yards_needed": 6,
        })


# ---------------------------------------------------------------------------
# Subtotal arithmetic — only the structural-match items contribute.
# The instruction is clear: items 1, 4, 5, 6, 7 are gaps. The subtotal
# the engine can produce today is only items 2 + 3 = $1100.00. Do not
# invent prices to back-fill the gaps.
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
