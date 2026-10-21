"""Hotfix: streamed chat UnboundLocalError on `messages`.

`_chat_stream_impl`'s inner `event_generator()` reads the outer `messages`
list, then later reassigns it (`apply_photo_context` / `inject_vision_context`).
Without `nonlocal messages`, Python treats the name as local for the whole
generator and every streamed turn raises:

    cannot access local variable 'messages' where it is not associated with a value

This test streams one chat turn with a mocked model (no network) and asserts
a reply chunk is yielded with no error event.
"""
from __future__ import annotations

import asyncio
import importlib
import json
from types import SimpleNamespace

def _events(chunks):
    out = []
    for chunk in chunks:
        for line in str(chunk).split("\n"):
            if line.startswith("data: "):
                out.append(json.loads(line[6:]))
    return out


async def _collect(agen):
    got = []
    async for chunk in agen:
        got.append(chunk)
    return got


def test_chat_stream_one_turn_yields_reply_without_messages_unbound(monkeypatch):
    r = importlib.import_module("app.routers.max.router")

    reply = "STREAM_OK_42."

    async def fake_chat_stream(*_args, **_kwargs):
        yield (reply, "mock-model")

    async def fake_chat(*_args, **_kwargs):
        return SimpleNamespace(content=reply, model_used="mock-model")

    async def fake_prompt(*_args, **_kwargs):
        return "You are MAX."

    async def fake_none(*_args, **_kwargs):
        return None

    async def fake_prelookups(*_args, **_kwargs):
        return [], ""

    def _no_live(*_args, **_kwargs):
        raise AssertionError("no live tool, send, or network calls in this test")

    monkeypatch.setattr(r.ai_router, "chat_stream", fake_chat_stream)
    monkeypatch.setattr(r.ai_router, "chat", fake_chat)
    monkeypatch.setattr(r, "get_system_prompt_with_brain", fake_prompt)
    monkeypatch.setattr(r, "_run_prelookups", fake_prelookups)
    monkeypatch.setattr(r, "_link_intelligence_response", fake_none)
    monkeypatch.setattr(r, "_maybe_delegate_first_response", fake_none)
    monkeypatch.setattr(r, "_maybe_handle_direct_route_request", lambda *_a, **_k: None)
    monkeypatch.setattr(r, "_maybe_handle_quoteiq_request", lambda *_a, **_k: None)
    monkeypatch.setattr(r, "_maybe_handle_gpu_safety_request", lambda *_a, **_k: None)
    monkeypatch.setattr(r, "_is_local_finance_readiness_request", lambda *_a, **_k: False)
    monkeypatch.setattr(r, "is_factual_question", lambda *_a, **_k: False)
    monkeypatch.setattr(r, "_is_performative_web_search_request", lambda *_a, **_k: False)
    monkeypatch.setattr(r, "is_self_status_question", lambda *_a, **_k: False)
    monkeypatch.setattr(r, "should_run_whats_new_summary", lambda *_a, **_k: False)
    monkeypatch.setattr(r, "should_force_runtime_truth_check", lambda *_a, **_k: False)
    monkeypatch.setattr(r, "should_clarify_inventory_request", lambda *_a, **_k: False)
    monkeypatch.setattr(r, "needs_continuation", lambda *_a, **_k: False)
    monkeypatch.setattr(r.answer_policy, "should_pre_search", lambda *_a, **_k: False)
    monkeypatch.setattr(r.token_tracker, "should_switch_to_local", lambda: False)
    monkeypatch.setattr(
        r,
        "should_force_founder_action_continuation",
        lambda *_a, **_k: (False, []),
    )
    monkeypatch.setattr(r, "execute_tool", _no_live)
    monkeypatch.setattr(
        r,
        "build_drawing_handoff",
        lambda *_a, **_k: SimpleNamespace(
            is_drawing_intent=False,
            ready=False,
            missing=[],
            intent_mode="unknown",
        ),
    )

    request = r.ChatRequest(
        message="Repeat this token exactly: STREAM_OK_42",
        history=[],
        channel="web",
        conversation_id="stream-messages-unbound",
    )

    async def _run():
        resp = await r._chat_stream_impl(request)
        return _events(await _collect(resp.body_iterator))

    events = asyncio.run(_run())

    errors = [e for e in events if e.get("type") == "error"]
    assert not errors, f"stream must not emit an error event: {errors}"

    texts = [e.get("content", "") for e in events if e.get("type") == "text"]
    assert texts, f"expected a reply chunk; events={[e.get('type') for e in events]}"
    assert any(reply in (t or "") for t in texts), f"reply chunk missing {reply!r}: {texts}"
    assert not any("cannot access local variable 'messages'" in (t or "") for t in texts)
    assert any(e.get("type") == "done" for e in events)
