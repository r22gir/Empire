"""
RecoveryForge Quota Tracker — enforces 80-image/day MiniMax analysis cap.

Daily cap: 80 images for RecoveryForge batch analysis.
Reserved: 20 images/day for customer quotes, MAX requests, workroom mockups,
          founder-directed tasks, and other non-RecoveryForge uses.

Storage: /data/images/recoveryforge_quota.json (date-keyed records)
Override: RECOVERYFORGE_ALLOW_QUOTA_OVERRIDE=1 bypasses cap (founder only).
"""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

QUOTA_FILE = "/data/images/recoveryforge_quota.json"
DAILY_CAP = 80
RESERVED = 20
OVERRIDE_ENV = "RECOVERYFORGE_ALLOW_QUOTA_OVERRIDE"


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_quota() -> dict[str, dict[str, Any]]:
    if os.path.exists(QUOTA_FILE):
        try:
            with open(QUOTA_FILE, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {}


def _save_quota(data: dict[str, dict[str, Any]]) -> None:
    Path(QUOTA_FILE).parent.mkdir(parents=True, exist_ok=True)
    with open(QUOTA_FILE, "w") as f:
        json.dump(data, f, indent=2)


def _record_usage(date: str, image_key: str, model: str, status: str, error: str | None = None) -> None:
    """Record one image analysis in the quota log."""
    data = _load_quota()
    if date not in data:
        data[date] = {"used": 0, "limit": DAILY_CAP, "reserved": RESERVED, "analyses": []}
    data[date]["analyses"].append({
        "image_key": image_key,
        "model": model,
        "status": status,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    data[date]["used"] = sum(1 for a in data[date]["analyses"] if a["status"] == "success")
    _save_quota(data)


def check_quota() -> dict[str, Any]:
    """
    Returns current quota status for RecoveryForge.

    Returns:
        daily_cap: 80
        daily_reserved_quota: 20
        used_today: int
        remaining_recoveryforge_today: int
        cap_reached: bool
        override_active: bool
        reset_date: str (midnight UTC tomorrow)
        server_date: str (current UTC date)
    """
    today = _today()
    override = os.environ.get(OVERRIDE_ENV, "").strip() == "1"

    data = _load_quota()
    entry = data.get(today, {"used": 0, "limit": DAILY_CAP, "reserved": RESERVED, "analyses": []})

    used = entry.get("used", 0)
    remaining = max(0, DAILY_CAP - used)

    tomorrow = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0)
    from datetime import timedelta
    tomorrow += timedelta(days=1)
    reset_date = tomorrow.strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "daily_cap": DAILY_CAP,
        "daily_reserved_quota": RESERVED,
        "used_today": used,
        "remaining_recoveryforge_today": remaining,
        "cap_reached": remaining == 0 and not override,
        "override_active": override,
        "reset_date": reset_date,
        "server_date": today,
        "quota_file": QUOTA_FILE,
    }


def consume_quota(image_key: str, model: str, success: bool, error: str | None = None) -> None:
    """
    Record a completed (or failed) image analysis against the daily quota.

    Only successful analyses count against the 80-image cap.
    """
    _record_usage(_today(), image_key, model, "success" if success else "failed", error)


def quota_allow_new() -> bool:
    """Returns True if a new image analysis is allowed under the quota cap."""
    status = check_quota()
    return not status["cap_reached"]