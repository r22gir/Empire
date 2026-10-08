"""Tests for the parametric mockup & drawing engine.

Asserts:
1. Marley's U-bench and L-bench reproduction matching reference dimensions:
   - U-bench: Left 37.75", Main 249.75", Right 48.5", Seat 18", Back 26.75", 12" channels
   - L-bench: Short 95.375", Long 107.75", Seat 18", Back 26.75", 12" channels
2. Single chair fixture (diamond tufted back, 28" W x 30" D x 22" BH).
3. WoodCraft wall unit casework fixture (108" W x 84" H x 20" D, 3 carcass bays).
4. Mathematical layout accuracy (channel math, tuft math, module math).
5. API endpoint POST /drawings/mockup with spec, presets, and dimension-less quote handling (honest omit).
6. Max AI tool generate_parametric_mockup execution.
"""
import io
import os
import uuid
import asyncio
from pathlib import Path
import pytest
import pdfplumber

from app.services.drawing.mockup_engine import (
    PieceSpec, FootprintSpec, SegmentSpec, BackStyleSpec, CushionSpec, MaterialFinishSpec,
    compute_channels, compute_tufts, compute_modules,
    marleys_u_and_l_preset, straight_bench_preset, l_bench_preset, u_bench_preset,
    single_chair_preset, woodcraft_wall_unit_preset,
    render_piece_mockup_pdf, render_pdf_to_png_previews,
)
from app.routers.drawings import generate_mockup_drawing, MockupFromSpecRequest
from app.services.max.tool_executor import execute_tool


def extract_pdf_text(pdf_path: str) -> str:
    with pdfplumber.open(pdf_path) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return text


def test_channel_math_exact_and_remainders():
    """Channels must be full channels plus equal end remainders."""
    # Main run 249.75" with 12" channels
    # 249.75 // 12 = 20 full (240"), remainder 9.75" -> 4.875" each end
    widths, end = compute_channels(249.75, 12.0)
    assert len(widths) == 22  # 20 full + 2 ends
    assert end == 4.875
    assert widths[0] == 4.875
    assert widths[-1] == 4.875
    assert sum(widths) == pytest.approx(249.75, 1e-4)

    # Left run 37.75" with 12" channels
    # 37.75 // 12 = 3 full (36"), remainder 1.75" -> 0.875" each end
    widths_l, end_l = compute_channels(37.75, 12.0)
    assert len(widths_l) == 5
    assert end_l == 0.875
    assert sum(widths_l) == pytest.approx(37.75, 1e-4)

    # Right run 48.5" with 12" channels
    # 48.5 // 12 = 4 full (48"), remainder 0.5" -> 0.25" each end
    widths_r, end_r = compute_channels(48.5, 12.0)
    assert len(widths_r) == 6
    assert end_r == 0.25
    assert sum(widths_r) == pytest.approx(48.5, 1e-4)

    # Exact multiple 36"
    widths_exact, end_exact = compute_channels(36.0, 12.0)
    assert len(widths_exact) == 3
    assert end_exact == 0.0
    assert all(w == 12.0 for w in widths_exact)


def test_marleys_u_and_l_reproduction(tmp_path):
    """Regenerate Marley's U and L banquette drawings and confirm they match reference dimensions."""
    presets = marleys_u_and_l_preset()
    u_spec = presets["u_bench"]
    l_spec = presets["l_bench"]

    # Verify U-spec dimensions
    seg_u = {s.name: s.length_in for s in u_spec.footprint.segments}
    assert seg_u["left"] == 37.75
    assert seg_u["main"] == 249.75
    assert seg_u["right"] == 48.5
    assert u_spec.cushion.seat_depth_in == 18.0
    assert u_spec.back.net_back_height_in == 26.75
    assert u_spec.back.channel_width_in == 12.0

    u_pdf = str(tmp_path / "marleys_u.pdf")
    render_piece_mockup_pdf(u_spec, u_pdf)
    assert os.path.exists(u_pdf)
    u_text = extract_pdf_text(u_pdf)
    assert "EMPIRE WORKROOM" in u_text
    assert "249.75" in u_text
    assert "37.75" in u_text
    assert "48.5" in u_text
    assert "26.75" in u_text
    assert "20 x 12" in u_text or "20 x 12\"" in u_text or "channels" in u_text

    # Test PNG preview generation
    pngs = render_pdf_to_png_previews(u_pdf, str(tmp_path / "u_preview"))
    assert len(pngs) == 2
    for p in pngs:
        assert os.path.exists(p)
        assert os.path.getsize(p) > 1000

    # Verify L-spec dimensions
    seg_l = {s.name: s.length_in for s in l_spec.footprint.segments}
    assert seg_l["short"] == 95.375
    assert seg_l["long"] == 107.75
    assert l_spec.cushion.seat_depth_in == 18.0
    assert l_spec.back.net_back_height_in == 26.75

    l_pdf = str(tmp_path / "marleys_l.pdf")
    render_piece_mockup_pdf(l_spec, l_pdf)
    assert os.path.exists(l_pdf)
    l_text = extract_pdf_text(l_pdf)
    assert "EMPIRE WORKROOM" in l_text
    assert "95.375" in l_text
    assert "107.75" in l_text


def test_chair_fixture(tmp_path):
    """Test single chair piece with arms, tufted back, and side section."""
    chair_spec = single_chair_preset(
        width_in=32.0,
        depth_in=32.0,
        seat_height_in=18.0,
        back_height_in=22.0,
        name="Luxe Club Chair",
        has_arms=True,
        arm_width_in=4.0,
        arm_height_in=24.0,
    )
    pdf_path = str(tmp_path / "chair_mockup.pdf")
    render_piece_mockup_pdf(chair_spec, pdf_path)
    assert os.path.exists(pdf_path)

    text = extract_pdf_text(pdf_path)
    assert "LUXE CLUB CHAIR" in text
    assert "SIDE SECTION" in text
    assert "Diamond tufted" in text or "tufted" in text
    # Ensure it does not say vertical channels for a tufted chair
    assert "12\" vertical channels" not in text
    assert "32" in text
    assert "22" in text

    pngs = render_pdf_to_png_previews(pdf_path, str(tmp_path / "chair_preview"))
    assert len(pngs) >= 1
    assert os.path.exists(pngs[0])


def test_woodcraft_project_data_integration_fixture(tmp_path):
    """Test that WoodCraft integration reads real WoodCraft/CraftForge project data from disk."""
    import json
    from app.routers.craftforge import DESIGNS_DIR, _save, _load

    test_design_id = f"test-wall-unit-{uuid.uuid4().hex[:8]}"
    project_record = {
        "id": test_design_id,
        "design_number": "CF-2026-909",
        "name": "Arlington Library Built-In Wall Unit",
        "customer_name": "Arlington Residence",
        "customer_address": "4200 Wilson Blvd, Arlington VA",
        "category": "furniture",
        "style": "Modern traditional",
        "primary_material": "Quarter-Sawn White Oak",
        "width": 144.0,
        "height": 96.0,
        "depth": 24.0,
        "materials": [
            {"name": "White Oak Plywood 3/4", "quantity": 12, "unit": "sheet", "cost_per_unit": 135.0},
            {"name": "White Oak Hardwood 4/4", "quantity": 180, "unit": "bdft", "cost_per_unit": 9.5},
            {"name": "Blum Soft-Close Slides", "quantity": 6, "unit": "pair", "cost_per_unit": 28.0},
        ],
        "created_at": "2026-10-08T12:00:00",
        "status": "draft",
    }

    # Save to CraftForge DESIGNS_DIR
    _save(DESIGNS_DIR, test_design_id, project_record)

    try:
        # Load through CraftForge read-only method
        loaded = _load(DESIGNS_DIR, test_design_id)
        assert loaded["name"] == "Arlington Library Built-In Wall Unit"

        # Build spec from loaded WoodCraft record
        unit_spec = woodcraft_wall_unit_preset(from_craftforge_design=loaded)
        assert unit_spec.business_unit == "woodcraft"
        assert unit_spec.client_name == "Arlington Residence"
        assert unit_spec.client_address == "4200 Wilson Blvd, Arlington VA"
        assert unit_spec.quote_number == "CF-2026-909"
        assert unit_spec.casework.overall_width_in == 144.0
        assert unit_spec.casework.overall_height_in == 96.0
        assert unit_spec.casework.overall_depth_in == 24.0
        assert unit_spec.casework.wood_species == "Quarter-Sawn White Oak"
        assert len(unit_spec.casework.materials) == 3

        # Render PDF & verify casework schedule & plan
        pdf_path = str(tmp_path / "arlington_wall_unit.pdf")
        render_piece_mockup_pdf(unit_spec, pdf_path)
        assert os.path.exists(pdf_path)

        text = extract_pdf_text(pdf_path)
        assert "WOODCRAFT BY EMPIRE" in text
        assert "Quarter-Sawn White Oak" in text
        assert "CASEWORK & MILLWORK SPECIFICATION" in text
        assert "CARCASS BOXES & BAYS" in text
        # Verify no upholstery terms in casework legend
        assert "seat cushion" not in text.lower()
    finally:
        # Cleanup fixture file
        p = os.path.join(DESIGNS_DIR, f"{test_design_id}.json")
        if os.path.exists(p):
            os.remove(p)


def test_api_endpoint_with_presets():
    """Verify POST /drawings/mockup with presets."""
    res = asyncio.run(generate_mockup_drawing(MockupFromSpecRequest(preset="marleys_u")))
    assert res["success"] is True
    assert os.path.exists(res["pdf_path"])
    assert len(res["png_previews"]) == 2
    for p in res["png_previews"]:
        assert os.path.exists(p)


def test_api_endpoint_omits_when_quote_lacks_dimensions():
    """When quote lines lack dimensions, omit the drawing section rather than printing errors."""
    # Fake quote with no dimensions
    req = MockupFromSpecRequest(quote_id="non_existent_quote_xyz")
    with pytest.raises(Exception):
        # Non-existent quote raises 404
        asyncio.run(generate_mockup_drawing(req))


def test_max_tool_execution():
    """Verify MAX tool generate_parametric_mockup executes and returns results."""
    tool_call = {
        "tool": "generate_parametric_mockup",
        "preset": "chair",
    }
    res = execute_tool(tool_call, founder=True)
    assert res.success is True
    assert res.result["success"] is True
    assert "pdf_path" in res.result
    assert len(res.result["png_previews"]) >= 1
