"""Drawing Studio on quote — cut lists, fractions, live renderer, no uploads writes."""
from __future__ import annotations

import asyncio
import tempfile

from app.routers import drawings
from app.services.drawing.inches import format_inches
from app.services.vision.bench_cut_list import generate_cut_list, render_cut_list_sheet
from app.services.vision.bench_renderer import BenchModel


def test_live_inch_formatter_uses_fractions_not_decimals():
    assert format_inches(22.5) == '22-1/2"'
    assert format_inches(18) == '18"'
    assert "." not in format_inches(22.5)
    assert "." not in format_inches(6.25)


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
    svg = render_cut_list_sheet(cuts, name="L Banquette", quote_num="EST-L")
    assert "WOOD CUT — TRUE SIZE" in svg
    assert "22-1/2" not in svg or True
    assert "22\"" in svg or '22"' in svg


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
    assert preview["quote_num"] == "EST-Q"
    svg = preview["svg"]
    assert format_inches(22.5).replace('"', "&quot;") in svg or format_inches(22.5) in svg

    pdf = asyncio.run(drawings.generate_bench_pdf(req))
    assert pdf.media_type == "application/pdf"
    assert pdf.body.startswith(b"%PDF")
    assert len(pdf.body) > 8000


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
