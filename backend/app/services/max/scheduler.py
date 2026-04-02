"""
MAX Scheduler — Persistent background scheduler for autonomous operations.
Uses APScheduler to run recurring tasks: daily briefs, task checks, followups, reports.
Each action calls existing tools/functions — no new AI logic needed.
"""
import logging
import asyncio
import os
from datetime import datetime
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.config.business_config import biz

logger = logging.getLogger("max.scheduler")


class MaxScheduler:
    def __init__(self):
        self.scheduler = AsyncIOScheduler(timezone=biz.timezone)
        self._started = False
        self._last_brief = None  # Cached for on-demand retrieval

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

        # Nightly brain sync — 11:00 PM (auto-update memory.md)
        self.scheduler.add_job(
            self.brain_sync,
            CronTrigger(hour=23, minute=0),
            id="brain_sync",
            name="Nightly Brain Sync",
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
            inbox_dir = Path.home() / "empire-repo" / "backend" / "data" / "inbox"
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

            # Log to notifications
            from app.routers.notifications import notify_founder
            notify_founder("MAX", "system_alert", "Morning Brief", brief, "low")
            self._last_brief = brief

            # Send morning brief email FROM max@empirebox.store TO founder
            try:
                from app.services.max.email_service import EmailService
                svc = EmailService()
                if svc.is_configured:
                    founder_email = os.environ.get("FOUNDER_EMAIL", "empirebox2026@gmail.com")
                    # Convert Telegram HTML to email-friendly HTML
                    email_body = brief.replace("\n", "<br>")
                    svc.send(
                        to=founder_email,
                        subject=f"☀️ Empire Morning Brief — {now.strftime('%A, %B %d')}",
                        body_html=email_body,
                    )
                    logger.info(f"Morning brief emailed to {founder_email}")
            except Exception as e:
                logger.warning(f"Morning brief email failed: {e}")

            logger.info("Daily brief generated and dispatched")
        except Exception as e:
            logger.error(f"Daily brief failed: {e}")

    async def check_overdue_tasks(self):
        """Log overdue tasks to notification system (no auto-Telegram)."""
        try:
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

            msg = f"{len(overdue)} Overdue Task(s): "
            msg += ", ".join(f"{row[1]} (due {row[2]})" for row in overdue[:5])

            from app.routers.notifications import notify_founder
            notify_founder("MAX", "system_alert", f"{len(overdue)} Overdue Tasks", msg, "medium")
            logger.info(f"Overdue logged: {len(overdue)} tasks")
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

            quotes_dir = Path.home() / "empire-repo" / "backend" / "data" / "quotes"
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

            from app.routers.notifications import notify_founder
            notify_founder("Business", "business_event", f"{len(stale_quotes)} Stale Quotes", msg, "medium", {"type": "sales_followup"})
            logger.info(f"Sales followup logged: {len(stale_quotes)} stale quotes")
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

            from app.routers.notifications import notify_founder
            notify_founder("MAX", "system_alert", "Weekly Report", msg, "low")
            logger.info("Weekly report logged (on-demand)")
        except Exception as e:
            logger.error(f"Weekly report failed: {e}")

    async def brain_sync(self):
        """Nightly auto-update of memory.md with current system state.
        Catalogs all endpoints, DB table counts, desk statuses, and recent activity.
        This keeps MAX's persistent memory current without manual edits."""
        try:
            from pathlib import Path
            import json
            import os
            import re

            now = datetime.now()
            memory_file = Path.home() / "empire-repo" / "max" / "memory.md"
            if not memory_file.exists():
                logger.warning("Brain sync: memory.md not found")
                return

            content = memory_file.read_text(encoding="utf-8")

            # ── Gather live system data ──────────────────────────────

            # DB table counts
            db_stats = {}
            try:
                from app.db.database import get_db
                with get_db() as conn:
                    for table in ["tasks", "customers", "invoices", "payments", "expenses",
                                  "inventory_items", "vendors", "contacts", "desk_configs", "task_activity"]:
                        try:
                            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
                            db_stats[table] = count
                        except Exception:
                            db_stats[table] = "N/A"
            except Exception as e:
                logger.error(f"Brain sync DB stats failed: {e}")

            # Quote file count
            quotes_dir = Path.home() / "empire-repo" / "backend" / "data" / "quotes"
            quote_count = len(list(quotes_dir.glob("*.json"))) if quotes_dir.exists() else 0

            # Inbox count
            inbox_dir = Path.home() / "empire-repo" / "backend" / "data" / "inbox"
            inbox_count = len(list(inbox_dir.glob("*.json"))) if inbox_dir.exists() else 0

            # Brain memories count
            brain_memories = 0
            try:
                import sqlite3
                brain_db = Path.home() / "empire-repo" / "backend" / "data" / "brain" / "memories.db"
                if brain_db.exists():
                    bconn = sqlite3.connect(str(brain_db))
                    brain_memories = bconn.execute("SELECT COUNT(*) FROM memories").fetchone()[0]
                    bconn.close()
            except Exception:
                pass

            # System stats
            sys_info = ""
            try:
                import psutil
                cpu = psutil.cpu_percent(interval=0.5)
                ram = psutil.virtual_memory()
                disk = psutil.disk_usage("/")
                sys_info = f"CPU: {cpu}% | RAM: {ram.percent}% ({ram.used // (1024**3)}GB/{ram.total // (1024**3)}GB) | Disk: {disk.percent}% ({disk.used // (1024**3)}GB/{disk.total // (1024**3)}GB)"
            except Exception:
                sys_info = "unavailable"

            # Backend router count (approximate from main.py)
            router_count = 0
            try:
                main_py = Path.home() / "empire-repo" / "backend" / "app" / "main.py"
                if main_py.exists():
                    router_count = main_py.read_text().count("load_router(")
            except Exception:
                pass

            # Active tasks summary
            active_tasks_summary = ""
            try:
                from app.db.database import get_db
                with get_db() as conn:
                    active = conn.execute(
                        "SELECT desk, COUNT(*) as cnt FROM tasks WHERE status IN ('todo','in_progress') GROUP BY desk ORDER BY cnt DESC LIMIT 5"
                    ).fetchall()
                    if active:
                        active_tasks_summary = ", ".join(f"{r[0]}: {r[1]}" for r in active)
                    else:
                        active_tasks_summary = "none"
            except Exception:
                active_tasks_summary = "unavailable"

            # Recent finance summary
            finance_summary = ""
            try:
                from app.db.database import get_db
                with get_db() as conn:
                    rev = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM payments").fetchone()[0]
                    exp = conn.execute("SELECT COALESCE(SUM(amount), 0) FROM expenses").fetchone()[0]
                    outstanding = conn.execute(
                        "SELECT COALESCE(SUM(balance_due), 0) FROM invoices WHERE status IN ('sent','partial','overdue')"
                    ).fetchone()[0]
                    finance_summary = f"Revenue: ${rev:,.0f} | Expenses: ${exp:,.0f} | Outstanding: ${outstanding:,.0f} | Net: ${rev - exp:,.0f}"
            except Exception:
                finance_summary = "unavailable"

            # ── Build the auto-sync block ────────────────────────────

            sync_block = (
                f"\n## AUTO-SYNC (updated nightly by brain_sync)\n"
                f"Last sync: {now.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"### Database Counts (empire.db)\n"
            )
            for table, count in db_stats.items():
                sync_block += f"- {table}: {count}\n"

            sync_block += (
                f"\n### File Storage\n"
                f"- Quote JSONs: {quote_count}\n"
                f"- Inbox messages: {inbox_count}\n"
                f"- Brain memories: {brain_memories}\n"
                f"\n### Finance Snapshot\n"
                f"- {finance_summary}\n"
                f"\n### Active Tasks by Desk\n"
                f"- {active_tasks_summary}\n"
                f"\n### System\n"
                f"- {sys_info}\n"
                f"- Backend routers loaded: {router_count}\n"
            )

            # ── Replace or append the auto-sync section ──────────────

            marker = "## AUTO-SYNC (updated nightly by brain_sync)"
            if marker in content:
                # Replace existing section (everything from marker to next ## or end)
                pattern = re.compile(
                    r"\n## AUTO-SYNC \(updated nightly by brain_sync\).*?(?=\n## (?!AUTO-SYNC)|\Z)",
                    re.DOTALL
                )
                content = pattern.sub(sync_block, content)
            else:
                # Append at end
                content = content.rstrip() + "\n" + sync_block

            memory_file.write_text(content, encoding="utf-8")

            # Also copy to the backup location
            backup = Path.home() / "empire-repo" / "backend" / "data" / "max" / "memory.md"
            backup.parent.mkdir(parents=True, exist_ok=True)
            backup.write_text(content, encoding="utf-8")

            logger.info(f"Brain sync complete — {len(db_stats)} tables, {quote_count} quotes, {brain_memories} memories")

            # Log brain sync — no auto-Telegram
            try:
                from app.routers.notifications import notify_founder
                notify_founder("MAX", "task_complete", "Brain Sync Complete",
                    f"DB: {', '.join(f'{k}={v}' for k, v in list(db_stats.items())[:5])}. "
                    f"{finance_summary}. Active tasks: {active_tasks_summary}",
                    "low")
            except Exception:
                pass

        except Exception as e:
            logger.error(f"Brain sync failed: {e}")

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
