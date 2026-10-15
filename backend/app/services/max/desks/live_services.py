"""Live service list for family health checks.

Avatar uses the same checks as GET /avatar/status (Simli, TTS, STT,
voice_status().enabled) and reports down when any check fails.
"""
from __future__ import annotations

import os
import shutil
import socket
import subprocess
from typing import Any

LIVE_SERVICES: list[dict[str, Any]] = [
    {"id": "empire-backend", "name": "empire-backend", "kind": "tcp", "port": 8012},
    {"id": "empire-portal", "name": "empire-portal", "kind": "tcp", "port": 3012},
    {"id": "avatar", "name": "avatar", "kind": "avatar", "module": "app.routers.avatar"},
    {"id": "disk", "name": "disk", "kind": "disk", "path": "/"},
]

EMPIRE_SERVICES: dict[str, int] = {
    "empire-backend": 8012,
    "empire-portal": 3012,
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


def _systemd_active(unit: str) -> bool:
    for args in (
        ["systemctl", "--user", "is-active", "--quiet", unit],
        ["systemctl", "is-active", "--quiet", unit],
        ["systemctl", "--user", "is-active", "--quiet", f"{unit}.service"],
        ["systemctl", "is-active", "--quiet", f"{unit}.service"],
    ):
        try:
            result = subprocess.run(args, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return True
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            continue
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


def _simli_edition() -> str:
    try:
        from app.edition import edition_name
        from app.services.max.simli_avatar import normalize_edition
        return normalize_edition(edition_name())
    except Exception:
        return "maxine"


def avatar_readiness() -> dict[str, Any]:
    """Same checks as GET /avatar/status: Simli, TTS, STT, live voice."""
    checks: dict[str, bool] = {}
    details: dict[str, Any] = {}
    try:
        from app.services.max.simli_avatar import simli_status
        simli = simli_status(_simli_edition())
        checks["simli"] = bool(simli.get("enabled"))
        details["simli"] = simli.get("status") or simli.get("reason")
    except Exception as exc:
        checks["simli"] = False
        details["simli"] = type(exc).__name__
    try:
        from app.services.max.tts_service import tts_service
        checks["tts"] = bool(tts_service.is_configured)
    except Exception as exc:
        checks["tts"] = False
        details["tts"] = type(exc).__name__
    try:
        from app.services.max.stt_service import stt_service
        checks["stt"] = bool(stt_service.is_configured)
    except Exception as exc:
        checks["stt"] = False
        details["stt"] = type(exc).__name__
    try:
        from app.services.max.voice_live import voice_status
        vs = voice_status()
        checks["voice"] = bool(vs.get("enabled"))
        details["voice"] = vs.get("reason")
    except Exception as exc:
        checks["voice"] = False
        details["voice"] = type(exc).__name__
    return {
        "online": all(checks.values()) if checks else False,
        "checks": checks,
        "details": details,
    }


def avatar_service_status() -> dict[str, Any]:
    """Avatar / Presentation Mode — down when Simli, TTS, STT or live voice is off."""
    ready = avatar_readiness()
    return {
        "status": "online" if ready["online"] else "offline",
        "port": 8012,
        "description": "Avatar / Presentation Mode",
        "type": "avatar",
        "checks": ready["checks"],
        "detail": ready["details"],
    }


def _module_importable(name: str) -> bool:
    try:
        import importlib
        importlib.import_module(name)
        return True
    except Exception:
        return False


def check_live_services(
    *,
    port_checker=port_open,
    container_checker=_container_running,
    systemd_checker=_systemd_active,
    process_checker=_process_running,
    disk_checker=_disk_status,
    module_checker=_module_importable,
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
        elif kind == "systemd":
            up = bool(systemd_checker(svc["unit"]))
            rows.append({
                **svc,
                "up": up,
                "detail": f"systemd {svc['unit']} {'active' if up else 'inactive'}",
            })
        elif kind == "container":
            up = bool(container_checker(svc.get("container") or svc.get("unit")))
            rows.append({
                **svc,
                "up": up,
                "detail": f"container {svc.get('container')} {'running' if up else 'not running'}",
            })
        elif kind == "avatar":
            row = avatar_service_status()
            rows.append({
                **svc,
                "up": row["status"] == "online",
                "detail": row.get("detail") or row.get("status"),
            })
        elif kind == "module":
            up = bool(module_checker(svc.get("module") or svc.get("name")))
            rows.append({
                **svc,
                "up": up,
                "detail": f"module {svc.get('module')} {'loaded' if up else 'missing'}",
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
        f"Service health — {up_n} UP, {down_n} DOWN",
        "",
    ]
    for r in rows:
        icon = "UP" if r.get("up") else "DOWN"
        lines.append(f"  [{icon}] {r['name']}: {r.get('detail', '')}")
    return "\n".join(lines)


def stuck_task_days() -> int:
    try:
        return max(1, int(os.environ.get("STUCK_TASK_DAYS", "7")))
    except (TypeError, ValueError):
        return 7
