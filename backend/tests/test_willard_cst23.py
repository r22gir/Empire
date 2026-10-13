"""
Tests for Willard CST-23 3D Assembly Model, Layer Engine & WoodCraft Project Data.
Validates:
1. Foam and fabric layers: thickness adjustments and toggles for back and seat.
2. Channel sizing rules:
   - Wood/board cut = true size, no add-ons.
   - Foam cut = same as wood cut.
   - Fabric cut = foam/channel width plus 2 to 3 inches for stapling.
   - Always list wood cut and fabric cut as separate labeled sizes.
   - Fractions only.
   - Custom reviewed piece notice.
3. Armrest options: Laminated END arm vs Slide-in, upholstered face, fringe returns.
4. Revised CNC production pack nesting on 8 sheets (corrects prior 9-sheet artifact),
   with files verified in /workspace/willard_cst23_rev/.
5. Tracked open items (channel height range, empty R24 dado pocket, foam/board thickness).
"""
import os
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.routers.willard_cst23 import router
from app.services.woodcraft.willard_cst23 import (
    format_fraction,
    calculate_cut_schedule,
    get_full_willard_spec,
    ChannelControlInput,
    LayerConfig,
    ArmrestConfig,
    NESTED_SHEETS_DATA,
    OPEN_ITEMS_DATA,
)

app = FastAPI()
app.include_router(router, prefix="/api/v1/craftforge/willard-cst23")
client = TestClient(app)


def test_fraction_formatting_fractions_only():
    """Verify all dimensions format to fractions only."""
    assert format_fraction(9.15625) == '9 5/32"'
    assert format_fraction(36.0) == '36"'
    assert format_fraction(2.5) == '2 1/2"'
    assert format_fraction(0.75) == '3/4"'
    assert format_fraction(0.5) == '1/2"'
    assert format_fraction(5.0) == '5"'
    assert format_fraction(11.65625) == '11 21/32"'
    assert format_fraction(0.0) == '0"'


def test_channel_cut_sizing_rules():
    """Verify core CST-23 sizing rules:
    - Wood/board cut = true size, no add-ons.
    - Foam cut = same as wood cut.
    - Fabric cut = foam/channel width plus 2 to 3 inches for stapling.
    - Separate labeled sizes.
    """
    channel_w = 9.15625  # 9 5/32"
    channel_h = 36.0     # 36"
    stapling = 2.5       # +2 1/2"
    foam_thick = 2.0     # 2"

    items = calculate_cut_schedule(
        channel_count=8,
        channel_width=channel_w,
        channel_height=channel_h,
        stapling_allowance=stapling,
        channel_foam_thickness=foam_thick,
    )

    channel_items = [i for i in items if i.category == "channel"]
    assert len(channel_items) == 8

    for item in channel_items:
        # 1. Wood cut = true size, no add-ons
        assert item.wood_cut_size == '9 5/32" × 36"'
        # 2. Foam cut = same as wood cut footprint
        assert item.foam_cut_size == '9 5/32" × 36" × 2"'
        # 3. Fabric cut = wood + stapling allowance
        assert item.fabric_cut_size == '11 21/32" × 38 1/2"'
        # Dimensions are separate and distinct
        assert item.wood_cut_size != item.fabric_cut_size


def test_custom_piece_rule_precedence():
    """Verify Willard CST-23 is marked as a reviewed custom piece."""
    spec = get_full_willard_spec()
    assert spec.status == "Reviewed Custom Piece"
    assert "Willard CST-23 is a reviewed custom piece" in spec.reviewed_rule_notice
    assert "Wood/board cut = true size, no add-ons" in spec.reviewed_rule_notice


def test_foam_and_fabric_layer_adjustments():
    """Verify foam and fabric layer thickness adjustability."""
    # Test adjusted back foam 3" and seat foam 6"
    spec = get_full_willard_spec(
        channel_foam_thickness=3.0,
        seat_foam_thickness=6.0,
    )
    assert spec.layers.back_foam_thickness == 3.0
    assert spec.layers.seat_foam_thickness == 6.0
    assert spec.dimensions["channel_foam_thickness"] == '3"'
    assert spec.dimensions["seat_foam_thickness"] == '6"'

    # Check cut schedule reflects adjusted foam
    ch1 = next(i for i in spec.cut_schedule if i.part_id == "CH-01")
    assert '3"' in ch1.foam_cut_size

    cush_l = next(i for i in spec.cut_schedule if i.part_id == "CUSH-L")
    assert '6"' in cush_l.foam_cut_size


def test_armrest_options():
    """Verify laminated END arm vs slide-in, plus upholstered/fringe options."""
    # Option A: Laminated END arm, upholstered, with fringe
    spec_a = get_full_willard_spec(
        arm_type="laminated_end",
        upholstered_arm=True,
        fringe=True,
    )
    assert spec_a.armrests.arm_type == "laminated_end"
    assert spec_a.armrests.upholstered is True
    assert spec_a.armrests.fringe is True
    arm_item_a = next(i for i in spec_a.cut_schedule if i.part_id == "ARM-01")
    assert "Laminated End" in arm_item_a.part_name
    assert "Vinyl Wrap" in arm_item_a.material

    # Option B: Slide-in, exposed wood, no fringe
    spec_b = get_full_willard_spec(
        arm_type="slide_in",
        upholstered_arm=False,
        fringe=False,
    )
    assert spec_b.armrests.arm_type == "slide_in"
    assert spec_b.armrests.upholstered is False
    assert spec_b.armrests.fringe is False
    arm_item_b = next(i for i in spec_b.cut_schedule if i.part_id == "ARM-01")
    assert "Slide In" in arm_item_b.part_name
    assert arm_item_b.fabric_cut_size == "N/A (Exposed Wood Finish)"
    assert not any(i.category == "trim" for i in spec_b.cut_schedule)


def test_revised_8_sheet_nesting_pack():
    """Verify revised pack nests on 8 sheets (not 9) and files exist in /workspace/willard_cst23_rev/."""
    assert NESTED_SHEETS_DATA["total_sheets"] == 8
    assert "8 sheets" in NESTED_SHEETS_DATA["artifact_vs_revised_note"]
    assert len(NESTED_SHEETS_DATA["sheets"]) == 8

    # Verify physical files on Chief e's box
    base_dir = "/workspace/willard_cst23_rev"
    assert os.path.isdir(base_dir), f"Directory {base_dir} must exist"

    pdf_file = os.path.join(base_dir, "Willard_CST23_RevPack_CutList.pdf")
    assert os.path.isfile(pdf_file), f"Cut list PDF must exist at {pdf_file}"
    assert os.path.getsize(pdf_file) > 100

    zip_file = os.path.join(base_dir, "Willard_CST23_Revised_Pack.zip")
    assert os.path.isfile(zip_file), f"ZIP pack must exist at {zip_file}"
    assert os.path.getsize(zip_file) > 500

    # Verify 25 nested SVGs exist
    for i in range(1, 26):
        svg_file = os.path.join(base_dir, f"svg_nested_{i:02d}.svg")
        assert os.path.isfile(svg_file), f"SVG file {svg_file} must exist"


def test_tracked_open_items():
    """Verify open items tracking under WoodCraft by Empire:
    1. Channel height range
    2. Empty R24 dado pocket
    3. Foam/board thickness
    Fractions only.
    """
    assert len(OPEN_ITEMS_DATA) == 3
    ids = [item["id"] for item in OPEN_ITEMS_DATA]
    titles = [item["title"] for item in OPEN_ITEMS_DATA]

    assert "Channel height range" in titles
    assert "Empty R24 dado pocket" in titles
    assert "Foam/board thickness" in titles

    # Fractions check in specs and ranges
    for item in OPEN_ITEMS_DATA:
        assert '"' in item["range"] or "radius" in item["range"]
        assert item["status"] == "OPEN"


def test_fastapi_endpoints():
    """Test API router endpoints."""
    # 1. Spec endpoint
    res = client.get("/api/v1/craftforge/willard-cst23/spec")
    assert res.status_code == 200
    data = res.json()
    assert data["project_id"] == "WC-PRJ-CST23"
    assert data["sheet_nesting"]["total_sheets"] == 8

    # 2. Sizing endpoint
    payload = {
        "channel_count": 8,
        "channel_width": 9.15625,
        "channel_height": 36.0,
        "stapling_allowance": 2.5,
        "channel_depth": 2.0,
    }
    res_size = client.post("/api/v1/craftforge/willard-cst23/sizing", json=payload)
    assert res_size.status_code == 200
    size_data = res_size.json()
    assert size_data["wood_cut_labeled"]["size"] == '9 5/32" × 36"'
    assert size_data["foam_cut_labeled"]["size"] == '9 5/32" × 36" × 2"'
    assert size_data["fabric_cut_labeled"]["size"] == '11 21/32" × 38 1/2"'

    # 3. Cut sheets endpoint
    res_sheets = client.get("/api/v1/craftforge/willard-cst23/cut-sheets")
    assert res_sheets.status_code == 200
    assert res_sheets.json()["total_sheets"] == 8

    # 4. Open items endpoint
    res_items = client.get("/api/v1/craftforge/willard-cst23/open-items")
    assert res_items.status_code == 200
    assert len(res_items.json()["open_items"]) == 3
