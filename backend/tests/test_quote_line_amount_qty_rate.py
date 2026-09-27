"""Quote Review Amount must be quantity × rate for qty > 1.

Live symptom (Workroom Quote Review, flat_math):
  BR Roman   qty 2  rate $590  amount $590   (should be $1,180)
  Optional p qty 2  rate $60   amount $60    (should be $120)

Root cause: quote_line_items.unit_price was aliased straight to `rate`
and subtotal straight to `amount`. For manual_line the engine's
proposed_price (the line total) was stored in BOTH columns, and rows
whose quantity was not the quantity the engine priced kept subtotal
equal to the unit rate. flat_math requires amount == qty × rate.
"""
from __future__ import annotations

import json
import sqlite3

import pytest


def test_line_rate_amount_extends_unextended_qty():
    """Screenshot shape: stored unit, subtotal, and rate are the same number."""
    from app.services.quote_service import _line_rate_and_amount

    rate, amount = _line_rate_and_amount({
        "quantity": 2,
        "unit_price": 590,
        "subtotal": 590,
        "final_price": 590,
        "price_overridden": 0,
        "computed_json": json.dumps({
            "unit_price_used": 590,
            "quantity": 1,
            "description": "BR Roman",
        }),
    })
    assert rate == pytest.approx(590)
    assert amount == pytest.approx(1180)


def test_line_rate_amount_does_not_double_when_column_is_line_total():
    """Older rows stored the line total in unit_price. Do not charge it twice."""
    from app.services.quote_service import _line_rate_and_amount

    rate, amount = _line_rate_and_amount({
        "quantity": 2,
        "unit_price": 1180,  # historical: column held qty × unit
        "subtotal": 1180,
        "final_price": 1180,
        "price_overridden": 0,
        "computed_json": json.dumps({
            "unit_price_used": 590,
            "quantity": 2,
        }),
    })
    assert rate == pytest.approx(590)
    assert amount == pytest.approx(1180)


def test_line_rate_amount_qty_one_and_override_unchanged():
    from app.services.quote_service import _line_rate_and_amount

    rate, amount = _line_rate_and_amount({
        "quantity": 1,
        "unit_price": 2400,
        "subtotal": 2400,
        "final_price": 1933.33,
        "price_overridden": 1,
    })
    assert rate == pytest.approx(1933.33)
    assert amount == pytest.approx(1933.33)


def test_flat_math_screenshot_lines(isolated_empire_db):
    """BR Roman 2×$590 and Optional 2×$60 must extend; flat_math passes."""
    from app.services.quote_engine.verification import verify_quote
    from app.services.quote_service import create_quote

    quote = create_quote({
        "customer_name": "ManualLine LiveProof",
        "business_unit": "workroom",
        "pricing_mode": "flat",
        "tax_rate": 0,
        "line_items": [
            {
                "category": "note",
                "description": "COM face",
                "quantity": 1,
                "unit": "sqft",
                "unit_price": 0,
            },
            {
                "category": "manual_line",
                "description": "LR STAT d",
                "quantity": 1,
                "unit": "sqft",
                "unit_price": 485,
                "inputs": {
                    "description": "LR STAT d",
                    "unit_price": 485,
                    "quantity": 1,
                },
            },
            {
                "category": "manual_line",
                "description": "BR Roman",
                "quantity": 2,
                "unit": "ea",
                "unit_price": 590,
                "inputs": {
                    "description": "BR Roman",
                    "unit_price": 590,
                    "quantity": 2,
                },
            },
            {
                "category": "manual_line",
                "description": "Optional p",
                "quantity": 2,
                "unit": "ea",
                "unit_price": 60,
                "inputs": {
                    "description": "Optional p",
                    "unit_price": 60,
                    "quantity": 2,
                },
            },
        ],
    })

    by_desc = {li["description"]: li for li in quote["line_items"]}
    assert by_desc["COM face"]["amount"] == pytest.approx(0)
    assert by_desc["LR STAT d"]["rate"] == pytest.approx(485)
    assert by_desc["LR STAT d"]["amount"] == pytest.approx(485)
    assert by_desc["BR Roman"]["quantity"] == pytest.approx(2)
    assert by_desc["BR Roman"]["rate"] == pytest.approx(590)
    assert by_desc["BR Roman"]["amount"] == pytest.approx(1180)
    assert by_desc["BR Roman"]["unit_price"] == pytest.approx(590)
    assert by_desc["Optional p"]["rate"] == pytest.approx(60)
    assert by_desc["Optional p"]["amount"] == pytest.approx(120)
    # 0 + 485 + 1180 + 120
    assert quote["subtotal"] == pytest.approx(1785)
    assert quote["total"] == pytest.approx(1785)

    result = verify_quote(quote)
    flat = next(c for c in result["checks"] if c["name"] == "flat_math")
    assert flat["passed"], flat


def test_get_quote_repairs_unextended_stored_row(isolated_empire_db):
    """DB row still has amount==rate at qty 2. The API response extends it."""
    from app.services.quote_engine.verification import verify_quote
    from app.services.quote_service import create_quote, get_quote

    created = create_quote({
        "customer_name": "Unextended Roman",
        "business_unit": "workroom",
        "pricing_mode": "flat",
        "tax_rate": 0,
        "line_items": [
            {
                "category": "manual_line",
                "description": "BR Roman",
                "quantity": 1,
                "unit": "ea",
                "unit_price": 590,
                "inputs": {
                    "description": "BR Roman",
                    "unit_price": 590,
                    "quantity": 1,
                },
            },
            {
                "category": "manual_line",
                "description": "Optional p",
                "quantity": 1,
                "unit": "ea",
                "unit_price": 60,
                "inputs": {
                    "description": "Optional p",
                    "unit_price": 60,
                    "quantity": 1,
                },
            },
        ],
    })
    qid = created["id"]

    conn = sqlite3.connect(isolated_empire_db)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute(
            """
            UPDATE quote_line_items
               SET quantity = 2, unit_price = 590, subtotal = 590,
                   proposed_price = 590, final_price = 590
             WHERE quote_id = ? AND description = 'BR Roman'
            """,
            (qid,),
        )
        conn.execute(
            """
            UPDATE quote_line_items
               SET quantity = 2, unit_price = 60, subtotal = 60,
                   proposed_price = 60, final_price = 60
             WHERE quote_id = ? AND description = 'Optional p'
            """,
            (qid,),
        )
        # Quote totals still the unextended sum, matching the live screen.
        conn.execute(
            """
            UPDATE quotes_v2
               SET subtotal = 650, tax_amount = 0, total = 650,
                   tax_rate = 0, discount_amount = 0
             WHERE id = ?
            """,
            (qid,),
        )
        conn.commit()
    finally:
        conn.close()

    quote = get_quote(qid)
    by_desc = {li["description"]: li for li in quote["line_items"]}
    assert by_desc["BR Roman"]["rate"] == pytest.approx(590)
    assert by_desc["BR Roman"]["amount"] == pytest.approx(1180)
    assert by_desc["Optional p"]["rate"] == pytest.approx(60)
    assert by_desc["Optional p"]["amount"] == pytest.approx(120)
    assert quote["subtotal"] == pytest.approx(1300)
    assert quote["total"] == pytest.approx(1300)

    result = verify_quote(quote)
    flat = next(c for c in result["checks"] if c["name"] == "flat_math")
    assert flat["passed"], flat


def test_resave_does_not_double_qty_line(isolated_empire_db):
    """Echoing the review payload back through PATCH must keep qty × rate."""
    from app.services.quote_service import create_quote, get_quote, update_quote

    created = create_quote({
        "customer_name": "Resave Roman",
        "business_unit": "workroom",
        "pricing_mode": "flat",
        "tax_rate": 0,
        "line_items": [
            {
                "category": "manual_line",
                "description": "BR Roman",
                "quantity": 2,
                "unit": "ea",
                "unit_price": 590,
                "inputs": {
                    "description": "BR Roman",
                    "unit_price": 590,
                    "quantity": 2,
                },
            },
        ],
    })
    assert created["total"] == pytest.approx(1180)

    again = update_quote(created["id"], {
        "line_items": created["line_items"],
        "business_unit": "workroom",
    })
    item = again["line_items"][0]
    assert item["quantity"] == pytest.approx(2)
    assert item["rate"] == pytest.approx(590)
    assert item["amount"] == pytest.approx(1180)
    assert again["total"] == pytest.approx(1180)

    # And a third read stays stable.
    loaded = get_quote(created["id"])
    assert loaded["line_items"][0]["amount"] == pytest.approx(1180)
    assert loaded["total"] == pytest.approx(1180)
