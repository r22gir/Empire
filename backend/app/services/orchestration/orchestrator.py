"""
EmpireOrchestrator — MAX-Hermes-OpenClaw Autonomous Loop
Monitors ecosystem health, delegates to OpenClaw, logs to Hermes, notifies founder.
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Any, Optional

from fastapi import HTTPException
import httpx

from app.services.openclaw_worker import dispatch_to_openclaw
from app.services.hermes_memory import HermesMemory

logger = logging.getLogger("orchestrator")

API = "http://localhost:8000/api/v1"
OPENCLAW_API = "http://localhost:7878"
BACKEND_HEALTH = "http://localhost:8000/health"
FRONTEND_HEALTH = "http://localhost:3005"


class EmpireOrchestrator:
    def __init__(self):
        self.enabled = False
        self.hermes = HermesMemory()
        self.alert_thresholds = {
            "task_failure_rate_pct": 10,
            "api_response_time_s": 2.0,
            "uncommitted_git_hours": 24,
        }

    # ── Health Checks ──────────────────────────────────────────────────────────

    async def check_backend_health(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(BACKEND_HEALTH)
                return {"healthy": r.ok, "service": "backend", "latency_ms": r.elapsed.total_seconds() * 1000}
        except Exception as e:
            return {"healthy": False, "service": "backend", "error": str(e)}

    async def check_frontend_health(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(FRONTEND_HEALTH)
                return {"healthy": r.ok, "service": "frontend", "latency_ms": r.elapsed.total_seconds() * 1000}
        except Exception as e:
            return {"healthy": False, "service": "frontend", "error": str(e)}

    async def check_openclaw_health(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{OPENCLAW_API}/health")
                if r.ok:
                    d = r.json()
                    return {
                        "healthy": True,
                        "service": "openclaw",
                        "task_count": d.get("task_count", 0),
                        "worker_status": d.get("worker_status", "unknown"),
                    }
                return {"healthy": False, "service": "openclaw"}
        except Exception as e:
            return {"healthy": False, "service": "openclaw", "error": str(e)}

    async def check_ollama_health(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get("http://localhost:11434/api/tags")
                return {"healthy": r.ok, "service": "ollama"}
        except Exception as e:
            return {"healthy": False, "service": "ollama", "error": str(e)}

    async def check_max_desks(self) -> dict:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{API}/desks")
                if r.ok:
                    d = r.json()
                    return {"healthy": True, "service": "max", "desk_count": len(d.get("desks", []))}
                return {"healthy": False, "service": "max"}
        except Exception as e:
            return {"healthy": False, "service": "max", "error": str(e)}

    async def detect_incident(self) -> Optional[dict]:
        """Scan all services, return first detected incident or None."""
        checks = [
            await self.check_backend_health(),
            await self.check_frontend_health(),
            await self.check_openclaw_health(),
            await self.check_ollama_health(),
            await self.check_max_desks(),
        ]
        for check in checks:
            if not check.get("healthy", False):
                return {
                    "type": "service_down",
                    "service": check.get("service"),
                    "details": check,
                    "timestamp": datetime.utcnow().isoformat(),
                }

        # Check task queue failure rate
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.get(f"{OPENCLAW_API}/tasks?limit=100")
                if r.ok:
                    tasks = r.json().get("tasks", [])
                    if tasks:
                        failed = sum(1 for t in tasks if t.get("status") == "failed")
                        rate = (failed / len(tasks)) * 100
                        if rate > self.alert_thresholds["task_failure_rate_pct"]:
                            return {
                                "type": "high_failure_rate",
                                "rate_pct": round(rate, 1),
                                "threshold": self.alert_thresholds["task_failure_rate_pct"],
                                "timestamp": datetime.utcnow().isoformat(),
                            }
        except Exception:
            pass

        return None

    # ── Hermes Integration ─────────────────────────────────────────────────────

    async def query_hermes_memory(self, incident_type: str) -> list[dict]:
        """Find similar past incidents in Hermes."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                r = await client.get(
                    f"http://localhost:8000/api/v1/hermes/search",
                    params={"query": incident_type, "limit": 5},
                )
                if r.ok:
                    return r.json().get("results", [])
        except Exception as e:
            logger.warning(f"Hermes query failed: {e}")
        return []

    async def log_outcome(self, incident_id: str, success: bool, details: dict):
        """Record incident resolution to Hermes for learning."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"http://localhost:8000/api/v1/hermes/incidents",
                    json={
                        "incident_id": incident_id,
                        "resolved": success,
                        "details": details,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                )
        except Exception as e:
            logger.warning(f"Hermes log failed: {e}")

    # ── OpenClaw Delegation ─────────────────────────────────────────────────────

    async def delegate_to_openclaw(self, task: dict) -> dict:
        """Dispatch a task to OpenClaw for execution."""
        try:
            result = await dispatch_to_openclaw(task)
            return {"success": True, "result": result}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ── Founder Notifications ──────────────────────────────────────────────────

    async def send_founder_notification(
        self,
        message: str,
        priority: str = "normal",
        channel: str = "telegram",
    ):
        """Send notification to founder via Telegram."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    f"http://localhost:8000/api/v1/notifications/telegram",
                    json={
                        "message": message,
                        "priority": priority,
                        "channel": channel,
                    },
                )
        except Exception as e:
            logger.warning(f"Telegram notification failed: {e}")

    # ── Main Orchestration Loop ────────────────────────────────────────────────

    async def run_cycle(self) -> dict:
        """One orchestration cycle: detect → resolve or alert → log."""
        cycle_start = datetime.utcnow().isoformat()
        incidents_detected = []
        resolutions = []

        incident = await self.detect_incident()
        if incident:
            incidents_detected.append(incident)
            similar = await self.query_hermes_memory(incident.get("type", ""))

            # Attempt self-heal via OpenClaw
            if incident.get("type") == "service_down":
                task = {
                    "type": "restart_service",
                    "service": incident.get("service"),
                    "priority": "high",
                }
                result = await self.delegate_to_openclaw(task)
                resolutions.append({
                    "incident": incident,
                    "attempted": True,
                    "result": result,
                })

                if not result.get("success"):
                    await self.send_founder_notification(
                        f"[ALERT] {incident.get('service')} is down. "
                        f"Auto-remediation failed. Manual intervention required.",
                        priority="high",
                    )
            elif incident.get("type") == "high_failure_rate":
                await self.send_founder_notification(
                    f"[WARNING] Task failure rate at {incident.get('rate_pct')}%. "
                    f"Threshold: {incident.get('threshold')}%. "
                    f"Low-priority tasks paused.",
                    priority="high",
                )

        return {
            "cycle_at": cycle_start,
            "incidents": incidents_detected,
            "resolutions": resolutions,
            "status": "ok" if not incidents_detected else "incident_handled",
        }

    async def start_autonomous_loop(self, interval_seconds: int = 300):
        """Background loop running every `interval_seconds`."""
        self.enabled = True
        logger.info(f"Orchestrator autonomous loop started (interval={interval_seconds}s)")
        while self.enabled:
            try:
                result = await self.run_cycle()
                logger.info(f"Cycle complete: {result['status']}")
            except Exception as e:
                logger.error(f"Orchestrator cycle error: {e}")
            await asyncio.sleep(interval_seconds)

    def stop_autonomous_loop(self):
        self.enabled = False
        logger.info("Orchestrator autonomous loop stopped")


orchestrator_instance = EmpireOrchestrator()
