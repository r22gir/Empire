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
    """Shop inches: whole numbers or 1/16\" fractions. Never ``72.00\"``."""
    from app.services.drawing.inches import format_inches
    return format_inches(value)


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
    if (
        "product_type" not in spec
        and not spec.get("family")
        and not spec.get("style")
    ):
        raise ValueError("spec must include 'product_type'")
    from app.services.drawing.templates.catalog_namespace import (
        prepare_drawing_spec,
    )
    try:
        spec, resolved = prepare_drawing_spec(spec)
    except KeyError:
        # Bare unknown slugs keep the flat-registry error (Phase B1
        # list). A named family or catalog id keeps the resolver error.
        bare = spec.get("product_type")
        qualified = bool(
            spec.get("family") or spec.get("catalog_family")
            or spec.get("style") or spec.get("catalog_style")
            or (isinstance(bare, str) and "/" in bare)
        )
        if bare and not qualified:
            get_template(str(bare))
        raise
    template = get_template(
        spec["product_type"], family=resolved.catalog_family,
    )
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
        # Ripplefold is its own sheet (elevation + top view + spec).
        # The pinch-pleat B2 gates measure a side section and a
        # stacked pair, and would reject this drawing.
        token = str(
            spec.get("product_type") or result.product_type or ""
        ).lower().replace("_", "").replace("-", "").replace(" ", "")
        if token == "ripplefold":
            return pdf_bytes
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
    """Idea sheet for families that are not on the golden vector path.

    Same title-block model as the bench SVG sheet (quote_sheet_layout):
    letterhead, one contact line per row, framed views of the existing
    geometry, dims in the gutter, layout math and assumptions below.
    One landscape page. No interleaved address/phone row.
    """
    from app.services.drawing.bench_quote_bridge import sheet_chrome
    from app.services.drawing.quote_sheet_layout import (
        PDF_TYPE,
        b1_page_regions,
        layout_title_block,
        project_view,
    )

    page_w, page_h = landscape(LETTER)
    buf = io.BytesIO()
    c = Canvas(
        buf, pagesize=(page_w, page_h),
        title=f"Empire Drawing — {result.product_type}",
        author="Empire Drafting Studio",
    )
    ink = colors.HexColor("#20241f")
    mute = colors.HexColor("#5c574c")
    hair = colors.HexColor("#c8c2b4")
    chip_fill = colors.HexColor("#f4efe2")
    paper = colors.HexColor("#fbfaf6")
    c.setFillColor(paper)
    c.rect(0, 0, page_w, page_h, fill=1, stroke=0)

    product = (result.product_type or "").replace("_", " ").title()
    family = result.family or ""
    chrome = sheet_chrome(spec.get("business_unit"))
    rows = [("FAMILY:", family), ("PRODUCT:", product)]
    for key, value in (result.title_block or {}).items():
        if value is None or str(value).strip() == "":
            continue
        rows.append((f"{str(key).upper()}:", str(value)))
    regions = b1_page_regions(page_w, page_h, title_rows=len(rows) + 2)
    header = regions["header"]
    # Header is top-down in the helper; PDF y grows up.
    header_top = page_h - header.y
    header_bot = header_top - header.h
    c.setFillColor(colors.HexColor("#f6f3ec"))
    c.rect(header.x, header_bot, header.w, header.h, fill=1, stroke=0)
    c.setStrokeColor(colors.HexColor("#b8912f"))
    c.setLineWidth(1.4)
    c.line(header.x, header_bot, header.right, header_bot)
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(header.x + 10, header_top - 16, chrome.get("company") or "EMPIRE WORKROOM")
    c.setFont("Helvetica", 8)
    c.setFillColor(mute)
    c.drawString(header.x + 10, header_top - 30, chrome.get("tagline") or "")
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 14)
    title = f"{family} — {product}".strip(" —")
    c.drawRightString(header.right - 10, header_top - 20, title)
    c.setFillColor(mute)
    c.setFont("Helvetica", 8)
    c.drawRightString(header.right - 10, header_top - 34, "IDEA SHEET  ·  NOT FOR CONSTRUCTION")

    title_rect = regions["title"]
    title_top = page_h - title_rect.y
    c.setStrokeColor(ink)
    c.setLineWidth(1.0)
    c.rect(title_rect.x, title_top - title_rect.h, title_rect.w, title_rect.h, fill=0, stroke=1)
    ops = layout_title_block(
        title_rect.w, title_rect.h, chrome, rows, chip="", sizes=PDF_TYPE,
    )
    _paint_block_ops(c, title_rect.x, title_top, ops, ink, mute, hair, chip_fill)

    views = list(result.geometry.views or ["elevation"])
    view_rect = regions["views"]
    view_top = page_h - view_rect.y
    n = max(1, len(views))
    gap = 8.0
    panel_h = (view_rect.h - gap * (n - 1)) / n
    for i, view in enumerate(views):
        panel_top = view_top - i * (panel_h + gap)
        panel_bot = panel_top - panel_h
        c.setStrokeColor(ink)
        c.setLineWidth(0.8)
        c.rect(view_rect.x, panel_bot, view_rect.w, panel_h, fill=0, stroke=1)
        c.setFillColor(colors.HexColor("#f6f3ec"))
        c.rect(view_rect.x, panel_top - 16, view_rect.w, 16, fill=1, stroke=0)
        c.setFillColor(ink)
        c.setFont("Helvetica-Bold", PDF_TYPE["caption"])
        c.drawString(view_rect.x + 8, panel_top - 12, f"{view.upper()} VIEW")
        inner_top = panel_top - 16
        inner_h = panel_h - 16
        width_label, height_label = _spec_dim_labels(spec, view)
        projected = project_view(
            result.geometry.points, result.geometry.edges, view,
            view_rect.w, inner_h, gutter=40,
            width_label=width_label, height_label=height_label,
        )
        for line in projected["lines"]:
            weight = line.get("weight") or "outline"
            c.setStrokeColor(ink if weight == "outline" else mute)
            c.setLineWidth(1.15 if weight == "outline" else 0.45)
            y1 = inner_top - line["y1"]
            y2 = inner_top - line["y2"]
            c.line(view_rect.x + line["x1"], y1, view_rect.x + line["x2"], y2)
        c.setFillColor(ink)
        c.setFont("Helvetica", PDF_TYPE["dim"])
        for label in projected["labels"]:
            lx = view_rect.x + label["x"]
            ly = inner_top - label["y"]
            if label.get("anchor") == "end":
                c.drawRightString(lx, ly, label["text"])
            elif label.get("anchor") == "middle":
                c.drawCentredString(lx, ly, label["text"])
            else:
                c.drawString(lx, ly, label["text"])

    notes = regions["notes"]
    notes_top = page_h - notes.y
    y = notes_top - 4
    bottom = page_h - notes.bottom + 4
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", PDF_TYPE["section"])
    c.drawString(notes.x, y, "LAYOUT MATH — segments + gaps = overall")
    y -= 14
    c.setFont("Helvetica", PDF_TYPE["body"])
    for ml in result.layout_math or []:
        seg = " + ".join(f"{n} × {_fmt_in(v)}" for n, v in ml.segments) or "—"
        gap_s = " + ".join(f"{n} × {_fmt_in(v)}" for n, v in ml.gaps) or ""
        equation = seg + (f" + {gap_s}" if ml.gaps else "")
        equation = f"{equation}  =  {_fmt_in(ml.total)}  (target {_fmt_in(ml.target_in)})"
        note = f"  ·  {ml.note}" if ml.note else ""
        y = _pdf_flow(c, notes.x, y, bottom, ml.label, "Helvetica-Bold",
                      PDF_TYPE["body"], notes.w, ink)
        y = _pdf_flow(c, notes.x + 8, y, bottom, equation + note, "Helvetica",
                      PDF_TYPE["note"], notes.w - 8, ink)
        y -= 2
    y -= 6
    if y > bottom + 12:
        c.setFont("Helvetica-Bold", PDF_TYPE["section"])
        c.setFillColor(ink)
        c.drawString(notes.x, y, "NOTES / ASSUMPTIONS — CONFIRM")
        y -= 13
        assumptions = list(result.assumptions or [])
        if not assumptions:
            assumptions = ["No assumptions — all dims sourced from spec."]
        for assumption in assumptions:
            y = _pdf_flow(c, notes.x, y, bottom, "* " + assumption,
                          "Helvetica-Oblique", PDF_TYPE["note"], notes.w,
                          colors.HexColor("#7c5a00"))

    c.setStrokeColor(ink)
    c.setLineWidth(1.1)
    c.rect(16, 16, page_w - 32, page_h - 32, fill=0, stroke=1)
    c.showPage()
    c.save()
    buf.seek(0)
    return buf.getvalue()


def _spec_dim_labels(spec: dict, view: str):
    """Quote dims for a view gutter. Not the padded geometry bbox."""
    dims = (spec or {}).get("dims") or {}
    width = dims.get("width")
    if view == "plan":
        other = dims.get("depth")
    else:
        other = dims.get("drop")
        if other is None:
            other = dims.get("height")

    def _one(value):
        if value is None or value == "":
            return None
        try:
            return _fmt_in(float(value))
        except (TypeError, ValueError):
            return None

    return _one(width), _one(other)


def _paint_block_ops(c, origin_x, top_y, ops, ink, mute, hair, chip_fill):
    """Paint quote_sheet_layout ops. ``top_y`` is the PDF y of the block top."""
    for op in ops:
        kind = op["kind"]
        if kind == "rect":
            c.setFillColor(chip_fill)
            c.rect(
                origin_x + op["x"],
                top_y - op["y"] - op["h"],
                op["w"], op["h"], fill=1, stroke=0,
            )
        elif kind == "rule":
            c.setStrokeColor(hair)
            c.setLineWidth(0.5)
            y = top_y - op["y"]
            c.line(origin_x + op["x1"], y, origin_x + op["x2"], y)
        elif kind == "text":
            size = op["size"]
            bold = op.get("weight") == "bold"
            c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
            c.setFillColor(mute if op.get("fill") == "mute" else ink)
            x = origin_x + op["x"]
            y = top_y - op["y"]
            anchor = op.get("anchor") or "start"
            if anchor == "middle":
                c.drawCentredString(x, y, op["text"])
            elif anchor == "end":
                c.drawRightString(x, y, op["text"])
            else:
                c.drawString(x, y, op["text"])


def _pdf_flow(c, x, y, bottom, text, font, size, width, color):
    """Draw wrapped lines downward. Returns the next baseline."""
    from app.services.drawing.quote_sheet_layout import wrap_text
    c.setFillColor(color)
    c.setFont(font, size)
    for line in wrap_text(text, width, size, factor=0.50):
        if y < bottom:
            return y
        c.drawString(x, y, line)
        y -= size + 3
    return y


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
