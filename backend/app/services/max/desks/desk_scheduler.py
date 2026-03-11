"""
Desk Scheduler — Autonomous daily tasks for AI desks.
Fires real tasks at scheduled times, executes them with AI,
stores results, and sends Telegram summaries to the founder.
Also handles event-driven triggers (new quotes, stale projects, service down).
"""
import asyncio
import logging
import socket
from datetime import datetime

logger = logging.getLogger("max.desks.scheduler")

# Schedule: (hour, minute, desk_id, task_title, task_description)
DAILY_SCHEDULE = [
    (8, 0, "finance", "Morning Invoice Audit",
     "Check all outstanding invoices. Flag any overdue more than 7 days. "
     "List each by client name, amount, and days overdue. Suggest collection actions."),

    (8, 30, "it", "Morning Service Health Check",
     "Check which Empire services are actually running right now. "
     "Test ports 8000, 3000, 3001, 3002, 3005, 3009, 7878, 11434. "
     "Report which are UP and which are DOWN. Flag any issues."),

    (9, 0, "sales", "Stale Quote Follow-Up Scan",
     "Review all quotes and proposals older than 3 days without a client response. "
     "For each stale quote, draft a polite follow-up message. "
     "Prioritize by deal value. Include specific next actions."),

    (9, 30, "support", "Open Ticket Summary",
     "Audit all open support tickets and client issues. "
     "Summarize status of each, flag urgent ones, suggest resolutions. "
     "Note any tickets that have been open more than 48 hours."),

    (10, 0, "marketing", "Daily Social Media Post",
     "Draft an Instagram post for Empire Workroom today. "
     "Topic: custom window treatments, home transformation, or client success. "
     "Include a compelling caption, relevant hashtags (20-25), and posting time recommendation. "
     "Make it specific and ready to post — not a template."),

    (10, 30, "forge", "Today's Pipeline Summary",
     "Summarize today's quote pipeline for Empire Workroom. "
     "List active quotes, pending measurements, upcoming installations, and production status. "
     "Flag anything that needs immediate attention. Include revenue at stake."),
]

# Empire services to health-check
EMPIRE_SERVICES = {
    "Backend API": 8000,
    "Empire App": 3000,
    "WorkroomForge": 3001,
    "LuxeForge": 3002,
    "Studio Portal": 3005,
    "Founder Dashboard": 3009,
    "OpenClaw": 7878,
    "Ollama": 11434,
}


class DeskScheduler:
    """Runs proactive scheduled tasks and event-driven triggers for AI desks."""

    def __init__(self):
        self._running = False
        self._last_run: dict[str, str] = {}  # task_key → last run date
        self._service_status: dict[str, bool] = {}  # port → last known status
        self._manager = None

    @property
    def manager(self):
        if self._manager is None:
            from .desk_manager import desk_manager
            self._manager = desk_manager
            self._manager.initialize()
        return self._manager

    async def start(self):
        """Start the scheduler loop."""
        self._running = True
        logger.info("Desk scheduler started — monitoring schedule and events")

        while self._running:
            try:
                now = datetime.now()
                today = now.strftime("%Y-%m-%d")

                # Check scheduled tasks
                for hour, minute, desk_id, title, description in DAILY_SCHEDULE:
                    task_key = f"{desk_id}:{title}"
                    if (
                        now.hour == hour
                        and now.minute == minute
                        and self._last_run.get(task_key) != today
                    ):
                        self._last_run[task_key] = today
                        asyncio.create_task(
                            self._execute_desk_task(desk_id, title, description, source="scheduler")
                        )

                # Event check: service health (every 5 min)
                if now.minute % 5 == 0:
                    task_key = f"health_monitor:{now.hour}:{now.minute}"
                    if self._last_run.get("health_monitor_tick") != f"{today}:{now.hour}:{now.minute}":
                        self._last_run["health_monitor_tick"] = f"{today}:{now.hour}:{now.minute}"
                        asyncio.create_task(self._check_service_health())

                # v6.0 Morning brief: 7:30 AM daily
                if now.hour == 7 and now.minute == 30:
                    brief_key = f"morning_brief:{today}"
                    if self._last_run.get("morning_brief") != brief_key:
                        self._last_run["morning_brief"] = brief_key
                        asyncio.create_task(self._generate_morning_brief())

                # v6.0 Weekly report: Monday 8:00 AM
                if now.weekday() == 0 and now.hour == 8 and now.minute == 0:
                    week_key = f"weekly_report:{today}"
                    if self._last_run.get("weekly_report") != week_key:
                        self._last_run["weekly_report"] = week_key
                        asyncio.create_task(self._generate_weekly_report())

                # v6.0 Pipeline executor: process pending subtasks (every 2 min)
                if now.minute % 2 == 0:
                    pl_tick = f"{today}:{now.hour}:{now.minute}"
                    if self._last_run.get("pipeline_tick") != pl_tick:
                        self._last_run["pipeline_tick"] = pl_tick
                        asyncio.create_task(self._run_pipeline_executor())

            except Exception as e:
                logger.warning(f"Scheduler tick error: {e}")

            await asyncio.sleep(60)  # Check every minute

    def stop(self):
        self._running = False
        logger.info("Desk scheduler stopped")

    async def _execute_desk_task(self, desk_id: str, title: str, description: str, source: str = "scheduler"):
        """Execute a task directly through the desk manager — no HTTP roundtrip."""
        logger.info(f"[Scheduler] Executing: {desk_id} → {title}")

        try:
            task = await self.manager.submit_task(
                title=title,
                description=description,
                priority="normal",
                source=source,
            )

            # If the desk completed it with canned/short text, enhance with AI
            if task.state.value == "completed" and source == "scheduler":
                result_len = len(task.result or "")
                if result_len < 500:
                    try:
                        desk = self.manager.get_desk(desk_id)
                        if desk:
                            ai_result = await desk.ai_execute_task(task)
                            if ai_result and len(ai_result) > result_len:
                                task.result = ai_result
                    except Exception as e:
                        logger.warning(f"AI enhancement failed for {desk_id}: {e}")

            # Store to database
            await self._persist_task(desk_id, task)

            # Send Telegram summary
            await self._notify_telegram(desk_id, title, task)

            logger.info(f"[Scheduler] Completed: {desk_id} → {title} ({task.state.value})")

        except Exception as e:
            logger.error(f"[Scheduler] Failed: {desk_id} → {title}: {e}")
            await self._notify_telegram_error(desk_id, title, str(e))

    async def _persist_task(self, desk_id: str, task):
        """Save task result to the SQLite tasks table."""
        try:
            from app.db.database import get_db
            import json

            with get_db() as conn:
                conn.execute(
                    """INSERT INTO tasks
                       (id, title, description, status, priority, desk,
                        created_by, source, tags, metadata)
                       VALUES (?, ?, ?, ?, ?, ?, 'scheduler', 'scheduler', ?, ?)""",
                    (
                        task.id,
                        task.title,
                        task.description[:500] if task.description else "",
                        "done" if task.state.value == "completed" else task.state.value,
                        task.priority.value if hasattr(task.priority, 'value') else "normal",
                        desk_id,
                        json.dumps([desk_id, "scheduler", "auto"]),
                        json.dumps({
                            "result": task.result[:2000] if task.result else None,
                            "source": "desk_scheduler",
                            "executed_at": datetime.now().isoformat(),
                        }),
                    ),
                )
                conn.execute(
                    """INSERT INTO task_activity (task_id, actor, action, detail)
                       VALUES (?, 'scheduler', 'auto_completed', ?)""",
                    (task.id, (task.result or "")[:500]),
                )
        except Exception as e:
            logger.warning(f"Failed to persist task {task.id}: {e}")

    async def _notify_telegram(self, desk_id: str, title: str, task):
        """Send task result summary to Telegram."""
        try:
            from app.services.max.telegram_bot import telegram_bot
            if not telegram_bot.is_configured:
                return

            desk = self.manager.get_desk(desk_id)
            agent = desk.agent_name if desk else desk_id
            status = task.state.value if hasattr(task.state, 'value') else str(task.state)
            icon = "✅" if status == "completed" else "⚠️" if status == "escalated" else "❌"

            # Truncate result for Telegram (4096 char limit)
            result_text = (task.result or "No output")[:800]

            msg = (
                f"{icon} <b>{agent} ({desk_id})</b>\n"
                f"<b>{title}</b>\n\n"
                f"{result_text}"
            )

            await telegram_bot.send_message(msg)
        except Exception as e:
            logger.warning(f"Telegram notification failed: {e}")

    async def _notify_telegram_error(self, desk_id: str, title: str, error: str):
        """Send error notification to Telegram."""
        try:
            from app.services.max.telegram_bot import telegram_bot
            if not telegram_bot.is_configured:
                return
            msg = f"❌ <b>Scheduler Error</b>\nDesk: {desk_id}\nTask: {title}\nError: {error[:300]}"
            await telegram_bot.send_message(msg)
        except Exception:
            pass

    async def _check_service_health(self):
        """Check all Empire services — alert on status changes."""
        changes = []

        for name, port in EMPIRE_SERVICES.items():
            is_up = self._port_open(port)
            was_up = self._service_status.get(name)

            if was_up is not None and was_up and not is_up:
                changes.append(f"🔴 {name} (:{port}) went DOWN")
            elif was_up is not None and not was_up and is_up:
                changes.append(f"🟢 {name} (:{port}) is back UP")

            self._service_status[name] = is_up

        if changes:
            logger.info(f"Service health changes: {changes}")
            try:
                from app.services.max.telegram_bot import telegram_bot
                if telegram_bot.is_configured:
                    msg = "🖥️ <b>Service Alert</b>\n\n" + "\n".join(changes)
                    await telegram_bot.send_message(msg)
            except Exception as e:
                logger.warning(f"Health alert notification failed: {e}")

    @staticmethod
    def _port_open(port: int, host: str = "127.0.0.1", timeout: float = 2.0) -> bool:
        """Check if a TCP port is accepting connections."""
        try:
            with socket.create_connection((host, port), timeout=timeout):
                return True
        except (ConnectionRefusedError, TimeoutError, OSError):
            return False

    # ── v6.0 Pipeline Executor ─────────────────────────────────────────

    async def _run_pipeline_executor(self):
        """Execute next ready subtasks from all active pipelines."""
        try:
            from app.services.max.pipeline import pipeline_engine
            results = await pipeline_engine.execute_next_subtasks()
            if results:
                logger.info(f"[Pipeline] Executed {len(results)} subtask(s): "
                           + ", ".join(f"{r['desk']}:{r['status']}" for r in results))
        except Exception as e:
            logger.warning(f"[Pipeline] Executor tick failed: {e}")

    # ── v6.0 Morning Brief & Weekly Report ──────────────────────────────

    async def _generate_morning_brief(self):
        """Generate and send morning briefing — all desk statuses, pipeline summary,
        key metrics, and priority actions. Sent to Telegram + stored for CC dashboard."""
        logger.info("[Scheduler] Generating morning brief")
        try:
            from app.services.max.telegram_bot import telegram_bot
            from app.services.max.pipeline import pipeline_engine
            from app.services.max.security.sanitizer import sanitizer as input_sanitizer

            # 1. Desk statuses
            statuses = await self.manager.get_all_statuses()
            desk_lines = []
            for s in statuses:
                desk_id = s.get("desk_id", "?")
                completed = s.get("completed_today", 0)
                active = len(s.get("active_task_details", []))
                escalated = s.get("escalated", 0)
                icon = "🟢" if not escalated else "🟡"
                desk_lines.append(f"{icon} <b>{desk_id}</b>: {completed} done, {active} active{f', {escalated} escalated' if escalated else ''}")

            # 2. Pipeline summary
            active_pipelines = pipeline_engine.get_active_pipelines()
            review_tasks = pipeline_engine.get_review_tasks()

            # 3. Service health
            health_lines = []
            for name, port in EMPIRE_SERVICES.items():
                up = self._port_open(port)
                health_lines.append(f"{'🟢' if up else '🔴'} {name} (:{port})")

            # 4. Security stats
            sec_stats = input_sanitizer.get_stats()

            # 5. Quotes summary
            quote_info = ""
            try:
                import json, os
                quotes_dir = os.path.expanduser("~/empire-repo/backend/data/quotes")
                open_quotes = 0
                total_pipeline = 0
                for f in os.listdir(quotes_dir):
                    if f.endswith(".json") and not f.startswith("_"):
                        with open(os.path.join(quotes_dir, f)) as qf:
                            q = json.load(qf)
                        if q.get("status") in ("draft", "sent"):
                            open_quotes += 1
                            total_pipeline += q.get("total", 0)
                quote_info = f"💰 <b>Quotes:</b> {open_quotes} open (${total_pipeline:,.0f} pipeline)"
            except Exception:
                quote_info = "💰 <b>Quotes:</b> (unavailable)"

            # Build brief
            now = datetime.now()
            brief = (
                f"🌅 <b>Morning Brief — {now.strftime('%A, %B %d')}</b>\n\n"
                f"<b>AI Desks ({len(statuses)})</b>\n"
                + "\n".join(desk_lines) + "\n\n"
                f"<b>Pipelines</b>\n"
                f"📊 {len(active_pipelines)} active, {len(review_tasks)} awaiting review\n\n"
                f"{quote_info}\n\n"
                f"<b>Services</b>\n"
                + "\n".join(health_lines) + "\n\n"
                f"🛡 <b>Security:</b> {sec_stats['total_checks']} checks, "
                f"{sec_stats['blocked_injection'] + sec_stats['blocked_sql'] + sec_stats['blocked_xss']} blocked"
            )

            # Send via Telegram
            if telegram_bot.is_configured:
                await telegram_bot.send_message(brief)

            # Store for CC dashboard
            try:
                import json as _json
                brief_path = os.path.expanduser("~/empire-repo/backend/data/reports/morning_brief.json")
                os.makedirs(os.path.dirname(brief_path), exist_ok=True)
                with open(brief_path, "w") as f:
                    _json.dump({
                        "date": now.strftime("%Y-%m-%d"),
                        "generated_at": now.isoformat(),
                        "html": brief,
                        "desk_count": len(statuses),
                        "active_pipelines": len(active_pipelines),
                        "review_tasks": len(review_tasks),
                        "security_stats": sec_stats,
                    }, f, indent=2)
            except Exception as e:
                logger.warning(f"Failed to save morning brief: {e}")

            logger.info("[Scheduler] Morning brief sent")

        except Exception as e:
            logger.error(f"[Scheduler] Morning brief failed: {e}")

    async def _generate_weekly_report(self):
        """Generate weekly business intelligence report with monetization suggestions.
        Sent every Monday at 8AM."""
        logger.info("[Scheduler] Generating weekly report")
        try:
            from app.services.max.telegram_bot import telegram_bot
            from app.services.max.pipeline import pipeline_engine
            import json, os

            now = datetime.now()

            # Gather weekly data
            # Quote stats
            quotes_dir = os.path.expanduser("~/empire-repo/backend/data/quotes")
            total_quotes = 0
            accepted = 0
            total_value = 0
            try:
                for f in os.listdir(quotes_dir):
                    if f.endswith(".json") and not f.startswith("_"):
                        with open(os.path.join(quotes_dir, f)) as qf:
                            q = json.load(qf)
                        total_quotes += 1
                        if q.get("status") == "accepted":
                            accepted += 1
                        total_value += q.get("total", 0)
            except Exception:
                pass

            # Pipeline stats
            all_pipelines = pipeline_engine.get_all_pipelines()

            # Ecosystem audit
            try:
                audit = await pipeline_engine.audit_ecosystem()
                findings_count = len(audit.get("findings", []))
            except Exception:
                findings_count = 0

            # Cost stats (from token tracker)
            cost_info = ""
            try:
                from app.services.max.token_tracker import token_tracker
                stats = token_tracker.get_stats(7)
                weekly_cost = stats.get("total", {}).get("cost_usd", 0)
                cost_info = f"💸 <b>AI Costs (7d):</b> ${weekly_cost:.2f}"
            except Exception:
                cost_info = "💸 <b>AI Costs:</b> (unavailable)"

            # Build report
            report = (
                f"📊 <b>Weekly Report — Week of {now.strftime('%B %d, %Y')}</b>\n\n"
                f"<b>Business Metrics</b>\n"
                f"📋 Total quotes: {total_quotes} (${total_value:,.0f})\n"
                f"✅ Accepted: {accepted}\n"
                f"📈 Win rate: {(accepted/total_quotes*100):.0f}%\n\n" if total_quotes > 0 else
                f"📊 <b>Weekly Report — Week of {now.strftime('%B %d, %Y')}</b>\n\n"
                f"<b>Business Metrics</b>\n"
                f"📋 No quotes this period\n\n"
            )

            report += (
                f"<b>Pipelines</b>\n"
                f"🔄 Total pipelines: {len(all_pipelines)}\n\n"
                f"{cost_info}\n\n"
                f"<b>Ecosystem Health</b>\n"
                f"🔍 Audit findings: {findings_count}\n\n"
                f"<b>Monetization Suggestions</b>\n"
                f"💡 CraftForge frontend (15 endpoints, 0 UI) — biggest gap\n"
                f"💡 Review stale quotes for follow-up revenue\n"
                f"💡 Consider SaaS pricing tiers for new signups"
            )

            # Send + store
            if telegram_bot.is_configured:
                await telegram_bot.send_message(report)

            report_path = os.path.expanduser("~/empire-repo/backend/data/reports/weekly_report.json")
            os.makedirs(os.path.dirname(report_path), exist_ok=True)
            with open(report_path, "w") as f:
                json.dump({
                    "week_of": now.strftime("%Y-%m-%d"),
                    "generated_at": now.isoformat(),
                    "html": report,
                    "total_quotes": total_quotes,
                    "accepted_quotes": accepted,
                    "total_value": total_value,
                    "pipelines": len(all_pipelines),
                    "audit_findings": findings_count,
                }, f, indent=2)

            logger.info("[Scheduler] Weekly report sent")

        except Exception as e:
            logger.error(f"[Scheduler] Weekly report failed: {e}")

    # ── Event triggers (called by other parts of the system) ──────────

    async def on_new_intake_project(self, project: dict):
        """Triggered when a new intake project is submitted."""
        name = project.get("name", "Unknown")
        treatment = project.get("treatment", "not specified")
        photos = len(project.get("photos", []))
        measurements = len(project.get("measurements", []))

        await self._execute_desk_task(
            "forge",
            f"New Intake Project: {name}",
            f"A new project was just submitted via the intake portal.\n"
            f"Project: {name}\n"
            f"Treatment: {treatment}\n"
            f"Photos: {photos}\n"
            f"Measurements: {measurements}\n\n"
            f"Review the submission and prepare initial assessment. "
            f"Estimate rough pricing range and identify what additional info is needed.",
            source="event:intake_submit",
        )

    async def on_photo_uploaded(self, project_id: str, photo_info: dict):
        """Triggered when a new photo is uploaded to an intake project."""
        await self._execute_desk_task(
            "forge",
            f"New Photo Uploaded: Project {project_id}",
            f"A client just uploaded a photo to project {project_id}.\n"
            f"Photo: {photo_info.get('original_name', 'unknown')}\n\n"
            f"Analyze what's visible in the context of a window treatment project. "
            f"Note window count, room type, existing treatments, and any measurement clues.",
            source="event:photo_upload",
        )

    async def on_quote_stale(self, quote: dict, days_old: int):
        """Triggered when a quote goes without response for N days."""
        await self._execute_desk_task(
            "sales",
            f"Stale Quote: {quote.get('client', 'Unknown')} ({days_old} days)",
            f"Quote for {quote.get('client', 'Unknown')} is {days_old} days old with no response.\n"
            f"Amount: ${quote.get('total', 0):,.2f}\n"
            f"Treatment: {quote.get('treatment', 'N/A')}\n\n"
            f"Draft a warm follow-up message. Be helpful, not pushy. "
            f"Suggest a specific next step (call, revised quote, fabric samples).",
            source="event:stale_quote",
        )

    async def on_service_down(self, service_name: str, port: int):
        """Triggered immediately when a service goes down."""
        await self._execute_desk_task(
            "it",
            f"SERVICE DOWN: {service_name} (port {port})",
            f"{service_name} on port {port} is not responding.\n"
            f"Diagnose the issue and suggest recovery steps. "
            f"Check if this is a known issue or new failure.",
            source="event:service_down",
        )

    async def trigger_now(self, desk_id: str, title: str, description: str):
        """Manually trigger a desk task immediately (for testing or on-demand use)."""
        await self._execute_desk_task(desk_id, title, description, source="manual")


# Singleton
desk_scheduler = DeskScheduler()
