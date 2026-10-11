"""Estimate PDF keeps each section, shows yardage, and clears the footer."""
from __future__ import annotations

import io

from app.services.estimates.mclean_estimate_pdf import (
    CONTENT_BOTTOM,
    _qty_with_unit,
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


def _296_line(
    description: str,
    qty: float,
    rate: float = 0,
    *,
    unit: str = "ea",
    category: str = "rate_needed",
) -> dict:
    amount = round(float(qty) * float(rate), 2)
    return {
        "description": description,
        "quantity": qty,
        "unit": unit,
        "rate": rate,
        "amount": amount,
        "category": category,
    }


def _296_items() -> list[dict]:
    """Shape of the deployed EST-2026-296 lines: phase in the description,
    category rate_needed, and the unit written on the line rather than in unit.
    """
    return [
        _296_line(
            "Phase 1 — Downstairs Living Room: Remove existing panels, "
            "per width — 8 widths ESTIMATE — RATE NEEDED",
            8,
        ),
        _296_line(
            "Phase 1 — Downstairs Living Room: White lining, per yard "
            "(Pricing Studio lining rate) — 32 yd",
            32,
            10.50,
        ),
        _296_line(
            "Phase 2 — Upstairs A/B/C/D: White lining, per yard "
            "(Pricing Studio lining rate) — 136 yd",
            136,
            10.50,
        ),
        _296_line(
            "Blackout lining fabric, 14 yd",
            14,
            category="materials",
        ),
        _296_line(
            "Install clips",
            2,
            4,
            category="labor",
        ),
    ]


def test_qty_uses_description_unit_when_stored_unit_is_each():
    items = _296_items()
    assert _qty_with_unit(items[0]) == "8 widths"
    assert _qty_with_unit(items[1]) == "32 yd"
    assert _qty_with_unit(items[2]) == "136 yd"
    assert _qty_with_unit(items[3]) == "14 yd"
    assert _qty_with_unit(items[4]) == "2 ea"
    assert _qty_with_unit({"description": "Panels", "quantity": 3, "unit": "widths"}) == "3 widths"


def test_rate_needed_is_not_a_section_and_subtotals_follow_the_phase():
    sections = group_estimate_sections(_296_items())
    names = [name for name, _lines in sections]
    assert names == [
        "Phase 1 — Downstairs Living Room",
        "Phase 2 — Upstairs A/B/C/D",
        "Materials",
        "Labor",
    ]
    assert "Rate Needed" not in names
    phase_1 = sections[0][1]
    assert len(phase_1) == 2
    assert phase_1[1]["rate"] == 10.50

    pdf = render_mclean_estimate_bytes({
        "quote_number": "EST-2026-296",
        "customer_name": "Dahlia Design",
        "customer_address": "Vienna / Ashburn, VA",
        "project_name": "Nehal Elrefai — Ripplefold drapery rework",
        "status": "draft",
        "created_at": "2026-10-02",
        "line_items": _296_items(),
    })
    from pypdf import PdfReader

    text = "\n".join(
        (page.extract_text() or "") for page in PdfReader(io.BytesIO(pdf)).pages
    )
    flat = " ".join(text.split())
    squashed = "".join(text.split()).upper()
    assert "8 widths" in flat
    assert "32 yd" in flat
    assert "136 yd" in flat
    assert "14 yd" in flat
    assert "2 ea" in flat
    assert "RATE NEEDED" in flat
    assert "PHASE 1 — DOWNSTAIRS LIVING ROOM" in flat
    assert "PHASE 2 — UPSTAIRS A/B/C/D" in flat
    assert "MATERIALS" in squashed
    assert "SUBTOTAL — Phase 1 — Downstairs Living Room" in flat
    assert "SUBTOTAL — Phase 2 — Upstairs A/B/C/D" in flat
    assert "$336.00" in flat
    assert "$1,428.00" in flat
    assert "SUBTOTAL — Rate Needed" not in flat
    assert "SUBTOTAL — RATE NEEDED" not in flat


def test_wrapped_description_row_grows_past_the_next_row():
    long_desc = (
        "Phase 1 — Downstairs Living Room: WRAP-A remove existing panels, "
        "strip the lining, resize every width, and reinstall the white lining "
        "and bump across the full finished length of the downstairs opening "
        "WRAP-B"
    )
    pdf = render_mclean_estimate_bytes({
        "quote_number": "EST-WRAP",
        "customer_name": "Dahlia Design",
        "status": "draft",
        "created_at": "2026-10-02",
        "line_items": [
            _296_line(long_desc, 8),
            _296_line(
                "Phase 1 — Downstairs Living Room: NEXT-ROW stays clear",
                8,
            ),
        ],
    })
    from pypdf import PdfReader

    hits: dict[str, float] = {}

    def visitor(text_run, _cm, tm, _font, _size):
        if not text_run:
            return
        for token in ("WRAP-A", "WRAP-B", "NEXT-ROW"):
            if token in text_run:
                hits[token] = float(tm[5])

    for page in PdfReader(io.BytesIO(pdf)).pages:
        page.extract_text(visitor_text=visitor)
    assert set(hits) == {"WRAP-A", "WRAP-B", "NEXT-ROW"}
    assert hits["WRAP-B"] < hits["WRAP-A"]
    assert hits["NEXT-ROW"] <= hits["WRAP-B"] - 12
