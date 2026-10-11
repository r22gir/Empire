"""Founder gate for credential and publish controls. The PIN is never logged."""
from __future__ import annotations

import hmac
import os


class FounderAuthError(Exception):
    def __init__(self, status_code: int, detail: str):
        self.status_code = status_code
        self.detail = detail
        super().__init__(detail)


def assert_founder(pin: str | None) -> None:
    expected = os.environ.get("FOUNDER_PIN", "")
    if not expected:
        raise FounderAuthError(
            503,
            "FOUNDER_PIN is unset. Founder-only account actions are refused.",
        )
    given = "" if pin is None else str(pin)
    if not hmac.compare_digest(given, expected):
        raise FounderAuthError(403, "Founder PIN required.")
