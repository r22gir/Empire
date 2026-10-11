"""Grok Bot (Chief e) / Cursor in the API-expense module: dollars only from Rafael's entries."""
import pytest


def test_manual_costs_no_invented_numbers(tmp_path, monkeypatch):
    from app.services.max import manual_costs as mc
    monkeypatch.setattr(mc, "_db_path", lambda: str(tmp_path / "costs.db"))
    monkeypatch.setattr(mc, "_cursor_builds", lambda days: 0)
    row = mc.summary(30)[0]
    assert row["provider"] == "grok_bot" and row["cost"] is None and row["status"] == "not_entered"
    from datetime import datetime
    m = datetime.now().strftime("%Y-%m")
    mc.add_entry("grok_bot", m, 40, "first")
    mc.add_entry("grok_bot", m, 42.5, "corrected")
    row = mc.summary(30)[0]
    assert row["cost"] == 42.5 and row["status"] == "entered"
    with pytest.raises(ValueError):
        mc.add_entry("grok_bot", "2026-13", 1)
    with pytest.raises(ValueError):
        mc.add_entry("nope", m, 1)
