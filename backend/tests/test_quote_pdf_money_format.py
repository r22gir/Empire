"""Flat quote PDF money uses thousands separators, and cost groups name themselves."""
from __future__ import annotations

import sys
import types
from pathlib import Path


def _quotes(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DB", str(tmp_path / "empire.db"))
    max_name = "app.services.max"
    existing = sys.modules.get(max_name)
    if existing is None or not getattr(existing, "__file__", None):
        pkg = types.ModuleType(max_name)
        pkg.__path__ = [str(Path(__file__).resolve().parents[1] / "app" / "services" / "max")]
        pkg.__package__ = max_name
        sys.modules[max_name] = pkg
    import app.routers.quotes as quotes
    return quotes


def test_flat_quote_rate_and_amount_use_thousands_separators(monkeypatch, tmp_path):
    quotes = _quotes(monkeypatch, tmp_path)
    html = quotes._flat_quote_lines_html([
        {
            "description": "White lining",
            "quantity": 136,
            "unit": "yd",
            "rate": 10.5,
            "amount": 1428,
        },
        {
            "description": "Panels",
            "quantity": 1,
            "unit": "ea",
            "rate": 1933.33,
            "amount": 2644,
        },
    ])
    assert "$10.50" in html
    assert "$1,428.00" in html
    assert "$1,933.33" in html
    assert "$2,644.00" in html
    assert "$1428.00" not in html
    assert "$2644.00" not in html


def test_cost_breakdown_subtotal_uses_the_group_name(monkeypatch, tmp_path):
    quotes = _quotes(monkeypatch, tmp_path)
    html = quotes._build_line_items_html([
        {
            "description": "Panels",
            "quantity": 2,
            "rate": 1200,
            "amount": 2400,
            "category": "labor",
            "room": "Living Room",
        },
        {
            "description": "Lining",
            "quantity": 10,
            "rate": 18.5,
            "amount": 185,
            "category": "fabric",
            "area": "Materials",
        },
    ])
    assert "Living Room Subtotal" in html
    assert "Materials Subtotal" in html
    assert "$2,400.00" in html
    assert "$185.00" in html
    assert "Room Subtotal" not in html.replace("Living Room Subtotal", "")
