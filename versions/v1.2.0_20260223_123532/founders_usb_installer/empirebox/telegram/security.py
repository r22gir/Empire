"""Security module: whitelist, PIN authentication, and rate limiting."""

import time
from collections import defaultdict
from typing import Optional


class SecurityManager:
    """Manages access control, PIN authentication, and rate limiting."""

    def __init__(self, config: dict):
        self._allowed_users: list[int] = config.get("allowed_users", [])
        self._pin_enabled: bool = config.get("pin_enabled", False)
        self._pin_code: str = str(config.get("pin_code", ""))
        self._pin_required_commands: list[str] = config.get(
            "pin_required_commands", ["stop_product", "stop_all", "restart"]
        )
        max_per_min: int = config.get("rate_limit", {}).get(
            "max_commands_per_minute", 30
        )
        self._rate_limit: int = max_per_min
        # {user_id: [timestamp, ...]}
        self._command_timestamps: dict[int, list[float]] = defaultdict(list)
        # Users who have successfully entered the PIN this session
        self._pin_verified: set[int] = set()

    # ── Whitelist ──────────────────────────────────────────────────────────

    def is_allowed(self, user_id: int) -> bool:
        """Return True if the user is on the whitelist."""
        return user_id in self._allowed_users

    # ── Rate limiting ──────────────────────────────────────────────────────

    def check_rate_limit(self, user_id: int) -> bool:
        """Return True if the user is within the allowed rate limit."""
        now = time.monotonic()
        window = now - 60.0
        timestamps = self._command_timestamps[user_id]
        # Discard timestamps older than one minute
        timestamps[:] = [t for t in timestamps if t > window]
        if len(timestamps) >= self._rate_limit:
            return False
        timestamps.append(now)
        return True

    # ── PIN authentication ─────────────────────────────────────────────────

    def pin_required(self, command: str) -> bool:
        """Return True if the command requires PIN verification."""
        return self._pin_enabled and command in self._pin_required_commands

    def verify_pin(self, user_id: int, pin: str) -> bool:
        """Verify the PIN for a user and cache the result."""
        if pin == self._pin_code:
            self._pin_verified.add(user_id)
            return True
        return False

    def is_pin_verified(self, user_id: int) -> bool:
        """Return True if the user has already verified their PIN."""
        return user_id in self._pin_verified

    def revoke_pin(self, user_id: int) -> None:
        """Revoke cached PIN verification for a user."""
        self._pin_verified.discard(user_id)
