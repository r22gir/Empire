"""System Monitor — CPU, RAM, disk, temperature stats via psutil."""
import os
import socket
import time
from datetime import datetime, timedelta
from pathlib import Path

import psutil
from fastapi import APIRouter

router = APIRouter()

_PROCESS_START_TIME = time.time()


def _get_disk_summary():
    """Aggregate disk usage across all physical partitions (skip snap/tmpfs/loop)."""
    total = 0
    used = 0
    drives = []
    seen_devices = set()
    for part in psutil.disk_partitions(all=False):
        if part.device in seen_devices:
            continue
        if any(skip in part.mountpoint for skip in ['/snap', '/boot/efi']):
            continue
        seen_devices.add(part.device)
        try:
            usage = psutil.disk_usage(part.mountpoint)
            total += usage.total
            used += usage.used
            drives.append({
                "mount": part.mountpoint,
                "device": part.device,
                "total_gb": round(usage.total / (1024 ** 3), 1),
                "used_gb": round(usage.used / (1024 ** 3), 1),
                "percent": usage.percent,
            })
        except PermissionError:
            continue
    pct = round((used / total) * 100, 1) if total else 0
    return {
        "total_gb": round(total / (1024 ** 3), 1),
        "used_gb": round(used / (1024 ** 3), 1),
        "percent": pct,
        "drives": drives,
    }


@router.get("/system/health")
async def system_health():
    """Quick health check — is the system alive and services reachable?"""
    ports = {"8000": "API", "3005": "CC", "7878": "OpenClaw", "11434": "Ollama"}
    services = {}
    for port_str, name in ports.items():
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        services[name] = sock.connect_ex(("127.0.0.1", int(port_str))) == 0
        sock.close()
    mem = psutil.virtual_memory()
    return {
        "status": "ok",
        "timestamp": datetime.now().isoformat(),
        "services": services,
        "ram_percent": mem.percent,
        "uptime_seconds": round(time.time() - _PROCESS_START_TIME, 1),
    }


@router.get("/system/stats")
async def system_stats():
    """Return current system resource usage."""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = _get_disk_summary()

    # Temperature sensors (may not exist on all systems)
    temps = {}
    try:
        sensor_temps = psutil.sensors_temperatures()
        for name, entries in sensor_temps.items():
            temps[name] = [
                {"label": e.label or name, "current": e.current, "high": e.high, "critical": e.critical}
                for e in entries
            ]
    except (AttributeError, RuntimeError):
        pass

    return {
        "cpu": {
            "percent": cpu_percent,
            "cores": psutil.cpu_count(logical=True),
            "freq_mhz": round(psutil.cpu_freq().current, 0) if psutil.cpu_freq() else None,
        },
        "memory": {
            "total_gb": round(mem.total / (1024 ** 3), 2),
            "used_gb": round(mem.used / (1024 ** 3), 2),
            "percent": mem.percent,
        },
        "disk": disk,
        "temperatures": temps,
    }


@router.get("/system/metrics")
async def system_metrics():
    """Lightweight observability — single endpoint for all key metrics."""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = _get_disk_summary()

    # Check active ports
    ports = {"8000": "API", "3005": "CC", "7878": "OpenClaw", "11434": "Ollama", "3077": "RecoveryForge"}
    active_ports = {}
    for port_str in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(0.5)
        active_ports[port_str] = sock.connect_ex(("127.0.0.1", int(port_str))) == 0
        sock.close()

    # AI costs today
    ai_costs_today = 0.0
    try:
        db_path = Path(os.path.expanduser("~/empire-repo/backend/data/token_usage.db"))
        if db_path.exists():
            import sqlite3
            conn = sqlite3.connect(str(db_path))
            today = datetime.now().strftime("%Y-%m-%d")
            row = conn.execute(
                "SELECT COALESCE(SUM(cost), 0) FROM token_usage WHERE date(timestamp) = ?", (today,)
            ).fetchone()
            ai_costs_today = round(row[0], 6) if row else 0.0
            conn.close()
    except Exception:
        pass

    # Error count last 24h
    error_count = 0
    try:
        log_path = Path("/tmp/backend.log")
        if log_path.exists():
            cutoff = datetime.now() - timedelta(hours=24)
            for line in log_path.read_text(errors="ignore").splitlines()[-2000:]:
                if "ERROR" in line or "CRITICAL" in line:
                    error_count += 1
    except Exception:
        pass

    return {
        "timestamp": datetime.now().isoformat(),
        "cpu_percent": cpu_percent,
        "ram_percent": mem.percent,
        "ram_used_gb": round(mem.used / (1024 ** 3), 2),
        "ram_total_gb": round(mem.total / (1024 ** 3), 2),
        "disk_percent": disk["percent"],
        "disk_used_gb": disk["used_gb"],
        "disk_total_gb": disk["total_gb"],
        "disk_drives": disk["drives"],
        "active_ports": active_ports,
        "ai_costs_today": ai_costs_today,
        "error_count_24h": error_count,
        "uptime_seconds": round(time.time() - _PROCESS_START_TIME, 1),
    }


@router.post("/system/brain-sync")
async def trigger_brain_sync():
    """Manually trigger a brain sync to update MAX's memory.md with current system state."""
    try:
        from app.services.max.scheduler import max_scheduler
        await max_scheduler.brain_sync()
        return {"status": "ok", "message": "Brain sync completed"}
    except Exception as e:
        return {"status": "error", "message": str(e)}
