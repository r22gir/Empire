"""Minimal role lookup used by founder MiniMax image/draft routes.

On studio this module is unused: family-only admin checks short-circuit
when EMPIRE_EDITION is workroom. Tests monkeypatch ``entry_role``.
This is not the AMP login gate.
"""
from __future__ import annotations

from typing import Optional


def entry_role(*, email: Optional[str] = None, username: Optional[str] = None) -> Optional[str]:
    if not email and not username:
        return None
    return None
