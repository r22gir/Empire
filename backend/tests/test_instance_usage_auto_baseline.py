"""Family usage cap uses recorded EmpireBox totals — no baseline env required."""
from __future__ import annotations

import sqlite3
from pathlib import Path

from datetime import datetime, timezone


def _env(monkeypatch, tmp_path, edition="amp"):
    monkeypatch.setenv("EMPIRE_EDITION", edition)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("ASSISTANT_NAME", "Max-e" if edition == "amp" else "Maxine")
    monkeypatch.delenv("EMPIRE_USAGE_BASELINE_MONTHLY_USD", raising=False)
    monkeypatch.delenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", raising=False)
    monkeypatch.delenv("EMPIRE_USAGE_PEER_DATA_DIRS", raising=False)


def _seed_usage_db(root: Path, tokens: int, provider: str = "minimax") -> Path:
    folder = root / "usage"
    folder.mkdir(parents=True, exist_ok=True)
    db = folder / "usage.db"
    now = datetime.now(timezone.utc)
    conn = sqlite3.connect(db)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS llm_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            day TEXT NOT NULL,
            month TEXT NOT NULL,
            model TEXT,
            provider TEXT,
            input_tokens INTEGER NOT NULL DEFAULT 0,
            output_tokens INTEGER NOT NULL DEFAULT 0,
            cost_usd REAL NOT NULL DEFAULT 0,
            kind TEXT,
            blocked INTEGER NOT NULL DEFAULT 0
        )
        """
    )
    conn.execute(
        """
        INSERT INTO llm_usage (
            created_at, day, month, model, provider,
            input_tokens, output_tokens, cost_usd, kind, blocked
        ) VALUES (?,?,?,?,?,?,?,?,?,0)
        """,
        (
            now.isoformat(),
            now.strftime("%Y-%m-%d"),
            now.strftime("%Y-%m"),
            "MiniMax-M3",
            provider,
            int(tokens),
            0,
            0.0,
            "chat",
        ),
    )
    conn.commit()
    conn.close()
    return db


def test_cap_enforces_without_baseline_env(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    monkeypatch.setattr("app.services.instance_usage._usage_data_roots", lambda: [tmp_path])
    from app.services.instance_usage import (
        DEFAULT_BASELINE_MONTHLY_TOKENS,
        enforce_usage_cap,
        record_usage,
        usage_summary,
    )

    empty = usage_summary()
    assert empty["enforced"] is True
    assert empty["baseline_basis"] == "recorded_tokens"
    assert empty["baseline"] == DEFAULT_BASELINE_MONTHLY_TOKENS
    assert empty["allowance"] == DEFAULT_BASELINE_MONTHLY_TOKENS * 0.20
    assert empty["remaining_percent"] == 100.0
    assert empty["level"] == "ok"
    assert empty["total_spend_hit"] is False
    assert "EMPIRE_USAGE_BASELINE" not in (empty["message"] or "")

    record_usage(input_tokens=int(DEFAULT_BASELINE_MONTHLY_TOKENS * 0.16), output_tokens=0)
    warned = usage_summary()
    assert warned["level"] == "warn"
    assert warned["remaining_percent"] == 20.0
    assert "Queda el 20%" in warned["message"]
    assert enforce_usage_cap(text="hola") is None


def test_recorded_total_across_editions_sets_baseline(monkeypatch, tmp_path):
    mine = tmp_path / "amp"
    peer = tmp_path / "maxine"
    _env(monkeypatch, mine)
    monkeypatch.setenv("EMPIRE_USAGE_DEFAULT_BASELINE_TOKENS", "1000")
    monkeypatch.setattr("app.services.instance_usage._usage_data_roots", lambda: [mine, peer])
    _seed_usage_db(peer, 800, provider="groq")
    from app.services.instance_usage import (
        enforce_usage_cap,
        record_usage,
        recorded_usage_across_editions,
        usage_summary,
    )

    record_usage(input_tokens=100, output_tokens=0, provider="minimax")
    totals = recorded_usage_across_editions()
    assert totals["tokens"] == 900
    summary = usage_summary()
    assert summary["baseline_basis"] == "recorded_tokens"
    assert summary["baseline"] == 900
    assert summary["allowance"] == 180
    assert summary["used"] == 100
    assert summary["level"] == "ok"
    assert summary["remaining_percent"] == 44.4

    record_usage(input_tokens=90, output_tokens=0)
    over = usage_summary()
    assert over["used"] == 190
    assert over["level"] == "blocked"
    assert over["total_spend_hit"] is False
    assert enforce_usage_cap(text="corto") is None
    assert enforce_usage_cap(text="x" * 500)


def test_short_chats_stop_only_at_total_spend(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    monkeypatch.setenv("EMPIRE_USAGE_DEFAULT_BASELINE_TOKENS", "1000")
    monkeypatch.setattr("app.services.instance_usage._usage_data_roots", lambda: [tmp_path])
    from app.services.instance_usage import enforce_usage_cap, record_usage, usage_summary

    record_usage(input_tokens=1000, output_tokens=0)
    summary = usage_summary()
    assert summary["baseline"] == 1000
    assert summary["allowance"] == 200
    assert summary["total_spend_hit"] is True
    assert summary["level"] == "blocked"
    assert summary["remaining_percent"] == 0.0
    refused = enforce_usage_cap(text="hola")
    assert refused and "tope total" in refused
    assert "mensajes cortos quedan en pausa" in refused
