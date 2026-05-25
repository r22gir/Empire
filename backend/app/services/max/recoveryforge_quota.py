"""
RecoveryForge Quota Tracker — enforces MCP Understand Image quota for vision analysis.

MiniMax Token Plan MCP Understand Image quota:
- 4,500 requests per 5-hour window (shared with text generation)
- Hard cap at 500 analyses per 5-hour window for RecoveryForge
- Soft cap at 1,500 analyses/day for RecoveryForge
- Reserve 1,500 requests per 5-hour window for general MAX/OpenClaw/work use

RecoveryForge batch classification uses MCP Understand Image only.
Image Generation quota is NEVER consumed by RecoveryForge batch classification.

Storage: /data/images/recoveryforge_quota.json (date + window-keyed records)
Override: RECOVERYFORGE_ALLOW_QUOTA_OVERRIDE=1 bypasses cap (founder only).
"""

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

QUOTA_FILE = "/data/images/recoveryforge_quota.json"

# RecoveryForge vision analysis caps
WINDOW_CAP = 500           # max RecoveryForge analyses per 5-hour window
DAILY_SOFT_CAP = 1500      # soft cap for RecoveryForge analyses per day
WINDOW_RESERVE = 1500      # requests reserved for general MAX/OpenClaw/work per window
BATCH_CHUNK_LIMIT = 25    # max images per batch run by default
OVERRIDE_ENV = "RECOVERYFORGE_ALLOW_QUOTA_OVERRIDE"

# Window duration in hours
WINDOW_HOURS = 5


def _window_key() -> str:
    """Return current 5-hour window identifier (YYYY-MM-DD-HH)."""
    now = datetime.now(timezone.utc)
    window_num = now.hour // WINDOW_HOURS
    return f"{now.strftime('%Y-%m-%d')}-{window_num}"


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


def _window_start() -> datetime:
    """Start of current 5-hour UTC window."""
    now = datetime.now(timezone.utc)
    window_num = now.hour // WINDOW_HOURS
    return now.replace(hour=window_num * WINDOW_HOURS, minute=0, second=0, microsecond=0)


def _window_end() -> datetime:
    """End of current 5-hour UTC window."""
    return _window_start() + timedelta(hours=WINDOW_HOURS)


def _record_usage(image_key: str, model: str, status: str, error: str | None = None) -> None:
    """Record one image analysis in the quota log."""
    today = _today()
    window_key = _window_key()

    data = _load_quota()
    if today not in data:
        data[today] = {"daily_used": 0, "daily_cap": DAILY_SOFT_CAP, "window_records": {}}
    if window_key not in data[today]["window_records"]:
        data[today]["window_records"][window_key] = {"window_used": 0, "window_cap": WINDOW_CAP}

    data[today]["window_records"][window_key]["analyses"] = data[today]["window_records"][window_key].get("analyses", [])
    data[today]["window_records"][window_key]["analyses"].append({
        "image_key": image_key,
        "model": model,
        "status": status,
        "error": error,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    data[today]["window_records"][window_key]["window_used"] = sum(
        1 for a in data[today]["window_records"][window_key]["analyses"] if a["status"] == "success"
    )
    data[today]["daily_used"] = sum(
        w.get("window_used", 0)
        for w in data[today].get("window_records", {}).values()
    )
    _save_quota(data)


def check_quota() -> dict[str, Any]:
    """
    Returns current RecoveryForge quota status.

    Tracks MCP Understand Image usage against:
    - Window cap: 500 analyses per 5-hour window
    - Daily soft cap: 1,500 analyses per day
    - Window reserve: 1,500 requests kept free for general MAX/OpenClaw/work use

    Returns:
        recoveryforge_vision_bucket: "mcp_understand_image"
        recoveryforge_window_cap: 500
        recoveryforge_daily_soft_cap: 1500
        current_window_used_by_recoveryforge: int
        current_window_remaining_for_recoveryforge: int
        current_window_reserved_for_general_use: 1500
        daily_used_by_recoveryforge: int
        daily_remaining_soft_cap: int
        image_generation_bucket_total: 100
        image_generation_used_by_recoveryforge_batch: 0 (always 0 — batch uses vision not generation)
        image_generation_reserved_for_quotes_and_mockups: true
        recoveryforge_manual_mockup_cap: 5
        batch_chunk_limit: 25
        cap_reached: bool
        override_enabled: bool
        reset_window_hint: str
    """
    today = _today()
    window_key = _window_key()
    override = os.environ.get(OVERRIDE_ENV, "").strip() == "1"
    window_start = _window_start()
    window_end = _window_end()

    data = _load_quota()
    entry = data.get(today, {"daily_used": 0, "window_records": {}})
    window_entry = entry.get("window_records", {}).get(window_key, {"window_used": 0})

    window_used = window_entry.get("window_used", 0)
    # Remaining RecoveryForge capacity in current window (500 cap minus used)
    window_available = max(0, WINDOW_CAP - window_used)

    daily_used = entry.get("daily_used", 0)
    daily_remaining = max(0, DAILY_SOFT_CAP - daily_used)

    # Cap is reached when RecoveryForge would have to consume into the reserve
    # Reserve is WINDOW_RESERVE=1500 general-use requests preserved per window
    cap_reached = (window_available == 0 and daily_remaining == 0) and not override

    reset_hint = window_end.strftime("%Y-%m-%dT%H:%M:%SZ")

    return {
        "recoveryforge_vision_bucket": "mcp_understand_image",
        "recoveryforge_window_cap": WINDOW_CAP,
        "recoveryforge_daily_soft_cap": DAILY_SOFT_CAP,
        "current_window_used_by_recoveryforge": window_used,
        "current_window_remaining_for_recoveryforge": window_available,
        "current_window_reserved_for_general_use": WINDOW_RESERVE,
        "daily_used_by_recoveryforge": daily_used,
        "daily_remaining_soft_cap": daily_remaining,
        "image_generation_bucket_total": 100,
        "image_generation_used_by_recoveryforge_batch": 0,
        "image_generation_reserved_for_quotes_and_mockups": True,
        "recoveryforge_manual_mockup_cap": 5,
        "batch_chunk_limit": BATCH_CHUNK_LIMIT,
        "cap_reached": cap_reached,
        "override_enabled": override,
        "reset_window_hint": reset_hint,
        "window_start_utc": window_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "server_date": today,
        "quota_file": QUOTA_FILE,
    }


def consume_quota(image_key: str, model: str, success: bool, error: str | None = None) -> None:
    """
    Record a completed (or failed) image analysis against the MCP Understand Image quota.

    Only successful analyses count against RecoveryForge caps.
    Failed analyses are recorded but do not consume quota.
    Image Generation quota is never consumed by RecoveryForge batch classification.
    """
    _record_usage(image_key, model, "success" if success else "failed", error)


def quota_allow_new() -> bool:
    """Returns True if a new RecoveryForge image analysis is allowed under window cap."""
    status = check_quota()
    return not status["cap_reached"]