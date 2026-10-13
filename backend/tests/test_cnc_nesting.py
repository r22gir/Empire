"""CNC nest: kerf, grain, X-Carve tiling, fractions, foam=wood, fabric labeled."""
from __future__ import annotations

import importlib
import re

import pytest


def _reload(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    from app.db import database
    importlib.reload(database)
    from app.services.cnc import inches, nesting, parts, pdf
    importlib.reload(inches)
    importlib.reload(parts)
    importlib.reload(nesting)
    importlib.reload(pdf)
    return inches, nesting, parts, pdf


def _sample_parts():
    return [
        {
            "id": "side",
            "name": "Side panel",
            "wood": {"width": "12 1/2", "length": "24"},
            "fabric": {"width": "15", "length": "27"},
            "grain": "with",
            "qty": 2,
        },
        {
            "id": "rail",
            "name": "Front rail",
            "width": "3",
            "length": "18 3/4",
            "grain": "with",
        },
    ]


def test_format_inches_never_decimal(monkeypatch, tmp_path):
    inches, _, _, _ = _reload(monkeypatch, tmp_path)
    assert inches.format_inches(inches.parse_inches("29 1/2")) == '29 1/2"'
    assert inches.format_inches(inches.parse_inches("1/8")) == '1/8"'
    assert inches.format_inches(inches.parse_inches("29-1/2")) == '29 1/2"'
    assert inches.format_inches(inches.parse_inches("36")) == '36"'
    assert inches.format_inches(0) == '0"'
    for raw in ("29 1/2", "1/8", "18 3/4", "96", "0"):
        text = inches.format_inches(inches.parse_inches(raw))
        assert "." not in text
        assert text.endswith('"')


def test_yield_is_fraction(monkeypatch, tmp_path):
    inches, _, _, _ = _reload(monkeypatch, tmp_path)
    assert inches.yield_fraction(1, 4) == "1/4"
    assert inches.yield_fraction(3, 4) == "3/4"
    assert inches.yield_fraction(2, 4) == "1/2"
    assert "." not in inches.yield_fraction(5, 8)


def test_wood_true_size_foam_equals_wood_fabric_separate(monkeypatch, tmp_path):
    _, nesting, _, _ = _reload(monkeypatch, tmp_path)
    result = nesting.nest_cut_list({"parts": _sample_parts(), "job_id": "job-demo"})
    inches_mod, _, _, _ = _reload(monkeypatch, tmp_path)
    inches_mod.assert_no_decimal_measurements(result)
    sides = [r for r in result["cut_list"] if r["name"].startswith("Side panel")]
    assert sides
    for row in sides:
        assert row["wood_width"] == '12 1/2"'
        assert row["wood_length"] == '24"'
        assert row["foam_width"] == row["wood_width"]
        assert row["foam_length"] == row["wood_length"]
        assert row["foam_equals_wood"] is True
        assert row["wood_is_true_size"] is True
        assert row["fabric_width"] == '15"'
        assert row["fabric_length"] == '27"'
        assert row["fabric_is_separate"] is True


def test_kerf_keeps_parts_apart(monkeypatch, tmp_path):
    inches, nesting, _, _ = _reload(monkeypatch, tmp_path)
    result = nesting.nest_cut_list({
        "kerf": "1/8",
        "sheet_width": "29 1/2",
        "sheet_length": "48",
        "parts": [
            {"name": "A", "width": "10", "length": "10", "grain": "free"},
            {"name": "B", "width": "10", "length": "10", "grain": "free"},
        ],
    })
    sheet = result["wood_sheets"][0]
    parts = sheet["parts"]
    assert len(parts) == 2
    kerf = inches.parse_inches(sheet["kerf"])
    a, b = parts
    ax, ay = inches.parse_inches(a["x"]), inches.parse_inches(a["y"])
    aw, al = inches.parse_inches(a["width"]), inches.parse_inches(a["length"])
    bx, by = inches.parse_inches(b["x"]), inches.parse_inches(b["y"])
    same_row = ay == by
    same_col = ax == bx
    if same_row:
        gap = abs(bx - (ax + aw)) if bx >= ax + aw else abs(ax - (bx + inches.parse_inches(b["width"])))
        assert gap >= kerf
    elif same_col:
        gap = abs(by - (ay + al)) if by >= ay + al else abs(ay - (by + inches.parse_inches(b["length"])))
        assert gap >= kerf
    else:
        # placed on different shelves; still on one sheet with a yield fraction
        assert "/" in sheet["yield"]


def test_grain_blocks_rotate_when_over_width(monkeypatch, tmp_path):
    _, nesting, _, _ = _reload(monkeypatch, tmp_path)
    with pytest.raises(nesting.NestError, match="29 1/2"):
        nesting.nest_cut_list({
            "parts": [{"name": "Wide", "width": "32", "length": "12", "grain": "with"}],
        })
    result = nesting.nest_cut_list({
        "parts": [{"name": "Wide", "width": "32", "length": "12", "grain": "free"}],
    })
    # Rotates to 12 x 32 and stays on one stock sheet with tile marks.
    assert result["wood_sheets"]
    assert any(s.get("registration_marks") or s.get("tiled") or s.get("parts") for s in result["wood_sheets"])


def test_long_panel_tiles_with_registration_marks(monkeypatch, tmp_path):
    inches, nesting, _, _ = _reload(monkeypatch, tmp_path)
    result = nesting.nest_cut_list({
        "tile_length": "29 1/2",
        "parts": [{"name": "Long stretcher", "width": "5 1/2", "length": "60", "grain": "with"}],
    })
    sheets = result["wood_sheets"]
    assert sheets, "long panel must nest on a stock sheet"
    marked = [s for s in sheets if s.get("registration_marks")]
    assert marked, "long panel must carry registration marks for X-Carve tiles"
    for sheet in sheets:
        assert inches.parse_inches(sheet["sheet_width"]) <= inches.parse_inches("29 1/2")
        # One stock sheet, not one fake sheet per machine pass.
        assert inches.parse_inches(sheet["sheet_length"]) >= inches.parse_inches("60")
        for mark in sheet.get("registration_marks") or []:
            assert mark["mark_size"] == '1/2"'
            assert "." not in mark["x"]
    inches.assert_no_decimal_measurements(result)


def test_machine_width_is_twenty_nine_and_a_half(monkeypatch, tmp_path):
    _, nesting, _, _ = _reload(monkeypatch, tmp_path)
    result = nesting.nest_cut_list({"parts": _sample_parts()})
    assert result["machine"] == "X-Carve"
    assert result["machine_width"] == '29 1/2"'
    assert result["kerf"] == '1/8"'
    assert "." not in result["machine_width"]
    assert "." not in result["kerf"]


def test_pdf_has_yield_and_fractions(monkeypatch, tmp_path):
    _, nesting, _, pdf = _reload(monkeypatch, tmp_path)
    result = nesting.nest_cut_list({
        "title": "Marley bench nest",
        "job_id": "job-demo",
        "parts": _sample_parts() + [
            {"name": "Long panel", "width": "8", "length": "72", "grain": "with",
             "fabric": {"width": "10", "length": "76"}},
        ],
    })
    blob = pdf.render_nest_pdf(result)
    assert blob.startswith(b"%PDF")
    text = blob.decode("latin-1", errors="ignore")
    assert "yield" in text.lower()
    assert "29 1/2" in text or "1/8" in text
    assert "12 1/2" in text
    assert "registration" in text.lower() or "TILE" in text
    assert "Foam" in text or "FOAM" in text or "foam" in text
    # No decimal inch callouts like 29.5 or 12.5
    assert not re.search(r"\b\d+\.\d+\"", text)


def test_api_nest_and_pdf(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    from fastapi import FastAPI
    from fastapi.testclient import TestClient
    from app.routers import cnc_nesting
    app = FastAPI()
    app.include_router(cnc_nesting.router, prefix="/api/v1")
    client = TestClient(app)
    body = {
        "title": "API nest",
        "job_id": "job-api",
        "kerf": "1/8",
        "parts": _sample_parts(),
    }
    nest = client.post("/api/v1/cnc/nest", json=body)
    assert nest.status_code == 200, nest.text
    data = nest.json()
    assert data["machine_width"] == '29 1/2"'
    assert "/" in data["yields"]["wood"][0]["yield"]
    pdf = client.post("/api/v1/cnc/nest/pdf", json=body)
    assert pdf.status_code == 200, pdf.text
    assert pdf.headers["content-type"].startswith("application/pdf")
    assert pdf.content.startswith(b"%PDF")
