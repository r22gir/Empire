"""
Realistic 3D bench renderer — isometric perspective SVGs with proper
upholstery details: rounded cushions, channel tufting, welting, legs,
shadow, and professional dimension callouts.

Used by sketch_to_drawing tool and architectural drawing generation.
"""
import math
import os
from pathlib import Path

# ── CONSTANTS ──────────────────────────────────────────────────────
SEAT_H = 18       # seat platform height (inches)
BACK_H = 18       # back height above seat
SEAT_D = 20       # seat depth
FOAM_T = 4        # foam thickness
PLAT_H = SEAT_H - FOAM_T  # platform/base height (under cushion)
TOTAL_H = SEAT_H + BACK_H

# Isometric math
ISO_A = 30
COS_A = math.cos(math.radians(ISO_A))
SIN_A = math.sin(math.radians(ISO_A))

# Colors
C_FABRIC_TOP = "#c9a96e"       # seat cushion top (warm upholstery)
C_FABRIC_FRONT = "#b8944f"     # seat cushion front face
C_FABRIC_SIDE = "#a6833e"      # seat cushion side
C_BACK_FRONT = "#d4b87a"       # back front face
C_BACK_SIDE = "#b8944f"        # back side
C_BACK_TOP = "#c9a96e"         # back top
C_BASE_FRONT = "#3d3225"       # base/platform front (dark wood)
C_BASE_SIDE = "#2e2518"        # base side
C_BASE_TOP = "#4a3d2e"         # base top
C_LEG = "#2e2518"              # leg color
C_WELT = "#8b7340"             # welting line
C_SHADOW = "#00000015"         # floor shadow
C_DIM = "#b8960c"              # dimension callout (gold)
C_DIM_TEXT = "#8b7000"
C_CHANNEL = "#a6833e"          # channel groove lines
FONT = "Arial, Helvetica, sans-serif"


def _iso(x, y, z, ox, oy, s):
    """3D → isometric 2D."""
    return (
        ox + (x * COS_A - y * COS_A) * s,
        oy - (x * SIN_A + y * SIN_A) * s - z * s,
    )


def _poly(pts, fill, stroke="#1a1a1a", sw=1.2, opacity=1.0, rx=0):
    """SVG polygon."""
    points = " ".join(f"{p[0]:.1f},{p[1]:.1f}" for p in pts)
    op = f' fill-opacity="{opacity}"' if opacity < 1 else ""
    return f'<polygon points="{points}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"{op}/>'


def _line(x1, y1, x2, y2, stroke, sw=1, dash=""):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{stroke}" stroke-width="{sw}"{d}/>'


def _text(x, y, txt, size=11, fill="#1a1a1a", anchor="middle", weight="normal", rotate=0):
    rot = f' transform="rotate({rotate},{x:.1f},{y:.1f})"' if rotate else ""
    return (
        f'<text x="{x:.1f}" y="{y:.1f}" text-anchor="{anchor}" '
        f'font-family="{FONT}" font-size="{size}" fill="{fill}" '
        f'font-weight="{weight}"{rot}>{txt}</text>'
    )


def _rounded_face(pts, fill, stroke="#1a1a1a", sw=1.2, r=4):
    """SVG path for a face with rounded corners."""
    if len(pts) < 3:
        return _poly(pts, fill, stroke, sw)
    # Build a path with rounded corners using quadratic curves
    d = []
    n = len(pts)
    for i in range(n):
        p0 = pts[(i - 1) % n]
        p1 = pts[i]
        p2 = pts[(i + 1) % n]
        # Vector from p1 to neighbors
        dx0, dy0 = p0[0] - p1[0], p0[1] - p1[1]
        dx2, dy2 = p2[0] - p1[0], p2[1] - p1[1]
        l0 = math.hypot(dx0, dy0) or 1
        l2 = math.hypot(dx2, dy2) or 1
        # Limit radius to half the shortest edge
        rr = min(r, l0 * 0.4, l2 * 0.4)
        # Points on edges at distance rr from corner
        s0x = p1[0] + dx0 / l0 * rr
        s0y = p1[1] + dy0 / l0 * rr
        s2x = p1[0] + dx2 / l2 * rr
        s2y = p1[1] + dy2 / l2 * rr
        if i == 0:
            d.append(f"M{s0x:.1f},{s0y:.1f}")
        else:
            d.append(f"L{s0x:.1f},{s0y:.1f}")
        d.append(f"Q{p1[0]:.1f},{p1[1]:.1f} {s2x:.1f},{s2y:.1f}")
    d.append("Z")
    return f'<path d="{" ".join(d)}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}" stroke-linejoin="round"/>'


def _dim_h(parts, p1, p2, label, offset=-16):
    """Horizontal dimension line with dots and label."""
    mx, my = (p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2 + offset
    parts.append(_line(p1[0], p1[1], p2[0], p2[1], C_DIM, 0.8, "5,3"))
    parts.append(f'<circle cx="{p1[0]:.1f}" cy="{p1[1]:.1f}" r="2.5" fill="{C_DIM}"/>')
    parts.append(f'<circle cx="{p2[0]:.1f}" cy="{p2[1]:.1f}" r="2.5" fill="{C_DIM}"/>')
    angle = math.degrees(math.atan2(p2[1] - p1[1], p2[0] - p1[0]))
    parts.append(_text(mx, my, label, 11, C_DIM_TEXT, weight="600", rotate=angle))


def _dim_v(parts, p_bot, p_top, label, offset=16):
    """Vertical dimension line."""
    mx = (p_bot[0] + p_top[0]) / 2 + offset
    my = (p_bot[1] + p_top[1]) / 2
    parts.append(_line(p_bot[0], p_bot[1], p_top[0], p_top[1], C_DIM, 0.8, "5,3"))
    parts.append(f'<circle cx="{p_bot[0]:.1f}" cy="{p_bot[1]:.1f}" r="2.5" fill="{C_DIM}"/>')
    parts.append(f'<circle cx="{p_top[0]:.1f}" cy="{p_top[1]:.1f}" r="2.5" fill="{C_DIM}"/>')
    angle = math.degrees(math.atan2(p_top[1] - p_bot[1], p_top[0] - p_bot[0]))
    parts.append(_text(mx, my, label, 11, C_DIM_TEXT, weight="600", rotate=angle))


# ── LEGS ───────────────────────────────────────────────────────────
def _draw_legs(parts, ox, oy, s, bench_w, seat_d, leg_h=5, inset=3):
    """Draw 4 tapered legs under the base."""
    leg_top = 3  # leg top width
    leg_bot = 2  # leg bottom width (tapered)
    positions = [
        (inset, inset),
        (bench_w - inset, inset),
        (inset, seat_d - inset),
        (bench_w - inset, seat_d - inset),
    ]
    for lx, ly in positions:
        # Only draw front-visible legs
        b1 = _iso(lx - leg_bot, ly - leg_bot, -leg_h, ox, oy, s)
        b2 = _iso(lx + leg_bot, ly - leg_bot, -leg_h, ox, oy, s)
        t1 = _iso(lx - leg_top, ly - leg_top, 0, ox, oy, s)
        t2 = _iso(lx + leg_top, ly - leg_top, 0, ox, oy, s)
        parts.append(_poly([b1, b2, t2, t1], C_LEG, C_LEG, 0.5))


# ── SHADOW ─────────────────────────────────────────────────────────
def _draw_shadow(parts, ox, oy, s, bench_w, seat_d):
    """Draw floor shadow ellipse."""
    center = _iso(bench_w / 2, seat_d / 2, -6, ox, oy, s)
    rw = bench_w * s * COS_A * 0.52
    rh = seat_d * s * SIN_A * 0.8
    parts.append(
        f'<ellipse cx="{center[0]:.1f}" cy="{center[1]:.1f}" '
        f'rx="{rw:.1f}" ry="{rh:.1f}" fill="#00000008" stroke="none"/>'
    )


# ── ARM CAPS ───────────────────────────────────────────────────────
def _draw_arm_cap(parts, ox, oy, s, ax, ay, aw, ad, ah):
    """Draw an upholstered arm cap at end of bench."""
    # Front face
    parts.append(_rounded_face([
        _iso(ax, ay, 0, ox, oy, s),
        _iso(ax + aw, ay, 0, ox, oy, s),
        _iso(ax + aw, ay, ah, ox, oy, s),
        _iso(ax, ay, ah, ox, oy, s),
    ], "#a6833e", C_WELT, 1.0, r=4))
    # Top face (rounded arm top)
    parts.append(_rounded_face([
        _iso(ax, ay, ah, ox, oy, s),
        _iso(ax + aw, ay, ah, ox, oy, s),
        _iso(ax + aw, ay + ad, ah, ox, oy, s),
        _iso(ax, ay + ad, ah, ox, oy, s),
    ], C_FABRIC_TOP, C_WELT, 0.8, r=5))
    # Side face
    parts.append(_rounded_face([
        _iso(ax + aw, ay, 0, ox, oy, s),
        _iso(ax + aw, ay + ad, 0, ox, oy, s),
        _iso(ax + aw, ay + ad, ah, ox, oy, s),
        _iso(ax + aw, ay, ah, ox, oy, s),
    ], C_FABRIC_SIDE, C_WELT, 0.8, r=3))


# ── SINGLE BENCH SECTION (reusable) ───────────────────────────────
def _draw_bench_section(parts, ox, oy, s, sx, sy, w, d, show_channels=True):
    """Draw one bench section: base + cushion + back with channels."""
    # ── FLOOR SHADOW (layered for depth) ──
    sh_c = _iso(sx + w / 2, sy + d / 2, -6, ox, oy, s)
    sh_rw = w * s * COS_A * 0.52
    sh_rh = d * s * SIN_A * 0.7
    parts.append(f'<ellipse cx="{sh_c[0]:.1f}" cy="{sh_c[1]+4:.1f}" rx="{sh_rw:.1f}" ry="{sh_rh:.1f}" fill="#00000006"/>')
    parts.append(f'<ellipse cx="{sh_c[0]:.1f}" cy="{sh_c[1]:.1f}" rx="{sh_rw*0.8:.1f}" ry="{sh_rh*0.6:.1f}" fill="#00000008"/>')

    # ── LEGS ──
    _draw_legs(parts, ox, oy, s, w + sx, d + sy, leg_h=4, inset=4)

    # ── BASE / PLATFORM (dark wood with kick board) ──
    kick_h = 3  # kick board recessed at bottom
    kick_inset = 2  # kick is recessed inward

    # Main base front face (above kick)
    parts.append(_rounded_face([
        _iso(sx, sy, kick_h, ox, oy, s),
        _iso(sx + w, sy, kick_h, ox, oy, s),
        _iso(sx + w, sy, PLAT_H, ox, oy, s),
        _iso(sx, sy, PLAT_H, ox, oy, s),
    ], C_BASE_FRONT, "#1a1a1a", 1.2, r=3))
    # Kick board (recessed)
    parts.append(_poly([
        _iso(sx + kick_inset, sy - kick_inset, 0, ox, oy, s),
        _iso(sx + w - kick_inset, sy - kick_inset, 0, ox, oy, s),
        _iso(sx + w - kick_inset, sy - kick_inset, kick_h, ox, oy, s),
        _iso(sx + kick_inset, sy - kick_inset, kick_h, ox, oy, s),
    ], "#1a1510", "#1a1a1a", 0.6))
    # Base bottom edge (overhang above kick)
    parts.append(_line(
        *_iso(sx, sy, kick_h, ox, oy, s),
        *_iso(sx + w, sy, kick_h, ox, oy, s),
        "#2a2015", 1.0))

    # Top of base
    parts.append(_poly([
        _iso(sx, sy, PLAT_H, ox, oy, s),
        _iso(sx + w, sy, PLAT_H, ox, oy, s),
        _iso(sx + w, sy + d, PLAT_H, ox, oy, s),
        _iso(sx, sy + d, PLAT_H, ox, oy, s),
    ], C_BASE_TOP, "#1a1a1a", 0.8))
    # Right side of base
    parts.append(_rounded_face([
        _iso(sx + w, sy, kick_h, ox, oy, s),
        _iso(sx + w, sy + d, kick_h, ox, oy, s),
        _iso(sx + w, sy + d, PLAT_H, ox, oy, s),
        _iso(sx + w, sy, PLAT_H, ox, oy, s),
    ], C_BASE_SIDE, "#1a1a1a", 1.0, r=3))

    # ── SEAT CUSHION (rounded, thick foam with gradient) ──
    cush_inset = 1.5  # cushion overhangs base slightly
    cx, cy = sx - cush_inset, sy - cush_inset
    cw, cd = w + cush_inset * 2, d + cush_inset
    cz = PLAT_H  # sits on top of base

    # Front face (gradient shading)
    parts.append(_rounded_face([
        _iso(cx, cy, cz, ox, oy, s),
        _iso(cx + cw, cy, cz, ox, oy, s),
        _iso(cx + cw, cy, cz + FOAM_T, ox, oy, s),
        _iso(cx, cy, cz + FOAM_T, ox, oy, s),
    ], "url(#cushFront)", C_WELT, 1.0, r=5))
    # Top face
    parts.append(_rounded_face([
        _iso(cx, cy, cz + FOAM_T, ox, oy, s),
        _iso(cx + cw, cy, cz + FOAM_T, ox, oy, s),
        _iso(cx + cw, cy + cd, cz + FOAM_T, ox, oy, s),
        _iso(cx, cy + cd, cz + FOAM_T, ox, oy, s),
    ], C_FABRIC_TOP, C_WELT, 0.8, r=6))

    # Seat seam lines (cushion divisions — every ~24")
    seat_seams = max(int(w / 24), 1)
    for si in range(1, seat_seams):
        seam_x = cx + cw * si / seat_seams
        sl1 = _iso(seam_x, cy + 1, cz + FOAM_T, ox, oy, s)
        sl2 = _iso(seam_x, cy + cd - 1, cz + FOAM_T, ox, oy, s)
        parts.append(_line(sl1[0], sl1[1], sl2[0], sl2[1], "#b8944f", 0.6))

    # Right side
    parts.append(_rounded_face([
        _iso(cx + cw, cy, cz, ox, oy, s),
        _iso(cx + cw, cy + cd, cz, ox, oy, s),
        _iso(cx + cw, cy + cd, cz + FOAM_T, ox, oy, s),
        _iso(cx + cw, cy, cz + FOAM_T, ox, oy, s),
    ], C_FABRIC_SIDE, C_WELT, 0.8, r=4))

    # Double welting line along top-front edge of cushion
    wl1 = _iso(cx + 2, cy, cz + FOAM_T, ox, oy, s)
    wl2 = _iso(cx + cw - 2, cy, cz + FOAM_T, ox, oy, s)
    parts.append(_line(wl1[0], wl1[1], wl2[0], wl2[1], C_WELT, 1.8))
    # Second welt offset
    wl1b = _iso(cx + 2, cy + 0.8, cz + FOAM_T, ox, oy, s)
    wl2b = _iso(cx + cw - 2, cy + 0.8, cz + FOAM_T, ox, oy, s)
    parts.append(_line(wl1b[0], wl1b[1], wl2b[0], wl2b[1], "#ddc48a", 0.6))

    # ── BACK CUSHION (with channel tufting) ──
    back_t = FOAM_T  # back cushion thickness
    bx, by = sx, sy + d - back_t
    bz = SEAT_H  # back starts at seat height

    # Front face (gradient)
    parts.append(_rounded_face([
        _iso(bx, by, bz, ox, oy, s),
        _iso(bx + w, by, bz, ox, oy, s),
        _iso(bx + w, by, bz + BACK_H, ox, oy, s),
        _iso(bx, by, bz + BACK_H, ox, oy, s),
    ], "url(#backFront)", C_WELT, 1.0, r=5))

    # Channel grooves (3D effect — shadow line + highlight line per channel)
    if show_channels:
        ch_count = max(int(w / 7), 4)
        ch_w = w / ch_count
        for i in range(1, ch_count):
            cx_ch = bx + w * i / ch_count
            # Deep groove shadow
            p1 = _iso(cx_ch, by - 0.3, bz + 1.5, ox, oy, s)
            p2 = _iso(cx_ch, by - 0.3, bz + BACK_H - 1.5, ox, oy, s)
            parts.append(_line(p1[0], p1[1], p2[0], p2[1], "#8b7340", 1.0))
            # Highlight on right edge of channel
            p1h = _iso(cx_ch + 1.8, by - 0.5, bz + 2, ox, oy, s)
            p2h = _iso(cx_ch + 1.8, by - 0.5, bz + BACK_H - 2, ox, oy, s)
            parts.append(_line(p1h[0], p1h[1], p2h[0], p2h[1], "#e8d8a8", 0.5))
        # Subtle puffiness — alternating channel shade
        for i in range(ch_count):
            if i % 2 == 0:
                cx1 = bx + ch_w * i + 2
                cx2 = bx + ch_w * (i + 1) - 2
                mid_z = bz + BACK_H / 2
                pm = _iso((cx1 + cx2) / 2, by - 0.8, mid_z, ox, oy, s)
                rr = ch_w * s * COS_A * 0.35
                parts.append(f'<circle cx="{pm[0]:.1f}" cy="{pm[1]:.1f}" r="{rr:.1f}" fill="#ddc48a" opacity="0.08"/>')

    # Back top face
    parts.append(_rounded_face([
        _iso(bx, by, bz + BACK_H, ox, oy, s),
        _iso(bx + w, by, bz + BACK_H, ox, oy, s),
        _iso(bx + w, by + back_t, bz + BACK_H, ox, oy, s),
        _iso(bx, by + back_t, bz + BACK_H, ox, oy, s),
    ], C_BACK_TOP, C_WELT, 0.8, r=4))
    # Back right side
    parts.append(_rounded_face([
        _iso(bx + w, by, bz, ox, oy, s),
        _iso(bx + w, by + back_t, bz, ox, oy, s),
        _iso(bx + w, by + back_t, bz + BACK_H, ox, oy, s),
        _iso(bx + w, by, bz + BACK_H, ox, oy, s),
    ], C_BACK_SIDE, C_WELT, 0.8, r=4))

    # Top welting line on back
    wt1 = _iso(bx + 2, by, bz + BACK_H, ox, oy, s)
    wt2 = _iso(bx + w - 2, by, bz + BACK_H, ox, oy, s)
    parts.append(_line(wt1[0], wt1[1], wt2[0], wt2[1], C_WELT, 1.2))

    # Bottom welting where back meets seat
    wb1 = _iso(bx + 2, by, bz, ox, oy, s)
    wb2 = _iso(bx + w - 2, by, bz, ox, oy, s)
    parts.append(_line(wb1[0], wb1[1], wb2[0], wb2[1], C_WELT, 1.0))


# ── PUBLIC: RENDER A FULL DRAWING ──────────────────────────────────

def render_straight(name: str, lf: float, rate: float = 195,
                    quote_num: str = "", svg_w: int = 740, svg_h: int = 460) -> str:
    """Render a straight bench in isometric perspective."""
    bench_w = lf * 12
    scale = min(420 / bench_w, 2.8)
    ox, oy = svg_w * 0.48, svg_h * 0.68

    parts = _header(svg_w, svg_h, name, lf, rate, quote_num)

    _draw_bench_section(parts, ox, oy, scale, 0, 0, bench_w, SEAT_D)

    # ── ARM CAPS (end pieces) ──
    arm_w = 3  # arm cap width
    arm_h = TOTAL_H + 2  # slightly taller than back
    # Left arm cap
    _draw_arm_cap(parts, ox, oy, scale, -arm_w, 0, arm_w, SEAT_D, arm_h)
    # Right arm cap
    _draw_arm_cap(parts, ox, oy, scale, bench_w, 0, arm_w, SEAT_D, arm_h)

    # ── DIMENSIONS ──
    _dim_h(parts,
           _iso(0, -6, -8, ox, oy, scale),
           _iso(bench_w, -6, -8, ox, oy, scale),
           f"{lf:.0f}' ({bench_w:.0f}\")", offset=-16)

    _dim_v(parts,
           _iso(bench_w + arm_w + 12, -2, 0, ox, oy, scale),
           _iso(bench_w + arm_w + 12, -2, TOTAL_H, ox, oy, scale),
           f'{TOTAL_H}"', offset=16)

    # Seat height sub-dim
    _dim_v(parts,
           _iso(bench_w + arm_w + 24, -2, 0, ox, oy, scale),
           _iso(bench_w + arm_w + 24, -2, SEAT_H, ox, oy, scale),
           f'seat {SEAT_H}"', offset=14)

    # Depth
    _dim_h(parts,
           _iso(bench_w + arm_w + 8, 0, SEAT_H + 3, ox, oy, scale),
           _iso(bench_w + arm_w + 8, SEAT_D, SEAT_H + 3, ox, oy, scale),
           f'{SEAT_D}" deep', offset=-12)

    parts += _footer(svg_w, svg_h)
    return _wrap(parts, svg_w, svg_h)


def render_l_shape(name: str, lf: float, rate: float = 195,
                   quote_num: str = "", svg_w: int = 740, svg_h: int = 500) -> str:
    """Render an L-shaped bench."""
    long_lf = lf * 0.6
    short_lf = lf * 0.4
    long_w = long_lf * 12
    short_d = short_lf * 12

    scale = min(400 / long_w, 280 / (short_d + SEAT_D), 2.2)
    ox, oy = svg_w * 0.44, svg_h * 0.70

    parts = _header(svg_w, svg_h, name, lf, rate, quote_num)

    # Long side
    _draw_bench_section(parts, ox, oy, scale, 0, 0, long_w, SEAT_D)
    # Short wing (perpendicular at right end)
    _draw_bench_section(parts, ox, oy, scale, long_w - SEAT_D, 0, SEAT_D, short_d)

    # Dimensions
    _dim_h(parts,
           _iso(0, -6, -8, ox, oy, scale),
           _iso(long_w, -6, -8, ox, oy, scale),
           f"{long_lf:.0f}' long side", offset=-16)

    _dim_h(parts,
           _iso(long_w + 8, 0, -4, ox, oy, scale),
           _iso(long_w + 8, short_d, -4, ox, oy, scale),
           f"{short_lf:.0f}' wing", offset=-12)

    parts += _footer(svg_w, svg_h)
    return _wrap(parts, svg_w, svg_h)


def render_u_shape(name: str, lf: float, rate: float = 195,
                   multiplier: int = 1, quote_num: str = "",
                   svg_w: int = 740, svg_h: int = 520) -> str:
    """Render a U-shaped booth."""
    per_booth = lf / multiplier if multiplier > 1 else lf
    center_lf = per_booth * 0.45
    wing_lf = per_booth * 0.275
    center_w = center_lf * 12
    wing_d = wing_lf * 12

    scale = min(360 / (center_w + SEAT_D * 2), 250 / (wing_d + SEAT_D), 2.0)
    ox, oy = svg_w * 0.47, svg_h * 0.68

    sub = f"Each booth: {per_booth:.0f} LF" if multiplier > 1 else f"{lf:.0f} LF total"
    parts = _header(svg_w, svg_h, name, lf, rate, quote_num, subtitle_extra=sub)

    # Center
    _draw_bench_section(parts, ox, oy, scale, 0, 0, center_w, SEAT_D)
    # Left wing
    _draw_bench_section(parts, ox, oy, scale, -SEAT_D, 0, SEAT_D, wing_d)
    # Right wing
    _draw_bench_section(parts, ox, oy, scale, center_w, 0, SEAT_D, wing_d)

    # Dimensions
    _dim_h(parts,
           _iso(-SEAT_D, -8, -8, ox, oy, scale),
           _iso(center_w + SEAT_D, -8, -8, ox, oy, scale),
           f"{per_booth:.0f}' total", offset=-16)

    _dim_h(parts,
           _iso(0, -4, -4, ox, oy, scale),
           _iso(center_w, -4, -4, ox, oy, scale),
           f"{center_lf:.0f}' center", offset=-14)

    _dim_h(parts,
           _iso(center_w + SEAT_D + 10, 0, -4, ox, oy, scale),
           _iso(center_w + SEAT_D + 10, wing_d, -4, ox, oy, scale),
           f"{wing_lf:.0f}' wing", offset=-12)

    parts += _footer(svg_w, svg_h)
    return _wrap(parts, svg_w, svg_h)


# ── HELPERS ────────────────────────────────────────────────────────

def _header(svg_w, svg_h, name, lf, rate, quote_num, subtitle_extra=""):
    parts = []
    # SVG defs for gradients
    parts.append(f'''<defs>
    <linearGradient id="floorGrad" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#f5f0e8"/>
      <stop offset="100%" stop-color="#e8e0d0"/>
    </linearGradient>
    <linearGradient id="cushFront" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#d4b87a"/>
      <stop offset="100%" stop-color="#a6833e"/>
    </linearGradient>
    <linearGradient id="backFront" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#dcc48a"/>
      <stop offset="60%" stop-color="#c9a96e"/>
      <stop offset="100%" stop-color="#b8944f"/>
    </linearGradient>
    <filter id="shadow" x="-20%" y="-20%" width="140%" height="140%">
      <feDropShadow dx="2" dy="4" stdDeviation="6" flood-color="#00000018"/>
    </filter>
  </defs>''')

    parts.append(f'<rect width="{svg_w}" height="{svg_h}" fill="white" rx="10"/>')
    parts.append(f'<rect x="2" y="2" width="{svg_w-4}" height="{svg_h-4}" fill="none" stroke="#e8e0d0" rx="10" stroke-width="1.5"/>')

    # Wall backdrop (brick texture)
    wall_y = 60
    wall_h = svg_h * 0.55
    parts.append(f'<rect x="20" y="{wall_y}" width="{svg_w-40}" height="{wall_h:.0f}" fill="#f0ebe4" rx="4"/>')
    # Brick rows
    brick_h = 10
    brick_w = 30
    for row in range(int(wall_h / brick_h)):
        ry = wall_y + row * brick_h
        if ry > wall_y + wall_h - 5:
            break
        offset = (brick_w / 2) if row % 2 else 0
        for col in range(int((svg_w - 40) / brick_w) + 1):
            bx = 20 + col * brick_w + offset
            if bx > svg_w - 22:
                continue
            bw = min(brick_w - 1, svg_w - 22 - bx)
            if bw < 5:
                continue
            parts.append(f'<rect x="{bx:.0f}" y="{ry:.0f}" width="{bw:.0f}" height="{brick_h - 1}" fill="none" stroke="#e0d8ce" stroke-width="0.3" rx="1"/>')

    # Floor plane (herringbone pattern)
    floor_y = wall_y + wall_h
    floor_h = svg_h - floor_y - 40
    parts.append(f'<rect x="20" y="{floor_y:.0f}" width="{svg_w-40}" height="{floor_h:.0f}" fill="url(#floorGrad)" rx="0"/>')
    # Herringbone lines
    for hi in range(0, svg_w, 18):
        hx = 20 + hi
        parts.append(f'<line x1="{hx}" y1="{floor_y}" x2="{hx+9}" y2="{floor_y + floor_h}" stroke="#ddd5c8" stroke-width="0.3"/>')
        parts.append(f'<line x1="{hx+9}" y1="{floor_y}" x2="{hx}" y2="{floor_y + floor_h}" stroke="#ddd5c8" stroke-width="0.3"/>')
    # Floor line
    parts.append(f'<line x1="20" y1="{floor_y:.0f}" x2="{svg_w-20}" y2="{floor_y:.0f}" stroke="#c8c0b0" stroke-width="0.8"/>')

    # Gold header bar
    parts.append(f'<rect x="0" y="0" width="{svg_w}" height="58" fill="#f8f4ec" rx="10"/>')
    parts.append(f'<rect x="0" y="30" width="{svg_w}" height="28" fill="#f8f4ec"/>')
    parts.append(f'<line x1="20" y1="58" x2="{svg_w-20}" y2="58" stroke="#d4af37" stroke-width="1.5"/>')

    parts.append(_text(svg_w / 2, 24, name, 15, "#1a1a1a", weight="bold"))
    sub = f"{quote_num} — " if quote_num else ""
    sub += f"{lf:.0f} LF @ ${rate:.0f}/lf = ${lf * rate:,.0f}"
    if subtitle_extra:
        sub += f" | {subtitle_extra}"
    parts.append(_text(svg_w / 2, 46, sub, 11, "#666"))
    return parts


def _footer(svg_w, svg_h):
    parts = []
    y = svg_h - 52

    # Spec box
    box_w = svg_w - 60
    box_h = 42
    parts.append(f'<rect x="30" y="{y-4}" width="{box_w}" height="{box_h}" fill="#faf8f4" stroke="#e8e0d0" rx="5"/>')

    # Left: specs
    parts.append(_text(40, y + 12, f"SEAT: {SEAT_H}\"H × {SEAT_D}\"D", 9, "#555", anchor="start", weight="600"))
    parts.append(_text(40, y + 24, f"BACK: {BACK_H}\"H vertical channels", 9, "#555", anchor="start"))
    parts.append(_text(40, y + 36, f"FOAM: {FOAM_T}\" HR density | 8-way hand-tied springs", 9, "#555", anchor="start"))

    # Right: branding
    parts.append(_text(svg_w - 40, y + 14, "Empire Workroom", 11, "#b8960c", anchor="end", weight="bold"))
    parts.append(_text(svg_w - 40, y + 28, "Architectural Drawing", 9, "#999", anchor="end"))
    parts.append(_text(svg_w - 40, y + 38, "empirebox.store", 8, "#bbb", anchor="end"))

    return parts


def _wrap(parts, w, h):
    body = "\n  ".join(parts)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" '
        f'width="{w}" height="{h}">\n  {body}\n</svg>'
    )


# ── BATCH: Generate all areas from a quote ─────────────────────────

def render_quote_drawings(line_items: list, quote_num: str = "") -> list[dict]:
    """Generate drawings for all areas in a quote. Returns [{name, svg, lf}, ...]."""
    results = []
    for item in line_items:
        desc = item.get("description", "")
        lf = item.get("quantity", 0)
        rate = item.get("rate", 195)
        if lf <= 0:
            continue

        name = desc.split("—")[0].strip() if "—" in desc else desc

        # Detect shape
        desc_lower = desc.lower()
        if "u-shape" in desc_lower or "u shape" in desc_lower:
            mult = 2 if "×2" in desc or "x2" in desc_lower else 1
            svg = render_u_shape(name, lf, rate, mult, quote_num)
        elif "l-shape" in desc_lower or "l shape" in desc_lower:
            svg = render_l_shape(name, lf, rate, quote_num)
        else:
            svg = render_straight(name, lf, rate, quote_num)

        results.append({"name": name, "svg": svg, "lf": lf})
    return results


def drawings_to_pdf(drawings: list[dict], output_path: str) -> str:
    """Convert list of drawing dicts to a multi-page PDF. Returns path."""
    from weasyprint import HTML as WeasyHTML

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    html = (
        '<!DOCTYPE html><html><head><meta charset="utf-8">'
        '<style>@page{size:letter landscape;margin:0.3in}'
        'body{margin:0}.pg{page-break-after:always;display:flex;'
        'align-items:center;justify-content:center;min-height:92vh}'
        '.pg:last-child{page-break-after:auto}</style></head><body>'
    )
    for d in drawings:
        html += f'<div class="pg">{d["svg"]}</div>'
    html += '</body></html>'

    WeasyHTML(string=html).write_pdf(output_path)
    return output_path
