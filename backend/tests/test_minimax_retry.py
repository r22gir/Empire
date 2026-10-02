"""MiniMax retries overloaded responses. Other failures stay single-shot."""
import asyncio

import httpx
import pytest

from app.services.max.minimax_retry import (
    BUSY_MESSAGE,
    request_with_retry,
    user_message_for_minimax,
)
from app.services.max.telegram_text import sanitize_telegram_text


class _Resp:
    def __init__(self, status, body=""):
        self.status_code = status
        self.text = body


def test_retries_529_then_succeeds_and_skips_401(monkeypatch):
    sleeps = []

    async def sleeper(seconds):
        sleeps.append(seconds)

    statuses = [529, 529, 200]

    async def call():
        return _Resp(statuses.pop(0), "overloaded_error" if statuses or True else "")

    resp = asyncio.run(request_with_retry(call, sleep=sleeper, rng=__import__("random").Random(1)))
    assert resp.status_code == 200
    assert len(sleeps) == 2
    assert 1.5 < sleeps[0] < 3.5
    assert 4.0 < sleeps[1] < 7.5

    async def denied():
        return _Resp(401, "nope")

    denied_resp = asyncio.run(request_with_retry(denied, sleep=sleeper, rng=__import__("random").Random(1)))
    assert denied_resp.status_code == 401
    assert len(sleeps) == 2


def test_connect_timeout_retries_then_raises():
    sleeps = []

    async def sleeper(seconds):
        sleeps.append(seconds)

    async def call():
        raise httpx.ConnectTimeout("connect")

    with pytest.raises(httpx.ConnectTimeout):
        asyncio.run(request_with_retry(call, sleep=sleeper, rng=__import__("random").Random(0)))
    assert len(sleeps) == 2


def test_busy_user_message_replaces_overloaded_text_only():
    assert user_message_for_minimax("MiniMax HTTP 529: overloaded_error") == BUSY_MESSAGE
    assert user_message_for_minimax("MiniMax HTTP 503: unavailable") == BUSY_MESSAGE
    assert user_message_for_minimax("ConnectTimeout") == BUSY_MESSAGE
    assert user_message_for_minimax("MiniMax HTTP 401: bad key") is None


def test_fallback_disabled_message_uses_the_friendly_line():
    from app.services.max.ai_router import AIRouter

    router = AIRouter.__new__(AIRouter)
    router.last_provider_errors = {"minimax": "MiniMax HTTP 529: overloaded_error"}
    requested = type("M", (), {"value": "minimax"})()
    assert AIRouter._fallback_disabled_message(router, requested) == BUSY_MESSAGE
    router.last_provider_errors = {"minimax": "MiniMax HTTP 401: bad key"}
    text = AIRouter._fallback_disabled_message(router, requested)
    assert "fallback is disabled" in text
    assert "401" in text


def test_telegram_rejoins_emoji_and_drops_lone_surrogates():
    grinning = "\U0001F600"
    pair = grinning.encode("utf-16", "surrogatepass").decode("utf-16", "surrogatepass")
    # Build the split form explicitly: high + low surrogate of U+1F600.
    split = chr(0xD83D) + chr(0xDE00)
    cleaned = sanitize_telegram_text("hi " + split + " " + chr(0xD800) + " " + grinning)
    cleaned.encode("utf-8")
    assert grinning in cleaned
    assert cleaned.count(grinning) == 2
    assert "\ud800" not in cleaned
    assert pair
