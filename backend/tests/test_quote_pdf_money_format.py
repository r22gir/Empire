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


def _grouped_quote(**extra) -> dict:
    quote = {
        "notes": "Sidemark: Nehal Elrefai. Widths are estimates.",
        "line_items": [
            {
                "description": "White lining",
                "quantity": 32,
                "unit": "yd",
                "rate": 10.5,
                "amount": 336,
                "category": "lining",
                "room": "Living Room",
            },
            {
                "description": "Blackout",
                "quantity": 14,
                "unit": "yd",
                "rate": 12,
                "amount": 168,
                "category": "fabric",
                "area": "Materials",
            },
        ],
    }
    quote.update(extra)
    return quote


def test_breakdown_quote_omits_the_top_line_table(monkeypatch, tmp_path):
    quotes = _quotes(monkeypatch, tmp_path)
    html = quotes.quote_pdf_work_html(quotes.quote_pdf_line_sections(_grouped_quote()))
    assert "Itemized Cost Breakdown" in html
    assert "Living Room Subtotal" in html
    assert "Materials Subtotal" in html
    assert "<th>Rate</th>" not in html
    assert html.index("Sidemark: Nehal Elrefai") < html.index("Itemized Cost Breakdown")
    assert html.index("Itemized Cost Breakdown") < html.index("Living Room Subtotal")


def test_quote_without_breakdown_keeps_the_top_line_table(monkeypatch, tmp_path):
    quotes = _quotes(monkeypatch, tmp_path)
    html = quotes.quote_pdf_work_html(quotes.quote_pdf_line_sections({
        "notes": "Confirm access.",
        "line_items": [{
            "description": "Install",
            "quantity": 1,
            "unit": "ea",
            "rate": 1200,
            "amount": 1200,
        }],
    }))
    assert "<th>Rate</th>" in html
    assert "$1,200.00" in html
    assert "Itemized Cost Breakdown" not in html
    assert html.index("Confirm access.") < html.index("<th>Rate</th>")


def test_show_flat_line_table_override_keeps_both(monkeypatch, tmp_path):
    quotes = _quotes(monkeypatch, tmp_path)
    html = quotes.quote_pdf_work_html(
        quotes.quote_pdf_line_sections(_grouped_quote(show_flat_line_table=True))
    )
    assert "<th>Rate</th>" in html
    assert "Itemized Cost Breakdown" in html
    assert html.index("<th>Rate</th>") < html.index("Itemized Cost Breakdown")
