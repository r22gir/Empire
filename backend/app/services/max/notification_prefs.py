"""
Telegram Notification Preferences — Controls which categories of notifications
get sent to the founder's Telegram. Persisted to JSON on disk.

Categories:
  desk_finance    — Morning Invoice Audit (8:00 AM)
  desk_it         — Service Health Check (8:30 AM)
  desk_sales      — Stale Quote Follow-Up (9:00 AM)
  desk_support    — Open Ticket Summary (9:30 AM)
  desk_marketing  — Daily Social Media Post (10:00 AM)
  desk_forge      — Pipeline Summary (10:30 AM)
  service_health  — Service up/down alerts (every 5 min)
  morning_brief   — Morning brief (7:30 AM)
  weekly_report   — Weekly report (Monday 8 AM)
  task_updates    — Task started/completed/failed
  intake_events   — New intake projects, photo uploads
  urgent_alerts   — Always on (cannot be disabled)
"""

import json
import logging
from pathlib import Path
from typing import Dict

logger = logging.getLogger("max.notification_prefs")

_PREFS_PATH = Path.home() / "empire-repo" / "backend" / "data" / "notification_prefs.json"

# All categories with defaults (True = send, False = muted)
DEFAULT_PREFS: Dict[str, dict] = {
    "desk_finance":   {"enabled": True, "label": "Finance Desk", "desc": "Morning Invoice Audit (8:00 AM)", "group": "desks"},
    "desk_it":        {"enabled": True, "label": "IT Desk", "desc": "Service Health Check (8:30 AM)", "group": "desks"},
    "desk_sales":     {"enabled": True, "label": "Sales Desk", "desc": "Stale Quote Follow-Up (9:00 AM)", "group": "desks"},
    "desk_support":   {"enabled": True, "label": "Support Desk", "desc": "Open Ticket Summary (9:30 AM)", "group": "desks"},
    "desk_marketing": {"enabled": True, "label": "Marketing Desk", "desc": "Daily Social Media Post (10:00 AM)", "group": "desks"},
    "desk_forge":     {"enabled": True, "label": "Forge Desk", "desc": "Pipeline Summary (10:30 AM)", "group": "desks"},
    "service_health": {"enabled": True, "label": "Service Alerts", "desc": "Service up/down notifications (every 5 min)", "group": "system"},
    "morning_brief":  {"enabled": True, "label": "Morning Brief", "desc": "Daily overview at 7:30 AM", "group": "system"},
    "weekly_report":  {"enabled": True, "label": "Weekly Report", "desc": "Business intelligence (Monday 8 AM)", "group": "system"},
    "task_updates":   {"enabled": True, "label": "Task Updates", "desc": "Task started / completed / failed", "group": "tasks"},
    "intake_events":  {"enabled": True, "label": "Intake Events", "desc": "New client projects & photo uploads", "group": "events"},
    "urgent_alerts":  {"enabled": True, "label": "Urgent Alerts", "desc": "Critical alerts (always on)", "group": "system", "locked": True},
}

# Map desk_id from scheduler to preference key
DESK_TO_PREF = {
    "finance": "desk_finance",
    "it": "desk_it",
    "sales": "desk_sales",
    "support": "desk_support",
    "marketing": "desk_marketing",
    "forge": "desk_forge",
}


def _load() -> dict:
    """Load prefs from disk, merging with defaults for any new categories."""
    if _PREFS_PATH.exists():
        try:
            stored = json.loads(_PREFS_PATH.read_text())
            # Merge: keep stored values, add any missing defaults
            merged = {}
            for key, default in DEFAULT_PREFS.items():
                if key in stored:
                    merged[key] = {**default, **stored[key]}
                else:
                    merged[key] = dict(default)
            return merged
        except Exception as e:
            logger.warning(f"Failed to load notification prefs: {e}")
    return {k: dict(v) for k, v in DEFAULT_PREFS.items()}


def _save(prefs: dict):
    """Persist prefs to disk."""
    _PREFS_PATH.parent.mkdir(parents=True, exist_ok=True)
    _PREFS_PATH.write_text(json.dumps(prefs, indent=2))


def get_all_prefs() -> dict:
    """Return all notification preferences."""
    return _load()


def update_prefs(updates: Dict[str, bool]) -> dict:
    """Update enabled/disabled state for given categories. Returns updated prefs."""
    prefs = _load()
    for key, enabled in updates.items():
        if key in prefs:
            if prefs[key].get("locked"):
                continue  # Can't disable urgent_alerts
            prefs[key]["enabled"] = bool(enabled)
    _save(prefs)
    return prefs


def is_allowed(category: str) -> bool:
    """Check if a notification category is currently allowed."""
    prefs = _load()
    entry = prefs.get(category)
    if not entry:
        return True  # Unknown categories default to allowed
    return entry.get("enabled", True)


def is_desk_allowed(desk_id: str) -> bool:
    """Check if notifications for a specific desk are allowed."""
    pref_key = DESK_TO_PREF.get(desk_id)
    if not pref_key:
        return True  # Unknown desks default to allowed
    return is_allowed(pref_key)
