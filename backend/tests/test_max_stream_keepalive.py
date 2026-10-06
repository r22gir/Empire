"""2026-10-06 Marleys screenshot drop: /max/chat/stream must send headers and
heartbeats right away (no silent ~19 s before the first byte), report failures
as plain-words ``error`` events, and never feed the UI's own error notice
back to the model as an assistant turn."""
import asyncio
import json

from fastapi.responses import StreamingResponse

import importlib

r = importlib.import_module("app.routers.max.router")


def _events(chunks):
    out = []
    for c in chunks:
        for line in str(c).split("\n"):
            if line.startswith("data: "):
                out.append(json.loads(line[6:]))
    return out


async def _collect(agen):
    got = []
    async for c in agen:
        got.append(c)
    return got


def _req(**kw):
    base = {"message": "Preparare an answer for marleys", "channel": "dashboard"}
    base.update(kw)
    return r.ChatRequest(**base)


def test_heartbeats_flow_while_reply_is_prepared(monkeypatch):
    monkeypatch.setattr(r, "_STREAM_PREP_HEARTBEAT_S", 0.05)

    async def slow_prepare():
        await asyncio.sleep(0.3)

        async def gen():
            yield 'data: {"type": "text", "content": "Hi Marley"}\n\n'
            yield 'data: {"type": "done", "model_used": "fake"}\n\n'
        return StreamingResponse(gen(), media_type="text/event-stream")

    ev = _events(asyncio.run(_collect(r._keepalive_stream(slow_prepare))))
    assert ev[0] == {"type": "heartbeat", "phase": "start"}
    assert sum(1 for e in ev if e.get("phase") == "prepare") >= 3
    assert [e["type"] for e in ev[-2:]] == ["text", "done"]
    assert ev[-2]["content"] == "Hi Marley"


def test_preparation_error_is_reported_in_plain_words():
    async def broken():
        raise RuntimeError("vision provider 500")

    ev = _events(asyncio.run(_collect(r._keepalive_stream(broken))))
    err = [e for e in ev if e["type"] == "error"]
    assert err and "server is up" in err[0]["content"]
    assert "RuntimeError" in err[0]["content"]
    assert ev[-1]["type"] == "done"


def test_mid_stream_exception_becomes_error_event():
    async def prepare():
        async def gen():
            yield 'data: {"type": "text", "content": "partial"}\n\n'
            raise ValueError("boom")
        return StreamingResponse(gen(), media_type="text/event-stream")

    ev = _events(asyncio.run(_collect(r._keepalive_stream(prepare))))
    assert ev[1]["content"] == "partial"
    assert any(e["type"] == "error" and "mid-reply" in e["content"] for e in ev)


def test_ui_error_placeholders_are_not_replayed():
    hist = [
        {"role": "user", "content": "Preparare an answer for marleys"},
        {"role": "assistant", "content": "**Connection error.** Backend may be offline."},
        {"role": "user", "content": "And this one"},
        {"role": "assistant", "content": "**Connection dropped.** The server is up."},
        {"role": "assistant", "content": "Here is the draft for Marley."},
    ]
    kept = r._drop_ui_error_turns(hist)
    assert [h["content"] for h in kept] == [
        "Preparare an answer for marleys", "And this one", "Here is the draft for Marley.",
    ]


def test_endpoint_returns_stream_at_once_and_strips_placeholder(monkeypatch):
    monkeypatch.setattr(r, "_STREAM_PREP_HEARTBEAT_S", 0.05)
    seen = {}

    async def fake_impl(request):
        seen["history"] = list(request.history)
        await asyncio.sleep(0.2)

        async def gen():
            yield 'data: {"type": "text", "content": "ok"}\n\n'
            yield 'data: {"type": "done", "model_used": "fake", "conversation_id": "c-test"}\n\n'
        return StreamingResponse(gen(), media_type="text/event-stream")

    monkeypatch.setattr(r, "_chat_stream_impl", fake_impl)
    req = _req(history=[
        {"role": "user", "content": "x"},
        {"role": "assistant", "content": "**Connection error.** Backend may be offline."},
    ])

    async def run():
        loop = asyncio.get_running_loop()
        t0 = loop.time()
        resp = await r.chat_stream(req, None)
        returned_after = loop.time() - t0
        chunks = await _collect(resp.body_iterator)
        return resp, returned_after, chunks

    resp, returned_after, chunks = asyncio.run(run())
    assert isinstance(resp, StreamingResponse)
    assert returned_after < 0.1  # headers no longer wait for preparation
    ev = _events(chunks)
    assert ev[0]["type"] == "heartbeat"
    assert ev[-1]["type"] == "done"
    assert seen["history"] == [{"role": "user", "content": "x"}]
