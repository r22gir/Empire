"""
Calendar and reminder skill for OpenClaw.

Provides reminders and scheduling functionality using a simple JSON file store.
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Dict, Any, List

from .base import Skill

logger = logging.getLogger(__name__)

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
REMINDERS_FILE = os.path.join(DATA_DIR, "reminders.json")


def _load_reminders() -> List[Dict[str, Any]]:
    os.makedirs(DATA_DIR, exist_ok=True)
    if not os.path.exists(REMINDERS_FILE):
        return []
    with open(REMINDERS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_reminders(reminders: List[Dict[str, Any]]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(REMINDERS_FILE, "w", encoding="utf-8") as f:
        json.dump(reminders, f, indent=2)


class CalendarSkill(Skill):
    """Calendar and reminder skill: add, list, and remove reminders."""

    name = "calendar"
    description = "Manage reminders and scheduled events"
    triggers = [
        "remind",
        "reminder",
        "schedule",
        "calendar",
        "appointment",
        "event",
        "meeting",
        "alarm",
    ]

    async def execute(self, intent: str, params: Dict[str, Any]) -> str:
        action = params.get("action", "list")

        if action == "add":
            title = params.get("title", intent)
            due = params.get("due", "")
            reminders = _load_reminders()
            entry = {
                "id": len(reminders) + 1,
                "title": title,
                "due": due,
                "created": datetime.now(timezone.utc).isoformat(),
            }
            reminders.append(entry)
            _save_reminders(reminders)
            return f"Reminder added: '{title}' due {due or 'unspecified'}"

        if action == "list":
            reminders = _load_reminders()
            if not reminders:
                return "No reminders found."
            lines = [f"- [{r['id']}] {r['title']} (due: {r.get('due', 'N/A')})" for r in reminders]
            return "Reminders:\n" + "\n".join(lines)

        if action == "delete":
            reminder_id = params.get("id")
            reminders = _load_reminders()
            reminders = [r for r in reminders if r["id"] != reminder_id]
            _save_reminders(reminders)
            return f"Reminder {reminder_id} deleted."

        return f"Unknown calendar action: {action}"
