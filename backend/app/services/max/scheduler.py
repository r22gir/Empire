"""
MAX Scheduler — Persistent background scheduler for autonomous operations.
Uses APScheduler to run recurring tasks: daily briefs, task checks, followups, reports.
Each action calls existing tools/functions — no new AI logic needed.
"""
import logging
import asyncio
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config.business_config import biz

logger = logging.getLogger("max.scheduler")


class MaxScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=biz.timezone)
        self._started = False

    async def start(self):
        if self._started:
            return
        self._started = True

        # Daily morning brief — 8:00 AM
        self.scheduler.add_job(
            self.send_daily_brief,
            CronTrigger(hour=8, minute=0),
            id="daily_brief",
            name="Daily Morning Brief",
        )

        # Check overdue tasks — 9:00 AM
        self.scheduler.add_job(
            self.check_overdue_tasks,
            CronTrigger(hour=9, minute=0),
            id="check_tasks",
            name="Overdue Task Check",
        )

        # Sales followup check — Monday 10:00 AM
        self.scheduler.add_job(
            self.run_sales_followup,
            CronTrigger(day_of_week="mon", hour=10, minute=0),
            id="sales_followup",
            name="Weekly Sales Followup",
        )

        # Weekly report — Friday 5:00 PM
        self.scheduler.add_job(
            self.send_weekly_report,
            CronTrigger(day_of_week="fri", hour=17, minute=0),
            id="weekly_report",
            name="Weekly Report",
        )

        self.scheduler.start()
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            logger.info(f"Scheduled: {job.name} → next run: {job.next_run_time}")

    async def send_daily_brief(self):
        """Compile and send morning brief via Telegram."""
        try:
            from app.services.max.telegram_bot import telegram_bot
            if not telegram_bot.is_configured:
                return

            # Gather stats
            import psutil
            from pathlib import Path
            import json

            now = datetime.now()
            cpu = psutil.cpu_percent(interval=1)
            ram = psutil.virtual_memory()
            disk = psutil.disk_usage("/")

            # Count open tasks
            open_tasks = 0
            overdue_tasks = 0
            try:
                from app.db.database import get_db
                db = get_db()
                cursor = db.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('todo','in_progress')")
                open_tasks = cursor.fetchone()[0]
                cursor = db.execute(
                    "SELECT COUNT(*) FROM tasks WHERE status IN ('todo','in_progress') "
                    "AND due_date IS NOT NULL AND due_date < ?",
                    (now.strftime("%Y-%m-%d"),)
                )
                overdue_tasks = cursor.fetchone()[0]
            except Exception:
                pass

            # Count inbox items
            inbox_count = 0
            inbox_dir = Path.home() / "Empire" / "data" / "inbox"
            if inbox_dir.exists():
                inbox_count = len(list(inbox_dir.glob("*.json")))

            brief = (
                f"<b>☀️ {biz.business_name} Morning Brief</b>\n"
                f"<i>{now.strftime('%A, %B %d, %Y')}</i>\n\n"
                f"📋 <b>Tasks:</b> {open_tasks} open"
            )
            if overdue_tasks:
                brief += f" ({overdue_tasks} overdue ⚠️)"
            brief += (
                f"\n📥 <b>Inbox:</b> {inbox_count} items\n"
                f"💻 <b>System:</b> CPU {cpu}% | RAM {ram.percent}% | Disk {disk.percent}%\n"
            )

            if overdue_tasks:
                brief += f"\n⚠️ {overdue_tasks} task(s) overdue — check /tasks"
            if ram.percent > 85:
                brief += f"\n⚠️ RAM usage high ({ram.percent}%)"
            if disk.percent > 90:
                brief += f"\n⚠️ Disk usage high ({disk.percent}%)"

            await telegram_bot.send_message(brief)
            logger.info("Daily brief sent")
        except Exception as e:
            logger.error(f"Daily brief failed: {e}")

    async def check_overdue_tasks(self):
        """Alert on overdue tasks via Telegram."""
        try:
            from app.services.max.telegram_bot import telegram_bot
            if not telegram_bot.is_configured:
                return

            from app.db.database import get_db
            now = datetime.now().strftime("%Y-%m-%d")
            db = get_db()
            cursor = db.execute(
                "SELECT id, title, due_date, desk FROM tasks "
                "WHERE status IN ('todo','in_progress') AND due_date IS NOT NULL AND due_date < ? "
                "ORDER BY due_date LIMIT 10",
                (now,)
            )
            overdue = cursor.fetchall()
            if not overdue:
                return

            msg = f"<b>⏰ {len(overdue)} Overdue Task(s)</b>\n\n"
            for row in overdue:
                msg += f"• <b>{row[1]}</b> (due {row[2]}, desk: {row[3]})\n"
            msg += "\nReply /tasks to manage"

            await telegram_bot.send_message(msg)
            logger.info(f"Overdue alert: {len(overdue)} tasks")
        except Exception as e:
            logger.error(f"Overdue check failed: {e}")

    async def run_sales_followup(self):
        """Check for quotes needing followup (older than N days without response)."""
        try:
            from app.services.max.telegram_bot import telegram_bot
            if not telegram_bot.is_configured:
                return

            from pathlib import Path
            import json

            quotes_dir = Path.home() / "Empire" / "data" / "quotes"
            if not quotes_dir.exists():
                return

            stale_quotes = []
            cutoff = datetime.now().timestamp() - (biz.followup_days_overdue * 86400)

            for qf in quotes_dir.glob("*.json"):
                if qf.name.startswith("_"):
                    continue
                try:
                    data = json.loads(qf.read_text())
                    status = data.get("status", "")
                    created = data.get("created_at", "")
                    if status in ("proposal", "draft") and created:
                        created_ts = datetime.fromisoformat(created).timestamp()
                        if created_ts < cutoff:
                            stale_quotes.append({
                                "id": data.get("quote_number", qf.stem),
                                "customer": data.get("customer", {}).get("name", "Unknown"),
                                "total": data.get("total", 0),
                                "created": created[:10],
                            })
                except Exception:
                    continue

            if not stale_quotes:
                return

            msg = f"<b>📞 Sales Followup — {len(stale_quotes)} stale quote(s)</b>\n\n"
            for q in stale_quotes[:5]:
                msg += f"• <b>{q['id']}</b> — {q['customer']} (${q['total']:.0f}, created {q['created']})\n"
            if len(stale_quotes) > 5:
                msg += f"\n...and {len(stale_quotes) - 5} more"

            await telegram_bot.send_message(msg)
            logger.info(f"Sales followup: {len(stale_quotes)} stale quotes")
        except Exception as e:
            logger.error(f"Sales followup failed: {e}")

    async def send_weekly_report(self):
        """Send end-of-week summary via Telegram."""
        try:
            from app.services.max.telegram_bot import telegram_bot
            if not telegram_bot.is_configured:
                return

            from app.db.database import get_db
            db = get_db()

            # Tasks completed this week
            completed = 0
            try:
                cursor = db.execute(
                    "SELECT COUNT(*) FROM tasks WHERE status = 'done' "
                    "AND completed_at >= datetime('now', '-7 days')"
                )
                completed = cursor.fetchone()[0]
            except Exception:
                pass

            # Tasks still open
            open_tasks = 0
            try:
                cursor = db.execute("SELECT COUNT(*) FROM tasks WHERE status IN ('todo','in_progress')")
                open_tasks = cursor.fetchone()[0]
            except Exception:
                pass

            now = datetime.now()
            msg = (
                f"<b>📊 {biz.business_name} Weekly Report</b>\n"
                f"<i>Week ending {now.strftime('%B %d, %Y')}</i>\n\n"
                f"✅ Tasks completed: {completed}\n"
                f"📋 Tasks open: {open_tasks}\n"
                f"\nHave a great weekend! 🎉"
            )

            await telegram_bot.send_message(msg)
            logger.info("Weekly report sent")
        except Exception as e:
            logger.error(f"Weekly report failed: {e}")

    def get_status(self) -> dict:
        """Return scheduler status for health checks."""
        if not self._started:
            return {"running": False, "jobs": []}
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                "id": job.id,
                "name": job.name,
                "next_run": str(job.next_run_time) if job.next_run_time else None,
            })
        return {"running": self.scheduler.running, "jobs": jobs}


# Singleton
max_scheduler = MaxScheduler()
