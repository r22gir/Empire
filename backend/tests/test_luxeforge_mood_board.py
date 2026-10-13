"""LuxeForge mood boards — isolated temp dir, no live writes."""
import pytest

from app.services import luxeforge_mood_board as boards
from app.services.measurements import inches_to_fraction, pair_inches


def _iso(tmp_path, monkeypatch):
    monkeypatch.setenv("EMPIRE_LUXE_MOOD_DIR", str(tmp_path / "mood"))
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))


def test_create_share_and_swatch_code(tmp_path, monkeypatch):
    _iso(tmp_path, monkeypatch)
    board = boards.create_board("Henderson suite", designer="Maya", client_name="Henderson")
    assert board["share_token"]
    assert board["module"] == "mood_board"

    updated = boards.add_swatch(board["id"], "V142-Navy", name="Silk", hex_color="#1d3557")
    assert updated["swatches"][0]["fabric_code"] == "V142-Navy"

    with pytest.raises(ValueError):
        boards.add_swatch(board["id"], "navy-142")

    shared = boards.get_board_by_token(board["share_token"])
    assert shared is not None
    assert shared["title"] == "Henderson suite"
    assert shared["swatches"][0]["fabric_code"] == "V142-Navy"


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
