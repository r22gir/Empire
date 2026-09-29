"""
F1 scorer fixtures — code_task_runner.py:399 (the bug) and the fix.

These tests reproduce REAL provider response shapes (native function_calls,
raw JSON, fenced JSON, prose, malformed) and assert that the scorer
records the parsed result, not the raw provider field.

Pre-fix behaviour:
    _request_code_response sets task.supports_tool_calls from
    response.function_calls alone. A JSON-only response has
    function_calls == None and is recorded as having emitted no
    tool calls, even though parse_tool_blocks parsed it successfully.

Post-fix behaviour:
    _execute sets task.supports_tool_calls from the parsed tool_calls
    list — single source of truth (DOCTRINE rule 12). Native, raw JSON,
    and fenced JSON all score as tool calls.

The two BUG fixtures (test_raw_json_with_no_native_call_is_scored_as_tool_call
and test_fenced_json_with_no_native_call_is_scored_as_tool_call) MUST FAIL
on pre-fix code with `task.supports_tool_calls is False` and pass on
post-fix code with `task.supports_tool_calls is True`.

The two NEGATIVE fixtures (test_prose_with_no_action_is_scored_as_no_tool_call
and test_malformed_json_no_tool_call_and_raw_text_persisted) MUST FAIL FOR
THE RIGHT REASON on pre-fix code if they fail at all:
  - prose fixture fails pre-fix because supports_tool_calls=False (correctly),
    even though the buggy scorer would have set False too — so this one
    passes both pre- and post-fix.
  - malformed fixture asserts (a) supports_tool_calls is False and
    (b) the raw text is persisted on the task (F2 invariant). Pre-fix
    code has no persistence helpers, so the F2 assertion fails on
    pre-fix code for the right reason (raw text not captured) — this
    is the FIX-driven negative, not the F1-driven negative.
"""

import asyncio
import json

from app.services.max import ai_router as ai_router_module
from app.services.max import code_task_runner as runner_module
from app.services.max import tool_executor as tool_executor_module
from app.services.max.code_task_runner import (
    AIModel,
    CodeTask,
    CodeTaskState,
    _select_code_model,
)
from app.services.max.desks import desk_manager as desk_manager_module
from app.services.max.tool_executor import ToolResult


class _FakeAIResponse:
    """Shape that matches the AIResponse dataclass used by _request_code_response."""

    def __init__(self, content="", model_used="minimax/MiniMax-M3", function_calls=None):
        self.content = content
        self.model_used = model_used
        self.function_calls = function_calls


def _patch_runner(monkeypatch, response):
    """Patch ai_router.chat so the REAL _request_code_response runs (the
    buggy line 423 / the new assignment in _execute is exercised) and
    execute_tool so tool calls become no-ops that report success.

    desk_manager is stubbed so we never need a real CodeForge desk.

    _select_code_model is forced to return (MINIMAX, "openclaw", False) so
    supports_native_tools is False. The F1 bug only manifests when
    supports_native_tools is False — for Grok (supports_native_tools=True)
    the buggy line accidentally returns True for JSON-only responses. In
    production the configured provider is MiniMax with
    supports_native_tools=False; this fixture must match that shape or
    the bug will not reproduce.
    """

    async def fake_chat(*args, **kwargs):
        return response

    def fake_select_code_model():
        return (AIModel.MINIMAX, "openclaw", False)

    monkeypatch.setattr(runner_module, "_select_code_model", fake_select_code_model)
    monkeypatch.setattr(ai_router_module.ai_router, "chat", fake_chat)
    monkeypatch.setattr(desk_manager_module.desk_manager, "initialize", lambda: None)
    monkeypatch.setattr(desk_manager_module.desk_manager, "get_desk", lambda name: object())

    def fake_execute_tool(tool_call, desk=None, **kwargs):
        return ToolResult(
            tool=tool_call.get("tool", "unknown"),
            success=True,
            result={"path": tool_call.get("path")},
        )

    monkeypatch.setattr(tool_executor_module, "execute_tool", fake_execute_tool)


# ── Fixture 1: native function_call (positive — should always pass) ──


def test_native_function_call_scored_as_tool_call(monkeypatch):
    """A response that arrives as response.function_calls with a native
    tool call must score as having emitted an executable action.

    Provider shape: OpenAI/Anthropic-style native function_calls payload.
    """
    response = _FakeAIResponse(
        content="ignored (the model may also include prose alongside native calls)",
        function_calls=[{"tool": "file_read", "path": "backend/app/main.py"}],
    )
    _patch_runner(monkeypatch, response)
    task = CodeTask(
        id="ct-f1-native",
        prompt="Inspect backend/app/main.py. Do not edit files.",
        execution_mode="read_only",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert task.supports_tool_calls is True, (
        "Native function_calls present must score as tool call"
    )
    assert task.state == CodeTaskState.COMPLETED
    assert task.executed_tool_calls[0]["tool"] == "file_read"


# ── Fixture 2: raw JSON with no native call ── THE F1 BUG ──


def test_raw_json_with_no_native_call_is_scored_as_tool_call(monkeypatch):
    """A response that arrives as raw JSON `{tool:..., args:{...}}` with
    no native function_calls must still score as having emitted an
    executable action.

    Provider shape: MiniMax and similar providers that emit the protocol's
    format 2 directly, not as native function_calls.

    TRIPS CONDITION: response.function_calls is None, but parse_tool_blocks
    returns a non-empty list. Pre-fix code records supports_tool_calls=False
    (the bug). Post-fix code records True (the parsed result).
    """
    response = _FakeAIResponse(
        content=json.dumps({
            "tool": "file_read",
            "args": {"path": "backend/app/main.py"},
        }),
        function_calls=None,
    )
    _patch_runner(monkeypatch, response)
    task = CodeTask(
        id="ct-f1-raw-json",
        prompt="Inspect backend/app/main.py. Do not edit files.",
        execution_mode="read_only",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert task.supports_tool_calls is True, (
        "F1 BUG: scorer recorded raw-JSON-only response as having emitted "
        "no tool calls. Pre-fix code_task_runner.py:399 read "
        "response.function_calls (None) and ignored parse_tool_blocks output."
    )
    assert task.state == CodeTaskState.COMPLETED
    assert task.executed_tool_calls[0]["tool"] == "file_read"


# ── Fixture 3: fenced JSON block with no native call ── THE F1 BUG ──


def test_fenced_json_with_no_native_call_is_scored_as_tool_call(monkeypatch):
    """A response that arrives as a fenced ```json block with no native
    function_calls must still score as having emitted an executable
    action.

    Provider shape: models that prefer fenced JSON blocks (e.g. some
    Ollama / OpenClaw shapes).

    TRIPS CONDITION: identical to the raw-JSON fixture — only the native
    field is read pre-fix, the parsed result is ignored.
    """
    response = _FakeAIResponse(
        content=(
            '```json\n'
            '{"tool":"file_read","args":{"path":"backend/app/main.py"}}\n'
            '```'
        ),
        function_calls=None,
    )
    _patch_runner(monkeypatch, response)
    task = CodeTask(
        id="ct-f1-fenced-json",
        prompt="Inspect backend/app/main.py. Do not edit files.",
        execution_mode="read_only",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert task.supports_tool_calls is True, (
        "F1 BUG: scorer recorded fenced-JSON-only response as having "
        "emitted no tool calls. parse_tool_blocks handles this format "
        "(tool_executor.py:175) but the scorer did not consult it."
    )
    assert task.state == CodeTaskState.COMPLETED
    assert task.executed_tool_calls[0]["tool"] == "file_read"


# ── Fixture 4: prose with no action (negative — must pass both pre- and post-fix) ──


def test_prose_with_no_action_is_scored_as_no_tool_call(monkeypatch):
    """A response that is pure prose with no tool action must score as
    having emitted NO tool call.

    TRIPS CONDITION: response.function_calls is None AND parse_tool_blocks
    returns []. The correct score is False. The pre-fix scorer happened
    to score this as False too (because supports_native_tools=False),
    so this fixture is a NEGATIVE that must pass on BOTH pre-fix and
    post-fix code. It exists to prove the fix does not flip a true
    negative into a false positive.
    """
    response = _FakeAIResponse(
        content="## Summary\nI am thinking about it. No action taken.",
        function_calls=None,
    )
    _patch_runner(monkeypatch, response)
    task = CodeTask(
        id="ct-f1-prose",
        # No path, no action verbs. Avoids the local-fallback planner
        # synthesising a file_read from the prompt.
        prompt="Just think. Do not edit files.",
        execution_mode="read_only",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    assert task.supports_tool_calls is False, (
        "Pure prose with no actionable JSON must score as no tool call"
    )
    assert task.state == CodeTaskState.ERROR
    # F2 invariant: the prose content must still be captured on the task
    assert task.last_response_text == response.content
    assert task.last_function_calls_summary == "absent (response.function_calls is None)"


# ── Fixture 5: malformed JSON (negative + F2 persistence) ──


def test_malformed_json_no_tool_call_and_raw_text_persisted(monkeypatch):
    """A response with malformed JSON must score as having emitted NO tool
    call, AND the raw text must be persisted on the task per F2 so a
    later failure path can record what the model actually returned.

    TRIPS CONDITION: response.function_calls is None AND parse_tool_blocks
    fails to parse. The correct score is False (no tool call). The raw
    text is the diagnostic — without F2 persistence the failure would be
    a verdict with no evidence, the same class of bug F2 fixes.

    Pre-fix code passes the supports_tool_calls=False assertion (same as
    the prose fixture) but FAILS the F2 assertion because no capture
    helper existed. Post-fix code passes both.
    """
    response = _FakeAIResponse(
        content='{"tool":"file_read","args":{"path":',  # truncated, unparseable
        function_calls=None,
    )
    _patch_runner(monkeypatch, response)
    task = CodeTask(
        id="ct-f1-malformed",
        prompt="Just respond with broken JSON. Do not edit files.",
        execution_mode="read_only",
    )

    asyncio.run(runner_module.code_task_runner._execute(task))

    # No tool call scored (negative fixture)
    assert task.supports_tool_calls is False
    # F2 invariant: raw text persisted on the task
    assert task.last_response_text == response.content
    assert task.last_function_calls_summary == "absent (response.function_calls is None)"
    assert "matched=False" in (task.last_parse_outcome or "")
    # And the task went to ERROR with populated result (full F2 round-trip)
    assert task.state == CodeTaskState.ERROR
    assert task.result is not None
    assert response.content in task.result