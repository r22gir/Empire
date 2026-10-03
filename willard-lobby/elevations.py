"""Schematic elevations for the Willard lobby pack.

Flat line work only. Proportions follow field inches. No photoreal fill.
Window 4 width was not on the June 9 sheet — the passway is diagrammatic
and carries no invented width.
"""

from __future__ import annotations

import math

from reportlab.lib.colors import HexColor

from house import (
    CREAM,
    GLASS,
    GOLD,
    GOLD_DEEP,
    INK,
    INK2,
    JABOT,
    MUTED,
    PANEL,
    PANEL_LINE,
    SHEER,
    SHEER_LINE,
    SWAG,
    VOID,
    WALL,
    dim_h,
    dim_v,
    extension,
)

WOOD = HexColor("#5C4636")
STONE = HexColor("#C9C3B8")
CASING = HexColor("#D9D2C6")


def _ripple(c, x, y, w, h, waves=4):
    c.setStrokeColor(PANEL_LINE)
    c.setLineWidth(0.45)
    for i in range(1, waves + 1):
        px = x + w * i / (waves + 1)
        path = c.beginPath()
        steps = 24
        for s in range(steps + 1):
            t = s / steps
            yy = y + 3 + (h - 6) * t
            xx = px + math.sin(t * math.pi * 5.0) * (w * 0.045)
            if s == 0:
                path.moveTo(xx, yy)
            else:
                path.lineTo(xx, yy)
        c.drawPath(path, stroke=1, fill=0)


def _panel(c, x, y, w, h):
    c.setFillColor(PANEL)
    c.setStrokeColor(INK)
    c.setLineWidth(0.8)
    c.rect(x, y, w, h, fill=1, stroke=1)
    _ripple(c, x, y, w, h)


def _fringe_edge(c, x, y, h, side):
    """Gold leading-edge fringe. side +1 draws ticks to the right of x."""
    c.setStrokeColor(GOLD_DEEP)
    c.setLineWidth(1.35)
    c.line(x, y + 2, x, y + h - 2)
    c.setLineWidth(0.45)
    step = 7
    yy = y + 4
    while yy < y + h - 4:
        c.line(x, yy, x + side * 4.5, yy - 2.2)
        yy += step


def _sheer(c, x, y, w, h):
    c.setFillColor(SHEER)
    c.rect(x, y, w, h, fill=1, stroke=0)
    c.setStrokeColor(SHEER_LINE)
    c.setLineWidth(0.35)
    for i in range(1, 7):
        xx = x + w * i / 7.0
        c.line(xx, y, xx, y + h)


def _tassel(c, x, y, length):
    c.setStrokeColor(GOLD_DEEP)
    c.setLineWidth(0.7)
    c.line(x, y, x, y - length * 0.42)
    c.setFillColor(GOLD)
    head_y = y - length * 0.48
    c.circle(x, head_y, 2.1, fill=1, stroke=0)
    top = head_y - 2.2
    bot = y - length
    path = c.beginPath()
    path.moveTo(x - 3.4, top)
    path.lineTo(x + 3.4, top)
    path.lineTo(x + 1.1, bot)
    path.lineTo(x - 1.1, bot)
    path.close()
    c.setFillColor(GOLD)
    c.drawPath(path, fill=1, stroke=0)
    c.setStrokeColor(GOLD_DEEP)
    c.setLineWidth(0.3)
    for i in range(-2, 3):
        c.line(x + i * 0.7, top, x + i * 0.28, bot)


def _bullion(c, x, y, side):
    """Tieback at (x, y). side +1 hangs the tassel to the right."""
    c.setStrokeColor(GOLD_DEEP)
    c.setLineWidth(0.8)
    c.line(x, y, x + side * 10, y)
    _tassel(c, x + side * 10, y + 2, 16)


def _swag_fringe(c, p0, p1, p2, p3):
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.45)
    for i in range(1, 14):
        t = i / 14.0
        u = 1 - t
        x = u**3 * p0[0] + 3 * u**2 * t * p1[0] + 3 * u * t**2 * p2[0] + t**3 * p3[0]
        y = u**3 * p0[1] + 3 * u**2 * t * p1[1] + 3 * u * t**2 * p2[1] + t**3 * p3[1]
        c.line(x, y, x, y - 5)


def _single_swag(c, x, top, w, depth):
    shoulder_l = (x + w * 0.20, top - depth * 0.20)
    dip_l = (x + w * 0.38, top - depth)
    mid = (x + w * 0.50, top - depth)
    dip_r = (x + w * 0.62, top - depth)
    shoulder_r = (x + w * 0.80, top - depth * 0.20)
    left = (x + w * 0.03, top)
    right = (x + w * 0.97, top)
    path = c.beginPath()
    path.moveTo(*left)
    path.curveTo(shoulder_l[0], shoulder_l[1], dip_l[0], dip_l[1], mid[0], mid[1])
    path.curveTo(dip_r[0], dip_r[1], shoulder_r[0], shoulder_r[1], right[0], right[1])
    path.lineTo(right[0], top + 1)
    path.lineTo(left[0], top + 1)
    path.close()
    c.setFillColor(SWAG)
    c.setStrokeColor(INK)
    c.setLineWidth(0.8)
    c.drawPath(path, fill=1, stroke=1)
    _swag_fringe(c, left, shoulder_l, dip_l, mid)
    _swag_fringe(c, mid, dip_r, shoulder_r, right)
    _tassel(c, x + w * 0.50, top - depth, max(14, depth * 0.55))


def _one_swag_span(c, x0, x1, top, depth, tassel=False):
    w = x1 - x0
    left = (x0, top)
    c1 = (x0 + w * 0.25, top - depth)
    mid = (x0 + w * 0.50, top - depth)
    c2 = (x0 + w * 0.75, top - depth)
    right = (x1, top)
    path = c.beginPath()
    path.moveTo(*left)
    path.curveTo(c1[0], c1[1], mid[0] - w * 0.05, mid[1], mid[0], mid[1])
    path.curveTo(mid[0] + w * 0.05, mid[1], c2[0], c2[1], right[0], right[1])
    path.lineTo(right[0], top + 1)
    path.lineTo(left[0], top + 1)
    path.close()
    c.setFillColor(SWAG)
    c.setStrokeColor(INK)
    c.setLineWidth(0.75)
    c.drawPath(path, fill=1, stroke=1)
    _swag_fringe(c, left, c1, mid, mid)
    _swag_fringe(c, mid, c2, right, right)
    if tassel:
        _tassel(c, (x0 + x1) / 2.0, top - depth, max(13, depth * 0.5))


def _jabot(c, x, top, side, length, width):
    path = c.beginPath()
    if side < 0:
        path.moveTo(x, top)
        path.lineTo(x + width, top - 1)
        path.lineTo(x + width * 0.62, top - length)
        path.lineTo(x + width * 0.12, top - length * 0.90)
    else:
        path.moveTo(x - width, top - 1)
        path.lineTo(x, top)
        path.lineTo(x - width * 0.12, top - length * 0.90)
        path.lineTo(x - width * 0.62, top - length)
    path.close()
    c.setFillColor(JABOT)
    c.setStrokeColor(INK)
    c.setLineWidth(0.6)
    c.drawPath(path, fill=1, stroke=1)


def _formal_valance(c, x, top, w, depth):
    path = c.beginPath()
    path.moveTo(x, top)
    path.lineTo(x + w, top)
    path.lineTo(x + w, top - depth * 0.62)
    path.curveTo(
        x + w * 0.78, top - depth * 0.62,
        x + w * 0.66, top - depth,
        x + w * 0.50, top - depth,
    )
    path.curveTo(
        x + w * 0.34, top - depth,
        x + w * 0.22, top - depth * 0.62,
        x, top - depth * 0.62,
    )
    path.close()
    c.setFillColor(SWAG)
    c.setStrokeColor(INK)
    c.setLineWidth(0.8)
    c.drawPath(path, fill=1, stroke=1)
    # bottom trim ticks along the scallop, schematic
    c.setStrokeColor(GOLD)
    c.setLineWidth(0.45)
    for i in range(1, 16):
        t = i / 16.0
        xx = x + w * t
        # approximate scallop depth
        dip = depth * (0.62 + 0.38 * math.sin(math.pi * t))
        c.line(xx, top - dip, xx, top - dip - 4.5)
    _tassel(c, x + w * 0.50, top - depth, max(14, depth * 0.45))


def _track(c, x, top, w):
    c.setStrokeColor(INK)
    c.setLineWidth(1.3)
    c.line(x + 2, top + 4, x + w - 2, top + 4)
    c.setLineWidth(0.4)
    c.line(x + 2, top + 7, x + w - 2, top + 7)


def _rod(c, x, top, w):
    c.setStrokeColor(INK)
    c.setLineWidth(1.5)
    c.line(x - 8, top + 5, x + w + 8, top + 5)
    # returns / finial ticks
    c.setFillColor(INK)
    c.circle(x - 8, top + 5, 2.2, fill=1, stroke=0)
    c.circle(x + w + 8, top + 5, 2.2, fill=1, stroke=0)


def _rings(c, x, top, w, count):
    c.setStrokeColor(INK)
    c.setLineWidth(0.6)
    c.setFillColor(CREAM)
    if count <= 1:
        return
    for i in range(count):
        xx = x + w * (i + 0.5) / count
        c.circle(xx, top + 5, 1.7, fill=1, stroke=1)


def _floor(c, x, y, w):
    c.setStrokeColor(INK)
    c.setLineWidth(1.1)
    c.line(x - 14, y, x + w + 14, y)


def _surround(c, ox, oy, ow, oh, kind):
    pad = 8
    if kind == "wood":
        c.setFillColor(WOOD)
    elif kind == "stone":
        c.setFillColor(STONE)
    elif kind == "case":
        c.setFillColor(CASING)
    else:
        c.setFillColor(WALL)
    c.setStrokeColor(INK2)
    c.setLineWidth(0.6)
    c.rect(ox - pad, oy - pad, ow + pad * 2, oh + pad * 2 + 6, fill=1, stroke=1)


def _stack_pair(c, ox, oy, ow, oh, stack, sheer, fringe=True, bullion=True):
    if sheer == "sheer":
        _sheer(c, ox, oy, ow, oh)
    elif sheer == "glass":
        c.setFillColor(GLASS)
        c.rect(ox, oy, ow, oh, fill=1, stroke=0)
    elif sheer == "void":
        c.setFillColor(VOID)
        c.rect(ox, oy, ow, oh, fill=1, stroke=0)
    pw = ow * stack
    _panel(c, ox, oy, pw, oh)
    _panel(c, ox + ow - pw, oy, pw, oh)
    if fringe:
        _fringe_edge(c, ox + pw, oy, oh, +1)
        _fringe_edge(c, ox + ow - pw, oy, oh, -1)
    if bullion:
        by = oy + oh * 0.40
        _bullion(c, ox + pw - 2, by, -1)
        _bullion(c, ox + ow - pw + 2, by, +1)
    return pw


def _frame_dims(c, ox, oy, ow, oh, width_label, height_label):
    if width_label:
        dim_y = oy + oh + 22
        extension(c, ox, oy + oh, ox, dim_y)
        extension(c, ox + ow, oy + oh, ox + ow, dim_y)
        dim_h(c, ox, ox + ow, dim_y, width_label)
    if height_label:
        dim_x = ox - 16
        extension(c, ox, oy, dim_x, oy)
        extension(c, ox, oy + oh, dim_x, oy + oh)
        dim_v(c, dim_x, oy, oy + oh, height_label)


def draw_lobby_pair(c, box, swag, surround, width_label, height_label):
    """Windows 1 and 2. box is (x, y, w, h) of the drawing field, y at bottom."""
    x, y, bw, bh = box
    # Field ratio 72 3/16 by 105 5/8.
    w_in, h_in = 72 + 3 / 16, 105 + 5 / 8
    pad_l, pad_r, pad_t, pad_b = 52, 18, 36, 28
    scale = min((bw - pad_l - pad_r) / w_in, (bh - pad_t - pad_b) / h_in)
    ow, oh = w_in * scale, h_in * scale
    ox = x + pad_l + ((bw - pad_l - pad_r) - ow) / 2
    oy = y + pad_b + ((bh - pad_t - pad_b) - oh) / 2
    _surround(c, ox, oy, ow, oh, surround)
    _stack_pair(c, ox, oy, ow, oh, stack=0.22, sheer="sheer")
    top = oy + oh
    depth = oh * (0.15 if swag == "single" else 0.17)
    if swag == "single":
        _single_swag(c, ox, top, ow, depth)
        _jabot(c, ox, top, -1, oh * 0.22, ow * 0.09)
        _jabot(c, ox + ow, top, +1, oh * 0.22, ow * 0.09)
    else:
        _one_swag_span(c, ox, ox + ow * 0.62, top, depth, tassel=False)
        _one_swag_span(c, ox + ow * 0.38, ox + ow, top, depth, tassel=False)
        _tassel(c, ox + ow * 0.50, top - depth * 0.25, max(14, depth * 0.55))
        _jabot(c, ox, top, -1, oh * 0.20, ow * 0.08)
        _jabot(c, ox + ow, top, +1, oh * 0.20, ow * 0.08)
    _track(c, ox, top, ow)
    _floor(c, ox, oy, ow)
    _frame_dims(c, ox, oy, ow, oh, width_label, height_label)
    return ox, oy, ow, oh


def draw_lincoln_window(c, box, width_label, height_label):
    x, y, bw, bh = box
    w_in, h_in = 73.0, 125.5
    pad_l, pad_r, pad_t, pad_b = 52, 18, 36, 26
    scale = min((bw - pad_l - pad_r) / w_in, (bh - pad_t - pad_b) / h_in)
    ow, oh = w_in * scale, h_in * scale
    ox = x + pad_l + ((bw - pad_l - pad_r) - ow) / 2
    oy = y + pad_b + ((bh - pad_t - pad_b) - oh) / 2
    _surround(c, ox, oy, ow, oh, "wall")
    _stack_pair(c, ox, oy, ow, oh, stack=0.30, sheer="glass")
    top = oy + oh
    _formal_valance(c, ox, top, ow, oh * 0.13)
    _rod(c, ox, top, ow)
    _floor(c, ox, oy, ow)
    _frame_dims(c, ox, oy, ow, oh, width_label, height_label)
    # style flag sits in the glass, small, so it cannot be read as a chosen swag
    c.setFillColor(INK)
    c.setFont("Sans", 6.5)
    c.drawCentredString(ox + ow / 2, oy + oh * 0.62, "VALANCE STYLE TBC")
    return ox, oy, ow, oh


def draw_passway(c, box, height_label):
    """Doorway. Width is diagrammatic — no width dimension is printed."""
    x, y, bw, bh = box
    # Proportion only. 58 is not a field measure and is never labeled.
    w_in, h_in = 58.0, 102.5
    pad_l, pad_r, pad_t, pad_b = 48, 14, 34, 28
    scale = min((bw - pad_l - pad_r) / w_in, (bh - pad_t - pad_b) / h_in)
    ow, oh = w_in * scale, h_in * scale
    ox = x + pad_l + ((bw - pad_l - pad_r) - ow) / 2
    oy = y + pad_b + ((bh - pad_t - pad_b) - oh) / 2
    _surround(c, ox, oy, ow, oh, "case")
    _stack_pair(c, ox, oy, ow, oh, stack=0.28, sheer="void")
    top = oy + oh
    _rod(c, ox, top, ow)
    pw = ow * 0.28
    _rings(c, ox, top, pw, 10)
    _rings(c, ox + ow - pw, top, pw, 10)
    _floor(c, ox, oy, ow)
    _frame_dims(c, ox, oy, ow, oh, None, height_label)
    c.setFillColor(CREAM)
    c.setFont("Sans", 8)
    c.drawCentredString(ox + ow / 2, oy + oh * 0.50, "NO VALANCE")
    c.setFont("Sans", 7.5)
    c.drawCentredString(ox + ow / 2, oy + oh * 0.50 - 12, "NO SHEERS")
    c.setFont("Sans", 7)
    c.drawCentredString(ox + ow / 2, oy + 16, "WIDTH NOT ON JUNE 9 SHEET")
    return ox, oy, ow, oh


def draw_office_opening(c, box):
    """Unpriced inside-office opening. Rectangle and the three field figures only."""
    x, y, bw, bh = box
    w_in, h_in = 68.25, 104.25
    pad_l, pad_r, pad_t, pad_b = 78, 24, 36, 36
    scale = min((bw - pad_l - pad_r) / w_in, (bh - pad_t - pad_b) / h_in)
    ow, oh = w_in * scale, h_in * scale
    ox = x + pad_l + ((bw - pad_l - pad_r) - ow) / 2
    oy = y + pad_b + ((bh - pad_t - pad_b) - oh) / 2
    c.setFillColor(WALL)
    c.setStrokeColor(INK)
    c.setLineWidth(1.0)
    c.rect(ox, oy, ow, oh, fill=1, stroke=1)
    # inner width marked VALANCE? — drawn as a second pair of extension ticks
    # 68 13/16 vs 68 1/4 is 9/16" and will not read at this scale.
    # Call it out in text beside the opening instead of a fake offset.
    _floor(c, ox, oy, ow)
    dim_y = oy + oh + 18
    extension(c, ox, oy + oh, ox, dim_y)
    extension(c, ox + ow, oy + oh, ox + ow, dim_y)
    dim_h(c, ox, ox + ow, dim_y, '68 1/4"  OUTER W')
    dim_x = ox - 18
    extension(c, ox, oy, dim_x, oy)
    extension(c, ox, oy + oh, dim_x, oy + oh)
    dim_v(c, dim_x, oy, oy + oh, '104 1/4"  H')
    c.setFillColor(INK)
    c.setFont("Sans", 8)
    c.drawCentredString(ox + ow / 2, oy + oh / 2 + 10, "INSIDE OFFICE")
    c.setFont("Sans", 7.5)
    c.drawCentredString(ox + ow / 2, oy + oh / 2 - 4, "NO TREATMENT DRAWN")
    c.drawCentredString(ox + ow / 2, oy + oh / 2 - 16, 'ALSO MARKED  68 13/16"')
    c.drawCentredString(ox + ow / 2, oy + oh / 2 - 28, "VALANCE?  —  NOT RESOLVED")
    return ox, oy, ow, oh
