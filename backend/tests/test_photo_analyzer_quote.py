"""Photo Analyzer items must land on a Workroom quotes-v2 row.

Save to Quote used to POST the legacy JSON /quotes store. Workroom lists
/quotes-v2?business_unit=workroom, so the alert said the quote was saved and
the line items were nowhere in Workroom. Catalog `labor` lines from the photo
path also cannot be written as-is: the pricing engine requires `hours`.
"""
from __future__ import annotations

import pytest


def test_measure_photo_lines_are_manual_and_priced():
    from app.services.quote_engine.photo_quote_lines import lines_from_photo_measure

    lines = lines_from_photo_measure({
        "width_inches": 36,
        "height_inches": 60,
        "window_type": "double-hung",
    })
    assert len(lines) == 2
    assert all(line["category"] == "manual_line" for line in lines)
    assert lines[0]["quantity"] == pytest.approx(3.8)
    assert lines[0]["unit_price"] == pytest.approx(45)
    assert lines[0]["amount"] == pytest.approx(171)
    assert lines[1]["unit_price"] == pytest.approx(150)
    assert lines[1]["amount"] == pytest.approx(150)
    assert "36" in lines[0]["description"] and "60" in lines[0]["description"]


def test_qis_labor_display_line_is_not_catalog_labor():
    from app.services.quote_engine.photo_quote_lines import as_workroom_quote_line

    line = as_workroom_quote_line({
        "category": "labor",
        "description": "Left Wall Window reupholstery",
        "quantity": 1,
        "unit": "ea",
        "rate": 380,
        "amount": 380,
    })
    assert line["category"] == "manual_line"
    assert line["unit_price"] == pytest.approx(380)
    assert "hours" not in (line.get("inputs") or {})


def test_photo_lines_create_and_update_a_workroom_quote(isolated_empire_db):
    from app.services.quote_engine.photo_quote_lines import (
        lines_from_analyzed_items,
        lines_from_photo_measure,
    )
    from app.services.quote_service import add_line_item, create_quote, get_quote, list_quotes

    measure_lines = lines_from_photo_measure({
        "width_inches": 36,
        "height_inches": 60,
        "window_type": "double-hung",
    })
    created = create_quote({
        "customer_name": "Photo Analyzer Customer",
        "business_unit": "workroom",
        "pricing_mode": "flat",
        "tax_rate": 0,
        "project_name": "AI Photo Analysis",
        "line_items": measure_lines,
    })
    assert created["business_unit"] == "workroom"
    by_desc = {line["description"]: line for line in created["line_items"]}
    fabric = next(line for desc, line in by_desc.items() if "Fabric" in desc)
    labor = next(line for desc, line in by_desc.items() if desc.endswith("Labor"))
    assert fabric["amount"] == pytest.approx(171)
    assert fabric["rate"] == pytest.approx(45)
    assert labor["amount"] == pytest.approx(150)
    assert created["subtotal"] == pytest.approx(321)
    assert created["total"] == pytest.approx(321)

    listed = list_quotes(business_unit="workroom", limit=50)
    assert any(row["id"] == created["id"] for row in listed["quotes"])

    analyzed = lines_from_analyzed_items(
        [
            {"name": "Left Wall Window", "description": "Left Wall Window", "type": "drapery_panel", "selected": True},
            {"description": "Skip me", "type": "valance", "selected": False, "width": 20, "height": 20},
        ],
        quote={
            "tiers": {
                "A": {
                    "items": [{
                        "name": "Left Wall Window",
                        "line_items": [{
                            "category": "labor",
                            "description": "Left Wall Window reupholstery",
                            "quantity": 1,
                            "unit": "ea",
                            "rate": 380,
                            "amount": 380,
                        }],
                    }],
                }
            }
        },
    )
    assert len(analyzed) == 1
    assert analyzed[0]["category"] == "manual_line"
    updated = add_line_item(created["id"], analyzed[0])
    descriptions = [line["description"] for line in updated["line_items"]]
    assert "Left Wall Window reupholstery" in descriptions
    assert any("Fabric" in desc for desc in descriptions)
    assert "Skip me" not in descriptions

    chair = lines_from_analyzed_items([
        {"type": "dining_chair_seat", "description": "Dining Chair Set", "quantity": 6, "selected": True},
    ])
    assert chair[0]["category"] == "note"
    with_note = add_line_item(created["id"], chair[0])
    note = next(line for line in with_note["line_items"] if line["description"] == "Dining Chair Set")
    assert note["amount"] == pytest.approx(0)

    reloaded = get_quote(created["id"])
    assert len(reloaded["line_items"]) == 4
