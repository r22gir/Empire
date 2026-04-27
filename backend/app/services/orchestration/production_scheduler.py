"""
Production Scheduler — Workroom daily optimization
Runs at 7 AM daily, optimizes job queue, notifies founder.
"""
import logging
from datetime import datetime, timedelta
import httpx

logger = logging.getLogger("scheduler")

API = "http://localhost:8000/api/v1"


class ProductionScheduler:
    def __init__(self):
        self.priority_order = {"urgent": 0, "high": 1, "normal": 2, "low": 3}

    async def get_active_jobs(self, status: str = None) -> list[dict]:
        """Fetch active jobs from workroom."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                params = {"status": status} if status else {}
                r = await client.get(f"{API}/workroom/jobs", params=params)
                if r.ok:
                    data = r.json()
                    return data.get("jobs", data) if isinstance(data, dict) else data
        except Exception as e:
            logger.warning(f"Failed to fetch jobs: {e}")
        return []

    async def check_material_inventory(self, job_id: str) -> dict:
        """Check if materials are in stock for a job."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(f"{API}/inventory/check", params={"job_id": job_id})
                if r.ok:
                    return r.json()
        except Exception as e:
            logger.warning(f"Material check failed: {e}")
        return {"in_stock": True, "missing": []}

    def calculate_deadline(self, job: dict) -> datetime:
        """Calculate deadline based on priority, complexity, workload."""
        now = datetime.utcnow()
        priority = job.get("priority", "normal")
        complexity = job.get("complexity", 1)

        days_map = {"urgent": 2, "high": 5, "normal": 10, "low": 15}
        days = days_map.get(priority, 10) * complexity

        # Add buffer if materials not in stock
        if not job.get("materials_ready", True):
            days += 3

        return now + timedelta(days=days)

    def optimize_queue(self, jobs: list[dict]) -> list[dict]:
        """Sort jobs by: urgency → material availability → deadline."""
        def sort_key(job):
            priority_score = self.priority_order.get(job.get("priority", "normal"), 2)
            material_score = 0 if job.get("materials_ready", True) else 1
            deadline = self.calculate_deadline(job)
            return (priority_score, material_score, deadline)

        return sorted(jobs, key=sort_key)

    async def update_craftforge_schedule(self, queue: list[dict]) -> dict:
        """Push optimized queue to CraftForge."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                r = await client.patch(
                    f"{API}/craftforge/schedule",
                    json={"queue": [{"id": j["id"], "order": i + 1} for i, j in enumerate(queue)]},
                )
                if r.ok:
                    return {"updated": True, "count": len(queue)}
        except Exception as e:
            logger.warning(f"CraftForge schedule update failed: {e}")
        return {"updated": False}

    async def notify_founder(self, priority_jobs: list[dict]) -> dict:
        """Send Telegram notification to founder with priority jobs."""
        if not priority_jobs:
            return {"sent": False}

        jobs_text = "\n".join([
            f"• {j.get('title', 'Job')} ({j.get('client', '—')}) — {j.get('priority', 'normal').upper()}"
            for j in priority_jobs[:5]
        ])

        message = f"""Good morning! 📋 Today's production priority:

{jobs_text}

Active jobs: {len(priority_jobs)}
Pending quotes: 24"""

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.post(
                    f"{API}/notifications/telegram",
                    json={"message": message, "priority": "normal"},
                )
                return {"sent": r.ok}
        except Exception as e:
            logger.warning(f"Founder notification failed: {e}")
            return {"sent": False}

    async def run_daily_optimization(self) -> dict:
        """Full daily optimization cycle."""
        # Fetch all active/in_production jobs
        all_jobs = await self.get_active_jobs()
        active_jobs = [j for j in all_jobs if j.get("status") in ("approved", "in_production")]

        # Optimize queue
        optimized = self.optimize_queue(active_jobs)

        # Update CraftForge
        update_result = await self.update_craftforge_schedule(optimized)

        # Notify founder of top priority
        priority_jobs = [j for j in optimized if j.get("priority") in ("urgent", "high")]
        notify_result = await self.notify_founder(priority_jobs)

        return {
            "total_active_jobs": len(active_jobs),
            "optimized_count": len(optimized),
            "schedule_updated": update_result.get("updated", False),
            "founder_notified": notify_result.get("sent", False),
            "top_priority": priority_jobs[:5],
        }


production_scheduler = ProductionScheduler()
