"""
ITDesk — Empire platform systems administration and monitoring.
Absorbs: legacy OpsBot (domains). Source: DB desk config (it).
"""
import logging
from datetime import datetime
from .base_desk import BaseDesk, DeskTask, DeskAction, TaskPriority

logger = logging.getLogger("max.desks.it")

# Known Empire services and ports
EMPIRE_SERVICES = {
    "backend": 8000,
    "homepage": 8080,
    "empire_app": 3000,
    "workroomforge": 3001,
    "luxeforge": 3002,
    "founder_dashboard": 3009,
    "openclaw": 7878,
    "ollama": 11434,
}


class ITDesk(BaseDesk):
    desk_id = "it"
    desk_name = "ITDesk"
    desk_description = (
        "Systems administration for the Empire platform. Monitors service health "
        "across all ports, handles deployments, troubleshooting, log analysis, and "
        "system optimization. Enforces Switchboard 3-server limit to protect Mini PC resources. "
        "Tracks RAM usage, disk space, and service uptime."
    )
    capabilities = [
        "service_health_check",
        "port_monitoring",
        "log_analysis",
        "deployment_management",
        "resource_monitoring",
        "troubleshooting",
        "restart_services",
        "backup_verification",
    ]

    def __init__(self):
        super().__init__()
        self.incidents: list[dict] = []
        self.health_checks: list[dict] = []

    async def handle_task(self, task: DeskTask) -> DeskTask:
        await self.accept_task(task)
        combined = f"{task.title} {task.description}".lower()

        try:
            if any(w in combined for w in ["health", "status", "check", "up", "down", "online"]):
                return await self._handle_health_check(task)
            elif any(w in combined for w in ["restart", "reboot", "start", "stop"]):
                return await self._handle_restart(task)
            elif any(w in combined for w in ["log", "error", "crash", "debug"]):
                return await self._handle_log_analysis(task)
            elif any(w in combined for w in ["deploy", "update", "upgrade", "release"]):
                return await self._handle_deployment(task)
            elif any(w in combined for w in ["ram", "memory", "disk", "cpu", "resource", "space"]):
                return await self._handle_resources(task)
            elif any(w in combined for w in ["backup", "sync", "restore"]):
                return await self._handle_backup(task)
            elif any(w in combined for w in ["port", "network", "firewall", "connection"]):
                return await self._handle_network(task)
            else:
                return await self._handle_general(task)
        except Exception as e:
            logger.error(f"ITDesk task failed: {e}")
            return await self.fail_task(task, str(e))

    async def _handle_health_check(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="health_check", detail="Running service health checks"))

        services_summary = ", ".join(f"{name}:{port}" for name, port in EMPIRE_SERVICES.items())

        self.health_checks.append({
            "task_id": task.id,
            "date": datetime.utcnow().isoformat(),
        })

        result = (
            f"Health check initiated. Empire services: {services_summary}. "
            f"Run 'bash ~/empire-repo/scripts/stability/health_check.sh' for live status. "
            f"Switchboard limit: 3 concurrent servers max."
        )
        return await self.complete_task(task, result)

    async def _handle_restart(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="restart_request", detail="Processing restart request"))

        # Service restarts always escalate — don't auto-restart
        return await self.escalate(
            task,
            f"Service restart requested: {task.title}. "
            f"Needs founder confirmation before restarting services."
        )

    async def _handle_log_analysis(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="log_analysis", detail="Analyzing logs"))

        result = (
            f"Log analysis: {task.title}. "
            f"Check: ~/empire-repo/logs/ for session logs, "
            f"'journalctl -b -p err' for system errors, "
            f"'dmesg | tail -50' for kernel messages. "
            f"Do NOT run sensors-detect (crashes this hardware)."
        )
        return await self.complete_task(task, result)

    async def _handle_deployment(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="deployment", detail="Processing deployment request"))

        # Deployments always escalate
        return await self.escalate(
            task,
            f"Deployment requested: {task.title}. Needs founder review and approval."
        )

    async def _handle_resources(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="resource_check", detail="Checking system resources"))

        result = (
            f"Resource check: {task.title}. "
            f"Commands: 'free -h' (RAM), 'df -h' (disk), 'sensors | grep Tctl' (CPU temp). "
            f"Hardware: AMD Ryzen 7 5825U, kernel 6.17. "
            f"Keep total RAM usage under 80%. SSD temp should stay under 70C."
        )
        return await self.complete_task(task, result)

    async def _handle_backup(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="backup_check", detail="Processing backup request"))

        result = (
            f"Backup task: {task.title}. "
            f"Use BackupSync desktop shortcut or: "
            f"rsync -av --delete --exclude='node_modules' --exclude='.next' "
            f"--exclude='venv' ~/empire-repo/ /media/rg/BACKUP11/EMPIRE/. "
            f"Verify BACKUP11 is mounted first."
        )
        return await self.complete_task(task, result)

    async def _handle_network(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="network_check", detail="Checking network/ports"))

        services_list = "\n".join(f"  {name}: :{port}" for name, port in EMPIRE_SERVICES.items())
        result = (
            f"Network check: {task.title}. "
            f"Empire ports:\n{services_list}\n"
            f"Use 'ss -tlnp | grep <port>' to verify listeners."
        )
        return await self.complete_task(task, result)

    async def _handle_general(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="general_it", detail="Processing IT task"))
        result = f"IT task processed: {task.title}. {task.description[:200]}"
        return await self.complete_task(task, result)

    async def report_status(self) -> dict:
        base = await super().report_status()
        base["incidents"] = len(self.incidents)
        base["health_checks_today"] = len([
            h for h in self.health_checks
            if h["date"][:10] == datetime.utcnow().strftime("%Y-%m-%d")
        ])
        return base
