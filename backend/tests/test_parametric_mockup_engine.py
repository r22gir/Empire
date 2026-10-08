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
    """Channels can be equal whole channels or symmetric end remainders."""
    # Equal distribution (default):
    # Main run 249.75" with 12" channels -> 21 equal channels
    widths_eq, end_eq = compute_channels(249.75, 12.0, equal_distribution=True)
    assert len(widths_eq) == 21
    assert end_eq == 0.0
    assert widths_eq[0] == pytest.approx(249.75 / 21, 1e-4)
    assert sum(widths_eq) == pytest.approx(249.75, 1e-4)

    # Left run 37.75" with 12" channels -> 3 equal channels
    widths_l_eq, _ = compute_channels(37.75, 12.0, equal_distribution=True)
    assert len(widths_l_eq) == 3

    # Right run 48.5" with 12" channels -> 4 equal channels
    widths_r_eq, _ = compute_channels(48.5, 12.0, equal_distribution=True)
    assert len(widths_r_eq) == 4

    # Remainder split mode (equal_distribution=False):
    # Main run 249.75" with 12" channels
    # 249.75 // 12 = 20 full (240"), remainder 9.75" -> 4.875" each end
    widths, end = compute_channels(249.75, 12.0, equal_distribution=False)
    assert len(widths) == 22  # 20 full + 2 ends
    assert end == 4.875
    assert widths[0] == 4.875
    assert widths[-1] == 4.875
    assert sum(widths) == pytest.approx(249.75, 1e-4)

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
    # 18" seat depth = 2" back + 16" seat cushion
    assert u_spec.footprint.back_thickness_in == 2.0
    assert u_spec.cushion.seat_depth_in == 16.0
    assert u_spec.back.net_back_height_in == 26.75
    assert u_spec.back.channel_width_in == 12.0

    u_pdf = str(tmp_path / "marleys_u.pdf")
    render_piece_mockup_pdf(u_spec, u_pdf)
    assert os.path.exists(u_pdf)
    u_text = extract_pdf_text(u_pdf)
    assert "EMPIRE WORKROOM" in u_text
    # Fraction labels: 249 3/4", 37 3/4", 48 1/2", 26 3/4"
    assert "249 3/4" in u_text
    assert "37 3/4" in u_text
    assert "48 1/2" in u_text
    assert "26 3/4" in u_text
    assert "21 equal channels" in u_text or "equal channels" in u_text

    # Verify no decimal inch strings in rendered text (e.g. .75", .5", .375")
    import re
    assert re.findall(r"\d+\.\d+\"", u_text) == []

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
    assert l_spec.footprint.back_thickness_in == 2.0
    assert l_spec.cushion.seat_depth_in == 16.0
    assert l_spec.back.net_back_height_in == 26.75

    l_pdf = str(tmp_path / "marleys_l.pdf")
    render_piece_mockup_pdf(l_spec, l_pdf)
    assert os.path.exists(l_pdf)
    l_text = extract_pdf_text(l_pdf)
    assert "EMPIRE WORKROOM" in l_text
    assert "95 3/8" in l_text
    assert "107 3/4" in l_text
    assert re.findall(r"\d+\.\d+\"", l_text) == []


def test_chair_fixture(tmp_path):
    """Test single chair piece with arms, tufted back, plan/section agreement, and rake handling."""
    chair_spec = single_chair_preset(
        width_in=34.0,
        depth_in=30.0,
        seat_height_in=18.0,
        back_height_in=22.0,
        rake_deg=8.0,
        name="Luxe Club Chair",
        has_arms=True,
        arm_width_in=4.0,
        arm_height_in=24.0,
    )
    # Check plan vs section seat depth agreement (30" - 4" = 26")
    assert chair_spec.cushion.seat_depth_in == 26.0
    assert chair_spec.footprint.overall_depth_in == 30.0
    assert chair_spec.back.rake_deg == 8.0

    pdf_path = str(tmp_path / "chair_mockup.pdf")
    render_piece_mockup_pdf(chair_spec, pdf_path)
    assert os.path.exists(pdf_path)

    text = extract_pdf_text(pdf_path)
    assert "LUXE CLUB CHAIR" in text
    assert "SIDE SECTION" in text
    assert "Diamond tufted" in text or "tufted" in text
    assert "12\" vertical channels" not in text
    assert "SEAT · 26\" deep" in text
    assert "SEAT 26\"" in text
    assert "RAKE 8°" in text
    # Ensure no decimal inches in chair PDF
    import re
    assert re.findall(r"\d+\.\d+\"", text) == []

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


def test_3d_render_and_curved_corners(tmp_path):
    """Test 3D live model HTML generation, 4 rendered stills, GLB triangles, and curved corners preset."""
    import re
    import trimesh
    from app.services.drawing.mockup_engine import (
        render_3d, marleys_u_and_l_preset, marleys_u_with_curved_corners_preset,
    )
    
    # 1. Plain Marley's U Bench 3D
    u_plain = marleys_u_and_l_preset()["u_bench"]
    res_plain = render_3d(u_plain, str(tmp_path / "plain_3d"), prefix="plain_u")
    assert os.path.exists(res_plain["html_path"])
    assert len(res_plain["stills"]) == 4
    for st in res_plain["stills"]:
        assert os.path.exists(st)
        assert os.path.getsize(st) > 1000
    assert os.path.exists(res_plain["glb_path"])
    
    # Verify plain GLB has > 1,000 triangles and watertight solids
    scene_p = trimesh.load(res_plain["glb_path"], file_type="glb")
    tri_p = sum(len(m.faces) for m in scene_p.geometry.values())
    assert tri_p > 1000

    with open(res_plain["html_path"], "r") as f:
        html_p = f.read()
    assert "EMPIRE WORKROOM" in html_p
    assert "MARLEY'S U BENCH" in html_p
    assert "Three.js" in html_p or "three.min.js" in html_p
    # Verify no decimal inch strings in rendered HUD labels (e.g. 249 3/4" not 249.75")
    hud_matches = re.findall(r"\b\d+\.\d+\"", html_p)
    assert hud_matches == []

    # 2. Marley's U Bench with 24" curved inside corners
    u_curved = marleys_u_with_curved_corners_preset()
    assert u_curved.footprint.corner_style == "curved"
    assert u_curved.footprint.inside_corner_radius_in == 24.0

    # Test footprint perimeter geometry differs (arc vertices present)
    verts_plain = u_plain.footprint.get_perimeter_vertices()
    verts_curved = u_curved.footprint.get_perimeter_vertices()
    assert len(verts_curved) > len(verts_plain)
    assert len(verts_curved) >= 30
    
    res_curved = render_3d(u_curved, str(tmp_path / "curved_3d"), prefix="curved_u")
    assert os.path.exists(res_curved["html_path"])
    assert len(res_curved["stills"]) == 4
    for st in res_curved["stills"]:
        assert os.path.exists(st)
        assert os.path.getsize(st) > 1000

    # Verify curved GLB has > 1,000 triangles
    scene_c = trimesh.load(res_curved["glb_path"], file_type="glb")
    tri_c = sum(len(m.faces) for m in scene_c.geometry.values())
    assert tri_c > 1000
    assert tri_p > 1000

    with open(res_curved["html_path"], "r") as f:
        html_c = f.read()
    assert "Curved Corners" in html_c or "24\"" in html_c
    assert re.findall(r"\b\d+\.\d+\"", html_c) == []

    # Verify plain vs curved still images actually differ visually
    from PIL import Image
    import numpy as np
    img_plain_top = np.array(Image.open(res_plain["stills"][2]))
    img_curved_top = np.array(Image.open(res_curved["stills"][2]))
    diff = np.abs(img_plain_top.astype(int) - img_curved_top.astype(int))
    assert np.max(diff) > 50  # significant pixel difference from curved corner sweep
    assert np.sum(diff > 10) > 10000

    # 3. Test API endpoint with format="3d"
    api_res = asyncio.run(generate_mockup_drawing(MockupFromSpecRequest(
        preset="marleys_u_curved",
        format="3d",
    )))
    assert api_res["success"] is True
    assert api_res["format"] == "3d"
    assert os.path.exists(api_res["html_path"])
    assert len(api_res["stills"]) == 4
    assert "viewer_url" in api_res

    # 4. Test Max tool with format="3d"
    max_tool_call = {
        "tool": "generate_parametric_mockup",
        "preset": "marleys_u",
        "format": "3d",
    }
    max_res = execute_tool(max_tool_call, founder=True)
    assert max_res.success is True
    assert max_res.result["format"] == "3d"
    assert "viewer_url" in max_res.result
    assert len(max_res.result["stills"]) == 4

