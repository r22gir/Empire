"""templates/printer.py — Phase B1 PDF printer (reportlab).

Per Empire Drawing Standard v1.0, every drawing sheet has:

  - Required views (drawn from GeometryResult.views)
  - Title block (right column, every sheet)
  - LAYOUT MATH lines (Rule 3: segments + gaps = overall)
  - NOTES / ASSUMPTIONS — CONFIRM (Rule 1: every inferred value)

This is the B1-checkpoint printer. It produces a single-page PDF per
spec render. The 10-sheet golden acceptance lands in B2 (Phase B2
extends the printer to multi-sheet output, page count = sheets).

render_drawing_from_spec / render_drawing deferred to Phase D per the
B plan (render_drawing needs enforcer proof); this printer is the
B1-pure entry point.
"""
from __future__ import annotations

import io
import math
from typing import Optional

from reportlab.lib.pagesizes import LETTER
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Preformatted, KeepTogether,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from app.services.drawing.templates.base import (
    FamilyTemplate, GeometryFamilyResult, GeometryResult,
    GeometryPoint, GeometryEdge, MathLine,
)
from app.services.drawing.templates.registry import get_template


# ── reportlab style sheet ─────────────────────────────────────────────

_BASE_STYLES = getSampleStyleSheet()

# Family of fonts: Helvetica per Standard.
_PARA = ParagraphStyle(
    name="EmpireBody", parent=_BASE_STYLES["BodyText"],
    fontName="Helvetica", fontSize=10, leading=12, alignment=TA_LEFT,
)
_HEADING = ParagraphStyle(
    name="EmpireHeading", parent=_BASE_STYLES["Heading2"],
    fontName="Helvetica-Bold", fontSize=14, leading=16,
)
_TITLE = ParagraphStyle(
    name="EmpireTitle", parent=_BASE_STYLES["Title"],
    fontName="Helvetica-Bold", fontSize=20, leading=22,
)
_MATH = ParagraphStyle(
    name="EmpireMath", parent=_BASE_STYLES["Code"],
    fontName="Courier", fontSize=10, leading=12,
)
_ASSUMED = ParagraphStyle(
    name="EmpireAssumed", parent=_BASE_STYLES["Italic"],
    fontName="Helvetica-Oblique", fontSize=9, leading=11,
    textColor=colors.HexColor("#7c5a00"),
)


# ── Helpers ────────────────────────────────────────────────────────────


def _fmt_in(value: float) -> str:
    """Format inches as text per Standard: '10-49/64"' exact fractions
    where reasonable. For B1 we use 1/16" granularity; B2 can move to
    1/64" once the spec format admits it.

    Strategy: render as float with 2 decimals PLUS a fractional
    suffix if the float is close to a rational multiple of 1/16.
    """
    # Round to nearest 1/16 and emit as fraction
    sixteenths = round(value * 16)
    whole = sixteenths // 16
    rem = sixteenths - whole * 16
    if rem == 0:
        return f'{whole}"' if whole else '0"'
    # Reduce fraction
    from math import gcd
    g = gcd(rem, 16)
    n = rem // g
    d = 16 // g
    if whole:
        return f'{whole}-{n}/{d}"'
    return f'{n}/{d}"'


def _dim_label(text: str) -> Paragraph:
    return Paragraph(text, _PARA)


def _render_dimension_lines(geom: GeometryResult) -> list:
    """Emit bbox-bounded dimension strings derived from geometry.
    Per Standard: dimension lines are 0.6pt with end ticks; we emit
    labels only here and let the SVG/PDF renderer do the lines."""
    out = []
    min_x, min_y, max_x, max_y = geom.bbox
    if max_x - min_x > 0:
        out.append(_dim_label(f'Overall width: {_fmt_in(max_x - min_x)}'))
    if max_y - min_y > 0:
        out.append(_dim_label(f'Overall height: {_fmt_in(max_y - min_y)}'))
    return out


def _render_layout_math_table(math_lines: list[MathLine]) -> Table:
    """Emit one row per MathLine — segments + gaps = target with note.

    Each row shows the closure line in monospace so it can be re-keyed
    into a fab ticket. Per Rule 3, segments + gaps MUST equal target
    within 1/64" or the row carries a 'WARN' prefix.
    """
    if not math_lines:
        return Table([["No layout math required."]],
                     colWidths=[6.5 * inch])
    data = [["LAYOUT MATH — segments + gaps = overall (Rule 3)", ""]]
    for ml in math_lines:
        seg_str = " + ".join(f'{n} × {_fmt_in(v)}' for n, v in ml.segments) or "—"
        gap_str = " + ".join(f'{n} × {_fmt_in(v)}' for n, v in ml.gaps) or "—"
        total_str = (
            f'{seg_str}' + (f' + {gap_str}' if ml.gaps else '')
        )
        warn = "" if ml.closing_tolerance_in < (1 / 64) else "  ⚠  "
        line_text = (
            f'{warn}{total_str}  =  {_fmt_in(ml.total)}  '
            f'(target {_fmt_in(ml.target_in)})'
        )
        data.append([Paragraph(ml.label, _PARA),
                     Preformatted(line_text, _MATH)])
    if any(ml.note for ml in math_lines):
        data.append(["Notes:", ""])
        for ml in math_lines:
            if ml.note:
                data.append([Paragraph("", _PARA),
                             Paragraph(ml.note, _ASSUMED)])
    t = Table(data, colWidths=[1.6 * inch, 4.9 * inch])
    t.setStyle(TableStyle([
        ("SPAN", (0, 0), (1, 0)),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f4ecd8")),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#777777")),
        ("INNERGRID", (0, 1), (-1, -1), 0.2, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _render_assumptions_block(assumptions: list[str]) -> list:
    if not assumptions:
        return [Paragraph("No assumptions — all dims sourced from spec.",
                          _PARA)]
    rows = [["NOTES / ASSUMPTIONS — CONFIRM before fabrication:"]]
    for a in assumptions:
        rows.append([Paragraph(f"• {a}", _ASSUMED)])
    t = Table(rows, colWidths=[6.5 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fef9e7")),
        ("BOX", (0, 0), (-1, -1), 0.4, colors.HexColor("#e0b700")),
        ("INNERGRID", (0, 1), (-1, -1), 0.2, colors.HexColor("#e0b700")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return [t]


def _render_title_block(family: str, product_type: str,
                       title_block: dict, spec: dict) -> Table:
    """Standard right-column title block. Header rows in a fixed order
    so the founder can scan the sheet fast."""
    rows = [
        ["EMPIRE WORKROOM", "CUSTOM UPHOLSTERY & FABRICATION"],
        ["5124 Frolich Ln, Hyattsville, MD 20781", "(703) 213-6484",
         "workroom@empirebox.store"],
        ["FAMILY", family],
        ["PRODUCT TYPE", product_type],
    ]
    # Inject the per-family title-block keys (skip ones we've already
    # rendered so we don't duplicate).
    seen = {"FAMILY", "PRODUCT TYPE"}
    for k, v in title_block.items():
        if k.upper() in seen:
            continue
        rows.append([k.upper(), str(v)])
        seen.add(k.upper())
    # Standard-required rows
    rows.append(["CLIENT", str(spec.get("client_name", "—"))])
    rows.append(["SITE", str(spec.get("site_address", "—"))])
    rows.append(["SHEET", "1 of 1 (B1 single-sheet output)"])
    rows.append(["STATUS", "FOR FOUNDER REVIEW"])
    rows.append(["MATERIAL", str(spec.get("material", "—"))])
    rows.append(["DATE", str(spec.get("date", "—"))])
    rows.append(["DRAWN BY", "Empire Drafting Studio (B1)"])
    t = Table(rows, colWidths=[1.5 * inch, 5.0 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (1, 0), colors.HexColor("#1a1a1a")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 11),
        ("BACKGROUND", (0, 0), (1, 1), colors.HexColor("#1a1a1a")),
        ("TEXTCOLOR", (0, 1), (-1, 1), colors.white),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#1a1a1a")),
        ("INNERGRID", (0, 2), (-1, -1), 0.2, colors.HexColor("#999999")),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return t


def _render_views_panel(geom: GeometryResult) -> list:
    """List the views present + bbox dimensions in print-friendly form.
    B1 has no SVG-yet renderer for the points/edges; per the B plan,
    the rendering of those points is D2-deferred. We emit a textual
    view summary + the geometric bbox so the founder can sanity-check
    dimensions without having to read pixel coordinates.

    B2 (and the B2 golden acceptance) replaces this with real
    line/curve drawing."""
    rows = [["VIEW", "POINTS", "EDGES", "BBOX (in)"]]
    if geom.views:
        for view in geom.views:
            pts = [p for p in geom.points if p.view == view]
            eds = [e for e in geom.edges if e.view == view]
            min_x, min_y, max_x, max_y = geom.bbox
            rows.append([
                view,
                str(len(pts)),
                str(len(eds)),
                f"{_fmt_in(max_x - min_x)} W × {_fmt_in(max_y - min_y)} H",
            ])
    else:
        rows.append(["(none specified)", "—", "—", "—"])
    t = Table(rows, colWidths=[1.6 * inch, 1.4 * inch, 1.4 * inch, 2.1 * inch])
    t.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e8e8e8")),
        ("BOX", (0, 0), (-1, -1), 0.5, colors.HexColor("#999999")),
        ("INNERGRID", (0, 1), (-1, -1), 0.2, colors.HexColor("#cccccc")),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("ALIGN", (1, 0), (-1, -1), "CENTER"),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    return [Paragraph("<b>Geometry Preview (B1 textual — full renderer lands in B2)</b>",
                      _PARA), Spacer(1, 4), t]


# ── Public API ────────────────────────────────────────────────────────


def _render_to_story(result: GeometryFamilyResult, spec: dict) -> list:
    """Materialize a reportlab story from a computed result."""
    story = []
    title = f"{result.family} — {result.product_type.replace('_', ' ').title()}"
    story.append(Paragraph(title, _TITLE))
    story.append(Spacer(1, 8))
    story.append(_render_title_block(result.family, result.product_type,
                                      result.title_block, spec))
    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>Required Views (Standard)</b>", _HEADING))
    story.append(Spacer(1, 4))
    for v in result.geometry.views:
        story.append(Paragraph(f"• {v}", _PARA))
    story.append(Spacer(1, 8))
    story.extend(_render_views_panel(result.geometry))
    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>Dimensions</b>", _HEADING))
    story.append(Spacer(1, 4))
    for line in _render_dimension_lines(result.geometry):
        story.append(line)
    story.append(Spacer(1, 12))
    story.append(_render_layout_math_table(result.layout_math))
    story.append(Spacer(1, 12))
    story.append(Paragraph("<b>Notes / Assumptions</b>", _HEADING))
    story.append(Spacer(1, 4))
    story.extend(_render_assumptions_block(result.assumptions))
    story.append(Spacer(1, 12))
    story.append(Paragraph(
        "<i>Empire Drawing Standard v1.0 — Phase B1 parametric family "
        "output. Sourced from spec; no values invented. Print B1: "
        "single-sheet textual preview. Phase B2 replaces the textual "
        "preview with vector line/curve drawing.</i>",
        _ASSUMED))
    return story


def render_spec(spec: dict) -> bytes:
    """End-to-end: validate, compute, render. Returns the PDF bytes.

    Raises ValueError on missing required dims. Raises KeyError on an
    unknown product_type. Callers MUST catch both and surface as
    HTTP 400-style answers; never return a PDF for an invalid spec.
    """
    if "product_type" not in spec:
        raise ValueError("spec must include 'product_type'")
    template = get_template(spec["product_type"])
    missing = template.validate_spec(spec)
    if not missing.is_complete:
        raise ValueError(
            f"{template.__class__.__name__}: spec is missing required "
            f"dims {missing.missing_required} — render a question first"
        )
    result = template.compute(spec)
    return render_spec_to_bytes(result, spec)


def render_spec_to_bytes(result: GeometryFamilyResult, spec: dict) -> bytes:
    """Render a pre-computed GeometryFamilyResult to PDF bytes. Useful
    for tests that pre-compute then assert on the rendered output."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.5 * inch, bottomMargin=0.5 * inch,
        title=f"Empire Drawing — {result.product_type}",
        author="Empire Drafting Studio (B1)",
    )
    story = _render_to_story(result, spec)
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()
