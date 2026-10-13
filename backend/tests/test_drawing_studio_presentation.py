"""Client-presentation Drawing Studio: true L/U plans, fractions, cut lists, PDF."""
import asyncio
import tempfile

from app.routers import drawings
from app.services.vision.bench_renderer import (
    BenchModel,
    generate_cut_list,
    generate_shop_sheet,
    l_plan_points,
    render_cut_list_sheet,
    render_l_shape,
    render_straight,
    render_u_shape,
    u_plan_points,
)
from app.services.vision.inches import format_inches, has_decimal_dimension
from app.services.vision.renderer_registry import get_title_block


def _assert_no_decimal_dims(svg: str):
    assert not has_decimal_dimension(svg), "drawing still contains a decimal inch label"


def test_true_l_plan_is_a_single_closed_polygon_not_a_strip():
    pts = l_plan_points(96, 60, 22)
    assert len(pts) == 6
    xs = [p[0] for p in pts]
    ys = [p[1] for p in pts]
    assert min(xs) == 0 and max(xs) == 96
    assert min(ys) == 0 and max(ys) == 60
    # Inner corner is present — this is an L, not a rectangle strip.
    assert (96 - 22, 22) in pts

    svg = render_l_shape("L Banquette", 96, 60, 22, 18, 18, quote_num="EST-L")
    assert "TRUE L-SHAPE PLAN" in svg
    assert "<polygon" in svg
    assert "PLAN VIEW" in svg
    assert "FRONT ELEVATION" in svg
    assert "EMPIRE WOODCRAFT" in svg or "EMPIRE WORKROOM" in svg
    _assert_no_decimal_dims(svg)
    assert format_inches(96).replace('"', "&quot;") in svg


def test_true_u_plan_is_a_single_closed_polygon_not_three_strips():
    pts = u_plan_points(72, 48, 20, 20)
    assert len(pts) == 8
    # Opening toward +y: inner recess exists.
    assert any(p[1] == 20 for p in pts)
    svg = render_u_shape("U Booth", 72, 48, 20, 20, 18, 18, quote_num="EST-U")
    assert "TRUE U-SHAPE PLAN" in svg
    assert "<polygon" in svg
    assert svg.count("<polygon") >= 1
    _assert_no_decimal_dims(svg)
    assert "EMPIRE WOODCRAFT" in svg or "EMPIRE WORKROOM" in svg


def test_straight_bench_keeps_fraction_labels_and_branding():
    svg = render_straight("Trust Bench", 72, 20, 18, 18)
    assert "72&quot;" in svg
    assert "96&quot;" not in svg
    _assert_no_decimal_dims(svg)
    brand = get_title_block("banquette")
    assert brand["company"] in svg or "EMPIRE WOODCRAFT" in svg or "EMPIRE WORKROOM" in svg


def test_cut_list_wood_true_size_foam_matches_fabric_separate():
    model = BenchModel(
        name="L Banquette", width=96, depth=22, seat_h=18, back_h=18,
        bench_type="l_shape", long=96, short=60,
    )
    cuts = generate_cut_list(model)
    assert cuts["wood"] and cuts["foam"] and cuts["fabric"]
    for wood, foam in zip(cuts["wood"], cuts["foam"]):
        assert wood["width"] == foam["width"]
        assert wood["length"] == foam["length"]
        assert wood["label"] == "WOOD CUT — TRUE SIZE"
        assert foam["label"] == "FOAM CUT — MATCHES WOOD"
        assert "." not in wood["size"]
        assert "." not in foam["size"]
    for fabric, wood in zip(cuts["fabric"], cuts["wood"]):
        assert fabric["width"] == wood["width"] + 4
        assert fabric["length"] == wood["length"] + 4
        assert fabric["label"] == "FABRIC CUT — LABELED SEPARATELY"
        assert "Fabric cut" in fabric["note"]
        assert "." not in fabric["size"]

    sheet = generate_shop_sheet(model)
    assert "WOOD CUT — TRUE SIZE" in sheet
    assert "FOAM CUT — MATCHES WOOD" in sheet
    assert "FABRIC CUT — LABELED SEPARATELY" in sheet
    for line in sheet.splitlines():
        if " × " in line:
            assert not has_decimal_dimension(line), line

    svg = render_cut_list_sheet(cuts, name="L Banquette", quote_num="EST-L")
    assert "WOOD CUT — TRUE SIZE" in svg
    assert "FOAM CUT — MATCHES WOOD" in svg
    assert "FABRIC CUT — LABELED SEPARATELY" in svg
    _assert_no_decimal_dims(svg)


def test_bench_api_returns_cut_list_and_pdf_is_multipage():
    req = drawings.BenchRequest(
        name="Presentation Bench",
        lf=8,
        seat_depth=22.5,
        seat_height=18,
        back_height=18,
        bench_type="straight",
    )
    preview = asyncio.run(drawings.generate_bench_svg(req))
    assert "svg" in preview
    assert preview["cut_list"]["wood"]
    assert preview["cut_list"]["foam"]
    assert preview["cut_list"]["fabric"]
    svg = preview["svg"]
    assert "22 1/2&quot;" in svg
    _assert_no_decimal_dims(svg)

    pdf = asyncio.run(drawings.generate_bench_pdf(req))
    assert pdf.media_type == "application/pdf"
    assert pdf.body.startswith(b"%PDF")
    # Drawing page + cut-list page: packet is larger than a single-view PDF.
    assert len(pdf.body) > 8000


def test_l_shape_api_uses_leg_lengths_not_unfolded_default_only():
    req = drawings.BenchRequest(
        name="Corner L",
        bench_type="l_shape",
        lf=13,
        leg1_length=8,
        leg2_length=5,
        seat_depth=22,
        seat_height=18,
        back_height=18,
    )
    preview = asyncio.run(drawings.generate_bench_svg(req))
    svg = preview["svg"]
    assert "TRUE L-SHAPE PLAN" in svg
    assert "96&quot;" in svg  # 8 ft long run
    assert "60&quot;" in svg  # 5 ft short run
    _assert_no_decimal_dims(svg)


def test_catalog_l_shape_style_routes_to_bench_renderer():
    req = drawings.UniversalDrawingRequest(
        user_text="L Shape Banquette presentation",
        params={
            "name": "Catalog L",
            "item_type": "banquette",
            "style_key": "l_shape",
            "width": 96,
            "depth": 22,
            "seat_height": 18,
            "back_height": 18,
        },
    )
    out = drawings._render_universal_drawing(req)
    assert out["item_type"] == "bench"
    assert out["bench_type"] == "l_shape"
    assert "TRUE L-SHAPE PLAN" in out["svg"]
    assert out.get("cut_list")


def test_dxf_writes_to_tempfile_not_uploads(monkeypatch):
    """No live-data write: DXF lands in tempfile, never uploads/arch_drawings."""
    captured = {}

    def fake_generate_dxf(model, output_path):
        captured["path"] = output_path
        with open(output_path, "w") as f:
            f.write("DXF")
        return output_path

    monkeypatch.setattr(
        "app.services.vision.bench_renderer.generate_dxf",
        fake_generate_dxf,
    )
    req = drawings.BenchRequest(name="Temp Bench", lf=6)
    asyncio.run(drawings.generate_bench_dxf(req))
    assert captured["path"].startswith(tempfile.gettempdir())
    assert "uploads" not in captured["path"]
    assert "empire.db" not in captured["path"]
