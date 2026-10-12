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
from .base_desk import TaskState
from app.services.max.desks.live_services import EMPIRE_SERVICES, LIVE_SERVICES, check_live_services, format_health_report

logger = logging.getLogger("max.desks.scheduler")

# Schedule: (hour, minute, desk_id, task_title, task_description)
# Each job queries live empire.db data via job_runner (named findings).
DAILY_SCHEDULE = [
    (8, 0, "finance", "Morning Invoice Audit",
     "Check all outstanding invoices in empire.db. Flag overdue. "
     "List each by invoice number, client name, amount, and days overdue."),

    (8, 30, "it", "Morning Service Health Check",
     "Check live Empire services: empire-backend 8000, empire-portal 3005, "
     "empire-amp, empire-maxine, tunnel, disk. Drop dead ports."),

    (9, 0, "sales", "Stale Quote Follow-Up Scan",
     "Review quotes_v2 older than 3 days without a client response. "
     "Draft follow-ups into the approval queue — do not send."),

    (9, 30, "support", "Open Ticket Summary",
     "Audit pending mail, unreviewed inbox, support tasks, and family-help "
     "(family stays isolated). Drafts only — no outbound."),

    (10, 0, "marketing", "Daily Social Media Post",
     "Draft an Instagram post from a named live job or quote. Approval only."),

    (10, 30, "forge", "Today's Pipeline Summary",
     "Summarize open quotes_v2, active jobs, and today's schedule_events."),

    (11, 0, "analytics", "Daily Business Metrics",
     "Pull key metrics from empire.db: customers, jobs, invoices, payments, "
     "expenses, inventory, open tasks. Named unpaid invoices."),

    (11, 30, "quality", "AI Quality Audit",
     "Report failed desk jobs, stuck tasks, and overdue work from the DB."),
]

# Live services only (empire-backend, empire-portal, amp, maxine, tunnel, disk).


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

                # Consolidated brief lives in MaxScheduler (after desks / using
                # yesterday's desk_job_results). Do not send a second 7:30 brief.

                # v6.0 Weekly report: Monday 8:00 AM
                if now.weekday() == 0 and now.hour == 8 and now.minute == 0:
                    week_key = f"weekly_report:{today}"
                    if self._last_run.get("weekly_report") != week_key:
                        self._last_run["weekly_report"] = week_key
                        asyncio.create_task(self._generate_weekly_report())

                # Accuracy digest: 10:00 PM daily
                if now.hour == 22 and now.minute == 0:
                    digest_key = f"accuracy_digest:{today}"
                    if self._last_run.get("accuracy_digest") != digest_key:
                        self._last_run["accuracy_digest"] = digest_key
                        asyncio.create_task(self._send_accuracy_digest())

                # v6.0 Pipeline executor: process pending subtasks (every 2 min)
                if now.minute % 2 == 0:
                    pl_tick = f"{today}:{now.hour}:{now.minute}"
                    if self._last_run.get("pipeline_tick") != pl_tick:
                        self._last_run["pipeline_tick"] = pl_tick
                        asyncio.create_task(self._run_pipeline_executor())

                # After the last scheduled desk job, route idle desks + record a run.
                if now.hour == 12 and now.minute == 0:
                    orch_key = f"orchestrator:{today}"
                    if self._last_run.get("orchestrator") != orch_key:
                        self._last_run["orchestrator"] = orch_key
                        asyncio.create_task(self._run_idle_desk_orchestrator())

            except Exception as e:
                logger.warning(f"Scheduler tick error: {e}")

            await asyncio.sleep(60)  # Check every minute

    def stop(self):
        self._running = False
        logger.info("Desk scheduler stopped")

    async def _execute_desk_task(self, desk_id: str, title: str, description: str, source: str = "scheduler"):
        """Execute a scheduled job against live DB data. Done only if review passes."""
        logger.info(f"[Scheduler] Executing: {desk_id} → {title}")

        try:
            from app.services.max.desks.job_runner import run_scheduled_job
            from .base_desk import DeskTask, TaskPriority

            out = run_scheduled_job(desk_id, title, description)
            task = DeskTask(
                id=out["id"],
                title=title,
                description=description,
                priority=TaskPriority.NORMAL,
                source=source,
            )
            if out["status"] == "done":
                task.state = TaskState.COMPLETED
            else:
                task.state = TaskState.FAILED
            task.result = out.get("result")
            task.completed_at = datetime.now().isoformat()
            if out.get("fail_reason"):
                task.escalation_reason = out["fail_reason"]

            await self._notify_telegram(desk_id, title, task)
            logger.info(f"[Scheduler] Completed: {desk_id} → {title} ({task.state.value})")
            return out

        except Exception as e:
            logger.error(f"[Scheduler] Failed: {desk_id} → {title}: {e}")
            await self._notify_telegram_error(desk_id, title, str(e))
            return None

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
        """Check live Empire services — alert on status changes."""
        changes = []
        for row in check_live_services():
            name = row["name"]
            is_up = bool(row.get("up"))
            was_up = self._service_status.get(name)
            if was_up is not None and was_up and not is_up:
                changes.append(f"DOWN {name}: {row.get('detail')}")
            elif was_up is not None and not was_up and is_up:
                changes.append(f"UP {name}: {row.get('detail')}")
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

    async def _run_idle_desk_orchestrator(self):
        """Give idle desks real jobs and persist an orchestrator run record."""
        try:
            from app.services.max.orchestrator_runs import route_idle_desks

            result = route_idle_desks()
            logger.info(
                "[Orchestrator] idle desks: %s tasks=%s run=%s",
                result.get("desks_assigned"), result.get("tasks_created"), result.get("run_id"),
            )
        except Exception as e:
            logger.warning("[Orchestrator] idle-desk routing failed: %s", e)

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
        """Build the ONE DB-backed brief. Does not send — MaxScheduler sends it."""
        logger.info("[Scheduler] Generating consolidated morning brief (no send)")
        try:
            from app.services.max.daily_brief import build_and_persist_brief

            return build_and_persist_brief()
        except Exception as e:
            logger.error(f"[Scheduler] Morning brief failed: {e}")
            return None

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
            # Quote stats from live data path (never ~/empire-repo)
            from app.services.data_paths import quotes_data_dir
            quotes_dir = str(quotes_data_dir())
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

            from app.services.data_paths import reports_dir
            report_path = str(reports_dir() / "weekly_report.json")
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

    async def _send_accuracy_digest(self):
        """Send daily MAX accuracy report via Telegram."""
        logger.info("[Scheduler] Generating accuracy digest")
        try:
            from app.services.max.accuracy_monitor import accuracy_monitor
            from app.services.max.telegram_bot import telegram_bot

            stats = accuracy_monitor.get_stats(days=1)
            total = stats.get("total_queries", 0)

            if total == 0:
                return  # No web queries today, skip digest

            accuracy = stats.get("accuracy_rate", 100)
            flagged = stats.get("fail_count", 0)
            avg_conf = stats.get("avg_confidence", 1.0)

            icon = "\u2705" if accuracy >= 90 else "\u26a0\ufe0f" if accuracy >= 70 else "\u274c"

            msg = (
                f"\ud83d\udcca <b>MAX Accuracy Report \u2014 Daily</b>\n\n"
                f"{icon} Accuracy: {accuracy:.1f}%\n"
                f"\ud83d\udcdd Total web queries: {total}\n"
                f"\ud83c\udfaf Avg confidence: {avg_conf:.1%}\n"
                f"\ud83d\udea9 Flagged responses: {flagged}\n"
            )

            # Add worst sources if any
            worst = stats.get("worst_sources", [])
            if worst:
                msg += "\n<b>Worst sources:</b>\n"
                for s in worst[:3]:
                    msg += f"  \u2022 {s['domain']}: {s['phantom_count']} phantom citations\n"

            # Per-channel breakdown
            by_channel = stats.get("by_channel", {})
            if by_channel:
                msg += "\n<b>By channel:</b>\n"
                for ch, ch_stats in by_channel.items():
                    ch_acc = ch_stats.get("accuracy_rate", 100)
                    ch_icon = "✅" if ch_acc >= 90 else "⚠️" if ch_acc >= 70 else "❌"
                    msg += f"  {ch_icon} {ch}: {ch_stats['total']} queries, {ch_acc:.0f}% accuracy"
                    if ch_stats.get("auto_fixed", 0) > 0:
                        msg += f", {ch_stats['auto_fixed']} auto-fixed"
                    msg += "\n"

            if telegram_bot.is_configured:
                await telegram_bot.send_message(msg)

            logger.info(f"[Scheduler] Accuracy digest sent: {total} queries, {accuracy:.1f}% accuracy")
        except Exception as e:
            logger.error(f"[Scheduler] Accuracy digest failed: {e}")

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
