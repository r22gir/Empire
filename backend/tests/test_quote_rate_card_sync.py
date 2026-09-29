"""Pricing Studio rate cards drive Workroom and WoodCraft quote dollars.

Dimension text on the quote/PDF path is fractions or whole inches.
"""
import io

import pytest

from app.services.pricing.dimensions import (
    format_design_dimensions,
    format_inches,
    quote_item_dimension_text,
)
from app.services.pricing.quote_sync import (
    apply_canonical_cnc_pricing,
    canonical_cnc_cost,
    canonical_fabrication_price,
    studio_calculate,
)
from app.services.pricing.rate_cards import lookup_rate
from app.services.quote_engine.line_item_builder import build_line_items
from app.services.quote_service import _price_line_item


def test_lookup_rate_is_the_engine_default_card():
    assert lookup_rate("workroom", "labor_rate") == 65
    assert lookup_rate("woodcraft", "machine_rate_per_hour") == 95
    assert lookup_rate("woodcraft", "design_rate") == 85
    assert lookup_rate("woodcraft", "assembly_rate") == 75
    with pytest.raises(KeyError):
        lookup_rate("woodcraft", "not_a_rate")


def test_workroom_quote_line_matches_pricing_studio():
    inputs = {"finished_width": 48, "finished_length": 84}
    studio = studio_calculate("workroom", {"item_type": "drapery", "pricing_inputs": inputs})
    line = _price_line_item("drapery", inputs, "workroom", {})
    assert studio["calculated_subtotal"] == line["proposed_price"]
    assert line["proposed_price"] > 0

    built = build_line_items(
        {
            "name": "Living room drapery",
            "type": "drapery",
            "dimensions": {"width": 48, "height": 84},
            "quantity": 1,
        },
        tier="A",
        lining="none",
    )
    labor = next(item for item in built if item["category"] == "labor")
    assert labor["amount"] == studio["calculated_subtotal"]
    assert "14." not in labor["description"]


def test_ripplefold_quote_uses_studio_style_rate():
    dims = {"width": 60, "height": 96}
    studio = studio_calculate(
        "workroom",
        {"item_type": "drapery_ripplefold", "pricing_inputs": dims},
    )
    fabrication = canonical_fabrication_price("drapery_ripplefold", dims)
    assert fabrication == studio["calculated_subtotal"]
    regular = canonical_fabrication_price("drapery", dims)
    assert fabrication != regular


def test_woodcraft_cnc_quote_matches_pricing_studio():
    minutes = 90
    studio = studio_calculate(
        "woodcraft",
        {"product_category": "cnc_router_time", "pricing_inputs": {"CNC_time_minutes": minutes}},
    )
    expected = round(minutes / 60 * lookup_rate("woodcraft", "machine_rate_per_hour"), 2)
    assert studio["calculated_subtotal"] == expected
    assert canonical_cnc_cost(minutes) == expected

    line = _price_line_item("cnc_router_time", {"CNC_time_minutes": minutes}, "woodcraft", {})
    assert line["proposed_price"] == expected
    assert line["business_unit"] == "woodcraft"


def test_saved_woodcraft_design_reprices_cnc_from_rate_card():
    data = apply_canonical_cnc_pricing({
        "cnc_jobs": [{"estimated_time_min": 60}],
        "cnc_time_cost": 90,
        "subtotal": 90,
        "total": 90,
        "margin_percent": 0,
        "discount_amount": 0,
        "discount_type": "dollar",
        "tax_rate": 0,
    })
    assert data["cnc_time_cost"] == 95
    assert data["cnc_rate_per_hour"] == 95
    assert data["total"] == 95

    again = apply_canonical_cnc_pricing(dict(data))
    assert again["cnc_time_cost"] == 95
    assert again["total"] == 95


def test_inches_display_as_fractions_or_whole_inches():
    assert format_inches(14.5) == '14½"'
    assert format_inches(72) == '72"'
    assert format_inches(72.0) == '72"'
    assert format_inches("72.00") == '72"'
    assert format_inches(14.25) == '14¼"'
    assert format_inches(0.5) == '½"'
    assert "14.5" not in format_inches(14.5)
    assert "72.00" not in format_inches("72.00")

    phrase = quote_item_dimension_text({"width": 14.5, "height": 72.00, "depth": 0})
    assert phrase == '14½" × 72"'
    assert format_design_dimensions(14.5, 72, None, "in") == '14½" W × 72" H'


def test_quote_pdf_dimension_line_uses_fractions(monkeypatch, tmp_path):
    from app.services import quote_pdf_service

    quote = {
        "id": "q-frac",
        "quote_number": "EST-FRAC",
        "customer_name": "Fraction Test",
        "status": "draft",
        "created_at": "2026-09-28",
        "line_items": [{
            "description": "Drapery panel",
            "width": 14.5,
            "height": 72.00,
            "quantity": 1,
            "unit_price": 285,
            "subtotal": 285,
        }],
        "subtotal": 285,
        "tax_rate": 0,
        "tax_amount": 0,
        "total": 285,
    }
    monkeypatch.setattr(quote_pdf_service, "get_quote", lambda _id: quote)
    monkeypatch.setattr(quote_pdf_service, "quote_pdf_dir", lambda: tmp_path)

    pdf_bytes = quote_pdf_service.generate_quote_pdf("q-frac")
    assert pdf_bytes[:4] == b"%PDF"

    text = _pdf_text(pdf_bytes)
    assert '14½"' in text or "14½" in text
    assert "72.00" not in text
    assert "14.5" not in text


def _pdf_text(pdf_bytes: bytes) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        from PyPDF2 import PdfReader
    reader = PdfReader(io.BytesIO(pdf_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)
