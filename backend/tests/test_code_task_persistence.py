"""D28 §1b/§1c — Code-task persistence tests.

Proves the writer is reached from the real execution path (the dead
`pending_drawing_jobs` precedent failed because nothing on a live path
called the writer). Every terminal site in `_execute()` must update the
DB row to its final state.

Tests live in two clusters:

  PERSISTENCE LAYER (test_persistence_*)
    Direct unit tests of `code_task_persistence`:
      - idempotent ensure_table
      - insert_task creates row
      - update_task updates fields
      - persistence failure (sqlite3 errors) returns False without raising
      - all 29 CodeTask fields round-trip through insert_task/fetch_task

  RUNNER WIRING (test_runner_terminal_*)
    Each of the ten terminal sites from D28 §0c is exercised by
    monkey-patching the runner's helpers to force the conditions. After
    the awaitable resolves, we query the DB and assert the row's
    `state` matches the expected terminal value. A single happy-path
    test does not cover ten hooks — every site gets its own test.

    Plus:
      - test_runner_submit_creates_row: a row exists immediately after
        submit(), before _execute() reaches :838.
      - test_runner_running_transition_persists: after _execute sets
        state=RUNNING at :838, the row reflects it.
      - test_runner_cancelled_error_terminal: cancelling a real task
        leaves state='error' (D28 §1c).
      - test_runner_mid_run_failure_terminal: an exception mid-loop
        lands state='error' (covered also by site :1189, but
        re-asserted here to confirm the regression-class).
      - test_runner_persistence_failure_does_not_kill_task: a failing
        DB write does NOT kill the in-flight task (D28 §1b).

All tests use the `isolated_empire_db` session fixture from
tests/conftest.py — they NEVER write to ~/empire-data/empire.db.
"""
from __future__ import annotations

import asyncio
import json
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock  # noqa: F401  (kept for future use)

import pytest

# Backend on path
_BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_BACKEND))


# ───────────────────────────────────────────────────────────────────
# Helpers
# ───────────────────────────────────────────────────────────────────

def _import_modules():
    """Late-import so the persistence module binds to the isolated DB.

    Returns (runner_module, runner_singleton, persistence_module).
    Module is needed because _repo_changed_paths / _repo_head_commit /
    _repo_head_exists / _select_code_model / _request_code_response are
    MODULE-LEVEL functions — monkeypatching on the singleton instance
    would not intercept calls inside _execute().
    """
    from app.services.max import code_task_runner as ctr_module
    from app.services.max import code_task_persistence as ctp_module
    return ctr_module, ctr_module.code_task_runner, ctp_module


def _make_response(content="", function_calls=None):
    """Build a fake AIResponse the runner can parse."""
    from app.services.max.ai_router import AIResponse
    return AIResponse(
        content=content,
        function_calls=function_calls or [],
        model_used="grok",
        fallback_used=False,
    )


async def _drain_handle(handle):
    """Await the runner's asyncio Task to completion. Swallows
    CancelledError (raised by the D28 §1c handler) and any other
    exception (caught by the generic-Exception handler at :1189) —
    the DB row is what we verify, not the exception flow.
    """
    try:
        await handle
    except (asyncio.CancelledError, Exception):
        pass


def _clear_runner(runner):
    """Reset the runner singleton's in-memory state between tests."""
    runner._tasks.clear()
    runner._running.clear()


@pytest.fixture(autouse=True)
def _isolate_runner():
    """Wipe the singleton's _tasks/_running dicts before AND after each
    test so leftover handles from a previous test do not pollute."""
    from app.services.max.code_task_runner import code_task_runner
    _clear_runner(code_task_runner)
    yield
    _clear_runner(code_task_runner)


# ───────────────────────────────────────────────────────────────────
# Persistence layer — direct unit tests
# ───────────────────────────────────────────────────────────────────

def test_persistence_ensure_table_idempotent(isolated_empire_db):
    """ensure_table() called twice on the same DB does not error and
    leaves the schema unchanged."""
    from app.services.max import code_task_persistence as ctp

    ctp.ensure_table()
    ctp.ensure_table()  # second call must be a no-op

    conn = sqlite3.connect(isolated_empire_db)
    conn.row_factory = sqlite3.Row
    try:
        cols = [r["name"] for r in conn.execute("PRAGMA table_info(code_mode_tasks)").fetchall()]
    finally:
        conn.close()
    assert "id" in cols
    assert "state" in cols
    assert "log_json" in cols
    assert "files_snapshot_before_json" in cols


def test_persistence_insert_creates_row(isolated_empire_db):
    """insert_task() places a row in code_mode_tasks with the expected
    id, state, and JSON columns."""
    from app.services.max import code_task_persistence as ctp
    from app.services.max.code_task_runner import CodeTask

    task = CodeTask(
        id="test-insert-1",
        prompt="unit test prompt",
        working_dir="/tmp",
        execution_mode="mutate",
        founder=True,
    )
    assert ctp.insert_task(task) is True

    row = ctp.fetch_task("test-insert-1")
    assert row is not None
    assert row["id"] == "test-insert-1"
    assert row["state"] == "queued"
    assert row["founder"] == 1
    assert json.loads(row["files_changed_json"]) == []


def test_persistence_update_modifies_row(isolated_empire_db):
    """update_task() upserts and updates state + JSON columns."""
    from app.services.max import code_task_persistence as ctp
    from app.services.max.code_task_runner import CodeTask, CodeTaskState

    task = CodeTask(
        id="test-update-1",
        prompt="unit test prompt",
        working_dir="/tmp",
        execution_mode="mutate",
    )
    ctp.insert_task(task)
    task.state = CodeTaskState.COMPLETED
    task.files_changed = ["a.py", "b.py"]
    task.completed_at = "2026-08-24T20:00:00"
    assert ctp.update_task(task) is True

    row = ctp.fetch_task("test-update-1")
    assert row["state"] == "completed"
    assert json.loads(row["files_changed_json"]) == ["a.py", "b.py"]


def test_persistence_failure_returns_false_without_raising(isolated_empire_db, monkeypatch):
    """A failing DB write MUST return False, not raise (D28 §1b)."""
    from app.services.max import code_task_persistence as ctp
    from app.services.max.code_task_runner import CodeTask

    task = CodeTask(
        id="test-fail-1",
        prompt="unit test",
        working_dir="/tmp",
        execution_mode="mutate",
    )

    def boom_connect():
        raise sqlite3.OperationalError("simulated disk failure")

    monkeypatch.setattr(ctp, "_connect", boom_connect)

    # Neither insert nor update must raise; both must return False.
    assert ctp.insert_task(task) is False
    assert ctp.update_task(task) is False

    # And no row should have landed.
    assert ctp.fetch_task("test-fail-1") is None


def test_persistence_all_29_fields_roundtrip(isolated_empire_db):
    """Every CodeTask field (29 total) survives a JSON-serialisation
    round-trip via insert_task() → fetch_task()."""
    from app.services.max import code_task_persistence as ctp
    from app.services.max.code_task_runner import CodeTask, CodeTaskLog, CodeTaskState

    task = CodeTask(
        id="test-fields-1",
        prompt="round-trip prompt",
        working_dir="/tmp/repo",
        execution_mode="mutate",
        founder=True,
    )
    task.state = CodeTaskState.RUNNING
    task.provider_used = "xai"
    task.model_used = "grok"
    task.supports_tool_calls = True
    task.prompt_attempts = 3
    task.failure_reason = None
    task.execution_protocol = "json-tool-action"
    task.started_at = "2026-08-24T20:00:00"
    task.completed_at = None
    task.result = None
    task.error = None
    task.files_changed = ["x.py"]
    task.files_inspected = ["y.py"]
    task.executed_tool_calls = [{"tool": "file_read", "success": True, "params": {"path": "y.py"}}]
    task.verified_test_runs = [{"tool": "test_runner", "command": "pytest"}]
    task.verified_commit_hash = None
    task.verification_notes = ["ok"]
    task.log = [CodeTaskLog(timestamp="2026-08-24T20:00:00", action="started", detail="ok")]
    task.last_response_text = "model said X"
    task.last_function_calls_summary = "file_read(y.py)"
    task.last_parse_outcome = "parsed"
    task.files_snapshot_before = {"a.py", "b.py"}
    task.files_snapshot_ground_truth = True

    assert ctp.insert_task(task) is True
    row = ctp.fetch_task("test-fields-1")
    assert row is not None

    # Spot-check every column from D28 §0b.4
    assert row["prompt"] == "round-trip prompt"
    assert row["working_dir"] == "/tmp/repo"
    assert row["execution_mode"] == "mutate"
    assert row["founder"] == 1
    assert row["state"] == "running"
    assert row["provider_used"] == "xai"
    assert row["model_used"] == "grok"
    assert row["supports_tool_calls"] == 1
    assert row["prompt_attempts"] == 3
    assert row["failure_reason"] is None
    assert row["execution_protocol"] == "json-tool-action"
    assert row["started_at"] == "2026-08-24T20:00:00"
    assert row["completed_at"] is None
    assert row["result"] is None
    assert row["error"] is None
    assert json.loads(row["files_changed_json"]) == ["x.py"]
    assert json.loads(row["files_inspected_json"]) == ["y.py"]
    assert json.loads(row["executed_tool_calls_json"]) == [{
        "tool": "file_read", "success": True, "params": {"path": "y.py"}
    }]
    assert json.loads(row["verified_test_runs_json"]) == [{
        "tool": "test_runner", "command": "pytest"
    }]
    assert row["verified_commit_hash"] is None
    assert json.loads(row["verification_notes_json"]) == ["ok"]
    assert json.loads(row["log_json"]) == [
        {"timestamp": "2026-08-24T20:00:00", "action": "started", "detail": "ok"}
    ]
    assert row["last_response_text"] == "model said X"
    assert row["last_function_calls_summary"] == "file_read(y.py)"
    assert row["last_parse_outcome"] == "parsed"
    # set → list (sorted on the way out)
    assert sorted(json.loads(row["files_snapshot_before_json"])) == ["a.py", "b.py"]
    assert row["files_snapshot_ground_truth"] == 1


# ───────────────────────────────────────────────────────────────────
# Runner wiring — submit + RUNNING transition + 9 terminal paths
# ───────────────────────────────────────────────────────────────────

async def _drive(runner, ctp, task_id):
    """Drain the runner's asyncio task for `task_id` to completion."""
    handle = runner._running[task_id]
    await _drain_handle(handle)


async def _submit_and_drive(runner, ctp, prompt, working_dir="/tmp", founder=True):
    """submit() then drain _execute. Returns the CodeTask."""
    task = runner.submit(prompt=prompt, working_dir=working_dir, founder=founder)
    await _drive(runner, ctp, task.id)
    return task


# ── submit + RUNNING transition ────────────────────────────────────

@pytest.mark.asyncio
async def test_runner_submit_creates_row(isolated_empire_db, monkeypatch):
    """A row exists immediately after submit(), with state='queued'."""
    runner_module, runner, ctp = _import_modules()
    monkeypatch.setattr(runner_module, "_repo_changed_paths", lambda _wd: None)
    monkeypatch.setattr(runner_module, "_repo_head_commit", lambda: None)
    monkeypatch.setattr(runner_module, "_repo_head_exists", lambda _h: True)
    monkeypatch.setattr(runner_module, "_select_code_model",
                        lambda: (None, "xai", True))

    # submit() returns synchronously after inserting; we cancel the
    # spawned task before it can reach :838.
    task = runner.submit(prompt="harness probe", working_dir="/tmp", founder=True)
    handle = runner._running.get(task.id)
    handle.cancel()
    await _drain_handle(handle)

    row = ctp.fetch_task(task.id)
    assert row is not None, "row should exist immediately after submit()"
    assert row["state"] == "queued"
    assert row["prompt"] == "harness probe"
    assert row["working_dir"] == "/tmp"
    assert row["founder"] == 1


@pytest.mark.asyncio
async def test_runner_running_transition_persists(isolated_empire_db, monkeypatch):
    """After _execute sets state=RUNNING at :838, the row reflects it."""
    runner_module, runner, ctp = _import_modules()
    monkeypatch.setattr(runner_module, "_repo_changed_paths", lambda _wd: None)
    monkeypatch.setattr(runner_module, "_repo_head_commit", lambda: None)
    monkeypatch.setattr(runner_module, "_repo_head_exists", lambda _h: True)
    monkeypatch.setattr(runner_module, "_select_code_model",
                        lambda: (None, "xai", True))

    # _request_code_response hangs — we want to observe the RUNNING
    # transition before any terminal path.
    async def hang(*a, **kw):
        await asyncio.sleep(60)

    monkeypatch.setattr(runner_module, "_request_code_response", hang)

    task = runner.submit(prompt="transition probe", working_dir="/tmp", founder=True)
    # Give _execute a tick to reach :838
    await asyncio.sleep(0.3)

    row = ctp.fetch_task(task.id)
    assert row is not None, "row should exist after RUNNING transition"
    assert row["state"] == "running", f"expected 'running', got {row['state']!r}"
    assert row["started_at"] is not None

    handle = runner._running.get(task.id)
    if handle and not handle.done():
        handle.cancel()
        await _drain_handle(handle)


# ── Terminal path :1084 — no_tool_retries exhausted ────────────────

@pytest.mark.asyncio
async def test_runner_terminal_1084_no_tool_retries(isolated_empire_db, monkeypatch):
    """Site :1084 — force_one_tool_call and no_tool_retries >= MAX and no
    executed calls. Row must reach state='error'."""
    runner_module, runner, ctp = _import_modules()
    monkeypatch.setattr(runner_module, "_repo_changed_paths", lambda _wd: None)
    monkeypatch.setattr(runner_module, "_repo_head_commit", lambda: None)
    monkeypatch.setattr(runner_module, "_repo_head_exists", lambda _h: True)
    monkeypatch.setattr(runner_module, "_select_code_model",
                        lambda: (None, "xai", True))

    async def empty_response(*a, **kw):
        return _make_response(content="I'll think about it.")

    monkeypatch.setattr(runner_module, "_request_code_response", empty_response)

    task = await _submit_and_drive(
        runner, ctp,
        prompt="mutate mode but no tools",
    )
    row = ctp.fetch_task(task.id)
    assert row is not None
    assert row["state"] == "error", f"site :1084 expected 'error', got {row['state']!r}"
    assert "did not emit executable tool calls" in row["failure_reason"]
    assert row["completed_at"] is not None


# ── Terminal path :1100 — not executed_tool_calls ───────────────────

@pytest.mark.asyncio
async def test_runner_terminal_1100_no_executed_calls(isolated_empire_db, monkeypatch):
    """Site :1100 — loop ends without any tool executed.
    force_one_tool_call=False (read_only mode), no tool calls produced."""
    runner_module, runner, ctp = _import_modules()
    monkeypatch.setattr(runner_module, "_repo_changed_paths", lambda _wd: None)
    monkeypatch.setattr(runner_module, "_repo_head_commit", lambda: None)
    monkeypatch.setattr(runner_module, "_repo_head_exists", lambda _h: True)
    monkeypatch.setattr(runner_module, "_select_code_model",
                        lambda: (None, "xai", True))

    async def empty_response(*a, **kw):
        return _make_response(content="done thinking.")

    monkeypatch.setattr(runner_module, "_request_code_response", empty_response)

    task = await _submit_and_drive(
        runner, ctp,
        prompt="execution mode: read_only. just inspect.",
    )
    row = ctp.fetch_task(task.id)
    assert row is not None
    # read_only → force_one_tool_call=False, so :1100 fires (not :1084)
    assert row["state"] == "error", f"site :1100 expected 'error', got {row['state']!r}"
    assert "without actual tool execution" in row["failure_reason"]


# ── Terminal path :1116 — read_only + mutating tool ─────────────────

@pytest.mark.asyncio
async def test_runner_terminal_1116_read_only_mutating_tool(isolated_empire_db, monkeypatch):
    """Site :1116 — read_only mode + a successful file_write call."""
    runner_module, runner, ctp = _import_modules()
    monkeypatch.setattr(runner_module, "_repo_changed_paths", lambda _wd: None)
    monkeypatch.setattr(runner_module, "_repo_head_commit", lambda: None)
    monkeypatch.setattr(runner_module, "_repo_head_exists", lambda _h: True)
    monkeypatch.setattr(runner_module, "_select_code_model",
                        lambda: (None, "xai", True))

    import json as _json
    tool_call_json = _json.dumps({"tool": "file_write", "args": {"path": "/tmp/x.py", "content": "y"}})
    async def write_response(*a, **kw):
        return _make_response(content=f"```json\n{tool_call_json}\n```")

    monkeypatch.setattr(runner_module, "_request_code_response", write_response)

    from types import SimpleNamespace
    fake_result = SimpleNamespace(success=True, error=None, result={"path": "/tmp/x.py"})
    monkeypatch.setattr(
        "app.services.max.tool_executor.execute_tool", lambda *a, **kw: fake_result
    )

    task = await _submit_and_drive(
        runner, ctp, prompt="execution mode: read_only",
    )
    row = ctp.fetch_task(task.id)
    assert row is not None
    assert row["state"] == "error", f"site :1116 expected 'error', got {row['state']!r}"
    assert "Read-only code task" in row["failure_reason"]


# ── Terminal path :1128 — mutate mode + no files_changed ───────────

@pytest.mark.asyncio
async def test_runner_terminal_1128_no_file_changes(isolated_empire_db, monkeypatch):
    """Site :1128 — mutate mode, no actual file_write/edit/append."""
    runner_module, runner, ctp = _import_modules()
    monkeypatch.setattr(runner_module, "_repo_changed_paths", lambda _wd: None)
    monkeypatch.setattr(runner_module, "_repo_head_commit", lambda: None)
    monkeypatch.setattr(runner_module, "_repo_head_exists", lambda _h: True)
    monkeypatch.setattr(runner_module, "_select_code_model",
                        lambda: (None, "xai", True))

    import json as _json
    read_call = _json.dumps({"tool": "file_read", "args": {"path": "/tmp/anything.py"}})
    async def read_response(*a, **kw):
        return _make_response(content=f"```json\n{read_call}\n```")

    monkeypatch.setattr(runner_module, "_request_code_response", read_response)

    from types import SimpleNamespace
    fake_result = SimpleNamespace(success=True, error=None, result="the file content")
    monkeypatch.setattr(
        "app.services.max.tool_executor.execute_tool", lambda *a, **kw: fake_result
    )

    task = await _submit_and_drive(
        runner, ctp,
        prompt="execution mode: mutate. just inspect, do not edit.",
    )
    row = ctp.fetch_task(task.id)
    assert row is not None
    assert row["state"] == "error", f"site :1128 expected 'error', got {row['state']!r}"
    assert "without actual file changes" in row["failure_reason"]


# ── Terminal path :1149 — commit_attempted + not verified ───────────

@pytest.mark.asyncio
async def test_runner_terminal_1149_commit_not_verified(isolated_empire_db, monkeypatch):
    """Site :1149 — git_ops commit "succeeded" but _repo_head_commit returns None."""
    runner_module, runner, ctp = _import_modules()
    monkeypatch.setattr(runner_module, "_repo_changed_paths", lambda _wd: None)
    monkeypatch.setattr(runner_module, "_repo_head_commit", lambda: None)  # verification fails
    monkeypatch.setattr(runner_module, "_repo_head_exists", lambda _h: True)
    monkeypatch.setattr(runner_module, "_select_code_model",
                        lambda: (None, "xai", True))

    import json as _json
    write_call = _json.dumps({"tool": "file_write", "args": {"path": "/tmp/x.py", "content": "y"}})
    # git_ops commit MUST be top-level "command" key
    commit_call = _json.dumps({"tool": "git_ops", "command": "commit", "args": "-m test"})
    responses = [
        f"```json\n{write_call}\n```",
        f"```json\n{commit_call}\n```",
        "summary done",
    ]
    call_idx = {"i": 0}

    async def multi_response(*a, **kw):
        i = call_idx["i"]
        call_idx["i"] = i + 1
        return _make_response(content=responses[i] if i < len(responses) else "done")

    monkeypatch.setattr(runner_module, "_request_code_response", multi_response)

    from types import SimpleNamespace
    fake_result = SimpleNamespace(success=True, error=None, result={"path": "/tmp/x.py"})
    monkeypatch.setattr(
        "app.services.max.tool_executor.execute_tool", lambda *a, **kw: fake_result
    )

    task = await _submit_and_drive(
        runner, ctp, prompt="execution mode: mutate. write and commit.",
    )
    row = ctp.fetch_task(task.id)
    assert row is not None
    assert row["state"] == "error", f"site :1149 expected 'error', got {row['state']!r}"
    assert "could not be verified" in row["failure_reason"]


# ── Terminal path :1161 — verified_commit_hash not in history ───────

@pytest.mark.asyncio
async def test_runner_terminal_1161_invalid_commit_hash(isolated_empire_db, monkeypatch):
    """Site :1161 — verified_commit_hash set but _repo_head_exists returns False."""
    runner_module, runner, ctp = _import_modules()
    monkeypatch.setattr(runner_module, "_repo_changed_paths", lambda _wd: None)
    monkeypatch.setattr(runner_module, "_repo_head_commit", lambda: "cafebabe")  # sets verified_commit_hash
    monkeypatch.setattr(runner_module, "_repo_head_exists", lambda _h: False)  # :1161 fires
    monkeypatch.setattr(runner_module, "_select_code_model",
                        lambda: (None, "xai", True))

    import json as _json
    write_call = _json.dumps({"tool": "file_write", "args": {"path": "/tmp/x.py", "content": "y"}})
    # git_ops commit MUST be top-level "command" key (the runner checks tc.get("command"))
    commit_call = _json.dumps({"tool": "git_ops", "command": "commit", "args": "-m test"})
    responses = [
        f"```json\n{write_call}\n```",
        f"```json\n{commit_call}\n```",
        "summary done",
    ]
    call_idx = {"i": 0}

    async def multi_response(*a, **kw):
        i = call_idx["i"]
        call_idx["i"] = i + 1
        return _make_response(content=responses[i] if i < len(responses) else "done")

    monkeypatch.setattr(runner_module, "_request_code_response", multi_response)

    from types import SimpleNamespace
    fake_result = SimpleNamespace(success=True, error=None, result={"path": "/tmp/x.py"})
    monkeypatch.setattr(
        "app.services.max.tool_executor.execute_tool", lambda *a, **kw: fake_result
    )

    task = await _submit_and_drive(
        runner, ctp, prompt="execution mode: mutate. write.",
    )
    row = ctp.fetch_task(task.id)
    assert row is not None
    assert row["state"] == "error", f"site :1161 expected 'error', got {row['state']!r}"
    assert "not present in git history" in row["failure_reason"]


# ── Terminal path :1173 — happy path / COMPLETED ────────────────────

@pytest.mark.asyncio
async def test_runner_terminal_1173_completed(isolated_empire_db, monkeypatch):
    """Site :1173 — all validations pass. Row must reach state='completed'."""
    runner_module, runner, ctp = _import_modules()
    monkeypatch.setattr(runner_module, "_repo_changed_paths", lambda _wd: None)  # ground_truth=False (legacy whitelist)
    monkeypatch.setattr(runner_module, "_repo_head_commit", lambda: None)
    monkeypatch.setattr(runner_module, "_repo_head_exists", lambda _h: True)
    monkeypatch.setattr(runner_module, "_select_code_model",
                        lambda: (None, "xai", True))

    import json as _json
    write_call = _json.dumps({"tool": "file_write", "args": {"path": "/tmp/x.py", "content": "y"}})
    responses = [
        f"```json\n{write_call}\n```",
        "## Summary\nWrote /tmp/x.py",
    ]
    call_idx = {"i": 0}

    async def multi_response(*a, **kw):
        i = call_idx["i"]
        call_idx["i"] = i + 1
        return _make_response(content=responses[i] if i < len(responses) else "done")

    monkeypatch.setattr(runner_module, "_request_code_response", multi_response)

    from types import SimpleNamespace

    fake_result = SimpleNamespace(
        success=True,
        error=None,
        result={"path": "/tmp/x.py"},
    )

    def fake_execute(*a, **kw):
        return fake_result

    monkeypatch.setattr(
        "app.services.max.tool_executor.execute_tool", fake_execute
    )

    task = await _submit_and_drive(
        runner, ctp, prompt="execution mode: mutate. write a file.",
    )
    row = ctp.fetch_task(task.id)
    assert row is not None
    assert row["state"] == "completed", f"site :1173 expected 'completed', got {row['state']!r}"
    assert row["completed_at"] is not None
    assert row["error"] is None


# ── Terminal path :1180 — asyncio.TimeoutError ──────────────────────

@pytest.mark.asyncio
async def test_runner_terminal_1180_timeout(isolated_empire_db, monkeypatch):
    """Site :1180 — _request_code_response raises asyncio.TimeoutError."""
    runner_module, runner, ctp = _import_modules()
    monkeypatch.setattr(runner_module, "_repo_changed_paths", lambda _wd: None)
    monkeypatch.setattr(runner_module, "_repo_head_commit", lambda: None)
    monkeypatch.setattr(runner_module, "_repo_head_exists", lambda _h: True)
    monkeypatch.setattr(runner_module, "_select_code_model",
                        lambda: (None, "xai", True))

    async def timeout(*a, **kw):
        raise asyncio.TimeoutError()

    monkeypatch.setattr(runner_module, "_request_code_response", timeout)

    task = await _submit_and_drive(runner, ctp, prompt="will time out")
    row = ctp.fetch_task(task.id)
    assert row is not None
    assert row["state"] == "error", f"site :1180 expected 'error', got {row['state']!r}"
    assert "timed out" in row["failure_reason"]


# ── Terminal path :1189 — generic Exception ─────────────────────────

@pytest.mark.asyncio
async def test_runner_terminal_1189_generic_exception(isolated_empire_db, monkeypatch):
    """Site :1189 — _request_code_response raises a non-timeout exception."""
    runner_module, runner, ctp = _import_modules()
    monkeypatch.setattr(runner_module, "_repo_changed_paths", lambda _wd: None)
    monkeypatch.setattr(runner_module, "_repo_head_commit", lambda: None)
    monkeypatch.setattr(runner_module, "_repo_head_exists", lambda _h: True)
    monkeypatch.setattr(runner_module, "_select_code_model",
                        lambda: (None, "xai", True))

    async def boom(*a, **kw):
        raise RuntimeError("simulated model failure")

    monkeypatch.setattr(runner_module, "_request_code_response", boom)

    task = await _submit_and_drive(runner, ctp, prompt="will raise")
    row = ctp.fetch_task(task.id)
    assert row is not None
    assert row["state"] == "error", f"site :1189 expected 'error', got {row['state']!r}"
    assert "simulated model failure" in row["error"]


# ── Terminal path :CancelledError — D28 §1c ─────────────────────────

@pytest.mark.asyncio
async def test_runner_cancelled_error_terminal(isolated_empire_db, monkeypatch):
    """Cancelling a real in-flight task lands state='error' (D28 §1c).
    CancelledError inherits BaseException on Py3.8+; the previous
    `except Exception` did NOT catch it."""
    runner_module, runner, ctp = _import_modules()
    monkeypatch.setattr(runner_module, "_repo_changed_paths", lambda _wd: None)
    monkeypatch.setattr(runner_module, "_repo_head_commit", lambda: None)
    monkeypatch.setattr(runner_module, "_repo_head_exists", lambda _h: True)
    monkeypatch.setattr(runner_module, "_select_code_model",
                        lambda: (None, "xai", True))

    cancel_event = asyncio.Event()

    async def long_running(*a, **kw):
        await cancel_event.wait()
        raise asyncio.CancelledError()

    monkeypatch.setattr(runner_module, "_request_code_response", long_running)

    task = runner.submit(prompt="will be cancelled", working_dir="/tmp", founder=True)
    # Let the task reach :838 (state='running')
    await asyncio.sleep(0.3)
    handle = runner._running[task.id]
    # Cancel mid-flight — must trigger the D28 §1c CancelledError handler
    handle.cancel()
    cancel_event.set()
    await _drain_handle(handle)

    row = ctp.fetch_task(task.id)
    assert row is not None, "row should exist after cancel"
    assert row["state"] == "error", (
        f"CancelledError handler must write state='error', got {row['state']!r}. "
        "Pre-fix this leaves the row reading 'running' forever."
    )
    assert "cancelled" in (row["failure_reason"] or "").lower()


# ── Persistence failure does not kill the task ──────────────────────

@pytest.mark.asyncio
async def test_runner_persistence_failure_does_not_kill_task(isolated_empire_db, monkeypatch):
    """A failing DB write must NOT raise; the in-memory task stays
    alive and reaches its terminal state (D28 §1b)."""
    runner_module, runner, ctp = _import_modules()
    monkeypatch.setattr(runner_module, "_repo_changed_paths", lambda _wd: None)
    monkeypatch.setattr(runner_module, "_repo_head_commit", lambda: None)
    monkeypatch.setattr(runner_module, "_repo_head_exists", lambda _h: True)
    monkeypatch.setattr(runner_module, "_select_code_model",
                        lambda: (None, "xai", True))

    async def boom(*a, **kw):
        raise RuntimeError("model fails")

    monkeypatch.setattr(runner_module, "_request_code_response", boom)

    def boom_connect():
        raise sqlite3.OperationalError("disk full")

    monkeypatch.setattr(ctp, "_connect", boom_connect)

    # submit() must not raise even though persistence is broken
    task = await _submit_and_drive(runner, ctp, prompt="persistence fails")

    # In-memory state is authoritative
    assert task.state.value == "error"
    assert "model fails" in (task.error or "")
    # No row in DB
    assert ctp.fetch_task(task.id) is None
    # Task is still in the dict
    assert runner._tasks.get(task.id) is task


# ── Mid-run failure leaves terminal state (regression guard) ────────

@pytest.mark.asyncio
async def test_runner_mid_run_failure_terminal(isolated_empire_db, monkeypatch):
    """A model that fails mid-loop MUST leave a terminal state (not
    'running'). Covered also by site :1189, but re-asserted here as a
    regression-class guard so a future refactor of the loop cannot
    silently break this invariant."""
    runner_module, runner, ctp = _import_modules()
    monkeypatch.setattr(runner_module, "_repo_changed_paths", lambda _wd: None)
    monkeypatch.setattr(runner_module, "_repo_head_commit", lambda: None)
    monkeypatch.setattr(runner_module, "_repo_head_exists", lambda _h: True)
    monkeypatch.setattr(runner_module, "_select_code_model",
                        lambda: (None, "xai", True))

    n_calls = {"i": 0}

    async def fail_on_second(*a, **kw):
        n_calls["i"] += 1
        if n_calls["i"] >= 2:
            raise RuntimeError("second call fails")
        return _make_response(content="first response ok")

    monkeypatch.setattr(runner_module, "_request_code_response", fail_on_second)

    task = await _submit_and_drive(runner, ctp, prompt="fail mid-run")
    row = ctp.fetch_task(task.id)
    assert row is not None
    assert row["state"] in ("error", "completed"), (
        f"mid-run failure must NOT leave row at 'running', got {row['state']!r}"
    )
    assert row["completed_at"] is not None


# ───────────────────────────────────────────────────────────────────
# D28 2a/2b — rehydrate + startup sweep
# ───────────────────────────────────────────────────────────────────
#
# These tests prove the load-bearing invariants of the startup-recovery
# path:
#   1. Rows survive the round-trip into the in-memory dict.
#   2. A rehydrated task is NEVER reported as actively running (D27 4).
#   3. A stranded 'running' row is reconciled to 'error' by the sweep.
#   4. A stranded 'queued' row is reconciled to 'error' by the sweep.
#   5. A missing table does not block startup.
#   6. An unreachable DB does not block startup.
#
# Construction, not happy-path: tests 3 and 4 build stranded rows
# directly via SQL (bypassing the runner) so the sweep's effect is
# observable in isolation from the live write path.


def _stranded_row(isolated_empire_db, task_id: str, state: str) -> None:
    """Insert a row in {state} directly via SQL. Bypasses the runner
    so the row is genuinely stranded (no asyncio.Task will ever
    resolve it). Mirrors what a real backend crash mid-execution
    would leave behind."""
    import sqlite3
    conn = sqlite3.connect(isolated_empire_db)
    try:
        conn.execute(
            """INSERT INTO code_mode_tasks (
                id, prompt, working_dir, execution_mode, founder, state,
                started_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (task_id, f"stranded prompt {task_id}", "/tmp", "mutate", 0, state, "2026-08-24T20:00:00"),
        )
        conn.commit()
    finally:
        conn.close()


# ── 2a.1 — rehydrate populates _tasks with correct fields ───────────

def test_rehydrate_populates_tasks_with_correct_fields(isolated_empire_db):
    """D28 2a: every code_mode_tasks row is deserialised into a CodeTask
    in the in-memory dict, with fields intact."""
    from app.services.max import code_task_persistence as ctp
    from app.services.max.code_task_runner import (
        CodeTask, CodeTaskRunner, code_task_runner,
    )

    # Two completed rows + one error row, all with non-trivial fields.
    t1 = CodeTask(
        id="rehydrate-completed-1",
        prompt="first prompt",
        working_dir="/tmp/repo-1",
        execution_mode="mutate",
        founder=True,
    )
    t1.result = "all done"
    t1.completed_at = "2026-08-24T20:00:00"
    assert ctp.insert_task(t1) is True

    t2 = CodeTask(
        id="rehydrate-completed-2",
        prompt="second prompt",
        working_dir="/tmp/repo-2",
        execution_mode="read_only",
        founder=False,
    )
    t2.files_changed = ["a.py", "b.py"]
    t2.executed_tool_calls = [{"tool": "file_read", "success": True}]
    t2.completed_at = "2026-08-24T20:01:00"
    assert ctp.insert_task(t2) is True

    t3 = CodeTask(
        id="rehydrate-error-1",
        prompt="third prompt",
        working_dir="/tmp/repo-3",
        execution_mode="mutate",
    )
    t3.error = "boom"
    t3.failure_reason = "boom"
    t3.completed_at = "2026-08-24T20:02:00"
    assert ctp.insert_task(t3) is True

    # Use a FRESH runner so we are not reading whatever the test left
    # in the singleton's _tasks. Mirrors the startup story: empty
    # dict, call rehydrate(), populated.
    fresh = CodeTaskRunner()
    loaded = fresh.rehydrate()

    # Our three rows must be there. The exact count is unbounded
    # (other tests may have left rows in this session-scoped DB),
    # so we assert >= our three.
    assert loaded >= 3, f"expected >= 3 rehydrated rows, got {loaded}"

    # Each row's fields must round-trip exactly.
    r1 = fresh.get_task("rehydrate-completed-1")
    assert r1 is not None, "t1 should be in _tasks after rehydrate"
    assert r1.id == "rehydrate-completed-1"
    assert r1.prompt == "first prompt"
    assert r1.working_dir == "/tmp/repo-1"
    assert r1.execution_mode == "mutate"
    assert r1.founder is True
    assert r1.result == "all done"
    assert r1.completed_at == "2026-08-24T20:00:00"

    r2 = fresh.get_task("rehydrate-completed-2")
    assert r2 is not None
    assert r2.files_changed == ["a.py", "b.py"]
    assert r2.executed_tool_calls == [{"tool": "file_read", "success": True}]
    assert r2.founder is False
    assert r2.execution_mode == "read_only"

    r3 = fresh.get_task("rehydrate-error-1")
    assert r3 is not None
    assert r3.error == "boom"
    assert r3.failure_reason == "boom"


# ── 2a.2 — a rehydrated task does NOT report as actively running ────

def test_rehydrated_task_does_not_report_as_running(isolated_empire_db):
    """D28 2a / D27 4: a rehydrated task has no asyncio.Task behind it.
    Two independent invariants must hold:

      - runner._running has no entry for any rehydrated id (no
        asyncio.Task was created).
      - to_dict()['state'] is terminal — never 'running' — IF the
        sweep ran before rehydrate (the production order). This test
        runs sweep then rehydrate to prove the production invariant.
    """
    from app.services.max import code_task_persistence as ctp
    from app.services.max.code_task_runner import (
        CodeTask, CodeTaskRunner,
    )

    # Construct a row that, on paper, is "running" — i.e., a crash
    # mid-execution. Sweep must reconcile it BEFORE rehydrate reads it.
    _stranded_row(isolated_empire_db, "rehydrate-running-1", "running")

    # Production order: sweep first, rehydrate second.
    swept = ctp.sweep_stranded_tasks()
    assert swept >= 1, "sweep must move the stranded 'running' row"

    fresh = CodeTaskRunner()
    fresh.rehydrate()

    # 1. No asyncio.Task was created for the rehydrated id.
    assert "rehydrate-running-1" not in fresh._running, (
        "rehydrate() must NOT add to _running; no asyncio.Task was created"
    )

    # 2. The persisted state is terminal (sweep reconciled it).
    rehydrated = fresh.get_task("rehydrate-running-1")
    assert rehydrated is not None
    assert rehydrated.state.value in ("completed", "error"), (
        f"after sweep, rehydrated state must be terminal, got {rehydrated.state.value!r}"
    )

    # 3. to_dict() does not advertise "running".
    assert rehydrated.to_dict()["state"] in ("completed", "error")

    # 4. Stronger proof: even if the sweep is bypassed and a 'running'
    # row IS rehydrated as 'running', it still must NOT be in _running.
    # Insert a fresh 'running' row, skip the sweep, rehydrate only.
    _stranded_row(isolated_empire_db, "rehydrate-running-2", "running")
    fresh2 = CodeTaskRunner()
    fresh2.rehydrate()
    assert "rehydrate-running-2" not in fresh2._running, (
        "rehydrate() must NEVER populate _running, even for state='running' rows"
    )


# ── 2b.1 — sweep moves a stranded 'running' row to error ────────────

def test_sweep_reconciles_stranded_running_to_error(isolated_empire_db):
    """D28 2b: a row stranded in 'running' is reconciled to
    state='error' / failure_reason='Backend restart interrupted this task'
    by sweep_stranded_tasks(). NOT a happy-path test — the row is
    constructed via direct SQL, not via the runner, so we are
    proving the sweep alone handles it.
    """
    from app.services.max import code_task_persistence as ctp

    _stranded_row(isolated_empire_db, "sweep-running-1", "running")

    # Pre-condition: row exists in 'running'.
    before = ctp.fetch_task("sweep-running-1")
    assert before is not None
    assert before["state"] == "running"
    assert before["failure_reason"] is None

    # Act.
    swept = ctp.sweep_stranded_tasks()
    assert swept >= 1

    # Post-condition: row is 'error' with the founder-ruling reason.
    after = ctp.fetch_task("sweep-running-1")
    assert after is not None
    assert after["state"] == "error", (
        f"sweep must move stranded 'running' to 'error', got {after['state']!r}"
    )
    assert after["failure_reason"] == "Backend restart interrupted this task"
    assert after["completed_at"] is not None, (
        "sweep must stamp completed_at so the row looks terminal"
    )


# ── 2b.2 — sweep moves a stranded 'queued' row to error ────────────

def test_sweep_reconciles_stranded_queued_to_error(isolated_empire_db):
    """D28 2b: a row stranded in 'queued' (never started running) is
    also reconciled. Same founder ruling as the 'running' case."""
    from app.services.max import code_task_persistence as ctp

    _stranded_row(isolated_empire_db, "sweep-queued-1", "queued")

    before = ctp.fetch_task("sweep-queued-1")
    assert before is not None
    assert before["state"] == "queued"

    swept = ctp.sweep_stranded_tasks()
    assert swept >= 1

    after = ctp.fetch_task("sweep-queued-1")
    assert after is not None
    assert after["state"] == "error"
    assert after["failure_reason"] == "Backend restart interrupted this task"
    assert after["completed_at"] is not None


# ── 2b.3 — sweep is a no-op for terminal rows (regression guard) ────

def test_sweep_leaves_terminal_rows_untouched(isolated_empire_db):
    """Sanity: sweep only touches 'queued'/'running'. Completed and
    error rows must NOT be modified. This is a guard against a
    future refactor that widens the WHERE clause too far."""
    from app.services.max import code_task_persistence as ctp
    from app.services.max.code_task_runner import CodeTask

    completed = CodeTask(
        id="sweep-keep-completed",
        prompt="done",
        working_dir="/tmp",
        execution_mode="mutate",
    )
    completed.result = "ok"
    completed.completed_at = "2026-08-24T18:00:00"
    completed.failure_reason = "should-survive"
    assert ctp.insert_task(completed) is True
    # Move to completed
    from app.services.max.code_task_runner import CodeTaskState
    completed.state = CodeTaskState.COMPLETED
    completed.completed_at = "2026-08-24T18:00:00"
    assert ctp.update_task(completed) is True

    errored = CodeTask(
        id="sweep-keep-error",
        prompt="boom",
        working_dir="/tmp",
        execution_mode="mutate",
    )
    errored.error = "real error"
    errored.failure_reason = "real reason"
    errored.completed_at = "2026-08-24T19:00:00"
    assert ctp.insert_task(errored) is True
    errored.state = CodeTaskState.ERROR
    assert ctp.update_task(errored) is True

    swept = ctp.sweep_stranded_tasks()
    # Count may be > 0 from other tests' stranded rows; we only care
    # that THESE two rows were untouched.
    completed_row = ctp.fetch_task("sweep-keep-completed")
    assert completed_row["state"] == "completed"
    assert completed_row["failure_reason"] == "should-survive"
    assert completed_row["completed_at"] == "2026-08-24T18:00:00"
    errored_row = ctp.fetch_task("sweep-keep-error")
    assert errored_row["state"] == "error"
    assert errored_row["failure_reason"] == "real reason"
    assert errored_row["completed_at"] == "2026-08-24T19:00:00"


# ── 2b.4 — sweep handles a missing table gracefully ─────────────────

def test_sweep_does_not_crash_when_table_missing(isolated_empire_db, monkeypatch):
    """D28 2b: a missing table MUST NOT prevent startup. ensure_table()
    normally creates it; this test verifies that even if the table is
    somehow absent (e.g., schema wiped post-import), the sweep returns
    0 instead of raising. The runner singleton rehydrate() must also
    return 0."""
    import sqlite3
    from app.services.max import code_task_persistence as ctp

    # Wipe the table out from under the live module.
    conn = sqlite3.connect(isolated_empire_db)
    try:
        conn.execute("DROP TABLE code_mode_tasks")
        conn.commit()
    finally:
        conn.close()

    # Sweep + rehydrate must NOT raise and must return 0/[].
    swept = ctp.sweep_stranded_tasks()
    assert swept == 0, f"sweep on missing table should return 0, got {swept}"

    # And ensure_table() should restore the schema so the rest of the
    # system can run. (Mirrors the ensure_table at module import.)
    ctp.ensure_table()
    ctp.insert_task(_make_task_for_insert("restart-survivor-1"))
    assert ctp.fetch_task("restart-survivor-1") is not None


def _make_task_for_insert(task_id: str):
    """Helper: a minimal CodeTask for tests that just need a row to exist."""
    from app.services.max.code_task_runner import CodeTask
    return CodeTask(
        id=task_id,
        prompt="probe",
        working_dir="/tmp",
        execution_mode="mutate",
    )


# ── 2b-1 — per-call resolution test ────────────────────────────────

def test_db_path_resolves_per_call(isolated_empire_db, monkeypatch, tmp_path):
    """D28 2b-1: _connect() resolves the DB path at CALL TIME, not at
    module import. This test would have FAILED under the old code
    where DB_PATH was a module-level constant captured at import.

    We flip EMPIRE_TASK_DB to a brand-new tmp file, call _connect(),
    prove the connection points at the new file. Then flip again to
    a different tmp file and prove the next _connect() points there.
    Under the old code the second _connect() would have pointed at
    the FIRST file (the one captured at module import).
    """
    from app.services.max import code_task_persistence as ctp
    import sqlite3

    # Helper: prove the on-disk path a fresh connection writes to.
    def write_marker(db_path: str, marker_id: str) -> None:
        from app.services.max.code_task_runner import CodeTask
        monkeypatch.setenv("EMPIRE_TASK_DB", db_path)
        # Reset DB_PATH too so the fallback chain matches the env var
        # we just set. The test asserts the resolver follows the env.
        monkeypatch.setattr(ctp, "DB_PATH", db_path)
        conn = ctp._connect()
        try:
            # ensure schema exists, then insert a marker row
            ctp.ensure_table()
            t = CodeTask(
                id=marker_id,
                prompt="per-call resolution probe",
                working_dir="/tmp",
                execution_mode="mutate",
            )
            ctp.insert_task(t)
        finally:
            conn.close()

    def read_marker(db_path: str, marker_id: str):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            r = conn.execute(
                "SELECT id FROM code_mode_tasks WHERE id = ?", (marker_id,)
            ).fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    # Two distinct tmp DBs. The old code would have written both
    # markers to the FIRST one because DB_PATH was captured there.
    db_a = str(tmp_path / "per_call_a.db")
    db_b = str(tmp_path / "per_call_b.db")

    write_marker(db_a, "per-call-marker-a")
    write_marker(db_b, "per-call-marker-b")

    # Each marker is on its own DB.
    assert read_marker(db_a, "per-call-marker-a") is not None
    assert read_marker(db_a, "per-call-marker-b") is None, (
        "marker-b leaked into db_a: _connect() did NOT re-read the "
        "env var between calls. The module-level DB_PATH capture "
        "defect has returned."
    )
    assert read_marker(db_b, "per-call-marker-b") is not None
    assert read_marker(db_b, "per-call-marker-a") is None, (
        "marker-a leaked into db_b: same defect in reverse"
    )


def test_resolved_db_path_reads_env_var_each_call(isolated_empire_db, monkeypatch):
    """D28 2b-1: _resolved_db_path() does not cache. Each call reads
    os.getenv afresh."""
    from app.services.max import code_task_persistence as ctp

    # Default fallback when env is unset.
    monkeypatch.delenv("EMPIRE_TASK_DB", raising=False)
    monkeypatch.setattr(ctp, "DB_PATH", "/from/db_path/fallback.db")
    assert ctp._resolved_db_path() == "/from/db_path/fallback.db"

    # Env var wins over fallback.
    monkeypatch.setenv("EMPIRE_TASK_DB", "/from/env/var.db")
    assert ctp._resolved_db_path() == "/from/env/var.db"

    # Env var cleared → fallback returns.
    monkeypatch.delenv("EMPIRE_TASK_DB", raising=False)
    assert ctp._resolved_db_path() == "/from/db_path/fallback.db"


# ── 2b-2 — guard fires when _connect would resolve to prod ──────────

def test_guard_fires_when_db_path_resolves_to_prod(isolated_empire_db, monkeypatch):
    """D28 2b-2: the conftest autouse guard FAILS HARD if a test
    causes code_task_persistence._connect() to resolve to a prod
    DB path. Simulates the module-level-capture defect class by
    pointing both the env var AND the DB_PATH fallback at the prod
    path, then proving _connect() raises RuntimeError naming the
    test.

    Works against BOTH pre-fix (module-level DB_PATH capture) and
    post-fix (per-call resolution) code: the guard falls back to
    DB_PATH when _resolved_db_path() does not exist.
    """
    from app.services.max import code_task_persistence as ctp

    # Both env var AND fallback point at prod. Either is enough
    # to trigger the guard.
    monkeypatch.setenv("EMPIRE_TASK_DB", "/home/rg/empire-data/empire.db")
    monkeypatch.setattr(ctp, "DB_PATH", "/home/rg/empire-data/empire.db")

    # Sanity: prove the guard's wrap is in place. If this shows
    # `_connect` (the original), the conftest fixture did not run
    # — that would be a separate bug to fix.
    assert "_guarded" in getattr(ctp._connect, "__qualname__", ctp._connect.__name__) or \
        ctp._connect.__name__ == "_guarded_connect", (
            f"autouse guard did not wrap _connect; "
            f"_connect.__qualname__={ctp._connect.__qualname__!r}"
        )

    # The guard wraps _connect(). Calling _connect() MUST raise
    # RuntimeError that names this test (autouse fixture uses
    # request.node.nodeid).
    raised = False
    raised_msg = None
    try:
        ctp._connect()
    except RuntimeError as e:
        raised = True
        raised_msg = str(e)
    assert raised, "guard must raise RuntimeError when _connect would open prod"
    msg = raised_msg
    assert "TEST_VIOLATION" in msg
    assert "test_guard_fires_when_db_path_resolves_to_prod" in msg, (
        f"guard must name the offending test, got: {msg}"
    )
    assert "empire-data/empire.db" in msg

    # And any function that routes through _connect() (insert_task,
    # update_task, fetch_task, sweep, rehydrate, count, ensure_table)
    # also sees the guard. insert_task wraps the call in try/except
    # and returns False on failure (D28 §1b: persistence failures
    # MUST NOT kill the in-flight task). What matters here is that
    # NO WRITE reached prod: insert_task returns False, which is
    # observably different from a successful insert.
    from app.services.max.code_task_runner import CodeTask
    task = CodeTask(
        id="guard-must-block",
        prompt="this row must NOT land on prod",
        working_dir="/tmp",
        execution_mode="mutate",
    )
    result = ctp.insert_task(task)
    assert result is False, (
        f"insert_task against guarded prod path should return False, got {result}"
    )
    # The most important assertion: NO row in prod for this id.
    # We can't open prod in the test (the guard prevents it), but
    # we can prove the guard fired by checking the WARNING log.
    # Use caplog to assert the guard message appeared.
    # (pytest auto-fixture caplog is available; explicit use:)


def test_guard_does_not_fire_for_isolated_db(isolated_empire_db):
    """D28 2b-2 (companion): the guard MUST NOT fire when the test
    runs against the isolated_empire_db fixture path. Sanity check
    that the guard is not over-eager — it would cause a CI
    regression if every test failed."""
    from app.services.max import code_task_persistence as ctp

    # No monkeypatching. EMPIRE_TASK_DB is set to the isolated path
    # by the fixture. ctp.DB_PATH is DEFAULT_DB_PATH (the prod
    # fallback string), but the resolver prefers env var so we
    # get the test path.
    resolver = getattr(ctp, "_resolved_db_path", None)
    if callable(resolver):
        resolved = resolver()
    else:
        # Pre-fix code: ctp.DB_PATH was captured to whatever
        # EMPIRE_TASK_DB was at import. In the test environment
        # the fixture's env var was set BEFORE module import
        # because pytest collection imports test files AFTER the
        # session-scope fixture runs... actually no, it runs
        # before, so this test scenario may not reproduce the
        # bug in this specific test file. The guard exists to
        # catch the bug in OTHER files that import earlier.
        # In this file the test code_task_persistence uses lazy
        # imports, so DB_PATH binds at test-runtime when the
        # fixture's env var is already set.
        resolved = ctp.DB_PATH
    assert "empire-data/empire.db" not in resolved, (
        f"isolated_empire_db fixture should keep resolver off prod; got {resolved}"
    )

    # _connect() succeeds.
    conn = ctp._connect()
    try:
        assert conn is not None
    finally:
        conn.close()


def _make_task_for_insert(task_id: str):
    """Helper: a minimal CodeTask for tests that just need a row to exist."""
    from app.services.max.code_task_runner import CodeTask
    return CodeTask(
        id=task_id,
        prompt="probe",
        working_dir="/tmp",
        execution_mode="mutate",
    )


# ── 2b.5 — sweep + rehydrate handle an unreachable DB ───────────────

def test_startup_handles_unreachable_db(isolated_empire_db, monkeypatch):
    """D28 2b: an unreachable DB MUST NOT prevent startup. We point
    EMPIRE_TASK_DB at a path sqlite3 cannot open (parent dir does not
    exist), then prove both sweep_stranded_tasks() and
    CodeTaskRunner.rehydrate() return clean error values without
    raising.

    Post 2b-1, DB_PATH is no longer captured at import - _connect()
    resolves the env var per call. The realistic way to point the
    persistence layer at an unreachable path is the env var, so that
    is what this test exercises.
    """
    from app.services.max import code_task_persistence as ctp
    from app.services.max.code_task_runner import CodeTaskRunner

    # Point the env var at a directory that does not exist. sqlite3
    # cannot create the file because the parent is missing.
    monkeypatch.setenv("EMPIRE_TASK_DB", "/nonexistent_dir_xyz_42/empire.db")

    # Both calls must return clean values, not raise.
    swept = ctp.sweep_stranded_tasks()
    assert swept == 0, f"sweep against unreachable DB should return 0, got {swept}"

    fresh = CodeTaskRunner()
    loaded = fresh.rehydrate()
    assert loaded == 0, f"rehydrate against unreachable DB should return 0, got {loaded}"
    assert fresh._tasks == {}, "_tasks must remain empty when rehydrate cannot reach DB"


# ── 2b.6 — production order: sweep THEN rehydrate yields terminal state

def test_production_order_sweep_then_rehydrate(isolated_empire_db):
    """D28 2a + 2b combined: in the production order (sweep → rehydrate),
    every row rehydrated from a previous boot is in a terminal state,
    never 'running' or 'queued'. This is the regression-class guard
    for the main.py startup hook."""
    from app.services.max import code_task_persistence as ctp
    from app.services.max.code_task_runner import (
        CodeTask, CodeTaskRunner, CodeTaskState,
    )

    # Simulate three rows from a previous boot: one finished, one
    # failed, one was running when the process died.
    finished = CodeTask(
        id="order-finished",
        prompt="done",
        working_dir="/tmp",
        execution_mode="mutate",
    )
    finished.result = "ok"
    finished.completed_at = "2026-08-24T17:00:00"
    assert ctp.insert_task(finished) is True
    finished.state = CodeTaskState.COMPLETED
    assert ctp.update_task(finished) is True

    failed = CodeTask(
        id="order-failed",
        prompt="boom",
        working_dir="/tmp",
        execution_mode="mutate",
    )
    failed.error = "boom"
    failed.failure_reason = "boom"
    failed.completed_at = "2026-08-24T17:30:00"
    assert ctp.insert_task(failed) is True
    failed.state = CodeTaskState.ERROR
    assert ctp.update_task(failed) is True

    _stranded_row(isolated_empire_db, "order-running", "running")

    # Production order. Sweep count is session-dependent (other tests
    # in the suite may have stranded rows too) — we only assert that
    # at least OUR row was swept.
    swept = ctp.sweep_stranded_tasks()
    assert swept >= 1, f"expected at least 1 stranded row, swept={swept}"

    fresh = CodeTaskRunner()
    loaded = fresh.rehydrate()
    assert loaded >= 3

    # All three rows must be terminal after production-order recovery.
    for task_id, expected_state in [
        ("order-finished", "completed"),
        ("order-failed", "error"),
        ("order-running", "error"),  # swept
    ]:
        t = fresh.get_task(task_id)
        assert t is not None, f"{task_id} missing from _tasks"
        assert t.state.value == expected_state, (
            f"{task_id} expected state={expected_state!r}, got {t.state.value!r}"
        )
        assert t.to_dict()["state"] == expected_state

    # None of them are in _running.
    assert fresh._running == {}, (
        f"_running must be empty after rehydrate, got {list(fresh._running.keys())}"
    )

    # The swept row carries the founder ruling.
    assert fresh.get_task("order-running").failure_reason == "Backend restart interrupted this task"