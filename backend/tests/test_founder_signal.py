"""Studio founder-activity + family reserve signal (brief 8c).

Temp dirs only. No live /data, no real email/WhatsApp/SMS, no real contacts.
"""
from __future__ import annotations

import asyncio
import inspect
import json
import os
import sqlite3
import stat
import threading
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest


FAKE_WA_FOUNDER = "15555550100"
FAKE_WA_STRANGER = "15555550199"


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
    monkeypatch.delenv("FAMILY_ABSOLUTE_MAX_PCT", raising=False)
    monkeypatch.setenv("EMPIRE_USAGE_DEFAULT_BASELINE_TOKENS", "10000000")
    monkeypatch.setenv("MINIMAX_PLAN_HARD_STOP_PCT", "80")
    monkeypatch.setenv("WHATSAPP_FOUNDER_PHONES", FAKE_WA_FOUNDER)
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


def _freeze(signal_env, monkeypatch, when: datetime) -> None:
    """Pin the clock via monkeypatch so it cannot leak into later tests."""
    monkeypatch.setattr(signal_env["fa"], "_now", lambda: when)
    monkeypatch.setattr(signal_env["fs"], "_now", lambda: when)


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
    monkeypatch.setenv("FAMILY_ABSOLUTE_MAX_PCT", "42")
    assert fs.brother_ceiling_pct() == 42.0


def test_active_five_minutes_ago_blocks_overage(signal_env, monkeypatch):
    fa = signal_env["fa"]
    fs = signal_env["fs"]
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    _freeze(signal_env, monkeypatch, t0)
    fa.mark_founder_active("max_chat")
    t1 = t0 + timedelta(minutes=5)
    _freeze(signal_env, monkeypatch, t1)
    _seed_meter(signal_env["meter"], tokens=1000, month="2026-10")
    status = fs.write_family_signals(now=t1)
    assert status["founder_active"] is True
    assert status["overage_allowed"] is False
    assert status["reason"] == "founder_active"
    assert status["reserve_ok"] is True
    assert status["remaining_pct"] == 90.0


def test_inactive_two_hours_low_usage_allows_overage(signal_env, monkeypatch):
    fa = signal_env["fa"]
    fs = signal_env["fs"]
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    _freeze(signal_env, monkeypatch, t0)
    fa.mark_founder_active("max_chat")
    t1 = t0 + timedelta(hours=2)
    _freeze(signal_env, monkeypatch, t1)
    _seed_meter(signal_env["meter"], tokens=100_000, month="2026-10")
    status = fs.write_family_signals(now=t1)
    assert status["founder_active"] is False
    assert status["reserve_ok"] is True
    assert status["overage_allowed"] is True
    assert status["reason"] == "inactive_reserve_ok"


def test_reserve_ok_uses_remaining_pct_not_token_floor(signal_env, monkeypatch):
    """October ~8.15M tokens used to trip reserve_low via pool=max(used, 10M).

    Reserve is MiniMax remaining_pct >= FOUNDER_RESERVE_PCT. Token sums
    stay in status.json for information only.
    """
    fa = signal_env["fa"]
    fs = signal_env["fs"]
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    _freeze(signal_env, monkeypatch, t0)
    fa.mark_founder_active("max_chat")
    t1 = t0 + timedelta(hours=2)
    _freeze(signal_env, monkeypatch, t1)
    _seed_meter(signal_env["meter"], tokens=8_150_000, month="2026-10")
    status = fs.write_family_signals(now=t1)
    assert status["used_tokens"] == 8_150_000
    assert status["remaining_pct"] == 90.0
    assert status["reserve_ok"] is True
    assert status["overage_allowed"] is True
    assert status["reason"] == "inactive_reserve_ok"


def test_reserve_below_40_percent_not_allowed(signal_env, monkeypatch):
    fa = signal_env["fa"]
    fs = signal_env["fs"]
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "hot")
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    _freeze(signal_env, monkeypatch, t0)
    fa.mark_founder_active("max_chat")
    t1 = t0 + timedelta(hours=2)
    _freeze(signal_env, monkeypatch, t1)
    _seed_meter(signal_env["meter"], tokens=1000, month="2026-10")
    status = fs.write_family_signals(now=t1)
    assert status["founder_active"] is False
    assert status["remaining_pct"] == 15.0
    assert status["reserve_ok"] is False
    assert status["overage_allowed"] is False
    assert status["reason"] == "reserve_low"


def test_unreadable_usage_does_not_fail_reserve(signal_env, monkeypatch):
    """Usage DBs are informational. Junk files must not fail reserve_ok."""
    fa = signal_env["fa"]
    fs = signal_env["fs"]
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    _freeze(signal_env, monkeypatch, t0)
    fa.mark_founder_active("max_chat")
    t1 = t0 + timedelta(hours=2)
    _freeze(signal_env, monkeypatch, t1)
    junk = signal_env["amp"] / "usage" / "usage.db"
    junk.parent.mkdir(parents=True, exist_ok=True)
    junk.write_text("not-a-sqlite-database", encoding="utf-8")
    _seed_meter(signal_env["meter"], tokens=1000, month="2026-10")
    status = fs.write_family_signals(now=t1)
    assert status["reserve_ok"] is True
    assert status["remaining_pct"] == 90.0
    assert status["overage_allowed"] is True
    assert "used_tokens" in status


def test_unreadable_plan_remains_not_allowed(signal_env, monkeypatch):
    fa = signal_env["fa"]
    fs = signal_env["fs"]
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "down")
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    _freeze(signal_env, monkeypatch, t0)
    fa.mark_founder_active("max_chat")
    t1 = t0 + timedelta(hours=2)
    _freeze(signal_env, monkeypatch, t1)
    _seed_meter(signal_env["meter"], tokens=1000, month="2026-10")
    status = fs.write_family_signals(now=t1)
    assert status["reserve_ok"] is False
    assert status["overage_allowed"] is False
    assert status["reason"] == "remains_unavailable"
    assert status["remaining_pct"] is None


def test_stale_plan_remains_not_allowed(signal_env, monkeypatch):
    fa = signal_env["fa"]
    fs = signal_env["fs"]
    monkeypatch.setenv("MINIMAX_REMAINS_STUB", "stale")
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    _freeze(signal_env, monkeypatch, t0)
    fa.mark_founder_active("max_chat")
    t1 = t0 + timedelta(hours=2)
    _freeze(signal_env, monkeypatch, t1)
    _seed_meter(signal_env["meter"], tokens=1000, month="2026-10")
    status = fs.write_family_signals(now=t1)
    assert status["reserve_ok"] is False
    assert status["overage_allowed"] is False
    assert status["reason"] == "remains_stale"
    assert status["remaining_pct"] == 90.0


def test_stale_cache_age_fails_closed_without_stub(signal_env, monkeypatch):
    fs = signal_env["fs"]
    monkeypatch.delenv("MINIMAX_REMAINS_STUB", raising=False)
    monkeypatch.setenv("FOUNDER_REMAINS_MAX_AGE_S", "30")

    def _fresh_unaged():
        return {
            "remains": {"ok": True, "available": True, "remaining_pct": 55.0, "used_pct": 45.0},
            "credits": {"ok": False, "available": False, "balance": None},
        }

    monkeypatch.setattr("app.services.minimax_meter._plan_snapshot", _fresh_unaged)
    monkeypatch.setattr("app.services.minimax_meter._stub_snapshot", lambda: None)
    monkeypatch.setattr(
        "app.services.minimax_quota.remains_cache_age_s", lambda: 500.0
    )
    t1 = datetime(2026, 10, 16, 14, 0, tzinfo=timezone.utc)
    status = fs.write_family_signals(now=t1)
    assert status["reserve_ok"] is False
    assert status["reason"] == "remains_stale"
    assert status["remaining_pct"] == 55.0


def test_atomic_write_permissions_and_schema(signal_env, monkeypatch):
    fa = signal_env["fa"]
    fs = signal_env["fs"]
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    _freeze(signal_env, monkeypatch, t0)
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
        assert set(fs.REQUIRED_STATUS_KEYS).issubset(data.keys())
        assert set(data.keys()) <= set(fs.STATUS_KEYS)
        assert data["schema"] == 1
        assert data["brother_ceiling_pct"] == 40.0
        tmp_leftovers = list(dest.parent.glob(".status.json.tmp.*"))
        assert tmp_leftovers == []
    assert not (signal_env["missing"] / "founder-signal").exists()


def test_brother_ceiling_written_from_absolute_max(signal_env, monkeypatch):
    fs = signal_env["fs"]
    monkeypatch.setenv("FAMILY_ABSOLUTE_MAX_PCT", "38")
    monkeypatch.setenv("FAMILY_BROTHER_CEILING_PCT", "22")
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    status = fs.write_family_signals(now=t0)
    assert status["brother_ceiling_pct"] == 38.0
    data = json.loads(
        (signal_env["amp"] / "founder-signal" / "status.json").read_text(encoding="utf-8")
    )
    assert data["schema"] == 1
    assert data["brother_ceiling_pct"] == 38.0


def test_maybe_mark_skips_non_founder(signal_env):
    fa = signal_env["fa"]
    fa.maybe_mark_founder_active(False, "max_chat")
    assert fa.last_active_at() is None
    fa.maybe_mark_founder_active(True, "max_chat")
    assert fa.last_active_at() is not None


def test_http_middleware_skips_get_marks_post(signal_env):
    fa = signal_env["fa"]
    fa.mark_http_founder_activity("GET", True)
    assert fa.last_active_at() is None
    fa.mark_http_founder_activity("HEAD", True)
    fa.mark_http_founder_activity("OPTIONS", True)
    assert fa.last_active_at() is None
    fa.mark_http_founder_activity("POST", False)
    assert fa.last_active_at() is None
    fa.mark_http_founder_activity("POST", True)
    assert fa.last_active_at() is not None
    main_src = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text(
        encoding="utf-8"
    )
    assert "mark_http_founder_activity" in main_src
    assert "request.method" in main_src


def test_mark_does_not_write_family_signal(signal_env, monkeypatch):
    fa = signal_env["fa"]
    fs = signal_env["fs"]
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    _freeze(signal_env, monkeypatch, t0)
    fa.mark_founder_active("max_chat")
    dest = signal_env["amp"] / "founder-signal" / "status.json"
    assert not dest.exists()
    activity = fa.activity_path()
    assert activity.is_file()
    written = []
    orig = fs.write_family_signals

    def _capture(*a, **k):
        written.append(True)
        return orig(*a, **k)

    monkeypatch.setattr(fs, "write_family_signals", _capture)
    fa.mark_founder_active("max_chat")
    assert written == []


def test_write_family_signals_offthread_uses_worker_thread(signal_env, monkeypatch):
    fs = signal_env["fs"]
    t0 = datetime(2026, 10, 16, 12, 0, tzinfo=timezone.utc)
    _freeze(signal_env, monkeypatch, t0)
    _seed_meter(signal_env["meter"], tokens=1000, month="2026-10")
    main_ident = threading.get_ident()
    seen: dict[str, int] = {}
    orig = fs.write_family_signals

    def _wrapper(*a, **k):
        seen["ident"] = threading.get_ident()
        return orig(*a, **k)

    monkeypatch.setattr(fs, "write_family_signals", _wrapper)
    status = asyncio.run(fs.write_family_signals_offthread(t0))
    assert seen["ident"] != main_ident
    assert status["schema"] == 1
    dest = signal_env["amp"] / "founder-signal" / "status.json"
    assert dest.is_file()
    main_src = (Path(__file__).resolve().parents[1] / "app" / "main.py").read_text(
        encoding="utf-8"
    )
    assert "write_family_signals_offthread" in main_src
    assert "to_thread" in inspect.getsource(fs.write_family_signals_offthread)


def test_whatsapp_inbound_and_voice_mark_allowlisted(signal_env, monkeypatch):
    fa = signal_env["fa"]
    import app.services.max.whatsapp_channel as wa

    marks: list[str] = []

    def _fake_mark(source="studio"):
        marks.append(source)
        return {"schema": 1, "last_active_at": "2026-10-16T12:00:00Z", "source": source}

    monkeypatch.setattr(fa, "mark_founder_active", _fake_mark)
    monkeypatch.setattr("app.services.founder_activity.mark_founder_active", _fake_mark)
    monkeypatch.setattr(wa, "founder_allowlist", lambda: frozenset({FAKE_WA_FOUNDER}))

    assert wa.mark_founder_whatsapp_activity(FAKE_WA_FOUNDER, "whatsapp_inbound") is True
    assert marks == ["whatsapp_inbound"]
    marks.clear()
    assert wa.mark_founder_whatsapp_activity(FAKE_WA_STRANGER, "whatsapp_inbound") is False
    assert marks == []

    inbound_src = inspect.getsource(wa.process_webhook)
    assert "mark_founder_whatsapp_activity" in inbound_src
    assert "whatsapp_inbound" in inbound_src
    voice_path = Path(__file__).resolve().parents[1] / "app" / "services" / "max" / "whatsapp_calling.py"
    voice_src = voice_path.read_text(encoding="utf-8")
    assert "mark_founder_whatsapp_activity" in voice_src
    assert "whatsapp_voice" in voice_src


def test_chat_service_marks_canonical_founder_not_non_founder(signal_env, monkeypatch):
    """Telegram/WhatsApp go through _chat_with_max_service, not chat_with_max."""
    import importlib

    fa = signal_env["fa"]
    marks: list[str] = []

    def _fake_mark(source="studio"):
        marks.append(source)
        return {"schema": 1, "last_active_at": "2026-10-16T12:00:00Z", "source": source}

    monkeypatch.setattr(fa, "mark_founder_active", _fake_mark)
    monkeypatch.setattr("app.services.founder_activity.mark_founder_active", _fake_mark)
    max_router = importlib.import_module("app.routers.max.router")

    async def fake_impl(*_a, **_k):
        return max_router.ChatResponse(response="ok", model_used="test-model")

    monkeypatch.setattr(max_router, "_chat_with_max_service_impl", fake_impl)
    request = max_router.ChatRequest(message="hello from studio", history=[], channel="telegram")
    asyncio.run(
        max_router._chat_with_max_service(
            request,
            canonical_channel="telegram",
            canonical_chat_id="5550100",
            canonical_founder=True,
        )
    )
    assert marks == ["telegram"]
    marks.clear()
    asyncio.run(
        max_router._chat_with_max_service(
            request,
            canonical_channel="whatsapp",
            canonical_chat_id=FAKE_WA_FOUNDER,
            canonical_founder=False,
        )
    )
    assert marks == []
    marks.clear()
    asyncio.run(
        max_router._chat_with_max_service(
            request,
            canonical_channel="whatsapp",
            canonical_chat_id=FAKE_WA_FOUNDER,
            canonical_founder=True,
        )
    )
    assert marks == ["whatsapp_chat"]


def test_mark_founder_active_on_founder_chat_not_on_non_founder(signal_env, monkeypatch):
    """chat_with_max marks founder activity only when the caller is the founder."""
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

    async def fake_impl(*_a, **_k):
        return max_router.ChatResponse(response="ok", model_used="test-model")

    monkeypatch.setattr(max_router, "_chat_with_max_service_impl", fake_impl)

    request = max_router.ChatRequest(message="hello from studio", history=[], channel="web")
    asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))
    assert any(src.startswith("max_chat") for src in marks)

    marks.clear()
    monkeypatch.setattr(max_router, "is_founder_message", lambda *_a, **_k: False)
    asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))
    assert marks == []
