"""
TelegramBot — Telegram integration for EmpireBox agents.

Sends notifications and receives commands via a Telegram bot.
Requires TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID environment variables.
"""

import logging
import os
from typing import Any, Dict, Optional

from ..base import Agent, AgentStatus

logger = logging.getLogger(__name__)

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")


class TelegramBot(Agent):
    """Sends notifications and receives commands via Telegram."""

    name = "telegram_bot"
    description = "Send notifications and receive commands via Telegram"
    products = ["all"]
    status = AgentStatus.IDLE

    async def run_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        action = task.get("action", "send")
        message = task.get("message", "")
        chat_id = task.get("chat_id", TELEGRAM_CHAT_ID)

        if not TELEGRAM_TOKEN:
            return {"success": False, "error": "TELEGRAM_BOT_TOKEN not configured"}
        if not chat_id:
            return {"success": False, "error": "TELEGRAM_CHAT_ID not configured"}

        if action == "send":
            return await self._send_message(chat_id, message)
        return {"success": False, "error": f"Unknown Telegram action: {action}"}

    async def _send_message(self, chat_id: str, text: str) -> Dict[str, Any]:
        try:
            import httpx
            url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
            payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload)
                resp.raise_for_status()
                return {"success": True, "message_id": resp.json().get("result", {}).get("message_id")}
        except Exception as exc:  # noqa: BLE001
            logger.error("Telegram send failed: %s", exc)
            return {"success": False, "error": str(exc)}

    async def get_stats(self) -> Dict[str, Any]:
        return {
            "agent": self.name,
            "status": self.status.value,
            "configured": bool(TELEGRAM_TOKEN and TELEGRAM_CHAT_ID),
        }
