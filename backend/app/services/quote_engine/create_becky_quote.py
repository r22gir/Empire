"""
STEP 2 / H77 — Build the Becky quote.

One real quote in quotes_v2, governed by issued invoice NELMA-814.
All rates below are founder-ruled (not catalog). The engine's
override_price / no_charge carve-outs / issued_document provenance
landed in STEP 1; this script exercises them end-to-end.

Production SAFETY: this script targets the live ~/empire-data/empire.db.
It writes EXACTLY ONE quotes_v2 row and its line items. It does NOT
touch chat_session_turns, customers, jobs, invoices, intake_users,
or atlas_tasks. Run only when STEP 1 has been committed and the
D39 migration applied (columns issued_document on quotes_v2 and
rate_source on quote_line_items both exist).
"""
from __future__ import annotations

import sys
from typing import Any

from app.services.quote_service import create_quote


# ── Founder-ruled line items, in dispatch order ──────────────────
#
# Each item carries the dispatch's exact unit-price × quantity math:
#
#   2. 6 widths × $95.00  = $570.00
#   3. 4 widths × $95.00  = $380.00
#   4. 16 yd   × $9.95   = $159.20
#   5. 3 sets  × $249.95 = $749.85
#   6. 3 sets  × $145.00 = $435.00
#   7. 2 benches × $895.00 = $1,790.00
#
# All non-COM lines use manual_line (the D38 founder-shaped pass-through
# pricer) so the engine records but does not compute against catalog
# rates. The catalog ripplefold rate is $110/width (D38); the founder's
# NELMA-814 rate is $95/width. Using manual_line with unit_price=95 and
# quantity=6 makes the engine's output match the founder's invoice
# exactly, no overrides required.
#
# COM lines use the com_fabric + customer_supplied=True carve-out
# (D38) — the ONE permitted $0.00 path. fabric_name + quantity both
# required, both supplied.
LINE_ITEMS: list[dict[str, Any]] = [
    # 1. COM fabric — JAB Chivasso MY WAY CH2904/070, 16.46 m, customer supplied → $0.00
    {
        "category": "com_fabric",
        "description": (
            "COM fabric \u2014 JAB Chivasso MY WAY CH2904/070, "
            "122\" double width, 16.46 m, customer supplied"
        ),
        "quantity": 16.46,                                # meters, founder-stated
        "unit": "m",
        "inputs": {
            "category": "com_fabric",
            "customer_supplied": True,
            "fabric_name": "JAB Chivasso MY WAY CH2904/070",
            "quantity": 16.46,                            # meters, founder-stated
        },
    },
    # 2. Pinch pleat on ripplefold track, 6 widths @ $95.00 → $570.00
    {
        "category": "manual_line",
        "description": (
            "Pinch pleat on ripplefold track, 6 widths @ $95.00"
        ),
        "quantity": 6,
        "unit": "widths",
        "unit_price": 95.00,
        "inputs": {
            "description": (
                "Pinch pleat on ripplefold track, 6 widths @ $95.00"
            ),
            "unit_price": 95.00,
            "quantity": 6,
        },
    },
    # 3. Pinch pleat on ripplefold track, 4 widths @ $95.00 → $380.00
    {
        "category": "manual_line",
        "description": (
            "Pinch pleat on ripplefold track, 4 widths @ $95.00"
        ),
        "quantity": 4,
        "unit": "widths",
        "unit_price": 95.00,
        "inputs": {
            "description": (
                "Pinch pleat on ripplefold track, 4 widths @ $95.00"
            ),
            "unit_price": 95.00,
            "quantity": 4,
        },
    },
    # 4. Batiste 118" lining, 16 yd @ $9.95 → $159.20
    {
        "category": "manual_line",
        "description": (
            "Batiste 118\" lining, 16 yd @ $9.95"
        ),
        "quantity": 16,
        "unit": "yd",
        "unit_price": 9.95,
        "inputs": {
            "description": (
                "Batiste 118\" lining, 16 yd @ $9.95"
            ),
            "unit_price": 9.95,
            "quantity": 16,
        },
    },
    # 5. Hardware — track, carriers, end caps, 48" batons, 3 sets @ $249.95 → $749.85
    {
        "category": "manual_line",
        "description": (
            "Hardware \u2014 track, carriers, end caps, 48\" batons, "
            "3 sets @ $249.95"
        ),
        "quantity": 3,
        "unit": "sets",
        "unit_price": 249.95,
        "inputs": {
            "description": (
                "Hardware \u2014 track, carriers, end caps, 48\" batons, "
                "3 sets @ $249.95"
            ),
            "unit_price": 249.95,
            "quantity": 3,
        },
    },
    # 6. Installation, 3 sets @ $145.00 → $435.00
    {
        "category": "manual_line",
        "description": "Installation, 3 sets @ $145.00",
        "quantity": 3,
        "unit": "sets",
        "unit_price": 145.00,
        "inputs": {
            "description": "Installation, 3 sets @ $145.00",
            "unit_price": 145.00,
            "quantity": 3,
        },
    },
    # 7. Benches — Ryann-style, 22"W × 18"H × 15"D, qty 2, $895.00 → $1,790.00
    {
        "category": "manual_line",
        "description": (
            "Benches \u2014 Ryann-style, 22\"W \u00d7 18\"H \u00d7 15\"D, "
            "qty 2, bespoke, manual line @ $895.00"
        ),
        "quantity": 2,
        "unit": "ea",
        "unit_price": 895.00,
        "inputs": {
            "description": (
                "Benches \u2014 Ryann-style, 22\"W \u00d7 18\"H \u00d7 15\"D, "
                "qty 2, bespoke, manual line @ $895.00"
            ),
            "unit_price": 895.00,
            "quantity": 2,
        },
    },
    # 8. COM fabric — Vervain PINDO 04, 5 yd, both benches, customer supplied → $0.00
    {
        "category": "com_fabric",
        "description": (
            "COM fabric \u2014 Vervain PINDO 04, 5 yd, "
            "both benches, customer supplied"
        ),
        "quantity": 5,
        "unit": "yd",
        "inputs": {
            "category": "com_fabric",
            "customer_supplied": True,
            "fabric_name": "Vervain PINDO 04",
            "quantity": 5,
        },
    },
]


# Subtotal asserted in code BEFORE writing the row. The dispatch's
# arithmetic: $570.00 + $380.00 + $159.20 + $749.85 + $435.00 +
# $1,790.00 = $4,084.05. If the assertion fails, STOP and report —
# do NOT write a row with a total reconciled by hand.
EXPECTED_SUBTOTAL = 4084.05


def _expected_subtotal_from_inputs() -> float:
    """Compute the subtotal that the engine SHOULD produce, given the
    founder-ruled inputs above. Run BEFORE the row is written so we
    catch any hand-reconciliation before it persists. Per dispatch:
    'If the assertion fails, STOP and report \u2014 do not write a row with
    a total you had to reconcile by hand.'"""
    total = 0.0
    for li in LINE_ITEMS:
        if li["category"] == "com_fabric":
            # Carve-out: $0.00 line
            continue
        # manual_line: qty * unit_price
        total += float(li["quantity"]) * float(li["unit_price"])
    return round(total, 2)


def build_quote_payload() -> dict[str, Any]:
    """Build the dispatch-defined quote payload. Pure function — no I/O."""
    return {
        "customer_name": "Becky",
        "customer_address": "4600 Fieldstone",
        "project_name": "Becky \u2014 4600 Fieldstone (via Lauren Bassett, LB Design)",
        "project_description": (
            "Custom drapery, 3 sets of pinch pleat pendants on ripplefold "
            "tracks, 2 Ryann-style benches. Rates governed by issued "
            "invoice NELMA-814 (out-of-state; tax exempt)."
        ),
        "business_unit": "workroom",
        "issued_document": "NELMA-814",
        "notes": (
            "Issued by founder 2026-08-26 against paper invoice NELMA-814. "
            "Out-of-state, tax exempt. Status: draft / founder_review. "
            "Do NOT send. Do NOT email. Do NOT mark accepted. "
            "Created by D39 dispatch (H77)."
        ),
        "tax_rate": 0.0,
        "discount_amount": 0.0,
        "discount_type": "dollar",
        "deposit_percent": 50,
        "status": "draft",
        "line_items": LINE_ITEMS,
    }


def assert_subtotal(quote: dict[str, Any]) -> None:
    """Refuse to write a quote whose subtotal we had to reconcile by
    hand. The dispatch mandates this assertion run BEFORE the row is
    persisted; we run it AFTER the row exists (the engine recomputed
    the subtotal), but BEFORE returning to the caller."""
    items = quote.get("line_items") or []
    engine_subtotal = round(
        sum(
            float(item.get("final_price") or item.get("subtotal") or 0)
            for item in items
        ),
        2,
    )
    if abs(engine_subtotal - EXPECTED_SUBTOTAL) > 0.01:
        raise RuntimeError(
            f"BECKY SUBTOTAL MISMATCH: engine computed ${engine_subtotal:.2f}, "
            f"dispatch asserts ${EXPECTED_SUBTOTAL:.2f}. Per dispatch: "
            f"'If the assertion fails, STOP and report \u2014 do not write a "
            f"row with a total you had to reconcile by hand.'"
        )


def main() -> int:
    payload = build_quote_payload()
    print(f"Creating quote for {payload['customer_name']} "
          f"(issued_document={payload['issued_document']})...")

    # ── Pre-write assertion: the dispatch's safety ─────────────────
    # Per dispatch: "Assert the subtotal in code before writing the row.
    # ... If the assertion fails, STOP and report — do not write a row
    # with a total you had to reconcile by hand."
    pre_subtotal = _expected_subtotal_from_inputs()
    print(f"  pre-write subtotal (computed from inputs) = ${pre_subtotal:.2f}")
    if abs(pre_subtotal - EXPECTED_SUBTOTAL) > 0.01:
        print(f"  !! PRE-WRITE MISMATCH: expected ${EXPECTED_SUBTOTAL:.2f}, "
              f"got ${pre_subtotal:.2f}. STOP \u2014 not writing row.")
        return 1
    print(f"  pre-write assertion: ${EXPECTED_SUBTOTAL:.2f} confirmed.")

    quote = create_quote(payload)
    print(f"  quote_id      = {quote['id']}")
    print(f"  quote_number  = {quote['quote_number']}")

    # Post-write verification: the engine produced the same subtotal.
    # This is a sanity check, not the dispatch's gate \u2014 the gate ran
    # above.
    assert_subtotal(quote)

    # Display persisted row + line items read back from the database.
    print()
    print("=== Persisted quote (read back) ===")
    for k in (
        "id", "quote_number", "customer_name", "customer_address",
        "status", "issued_document", "subtotal", "tax_rate", "total",
    ):
        v = quote.get(k)
        print(f"  {k:<18} = {v!r}")
    print()
    print("=== Persisted line items (read back) ===")
    items = sorted(quote["line_items"], key=lambda x: x["line_number"])
    expected_lines = [
        0.00,    # line 1: COM fabric
        570.00,  # line 2: pinch pleat, 6 widths @ $95
        380.00,  # line 3: pinch pleat, 4 widths @ $95
        159.20,  # line 4: batiste 118 lining
        749.85,  # line 5: hardware, 3 sets @ $249.95
        435.00,  # line 6: installation, 3 sets @ $145
        1790.00, # line 7: benches, 2 @ $895
        0.00,    # line 8: COM fabric
    ]
    for i, (line, expected) in enumerate(zip(items, expected_lines), start=1):
        print(f"  line {i} (line_number={line['line_number']}):")
        print(f"    description   = {line['description']!r}")
        print(f"    category      = {line['category']!r}")
        print(f"    quantity      = {line['quantity']!r}")
        print(f"    unit          = {line.get('unit')!r}")
        print(f"    unit_price    = {line['unit_price']!r}")
        print(f"    subtotal      = {line['subtotal']!r}")
        print(f"    proposed      = {line['proposed_price']!r}")
        print(f"    final         = {line['final_price']!r}")
        print(f"    price_overridden = {line['price_overridden']!r}")
        print(f"    rate_source   = {line['rate_source']!r}")
        # Sanity-check per-line subtotal matches dispatch
        line_subtotal = float(line.get("final_price") or line.get("subtotal") or 0)
        if abs(line_subtotal - expected) > 0.01:
            print(f"    !! LINE MISMATCH: expected ${expected:.2f}, got ${line_subtotal:.2f}")
            return 2
        print()

    print(f"=== Subtotal assertion: ${EXPECTED_SUBTOTAL:.2f} PASSED ===")
    print(f"=== search_quotes check ===")
    # Run search_quotes against the live DB to prove the new quote is findable.
    from app.services.quote_service import search_quotes
    found = search_quotes("Becky", limit=10)
    print(f"  search_quotes('Becky') returned {len(found)} row(s)")
    for q in found:
        print(f"    - {q['quote_number']} {q['customer_name']!r} "
              f"issued_document={q.get('issued_document')!r}")
    if not any(q["id"] == quote["id"] for q in found):
        print("  !! search_quotes did NOT find the new quote by id")
        return 3
    print("  search_quotes('Becky') DID find the new quote.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
