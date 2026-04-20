import asyncio
import contextlib
import importlib
import sqlite3
from pathlib import Path

from fastapi import BackgroundTasks, Response

from app.services.max.ai_router import AIResponse
from app.services.max import tool_executor


max_router = importlib.import_module("app.routers.max.router")


def _temp_task_db(path: Path):
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        CREATE TABLE tasks (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            description TEXT,
            status TEXT,
            priority TEXT,
            desk TEXT,
            created_by TEXT,
            due_date TEXT,
            tags TEXT,
            metadata TEXT,
            created_at TEXT,
            updated_at TEXT
        );
        CREATE TABLE task_activity (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            task_id TEXT,
            actor TEXT,
            action TEXT,
            detail TEXT,
            created_at TEXT
        );
        CREATE TABLE openclaw_tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            desk TEXT,
            priority INTEGER,
            source TEXT,
            assigned_to TEXT,
            status TEXT DEFAULT 'queued',
            error TEXT,
            parent_task_id TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        INSERT INTO openclaw_tasks (id, title, description, desk, priority, source, assigned_to, parent_task_id)
        VALUES (44, 'Contrast issues', 'old unrelated task', 'Design', 5, 'old', 'openclaw', 'old-parent');
        """
    )
    conn.commit()
    conn.close()


def test_founder_task_request_fails_when_openclaw_returns_unrelated_task_id(monkeypatch, tmp_path):
    db_path = tmp_path / "empire.db"
    _temp_task_db(db_path)

    @contextlib.contextmanager
    def temp_get_db():
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    class FakeResponse:
        status_code = 200
        def json(self):
            return {"id": 44, "title": "Contrast issues"}

    monkeypatch.setattr(tool_executor, "get_db", temp_get_db)
    monkeypatch.setattr(
        "app.services.max.openclaw_gate.check_openclaw_gate",
        lambda: type("Gate", (), {"to_dict": lambda self: {"allowed": True, "state": "healthy"}})(),
    )
    monkeypatch.setattr("httpx.post", lambda *args, **kwargs: FakeResponse())

    result = tool_executor.execute_tool({
        "tool": "create_task",
        "title": "Review the current founder email workflow",
        "description": "Review the current founder email workflow",
        "desk": "operations",
    }, founder=True)

    assert result.success is False
    assert "identity verification failed" in result.error
    assert result.result["openclaw_task_id"] == 44
    assert result.result["actual_openclaw_task"]["title"] == "Contrast issues"


def test_decision_only_prompt_does_not_execute_task_tool(monkeypatch):
    async def fake_chat(*args, **kwargs):
        return AIResponse(
            content='```tool\n{"tool":"create_task","title":"Email workflow","description":"Review founder email workflow"}\n```',
            model_used="test-model",
        )

    def fail_execute_tool(*args, **kwargs):
        raise AssertionError("decision-only prompt must not execute tools")

    monkeypatch.setattr(max_router.ai_router, "chat", fake_chat)
    monkeypatch.setattr(max_router, "execute_tool", fail_execute_tool)

    request = max_router.ChatRequest(
        message="tell me whether this should be logged only or delegated",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "decision-boundary"
    assert "did not create, queue, or delegate" in response.response
