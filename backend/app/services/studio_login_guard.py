"""In-memory Studio sign-in lockout (per IP + global).

Does not write to the live database. State lives in process memory so
tests can reset it without touching empire.db or sending email.
"""
from __future__ import annotations

import math
import threading
import time
from dataclasses import dataclass
from typing import Optional


IP_FAIL_LIMIT = 5
GLOBAL_FAIL_LIMIT = 50
LOCK_SECONDS = 15 * 60
REMEMBERED_DEVICE_HINT = "A remembered device still works."


def format_remaining(seconds: float) -> str:
    remaining = max(1, int(math.ceil(seconds)))
    minutes, secs = divmod(remaining, 60)
    parts: list[str] = []
    if minutes:
        parts.append(f"{minutes} minute{'s' if minutes != 1 else ''}")
    if secs or not parts:
        parts.append(f"{secs} second{'s' if secs != 1 else ''}")
    return " ".join(parts)


def lockout_message(seconds: float) -> str:
    return (
        "Too many failed sign-in attempts. Try again in "
        f"{format_remaining(seconds)}. {REMEMBERED_DEVICE_HINT}"
    )


@dataclass
class _Bucket:
    failures: int = 0
    locked_until: float = 0.0


class StudioLoginGuard:
    """5 failures / 15 min per IP; 50 failures / 15 min globally."""

    def __init__(
        self,
        ip_limit: int = IP_FAIL_LIMIT,
        global_limit: int = GLOBAL_FAIL_LIMIT,
        lock_seconds: float = LOCK_SECONDS,
        clock=time.monotonic,
    ):
        self.ip_limit = ip_limit
        self.global_limit = global_limit
        self.lock_seconds = lock_seconds
        self._clock = clock
        self._lock = threading.Lock()
        self._ips: dict[str, _Bucket] = {}
        self._global = _Bucket()

    def reset(self) -> None:
        with self._lock:
            self._ips.clear()
            self._global = _Bucket()

    def remaining_lock(self, ip: str, now: Optional[float] = None) -> float:
        now = self._now(now)
        with self._lock:
            return self._remaining_unlocked(ip, now)

    def check(self, ip: str, now: Optional[float] = None) -> Optional[str]:
        """Return a lockout message if this IP (or everyone) is locked."""
        remaining = self.remaining_lock(ip, now)
        if remaining > 0:
            return lockout_message(remaining)
        return None

    def record_failure(self, ip: str, now: Optional[float] = None) -> Optional[str]:
        now = self._now(now)
        key = ip or "unknown"
        with self._lock:
            bucket = self._ips.setdefault(key, _Bucket())
            self._expire(bucket, now)
            self._expire(self._global, now)
            bucket.failures += 1
            self._global.failures += 1
            if bucket.failures >= self.ip_limit:
                bucket.locked_until = now + self.lock_seconds
            if self._global.failures >= self.global_limit:
                self._global.locked_until = now + self.lock_seconds
            remaining = self._remaining_unlocked(key, now)
        if remaining > 0:
            return lockout_message(remaining)
        return None

    def record_success(self, ip: str) -> None:
        # Clear this IP so a successful sign-in is not immediately locked.
        # Do not reset the global count — one success must not erase a
        # distributed brute-force tally.
        key = ip or "unknown"
        with self._lock:
            self._ips.pop(key, None)

    def _now(self, now: Optional[float]) -> float:
        return self._clock() if now is None else now

    def _expire(self, bucket: _Bucket, now: float) -> None:
        if bucket.locked_until and now >= bucket.locked_until:
            bucket.failures = 0
            bucket.locked_until = 0.0

    def _remaining_unlocked(self, ip: str, now: float) -> float:
        bucket = self._ips.get(ip) or _Bucket()
        self._expire(bucket, now)
        self._expire(self._global, now)
        return max(0.0, bucket.locked_until - now, self._global.locked_until - now)


_GUARD = StudioLoginGuard()


def reset_studio_login_guard() -> None:
    """Test helper — do not call from production request paths."""
    _GUARD.reset()


def studio_login_lockout_message(ip: Optional[str]) -> Optional[str]:
    return _GUARD.check(ip or "unknown")


def record_studio_login_failure(ip: Optional[str]) -> Optional[str]:
    return _GUARD.record_failure(ip or "unknown")


def record_studio_login_success(ip: Optional[str]) -> None:
    _GUARD.record_success(ip or "unknown")
