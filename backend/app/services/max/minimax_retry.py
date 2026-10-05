"""Retry MiniMax when the API is overloaded or the connection never starts.

Three attempts, with jittered waits that add up to about eight seconds.
401 and other client errors are not retried. Read timeouts are not retried.
"""
from __future__ import annotations

import asyncio
import random
import time
from typing import Awaitable, Callable, Optional, TypeVar

import httpx

BUSY_MESSAGE = "MiniMax is busy, try again in a moment."
ATTEMPTS = 3
# Two gaps between three attempts. Jitter stays near this budget.
WAIT_SECONDS = (2.4, 5.6)

T = TypeVar("T")


def is_retryable_status(status: int) -> bool:
    return status in (429, 529) or 500 <= int(status) <= 599


def is_connect_failure(exc: BaseException) -> bool:
    return isinstance(exc, (httpx.ConnectTimeout, httpx.ConnectError, httpx.PoolTimeout))


def is_busy_error_text(text: str | None) -> bool:
    raw = (text or "").lower()
    if any(marker in raw for marker in ("http 429", "http 529", "overloaded_error", "connecttimeout", "connecterror", "pooltimeout")):
        return True
    for code in range(500, 600):
        if f"http {code}" in raw:
            return True
    return False


def user_message_for_minimax(error_text: str | None) -> Optional[str]:
    if is_busy_error_text(error_text):
        return BUSY_MESSAGE
    return None


def _jitter(seconds: float, rng: random.Random) -> float:
    return max(0.05, seconds + rng.uniform(-seconds * 0.15, seconds * 0.15))


async def request_with_retry(
    call: Callable[[], Awaitable[T]],
    *,
    attempts: int = ATTEMPTS,
    sleep: Optional[Callable[..., Awaitable[None]]] = None,
    rng: Optional[random.Random] = None,
) -> T:
    sleeper = sleep or asyncio.sleep
    rng = rng or random.Random()
    for attempt in range(attempts):
        try:
            result = await call()
        except Exception as exc:
            if is_connect_failure(exc) and attempt < attempts - 1:
                await sleeper(_jitter(WAIT_SECONDS[attempt], rng))
                continue
            raise
        status = int(getattr(result, "status_code", 200) or 200)
        if is_retryable_status(status) and attempt < attempts - 1:
            await sleeper(_jitter(WAIT_SECONDS[attempt], rng))
            continue
        return result
    raise RuntimeError("MiniMax retry exhausted")


def request_with_retry_sync(
    call: Callable[[], T],
    *,
    attempts: int = ATTEMPTS,
    sleep: Optional[Callable[[float], None]] = None,
    rng: Optional[random.Random] = None,
) -> T:
    sleeper = sleep or time.sleep
    rng = rng or random.Random()
    for attempt in range(attempts):
        try:
            result = call()
        except Exception as exc:
            if is_connect_failure(exc) and attempt < attempts - 1:
                sleeper(_jitter(WAIT_SECONDS[attempt], rng))
                continue
            raise
        status = int(getattr(result, "status_code", 200) or 200)
        if is_retryable_status(status) and attempt < attempts - 1:
            sleeper(_jitter(WAIT_SECONDS[attempt], rng))
            continue
        return result
    raise RuntimeError("MiniMax retry exhausted")
