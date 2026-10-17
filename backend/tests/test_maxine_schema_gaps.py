"""Maxine schema gaps: tasks.source migration, crypto expiry skip, overdue get_db.

Tmp DBs only. No live data, no real contacts, no outbound senders.
"""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def _block_outbound(monkeypatch):
    def _boom(*_a, **_k):
        raise RuntimeError("outbound send blocked in tests")

    monkeypatch.setattr(
        "app.services.max.email_service.EmailService.send",
        _boom,
        raising=False,
    )


OLD_TASKS_SCHEMA = """
CREATE TABLE tasks (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    description TEXT,
    status TEXT NOT NULL DEFAULT 'todo',
    priority TEXT NOT NULL DEFAULT 'normal',
    desk TEXT NOT NULL,
    business TEXT,
    assigned_to TEXT,
    created_by TEXT DEFAULT 'founder',
    due_date TEXT,
    tags TEXT,
    metadata TEXT,
    parent_task_id TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    completed_at TEXT,
    pipeline_id TEXT,
    subtask_order INTEGER DEFAULT 0,
    acceptance_criteria TEXT,
    channel TEXT DEFAULT 'system',
    result_summary TEXT,
    resume_state TEXT
);
"""


def _maxine_tmp(monkeypatch, tmp_path: Path) -> Path:
    db_path = tmp_path / "empire.db"
    monkeypatch.setenv("EMPIRE_EDITION", "maxine")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_TASK_DB", str(db_path))
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)
    return db_path


def _task_columns(db_path: Path) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    finally:
        conn.close()


def test_init_database_adds_source_idempotently(monkeypatch, tmp_path):
    db_path = _maxine_tmp(monkeypatch, tmp_path)
    conn = sqlite3.connect(db_path)
    conn.executescript(OLD_TASKS_SCHEMA)
    conn.commit()
    conn.close()
    assert "source" not in _task_columns(db_path)

    from app.db.init_db import init_database

    init_database()
    cols = _task_columns(db_path)
    assert "source" in cols
    assert "follow_up_date" in cols
    assert "recurrence" in cols

    init_database()
    assert "source" in _task_columns(db_path)


def test_desk_manager_sync_task_inserts_without_error(monkeypatch, tmp_path):
    db_path = _maxine_tmp(monkeypatch, tmp_path)
    conn = sqlite3.connect(db_path)
    conn.executescript(OLD_TASKS_SCHEMA)
    conn.commit()
    conn.close()

    from app.db.init_db import init_database
    from app.services.max.desks.base_desk import DeskTask, TaskPriority, TaskState
    from app.services.max.desks.desk_manager import AIDeskManager

    init_database()
    task = DeskTask(
        id="t-fake-sync-1",
        title="Revisar cotizacion de ejemplo",
        description="Tarea de prueba",
        priority=TaskPriority.NORMAL,
        state=TaskState.COMPLETED,
        source="max",
        result="ok",
        completed_at="2026-10-16T12:00:00",
    )
    AIDeskManager()._sync_task_to_db(task, desk_id="finance")

    conn = sqlite3.connect(db_path)
    try:
        row = conn.execute(
            "SELECT id, title, source, desk FROM tasks WHERE id = ?",
            ("t-fake-sync-1",),
        ).fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[0] == "t-fake-sync-1"
    assert row[2] == "max"
    assert row[3] == "finance"


def test_family_scheduler_omits_crypto_expiry_job(monkeypatch, tmp_path):
    _maxine_tmp(monkeypatch, tmp_path)
    from app.services.max.scheduler import MaxScheduler

    scheduler = MaxScheduler()

    async def _noop():
        return None

    for name in [
        "send_daily_brief",
        "check_overdue_tasks",
        "run_sales_followup",
        "send_weekly_report",
        "brain_sync",
        "expire_crypto_payments",
        "nightly_drive_export",
    ]:
        monkeypatch.setattr(scheduler, name, _noop)

    async def _run():
        await scheduler.start()
        try:
            ids = {job.id for job in scheduler.scheduler.get_jobs()}
            assert "expire_crypto_payments" not in ids
            assert "daily_brief" in ids
        finally:
            scheduler.scheduler.shutdown(wait=False)

    asyncio.run(_run())


def test_workroom_scheduler_keeps_crypto_expiry_job(monkeypatch, tmp_path):
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    from app.services.max.scheduler import MaxScheduler

    scheduler = MaxScheduler()

    async def _noop():
        return None

    for name in [
        "send_daily_brief",
        "check_overdue_tasks",
        "run_sales_followup",
        "send_weekly_report",
        "brain_sync",
        "expire_crypto_payments",
        "nightly_drive_export",
    ]:
        monkeypatch.setattr(scheduler, name, _noop)

    async def _run():
        await scheduler.start()
        try:
            ids = {job.id for job in scheduler.scheduler.get_jobs()}
            assert "expire_crypto_payments" in ids
        finally:
            scheduler.scheduler.shutdown(wait=False)

    asyncio.run(_run())


def test_expire_crypto_payments_missing_table_is_quiet(tmp_path, monkeypatch, caplog):
    db_path = tmp_path / "empirebox.db"
    sqlite3.connect(db_path).close()
    from sqlalchemy import create_engine

    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
    )
    monkeypatch.setattr("app.database.engine", engine)

    from app.services.max.scheduler import MaxScheduler

    MaxScheduler._crypto_table_absent_logged = False
    caplog.set_level(logging.INFO)
    asyncio.run(MaxScheduler().expire_crypto_payments())
    assert "crypto_payments table absent" in caplog.text
    assert not any(r.levelno >= logging.ERROR for r in caplog.records)


def test_overdue_check_runs_without_raising(monkeypatch, tmp_path):
    db_path = _maxine_tmp(monkeypatch, tmp_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'todo',
            priority TEXT NOT NULL DEFAULT 'normal',
            desk TEXT NOT NULL,
            due_date TEXT
        )
        """
    )
    conn.execute(
        "INSERT INTO tasks (id, title, status, priority, desk, due_date) "
        "VALUES (?, ?, 'todo', 'normal', 'finance', ?)",
        ("t-overdue-schema", "Pagar factura de ejemplo", "2020-01-01"),
    )
    conn.commit()
    conn.close()

    from app.services.max.monitor import MaxMonitor
    from app.services.max.scheduler import MaxScheduler

    monkeypatch.setattr(
        "app.routers.notifications.notify_founder",
        lambda *a, **k: {"id": "n-test"},
    )

    text = asyncio.run(MaxMonitor()._check_overdue_tasks())
    assert text is not None
    assert "Pagar factura de ejemplo" in text

    asyncio.run(MaxScheduler().check_overdue_tasks())
