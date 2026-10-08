"""Renderers for Plan, Elevation, and Section views from PieceSpec."""
from __future__ import annotations

import math
from typing import Optional, List, Tuple
from reportlab.lib.colors import HexColor, Color
from reportlab.pdfgen import canvas

from app.services.drawing.mockup_engine.spec import PieceSpec, SegmentSpec
from app.services.drawing.mockup_engine.math_layout import compute_channels, compute_tufts, compute_modules
from app.services.drawing.mockup_engine.canvas_helpers import (
    format_in, dim_h, dim_v, draw_scale_bar,
    INK, MUT, GOLD, PAPER, WHITE, GRAY_LINE, WOOD_FILL, WOOD_DARK
)


def render_plan_view(
    c: canvas.Canvas,
    spec: PieceSpec,
    ox: float,
    top: float,
    scale: float,
) -> None:
    """Render the true-shape plan view (top-down) for the piece."""
    s = scale
    shape = spec.footprint.shape
    d = spec.cushion.seat_depth_in * s
    t = spec.footprint.back_thickness_in * s
    back_c = HexColor(spec.material.color_hex)
    seat_c = HexColor(spec.material.seat_color_hex)
    seam_c = HexColor(spec.material.seam_color_hex)

    def draw_seat(x, y, w, h):
        c.setFillColor(seat_c)
        c.setStrokeColor(seam_c)
        c.setLineWidth(0.6)
        c.rect(x, y, w, h, stroke=1, fill=1)

    def draw_back(x, y, w, h):
        c.setFillColor(back_c)
        c.setStrokeColor(seam_c)
        c.setLineWidth(0.6)
        c.rect(x, y, w, h, stroke=1, fill=1)

    if shape == "u_shape":
        # Extract runs: left, main, right
        seg_dict = {seg.name.lower(): seg.length_in for seg in spec.footprint.segments}
        left_len = seg_dict.get("left", 37.75)
        main_len = seg_dict.get("main", 249.75)
        right_len = seg_dict.get("right", 48.5)

        l, m, r = left_len * s, main_len * s, right_len * s
        x0 = ox + t + d  # main seat starts after left back + left seat
        
        # Main leg
        draw_back(x0, top - t, m, t)
        draw_seat(x0, top - t - d, m, d)

        # Left leg (returns down)
        draw_back(ox, top - t - l, t, l)
        draw_seat(ox + t, top - t - l, d, l)

        # Right leg (returns down)
        draw_back(x0 + m + d, top - t - r, t, r)
        draw_seat(x0 + m, top - t - r, d, r)

        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(x0 + m / 2, top - t - d / 2 - 2, f'SEAT (plain) · {format_in(spec.cushion.seat_depth_in)} deep')

        dim_h(c, x0, x0 + m, top + 8, f"MAIN  {format_in(main_len)}")
        dim_v(c, ox - 10, top - t - l, top - t, f"LEFT {format_in(left_len)}", right=False)
        dim_v(c, x0 + m + d + t + 10, top - t - r, top - t, f"RIGHT {format_in(right_len)}")
        dim_v(c, x0 + m * 0.18, top - t - d, top - t, format_in(spec.cushion.seat_depth_in), size=6)

        c.setFillColor(MUT)
        c.setFont("Helvetica", 6.5)
        c.drawString(x0 + 4, top - t - d - 10, f"{spec.back.style} backs ({spec.material.color_name} band) on the wall side of every leg")

    elif shape == "l_shape":
        seg_dict = {seg.name.lower(): seg.length_in for seg in spec.footprint.segments}
        short_len = seg_dict.get("short", seg_dict.get("leg1", 95.375))
        long_len = seg_dict.get("long", seg_dict.get("leg2", 107.75))

        sh, lg = short_len * s, long_len * s
        # Short run (top)
        draw_back(ox, top - t, sh, t)
        draw_seat(ox, top - t - d, sh, d)

        # Long run (right)
        draw_seat(ox + sh, top - t - lg, d, lg)
        draw_back(ox + sh + d, top - t - lg, t, lg)

        dim_h(c, ox, ox + sh, top + 8, f"SHORT  {format_in(short_len)}")
        dim_v(c, ox + sh + d + t + 10, top - t - lg, top - t, f"LONG {format_in(long_len)}")

        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(ox + sh / 2, top - t - d / 2 - 2, "SEAT (plain)")
        dim_v(c, ox + sh * 0.12, top - t - d, top - t, format_in(spec.cushion.seat_depth_in), size=6)

    elif shape in ("straight", "single"):
        width = spec.footprint.overall_width_in or (spec.footprint.segments[0].length_in if spec.footprint.segments else 36.0)
        w = width * s
        draw_back(ox, top - t, w, t)
        draw_seat(ox, top - t - d, w, d)

        dim_h(c, ox, ox + w, top + 8, f"OVERALL WIDTH  {format_in(width)}")
        dim_v(c, ox + w + 8, top - t - d, top - t, format_in(spec.cushion.seat_depth_in), size=6)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 6.5)
        c.drawCentredString(ox + w / 2, top - t - d / 2 - 2, f"SEAT · {format_in(spec.cushion.seat_depth_in)} deep")

    elif spec.casework:
        # Wall unit / cabinet casework plan view
        cw = spec.casework
        w = cw.overall_width_in * s
        dp = cw.overall_depth_in * s
        c.setFillColor(WOOD_FILL)
        c.setStrokeColor(WOOD_DARK)
        c.setLineWidth(0.8)
        c.rect(ox, top - dp, w, dp, stroke=1, fill=1)

        # Draw box divisions in plan
        cur_x = ox
        for b in cw.boxes:
            bw = b.width_in * s
            c.setStrokeColor(WOOD_DARK)
            c.line(cur_x, top - dp, cur_x, top)
            cur_x += bw

        dim_h(c, ox, ox + w, top + 8, f"CASEWORK WIDTH  {format_in(cw.overall_width_in)}")
        dim_v(c, ox + w + 8, top - dp, top, f"{format_in(cw.overall_depth_in)} D", size=6)
        c.setFillColor(WHITE)
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(ox + w / 2, top - dp / 2 - 2, f"MILLWORK / CASEWORK PLAN · {cw.wood_species}")


def render_elevation_segment(
    c: canvas.Canvas,
    spec: PieceSpec,
    x: float,
    y: float,
    scale: float,
    length: float,
    name: str,
) -> float:
    """Render front elevation for an upholstery piece segment."""
    s = scale
    w = length * s
    back_h = spec.back.net_back_height_in * s
    seat_h = spec.cushion.cushion_thickness_in * s
    by = y + seat_h
    bh = back_h

    back_c = HexColor(spec.material.color_hex)
    seat_c = HexColor(spec.material.seat_color_hex)
    seam_c = HexColor(spec.material.seam_color_hex)

    # Seat cushion band
    c.setFillColor(seat_c)
    c.setStrokeColor(seam_c)
    c.setLineWidth(0.6)
    c.rect(x, y, w, seat_h, stroke=1, fill=1)

    # Backrest base rect
    c.setFillColor(back_c)
    c.rect(x, by, w, bh, stroke=1, fill=1)

    # Back pattern calculation
    pattern = spec.back.style
    note = ""

    if pattern == "channel":
        target_ch = spec.back.channel_width_in
        widths, end = compute_channels(length, target_ch)
        c.setStrokeColor(seam_c)
        c.setLineWidth(0.9)
        xx = x
        for cw in widths[:-1]:
            xx += cw * s
            c.line(xx, by + 1, xx, by + bh - 1)
        # Soft highlight line in each channel
        c.setStrokeColor(HexColor("#B67748"))
        c.setLineWidth(0.4)
        xx = x
        for cw in widths:
            if cw * s > 6:
                c.line(xx + cw * s * 0.5, by + 3, xx + cw * s * 0.5, by + bh - 3)
            xx += cw * s

        n_full = sum(1 for cw in widths if abs(cw - target_ch) < 1e-9)
        note = f'{n_full} x {format_in(target_ch)} channels'
        if end > 0:
            if end >= 3.0:
                note += f' + {format_in(end)} end channel each side'
            else:
                note += f' + {format_in(end)} end trim each side'

    elif pattern in ("tufted", "button_tufted"):
        sp_x = spec.back.tuft_spacing_x_in or 8.0
        sp_y = spec.back.tuft_spacing_y_in or 8.0
        tufts, meta = compute_tufts(length, spec.back.net_back_height_in, sp_x, sp_y)
        c.setFillColor(seam_c)
        for (tx, ty) in tufts:
            c.circle(x + tx * s, by + ty * s, 1.8, stroke=0, fill=1)
        note = f'Diamond tufted back: {meta["rows"]} rows x {meta["cols"]} cols (~{format_in(sp_x)} x {format_in(sp_y)} pattern)'

    elif pattern in ("padded_modules", "basketweave"):
        mw = spec.back.module_width_in or 12.0
        mh = spec.back.module_height_in or 8.0
        mods, meta = compute_modules(length, spec.back.net_back_height_in, mw, mh)
        c.setStrokeColor(seam_c)
        c.setLineWidth(0.8)
        for (mx, my, mod_w, mod_h) in mods:
            c.rect(x + mx * s, by + my * s, mod_w * s, mod_h * s, stroke=1, fill=0)
        note = f'Padded module back: {meta["nx"]} x {meta["ny"]} grid ({format_in(meta["mod_w"])} x {format_in(meta["mod_h"])})'

    elif pattern == "plain":
        note = f'Plain back ({spec.material.name})'

    # Dimensions
    dim_h(c, x, x + w, by + bh + 8, f"{name}  {format_in(length)}")
    dim_v(c, x + w + 8, by, by + bh, f'{format_in(spec.back.net_back_height_in)} net back', size=6)

    c.setFillColor(MUT)
    c.setFont("Helvetica", 6.5)
    c.drawString(x, y - 10, note)
    c.drawString(x, y - 19, f"seat cushion: plain {spec.material.color_name} (height shown nominal)")

    return by + bh


def render_casework_elevation(
    c: canvas.Canvas,
    spec: PieceSpec,
    x: float,
    y: float,
    scale: float,
) -> float:
    """Render front elevation of a WoodCraft casework / wall unit."""
    s = scale
    cw = spec.casework
    w = cw.overall_width_in * s
    h = cw.overall_height_in * s
    tk_h = cw.toe_kick_height_in * s

    # Toe kick recessed band
    c.setFillColor(HexColor("#333333"))
    c.rect(x, y, w, tk_h, stroke=0, fill=1)

    # Main carcass outline
    c.setFillColor(WOOD_FILL)
    c.setStrokeColor(WOOD_DARK)
    c.setLineWidth(1.0)
    c.rect(x, y + tk_h, w, h - tk_h, stroke=1, fill=1)

    # Render individual boxes
    cur_x = x
    for b in cw.boxes:
        bw = b.width_in * s
        bh = b.height_in * s
        by = y + tk_h + (b.y_offset_in * s)

        c.setStrokeColor(WOOD_DARK)
        c.setLineWidth(0.8)
        c.rect(cur_x, by, bw, bh, stroke=1, fill=0)

        # Draw shelves or drawers
        if b.drawers > 0:
            dh = bh / b.drawers
            for d_idx in range(b.drawers):
                dy = by + d_idx * dh
                c.rect(cur_x + 2, dy + 2, bw - 4, dh - 4, stroke=1, fill=0)
                # Drawer pull
                c.setLineWidth(1.2)
                c.line(cur_x + bw / 2 - 6, dy + dh / 2, cur_x + bw / 2 + 6, dy + dh / 2)
        elif b.shelves > 0:
            sh_gap = bh / (b.shelves + 1)
            for s_idx in range(1, b.shelves + 1):
                sy = by + s_idx * sh_gap
                c.setLineWidth(0.8)
                c.line(cur_x, sy, cur_x + bw, sy)
        elif b.doors > 0:
            door_w = bw / b.doors
            for dr_idx in range(b.doors):
                drx = cur_x + dr_idx * door_w
                c.rect(drx + 2, by + 2, door_w - 4, bh - 4, stroke=1, fill=0)
                # Knob/handle
                c.circle(drx + (door_w - 6 if dr_idx == 0 else 6), by + bh / 2, 1.5, stroke=1, fill=1)

        # Label bay inside or right below bay top
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 5.5)
        short_name = b.name.split("-")[0].strip()
        c.drawCentredString(cur_x + bw / 2, by + bh - 10, f"{short_name} ({format_in(b.width_in)})")

        cur_x += bw

    # Overall casework dimensions
    dim_h(c, x, x + w, y + h + 10, f"CASEWORK OVERALL  {format_in(cw.overall_width_in)}")
    dim_v(c, x + w + 12, y, y + h, f"{format_in(cw.overall_height_in)} H", size=6)

    c.setFillColor(MUT)
    c.setFont("Helvetica", 6.5)
    c.drawString(x, y - 10, f"Wood species: {cw.wood_species} · Finish: {cw.finish} · Carcass boxes: {len(cw.boxes)}")
    c.drawString(x, y - 19, f"Toe kick: {format_in(cw.toe_kick_height_in)} H x {format_in(cw.toe_kick_depth_in)} recessed")

    return y + h


def render_side_section(
    c: canvas.Canvas,
    spec: PieceSpec,
    x: float,
    y: float,
    scale: float,
) -> None:
    """Render a clean side section view of the seat & back."""
    s = scale
    d = spec.cushion.seat_depth_in * s
    th = spec.footprint.back_thickness_in * s
    sh = spec.cushion.seat_height_in * s
    bh = spec.back.net_back_height_in * s
    cth = spec.cushion.cushion_thickness_in * s

    back_c = HexColor(spec.material.color_hex)
    seat_c = HexColor(spec.material.seat_color_hex)
    seam_c = HexColor(spec.material.seam_color_hex)

    # Base / plinth
    plinth_h = max(0, sh - cth)
    c.setFillColor(HexColor("#444444"))
    c.rect(x + th, y, d, plinth_h, stroke=1, fill=1)

    # Seat cushion (sits on base)
    c.setFillColor(seat_c)
    c.setStrokeColor(seam_c)
    c.rect(x + th, y + plinth_h, d, cth, stroke=1, fill=1)

    # Backrest (sits above seat cushion plane)
    c.setFillColor(back_c)
    c.rect(x, y + sh, th, bh, stroke=1, fill=1)

    # Wall ghost line
    c.setStrokeColor(GRAY_LINE)
    c.setDash(2, 2)
    c.line(x, y - 10, x, y + sh + bh + 20)
    c.setDash()

    dim_h(c, x + th, x + th + d, y - 10, f'SEAT {format_in(spec.cushion.seat_depth_in)}')
    dim_v(c, x + th + d + 8, y, y + sh, f'SEAT H {format_in(spec.cushion.seat_height_in)}', size=6)
    dim_v(c, x - 10, y + sh, y + sh + bh, f'BACK H {format_in(spec.back.net_back_height_in)}', size=6, right=False)

    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString(x + th + d / 2, y + sh + bh + 12, "SIDE SECTION")
