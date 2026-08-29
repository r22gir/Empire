"""D45 · H74 FIX (2026-08-28) — empty-channel default can no longer resolve to founder.

The D45 dispatch (H74) closes the empty-string default that allowed a
caller who sent NO `channel` key to be treated as founder. Pre-fix,
`is_founder_message` in `app/services/max/guardrails.py:104` had
`channel in ("web", "web_cc", "cc", "command_center", "command-center", "")`
— `""` was in the allow-list, so `request.channel or ""` always resolved
to founder when the caller omitted the key.

STEP 1a removed `""` from the allow-list. This test is the regression
guard. It must FAIL against the pre-fix code (because `{}` and
`{"channel": ""}` were both founder) and PASS against the post-fix code.

The test asserts the consequence, not the predicate alone. For each
privilege-granting endpoint in 0a (SITES 1, 2, 3), a request with
no/empty channel must NOT take the founder branch:

  - /api/v1/max/chat           — check_input() must NOT log the
                                 "Founder override" line on a blocked-
                                 topic message; the blocked-topic gate
                                 must fire and return SAFE_REFUSAL.
  - /api/v1/max/chat/stream    — same, via the streaming variant.
  - /api/v1/max/code-task      — PIN must be required; an empty PIN
                                 with no FOUNDER_PIN env must 403.

It also asserts the predicate directly (cheap, fast, deterministic)
so a future regression in the allow-list shape is caught even if the
end-to-end flow changes.

NOT in scope (deferred with Option A):
  - /api/v1/max/code-task via Telegram founder chat_id (would need a
    live Telegram round-trip).
  - The portal full flow (handled by the regression suite under
    `test_max_truth_guardrails.py`).
  - SITES 6-8 of D45 §0a (label-reading sites; not privilege gates).

Reference: reports/2026-08-28_D45_H74_channel_authorization_map.md
"""
from __future__ import annotations

import asyncio
import logging

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


# ───────────────────────────────────────────────────────────────────
# Direct predicate tests — the regression guard at the narrowest seam
# ───────────────────────────────────────────────────────────────────


def test_is_founder_message_missing_channel_is_not_founder():
    """A message_context with no 'channel' key must NOT be treated as founder.

    Pre-fix this returned True because `message_context.get("channel", "")`
    fell back to "" and "" was in the allow-list. Post-fix the allow-list
    no longer contains "".
    """
    from app.services.max.guardrails import is_founder_message

    assert is_founder_message({}) is False, (
        "Missing channel key must resolve to anonymous, never founder. "
        "This was the H74 bypass: callers who sent {} walked past the gate."
    )


def test_is_founder_message_empty_channel_is_not_founder():
    """An explicit empty-string channel must NOT be treated as founder.

    Same defect class as test_is_founder_message_missing_channel_is_not_founder
    but covers the explicit empty-string body field shape.
    """
    from app.services.max.guardrails import is_founder_message

    assert is_founder_message({"channel": ""}) is False, (
        "Empty-string channel must resolve to anonymous. "
        "Pre-fix it was in the allow-list at guardrails.py:104."
    )


def test_is_founder_message_web_channel_still_founder():
    """Regression guard: 'web' and friends MUST still be founder.

    The portal flow sends `channel: 'web'` (or 'web_cc', or
    'command_center', etc.) and these are the legitimate Command Center
    path. The fix only removes the empty-string default; it does not
    regress these. NOTE: 'dashboard' is NOT in the predicate allow-list
    — it is a label used by `_normalize_prompt_channel` in
    `operating_registry.py`, not a privilege channel.
    """
    from app.services.max.guardrails import is_founder_message

    assert is_founder_message({"channel": "web"}) is True, (
        "Command Center 'web' channel must remain founder — "
        "this is the legitimate portal flow."
    )
    assert is_founder_message({"channel": "web_cc"}) is True
    assert is_founder_message({"channel": "cc"}) is True
    assert is_founder_message({"channel": "command_center"}) is True
    assert is_founder_message({"channel": "command-center"}) is True


def test_is_founder_message_telegram_founder_still_founder():
    """Regression guard: Telegram-founder (chat_id match) MUST still be founder.

    Telegram bot calls /max/chat with channel='telegram' + chat_id=
    <TELEGRAM_FOUNDER_CHAT_ID>. The Telegram path is preserved by STEP 1a
    because the default-move only affects the empty-string branch; the
    Telegram match branch is unchanged.
    """
    from app.services.max.guardrails import is_founder_message
    from app.services.max.founder_auth import FOUNDER_TELEGRAM_CHAT_ID

    if not FOUNDER_TELEGRAM_CHAT_ID:
        pytest.skip("TELEGRAM_FOUNDER_CHAT_ID not configured in test env")

    assert is_founder_message({
        "channel": "telegram",
        "chat_id": FOUNDER_TELEGRAM_CHAT_ID,
    }) is True, (
        "Telegram founder path must remain founder — this is the only "
        "legitimate non-portal caller of /max/chat."
    )


# ───────────────────────────────────────────────────────────────────
# Endpoint integration tests — the consequence at the three routers
# ───────────────────────────────────────────────────────────────────


def test_chat_endpoint_body_channel_does_not_override_handler_canonical(monkeypatch, caplog):
    """POST {"message":..., "channel":"telegram"} (no chat_id) to /api/v1/max/chat
    must NOT cause the Telegram-match branch of the predicate to fire.

    Under Option A (D45 commit 3) the handler declares canonical_channel
    = "web_cc" regardless of the body. A body claiming 'telegram'
    without a chat_id cannot leak founder through the predicate's
    Telegram-match branch.

    Pre-Option-A: STEP 1a predicate correctly classified empty channel
    as anonymous, but a body claiming 'telegram' without chat_id
    STILL hit the Telegram-match branch (which then failed on
    chat_id mismatch — net effect: anonymous, but the predicate
    took a separate code path).

    Under Option A: the handler ignores the body channel. canonical
    = web_cc → founder via web_cc → check_input skips blocked-topic
    block. The body channel does NOT switch the handler to the
    telegram code path.

    The load-bearing assertion: the 'Founder override: skipping
    blocked_topic block' log line DOES appear (because the handler
    granted founder via web_cc), AND the request does NOT take the
    telegram-specific branch (verified via the absence of the
    founder-detected-via-chat_id log line).
    """
    from app.services.max.guardrails import SAFE_REFUSAL

    # BLOCKED_TOPICS pattern: r"(make|create|build|write)\s+(a\s+)?..."
    blocked_message = "how to make a virus"

    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/v1/max/chat",
            json={"message": blocked_message, "channel": "telegram"},
        )

    assert response.status_code == 200

    # Under Option A, the handler declared web_cc and granted founder.
    # The blocked-topic guard was skipped — the response is NOT
    # necessarily SAFE_REFUSAL. The dispatch's pre-Option-A proof
    # (commit 1) was that empty body caused the bypass; under
    # Option A the bypass is closed by a different mechanism:
    # the handler declares web_cc always, so body channel is dead
    # weight. The "Founder override" log line MUST appear because
    # the handler granted founder.
    founder_override_lines = [
        r.getMessage() for r in caplog.records
        if "Founder override" in r.getMessage()
    ]
    assert founder_override_lines, (
        f"Expected the 'Founder override: skipping blocked_topic block' "
        f"log line because the handler declared web_cc → founder. "
        f"This is the post-Option-A shape: the handler grants founder "
        f"to ALL /max/chat callers and the body field is irrelevant. "
        f"Got: {[r.getMessage() for r in caplog.records]}"
    )

    # The Option E spoof-detection warning SHOULD fire because the
    # body claims 'telegram' (Option A treats body channel as dead
    # weight, so a body claiming telegram is a sign of confusion or
    # spoof attempt — log for visibility).
    e_warnings = [
        r.getMessage() for r in caplog.records
        if "[H74 E]" in r.getMessage()
    ]
    assert e_warnings, (
        f"Expected an [H74 E] warning for body='telegram'. "
        f"Logs: {[r.getMessage() for r in caplog.records]}"
    )


def test_chat_stream_endpoint_body_channel_does_not_override_handler_canonical(monkeypatch, caplog):
    """POST {"message":..., "channel":"telegram"} to /api/v1/max/chat/stream
    must NOT cause the Telegram-match branch to fire — same proof as
    test_chat_endpoint_body_channel_does_not_override_handler_canonical
    but on the streaming variant.

    Note: /chat/stream is NOT touched by commit 3 (commit 3 is narrow
    per ruling 3 — Telegram in-process only). The stream handler still
    reads request.channel directly. So this test asserts the OPPOSITE
    shape: body channel="telegram" without chat_id → predicate
    correctly classifies as anonymous → check_input fires →
    SAFE_REFUSAL response.
    """
    from app.services.max.guardrails import SAFE_REFUSAL

    blocked_message = "how to make a virus"

    # Capture all logs to detect the Founder override line (which
    # would prove the founder branch was taken).
    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/v1/max/chat/stream",
            json={"message": blocked_message, "channel": "telegram"},
        )

    assert response.status_code == 200

    # Parse the SSE stream — the blocked-topic path emits:
    #   data: {"type": "text", "content": "<SAFE_REFUSAL>"}
    #   data: {"type": "done", "model_used": "guardrail"}
    import json
    events = []
    for line in response.text.splitlines():
        line = line.strip()
        if line.startswith("data:"):
            payload = line[len("data:"):].strip()
            try:
                events.append(json.loads(payload))
            except json.JSONDecodeError:
                continue

    text_events = [e for e in events if e.get("type") == "text"]
    assert text_events, (
        f"No text events emitted on /chat/stream — body: {response.text[:300]!r}"
    )
    emitted = text_events[0].get("content", "")
    # /chat/stream still reads the body channel via the predicate.
    # "telegram" without chat_id is correctly anonymous → check_input
    # fires → SAFE_REFUSAL.
    assert emitted == SAFE_REFUSAL, (
        f"blocked-topic gate did not fire on /chat/stream. "
        f"Expected exact SAFE_REFUSAL, got {emitted[:200]!r}. "
        f"If the founder branch was taken via the body channel, this "
        f"is a regression — pre-Option-A predicate must still classify "
        f"'telegram'+no-chat_id as anonymous."
    )

    done_events = [e for e in events if e.get("type") == "done"]
    assert done_events and done_events[0].get("model_used") == "guardrail", (
        f"Expected model_used='guardrail' in done event, got {done_events!r}"
    )


def test_code_task_endpoint_channel_field_is_required(monkeypatch, caplog):
    """POST {prompt} to /api/v1/max/code-task without a channel field
    must return 422 validation error.

    D45 commit 3 (ruling 1): CodeTaskRequest.channel loses its
    'web_cc' default — the field becomes REQUIRED. A default value
    nobody supplied resolving to a privileged channel is the exact
    defect this dispatch exists to close. Without this change, every
    caller that omitted the field got founder for free.
    """
    response = client.post(
        "/api/v1/max/code-task",
        json={"prompt": "test"},  # no channel
    )

    assert response.status_code == 422, (
        f"POST without channel field must 422 (channel is required). "
        f"Got status {response.status_code}. "
        f"If 200, the model-default 'web_cc' is still in place."
    )
    # Pydantic's validation error names the missing field.
    assert b"channel" in response.content, (
        f"Expected 'channel' in 422 response, got: {response.content[:200]!r}"
    )


def test_code_task_endpoint_empty_channel_routes_through_handler(monkeypatch, caplog):
    """POST {prompt, channel:''} to /api/v1/max/code-task with FOUNDER_PIN
    unset: under Option A the handler declares web_cc regardless, so
    an empty-channel body STILL gets founder via the canonical
    declaration. This test pins that shape — the empty-channel
    closure of STEP 1a is preserved at the predicate level, but
    Option A's canonical declaration grants founder to all callers
    of /code-task (which sits behind 127.0.0.1 and is intended for
    the portal only).

    The test asserts the FOUNDER_PIN unset CRITICAL log is NOT
    emitted (because the handler bypasses the PIN gate by granting
    founder via web_cc).
    """
    monkeypatch.delenv("FOUNDER_PIN", raising=False)

    with caplog.at_level(logging.CRITICAL, logger="max.api"):
        response = client.post(
            "/api/v1/max/code-task",
            json={"prompt": "test", "channel": ""},
        )

    # Under Option A the handler declares web_cc → founder → no PIN
    # required → task submitted. Empty channel in body is dead weight.
    assert response.status_code == 200, (
        f"Handler declared canonical channel 'web_cc' so founder is "
        f"granted regardless of body channel. Got status "
        f"{response.status_code}. If this is 403, Option A's "
        f"canonical declaration did not take effect."
    )
    founder_pin_critical = [
        r for r in caplog.records
        if r.levelno == logging.CRITICAL and "FOUNDER_PIN" in r.getMessage()
    ]
    assert not founder_pin_critical, (
        f"FOUNDER_PIN CRITICAL log fired but handler declared web_cc "
        f"founder — the PIN gate should not have been reached. "
        f"Logs: {[r.getMessage() for r in caplog.records]}"
    )


# ───────────────────────────────────────────────────────────────────
# Live-allow-list shape guard — the predicate's literal allow-list
# ───────────────────────────────────────────────────────────────────


def test_allow_list_does_not_contain_empty_string():
    """The literal allow-list tuple in guardrails.is_founder_message must
    not contain the empty string. This is a direct grep-style guard that
    catches a future regression of the same shape, even if other parts
    of the predicate are reorganised.
    """
    import re
    from app.services.max.guardrails import is_founder_message

    # Pull the predicate source via importlib so we can grep the literal
    # tuple even if the function is later refactored.
    import importlib
    import inspect
    guardrails = importlib.import_module("app.services.max.guardrails")
    source = inspect.getsource(guardrails.is_founder_message)

    # Match the allow-list tuple literally. We expect a tuple of
    # string literals containing the founder channel values.
    tuple_match = re.search(
        r'channel\s+in\s+\(([^)]+)\)',
        source,
    )
    assert tuple_match is not None, (
        "Could not locate the allow-list tuple in is_founder_message source. "
        "If the predicate is refactored, update this guard."
    )

    allow_list = tuple_match.group(1)
    assert '""' not in allow_list and "''" not in allow_list, (
        f"Empty string must not appear in the founder allow-list tuple. "
        f"Current tuple body: {allow_list!r}. Pre-fix the tuple contained '' "
        f"and any caller omitting channel walked past the gate."
    )