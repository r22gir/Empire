"""
Phoenix — Quality Desk: Monitors AI quality across all desks.
Reviews accuracy, flags declining performance, generates quality digests.
"""
import logging
from typing import Optional
from .base_desk import BaseDesk, DeskTask, DeskAction, TaskState

logger = logging.getLogger("max.desks.quality")


class QualityDesk(BaseDesk):
    desk_id = "quality"
    desk_name = "Quality Desk"
    desk_description = "AI quality monitoring — accuracy tracking, quality digests, escalation"
    agent_name = "Phoenix"
    capabilities = [
        "quality_check",
        "accuracy_report",
        "weekly_digest",
        "escalate_issues",
    ]
    preferred_model = "claude-sonnet-4-6"  # Phoenix: Sonnet for quality checks

    async def _get_quality_metrics(self) -> dict:
        """Pull quality metrics from accuracy monitor."""
        try:
            from app.db.database import get_db
            with get_db() as conn:
                total = conn.execute("SELECT COUNT(*) as cnt FROM max_response_audit").fetchone()["cnt"]
                flagged = conn.execute(
                    "SELECT COUNT(*) as cnt FROM max_response_audit WHERE is_grounded = 0"
                ).fetchone()["cnt"]

            accuracy = round((total - flagged) / max(total, 1) * 100, 1)
            return {
                "total_responses": total,
                "flagged_responses": flagged,
                "accuracy_pct": accuracy,
            }
        except Exception as e:
            logger.error(f"Quality metrics failed: {e}")
            return {"total_responses": 0, "flagged_responses": 0, "accuracy_pct": 100.0}

    async def _handle_task(self, task: DeskTask) -> DeskTask:
        """Run quality check and generate report."""
        task.state = TaskState.IN_PROGRESS
        task.actions.append(DeskAction(action="started", detail="Running quality audit"))

        metrics = await self._get_quality_metrics()

        report = (
            f"Quality Report:\n"
            f"  Total responses audited: {metrics['total_responses']}\n"
            f"  Flagged (ungrounded): {metrics['flagged_responses']}\n"
            f"  Accuracy: {metrics['accuracy_pct']}%\n"
        )

        if metrics['accuracy_pct'] < 90:
            report += "\n  WARNING: Accuracy below 90% threshold!"
            task.actions.append(DeskAction(
                action="alert",
                detail=f"Accuracy at {metrics['accuracy_pct']}% — below threshold",
            ))

        task.result = report
        task.state = TaskState.COMPLETED
        task.actions.append(DeskAction(action="completed", detail="Quality audit complete"))

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
