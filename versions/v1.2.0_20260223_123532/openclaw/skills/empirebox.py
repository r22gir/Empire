"""
EmpireBox integration skill for OpenClaw.

Optional plugin that connects OpenClaw to the EmpireBox platform.
Requires EmpireBox backend to be running and configured.
"""

import logging
import os
from typing import Dict, Any

import httpx

from .base import Skill

logger = logging.getLogger(__name__)

EMPIREBOX_BASE_URL = os.getenv("EMPIREBOX_URL", "http://localhost:8000")


class EmpireBoxSkill(Skill):
    """EmpireBox integration skill: manage Forge products, health checks, backups."""

    name = "empirebox"
    description = "Manage EmpireBox Forge products: list, start, stop, health, backups, logs"
    triggers = [
        "list products",
        "forge",
        "start service",
        "stop service",
        "health check",
        "backup",
        "view logs",
        "revenue",
        "orders",
        "tickets",
    ]

    async def execute(self, intent: str, params: Dict[str, Any]) -> str:
        action = params.get("action", "status")
        service = params.get("service", "all")

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                if action == "status":
                    resp = await client.get(f"{EMPIREBOX_BASE_URL}/health")
                    return f"EmpireBox status: {resp.json()}"
                if action == "list":
                    resp = await client.get(f"{EMPIREBOX_BASE_URL}/api/products")
                    return f"Forge products: {resp.json()}"
                if action == "backup":
                    resp = await client.post(f"{EMPIREBOX_BASE_URL}/api/backup")
                    return f"Backup result: {resp.json()}"
                if action == "logs":
                    resp = await client.get(f"{EMPIREBOX_BASE_URL}/api/logs/{service}")
                    return f"Logs for {service}: {resp.text[:500]}"
                return f"Unknown EmpireBox action: {action}"
        except httpx.RequestError as exc:
            logger.warning("EmpireBox unreachable: %s", exc)
            return f"EmpireBox is not reachable at {EMPIREBOX_BASE_URL}: {exc}"
