"""LuxeForge designer selection board. Isolated DB. Never writes live quotes."""

from __future__ import annotations

import os

from fastapi.testclient import TestClient

from app.main import app
from app.services.luxeforge.selection_board import board_to_estimate, demo_board


client = TestClient(app)


def test_catalog_and_preview_never_writes_quote(isolated_empire_db):
    assert os.environ.get("EMPIRE_TASK_DB") == isolated_empire_db
    cat = client.get("/api/v1/luxe/catalog")
    assert cat.status_code == 200, cat.text
    body = cat.json()
    assert len(body["fabrics"]) >= 4
    assert len(body["finishes"]) >= 4
    assert len(body["photos"]) >= 3
    assert body["wrote_live"] is False

    demo = client.get("/api/v1/luxe/boards/demo")
    assert demo.status_code == 200
    estimate = demo.json()["estimate"]
    assert estimate["wrote_quote"] is False
    assert estimate["wrote_live"] is False
    assert estimate["sent"] is False
    assert estimate["subtotal"] > 0
    assert estimate["catalog_counts"]["fabrics"] >= 1
    assert estimate["catalog_counts"]["photos"] >= 1

    preview = client.post("/api/v1/luxe/estimate/preview", json={
        "title": "Study",
        "client_name": "Preview only",
        "treatment": "drapery",
        "selections": [
            {"id": "fab-silk-taffeta", "qty": 10},
            {"id": "fin-brass-antique", "qty": 1},
            {"id": "pho-drawing-room"},
        ],
    })
    assert preview.status_code == 200, preview.text
    out = preview.json()
    assert out["wrote_quote"] is False
    assert out["wrote_live"] is False
    assert out["estimate"]["materials"] > 0
    assert "disclaimer" in out["estimate"]


def test_persisted_board_stays_off_live_quotes(isolated_empire_db):
    created = client.post("/api/v1/luxe/boards", json={
        "title": "Banquette study",
        "client_name": "Sample",
        "treatment": "upholstery",
        "selections": [
            {"id": "fab-mohair-velvet", "qty": 12},
            {"id": "fin-walnut-handrub", "qty": 1},
        ],
    })
    assert created.status_code == 200, created.text
    assert created.json()["wrote_quote"] is False
    board_id = created.json()["board"]["id"]
    assert board_id != "demo"
    est = client.post(f"/api/v1/luxe/boards/{board_id}/estimate")
    assert est.status_code == 200
    assert est.json()["wrote_quote"] is False
    assert est.json()["estimate"]["treatment"] == "upholstery"
    assert est.json()["estimate"]["subtotal"] > 1000


def test_board_to_estimate_math_is_preview_only():
    board = demo_board()
    est = board_to_estimate(board)
    assert est["wrote_quote"] is False
    assert est["wrote_live"] is False
    assert est["materials"] > 0
    assert est["labor"] > 0
    assert est["deposit_suggested"] == round(est["subtotal"] * 0.5, 2)
    assert all(line["amount"] >= 0 for line in est["lines"])
