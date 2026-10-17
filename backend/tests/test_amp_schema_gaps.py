"""3a — family edition tasks.source migration + crypto expiry skip.

Tmp DBs only. No live data, no real contacts, no outbound sends.
"""
from __future__ import annotations

import asyncio
import logging
import sqlite3
from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


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
    completed_at TEXT
);
"""


def _amp_tmp(monkeypatch, tmp_path):
    monkeypatch.setenv("EMPIRE_EDITION", "amp")
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))
    monkeypatch.delenv("FOUNDER_EMAIL", raising=False)


def _workroom_tmp(monkeypatch, tmp_path):
    monkeypatch.delenv("EMPIRE_EDITION", raising=False)
    monkeypatch.setenv("EMPIRE_DATA_DIR", str(tmp_path))
    monkeypatch.setenv("EMPIRE_TASK_DB", str(tmp_path / "empire.db"))


def _task_columns(db_path: str) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        return {row[1] for row in conn.execute("PRAGMA table_info(tasks)")}
    finally:
        conn.close()


def test_migrate_task_columns_adds_source_and_is_idempotent(monkeypatch, tmp_path):
    _amp_tmp(monkeypatch, tmp_path)
    db_path = tmp_path / "empire.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(OLD_TASKS_SCHEMA)
    conn.commit()
    conn.close()
    assert "source" not in _task_columns(str(db_path))

    from app.db.init_db import init_database

    init_database()
    cols = _task_columns(str(db_path))
    assert "source" in cols
    assert "follow_up_date" in cols
    assert "recurrence" in cols

    init_database()
    cols2 = _task_columns(str(db_path))
    assert cols2 == cols


def test_desk_manager_sync_inserts_into_migrated_db(monkeypatch, tmp_path):
    _amp_tmp(monkeypatch, tmp_path)
    db_path = tmp_path / "empire.db"
    conn = sqlite3.connect(db_path)
    conn.executescript(OLD_TASKS_SCHEMA)
    conn.commit()
    conn.close()

    from app.db.init_db import init_database
    from app.services.max.desks.base_desk import DeskTask, TaskPriority, TaskState
    from app.services.max.desks.desk_manager import AIDeskManager

    init_database()
    mgr = AIDeskManager()
    task = DeskTask(
        id="t-fake-1",
        title="Revisar factura de prueba",
        description="tarea falsa para el test",
        priority=TaskPriority.NORMAL,
        source="test",
    )
    task.state = TaskState.COMPLETED
    task.completed_at = datetime(2026, 10, 16, 12, 0, 0).isoformat()
    mgr._sync_task_to_db(task, "finance")

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM tasks WHERE id = ?", ("t-fake-1",)).fetchone()
    conn.close()
    assert row is not None
    assert row["title"] == "Revisar factura de prueba"
    assert row["source"] == "test"
    assert row["desk"] == "finance"
    assert row["status"] == "done"


def test_family_scheduler_omits_crypto_expiry_job(monkeypatch, tmp_path):
    _amp_tmp(monkeypatch, tmp_path)
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


def test_workroom_scheduler_still_registers_crypto_expiry(monkeypatch, tmp_path):
    _workroom_tmp(monkeypatch, tmp_path)
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


def test_expire_crypto_payments_missing_table_is_quiet(monkeypatch, tmp_path, caplog):
    _amp_tmp(monkeypatch, tmp_path)
    box = tmp_path / "empirebox.db"
    sqlite3.connect(box).close()
    engine = create_engine(f"sqlite:///{box}")
    Session = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    monkeypatch.setattr("app.database.SessionLocal", Session)

    from app.services.max.scheduler import MaxScheduler

    scheduler = MaxScheduler()
    with caplog.at_level(logging.INFO, logger="max.scheduler"):
        asyncio.run(scheduler.expire_crypto_payments())
        asyncio.run(scheduler.expire_crypto_payments())

    assert not any(r.levelno >= logging.ERROR for r in caplog.records)
    infos = [r.message for r in caplog.records if "crypto_payments table absent" in r.message]
    assert len(infos) == 1


def test_overdue_check_runs_on_tmp_db(monkeypatch, tmp_path):
    _amp_tmp(monkeypatch, tmp_path)
    from app.db.init_db import init_database
    from app.services.max.monitor import MaxMonitor
    from app.services.max.scheduler import MaxScheduler

    init_database()
    conn = sqlite3.connect(tmp_path / "empire.db")
    conn.execute(
        """INSERT INTO tasks (id, title, description, status, priority, desk, due_date, source)
           VALUES (?, ?, ?, 'todo', 'normal', 'finance', '2020-01-01', 'test')""",
        ("t-overdue-1", "Pagar factura de prueba", "tarea vencida falsa"),
    )
    conn.commit()
    conn.close()

    monitor = MaxMonitor()
    text = asyncio.run(monitor._check_overdue_tasks())
    assert text is not None
    assert "Pagar factura de prueba" in text

    monkeypatch.setattr(
        "app.routers.notifications.notify_founder",
        lambda *a, **k: None,
    )
    scheduler = MaxScheduler()
    asyncio.run(scheduler.check_overdue_tasks())
