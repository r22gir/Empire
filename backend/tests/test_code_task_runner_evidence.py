import asyncio

from app.services.max import code_task_runner as runner_module
from app.services.max.code_task_runner import CodeTask, CodeTaskState
from app.services.max.tool_executor import ToolResult
from app.services.max import tool_executor as tool_executor_module
from app.services.max.desks import desk_manager as desk_manager_module


class _FakeDesk:
    def __init__(self, responses):
        self._responses = iter(responses)

    async def ai_call(self, prompt: str):
        return next(self._responses)


def _patch_runner(monkeypatch, responses, execute_tool_result):
    fake_desk = _FakeDesk(responses)
    monkeypatch.setattr(desk_manager_module.desk_manager, "initialize", lambda: None)
    monkeypatch.setattr(desk_manager_module.desk_manager, "get_desk", lambda name: fake_desk)
    monkeypatch.setattr(
        tool_executor_module,
        "execute_tool",
        lambda tool_call, desk=None: execute_tool_result(tool_call),
    )


def test_read_only_prose_only_summary_is_rejected(monkeypatch):
    _patch_runner(
        monkeypatch,
        ["## Summary\nI inspected the file and made no changes."],
        lambda tool_call: ToolResult(tool=tool_call["tool"], success=True, result={"path": tool_call.get("path")}),
    )
    task = CodeTask(
        id="ct-read-only",
        prompt="Inspect backend/app/main.py. Do not edit files.",
        execution_mode="read_only",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert task.state == CodeTaskState.ERROR
    assert "actual tool execution" in (task.error or "")


def test_real_file_edit_appears_in_files_changed(monkeypatch):
    def fake_execute(tool_call):
        return ToolResult(
            tool=tool_call["tool"],
            success=True,
            result={"path": "backend/app/services/max/drawing_intent.py", "replacements": 1},
        )

    _patch_runner(
        monkeypatch,
        [
            """```tool
{"tool":"file_edit","path":"backend/app/services/max/drawing_intent.py","old_str":"a","new_str":"b"}
```""",
            "## Summary\nDone.",
        ],
        fake_execute,
    )
    task = CodeTask(
        id="ct-edit",
        prompt="Fix drawing intent logic in backend/app/services/max/drawing_intent.py.",
        execution_mode="mutate",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert task.state == CodeTaskState.COMPLETED
    assert "backend/app/services/max/drawing_intent.py" in task.files_changed
    assert task.executed_tool_calls[0]["tool"] == "file_edit"
    assert "Actual tool calls executed:" in (task.result or "")


def test_test_runner_output_is_captured_before_summary(monkeypatch):
    def fake_execute(tool_call):
        return ToolResult(
            tool=tool_call["tool"],
            success=True,
            result={"results": [{"label": "pytest", "ok": True}], "passed": 1, "failed": 0},
        )

    _patch_runner(
        monkeypatch,
        [
            """```tool
{"tool":"test_runner","command":"pytest backend/tests/test_openclaw_worker.py -q"}
```""",
            "## Summary\nTests passed.",
        ],
        fake_execute,
    )
    task = CodeTask(
        id="ct-test",
        prompt="Run tests for backend/app/services/openclaw_worker.py. Do not edit files.",
        execution_mode="read_only",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert task.state == CodeTaskState.COMPLETED
    assert task.verified_test_runs
    assert task.verified_test_runs[0]["tool"] == "test_runner"
    assert "Verified tests:" in (task.result or "")
