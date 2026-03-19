"""
Raven — Analytics Desk: Business intelligence across all modules.
Queries DB for metrics, generates daily/weekly summaries, revenue forecasting.
"""
import logging
from typing import Optional
from .base_desk import BaseDesk, DeskTask, DeskAction, TaskState

logger = logging.getLogger("max.desks.analytics")


class AnalyticsDesk(BaseDesk):
    desk_id = "analytics"
    desk_name = "Analytics Desk"
    desk_description = "Business intelligence — metrics, trends, revenue forecasting"
    agent_name = "Raven"
    capabilities = [
        "daily_metrics",
        "weekly_report",
        "revenue_forecast",
        "pipeline_analysis",
        "cost_analysis",
    ]
    preferred_model = "claude-sonnet-4-6"  # Raven: Sonnet for analytics

    async def _get_metrics(self) -> dict:
        """Pull key metrics from all databases."""
        try:
            from app.db.database import get_db, dict_row
            with get_db() as conn:
                customers = conn.execute("SELECT COUNT(*) as cnt FROM customers").fetchone()["cnt"]
                jobs_pending = conn.execute("SELECT COUNT(*) as cnt FROM jobs WHERE status = 'pending'").fetchone()["cnt"]
                jobs_completed = conn.execute("SELECT COUNT(*) as cnt FROM jobs WHERE status = 'completed'").fetchone()["cnt"]
                invoices_unpaid = conn.execute("SELECT COUNT(*) as cnt FROM invoices WHERE status IN ('draft','sent')").fetchone()["cnt"]
                invoices_paid = conn.execute("SELECT COUNT(*) as cnt FROM invoices WHERE status = 'paid'").fetchone()["cnt"]
                revenue = conn.execute("SELECT COALESCE(SUM(amount_paid),0) as total FROM invoices").fetchone()["total"]
                expenses = conn.execute("SELECT COALESCE(SUM(amount),0) as total FROM expenses").fetchone()["total"]
                inventory = conn.execute("SELECT COUNT(*) as cnt FROM inventory_items").fetchone()["cnt"]
                tasks_open = conn.execute("SELECT COUNT(*) as cnt FROM tasks WHERE status NOT IN ('done','cancelled')").fetchone()["cnt"]

            return {
                "customers": customers,
                "jobs_pending": jobs_pending,
                "jobs_completed": jobs_completed,
                "invoices_unpaid": invoices_unpaid,
                "invoices_paid": invoices_paid,
                "revenue": round(revenue, 2),
                "expenses": round(expenses, 2),
                "profit": round(revenue - expenses, 2),
                "inventory_items": inventory,
                "tasks_open": tasks_open,
            }
        except Exception as e:
            logger.error(f"Metrics query failed: {e}")
            return {}

    async def _handle_task(self, task: DeskTask) -> DeskTask:
        """Generate analytics report."""
        task.state = TaskState.IN_PROGRESS
        task.actions.append(DeskAction(action="started", detail="Pulling metrics"))

        metrics = await self._get_metrics()

        report = (
            f"Daily Metrics:\n"
            f"  Customers: {metrics.get('customers', 0)}\n"
            f"  Jobs: {metrics.get('jobs_pending', 0)} pending, {metrics.get('jobs_completed', 0)} completed\n"
            f"  Invoices: {metrics.get('invoices_unpaid', 0)} unpaid, {metrics.get('invoices_paid', 0)} paid\n"
            f"  Revenue: ${metrics.get('revenue', 0):,.2f}\n"
            f"  Expenses: ${metrics.get('expenses', 0):,.2f}\n"
            f"  Profit: ${metrics.get('profit', 0):,.2f}\n"
            f"  Inventory: {metrics.get('inventory_items', 0)} items\n"
            f"  Open tasks: {metrics.get('tasks_open', 0)}"
        )

        task.result = report
        task.state = TaskState.COMPLETED
        task.actions.append(DeskAction(action="completed", detail="Metrics compiled"))

        # Notify via Telegram
        await self.notify_telegram(report)

        return task

    def get_status(self) -> dict:
        return {
            "desk_id": self.desk_id,
            "agent": self.agent_name,
            "active_tasks": len(self.active_tasks),
            "completed_today": len(self.completed_tasks),
            "capabilities": self.capabilities,
        }
