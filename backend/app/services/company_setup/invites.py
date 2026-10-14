"""Team invite records. Never sends email or WhatsApp."""
from __future__ import annotations

import logging
import secrets
from datetime import datetime, timezone
from typing import Any

from app.services.company_setup.io import atomic_write, edition_lock, read_json_list
from app.services.company_setup.schema import TEAM_ROLES
from app.services.company_setup.store import edition_company_dir

logger = logging.getLogger("max.company_setup")


def _path():
    return edition_company_dir() / "invites.json"


def list_invites() -> list[dict[str, Any]]:
    return [r for r in read_json_list(_path()) if isinstance(r, dict)]


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
    with edition_lock(edition_company_dir()):
        rows = [r for r in read_json_list(_path()) if isinstance(r, dict)]
        rows.append(row)
        atomic_write(_path(), rows, mode=0o600, backup=True)
    logger.info("company setup invite recorded role=%s sent=false", role)
    return row
