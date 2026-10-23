"""Layout audit for Max drawing PDFs — notes/captions must not clip or overlap.

Uses the real generate_job_drawing path plus mock jobs (U+L banquettes,
long notes). Measures pdfplumber word bboxes against the page and
neighboring words. Fractions only in printed measurements.
"""
from __future__ import annotations

import os
import re
from pathlib import Path

import pytest

from app.services.drawing.templates.text_layout import (
    audit_drawing_layout,
    measurement_decimals,
    protect_measures,
    wrap_text,
)


HISTORY = [
    {"role": "user", "content": "make a drawing for the Marley's job with channel backs on V003-Cognac and seat cushions on Black"},
    {"role": "assistant", "content": "New drawing for Marley's (REV A)"},
]

MOCK_QUOTE = {
    "customer_name": "Marley's",
    "quote_number": "EST-TEMP-NL",
    "project_name": "Marley's Hyattsville",
    "line_items": [],
    "total": 0,
}

LONG_NOTE = (
    "NIGHTLAB LONG NOTE MARKER ALPHA. Confirm every open end, shell, "
    "and seat-to-back joint on site before any wood or fabric cut. "
    "Do not assume the field sketch includes the same shell as this sheet. "
) * 6 + "MARKER OMEGA UNIQUE STRING."


@pytest.fixture
def drawings_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("MAX_DRAWINGS_OUTPUT_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setattr(
        "app.services.drawing.job_drawing.resolve_job_quote",
        lambda hint: dict(MOCK_QUOTE),
    )
    return tmp_path


def _extract_pages(pdf_path: str) -> list[str]:
    import pdfplumber
    with pdfplumber.open(pdf_path) as pdf:
        return [page.extract_text() or "" for page in pdf.pages]


def _assert_layout(pdf_path: str, *, pages: tuple[int, ...] = (2, 3)) -> None:
    report = audit_drawing_layout(pdf_path)
    overflow = [i for i in report.overflow() if i.page in pages]
    overlaps = [i for i in report.overlaps() if i.page in pages]
    assert not overflow, "text overflow vs page/frame:\n" + "\n".join(
        f"  p{i.page} {i.detail}" for i in overflow[:12]
    )
    assert not overlaps, "text overlap:\n" + "\n".join(
        f"  p{i.page} {i.detail}" for i in overlaps[:12]
    )
    blob = "\n".join(_extract_pages(pdf_path))
    assert measurement_decimals(blob) == []
    assert re.findall(r'\d+\.\d+"', blob) == []


def test_wrap_keeps_mixed_number_inch_tokens():
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import letter

    path = Path(os.environ.get("TMPDIR") or "/tmp") / "wrap_probe.pdf"
    c = canvas.Canvas(str(path), pagesize=letter)
    assert "7\u00a03/4\"" in protect_measures('3 x 10" channels + 7 3/4" ODD')
    lines = wrap_text(c, '3 x 10" channels + 7 3/4" ODD at open end', "Helvetica", 6.5, 90)
    joined = " | ".join(lines)
    assert "7 3/4\"" in joined
    assert not any(line.strip() == "7" for line in lines)


def test_ul_banquette_pages_2_3_from_generate_job_drawing(drawings_dir):
    from app.services.drawing.job_drawing import generate_job_drawing

    result = generate_job_drawing(
        message="revise the drawing: channel width 10 inch, seat cushions on Black",
        history=HISTORY,
        job_hint="marleys",
        quote=MOCK_QUOTE,
    )
    assert result["success"]
    path = result["pdf_path"]
    pages = _extract_pages(path)
    assert len(pages) >= 3
    assert "TOP VIEW PLAN — L booth" in pages[1]
    assert "FRONT ELEVATIONS" in pages[2]
    assert "SIDE SECTION" in pages[2]
    _assert_layout(path, pages=(2, 3))
    # Captions must keep the odd remainder as one measurement token.
    assert "7 3/4\"" in pages[2] or "7 3/4" in pages[2]


def test_long_notes_flow_instead_of_clip(drawings_dir):
    from app.services.drawing.templates.banquette_fixtures import marleys_standard_job
    from app.services.drawing.templates.banquette_standard import render_banquette_job_pdf

    job = marleys_standard_job(revision="A", drawn_date="2026-10-23")
    for bench in job.benches:
        bench.notes = list(bench.notes) + [LONG_NOTE]
    path = drawings_dir / "long_notes_ul.pdf"
    render_banquette_job_pdf(job, path)
    pages = _extract_pages(str(path))
    blob = "\n".join(pages)
    assert "NIGHTLAB LONG NOTE MARKER ALPHA" in blob
    assert "MARKER OMEGA UNIQUE STRING" in blob
    _assert_layout(str(path), pages=(1, 2, 3))
    # Page 2 is the L plan — notes live in the right-hand frame.
    assert "NOTES" in pages[1]
    assert "MARKER" in pages[1] or "MARKER" in pages[0]


def test_generate_job_drawing_long_notes_ul(drawings_dir, monkeypatch):
    from app.services.drawing.job_drawing import generate_job_drawing
    from app.services.drawing.templates.banquette_fixtures import marleys_job_layouts

    layouts = marleys_job_layouts()
    for layout in layouts:
        layout["notes"] = [
            "Corner joints follow the standard U / L rule.",
            LONG_NOTE,
        ]
    monkeypatch.setattr(
        "app.services.drawing.job_drawing.job_set_layouts",
        lambda hint: layouts,
    )
    result = generate_job_drawing(
        message="make a drawing for the Marley's job",
        job_hint="marleys",
        quote=MOCK_QUOTE,
        layout_data=None,
    )
    assert result["success"]
    blob = "\n".join(_extract_pages(result["pdf_path"]))
    assert "NIGHTLAB LONG NOTE MARKER ALPHA" in blob
    assert "MARKER OMEGA UNIQUE STRING" in blob
    _assert_layout(result["pdf_path"], pages=(2, 3))


def test_straight_bench_layout_check(drawings_dir):
    from app.services.drawing.shop_date import shop_today
    from app.services.drawing.templates.banquette_job import build_banquette_job
    from app.services.drawing.templates.banquette_standard import render_banquette_job_pdf

    job = build_banquette_job(
        layouts=[{
            "shape": "straight",
            "width_in": 96,
            "depth_in": 16,
            "back_height_in": 26.75,
            "channel_width_in": 12,
            "foam_thickness_in": 2.0,
            "piece_name": "Temp straight",
            "client_name": "TempBanquette Client",
            "project_name": "TempBanquette booth",
            "notes": [LONG_NOTE],
        }],
        fabrics={
            "back": {"code": "V100-Cognac", "color": "Cognac", "label": "V100-Cognac"},
            "seat": {"code": "V101-Black", "color": "Black", "label": "V101-Black"},
        },
        conflicts=[],
        quote=None,
        revision="A",
        drawn_date=shop_today(),
        job_hint="TempBanquette",
    )
    path = drawings_dir / "straight_long_notes.pdf"
    render_banquette_job_pdf(job, path)
    blob = "\n".join(_extract_pages(str(path)))
    assert "MARKER OMEGA UNIQUE STRING" in blob
    _assert_layout(str(path), pages=(1, 2))
