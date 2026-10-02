"""Estimate PDF keeps each section, shows yardage, and clears the footer."""
from __future__ import annotations

import io

from app.services.estimates.mclean_estimate_pdf import (
    CONTENT_BOTTOM,
    group_estimate_sections,
    render_mclean_estimate_bytes,
)


def _quote() -> dict:
    notes = "\n".join(
        f"Install note {i}: confirm site access before the crew arrives."
        for i in range(1, 28)
    )
    notes += "\nYARDAGE-NOTE-MARKER stays above the footer."
    return {
        "id": "q-296",
        "quote_number": "EST-2026-296",
        "customer_name": "Client House",
        "customer_address": "100 Main Street",
        "project_name": "Living room drapery",
        "status": "draft",
        "created_at": "2026-10-01",
        "billed_by": "nelmas_workroom",
        "notes": notes,
        "line_items": [
            {"description": "SECTION — Drapery", "unit": "section"},
            {
                "description": "Living room panels",
                "section": "Drapery",
                "category": "com_fabric",
                "quantity": 12.5,
                "unit": "yd",
                "rate": 18.5,
            },
            {
                "description": "COM lining",
                "section": "Drapery",
                "category": "com_fabric",
                "quantity": 8,
                "unit": "yd",
                "unit_price": 6,
            },
            {"description": "SECTION — Hardware", "unit": "section"},
            {
                "description": "Reeded rods",
                "section": "Hardware",
                "quantity": 3,
                "unit": "widths",
                "unit_price": 40,
                "amount": 120,
            },
        ],
        "subtotal": 399.25,
        "tax_rate": 0,
        "tax_amount": 0,
        "total": 399.25,
    }


def test_sections_keep_yardage_lines():
    sections = group_estimate_sections(_quote()["line_items"])
    names = [name for name, _lines in sections]
    assert names == ["Drapery", "Hardware"]
    drapery = sections[0][1]
    assert len(drapery) == 2
    assert drapery[0]["quantity"] == 12.5
    assert "Extra work" not in names


def test_rendered_quote_shows_qty_rate_and_keeps_notes_above_the_footer():
    pdf = render_mclean_estimate_bytes(_quote())
    assert pdf[:4] == b"%PDF"
    from pypdf import PdfReader

    reader = PdfReader(io.BytesIO(pdf))
    text = "\n".join((page.extract_text() or "") for page in reader.pages)
    flat = " ".join(text.split())
    squashed = "".join(text.split()).upper()
    # Letterhead is tracked, so the brand name is checked without spaces.
    assert "EMPIREWORKROOM" in squashed
    assert "NELMA" not in squashed
    assert "RAFAEL" not in squashed
    assert "DRAPERY" in squashed
    assert "HARDWARE" in squashed
    assert "EXTRAWORK" not in squashed
    assert "12.5" in flat and "yd" in flat
    assert "widths" in flat
    assert "18.50" in flat
    assert "231.25" in flat
    assert "120.00" in flat
    assert "YARDAGE-NOTE-MARKER" in flat

    positions = []

    def visitor(text_run, _cm, tm, _font, _size):
        if text_run and "YARDAGE-NOTE-MARKER" in text_run:
            positions.append(float(tm[5]))

    for page in reader.pages:
        page.extract_text(visitor_text=visitor)
    assert positions, "note marker was not placed on a page"
    assert min(positions) >= CONTENT_BOTTOM


def test_overridden_line_amount_is_the_final_price():
    pdf = render_mclean_estimate_bytes({
        "quote_number": "EST-OVR",
        "customer_name": "Client House",
        "status": "draft",
        "created_at": "2026-10-01",
        "line_items": [
            {
                "description": "Panels",
                "quantity": 1,
                "unit_price": 1800,
                "subtotal": 1800,
                "price_overridden": 1,
                "final_price": 1933.33,
            },
            {
                "description": "Install",
                "quantity": 1,
                "unit_price": 1200,
                "subtotal": 1200,
            },
        ],
    })
    from pypdf import PdfReader
    text = "\n".join(
        (page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages
    )
    flat = " ".join(text.split())
    assert "1,933.33" in flat
    assert "1,200.00" in flat
    assert "3,133.33" in flat
