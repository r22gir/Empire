"""WoodCraft bench quote → diagram idea transmission.

Covers the quote-diagram bar: flat is not rewritten to channels, a short
bench stays in inches, and a WoodCraft sheet is labeled WC instead of
Empire Workroom upholstery letterhead.
"""
import asyncio

from app.routers import craftforge, drawings
from app.services.drawing.bench_quote_bridge import (
    BENCH_BACK_HEIGHT_DEFAULT_IN,
    map_craftforge_design,
    resolve_back_height,
    resolve_sketch_bench,
)


def _svg(req: drawings.BenchRequest) -> dict:
    return asyncio.run(drawings.generate_bench_svg(req))


def test_flat_panel_is_not_coerced_to_channels():
    out = _svg(drawings.BenchRequest(
        name="Plain back",
        width_in=66,
        seat_depth=20,
        seat_height=18,
        back_height=18,
        panel_style="flat",
        has_back=True,
    ))
    svg = out["svg"]
    assert out["resolved"]["panel_style"] == "flat"
    assert out["resolved"]["has_back"] is True
    assert "FLAT BACK" in svg
    assert "CHANNELED BACK" not in svg
    assert 'stroke-width="0.3"' not in svg
    assert "WR · FREESTANDING BENCH · FLAT" in svg


def test_no_back_stays_backless():
    out = _svg(drawings.BenchRequest(
        name="Backless",
        width_in=48,
        seat_depth=18,
        seat_height=18,
        panel_style="flat",
        has_back=False,
    ))
    svg = out["svg"]
    assert out["resolved"]["has_back"] is False
    assert out["resolved"]["back_height_assumed"] is False
    assert "NO BACK" in svg
    assert "CHANNELED BACK" not in svg
    assert "FLAT BACK" not in svg
    assert 'stroke-width="0.3"' not in svg
    assert "WR · FREESTANDING BENCH · NO BACK" in svg


def test_channeled_still_draws_channels_and_passes_counts():
    out = _svg(drawings.BenchRequest(
        name="Channeled",
        width_in=60,
        seat_depth=20,
        seat_height=18,
        back_height=34,
        panel_style="vertical_channels",
        has_back=True,
        cushion_width=20,
        channel_count=4,
    ))
    svg = out["svg"]
    assert out["resolved"]["panel_style"] == "vertical_channels"
    assert out["resolved"]["channel_count"] == 4
    assert out["resolved"]["cushion_width"] == 20
    assert out["resolved"]["back_height"] == 34
    assert out["resolved"]["back_height_assumed"] is False
    assert "CHANNELED BACK" in svg
    assert "FLAT BACK" not in svg
    assert 'stroke-width="0.3"' in svg
    assert "3 @ 20&quot;" in svg
    assert "WR · FREESTANDING BENCH · CHANNELED" in svg


def test_short_width_is_inches_unless_unit_is_feet():
    inches = _svg(drawings.BenchRequest(
        name="Thirty six",
        lf=36,
        seat_depth=20,
        seat_height=18,
        back_height=18,
        panel_style="flat",
    ))
    assert inches["resolved"]["width_in"] == 36
    assert "36&quot; W" in inches["svg"]
    assert "432&quot;" not in inches["svg"]

    feet = _svg(drawings.BenchRequest(
        name="Three feet",
        lf=3,
        length_unit="ft",
        seat_depth=20,
        seat_height=18,
        back_height=18,
        panel_style="flat",
    ))
    assert feet["resolved"]["width_in"] == 36
    assert "36&quot; W" in feet["svg"]


def test_omitted_back_height_uses_one_default_and_marks_assumed():
    out = _svg(drawings.BenchRequest(
        name="Needs BH",
        width_in=72,
        has_back=True,
        panel_style="flat",
    ))
    assert out["resolved"]["back_height"] == BENCH_BACK_HEIGHT_DEFAULT_IN
    assert out["resolved"]["back_height_assumed"] is True
    assert "ASSUMED — CONFIRM BEFORE FABRICATION" in out["svg"]

    height, assumed = resolve_back_height(None)
    assert height == 18
    assert assumed is True
    height, assumed = resolve_back_height(34)
    assert height == 34
    assert assumed is False


def test_sketch_path_matches_api_back_height_and_inches():
    omitted = resolve_sketch_bench({"shape": "straight", "lf": 10, "panel_style": "flat"})
    assert omitted["width_in"] == 120  # documented lf is feet
    assert omitted["back_height"] == 18
    assert omitted["back_height_assumed"] is True
    assert omitted["panel_style"] == "flat"

    short = resolve_sketch_bench({
        "shape": "straight",
        "width": 36,
        "panel_style": "flat",
        "business_unit": "woodcraft",
        "has_back": True,
        "back_height": 18,
    })
    assert short["width_in"] == 36
    assert short["category_chip"] == "WC · FREESTANDING BENCH · FLAT"
    assert short["chrome"]["company"] == "WOODCRAFT BY EMPIRE"
    assert "WORKROOM" not in short["chrome"]["company"]


def test_woodcraft_chrome_and_category_chip():
    out = _svg(drawings.BenchRequest(
        name="Shop bench",
        width_in=66,
        seat_depth=20,
        seat_height=18,
        back_height=18,
        panel_style="vertical_channels",
        has_back=True,
        business_unit="woodcraft",
        product_type="freestanding_bench",
        channel_count=6,
    ))
    svg = out["svg"]
    assert out["resolved"]["category_chip"] == "WC · FREESTANDING BENCH · CHANNELED"
    assert "WC · FREESTANDING BENCH · CHANNELED" in svg
    assert "WOODCRAFT BY EMPIRE" in svg
    assert "CUSTOM WOODWORK" in svg
    assert "EMPIRE WORKROOM" not in svg
    assert "CUSTOM UPHOLSTERY" not in svg
    assert "CHANNELED BACK" in svg


def test_craftforge_furniture_bench_maps_optional_back_without_channels():
    design = {
        "category": "furniture",
        "style": "modern",
        "project_name": "Mock Max WoodCraft bench",
        "design_number": "CF-2026-011",
        "unit": "in",
        "dimensions": {"width_in": 66.0, "depth_in": 20.0, "height_in": 18.0, "unit": "in"},
        "line_items": [{
            "description": (
                'Freestanding bench — 66" L × 20" D × 18" H seat · optional back rail'
            ),
        }],
    }
    mapped = map_craftforge_design(design)
    assert mapped.connected is True
    assert mapped.params["width_in"] == 66
    assert mapped.params["seat_depth"] == 20
    assert mapped.params["seat_height"] == 18
    assert mapped.params["has_back"] is False
    assert mapped.params["business_unit"] == "woodcraft"
    assert mapped.params["panel_style"] == "none"
    assert mapped.category_chip == "WC · FREESTANDING BENCH · NO BACK"
    assert "OPTIONAL BACK" in mapped.params["diagram_note"]

    out = _svg(drawings.BenchRequest(**mapped.params))
    assert "WOODCRAFT BY EMPIRE" in out["svg"]
    assert "EMPIRE WORKROOM" not in out["svg"]
    assert "NO BACK" in out["svg"]
    assert "OPTIONAL BACK" in out["svg"]
    assert "CHANNELED BACK" not in out["svg"]
    assert "66&quot; W" in out["svg"]
    assert "432&quot;" not in out["svg"]


def test_craftforge_channeled_bench_keeps_quote_back_height():
    design = {
        "category": "furniture",
        "name": "Channeled freestanding bench",
        "unit": "in",
        "width": 72,
        "depth": 22,
        "height": 18,
        "back_height": 34,
        "panel_style": "vertical_channels",
        "has_back": True,
        "channel_count": 5,
        "cushion_width": 24,
        "line_items": [{"description": "Freestanding bench with channeled back"}],
    }
    mapped = map_craftforge_design(design)
    assert mapped.connected is True
    assert mapped.params["back_height"] == 34
    assert mapped.params["panel_style"] == "vertical_channels"
    assert mapped.params["has_back"] is True
    assert mapped.params["channel_count"] == 5
    assert mapped.category_chip == "WC · FREESTANDING BENCH · CHANNELED"

    out = _svg(drawings.BenchRequest(**mapped.params))
    assert out["resolved"]["back_height"] == 34
    assert out["resolved"]["back_height_assumed"] is False
    assert "CHANNELED BACK" in out["svg"]
    assert "WC · FREESTANDING BENCH · CHANNELED" in out["svg"]
    assert 'stroke-width="0.3"' in out["svg"]


def test_craftforge_non_bench_is_not_forced_onto_the_bench_sheet():
    mapped = map_craftforge_design({
        "category": "cornice",
        "name": "Straight cornice",
        "width": 84,
        "height": 8,
        "depth": 6,
    })
    assert mapped.connected is False
    assert mapped.category == "cornice"


def test_design_diagram_route_renders_mapped_bench(monkeypatch):
    design = {
        "id": "cf-bench",
        "design_number": "CF-2026-011",
        "category": "furniture",
        "name": "Freestanding bench",
        "unit": "in",
        "width": 66,
        "depth": 20,
        "height": 18,
        "panel_style": "flat",
        "has_back": True,
        "back_height": 18,
    }
    monkeypatch.setattr(craftforge, "_load", lambda directory, design_id: design)
    out = asyncio.run(craftforge.design_bench_diagram("cf-bench"))
    assert out["diagram"]["connected"] is True
    assert out["diagram"]["category_chip"] == "WC · FREESTANDING BENCH · FLAT"
    assert "FLAT BACK" in out["svg"]
    assert "WOODCRAFT BY EMPIRE" in out["svg"]
    assert "EMPIRE WORKROOM" not in out["svg"]
    assert "66&quot; W" in out["svg"]
