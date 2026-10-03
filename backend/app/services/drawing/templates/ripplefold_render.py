"""Ripplefold sheet: elevation, top-view track, and a spec table.

Drawing-standard chrome (landscape letter, McLean bands). Mount and
ceiling are printed only when the job carries them. A partial
coverage track is placed only when align or an offset is known.
"""
from __future__ import annotations

import io
import math
from datetime import date
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

from app.services.drawing.inches import format_inches
from app.services.drawing.max_sheet_chrome import (
    GOLD, HAIR, HDR_H, INK, MUTE, PDF_AUTHOR,
    PDF_CREATOR, PH, PW, _ensure_fonts, render_chrome_bands,
)
from app.services.drawing.templates.ripplefold_spec import (
    RipplefoldJob, resolve_ripplefold,
)


def _ripplefold_token(value: str | None) -> bool:
    token = str(value or "").lower().replace("_", "").replace("-", "").replace(" ", "")
    return token == "ripplefold"


def _sheet_date() -> str:
    months = ("JAN", "FEB", "MAR", "APR", "MAY", "JUN",
              "JUL", "AUG", "SEP", "OCT", "NOV", "DEC")
    today = date.today()
    return f"{today.day:02d} {months[today.month - 1]} {today.year}"


def _not_given(value, *, inches: bool = False) -> str:
    if value is None or value == "":
        return "NOT GIVEN"
    if inches:
        return format_inches(float(value))
    return str(value)


def _spec_rows(job: RipplefoldJob) -> list[tuple[str, str]]:
    if job.offset is None:
        offset = "NOT GIVEN"
    elif job.align == "center" and job.coverage_width < job.window_width - 1e-6:
        offset = f"{format_inches(job.offset)} EACH SIDE"
    else:
        offset = format_inches(job.offset)
    if job.align == "center" and job.coverage_width < job.window_width - 1e-6:
        align = "CENTER — RE-CENTERED TRACK"
    elif job.align:
        align = job.align.upper()
    else:
        align = "NOT GIVEN"
    track = format_inches(job.track_length)
    if job.track_equals_coverage:
        track += " EQUALS COVERAGE"
    if job.carrier_count is None:
        carriers = "NOT GIVEN"
    else:
        carriers = f"{job.carrier_count} ({job.carriers_per_panel} PER PANEL)"
    if job.stack is None:
        stack = "NOT GIVEN"
    elif job.stack_source == "kirsch chart":
        stack = f"{format_inches(job.stack)} KIRSCH CHART"
    else:
        stack = format_inches(job.stack)
    control = {"center": "CENTER DRAW", "one-way": "ONE-WAY"}.get(job.control or "", "NOT GIVEN")
    masters = (job.masters or "NOT GIVEN").upper()
    return [
        ("WINDOW", format_inches(job.window_width)),
        ("HEIGHT", format_inches(job.window_height)),
        ("COVERAGE", f"{format_inches(job.coverage_width)}  {job.layer.upper()}"),
        ("ALIGN", align),
        ("OFFSET", offset),
        ("TRACK", track),
        ("FULLNESS", f"{job.fullness}%" if job.fullness else "NOT GIVEN"),
        ("CARRIER", job.carrier or "NOT GIVEN"),
        ("SPACING", _not_given(job.carrier_spacing, inches=True)),
        ("CONTROL", control),
        ("MASTERS", masters),
        ("CARRIERS", carriers),
        ("STACK", stack),
        ("MOUNT", (job.mount or "NOT GIVEN").upper()),
        ("CEILING", _not_given(job.ceiling_height, inches=True)),
        ("MOUNT HEIGHT", _not_given(job.mount_height, inches=True)),
        ("LAYER", job.layer.upper()),
    ]
    if job.side_panels:
        rows.append(("SIDE PANELS", str(job.side_panels)))
        if job.side_widths is not None:
            rows.append(("SIDE WIDTHS", format_inches(job.side_widths).replace('"', "") + " EACH"))
        rows.append(("SIDES", "STATIONARY DRAPERY"))


def _dim_h(c, x0, x1, y, label, font) -> None:
    if abs(x1 - x0) < 8:
        return
    c.setStrokeColor(GOLD)
    c.setFillColor(INK)
    c.setLineWidth(0.7)
    c.line(x0, y, x1, y)
    c.line(x0, y - 3.5, x0, y + 3.5)
    c.line(x1, y - 3.5, x1, y + 3.5)
    c.setFont(font, 7)
    c.drawCentredString((x0 + x1) / 2.0, y + 4.5, label)


def _dim_v(c, x, y0, y1, label, font) -> None:
    c.setStrokeColor(GOLD)
    c.setFillColor(INK)
    c.setLineWidth(0.7)
    c.line(x, y0, x, y1)
    c.line(x - 3.5, y0, x + 3.5, y0)
    c.line(x - 3.5, y1, x + 3.5, y1)
    c.setFont(font, 7)
    c.saveState()
    c.translate(x + 10, (y0 + y1) / 2.0)
    c.rotate(90)
    c.drawCentredString(0, 0, label)
    c.restoreState()


def _span(job: RipplefoldJob, origin: float, scale: float) -> tuple[float, float] | None:
    if job.offset is None:
        return None
    x0 = origin + job.offset * scale
    return x0, x0 + job.coverage_width * scale


def _wave(c, x0, x1, y_base, amp, period, color, width, phase=0.0) -> None:
    if x1 - x0 < 4 or period <= 0:
        return
    c.setStrokeColor(color)
    c.setLineWidth(width)
    path = c.beginPath()
    steps = max(24, int((x1 - x0) / 2))
    for i in range(steps + 1):
        t = i / steps
        x = x0 + (x1 - x0) * t
        y = y_base + amp * math.sin((x - x0) / period * 2 * math.pi + phase)
        if i == 0:
            path.moveTo(x, y)
        else:
            path.lineTo(x, y)
    c.drawPath(path, stroke=1, fill=0)


def _elevation_folds(c, x0, x1, y0, y1, spacing_pt, color, width) -> None:
    if spacing_pt <= 0 or x1 <= x0:
        return
    c.setStrokeColor(color)
    c.setLineWidth(width)
    x = x0
    mid_y = (y0 + y1) / 2.0
    while x <= x1 + 0.1:
        path = c.beginPath()
        path.moveTo(x, y1)
        bulge = spacing_pt * 0.42
        path.curveTo(x + bulge, mid_y, x - bulge, mid_y, x, y0)
        c.drawPath(path, stroke=1, fill=0)
        x += spacing_pt


def _paint_fabric(c, x, y, w, h, image: str | None, font) -> None:
    """Stationary drapery panel. Uses the fabric photo when one was given."""
    if w < 2 or h < 2:
        return
    path = Path(image) if image else None
    if path and path.is_file():
        c.saveState()
        clip = c.beginPath()
        clip.rect(x, y, w, h)
        c.clipPath(clip, stroke=0, fill=0)
        c.drawImage(str(path), x, y, w, h, preserveAspectRatio=True, anchor="c", mask="auto")
        c.restoreState()
    else:
        c.setFillColor(HexColor("#c4b49a"))
        c.rect(x, y, w, h, fill=1, stroke=0)
        _elevation_folds(c, x, x + w, y + 1, y + h - 1, max(w / 4, 4), HexColor("#8c7358"), 0.6)
    c.setFillColor(INK)
    c.setFont(font, 5.5)
    c.drawCentredString(x + w / 2.0, y + 8, "STATIONARY")


def _draw_elevation(c, job: RipplefoldJob, font, font_b) -> None:
    c.setFillColor(INK)
    c.setFont(font_b, 9)
    c.drawString(32, PH - HDR_H - 18, "ELEVATION")
    box_l, box_r = 36.0, 430.0
    box_b, box_t = 78.0, PH - HDR_H - 28
    scale = min((box_r - box_l - 36) / job.window_width,
                (box_t - box_b - 36) / job.window_height)
    win_w = job.window_width * scale
    win_h = job.window_height * scale
    ox = box_l + 8
    oy = box_b + 28 + max(0, (box_t - box_b - 36 - win_h) / 2.0)

    c.setFillColor(HexColor("#d7e4ee"))
    c.setStrokeColor(INK)
    c.setLineWidth(1.3)
    c.rect(ox, oy, win_w, win_h, fill=1, stroke=1)

    if job.ceiling_height is not None:
        c.setStrokeColor(GOLD)
        c.setLineWidth(1.0)
        ceil_y = oy + win_h + 14
        c.line(ox, ceil_y, ox + win_w, ceil_y)
        c.setFillColor(INK)
        c.setFont(font, 7)
        c.drawString(ox, ceil_y + 3, f"CEILING {format_inches(job.ceiling_height)}")

    placed = _span(job, ox, scale)
    spacing = job.carrier_spacing or 2.125
    if placed:
        x0, x1 = placed
        if job.layered:
            c.setFillColor(HexColor("#eef3f8"))
            c.rect(x0, oy, x1 - x0, win_h, fill=1, stroke=0)
            _elevation_folds(c, x0, x1, oy + 2, oy + win_h - 2,
                             spacing * scale, HexColor("#9eb0c2"), 0.6)
        wash = HexColor("#f3efe6") if job.layer == "sheer" and not job.layered else HexColor("#e7dcc8")
        c.setFillColor(wash, alpha=0.72 if job.layered else 1)
        c.rect(x0, oy, max(x1 - x0, 1), win_h, fill=1, stroke=0)
        ink = HexColor("#7f92a3") if job.layer == "sheer" and not job.layered else INK
        _elevation_folds(c, x0, x1, oy + 2, oy + win_h - 2, spacing * scale, ink, 0.8)
        if job.side_panels and job.offset and job.offset > 0.5:
            _paint_fabric(c, ox, oy, max(x0 - ox, 1), win_h, job.fabric_image, font)
            right_w = ox + win_w - x1
            _paint_fabric(c, x1, oy, max(right_w, 1), win_h, job.fabric_image, font)
            c.setFillColor(INK)
            c.setFont(font, 6)
            label = "DRAPERY  ·  RIPPLEFOLD SHEER  ·  DRAPERY"
            if job.side_widths is not None:
                label += f"  ·  {format_inches(job.side_widths).replace(chr(34), '')} WIDTHS"
            c.drawString(ox, oy - 52, label[:70])
        c.setStrokeColor(INK)
        c.setLineWidth(1.4)
        c.line(x0, oy + win_h, x1, oy + win_h)
        _dim_h(c, x0, x1, oy - 12, format_inches(job.coverage_width), font)
        if job.offset and job.offset > 0.05:
            _dim_h(c, ox, x0, oy - 26, format_inches(job.offset), font)
            right = job.window_width - job.offset - job.coverage_width
            if right > 0.05:
                _dim_h(c, x1, ox + win_w, oy - 26, format_inches(right), font)
    else:
        c.setFillColor(MUTE)
        c.setFont(font, 7)
        c.drawString(ox + 4, oy + win_h / 2.0, "COVERAGE POSITION NOT GIVEN")

    _dim_h(c, ox, ox + win_w, oy - 40, format_inches(job.window_width), font)
    _dim_v(c, ox + win_w + 14, oy, oy + win_h, format_inches(job.window_height), font)
    c.setFillColor(MUTE)
    c.setFont(font, 6.5)
    c.drawString(ox, oy + win_h + 4, "RIPPLEFOLD")


def _draw_top(c, job: RipplefoldJob, font, font_b) -> None:
    c.setFillColor(INK)
    c.setFont(font_b, 9)
    c.drawString(458, PH - HDR_H - 18, "TOP VIEW")
    frame_l, frame_r = 458.0, 760.0
    frame_t = PH - HDR_H - 28
    frame_b = frame_t - 168
    c.setStrokeColor(HAIR)
    c.setFillColor(HexColor("#fbf8f1"))
    c.setLineWidth(0.8)
    c.roundRect(frame_l, frame_b, frame_r - frame_l, frame_t - frame_b, 3, fill=1, stroke=1)

    scale = (frame_r - frame_l - 28) / job.window_width
    ox = frame_l + 14
    wall_y = frame_t - 28
    win_w = job.window_width * scale
    c.setStrokeColor(INK)
    c.setLineWidth(2.0)
    c.line(ox, wall_y, ox + win_w, wall_y)
    c.setFillColor(MUTE)
    c.setFont(font, 6)
    c.drawString(ox, wall_y + 4, "WINDOW")

    placed = _span(job, ox, scale)
    track_y = wall_y - 16
    spacing_pt = (job.carrier_spacing or 2.125) * scale
    if not placed:
        c.setFillColor(MUTE)
        c.setFont(font, 7)
        c.drawString(ox, track_y, "TRACK POSITION NOT GIVEN")
        return

    x0, x1 = placed
    if job.side_panels and job.offset and job.offset > 0.5:
        c.setFillColor(HexColor("#c4b49a"))
        c.rect(ox, track_y - 10, max(x0 - ox, 1), 8, fill=1, stroke=0)
        c.rect(x1, track_y - 10, max(ox + win_w - x1, 1), 8, fill=1, stroke=0)
        c.setFillColor(INK)
        c.setFont(font, 5)
        c.drawString(ox, track_y - 18, "DRAPERY")
    layers = [("SHEER", HexColor("#9eb0c2"), track_y)] if job.layered else []
    face = HexColor("#7f92a3") if job.layer == "sheer" and not job.layered else INK
    layers.append((job.layer.upper(), face, track_y - (14 if job.layered else 0)))
    for name, color, y in layers:
        c.setStrokeColor(color)
        c.setLineWidth(1.6)
        c.line(x0, y, x1, y)
        n = max(2, int(round(job.coverage_width / (job.carrier_spacing or 2.125))))
        for i in range(n + 1):
            tick_x = x0 + (x1 - x0) * i / n
            c.line(tick_x, y - 2.2, tick_x, y + 2.2)
        period = max(spacing_pt * 2.0, 4)
        _wave(c, x0, x1, y - 12, 7 if name != "SHEER" else 5, period, color, 0.8)
        if job.masters == "overlap":
            mid = (x0 + x1) / 2.0
            c.setStrokeColor(GOLD)
            c.setLineWidth(1.2)
            c.line(mid - period / 2.0, y - 3, mid + period / 2.0, y + 3)
        elif job.masters == "butt" and job.control == "center":
            mid = (x0 + x1) / 2.0
            c.setStrokeColor(GOLD)
            c.setLineWidth(1.1)
            c.line(mid, y - 5, mid, y + 5)
        c.setFillColor(MUTE)
        c.setFont(font, 5.5)
        c.drawString(x1 + 3, y - 2, name[:12])

    if job.stack and job.coverage_width:
        stack_w = job.stack / job.coverage_width * (x1 - x0)
        c.setStrokeColor(GOLD)
        c.setLineWidth(0.6)
        ends = [x0] if job.control == "one-way" else [x0, x1 - stack_w]
        for sx in ends:
            c.rect(sx, track_y - 28, stack_w, 8, fill=0, stroke=1)
        c.setFillColor(INK)
        c.setFont(font, 6)
        c.drawString(x0, track_y - 38, f"STACK {format_inches(job.stack)}")

    _dim_h(c, x0, x1, frame_b + 22, f"TRACK {format_inches(job.track_length)}", font)
    _dim_h(c, ox, ox + win_w, frame_b + 8, format_inches(job.window_width), font)


def _draw_table(c, job: RipplefoldJob, font, font_b) -> None:
    x, y = 458.0, PH - HDR_H - 214
    c.setFillColor(INK)
    c.setFont(font_b, 9)
    c.drawString(x, y, "RIPPLEFOLD")
    y -= 14
    rows = _spec_rows(job)
    c.setFont(font, 6.6)
    for label, value in rows:
        c.setFillColor(MUTE)
        c.drawString(x, y, label)
        c.setFillColor(INK)
        c.drawString(x + 78, y, value[:42])
        y -= 11
    if job.notes:
        y -= 4
        c.setFillColor(MUTE)
        c.setFont(font, 6)
        for note in job.notes:
            c.drawString(x, y, note.upper()[:64])
            y -= 9


def render_ripplefold_pdf(spec: dict) -> bytes:
    """Landscape RIPPLEFOLD sheet. Does not invent mount or ceiling."""
    job = resolve_ripplefold(spec)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(PW, PH))
    c.setTitle("RIPPLEFOLD")
    c.setAuthor(PDF_AUTHOR)
    c.setCreator(PDF_CREATOR)
    c.setSubject("RIPPLEFOLD shop drawing")
    client = str(spec.get("client_name") or "WORKROOM")
    project = str(spec.get("project") or spec.get("site_address") or "DRAPERY")
    render_chrome_bands(
        c,
        sheet_no=int(spec.get("sheet_no") or 1),
        total=int(spec.get("sheet_total") or 1),
        right_title=str(spec.get("sheet_title") or "RIPPLEFOLD"),
        client=client,
        project=project,
        rev="A",
        date=_sheet_date(),
    )
    _font_b, font, font_bold, _italic = _ensure_fonts()
    _draw_elevation(c, job, font, font_bold)
    _draw_top(c, job, font, font_bold)
    _draw_table(c, job, font, font_bold)
    c.showPage()
    c.save()
    return buf.getvalue()


def _window_spec(window: dict) -> dict:
    dims: dict = {}

    def take(dest: str, *keys: str) -> None:
        for key in keys:
            if key in window and window[key] not in (None, ""):
                dims[dest] = window[key]
                return

    take("width", "width", "windowWidth", "window_width")
    take("height", "height", "windowHeight", "window_height")
    take("coverage_width", "coverageWidth", "coverage_width", "coverage")
    take("track_length", "trackLength", "track_length", "track")
    take("fullness_pct", "fullnessPct", "fullness_pct", "fullnessPercent")
    if "fullness_pct" not in dims and window.get("fullness") not in (None, ""):
        dims["fullness"] = window["fullness"]
    take("carrier", "carrier", "carrierNo", "carrier_no")
    take("carrier_spacing", "carrierSpacing", "carrier_spacing", "spacing")
    take("masters", "masters", "master")
    take("control", "control", "drawDirection", "draw", "draw_direction")
    take("coverage_align", "coverageAlign", "coverage_align", "align")
    take("offset", "coverageOffset", "coverage_offset", "offset")
    mount = window.get("mountType", window.get("mount"))
    if mount not in (None, ""):
        dims["mount"] = mount
    take("ceiling_height", "ceilingHeight", "ceiling_height", "ceiling")
    take("mount_height", "mountHeight", "mount_height")
    take("layer", "layer", "fabricLayer", "fabric_layer")
    if window.get("layered") not in (None, "", False):
        dims["layered"] = window["layered"]
    return {"product_type": "ripplefold", "dims": dims}


def build_ripplefold_quote_svg(window: dict) -> str:
    """Quote / presentation card. Mount stays blank when the window omits it."""
    name = escape(str(window.get("name") or "Window"))
    qty = window.get("quantity") or 1
    try:
        job = resolve_ripplefold(_window_spec(window))
    except ValueError as exc:
        return (
            '<div style="margin:6px 0;padding:8px;border:1px solid #cdc4b0;'
            'background:#f7f3ea;font-size:12px">RIPPLEFOLD — '
            f'{escape(str(exc))}</div>'
        )
    scale = 1.7
    win_w = max(job.window_width * scale, 120)
    win_h = max(job.window_height * scale, 80)
    pad = 36
    svg_w = int(win_w + pad * 2 + 28)
    svg_h = int(win_h + 108)
    ox, oy = pad, 28
    parts = [
        '<div style="display:inline-block;vertical-align:top;margin:6px 8px 6px 0;'
        'page-break-inside:avoid">',
        f'<svg width="{svg_w}" height="{svg_h}" viewBox="0 0 {svg_w} {svg_h}" '
        'xmlns="http://www.w3.org/2000/svg" style="max-width:100%;background:#f7f3ea;'
        'border:1px solid #cdc4b0">',
        f'<text x="8" y="16" font-size="11" font-weight="700" fill="#20241f">'
        f'RIPPLEFOLD  {name}{f" (×{qty})" if qty and qty > 1 else ""}</text>',
        f'<text x="{svg_w - 8}" y="16" text-anchor="end" font-size="8" fill="#7b7466">'
        'ELEVATION</text>',
        f'<rect x="{ox}" y="{oy}" width="{win_w}" height="{win_h}" fill="#d7e4ee" '
        'stroke="#20241f" stroke-width="1.4"/>',
    ]
    if job.offset is not None:
        x0 = ox + job.offset * scale
        cov = job.coverage_width * scale
        wash = "#f3efe6" if job.layer == "sheer" else "#e7dcc8"
        parts.append(
            f'<rect x="{x0}" y="{oy}" width="{cov}" height="{win_h}" fill="{wash}"/>'
        )
        spacing = (job.carrier_spacing or 2.125) * scale
        x = x0
        stroke = "#7f92a3" if job.layer == "sheer" else "#20241f"
        while x <= x0 + cov:
            parts.append(
                f'<path d="M{x:.1f},{oy + 1} C{x + spacing * 0.4:.1f},{oy + win_h * 0.35:.1f} '
                f'{x - spacing * 0.4:.1f},{oy + win_h * 0.65:.1f} {x:.1f},{oy + win_h - 1:.1f}" '
                f'fill="none" stroke="{stroke}" stroke-width="0.7"/>'
            )
            x += max(spacing, 3)
        parts.append(
            f'<line x1="{x0}" y1="{oy}" x2="{x0 + cov}" y2="{oy}" stroke="#20241f" stroke-width="2"/>'
        )
        parts.append(
            f'<text x="{(x0 + x0 + cov) / 2:.1f}" y="{oy + win_h + 14}" text-anchor="middle" '
            f'font-size="9" fill="#b8912f">{escape(format_inches(job.coverage_width))}</text>'
        )
    parts.append(
        f'<text x="{ox + win_w / 2:.1f}" y="{oy + win_h + 28}" text-anchor="middle" '
        f'font-size="10" fill="#b8912f" font-weight="700">{escape(format_inches(job.window_width))}</text>'
    )
    parts.append(
        f'<text x="{ox + win_w + 8}" y="{oy + win_h / 2:.1f}" font-size="10" fill="#b8912f" '
        f'font-weight="700">{escape(format_inches(job.window_height))}</text>'
    )
    # Top-view strip
    ty = oy + win_h + 40
    parts.append(
        f'<text x="{ox}" y="{ty}" font-size="8" fill="#20241f" font-weight="700">TOP VIEW</text>'
    )
    parts.append(
        f'<line x1="{ox}" y1="{ty + 10}" x2="{ox + win_w}" y2="{ty + 10}" '
        'stroke="#20241f" stroke-width="1.2"/>'
    )
    if job.offset is not None:
        x0 = ox + job.offset * scale
        cov = job.coverage_width * scale
        parts.append(
            f'<line x1="{x0}" y1="{ty + 18}" x2="{x0 + cov}" y2="{ty + 18}" '
            'stroke="#b8912f" stroke-width="2"/>'
        )
        period = max((job.carrier_spacing or 2.125) * scale * 2, 6)
        d = [f"M{x0:.1f},{ty + 28:.1f}"]
        steps = 40
        for i in range(1, steps + 1):
            t = i / steps
            x = x0 + cov * t
            y = ty + 28 + 5 * math.sin(t * cov / period * 2 * math.pi)
            d.append(f"L{x:.1f},{y:.1f}")
        parts.append(
            f'<path d="{" ".join(d)}" fill="none" stroke="#20241f" stroke-width="0.8"/>'
        )
    parts.append("</svg>")
    rows = _spec_rows(job)
    parts.append(
        f'<div style="margin-top:4px;padding:8px 10px;background:#f7f3ea;'
        f'border:1px solid #cdc4b0;font-size:0.72em;max-width:{svg_w}px;line-height:1.55">'
    )
    parts.append('<strong style="color:#20241f">RIPPLEFOLD</strong><br>')
    for label, value in rows:
        parts.append(f'<span style="color:#7b7466">{escape(label)}</span> '
                     f'{escape(value)}<br>')
    parts.append("</div></div>")
    return "".join(parts)
