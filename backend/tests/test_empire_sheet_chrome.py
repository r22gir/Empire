"""Shared Empire sheet chrome: margins, letterhead, fraction dims, PDF fit.

Drawing Studio used to embed a 1320px SVG on letter landscape with a
0.18in margin. WeasyPrint kept that pixel size, so both headers clipped
(ODCRAFT / STRAIGHT). These checks lock the fit-to-page wrapper and the
McLean band that WoodCraft quotes now share with Workroom.
"""
from __future__ import annotations

import io
import xml.etree.ElementTree as ET

import pytest

from app.services.drawing.empire_sheet_chrome import (
    BAND,
    GOLD,
    MIN_HEADER_INSET_UU,
    PAGE_MARGIN_IN,
    SheetMeta,
    client_document_html,
    drawings_pdf_html,
    format_length_for_sheet,
    prepare_svg_for_page,
)
from app.services.drawing.inches import format_inches
from app.services.vision.parametric_templates import render_template_instance


def test_page_margin_keeps_letterhead_off_the_trim():
    assert PAGE_MARGIN_IN >= 0.4
    html = drawings_pdf_html([{
        "svg": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1320 900" width="1320" height="900"></svg>',
    }])
    assert f"margin:{PAGE_MARGIN_IN}in" in html
    assert 'width="1320"' not in html
    assert 'height="900"' not in html
    assert "viewBox" in html
    fitted = prepare_svg_for_page(
        '<svg width="1320" height="900" viewBox="0 0 1320 900"></svg>'
    )
    assert "width=" not in fitted
    assert "height=" not in fitted


def test_fraction_dims_stay_shop_language():
    assert format_inches(72) == '72"'
    assert format_inches(72.0) == '72"'
    assert format_inches(14.5) == '14-1/2"'
    assert format_length_for_sheet(14.5, "in") == '14-1/2"'
    assert format_length_for_sheet("72.00", "inches") == '72"'
    assert "14.5" not in format_length_for_sheet(14.5, "in")
    assert "72.00" not in format_length_for_sheet(72, "in")


def test_woodcraft_quote_html_uses_mclean_band():
    html = client_document_html(
        "<p>Freestanding bench</p>",
        SheetMeta(
            company="WOODCRAFT BY EMPIRE",
            doc_id="CF-2026-011",
            date_label="2026-09-27",
            valid_label="2026-10-27",
            contact_lines=("woodcraft@empirebox.store",),
        ),
    )
    assert f"margin: {PAGE_MARGIN_IN}in" in html
    assert "letter landscape" in html
    assert "WOODCRAFT BY EMPIRE" in html
    assert "POWERED BY EMPIRE WORKROOM" in html
    assert "CF-2026-011" in html
    assert "REV A" in html
    assert "SHEET 01 OF 01" in html
    assert BAND in html
    assert GOLD in html
    assert "border-radius:6px" not in html


def _texts(svg: str):
    root = ET.fromstring(svg)
    out = []
    for el in root.iter():
        if el.tag.split("}")[-1] != "text":
            continue
        out.append((
            el.text or "",
            float(el.attrib.get("x", 0)),
            float(el.attrib.get("y", 0)),
            el.attrib.get("text-anchor", "start"),
            float(el.attrib.get("font-size", 10)),
        ))
    return out


def test_banquette_sheet_headers_stay_inside_and_use_fractions():
    result = render_template_instance("straight", {
        "item_type": "banquette",
        "name": "Straight Banquette",
        "dimensions": {"width": 120, "depth": 22, "height": 36, "seat_height": 18},
    })
    assert result is not None
    svg = result["svg"]
    assert "EMPIRE WOODCRAFT" in svg
    assert "STRAIGHT BANQUETTE" in svg
    assert "PRESENTATION SHEET" in svg

    texts = _texts(svg)
    labels = [t[0] for t in texts]
    assert 'Width: 120"' in labels
    assert not any(label.startswith("Width: 120.") for label in labels)
    company = next(t for t in texts if t[0] == "EMPIRE WOODCRAFT")
    title = next(t for t in texts if t[0] == "STRAIGHT BANQUETTE")
    assert company[1] >= MIN_HEADER_INSET_UU
    assert title[1] <= 1320 - MIN_HEADER_INSET_UU
    # Right-aligned title must still begin on the sheet.
    title_width = len(title[0]) * title[4] * 0.56
    assert title[1] - title_width >= MIN_HEADER_INSET_UU

    root = ET.fromstring(svg)
    rects = [
        el for el in root.iter()
        if el.tag.split("}")[-1] == "rect" and el.attrib.get("fill") == BAND
    ]
    assert len(rects) >= 2
    footer = max(rects, key=lambda el: float(el.attrib["y"]))
    assert float(footer.attrib["y"]) >= 870


def test_half_inch_callout_is_a_fraction():
    result = render_template_instance("straight", {
        "item_type": "banquette",
        "name": "Straight Banquette",
        "dimensions": {"width": 14.5, "depth": 22, "height": 36},
    })
    labels = [t[0] for t in _texts(result["svg"])]
    assert 'Width: 14-1/2"' in labels
    assert '14-1/2" W' in labels
    assert not any("14.5" in label or "14.50" in label for label in labels)


def test_presentation_pdf_keeps_both_headers(tmp_path):
    pytest.importorskip("weasyprint")
    pytest.importorskip("pdfplumber")
    import pdfplumber
    from weasyprint import HTML

    result = render_template_instance("straight", {
        "item_type": "banquette",
        "name": "Straight Banquette",
        "dimensions": {"width": 120, "depth": 22, "height": 36},
    })
    html = drawings_pdf_html([{"name": "Straight Banquette", "svg": result["svg"]}])
    pdf_path = tmp_path / "banquette.pdf"
    HTML(string=html).write_pdf(pdf_path)
    with pdfplumber.open(io.BytesIO(pdf_path.read_bytes())) as doc:
        page = doc.pages[0]
        assert page.width > page.height
        text = (page.extract_text() or "").replace(" ", "")
        assert "EMPIREWOODCRAFT" in text
        assert "STRAIGHTBANQUETTE" in text
        margin = PAGE_MARGIN_IN * 72 * 0.65
        words = page.extract_words() or []
        assert words
        for word in words:
            assert word["x0"] >= margin, word
            assert word["x1"] <= page.width - margin, word
            assert word["top"] >= margin, word
            assert word["bottom"] <= page.height - margin, word
