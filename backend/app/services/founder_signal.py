"""Read Studio's founder-activity signal. This module never writes the file.

Studio (brief 8c) writes ``{EMPIRE_DATA_DIR}/founder-signal/status.json``:

    {
      "schema": 1,
      "updated_at": "ISO-8601Z",
      "founder_active": false,
      "founder_last_active_at": "ISO-8601Z",
      "reserve_ok": true,
      "overage_allowed": true,
      "reason": "inactive_reserve_ok"
    }

Missing / stale / malformed → overage_allowed=False (fail closed).
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

SIGNAL_RELATIVE = Path("founder-signal") / "status.json"
DEFAULT_MAX_AGE_S = 180
SCHEMA = 1


def max_age_s() -> int:
    raw = (os.getenv("FOUNDER_SIGNAL_MAX_AGE_S") or "").strip()
    if raw:
        try:
            return max(1, int(raw))
        except ValueError:
            pass
    return DEFAULT_MAX_AGE_S


def signal_path() -> Optional[Path]:
    from app.edition import data_root_or_none

    root = data_root_or_none()
    if root is None:
        return None
    return root / SIGNAL_RELATIVE


def _parse_iso(raw: Any) -> Optional[datetime]:
    if not raw or not isinstance(raw, str):
        return None
    text = raw.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _closed(reason: str) -> dict:
    return {
        "schema": SCHEMA,
        "valid": False,
        "overage_allowed": False,
        "founder_active": None,
        "reserve_ok": None,
        "reason": reason,
        "updated_at": None,
        "founder_last_active_at": None,
        "age_s": None,
    }


def read_founder_signal(*, now: Optional[datetime] = None) -> dict:
    """Read and validate the signal file. Never writes."""
    path = signal_path()
    if path is None or not path.is_file():
        return _closed("missing")
    try:
        raw = path.read_text(encoding="utf-8")
        data = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError, TypeError):
        return _closed("malformed")
    if not isinstance(data, dict):
        return _closed("malformed")
    if data.get("schema") != SCHEMA:
        return _closed("malformed")
    updated = _parse_iso(data.get("updated_at"))
    if updated is None:
        return _closed("malformed")
    clock = now or datetime.now(timezone.utc)
    age = (clock - updated).total_seconds()
    if age > max_age_s() or age < -5:
        return _closed("stale")
    if not isinstance(data.get("overage_allowed"), bool):
        return _closed("malformed")
    return {
        "schema": SCHEMA,
        "valid": True,
        "overage_allowed": bool(data["overage_allowed"]),
        "founder_active": bool(data.get("founder_active")),
        "reserve_ok": bool(data.get("reserve_ok")),
        "reason": str(data.get("reason") or ""),
        "updated_at": data.get("updated_at"),
        "founder_last_active_at": data.get("founder_last_active_at"),
        "age_s": age,
    }
