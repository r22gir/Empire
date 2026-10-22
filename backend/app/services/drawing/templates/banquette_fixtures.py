"""Named prior-layout fixtures for the banquette shop-drawing template.

These are job specs (measurements + notes), not renderer code. The
11x17 template consumes BanquetteJob the same way for any client.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any

from app.services.drawing.templates.banquette_job import (
    BanquetteJob,
    BenchSpec,
    FabricFace,
    build_runs,
    build_seats,
    default_open_items,
    joint_notes,
)

# Marley's Hyattsville — prior layout that produced the 2026-10-21
# four-page internal set. Seat depth 20 9/16" (seat runs under backs).
_D = float(Fraction(329, 16))       # 20 9/16
_BK = float(Fraction(41, 16))       # 2 9/16 wall to back face
_OV = 1.0
_CH = float(Fraction(107, 4))       # 26 3/4
_FOAM = 2.0
_CH_W = 12.0
# Current Marley's spec (Rafael): Black seats = V001-Raven, Cognac backs = V003-Cognac.
MARLEYS_SEAT_CODE = "V001-Raven"
MARLEYS_SEAT_COLOR = "Black"
MARLEYS_BACK_CODE = "V003-Cognac"
MARLEYS_BACK_COLOR = "Cognac"
_UM = float(Fraction(999, 4))       # 249 3/4
_UL = float(Fraction(151, 4))       # 37 3/4
_UR = float(Fraction(97, 2))        # 48 1/2
_LL = float(Fraction(431, 4))       # 107 3/4
_LS = float(Fraction(763, 8))       # 95 3/8


def _marleys_u_bench() -> BenchSpec:
    runs = build_runs(
        shape="u_shape",
        bench_id="U",
        channel_width_in=_CH_W,
        segments={"left": _UL, "main": _UM, "right": _UR},
    )
    seats = build_seats(
        shape="u_shape",
        runs=runs,
        seat_depth_in=_D,
        back_stack_in=_BK,
    )
    bench = BenchSpec(
        bench_id="U",
        name="U Booth",
        shape="u_shape",
        seat_depth_in=_D,
        back_stack_in=_BK,
        front_overhang_in=_OV,
        channel_height_in=_CH,
        channel_width_in=_CH_W,
        foam_thickness_in=_FOAM,
        seat_height_in=18.0,
        runs=runs,
        seats=seats,
        notes=[],
    )
    bench.notes = joint_notes(bench)
    return bench


def _marleys_l_bench() -> BenchSpec:
    runs = build_runs(
        shape="l_shape",
        bench_id="L",
        channel_width_in=_CH_W,
        segments={"long": _LL, "short": _LS},
    )
    seats = build_seats(
        shape="l_shape",
        runs=runs,
        seat_depth_in=_D,
        back_stack_in=_BK,
    )
    bench = BenchSpec(
        bench_id="L",
        name="L Booth",
        shape="l_shape",
        seat_depth_in=_D,
        back_stack_in=_BK,
        front_overhang_in=_OV,
        channel_height_in=_CH,
        channel_width_in=_CH_W,
        foam_thickness_in=_FOAM,
        seat_height_in=18.0,
        runs=runs,
        seats=seats,
        notes=[
            "Short-leg open end is modeled from the long-leg wall; field sketch outer "
            "includes the shell — VERIFY ON SITE.",
        ],
    )
    bench.notes = joint_notes(bench) + bench.notes
    return bench


def marleys_job_layouts() -> list[dict[str, Any]]:
    """Layout dicts for job_set_layouts / resolve_layout."""
    u = _marleys_u_bench()
    l = _marleys_l_bench()
    return [
        {
            "source": "prior_layout_preset",
            "preset": "marleys_u",
            "shape": "u_shape",
            "width_in": _UM,
            "main_in": _UM,
            "left_in": _UL,
            "right_in": _UR,
            "depth_in": _D,
            "back_height_in": _CH,
            "back_stack_in": _BK,
            "channel_width_in": _CH_W,
            "foam_thickness_in": _FOAM,
            "front_overhang_in": _OV,
            "seat_height_in": 18.0,
            "client_name": "Marley's",
            "project_name": "Marley's Hyattsville",
            "quote_number": "EST-2026-299",
            "piece_name": "U Booth",
            "bench_id": "U",
        },
        {
            "source": "prior_layout_preset",
            "preset": "marleys_l",
            "shape": "l_shape",
            "width_in": _LL,
            "long_in": _LL,
            "short_in": _LS,
            "depth_in": _D,
            "back_height_in": _CH,
            "back_stack_in": _BK,
            "channel_width_in": _CH_W,
            "foam_thickness_in": _FOAM,
            "front_overhang_in": _OV,
            "seat_height_in": 18.0,
            "client_name": "Marley's",
            "project_name": "Marley's Hyattsville",
            "quote_number": "EST-2026-299",
            "piece_name": "L Booth",
            "bench_id": "L",
        },
    ]


def marleys_standard_job(
    *,
    seat_fabric: FabricFace | None = None,
    back_fabric: FabricFace | None = None,
    revision: str = "A",
    drawn_date: str = "",
    extra_conflicts: list[str] | None = None,
) -> BanquetteJob:
    """Full U+L job. Default seat is V001-Raven (Black), backs V003-Cognac."""
    seat = seat_fabric or FabricFace(
        code=MARLEYS_SEAT_CODE,
        color=MARLEYS_SEAT_COLOR,
        label=MARLEYS_SEAT_CODE,
        hex="#1C1C1C",
        plan_hex="#1C1C1C",
    )
    back = back_fabric or FabricFace(
        code=MARLEYS_BACK_CODE,
        color=MARLEYS_BACK_COLOR,
        label=MARLEYS_BACK_CODE,
        hex="#9A5B2E",
        plan_hex="#c98b55",
    )
    job = BanquetteJob(
        client_name="Marley's",
        project_name="Marley's Hyattsville",
        quote_number="EST-2026-299",
        benches=[_marleys_u_bench(), _marleys_l_bench()],
        seat_fabric=seat,
        back_fabric=back,
        foam_thickness_in=_FOAM,
        allowance_in=5.0,
        allowance_status="confirm_with_rafael",
        allowance_label='2" foam — wrap both faces + 1" sew (confirm with Rafael)',
        conflicts=list(extra_conflicts or []) + [
            "EST-2026-299 rev B priced seat cushions at 18\" deep — this drawing uses 20 9/16\" (pricing not updated).",
            "EST-2026-299 rev B listed seat cushions in Cognac — seats are V001-Raven (Black); vinyl line / yardage will change.",
            "Arm / short-leg seats were priced at full back-run length; actual seat boards butt the main / long seat.",
            "Oct 6 layout showed basketweave-square back modules — this rev is all 12\" channel backs, Option A odd channels.",
            "No estimate or client document was changed. This sheet is internal only.",
        ],
        open_items=[
            "Channel height: 26 3/4\" (cut list / estimate) vs 30\" (L) to 30 1/4\" (U) on the field sketch.",
            "Seat depth: 20 9/16\" (seat runs under backs, this drawing) vs 18\" alternate.",
            "Allowance: 2\" foam = 5\" per side (fabric = wood + 10\") — CONFIRM.",
            "Seat vinyl is V001-Raven (Black). Channel backs are V003-Cognac.",
            "Open-end positions & one L end near the wall / fire alarm — verify on site.",
        ],
        revision=revision,
        drawn_date=drawn_date,
        subtitle="FULL U + L LAYOUT (rev)",
    )
    if not job.open_items:
        job.open_items = default_open_items(job)
    return job


def job_default_fabrics(job_hint: str | None) -> dict[str, str]:
    """Seat/back codes for a named job when the turn does not change them."""
    key = (job_hint or "").strip().lower().replace("'", "")
    if "marley" in key:
        return {"seat": MARLEYS_SEAT_CODE, "back": MARLEYS_BACK_CODE}
    return {}


def known_job_layouts(job_hint: str | None) -> list[dict[str, Any]]:
    key = (job_hint or "").strip().lower().replace("'", "")
    if "marley" in key:
        return marleys_job_layouts()
    return []


def known_job_spec(job_hint: str | None) -> BanquetteJob | None:
    key = (job_hint or "").strip().lower().replace("'", "")
    if "marley" in key:
        return marleys_standard_job()
    return None
