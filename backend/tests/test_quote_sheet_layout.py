"""Idea-sheet chrome: title block, gutters, and no obvious text collisions.

Bench SVG sheets and B1 story sheets (valance, cornice) share
quote_sheet_layout. These checks lock the formatting bar from the
CF-2026-011 review: a title block is present, WoodCraft letterhead
stays WoodCraft, and text runs do not sit on each other.
"""
from __future__ import annotations

import io
import re
import xml.etree.ElementTree as ET

import pytest

from app.services.drawing.quote_sheet_layout import (
    SHEET_H,
    SHEET_W,
    boxes_overlap,
    idea_sheet_regions,
    layout_title_block,
    text_bbox,
    SVG_TYPE,
)
from app.services.vision.bench_renderer import render_straight


def _local(tag: str) -> str:
    return tag.split("}")[-1]


def _svg_text_boxes(svg: str):
    """Text boxes in sheet coordinates, honoring translate groups."""
    root = ET.fromstring(svg)
    boxes = []

    def walk(el, tx, ty):
        transform = el.attrib.get("transform", "")
        match = re.search(
            r"translate\(\s*([\d.\-]+)[,\s]+([\d.\-]+)\s*\)", transform,
        )
        ntx, nty = tx, ty
        if match:
            ntx += float(match.group(1))
            nty += float(match.group(2))
        if _local(el.tag) == "text":
            x = float(el.attrib.get("x", 0)) + ntx
            y = float(el.attrib.get("y", 0)) + nty
            size = float(el.attrib.get("font-size", 10))
            anchor = el.attrib.get("text-anchor", "start")
            raw = el.text or ""
            boxes.append((raw, text_bbox(x, y, raw, size, anchor)))
        for child in list(el):
            walk(child, ntx, nty)

    walk(root, 0, 0)
    return boxes


def _wc_bench_svg() -> str:
    return render_straight(
        "MOCK DRAFT CF-2026-011 FREESTANDING BENCH",
        66,
        depth_in=20,
        seat_h_in=18,
        back_h_in=18,
        quote_num="CF-2026-011",
        cushion_width=24,
        panel_style="vertical_channels",
        channel_count=6,
        business_unit="woodcraft",
        product_type="freestanding_bench",
        date="09/26/2026",
    )


def test_regions_keep_views_and_title_apart():
    regions = idea_sheet_regions(title_rows=10)
    names = ("plan", "elev", "iso", "title", "header")
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            ra, rb = regions[a], regions[b]
            box_a = (ra.x, ra.y, ra.right, ra.bottom)
            box_b = (rb.x, rb.y, rb.right, rb.bottom)
            assert not boxes_overlap(box_a, box_b, min_px=0.5), (a, b)
    for name in ("plan", "elev"):
        frame = regions[name]
        safe = regions[f"{name}_safe"]
        assert safe.x >= frame.x and safe.right <= frame.right
        assert safe.y >= frame.y and safe.bottom <= frame.bottom
        assert safe.w > 200 and safe.h > 80
    # Views get the wide column; the spec block is not an equal quadrant.
    assert regions["plan"].w > regions["title"].w
    assert regions["elev"].w > regions["title"].w


def test_title_block_rows_stay_above_the_footer():
    chrome = {
        "company": "WOODCRAFT BY EMPIRE",
        "tagline": "CUSTOM WOODWORK",
        "address": "5124 Frolich Ln, Hyattsville, MD 20781",
        "contact": "(703) 213-6484 | workroom@empirebox.store",
        "drawn_by": "MAX AI / WoodCraft",
    }
    rows = [
        ("ITEM:", "MOCK DRAFT CF-2026-011 FREESTANDING BENCH"),
        ("DIMENSIONS:", '66" W × 20" D × 18" SH × 18" BH'),
        ("NOTE:", 'back height 18" ASSUMED — CONFIRM BEFORE FABRICATION'),
    ]
    ops = layout_title_block(400, 360, chrome, rows, "WC · FREESTANDING BENCH · CHANNELED", SVG_TYPE)
    texts = [op for op in ops if op["kind"] == "text"]
    footer = [op for op in texts if "NOT TO SCALE" in op["text"]]
    assert len(footer) == 1
    body = [op for op in texts if op is not footer[0]]
    assert body
    assert max(op["y"] for op in body) < footer[0]["y"] - 8
    # Phone and email are separate lines — the old 3-cell row interleaved them.
    joined = "\n".join(op["text"] for op in texts)
    assert "(703) 213-6484" in joined
    assert "workroom@empirebox.store" in joined
    assert "Hyattsville" in joined
    phone_y = next(op["y"] for op in texts if "213-6484" in op["text"])
    mail_y = next(op["y"] for op in texts if "workroom@" in op["text"])
    assert phone_y != mail_y
    boxes = [
        text_bbox(op["x"], op["y"], op["text"], op["size"], op.get("anchor", "start"))
        for op in texts
    ]
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            assert not boxes_overlap(a, b, min_px=1.0)


def test_wc_bench_sheet_has_title_block_and_no_text_collisions():
    svg = _wc_bench_svg()
    assert "WOODCRAFT BY EMPIRE" in svg
    assert "EMPIRE WORKROOM" not in svg
    assert "WC · FREESTANDING BENCH · CHANNELED" in svg
    assert "PLAN VIEW" in svg
    assert "FRONT ELEVATION" in svg
    assert "ISOMETRIC VIEW" in svg
    assert "NOT TO SCALE" in svg
    assert "CF-2026-011" in svg
    assert "CHANNELED BACK" in svg
    boxes = _svg_text_boxes(svg)
    assert len(boxes) > 20
    for label, box in boxes:
        assert box[0] >= 4 and box[1] >= 4, (label, box)
        assert box[2] <= SHEET_W - 4 and box[3] <= SHEET_H - 4, (label, box)
    for i, (la, a) in enumerate(boxes):
        for lb, b in boxes[i + 1:]:
            assert not boxes_overlap(a, b, min_px=1.5), (la, lb)


def test_b1_valance_and_cornice_sheets_are_one_readable_page():
    pytest.importorskip("pdfplumber")
    import pdfplumber
    from app.services.drawing.templates import render_spec

    samples = {
        "valance": {
            "product_type": "kingston",
            "dims": {"width": 72, "drop": 14},
        },
        "cornice": {
            "product_type": "straight",
            "dims": {"width": 84, "depth": 6, "drop": 12},
        },
    }
    for name, spec in samples.items():
        pdf = render_spec(spec)
        with pdfplumber.open(io.BytesIO(pdf)) as doc:
            assert len(doc.pages) == 1, name
            assert doc.pages[0].width > doc.pages[0].height
            text = doc.pages[0].extract_text() or ""
            assert "EMPIRE WORKROOM" in text
            assert "Hyattsville" in text
            assert "(703) 213-6484" in text
            assert "workroom@empirebox.store" in text
            # The old 2-column title row interleaved the address and the phone.
            assert "3M)D" not in text
            assert "Hyattsvil(l" not in text
            assert "(cid:" not in text
            assert "NOT TO SCALE" in text
            assert "LAYOUT MATH" in text
            words = doc.pages[0].extract_words() or []
            boxes = [(w["text"], (w["x0"], w["top"], w["x1"], w["bottom"])) for w in words]
            for i, (wa, a) in enumerate(boxes):
                for wb, b in boxes[i + 1:]:
                    assert not boxes_overlap(a, b, min_px=1.2), (name, wa, wb)
        if name == "valance":
            assert "Valance" in text
            assert "Kingston" in text
            assert "ELEVATION" in text
        else:
            assert "Cornice" in text
            assert "PLAN" in text
            assert "ELEVATION" in text
            assert "vector renderer not yet implemented" not in text
