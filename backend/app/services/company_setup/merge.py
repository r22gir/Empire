"""Deep merge that never replaces the whole business.json document."""
from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.services.company_setup.schema import PRESERVE_KEYS


def deep_merge(base: dict[str, Any] | None, incoming: dict[str, Any] | None) -> dict[str, Any]:
    """Merge incoming into base. Incoming None/missing keys leave base intact.

    Lists provided by incoming replace that key (caller sends the full list).
    An incoming value of None does not delete an existing key.
    """
    out: dict[str, Any] = deepcopy(base) if isinstance(base, dict) else {}
    if not isinstance(incoming, dict):
        return out
    for key, value in incoming.items():
        if value is None:
            continue
        if key in out and isinstance(out[key], dict) and isinstance(value, dict):
            out[key] = deep_merge(out[key], value)
        else:
            out[key] = deepcopy(value)
    return out


def preserve_existing(existing: dict[str, Any] | None, merged: dict[str, Any]) -> dict[str, Any]:
    """Re-apply preserved keys if the merge dropped them."""
    existing = existing if isinstance(existing, dict) else {}
    out = dict(merged)
    for key in PRESERVE_KEYS:
        if key in existing and (key not in out or out.get(key) in (None, "", [], {})):
            out[key] = deepcopy(existing[key])
    return out


def public_view(data: dict[str, Any] | None) -> dict[str, Any]:
    """Client-safe company record. Never includes secret material."""
    data = dict(data or {})
    data.pop("whatsapp_secrets", None)
    data.pop("secrets", None)
    for key in list(data.keys()):
        low = key.lower()
        if "token" in low or "secret" in low or "password" in low or "api_key" in low:
            data.pop(key, None)
    return data
