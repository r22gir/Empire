"""Morning Brief next_run: always forward in America/New_York, never catch-up.

Port of PR #198 (Maxine) onto Max-e. No live SMTP. Fake owner addresses only.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import pytest

from app.services.max import scheduler as sched


ET = ZoneInfo("America/New_York")
FAKE_OWNER = "juan.owner@example.com"

# Same live-bug window as Maxine PR #198: 10:40 PM ET Oct 21 2026, next_run Oct 18.
STALE_NEXT_RUN = "2026-10-18T08:00:00-04:00"
BUG_NOW = datetime(2026, 10, 21, 22, 40, tzinfo=ET)
RECOVERED_NEXT = datetime(2026, 10, 22, 8, 0, tzinfo=ET)


def _amp_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Max-e")
    monkeypatch.setenv("EDITION_OWNER_EMAIL", FAKE_OWNER)
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)
    monkeypatch.delenv("MORNING_BRIEF_STATE_PATH", raising=False)


@pytest.fixture()
def amp(tmp_path, monkeypatch):
    _amp_env(monkeypatch, tmp_path)
    yield tmp_path


def _freeze_et(monkeypatch, when: datetime):
    frozen = when if when.tzinfo else when.replace(tzinfo=ET)

    def _frozen_now(now=None):
        if now is None:
            return frozen
        if now.tzinfo is None:
            return now.replace(tzinfo=ET)
        return now.astimezone(ET)

    monkeypatch.setattr(sched, "morning_brief_now", _frozen_now)


def _capture_email(monkeypatch):
    sent: list[dict] = []

    def _fake(brief, now=None):
        sent.append({"brief": brief, "now": now, "to": FAKE_OWNER, "cc": None})
        return {"sent": True, "skipped": False, "to": FAKE_OWNER, "cc": None}

    monkeypatch.setattr(sched, "_refuse_live_brief_send", lambda: None)
    monkeypatch.setattr(sched, "email_daily_brief", _fake)
    return sent


def test_next_run_is_always_forward_in_et():
    now = datetime(2026, 10, 21, 22, 40, tzinfo=ET)
    nxt = sched.next_morning_brief_run(now)
    assert nxt == RECOVERED_NEXT
    assert nxt.tzinfo == ET
    assert nxt > now


def test_utc_now_does_not_shift_the_et_slot():
    # 10:40 PM ET Oct 21 == 02:40 UTC Oct 22. Next brief is still Oct 22 8:00 AM ET.
    now_utc = datetime(2026, 10, 22, 2, 40, tzinfo=timezone.utc)
    nxt = sched.next_morning_brief_run(now_utc)
    assert nxt == RECOVERED_NEXT
    assert nxt.utcoffset() == timedelta(hours=-4)


def test_naive_datetime_is_treated_as_et_not_utc():
    naive = datetime(2026, 10, 21, 22, 40, 0)
    nxt = sched.next_morning_brief_run(naive)
    assert nxt == RECOVERED_NEXT


def test_past_next_run_recovers_without_catch_up(amp, caplog):
    sched.save_morning_brief_state({
        "last_sent_date": "2026-10-18",
        "next_run": STALE_NEXT_RUN,
    })
    with caplog.at_level(logging.WARNING, logger="max.scheduler"):
        nxt = sched.recover_morning_brief_schedule(BUG_NOW)
    assert nxt == RECOVERED_NEXT
    assert nxt > BUG_NOW
    assert "in the past" in caplog.text
    assert "no catch-up" in caplog.text
    assert sched.should_send_morning_brief(BUG_NOW, "2026-10-18") is False
    saved = sched.load_morning_brief_state()
    assert saved["next_run"] == RECOVERED_NEXT.isoformat()
    assert saved["last_sent_date"] == "2026-10-18"
    assert saved["timezone"] == "America/New_York"


def test_past_next_run_start_does_not_send_catch_up(amp, monkeypatch):
    sched.save_morning_brief_state({
        "last_sent_date": "2026-10-18",
        "next_run": STALE_NEXT_RUN,
    })
    _freeze_et(monkeypatch, BUG_NOW)
    sent = _capture_email(monkeypatch)
    fired = []

    scheduler = sched.MaxScheduler()
    real_send = scheduler.send_daily_brief

    async def _wrapped():
        fired.append("send_daily_brief")
        return await real_send()

    monkeypatch.setattr(scheduler, "send_daily_brief", _wrapped)

    async def _run():
        await scheduler.start()
        try:
            job = scheduler.scheduler.get_job("daily_brief")
            assert job is not None
            assert job.next_run_time is not None
            got = job.next_run_time.astimezone(ET)
            assert got == RECOVERED_NEXT
            await asyncio.sleep(0.05)
        finally:
            scheduler.scheduler.shutdown(wait=False)

    asyncio.run(_run())
    assert fired == []
    assert sent == []
    saved = sched.load_morning_brief_state()
    assert saved["next_run"] == RECOVERED_NEXT.isoformat()
    assert saved["last_sent_date"] == "2026-10-18"


def test_restart_twice_in_a_day_does_not_double_send(amp, monkeypatch):
    eight_am = datetime(2026, 10, 21, 8, 0, 0, tzinfo=ET)
    ten_am = datetime(2026, 10, 21, 10, 0, 0, tzinfo=ET)
    sent = _capture_email(monkeypatch)
    monkeypatch.setattr("app.routers.notifications.notify_founder", lambda *a, **k: {"id": "n"})

    _freeze_et(monkeypatch, eight_am)
    asyncio.run(sched.MaxScheduler().send_daily_brief())
    assert len(sent) == 1
    assert sent[0]["to"] == FAKE_OWNER
    assert sched.load_morning_brief_state()["last_sent_date"] == "2026-10-21"

    _freeze_et(monkeypatch, ten_am)
    asyncio.run(sched.MaxScheduler().send_daily_brief())
    assert len(sent) == 1

    async def _start_once():
        s = sched.MaxScheduler()
        await s.start()
        try:
            job = s.scheduler.get_job("daily_brief")
            got = job.next_run_time.astimezone(ET)
            assert got == datetime(2026, 10, 22, 8, 0, tzinfo=ET)
            await asyncio.sleep(0.05)
        finally:
            s.scheduler.shutdown(wait=False)

    asyncio.run(_start_once())
    asyncio.run(_start_once())
    assert len(sent) == 1
    saved = sched.load_morning_brief_state()
    assert saved["last_sent_date"] == "2026-10-21"
    assert saved["next_run"] == datetime(2026, 10, 22, 8, 0, tzinfo=ET).isoformat()


def test_missed_morning_slot_is_not_caught_up(amp, monkeypatch):
    _freeze_et(monkeypatch, BUG_NOW)
    sent = _capture_email(monkeypatch)
    monkeypatch.setattr("app.routers.notifications.notify_founder", lambda *a, **k: {"id": "n"})
    asyncio.run(sched.MaxScheduler().send_daily_brief())
    assert sent == []
    assert sched.load_morning_brief_state().get("last_sent_date") != "2026-10-21"


def test_dst_spring_forward_lands_on_8am_edt():
    # 2026-03-08 02:00 EST → 03:00 EDT. 8:00 AM still exists (EDT, UTC-4).
    before = datetime(2026, 3, 7, 22, 40, tzinfo=ET)
    nxt = sched.next_morning_brief_run(before)
    assert nxt == datetime(2026, 3, 8, 8, 0, tzinfo=ET)
    assert nxt.utcoffset() == timedelta(hours=-4)

    after_gap = datetime(2026, 3, 8, 3, 30, tzinfo=ET)
    nxt = sched.next_morning_brief_run(after_gap)
    assert nxt == datetime(2026, 3, 8, 8, 0, tzinfo=ET)
    assert nxt.utcoffset() == timedelta(hours=-4)


def test_dst_fall_back_lands_on_8am_est():
    # 2026-11-01 02:00 EDT → 01:00 EST. 8:00 AM still exists (EST, UTC-5).
    before = datetime(2026, 10, 31, 22, 40, tzinfo=ET)
    nxt = sched.next_morning_brief_run(before)
    assert nxt == datetime(2026, 11, 1, 8, 0, tzinfo=ET)
    assert nxt.utcoffset() == timedelta(hours=-5)

    after = datetime(2026, 11, 1, 3, 30, tzinfo=ET)
    nxt = sched.next_morning_brief_run(after)
    assert nxt == datetime(2026, 11, 1, 8, 0, tzinfo=ET)
    assert nxt.utcoffset() == timedelta(hours=-5)


def test_recover_after_dst_fall_back_ignores_stale_edt_next_run(amp):
    now = datetime(2026, 11, 1, 22, 40, tzinfo=ET)
    state = {
        "last_sent_date": "2026-10-31",
        "next_run": "2026-11-01T08:00:00-04:00",  # stale EDT offset after the fall-back
    }
    nxt = sched.recover_morning_brief_schedule(now, state)
    assert nxt == datetime(2026, 11, 2, 8, 0, tzinfo=ET)
    assert nxt.utcoffset() == timedelta(hours=-5)
    assert nxt > now


def test_cron_trigger_uses_america_new_york(amp, monkeypatch):
    scheduler = sched.MaxScheduler()

    async def _noop():
        return None

    monkeypatch.setattr(scheduler, "send_daily_brief", _noop)

    async def _run():
        await scheduler.start()
        try:
            job = scheduler.scheduler.get_job("daily_brief")
            tz = getattr(job.trigger, "timezone", None)
            name = getattr(tz, "key", None) or str(tz)
            assert "America/New_York" in name
            assert job.misfire_grace_time == 1
        finally:
            scheduler.scheduler.shutdown(wait=False)

    asyncio.run(_run())
