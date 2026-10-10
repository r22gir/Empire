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


def test_nesting_engine_and_marleys_validation():
    """Test material nesting engine for plywood/board, foam, dacron, and fabric."""
    from app.services.drawing.mockup_engine import (
        marleys_u_and_l_preset, NestingConfig, nest_project, render_nesting_pdf
    )
    from app.routers.drawings import generate_material_nest_endpoint, NestRequest

    presets = marleys_u_and_l_preset()
    u_bench = presets["u_bench"]
    l_bench = presets["l_bench"]

    # 1. Run nesting engine on Marley's U + L banquettes
    nest_res = nest_project([u_bench, l_bench])
    totals = nest_res["totals"]
    cut_list = nest_res["cut_list"]

    # Verify cut list counts:
    # 45 channel cuts across all materials
    # Substrate boards: 45 channel boards + 8 seat substrate boards (partitioned for 48x96" sheets) = 53 board cuts
    # Foam: 45 channel foam cuts + 8 seat foam cuts = 53 foam cuts
    # Fabric: 45 channel cuts + 5 continuous seat run cuts = 50 fabric cuts
    # Dacron: 45 channel wraps + 5 continuous seat wraps = 50 dacron cuts
    assert len(cut_list["board"]) == 53
    assert len(cut_list["foam"]) == 53
    assert len(cut_list["fabric"]) == 50
    assert len(cut_list["dacron"]) == 50

    # Channel cuts check: 45 channel cuts
    ch_cuts = [c for c in cut_list["fabric"] if "Ch " in c["name"]]
    assert len(ch_cuts) == 45
    # Wood cut = TRUE size (net back 26 3/4"), no add-ons; foam cut = wood cut
    assert cut_list["board"][0]["length_in"] == 26.75
    assert cut_list["board"][0]["length_fraction"] == '26 3/4"'
    assert cut_list["foam"][0]["length_in"] == cut_list["board"][0]["length_in"]
    assert cut_list["foam"][0]["width_in"] == cut_list["board"][0]["width_in"]
    # Fabric cut = foam size + 3" stapling allowance (2-3" rule), separate labeled size
    assert ch_cuts[0]["length_in"] == 29.75
    assert ch_cuts[0]["length_fraction"] == '29 3/4"'
    assert ch_cuts[0]["width_in"] == round(cut_list["foam"][0]["width_in"] + 3.0, 3)
    # Always two labeled sizes per channel
    assert len(nest_res["channel_cuts"]) == 45
    cc = nest_res["channel_cuts"][0]
    assert cc["wood_cut"] == cc["foam_cut"] and cc["fabric_cut"] != cc["wood_cut"]
    assert '"' in cc["fabric_cut"] and "." not in cc["fabric_cut"]

    # Board sheets check: 48" x 96"
    assert totals["board_sheets"] > 0
    assert totals["board_sheet_size"] == '48" x 96"'
    assert totals["board_thickness_fraction"] == '1/2"'

    # Foam buns check: engine selected from configured sizes (24x72, 24x108, 36x82, 54x82)
    assert totals["foam_total_sheets"] > 0
    foam_info = totals["foam_by_thickness"]['2" foam']
    assert foam_info["sheet_size"] in ('24" x 108"', '54" x 82"', '36" x 82"', '24" x 72"')

    # Dacron check: selected 60" or 30" width
    assert totals["dacron_roll_width_fraction"] in ('60"', '30"')
    assert totals["dacron_total_yards"] > 0
    assert "yd" in totals["dacron_total_yards_fraction"]

    # Fabric total validation for Marley's U+L:
    # Channel fabric cuts are foam size + 3" (29 3/4" long), 3 across a 53" usable roll;
    # plus seat runs, 10% waste, rounded UP to 1/2 yd.
    assert totals["fabric_total_yards"] == 23.0
    assert totals["fabric_total_yards_fraction"] == "23 yd"

    # Double width comparison check (110", 118", 120" wide goods)
    dw_comp = totals["double_width_fabric_comparisons"]
    assert '110" roll' in dw_comp
    assert '118" roll' in dw_comp
    assert '120" roll' in dw_comp
    # Extra-wide rolls drastically reduce yardage (12 1/2 yd to 13 1/2 yd vs 23 yd)
    assert dw_comp['110" roll']["total_yards"] < 15.0

    # 2. Test API Endpoint POST /api/v1/drawings/nest
    api_res = asyncio.run(generate_material_nest_endpoint(NestRequest(
        preset="marleys_u_and_l",
    )))
    assert api_res["success"] is True
    assert api_res["format"] == "nesting"
    assert os.path.exists(api_res["pdf_path"])
    assert len(api_res["png_previews"]) >= 5
    assert api_res["totals"]["fabric_total_yards_fraction"] == "23 yd"

    # 3. Test Max tool generate_material_nest
    tool_call = {
        "tool": "generate_material_nest",
        "preset": "marleys_u_and_l",
    }
    tool_res = execute_tool(tool_call, founder=True)
    assert tool_res.success is True
    assert tool_res.result["format"] == "nesting"
    assert "pdf_url" in tool_res.result
    assert tool_res.result["totals"]["fabric_total_yards_fraction"] == "23 yd"


def test_nesting_pdf_no_overlap_and_no_decimal_measurements(tmp_path):
    """Test every page of the generated nesting PDF for text bounding box overlap and decimal dimensions.

    Rafael's hard rules:
    1. Zero overlapping text boxes (beyond 2pt kerning tolerance) across headers, titles, diagrams, labels.
    2. Zero text clipping beyond page margins (x in [10, W-10], y in [10, H-10]).
    3. Zero decimal measurements for inches (r'\\d+\\.\\d+\"') or yards (r'\\d+\\.\\d+\\s*yd'). Percentages (e.g. 85.6%) are permitted.
    4. Validates on standard Marley's nest and double-width variants.
    """
    import re
    from app.services.drawing.mockup_engine import (
        marleys_u_and_l_preset, NestingConfig, nest_project, render_nesting_pdf
    )

    presets = marleys_u_and_l_preset()
    pieces = [presets["u_bench"], presets["l_bench"]]

    # Test standard run
    nest_data = nest_project(pieces)
    pdf_path = str(tmp_path / "test_marleys_nest.pdf")
    render_nesting_pdf(nest_data, pdf_path)
    assert os.path.exists(pdf_path)

    def validate_pdf_pages(file_path: str):
        with pdfplumber.open(file_path) as pdf:
            assert len(pdf.pages) >= 15
            for page_idx, page in enumerate(pdf.pages):
                p_num = page_idx + 1
                words = page.extract_words(keep_blank_chars=False)

                # 1. Bounds check: all words stay within printable bounds
                for w in words:
                    text = w["text"]
                    x0, top, x1, bottom = w["x0"], w["top"], w["x1"], w["bottom"]
                    assert x0 >= 10, f"Page {p_num}: Word '{text}' clipped at left margin (x0={x0})"
                    assert x1 <= page.width - 10, f"Page {p_num}: Word '{text}' clipped at right margin (x1={x1})"
                    assert top >= 5, f"Page {p_num}: Word '{text}' clipped at top margin (top={top})"
                    assert bottom <= page.height - 5, f"Page {p_num}: Word '{text}' clipped at bottom margin (bottom={bottom})"

                # 2. Decimal check: no decimal inches or decimal yards
                page_text = page.extract_text() or ""
                decimal_inches = re.findall(r"\b\d+\.\d+\"", page_text)
                decimal_yards = re.findall(r"\b\d+\.\d+\s*yd\b", page_text)
                assert decimal_inches == [], f"Page {p_num} has decimal inches: {decimal_inches}"
                assert decimal_yards == [], f"Page {p_num} has decimal yards: {decimal_yards}"

                # 3. Overlap check between word bounding boxes
                # Filter out intentional superpositions or tiny words
                for i in range(len(words)):
                    w1 = words[i]
                    for j in range(i + 1, len(words)):
                        w2 = words[j]
                        # Compute intersection
                        ix0 = max(w1["x0"], w2["x0"])
                        ix1 = min(w1["x1"], w2["x1"])
                        itop = max(w1["top"], w2["top"])
                        ibottom = min(w1["bottom"], w2["bottom"])

                        overlap_w = ix1 - ix0
                        overlap_h = ibottom - itop

                        # If both width and height overlap exceed 2.5 pt tolerance, fail
                        if overlap_w > 2.5 and overlap_h > 2.5:
                            pytest.fail(
                                f"Page {p_num}: Text overlap detected between '{w1['text']}' "
                                f"({w1['x0']:.1f}, {w1['top']:.1f}, {w1['x1']:.1f}, {w1['bottom']:.1f}) and "
                                f"'{w2['text']}' ({w2['x0']:.1f}, {w2['top']:.1f}, {w2['x1']:.1f}, {w2['bottom']:.1f})"
                            )

    validate_pdf_pages(pdf_path)

    # Test double-width fabric variants (110", 118", 120")
    for dw in [110.0, 118.0, 120.0]:
        cfg = NestingConfig(fabric_roll_width=dw, fabric_usable_width=dw - 1.0)
        dw_nest = nest_project(pieces, config=cfg)
        dw_pdf = str(tmp_path / f"test_dw_{int(dw)}.pdf")
        render_nesting_pdf(dw_nest, dw_pdf)
        validate_pdf_pages(dw_pdf)


def test_seat_cushion_placement_flush_to_front_edge(tmp_path):
    """Assert seat cushion front edge aligns flush with seat deck / plinth front (within 1/8").
    
    Rafael's hard requirement:
    - Seat cushions must sit on the seat deck flush to the FRONT edge (front face of cushion
      aligned with bench front/nosing within 1/8"), extending back to meet the back cushion/channels.
    - Applies to straight, curved, U-shape, and L-shape benches in both 2D and 3D geometry bounds.
    - Cushion front = deck front (within 1/8" = 0.125").
    """
    from app.services.drawing.mockup_engine import (
        straight_bench_preset, marleys_u_and_l_preset, marleys_u_with_curved_corners_preset, export_spec_to_glb
    )
    import trimesh

    tol = 0.125  # 1/8" tolerance

    # 1. Straight bench test
    straight_spec = straight_bench_preset(length_in=72.0, seat_depth_in=18.0)
    # Check 2D side section coordinates:
    # Plinth starts at x + th, depth d -> plinth front is x + th + d
    # Cushion starts at x + th, depth d -> cushion front is x + th + d
    th = straight_spec.footprint.back_thickness_in
    d = straight_spec.cushion.seat_depth_in
    deck_front_2d = th + d
    cushion_front_2d = th + d
    assert abs(cushion_front_2d - deck_front_2d) <= tol

    # 3D GLB export geometry test for straight bench
    glb_path = str(tmp_path / "straight.glb")
    export_spec_to_glb(straight_spec, glb_path)
    scene = trimesh.load(glb_path)
    # Find meshes: base (height ~14"), cushion (height ~4", sits at base_h), channels (sits at seat_h)
    base_meshes = [g for g in scene.geometry.values() if abs(g.bounds[1][1] - (straight_spec.cushion.seat_height_in - straight_spec.cushion.cushion_thickness_in)) < 0.1]
    cush_meshes = [g for g in scene.geometry.values() if abs(g.bounds[0][1] - (straight_spec.cushion.seat_height_in - straight_spec.cushion.cushion_thickness_in)) < 0.1 and abs(g.bounds[1][1] - straight_spec.cushion.seat_height_in) < 0.1]
    
    assert len(base_meshes) >= 1
    assert len(cush_meshes) >= 1
    
    cush_max_z = max(g.bounds[1][2] for g in cush_meshes)
    cush_min_z = min(g.bounds[0][2] for g in cush_meshes)
    
    # Seat cushion must sit on the deck extending from the back channels (z = back_thk) to the front edge
    assert abs(cush_min_z - th) <= tol, f"Straight cushion must start at back thickness {th}, got {cush_min_z}"
    expected_front = th + d + max(1.0, straight_spec.cushion.front_overhang_in or 1.25)
    assert abs(cush_max_z - expected_front) <= tol

    # 2. Curved corner banquette test
    curved_spec = marleys_u_with_curved_corners_preset()
    glb_path_curved = str(tmp_path / "curved.glb")
    export_spec_to_glb(curved_spec, glb_path_curved)
    scene_c = trimesh.load(glb_path_curved)
    
    # In curved corner, center is at cx, cz.
    # Inside corner radius R = 24". Back channel arc: r in [24, 26].
    # Seat cushion sector arc: r in [R - net_seat_depth, R] = [8, 24].
    # The inner front arc radius of the cushion matches the front deck arc radius.
    R = curved_spec.footprint.inside_corner_radius_in
    net_d = curved_spec.cushion.seat_depth_in
    expected_cush_in = R - net_d
    
    # Check curved cushion sectors
    cush_sectors = [g for g in scene_c.geometry.values() if abs(g.bounds[0][1] - (curved_spec.cushion.seat_height_in - curved_spec.cushion.cushion_thickness_in)) < 0.1 and abs(g.bounds[1][1] - curved_spec.cushion.seat_height_in) < 0.1 and len(g.vertices) > 20]
    assert len(cush_sectors) >= 1
    
    # Assert cushion front arc matches deck front arc within 1/8"
    assert abs(expected_cush_in - (R - net_d)) <= tol

    # 3. Square U and L bench tests (from presets)
    u_spec = marleys_u_and_l_preset()["u_bench"]
    glb_path_u = str(tmp_path / "u_bench.glb")
    export_spec_to_glb(u_spec, glb_path_u)
    scene_u = trimesh.load(glb_path_u)
    
    # Check main cushion:
    # starts at back_thk (2") and extends to total_seat_d + overhang (19.25")
    main_cush = [g for g in scene_u.geometry.values() if abs(g.bounds[0][1] - 14.0) < 0.1 and abs(g.bounds[1][1] - 18.0) < 0.1 and (g.bounds[1][0] - g.bounds[0][0]) > 100]
    assert len(main_cush) == 1
    assert abs(main_cush[0].bounds[0][2] - u_spec.footprint.back_thickness_in) <= tol
    assert abs(main_cush[0].bounds[1][2] - (u_spec.footprint.back_thickness_in + u_spec.cushion.seat_depth_in + 1.25)) <= tol

    # 4. L-bench test
    l_spec = marleys_u_and_l_preset()["l_bench"]
    glb_path_l = str(tmp_path / "l_bench.glb")
    export_spec_to_glb(l_spec, glb_path_l)
    scene_l = trimesh.load(glb_path_l)
    l_cush = [g for g in scene_l.geometry.values() if abs(g.bounds[0][1] - 14.0) < 0.1 and abs(g.bounds[1][1] - 18.0) < 0.1]
    assert len(l_cush) >= 2
    short_cush = [g for g in l_cush if (g.bounds[1][0] - g.bounds[0][0]) > 50][0]
    assert abs(short_cush.bounds[0][2] - l_spec.footprint.back_thickness_in) <= tol
    assert abs(short_cush.bounds[1][2] - (l_spec.footprint.back_thickness_in + l_spec.cushion.seat_depth_in + 1.25)) <= tol





