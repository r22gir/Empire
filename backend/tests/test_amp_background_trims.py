"""2a — family editions skip Workroom desk jobs. tmp EMPIRE_DATA_DIR only."""
from __future__ import annotations

import asyncio
import socket
from datetime import datetime
from types import SimpleNamespace

from app.services.family_background import mark_unchanged, skip_if_unchanged
from app.services.instance_usage import record_usage
from app.services.max.desks.desk_scheduler import (
    DeskScheduler,
    active_desk_schedule,
    desk_task_key,
)


def _family_env(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_DEFAULT_LOCALE", "es")
    monkeypatch.setenv("ASSISTANT_NAME", "Max-e")
    monkeypatch.setenv("INSTANCE_USAGE_CAP_PCT", "20")
    monkeypatch.setenv("EMPIRE_USAGE_BASELINE_MONTHLY_TOKENS", "1000")
    monkeypatch.delenv("FAMILY_DESK_SCHEDULE", raising=False)
    monkeypatch.delenv("EMPIRE_BACKEND_PORT", raising=False)
    monkeypatch.delenv("EMPIRE_FRONTEND_EXPECTED_PORT", raising=False)
    monkeypatch.delenv("EMPIRE_USAGE_BASELINE_MONTHLY_USD", raising=False)
    monkeypatch.setattr("app.services.instance_usage._usage_data_roots", lambda: [tmp_path])


async def _flush(tasks):
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)


def test_family_empty_schedule_never_executes_desk_task(monkeypatch, tmp_path):
    _family_env(monkeypatch, tmp_path)
    assert active_desk_schedule() == []
    sched = DeskScheduler()
    calls = []

    async def fake_exec(*args, **kwargs):
        calls.append((args, kwargs))

    monkeypatch.setattr(sched, "_execute_desk_task", fake_exec)

    async def run():
        for clock in (
            datetime(2026, 10, 16, 8, 0, 0),
            datetime(2026, 10, 16, 8, 30, 0),
            datetime(2026, 10, 16, 10, 0, 0),
        ):
            await _flush(await sched._tick(clock))

    asyncio.run(run())
    assert calls == []
    from app.services.instance_usage import usage_db_path
    path = usage_db_path()
    if path and path.is_file():
        import sqlite3
        conn = sqlite3.connect(path)
        n = conn.execute("SELECT COUNT(*) FROM llm_usage").fetchone()[0]
        conn.close()
        assert n == 0


def test_family_desk_schedule_opt_in_only_named_task(monkeypatch, tmp_path):
    _family_env(monkeypatch, tmp_path)
    monkeypatch.setenv("FAMILY_DESK_SCHEDULE", "finance:Morning Invoice Audit,not-a-real:Task")
    keys = [desk_task_key(row[2], row[3]) for row in active_desk_schedule()]
    assert keys == ["finance:Morning Invoice Audit"]

    sched = DeskScheduler()
    calls = []

    async def fake_exec(desk_id, title, description, source="scheduler"):
        calls.append((desk_id, title, source))

    monkeypatch.setattr(sched, "_execute_desk_task", fake_exec)

    async def run():
        await _flush(await sched._tick(datetime(2026, 10, 16, 8, 0, 0)))
        await _flush(await sched._tick(datetime(2026, 10, 16, 8, 30, 0)))

    asyncio.run(run())
    assert calls == [("finance", "Morning Invoice Audit", "scheduler")]


def test_workroom_8am_still_schedules_finance(monkeypatch, tmp_path):
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.setenv("EMPIRE_EDITION", "")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    # empty edition + non-family data dir basename
    sched = DeskScheduler()
    calls = []

    async def fake_exec(desk_id, title, description, source="scheduler"):
        calls.append((desk_id, title))

    async def noop(*_a, **_k):
        return None

    monkeypatch.setattr(sched, "_execute_desk_task", fake_exec)
    monkeypatch.setattr(sched, "_check_service_health", noop)
    monkeypatch.setattr(sched, "_run_pipeline_executor", noop)

    async def run():
        await _flush(await sched._tick(datetime(2026, 10, 16, 8, 0, 0)))

    asyncio.run(run())
    assert ("finance", "Morning Invoice Audit") in calls


def test_family_health_tick_skips_workroom_ports(monkeypatch, tmp_path):
    _family_env(monkeypatch, tmp_path)
    probed = []

    def fake_connect(address, timeout=None):
        probed.append(address)
        raise ConnectionRefusedError()

    monkeypatch.setattr(socket, "create_connection", fake_connect)
    sched = DeskScheduler()

    async def run():
        await _flush(await sched._tick(datetime(2026, 10, 16, 8, 0, 0)))

    asyncio.run(run())
    workroom = {8000, 3000, 3001, 3002, 3005, 3009, 7878, 11434}
    assert not any(addr[1] in workroom for addr in probed)


def test_skip_unchanged_hash_skips_second_identical_context(monkeypatch, tmp_path):
    _family_env(monkeypatch, tmp_path)
    assert skip_if_unchanged("desk-finance-audit", "same-context") is False
    assert skip_if_unchanged("desk-finance-audit", "same-context") is False
    assert not (tmp_path / "run" / "desk-finance-audit.hash").is_file()
    mark_unchanged("desk-finance-audit", "same-context")
    assert skip_if_unchanged("desk-finance-audit", "same-context") is True
    assert skip_if_unchanged("desk-finance-audit", "changed") is False
    stored = tmp_path / "run" / "desk-finance-audit.hash"
    assert stored.is_file()


def test_skip_unchanged_includes_date_and_retries_failed_run(monkeypatch, tmp_path):
    _family_env(monkeypatch, tmp_path)
    assert skip_if_unchanged("desk-finance-audit", "invoices", day="2026-10-16") is False
    mark_unchanged("desk-finance-audit", "invoices", day="2026-10-16")
    assert skip_if_unchanged("desk-finance-audit", "invoices", day="2026-10-16") is True
    assert skip_if_unchanged("desk-finance-audit", "invoices", day="2026-10-17") is False


def test_family_desk_task_never_uses_overage(monkeypatch, tmp_path):
    _family_env(monkeypatch, tmp_path)
    record_usage(input_tokens=250, output_tokens=0)
    from app.services.family_background import family_background_cap_message
    from app.services.instance_usage import MENSAJE_PAUSED_SIGNAL, family_overage_allowed

    assert family_overage_allowed() is False
    assert family_background_cap_message(kind="desk_task", source="scheduler") == MENSAJE_PAUSED_SIGNAL


def test_opted_in_task_skips_model_when_unchanged(monkeypatch, tmp_path):
    _family_env(monkeypatch, tmp_path)
    monkeypatch.setenv("FAMILY_DESK_SCHEDULE", "finance:Morning Invoice Audit")
    sched = DeskScheduler()
    submits = []

    class FakeTask:
        id = "task-1"
        title = "Morning Invoice Audit"
        description = "Check all outstanding invoices."
        result = "x" * 600
        state = SimpleNamespace(value="completed")
        priority = SimpleNamespace(value="normal")
        completed_at = None

    class FakeManager:
        def initialize(self):
            return None

        async def submit_task(self, **kwargs):
            submits.append(kwargs)
            return FakeTask()

        def get_desk(self, desk_id):
            return None

    sched._manager = FakeManager()

    async def noop(*_a, **_k):
        return None

    monkeypatch.setattr(sched, "_persist_task", noop)
    monkeypatch.setattr(sched, "_notify_telegram", noop)
    monkeypatch.setattr(sched, "_notify_telegram_error", noop)

    async def run():
        await sched._execute_desk_task(
            "finance",
            "Morning Invoice Audit",
            "Check all outstanding invoices.",
            source="scheduler",
        )
        await sched._execute_desk_task(
            "finance",
            "Morning Invoice Audit",
            "Check all outstanding invoices.",
            source="scheduler",
        )

    asyncio.run(run())
    assert len(submits) == 1


def test_failed_desk_run_does_not_save_hash(monkeypatch, tmp_path):
    _family_env(monkeypatch, tmp_path)
    monkeypatch.setenv("FAMILY_DESK_SCHEDULE", "finance:Morning Invoice Audit")
    sched = DeskScheduler()
    submits = []

    class FailedTask:
        id = "task-fail"
        title = "Morning Invoice Audit"
        description = "Check all outstanding invoices."
        result = ""
        state = SimpleNamespace(value="failed")
        priority = SimpleNamespace(value="normal")
        completed_at = None

    class FakeManager:
        def initialize(self):
            return None

        async def submit_task(self, **kwargs):
            submits.append(kwargs)
            return FailedTask()

        def get_desk(self, desk_id):
            return None

    sched._manager = FakeManager()

    async def noop(*_a, **_k):
        return None

    monkeypatch.setattr(sched, "_persist_task", noop)
    monkeypatch.setattr(sched, "_notify_telegram", noop)
    monkeypatch.setattr(sched, "_notify_telegram_error", noop)

    async def run():
        await sched._execute_desk_task(
            "finance",
            "Morning Invoice Audit",
            "Check all outstanding invoices.",
            source="scheduler",
        )
        await sched._execute_desk_task(
            "finance",
            "Morning Invoice Audit",
            "Check all outstanding invoices.",
            source="scheduler",
        )

    asyncio.run(run())
    assert len(submits) == 2
    run_dir = tmp_path / "run"
    assert not run_dir.exists() or not list(run_dir.glob("*.hash"))
