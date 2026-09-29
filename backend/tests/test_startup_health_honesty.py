"""startup_health must report honesty vs live repo HEAD."""
from __future__ import annotations

import json
from pathlib import Path
from unittest import mock

from app.services.max import startup_health as sh


def test_enrich_marks_stale_when_boot_commit_differs(tmp_path, monkeypatch):
    record = {
        "running_commit_hash": "deadbeef",
        "running_branch": "feature/drawing-standard",
        "recorded_at": "2026-09-25T15:56:05.916066+00:00",
        "known_stale_state_conditions": [],
    }
    path = tmp_path / "startup_health.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setattr(sh, "STARTUP_HEALTH_PATH", path)

    with mock.patch.object(sh, "_live_repo_commit", return_value=("81b120e", "feature/drawing-standard")):
        enriched = sh.enrich_startup_health_record()

    assert enriched is not None
    assert enriched["running_commit_hash"] == "deadbeef"  # boot truth preserved
    assert enriched["boot_commit_hash"] == "deadbeef"
    assert enriched["current_repo_commit"] == "81b120e"
    assert enriched["matches_current_commit"] is False
    assert enriched["honesty"] == "stale_vs_repo_head"
    assert "81b120e" in (enriched["warning"] or "")
    assert "startup_commit_stale_vs_repo_head" in enriched["known_stale_state_conditions"]


def test_enrich_ok_when_boot_matches_live(tmp_path, monkeypatch):
    record = {
        "running_commit_hash": "81b120e",
        "running_branch": "feature/drawing-standard",
        "recorded_at": "2026-09-26T05:00:00+00:00",
        "known_stale_state_conditions": ["startup_commit_stale_vs_repo_head"],
    }
    path = tmp_path / "startup_health.json"
    path.write_text(json.dumps(record), encoding="utf-8")
    monkeypatch.setattr(sh, "STARTUP_HEALTH_PATH", path)

    with mock.patch.object(sh, "_live_repo_commit", return_value=("81b120e", "feature/drawing-standard")):
        enriched = sh.enrich_startup_health_record()

    assert enriched["matches_current_commit"] is True
    assert enriched["honesty"] == "ok"
    assert enriched["warning"] is None
    assert "startup_commit_stale_vs_repo_head" not in enriched["known_stale_state_conditions"]
