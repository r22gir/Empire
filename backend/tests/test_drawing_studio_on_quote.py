"""Drawing Studio on quote — cut lists, spaced fractions, live renderer, no uploads writes."""
from __future__ import annotations

import asyncio
import tempfile

from app.config.fabric_cut_allowance import (
    CONFIRM_WITH_RAFAEL,
    NEEDS_FOAM_THICKNESS,
    lookup_fabric_allowance,
)
from app.routers import drawings
from app.services.drawing.inches import format_inches
from app.services.vision.bench_cut_list import (
    format_cut_inches,
    generate_cut_list,
    render_cut_list_sheet,
)
from app.services.vision.bench_renderer import BenchModel


def test_live_inch_formatter_uses_fractions_not_decimals():
    """Title-block / Helvetica path keeps the live hyphen contract."""
    assert format_inches(22.5) == '22-1/2"'
    assert format_inches(18) == '18"'
    assert "." not in format_inches(22.5)
    assert "." not in format_inches(6.25)


def test_cut_list_prints_spaced_fractions_never_hyphen_or_decimal():
    assert format_cut_inches(22.5) == '22 1/2"'
    assert format_cut_inches(18) == '18"'
    assert format_cut_inches(0.5) == '1/2"'
    assert format_cut_inches(6.25) == '6 1/4"'
    assert "-" not in format_cut_inches(22.5)
    assert "." not in format_cut_inches(22.5)
    assert "." not in format_cut_inches(6.25)


def test_cut_list_wood_true_size_foam_matches_fabric_needs_thickness_when_unknown():
    model = BenchModel(
        name="L Banquette", width=96, depth=22.5, seat_h=18, back_h=18,
        bench_type="l_shape", long=96, short=60,
    )
    cuts = generate_cut_list(model)
    assert cuts["wood"] and cuts["foam"] and cuts["fabric"]
    assert cuts["fabric_allowance_status"] == NEEDS_FOAM_THICKNESS
    assert cuts["fabric_allowance_in"] is None
    sizes = {wood["size"] for wood in cuts["wood"]}
    assert sizes == {'22 1/2" × 96"', '22 1/2" × 60"'}
    for wood, foam, fabric in zip(cuts["wood"], cuts["foam"], cuts["fabric"]):
        assert wood["width"] == foam["width"] == 22.5
        assert wood["length"] == foam["length"]
        assert wood["label"] == "WOOD CUT — TRUE SIZE"
        assert foam["label"] == "FOAM CUT — MATCHES WOOD"
        assert foam["size"] == wood["size"]
        assert fabric["size"] == NEEDS_FOAM_THICKNESS
        assert fabric["width"] is None
        assert fabric["length"] is None
        assert fabric["label"] == "FABRIC CUT — LABELED SEPARATELY"
        assert "needs foam thickness" in fabric["note"].lower()
        assert "-" not in wood["size"]
        assert "." not in wood["size"]
    svg = render_cut_list_sheet(cuts, name="L Banquette", quote_num="EST-L")
    assert "WOOD CUT — TRUE SIZE" in svg
    assert NEEDS_FOAM_THICKNESS in svg
    assert "22-1/2" not in svg
    assert "22.5" not in svg


def test_cut_list_fabric_allowance_from_foam_thickness_table():
    model = BenchModel(
        name="Straight", width=96, depth=22.5, seat_h=18, back_h=18,
        foam_thickness_in=2.0,
    )
    row = lookup_fabric_allowance(2.0)
    extra = row["allowance_in"]
    assert extra == 5.0
    assert extra != 4
    assert row["status"] == CONFIRM_WITH_RAFAEL
    assert "confirm with Rafael" in row["label"]

    cuts = generate_cut_list(model)
    wood = cuts["wood"][0]
    fabric = cuts["fabric"][0]
    assert cuts["foam_thickness_in"] == 2.0
    assert cuts["fabric_allowance_in"] == extra
    assert cuts["fabric_allowance_status"] == CONFIRM_WITH_RAFAEL
    assert fabric["width"] == wood["width"] + extra
    assert fabric["length"] == wood["length"] + extra
    assert fabric["size"] == '27 1/2" × 101"'
    assert "confirm with Rafael" in fabric["note"]
    assert "+" not in fabric["size"]
    assert "-" not in fabric["size"]
    assert "." not in fabric["size"]


def test_cut_list_unmatched_foam_thickness_does_not_guess():
    model = BenchModel(name="Odd foam", width=48, depth=18, foam_thickness_in=2.25)
    cuts = generate_cut_list(model)
    assert cuts["fabric_allowance_status"] == NEEDS_FOAM_THICKNESS
    assert cuts["fabric_allowance_in"] is None
    assert cuts["fabric"][0]["size"] == NEEDS_FOAM_THICKNESS
    assert cuts["wood"][0]["width"] == cuts["foam"][0]["width"] == 18


def test_bench_api_returns_cut_list_and_pdf_is_multipage():
    req = drawings.BenchRequest(
        name="Presentation Bench",
        lf=96,
        length_unit="in",
        seat_depth=22.5,
        seat_height=18,
        back_height=18,
        bench_type="straight",
        quote_num="EST-Q",
    )
    preview = asyncio.run(drawings.generate_bench_svg(req))
    assert preview["svg"]
    assert preview["cut_list"]["wood"]
    assert preview["cut_list"]["foam"]
    assert preview["cut_list"]["fabric"]
    assert preview["cut_list"]["fabric_allowance_status"] == NEEDS_FOAM_THICKNESS
    assert preview["cut_list"]["fabric"][0]["size"] == NEEDS_FOAM_THICKNESS
    assert preview["quote_num"] == "EST-Q"
    svg = preview["svg"]
    assert format_inches(22.5).replace('"', "&quot;") in svg or format_inches(22.5) in svg

    pdf = asyncio.run(drawings.generate_bench_pdf(req))
    assert pdf.media_type == "application/pdf"
    assert pdf.body.startswith(b"%PDF")
    assert len(pdf.body) > 8000


def test_bench_api_passes_foam_thickness_into_fabric_cut():
    req = drawings.BenchRequest(
        name="Quote Bench",
        lf=96,
        length_unit="in",
        seat_depth=22.5,
        bench_type="straight",
        foam_thickness=4.0,
    )
    preview = asyncio.run(drawings.generate_bench_svg(req))
    cuts = preview["cut_list"]
    extra = lookup_fabric_allowance(4.0)["allowance_in"]
    assert extra == 9.0
    wood = cuts["wood"][0]
    fabric = cuts["fabric"][0]
    assert cuts["foam_thickness_in"] == 4.0
    assert fabric["width"] == wood["width"] + extra
    assert fabric["size"] == format_cut_inches(wood["width"] + extra) + " × " + format_cut_inches(wood["length"] + extra)
    assert "22 1/2" in wood["size"]
    assert "22-1/2" not in wood["size"]


def test_l_shape_api_uses_live_leg_lengths():
    req = drawings.BenchRequest(
        name="Corner L",
        bench_type="l_shape",
        length_unit="in",
        lf=156,
        leg1_length=96,
        leg2_length=60,
        seat_depth=22,
        seat_height=18,
        back_height=18,
    )
    preview = asyncio.run(drawings.generate_bench_svg(req))
    cuts = preview["cut_list"]
    lengths = sorted(item["length"] for item in cuts["wood"])
    assert lengths == [60, 96]
    svg = preview["svg"]
    assert format_inches(96).replace('"', "&quot;") in svg or "96" in svg


def test_dxf_writes_to_tempfile_not_uploads(monkeypatch):
    captured = {}

    def fake_generate_dxf(model, output_path):
        captured["path"] = output_path
        with open(output_path, "w") as fh:
            fh.write("DXF")
        return output_path

    monkeypatch.setattr(
        "app.services.vision.bench_renderer.generate_dxf",
        fake_generate_dxf,
    )
    req = drawings.BenchRequest(name="Temp Bench", lf=72, length_unit="in")
    asyncio.run(drawings.generate_bench_dxf(req))
    assert captured["path"].startswith(tempfile.gettempdir())
    assert "uploads" not in captured["path"]
    assert "empire.db" not in captured["path"]
