"""
Smart home automation skill for OpenClaw.

Integrates with home automation platforms (Home Assistant, etc.).
"""

import logging
import os
from typing import Dict, Any

import httpx

from .base import Skill

logger = logging.getLogger(__name__)

HA_BASE_URL = os.getenv("HOME_ASSISTANT_URL", "http://localhost:8123")
HA_TOKEN = os.getenv("HOME_ASSISTANT_TOKEN", "")


class SmartHomeSkill(Skill):
    """Home automation skill: control lights, thermostat, locks, and devices."""

    name = "smarthome"
    description = "Control smart home devices via Home Assistant"
    triggers = [
        "turn on",
        "turn off",
        "lights",
        "thermostat",
        "temperature",
        "lock",
        "unlock",
        "home",
        "smart home",
        "device",
    ]

    async def execute(self, intent: str, params: Dict[str, Any]) -> str:
        action = params.get("action", "status")
        entity_id = params.get("entity_id", "")

        if not HA_TOKEN:
            return "Home Assistant token not configured. Set HOME_ASSISTANT_TOKEN in environment."

        headers = {
            "Authorization": f"Bearer {HA_TOKEN}",
            "Content-Type": "application/json",
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if action == "status":
                    resp = await client.get(f"{HA_BASE_URL}/api/", headers=headers)
                    return f"Home Assistant status: {resp.json()}"
                if action in ("turn_on", "turn_off"):
                    domain = entity_id.split(".")[0] if "." in entity_id else "light"
                    service = action
                    resp = await client.post(
                        f"{HA_BASE_URL}/api/services/{domain}/{service}",
                        headers=headers,
                        json={"entity_id": entity_id},
                    )
                    return f"'{action}' executed for {entity_id}: {resp.status_code}"
                return f"Unknown smart home action: {action}"
        except httpx.RequestError as exc:
            logger.warning("Home Assistant unreachable: %s", exc)
            return f"Home Assistant is not reachable: {exc}"
