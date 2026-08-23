"""PHASE 2 · R12 corrected Option A — continuation-guard tests.

The founder reports MAX freezing whenever the drawing tool or
router is invoked. Probe L (T1 "draw me a bench" → T2 "96 wide
22 deep 18 seat 34 back") takes 13 s on the live backend
because the L2 message fails is_drawing_intent and the LLM tool
loop retries sketch_to_drawing 2-3× on text+dims refusal.

The continuation guard (`looks_like_continuation` in
drawing_pending.py) reads the last few assistant turns in chat
history. If the most recent drawing-router turn was a
missing-keys response AND the current message looks like a
continuation reply (via `is_continuation_reply`), the chat/stream
handler routes directly to `_drawing_render` without invoking
the LLM. Probes drop from 13 s to <200 ms.

These tests pin the behavior at both endpoints using TestClient
+ the in-process FastAPI app. The pending-table path is left
untouched (dead architecture, retirement is its own round) per
the dispatch.
"""
from __future__ import annotations

import time

from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def _post_chat(message, history=None, conversation_id=None):
    payload = {"message": message, "channel": "web"}
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    if history is not None:
        payload["history"] = history
    t0 = time.time()
    r = client.post("/api/v1/max/chat", json=payload)
    elapsed = time.time() - t0
    body = r.json() if r.headers.get("content-type", "").startswith(
        "application/json"
    ) else r.text
    return r.status_code, body, elapsed


def _post_chat_stream(message, history=None, conversation_id=None):
    import json
    payload = {"message": message, "channel": "web"}
    if conversation_id is not None:
        payload["conversation_id"] = conversation_id
    if history is not None:
        payload["history"] = history
    t0 = time.time()
    r = client.post("/api/v1/max/chat/stream", json=payload)
    elapsed = time.time() - t0
    events = []
    for chunk in r.text.strip().split("\n\n"):
        chunk = chunk.strip()
        if chunk.startswith("data: "):
            try:
                events.append(json.loads(chunk[6:]))
            except Exception:
                pass
    return r.status_code, events, elapsed


# ──────────────────────────────────────────────────────────────────────
# Probe L (continuation reply that supplies the missing dims)
# ──────────────────────────────────────────────────────────────────────


class TestProbeLChatEndpoint:
    """L T1 missing-keys response → L T2 pure-dim continuation.
    The T2 reply must route through drawing-router in <200 ms."""

    def test_l_t1_missing_keys_response(self):
        s, b, t = _post_chat(
            "draw me a flat roman shade", conversation_id="r12_l"
        )
        assert s == 200
        assert b["model_used"] == "drawing-router"
        # The missing-keys response carries the canonical phrase the
        # continuation guard parses.
        assert "still missing" in b["response"].lower()

    def test_l_t2_continuation_under_200ms(self):
        """The dispatch's acceptance criterion for the corrected
        Option A: a pure-dim second turn must render under
        drawing-router in <200 ms."""
        # Establish history from T1.
        s, b, _ = _post_chat(
            "draw me a flat roman shade", conversation_id="r12_l"
        )
        assert s == 200
        history = [
            {"role": "user", "content": "draw me a flat roman shade"},
            {"role": "assistant", "content": b["response"]},
        ]
        s, b, t = _post_chat(
            "38 wide 64 long",
            history=history,
            conversation_id="r12_l",
        )
        assert s == 200
        assert t < 0.2, f"L T2 should be <200 ms, was {t:.3f} s"
        assert b["model_used"] == "drawing-router", (
            f"expected drawing-router, got {b.get('model_used')!r}"
        )
        # The tool_result should carry the rendered PDF.
        tool_results = b.get("tool_results") or []
        tool_names = [r.get("tool") for r in tool_results]
        assert "render_shop_drawing" in tool_names, (
            f"expected render_shop_drawing tool_result, got {tool_names!r}"
        )

    def test_l_t2_no_history_falls_through(self):
        """The same dims message without history falls through
        (no continuation context). The continuation guard must
        NOT fire on bare dims."""
        s, b, _ = _post_chat("38 wide 64 long")
        assert s == 200
        # We don't pin model_used here — the LLM may or may not be
        # invoked depending on provider config in the test env.
        # The only invariant is: NOT a drawing-router render of the
        # flat_fold product (because the continuation guard must
        # require history).
        # Negative: a 13-second sketch_to_drawing retry loop would
        # still match this expectation, but the guard was already
        # unit-tested via the pure function in
        # test_drawing_pending_helpers if added separately.
        assert b.get("model_used") != "drawing-router" or (
            "render_shop_drawing" not in [
                r.get("tool") for r in (b.get("tool_results") or [])
            ]
        )


class TestProbeLStreamEndpoint:
    """Same scenario via /chat/stream. SSE events must end with
    done.model_used == drawing-router."""

    def test_l_t2_stream_under_200ms(self):
        # Establish history from a /chat turn (same conv_id).
        s, b, _ = _post_chat(
            "draw me a flat roman shade", conversation_id="r12_l_stream"
        )
        assert s == 200
        history = [
            {"role": "user", "content": "draw me a flat roman shade"},
            {"role": "assistant", "content": b["response"]},
        ]
        s, events, t = _post_chat_stream(
            "38 wide 64 long",
            history=history,
            conversation_id="r12_l_stream",
        )
        assert s == 200
        assert t < 0.2, f"stream L T2 should be <200 ms, was {t:.3f} s"
        done = next((e for e in events if e.get("type") == "done"), None)
        assert done is not None, "stream must emit a done event"
        assert done.get("model_used") == "drawing-router"
        # tool_result event with render_shop_drawing must appear.
        tool_events = [
            e for e in events
            if e.get("type") == "tool_result"
            and e.get("tool") == "render_shop_drawing"
        ]
        assert tool_events, (
            f"stream must emit render_shop_drawing tool_result; "
            f"events={[e.get('type') for e in events]}"
        )


# ──────────────────────────────────────────────────────────────────────
# Pure-function unit tests for looks_like_continuation
# ──────────────────────────────────────────────────────────────────────


class TestLooksLikeContinuation:
    """Pure-function unit tests. No FastAPI, no LLM."""

    def test_fires_on_l_t2_with_history(self):
        from app.services.max.drawing_pending import looks_like_continuation
        history = [
            {"role": "user", "content": "draw me a flat roman shade"},
            {"role": "assistant", "content": (
                "I have the 'flat_fold' product_type but I'm still "
                "missing: width, height. Please supply those so I can "
                "render the B1 sheet."
            )},
        ]
        ctx = looks_like_continuation("38 wide 64 long", history)
        assert ctx is not None
        assert ctx["b1_product_type"] == "flat_fold"
        assert ctx["missing_keys"] == ["width", "height"]

    def test_fires_on_bench_with_missing_height_seat_back(self):
        """Probe L T2 with bench-context history fires the guard."""
        from app.services.max.drawing_pending import looks_like_continuation
        history = [
            {"role": "user", "content": "draw me a bench"},
            {"role": "assistant", "content": (
                "I have the 'bench' product_type but I'm still "
                "missing: width, height, depth. Please supply those "
                "so I can render the B1 sheet."
            )},
        ]
        ctx = looks_like_continuation(
            "96 wide 22 deep 18 seat 34 back", history
        )
        assert ctx is not None
        assert ctx["b1_product_type"] == "bench"
        assert ctx["missing_keys"] == ["width", "height", "depth"]

    def test_returns_none_for_empty_history(self):
        from app.services.max.drawing_pending import looks_like_continuation
        assert looks_like_continuation("38 wide 64 long", []) is None
        assert looks_like_continuation("38 wide 64 long", None) is None

    def test_returns_none_for_unrelated_assistant_turn(self):
        from app.services.max.drawing_pending import looks_like_continuation
        history = [{"role": "assistant", "content": "Hello, how can I help?"}]
        assert looks_like_continuation("38 wide 64 long", history) is None

    def test_returns_none_for_non_continuation_text(self):
        from app.services.max.drawing_pending import looks_like_continuation
        history = [{"role": "assistant", "content": (
            "I have the 'flat_fold' product_type but I'm still "
            "missing: width, height."
        )}]
        assert looks_like_continuation(
            "what is the meaning of life", history
        ) is None

    def test_returns_none_when_no_recent_missing_keys_turn(self):
        """If the most recent assistant turn is not a missing-keys
        response (e.g. a successful render), do not pick up an
        older missing-keys turn from the past."""
        from app.services.max.drawing_pending import looks_like_continuation
        history = [
            {"role": "user", "content": "draw me a flat roman shade"},
            {"role": "assistant", "content": (
                "I have the 'flat_fold' product_type but I'm still "
                "missing: width, height."
            )},
            {"role": "user", "content": "38 wide 64 long"},
            {"role": "assistant", "content": (
                "Drawn flat_fold (B1, width=38\", height=64\") → "
                "/home/rg/empire-repo-main/backend/data/drawings/"
                "flat_fold_xyz.pdf"
            )},
        ]
        # Continuation of a *completed* render should NOT fire.
        assert looks_like_continuation(
            "40 wide 60 long", history
        ) is None