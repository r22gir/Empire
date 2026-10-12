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

        # Every 15 minutes — expire stale pending crypto payments
        self.scheduler.add_job(
            self.expire_crypto_payments,
            CronTrigger(minute="*/15"),
            id="expire_crypto_payments",
            name="Expire Stale Crypto Payments",
        )

        # Every 5 minutes — Organizer due-date reminders through notify_founder
        self.scheduler.add_job(
            self.dispatch_organizer_reminders,
            CronTrigger(minute="*/5"),
            id="organizer_reminders",
            name="Organizer Due Reminders",
        )

        self.scheduler.start()
        jobs = self.scheduler.get_jobs()
        for job in jobs:
            logger.info(f"Scheduled: {job.name} → next run: {job.next_run_time}")

    async def send_daily_brief(self):
        """ONE daily brief, built from the DB (yesterday's desk results + live data)."""
        try:
            from app.services.max.daily_brief import send_consolidated_brief

            payload = await send_consolidated_brief()
            self._last_brief = payload.get("html") or payload.get("text_plain")
            logger.info("Daily brief generated and dispatched")
            return payload
        except Exception as e:
            logger.error(f"Daily brief failed: {e}")
            return None

    async def check_overdue_tasks(self):
        """Log overdue tasks to notification system (no auto-Telegram)."""
        try:
            from app.db.database import get_db
            now = datetime.now().strftime("%Y-%m-%d")
            with get_db() as db:
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
            from app.services.data_paths import quotes_data_dir

            quotes_dir = quotes_data_dir()
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
            completed = 0
            open_tasks = 0
            try:
                with get_db() as db:
                    completed = db.execute(
                        "SELECT COUNT(*) FROM tasks WHERE status = 'done' "
                        "AND completed_at >= datetime('now', '-7 days')"
                    ).fetchone()[0]
                    open_tasks = db.execute(
                        "SELECT COUNT(*) FROM tasks WHERE status IN ('todo','in_progress')"
                    ).fetchone()[0]
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
            # Sprint 1c: read MAX's memory.md from the canonical repo path.
            # Resolution order:
            #   1. MAX_MEMORY_PATH env var (explicit override)
            #   2. <canonical_repo>/max/memory.md (default — derived from
            #      this scheduler file's location, walks up to the repo root)
            #   3. ~/empire-repo/max/memory.md (legacy fallback during
            #      stale-fork retirement)
            memory_file = None
            env_path = os.getenv("MAX_MEMORY_PATH")
            if env_path:
                memory_file = Path(env_path)
            else:
                # backend/app/services/max/scheduler.py → repo root is 4 parents up.
                # No legacy fallback to ~/empire-repo; canonical only.
                canonical_repo = Path(__file__).resolve().parents[4]
                memory_file = canonical_repo / "max" / "memory.md"
            if not memory_file.exists():
                logger.warning(f"Brain sync: memory.md not found at {memory_file}")
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

            from app.services.data_paths import quotes_data_dir, brain_dir
            from app.services.max.desks.live_data import count_unreviewed_inbox

            quotes_dir = quotes_data_dir()
            quote_count = len(list(quotes_dir.glob("*.json"))) if quotes_dir.exists() else 0

            inbox_count = count_unreviewed_inbox()

            # Brain memories count
            brain_memories = 0
            try:
                import sqlite3
                brain_db = brain_dir() / "memories.db"
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
                main_py = Path(__file__).resolve().parents[3] / "main.py"
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

    async def dispatch_organizer_reminders(self):
        """Deliver persisted Organizer reminders through Max's notification system."""
        try:
            from app.db.database import get_db
            from app.services.organizer.reminders import dispatch_due_reminders
            with get_db() as conn:
                fired = dispatch_due_reminders(conn)
                try:
                    from app.services.organizer.waiting import dispatch_waiting_nudges
                    nudges = dispatch_waiting_nudges(conn)
                    if nudges.get("dispatched"):
                        logger.info("Organizer waiting drafts prepared: %s", nudges["dispatched"])
                except Exception as inner:
                    logger.error("Organizer waiting drafts failed: %s", inner)
                try:
                    from app.services.organizer.templates import spawn_due_recurring
                    spawned = spawn_due_recurring(conn)
                    if spawned.get("count"):
                        logger.info("Organizer recurring copies: %s", spawned["count"])
                except Exception as inner:
                    logger.error("Organizer recurrence spawn failed: %s", inner)
            if fired:
                logger.info("Organizer reminders dispatched: %s", len(fired))
        except Exception as e:
            logger.error(f"Organizer reminder dispatch failed: {e}")

    async def expire_crypto_payments(self):
        """Run every 15 minutes to expire stale pending crypto payments."""
        try:
            from app.database import SessionLocal
            from app.services.crypto_payment_service import CryptoPaymentService
            db = SessionLocal()
            try:
                count = CryptoPaymentService.expire_stale_payments(db)
                if count > 0:
                    logger.info(f"Crypto expiry job: {count} stale payment(s) marked expired")
                    from app.routers.notifications import notify_founder
                    notify_founder(
                        "Business", "business_event",
                        f"{count} Crypto Payment(s) Expired",
                        f"{count} pending crypto payment(s) have expired and been marked expired.",
                        "low"
                    )
            finally:
                db.close()
        except Exception as e:
            logger.error(f"Crypto payment expiry job failed: {e}")

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
