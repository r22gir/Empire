"""System Monitor — CPU, RAM, disk, temperature stats via psutil."""
import psutil
from fastapi import APIRouter

router = APIRouter()


@router.get("/system/stats")
async def system_stats():
    """Return current system resource usage."""
    cpu_percent = psutil.cpu_percent(interval=0.5)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

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
        "disk": {
            "total_gb": round(disk.total / (1024 ** 3), 2),
            "used_gb": round(disk.used / (1024 ** 3), 2),
            "percent": disk.percent,
        },
        "temperatures": temps,
    }
