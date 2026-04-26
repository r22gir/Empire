import asyncio
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

from app.services import openclaw_worker
from app.services.max import openclaw_gate


def _init_openclaw_db(path: Path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute(
        """
        CREATE TABLE openclaw_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            desk TEXT DEFAULT 'general',
            priority INTEGER DEFAULT 5,
            source TEXT DEFAULT 'manual',
            assigned_to TEXT DEFAULT 'openclaw',
            status TEXT DEFAULT 'queued',
            result TEXT,
            error TEXT,
            files_modified TEXT,
            commit_hash TEXT,
            retry_count INTEGER DEFAULT 0,
            max_retries INTEGER DEFAULT 2,
            parent_task_id TEXT,
            started_at TEXT,
            completed_at TEXT,
            created_at TEXT DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()
    conn.close()


def _insert_task(path: Path, **overrides) -> dict:
    data = {
        "title": "Code task",
        "description": "Inspect backend/app/main.py. Do not edit files.",
        "desk": "codeforge",
        "priority": 5,
        "source": "test",
        "status": "queued",
        "started_at": None,
    }
    data.update(overrides)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        """INSERT INTO openclaw_tasks
           (title, description, desk, priority, source, status, started_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            data["title"],
            data["description"],
            data["desk"],
            data["priority"],
            data["source"],
            data["status"],
            data["started_at"],
        ),
    )
    conn.commit()
    row = conn.execute("SELECT * FROM openclaw_tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    conn.close()
    return dict(row)


def _get_task(path: Path, task_id: int) -> dict:
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    row = conn.execute("SELECT * FROM openclaw_tasks WHERE id = ?", (task_id,)).fetchone()
    conn.close()
    return dict(row)


def _patch_worker_basics(monkeypatch, db_path: Path):
    monkeypatch.setattr(openclaw_worker, "DB_PATH", str(db_path))
    monkeypatch.setattr(openclaw_worker, "_notify_telegram", lambda message: asyncio.sleep(0))
    monkeypatch.setattr(openclaw_worker, "_git_changed_files", lambda: set())
    monkeypatch.setattr(openclaw_worker, "_git_head", lambda: "b6b40f9")
    monkeypatch.setattr(openclaw_worker, "_is_drawing_task", lambda task: False)


def test_non_health_task_cannot_complete_with_generic_port_health(monkeypatch, tmp_path):
    db_path = tmp_path / "empire.db"
    _init_openclaw_db(db_path)
    task = _insert_task(
        db_path,
        title="Harden MAX drawing handoff truth",
        description="Fix the code path. Do not run a health check.",
        desk="codeforge",
    )
    _patch_worker_basics(monkeypatch, db_path)

    async def fake_execute(_task):
        return openclaw_worker.ExecutionResult(
            success=True,
            executor="openclaw_chat",
            result="8000: ONLINE\n3005: ONLINE\n7878: ONLINE\n11434: ONLINE\n3077: OFFLINE",
        )

    monkeypatch.setattr(openclaw_worker, "_execute_task", fake_execute)

    asyncio.run(openclaw_worker._process_task(task))

    row = _get_task(db_path, task["id"])
    assert row["status"] == "failed"
    assert "generic service health" in row["error"]
    assert row["completed_at"]


def test_explicit_health_task_may_complete_with_health_summary(monkeypatch, tmp_path):
    db_path = tmp_path / "empire.db"
    _init_openclaw_db(db_path)
    task = _insert_task(
        db_path,
        title="OpenClaw port health check",
        description="Check ports and service status.",
        desk="it",
    )
    _patch_worker_basics(monkeypatch, db_path)

    async def fake_execute(_task):
        return openclaw_worker.ExecutionResult(
            success=True,
            executor="openclaw_worker.local_health_check",
            result="8000: ONLINE\n3005: ONLINE\n7878: ONLINE\n11434: ONLINE\n3077: OFFLINE",
        )

    monkeypatch.setattr(openclaw_worker, "_execute_task", fake_execute)

    asyncio.run(openclaw_worker._process_task(task))

    row = _get_task(db_path, task["id"])
    assert row["status"] == "done"
    assert "Executor path used: openclaw_worker.local_health_check" in row["result"]
    assert "8000: ONLINE" in row["result"]


def test_executor_unavailable_marks_task_failed(monkeypatch, tmp_path):
    db_path = tmp_path / "empire.db"
    _init_openclaw_db(db_path)
    task = _insert_task(db_path, title="Code task", description="Change code safely.", desk="codeforge")
    _patch_worker_basics(monkeypatch, db_path)

    async def fake_execute(_task):
        return openclaw_worker.ExecutionResult(
            success=False,
            executor="code_task_runner",
            error="CodeTaskRunner unavailable: CodeForge desk not available",
        )

    monkeypatch.setattr(openclaw_worker, "_execute_task", fake_execute)

    asyncio.run(openclaw_worker._process_task(task))

    row = _get_task(db_path, task["id"])
    assert row["status"] == "failed"
    assert "CodeTaskRunner unavailable" in row["error"]
    assert row["completed_at"]


def test_orphaned_running_task_is_recovered(monkeypatch, tmp_path):
    db_path = tmp_path / "empire.db"
    _init_openclaw_db(db_path)
    old_started_at = (datetime.now() - timedelta(minutes=30)).isoformat()
    task = _insert_task(
        db_path,
        title="Old running task",
        description="Started before worker restart.",
        status="running",
        started_at=old_started_at,
    )
    monkeypatch.setattr(openclaw_worker, "DB_PATH", str(db_path))

    recovered = openclaw_worker._recover_orphaned_running_tasks()

    row = _get_task(db_path, task["id"])
    assert recovered == 1
    assert row["status"] == "failed"
    assert row["error"] == "Recovered orphaned running task after worker restart."


def test_worker_heartbeat_sets_current_task_id_while_processing(monkeypatch, tmp_path):
    db_path = tmp_path / "empire.db"
    _init_openclaw_db(db_path)
    task = _insert_task(db_path, title="Read code", description="Inspect backend/app/main.py.", desk="codeforge")
    _patch_worker_basics(monkeypatch, db_path)
    heartbeats = []

    def fake_heartbeat(**kwargs):
        heartbeats.append(kwargs)
        return kwargs

    async def fake_execute(_task):
        return openclaw_worker.ExecutionResult(
            success=True,
            executor="code_task_runner",
            result="Inspected backend/app/main.py",
            tools_run=["reading: backend/app/main.py"],
            files_inspected=["backend/app/main.py"],
        )

    monkeypatch.setattr(openclaw_worker, "write_openclaw_worker_heartbeat", fake_heartbeat)
    monkeypatch.setattr(openclaw_worker, "_execute_task", fake_execute)

    asyncio.run(openclaw_worker._process_task(task))

    assert any(call.get("current_task_id") == task["id"] for call in heartbeats)
    assert heartbeats[-1]["current_task_id"] is None


def test_code_task_description_is_passed_to_code_task_runner(monkeypatch):
    from app.services.max import code_task_runner as runner_module
    from app.services.max.code_task_runner import CodeTaskState

    captured = {}

    class FakeLog:
        action = "reading"
        detail = "file_read: backend/app/services/openclaw_worker.py"

    class FakeCodeTask:
        id = "ct-1"
        state = CodeTaskState.COMPLETED
        result = "Read the worker file."
        error = None
        files_changed = []
        log = [FakeLog()]

    def fake_submit(prompt):
        captured["prompt"] = prompt
        return FakeCodeTask()

    monkeypatch.setattr(runner_module.code_task_runner, "submit", fake_submit)

    task = {
        "id": 77,
        "title": "OpenClaw executor read-only repo inspection",
        "description": "Inspect backend/app/services/max/drawing_intent.py. Do not edit files. Do not commit.",
        "desk": "codeforge",
        "priority": 5,
        "source": "test",
    }

    result = asyncio.run(openclaw_worker._execute_code_task(task))

    assert result.success is True
    assert result.executor == "code_task_runner"
    assert task["title"] in captured["prompt"]
    assert task["description"] in captured["prompt"]
    assert "Do not commit" in captured["prompt"]


def test_gate_degraded_for_stale_running_task_without_active_worker(monkeypatch):
    openclaw_gate.clear_openclaw_gate_cache()

    class Resp:
        status_code = 200

    monkeypatch.setattr(openclaw_gate.httpx, "get", lambda *args, **kwargs: Resp())
    monkeypatch.setattr(
        openclaw_gate,
        "_queue_snapshot",
        lambda: (True, {"running": 1, "total": 1, "stale_running": 1, "stale_running_ids": [42]}, {"total": 1}),
    )
    monkeypatch.setattr(
        openclaw_gate,
        "read_openclaw_worker_heartbeat",
        lambda: {"state": "fresh", "fresh": True, "current_task_id": None},
    )

    result = openclaw_gate.check_openclaw_gate(force=True)

    assert result.state == "degraded"
    assert "stale running OpenClaw task" in result.reason
