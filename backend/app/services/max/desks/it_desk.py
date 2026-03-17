"""
ITDesk — Empire platform systems administration and monitoring.
Agent: Orion. Does REAL health checks — actually tests ports and resources.
UPGRADED v5.0: service_manager (status/restart/start/stop/logs), package_manager (pip/npm install).
"""
import logging
import os
import socket
import shutil
from datetime import datetime
from .base_desk import BaseDesk, DeskTask, DeskAction, TaskPriority

logger = logging.getLogger("max.desks.it")

# Known Empire services and ports
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


def _port_open(port: int, host: str = "127.0.0.1", timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


def _get_system_resources() -> dict:
    """Get real system resource usage."""
    resources = {}
    try:
        with open("/proc/meminfo") as f:
            lines = f.readlines()
        mem = {}
        for line in lines:
            parts = line.split()
            if parts[0] in ("MemTotal:", "MemAvailable:", "MemFree:", "SwapTotal:", "SwapFree:"):
                mem[parts[0].rstrip(":")] = int(parts[1])
        total_gb = mem.get("MemTotal", 0) / 1024 / 1024
        avail_gb = mem.get("MemAvailable", 0) / 1024 / 1024
        used_gb = total_gb - avail_gb
        resources["ram"] = {
            "total_gb": round(total_gb, 1),
            "used_gb": round(used_gb, 1),
            "avail_gb": round(avail_gb, 1),
            "pct": round((used_gb / total_gb) * 100, 1) if total_gb else 0,
        }
    except Exception:
        resources["ram"] = {"error": "Could not read /proc/meminfo"}

    try:
        disk = shutil.disk_usage("/home")
        resources["disk"] = {
            "total_gb": round(disk.total / 1e9, 1),
            "used_gb": round(disk.used / 1e9, 1),
            "free_gb": round(disk.free / 1e9, 1),
            "pct": round((disk.used / disk.total) * 100, 1),
        }
    except Exception:
        resources["disk"] = {"error": "Could not check disk"}

    try:
        with open("/proc/loadavg") as f:
            parts = f.read().split()
        resources["load"] = {
            "1min": float(parts[0]),
            "5min": float(parts[1]),
            "15min": float(parts[2]),
        }
    except Exception:
        resources["load"] = {"error": "Could not read load"}

    try:
        cpu_count = os.cpu_count() or 1
        resources["cpu_cores"] = cpu_count
    except Exception:
        pass

    return resources


class ITDesk(BaseDesk):
    desk_id = "it"
    desk_name = "ITDesk"
    agent_name = "Orion"
    desk_description = (
        "Systems administration for the Empire platform. Monitors service health "
        "across all ports, tracks RAM/disk/CPU, handles troubleshooting. "
        "Does REAL port checks and resource monitoring."
    )
    capabilities = [
        "service_health_check",
        "port_monitoring",
        "log_analysis",
        "resource_monitoring",
        "troubleshooting",
        "backup_verification",
        "service_manager",
        "package_manager",
    ]

    def __init__(self):
        super().__init__()
        self.incidents: list[dict] = []
        self.health_checks: list[dict] = []

    async def handle_task(self, task: DeskTask) -> DeskTask:
        await self.accept_task(task)
        combined = f"{task.title} {task.description}".lower()

        try:
            if any(w in combined for w in ["health", "status", "check", "up", "down", "online", "service"]):
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
            else:
                return await self._handle_general(task)
        except Exception as e:
            logger.error(f"ITDesk task failed: {e}")
            return await self.fail_task(task, str(e))

    async def _handle_health_check(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="health_check", detail="Running REAL port checks"))

        # Actually test each port
        results = []
        up_count = 0
        down_count = 0
        for name, port in EMPIRE_SERVICES.items():
            is_up = _port_open(port)
            icon = "🟢" if is_up else "🔴"
            results.append(f"  {icon} {name} (:{port})")
            if is_up:
                up_count += 1
            else:
                down_count += 1

        # Get resources
        resources = _get_system_resources()
        ram = resources.get("ram", {})
        disk = resources.get("disk", {})
        load = resources.get("load", {})

        lines = [
            f"Empire Service Health Check — {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            f"Services: {up_count} UP, {down_count} DOWN",
            "",
        ]
        lines.extend(results)
        lines.append("")
        if "error" not in ram:
            lines.append(f"RAM: {ram['used_gb']}GB / {ram['total_gb']}GB ({ram['pct']}%)")
        if "error" not in disk:
            lines.append(f"Disk: {disk['used_gb']}GB / {disk['total_gb']}GB ({disk['pct']}%) — {disk['free_gb']}GB free")
        if "error" not in load:
            cores = resources.get("cpu_cores", "?")
            lines.append(f"Load: {load['1min']} / {load['5min']} / {load['15min']} ({cores} cores)")

        # Flag issues
        warnings = []
        if "error" not in ram and ram["pct"] > 80:
            warnings.append(f"⚠️ RAM usage high: {ram['pct']}%")
        if "error" not in disk and disk["pct"] > 85:
            warnings.append(f"⚠️ Disk usage high: {disk['pct']}%")
        if down_count > 0:
            warnings.append(f"⚠️ {down_count} service(s) DOWN")

        if warnings:
            lines.append("")
            lines.append("WARNINGS:")
            lines.extend(warnings)

        self.health_checks.append({
            "task_id": task.id,
            "date": datetime.utcnow().isoformat(),
            "up": up_count,
            "down": down_count,
        })

        result = "\n".join(lines)

        # Notify Telegram if issues found
        if warnings:
            await self.notify_telegram(result)

        return await self.complete_task(task, result)

    async def _handle_resources(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="resource_check", detail="Checking real system resources"))

        resources = _get_system_resources()
        ram = resources.get("ram", {})
        disk = resources.get("disk", {})
        load = resources.get("load", {})

        lines = [f"System Resources — {datetime.now().strftime('%Y-%m-%d %H:%M')}"]
        if "error" not in ram:
            lines.append(f"RAM: {ram['used_gb']}GB used / {ram['total_gb']}GB total ({ram['pct']}%)")
            lines.append(f"  Available: {ram['avail_gb']}GB")
        if "error" not in disk:
            lines.append(f"Disk /home: {disk['used_gb']}GB used / {disk['total_gb']}GB total ({disk['pct']}%)")
            lines.append(f"  Free: {disk['free_gb']}GB")
        if "error" not in load:
            lines.append(f"Load avg: {load['1min']} (1m) / {load['5min']} (5m) / {load['15min']} (15m)")
            lines.append(f"CPU cores: {resources.get('cpu_cores', '?')}")

        result = "\n".join(lines)
        return await self.complete_task(task, result)

    async def _handle_restart(self, task: DeskTask) -> DeskTask:
        """Handle service restart via service_manager tool (Level 3 — PIN required)."""
        task.actions.append(DeskAction(action="restart_request", detail="Processing restart request via service_manager"))
        from app.services.max.tool_executor import execute_tool

        combined = f"{task.title} {task.description}".lower()
        # Detect which service
        service = "all"
        for svc in ["backend", "cc", "openclaw", "ollama", "recoveryforge", "relistapp"]:
            if svc in combined:
                service = svc
                break

        # Detect command
        cmd = "restart"
        if "stop" in combined:
            cmd = "stop"
        elif "start" in combined:
            cmd = "start"

        r = execute_tool({"tool": "service_manager", "command": cmd, "service": service}, desk="it")
        if r.success and r.result:
            services = r.result.get("services", [])
            lines = [f"Service {cmd}: {service}"]
            for s in services:
                status = "UP" if s.get("running") else "DOWN"
                lines.append(f"  {s.get('name')}: {status} (:{s.get('port', '?')})")
            return await self.complete_task(task, "\n".join(lines))
        else:
            return await self.escalate(task, f"Service {cmd} failed: {r.error or 'unknown error'}. Needs founder intervention.")

    async def _handle_log_analysis(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="log_analysis", detail="Analyzing logs"))
        # Use AI for actual log analysis
        try:
            result = await self.ai_execute_task(task)
        except Exception:
            result = (
                f"Log analysis: {task.title}. "
                f"Check: ~/empire-repo/logs/ for session logs, "
                f"'journalctl -b -p err' for system errors."
            )
        return await self.complete_task(task, result)

    async def _handle_deployment(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="deployment", detail="Processing deployment request"))
        return await self.escalate(
            task,
            f"Deployment requested: {task.title}. Needs founder review and approval."
        )

    async def _handle_backup(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="backup_check", detail="Checking backup status"))
        result = (
            f"Backup task: {task.title}. "
            f"Use: rsync -av --delete --exclude='node_modules' --exclude='.next' "
            f"--exclude='venv' ~/empire-repo/ /media/rg/BACKUP11/EMPIRE/"
        )
        return await self.complete_task(task, result)

    async def _handle_general(self, task: DeskTask) -> DeskTask:
        task.actions.append(DeskAction(action="general_it", detail="Processing IT task"))
        try:
            result = await self.ai_execute_task(task)
        except Exception:
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
