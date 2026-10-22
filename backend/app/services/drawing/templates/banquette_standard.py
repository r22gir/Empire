"""Empire Workroom standard upholstery / banquette shop-drawing template.

11x17 landscape, fractions only, Empire branding. One PDF is the full job
set: a true-shape plan per bench, front elevations with channel divisions,
a side section, the wood/foam vs fabric schedule, and estimate notes.

Layout and sheet language follow the shop reference (U / L / straight
plans with joints, legend, quoted runs, separately labeled cuts). The
renderer reads BanquetteJob — it does not hardcode a client.
"""
from __future__ import annotations

from fractions import Fraction
from pathlib import Path
from typing import Iterable

from reportlab.lib import colors
from reportlab.lib.pagesizes import elevenSeventeen, landscape
from reportlab.pdfgen import canvas

from app.services.drawing.shop_date import shop_today
from app.services.drawing.templates.banquette_job import (
    BanquetteJob,
    BenchSpec,
    ChannelPiece,
    RunSpec,
    SeatBoard,
    estimate_yardage,
    inch_text,
    label_ink_for_fill,
    schedule_rows,
)

TAB = landscape(elevenSeventeen)  # 17" x 11"
PW, PH = TAB
BR = colors.HexColor("#3a2c1c")
RED = colors.HexColor("#b02020")
DIM = colors.HexColor("#1f4e8c")
SEATF = colors.HexColor("#3b2a20")
CHF = colors.HexColor("#c98b55")
ODDF = colors.HexColor("#e8b070")
SHELL = colors.HexColor("#555555")
CREAM = colors.HexColor("#f6efe4")
INK = colors.black


def _frac(value, denom=None) -> Fraction:
    if denom is not None:
        return Fraction(value, denom)
    return Fraction(value).limit_denominator(64)


def _scale_label(sc: float) -> str:
    real = 72.0 / float(sc)
    return inch_text(real)


class Plan:
    """Inch-space plan: +x right, +z down the sheet (wall at top)."""

    def __init__(self, c: canvas.Canvas, ox: float, oy: float, sc: float):
        self.c = c
        self.ox = ox
        self.oy = oy
        self.sc = sc

    def P(self, x, z) -> tuple[float, float]:
        return self.ox + float(x) * self.sc, self.oy - float(z) * self.sc

    def rect(self, x0, z0, x1, z1, fill=None, stroke=INK, lw=0.8, dash=None):
        X0, Y0 = self.P(x0, z0)
        X1, Y1 = self.P(x1, z1)
        self.c.setLineWidth(lw)
        self.c.setStrokeColor(stroke)
        if dash:
            self.c.setDash(*dash)
        if fill is not None:
            self.c.setFillColor(fill)
        self.c.rect(
            min(X0, X1), min(Y0, Y1), abs(X1 - X0), abs(Y1 - Y0),
            fill=1 if fill is not None else 0, stroke=1,
        )
        self.c.setDash()

    def text(self, x, z, t, size=6.5, rot=0, bold=False, col=INK):
        X, Y = self.P(x, z)
        self.c.saveState()
        self.c.translate(X, Y)
        self.c.rotate(rot)
        self.c.setFillColor(col)
        self.c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        self.c.drawCentredString(0, -size / 3, t)
        self.c.restoreState()

    def dimx(self, x0, x1, z, label, off=0, size=6.5):
        X0, Y = self.P(x0, z)
        X1, _ = self.P(x1, z)
        Y += off
        self.c.setStrokeColor(DIM)
        self.c.setLineWidth(0.5)
        self.c.line(X0, Y, X1, Y)
        self.c.line(X0, Y - 3, X0, Y + 3)
        self.c.line(X1, Y - 3, X1, Y + 3)
        self.c.setFillColor(DIM)
        self.c.setFont("Helvetica", size)
        self.c.drawCentredString((X0 + X1) / 2, Y + 2, label)

    def dimz(self, z0, z1, x, label, off=0, size=6.5):
        X, Y0 = self.P(x, z0)
        _, Y1 = self.P(x, z1)
        X += off
        self.c.setStrokeColor(DIM)
        self.c.setLineWidth(0.5)
        self.c.line(X, Y0, X, Y1)
        self.c.line(X - 3, Y0, X + 3, Y0)
        self.c.line(X - 3, Y1, X + 3, Y1)
        self.c.saveState()
        self.c.translate(X - 2, (Y0 + Y1) / 2)
        self.c.rotate(90)
        self.c.setFillColor(DIM)
        self.c.setFont("Helvetica", size)
        self.c.drawCentredString(0, 0, label)
        self.c.restoreState()


def _header(c: canvas.Canvas, job: BanquetteJob, title: str, page: int, total: int) -> None:
    today = job.drawn_date or shop_today()
    c.setFillColor(BR)
    c.setFont("Helvetica-Bold", 16)
    c.drawString(36, PH - 40, job.branding)
    c.setFont("Helvetica", 10)
    client_line = f"{job.client_name} · {job.subtitle} · {title}" if job.subtitle else f"{job.client_name} · {title}"
    c.drawString(36, PH - 55, client_line)
    c.setFillColor(RED)
    c.setFont("Helvetica-Bold", 18)
    c.drawRightString(PW - 36, PH - 42, job.draft_banner)
    c.setFont("Helvetica", 8)
    c.drawRightString(PW - 36, PH - 55, "internal only · not for client · not for production until Rafael OKs")
    c.setFillColor(INK)
    c.setFont("Helvetica", 7)
    c.drawString(
        36, 20,
        'All dimensions in inches, fractions to 1/16". Wood = true size. Foam = wood. '
        "Fabric = wood + 2 x allowance (separate column).",
    )
    rev = f"REV {today}"
    if job.revision:
        rev += f" · {job.revision}"
    c.drawRightString(PW - 36, 20, f"{rev} · Page {page} of {total}")
    c.setStrokeColor(BR)
    c.line(36, PH - 62, PW - 36, PH - 62)


def _legend(c: canvas.Canvas, job: BanquetteJob, x: float, y: float, bench: BenchSpec | None = None) -> None:
    seat = job.seat_fabric
    back = job.back_fabric
    seat_note = f"Seat — {seat.sheet_label}"
    if seat.notes:
        seat_note += f", {seat.notes}"
    items = [
        (colors.HexColor(seat.fill_hex), seat_note),
        (colors.HexColor(back.plan_hex), f"Channel back {inch_text(job.benches[0].channel_width_in)} — {back.sheet_label}"),
        (ODDF, f"ODD channel — {back.sheet_label}"),
        (None, "Base footprint (existing millwork, dashed)"),
        (SHELL, "Outside back shell / wall (existing)"),
    ]
    c.setFont("Helvetica", 7.5)
    for i, (col, text) in enumerate(items):
        yy = y - i * 12
        if col is None:
            c.setDash(3, 2)
            c.setStrokeColor(INK)
            c.rect(x, yy, 14, 8, fill=0)
            c.setDash()
        else:
            c.setFillColor(col)
            c.setStrokeColor(INK)
            c.rect(x, yy, 14, 8, fill=1)
        c.setFillColor(INK)
        c.drawString(x + 20, yy + 1, text)
    yy = y - len(items) * 12 - 6
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(x, yy, "Quoted runs")
    yy -= 11
    c.setFont("Helvetica", 7)
    shown = [bench] if bench is not None else job.benches
    for item in shown:
        for run in item.runs:
            c.drawString(x, yy, f"{run.name}: {inch_text(run.back_run_in)}")
            yy -= 10


def _scalebar(c: canvas.Canvas, p: Plan, x: float, y: float) -> None:
    length = 48
    w = length * p.sc
    c.setStrokeColor(INK)
    c.setLineWidth(0.6)
    for i in range(4):
        c.setFillColor(INK if i % 2 == 0 else colors.white)
        c.rect(x + i * w / 4, y, w / 4, 4, fill=1)
    c.setFillColor(INK)
    c.setFont("Helvetica", 7)
    for i, t in enumerate(['0', '12"', '24"', '36"', '48"']):
        c.drawCentredString(x + i * w / 4, y - 9, t)
    c.drawString(x + w + 8, y, "SCALE BAR (inches, true scale)")


def _draw_channels(
    p: Plan,
    channels: Iterable[ChannelPiece],
    axis: str,
    start,
    band0,
    band1,
    lab_side,
    fill_std,
    fill_odd,
) -> None:
    pos = _frac(start)
    for ch in channels:
        w = _frac(ch.width_in)
        fill = fill_odd if ch.is_odd else fill_std
        if axis == "x":
            p.rect(pos, band0, pos + w, band1, fill=fill, lw=0.5)
            mid = pos + w / 2
            p.text(mid, ( _frac(band0) + _frac(band1) ) / 2, ch.label, size=4.6)
            p.text(
                mid, lab_side, ch.width_text, size=5.2,
                col=colors.HexColor("#7a3b0c") if ch.is_odd else INK,
                bold=ch.is_odd,
            )
        else:
            p.rect(band0, pos, band1, pos + w, fill=fill, lw=0.5)
            mid = pos + w / 2
            p.text((_frac(band0) + _frac(band1)) / 2, mid, ch.label, size=4.6, rot=90)
            p.text(
                lab_side, mid, ch.width_text, size=5.2, rot=90,
                col=colors.HexColor("#7a3b0c") if ch.is_odd else INK,
                bold=ch.is_odd,
            )
        pos += w


def _seat_fill(job: BanquetteJob):
    return colors.HexColor(job.seat_fabric.fill_hex)


def _seat_label_color(job: BanquetteJob):
    return colors.HexColor(label_ink_for_fill(job.seat_fabric.fill_hex))


def _ch_fill(job: BanquetteJob):
    return colors.HexColor(job.back_fabric.plan_hex)


def _draw_u_plan(c: canvas.Canvas, job: BanquetteJob, bench: BenchSpec) -> Plan:
    main = bench.run_by_role("main")
    left = bench.run_by_role("left")
    right = bench.run_by_role("right")
    assert main and left and right
    d = _frac(bench.seat_depth_in)
    bk = _frac(bench.back_stack_in)
    ov = _frac(bench.front_overhang_in)
    m = _frac(main.back_run_in)
    eul = bk + _frac(left.back_run_in)
    eur = bk + _frac(right.back_run_in)
    sc = (PW - 110) / float(m + 6)
    p = Plan(c, 60, PH - 185, sc)
    scale = _scale_label(sc)
    c.setFont("Helvetica", 8)
    c.drawString(
        36, PH - 76,
        f"Scale approx. 1:{scale[:-1]}  (1\" on paper = {scale} real when printed full size on 11x17). "
        f"Wall / back side at top. Seat depth {inch_text(d)} (seat runs under the backs) — PRIMARY.",
    )
    # shell
    p.rect(-_frac("3/4"), -_frac("3/4"), m + _frac("3/4"), 0, fill=SHELL, lw=0.3)
    p.rect(-_frac("3/4"), 0, 0, eul, fill=SHELL, lw=0.3)
    p.rect(m, 0, m + _frac("3/4"), eur, fill=SHELL, lw=0.3)
    # main seats along x
    main_seats = [s for s in bench.seats if s.run_id == main.run_id]
    x0 = _frac(0)
    for seat in main_seats:
        L = _frac(seat.length_in)
        p.rect(x0, 0, x0 + L, d, fill=_seat_fill(job))
        ink = _seat_label_color(job)
        p.text(x0 + L / 2, d * _frac(2, 3), seat.label, size=9, bold=True, col=ink)
        p.text(x0 + L / 2, d * _frac(2, 3) + 3.2, seat.size_text, size=7, col=ink)
        x0 += L
    # return seats
    left_seat = next(s for s in bench.seats if s.run_id == left.run_id)
    right_seat = next(s for s in bench.seats if s.run_id == right.run_id)
    ink = _seat_label_color(job)
    p.rect(0, d, d, eul, fill=_seat_fill(job))
    p.text(d / 2 + 2, (d + eul) / 2 - 3, left_seat.label, size=9, bold=True, col=ink)
    p.text(d / 2 + 2, (d + eul) / 2 + 1.5, f"{inch_text(d)} x", size=6.5, col=ink)
    p.text(d / 2 + 2, (d + eul) / 2 + 4.5, inch_text(left_seat.length_in), size=6.5, col=ink)
    p.rect(m - d, d, m, eur, fill=_seat_fill(job))
    p.text(m - d / 2 - 2, (d + eur) / 2 - 3, right_seat.label, size=9, bold=True, col=ink)
    p.text(m - d / 2 - 2, (d + eur) / 2 + 1.5, f"{inch_text(d)} x", size=6.5, col=ink)
    p.text(m - d / 2 - 2, (d + eur) / 2 + 4.5, inch_text(right_seat.length_in), size=6.5, col=ink)
    # base footprint
    p.rect(0, 0, m, d - ov, dash=(3, 2), lw=0.7)
    p.rect(0, d - ov, d - ov, eul, dash=(3, 2), lw=0.7)
    p.rect(m - d + ov, d - ov, m, eur, dash=(3, 2), lw=0.7)
    band = min(bk, _frac(5, 2))
    _draw_channels(p, main.channels, "x", 0, 0, band, band + _frac("7/5"), _ch_fill(job), ODDF)
    _draw_channels(p, left.channels, "z", bk, 0, band, band + _frac("7/5"), _ch_fill(job), ODDF)
    _draw_channels(p, right.channels, "z", bk, m - band, m, m - band - _frac("7/5"), _ch_fill(job), ODDF)
    # dims
    p.dimx(0, m, -_frac("3/4"), f"U main back run / seats {inch_text(m)} (inside of shell, corner to corner)", off=26, size=7.5)
    odd = next((ch for ch in main.channels if ch.is_odd), None)
    std = [ch for ch in main.channels if not ch.is_odd]
    if odd and odd == main.channels[0]:
        p.dimx(0, _frac(odd.width_in), -_frac("3/4"), f"{odd.width_text} ODD", off=12, size=6)
        p.dimx(_frac(odd.width_in), m, -_frac("3/4"), f"{len(std)} @ {inch_text(bench.channel_width_in)} = {inch_text(sum(ch.width_in for ch in std))}", off=12, size=6)
    x0 = _frac(0)
    for seat in main_seats:
        L = _frac(seat.length_in)
        p.dimx(x0, x0 + L, eur, inch_text(L), off=-34, size=7)
        x0 += L
    p.dimz(0, d, -_frac("3/4"), f"seat {inch_text(d)}", off=-14)
    p.dimz(d, eul, -_frac("3/4"), f"{left_seat.label} {inch_text(left_seat.length_in)}", off=-14)
    p.dimz(0, eul, -_frac("3/4"), f"U left arm {inch_text(eul)} (open end)", off=-30)
    p.dimz(0, bk, m + _frac("3/4"), f"{inch_text(bk)} back", off=12, size=5.5)
    p.dimz(bk, eur, m + _frac("3/4"), f"back run {inch_text(right.back_run_in)}", off=12)
    p.dimz(0, eur, m + _frac("3/4"), f"U right arm {inch_text(eur)} (open end)", off=28)
    p.text(m * _frac(4, 5), d + 2, f"{inch_text(ov)} front overhang (front only)", size=6, col=DIM)
    p.dimx(0, d - ov, eul, f"base {inch_text(d - ov)}", off=-14, size=6)
    p.dimx(0, d, eul, f"seat {inch_text(d)}", off=-24, size=6)
    p.dimx(m - d, m, eur, f"seat {inch_text(d)}", off=-14, size=6)
    p.text(d / 2, eul + 12, "OPEN END — seat, back, base flush", size=6.5, col=RED)
    p.text(m - d / 2 - 8, eur + 12, "OPEN END — seat, back, base flush", size=6.5, col=RED)
    return p


def _draw_l_plan(c: canvas.Canvas, job: BanquetteJob, bench: BenchSpec) -> Plan:
    long = bench.run_by_role("long")
    short = bench.run_by_role("short")
    assert long and short
    d = _frac(bench.seat_depth_in)
    bk = _frac(bench.back_stack_in)
    ov = _frac(bench.front_overhang_in)
    lx = _frac(long.back_run_in)
    els = bk + _frac(short.back_run_in)
    sc = min((PW - 460) / float(lx + 8), (PH - 230) / float(els + 8))
    p = Plan(c, 100, PH - 150, sc)
    scale = _scale_label(sc)
    c.setFont("Helvetica", 8)
    c.drawString(
        36, PH - 76,
        f"Scale approx. 1:{scale[:-1]} (1\" on paper = {scale} real on 11x17). "
        f"Long-leg wall at top, short-leg wall at left. Seat depth {inch_text(d)} — PRIMARY.",
    )
    p.rect(0, -_frac("3/4"), lx, 0, fill=SHELL, lw=0.3)
    p.rect(-_frac("3/4"), -_frac("3/4"), 0, els, fill=SHELL, lw=0.3)
    long_seats = [s for s in bench.seats if s.run_id == long.run_id]
    x0 = _frac(0)
    for seat in long_seats:
        L = _frac(seat.length_in)
        ink = _seat_label_color(job)
        p.rect(x0, 0, x0 + L, d, fill=_seat_fill(job))
        p.text(x0 + L / 2, d * _frac(2, 3), seat.label, size=10, bold=True, col=ink)
        p.text(x0 + L / 2, d * _frac(2, 3) + 3, seat.size_text, size=8, col=ink)
        x0 += L
    short_seat = next(s for s in bench.seats if s.run_id == short.run_id)
    p.rect(0, d, d, els, fill=_seat_fill(job))
    p.text(d / 2 + 1, (d + els) / 2 - 2, short_seat.label, size=10, bold=True, col=ink)
    p.text(d / 2 + 1, (d + els) / 2 + 2, short_seat.size_text, size=7.5, col=ink)
    p.rect(0, 0, lx, d - ov, dash=(3, 2), lw=0.7)
    p.rect(0, d - ov, d - ov, els, dash=(3, 2), lw=0.7)
    band = min(bk, _frac(5, 2))
    _draw_channels(p, long.channels, "x", 0, 0, band, band + _frac("8/5"), _ch_fill(job), ODDF)
    _draw_channels(p, short.channels, "z", bk, 0, band, band + _frac("8/5"), _ch_fill(job), ODDF)
    p.dimx(0, lx, -_frac("3/4"), f"L long leg back run / seats {inch_text(lx)}", off=26, size=8)
    odd = next((ch for ch in long.channels if ch.is_odd), None)
    std = [ch for ch in long.channels if not ch.is_odd]
    if odd and long.channels[-1].is_odd:
        p.dimx(0, lx - _frac(odd.width_in), -_frac("3/4"), f"{len(std)} @ {inch_text(bench.channel_width_in)} = {inch_text(sum(ch.width_in for ch in std))}", off=12, size=6.5)
        p.dimx(lx - _frac(odd.width_in), lx, -_frac("3/4"), f"{odd.width_text} ODD", off=12, size=6.5)
    x0 = _frac(0)
    for seat in long_seats:
        L = _frac(seat.length_in)
        p.dimx(x0, x0 + L, d, inch_text(L), off=-18, size=7.5)
        x0 += L
    p.dimz(0, d, lx, f"seat {inch_text(d)}", off=14)
    p.dimz(0, d - ov, lx, f"base {inch_text(d - ov)}", off=30)
    p.dimz(0, els, -_frac("3/4"), f"L short leg {inch_text(els)} (open end)", off=-30)
    p.dimz(0, bk, -_frac("3/4"), inch_text(bk), off=-14, size=5.5)
    p.dimz(bk, els, -_frac("3/4"), f"back run {inch_text(short.back_run_in)}", off=-14, size=6.5)
    p.dimz(d, els, d, f"{short_seat.label} {inch_text(short_seat.length_in)}", off=14, size=7)
    p.dimx(0, d, els, f"seat {inch_text(d)}", off=-16, size=6.5)
    p.dimx(0, d - ov, els, f"base {inch_text(d - ov)}", off=-27, size=6.5)
    p.text(lx - 8, d + 7, "OPEN END — flush", size=6.5, col=RED)
    p.text(d / 2 + 28, els + 3, "OPEN END — seat, back, base flush", size=6.5, col=RED)
    return p


def _draw_straight_plan(c: canvas.Canvas, job: BanquetteJob, bench: BenchSpec) -> Plan:
    main = bench.run_by_role("main") or bench.runs[0]
    d = _frac(bench.seat_depth_in)
    bk = _frac(bench.back_stack_in)
    ov = _frac(bench.front_overhang_in)
    w = _frac(main.back_run_in)
    sc = min((PW - 160) / float(w + 8), (PH - 280) / float(d + 16))
    p = Plan(c, 80, PH - 160, sc)
    scale = _scale_label(sc)
    c.setFont("Helvetica", 8)
    c.drawString(
        36, PH - 76,
        f"Scale approx. 1:{scale[:-1]} (1\" on paper = {scale} real on 11x17). "
        f"Wall / back at top. Seat depth {inch_text(d)} — PRIMARY.",
    )
    p.rect(-_frac("3/4"), -_frac("3/4"), w + _frac("3/4"), 0, fill=SHELL, lw=0.3)
    x0 = _frac(0)
    for seat in bench.seats:
        L = _frac(seat.length_in)
        ink = _seat_label_color(job)
        p.rect(x0, 0, x0 + L, d, fill=_seat_fill(job))
        p.text(x0 + L / 2, d * _frac(2, 3), seat.label, size=10, bold=True, col=ink)
        p.text(x0 + L / 2, d * _frac(2, 3) + 3, seat.size_text, size=8, col=ink)
        x0 += L
    p.rect(0, 0, w, d - ov, dash=(3, 2), lw=0.7)
    band = min(bk, _frac(5, 2))
    _draw_channels(p, main.channels, "x", 0, 0, band, band + _frac("8/5"), _ch_fill(job), ODDF)
    p.dimx(0, w, -_frac("3/4"), f"back run / seats {inch_text(w)}", off=26, size=8)
    p.dimz(0, d, w, f"seat {inch_text(d)}", off=14)
    p.dimz(0, d - ov, w, f"base {inch_text(d - ov)}", off=30)
    p.text(w / 2, d + 8, "OPEN ENDS — seat, back, base flush", size=6.5, col=RED)
    return p


def _notes_block(c: canvas.Canvas, lines: list[str], x: float, y: float, size: float = 7.5, leading: float = 11) -> None:
    c.setFont("Helvetica", size)
    c.setFillColor(INK)
    for i, text in enumerate(lines):
        c.drawString(x, y - i * leading, text[:140])


def _draw_plan_page(c: canvas.Canvas, job: BanquetteJob, bench: BenchSpec, page: int, total: int) -> None:
    title = {
        "u_shape": "TOP VIEW PLAN — U booth (to scale)",
        "l_shape": "TOP VIEW PLAN — L booth (to scale)",
        "straight": "TOP VIEW PLAN — straight bench (to scale)",
    }.get(bench.shape, "TOP VIEW PLAN (to scale)")
    _header(c, job, title, page, total)
    if bench.shape == "u_shape":
        p = _draw_u_plan(c, job, bench)
        _legend(c, job, PW - 330, 170, bench)
        _notes_block(c, bench.notes, 40, 170)
        _scalebar(c, p, 40, 40)
    elif bench.shape == "l_shape":
        p = _draw_l_plan(c, job, bench)
        _legend(c, job, PW - 330, PH - 110, bench)
        _notes_block(c, bench.notes, PW - 330, PH - 240, size=8, leading=12)
        _scalebar(c, p, PW - 430, 60)
    else:
        p = _draw_straight_plan(c, job, bench)
        _legend(c, job, PW - 330, PH - 110, bench)
        _notes_block(c, bench.notes, 40, 160)
        _scalebar(c, p, 40, 40)
    c.showPage()


def _elevation_run(
    c: canvas.Canvas,
    job: BanquetteJob,
    bench: BenchSpec,
    run: RunSpec,
    x: float,
    y: float,
    scale: float,
    name: str,
) -> None:
    s = scale
    w = run.back_run_in * s
    back_h = bench.channel_height_in * s
    seat_h = 4.0 * s
    c.setFillColor(colors.HexColor(job.seat_fabric.fill_hex))
    c.setStrokeColor(INK)
    c.setLineWidth(0.6)
    c.rect(x, y, w, seat_h, stroke=1, fill=1)
    pos = x
    for ch in run.channels:
        cw = ch.width_in * s
        c.setFillColor(ODDF if ch.is_odd else colors.HexColor(job.back_fabric.plan_hex))
        c.rect(pos, y + seat_h, cw, back_h, stroke=1, fill=1)
        if cw > 8:
            c.setFillColor(INK)
            c.setFont("Helvetica", 4.5)
            c.drawCentredString(pos + cw / 2, y + seat_h + back_h / 2, ch.label)
        pos += cw
    c.setStrokeColor(DIM)
    c.setLineWidth(0.5)
    c.line(x, y + seat_h + back_h + 8, x + w, y + seat_h + back_h + 8)
    c.line(x, y + seat_h + back_h + 5, x, y + seat_h + back_h + 11)
    c.line(x + w, y + seat_h + back_h + 5, x + w, y + seat_h + back_h + 11)
    c.setFillColor(DIM)
    c.setFont("Helvetica", 7)
    c.drawCentredString(x + w / 2, y + seat_h + back_h + 10, f"{name}  {inch_text(run.back_run_in)}")
    c.setFillColor(INK)
    c.setFont("Helvetica", 6.5)
    n_std = len(run.standard_channels)
    odd = run.odd_channels
    extra = f" + {odd[0].width_text} ODD at {run.odd_at}" if odd else ""
    c.drawString(x, y - 10, f"{n_std} x {inch_text(bench.channel_width_in)} channels{extra}")
    c.drawString(x, y - 19, f"seat cushion: {job.seat_fabric.sheet_label}   back: {job.back_fabric.sheet_label}")


def _side_section(c: canvas.Canvas, job: BanquetteJob, bench: BenchSpec, x: float, y: float, scale: float) -> None:
    s = scale
    d = bench.seat_depth_in * s
    bk = bench.back_stack_in * s
    ov = bench.front_overhang_in * s
    bh = bench.channel_height_in * s
    sh = (bench.seat_height_in or 18.0) * s
    seat_t = 4.0 * s
    # wall
    c.setFillColor(SHELL)
    c.rect(x - 8, y, 8, sh + bh + 10, fill=1, stroke=0)
    # base
    c.setStrokeColor(INK)
    c.setDash(3, 2)
    c.rect(x, y, d - ov, sh - seat_t, fill=0, stroke=1)
    c.setDash()
    # seat
    c.setFillColor(colors.HexColor(job.seat_fabric.fill_hex))
    c.rect(x, y + sh - seat_t, d, seat_t, fill=1, stroke=1)
    # back
    c.setFillColor(colors.HexColor(job.back_fabric.plan_hex))
    c.rect(x, y + sh, bk, bh, fill=1, stroke=1)
    c.setStrokeColor(DIM)
    c.setFont("Helvetica", 6.5)
    c.setFillColor(DIM)
    c.drawString(x, y - 12, f"SIDE SECTION  seat {inch_text(bench.seat_depth_in)}  back {inch_text(bench.back_stack_in)}  height {inch_text(bench.channel_height_in)}")
    c.drawString(x, y - 22, f"front overhang {inch_text(bench.front_overhang_in)}  foam {inch_text(bench.foam_thickness_in) if bench.foam_thickness_in else 'TBC'}")
    c.setFillColor(INK)
    c.setFont("Helvetica-Bold", 7)
    c.drawString(x, y + sh + bh + 6, "SIDE SECTION")


def _draw_elevations_page(c: canvas.Canvas, job: BanquetteJob, page: int, total: int) -> None:
    _header(c, job, "FRONT ELEVATIONS · SIDE SECTION", page, total)
    c.setFont("Helvetica", 8)
    c.drawString(
        36, PH - 76,
        f"Channel divisions are Option A (full {inch_text(job.benches[0].channel_width_in)} + odd remainder). "
        f"Seat and back are separate parts / fabrics.",
    )
    y = PH - 220
    x = 50
    for bench in job.benches:
        runs = list(bench.runs)
        max_run = max(r.back_run_in for r in runs)
        scale = min(1.8, 640.0 / max_run)
        elev_h = bench.channel_height_in * scale + 4.0 * scale
        c.setFont("Helvetica-Bold", 10)
        c.setFillColor(INK)
        c.drawString(x, y + elev_h + 28, bench.name.upper())
        long_runs = [r for r in runs if r.back_run_in * scale > 280]
        short_runs = [r for r in runs if r not in long_runs]
        for run in long_runs:
            _elevation_run(c, job, bench, run, x, y, scale, run.name.upper())
            y -= elev_h + 48
        cursor = x
        row_y = y
        for run in short_runs:
            w = run.back_run_in * scale
            if cursor > x and cursor + w > PW - 240:
                y -= elev_h + 48
                cursor = x
                row_y = y
            _elevation_run(c, job, bench, run, cursor, row_y, scale, run.name.upper())
            cursor += w + 28
        _side_section(c, job, bench, PW - 200, row_y, min(2.8, 130.0 / max(bench.seat_depth_in, 1)))
        y = row_y - elev_h - 70
    c.showPage()


def _draw_schedule_page(c: canvas.Canvas, job: BanquetteJob, page: int, total: int) -> None:
    _header(c, job, "PART SCHEDULE — wood / foam cut vs fabric cut (separately labeled)", page, total)
    rows = schedule_rows(job)
    extra = job.allowance_in
    extra_txt = inch_text(extra) if extra is not None else "TBC"
    foam_txt = inch_text(job.foam_thickness_in) if job.foam_thickness_in else "TBC"
    cols = [
        ("Part", 92),
        ("Run", 90),
        ("Qty", 28),
        ("Fabric (code / color)", 150),
        ('WOOD cut W x L (true size)', 150),
        (f'FOAM cut (= wood) x {foam_txt}', 165),
        (f"FABRIC cut W x L (wood + 2 x {extra_txt})", 200),
        ("Notes", PW - 72 - 875),
    ]
    y = PH - 90
    x = 36
    c.setFillColor(BR)
    c.rect(36, y - 4, PW - 72, 15, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 8)
    for title, wd in cols:
        c.drawString(x + 2, y, title)
        x += wd
    y -= 16
    c.setFont("Helvetica", 8)
    for i, row in enumerate(rows):
        if y < 70:
            c.showPage()
            _header(c, job, "PART SCHEDULE (continued)", page, total)
            y = PH - 90
        if i % 2 == 0:
            c.setFillColor(CREAM)
            c.rect(36, y - 4, PW - 72, 13, fill=1, stroke=0)
        c.setFillColor(INK)
        x = 36
        vals = [
            row.label, row.run_name, row.qty, row.fabric_label,
            row.wood_size, row.foam_size,
            row.fabric_size + ("  (confirm)" if job.allowance_status != "confirmed" else ""),
            row.notes,
        ]
        for (title, wd), val in zip(cols, vals):
            c.drawString(x + 2, y, str(val)[: max(8, int(wd / 6))])
            x += wd
        y -= 13
    n_seat = sum(r.qty for r in rows if r.part.startswith("Seat"))
    n_ch = sum(r.qty for r in rows if "channel" in r.part.lower())
    y -= 8
    c.setFont("Helvetica-Bold", 8.5)
    c.setFillColor(INK)
    c.drawString(
        36, y,
        f"Totals: {n_seat} seats ({job.seat_fabric.sheet_label}) + {n_ch} channels "
        f"({job.back_fabric.sheet_label}) = {n_seat + n_ch} parts.  "
        f"Seats: W = depth, L = length along run.  Channels: W = channel width, L = height "
        f"{inch_text(job.benches[0].channel_height_in)}.",
    )
    y -= 13
    c.setFont("Helvetica", 8)
    for line in (
        f"Wood = true size. Foam = wood (true size), {foam_txt} thick. Fabric = wood + 2 x allowance; "
        f"{job.allowance_label}",
        "WOOD CUT — TRUE SIZE.  FOAM CUT — MATCHES WOOD.  FABRIC CUT — LABELED SEPARATELY.",
        "Bases / toe kicks / outside shells / end panels = existing millwork, not cut.",
    ):
        c.drawString(36, y, line[:150])
        y -= 11
    c.showPage()


def _box(c: canvas.Canvas, x, y, w, h, title, lines, col=BR, size=8.5, lead=12) -> None:
    c.setStrokeColor(col)
    c.setLineWidth(1.2)
    c.rect(x, y - h, w, h)
    c.setFillColor(col)
    c.rect(x, y - 16, w, 16, fill=1, stroke=0)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 9.5)
    c.drawString(x + 6, y - 12, title)
    yy = y - 30
    for text in lines:
        bold = text.startswith("*")
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold" if bold else "Helvetica", size)
        c.drawString(x + 8, yy, text.lstrip("*")[: max(20, int((w - 16) / 5))])
        yy -= lead


def _draw_summary_page(c: canvas.Canvas, job: BanquetteJob, page: int, total: int) -> None:
    _header(c, job, "FABRIC SUMMARY · OPEN ITEMS · CONFLICTS WITH ESTIMATE", page, total)
    yards = estimate_yardage(job)
    fab_lines = [f"*{job.back_fabric.sheet_label} — channel backs", ""]
    for line in yards:
        if line.fabric_label == job.back_fabric.sheet_label:
            fab_lines = [
                f"*{line.fabric_label} — channel backs ({line.qty} pcs)",
                f"   {line.qty} pcs @ {line.typical_cut} fabric cut, {line.notes}",
                f"   Net ≈ {line.net_text}   ->   ORDER {line.order_text}",
                "",
            ]
    for line in yards:
        if line.fabric_label == job.seat_fabric.sheet_label:
            fab_lines += [
                f"*{line.fabric_label} — seat cushions ({line.qty} pcs)",
                f"   {line.qty} pcs @ {line.typical_cut} fabric cut, {line.notes}",
                f"   Net ≈ {line.net_text}   ->   ORDER {line.order_text}",
                "",
            ]
    fab_lines.append("Codes and colors only. Never brand / supplier names.")
    _box(c, 36, PH - 80, 560, 200, f'FABRIC SUMMARY ({inch_text(job.roll_width_in)} roll, separate seat / back fabrics)', fab_lines)
    c.setFillColor(colors.HexColor(job.back_fabric.plan_hex))
    c.rect(550, PH - 140, 30, 20, fill=1)
    c.setFillColor(colors.HexColor(job.seat_fabric.hex))
    c.rect(550, PH - 212, 30, 20, fill=1)
    open_lines = []
    for i, item in enumerate(job.open_items, 1):
        open_lines.append(f"{i}. {item}")
    if not open_lines:
        open_lines = ["None recorded."]
    _box(c, 616, PH - 80, PW - 652, 200, "OPEN ITEMS — confirm before cutting", open_lines, col=RED, size=8.3)
    conflict_lines = ["*Estimate / prior-doc mismatches (prices not changed):", ""]
    if job.conflicts:
        for item in job.conflicts:
            conflict_lines.append(f"  {item}")
    else:
        conflict_lines.append("  None — drawing matches the estimate dims that were supplied.")
    if not any("internal only" in (item or "").lower() for item in job.conflicts):
        conflict_lines += ["", "No estimate or client document was changed. This sheet is internal only."]
    _box(
        c, 36, PH - 300, PW - 72, 330,
        f"CONFLICTS — {job.quote_number} vs this revision",
        conflict_lines, col=colors.HexColor("#1f4e8c"), size=8.5, lead=13,
    )
    c.showPage()


def pages_for_job(job: BanquetteJob) -> int:
    return len(job.benches) + 3  # plans + elevations + schedule + summary


def render_banquette_job_pdf(job: BanquetteJob, output_path: str | Path) -> Path:
    """Write the full job set to a new 11x17 PDF. Never overwrites in place."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    if not job.drawn_date:
        job.drawn_date = shop_today()
    c = canvas.Canvas(str(path), pagesize=TAB)
    try:
        c._doc.compression = 0
    except Exception:
        pass
    c.setTitle(f"{job.branding} {job.client_name} {job.subtitle} REV {job.revision} {job.drawn_date}")
    c.setAuthor(job.branding)
    total = pages_for_job(job)
    page = 1
    for bench in job.benches:
        _draw_plan_page(c, job, bench, page, total)
        page += 1
    _draw_elevations_page(c, job, page, total)
    page += 1
    _draw_schedule_page(c, job, page, total)
    page += 1
    _draw_summary_page(c, job, page, total)
    c.save()
    return path
