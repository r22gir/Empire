"""templates/printer.py — Phase B1 PDF printer (reportlab).

Per Empire Drawing Standard v1.0, every drawing sheet has:

  - Required views (drawn from GeometryResult.views)
  - Title block (right column, every sheet)
  - LAYOUT MATH lines (Rule 3: segments + gaps = overall)
  - NOTES / ASSUMPTIONS — CONFIRM (Rule 1: every inferred value)

Phase B2 (2026-07-24) — replaces the textual "Geometry Preview"
panel with a real scaled line drawing per product family. Roman
Shades shipped first; drapery, valance, cornice, bench/banquette,
headboard_channel land in B2 follow-on commits. The vector
renderer lives in `b2_renderers.py`; this file orchestrates the
end-to-end PDF build and embeds the family's vector drawing
inside the reportlab canvas (one per family).

HOTFIX B2 output defects fixed in this file:
  (1) Header address/phone column collision — three cells
      ("5124 Frolich Ln...", "(703) 213-6484", "workroom@...") in
      one 5"-wide row; glyphs interleaved into nonsense
      "Hyattsvil(l7e0, 3M)D 2 1230-7684184". Fix: split into 3
      separate rows in the new vector title block (see
      b2_renderers._draw_title_block).
  (2) CLIENT field showed the parsed subject ("shade") — the
      router passed drawing_handoff.subject as client_name.
      Fix: CLIENT row only renders when an explicit client_name
      was supplied (not the parsed item type).
  (3) (cid:127) bullet glyphs in NOTES — replaced with ASCII '*'
      in the B2 helper (see b2_renderers).
  (4) Empty MATERIAL/SITE/DATE rows — render "—" or omit. The B2
      helper OMITS the row entirely when the value is empty.

render_drawing_from_spec / render_drawing deferred to Phase D per the
B plan (render_drawing needs enforcer proof); this printer is the
B1+B2-pure entry point.
"""
from __future__ import annotations

import io
import math
from typing import Optional

from reportlab.lib.pagesizes import LETTER, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    Preformatted, KeepTogether,
)
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from app.services.drawing.templates.base import (
    FamilyTemplate, GeometryFamilyResult, GeometryResult,
    GeometryPoint, GeometryEdge, MathLine,
)
from app.services.drawing.templates.registry import get_template
from app.services.drawing.templates.b2_renderers import (
    render_roman_shades_vector,
)


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
    """B1-only stub — REPLACED in B2 by the vector renderer.

    The textual views panel that previously rendered here has been
    replaced by `b2_renderers.render_roman_shades_vector`, which
    draws the geometry as actual line art on the reportlab canvas.
    This function is kept as a sentinel: callers that import
    _render_views_panel for a non-Roman family fall through to a
    placeholder that the vector renderer replaces family-by-family.
    """
    return [Paragraph(
        "<i>(vector renderer not yet implemented for this family — "
        "Roman Shades shipped in B2; drapery, valance, cornice, "
        "bench/banquette, headboard_channel land in B2 follow-on "
        "commits per the rollout plan)</i>",
        _ASSUMED)]


# ── Public API ────────────────────────────────────────────────────────


def _render_to_story(result: GeometryFamilyResult, spec: dict) -> list:
    """Materialize a reportlab story from a computed result.

    Phase B2: this is no longer a story-based build. The vector
    drawing is rendered directly on the canvas via b2_renderers;
    the page frame + title block are drawn with canvas ops too.
    The story pipeline below is kept as a stub so SimpleDocTemplate
    still has SOMETHING to assemble (the real content is on the
    canvas, which survives because we let doc.build() complete on
    an empty story — it just emits a blank page frame).
    """
    return []


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
    """Render a pre-computed GeometryFamilyResult to PDF bytes.

    Phase B2 path: vector drawing directly on the canvas. We build
    the page with `canvas.Canvas(...)`, draw the family-specific
    vector renderer, then call `showPage` + `save`.

    Family dispatch:
      - Roman Shades → render_roman_shades_vector (B2 vector)
      - All other families → B1 story path (until B2 follow-on
        commits ship each family's vector renderer). The story
        path keeps the B1 textual preview alive for non-Roman
        families so existing tests + live callers don't see a
        regression.

    The 4 B1 output defects are fixed in the vector path:
      (1) 3-row header (no address/phone column collision)
      (2) CLIENT row only when client_name is non-empty
      (3) ASCII '*' instead of the missing-glyph bullet
      (4) Empty MATERIAL/SITE/DATE rows omitted
    """
    if result.family == "Roman Shades":
        pdf_bytes = _render_b2_vector(result, spec)
    elif result.family == "Drapery":
        # CORRECTION R3.2 generalization: each family gets a
        # vector renderer in the v11 sheet language. Drapery uses
        # its own panel/pleat anatomy (NOT the Roman-shades bar
        # ladder). See templates/drapery_render.py.
        from app.services.drawing.templates.drapery_render import (
            render_drapery,
        )
        pdf_bytes = render_drapery(spec)
    else:
        # Non-vector families: keep the B1 textual preview so existing
        # tests + the live chat path keep producing a PDF for every
        # family. The vector renderer for each family lands in B2
        # follow-on commits. The QC gate is vector-only (it measures
        # bbox positions of vector text + lines), so it is NOT
        # applied to the B1 story path here.
        return _render_b1_story(result, spec)

    # R12.3.3 — every vector-rendered sheet is run through the
    # geometric QC gate (b2_qc.enforce_b2_qc) before returning
    # bytes. The gate was defined during the B2 rollout and
    # tested extensively via tests/test_drawing_vector_b2.py but
    # was never wired into the production render path. The gate
    # fails CLOSED: a collision, a same-baseline overlap, a
    # column overflow, or a missing element-spread all raise
    # B2QCFailure, which propagates out of render_spec. Per the
    # founder's R12.3.3 ruling, any QC failure refuses the render.
    from app.services.drawing.templates.b2_qc import enforce_b2_qc
    # R12.3.4 — pass the spec so the scale-truth and title+witnesses
    # gates can derive expected values from the renderer's own
    # _fmt_in / fold_descriptor helpers (single source of truth)
    # rather than parsing the rendered text with a hard-coded regex.
    enforce_b2_qc(pdf_bytes, result.family, result.product_type, spec=spec)
    return pdf_bytes


def _render_b2_vector(result: GeometryFamilyResult, spec: dict) -> bytes:
    """Roman Shades vector path (Phase B2)."""
    buf = io.BytesIO()
    c = Canvas(
        buf,
        pagesize=landscape(LETTER),
        leftMargin=0.4 * inch,
        rightMargin=0.4 * inch,
        topMargin=0.3 * inch,
        bottomMargin=0.3 * inch,
        title=f"Empire Drawing — {result.product_type}",
        author="Empire Drafting Studio (B2)",
    )
    c.setStrokeColor(colors.HexColor("#333333"))
    c.setLineWidth(1.2)
    c.rect(0.25 * inch, 0.25 * inch,
           11.0 - 0.5 * inch, 8.5 - 0.5 * inch, stroke=1, fill=0)
    render_roman_shades_vector(
        c, result.geometry, result.layout_math,
        result.title_block, family_name=result.family,
        product_type=result.product_type, spec=spec,
    )
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


def _render_b1_story(result: GeometryFamilyResult, spec: dict) -> bytes:
    """Non-Roman families: B1 textual preview path (preserved until
    B2 follow-on commits land each family's vector renderer)."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=LETTER,
        leftMargin=0.6 * inch, rightMargin=0.6 * inch,
        topMargin=0.5 * inch, bottomMargin=0.5 * inch,
        title=f"Empire Drawing — {result.product_type}",
        author="Empire Drafting Studio (B1)",
    )
    story = _render_to_story_b1(result, spec)
    doc.build(story)
    buf.seek(0)
    return buf.getvalue()


def _render_to_story_b1(result: GeometryFamilyResult, spec: dict) -> list:
    """B1 textual preview (preserved for non-Roman families)."""
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
    return story
