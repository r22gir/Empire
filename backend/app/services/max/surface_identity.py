"""Canonical MAX surface identity helpers."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


WEB_ALIASES = {"web", "web_cc", "dashboard", "command_center", "mobile_browser", "studio_browser"}


def normalize_surface(channel: str | None) -> dict[str, str]:
    ch = (channel or "web").strip().lower()
    if ch in WEB_ALIASES:
        return {
            "surface": "Founder/Web MAX",
            "surface_key": "founder_web",
            "canonical_channel": "web_chat",
            "input_channel": channel or "web",
        }
    if ch == "telegram":
        return {
            "surface": "Telegram MAX",
            "surface_key": "telegram",
            "canonical_channel": "telegram",
            "input_channel": channel or "telegram",
        }
    if ch == "email":
        return {
            "surface": "Email MAX",
            "surface_key": "email",
            "canonical_channel": "email",
            "input_channel": channel or "email",
        }
    return {
        "surface": ch or "unknown",
        "surface_key": ch or "unknown",
        "canonical_channel": ch or "system",
        "input_channel": channel or "",
    }


def founder_identity_key(channel: str | None = None, user_id: str | None = None) -> str:
    """Shared founder key across Web browser sessions without inventing Phone MAX."""
    identity = user_id or "founder"
    surface = normalize_surface(channel)
    if surface["canonical_channel"] == "web_chat":
        return f"{identity}:web_chat"
    return f"{identity}:{surface['canonical_channel']}"


def build_response_metadata(channel: str | None, skill_used: str | None = None) -> dict[str, Any]:
    from app.services.max.operating_registry import get_registry_load_info

    registry = get_registry_load_info()
    surface = normalize_surface(channel)
    return {
        "registry_version": registry.get("registry_version") or "",
        "surface": surface["surface"],
        "response_at": datetime.now(timezone.utc).isoformat(),
        "skill_used": skill_used,
    }


def build_ledger_metadata(channel: str | None, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    surface = normalize_surface(channel)
    metadata = {
        "surface": surface["surface"],
        "surface_key": surface["surface_key"],
        "canonical_channel": surface["canonical_channel"],
        "input_channel": surface["input_channel"],
        "identity_key": founder_identity_key(channel),
    }
    if extra:
        metadata.update(extra)
    return metadata
