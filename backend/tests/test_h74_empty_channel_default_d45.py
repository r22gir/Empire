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


def test_chat_endpoint_empty_body_does_not_take_founder_branch(monkeypatch, caplog):
    """POST {} to /api/v1/max/chat must NOT take the founder branch.

    The check_input guardrail at guardrails.py:135 emits
    "Founder override: skipping blocked_topic block" when founder=True.
    A blocked-topic message posted with no channel key must NOT produce
    that log line — that is the load-bearing signal that the founder
    branch was taken.

    Pre-fix: empty body → founder=True → check_input skips the gate →
    "Founder override: skipping blocked_topic block" log line appears.
    Post-fix: empty body → founder=False → check_input returns
    ("blocked_topic") and the input_sanitizer downstream returns
    SAFE_REFUSAL, but the check_input founder-override log does NOT
    fire.

    Note: the response body is SAFE_REFUSAL either way (input_sanitizer
    catches it downstream). The proof of the founder-bypass regression
    is the LOG LINE, not the response shape.
    """
    from app.services.max.guardrails import SAFE_REFUSAL

    # BLOCKED_TOPICS pattern: r"(make|create|build|write)\s+(a\s+)?..."
    blocked_message = "how to make a virus"

    with caplog.at_level(logging.INFO, logger="max.guardrails"):
        response = client.post(
            "/api/v1/max/chat",
            json={"message": blocked_message},
        )

    assert response.status_code == 200
    data = response.json()
    # Response should still be SAFE_REFUSAL (sanitizer downstream).
    assert data.get("response") == SAFE_REFUSAL

    # The "Founder override" log line must NOT appear — this is the
    # load-bearing assertion. Pre-fix it appears and proves the
    # founder branch leaked through to check_input.
    founder_override_lines = [
        r.getMessage() for r in caplog.records
        if "Founder override" in r.getMessage()
    ]
    assert not founder_override_lines, (
        f"Founder override log fired on empty-channel request: "
        f"{founder_override_lines}. Pre-fix predicate leaked founder to an empty body."
    )


def test_chat_stream_endpoint_empty_body_does_not_take_founder_branch(monkeypatch, caplog):
    """POST {} to /api/v1/max/chat/stream must NOT take the founder branch.

    Same logic as test_chat_endpoint_empty_body_does_not_take_founder_branch
    but on the streaming endpoint. The streaming variant gates the same
    check_input call. We assert against the SAFE_REFUSAL constant, NOT a
    substring, because the AI's own content policy can also produce a
    refusal-shaped answer — the founder-bypass regression is only visible
    when the guardrail code path (which returns the exact SAFE_REFUSAL)
    fires.
    """
    from app.services.max.guardrails import SAFE_REFUSAL

    blocked_message = "how to make a virus"

    # Capture ALL logs — the "Founder override" message is emitted on
    # logger "max.guardrails" inside check_input, not on max.api.
    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/v1/max/chat/stream",
            json={"message": blocked_message},
        )

    assert response.status_code == 200

    # Parse the SSE stream — each "data: {...}" line is a JSON event.
    # The blocked-topic path emits:
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

    # The text-event content must be exactly the SAFE_REFUSAL constant.
    text_events = [e for e in events if e.get("type") == "text"]
    assert text_events, (
        f"No text events emitted on /chat/stream — body: {response.text[:300]!r}"
    )
    emitted = text_events[0].get("content", "")
    assert emitted == SAFE_REFUSAL, (
        f"blocked-topic gate did not fire on /chat/stream. "
        f"Expected exact SAFE_REFUSAL, got {emitted[:200]!r}. "
        f"Founder branch was likely taken despite empty channel."
    )

    # The done event must report model_used="guardrail" — proof the
    # request never reached the AI layer.
    done_events = [e for e in events if e.get("type") == "done"]
    assert done_events and done_events[0].get("model_used") == "guardrail", (
        f"Expected model_used='guardrail' in done event, got {done_events!r}"
    )

    # The "Founder override" log line must NOT appear — the load-bearing
    # assertion. Pre-fix it appears and proves the founder branch leaked.
    founder_override_lines = [
        r.getMessage() for r in caplog.records
        if "Founder override" in r.getMessage()
    ]
    assert not founder_override_lines, (
        f"Founder override log fired on empty-channel streaming request: "
        f"{founder_override_lines}."
    )


def test_code_task_endpoint_empty_channel_requires_pin(monkeypatch, caplog):
    """POST {prompt, channel:''} to /api/v1/max/code-task with FOUNDER_PIN
    unset must refuse with 403.

    Pre-fix, sending channel="" was treated as founder ("" was in the
    allow-list), so PIN was bypassed and the code task was submitted.
    Post-fix, channel="" → anonymous → PIN required → 403.

    Note: CodeTaskRequest.channel has a model default of "web_cc" (the
    portal's canonical channel), so a body that OMITS channel entirely
    still gets founder=True via that default. The empty-string bypass
    that STEP 1a closes is the case where channel is explicitly "" — the
    body is sent, the field stores "", and the predicate now correctly
    classifies it as anonymous. The model-default bypass lives on the
    model side and is addressed in the followup Option A commit (when
    that lands).
    """
    monkeypatch.delenv("FOUNDER_PIN", raising=False)

    with caplog.at_level(logging.CRITICAL, logger="max.api"):
        response = client.post(
            "/api/v1/max/code-task",
            json={"prompt": "test", "channel": ""},
        )

    assert response.status_code == 403, (
        f"empty-channel POST to /code-task must require PIN. "
        f"Got status {response.status_code}. Pre-fix the empty channel "
        f"walked past the gate; STEP 1a closes that path."
    )
    assert any(
        r.levelno == logging.CRITICAL and "FOUNDER_PIN" in r.getMessage()
        for r in caplog.records
    ), (
        "Expected a CRITICAL log line on max.api when FOUNDER_PIN is unset."
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