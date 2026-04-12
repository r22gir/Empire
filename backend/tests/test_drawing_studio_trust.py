import asyncio

from app.routers import drawings


def test_bench_drawing_preview_and_pdf_use_current_dimensions():
    small = drawings.BenchRequest(
        name="Trust Bench",
        lf=6,
        seat_depth=20,
        seat_height=18,
        back_height=18,
    )
    large = drawings.BenchRequest(
        name="Trust Bench",
        lf=8,
        seat_depth=20,
        seat_height=18,
        back_height=18,
    )

    small_svg = asyncio.run(drawings.generate_bench_svg(small))["svg"]
    large_svg = asyncio.run(drawings.generate_bench_svg(large))["svg"]

    assert small_svg != large_svg
    assert "72&quot;" in small_svg
    assert "96&quot;" not in small_svg
    assert "96&quot;" in large_svg
    assert "72&quot;" not in large_svg

    small_pdf = asyncio.run(drawings.generate_bench_pdf(small))
    large_pdf = asyncio.run(drawings.generate_bench_pdf(large))

    assert small_pdf.media_type == "application/pdf"
    assert large_pdf.media_type == "application/pdf"
    assert small_pdf.body != large_pdf.body
    assert small_pdf.body.startswith(b"%PDF")
    assert large_pdf.body.startswith(b"%PDF")


def test_drawing_asset_preserves_quote_item_linkage_aliases(monkeypatch, tmp_path):
    monkeypatch.setattr(
        drawings.os.path,
        "expanduser",
        lambda path: str(tmp_path / "arch_drawings") if path.endswith("uploads/arch_drawings") else path,
    )

    response = asyncio.run(drawings.save_drawing_asset(drawings.DrawingAssetRequest(
        name="WoodCraft Banquette",
        item_type="bench_l_shaped",
        route_to="woodcraft",
        svg="<svg></svg>",
        assigned_room_id="room-banquette",
        assigned_item_id="item-banquette",
        item_key="item-banquette",
        dimensions={"width": 96, "height": 34, "depth": 24},
    )))
    asset = response["asset"]

    assert asset["route_to"] == "woodcraft"
    assert asset["assigned_room_id"] == "room-banquette"
    assert asset["assigned_item_id"] == "item-banquette"
    assert asset["item_key"] == "item-banquette"
    assert (tmp_path / "arch_drawings" / asset["filename"]).exists()


def test_drawing_asset_preserves_frontend_room_and_item_ids(monkeypatch, tmp_path):
    monkeypatch.setattr(
        drawings.os.path,
        "expanduser",
        lambda path: str(tmp_path / "arch_drawings") if path.endswith("uploads/arch_drawings") else path,
    )

    response = asyncio.run(drawings.save_drawing_asset(drawings.DrawingAssetRequest(
        name="Frontend Banquette",
        item_type="bench_l_shaped",
        route_to="woodcraft",
        svg="<svg></svg>",
        room_id="room-ui",
        item_id="item-ui",
    )))
    asset = response["asset"]

    assert asset["assigned_room_id"] == "room-ui"
    assert asset["assigned_item_id"] == "item-ui"
    assert asset["item_key"] == "item-ui"
