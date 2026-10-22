"""Reusable upholstery / banquette job spec for Max's shop-drawing template.

Driven by job measurements — not a single client. U, L, and straight benches
share one channel / seat / cut-size contract:

- Channel Option A: full target-width boards + one odd remainder.
- Main / long back runs through the corner; return backs start at the
  main back face and butt it.
- Main / long seats run wall-to-front under the backs; return seats
  butt the main seat front.
- Wood / board cut = true size. Foam cut = wood. Fabric cut =
  wood + 2 × allowance_in for that foam thickness.
- Printed sizes are fractions only.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field, replace
from fractions import Fraction
from typing import Any, Iterable, Optional

from app.config.fabric_cut_allowance import (
    CONFIRM_WITH_RAFAEL,
    NEEDS_FOAM_THICKNESS,
    fabric_dimension_in,
    lookup_fabric_allowance,
)
from app.services.vision.bench_cut_list import (
    FABRIC_LABEL,
    FOAM_LABEL,
    WOOD_LABEL,
    format_cut_inches,
)

MAX_SEAT_LENGTH_IN = 96.0
MAX_SEAT_DEPTH_IN = 48.0
DEFAULT_CHANNEL_WIDTH_IN = 12.0
DEFAULT_ROLL_WIDTH_IN = 54.0
PLY_THICKNESS_IN = 0.5
YARD_EXTRA = 0.10


def as_frac(value: Any) -> Fraction:
    if isinstance(value, Fraction):
        return value
    if value in (None, ""):
        raise ValueError("missing inch value")
    return Fraction(value).limit_denominator(64)


def inch_text(value: Any) -> str:
    return format_cut_inches(float(as_frac(value)))


def no_decimal_inches(text: str) -> bool:
    import re
    return not re.search(r"\d+\.\d+\"", text or "")


@dataclass(frozen=True)
class ChannelPiece:
    label: str
    width_in: float
    is_odd: bool = False

    @property
    def width_text(self) -> str:
        return inch_text(self.width_in)


@dataclass
class RunSpec:
    run_id: str
    name: str
    role: str  # main | left | right | long | short
    axis: str  # x along wall, z along return
    back_run_in: float
    channels: list[ChannelPiece] = field(default_factory=list)
    odd_at: str = "open end"
    open_end: bool = True

    @property
    def channel_sum_in(self) -> float:
        return float(sum(as_frac(c.width_in) for c in self.channels))

    @property
    def odd_channels(self) -> list[ChannelPiece]:
        return [c for c in self.channels if c.is_odd]

    @property
    def standard_channels(self) -> list[ChannelPiece]:
        return [c for c in self.channels if not c.is_odd]


@dataclass
class SeatBoard:
    label: str
    run_id: str
    length_in: float
    depth_in: float
    note: str = ""
    butts_front_of: Optional[str] = None

    @property
    def size_text(self) -> str:
        return f"{inch_text(self.depth_in)} x {inch_text(self.length_in)}"


@dataclass
class FabricFace:
    code: Optional[str] = None
    color: Optional[str] = None
    label: str = "TBC — CONFIRM BEFORE CUT"
    hex: str = "#9A5B2E"
    plan_hex: str = "#c98b55"
    notes: str = ""

    @property
    def sheet_label(self) -> str:
        code = (self.code or "").strip()
        color = (self.color or "").strip()
        if code and color and color.lower() not in code.lower():
            return f"{code} {color}"
        if code:
            return code
        if color:
            return color
        return self.label or "TBC — CONFIRM BEFORE CUT"

    @property
    def fill_hex(self) -> str:
        """Actual color on the sheet. Never a lightened stand-in."""
        return (self.plan_hex or self.hex or "#5C4033").strip() or "#5C4033"


@dataclass
class BenchSpec:
    bench_id: str
    name: str
    shape: str  # u_shape | l_shape | straight
    seat_depth_in: float
    back_stack_in: float
    front_overhang_in: float
    channel_height_in: float
    channel_width_in: float
    foam_thickness_in: Optional[float] = None
    seat_height_in: Optional[float] = None
    runs: list[RunSpec] = field(default_factory=list)
    seats: list[SeatBoard] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    board_material: str = '1/2" plywood'
    board_thickness: str = '1/2"'

    def run(self, run_id: str) -> RunSpec:
        for item in self.runs:
            if item.run_id == run_id:
                return item
        raise KeyError(run_id)

    def run_by_role(self, role: str) -> Optional[RunSpec]:
        for item in self.runs:
            if item.role == role:
                return item
        return None

    def open_end_in(self, role: str) -> float:
        run = self.run_by_role(role)
        if run is None:
            return 0.0
        if role in ("main", "long"):
            return float(as_frac(run.back_run_in))
        return float(as_frac(self.back_stack_in) + as_frac(run.back_run_in))


@dataclass
class CutRow:
    label: str
    run_name: str
    part: str
    qty: int
    fabric_label: str
    wood_w: float
    wood_l: float
    foam_thickness_in: Optional[float]
    allowance_in: Optional[float]
    notes: str = ""

    @property
    def wood_size(self) -> str:
        return f"{inch_text(self.wood_w)} x {inch_text(self.wood_l)}"

    @property
    def foam_size(self) -> str:
        thick = inch_text(self.foam_thickness_in) if self.foam_thickness_in else "TBC"
        return f"{self.wood_size} x {thick}"

    @property
    def fabric_size(self) -> str:
        if self.allowance_in is None:
            return NEEDS_FOAM_THICKNESS
        w = fabric_dimension_in(self.wood_w, self.allowance_in)
        l = fabric_dimension_in(self.wood_l, self.allowance_in)
        return f"{inch_text(w)} x {inch_text(l)}"


@dataclass
class YardageLine:
    fabric_label: str
    qty: int
    typical_cut: str
    net_yd: float
    order_yd: float
    notes: str = ""

    @property
    def net_text(self) -> str:
        return f"{inch_text(self.net_yd).rstrip(chr(34))} yd"

    @property
    def order_text(self) -> str:
        return f"{inch_text(self.order_yd).rstrip(chr(34))} yd"


@dataclass
class BanquetteJob:
    client_name: str
    project_name: str
    quote_number: str
    benches: list[BenchSpec]
    seat_fabric: FabricFace
    back_fabric: FabricFace
    foam_thickness_in: Optional[float]
    allowance_in: Optional[float]
    allowance_status: str
    allowance_label: str
    conflicts: list[str] = field(default_factory=list)
    open_items: list[str] = field(default_factory=list)
    revision: str = "A"
    drawn_date: str = ""
    branding: str = "EMPIRE WORKROOM"
    stamp: str = "INTERNAL ONLY — never send to clients"
    draft_banner: str = "DRAFT / INTERNAL"
    subtitle: str = ""
    roll_width_in: float = DEFAULT_ROLL_WIDTH_IN
    extra_notes: list[str] = field(default_factory=list)
    business_unit: str = "workroom"

    @property
    def piece_names(self) -> list[str]:
        return [b.name for b in self.benches]


def channel_option_a(
    run_in: float,
    channel_width_in: float,
    prefix: str,
    *,
    odd_at: str = "open end",
) -> list[ChannelPiece]:
    """Full-width channels plus one odd remainder (Option A).

    odd_at='left' / 'left corner' / 'start' puts the odd board first.
    Otherwise the odd board is at the open end.
    """
    run = as_frac(run_in)
    width = as_frac(channel_width_in)
    if width <= 0:
        raise ValueError("channel_width_in must be > 0")
    if run <= 0:
        raise ValueError("run length must be > 0")
    n_full = int(run // width)
    rem = run - n_full * width
    # Skinny leftover (< half a channel) is not a shop board — fold it into
    # one wider odd piece (37 3/4 → 2×12 + 13 3/4, not 3×12 + 1 3/4).
    if rem > 0 and rem < width / 2 and n_full > 0:
        n_full -= 1
        rem = run - n_full * width
    start_odd = rem > 0 and odd_at.lower() in {"left", "left corner", "start", "corner"}
    pieces: list[ChannelPiece] = []
    if rem > 0 and start_odd:
        pieces.append(ChannelPiece(f"{prefix}-C01", float(rem), True))
    for i in range(n_full):
        idx = len(pieces) + 1
        pieces.append(ChannelPiece(f"{prefix}-C{idx:02d}", float(width), False))
    if rem > 0 and not start_odd:
        idx = len(pieces) + 1
        pieces.append(ChannelPiece(f"{prefix}-C{idx:02d}", float(rem), True))
    assert abs(sum(as_frac(p.width_in) for p in pieces) - run) < Fraction(1, 64)
    return pieces


def split_equal_seats(run_in: float, max_len: float = MAX_SEAT_LENGTH_IN) -> list[float]:
    """Equal seat boards along a run, each ≤ max_len (96\" plywood)."""
    run = float(as_frac(run_in))
    if run <= 0:
        raise ValueError("seat run must be > 0")
    n = max(1, math.ceil(run / max_len - 1e-12))
    each = float(as_frac(run) / n)
    if each > max_len + 1e-9:
        raise ValueError(f"cannot split {inch_text(run)} into boards ≤ {inch_text(max_len)}")
    return [each] * n


def return_seat_length_in(back_stack_in: float, back_run_in: float, seat_depth_in: float) -> float:
    """Return / arm seat butts the main seat front: open-end − seat depth."""
    return float(as_frac(back_stack_in) + as_frac(back_run_in) - as_frac(seat_depth_in))


def _prefix_for(shape: str, role: str, bench_id: str) -> str:
    table = {
        ("u_shape", "main"): "UM",
        ("u_shape", "left"): "UL",
        ("u_shape", "right"): "UR",
        ("l_shape", "long"): "LL",
        ("l_shape", "short"): "LS",
        ("straight", "main"): "SM",
    }
    return table.get((shape, role), f"{(bench_id or 'B')[:2].upper()}{role[:1].upper()}")


def _seat_prefix(shape: str) -> str:
    return {"u_shape": "US", "l_shape": "LS", "straight": "SS"}.get(shape, "S")


def _odd_at_for(role: str) -> str:
    # U main: odd at the left corner. Every other run: odd at the open end.
    return "left corner" if role == "main" else "open end"


def build_runs(
    *,
    shape: str,
    bench_id: str,
    channel_width_in: float,
    segments: dict[str, float],
) -> list[RunSpec]:
    """Build Option-A channel runs from wall-run lengths."""
    order = {
        "u_shape": (("left", "z"), ("main", "x"), ("right", "z")),
        "l_shape": (("long", "x"), ("short", "z")),
        "straight": (("main", "x"),),
    }[shape]
    names = {
        "main": "main",
        "left": "left arm",
        "right": "right arm",
        "long": "long leg",
        "short": "short leg",
    }
    runs: list[RunSpec] = []
    for role, axis in order:
        length = segments.get(role)
        if not length:
            raise ValueError(f"{shape} missing {role} run")
        prefix = _prefix_for(shape, role, bench_id)
        odd_at = _odd_at_for(role)
        label = f"{bench_id} {names[role]}" if bench_id else names[role]
        runs.append(
            RunSpec(
                run_id=prefix,
                name=label,
                role=role,
                axis=axis,
                back_run_in=float(as_frac(length)),
                channels=channel_option_a(length, channel_width_in, prefix, odd_at=odd_at),
                odd_at=odd_at,
                open_end=role != "main" or shape == "straight",
            )
        )
    return runs


def build_seats(
    *,
    shape: str,
    runs: Iterable[RunSpec],
    seat_depth_in: float,
    back_stack_in: float,
    max_len: float = MAX_SEAT_LENGTH_IN,
) -> list[SeatBoard]:
    by_role = {r.role: r for r in runs}
    prefix = _seat_prefix(shape)
    depth = float(as_frac(seat_depth_in))
    seats: list[SeatBoard] = []
    n = 1

    def add(run: RunSpec, length: float, note: str, butts: Optional[str] = None) -> None:
        nonlocal n
        if length > max_len + 1e-9 or depth > MAX_SEAT_DEPTH_IN + 1e-9:
            raise ValueError(f"seat {prefix}{n} exceeds shop max ({inch_text(length)} x {inch_text(depth)})")
        seats.append(
            SeatBoard(
                label=f"{prefix}{n}",
                run_id=run.run_id,
                length_in=float(as_frac(length)),
                depth_in=depth,
                note=note,
                butts_front_of=butts,
            )
        )
        n += 1

    if shape == "u_shape":
        main = by_role["main"]
        parts = split_equal_seats(main.back_run_in, max_len)
        for i, length in enumerate(parts):
            where = "left corner" if i == 0 else ("right corner" if i == len(parts) - 1 else "center")
            add(main, length, f"U main seat {i + 1} of {len(parts)} ({where})")
        left = by_role["left"]
        right = by_role["right"]
        add(
            left,
            return_seat_length_in(back_stack_in, left.back_run_in, depth),
            "butts U main seat front; open end flush",
            main.run_id,
        )
        add(
            right,
            return_seat_length_in(back_stack_in, right.back_run_in, depth),
            "butts U main seat front; open end flush",
            main.run_id,
        )
    elif shape == "l_shape":
        long = by_role["long"]
        parts = split_equal_seats(long.back_run_in, max_len)
        for i, length in enumerate(parts):
            where = "corner" if i == 0 else "open end flush"
            add(long, length, f"L long seat {i + 1} of {len(parts)} ({where})")
        short = by_role["short"]
        add(
            short,
            return_seat_length_in(back_stack_in, short.back_run_in, depth),
            "butts L long seat front; open end flush",
            long.run_id,
        )
    else:
        main = by_role["main"]
        parts = split_equal_seats(main.back_run_in, max_len)
        for i, length in enumerate(parts):
            add(main, length, f"straight seat {i + 1} of {len(parts)}")
    return seats


def joint_notes(bench: BenchSpec) -> list[str]:
    depth = inch_text(bench.seat_depth_in)
    stack = inch_text(bench.back_stack_in)
    ov = inch_text(bench.front_overhang_in)
    lines: list[str] = []
    if bench.shape == "u_shape":
        main = bench.run_by_role("main")
        left = bench.run_by_role("left")
        right = bench.run_by_role("right")
        lines.append(
            f"Corners: U main back runs through both corners; arm backs start at the "
            f"main back face ({stack} from wall) and butt it."
        )
        lines.append(
            f"U main seats run wall-to-front under the backs; arm seats butt the main "
            f"seat front edge (at {depth})."
        )
        if main and left and right:
            lines.append(
                f"Check: U left {stack} + {inch_text(left.back_run_in)} = "
                f"{inch_text(bench.open_end_in('left'))} = {depth} + "
                f"{inch_text(return_seat_length_in(bench.back_stack_in, left.back_run_in, bench.seat_depth_in))}.   "
                f"U right {stack} + {inch_text(right.back_run_in)} = "
                f"{inch_text(bench.open_end_in('right'))} = {depth} + "
                f"{inch_text(return_seat_length_in(bench.back_stack_in, right.back_run_in, bench.seat_depth_in))}."
            )
    elif bench.shape == "l_shape":
        long = bench.run_by_role("long")
        short = bench.run_by_role("short")
        lines.append(
            f"Corner: L long back runs through the corner; short-leg backs start at "
            f"the long back face ({stack}) and butt it."
        )
        lines.append(
            f"L long seats run wall-to-front under the backs; the short-leg seat "
            f"butts the long seat front at {depth}."
        )
        if long and short:
            lines.append(
                f"Check: long {inch_text(long.back_run_in)} = "
                f"{' + '.join(inch_text(s.length_in) for s in bench.seats if s.run_id == long.run_id)}."
            )
            lines.append(
                f"Check: short {stack} + {inch_text(short.back_run_in)} = "
                f"{inch_text(bench.open_end_in('short'))} = {depth} + "
                f"{inch_text(return_seat_length_in(bench.back_stack_in, short.back_run_in, bench.seat_depth_in))}."
            )
    else:
        main = bench.run_by_role("main")
        if main:
            lines.append(
                f"Straight run {inch_text(main.back_run_in)}; seats run wall-to-front "
                f"under the back ({depth})."
            )
    lines.append(
        f"Seat overhangs the base {ov} at the FRONT only; sides and open ends are flush with the base."
    )
    odd_bits = []
    for run in bench.runs:
        for ch in run.odd_channels:
            odd_bits.append(f"{ch.label} {ch.width_text} at {run.odd_at}")
    if odd_bits:
        lines.append("Channel boards stand on the rear of the seat along the wall/shell. Odd pieces: " + "; ".join(odd_bits) + ".")
    else:
        lines.append("Channel boards stand on the rear of the seat along the wall/shell.")
    return lines


def hex_luminance(hex_color: str) -> float:
    raw = (hex_color or "").strip().lstrip("#")
    if len(raw) != 6:
        return 1.0
    r = int(raw[0:2], 16) / 255.0
    g = int(raw[2:4], 16) / 255.0
    b = int(raw[4:6], 16) / 255.0
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def is_dark_hex(hex_color: str, threshold: float = 0.45) -> bool:
    return hex_luminance(hex_color) < threshold


def label_ink_for_fill(hex_color: str) -> str:
    """White type on dark fills so seat labels stay readable."""
    return "#FFFFFF" if is_dark_hex(hex_color) else "#20241f"


def fabric_from_resolved(resolved: dict[str, Any] | None, *, role: str) -> FabricFace:
    from app.services.drawing.client_material import color_hex_for

    src = resolved or {}
    code = src.get("code")
    color = src.get("color")
    label = src.get("label") or "TBC — CONFIRM BEFORE CUT"
    hex_v = color_hex_for(color or code or "", default="#9A5B2E" if role == "back" else "#5C4033")
    # Use the real color on plan / elevation / legend. Dark seats stay dark.
    plan = hex_v
    if role == "back" and "cognac" in f"{color or ''} {code or ''}".lower():
        plan = hex_v
    return FabricFace(
        code=code,
        color=color,
        label=label,
        hex=hex_v,
        plan_hex=plan,
        notes=str(src.get("notes") or ""),
    )


def _allowance_bundle(foam_thickness_in: Optional[float]) -> dict[str, Any]:
    row = lookup_fabric_allowance(foam_thickness_in)
    return {
        "foam_thickness_in": foam_thickness_in,
        "allowance_in": row.get("allowance_in"),
        "allowance_status": row.get("status") or NEEDS_FOAM_THICKNESS,
        "allowance_label": row.get("label") or NEEDS_FOAM_THICKNESS,
    }


def _seat_rows(job: BanquetteJob, bench: BenchSpec) -> list[CutRow]:
    foam = job.foam_thickness_in
    extra = job.allowance_in
    rows: list[CutRow] = []
    for seat in bench.seats:
        rows.append(
            CutRow(
                label=seat.label,
                run_name=next((r.name for r in bench.runs if r.run_id == seat.run_id), seat.run_id),
                part="Seat board",
                qty=1,
                fabric_label=job.seat_fabric.sheet_label,
                wood_w=seat.depth_in,
                wood_l=seat.length_in,
                foam_thickness_in=foam,
                allowance_in=extra,
                notes=seat.note,
            )
        )
    return rows


def _channel_rows(job: BanquetteJob, bench: BenchSpec) -> list[CutRow]:
    foam = job.foam_thickness_in
    extra = job.allowance_in
    rows: list[CutRow] = []
    for run in bench.runs:
        std = run.standard_channels
        if std:
            first, last = std[0], std[-1]
            rows.append(
                CutRow(
                    label=f"{first.label}–{last.label[-3:]}",
                    run_name=run.name,
                    part="Back channel board",
                    qty=len(std),
                    fabric_label=job.back_fabric.sheet_label,
                    wood_w=std[0].width_in,
                    wood_l=bench.channel_height_in,
                    foam_thickness_in=foam,
                    allowance_in=extra,
                    notes=f"{inch_text(std[0].width_in)} channel, vertical",
                )
            )
        for ch in run.odd_channels:
            rows.append(
                CutRow(
                    label=ch.label,
                    run_name=run.name,
                    part="Back channel board (ODD)",
                    qty=1,
                    fabric_label=job.back_fabric.sheet_label,
                    wood_w=ch.width_in,
                    wood_l=bench.channel_height_in,
                    foam_thickness_in=foam,
                    allowance_in=extra,
                    notes=f"ODD channel at {run.odd_at}",
                )
            )
    return rows


def schedule_rows(job: BanquetteJob, *, seats_first: bool = True) -> list[CutRow]:
    rows: list[CutRow] = []
    for bench in job.benches:
        seats = _seat_rows(job, bench)
        channels = _channel_rows(job, bench)
        rows.extend(seats + channels if seats_first else channels + seats)
    return rows


def _orient_on_roll(w: float, l: float, roll: float) -> tuple[int, float]:
    """How many fit across the roll, and inches advanced per row."""
    options = []
    if w <= roll:
        options.append((max(1, int(roll // w)), l))
    if l <= roll:
        options.append((max(1, int(roll // l)), w))
    if not options:
        return 1, max(w, l)
    return max(options, key=lambda t: t[0])


def estimate_yardage(job: BanquetteJob) -> list[YardageLine]:
    rows = schedule_rows(job)
    by_fab: dict[str, list[CutRow]] = {}
    for row in rows:
        by_fab.setdefault(row.fabric_label, []).append(row)
    out: list[YardageLine] = []
    roll = job.roll_width_in or DEFAULT_ROLL_WIDTH_IN
    extra = job.allowance_in
    for label, group in by_fab.items():
        qty = sum(r.qty for r in group)
        typical = group[0]
        pieces: list[tuple[float, float]] = []
        for row in group:
            if extra is None:
                cut_w, cut_l = row.wood_w, row.wood_l
            else:
                cut_w = fabric_dimension_in(row.wood_w, extra)
                cut_l = fabric_dimension_in(row.wood_l, extra)
            pieces.extend([(cut_w, cut_l)] * row.qty)
        ws = [p[0] for p in pieces]
        ls = [p[1] for p in pieces]
        if extra is None:
            typ_w, typ_l = typical.wood_w, typical.wood_l
        else:
            typ_w = fabric_dimension_in(typical.wood_w, extra)
            typ_l = fabric_dimension_in(typical.wood_l, extra)
        if pieces and all(w * 2 <= roll for w in ws) and (max(ls) - min(ls) < 0.2):
            across_shown = 2
            inches = math.ceil(qty / 2) * ls[0]
        elif pieces and all(w > roll / 2 for w in ws):
            across_shown = 1
            inches = sum(ls)
        else:
            across_shown = 1
            inches = 0.0
            for cut_w, cut_l in pieces:
                across, advance = _orient_on_roll(cut_w, cut_l, roll)
                across_shown = max(across_shown, across)
                inches += advance / across
        net = inches / 36.0
        order = net * (1.0 + YARD_EXTRA)
        out.append(
            YardageLine(
                fabric_label=label,
                qty=qty,
                typical_cut=f"{inch_text(typ_w)} x {inch_text(typ_l)}",
                net_yd=net,
                order_yd=order,
                notes=f"{across_shown} across {inch_text(roll)} roll (≈ {int(YARD_EXTRA * 100)}% extra)",
            )
        )
    return out


def result_cut_list(job: BanquetteJob) -> dict[str, Any]:
    """Shape expected by generate_job_drawing / existing desk tests."""
    rows = schedule_rows(job, seats_first=False)
    wood, foam, fabric = [], [], []
    for row in rows:
        wood.append({
            "part": row.part,
            "kind": "wood",
            "label": WOOD_LABEL,
            "width": row.wood_w,
            "length": row.wood_l,
            "size": row.wood_size,
        })
        foam.append({
            "part": row.part,
            "kind": "foam",
            "label": FOAM_LABEL,
            "width": row.wood_w,
            "length": row.wood_l,
            "size": row.wood_size,
        })
        fab_w = fabric_dimension_in(row.wood_w, row.allowance_in) if row.allowance_in is not None else None
        fab_l = fabric_dimension_in(row.wood_l, row.allowance_in) if row.allowance_in is not None else None
        fabric.append({
            "part": row.part,
            "kind": "fabric",
            "label": FABRIC_LABEL,
            "width": fab_w,
            "length": fab_l,
            "size": row.fabric_size,
            "note": "(allowance unconfirmed)" if job.allowance_status == CONFIRM_WITH_RAFAEL else "",
        })
    return {
        "wood": wood,
        "foam": foam,
        "fabric": fabric,
        "allowance": {
            "foam_thickness_in": job.foam_thickness_in,
            "allowance_in": job.allowance_in,
            "status": job.allowance_status,
            "label": job.allowance_label,
        },
        "foam_thickness_in": job.foam_thickness_in,
        "schedule": rows,
    }


def _shape_of(layout: dict[str, Any]) -> str:
    raw = str(layout.get("shape") or "").lower()
    if raw in {"u_shape", "u"}:
        return "u_shape"
    if raw in {"l_shape", "l"}:
        return "l_shape"
    if layout.get("left_in") and layout.get("right_in"):
        return "u_shape"
    if layout.get("short_in") and layout.get("long_in"):
        return "l_shape"
    return "straight"


def _segments_from_layout(layout: dict[str, Any], shape: str) -> dict[str, float]:
    if shape == "u_shape":
        main = layout.get("main_in") or layout.get("width_in")
        return {
            "left": float(layout["left_in"]),
            "main": float(main),
            "right": float(layout["right_in"]),
        }
    if shape == "l_shape":
        return {
            "long": float(layout.get("long_in") or layout.get("width_in")),
            "short": float(layout["short_in"]),
        }
    return {"main": float(layout.get("width_in") or layout.get("main_in"))}


def bench_from_layout(
    layout: dict[str, Any],
    *,
    channel_width_in: float,
    foam_thickness_in: Optional[float],
    index: int = 0,
) -> BenchSpec:
    shape = _shape_of(layout)
    depth = layout.get("depth_in")
    back_h = layout.get("back_height_in")
    if not depth or not back_h:
        raise ValueError("layout missing seat depth or back height")
    assumptions: list[str] = []
    back_stack = layout.get("back_stack_in")
    if back_stack in (None, ""):
        back_stack = foam_thickness_in
        assumptions.append(
            "ASSUMED — CONFIRM BEFORE FABRICATION: back stack in plan = foam thickness "
            "(no ply / finish add-on specified)."
        )
    overhang = layout.get("front_overhang_in")
    if overhang in (None, ""):
        overhang = 1.0
        assumptions.append('ASSUMED — CONFIRM BEFORE FABRICATION: front overhang 1".')
    bench_id = str(layout.get("bench_id") or ("U" if shape == "u_shape" else "L" if shape == "l_shape" else "S"))
    name = str(layout.get("piece_name") or layout.get("project_name") or f"{shape} bench {index + 1}")
    runs = layout.get("runs")
    if runs:
        run_specs = runs
    else:
        run_specs = build_runs(
            shape=shape,
            bench_id=bench_id,
            channel_width_in=channel_width_in,
            segments=_segments_from_layout(layout, shape),
        )
    seats = layout.get("seats") or build_seats(
        shape=shape,
        runs=run_specs,
        seat_depth_in=float(depth),
        back_stack_in=float(back_stack),
    )
    bench = BenchSpec(
        bench_id=bench_id,
        name=name,
        shape=shape,
        seat_depth_in=float(depth),
        back_stack_in=float(back_stack),
        front_overhang_in=float(overhang),
        channel_height_in=float(back_h),
        channel_width_in=float(channel_width_in),
        foam_thickness_in=foam_thickness_in,
        seat_height_in=layout.get("seat_height_in"),
        runs=list(run_specs),
        seats=list(seats),
        notes=list(layout.get("notes") or []),
        assumptions=assumptions,
    )
    if not bench.notes:
        bench.notes = joint_notes(bench)
    return bench


def apply_channel_width(bench: BenchSpec, channel_width_in: float) -> BenchSpec:
    """Rebuild Option-A channels for a revised width. Seat boards stay."""
    segments = {r.role: r.back_run_in for r in bench.runs}
    runs = build_runs(
        shape=bench.shape,
        bench_id=bench.bench_id,
        channel_width_in=channel_width_in,
        segments=segments,
    )
    return replace(bench, channel_width_in=float(channel_width_in), runs=runs, notes=joint_notes(
        replace(bench, channel_width_in=float(channel_width_in), runs=runs)
    ))


def default_open_items(job: BanquetteJob) -> list[str]:
    items: list[str] = []
    if job.allowance_status != "confirmed":
        allow = inch_text(job.allowance_in) if job.allowance_in is not None else "unknown"
        items.append(
            f"Allowance: {inch_text(job.foam_thickness_in) if job.foam_thickness_in else 'TBC'} foam = "
            f"{allow} per side (fabric = wood + 2 × allowance) — CONFIRM."
        )
    for bench in job.benches:
        items.extend(bench.assumptions)
    items.append("Open-end positions — verify on site.")
    return items


def build_banquette_job(
    *,
    layouts: list[dict[str, Any]],
    fabrics: dict[str, Any],
    conflicts: list[str],
    quote: dict[str, Any] | None,
    revision: str,
    drawn_date: str,
    job_hint: str | None = None,
    extra_open_items: list[str] | None = None,
    extra_conflicts: list[str] | None = None,
    subtitle: str | None = None,
) -> BanquetteJob:
    if not layouts:
        raise ValueError("job requires at least one bench layout")
    first = layouts[0]
    foam = first.get("foam_thickness_in")
    channel = first.get("channel_width_in") or DEFAULT_CHANNEL_WIDTH_IN
    benches = [
        bench_from_layout(layout, channel_width_in=float(channel), foam_thickness_in=foam, index=i)
        for i, layout in enumerate(layouts)
    ]
    allow = _allowance_bundle(foam)
    client = (quote or {}).get("customer_name") or first.get("client_name") or job_hint or "Client"
    project = (quote or {}).get("project_name") or first.get("project_name") or f"{client} drawing"
    number = (quote or {}).get("quote_number") or first.get("quote_number") or "INTERNAL"
    seat = fabric_from_resolved(fabrics.get("seat"), role="seat")
    back = fabric_from_resolved(fabrics.get("back"), role="back")
    job = BanquetteJob(
        client_name=str(client),
        project_name=str(project),
        quote_number=str(number),
        benches=benches,
        seat_fabric=seat,
        back_fabric=back,
        foam_thickness_in=foam,
        allowance_in=allow["allowance_in"],
        allowance_status=allow["allowance_status"],
        allowance_label=allow["allowance_label"],
        conflicts=list(conflicts or []) + list(extra_conflicts or []),
        open_items=list(extra_open_items or []),
        revision=revision,
        drawn_date=drawn_date,
        subtitle=subtitle or "FULL LAYOUT (rev)",
    )
    if not job.open_items:
        job.open_items = default_open_items(job)
    return job
