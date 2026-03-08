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

CHECK_INTERVAL = 3600  # 1 hour


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

        markup = {"inline_keyboard": [[
            {"text": "📋 Full Details", "callback_data": "monitor_details"},
            {"text": "✅ Dismiss", "callback_data": "monitor_dismiss"},
        ]]}
        await telegram_bot.send_message(msg, reply_markup=markup)
        logger.info(f"Monitor alert sent ({len(new_alerts)} check(s))")

    async def _check_overdue_tasks(self) -> str | None:
        """Check for overdue tasks — lists task names."""
        try:
            from app.db.database import get_db
            now = datetime.now().strftime("%Y-%m-%d")
            db = get_db()
            cursor = db.execute(
                "SELECT title, due_date, desk_id FROM tasks "
                "WHERE status IN ('todo','in_progress') "
                "AND due_date IS NOT NULL AND due_date < ? "
                "ORDER BY due_date LIMIT 5",
                (now,)
            )
            rows = cursor.fetchall()
            if not rows:
                return None
            lines = []
            for row in rows:
                title = row[0] if isinstance(row, (list, tuple)) else row["title"]
                due = row[1] if isinstance(row, (list, tuple)) else row["due_date"]
                desk = row[2] if isinstance(row, (list, tuple)) else row.get("desk_id", "")
                desk_tag = f" [{desk}]" if desk else ""
                lines.append(f"  • {title}{desk_tag} (due {due})")
            extra = f"\n  + {len(rows)}+ more" if len(rows) == 5 else ""
            return f"\n⏰ <b>{len(rows)} overdue task(s):</b>\n" + "\n".join(lines) + extra
        except Exception as e:
            logger.debug(f"Overdue check error: {e}")
        return None

    def _check_inbox(self) -> str | None:
        """Check for unread inbox items — only alert at 15+."""
        try:
            inbox_dir = Path.home() / "empire-repo" / "backend" / "data" / "inbox"
            if not inbox_dir.exists():
                return None
            count = len(list(inbox_dir.glob("*.json")))
            if count > 15:
                return f"\n📥 <b>{count} inbox items</b> piling up — review when you can"
        except Exception as e:
            logger.debug(f"Inbox check error: {e}")
        return None

    def _check_system_health(self) -> str | None:
        """Check CPU, RAM, disk — higher thresholds to reduce noise."""
        try:
            import psutil
            warnings = []
            ram = psutil.virtual_memory()
            if ram.percent > 92:
                used_gb = ram.used / (1024**3)
                total_gb = ram.total / (1024**3)
                warnings.append(f"RAM {ram.percent}% ({used_gb:.1f}/{total_gb:.1f} GB)")
            disk = psutil.disk_usage("/")
            if disk.percent > 95:
                free_gb = disk.free / (1024**3)
                warnings.append(f"Disk {disk.percent}% ({free_gb:.1f} GB free)")
            cpu = psutil.cpu_percent(interval=2)
            if cpu > 95:
                warnings.append(f"CPU {cpu}%")
            if warnings:
                return f"\n⚠️ <b>System critical:</b> {', '.join(warnings)}"
        except Exception as e:
            logger.debug(f"Health check error: {e}")
        return None

    async def get_full_report(self) -> str:
        """Generate a detailed report for the 'Full Details' callback."""
        import psutil
        lines = [f"<b>📊 {biz.ai_assistant_name} System Report</b>", f"<i>{datetime.now().strftime('%b %d, %I:%M %p')}</i>\n"]

        # System stats
        ram = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        cpu = psutil.cpu_percent(interval=1)
        lines.append(f"<b>System:</b>")
        lines.append(f"  CPU: {cpu}%")
        lines.append(f"  RAM: {ram.percent}% ({ram.used / (1024**3):.1f}/{ram.total / (1024**3):.1f} GB)")
        lines.append(f"  Disk: {disk.percent}% ({disk.free / (1024**3):.1f} GB free)")

        # Tasks
        try:
            from app.db.database import get_db
            db = get_db()
            now = datetime.now().strftime("%Y-%m-%d")
            overdue = db.execute(
                "SELECT title, due_date, desk_id FROM tasks "
                "WHERE status IN ('todo','in_progress') AND due_date IS NOT NULL AND due_date < ? "
                "ORDER BY due_date LIMIT 10", (now,)
            ).fetchall()
            active = db.execute(
                "SELECT COUNT(*) FROM tasks WHERE status IN ('todo','in_progress')"
            ).fetchone()[0]
            lines.append(f"\n<b>Tasks:</b> {active} active")
            if overdue:
                lines.append(f"  ⏰ {len(overdue)} overdue:")
                for row in overdue:
                    t = row[0] if isinstance(row, (list, tuple)) else row["title"]
                    d = row[1] if isinstance(row, (list, tuple)) else row["due_date"]
                    desk = row[2] if isinstance(row, (list, tuple)) else row.get("desk_id", "")
                    lines.append(f"    • {t} (due {d}){f' [{desk}]' if desk else ''}")
            else:
                lines.append("  ✅ No overdue tasks")
        except Exception:
            lines.append("\n<b>Tasks:</b> unable to query")

        # Inbox
        inbox_dir = Path.home() / "empire-repo" / "backend" / "data" / "inbox"
        inbox_count = len(list(inbox_dir.glob("*.json"))) if inbox_dir.exists() else 0
        lines.append(f"\n<b>Inbox:</b> {inbox_count} items")

        # Quotes today
        try:
            quotes_dir = Path.home() / "empire-repo" / "backend" / "data" / "quotes"
            today_str = datetime.now().strftime("%Y-%m-%d")
            today_quotes = 0
            if quotes_dir.exists():
                import json as _json
                for qf in quotes_dir.glob("*.json"):
                    try:
                        q = _json.loads(qf.read_text())
                        if q.get("created_at", "").startswith(today_str):
                            today_quotes += 1
                    except Exception:
                        pass
            lines.append(f"\n<b>Quotes today:</b> {today_quotes}")
        except Exception:
            pass

        return "\n".join(lines)

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "interval_seconds": CHECK_INTERVAL,
        }


# Singleton
max_monitor = MaxMonitor()
