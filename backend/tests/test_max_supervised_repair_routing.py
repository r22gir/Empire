import asyncio
import importlib
from datetime import datetime, timedelta, timezone

from fastapi import BackgroundTasks, Response


def _preflight_payload():
    return {
        "lane": "v10-test",
        "branch": "feature/v10.0-test-lane",
        "commit": "fa70b4a",
        "backend_port": 8010,
        "frontend_port": 3010,
        "git_freshness_status": "ok",
        "hermes_artifact_layer_enabled": True,
        "safe_to_create_bounded_openclaw_task": True,
        "note": "no task created yet",
        "endpoint_checks": {
            "max_status": {"ok": True, "status_code": 200},
            "git_status": {"ok": True, "status_code": 200},
            "hermes_artifacts_status": {"ok": True, "status_code": 200},
        },
    }


def _future_iso(minutes: int = 30) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


def _past_iso(minutes: int = 30) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def _recommendation_record(task_ref: str = "sv10r_demo_token", *, consumed: bool = False, expires_at: str | None = None):
    return {
        "task_ref": task_ref,
        "created_at": _past_iso(1),
        "expires_at": expires_at or _future_iso(60),
        "consumed": consumed,
        "consumed_at": _past_iso(1) if consumed else None,
        "lane": "v10-test",
        "branch": "feature/v10.0-test-lane",
        "commit": "fa70b4a",
        "task_title": "Supervised v10 repair: enforce recommendation-to-create confirmation token",
        "task_scope": (
            "Add a task_ref handshake so supervised recommendation output produces a single bounded token, "
            "and the create route requires that exact token before queueing OpenClaw work."
        ),
        "allowed_paths": [
            "/home/rg/empire-repo-v10/backend/app/routers/max/router.py",
            "/home/rg/empire-repo-v10/backend/tests/test_max_supervised_repair_routing.py",
        ],
        "forbidden_paths": [
            "/home/rg/empire-repo-main",
            "/home/rg/empire-repo-feature",
            "/home/rg/empire-repo",
        ],
        "required_tests": [
            "pytest backend/tests/test_max_supervised_repair_routing.py -q",
            "pytest backend/tests/test_max_truth_guardrails.py -q",
            "pytest backend/tests/test_runtime_git_lane_mapping.py -q",
        ],
        "final_report_required": True,
        "commit_required": True,
        "stable_main_untouched_required": True,
        "promotion_forbidden": True,
        "hermes_artifact_ids": ["ha_v10_1", "ha_v10_2"],
        "hermes_context": [
            {"id": "ha_v10_1", "title": "Runtime lane fix"},
            {"id": "ha_v10_2", "title": "Attestation review"},
        ],
        "safety_gate_snapshot": {
            "lane": "v10-test",
            "branch": "feature/v10.0-test-lane",
            "safe_to_create_bounded_openclaw_task": True,
            "git_freshness_status": "ok",
            "hermes_artifact_layer_enabled": True,
        },
        "task_payload": {
            "title": "Supervised v10 repair: enforce recommendation-to-create confirmation token",
            "scope": (
                "Add a task_ref handshake so supervised recommendation output produces a single bounded token, "
                "and the create route requires that exact token before queueing OpenClaw work."
            ),
            "lane": "v10-test",
            "worktree": "/home/rg/empire-repo-v10",
            "branch": "feature/v10.0-test-lane",
            "bounded_task": True,
            "v10_only": True,
            "allowed_paths": [
                "/home/rg/empire-repo-v10/backend/app/routers/max/router.py",
                "/home/rg/empire-repo-v10/backend/tests/test_max_supervised_repair_routing.py",
            ],
            "forbidden_paths": [
                "/home/rg/empire-repo-main",
                "/home/rg/empire-repo-feature",
                "/home/rg/empire-repo",
            ],
            "required_tests": [
                "pytest backend/tests/test_max_supervised_repair_routing.py -q",
                "pytest backend/tests/test_max_truth_guardrails.py -q",
                "pytest backend/tests/test_runtime_git_lane_mapping.py -q",
            ],
            "final_report_required": True,
            "commit_required": True,
            "stable_main_untouched_required": True,
            "promotion_forbidden": True,
            "founder_approval_source": "supervised-v10-openclaw-task-create",
            "likely_files_affected": [
                "backend/app/routers/max/router.py",
                "backend/tests/test_max_supervised_repair_routing.py",
            ],
        },
    }


def _approval_prompt(task_ref: str) -> str:
    return f"Approved task_ref={task_ref}. Create exactly one bounded OpenClaw task."


def _level1_prompt() -> str:
    return (
        "MAX, start Level 1 supervised v10 delegation. "
        "First verify v10 lane, git freshness, Hermes enabled, inspect queue if supported, "
        "confirm task_id=8 is cancelled, then recommend exactly 3 bounded v10 tasks. "
        "Do not create any tasks."
    )


def _openclaw_task_row(
    task_id: int = 8,
    status: str = "queued",
    *,
    lane: str = "v10-test",
    branch: str = "feature/v10.0-test-lane",
    worktree: str = "/home/rg/empire-repo-v10",
) -> dict:
    return {
        "id": task_id,
        "title": "Supervised v10 repair: enforce recommendation-to-create confirmation token",
        "description": (
            "Add a task_ref handshake so supervised recommendation output produces a single bounded token, "
            "and the create route requires that exact token before queueing OpenClaw work.\n\n"
            "Task payload:\n"
            "{\n"
            f'  "lane": "{lane}",\n'
            f'  "branch": "{branch}",\n'
            f'  "worktree": "{worktree}",\n'
            '  "scope": "Add a task_ref handshake so supervised recommendation output produces a single bounded token, and the create route requires that exact token before queueing OpenClaw work.",\n'
            '  "required_tests": ["pytest backend/tests/test_max_supervised_repair_routing.py -q"]\n'
            "}"
        ),
        "status": status,
        "source": "supervised-v10-openclaw-task-create",
        "commit_hash": None,
        "created_at": "2026-05-16 03:23:52",
    }


def _legacy_duplicate_task_row(task_id: int = 1, status: str = "queued", source: str = "max") -> dict:
    return {
        "id": task_id,
        "title": "Supervised v10 repair: enforce recommendation-to-create confirmation token",
        "description": (
            "Implement tokenized handoff from supervised recommendation route to task-creation route.\n"
            "- Add task_ref emission in recommendation output.\n"
            "- Require matching task_ref in create route.\n"
            "- Keep v10 lane-only scope and update routing tests.\n\n"
            "## Hermes Support Packet\n"
            "**Task:** Supervised v10 repair: enforce recommendation-to-create confirmation token\n"
        ),
        "status": status,
        "desk": "codedesk",
        "source": source,
        "commit_hash": None,
        "created_at": "2026-05-16 02:19:56",
    }


def _unknown_lane_arbitrary_task_row(task_id: int = 77, status: str = "queued") -> dict:
    return {
        "id": task_id,
        "title": "Unrelated OpenClaw cleanup task",
        "description": "Investigate an unrelated queue item with no v10 lane metadata.",
        "status": status,
        "desk": "codedesk",
        "source": "max",
        "commit_hash": None,
        "created_at": "2026-05-16 02:19:56",
    }


class _FakeCursor:
    def __init__(self, row, rowcount: int = 0):
        self._row = row
        self.rowcount = rowcount

    def fetchone(self):
        return self._row


class _ReadOnlyDB:
    def __init__(self, row):
        self._row = row
        self.queries: list[str] = []

    def execute(self, query, params=()):
        self.queries.append(str(query))
        assert str(query).lstrip().upper().startswith("SELECT")
        return _FakeCursor(self._row, rowcount=1 if self._row else 0)


class _MutableDB:
    def __init__(self, row):
        self._row = row
        self.queries: list[str] = []
        self.update_count = 0

    def execute(self, query, params=()):
        sql = str(query)
        normalized = sql.strip().lower()
        self.queries.append(sql)
        if normalized.startswith("select"):
            task_id = params[0] if params else None
            row = self._row if (self._row and int(self._row.get("id")) == int(task_id)) else None
            return _FakeCursor(row, rowcount=1 if row else 0)
        if "update openclaw_tasks" in normalized and "set status = 'cancelled'" in normalized:
            task_id = params[1] if len(params) > 1 else None
            if self._row and int(self._row.get("id")) == int(task_id) and str(self._row.get("status")).lower() in {"queued", "paused"}:
                self._row["status"] = "cancelled"
                self._row["error"] = params[0] if params else None
                self._row["completed_at"] = "2026-05-16 00:00:00"
                self.update_count += 1
                return _FakeCursor(None, rowcount=1)
            return _FakeCursor(None, rowcount=0)
        raise AssertionError(f"unexpected SQL in mutable test DB: {sql}")


class _ReadOnlyDBCtx:
    def __init__(self, db):
        self.db = db

    def __enter__(self):
        return self.db

    def __exit__(self, exc_type, exc, tb):
        return False


def test_level1_delegation_routes_before_disposition_and_stays_read_only(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(
        max_router,
        "_collect_supervised_v10_openclaw_queue_snapshot",
        lambda limit=10: {
            "supported": True,
            "count": 1,
            "tasks": [{"id": 8, "status": "cancelled", "title": "already handled"}],
            "note": "queue listing supported",
        },
    )
    monkeypatch.setattr(
        max_router,
        "_collect_supervised_v10_openclaw_task_status",
        lambda task_id: {
            "supported": True,
            "task_id": task_id,
            "found": True,
            "title": "Supervised v10 repair: enforce recommendation-to-create confirmation token",
            "status": "cancelled",
            "lane": "v10-test",
            "branch": "feature/v10.0-test-lane",
            "worktree": "/home/rg/empire-repo-v10",
            "source": "supervised-v10-openclaw-task-create",
            "created_at": "2026-05-16 03:23:52",
        },
    )
    monkeypatch.setattr(
        max_router,
        "_collect_supervised_v10_approved_hermes_context",
        lambda founder, limit=4: {
            "query": "q",
            "artifacts": [
                {"id": "ha1", "title": "artifact 1", "module": "system", "lane": "v10-test", "approval_status": "approved"},
                {"id": "ha2", "title": "artifact 2", "module": "system", "lane": "v10-test", "approval_status": "approved"},
            ],
            "tool_results": [],
        },
    )
    monkeypatch.setattr(
        max_router,
        "_build_supervised_v10_level1_recommended_tasks",
        lambda: [
            {"title": "Task A", "scope": "A", "why_safe": "safe", "likely_files_affected": ["a"], "tests_required": ["t1"], "founder_approval_required_before_creation": True, "task_ref_required_for_creation": True},
            {"title": "Task B", "scope": "B", "why_safe": "safe", "likely_files_affected": ["b"], "tests_required": ["t2"], "founder_approval_required_before_creation": True, "task_ref_required_for_creation": True},
            {"title": "Task C", "scope": "C", "why_safe": "safe", "likely_files_affected": ["c"], "tests_required": ["t3"], "founder_approval_required_before_creation": True, "task_ref_required_for_creation": True},
        ],
    )
    monkeypatch.setattr(
        max_router,
        "_supervised_v10_openclaw_task_disposition_response",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("level1 sprint should not route to disposition")),
    )
    monkeypatch.setattr(
        max_router,
        "_enqueue_supervised_v10_openclaw_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("level1 sprint must not queue tasks")),
    )

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message=_level1_prompt(), history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "supervised-v10-level1-delegation-sprint"
    result = (response.tool_results[-1] or {}).get("result") or {}
    assert result.get("created_tasks") == 0
    assert result.get("mutated_tasks") == 0
    assert result.get("no_task_creation_performed") is True
    assert result.get("no_task_mutation_performed") is True
    assert len(result.get("recommended_tasks") or []) == 3
    assert "- task_ref_batch_support: not_supported" in response.response


def test_supervised_preflight_routes_correctly():
    max_router = importlib.import_module("app.routers.max.router")

    request = max_router.ChatRequest(
        message="Run v10 supervised repair PREFLIGHT ONLY.",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))
    assert response.model_used == "supervised-v10-repair-preflight"


def test_openclaw_task_inspect_routes_before_module_knowledge(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    db_module = importlib.import_module("app.db.database")
    fake_db = _ReadOnlyDB(_openclaw_task_row(task_id=8, status="queued"))

    monkeypatch.setattr(db_module, "get_db", lambda: _ReadOnlyDBCtx(fake_db))
    monkeypatch.setattr(db_module, "dict_row", lambda row: row)
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(max_router, "_is_reference_commit_reachable", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        max_router.ai_router,
        "chat",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("should not hit ai_router for inspect route")),
    )

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(
                message="MAX, inspect OpenClaw task_id=8. Do not create a new task.",
                history=[],
                channel="web",
            ),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "supervised-v10-openclaw-task-inspect"
    assert "- task_id: 8" in response.response
    assert "- duplicate_assessment: duplicate_validation_task" in response.response
    assert "- recommendation: cancel" in response.response
    assert len(fake_db.queries) == 1


def test_openclaw_task_inspect_is_read_only_and_does_not_queue(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    db_module = importlib.import_module("app.db.database")
    fake_db = _ReadOnlyDB(_openclaw_task_row(task_id=8, status="queued"))

    monkeypatch.setattr(db_module, "get_db", lambda: _ReadOnlyDBCtx(fake_db))
    monkeypatch.setattr(db_module, "dict_row", lambda row: row)
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(max_router, "_is_reference_commit_reachable", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        max_router,
        "_enqueue_supervised_v10_openclaw_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("inspect route must not queue tasks")),
    )

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(
                message="check OpenClaw task id 8 and report task title/status/lane; do not create a new task",
                history=[],
                channel="web",
            ),
            BackgroundTasks(),
            Response(),
        )
    )
    result = (response.tool_results[0] or {}).get("result") or {}
    assert response.model_used == "supervised-v10-openclaw-task-inspect"
    assert result.get("created_task") is False
    assert result.get("no_mutation_performed") is True
    assert result.get("task_title") == "Supervised v10 repair: enforce recommendation-to-create confirmation token"


def test_openclaw_task_inspect_missing_task_id_returns_missing_gate(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(
                message="inspect OpenClaw task. do not create a new task.",
                history=[],
                channel="web",
            ),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "supervised-v10-openclaw-task-inspect"
    assert "- failed_gate: missing_task_id" in response.response


def test_openclaw_task_inspect_unknown_task_returns_not_found(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    db_module = importlib.import_module("app.db.database")
    fake_db = _ReadOnlyDB(None)

    monkeypatch.setattr(db_module, "get_db", lambda: _ReadOnlyDBCtx(fake_db))
    monkeypatch.setattr(db_module, "dict_row", lambda row: row)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(
                message="inspect OpenClaw task_id=999999. do not create a new task.",
                history=[],
                channel="web",
            ),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "supervised-v10-openclaw-task-inspect"
    assert "- failed_gate: task_not_found" in response.response


def test_disposition_without_approval_does_not_mutate(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    db_module = importlib.import_module("app.db.database")
    fake_db = _MutableDB(_openclaw_task_row(task_id=8, status="queued"))

    monkeypatch.setattr(db_module, "get_db", lambda: _ReadOnlyDBCtx(fake_db))
    monkeypatch.setattr(db_module, "dict_row", lambda row: row)
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(max_router, "_is_reference_commit_reachable", lambda *_args, **_kwargs: True)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(
                message="Cancel OpenClaw task_id=8 as duplicate validation task.",
                history=[],
                channel="web",
            ),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "supervised-v10-openclaw-task-disposition"
    assert "- failed_gate: founder_approval" in response.response
    assert "- mutated: False" in response.response
    assert fake_db.update_count == 0
    assert fake_db._row["status"] == "queued"


def test_disposition_with_approval_cancels_queued_duplicate(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    db_module = importlib.import_module("app.db.database")
    fake_db = _MutableDB(_openclaw_task_row(task_id=8, status="queued"))

    monkeypatch.setattr(db_module, "get_db", lambda: _ReadOnlyDBCtx(fake_db))
    monkeypatch.setattr(db_module, "dict_row", lambda row: row)
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(max_router, "_is_reference_commit_reachable", lambda *_args, **_kwargs: True)
    monkeypatch.setattr(
        max_router,
        "_enqueue_supervised_v10_openclaw_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("disposition route must not create tasks")),
    )

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(
                message="Approved. Cancel OpenClaw task_id=8 as duplicate validation task.",
                history=[],
                channel="web",
            ),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "supervised-v10-openclaw-task-disposition"
    assert "- mutated: True" in response.response
    assert "- new_status: cancelled" in response.response
    result = (response.tool_results[0] or {}).get("result") or {}
    assert result.get("created_task") is False
    assert fake_db.update_count == 1
    assert fake_db._row["status"] == "cancelled"


def test_disposition_unknown_task_returns_not_found(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    db_module = importlib.import_module("app.db.database")
    fake_db = _MutableDB(None)

    monkeypatch.setattr(db_module, "get_db", lambda: _ReadOnlyDBCtx(fake_db))
    monkeypatch.setattr(db_module, "dict_row", lambda row: row)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(
                message="Approved. Cancel OpenClaw task_id=999999 as duplicate validation task.",
                history=[],
                channel="web",
            ),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "supervised-v10-openclaw-task-disposition"
    assert "- failed_gate: task_not_found" in response.response


def test_disposition_running_task_is_not_mutated(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    db_module = importlib.import_module("app.db.database")
    fake_db = _MutableDB(_openclaw_task_row(task_id=8, status="running"))

    monkeypatch.setattr(db_module, "get_db", lambda: _ReadOnlyDBCtx(fake_db))
    monkeypatch.setattr(db_module, "dict_row", lambda row: row)
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(max_router, "_is_reference_commit_reachable", lambda *_args, **_kwargs: True)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(
                message="Approved. Cancel OpenClaw task_id=8 as duplicate validation task.",
                history=[],
                channel="web",
            ),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "supervised-v10-openclaw-task-disposition"
    assert "- failed_gate: status_not_mutable" in response.response
    assert fake_db.update_count == 0
    assert fake_db._row["status"] == "running"


def test_disposition_rejects_non_v10_task(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    db_module = importlib.import_module("app.db.database")
    fake_db = _MutableDB(
        _openclaw_task_row(
            task_id=8,
            status="queued",
            lane="main-stable",
            branch="main",
            worktree="/home/rg/empire-repo-main",
        )
    )

    monkeypatch.setattr(db_module, "get_db", lambda: _ReadOnlyDBCtx(fake_db))
    monkeypatch.setattr(db_module, "dict_row", lambda row: row)
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(
                message="Founder approves cancelling OpenClaw task_id=8.",
                history=[],
                channel="web",
            ),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "supervised-v10-openclaw-task-disposition"
    assert "- failed_gate: lane" in response.response
    assert fake_db.update_count == 0


def test_unknown_lane_arbitrary_task_cannot_be_cancelled(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    db_module = importlib.import_module("app.db.database")
    fake_db = _MutableDB(_unknown_lane_arbitrary_task_row(task_id=77, status="queued"))

    monkeypatch.setattr(db_module, "get_db", lambda: _ReadOnlyDBCtx(fake_db))
    monkeypatch.setattr(db_module, "dict_row", lambda row: row)
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(max_router, "_is_reference_commit_reachable", lambda *_args, **_kwargs: True)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(
                message="Approved. Cancel OpenClaw task_id=77 as duplicate validation task.",
                history=[],
                channel="web",
            ),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "supervised-v10-openclaw-task-disposition"
    assert "- failed_gate: lane" in response.response
    assert "- lane_source: unknown" in response.response
    assert fake_db.update_count == 0
    assert fake_db._row["status"] == "queued"


def test_legacy_unknown_lane_duplicate_can_be_cancelled_with_approval(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    db_module = importlib.import_module("app.db.database")
    fake_db = _MutableDB(_legacy_duplicate_task_row(task_id=1, status="queued"))

    monkeypatch.setattr(db_module, "get_db", lambda: _ReadOnlyDBCtx(fake_db))
    monkeypatch.setattr(db_module, "dict_row", lambda row: row)
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(max_router, "_is_reference_commit_reachable", lambda *_args, **_kwargs: True)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(
                message="Approved. Cancel OpenClaw task_id=1 as duplicate validation task.",
                history=[],
                channel="web",
            ),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "supervised-v10-openclaw-task-disposition"
    assert "- mutated: True" in response.response
    assert "- lane_source: inferred_legacy" in response.response
    assert "- legacy_metadata_missing: True" in response.response
    result = (response.tool_results[0] or {}).get("result") or {}
    assert result.get("lane_source") == "inferred_legacy"
    assert fake_db.update_count == 1
    assert fake_db._row["status"] == "cancelled"


def test_legacy_unknown_lane_duplicate_without_approval_is_blocked(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    db_module = importlib.import_module("app.db.database")
    fake_db = _MutableDB(_legacy_duplicate_task_row(task_id=1, status="queued"))

    monkeypatch.setattr(db_module, "get_db", lambda: _ReadOnlyDBCtx(fake_db))
    monkeypatch.setattr(db_module, "dict_row", lambda row: row)
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(max_router, "_is_reference_commit_reachable", lambda *_args, **_kwargs: True)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(
                message="Cancel OpenClaw task_id=1 as duplicate validation task.",
                history=[],
                channel="web",
            ),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "supervised-v10-openclaw-task-disposition"
    assert "- failed_gate: founder_approval" in response.response
    assert fake_db.update_count == 0
    assert fake_db._row["status"] == "queued"


def test_legacy_unknown_lane_running_duplicate_is_not_cancelled(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    db_module = importlib.import_module("app.db.database")
    fake_db = _MutableDB(_legacy_duplicate_task_row(task_id=1, status="running"))

    monkeypatch.setattr(db_module, "get_db", lambda: _ReadOnlyDBCtx(fake_db))
    monkeypatch.setattr(db_module, "dict_row", lambda row: row)
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(max_router, "_is_reference_commit_reachable", lambda *_args, **_kwargs: True)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(
                message="Approved. Cancel OpenClaw task_id=1 as duplicate validation task.",
                history=[],
                channel="web",
            ),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "supervised-v10-openclaw-task-disposition"
    assert "- failed_gate: status_not_mutable" in response.response
    assert "- lane_source: inferred_legacy" in response.response
    assert fake_db.update_count == 0
    assert fake_db._row["status"] == "running"


def test_recommendation_emits_task_ref_and_stores_pending_recommendation(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    stored_calls: list[dict] = []

    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)

    def fake_execute_tool(tool_call, founder=False):
        tool = tool_call.get("tool")
        if tool == "hermes_artifact_search":
            return max_router.ToolResult(
                tool=tool,
                success=True,
                result={
                    "results": [
                        {"id": "ha_v10_1", "title": "Runtime lane fix", "module": "system", "approval_status": "approved"},
                        {"id": "ha_v10_2", "title": "Attestation review", "module": "system", "approval_status": "approved"},
                    ]
                },
            )
        if tool == "hermes_artifact_get":
            artifact_id = tool_call.get("artifact_id")
            return max_router.ToolResult(
                tool=tool,
                success=True,
                result={
                    "metadata": {
                        "id": artifact_id,
                        "module": "system",
                        "lane": "v10-test",
                        "approval_status": "approved",
                    },
                    "summary": f"summary {artifact_id}",
                    "is_current": True,
                },
            )
        raise AssertionError(f"Unexpected tool call: {tool_call}")

    def fake_store(*, preflight, task_payload, artifacts_used):
        stored_calls.append(
            {"preflight": preflight, "task_payload": dict(task_payload), "artifacts_used": list(artifacts_used)}
        )
        return {
            "task_ref": "sv10r_demo123",
            "task_ref_created_at": _past_iso(1),
            "task_ref_expires_at": _future_iso(30),
            "recommendation_hash": "abc123",
            "safety_gate_snapshot": {"safe_to_create_bounded_openclaw_task": True},
            "hermes_artifact_ids": ["ha_v10_1", "ha_v10_2"],
            "hermes_context": [{"id": "ha_v10_1"}, {"id": "ha_v10_2"}],
        }

    monkeypatch.setattr(max_router, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(max_router, "_store_supervised_pending_recommendation", fake_store)
    monkeypatch.setattr(
        max_router,
        "_enqueue_supervised_v10_openclaw_task",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("recommendation route must not queue tasks")),
    )

    request = max_router.ChatRequest(
        message=(
            "MAX, continue supervised v10 self-repair mode. "
            "Search Hermes for approved/current v10 repair context. "
            "Recommend exactly one bounded OpenClaw repair task. Do not create the task yet."
        ),
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))

    assert response.model_used == "supervised-v10-repair-recommend-task"
    assert "- task_ref: sv10r_demo123" in response.response
    assert "Approved task_ref=sv10r_demo123. Create exactly one bounded OpenClaw task." in response.response
    assert len(stored_calls) == 1
    assert len(stored_calls[0]["artifacts_used"]) >= 1
    assert not any((tr.get("result") or {}).get("task_id") for tr in (response.tool_results or []))


def test_create_rejects_missing_task_ref(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)

    request = max_router.ChatRequest(
        message="Continue supervised v10 self-repair mode. Create exactly one bounded OpenClaw task for the recommended task.",
        history=[],
        channel="web",
    )
    response = asyncio.run(max_router.chat_with_max(request, BackgroundTasks(), Response()))
    assert response.model_used == "supervised-v10-openclaw-task-create"
    assert "- queued: False" in response.response
    assert "- failed_gate: founder_approval" in response.response


def test_create_rejects_wrong_task_ref(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(max_router, "_load_supervised_pending_recommendation", lambda _ref: None)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message=_approval_prompt("sv10r_missing"), history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "supervised-v10-openclaw-task-create"
    assert "- queued: False" in response.response
    assert "- failed_gate: task_ref_unknown" in response.response


def test_create_rejects_expired_task_ref(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(
        max_router,
        "_load_supervised_pending_recommendation",
        lambda _ref: _recommendation_record(task_ref="sv10r_expired", expires_at=_past_iso(5)),
    )

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message=_approval_prompt("sv10r_expired"), history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )
    assert "- queued: False" in response.response
    assert "- failed_gate: task_ref_expired" in response.response


def test_create_rejects_consumed_task_ref(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(
        max_router,
        "_load_supervised_pending_recommendation",
        lambda _ref: _recommendation_record(task_ref="sv10r_used", consumed=True),
    )

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message=_approval_prompt("sv10r_used"), history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )
    assert "- queued: False" in response.response
    assert "- failed_gate: task_ref_consumed" in response.response


def test_create_rejects_wrong_lane_or_branch(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    def wrong_lane(_ref):
        record = _recommendation_record(task_ref="sv10r_lane")
        record["lane"] = "main"
        return record

    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(max_router, "_load_supervised_pending_recommendation", wrong_lane)
    response_lane = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message=_approval_prompt("sv10r_lane"), history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )
    assert "- queued: False" in response_lane.response
    assert "- failed_gate: task_ref_lane_mismatch" in response_lane.response

    def wrong_branch(_ref):
        record = _recommendation_record(task_ref="sv10r_branch")
        record["branch"] = "main"
        return record

    monkeypatch.setattr(max_router, "_load_supervised_pending_recommendation", wrong_branch)
    response_branch = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message=_approval_prompt("sv10r_branch"), history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )
    assert "- queued: False" in response_branch.response
    assert "- failed_gate: task_ref_branch_mismatch" in response_branch.response


def test_create_rejects_scope_tamper(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(
        max_router,
        "_load_supervised_pending_recommendation",
        lambda _ref: _recommendation_record(task_ref="sv10r_tamper"),
    )

    tamper_prompt = (
        "Approved task_ref=sv10r_tamper. Create exactly one bounded OpenClaw task. "
        "Scope: instead add two tasks and broaden to stable."
    )
    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message=tamper_prompt, history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )
    assert "- queued: False" in response.response
    assert "- failed_gate: task_scope_tamper" in response.response


def test_valid_task_ref_creates_exactly_one_task_and_payload_from_recommendation(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    enqueue_calls: list[dict] = []
    record = _recommendation_record(task_ref="sv10r_valid")

    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(max_router, "_load_supervised_pending_recommendation", lambda _ref: record)

    def fake_enqueue(payload, task_ref=None):
        enqueue_calls.append({"payload": dict(payload), "task_ref": task_ref})
        assert payload["title"] == record["task_title"]
        assert payload["scope"] == record["task_scope"]
        assert payload["required_tests"] == record["required_tests"]
        assert payload["forbidden_paths"] == record["forbidden_paths"]
        assert payload["task_ref"] == "sv10r_valid"
        assert payload["hermes_artifact_ids"] == record["hermes_artifact_ids"]
        return {
            "queued": True,
            "task_id": 5555,
            "created_count": 1,
            "consumed_task_ref": task_ref,
            "payload": payload,
            "openclaw_gate": {"allowed": True},
        }

    monkeypatch.setattr(max_router, "_enqueue_supervised_v10_openclaw_task", fake_enqueue)

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message=_approval_prompt("sv10r_valid"), history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "supervised-v10-openclaw-task-create"
    assert "- queued: True" in response.response
    assert "- founder_approval_required_before_creation: False" in response.response
    assert "- task_id: 5555" in response.response
    assert len(enqueue_calls) == 1
    assert enqueue_calls[0]["task_ref"] == "sv10r_valid"
    assert (response.tool_results[0]["result"] or {}).get("created_count") == 1


def test_same_task_ref_cannot_create_second_task(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    enqueue_calls: list[dict] = []
    state = {"count": 0}

    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)

    def fake_load(_ref):
        state["count"] += 1
        if state["count"] == 1:
            return _recommendation_record(task_ref="sv10r_once", consumed=False)
        return _recommendation_record(task_ref="sv10r_once", consumed=True)

    def fake_enqueue(payload, task_ref=None):
        enqueue_calls.append({"payload": dict(payload), "task_ref": task_ref})
        return {
            "queued": True,
            "task_id": 7001,
            "created_count": 1,
            "consumed_task_ref": task_ref,
            "payload": payload,
            "openclaw_gate": {"allowed": True},
        }

    monkeypatch.setattr(max_router, "_load_supervised_pending_recommendation", fake_load)
    monkeypatch.setattr(max_router, "_enqueue_supervised_v10_openclaw_task", fake_enqueue)

    first = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message=_approval_prompt("sv10r_once"), history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )
    second = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message=_approval_prompt("sv10r_once"), history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )

    assert "- queued: True" in first.response
    assert "- queued: False" in second.response
    assert "- failed_gate: task_ref_consumed" in second.response
    assert len(enqueue_calls) == 1


def test_preflight_only_does_not_create_task(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")
    enqueue_calls: list[dict] = []

    monkeypatch.setattr(max_router, "_build_supervised_v10_repair_preflight_result", _preflight_payload)
    monkeypatch.setattr(
        max_router,
        "_enqueue_supervised_v10_openclaw_task",
        lambda payload, task_ref=None: enqueue_calls.append((payload, task_ref)) or {"queued": True, "task_id": 1},
    )

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message="Run v10 supervised repair PREFLIGHT ONLY.", history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "supervised-v10-repair-preflight"
    assert len(enqueue_calls) == 0


def test_openclaw_definition_question_still_routes_to_module_knowledge(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    async def fail_ai_router(*_args, **_kwargs):
        raise AssertionError("Module knowledge should handle this directly")

    monkeypatch.setattr(max_router.ai_router, "chat", fail_ai_router)
    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message="What is OpenClaw?", history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "empire-module-knowledge"


def test_runtime_truth_prompt_still_routes_to_runtime_truth_check(monkeypatch):
    max_router = importlib.import_module("app.routers.max.router")

    def fake_execute_tool(tool_call, founder=False):
        assert tool_call["tool"] == "empire_runtime_truth_check"
        return max_router.ToolResult(
            tool="empire_runtime_truth_check",
            success=True,
            result={"git_freshness": {"freshness_status": "ok"}},
        )

    monkeypatch.setattr(max_router, "execute_tool", fake_execute_tool)
    monkeypatch.setattr(max_router, "format_runtime_truth_check", lambda result, message: "runtime preflight ok")

    response = asyncio.run(
        max_router.chat_with_max(
            max_router.ChatRequest(message="what services are online?", history=[], channel="web"),
            BackgroundTasks(),
            Response(),
        )
    )
    assert response.model_used == "empire-runtime-truth-check"
    assert response.response == "runtime preflight ok"
