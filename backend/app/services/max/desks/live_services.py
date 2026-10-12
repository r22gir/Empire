"""Live Empire service list for IT health checks.

Dead ports (WorkroomForge 3001, LuxeForge 3002, Founder Dashboard 3009,
Ollama 11434) are not checked. Family editions (amp/maxine) are health-
checked only — this module does not send traffic into those editions.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
from typing import Any

# Real live services on the Dell / Studio line.
LIVE_SERVICES: list[dict[str, Any]] = [
    {"id": "empire-backend", "name": "empire-backend", "kind": "tcp", "port": 8000},
    {"id": "empire-portal", "name": "empire-portal", "kind": "tcp", "port": 3005},
    {"id": "empire-amp", "name": "empire-amp", "kind": "container", "container": "empire-amp"},
    {"id": "empire-maxine", "name": "empire-maxine", "kind": "container", "container": "empire-maxine"},
    {"id": "tunnel", "name": "tunnel", "kind": "process", "process": "cloudflared"},
    {"id": "disk", "name": "disk", "kind": "disk", "path": "/"},
]

# Legacy names kept so old callers that still iterate a dict of ports
# do not start checking dead ports again.
EMPIRE_SERVICES: dict[str, int] = {
    "empire-backend": 8000,
    "empire-portal": 3005,
}


def port_open(port: int, host: str = "127.0.0.1", timeout: float = 2.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


def _container_running(name: str) -> bool:
    try:
        result = subprocess.run(
            ["docker", "inspect", "-f", "{{.State.Running}}", name],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0 and result.stdout.strip().lower() == "true"
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _process_running(name: str) -> bool:
    try:
        result = subprocess.run(
            ["pgrep", "-f", name],
            capture_output=True, text=True, timeout=5,
        )
        return result.returncode == 0 and bool(result.stdout.strip())
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return False


def _disk_status(path: str = "/") -> dict[str, Any]:
    usage = shutil.disk_usage(path)
    pct = round((usage.used / usage.total) * 100, 1) if usage.total else 0
    return {
        "id": "disk",
        "name": "disk",
        "kind": "disk",
        "up": pct < 95,
        "pct": pct,
        "free_gb": round(usage.free / 1e9, 1),
        "used_gb": round(usage.used / 1e9, 1),
        "total_gb": round(usage.total / 1e9, 1),
        "detail": f"{pct}% used, {round(usage.free / 1e9, 1)} GB free",
    }


def check_live_services(
    *,
    port_checker=port_open,
    container_checker=_container_running,
    process_checker=_process_running,
    disk_checker=_disk_status,
) -> list[dict[str, Any]]:
    """Return a status row for each live service. Inject checkers in tests."""
    rows: list[dict[str, Any]] = []
    for svc in LIVE_SERVICES:
        kind = svc["kind"]
        if kind == "tcp":
            up = bool(port_checker(svc["port"]))
            rows.append({
                **svc,
                "up": up,
                "detail": f"port {svc['port']} {'UP' if up else 'DOWN'}",
            })
        elif kind == "container":
            up = bool(container_checker(svc["container"]))
            rows.append({
                **svc,
                "up": up,
                "detail": f"container {svc['container']} {'running' if up else 'not running'}",
            })
        elif kind == "process":
            up = bool(process_checker(svc["process"]))
            rows.append({
                **svc,
                "up": up,
                "detail": f"process {svc['process']} {'running' if up else 'not running'}",
            })
        elif kind == "disk":
            rows.append(disk_checker(svc.get("path") or "/"))
    return rows


def format_health_report(rows: list[dict[str, Any]] | None = None) -> str:
    rows = rows if rows is not None else check_live_services()
    up_n = sum(1 for r in rows if r.get("up"))
    down_n = len(rows) - up_n
    lines = [
        f"Empire service health — {up_n} UP, {down_n} DOWN",
        "",
    ]
    for r in rows:
        icon = "UP" if r.get("up") else "DOWN"
        lines.append(f"  [{icon}] {r['name']}: {r.get('detail', '')}")
    warnings = [r for r in rows if not r.get("up")]
    if warnings:
        lines.append("")
        lines.append("WARNINGS:")
        for r in warnings:
            lines.append(f"  - {r['name']} {r.get('detail', '')}")
    return "\n".join(lines)


def stuck_task_days() -> int:
    try:
        return max(1, int(os.environ.get("STUCK_TASK_DAYS", "7")))
    except (TypeError, ValueError):
        return 7
