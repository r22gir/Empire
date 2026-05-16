import asyncio
import importlib
from datetime import datetime, timedelta, timezone

from fastapi import BackgroundTasks, Response


def _preflight_payload():
    return {
        "lane": "v10-test",
        "branch": "feature/v10.0-test-lane",
        "commit": "714bf6a",
        "backend_port": 8010,
        "frontend_port": 3010,
        "git_freshness_status": "ok",
        "hermes_artifact_layer_enabled": True,
        "safe_to_create_bounded_openclaw_task": True,
        "note": "no task created yet",
        "endpoint_checks": {
            "max_status": {"ok": True},
            "git_status": {"ok": True},
            "hermes_artifacts_status": {"ok": True},
        },
    }


def _future_iso(minutes: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def _fake_recommendation(max_router):
    return {
        "preflight": _preflight_payload(),
        "search_query": "v10 repair",
        "artifacts_used": [
            {"id": "ha1", "title": "Artifact One", "module": "system", "lane": "v10-test", "approval_status": "approved"}
        ],
        "recommended_task": {
            "title": "Fake bounded v10 task",
            "scope": "Small v10-only fix.",
            "why_safe": "router/test only",
            "likely_files_affected": ["backend/app/routers/max/router.py"],
            "tests_required": ["pytest backend/tests/test_max_operations_capability_registry.py -q"],
            "founder_approval_required_before_creation": True,
            "task_ref": "sv10r_fake",
            "task_ref_created_at": _future_iso(-1),
            "task_ref_expires_at": _future_iso(30),
            "hermes_artifact_ids": ["ha1"],
        },
        "tool_results": [max_router.ToolResult(tool="hermes_artifact_search", success=True, result={"results": []}).to_dict()],
    }


def _task_row(task_id=8, status="queued"):
    return {
        "id": task_id,
        "title": "Supervised v10 repair: enforce recommendation-to-create confirmation token",
        "description": (
            "Task payload:\n"
            "{\n"
            '  "lane": "v10-test",\n'
            '  "branch": "feature/v10.0-test-lane",\n'
            '  "worktree": "/home/rg/empire-repo-v10",\n'
            '  "scope": "task_ref handshake",\n'
            '  "required_tests": ["pytest backend/tests/test_max_supervised_repair_routing.py -q"]\n'
            "}"
        ),
        "status": status,
        "source": "supervised-v10-openclaw-task-create",
        "created_at": "2026-05-16 03:23:52",
        "completed_at": None,
        "error": None,
        "desk": "codedesk",
        "priority": 5,
    }


def _legacy_task_row(task_id=1, status="queued"):
    return {
        "id": task_id,
        "title": "Supervised v10 repair: enforce recommendation-to-create confirmation token",
        "description": (
            "Implement tokenized handoff from supervised recommendation route to task-creation route.\n"
            "- Add task_ref emission in recommendation output.\n"
            "- Require matching task_ref in create route.\n"
            "- Keep v10 lane-only scope and update routing tests."
        ),
        "status": status,
        "source": "max",
        "created_at": "2026-05-16 02:19:56",
        "completed_at": None,
        "error": None,
        "desk": "codedesk",
        "priority": 5,
    }


class _FakeCursor:
    def __init__(self, row=None, rows=None, rowcount=0):
        self._row = row
        self._rows = rows if rows is not None else ([] if row is None else [row])
        self.rowcount = rowcount
        self.lastrowid = 9999

    def fetchone(self):
        return self._row

    def fetchall(self):
        return self._rows


class _FakeDB:
    def __init__(self, row=None, rows=None):
        self.row = row
        self.rows = rows if rows is not None else ([] if row is None else [row])
        self.update_count = 0
        self.insert_count = 0

    def execute(self, query, params=()):
        sql = str(query).lower()
        if sql.strip().startswith("select"):
            if "where id = ?" in sql:
                task_id = params[0] if params else None
                row = self.row if self.row and int(self.row.get("id")) == int(task_id) else None
                return _FakeCursor(row=row, rowcount=1 if row else 0)
            return _FakeCursor(rows=list(self.rows), rowcount=len(self.rows))
        if "update openclaw_tasks" in sql:
            if self.row and str(self.row.get("status")).lower() in {"queued", "paused"}:
                self.row["status"] = "cancelled"
                self.update_count += 1
                return _FakeCursor(rowcount=1)
            return _FakeCursor(rowcount=0)
        if "insert into openclaw_tasks" in sql:
            self.insert_count += 1
            return _FakeCursor(rowcount=1)
        raise AssertionError(f"unexpected SQL: {query}")


class _FakeDBCtx:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self.db

    def __exit__(self, exc_type, exc, tb):
        return False


def _patch_task_db(monkeypatch, row=None, rows=None):
    db_module = importlib.import_module("app.db.database")
    fake_db = _FakeDB(row=row, rows=rows)
    monkeypatch.setattr(db_module, "get_db", lambda: _FakeDBCtx(fake_db))
    monkeypatch.setattr(db_module, "dict_row", lambda value: value)
    monkeypatch.setattr(db_module, "dict_rows", lambda values: list(values))
    return fake_db


def _chat(max_router, message: str):
    return asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message=message, history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )


def _patch_common(monkeypatch, max_router):
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(max_router, "_is_reference_commit_reachable", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_recommendation", lambda founder: _fake_recommendation(max_router))


def test_capabilities_endpoint_and_status_shape():
    max_router = importlib.import_module("app.routers.max.router")
    payload = asyncio.run(max_router.max_capabilities())
    status = payload["operations_capability_registry"]
    assert status["enabled"] is True
    assert status["capability_count"] >= 9
    assert status["read_only_count"] > status["mutating_count"]
    assert any(item["capability_id"] == "openclaw_task_list" for item in payload["capabilities"])


def test_run_v10_preflight_routes_to_preflight(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    _patch_common(monkeypatch, max_router)
    response = _chat(max_router, "Run v10 preflight.")
    assert response.model_used == "supervised-v10-repair-preflight"


def test_level1_natural_language_routes_to_sprint(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    _patch_common(monkeypatch, max_router)
    _patch_task_db(monkeypatch, row=_task_row(status="cancelled"), rows=[_task_row(status="cancelled")])
    monkeypatch.setattr(
        max_router,
        "_collect_supervised_v10_approved_hermes_context",
        lambda founder, limit=4: {"query": "q", "artifacts": [], "tool_results": []},
    )
    response = _chat(max_router, "Start Level 1 supervised v10 delegation.")
    assert response.model_used == "supervised-v10-level1-delegation-sprint"
    result = response.tool_results[-1]["result"]
    assert result["created_tasks"] == 0
    assert result["mutated_tasks"] == 0


def test_recommendation_natural_language_routes(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    _patch_common(monkeypatch, max_router)
    assert _chat(max_router, "Find something small OpenClaw can fix next.").model_used == "supervised-v10-repair-recommend-task"
    assert _chat(max_router, "Recommend one bounded v10 repair.").model_used == "supervised-v10-repair-recommend-task"
    assert _chat(max_router, "Use Hermes approved context to recommend a task.").model_used == "supervised-v10-repair-recommend-task"


def test_task_inspect_natural_language_routes(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    _patch_common(monkeypatch, max_router)
    _patch_task_db(monkeypatch, row=_task_row(status="cancelled"))
    assert _chat(max_router, "Inspect task 8.").model_used == "supervised-v10-openclaw-task-inspect"
    response = _chat(max_router, "Check OpenClaw task_id=8 and tell me if it is duplicate.")
    assert response.model_used == "supervised-v10-openclaw-task-inspect"


def test_task_disposition_routes_and_blocks_without_approval(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    _patch_common(monkeypatch, max_router)
    fake_db = _patch_task_db(monkeypatch, row=_task_row(status="queued"))
    response = _chat(max_router, "Cancel task 8 as duplicate.")
    assert response.model_used == "supervised-v10-openclaw-task-disposition"
    assert "founder_approval" in response.response
    assert fake_db.update_count == 0


def test_approved_disposition_routes_to_disposition(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    _patch_common(monkeypatch, max_router)
    fake_db = _patch_task_db(monkeypatch, row=_task_row(status="queued"))
    response = _chat(max_router, "Approved. Cancel OpenClaw task_id=8 as duplicate.")
    assert response.model_used == "supervised-v10-openclaw-task-disposition"
    assert fake_db.update_count == 1


def test_task_creation_requires_task_ref_and_uses_create_route(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    _patch_common(monkeypatch, max_router)
    monkeypatch.setattr(max_router, "_load_supervised_pending_recommendation", lambda _ref: None)

    missing = _chat(max_router, "Create a task.")
    assert missing.model_used == "supervised-v10-openclaw-task-create"
    assert "task_ref" in missing.response

    unknown = _chat(max_router, "Approved task_ref=abc123. Create exactly one bounded OpenClaw task.")
    assert unknown.model_used == "supervised-v10-openclaw-task-create"
    assert "task_ref_unknown" in unknown.response


def test_module_explanation_still_routes_to_module_knowledge(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    async def fail_ai_router(*_args, **_kwargs):
        raise AssertionError("module knowledge should handle explanation prompts")
    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)
    assert _chat(max_router, "What is OpenClaw?").model_used == "empire-module-knowledge"
    assert _chat(max_router, "Explain Hermes.").model_used == "empire-module-knowledge"


def test_openclaw_queue_routes_to_read_only_list(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    _patch_common(monkeypatch, max_router)
    fake_db = _patch_task_db(monkeypatch, rows=[_legacy_task_row(task_id=1, status="queued"), _task_row(task_id=9, status="queued")])
    response = _chat(max_router, "Show the OpenClaw queue.")
    assert response.model_used == "supervised-v10-openclaw-task-list"
    assert "lane_source=inferred_legacy" in response.response
    assert "duplicate_hint=duplicate_validation_task" in response.response
    assert "disposition_allowed=True" in response.response
    result = response.tool_results[0]["result"]
    assert result["created_tasks"] == 0
    assert result["mutated_tasks"] == 0
    assert result["tasks"][0]["lane_source"] == "inferred_legacy"
    assert fake_db.insert_count == 0
    assert fake_db.update_count == 0


def test_unknown_operation_returns_safe_missing_capability_not_module_knowledge(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    async def fail_ai_router(*_args, **_kwargs):
        raise AssertionError("unknown operation should not fall through to model")
    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)
    response = _chat(max_router, "Pause all OpenClaw jobs.")
    assert response.model_used == "max-operations-capability-missing"
    assert "openclaw_task_pause_all" in response.response


def test_runtime_truth_still_wins(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    def fake_execute_tool(tool_call, founder=False):
        assert tool_call["tool"] == "empire_runtime_truth_check"
        return max_router.ToolResult(tool="empire_runtime_truth_check", success=True, result={"git_freshness": {"freshness_status": "ok"}})
    monkeypatch.setattr(max_router, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(max_router, "format_runtime_truth_check", lambda result, message: "runtime truth ok")
    response = _chat(max_router, "what services are online?")
    assert response.model_used == "empire-runtime-truth-check"
    assert response.response == "runtime truth ok"


def test_hermes_artifact_memory_still_works(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    def fake_execute_tool(tool_call, founder=False):
        tool = tool_call["tool"]
        if tool == "hermes_artifact_search":
            return max_router.ToolResult(tool=tool, success=True, result={"results": [{"id": "ha1", "title": "Decision", "approval_status": "approved", "module": "system"}]})
        if tool == "hermes_artifact_get":
            return max_router.ToolResult(
                tool=tool,
                success=True,
                result={
                    "metadata": {"id": "ha1", "approval_status": "approved", "module": "system", "source_agent": "max"},
                    "summary": "Approved decision summary.",
                    "is_current": True,
                },
            )
        raise AssertionError(tool_call)
    monkeypatch.setattr(max_router, "execute_tool", fake_execute_tool)
    response = _chat(max_router, "Search Hermes approved context.")
    assert response.model_used == "hermes-artifact-memory"
    assert "Artifact memory used" in response.response
