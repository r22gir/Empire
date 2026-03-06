"""
MAX Proactive Monitor — Background loop that checks system health,
overdue tasks, and inbox items. Sends Telegram alerts automatically.
Runs every 15 minutes inside the FastAPI process.
"""
import logging
import asyncio
from datetime import datetime
from pathlib import Path

from app.config.business_config import biz

logger = logging.getLogger("max.monitor")

CHECK_INTERVAL = 900  # 15 minutes


class MaxMonitor:
    def __init__(self):
        self._running = False
        self._task: asyncio.Task | None = None
        self._sent_today: dict[str, str] = {}  # alert_key -> date, dedup within same day

    async def start(self):
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info(f"Monitor started (interval: {CHECK_INTERVAL}s)")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Monitor stopped")

    async def _loop(self):
        # Wait 60s after startup before first check
        await asyncio.sleep(60)
        while self._running:
            try:
                await self._run_checks()
            except Exception as e:
                logger.error(f"Monitor check failed: {e}")
            await asyncio.sleep(CHECK_INTERVAL)

    async def _run_checks(self):
        """Run all monitoring checks."""
        alerts = []

        # 1. Overdue tasks
        overdue = await self._check_overdue_tasks()
        if overdue:
            alerts.append(overdue)

        # 2. Unread inbox
        inbox = self._check_inbox()
        if inbox:
            alerts.append(inbox)

        # 3. System health
        health = self._check_system_health()
        if health:
            alerts.append(health)

        if not alerts:
            return

        # Deduplicate: only send each alert type once per day
        today = datetime.now().strftime("%Y-%m-%d")
        new_alerts = []
        for alert in alerts:
            # Use first 40 chars as dedup key (captures the alert type)
            key = alert.strip()[:40]
            if self._sent_today.get(key) == today:
                continue
            self._sent_today[key] = today
            new_alerts.append(alert)

        # Purge stale entries from previous days
        self._sent_today = {k: v for k, v in self._sent_today.items() if v == today}

        if not new_alerts:
            return

        # Send combined alert
        from app.services.max.telegram_bot import telegram_bot
        if not telegram_bot.is_configured:
            return

        msg = f"<b>🔔 {biz.ai_assistant_name} Monitor Alert</b>\n"
        msg += f"<i>{datetime.now().strftime('%I:%M %p')}</i>\n"
        msg += "\n".join(new_alerts)

        await telegram_bot.send_message(msg)
        logger.info(f"Monitor alert sent ({len(new_alerts)} check(s))")

    async def _check_overdue_tasks(self) -> str | None:
        """Check for overdue tasks."""
        try:
            from app.db.database import get_db
            now = datetime.now().strftime("%Y-%m-%d")
            db = get_db()
            cursor = db.execute(
                "SELECT COUNT(*) FROM tasks "
                "WHERE status IN ('todo','in_progress') "
                "AND due_date IS NOT NULL AND due_date < ?",
                (now,)
            )
            count = cursor.fetchone()[0]
            if count > 0:
                return f"\n⏰ <b>{count} overdue task(s)</b> — reply /tasks to review"
        except Exception as e:
            logger.debug(f"Overdue check error: {e}")
        return None

    def _check_inbox(self) -> str | None:
        """Check for unread inbox items."""
        try:
            inbox_dir = Path.home() / "Empire" / "data" / "inbox"
            if not inbox_dir.exists():
                return None
            count = len(list(inbox_dir.glob("*.json")))
            if count > 5:
                return f"\n📥 <b>{count} inbox items</b> waiting for review"
        except Exception as e:
            logger.debug(f"Inbox check error: {e}")
        return None

    def _check_system_health(self) -> str | None:
        """Check CPU, RAM, disk thresholds."""
        try:
            import psutil
            warnings = []
            ram = psutil.virtual_memory()
            if ram.percent > 85:
                warnings.append(f"RAM {ram.percent}%")
            disk = psutil.disk_usage("/")
            if disk.percent > 90:
                warnings.append(f"Disk {disk.percent}%")
            cpu = psutil.cpu_percent(interval=1)
            if cpu > 90:
                warnings.append(f"CPU {cpu}%")
            if warnings:
                return f"\n⚠️ <b>System:</b> {', '.join(warnings)} — high usage"
        except Exception as e:
            logger.debug(f"Health check error: {e}")
        return None

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "interval_seconds": CHECK_INTERVAL,
        }


# Singleton
max_monitor = MaxMonitor()
