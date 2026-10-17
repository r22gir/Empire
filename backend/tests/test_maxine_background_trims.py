"""Family desk scheduler: no Workroom jobs, no Workroom health probes."""
from __future__ import annotations

import asyncio
import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from app.services.max.desks.desk_scheduler import (
    DeskScheduler,
    active_daily_schedule,
    family_health_ports,
)
from app.services.max.scheduler import MaxScheduler


@pytest.fixture(autouse=True)
def _no_outbound(monkeypatch):
    def _boom(*args, **kwargs):
        raise AssertionError("no outbound email/WhatsApp/SMS in desk trim tests")

    monkeypatch.setattr("app.services.max.email_service.EmailService.send", _boom)
    for target in (
        "app.services.max.telegram_bot.telegram_bot.send_message",
        "app.services.whatsapp_cloud.send_text",
    ):
        try:
            monkeypatch.setattr(target, _boom)
        except Exception:
            pass


def _maxine_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "1000")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    monkeypatch.delenv("FAMILY_DESK_SCHEDULE", raising=False)
    monkeypatch.delenv("EMPIRE_BACKEND_PORT", raising=False)
    monkeypatch.delenv("EMPIRE_FRONTEND_EXPECTED_PORT", raising=False)
    monkeypatch.setattr("app.services.instance_usage._usage_data_roots", lambda: [tmp_path])


def _workroom_env(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("EMPIRE_EDITION", "workroom")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path / "workroom-data"))
    monkeypatch.delenv("FAMILY_DESK_SCHEDULE", raising=False)


def _usage_rows(tmp_path: Path) -> int:
    db = tmp_path / "usage" / "usage.db"
    if not db.is_file():
        return 0
    conn = sqlite3.connect(db)
    try:
        row = conn.execute("SELECT COUNT(*) FROM llm_usage").fetchone()
        return int(row[0]) if row else 0
    except sqlite3.Error:
        return 0
    finally:
        conn.close()


def test_family_empty_schedule_skips_workroom_ticks(monkeypatch, tmp_path):
    _maxine_env(monkeypatch, tmp_path)
    assert active_daily_schedule() == []
    scheduler = DeskScheduler()
    fired = []

    async def _record(desk_id, title, description, source="scheduler"):
        fired.append((desk_id, title, source))

    monkeypatch.setattr(scheduler, "_execute_desk_task", _record)

    async def _run():
        for hour, minute in ((8, 0), (8, 30), (10, 0)):
            await scheduler.tick(datetime(2026, 10, 16, hour, minute))

    asyncio.run(_run())
    assert fired == []
    assert _usage_rows(tmp_path) == 0


def test_family_opt_in_schedule_fires_only_that_task(monkeypatch, tmp_path):
    _maxine_env(monkeypatch, tmp_path)
    monkeypatch.setenv("FAMILY_DESK_SCHEDULE", "finance:Morning Invoice Audit,not-a-real-key")
    scheduler = DeskScheduler()
    fired = []

    class _Task:
        def __init__(self):
            self.id = "task-1"
            self.title = "Morning Invoice Audit"
            self.description = "audit"
            self.result = "ok" * 300
            self.state = type("S", (), {"value": "completed"})()
            self.priority = type("P", (), {"value": "normal"})()
            self.completed_at = None

    class _Manager:
        def initialize(self):
            return None

        async def submit_task(self, **kwargs):
            fired.append(kwargs)
            return _Task()

        def get_desk(self, desk_id):
            raise AssertionError("family opt-in must not call the model")

    scheduler._manager = _Manager()

    async def _run():
        await scheduler.tick(datetime(2026, 10, 16, 8, 0))
        await scheduler.tick(datetime(2026, 10, 16, 8, 30))
        await scheduler.tick(datetime(2026, 10, 16, 10, 0))

    asyncio.run(_run())
    assert len(fired) == 1
    assert fired[0]["title"] == "Morning Invoice Audit"
    assert fired[0]["source"] == "scheduler"


def test_workroom_eight_am_still_schedules_finance(monkeypatch, tmp_path):
    _workroom_env(monkeypatch, tmp_path)
    scheduler = DeskScheduler()
    fired = []

    async def _record(desk_id, title, description, source="scheduler"):
        fired.append((desk_id, title))

    monkeypatch.setattr(scheduler, "_execute_desk_task", _record)
    monkeypatch.setattr(scheduler, "_check_service_health", lambda: asyncio.sleep(0))
    monkeypatch.setattr(scheduler, "_run_pipeline_executor", lambda: asyncio.sleep(0))

    asyncio.run(scheduler.tick(datetime(2026, 10, 16, 8, 0)))
    assert ("finance", "Morning Invoice Audit") in fired


def test_family_health_tick_does_not_probe_workroom_ports(monkeypatch, tmp_path):
    _maxine_env(monkeypatch, tmp_path)
    probed = []

    def _fake_connect(address, timeout=None):
        probed.append(address)
        raise ConnectionRefusedError("blocked")

    monkeypatch.setattr("socket.create_connection", _fake_connect)
    scheduler = DeskScheduler()
    asyncio.run(scheduler.tick(datetime(2026, 10, 16, 8, 0)))
    asyncio.run(scheduler._check_service_health())
    workroom = {8000, 3000, 3001, 3002, 3005, 3009, 7878, 11434}
    assert all(addr[1] not in workroom for addr in probed)
    assert family_health_ports() == {}


def test_family_max_scheduler_still_registers_morning_brief(monkeypatch, tmp_path):
    _maxine_env(monkeypatch, tmp_path)
    scheduler = MaxScheduler()

    async def _noop():
        return None

    for name in (
        "send_daily_brief",
        "check_overdue_tasks",
        "run_sales_followup",
        "send_weekly_report",
        "brain_sync",
        "expire_crypto_payments",
        "nightly_drive_export",
    ):
        monkeypatch.setattr(scheduler, name, _noop)

    async def _run():
        await scheduler.start()
        try:
            ids = {job.id for job in scheduler.scheduler.get_jobs()}
            assert "daily_brief" in ids
        finally:
            scheduler.scheduler.shutdown(wait=False)

    asyncio.run(_run())


def test_skip_if_unchanged_stores_hash_under_run(monkeypatch, tmp_path):
    _maxine_env(monkeypatch, tmp_path)
    from app.services.family_job_skip import skip_if_unchanged

    assert skip_if_unchanged("desk:finance:Morning Invoice Audit", "ctx-a") is False
    assert skip_if_unchanged("desk:finance:Morning Invoice Audit", "ctx-a") is True
    assert skip_if_unchanged("desk:finance:Morning Invoice Audit", "ctx-b") is False
    hashes = list((tmp_path / "run").glob("*.hash"))
    assert len(hashes) == 1


def test_family_opt_in_refuses_overage(monkeypatch, tmp_path):
    _maxine_env(monkeypatch, tmp_path)
    monkeypatch.setenv("FAMILY_DESK_SCHEDULE", "finance:Morning Invoice Audit")
    from app.services.instance_usage import record_usage

    record_usage(input_tokens=250, output_tokens=0)
    scheduler = DeskScheduler()
    fired = []

    async def _record(desk_id, title, description, source="scheduler"):
        fired.append(title)

    # Patch after constructing so tick still uses the real execute path.
    original = scheduler._execute_desk_task

    async def _wrap(desk_id, title, description, source="scheduler"):
        fired.append("entered")
        return await original(desk_id, title, description, source)

    monkeypatch.setattr(scheduler, "_execute_desk_task", _wrap)

    class _Manager:
        def initialize(self):
            return None

        async def submit_task(self, **kwargs):
            fired.append("model")
            raise AssertionError("background must not run on overage")

    scheduler._manager = _Manager()
    asyncio.run(scheduler.tick(datetime(2026, 10, 16, 8, 0)))
    assert "model" not in fired
