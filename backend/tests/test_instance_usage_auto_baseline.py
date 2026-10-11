"""Family usage cap uses recorded EmpireBox totals — no baseline env required."""
from __future__ import annotations

import asyncio
import logging
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
    monkeypatch.setenv("EMPIRE_USAGE_DEFAULT_BASELINE_TOKENS", "500")
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

    record_usage(input_tokens=110, output_tokens=0)
    over = usage_summary()
    assert over["used"] == 210
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


def test_public_usage_hides_empirebox_totals(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "1000")
    monkeypatch.setattr("app.services.instance_usage._usage_data_roots", lambda: [tmp_path])
    from app.services.instance_usage import public_usage_summary, record_usage, usage_summary

    record_usage(input_tokens=15, output_tokens=0)
    internal = usage_summary()
    assert internal["allowance"] == 200
    assert internal["baseline"] == 1000
    public = public_usage_summary()
    assert public["used_percent"] == 7.5
    assert public["remaining_percent"] == 92.5
    assert public["level"] == "ok"
    hidden = {"baseline", "baseline_basis", "allowance", "used", "day", "month", "ratio"}
    assert hidden.isdisjoint(public)


def test_chat_stream_respects_usage_cap(monkeypatch, tmp_path):
    _env(monkeypatch, tmp_path)
    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "1000")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    monkeypatch.setattr("app.services.instance_usage._usage_data_roots", lambda: [tmp_path])
    from app.services.instance_usage import record_usage
    from app.services.max.ai_router import AIMessage, AIResponse, AIRouter

    async def fake_selected(self, **_kwargs):
        return AIResponse(content="STREAMED", model_used="minimax-test")

    monkeypatch.setattr(AIRouter, "_chat_via_selected_routing", fake_selected)
    router = AIRouter()

    async def collect(text: str):
        return [
            item
            async for item in router.chat_stream(
                [AIMessage(role="user", content=text)],
                source="web",
            )
        ]

    record_usage(input_tokens=200, output_tokens=0)
    short = asyncio.run(collect("hola"))
    assert short == [("STREAMED", "minimax-test")]

    heavy = asyncio.run(collect("x" * 500))
    assert heavy[0][1] == "usage-cap"
    assert "tope" in heavy[0][0]

    record_usage(input_tokens=800, output_tokens=0)
    stopped = asyncio.run(collect("hola"))
    assert stopped[0][1] == "usage-cap"
    assert "tope total" in stopped[0][0]


def test_usage_cap_check_logs_warning(monkeypatch, tmp_path, caplog):
    _env(monkeypatch, tmp_path)
    from app.services.max.ai_router import AIMessage, AIRouter

    def boom(**_kwargs):
        raise RuntimeError("cap boom")

    monkeypatch.setattr("app.services.instance_usage.enforce_usage_cap", boom)
    router = AIRouter()
    with caplog.at_level(logging.WARNING, logger="max.ai_router"):
        _model, refusal = router._family_chat_prep(
            [AIMessage(role="user", content="hola")],
            desk=None,
            tools=False,
            source="",
            image_filename=None,
            model=None,
        )
    assert refusal is None
    assert "usage cap check failed open" in caplog.text
    assert "chat proceeds without a cap refusal" in caplog.text
