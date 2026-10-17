"""Read Studio's founder-activity signal for the family soft cap.

Studio (brief 8c) writes ``{EMPIRE_DATA_DIR}/founder-signal/status.json``.
This module never writes that file. Missing, stale, or malformed input
fails closed: overage is not allowed.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any, Optional

SIGNAL_SCHEMA = 1
DEFAULT_MAX_AGE_S = 180


def signal_max_age_s() -> int:
    raw = os.getenv("FOUNDER_SIGNAL_MAX_AGE_S", "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return DEFAULT_MAX_AGE_S


def signal_path():
    from pathlib import Path

    from app.edition import data_root_or_none

    root = data_root_or_none()
    if root is None:
        return None
    return Path(root) / "founder-signal" / "status.json"


def _parse_iso(ts: str) -> Optional[datetime]:
    raw = (ts or "").strip()
    if not raw:
        return None
    if raw.endswith("Z"):
        raw = raw[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(raw)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _fail_closed(reason: str) -> dict[str, Any]:
    return {
        "ok": False,
        "schema": None,
        "updated_at": None,
        "founder_active": True,
        "founder_last_active_at": None,
        "reserve_ok": False,
        "overage_allowed": False,
        "brother_ceiling_pct": None,
        "reason": reason,
    }


def load_founder_signal(*, now: Optional[datetime] = None) -> dict[str, Any]:
    """Validate and return the Studio signal. Never writes."""
    path = signal_path()
    if path is None or not path.is_file():
        return _fail_closed("missing")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return _fail_closed("malformed")
    if not isinstance(data, dict):
        return _fail_closed("malformed")
    if data.get("schema") != SIGNAL_SCHEMA:
        return _fail_closed("malformed")
    if "overage_allowed" not in data or "founder_active" not in data:
        return _fail_closed("malformed")
    updated = _parse_iso(str(data.get("updated_at") or ""))
    if updated is None:
        return _fail_closed("malformed")
    now = now or datetime.now(timezone.utc)
    age = (now - updated).total_seconds()
    if age > signal_max_age_s() or age < -30:
        return _fail_closed("stale")
    allowed = bool(data.get("overage_allowed"))
    ceiling = None
    raw_ceiling = data.get("brother_ceiling_pct")
    if raw_ceiling is not None and raw_ceiling != "":
        try:
            value = float(raw_ceiling)
            if 0 < value <= 100:
                ceiling = value
        except (TypeError, ValueError):
            ceiling = None
    return {
        "ok": True,
        "schema": SIGNAL_SCHEMA,
        "updated_at": updated.isoformat().replace("+00:00", "Z"),
        "founder_active": bool(data.get("founder_active")),
        "founder_last_active_at": data.get("founder_last_active_at"),
        "reserve_ok": bool(data.get("reserve_ok")),
        "overage_allowed": allowed,
        "brother_ceiling_pct": ceiling,
        "reason": str(data.get("reason") or ("inactive_reserve_ok" if allowed else "founder_active")),
    }
