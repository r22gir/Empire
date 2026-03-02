"""Push notification system for EmpireBox system events."""

import asyncio
import logging
import time
from typing import Optional

import psutil
from telegram import Bot
from telegram.error import TelegramError

logger = logging.getLogger(__name__)

# Thresholds for system alerts
CPU_THRESHOLD = 90.0      # percent
DISK_THRESHOLD = 90.0     # percent
MEMORY_THRESHOLD = 90.0   # percent


class NotificationService:
    """Monitors system resources and pushes alerts to allowed Telegram users."""

    def __init__(self, bot: Bot, config: dict, allowed_users: list[int]):
        self._bot = bot
        self._enabled: bool = config.get("enabled", True)
        self._system_alerts: bool = config.get("system_alerts", True)
        self._product_crashes: bool = config.get("product_crashes", True)
        self._daily_summary: bool = config.get("daily_summary", False)
        self._daily_summary_time: str = config.get("daily_summary_time", "09:00")
        self._allowed_users = allowed_users
        self._last_alert_time: dict[str, float] = {}
        self._alert_cooldown = 300  # seconds between repeated alerts

    # ── Public helpers ─────────────────────────────────────────────────────

    async def send_to_all(self, text: str) -> None:
        """Send *text* to every allowed user."""
        for uid in self._allowed_users:
            try:
                await self._bot.send_message(chat_id=uid, text=text)
            except TelegramError as exc:
                logger.warning("Could not notify user %s: %s", uid, exc)

    async def notify_product_crash(self, product: str) -> None:
        """Send a product-crash alert if notifications are enabled."""
        if not self._enabled or not self._product_crashes:
            return
        if not self._cooldown_ok(f"crash:{product}"):
            return
        await self.send_to_all(f"🚨 *Product crash detected:* `{product}`")

    async def notify_backup_complete(self, success: bool, detail: str = "") -> None:
        """Send a backup-completion notification."""
        if not self._enabled:
            return
        icon = "✅" if success else "❌"
        msg = f"{icon} *Backup {'completed' if success else 'failed'}.*"
        if detail:
            msg += f"\n{detail}"
        await self.send_to_all(msg)

    # ── Background monitoring loop ─────────────────────────────────────────

    async def start_monitoring(self) -> None:
        """Run the background system-alert polling loop."""
        if not self._enabled or not self._system_alerts:
            return
        asyncio.create_task(self._monitor_loop())

    async def _monitor_loop(self) -> None:
        while True:
            await asyncio.sleep(60)
            await self._check_system_resources()

    async def _check_system_resources(self) -> None:
        try:
            cpu = psutil.cpu_percent(interval=1)
            if cpu >= CPU_THRESHOLD and self._cooldown_ok("cpu"):
                await self.send_to_all(
                    f"⚠️ *High CPU usage:* {cpu:.1f}%"
                )

            mem = psutil.virtual_memory().percent
            if mem >= MEMORY_THRESHOLD and self._cooldown_ok("memory"):
                await self.send_to_all(
                    f"⚠️ *High memory usage:* {mem:.1f}%"
                )

            disk = psutil.disk_usage("/").percent
            if disk >= DISK_THRESHOLD and self._cooldown_ok("disk"):
                await self.send_to_all(
                    f"⚠️ *Low disk space:* {disk:.1f}% used"
                )
        except Exception as exc:  # noqa: BLE001
            logger.error("Resource monitoring error: %s", exc)

    # ── Internal helpers ───────────────────────────────────────────────────

    def _cooldown_ok(self, key: str) -> bool:
        now = time.monotonic()
        if now - self._last_alert_time.get(key, 0) >= self._alert_cooldown:
            self._last_alert_time[key] = now
            return True
        return False
