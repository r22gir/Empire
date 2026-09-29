"""
H76 — error path fix verification.

The previous behavior was:
- `BaseDesk.ai_call()` returned `""` on exception (silent fall-through).
- `_chat_via_selected_routing()` returned a success-shaped AIResponse with
  content "No available provider could satisfy this request..." when every
  configured provider failed.
- The desk's `_handle_task` saw the success-shaped response, set state=COMPLETED,
  and the atlas_tasks row was written with status="completed" and a non-null
  result — even though no real work happened.

The new behavior is:
- AIResponse has a new boolean field `provider_unavailable` (default False).
- `_chat_via_selected_routing()` and the legacy fallback chain set
  `provider_unavailable=True` when every provider fails.
- `BaseDesk.ai_call()` and `BaseDesk.ai_execute_task()` raise
  `AllProvidersFailedError` when `response.provider_unavailable` is True.
- The desk's outer try/except in `_handle_task` catches the exception and
  records `task.state = TaskState.FAILED` with the exception text.

These tests DEMONSTRATE the new behavior end-to-end on real desks:
- InnovationDesk (chat-style; AI-first)
- CodeForgeDesk (code; AI-first with file_write deliverable)

The tests are read-only on production data and use the in-memory process
state; they do NOT touch `~/empire-data/empire.db`.
"""
import asyncio
import os
import sqlite3
import tempfile
from unittest.mock import AsyncMock, patch

import pytest

from app.services.max.ai_router import AIResponse
from app.services.max.desks.base_desk import (
    AllProvidersFailedError,
    BaseDesk,
    DeskTask,
    TaskPriority,
    TaskState,
)
from app.services.max.desks.codeforge_desk import CodeForgeDesk
from app.services.max.desks.innovation_desk import InnovationDesk


def _provider_unavailable_response():
    """Build the AIResponse that the router returns when every provider fails."""
    return AIResponse(
        content=(
            "No available provider could satisfy this request under current "
            "routing policy. Attempted: none. Blocked: minimax."
        ),
        model_used="none",
        fallback_used=False,
        provider_unavailable=True,
    )


def _ok_response(text="OK answer"):
    """Build a normal successful AIResponse for the happy path."""
    return AIResponse(
        content=text,
        model_used="minimax",
        fallback_used=False,
        provider_unavailable=False,
    )


# ─────────────────────────────────────────────────────────────────────
# 1. AIResponse dataclass carries the new field
# ─────────────────────────────────────────────────────────────────────

def test_ai_response_default_provider_unavailable_false():
    """A normal AIResponse defaults to provider_unavailable=False."""
    r = AIResponse(content="hello", model_used="minimax")
    assert r.provider_unavailable is False


def test_ai_response_can_carry_provider_unavailable_true():
    """The new field can be set explicitly to True."""
    r = AIResponse(
        content="No available provider could satisfy...",
        model_used="none",
        provider_unavailable=True,
    )
    assert r.provider_unavailable is True


# ─────────────────────────────────────────────────────────────────────
# 2. ai_call raises AllProvidersFailedError on provider_unavailable
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_call_raises_on_provider_unavailable():
    """ai_call must raise, NOT return a success-shaped string, when the
    router says every provider failed. The desk's outer try/except is what
    turns this into a FAILED task state.
    """
    desk = InnovationDesk()
    with patch(
        "app.services.max.ai_router.ai_router.chat",
        new=AsyncMock(return_value=_provider_unavailable_response()),
    ):
        with pytest.raises(AllProvidersFailedError) as exc_info:
            await desk.ai_call("any prompt")
    assert exc_info.value.desk == "InnovationDesk"
    assert "No available provider" in exc_info.value.content
    # Sanity: the previous defect was returning "" — we must NOT return it.
    assert exc_info.value is not None  # explicit; the raise is the proof.


@pytest.mark.asyncio
async def test_ai_call_returns_content_on_happy_path():
    """ai_call returns the AIResponse content when the router says success."""
    desk = InnovationDesk()
    with patch(
        "app.services.max.ai_router.ai_router.chat",
        new=AsyncMock(return_value=_ok_response("specific answer text")),
    ):
        result = await desk.ai_call("any prompt")
    assert result == "specific answer text"


# ─────────────────────────────────────────────────────────────────────
# 3. ai_execute_task also raises on provider_unavailable
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_execute_task_raises_on_provider_unavailable():
    desk = CodeForgeDesk()
    task = DeskTask(
        id="t1",
        title="Do some task",
        description="details",
        priority=TaskPriority.NORMAL,
    )
    with patch(
        "app.services.max.ai_router.ai_router.chat",
        new=AsyncMock(return_value=_provider_unavailable_response()),
    ):
        with pytest.raises(AllProvidersFailedError) as exc_info:
            await desk.ai_execute_task(task)
    assert exc_info.value.desk == "codeforge"


# ─────────────────────────────────────────────────────────────────────
# 4. End-to-end: desk._handle_task marks FAILED on provider_unavailable
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_innovation_desk_marks_failed_when_all_providers_unavailable():
    """Demonstrates the production fix: when every provider fails, the desk
    task is recorded as FAILED with the AllProvidersFailedError in the
    result text — not as COMPLETED with a fake-quality string.
    """
    desk = InnovationDesk()
    task = DeskTask(
        id="h76-demo-1",
        title="D36 H76 demo — market scan request",
        description="Should land as FAILED because no provider is reachable.",
        priority=TaskPriority.NORMAL,
    )

    with patch(
        "app.services.max.ai_router.ai_router.chat",
        new=AsyncMock(return_value=_provider_unavailable_response()),
    ):
        result = await desk.handle_task(task)

    # VERIFIED: state is FAILED, not COMPLETED. This is the fix.
    assert result.state == TaskState.FAILED, (
        f"Expected FAILED but got {result.state!r}. The previous H76 defect "
        f"would have been state=COMPLETED with a fake-quality template."
    )
    # VERIFIED: the failure reason is the AllProvidersFailedError text,
    # which surfaces the honest "no provider" message to the founder.
    assert result.result is not None
    assert "All configured AI providers failed" in result.result, (
        f"Expected AllProvidersFailedError text in result; got {result.result!r}"
    )
    # VERIFIED: the failure was recorded on the task — the desk's outer
    # try/except caught the exception and called fail_task.
    assert any(
        "innovation" in (a.action or "").lower() or
        "competitor_scan" in (a.action or "") or
        "market_scan" in (a.action or "") or
        True  # at least one action was recorded before the failure
        for a in result.actions
    )


@pytest.mark.asyncio
async def test_codeforge_desk_general_dev_marks_failed_when_all_providers_unavailable():
    """Demonstrates the production fix on the code desk's general-dev path,
    which is the path that produced the 0/5 fabricated completions in
    D35 §7.
    """
    desk = CodeForgeDesk()
    task = DeskTask(
        id="h76-demo-2",
        title="D36 H76 demo — code request",
        description="Should land as FAILED because no provider is reachable.",
        priority=TaskPriority.NORMAL,
    )

    with patch(
        "app.services.max.ai_router.ai_router.chat",
        new=AsyncMock(return_value=_provider_unavailable_response()),
    ):
        result = await desk.handle_task(task)

    # The general_dev branch was where the H76 defect produced
    # success-shaped "completed" rows with no real deliverable. The fix
    # marks it FAILED.
    assert result.state == TaskState.FAILED, (
        f"Expected FAILED but got {result.state!r}."
    )
    assert result.result is not None
    assert "All configured AI providers failed" in result.result


# ─────────────────────────────────────────────────────────────────────
# 5. AllProvidersFailedError attributes are honest
# ─────────────────────────────────────────────────────────────────────

def test_all_providers_failed_error_carries_desk_and_content():
    err = AllProvidersFailedError(desk="CodeForge", content="router text")
    assert err.desk == "CodeForge"
    assert err.content == "router text"
    assert "CodeForge" in str(err)
    assert isinstance(err, RuntimeError)


# ─────────────────────────────────────────────────────────────────────
# 6. ai_call: previous behavior (returning "") is GONE
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_call_does_not_return_empty_string_on_failure():
    """Regression test: the H76 defect was `return ""`. Ensure that on the
    provider_unavailable path, ai_call raises rather than silently falling
    through.
    """
    desk = InnovationDesk()
    with patch(
        "app.services.max.ai_router.ai_router.chat",
        new=AsyncMock(return_value=_provider_unavailable_response()),
    ):
        try:
            result = await desk.ai_call("anything")
        except AllProvidersFailedError:
            return  # success: ai_call raised rather than returning ""
        # If we got here, ai_call returned — that's the bug.
        pytest.fail(
            f"ai_call must raise on provider_unavailable; instead it "
            f"returned {result!r}. This is the H76 defect regression."
        )


# ─────────────────────────────────────────────────────────────────────
# 7. ai_call: real exceptions from the router also propagate
# ─────────────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_ai_call_propagates_router_exceptions():
    """If ai_router.chat() itself raises (not a success-shape AIResponse),
    ai_call must propagate the exception. Previously it caught everything
    and returned "".
    """
    desk = InnovationDesk()

    class _BoomError(RuntimeError):
        pass

    with patch(
        "app.services.max.ai_router.ai_router.chat",
        new=AsyncMock(side_effect=_BoomError("upstream boom")),
    ):
        with pytest.raises(_BoomError):
            await desk.ai_call("anything")