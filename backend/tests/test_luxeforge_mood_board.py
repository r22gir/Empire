"""LuxeForge mood boards — isolated temp dir, registry codes only."""
import json

import pytest

from app.services import luxeforge_mood_board as boards
from app.services.fabric_code_catalog import (
    client_catalog,
    client_view,
    lookup_code,
    next_vinyl_hint,
)
from app.services.measurements import inches_to_fraction, pair_inches


def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("EMPIRE_LUXE_MOOD_DIR", str(tmp_path / "mood"))
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))


def test_catalog_is_csv_only_and_hides_supplier():
    catalog = client_catalog()
    codes = [row["code"] for row in catalog]
    assert codes == [
        "V001-Assigned", "V002-Assigned", "V003-Assigned",
        "V004-Assigned", "V005-Assigned", "V006-Assigned", "V007-Assigned",
    ]
    assert next_vinyl_hint() == "V008"
    blob = json.dumps(catalog)
    assert "brand" not in blob
    assert "supplier" not in blob
    assert "supplier_sku" not in blob
    for row in catalog:
        assert set(row.keys()) == {
            "code", "color", "material_type", "width_inches",
            "pattern_repeat_v", "pattern_repeat_h", "backing", "specs",
        }


def test_lookup_rejects_invented_codes_allows_uncoded():
    assert lookup_code(None) is None
    assert lookup_code("") is None
    assert lookup_code("V001-Assigned")["code"] == "V001-Assigned"
    with pytest.raises(ValueError, match="not in the shared registry"):
        lookup_code("V142-Navy")
    with pytest.raises(ValueError, match="not in the shared registry"):
        lookup_code("V008-Cognac")
    with pytest.raises(ValueError, match="not in the shared registry"):
        lookup_code("V003-Ivory")


def test_swatch_from_registry_or_uncoded(tmp_path, monkeypatch):
    _iso(tmp_path, monkeypatch)
    board = boards.create_board("Henderson suite", designer="Maya", client_name="Henderson")

    coded = boards.add_swatch(board["id"], "V001-Assigned", hex_color="#1d3557")
    assert coded["swatches"][0]["fabric_code"] == "V001-Assigned"
    assert coded["swatches"][0]["uncoded"] is False
    assert "brand" not in coded["swatches"][0]
    assert "supplier" not in coded["swatches"][0]

    uncoded = boards.add_swatch(coded["id"], None, hex_color="#c9a84c")
    assert uncoded["swatches"][1]["fabric_code"] is None
    assert uncoded["swatches"][1]["uncoded"] is True

    with pytest.raises(ValueError, match="not in the shared registry"):
        boards.add_swatch(board["id"], "V142-Navy")


def test_share_projection_strips_brand_and_supplier(tmp_path, monkeypatch):
    _iso(tmp_path, monkeypatch)
    board = boards.create_board("Share me")
    boards.add_swatch(board["id"], "V002-Assigned")
    loaded = boards.get_board(board["id"])
    loaded["swatches"][0]["brand"] = "HiddenBrand"
    loaded["swatches"][0]["supplier"] = "HiddenSupplier"
    loaded["swatches"][0]["supplier_sku"] = "HS-99"
    public = boards.share_projection(loaded)
    blob = json.dumps(public)
    assert "HiddenBrand" not in blob
    assert "HiddenSupplier" not in blob
    assert "HS-99" not in blob
    assert "supplier" not in blob
    assert "brand" not in blob
    assert public["swatches"][0]["fabric_code"] == "V002-Assigned"
    assert public["read_only"] is True
    view = client_view({"code": "V001-Assigned", "color": "Assigned", "brand": "X", "supplier": "Y"})
    assert "brand" not in view
    assert "supplier" not in view


def test_image_notes_and_fraction_sizes(tmp_path, monkeypatch):
    _iso(tmp_path, monkeypatch)
    board = boards.create_board("Cornice study")
    boards.add_image(board["id"], "https://example.test/room.jpg", caption="Living", width_in=36.75, height_in=18.5)
    boards.add_note(board["id"], "Keep the contrast welt in ivory.")
    loaded = boards.get_board(board["id"])
    assert loaded["images"][0]["width_fraction"] == '36 3/4"'
    assert loaded["images"][0]["height_fraction"] == '18 1/2"'
    assert loaded["images"][0]["size_fraction"] == '36 3/4" × 18 1/2"'
    assert loaded["notes"][0]["text"].startswith("Keep the contrast")


def test_rotate_share_invalidates_old_token(tmp_path, monkeypatch):
    _iso(tmp_path, monkeypatch)
    board = boards.create_board("Private")
    old = board["share_token"]
    rotated = boards.rotate_share_token(board["id"])
    assert rotated["share_token"] != old
    assert boards.get_board_by_token(old) is None
    assert boards.get_board_by_token(rotated["share_token"])["id"] == board["id"]


def test_inches_to_fraction_helpers():
    assert inches_to_fraction(4.75) == '4 3/4"'
    assert inches_to_fraction(0.125) == '1/8"'
    assert inches_to_fraction(36) == '36"'
    assert inches_to_fraction(None) == "—"
    assert pair_inches(12.5, 8.25) == '12 1/2" × 8 1/4"'


def test_list_and_delete(tmp_path, monkeypatch):
    _iso(tmp_path, monkeypatch)
    a = boards.create_board("A")
    boards.create_board("B")
    assert len(boards.list_boards()) == 2
    assert boards.delete_board(a["id"]) is True
    assert boards.get_board(a["id"]) is None
    assert len(boards.list_boards()) == 1
