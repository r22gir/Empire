"""Round 10 — bench fabrication param parsing and geometry sums."""
import re

import pytest

from app.services.drawing.bench_fabrication_params import (
    DEFAULT_BACK_ANGLE_DEG,
    DEFAULT_BACK_THICKNESS_IN,
    DEFAULT_SEAT_CUSHION_THICKNESS_IN,
    RAKED_BACK_DEFAULT_DEG,
    parse_bench_fabrication_from_text,
    resolve_bench_fabrication,
)
from app.services.max.tool_executor import execute_tool
from app.services.vision.bench_renderer import render_straight
from app.services.vision.bench_svg_dim_layout import (
    validate_bench_raked_bh_parallel_to_back,
    validate_bench_seat_cushion_consistency,
    validate_bench_seat_overhang_dim,
    validate_bench_side_back_rake_rearward,
    validate_bench_side_seat_dim_stack,
    validate_bench_side_tufts_inside_back,
)


OWNER_A = (
    "straight bench 84 in long, 18 in deep, 18 in high, tufted back 16 in, "
    "2 in foam seat cushion, 3 seat cushions, 2 back cushions"
)
OWNER_B = OWNER_A + ", raked back 10 degrees"


@pytest.mark.parametrize(
    "text,expected",
    [
        ("3 seat cushions, 2 back cushions", {"seat_sections": 3, "back_sections": 2}),
        ("seat in 4 sections", {"seat_sections": 4}),
        ("one-piece back", {"back_sections": 1}),
        ("2 in foam seat cushions", {"seat_cushion_thickness": 2.0}),
        ('4" cushion', {"seat_cushion_thickness": 4.0}),
        ("raked back", {"back_angle_deg": RAKED_BACK_DEFAULT_DEG}),
        ("raked back 10 degrees", {"back_angle_deg": 10.0}),
        ("back lean 10 degrees", {"back_angle_deg": 10.0}),
    ],
)
def test_parse_bench_fabrication_phrases(text, expected):
    got = parse_bench_fabrication_from_text(text)
    for key, val in expected.items():
        assert got.get(key) == val


def test_resolve_defaults_and_section_widths():
    fab = resolve_bench_fabrication(
        width_in=84,
        overall_depth_in=18,
        seat_height_in=18,
        notes="",
        seat_sections_default=4,
    )
    assert fab.seat_cushion_thickness_in == DEFAULT_SEAT_CUSHION_THICKNESS_IN
    assert fab.back_thickness_in == DEFAULT_BACK_THICKNESS_IN
    assert fab.back_angle_deg == DEFAULT_BACK_ANGLE_DEG
    assert fab.seat_sections == 4
    assert fab.back_sections == 4
    assert abs(fab.seat_section_width_in * fab.seat_sections - 84) < 0.01
    assert abs(fab.back_section_width_in * fab.back_sections - 84) < 0.01
    assert abs(fab.seat_cushion_depth_in(18) + fab.back_thickness_in - 18) < 0.01


def test_owner_message_resolves_sections_and_cushion():
    fab = resolve_bench_fabrication(
        width_in=84,
        overall_depth_in=18,
        seat_height_in=18,
        notes=OWNER_A,
        seat_sections_default=4,
    )
    assert fab.seat_sections == 3
    assert fab.back_sections == 2
    assert fab.seat_cushion_thickness_in == 2.0
    assert abs(3 * fab.seat_section_width_in - 84) < 0.01
    assert abs(2 * fab.back_section_width_in - 84) < 0.01
    assert abs(fab.seat_cushion_depth_in(18) + 2 - 18) < 0.01


def _bench_svg_from_owner(msg: str) -> str:
    res = execute_tool({
        "tool": "render_shop_drawing",
        "product_type": "bench",
        "description": msg,
        "dims": {
            "width": 84,
            "depth": 18,
            "seat_height": 18,
            "back_height": 16,
            "panel_style": "tufted",
        },
    })
    assert res.success, res.error
    return res.result["svg"]


def test_owner_vertical_back_svg():
    svg = _bench_svg_from_owner(OWNER_A)
    assert "SEAT CUSHIONS" in svg and "3@28" in svg.replace(" ", "")
    assert "BACK CUSHIONS" in svg and "2@42" in svg.replace(" ", "")
    assert "CUSH" in svg
    assert 'data-back-angle-deg="0.00"' in svg
    validate_bench_side_back_rake_rearward(svg)
    validate_bench_side_seat_dim_stack(svg)
    validate_bench_side_tufts_inside_back(svg)
    validate_bench_seat_cushion_consistency(svg, cushion_in=2.0, deck_in=16.0, seat_h_in=18.0)
    validate_bench_seat_overhang_dim(svg, 1.0)


def test_owner_raked_back_svg():
    svg = _bench_svg_from_owner(OWNER_B)
    assert 'data-back-angle-deg="10.00"' in svg
    validate_bench_side_back_rake_rearward(svg)
    validate_bench_side_seat_dim_stack(svg)
    validate_bench_side_tufts_inside_back(svg)
    validate_bench_seat_cushion_consistency(svg, cushion_in=2.0, deck_in=16.0, seat_h_in=18.0)
    validate_bench_seat_overhang_dim(svg, 1.0)
    validate_bench_raked_bh_parallel_to_back(svg)


def test_render_straight_cushion_subdim():
    svg = render_straight(
        "Bench",
        84,
        depth_in=18,
        seat_h_in=18,
        back_h_in=16,
        panel_style="tufted",
        include_side_elevation=True,
        sheet_kind="shop",
        description=OWNER_A,
    )
    assert '2&quot; CUSH' in svg or '2" CUSH' in svg
