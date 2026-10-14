"""Team invite records. Never sends email or WhatsApp."""
from __future__ import annotations

import json
import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from app.services.company_setup.schema import TEAM_ROLES
from app.services.company_setup.store import edition_company_dir

logger = logging.getLogger("max.company_setup")


def _path():
    return edition_company_dir() / "invites.json"


def _load() -> list[dict[str, Any]]:
    path = _path()
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    if isinstance(data, list):
        return [r for r in data if isinstance(r, dict)]
    return []


def _save(rows: list[dict[str, Any]]) -> None:
    path = _path()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rows, indent=2) + "\n", encoding="utf-8")


def list_invites() -> list[dict[str, Any]]:
    return _load()


def create_invite(email: str, role: str, name: str = "") -> dict[str, Any]:
    """Record an invite. Does not send mail, WhatsApp, or SMS."""
    role = (role or "viewer").strip().lower()
    if role not in TEAM_ROLES:
        raise ValueError(f"Unknown role. Must be one of: {list(TEAM_ROLES)}")
    email = (email or "").strip().lower()
    if not email or "@" not in email:
        raise ValueError("Invite needs a valid email address")
    row = {
        "id": secrets.token_hex(8),
        "email": email,
        "name": (name or "").strip(),
        "role": role,
        "status": "pending",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sent": False,
        "send_channel": "none",
    }
    rows = _load()
    rows.append(row)
    _save(rows)
    logger.info("company setup invite recorded role=%s sent=false", role)
    return row
