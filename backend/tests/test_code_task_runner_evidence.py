import json
import asyncio

from app.services.max import code_task_runner as runner_module
from app.services.max.code_task_runner import CodeTask, CodeTaskState
from app.services.max.tool_executor import ToolResult
from app.services.max import tool_executor as tool_executor_module
from app.services.max.desks import desk_manager as desk_manager_module
from app.services.max.tool_safety import validate_path


class _FakeCodeResponse:
    def __init__(self, content="", model_used="ollama-llama3.1", function_calls=None):
        self.content = content
        self.model_used = model_used
        self.function_calls = function_calls


class _FakeCodeRequester:
    def __init__(self, responses):
        self._responses = iter(responses)
        self.prompts = []

    async def request(self, prompt: str, **kwargs):
        self.prompts.append(prompt)
        return next(self._responses)


def _patch_runner(monkeypatch, responses, execute_tool_result):
    monkeypatch.setattr(desk_manager_module.desk_manager, "initialize", lambda: None)
    monkeypatch.setattr(desk_manager_module.desk_manager, "get_desk", lambda name: object())
    fake_requester = _FakeCodeRequester(responses)
    monkeypatch.setattr(runner_module, "_request_code_response", fake_requester.request)
    monkeypatch.setattr(
        tool_executor_module,
        "execute_tool",
        lambda tool_call, desk=None: execute_tool_result(tool_call),
    )
    return fake_requester


def test_read_only_prose_only_summary_is_rejected(monkeypatch):
    _patch_runner(
        monkeypatch,
        [_FakeCodeResponse("## Summary\nI inspected the file and made no changes.")],
        lambda tool_call: ToolResult(tool=tool_call["tool"], success=True, result={"path": tool_call.get("path")}),
    )
    task = CodeTask(
        id="ct-read-only",
        prompt="Inspect the file. Do not edit files.",
        execution_mode="read_only",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert task.state == CodeTaskState.ERROR
    assert "actual tool execution" in (task.error or "")


def test_edit_task_prose_then_tool_retry(monkeypatch):
    fake_requester = _patch_runner(
        monkeypatch,
        [
            _FakeCodeResponse("## Summary\nI will inspect the file and then update it."),
            _FakeCodeResponse(
                """{
  "tool": "file_edit",
  "args": {
    "path": "backend/app/services/max/drawing_intent.py",
    "old": "a",
    "new": "b"
  }
}"""
            ),
            _FakeCodeResponse("## Summary\nDone."),
        ],
        lambda tool_call: ToolResult(
            tool=tool_call["tool"],
            success=True,
            result={"path": "backend/app/services/max/drawing_intent.py", "replacements": 1},
        ),
    )
    task = CodeTask(
        id="ct-retry",
        prompt="Fix drawing intent logic in backend/app/services/max/drawing_intent.py.",
        execution_mode="mutate",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert task.state == CodeTaskState.COMPLETED
    assert any(
        '"tool":"file_read","args":{"path":"backend/app/services/max/drawing_intent.py"}}' in prompt
        for prompt in fake_requester.prompts
    )
    assert any(
        '{"tool":"file_edit","args":{"path":"backend/app/services/max/drawing_intent.py","old":"before","new":"after"}}' in prompt
        for prompt in fake_requester.prompts
    )
    assert task.executed_tool_calls[0]["tool"] == "file_edit"
    assert "backend/app/services/max/drawing_intent.py" in task.files_changed


def test_edit_task_no_tools_after_retries_fails(monkeypatch):
    fake_requester = _patch_runner(
        monkeypatch,
        [
            _FakeCodeResponse("## Summary\nI will inspect it."),
            _FakeCodeResponse("## Summary\nStill reasoning."),
            _FakeCodeResponse("## Summary\nNeed more context."),
        ],
        lambda tool_call: ToolResult(tool=tool_call["tool"], success=True, result={"path": tool_call.get("path")}),
    )
    task = CodeTask(
        id="ct-no-tools",
        prompt="Fix the bug described above.",
        execution_mode="mutate",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert task.state == CodeTaskState.ERROR
    assert "selected code model did not emit executable tool calls" in (task.error or "")
    assert task.provider_used is not None
    assert task.model_used is not None
    assert task.prompt_attempts >= 2
    assert task.failure_reason and task.model_used in task.error
    assert "No deterministic fallback plan could be inferred" in (task.error or "")
    assert len(fake_requester.prompts) >= 2


def test_edit_task_fallback_planner_executes_explicit_write_and_edit_prompt(monkeypatch):
    fake_requester = _patch_runner(
        monkeypatch,
        [
            _FakeCodeResponse("## Summary\nI am thinking."),
            _FakeCodeResponse("## Summary\nStill thinking."),
            _FakeCodeResponse("## Summary\nNo tool call."),
            _FakeCodeResponse("## Summary\nDone."),
        ],
        lambda tool_call: ToolResult(
            tool=tool_call["tool"],
            success=True,
            result={
                "path": "/tmp/codetaskrunner_tool_test.txt",
                "content": tool_call.get("content"),
                "replacements": 1,
            },
        ),
    )
    task = CodeTask(
        id="ct-fallback",
        prompt="Write /tmp/codetaskrunner_tool_test.txt with content before, then edit it to after. Do not touch repo files. Do not commit.",
        execution_mode="mutate",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert task.state == CodeTaskState.COMPLETED
    assert [call["tool"] for call in task.executed_tool_calls[:2]] == ["file_write", "file_edit"]
    assert "/tmp/codetaskrunner_tool_test.txt" in task.files_changed
    assert any("fallback planner" in note.lower() for note in task.verification_notes)
    assert any("executable tool action" in prompt.lower() for prompt in fake_requester.prompts)


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
            _FakeCodeResponse(
                """{
  "tool": "file_edit",
  "args": {
    "path": "backend/app/services/max/drawing_intent.py",
    "old": "a",
    "new": "b"
  }
}"""
            ),
            _FakeCodeResponse("## Summary\nDone."),
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
            _FakeCodeResponse(
                """{
  "tool": "test_runner",
  "args": {
    "command": "pytest backend/tests/test_openclaw_worker.py -q"
  }
}"""
            ),
            _FakeCodeResponse("## Summary\nTests passed."),
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


def test_read_only_task_can_complete_with_file_read_evidence(monkeypatch):
    fake_requester = _patch_runner(
        monkeypatch,
        [
            _FakeCodeResponse(
                """{
  "tool": "file_read",
  "args": {
    "path": "backend/app/services/openclaw_worker.py"
  }
}"""
            ),
            _FakeCodeResponse("## Summary\nRead complete."),
        ],
        lambda tool_call: ToolResult(
            tool=tool_call["tool"],
            success=True,
            result={"path": "backend/app/services/openclaw_worker.py", "content": "x"},
        ),
    )
    task = CodeTask(
        id="ct-read-ok",
        prompt="Inspect backend/app/services/openclaw_worker.py. Do not edit files. Do not commit.",
        execution_mode="read_only",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert task.state == CodeTaskState.COMPLETED
    assert task.files_inspected == ["backend/app/services/openclaw_worker.py"]
    assert not task.files_changed
    assert any("Do not edit files" in prompt for prompt in fake_requester.prompts)


def test_native_tool_call_path_executes(monkeypatch):
    fake_requester = _patch_runner(
        monkeypatch,
        [
            _FakeCodeResponse(
                "ignored",
                function_calls=[
                    {"tool": "file_read", "path": "backend/app/services/openclaw_worker.py"}
                ],
            ),
            _FakeCodeResponse("## Summary\nRead complete."),
        ],
        lambda tool_call: ToolResult(
            tool=tool_call["tool"],
            success=True,
            result={"path": "backend/app/services/openclaw_worker.py", "content": "x"},
        ),
    )
    task = CodeTask(
        id="ct-native",
        prompt="Inspect backend/app/services/openclaw_worker.py. Do not edit files.",
        execution_mode="read_only",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert task.state == CodeTaskState.COMPLETED
    assert task.executed_tool_calls[0]["tool"] == "file_read"
    assert task.files_inspected == ["backend/app/services/openclaw_worker.py"]
    assert fake_requester.prompts


def test_native_edit_function_call_is_normalized(monkeypatch):
    fake_requester = _patch_runner(
        monkeypatch,
        [
            _FakeCodeResponse(
                "ignored",
                function_calls=[
                    {
                        "name": "file_edit",
                        "arguments": json.dumps({
                            "path": "/tmp/codetaskrunner_tool_test.txt",
                            "old": "before",
                            "new": "after",
                        }),
                    }
                ],
            ),
            _FakeCodeResponse("## Summary\nEdit complete."),
        ],
        lambda tool_call: ToolResult(
            tool=tool_call["tool"],
            success=True,
            result={"path": "/tmp/codetaskrunner_tool_test.txt", "replacements": 1},
        ),
    )
    task = CodeTask(
        id="ct-native-edit",
        prompt="Write /tmp/codetaskrunner_tool_test.txt with content before, then edit it to after. Do not commit.",
        execution_mode="mutate",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert task.state == CodeTaskState.COMPLETED
    assert task.executed_tool_calls[0]["tool"] == "file_edit"
    assert "/tmp/codetaskrunner_tool_test.txt" in task.files_changed
    assert fake_requester.prompts


def test_invalid_json_output_fails(monkeypatch):
    _patch_runner(
        monkeypatch,
        [_FakeCodeResponse('{"tool":"file_read","args":{"path":"backend/app/main.py"')],
        lambda tool_call: ToolResult(tool=tool_call["tool"], success=True, result={"path": tool_call.get("path")}),
    )
    task = CodeTask(
        id="ct-invalid-json",
        prompt="Inspect the file. Do not edit files.",
        execution_mode="read_only",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert task.state == CodeTaskState.ERROR
    assert "actual tool execution" in (task.error or "")


def test_unknown_tool_output_is_rejected(monkeypatch):
    _patch_runner(
        monkeypatch,
        [
            _FakeCodeResponse('{"tool":"made_up_tool","args":{"path":"backend/app/main.py"}}'),
            _FakeCodeResponse("## Summary\nDone."),
        ],
        lambda tool_call: ToolResult(tool=tool_call["tool"], success=False, error="Unknown tool"),
    )
    task = CodeTask(
        id="ct-unknown-tool",
        prompt="Inspect the file. Do not edit files.",
        execution_mode="read_only",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert task.state == CodeTaskState.ERROR
    assert task.executed_tool_calls == []
    assert any(entry.action == "blocked" and "made_up_tool" in entry.detail for entry in task.log)


def test_path_escape_is_rejected_by_tool_safety():
    ok, reason = validate_path("/etc/passwd")
    assert not ok
    assert "protected system directory" in reason or "allowed directories" in reason

    ok_tmp, reason_tmp = validate_path("/data/empire/self_heal_tests/code_task_evidence_test.json")
    assert ok_tmp, reason_tmp
