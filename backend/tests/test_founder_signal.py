"""Studio founder-activity + family reserve signal (brief 8c).

Temp dirs only. No live /data, no real email/WhatsApp/SMS, no real contacts.
"""
from __future__ import annotations

import json
import os
import sqlite3
import stat
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


def _block_live_sends(monkeypatch) -> None:
    def _boom(*_a, **_k):
        raise AssertionError("tests must not send live email, WhatsApp, or SMS")

    monkeypatch.setattr(
        "app.services.max.email_service.EmailService.send", _boom, raising=False
    )
    monkeypatch.setattr(
        "app.services.max.whatsapp_channel.send_template", _boom, raising=False
    )


def _seed_usage_db(path: Path, *, tokens: int, month: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
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
                f"{month}-01T00:00:00Z",
                f"{month}-01",
                month,
                "MiniMax-M3",
                "minimax",
                int(tokens),
                0,
                0.0,
                "chat",
            ),
        )
        conn.commit()
    finally:
        conn.close()


def _seed_meter(meter_dir: Path, *, tokens: int, month: str) -> None:
    path = meter_dir / "workroom" / "calls-workroom.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    rec = {
        "id": "seedmeter1",
        "ts": f"{month}-01T00:00:00Z",
        "edition": "workroom",
        "kind": "text",
        "status": "settled",
        "input_tokens": int(tokens),
        "output_tokens": 0,
        "blocked": False,
        "model": "MiniMax-M3",
    }
    path.write_text(json.dumps(rec) + "\n", encoding="utf-8")
    os.chmod(path, 0o600)


@pytest.fixture
def signal_env(monkeypatch, tmp_path):
    _block_live_sends(monkeypatch)
    amp = tmp_path / "amp"
    maxine = tmp_path / "maxine"
    missing = tmp_path / "not-created"
    studio = tmp_path / "studio"
    meter = tmp_path / "meter"
    amp.mkdir()
    maxine.mkdir()
    studio.mkdir()
    meter.mkdir()
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(studio))
    monkeypatch.setenv("EMPIRE_EDITION", "studio")
    monkeypatch.setenv("FAMILY_SIGNAL_DIRS", f"{amp},{maxine},{missing}")
    monkeypatch.setenv("MINIMAX_METER_DIR", str(meter))
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "ok")
    monkeypatch.setenv("MINIMAX_REMAINS_PROBE", "0")
    monkeypatch.setenv("FOUNDER_ACTIVE_WINDOW_MIN", "30")
    monkeypatch.setenv("FOUNDER_RESERVE_PCT", "40")
    monkeypatch.setenv("FAMILY_BROTHER_CEILING_PCT", "40")
    monkeypatch.setenv("EMPIRE_USAGE_DEFAULT_BASELINE_TOKENS", "10000000")
    monkeypatch.setenv("MINIMAX_PLAN_HARD_STOP_PCT", "80")
    import app.services.founder_activity as fa
    import app.services.family_signal as fs

    fa._last_active_at = None
    fa._last_source = ""
    fa._last_disk_write_mono = 0.0
    return {
        "amp": amp,
        "maxine": maxine,
        "missing": missing,
        "studio": studio,
        "meter": meter,
        "fa": fa,
        "fs": fs,
    }


def _freeze(signal_env, when: datetime) -> None:
    signal_env["fa"]._now = lambda: when
    signal_env["fs"]._now = lambda: when


def test_brother_ceiling_and_reserve_env(signal_env, monkeypatch):
    fs = signal_env["fs"]
    assert fs.brother_ceiling_pct() == 40.0
    assert fs.reserve_pct() == 40.0
    monkeypatch.setenv("FAMILY_BROTHER_CEILING_PCT", "35")
    monkeypatch.setenv("FOUNDER_RESERVE_PCT", "50")
    monkeypatch.setenv("FOUNDER_ACTIVE_WINDOW_MIN", "10")
    assert fs.brother_ceiling_pct() == 35.0
    assert fs.reserve_pct() == 50.0
    assert signal_env["fa"].active_window_min() == 10


def test_active_five_minutes_ago_blocks_overage(signal_env):
    fa = signal_env["fa"]
    fs = signal_env["fs"]
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    _freeze(signal_env, t0)
    fa.mark_founder_active("max_chat")
    t1 = t0 + timedelta(minutes=5)
    _freeze(signal_env, t1)
    _seed_meter(signal_env["meter"], tokens=1000, month="2026-10")
    status = fs.write_family_signals(now=t1)
    assert status["founder_active"] is True
    assert status["overage_allowed"] is False
    assert status["reason"] == "founder_active"
    assert status["reserve_ok"] is True


def test_inactive_two_hours_low_usage_allows_overage(signal_env):
    fa = signal_env["fa"]
    fs = signal_env["fs"]
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    _freeze(signal_env, t0)
    fa.mark_founder_active("max_chat")
    t1 = t0 + timedelta(hours=2)
    _freeze(signal_env, t1)
    _seed_meter(signal_env["meter"], tokens=100_000, month="2026-10")
    status = fs.write_family_signals(now=t1)
    assert status["founder_active"] is False
    assert status["reserve_ok"] is True
    assert status["overage_allowed"] is True
    assert status["reason"] == "inactive_reserve_ok"


def test_reserve_below_40_percent_not_allowed(signal_env):
    fa = signal_env["fa"]
    fs = signal_env["fs"]
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    _freeze(signal_env, t0)
    fa.mark_founder_active("max_chat")
    t1 = t0 + timedelta(hours=2)
    _freeze(signal_env, t1)
    _seed_meter(signal_env["meter"], tokens=7_000_000, month="2026-10")
    status = fs.write_family_signals(now=t1)
    assert status["founder_active"] is False
    assert status["reserve_ok"] is False
    assert status["overage_allowed"] is False
    assert status["reason"] == "reserve_low"


def test_unreadable_usage_not_allowed(signal_env):
    fa = signal_env["fa"]
    fs = signal_env["fs"]
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    _freeze(signal_env, t0)
    fa.mark_founder_active("max_chat")
    t1 = t0 + timedelta(hours=2)
    _freeze(signal_env, t1)
    junk = signal_env["amp"] / "usage" / "usage.db"
    junk.parent.mkdir(parents=True, exist_ok=True)
    junk.write_text("not-a-sqlite-database", encoding="utf-8")
    _seed_meter(signal_env["meter"], tokens=1000, month="2026-10")
    status = fs.write_family_signals(now=t1)
    assert status["reserve_ok"] is False
    assert status["overage_allowed"] is False
    assert status["reason"] == "inputs_unreadable"


def test_unreadable_plan_remains_not_allowed(signal_env, monkeypatch):
    fa = signal_env["fa"]
    fs = signal_env["fs"]
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "down")
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    _freeze(signal_env, t0)
    fa.mark_founder_active("max_chat")
    t1 = t0 + timedelta(hours=2)
    _freeze(signal_env, t1)
    _seed_meter(signal_env["meter"], tokens=1000, month="2026-10")
    status = fs.write_family_signals(now=t1)
    assert status["overage_allowed"] is False
    assert status["reason"] == "inputs_unreadable"


def test_atomic_write_permissions_and_schema(signal_env):
    fa = signal_env["fa"]
    fs = signal_env["fs"]
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    _freeze(signal_env, t0)
    fa.mark_founder_active("max_chat")
    _seed_meter(signal_env["meter"], tokens=1000, month="2026-10")
    fs.write_family_signals(now=t0)
    for root in (signal_env["amp"], signal_env["maxine"]):
        dest = root / "founder-signal" / "status.json"
        assert dest.is_file()
        mode = stat.S_IMODE(dest.stat().st_mode)
        assert mode == 0o600
        dir_mode = stat.S_IMODE(dest.parent.stat().st_mode)
        assert dir_mode == 0o700
        data = json.loads(dest.read_text(encoding="utf-8"))
        assert set(data.keys()) == set(fs.STATUS_KEYS)
        assert data["schema"] == 1
        tmp_leftovers = list(dest.parent.glob(".status.json.tmp.*"))
        assert tmp_leftovers == []
    assert not (signal_env["missing"] / "founder-signal").exists()


def test_maybe_mark_skips_non_founder(signal_env):
    fa = signal_env["fa"]
    fa.maybe_mark_founder_active(False, "max_chat")
    assert fa.last_active_at() is None
    fa.maybe_mark_founder_active(True, "max_chat")
    assert fa.last_active_at() is not None


def test_mark_founder_active_on_founder_chat_not_on_non_founder(signal_env, monkeypatch):
    """chat_with_max marks founder activity only when the caller is the founder."""
    import asyncio
    import importlib

    from fastapi import BackgroundTasks, Response

    fa = signal_env["fa"]
    marks = []

    def _fake_mark(source="studio"):
        marks.append(source)
        return {"schema": 1, "last_active_at": "2026-10-16T12:00:00Z", "source": source}

    monkeypatch.setattr(fa, "mark_founder_active", _fake_mark)
    monkeypatch.setattr(
        "app.services.founder_activity.mark_founder_active", _fake_mark
    )
    max_router = importlib.import_module("app.routers.max.router")
    monkeypatch.setattr(max_router, "is_founder_message", lambda *_a, **_k: True)

    async def fake_ai(*_a, **_k):
        from app.services.max.ai_router import AIResponse

        return AIResponse(content="ok", model_used="test-model")

    monkeypatch.setattr(max_router.ai_router, "chat", fake_ai)

    request = max_router.ChatRequest(message="hello from studio", history=[], channel="web")
    asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))
    assert any(src.startswith("max_chat") for src in marks)

    marks.clear()
    monkeypatch.setattr(max_router, "is_founder_message", lambda *_a, **_k: False)
    asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))
    assert marks == []
