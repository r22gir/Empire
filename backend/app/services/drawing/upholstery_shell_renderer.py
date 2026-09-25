"""Upholstery-on-existing-shell banquette sheets (U / L).

Acceptance: Marleys EST-2026-272 — orthographic pack first:
  TOP (plan) / FRONT / SIDE for U and L, then mockup / schedule / materials.
Isometric is PARKED for discussion packs (omit by default; closed-face iso
rule remains in EMPIRE_DRAWING_STANDARD / system_prompt for later).

This is NOT the millwork/CNC bench_renderer. No wood frame, ribs,
dados, or 24" auto-slice cushion heroes.
  TOP  = shell outline + seat cushion footprint (outer/inner/depth)
  SIDE = elevation with video dim chain: overall H, overall D, seat H AFF,
         seat depth, lean (foam = distinct mat'l, NEVER labeled as seat H)
  FRONT = face view (pattern on back / plain seat)
Seat H = AFF plane (~18" PROV), NEVER foam thickness.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas
from reportlab.lib.colors import HexColor, black, white, Color

NAVY = HexColor("#1a365d")
GOLD = HexColor("#b8860b")
GRAY = HexColor("#4a5568")
SHELL = HexColor("#2c5282")
CUSH = HexColor("#c05621")
PROV = HexColor("#c53030")
LT_BLUE = HexColor("#ebf4ff")
LT_PEACH = HexColor("#feebc8")
LT_FOAM = HexColor("#fbd38d")
LT_PEACH = HexColor("#feebc8")
# Client mockup — match Sep 2022 ref (black basketweave back / plain black seat)
# Founder lock: every basketweave bar uses this one fabric fill.  The pattern
# is carried by the stronger seam/grid lines below, never by alternating bar
# colors (which creates a false light/dark illusion in the client mockup).
PATTERN_BACK = HexColor("#2a2a2a")      # one charcoal/black fabric fill
PATTERN_BACK_DK = HexColor("#111111")   # outline / seam ink
PATTERN_BACK_BAR = PATTERN_BACK          # compatibility alias; never a second fill
PATTERN_BACK_GAP = PATTERN_BACK_DK       # compatibility alias; no gap fill
PATTERN_BACK_SEAM = HexColor("#080808")  # visible seams between the 2 bars
PLAIN_SEAT = HexColor("#1c1c1c")        # plain smooth black seat
PLAIN_SEAT_DK = HexColor("#0e0e0e")
LT_GRAY = HexColor("#edf2f7")
MED_GRAY = HexColor("#cbd5e0")

# Empire yardage defaults (drawing/yardage.py)
FABRIC_WIDTH_DEFAULT = 54.0
WASTE_FABRIC = 1.15          # 15%
WASTE_PLY = 1.15             # 15% cutting waste on 1/2" ply
PLY_SHEET_SF = 32.0          # 4x8 sheet
PLY_THICKNESS = 0.5

COS30 = math.cos(math.radians(30))
SIN30 = math.sin(math.radians(30))


@dataclass
class UShellSpec:
    """U banquette upholstery-on-shell dims — ALL INCHES."""
    back_outer: float = 249.75
    arm_left: float = 41.25       # wing LENGTH along room (not thickness)
    arm_right: float = 52.0       # wing LENGTH — asymmetric, do NOT max()
    seat_depth: float = 16.25     # cushion depth / wing THICKNESS
    shell_height: float = 30.25
    net_back_height: float = 26.75  # sits ON seat foam; = shell - 3.5 board/foam/Dacron
    seat_height: float = 18.0  # AFF seat plane (PROV) — NOT foam thickness
    seat_foam: float = 2.0     # material thickness only (distinct from seat_height AFF)
    board_stack: float = 3.5
    # Provisional lean/pitch from Rafael help-video sketch (Sep 2026):
    # top of back set back toward wall vs seat-back line. Confirm on site.
    back_lean_in: float = 3.0

    @property
    def developed_outer_in(self) -> float:
        return self.back_outer + self.arm_left + self.arm_right

    @property
    def developed_outer_lf(self) -> float:
        return self.developed_outer_in / 12.0

    @property
    def developed_inner_in(self) -> float:
        """Seat-front developed run: outer − 4×seat_depth (2 corners × 2 cuts)."""
        return self.developed_outer_in - 4.0 * self.seat_depth

    @property
    def developed_inner_lf(self) -> float:
        return self.developed_inner_in / 12.0

    @property
    def inner_back(self) -> float:
        return self.back_outer - 2.0 * self.seat_depth

    @property
    def inner_arm_left(self) -> float:
        return self.arm_left - self.seat_depth

    @property
    def inner_arm_right(self) -> float:
        return self.arm_right - self.seat_depth

    @property
    def footprint_width(self) -> float:
        return self.back_outer + 2 * self.seat_depth

    @property
    def back_sf(self) -> float:
        return self.developed_outer_lf * (self.net_back_height / 12.0)

    @property
    def seat_sf(self) -> float:
        return self.developed_outer_lf * (self.seat_depth / 12.0)


@dataclass
class LShellSpec:
    """L banquette — ALL INCHES. Depth/height provisional vs U."""
    leg_short: float = 48.875
    leg_long: float = 107.75
    seat_depth: float = 19.0
    shell_height: float = 30.0
    seat_height: float = 18.0
    net_back_height: float = 26.75  # match U / quote L-B 29.09; 0 → shell-3.5
    seat_foam: float = 2.0
    back_lean_in: float = 3.0  # provisional — match U until site-confirmed
    provisional: bool = True

    @property
    def developed_outer_in(self) -> float:
        return self.leg_short + self.leg_long

    @property
    def developed_outer_lf(self) -> float:
        return self.developed_outer_in / 12.0

    @property
    def developed_inner_in(self) -> float:
        """Seat-front developed: each leg loses one seat_depth at the corner."""
        return self.developed_outer_in - 2.0 * self.seat_depth

    @property
    def developed_inner_lf(self) -> float:
        return self.developed_inner_in / 12.0

    @property
    def inner_leg_short(self) -> float:
        return self.leg_short - self.seat_depth

    @property
    def inner_leg_long(self) -> float:
        return self.leg_long - self.seat_depth

    @property
    def net_back(self) -> float:
        if self.net_back_height > 0:
            return self.net_back_height
        return max(self.shell_height - 3.5, 0)

    @property
    def back_sf(self) -> float:
        return self.developed_outer_lf * (self.net_back / 12.0)

    @property
    def seat_sf(self) -> float:
        return self.developed_outer_lf * (self.seat_depth / 12.0)


@dataclass
class SheetMeta:
    quote_num: str = "EST-2026-272"
    job: str = "Marley's Hyattsville — U+L Banquette Upholstery"
    note: str = (
        "Existing shells on site. Cushion footprint + shell outline only — not wood frame. "
        "DRAFT. BACK = basketweave bar 6.5×13 / tile 13×13 (2 bars H/V) + lean/pitch PROV; SEAT = plain. Height leftover 0.75\" OPEN."
    )
    client: str = "Dave Romero / Marley's Hyattsville"
    rev: str = "H-ORTHO"
    drawn_by: str = "MAX AI / Empire Workroom"
    date_str: str = ""

    def __post_init__(self):
        if not self.date_str:
            self.date_str = datetime.now().strftime("%m/%d/%Y")


# ── Modular basketweave construction (Rafael / Founder LOCK Sep 2026) ──
# PATTERN backs = constructed BAR boards (1/2" ply + foam + fabric), NOT printed COM face-SF.
# Founder lock: bar FACE = 6.5" × 13"; tile = 13" × 13" (TWO bars per square, H/V alternating).
# NOT height-divided small bars. KILL prior 2.229 / 3.344 / 6.6875 / 7.5 / 8.917 assumptions.
# Net back 26.75" = 2 full rows of 13" + 0.75" leftover closer/trim band (OPEN — flag).
# Walk developed runs → full tiles + end closers; U gets inside-corner specials.
# Seat = PLAIN large pieces.
NET_BACK_ROWS = 2                             # full 13" tile rows (NOT 4-row height divide)
BARS_PER_TILE = 2                             # Rafael close-up: 2 bars per square tile
TILE_FACE_IN = 13.0                           # LOCKED square tile (NOT net_back/rows)
BAR_FACE_W_IN = 6.5                           # LOCKED bar face width
BAR_FACE_H_IN = 13.0                          # LOCKED bar face height (= tile edge)
MODULE_FACE_IN = TILE_FACE_IN                 # alias: square tile face
HEIGHT_LEFTOVER_IN = 0.75                     # 26.75 - 2×13; closer/trim band — OPEN
MODULE_FOAM_THK_IN = 1.5                      # foam wrap each side of bar
MODULE_STAPLE_IN = 2.5                        # staple-back allowance (mid of Rafael's 2–3")
# Fabric blank = face + 2×(foam + staple) → 6.5+8=14.5, 13+8=21
U_INSIDE_CORNERS = 2                          # U-shape inside-corner specials
SEAT_FOAM_THK_IN = 2.0                        # seat foam (matches UShellSpec.seat_foam default)
SEAT_STAPLE_IN = 2.5                          # plain seat fabric staple-back allowance
SEAT_WRAP_EDGE_IN = SEAT_FOAM_THK_IN + SEAT_STAPLE_IN  # per edge
NEST_WASTE_FABRIC = 1.10                      # 10% nesting/cutting waste on top of blank sizes
# (staple/wrap already inside blanks — do NOT also apply old face-SF 15% as pattern match)


@dataclass
class ModuleSchedule:
    """Per-board / per-piece modular back takeoff (bars, closers, corner specials)."""
    mark: str
    location: str
    module_face_in: float       # primary face dim (bar W or closer W or tile)
    cols: int                   # full tile cols along run (0 for non-grid lines)
    rows: int                   # full tile rows (2) or 0
    count: int                  # board / blank count
    ply_blank_in: tuple         # (w, h)
    foam_blank_in: tuple
    fabric_blank_in: tuple
    ply_sf: float
    foam_sf: float
    fabric_sf: float
    notes: str


@dataclass
class MaterialsTakeoff:
    fabric_width_in: float
    waste_fabric: float          # nest waste multiplier on blanks
    waste_ply: float
    # Face areas (info / comparison only — NOT order basis for pattern)
    pattern_back_sf: float
    plain_seat_sf: float
    # Photo-locked tile / bar geometry
    module_face_in: float        # tile square (= TILE_FACE_IN = 13")
    bar_face_in: tuple           # (w, h) std bar = (6.5, 13)
    tile_rows: int               # 2 full rows
    height_leftover_in: float    # 0.75" closer/trim band
    height_leftover_status: str  # OPEN until founder closes
    module_foam_thk_in: float
    module_staple_in: float
    # Walk counts
    u_full_tiles: int
    u_end_closer_w_in: float
    u_end_closers: int
    u_inside_corner_specials: int
    l_full_tiles: int
    l_end_closer_w_in: float
    l_end_closers: int
    u_std_bars: int
    l_std_bars: int
    std_bar_count_total: int
    board_count_total: int       # std bars + closers + IC specials
    # Compat aliases (std bars as primary "module" count)
    u_module_count: int
    l_module_count: int
    module_count_total: int
    module_ply_blank_in: tuple   # std bar ply
    module_foam_blank_in: tuple
    module_fabric_blank_in: tuple
    pattern_fabric_sf_blanks: float
    pattern_yards_raw: float
    pattern_yards_order: float
    # PLAIN seats (non-modular)
    seat_wrap_edge_in: float
    plain_fabric_sf_blanks: float
    plain_yards_raw: float
    plain_yards_order: float
    # 1/2" ply
    ply_back_sf: float           # sum of bar/closer/IC ply faces
    ply_seat_sf: float           # seat decks (face)
    ply_total_sf: float
    ply_with_waste_sf: float
    ply_sheets: int
    modules: list                # list[ModuleSchedule]
    assumptions: list
    formulas: list


def _ceil_quarter(y: float) -> float:
    return math.ceil(y * 4.0) / 4.0


def _walk_tiles(developed_in: float, tile: float) -> tuple[int, float]:
    """Full tiles that fit along developed run + leftover width for end closer."""
    full = max(0, int(math.floor((developed_in / tile) + 1e-9)))
    rem = round(developed_in - full * tile, 4)
    if rem < 0.05:
        rem = 0.0
    return full, rem


def _fabric_blank_in(face_w: float, face_h: float, foam_thk: float, staple: float) -> tuple[float, float]:
    """Face + foam-edge wrap + staple-on-back allowance (Rafael: fabric allowance)."""
    add = 2.0 * (foam_thk + staple)
    return (face_w + add, face_h + add)


def compute_materials(
    u: UShellSpec,
    L: LShellSpec,
    fabric_width_in: float = FABRIC_WIDTH_DEFAULT,
    waste_fabric: float = NEST_WASTE_FABRIC,
    waste_ply: float = WASTE_PLY,
    module_face_in: float = MODULE_FACE_IN,
    module_foam_thk: float = MODULE_FOAM_THK_IN,
    module_staple: float = MODULE_STAPLE_IN,
) -> MaterialsTakeoff:
    """Founder-locked 6.5×13 bar / 13×13 tile basketweave takeoff + plain seat wrap.

    TILE = 13" square (NOT net_back÷rows). Std bar FACE = 6.5" × 13" (TWO bars/tile, H/V).
    Net back 26.75" = 2×13" + 0.75" leftover closer/trim (OPEN).
    Walk U/L developed runs → full tiles + end closers; U adds inside-corner specials.
    PATTERN fabric ordered from BAR blanks (face + foam wrap + staple), not face-SF.
    Fabric blank = face + 2×(1.5 foam + 2.5 staple) → 14.5" × 21".
    """
    tile = float(module_face_in)  # 13.0 locked
    rows = NET_BACK_ROWS          # 2 full rows
    bars_n = BARS_PER_TILE
    bar_w = float(BAR_FACE_W_IN)  # 6.5 locked — do NOT derive as height-divide
    bar_h = float(BAR_FACE_H_IN)  # 13.0 locked
    h_left = float(HEIGHT_LEFTOVER_IN)  # 0.75 OPEN
    foam_t = module_foam_thk
    staple = module_staple

    u_full, u_rem = _walk_tiles(u.developed_outer_in, tile)
    l_full, l_rem = _walk_tiles(L.developed_outer_in, tile)

    u_std = u_full * rows * bars_n
    l_std = l_full * rows * bars_n
    u_ec = rows if u_rem > 0 else 0
    l_ec = rows if l_rem > 0 else 0
    u_ic = U_INSIDE_CORNERS * rows  # one special board per row at each inside corner

    # Std bar blanks (all standard boards the same)
    ply_blank = (round(bar_w, 5), round(bar_h, 5))
    foam_blank = ply_blank
    fab_blank = _fabric_blank_in(bar_w, bar_h, foam_t, staple)
    fab_blank_sf = (fab_blank[0] * fab_blank[1]) / 144.0
    ply_blank_sf = (bar_w * bar_h) / 144.0

    # End closer blanks — single bar strip of leftover width × tile height per row
    def closer_pack(rem: float, count: int):
        if count <= 0 or rem <= 0:
            return (0.0, 0.0), (0.0, 0.0), (0.0, 0.0), 0.0, 0.0
        ply_c = (round(rem, 4), round(bar_h, 4))
        fab_c = _fabric_blank_in(rem, bar_h, foam_t, staple)
        ply_sf = count * (ply_c[0] * ply_c[1]) / 144.0
        fab_sf = count * (fab_c[0] * fab_c[1]) / 144.0
        return ply_c, ply_c, fab_c, ply_sf, fab_sf

    u_ec_ply, u_ec_foam, u_ec_fab, u_ec_ply_sf, u_ec_fab_sf = closer_pack(u_rem, u_ec)
    l_ec_ply, l_ec_foam, l_ec_fab, l_ec_ply_sf, l_ec_fab_sf = closer_pack(l_rem, l_ec)

    # Inside-corner specials: same face blank as std bar (shop miters/wraps at corner)
    ic_ply_sf = u_ic * ply_blank_sf
    ic_fab_sf = u_ic * fab_blank_sf

    pattern_fab_sf = (
        (u_std + l_std) * fab_blank_sf
        + u_ec_fab_sf + l_ec_fab_sf
        + ic_fab_sf
    )
    pat_raw = (pattern_fab_sf * 4.0 * waste_fabric) / fabric_width_in

    ply_back = (
        (u_std + l_std) * ply_blank_sf
        + u_ec_ply_sf + l_ec_ply_sf
        + ic_ply_sf
    )

    board_total = u_std + l_std + u_ec + l_ec + u_ic

    modules = [
        ModuleSchedule(
            mark="U-STD",
            location="U std bars (2-bar tiles)",
            module_face_in=round(bar_w, 5),
            cols=u_full,
            rows=rows,
            count=u_std,
            ply_blank_in=ply_blank,
            foam_blank_in=foam_blank,
            fabric_blank_in=fab_blank,
            ply_sf=round(u_std * ply_blank_sf, 2),
            foam_sf=round(u_std * ply_blank_sf, 2),
            fabric_sf=round(u_std * fab_blank_sf, 2),
            notes=(
                f'{u_full} full tiles × {rows} rows × {bars_n} bars; '
                f'bar {bar_w:.4f}"×{bar_h:.4f}"; run {u.developed_outer_in:.2f}"'
            ),
        ),
        ModuleSchedule(
            mark="U-EC",
            location="U end closers",
            module_face_in=round(u_rem, 4) if u_rem else 0.0,
            cols=1 if u_ec else 0,
            rows=rows if u_ec else 0,
            count=u_ec,
            ply_blank_in=u_ec_ply if u_ec else (0.0, 0.0),
            foam_blank_in=u_ec_foam if u_ec else (0.0, 0.0),
            fabric_blank_in=u_ec_fab if u_ec else (0.0, 0.0),
            ply_sf=round(u_ec_ply_sf, 2),
            foam_sf=round(u_ec_ply_sf, 2),
            fabric_sf=round(u_ec_fab_sf, 2),
            notes=(
                f'leftover {u_rem:.4f}" after {u_full}×{tile:.1f}"; '
                f'{u_ec} boards ({rows} rows × 1 closer col)'
                if u_ec else "no leftover — run divides evenly"
            ),
        ),
        ModuleSchedule(
            mark="U-IC",
            location="U inside-corner specials",
            module_face_in=round(bar_w, 5),
            cols=U_INSIDE_CORNERS,
            rows=rows,
            count=u_ic,
            ply_blank_in=ply_blank,
            foam_blank_in=foam_blank,
            fabric_blank_in=fab_blank,
            ply_sf=round(ic_ply_sf, 2),
            foam_sf=round(ic_ply_sf, 2),
            fabric_sf=round(ic_fab_sf, 2),
            notes=f'{U_INSIDE_CORNERS} inside corners × {rows} rows; shop-miter/wrap specials',
        ),
        ModuleSchedule(
            mark="L-STD",
            location="L std bars (2-bar tiles) [prov.]",
            module_face_in=round(bar_w, 5),
            cols=l_full,
            rows=rows,
            count=l_std,
            ply_blank_in=ply_blank,
            foam_blank_in=foam_blank,
            fabric_blank_in=fab_blank,
            ply_sf=round(l_std * ply_blank_sf, 2),
            foam_sf=round(l_std * ply_blank_sf, 2),
            fabric_sf=round(l_std * fab_blank_sf, 2),
            notes=(
                f'{l_full} full tiles × {rows} rows × {bars_n} bars; '
                f'run {L.developed_outer_in:.3f}" PROV'
            ),
        ),
        ModuleSchedule(
            mark="L-EC",
            location="L end closers [prov.]",
            module_face_in=round(l_rem, 4) if l_rem else 0.0,
            cols=1 if l_ec else 0,
            rows=rows if l_ec else 0,
            count=l_ec,
            ply_blank_in=l_ec_ply if l_ec else (0.0, 0.0),
            foam_blank_in=l_ec_foam if l_ec else (0.0, 0.0),
            fabric_blank_in=l_ec_fab if l_ec else (0.0, 0.0),
            ply_sf=round(l_ec_ply_sf, 2),
            foam_sf=round(l_ec_ply_sf, 2),
            fabric_sf=round(l_ec_fab_sf, 2),
            notes=(
                f'leftover {l_rem:.4f}" after {l_full}×{tile:.1f}"; '
                f'{l_ec} boards PROV'
                if l_ec else "no leftover — run divides evenly"
            ),
        ),
        ModuleSchedule(
            mark="HT-BAND",
            location="Height leftover closer/trim",
            module_face_in=round(h_left, 4),
            cols=0,
            rows=0,
            count=0,
            ply_blank_in=(0.0, 0.0),
            foam_blank_in=(0.0, 0.0),
            fabric_blank_in=(0.0, 0.0),
            ply_sf=0.0,
            foam_sf=0.0,
            fabric_sf=0.0,
            notes=(
                f'net back {u.net_back_height:.2f}" = {rows}×{tile:.0f}" + {h_left:.2f}" '
                f'leftover — OPEN (closer/trim band; not in STD bar count)'
            ),
        ),
    ]

    # --- Plain seats (NON-modular large pieces) ---
    wrap = SEAT_WRAP_EDGE_IN

    def seat_blank_sf(depth: float, developed: float) -> float:
        return ((depth + 2 * wrap) * (developed + 2 * wrap)) / 144.0

    u_seat_fab = seat_blank_sf(u.seat_depth, u.developed_outer_in)
    l_seat_fab = seat_blank_sf(L.seat_depth, L.developed_outer_in)
    plain_fab_sf = u_seat_fab + l_seat_fab
    pln_raw = (plain_fab_sf * 4.0 * waste_fabric) / fabric_width_in

    plain_face = u.seat_sf + L.seat_sf
    pattern_face = u.back_sf + L.back_sf  # info only
    ply_seat = plain_face
    ply_tot = ply_back + ply_seat
    ply_w = ply_tot * waste_ply
    sheets = int(math.ceil(ply_w / PLY_SHEET_SF))

    bar_w_r = round(bar_w, 5)
    bar_h_r = round(bar_h, 5)
    assumptions = [
        "CONSTRUCTION (Founder lock / Rafael): PATTERN backs = built basketweave BAR boards — bar FACE 6.5\"×13\", tile 13\"×13\", 2 bars H/V alternating. NOT printed COM face-SF. KILL 2.229/3.344/6.6875/7.5/8.917 height-divide assumptions.",
        f'TILE LOCKED {tile:.1f}" square (NOT net_back÷rows). STD bar FACE {bar_w_r:.1f}" × {bar_h_r:.1f}" (all standard boards the same).',
        f'Net back {u.net_back_height:.2f}" = {rows}×{tile:.0f}" + {h_left:.2f}" leftover closer/trim band — status OPEN (not ordered as std bars).',
        f'Walk developed runs -> full tiles + end closers. U also gets {U_INSIDE_CORNERS} inside-corner specials x {rows} rows = {u_ic} boards.',
        f'Each STD bar = 1/2" ply {bar_w_r:.1f}"x{bar_h_r:.1f}" + foam {foam_t:.1f}" + fabric blank.',
        f'Fabric EXTRA (Rafael): foam-edge wrap {foam_t:.1f}" each side + staple-on-back {staple:.1f}" (mid of 2-3") each side -> STD blank {fab_blank[0]:.1f}"x{fab_blank[1]:.1f}" (expect 14.5×21).',
        f'Nesting/cutting waste on blanks {round((waste_fabric - 1) * 100)}% (separate from staple/wrap already in blank).',
        'SEAT = PLAIN large pieces (NOT modular basketweave). Shop may split for handling.',
        f'Plain seat fabric wrap ASSUMED {wrap:.1f}" per edge (= {SEAT_FOAM_THK_IN:.1f}" foam + {SEAT_STAPLE_IN:.1f}" staple). Blank = (depth+2w) x (developed+2w).',
        f'Fabric width ASSUMED {fabric_width_in:.0f}" (Empire default; provenance=pending until COM confirmed).',
        f'1/2" plywood: SUM of bar + closer + IC ply faces + seat deck face SF. Waste {round((waste_ply - 1) * 100)}%. Sheet 4x8 = {PLY_SHEET_SF:.0f} sf.',
        'Do NOT order pattern yardage from face-SF x waste — order from BAR / closer / IC blanks.',
        'L depth/height still PROVISIONAL — L board counts & seat blanks change when locked to U.',
        f'Back lean/pitch provisional {u.back_lean_in:.1f}" top setback — boards follow angled back face; confirm lean on site.',
        'COM / Nelma TBD — mockup colors placeholder only. No mill/SKU on this rev.',
        'DRAFT deliverable — Face-SF figures kept for audit only; bar blanks are the order basis for PATTERN.',
    ]
    formulas = [
        f'U developed = {u.back_outer:.2f}+{u.arm_left:.2f}+{u.arm_right:.2f} = {u.developed_outer_in:.2f}" = {u.developed_outer_lf:.2f} lf',
        f'TILE = {tile:.1f}" LOCKED; BAR = {bar_w_r:.1f}"×{bar_h_r:.1f}" LOCKED; height = {rows}×{tile:.0f}" + {h_left:.2f}" leftover OPEN',
        f'U walk: floor({u.developed_outer_in:.2f}/{tile:.1f}) = {u_full} full tiles × {rows} high + end closer {u_rem:.3f}" -> {u_ec} closer boards; IC {u_ic}',
        f'L walk: floor({L.developed_outer_in:.3f}/{tile:.1f}) = {l_full} full tiles × {rows} high + end closer {l_rem:.3f}" -> {l_ec} closer boards [prov.]',
        f'U STD bars = {u_full}x{rows}x{bars_n} = {u_std}; L STD bars = {l_full}x{rows}x{bars_n} = {l_std}; full-field STD ≈ {u_std + l_std}',
        f'Board total = STD {u_std}+{l_std} + EC {u_ec}+{l_ec} + IC {u_ic} = {board_total} (height leftover NOT in board count — OPEN)',
        f'STD fabric blank/bar = ({bar_w_r:.1f}+2x({foam_t}+{staple})) x ({bar_h_r:.1f}+2x({foam_t}+{staple})) = {fab_blank[0]:.1f}"x{fab_blank[1]:.1f}" = {fab_blank_sf:.4f} sf',
        f'PATTERN fabric SF (blanks) = {pattern_fab_sf:.2f} sf',
        f'PATTERN yards = ({pattern_fab_sf:.2f} x 4 x {waste_fabric:.2f}) / {fabric_width_in:.0f}" = {pat_raw:.2f} -> order {_ceil_quarter(pat_raw):.2f} yd',
        f'U seat blank = ({u.seat_depth:.2f}+2x{wrap:.1f}) x ({u.developed_outer_in:.2f}+2x{wrap:.1f}) / 144 = {u_seat_fab:.2f} sf',
        f'L seat blank = ({L.seat_depth:.1f}+2x{wrap:.1f}) x ({L.developed_outer_in:.3f}+2x{wrap:.1f}) / 144 = {l_seat_fab:.2f} sf [prov.]',
        f'PLAIN yards = ({plain_fab_sf:.2f} x 4 x {waste_fabric:.2f}) / {fabric_width_in:.0f}" = {pln_raw:.2f} -> order {_ceil_quarter(pln_raw):.2f} yd',
        f'Ply = boards {ply_back:.2f} sf + seat decks {ply_seat:.2f} sf = {ply_tot:.2f}; x{waste_ply:.2f} = {ply_w:.2f} sf -> {sheets} sheet(s) 4x8 1/2"',
        f'(Info) face-SF backs {pattern_face:.2f} / seats {plain_face:.2f} — NOT pattern order basis',
    ]

    return MaterialsTakeoff(
        fabric_width_in=fabric_width_in,
        waste_fabric=waste_fabric,
        waste_ply=waste_ply,
        pattern_back_sf=round(pattern_face, 2),
        plain_seat_sf=round(plain_face, 2),
        module_face_in=tile,
        bar_face_in=(bar_w_r, bar_h_r),
        tile_rows=rows,
        height_leftover_in=h_left,
        height_leftover_status="OPEN",
        module_foam_thk_in=foam_t,
        module_staple_in=staple,
        u_full_tiles=u_full,
        u_end_closer_w_in=u_rem,
        u_end_closers=u_ec,
        u_inside_corner_specials=u_ic,
        l_full_tiles=l_full,
        l_end_closer_w_in=l_rem,
        l_end_closers=l_ec,
        u_std_bars=u_std,
        l_std_bars=l_std,
        std_bar_count_total=u_std + l_std,
        board_count_total=board_total,
        u_module_count=u_std + u_ec + u_ic,
        l_module_count=l_std + l_ec,
        module_count_total=board_total,
        module_ply_blank_in=ply_blank,
        module_foam_blank_in=foam_blank,
        module_fabric_blank_in=fab_blank,
        pattern_fabric_sf_blanks=round(pattern_fab_sf, 2),
        pattern_yards_raw=round(pat_raw, 2),
        pattern_yards_order=_ceil_quarter(pat_raw),
        seat_wrap_edge_in=wrap,
        plain_fabric_sf_blanks=round(plain_fab_sf, 2),
        plain_yards_raw=round(pln_raw, 2),
        plain_yards_order=_ceil_quarter(pln_raw),
        ply_back_sf=round(ply_back, 2),
        ply_seat_sf=round(ply_seat, 2),
        ply_total_sf=round(ply_tot, 2),
        ply_with_waste_sf=round(ply_w, 2),
        ply_sheets=sheets,
        modules=modules,
        assumptions=assumptions,
        formulas=formulas,
    )



def _iso(x, y, z, ox, oy, s):
    """3D (x=width, y=depth, z=height) → 2D isometric screen coords."""
    return (
        ox + (x * COS30 - y * COS30) * s,
        oy - (x * SIN30 + y * SIN30) * s - z * s,
    )



def lean_angle_deg(lean_in: float, net_back_h: float) -> float:
    """Back pitch in degrees from vertical: atan(lean / net_back_height).

    Always pass net back height (e.g. U 26.75"), never shell_h − seat_h AFF
    (that understates the hypotenuse and inflates the angle ~14° vs ~6.4°).
    """
    if net_back_h <= 0:
        return 0.0
    return math.degrees(math.atan(lean_in / net_back_h))


def _poly_fill(c, pts, fill, stroke, lw=1.0):
    if len(pts) < 2:
        return
    p = c.beginPath()
    p.moveTo(pts[0][0], pts[0][1])
    for pt in pts[1:]:
        p.lineTo(pt[0], pt[1])
    p.close()
    c.setFillColor(fill)
    c.setStrokeColor(stroke)
    c.setLineWidth(lw)
    c.drawPath(p, fill=1, stroke=1)



def _basketweave_grid(c, x0, y0, x1, y1, tile=10.0):
    """Paint a uniform fabric field with the locked 2-bar H/V seam pattern.

    A tile is always two equal bars (6.5×13 at the locked face scale).  All
    bars share ``PATTERN_BACK``; tile boundaries and the one center seam are
    drawn darker/thicker so the texture reads without a two-tone illusion.
    """
    if x1 <= x0 or y1 <= y0:
        return
    c.setFillColor(PATTERN_BACK)
    c.rect(x0, y0, x1 - x0, y1 - y0, fill=1, stroke=0)
    cols = int((x1 - x0) / tile) + 2
    rows = int((y1 - y0) / tile) + 2
    seam_width = max(1.15, min(2.0, tile * 0.075))
    c.setStrokeColor(PATTERN_BACK_SEAM)
    c.setLineWidth(seam_width)
    c.setLineCap(1)
    for i in range(cols):
        for j in range(rows):
            tx = x0 + i * tile
            ty = y0 + j * tile
            horizontal = ((i + j) % 2 == 0)
            # Tile boundary + the single center seam: exactly two bars/tile.
            c.line(tx, ty, tx + tile, ty)
            c.line(tx, ty, tx, ty + tile)
            if horizontal:
                c.line(tx, ty + tile / 2.0, tx + tile, ty + tile / 2.0)
            else:
                c.line(tx + tile / 2.0, ty, tx + tile / 2.0, ty + tile)


def _basketweave_rect(c, x, y, w, h, tile=10.0):
    """Fill axis-aligned rect with visible basketweave seams (backs)."""
    if w <= 1 or h <= 1:
        return
    c.saveState()
    p = c.beginPath()
    p.rect(x, y, w, h)
    c.clipPath(p, stroke=0, fill=0)
    # Local tile grid from rect origin so pattern aligns on elev/plan.
    _basketweave_grid(c, x, y, x + w, y + h, tile=tile)
    c.restoreState()


def _basketweave_poly(c, pts, tile=10.0):
    """Clip to polygon and paint uniform fabric with 2-bar H/V seams."""
    if len(pts) < 3:
        return
    c.saveState()
    p = c.beginPath()
    p.moveTo(pts[0][0], pts[0][1])
    for pt in pts[1:]:
        p.lineTo(pt[0], pt[1])
    p.close()
    c.clipPath(p, stroke=0, fill=0)
    xs = [pt[0] for pt in pts]
    ys = [pt[1] for pt in pts]
    x0, y0, x1, y1 = min(xs) - 2, min(ys) - 2, max(xs) + 2, max(ys) + 2
    _basketweave_grid(c, x0, y0, x1, y1, tile=tile)
    c.restoreState()


def _title_block(c, w, h, sheet, sheet_title, meta: SheetMeta, total_sheets: int):
    """McLean-ish dense title block: company, job, client, rev, date, sheet X of N."""
    tb_h = 1.05 * inch
    tb_y = 0.28 * inch
    c.setStrokeColor(NAVY)
    c.setLineWidth(1.4)
    c.setFillColor(white)
    c.rect(0.35 * inch, tb_y, w - 0.7 * inch, tb_h, fill=1, stroke=1)
    # Gold accent bar
    c.setFillColor(GOLD)
    c.rect(0.35 * inch, tb_y, 0.14 * inch, tb_h, fill=1, stroke=0)
    # Divider columns
    c.setStrokeColor(MED_GRAY)
    c.setLineWidth(0.5)
    col1 = 3.6 * inch
    col2 = 7.0 * inch
    c.line(col1, tb_y, col1, tb_y + tb_h)
    c.line(col2, tb_y, col2, tb_y + tb_h)

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 10)
    c.drawString(0.6 * inch, tb_y + 0.78 * inch, "EMPIRE WORKROOM")
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY)
    c.drawString(0.6 * inch, tb_y + 0.58 * inch, meta.job[:62])
    c.drawString(0.6 * inch, tb_y + 0.40 * inch, f"Client: {meta.client[:48]}")
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(0.6 * inch, tb_y + 0.18 * inch, "FOR DISCUSSION — NOT FOR CONSTRUCTION")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(col1 + 0.12 * inch, tb_y + 0.78 * inch, sheet_title)
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY)
    c.drawString(col1 + 0.12 * inch, tb_y + 0.55 * inch, meta.note[:58])
    c.drawString(col1 + 0.12 * inch, tb_y + 0.35 * inch, f"Drawn: {meta.drawn_by}")
    c.drawString(col1 + 0.12 * inch, tb_y + 0.18 * inch, f"Rev {meta.rev}  ·  {meta.date_str}")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(w - 0.5 * inch, tb_y + 0.72 * inch, meta.quote_num)
    c.setFont("Helvetica", 8)
    c.setFillColor(GRAY)
    c.drawRightString(w - 0.5 * inch, tb_y + 0.48 * inch, f"Sheet {sheet} of {total_sheets}")
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(CUSH)
    c.drawRightString(w - 0.5 * inch, tb_y + 0.22 * inch, "BASKETWEAVE BACK / PLAIN SEAT")


def _page_header(c, w, h, title, subtitle: str = ""):
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(0.45 * inch, h - 0.38 * inch, title)
    if subtitle:
        c.setFont("Helvetica", 8)
        c.setFillColor(GRAY)
        c.drawString(0.45 * inch, h - 0.55 * inch, subtitle)
        line_y = h - 0.62 * inch
    else:
        line_y = h - 0.48 * inch
    c.setStrokeColor(GOLD)
    c.setLineWidth(2)
    c.line(0.45 * inch, line_y, w - 0.45 * inch, line_y)
    return line_y - 0.15 * inch


def _legend(c, x, y, items):
    """Compact color legend. items = [(color, label), ...]"""
    c.setFont("Helvetica-Bold", 7)
    c.setFillColor(NAVY)
    c.drawString(x, y + 12, "LEGEND")
    yy = y
    for col, lab in items:
        c.setFillColor(col)
        c.rect(x, yy, 10, 8, fill=1, stroke=0)
        c.setStrokeColor(GRAY)
        c.setLineWidth(0.4)
        c.rect(x, yy, 10, 8, fill=0, stroke=1)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 6.5)
        c.drawString(x + 14, yy + 1, lab)
        yy -= 12


def _dim_h(c, x1, x2, y, label, color=GRAY):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(0.6)
    c.line(x1, y, x2, y)
    c.line(x1, y - 4, x1, y + 4)
    c.line(x2, y - 4, x2, y + 4)
    c.setFont("Helvetica", 7)
    c.drawCentredString((x1 + x2) / 2, y + 5, label)


def _dim_v(c, x, y1, y2, label, color=GRAY):
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(0.6)
    c.line(x, y1, x, y2)
    c.line(x - 4, y1, x + 4, y1)
    c.line(x - 4, y2, x + 4, y2)
    c.saveState()
    c.translate(x - 6, (y1 + y2) / 2)
    c.rotate(90)
    c.setFont("Helvetica", 7)
    c.drawCentredString(0, 0, label)
    c.restoreState()


def _draw_u_plan(c, ox, oy, scale, u: UShellSpec, colored: bool = False):
    s = scale
    W, AL, AR, D = u.back_outer, u.arm_left, u.arm_right, u.seat_depth

    def sx(x):
        return ox + x * s

    def sy(y_from_back):
        return oy - y_from_back * s

    # Shell band
    shell_fill = LT_BLUE if not colored else HexColor("#a0aec0")
    c.setFillColor(shell_fill)
    path = c.beginPath()
    path.moveTo(sx(0), sy(AL))
    path.lineTo(sx(0), sy(0))
    path.lineTo(sx(W), sy(0))
    path.lineTo(sx(W), sy(AR))
    path.lineTo(sx(W - D), sy(AR))
    path.lineTo(sx(W - D), sy(D))
    path.lineTo(sx(D), sy(D))
    path.lineTo(sx(D), sy(AL))
    path.close()
    c.drawPath(path, fill=1, stroke=0)

    if colored:
        # Pattern back band — visible basketweave (match Sep 2022 / bar tile)
        back_pts = [
            (sx(0), sy(AL)), (sx(0), sy(0)), (sx(W), sy(0)), (sx(W), sy(AR)),
            (sx(W - 2), sy(AR)), (sx(W - 2), sy(2)), (sx(2), sy(2)), (sx(2), sy(AL)),
        ]
        _basketweave_poly(c, back_pts, tile=8.5)
        # Plain seat footprint (flat / solid — no weave)
        c.setFillColor(PLAIN_SEAT)
        sp = c.beginPath()
        sp.moveTo(sx(2), sy(AL))
        sp.lineTo(sx(2), sy(D))
        sp.lineTo(sx(W - 2), sy(D))
        sp.lineTo(sx(W - 2), sy(AR))
        sp.lineTo(sx(W - D), sy(AR))
        sp.lineTo(sx(W - D), sy(D))
        sp.lineTo(sx(D), sy(D))
        sp.lineTo(sx(D), sy(AL))
        sp.close()
        c.drawPath(sp, fill=1, stroke=0)

    c.setStrokeColor(SHELL)
    c.setLineWidth(1.8)
    c.line(sx(0), sy(AL), sx(0), sy(0))
    c.line(sx(0), sy(0), sx(W), sy(0))
    c.line(sx(W), sy(0), sx(W), sy(AR))

    c.setStrokeColor(CUSH if not colored else PLAIN_SEAT_DK)
    c.setLineWidth(1.2)
    c.setDash(4, 3)
    c.line(sx(D), sy(AL), sx(D), sy(D))
    c.line(sx(D), sy(D), sx(W - D), sy(D))
    c.line(sx(W - D), sy(D), sx(W - D), sy(AR))
    c.setDash()

    c.setStrokeColor(GRAY)
    c.setDash(2, 2)
    c.line(sx(0), sy(AL), sx(D), sy(AL))
    c.line(sx(W - D), sy(AR), sx(W), sy(AR))
    c.setDash()

    _dim_h(c, sx(0), sx(W), sy(0) + 14, f'{W:.2f}" back outer')
    _dim_v(c, sx(0) - 14, sy(0), sy(AL), f'{AL:.2f}" L arm')
    _dim_v(c, sx(W) + 14, sy(0), sy(AR), f'{AR:.2f}" R arm')
    _dim_h(c, sx(0), sx(D), sy(D) - 12, f'{D:.2f}" seat', CUSH)

    c.setFillColor(SHELL)
    c.setFont("Helvetica-Bold", 8)
    c.drawCentredString(sx(W / 2), sy(D / 2) - 4, "SHELL / WALL")
    if colored:
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(sx(W / 2), sy(4), "BASKETWEAVE BACK")
        c.setFont("Helvetica", 6)
        c.drawCentredString(sx(W / 2), sy(8), "to match Sep 2022 / bar tile")
        c.setFillColor(HexColor("#aaaaaa"))
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(sx(W / 2), sy(min(AL, AR) * 0.55 + D), "PLAIN SEAT")
    else:
        c.setFillColor(CUSH)
        c.drawCentredString(sx(W / 2), sy(min(AL, AR) * 0.55 + D), "SEAT CUSHION FOOTPRINT")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 7)
    c.drawString(sx(D) + 4, sy(AL) - 10, "miter @ corners")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(
        sx(0), sy(max(AL, AR)) - 28,
        f'Developed outer run (upholstery): {u.developed_outer_in:.2f}" = '
        f'{u.developed_outer_lf:.2f} lf   (back {W:.2f} + L {AL:.2f} + R {AR:.2f})',
    )
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY)
    c.drawString(
        sx(0), sy(max(AL, AR)) - 40,
        f'Booth footprint width (plan): {u.footprint_width:.2f}" = back + 2×seat_depth — NOT the lf takeoff.',
    )


def _draw_u_elev(c, ox, oy, scale_h, width_pts, u: UShellSpec, colored: bool = False):
    """SIDE elevation — Rafael video dim chain.

    Dims (required): overall H, overall D, seat H AFF, seat depth, lean.
    Foam is a distinct material callout — NEVER drawn/labeled as seat H.
    Seat plane at seat_height AFF; back rises from seat plane to shell top with lean.
    """
    s = scale_h
    H = u.shell_height
    seat_h = u.seat_height
    foam = u.seat_foam
    lean = u.back_lean_in
    depth = u.seat_depth
    bt = min(3.0, depth * 0.18)  # schematic back thickness
    overall_d = depth + bt
    ang = lean_angle_deg(lean, max(0.1, H - seat_h))

    # Fit depth+lean into ~92% of width_pts; height uses scale_h
    ds = (width_pts * 0.92) / (overall_d + lean + 4)
    # Prefer shared visual scale: use min so both axes fit
    Hs = H * s
    # If height scale makes depth too wide, shrink both
    if overall_d * s + lean * s + 20 > width_pts:
        s = (width_pts * 0.90) / (overall_d + lean + 2)
        Hs = H * s
    ds = s
    Ds = depth * ds
    BTs = bt * ds
    Ls = lean * ds
    seatHs = seat_h * s
    foams = foam * s
    wall_x = ox + Ds + BTs + Ls + 6
    floor_y = oy
    front_x = wall_x - BTs - Ds

    # Shell / wall band (against wall, full H)
    c.setFillColor(LT_BLUE)
    c.setStrokeColor(SHELL)
    c.setLineWidth(1.4)
    c.rect(front_x - 4, floor_y, (wall_x + 4) - (front_x - 4), Hs, fill=1, stroke=1)

    # Seat volume — closed face from floor to seat H AFF (plain)
    seat_fill = PLAIN_SEAT if colored else LT_FOAM
    c.setFillColor(seat_fill)
    c.setStrokeColor(PLAIN_SEAT_DK if colored else CUSH)
    c.setLineWidth(1.1)
    c.rect(front_x, floor_y, Ds, seatHs, fill=1, stroke=1)
    # Foam band at top of seat (mat'l thickness only — not the AFF dim)
    foam_y0 = floor_y + max(0.0, seatHs - foams)
    c.setFillColor(LT_FOAM if not colored else HexColor("#3a3a3a"))
    c.setStrokeColor(CUSH)
    c.setLineWidth(0.7)
    c.rect(front_x, foam_y0, Ds, foams, fill=1, stroke=1)

    # Leaning back — from seat plane to shell top
    bf_x = wall_x - BTs          # bottom front (at seat rear)
    bb_x = wall_x                # bottom back (wall)
    tf_x = wall_x - BTs + Ls     # top front (leaned toward wall)
    tb_x = wall_x + Ls * 0.12
    z0 = floor_y + seatHs
    z1 = floor_y + Hs
    back_pts = [(bf_x, z0), (bb_x, z0), (tb_x, z1), (tf_x, z1)]
    if colored:
        _basketweave_poly(c, back_pts, tile=8.5)
        c.setStrokeColor(PATTERN_BACK_DK)
    else:
        c.setFillColor(LT_PEACH)
        p = c.beginPath()
        p.moveTo(*back_pts[0])
        for pt in back_pts[1:]:
            p.lineTo(*pt)
        p.close()
        c.setStrokeColor(CUSH)
        c.drawPath(p, fill=1, stroke=1)
        c.setStrokeColor(CUSH)
    c.setLineWidth(1.2)
    p = c.beginPath()
    p.moveTo(*back_pts[0])
    for pt in back_pts[1:]:
        p.lineTo(*pt)
    p.close()
    c.drawPath(p, fill=0, stroke=1)

    # Lean guide
    c.setStrokeColor(PROV)
    c.setDash(3, 2)
    c.setLineWidth(0.8)
    c.line(bf_x, z0, bf_x, z1)
    c.setDash()
    c.setLineWidth(1.0)
    c.line(bf_x, z1 + 6, tf_x, z1 + 6)
    c.line(bf_x, z1 + 3, bf_x, z1 + 9)
    c.line(tf_x, z1 + 3, tf_x, z1 + 9)
    c.setFillColor(PROV)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawCentredString((bf_x + tf_x) / 2, z1 + 12, f'lean {lean:.1f}" PROV')
    c.setFont("Helvetica", 6.5)
    c.drawCentredString((bf_x + tf_x) / 2, z1 + 22, f'≈ {ang:.1f}° from vertical')

    # ── Video dim chain (SIDE) ─────────────────────────────────────
    # overall H
    _dim_v(c, front_x - 22, floor_y, floor_y + Hs, f'{H:.2f}" overall H')
    # seat H AFF (PROV) — NOT foam
    _dim_v(c, front_x - 8, floor_y, floor_y + seatHs, f'{seat_h:.1f}" seat H AFF PROV', PROV)
    # seat depth
    _dim_h(c, front_x, front_x + Ds, floor_y - 12, f'{depth:.2f}" seat depth')
    # overall D
    _dim_h(c, front_x, wall_x, floor_y - 26, f'{overall_d:.1f}" overall D')
    # foam mat'l callout (distinct)
    c.setFillColor(CUSH)
    c.setFont("Helvetica", 6.5)
    c.drawString(front_x + 3, foam_y0 + foams / 2 - 2, f'foam {foam:.1f}" mat\'l (≠ seat H)')

    # Labels
    if colored:
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 7.5)
        mid_x = (bf_x + tf_x + bb_x + tb_x) / 4
        mid_y = (z0 + z1) / 2
        c.drawCentredString(mid_x, mid_y + 4, "BASKETWEAVE")
        c.setFont("Helvetica", 6)
        c.drawCentredString(mid_x, mid_y - 6, "angled BACK")
        c.setFillColor(HexColor("#bbbbbb"))
        c.setFont("Helvetica-Bold", 7)
        c.drawCentredString(front_x + Ds / 2, floor_y + seatHs * 0.45, "PLAIN SEAT")
    else:
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 7)
        c.drawString(front_x + 4, floor_y + seatHs * 0.4, "seat (plain)")
        c.drawString(bf_x + 4, z0 + (z1 - z0) * 0.55, "back (leans)")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(ox, floor_y + Hs + 28, "SIDE — VIDEO DIM CHAIN")
    c.setFont("Helvetica", 6.5)
    c.setFillColor(PROV)
    c.drawString(
        ox, floor_y + Hs + 16,
        f'H {H:.2f}" · D {overall_d:.1f}" · seat H {seat_h:.1f}" AFF PROV · seat depth {depth:.2f}" · lean {lean:.1f}" PROV · foam {foam:.1f}" mat\'l',
    )
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 6)
    c.drawString(
        ox, floor_y + Hs + 6,
        f'Net back cushion order H {u.net_back_height:.2f}" (materials). Visible face above seat ≈ {H - seat_h:.2f}". Confirm lean on site.',
    )


def _draw_u_front(c, ox, oy, scale_h, width_pts, u: UShellSpec, colored: bool = False):
    """FRONT face view — pattern on back / plain seat. Readable across back run."""
    s = scale_h
    H = u.shell_height
    seat_h = u.seat_height
    foam = u.seat_foam
    W = u.back_outer
    # Fit width into width_pts
    ws = width_pts / W
    # Height scale independent; clamp so Hs fits reasonably
    Hs = H * s
    if Hs > 5.2 * inch:
        s = (5.2 * inch) / H
        Hs = H * s
    seatHs = seat_h * s
    foams = foam * s
    Ws = W * ws
    floor_y = oy
    x0 = ox

    # Shell outline
    c.setFillColor(LT_BLUE)
    c.setStrokeColor(SHELL)
    c.setLineWidth(1.3)
    c.rect(x0, floor_y, Ws, Hs, fill=1, stroke=1)

    # Plain seat band (floor to seat H)
    seat_fill = PLAIN_SEAT if colored else LT_FOAM
    c.setFillColor(seat_fill)
    c.setStrokeColor(PLAIN_SEAT_DK if colored else CUSH)
    c.rect(x0 + 2, floor_y, Ws - 4, seatHs, fill=1, stroke=1)
    # Foam mat'l band at seat top
    c.setFillColor(LT_FOAM if not colored else HexColor("#3a3a3a"))
    c.setStrokeColor(CUSH)
    c.setLineWidth(0.6)
    c.rect(x0 + 2, floor_y + seatHs - foams, Ws - 4, foams, fill=1, stroke=1)

    # Pattern back face (seat plane to shell top)
    back_h = Hs - seatHs
    if colored:
        _basketweave_rect(c, x0 + 2, floor_y + seatHs, Ws - 4, back_h, tile=max(5.0, back_h * (13.0 / 26.75)))
        c.setStrokeColor(PATTERN_BACK_DK)
        c.setLineWidth(1.0)
        c.rect(x0 + 2, floor_y + seatHs, Ws - 4, back_h, fill=0, stroke=1)
    else:
        c.setFillColor(LT_PEACH)
        c.setStrokeColor(CUSH)
        c.rect(x0 + 2, floor_y + seatHs, Ws - 4, back_h, fill=1, stroke=1)

    # Arm end marks (asymmetric callouts)
    c.setStrokeColor(SHELL)
    c.setDash(2, 2)
    c.setLineWidth(0.7)
    # indicate wings as tick marks at ends
    c.line(x0, floor_y + Hs + 4, x0, floor_y + Hs + 14)
    c.line(x0 + Ws, floor_y + Hs + 4, x0 + Ws, floor_y + Hs + 14)
    c.setDash()

    # Dims
    _dim_h(c, x0, x0 + Ws, floor_y + Hs + 18, f'{W:.2f}" back outer (FRONT)')
    _dim_v(c, x0 - 16, floor_y, floor_y + Hs, f'{H:.2f}" overall H')
    _dim_v(c, x0 + Ws + 12, floor_y, floor_y + seatHs, f'{seat_h:.1f}" seat H AFF PROV', PROV)

    # Labels
    if colored:
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 9)
        c.drawCentredString(x0 + Ws / 2, floor_y + seatHs + back_h * 0.55, "BASKETWEAVE BACK")
        c.setFont("Helvetica", 7)
        c.drawCentredString(x0 + Ws / 2, floor_y + seatHs + back_h * 0.40, "bar 6.5×13 / tile 13×13 · Sep 2022 match")
        c.setFillColor(HexColor("#bbbbbb"))
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x0 + Ws / 2, floor_y + seatHs * 0.42, "PLAIN SEAT")
    else:
        c.setFillColor(GRAY)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(x0 + Ws / 2, floor_y + seatHs + back_h * 0.5, "PATTERN BACK")
        c.drawCentredString(x0 + Ws / 2, floor_y + seatHs * 0.4, "PLAIN SEAT")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x0, floor_y + Hs + 36, "FRONT — FACE VIEW (pattern on back / plain seat)")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 6.5)
    c.drawString(
        x0, floor_y + Hs + 26,
        f'Arms asymmetric L {u.arm_left:.2f}" / R {u.arm_right:.2f}" (shown in TOP). Foam {foam:.1f}" mat\'l ≠ seat H. Lean shown in SIDE.',
    )


def _draw_l_side(c, ox, oy, scale_h, width_pts, L: LShellSpec, colored: bool = False):
    """L SIDE elevation — same video dim chain as U (provisional)."""
    # Reuse U side geometry via a thin adapter
    u_like = UShellSpec(
        back_outer=L.leg_long,
        arm_left=L.leg_short,
        arm_right=L.leg_short,
        seat_depth=L.seat_depth,
        shell_height=L.shell_height,
        net_back_height=L.net_back,
        seat_height=L.seat_height,
        seat_foam=L.seat_foam,
        back_lean_in=L.back_lean_in,
    )
    _draw_u_elev(c, ox, oy, scale_h, width_pts, u_like, colored=colored)
    c.setFillColor(PROV)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(ox, oy - 42, f'L PROVISIONAL — depth {L.seat_depth:.1f}" / H {L.shell_height:.1f}" / seat H {L.seat_height:.1f}" AFF — lock to U before fab')


def _draw_l_front(c, ox, oy, scale_h, width_pts, L: LShellSpec, colored: bool = False):
    """L FRONT — long-leg face (pattern back / plain seat), provisional."""
    u_like = UShellSpec(
        back_outer=L.leg_long,
        arm_left=L.leg_short,
        arm_right=L.leg_short,
        seat_depth=L.seat_depth,
        shell_height=L.shell_height,
        net_back_height=L.net_back,
        seat_height=L.seat_height,
        seat_foam=L.seat_foam,
        back_lean_in=L.back_lean_in,
    )
    _draw_u_front(c, ox, oy, scale_h, width_pts, u_like, colored=colored)
    c.setFillColor(PROV)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(ox, oy - 42, f'L FRONT along long leg {L.leg_long:.3f}" — PROVISIONAL; short leg {L.leg_short:.3f}" in TOP')


def _draw_l_plan(c, ox, oy, scale, L: LShellSpec, colored: bool = False):
    s = scale
    A, B, D = L.leg_short, L.leg_long, L.seat_depth

    def sx(x):
        return ox + x * s

    def sy(y):
        return oy - y * s

    outer = [(0, 0), (B, 0), (B, D), (D, D), (D, A), (0, A)]
    outer_pts = [(sx(p[0]), sy(p[1])) for p in outer]
    c.setStrokeColor(SHELL)
    c.setLineWidth(1.8)
    if colored:
        _basketweave_poly(c, outer_pts, tile=8.5)
        path = c.beginPath()
        path.moveTo(outer_pts[0][0], outer_pts[0][1])
        for p in outer_pts[1:]:
            path.lineTo(p[0], p[1])
        path.close()
        c.drawPath(path, fill=0, stroke=1)
    else:
        c.setFillColor(LT_BLUE)
        path = c.beginPath()
        path.moveTo(sx(0), sy(0))
        for p in outer[1:]:
            path.lineTo(sx(p[0]), sy(p[1]))
        path.close()
        c.drawPath(path, fill=1, stroke=1)

    if colored:
        c.setFillColor(PLAIN_SEAT)
        # Seat band inset by ~nothing — show seat footprint region
        c.setStrokeColor(PLAIN_SEAT_DK)
        c.setLineWidth(1.0)
        # Fill approximate seat zone
        sp = c.beginPath()
        sp.moveTo(sx(1), sy(1))
        sp.lineTo(sx(B - 1), sy(1))
        sp.lineTo(sx(B - 1), sy(D - 1))
        sp.lineTo(sx(D - 1), sy(D - 1))
        sp.lineTo(sx(D - 1), sy(A - 1))
        sp.lineTo(sx(1), sy(A - 1))
        sp.close()
        c.drawPath(sp, fill=1, stroke=0)

    c.setStrokeColor(CUSH if not colored else PLAIN_SEAT_DK)
    c.setLineWidth(1.2)
    c.setDash(4, 3)
    c.line(sx(D), sy(D), sx(B - D), sy(D))
    c.line(sx(D), sy(D), sx(D), sy(A - D))
    c.setDash()

    _dim_h(c, sx(0), sx(B), sy(0) + 14, f'{B:.3f}" long leg')
    _dim_v(c, sx(0) - 14, sy(0), sy(A), f'{A:.3f}" short leg')
    _dim_h(c, sx(B - D), sx(B), sy(D / 2), f'{D:.1f}"', PROV)

    c.setFillColor(PROV)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(sx(B / 3), sy(A / 2), "L DEPTH / HEIGHT PROVISIONAL")
    if colored:
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawCentredString(sx(B / 2), sy(D / 2) + 4, "BASKETWEAVE BACK")
        c.setFont("Helvetica", 6)
        c.drawCentredString(sx(B / 2), sy(D / 2) - 6, "to match Sep 2022 / bar tile")
        c.setFillColor(HexColor("#bbbbbb"))
        c.setFont("Helvetica-Bold", 8)
        c.drawString(sx(D) + 6, sy(D) + 8, "PLAIN SEAT")
    else:
        c.setFillColor(SHELL)
        c.setFont("Helvetica-Bold", 8)
        c.drawCentredString(sx(B / 2), sy(D / 2) - 2, "SHELL")
        c.setFillColor(CUSH)
        c.drawString(sx(D) + 6, sy(D) + 8, "seat footprint")

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(
        sx(0), sy(A) - 22,
        f'Developed outer run: {L.developed_outer_in:.3f}" = {L.developed_outer_lf:.2f} lf',
    )


def _draw_box_iso(c, ox, oy, s, sx, sy, w, d, z0, z1, fill, stroke, lw=1.0, hatch=False):
    """Draw a rectangular prism in isometric from z0 to z1.
    hatch=True → basketweave on front+top (PATTERN BACK cushions).
    """
    # Top face
    top = [
        _iso(sx, sy, z1, ox, oy, s),
        _iso(sx + w, sy, z1, ox, oy, s),
        _iso(sx + w, sy + d, z1, ox, oy, s),
        _iso(sx, sy + d, z1, ox, oy, s),
    ]
    # Front face (low y)
    front = [
        _iso(sx, sy, z0, ox, oy, s),
        _iso(sx + w, sy, z0, ox, oy, s),
        _iso(sx + w, sy, z1, ox, oy, s),
        _iso(sx, sy, z1, ox, oy, s),
    ]
    # Right face
    right = [
        _iso(sx + w, sy, z0, ox, oy, s),
        _iso(sx + w, sy + d, z0, ox, oy, s),
        _iso(sx + w, sy + d, z1, ox, oy, s),
        _iso(sx + w, sy, z1, ox, oy, s),
    ]
    # Draw back-to-front-ish: right, front, top
    right_fill = Color(fill.red * 0.85, fill.green * 0.85, fill.blue * 0.85)
    top_fill = Color(min(1, fill.red * 1.12), min(1, fill.green * 1.12), min(1, fill.blue * 1.12))
    _poly_fill(c, right, right_fill, stroke, lw)
    if hatch:
        _basketweave_poly(c, front, tile=11.0)
        c.setStrokeColor(stroke)
        c.setLineWidth(lw)
        p = c.beginPath()
        p.moveTo(front[0][0], front[0][1])
        for pt in front[1:]:
            p.lineTo(pt[0], pt[1])
        p.close()
        c.drawPath(p, fill=0, stroke=1)
        _basketweave_poly(c, top, tile=11.0)
        p = c.beginPath()
        p.moveTo(top[0][0], top[0][1])
        for pt in top[1:]:
            p.lineTo(pt[0], pt[1])
        p.close()
        c.drawPath(p, fill=0, stroke=1)
        # Keep every basketweave face on the same fabric fill; seams provide
        # the texture and the outline provides the edge definition.
        _poly_fill(c, right, PATTERN_BACK, stroke, lw)
    else:
        _poly_fill(c, front, fill, stroke, lw)
        _poly_fill(c, top, top_fill, stroke, lw)



def _draw_lean_box_iso(
    c, ox, oy, s, sx, sy, w, d, z0, z1, fill, stroke,
    lean_in=0.0, lean_axis="y", lw=1.0, hatch=False,
):
    """Isometric prism with top face shifted by lean_in along lean_axis toward wall.

    lean_axis 'y' → center/back runs (thickness along +y / wall).
    lean_axis 'x-' → left arm back (wall at low x; lean shifts top toward -x).
    lean_axis 'x+' → right arm back (wall at high x; lean shifts top toward +x).
    """
    if lean_axis == "y":
        dx0 = dy0 = 0.0
        dxt, dyt = 0.0, lean_in
    elif lean_axis == "x-":
        dx0 = dy0 = 0.0
        dxt, dyt = -lean_in, 0.0
    else:  # x+
        dx0 = dy0 = 0.0
        dxt, dyt = lean_in, 0.0

    # Bottom face corners (z0), top face corners (z1) shifted
    # Order: front-left, front-right, back-right, back-left in local sx/sy
    # front = low y, back = high y; left = low x, right = high x
    b_fl = _iso(sx + dx0, sy + dy0, z0, ox, oy, s)
    b_fr = _iso(sx + w + dx0, sy + dy0, z0, ox, oy, s)
    b_br = _iso(sx + w + dx0, sy + d + dy0, z0, ox, oy, s)
    b_bl = _iso(sx + dx0, sy + d + dy0, z0, ox, oy, s)
    t_fl = _iso(sx + dxt, sy + dyt, z1, ox, oy, s)
    t_fr = _iso(sx + w + dxt, sy + dyt, z1, ox, oy, s)
    t_br = _iso(sx + w + dxt, sy + d + dyt, z1, ox, oy, s)
    t_bl = _iso(sx + dxt, sy + d + dyt, z1, ox, oy, s)

    top = [t_fl, t_fr, t_br, t_bl]
    # Front face (low y): b_fl, b_fr, t_fr, t_fl
    front = [b_fl, b_fr, t_fr, t_fl]
    # Right face (high x): b_fr, b_br, t_br, t_fr
    right = [b_fr, b_br, t_br, t_fr]

    right_fill = Color(fill.red * 0.85, fill.green * 0.85, fill.blue * 0.85)
    top_fill = Color(min(1, fill.red * 1.12), min(1, fill.green * 1.12), min(1, fill.blue * 1.12))
    _poly_fill(c, right, right_fill if not hatch else PATTERN_BACK, stroke, lw)
    if hatch:
        _basketweave_poly(c, front, tile=11.0)
        c.setStrokeColor(stroke)
        c.setLineWidth(lw)
        p = c.beginPath()
        p.moveTo(front[0][0], front[0][1])
        for pt in front[1:]:
            p.lineTo(pt[0], pt[1])
        p.close()
        c.drawPath(p, fill=0, stroke=1)
        _basketweave_poly(c, top, tile=11.0)
        p = c.beginPath()
        p.moveTo(top[0][0], top[0][1])
        for pt in top[1:]:
            p.lineTo(pt[0], pt[1])
        p.close()
        c.drawPath(p, fill=0, stroke=1)
    else:
        _poly_fill(c, front, fill, stroke, lw)
        _poly_fill(c, top, top_fill, stroke, lw)



def _iso_dim(c, p1, p2, label, color=GRAY, tick=4.5, offset=10.0, font_size=6.5, bold=False):
    """Dimension arrow ON an iso edge. Short shop label; white halo so text stays readable."""
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1.0
    ux, uy = dx / length, dy / length
    # perpendicular (screen)
    px, py = -uy, ux
    # offset both ends along normal
    a1 = (x1 + px * offset, y1 + py * offset)
    a2 = (x2 + px * offset, y2 + py * offset)
    c.setStrokeColor(color)
    c.setFillColor(color)
    c.setLineWidth(0.7)
    c.line(a1[0], a1[1], a2[0], a2[1])
    # end ticks
    for ax, ay in (a1, a2):
        c.line(ax - ux * 0 + px * (-tick / 2), ay - uy * 0 + py * (-tick / 2),
               ax + px * (tick / 2), ay + py * (tick / 2))
    # small arrow heads
    ah = 3.5
    for (ax, ay), sgn in ((a1, 1), (a2, -1)):
        c.line(ax, ay, ax + sgn * ux * ah + px * 2, ay + sgn * uy * ah + py * 2)
        c.line(ax, ay, ax + sgn * ux * ah - px * 2, ay + sgn * uy * ah - py * 2)
    mx, my = (a1[0] + a2[0]) / 2 + px * 3, (a1[1] + a2[1]) / 2 + py * 3
    # white halo behind label — kills overlap-on-geometry clutter
    c.setFont("Helvetica-Bold" if bold else "Helvetica", font_size)
    tw = c.stringWidth(label, "Helvetica-Bold" if bold else "Helvetica", font_size)
    c.setFillColor(white)
    c.setStrokeColor(white)
    c.rect(mx - tw / 2 - 1.5, my - 1.5, tw + 3, font_size + 2, fill=1, stroke=0)
    c.setFillColor(color)
    c.drawCentredString(mx, my, label)


def _iso_poly(c, pts3, ox, oy, s, fill, stroke, lw=1.0, hatch=False):
    """Project list of (x,y,z) through _iso and fill/stroke; optional basketweave."""
    pts = [_iso(x, y, z, ox, oy, s) for x, y, z in pts3]
    if hatch:
        _basketweave_poly(c, pts, tile=11.0)
        c.setStrokeColor(stroke)
        c.setLineWidth(lw)
        p = c.beginPath()
        p.moveTo(pts[0][0], pts[0][1])
        for pt in pts[1:]:
            p.lineTo(pt[0], pt[1])
        p.close()
        c.drawPath(p, fill=0, stroke=1)
    else:
        _poly_fill(c, pts, fill, stroke, lw)
    return pts


def _auto_iso_scale(dims, area_w, area_h, margin=40):
    mx, my, mz = dims
    corners = [_iso(x, y, z, 0, 0, 1) for x in (0, mx) for y in (0, my) for z in (0, mz)]
    xs = [p[0] for p in corners]
    ys = [p[1] for p in corners]
    raw_w = max(xs) - min(xs) or 1
    raw_h = max(ys) - min(ys) or 1
    scale = min((area_w - margin * 2) / raw_w, (area_h - margin * 2) / raw_h)
    corners2 = [_iso(x, y, z, 0, 0, scale) for x in (0, mx) for y in (0, my) for z in (0, mz)]
    xs2 = [p[0] for p in corners2]
    ys2 = [p[1] for p in corners2]
    ox = area_w / 2 - (min(xs2) + max(xs2)) / 2
    oy = area_h / 2 - (min(ys2) + max(ys2)) / 2 + margin / 2
    return scale, ox, oy


def _draw_u_iso(c, origin_x, origin_y, area_w, area_h, u: UShellSpec, colored: bool = True):
    """Closed-face U isometric — constructive dim chains (Rafael book standard).

    Plan/run chain: OUTER + INNER + seat DEPTH → closes seat plane & back widths.
    Section chain: shell H + overall D + seat H AFF + lean + foam(mat'l) as DISTINCT dims.
    Seat H is AFF plane height (PROV ~18"), NEVER foam thickness.
    Dim arrows sit ON the edges they define; shop labels stay short (no overlap).
    """
    AL, AR, D = u.arm_left, u.arm_right, u.seat_depth
    W = u.back_outer
    lean = u.back_lean_in
    seat_h = u.seat_height          # AFF — closes seat plane from floor
    foam = u.seat_foam              # material only — NOT seat H
    shell_h = u.shell_height
    side_max = max(AL, AR)
    total_w = W + 2 * D
    left_y0 = side_max - AL
    right_y0 = side_max - AR
    # visual back board thickness (kept thin — geometry is closed faces, not fake fat cushions)
    bt = min(2.0, D * 0.12)
    # back top = shell top; visible back above seat = shell_h - seat_h (AFF geometry)
    z_seat = seat_h
    z_top = shell_h

    scale, ox, oy = _auto_iso_scale((total_w, side_max, shell_h), area_w, area_h, margin=56)
    ox += origin_x
    oy += origin_y

    seat_fill = PLAIN_SEAT if colored else LT_FOAM
    back_fill = PATTERN_BACK if colored else LT_PEACH
    stroke = NAVY
    apron_fill = Color(seat_fill.red * 0.82, seat_fill.green * 0.82, seat_fill.blue * 0.82)

    def P(x, y, z):
        return _iso(x, y, z, ox, oy, scale)

    # ── SEAT TOP (closes seat plane): outer U then reverse along inner front ──
    seat_outer = [
        (0, left_y0, z_seat),
        (0, side_max, z_seat),
        (total_w, side_max, z_seat),
        (total_w, right_y0, z_seat),
        (total_w - D, right_y0, z_seat),
        (total_w - D, side_max - D, z_seat),
        (D, side_max - D, z_seat),
        (D, left_y0, z_seat),
    ]
    _iso_poly(c, seat_outer, ox, oy, scale, seat_fill, stroke, lw=1.1)

    # ── SEAT FRONT APRONS (vertical faces under seat plane — close seat front) ──
    z0 = 0.0
    _iso_poly(c, [
        (D, left_y0, z0), (D, side_max - D, z0),
        (D, side_max - D, z_seat), (D, left_y0, z_seat),
    ], ox, oy, scale, apron_fill, stroke, lw=0.8)
    _iso_poly(c, [
        (D, side_max - D, z0), (total_w - D, side_max - D, z0),
        (total_w - D, side_max - D, z_seat), (D, side_max - D, z_seat),
    ], ox, oy, scale, apron_fill, stroke, lw=0.8)
    _iso_poly(c, [
        (total_w - D, right_y0, z0), (total_w - D, side_max - D, z0),
        (total_w - D, side_max - D, z_seat), (total_w - D, right_y0, z_seat),
    ], ox, oy, scale, apron_fill, stroke, lw=0.8)

    # ── BACK FACES (leaned) — outer run closes each back plane width ──
    # LEFT back (wall at x=0; lean toward -x / wall)
    _iso_poly(c, [
        (bt, left_y0, z_seat),
        (bt, side_max, z_seat),
        (bt - lean, side_max, z_top),
        (bt - lean, left_y0, z_top),
    ], ox, oy, scale, back_fill, stroke, lw=1.0, hatch=colored)
    # CENTER back (wall at y=side_max; lean toward +y / wall)
    _iso_poly(c, [
        (D, side_max - bt, z_seat),
        (D + W, side_max - bt, z_seat),
        (D + W, side_max - bt + lean, z_top),
        (D, side_max - bt + lean, z_top),
    ], ox, oy, scale, back_fill, stroke, lw=1.0, hatch=colored)
    # RIGHT back (wall at x=total_w; lean toward +x / wall)
    _iso_poly(c, [
        (total_w - bt, right_y0, z_seat),
        (total_w - bt, side_max, z_seat),
        (total_w - bt + lean, side_max, z_top),
        (total_w - bt + lean, right_y0, z_top),
    ], ox, oy, scale, back_fill, stroke, lw=1.0, hatch=colored)

    # ── ARM END FACES (section silhouettes) ──
    left_section = [
        (0, left_y0, 0),
        (D, left_y0, 0),
        (D, left_y0, z_seat),
        (bt, left_y0, z_seat),
        (bt - lean, left_y0, z_top),
        (0, left_y0, shell_h),
    ]
    _iso_poly(c, left_section, ox, oy, scale,
              Color(0.75, 0.80, 0.88) if not colored else Color(0.55, 0.58, 0.62),
              stroke, lw=1.15)
    right_section = [
        (total_w, right_y0, 0),
        (total_w - D, right_y0, 0),
        (total_w - D, right_y0, z_seat),
        (total_w - bt, right_y0, z_seat),
        (total_w - bt + lean, right_y0, z_top),
        (total_w, right_y0, shell_h),
    ]
    _iso_poly(c, right_section, ox, oy, scale,
              Color(0.75, 0.80, 0.88) if not colored else Color(0.55, 0.58, 0.62),
              stroke, lw=1.15)

    # ── PLAN / RUN DIMS — short shop labels on edges (no "closes …" clutter) ──
    _iso_dim(c, P(bt - lean, left_y0, z_top), P(bt - lean, side_max, z_top),
             f'OUTER L {AL:.2f}"', NAVY, offset=14, bold=True, font_size=6.5)
    # OUTER back on top edge. Offset NEGATIVE: +offset collided with INNER (higher-z
    # edge sits lower on screen; +perp pulled OUTER up into INNER).
    _iso_dim(c, P(D, side_max - bt + lean, z_top), P(D + W, side_max - bt + lean, z_top),
             f'OUTER {W:.2f}"', NAVY, offset=-22, bold=True, font_size=6.5)
    # OUTER R / INNER R: dim the BACK half of the arm so labels stay clear of tip section stack
    _iso_dim(c, P(total_w - bt + lean, right_y0 + AR * 0.45, z_top), P(total_w - bt + lean, side_max, z_top),
             f'OUTER R {AR:.2f}"', NAVY, offset=-18, bold=True, font_size=6.5)

    _iso_dim(c, P(D, left_y0, z_seat), P(D, side_max - D, z_seat),
             f'INNER L {u.inner_arm_left:.2f}"', GRAY, offset=-13, font_size=6)
    # INNER back = outer − 2×seat_depth (clear span). Offset POSITIVE away from OUTER.
    _iso_dim(c, P(D + D, side_max - D, z_seat), P(total_w - 2 * D, side_max - D, z_seat),
             f'INNER {u.inner_back:.2f}"', GRAY, offset=18, font_size=6)
    _iso_dim(c, P(total_w - D, right_y0 + u.inner_arm_right * 0.45, z_seat),
             P(total_w - D, side_max - D, z_seat),
             f'INNER R {u.inner_arm_right:.2f}"', GRAY, offset=15, font_size=6)

    # DEPTH once on center left corner (avoid right-tip clash with section D)
    _iso_dim(c, P(0, side_max, z_seat), P(D, side_max - D, z_seat),
             f'DEPTH {D:.2f}"', CUSH, offset=18, font_size=6.5, bold=True)

    # ── SECTION CHAIN on RIGHT end — five DISTINCT dims, fanned offsets ──
    # shell H (wall edge, outward)
    _iso_dim(c, P(total_w, right_y0, 0), P(total_w, right_y0, shell_h),
             f'H {shell_h:.2f}"', PROV, offset=22, bold=True, font_size=7)
    # overall depth (floor edge)
    _iso_dim(c, P(total_w, right_y0, 0), P(total_w - D, right_y0, 0),
             f'D {D:.2f}"', PROV, offset=-16, font_size=6.5)
    # seat H AFF (front vertical) — NOT foam
    _iso_dim(c, P(total_w - D, right_y0, 0), P(total_w - D, right_y0, z_seat),
             f'seat H {seat_h:.1f}" AFF PROV', PROV, offset=-20, bold=True, font_size=7)
    # lean (top setback)
    _iso_dim(c, P(total_w - bt, right_y0, z_top), P(total_w - bt + lean, right_y0, z_top),
             f'lean {lean:.1f}" PROV', PROV, offset=14, bold=True, font_size=6.5)
    # foam material callout — separate from seat H, parked off the section stack
    fx, fy = P(total_w - D * 0.35, right_y0, z_seat * 0.55)
    c.setFillColor(PROV)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(fx + 10, fy - 2, f'foam {foam:.1f}" mat\'l')

    # Title / chain legend
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(origin_x + 8, origin_y + area_h - 12,
                 f'ISO U — CLOSED FACES · outer {u.developed_outer_in:.2f}" / inner {u.developed_inner_in:.2f}"')
    c.setFont("Helvetica", 6.5)
    c.setFillColor(GRAY)
    c.drawString(origin_x + 8, origin_y + area_h - 24,
                 "Plan: OUTER+INNER+DEPTH · Section: H + D + seat H AFF + lean + foam(mat'l) — distinct")
    c.setFillColor(PROV)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(origin_x + 8, origin_y + 6,
                 f'seat H {seat_h:.1f}" AFF PROV · foam {foam:.1f}" mat\'l · lean {lean:.1f}" PROV (~{lean_angle_deg(lean, u.net_back_height):.1f}°) — confirm on site')


def _draw_l_iso(c, origin_x, origin_y, area_w, area_h, L: LShellSpec, colored: bool = True):
    """Closed-face L isometric — same constructive dim-chain rules as U.

    Section chain: shell H + overall D + seat H AFF + lean + foam(mat'l) as DISTINCT dims.
    Seat H is AFF (PROV), never foam thickness.
    """
    A, B, D = L.leg_short, L.leg_long, L.seat_depth
    lean = L.back_lean_in
    seat_h = L.seat_height          # AFF PROV
    foam = L.seat_foam              # material only
    shell_h = L.shell_height
    bt = min(2.0, D * 0.12)
    z_seat = seat_h
    z_top = shell_h

    scale, ox, oy = _auto_iso_scale((B, A, shell_h), area_w, area_h, margin=56)
    ox += origin_x
    oy += origin_y

    seat_fill = PLAIN_SEAT if colored else LT_FOAM
    back_fill = PATTERN_BACK if colored else LT_PEACH
    stroke = NAVY
    apron_fill = Color(seat_fill.red * 0.82, seat_fill.green * 0.82, seat_fill.blue * 0.82)

    def P(x, y, z):
        return _iso(x, y, z, ox, oy, scale)

    # Seat top L-ring
    seat_pts = [
        (0, 0, z_seat),
        (0, A, z_seat),
        (B, A, z_seat),
        (B, A - D, z_seat),
        (D, A - D, z_seat),
        (D, 0, z_seat),
    ]
    _iso_poly(c, seat_pts, ox, oy, scale, seat_fill, stroke, lw=1.1)

    # Aprons on inner fronts
    _iso_poly(c, [
        (D, A - D, 0), (B, A - D, 0), (B, A - D, z_seat), (D, A - D, z_seat),
    ], ox, oy, scale, apron_fill, stroke, lw=0.8)
    _iso_poly(c, [
        (D, 0, 0), (D, A - D, 0), (D, A - D, z_seat), (D, 0, z_seat),
    ], ox, oy, scale, apron_fill, stroke, lw=0.8)

    # Back faces
    _iso_poly(c, [
        (0, A - bt, z_seat), (B, A - bt, z_seat),
        (B, A - bt + lean, z_top), (0, A - bt + lean, z_top),
    ], ox, oy, scale, back_fill, stroke, lw=1.0, hatch=colored)
    _iso_poly(c, [
        (bt, 0, z_seat), (bt, A - D, z_seat),
        (bt - lean, A - D, z_top), (bt - lean, 0, z_top),
    ], ox, oy, scale, back_fill, stroke, lw=1.0, hatch=colored)

    # End section faces
    _iso_poly(c, [
        (0, 0, 0), (D, 0, 0), (D, 0, z_seat), (bt, 0, z_seat),
        (bt - lean, 0, z_top), (0, 0, shell_h),
    ], ox, oy, scale, Color(0.55, 0.58, 0.62), stroke, lw=1.15)
    _iso_poly(c, [
        (B, A, 0), (B, A - D, 0), (B, A - D, z_seat), (B, A - bt, z_seat),
        (B, A - bt + lean, z_top), (B, A, shell_h),
    ], ox, oy, scale, Color(0.55, 0.58, 0.62), stroke, lw=1.15)

    # OUTER / INNER — short shop labels
    _iso_dim(c, P(0, A - bt + lean, z_top), P(B, A - bt + lean, z_top),
             f'OUTER long {B:.3f}"', NAVY, offset=16, bold=True, font_size=6.5)
    # OUTER/INNER short: dim away from y=0 tip so section chain on long tip stays clean
    _iso_dim(c, P(bt - lean, A * 0.35, z_top), P(bt - lean, A - D, z_top),
             f'OUTER short {A:.3f}"', NAVY, offset=-16, bold=True, font_size=6.5)
    _iso_dim(c, P(D, A - D, z_seat), P(B, A - D, z_seat),
             f'INNER long {L.inner_leg_long:.3f}"', GRAY, offset=-14, font_size=6)
    _iso_dim(c, P(D, L.inner_leg_short * 0.35, z_seat), P(D, A - D, z_seat),
             f'INNER short {L.inner_leg_short:.3f}"', GRAY, offset=15, font_size=6)

    # DEPTH on long tip floor — also feeds section D
    _iso_dim(c, P(B, A, z_seat), P(B, A - D, z_seat),
             f'DEPTH {D:.1f}"', CUSH, offset=14, bold=True, font_size=6.5)

    # Section chain on long tip — five DISTINCT dims, fanned
    _iso_dim(c, P(B, A, 0), P(B, A, shell_h),
             f'H {shell_h:.1f}" PROV', PROV, offset=20, bold=True, font_size=7)
    _iso_dim(c, P(B, A, 0), P(B, A - D, 0),
             f'D {D:.1f}"', PROV, offset=-14, font_size=6.5)
    _iso_dim(c, P(B, A - D, 0), P(B, A - D, z_seat),
             f'seat H {seat_h:.1f}" AFF PROV', PROV, offset=-18, bold=True, font_size=7)
    _iso_dim(c, P(B, A - bt, z_top), P(B, A - bt + lean, z_top),
             f'lean {lean:.1f}" PROV', PROV, offset=12, bold=True, font_size=6.5)
    fx, fy = P(B, A - D * 0.35, z_seat * 0.55)
    c.setFillColor(PROV)
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(fx + 12, fy - 2, f'foam {foam:.1f}" mat\'l')

    c.setFillColor(PROV)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(origin_x + 8, origin_y + 8,
                 f'seat H {seat_h:.1f}" AFF PROV · foam {foam:.1f}" mat\'l · lean {lean:.1f}" PROV')
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(
        origin_x + 8, origin_y + area_h - 12,
        f'ISO L — outer {L.developed_outer_in:.3f}" / inner {L.developed_inner_in:.3f}"',
    )
    c.setFont("Helvetica", 6.5)
    c.setFillColor(GRAY)
    c.drawString(
        origin_x + 8, origin_y + area_h - 24,
        "Plan: OUTER+INNER+DEPTH · Section: H + D + seat H AFF + lean + foam(mat'l) — lock to U before fab",
    )


def _key_dims_panel(c, x, y, u: UShellSpec, L: LShellSpec):
    c.setFillColor(LT_GRAY)
    c.setStrokeColor(NAVY)
    c.setLineWidth(0.8)
    c.roundRect(x, y - 1.55 * inch, 3.4 * inch, 1.65 * inch, 4, fill=1, stroke=1)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 8, y, "KEY DIMENSIONS (LOCKED)")
    c.setFont("Helvetica", 7)
    c.setFillColor(GRAY)
    lines = [
        f'U back outer {u.back_outer:.2f}"  |  L arm {u.arm_left:.2f}"  |  R arm {u.arm_right:.2f}"',
        f'U seat depth {u.seat_depth:.2f}"  |  shell H {u.shell_height:.2f}"  |  net back {u.net_back_height:.2f}"',
        f'U seat H {u.seat_height:.1f}" AFF PROV  |  foam {u.seat_foam:.1f}" mat\'l  |  developed {u.developed_outer_lf:.2f} lf',
        f'L legs {L.leg_short:.3f}" + {L.leg_long:.3f}"  |  depth {L.seat_depth:.1f}" PROV',
        f'L shell {L.shell_height:.1f}" PROV  |  seat H {L.seat_height:.1f}" AFF PROV  |  foam {L.seat_foam:.1f}"',
        "BACK = basketweave (Sep 2022 / bar tile) · SEAT = plain",
    ]
    yy = y - 14
    for ln in lines:
        c.drawString(x + 8, yy, ln)
        yy -= 11


# ── Sheet builders ────────────────────────────────────────────────


def _video_dim_checklist(c, x, y, u: UShellSpec, L: LShellSpec):
    """Site-measure checklist from Rafael help-video sketch (lean + L dims)."""
    box_h = 1.85 * inch
    box_w = 3.55 * inch
    c.setFillColor(HexColor("#1a202c"))
    c.setStrokeColor(PROV)
    c.setLineWidth(1.5)
    c.roundRect(x, y - box_h, box_w, box_h, 4, fill=1, stroke=1)
    c.setFillColor(PROV)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(x + 8, y - 14, "SITE DIM CHECKLIST (Rafael video)")
    c.setFillColor(white)
    c.setFont("Helvetica", 6.5)
    lines = [
        "Capture on site before fab / COM order:",
        f'☐ Full height (shell) — U now {u.shell_height:.2f}"',
        f'☐ Full depth (overall) — U seat {u.seat_depth:.2f}" + back thick',
        f'☐ Seat height AFF — U {u.seat_height:.1f}" / L {L.seat_height:.1f}" PROV (NOT foam)',
        f'☐ Seat foam thickness — {u.seat_foam:.1f}" mat\'l (distinct from seat H AFF)',
        f'☐ Seat depth — U {u.seat_depth:.2f}" / L {L.seat_depth:.1f}" PROV',
        f'☐ Outside L runs — long {L.leg_long:.3f}" / short {L.leg_short:.3f}"',
        "☐ Inside L runs (clear opening) — TBD measure",
        f'☐ Back LEAN/PITCH — top setback (now {u.back_lean_in:.1f}" PROV)',
        "☐ Confirm basketweave on angled BACK only; seat PLAIN",
    ]
    yy = y - 28
    for ln in lines:
        c.drawString(x + 8, yy, ln)
        yy -= 11
    c.setFillColor(HexColor("#fbd38d"))
    c.setFont("Helvetica", 6)
    c.drawString(x + 8, y - box_h + 6, "Do not fab lean or L depth/height until checked.")


def render_upholstery_shell_pdf(
    *,
    out_path: str | Path,
    u: Optional[UShellSpec] = None,
    L: Optional[LShellSpec] = None,
    meta: Optional[SheetMeta] = None,
    include_u: bool = True,
    include_l: bool = True,
    include_iso: bool = False,
    fabric_width_in: float = FABRIC_WIDTH_DEFAULT,
) -> dict:
    """Write upholstery-on-shell PDF — TOP/FRONT/SIDE ortho first; iso omitted by default."""
    u = u or UShellSpec()
    L = L or LShellSpec()
    meta = meta or SheetMeta()
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    mats = compute_materials(u, L, fabric_width_in=fabric_width_in)

    # Sheet roster — TOP / FRONT / SIDE ortho lead; iso PARKED (omit by default)
    roster = []
    if include_u:
        roster += ["U Top (Plan)", "U Front", "U Side"]
    if include_l:
        roster += ["L Top (Plan)", "L Front", "L Side"]
    roster += ["Client Mockup", "Cushion Schedule", "Materials", "Module Schedule"]
    if include_iso:
        if include_u:
            roster.append("U Isometric (DEFERRED)")
        if include_l:
            roster.append("L Isometric (DEFERRED)")
    total = len(roster)
    sheets_done = []

    c = canvas.Canvas(str(out_path), pagesize=landscape(letter))
    w, h = landscape(letter)
    si = 0

    def finish(title_short):
        nonlocal si
        si += 1
        _title_block(c, w, h, str(si), title_short, meta, total)
        c.showPage()
        sheets_done.append(title_short)

    # ── U TOP (Plan) ──
    if include_u:
        _page_header(
            c, w, h,
            "U BANQUETTE — TOP (PLAN)",
            "Upholstery on existing shell · asymmetric arms · outer / inner / seat depth · developed outer run = lf takeoff",
        )
        scale = (8.6 * inch) / u.back_outer
        _draw_u_plan(c, 0.85 * inch, h - 1.25 * inch, scale, u)
        _legend(c, w - 2.4 * inch, h - 1.3 * inch, [
            (LT_BLUE, "Shell / wall outline"),
            (CUSH, "Seat cushion footprint"),
            (NAVY, "Developed run callout"),
        ])
        _key_dims_panel(c, w - 3.9 * inch, 2.7 * inch, u, L)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 7.5)
        c.drawString(
            0.45 * inch, 1.50 * inch,
            "TOP/PLAN: Blue = shell/wall. Orange dashed = seat footprint. Opening toward bottom. BOTH arms drawn (never max). Units: inches.",
        )
        finish("U Top (Plan)")

        # ── U FRONT ──
        _page_header(
            c, w, h,
            "U BANQUETTE — FRONT (FACE VIEW)",
            f'Pattern on back / plain seat · shell H {u.shell_height}" · seat H {u.seat_height:.1f}" AFF PROV · foam {u.seat_foam:.1f}" mat\'l (≠ seat H)',
        )
        _draw_u_front(c, 0.55 * inch, 1.85 * inch, 8.4, 9.5 * inch, u, colored=True)
        _legend(c, w - 2.55 * inch, h - 1.15 * inch, [
            (PATTERN_BACK_BAR, "Basketweave BACK"),
            (PLAIN_SEAT, "Plain SEAT"),
            (PROV, "Seat H AFF provisional"),
        ])
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 7.5)
        c.drawString(
            0.45 * inch, 1.48 * inch,
            "FRONT = face of back run. Lean / pitch shown on SIDE sheet. Arms asymmetric — see TOP. Not a wood-frame section.",
        )
        finish("U Front")

        # ── U SIDE ──
        _page_header(
            c, w, h,
            "U BANQUETTE — SIDE (ELEVATION)",
            f'Video dim chain: overall H · overall D · seat H AFF · seat depth · lean  |  lean {u.back_lean_in:.1f}" PROV',
        )
        _draw_u_elev(c, 0.55 * inch, 2.05 * inch, 8.0, 6.6 * inch, u, colored=True)
        _legend(c, 7.7 * inch, 6.6 * inch, [
            (PATTERN_BACK_BAR, "Basketweave BACK (leaned)"),
            (PLAIN_SEAT, "Plain SEAT"),
            (PROV, "Lean / seat H provisional"),
        ])
        _video_dim_checklist(c, 7.55 * inch, 4.55 * inch, u, L)
        c.setFillColor(GRAY)
        c.setFont("Helvetica", 7.5)
        c.drawString(
            0.45 * inch, 1.50 * inch,
            "SIDE dim chain from Rafael help-video: overall H, overall D, seat H AFF, seat depth, lean. Foam is mat'l only — never labeled as seat H. Confirm lean on site.",
        )
        finish("U Side")

    if include_l:
        # ── L TOP (Plan) ──
        _page_header(
            c, w, h,
            "L BANQUETTE — TOP (PLAN) (provisional depth/height)",
            "Lock L depth/height to U before fabrication · developed run labeled",
        )
        scale_l = (7.2 * inch) / L.leg_long
        _draw_l_plan(c, 1.1 * inch, h - 1.3 * inch, scale_l, L)
        _legend(c, w - 2.5 * inch, h - 1.3 * inch, [
            (LT_BLUE, "Shell outline"),
            (CUSH, "Seat footprint"),
            (PROV, "Provisional flag"),
        ])
        c.setFillColor(PROV)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(
            0.45 * inch, 1.50 * inch,
            f'PROVISIONAL: L depth {L.seat_depth}" / height {L.shell_height}" / seat {L.seat_height}" AFF — lock to U before fab.',
        )
        finish("L Top (Plan)")

        # ── L FRONT ──
        _page_header(
            c, w, h,
            "L BANQUETTE — FRONT (FACE VIEW) (provisional)",
            f'Long-leg face · pattern on back / plain seat · lock depth/height to U before fab',
        )
        _draw_l_front(c, 0.55 * inch, 1.95 * inch, 8.0, 9.5 * inch, L, colored=True)
        _legend(c, w - 2.55 * inch, h - 1.15 * inch, [
            (PATTERN_BACK_BAR, "Basketweave BACK"),
            (PLAIN_SEAT, "Plain SEAT"),
            (PROV, "Provisional geometry"),
        ])
        finish("L Front")

        # ── L SIDE ──
        _page_header(
            c, w, h,
            "L BANQUETTE — SIDE (ELEVATION) (provisional)",
            f'Video dim chain (same as U) · lean {L.back_lean_in:.1f}" PROV · lock to U before fab',
        )
        _draw_l_side(c, 0.55 * inch, 2.15 * inch, 8.0, 6.6 * inch, L, colored=True)
        _legend(c, 7.7 * inch, 6.6 * inch, [
            (PATTERN_BACK_BAR, "Basketweave BACK (leaned)"),
            (PLAIN_SEAT, "Plain SEAT"),
            (PROV, "Provisional"),
        ])
        _video_dim_checklist(c, 7.55 * inch, 4.55 * inch, u, L)
        finish("L Side")

    # ── Client Mockup ──
    _page_header(
        c, w, h,
        "CLIENT MOCKUP — BASKETWEAVE BACK / PLAIN SEAT",
        "basketweave to match Sep 2022 / bar tile · plain smooth seat · COM / Nelma TBD",
    )
    # U plan colored (left) + elev colored (right)
    scale_m = (5.8 * inch) / u.back_outer
    _draw_u_plan(c, 0.55 * inch, h - 1.35 * inch, scale_m, u, colored=True)
    _draw_u_elev(c, 7.3 * inch, 3.4 * inch, 5.5, 3.2 * inch, u, colored=True)
    # Small L plan colored bottom
    scale_lm = (3.8 * inch) / L.leg_long
    _draw_l_plan(c, 0.55 * inch, 3.35 * inch, scale_lm, L, colored=True)

    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(7.3 * inch, 3.1 * inch, "COLOR / PATTERN KEY")
    c.setFont("Helvetica", 7)
    c.setFillColor(PATTERN_BACK_BAR)
    c.drawString(7.3 * inch, 2.88 * inch, "■ BASKETWEAVE BACK — groups of 2")
    c.drawString(7.3 * inch, 2.74 * inch, "  bars alternating H/V (pads)")
    c.setFillColor(HexColor("#aaaaaa"))
    c.drawString(7.3 * inch, 2.56 * inch, "■ PLAIN SEAT — smooth solid black")
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 6.5)
    c.drawString(7.3 * inch, 2.36 * inch, "basketweave to match Sep 2022 /")
    c.drawString(7.3 * inch, 2.22 * inch, "bar tile. COM TBD — not mill match.")
    # Mini weave swatch
    _basketweave_rect(c, 7.3 * inch, 1.55 * inch, 1.35 * inch, 0.55 * inch, tile=max(4.0, 0.55 * inch * (TILE_FACE_IN / 26.75)))
    c.setFillColor(PLAIN_SEAT)
    c.rect(8.8 * inch, 1.55 * inch, 0.85 * inch, 0.55 * inch, fill=1, stroke=0)
    c.setStrokeColor(GRAY)
    c.setLineWidth(0.5)
    c.rect(7.3 * inch, 1.55 * inch, 1.35 * inch, 0.55 * inch, fill=0, stroke=1)
    c.rect(8.8 * inch, 1.55 * inch, 0.85 * inch, 0.55 * inch, fill=0, stroke=1)
    c.setFillColor(white)
    c.setFont("Helvetica", 5.5)
    c.drawCentredString(7.3 * inch + 0.67 * inch, 1.75 * inch, "weave")
    c.drawCentredString(8.8 * inch + 0.42 * inch, 1.75 * inch, "plain")
    finish("Client Mockup")

    # ── Cushion Schedule ──
    _page_header(
        c, w, h,
        f"CUSHION SCHEDULE — {meta.quote_num}",
        "By run + SF · no 24\" auto-slice · PATTERN = backs · PLAIN = seats",
    )
    rows = [
        ("Mark", "Location", "Fabric", "Run", "H / Depth", "SF", "Notes"),
        (
            "U-B", "U backs", "PATTERN",
            f'{u.developed_outer_in:.2f}" ({u.developed_outer_lf:.2f} lf)',
            f'{u.net_back_height:.2f}" net',
            f"{u.back_sf:.2f}",
            "Arms in developed run",
        ),
        (
            "U-S", "U seats", "PLAIN",
            f'{u.developed_outer_lf:.2f} lf',
            f'{u.seat_depth:.2f}" × {u.seat_foam:.1f}" foam',
            f"{u.seat_sf:.2f}",
            "Shop splits sew/handle",
        ),
        (
            "L-B", "L backs", "PATTERN",
            f'{L.developed_outer_lf:.2f} lf',
            f'{L.net_back:.2f}" prov.',
            f"{L.back_sf:.2f}",
            "Lock height to U",
        ),
        (
            "L-S", "L seats", "PLAIN",
            f'{L.developed_outer_lf:.2f} lf',
            f'{L.seat_depth:.1f}" prov.',
            f"{L.seat_sf:.2f}",
            "Lock depth to U",
        ),
    ]
    y = h - 1.05 * inch
    col_x = [0.45, 1.05, 2.15, 3.15, 5.55, 7.15, 8.0]
    # header bar
    c.setFillColor(NAVY)
    c.rect(0.4 * inch, y - 0.06 * inch, w - 0.8 * inch, 0.28 * inch, fill=1, stroke=0)
    for i, row in enumerate(rows):
        if i == 0:
            c.setFillColor(white)
            c.setFont("Helvetica-Bold", 8)
        else:
            c.setFillColor(LT_GRAY if i % 2 == 0 else white)
            c.rect(0.4 * inch, y - 0.08 * inch, w - 0.8 * inch, 0.26 * inch, fill=1, stroke=0)
            c.setFillColor(black)
            c.setFont("Helvetica", 7.5)
            # fabric column color hint
        for j, cell in enumerate(row):
            if i > 0 and j == 2:
                c.setFillColor(PATTERN_BACK_BAR if cell == "PATTERN" else HexColor("#666666"))
                c.setFont("Helvetica-Bold", 7.5)
            elif i > 0:
                c.setFillColor(black)
                c.setFont("Helvetica", 7.5)
            c.drawString(col_x[j] * inch, y, str(cell))
        y -= 0.28 * inch

    y -= 0.1 * inch
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 8)
    for n in [
        "Rates on quote: backs $85/sf (PATTERN labor), seats $45/sf (PLAIN labor). Fabric COM TBD — $0 on quote.",
        "Do NOT auto-slice every 24\" into cushion count. Schedule is by run + SF.",
        "No wood ribs, dados, CNC nests, or frame cut list on this set — upholstery on existing shells only.",
        f"U developed outer run {u.developed_outer_lf:.2f} lf is the takeoff (not footprint width {u.footprint_width:.2f}\").",
    ]:
        c.drawString(0.45 * inch, y, "• " + n)
        y -= 0.20 * inch
    finish("Cushion Schedule")

    # ── Materials (modular basketweave order basis) ──
    _page_header(
        c, w, h,
        "MATERIALS TAKEOFF — MODULAR BASKETWEAVE + PLAIN SEAT",
        f'TILE {mats.module_face_in:.1f}" · STD bar {mats.bar_face_in[0]:.1f}"×{mats.bar_face_in[1]:.1f}" · 2 rows + {mats.height_leftover_in:.2f}" leftover OPEN · foam+{mats.module_staple_in:.1f}" staple · nest {round((mats.waste_fabric-1)*100)}%',
    )

    def card(x, y, title, lines, accent):
        c.setFillColor(white)
        c.setStrokeColor(accent)
        c.setLineWidth(1.5)
        c.roundRect(x, y, 3.3 * inch, 1.65 * inch, 5, fill=1, stroke=1)
        c.setFillColor(accent)
        c.rect(x, y + 1.45 * inch, 3.3 * inch, 0.2 * inch, fill=1, stroke=0)
        c.setFillColor(white)
        c.setFont("Helvetica-Bold", 7.5)
        c.drawString(x + 8, y + 1.50 * inch, title)
        c.setFillColor(NAVY)
        c.setFont("Helvetica", 7)
        yy = y + 1.25 * inch
        for ln in lines:
            c.drawString(x + 8, yy, ln)
            yy -= 0.15 * inch

    fb = mats.module_fabric_blank_in
    pb = mats.module_ply_blank_in
    card(
        0.45 * inch, h - 2.95 * inch, "PATTERN BARS (BACKS — 6.5×13)",
        [
            f"STD bars: U {mats.u_std_bars} + L {mats.l_std_bars} = {mats.std_bar_count_total}",
            f'STD ply/foam: {pb[0]:.1f}" × {pb[1]:.1f}"  |  fab {fb[0]:.1f}"×{fb[1]:.1f}"',
            f"U: {mats.u_full_tiles} tiles ×2 + {mats.u_end_closers} EC + {mats.u_inside_corner_specials} IC",
            f"L: {mats.l_full_tiles} tiles ×2 + {mats.l_end_closers} EC  |  boards {mats.board_count_total}",
            f"ORDER: {mats.pattern_yards_order:.2f} yd  @ {mats.fabric_width_in:.0f}\"  (nest {round((mats.waste_fabric-1)*100)}%)",
        ],
        PATTERN_BACK_DK,
    )
    card(
        3.95 * inch, h - 2.95 * inch, "PLAIN FABRIC (SEATS — NOT MODULAR)",
        [
            f"Seat blanks (wrap {mats.seat_wrap_edge_in:.1f}\"/edge): {mats.plain_fabric_sf_blanks:.2f} sf",
            f"Face SF (info): U+L = {mats.plain_seat_sf:.2f} sf",
            f"Yards raw: {mats.plain_yards_raw:.2f} yd",
            f"ORDER: {mats.plain_yards_order:.2f} yd  @ {mats.fabric_width_in:.0f}\"",
            "Large pieces — do NOT cut as basketweave modules.",
        ],
        HexColor("#4a5568"),
    )
    card(
        7.45 * inch, h - 2.95 * inch, '1/2" PLYWOOD',
        [
            f"Back BOARDS: {mats.ply_back_sf:.2f} sf ({mats.board_count_total} bars/EC/IC)",
            f"Seat DECKS: {mats.ply_seat_sf:.2f} sf (face)",
            f"Total: {mats.ply_total_sf:.2f} sf",
            f"With {round((mats.waste_ply-1)*100)}% waste: {mats.ply_with_waste_sf:.2f} sf",
            f"SHEETS 4×8: {mats.ply_sheets}  (1/2\" ACX/shop)",
        ],
        NAVY,
    )

    # Construction callout
    c.setFillColor(HexColor("#1a202c"))
    c.setStrokeColor(GOLD)
    c.setLineWidth(1.4)
    c.roundRect(0.45 * inch, h - 3.70 * inch, w - 0.9 * inch, 0.60 * inch, 4, fill=1, stroke=1)
    c.setFillColor(GOLD)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(0.55 * inch, h - 3.22 * inch, "CONSTRUCTION (Rafael)")
    c.setFillColor(white)
    c.setFont("Helvetica", 7)
    c.drawString(
        1.95 * inch, h - 3.22 * inch,
        "PATTERN = bar 6.5×13 / tile 13×13 (2 bars H/V) — ply + foam + fabric.  SEAT = PLAIN. Height leftover 0.75\" OPEN.",
    )
    c.setFillColor(HexColor("#fbd38d"))
    c.setFont("Helvetica-Bold", 6.5)
    c.drawString(
        0.55 * inch, h - 3.42 * inch,
        f'Fabric EXTRA = foam wrap {mats.module_foam_thk_in:.1f}"/side + staple-on-back {mats.module_staple_in:.1f}"/side (mid of Rafael\'s 2–3"). Order PATTERN from BAR blanks — NOT face-SF.',
    )
    c.setFillColor(HexColor("#cbd5e0"))
    c.setFont("Helvetica", 6.5)
    c.drawString(
        0.55 * inch, h - 3.58 * inch,
        f'TILE LOCKED {mats.module_face_in:.1f}". STD bar {mats.bar_face_in[0]:.1f}"×{mats.bar_face_in[1]:.1f}". Height {mats.tile_rows}×13 + {mats.height_leftover_in:.2f}" {mats.height_leftover_status}. Full tiles + end closers; U IC. See MODULE SCHEDULE.',
    )

    # Formulas (compact)
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(0.45 * inch, h - 3.90 * inch, "FORMULAS (audit)")
    c.setFont("Helvetica", 6.5)
    c.setFillColor(GRAY)
    yy = h - 4.08 * inch
    for fml in mats.formulas:
        c.drawString(0.5 * inch, yy, "• " + fml)
        yy -= 0.125 * inch

    # Assumptions
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(0.45 * inch, yy - 0.06 * inch, "ASSUMPTIONS — Rafael: correct if shop practice differs")
    yy -= 0.22 * inch
    c.setFont("Helvetica", 6)
    c.setFillColor(GRAY)
    for a in mats.assumptions:
        text = "• " + a
        if len(text) > 155:
            c.drawString(0.5 * inch, yy, text[:155])
            yy -= 0.11 * inch
            c.drawString(0.65 * inch, yy, text[155:])
        else:
            c.drawString(0.5 * inch, yy, text)
        yy -= 0.11 * inch

    finish("Materials")

    # ── Module Schedule ──
    _page_header(
        c, w, h,
        "MODULE SCHEDULE — 6.5×13 BARS / 13×13 TILES + CLOSERS + U CORNERS",
        f'STD bar = 1/2" ply {pb[0]:.1f}"×{pb[1]:.1f}" + foam {mats.module_foam_thk_in:.1f}" + fabric {fb[0]:.1f}"×{fb[1]:.1f}" (wrap+staple → 14.5×21)',
    )

    # Table header
    headers = ["Mark", "Location", "Cols", "Rows", "Qty", 'Ply blank', 'Foam blank', 'Fabric blank', "Ply SF", "Fab SF", "Notes"]
    col_x = [0.45, 1.05, 3.35, 3.85, 4.35, 4.90, 6.05, 7.20, 8.55, 9.20, 9.85]
    y = h - 1.05 * inch
    c.setFillColor(NAVY)
    c.rect(0.4 * inch, y - 0.06 * inch, w - 0.8 * inch, 0.26 * inch, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 7)
    for j, lab in enumerate(headers):
        c.drawString(col_x[j] * inch, y, lab)
    y -= 0.30 * inch

    for i, mod in enumerate(mats.modules):
        c.setFillColor(LT_GRAY if i % 2 == 0 else white)
        c.rect(0.4 * inch, y - 0.08 * inch, w - 0.8 * inch, 0.28 * inch, fill=1, stroke=0)
        c.setFillColor(black)
        c.setFont("Helvetica", 7)
        cells = [
            mod.mark,
            mod.location[:28],
            str(mod.cols),
            str(mod.rows),
            str(mod.count),
            f'{mod.ply_blank_in[0]:.1f}×{mod.ply_blank_in[1]:.1f}',
            f'{mod.foam_blank_in[0]:.1f}×{mod.foam_blank_in[1]:.1f}',
            f'{mod.fabric_blank_in[0]:.1f}×{mod.fabric_blank_in[1]:.1f}',
            f'{mod.ply_sf:.1f}',
            f'{mod.fabric_sf:.1f}',
            (mod.notes or "")[:28],
        ]
        for j, cell in enumerate(cells):
            if j == 0:
                c.setFillColor(PATTERN_BACK_BAR)
                c.setFont("Helvetica-Bold", 7)
            else:
                c.setFillColor(black)
                c.setFont("Helvetica", 7)
            c.drawString(col_x[j] * inch, y, cell)
        y -= 0.30 * inch

    # Totals row
    c.setFillColor(HexColor("#2d3748"))
    c.rect(0.4 * inch, y - 0.08 * inch, w - 0.8 * inch, 0.28 * inch, fill=1, stroke=0)
    c.setFillColor(white)
    c.setFont("Helvetica-Bold", 7.5)
    c.drawString(col_x[0] * inch, y, "TOTAL")
    c.drawString(col_x[4] * inch, y, str(mats.module_count_total))
    c.drawString(col_x[8] * inch, y, f'{mats.ply_back_sf:.1f}')
    c.drawString(col_x[9] * inch, y, f'{mats.pattern_fabric_sf_blanks:.1f}')
    y -= 0.45 * inch

    # Per-module build note
    c.setFillColor(NAVY)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(0.45 * inch, y, "PER-BAR BUILD (shop)")
    y -= 0.18 * inch
    c.setFont("Helvetica", 7.5)
    c.setFillColor(GRAY)
    for ln in [
        f'1. Cut 1/2" ply STD bar {pb[0]:.1f}" × {pb[1]:.1f}" (FOUNDER LOCK: bar 6.5×13 / tile 13×13 / 2 bars H/V — NOT height-divided).',
        f'2. Cut foam {mats.module_foam_thk_in:.1f}" thick to same bar face (or slight oversize per shop practice).',
        f'3. Cut fabric {fb[0]:.1f}" × {fb[1]:.1f}" = face + 2×(foam {mats.module_foam_thk_in:.1f}" + staple {mats.module_staple_in:.1f}"). Staple to BACK of ply.',
        f'4. Walk runs: U {mats.u_full_tiles} tiles ×2 + {mats.u_end_closers} EC ({mats.u_end_closer_w_in:.3f}") + {mats.u_inside_corner_specials} IC; L {mats.l_full_tiles} ×2 + {mats.l_end_closers} EC. Alternate H/V.',
        f'5. Height leftover {mats.height_leftover_in:.2f}" closer/trim band — {mats.height_leftover_status} (not in STD bar count).',
        "6. SEATS: plain fabric large blanks only — see Materials sheet. No modular basketweave on seats.",
    ]:
        c.drawString(0.5 * inch, y, "• " + ln)
        y -= 0.16 * inch

    y -= 0.10 * inch
    c.setFillColor(PROV)
    c.setFont("Helvetica-Bold", 8)
    c.drawString(0.45 * inch, y, "ORDER SUMMARY")
    y -= 0.16 * inch
    c.setFillColor(NAVY)
    c.setFont("Helvetica", 8)
    for ln in [
        f'PATTERN (bar fabric): {mats.pattern_yards_order:.2f} yd @ {mats.fabric_width_in:.0f}"  — from {mats.board_count_total} boards (STD+EC+IC) + {round((mats.waste_fabric-1)*100)}% nest',
        f'PLAIN (seat fabric): {mats.plain_yards_order:.2f} yd @ {mats.fabric_width_in:.0f}"  — large wraps, not bars',
        f'1/2" ply: {mats.ply_sheets} sheets 4×8  — boards {mats.ply_back_sf:.1f} sf + seat decks {mats.ply_seat_sf:.1f} sf + {round((mats.waste_ply-1)*100)}% waste',
        f'Foam (backs): ~{mats.ply_back_sf:.1f} sf @ {mats.module_foam_thk_in:.1f}" (bar faces); seat foam separate @ seat thickness',
    ]:
        c.drawString(0.5 * inch, y, "• " + ln)
        y -= 0.16 * inch

    y -= 0.08 * inch
    c.setFillColor(GRAY)
    c.setFont("Helvetica", 7)
    c.drawString(
        0.45 * inch, y,
        "DRAFT. Face-SF pattern yardage is NOT the order basis. Bar blanks are. Founder lock: bar 6.5×13 / tile 13×13 / 2 rows + 0.75\" leftover OPEN.",
    )
    finish("Module Schedule")

    # ── ISO (DEFERRED) — parked per Rafael 2026-09-24; not the discussion deliverable ──
    if include_iso and include_u:
        _page_header(
            c, w, h,
            "U BANQUETTE — ISOMETRIC (DEFERRED)",
            "PARKED — closed-face iso rule remains in EMPIRE_DRAWING_STANDARD; ortho TOP/FRONT/SIDE is the deliverable for this pack",
        )
        # Deferred banner
        c.setFillColor(PROV)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(w / 2, h - 0.85 * inch, "DEFERRED — ISOMETRIC PARKED (work on later)")
        _draw_u_iso(c, 0.6 * inch, 1.55 * inch, w - 1.2 * inch, h - 3.4 * inch, u, colored=True)
        finish("U Isometric (DEFERRED)")
    if include_iso and include_l:
        _page_header(
            c, w, h,
            "L BANQUETTE — ISOMETRIC (DEFERRED)",
            "PARKED — provisional L · ortho TOP/FRONT/SIDE is the deliverable for this pack",
        )
        c.setFillColor(PROV)
        c.setFont("Helvetica-Bold", 14)
        c.drawCentredString(w / 2, h - 0.85 * inch, "DEFERRED — ISOMETRIC PARKED (work on later)")
        _draw_l_iso(c, 0.6 * inch, 1.55 * inch, w - 1.2 * inch, h - 3.4 * inch, L, colored=True)
        finish("L Isometric (DEFERRED)")

    c.save()
    return {
        "pdf_path": str(out_path),
        "size_bytes": out_path.stat().st_size,
        "sheets": sheets_done,
        "sheet_count": len(sheets_done),
        "product_type": "upholstery_on_shell",
        "true_ul_polyline": True,
        "units": "inches",
        "u": {
            "back_outer": u.back_outer,
            "arm_left": u.arm_left,
            "arm_right": u.arm_right,
            "seat_depth": u.seat_depth,
            "shell_height": u.shell_height,
            "net_back_height": u.net_back_height,
            "seat_height": u.seat_height,
            "seat_foam": u.seat_foam,
            "developed_outer_in": u.developed_outer_in,
            "developed_outer_lf": round(u.developed_outer_lf, 2),
            "footprint_width": u.footprint_width,
            "back_sf": round(u.back_sf, 2),
            "seat_sf": round(u.seat_sf, 2),
        },
        "l": {
            "leg_short": L.leg_short,
            "leg_long": L.leg_long,
            "seat_depth": L.seat_depth,
            "shell_height": L.shell_height,
            "seat_height": L.seat_height,
            "seat_foam": L.seat_foam,
            "developed_outer_in": L.developed_outer_in,
            "developed_outer_lf": round(L.developed_outer_lf, 2),
            "back_sf": round(L.back_sf, 2),
            "seat_sf": round(L.seat_sf, 2),
            "provisional": L.provisional,
        },
        "materials": {
            "fabric_width_in": mats.fabric_width_in,
            "waste_fabric_pct": round((mats.waste_fabric - 1) * 100),
            "construction": "modular_basketweave_bars_65x13",
            "module_face_in": mats.module_face_in,
            "tile_face_in": mats.module_face_in,
            "tile_rows": mats.tile_rows,
            "height_leftover_in": mats.height_leftover_in,
            "height_leftover_status": mats.height_leftover_status,
            "bar_face_in": list(mats.bar_face_in),
            "module_foam_thk_in": mats.module_foam_thk_in,
            "module_staple_in": mats.module_staple_in,
            "u_full_tiles": mats.u_full_tiles,
            "u_end_closer_w_in": mats.u_end_closer_w_in,
            "u_end_closers": mats.u_end_closers,
            "u_inside_corner_specials": mats.u_inside_corner_specials,
            "l_full_tiles": mats.l_full_tiles,
            "l_end_closer_w_in": mats.l_end_closer_w_in,
            "l_end_closers": mats.l_end_closers,
            "u_std_bars": mats.u_std_bars,
            "l_std_bars": mats.l_std_bars,
            "std_bar_count_total": mats.std_bar_count_total,
            "board_count_total": mats.board_count_total,
            "u_module_count": mats.u_module_count,
            "l_module_count": mats.l_module_count,
            "module_count_total": mats.module_count_total,
            "module_ply_blank_in": list(mats.module_ply_blank_in),
            "module_foam_blank_in": list(mats.module_foam_blank_in),
            "module_fabric_blank_in": list(mats.module_fabric_blank_in),
            "pattern_fabric_sf_blanks": mats.pattern_fabric_sf_blanks,
            "pattern_back_sf_face_info": mats.pattern_back_sf,
            "plain_seat_sf_face_info": mats.plain_seat_sf,
            "plain_fabric_sf_blanks": mats.plain_fabric_sf_blanks,
            "seat_wrap_edge_in": mats.seat_wrap_edge_in,
            "pattern_yards_raw": mats.pattern_yards_raw,
            "plain_yards_raw": mats.plain_yards_raw,
            "pattern_yards_order": mats.pattern_yards_order,
            "plain_yards_order": mats.plain_yards_order,
            "ply_back_sf": mats.ply_back_sf,
            "ply_seat_sf": mats.ply_seat_sf,
            "ply_total_sf": mats.ply_total_sf,
            "ply_with_waste_sf": mats.ply_with_waste_sf,
            "ply_sheets_4x8": mats.ply_sheets,
            "modules": [
                {
                    "mark": mod.mark, "location": mod.location, "cols": mod.cols,
                    "rows": mod.rows, "count": mod.count,
                    "ply_blank_in": list(mod.ply_blank_in),
                    "foam_blank_in": list(mod.foam_blank_in),
                    "fabric_blank_in": list(mod.fabric_blank_in),
                    "ply_sf": mod.ply_sf, "foam_sf": mod.foam_sf, "fabric_sf": mod.fabric_sf,
                    "notes": mod.notes,
                }
                for mod in mats.modules
            ],
            "assumptions": mats.assumptions,
            "formulas": mats.formulas,
        },
        "drawing_engine": "drawing.upholstery_shell_renderer",
        "no_24in_autoslice": True,
        "asymmetric_arms": True,
        "has_isometric": bool(include_iso),
        "has_client_mockup": True,
        "has_materials": True,
        "has_module_schedule": True,
        "modular_basketweave": True,
        "founder_locked_65x13": True,
        "photo_locked_4row": False,  # killed — was wrong small-bar height divide
        "std_bar_face_in": list(mats.bar_face_in),
        "pattern_backs_only": True,
        "plain_seats_only": True,
    }
