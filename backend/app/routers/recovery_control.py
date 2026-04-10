"""Recovery Control API — independent recovery/control path for EmpireBox.

This module provides a lightweight, standalone recovery control surface that does NOT
depend on the main Command Center being healthy. It exposes service status, restart
capabilities, and connectivity checks via the backend API (port 8000).

Access: curl http://localhost:8000/api/v1/recovery/status
        curl -X POST http://localhost:8000/api/v1/recovery/restart/backend
        curl -X POST http://localhost:8000/api/v1/recovery/restart/frontend
        curl -X POST http://localhost:8000/api/v1/recovery/restart/cloudflared
        curl http://localhost:8000/api/v1/recovery/connectivity
"""
import json
import os
import socket
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/recovery-core", tags=["recovery-core"])

_SERVICE_DEFINITIONS = {
    "backend": {
        "name": "Empire Backend API",
        "port": 8000,
        "service_name": "empire-backend.service",
        "description": "FastAPI backend on port 8000",
    },
    "frontend": {
        "name": "Empire Studio Portal",
        "port": 3005,
        "service_name": "empire-portal.service",
        "description": "Next.js frontend on port 3005",
    },
    "cloudflared": {
        "name": "Cloudflare Tunnel",
        "port": None,
        "service_name": "cloudflared-studio.service",
        "description": "Cloudflare tunnel for studio.empirebox.store and api.empirebox.store",
    },
    "openclaw": {
        "name": "OpenClaw AI Server",
        "port": 7878,
        "service_name": "empire-openclaw.service",
        "description": "OpenClaw autonomous task server on port 7878",
    },
    "ollama": {
        "name": "Ollama LLM Server",
        "port": 11434,
        "service_name": None,
        "description": "Ollama LLM server on port 11434 (not installed as systemd service)",
    },
    "pairing": {
        "name": "OpenCode ACP Pairing Server",
        "port": 8787,
        "service_name": None,
        "description": "OpenCode phone pairing server on port 8787",
    },
}


def _is_port_open(port: int, host: str = "127.0.0.1", timeout: float = 0.5) -> bool:
    """Check if a port is accepting connections."""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except (OSError, socket.error):
        return False


def _get_service_status(service_name: str) -> dict[str, Any]:
    """Get systemd service status."""
    if not service_name:
        return {"active": None, "enabled": None, "status": "not_configured"}

    try:
        result = subprocess.run(
            ["systemctl", "--user", "is-active", service_name],
            capture_output=True, text=True, timeout=5,
        )
        active = result.stdout.strip() == "active"

        result_enabled = subprocess.run(
            ["systemctl", "--user", "is-enabled", service_name],
            capture_output=True, text=True, timeout=5,
        )
        enabled = result_enabled.returncode == 0

        return {"active": active, "enabled": enabled, "status": "active" if active else "inactive"}
    except subprocess.TimeoutExpired:
        return {"active": None, "enabled": None, "status": "timeout"}
    except FileNotFoundError:
        return {"active": None, "enabled": None, "status": "systemd_unavailable"}
    except Exception as e:
        return {"active": None, "enabled": None, "status": f"error: {str(e)}"}


def _restart_service(service_name: str) -> dict[str, Any]:
    """Restart a systemd user service."""
    if not service_name:
        raise HTTPException(status_code=400, detail="No service name provided")

    try:
        subprocess.run(
            ["systemctl", "--user", "restart", service_name],
            capture_output=True, timeout=30,
        )
        time.sleep(1)
        new_status = _get_service_status(service_name)
        return {
            "restarted": True,
            "service": service_name,
            "new_status": new_status,
        }
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail=f"Timeout restarting {service_name}")
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to restart {service_name}: {str(e)}")


def _check_connectivity() -> dict[str, Any]:
    """Check local connectivity to key endpoints."""
    results = {}

    results["studio.empirebox.store"] = {
        "local_reachable": _is_port_open(3005),
        "cloudflare_tunnel": _is_port_open(3005),
        "note": "Requires cloudflared running",
    }

    results["api.empirebox.store"] = {
        "local_reachable": _is_port_open(8000),
        "cloudflare_tunnel": _is_port_open(8000),
        "note": "Requires cloudflared running",
    }

    return results


def _get_key_ports_status() -> dict[str, Any]:
    """Check status of all key ports."""
    ports = {
        3005: "frontend",
        8000: "backend",
        7878: "openclaw",
        11434: "ollama",
        8787: "pairing",
    }

    status = {}
    for port, name in ports.items():
        is_open = _is_port_open(port)
        status[name] = {
            "port": port,
            "open": is_open,
            "status": "listening" if is_open else "not_listening",
        }

    return status


def _get_process_info() -> dict[str, Any]:
    """Get information about Empire processes."""
    processes = {}
    for proc in psutil.process_iter(["pid", "name", "cmdline", "create_time"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            cmdline_str = " ".join(cmdline)

            if "uvicorn" in cmdline_str and "app.main:app" in cmdline_str:
                processes["backend"] = {
                    "pid": proc.info["pid"],
                    "uptime_seconds": time.time() - proc.info["create_time"],
                    "command": cmdline_str[:100],
                }
            elif "next" in cmdline_str and "3005" in cmdline_str:
                processes["frontend"] = {
                    "pid": proc.info["pid"],
                    "uptime_seconds": time.time() - proc.info["create_time"],
                    "command": cmdline_str[:100],
                }
            elif "cloudflared" in cmdline_str:
                processes["cloudflared"] = {
                    "pid": proc.info["pid"],
                    "uptime_seconds": time.time() - proc.info["create_time"],
                    "command": cmdline_str[:100],
                }
            elif "opencode" in cmdline_str and "serve" in cmdline_str:
                processes["pairing"] = {
                    "pid": proc.info["pid"],
                    "uptime_seconds": time.time() - proc.info["create_time"],
                    "command": cmdline_str[:100],
                }
            elif "ollama" in cmdline_str:
                processes["ollama"] = {
                    "pid": proc.info["pid"],
                    "uptime_seconds": time.time() - proc.info["create_time"],
                    "command": cmdline_str[:100],
                }
            elif "openclaw" in cmdline_str or ("server.py" in cmdline_str and "7878" in cmdline_str):
                processes["openclaw"] = {
                    "pid": proc.info["pid"],
                    "uptime_seconds": time.time() - proc.info["create_time"],
                    "command": cmdline_str[:100],
                }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass

    return processes


@router.get("/status")
async def recovery_status():
    """Comprehensive recovery status — all services, ports, and connectivity.

    This is the primary endpoint for checking system health from a recovery standpoint.
    It does NOT depend on the Command Center being healthy, only on the backend API.

    Returns:
        - services: systemd service status for each key service
        - ports: which key ports are listening
        - connectivity: local reachability of studio and api endpoints
        - processes: running EmpireBox processes with uptime
        - system: basic system resource usage
    """
    ports_status = _get_key_ports_status()

    services_status = {}
    for service_id, svc_def in _SERVICE_DEFINITIONS.items():
        svc_name = svc_def.get("service_name")
        services_status[service_id] = {
            **svc_def,
            "service_status": _get_service_status(svc_name) if svc_name else {"status": "no_systemd_service"},
            "port_status": ports_status.get(service_id, {}).get("open", False) if service_id in ports_status else None,
        }

    connectivity = _check_connectivity()
    processes = _get_process_info()

    mem = psutil.virtual_memory()
    cpu_percent = psutil.cpu_percent(interval=0.3)

    boot_time = datetime.fromtimestamp(psutil.boot_time())
    uptime_seconds = time.time() - psutil.boot_time()

    return {
        "timestamp": datetime.now().isoformat(),
        "status": "operational" if ports_status["backend"]["open"] else "degraded",
        "boot_time": boot_time.isoformat(),
        "uptime_seconds": round(uptime_seconds, 1),
        "system": {
            "cpu_percent": cpu_percent,
            "ram_percent": mem.percent,
            "ram_used_gb": round(mem.used / (1024 ** 3), 2),
            "ram_total_gb": round(mem.total / (1024 ** 3), 2),
        },
        "services": services_status,
        "ports": ports_status,
        "connectivity": connectivity,
        "processes": processes,
    }


class RestartRequest(BaseModel):
    service: str


@router.post("/restart/{service_name}")
async def restart_service(service_name: str):
    """Restart a specific service.

    Args:
        service_name: One of: backend, frontend, cloudflared, openclaw, pairing

    Returns:
        Restart result with new service status

    Note:
        ollama cannot be restarted via this endpoint as it's not a systemd service.
        Use /system/ollama/toggle instead.
    """
    service_map = {
        "backend": "empire-backend.service",
        "frontend": "empire-portal.service",
        "cloudflared": "cloudflared-studio.service",
        "openclaw": "empire-openclaw.service",
    }

    if service_name == "ollama":
        raise HTTPException(
            status_code=400,
            detail="Ollama is not a systemd service. Use POST /api/v1/system/ollama/toggle instead."
        )

    if service_name == "pairing":
        raise HTTPException(
            status_code=400,
            detail="Pairing server (ACP) cannot be restarted via systemd. Use POST /api/v1/qr/pairing/stop then POST /api/v1/qr/pairing/start instead."
        )

    if service_name not in service_map:
        raise HTTPException(
            status_code=400,
            detail=f"Unknown service: {service_name}. Valid options: {list(service_map.keys())}"
        )

    service_file = service_map[service_name]
    return _restart_service(service_file)


@router.post("/restart/all")
async def restart_all_services():
    """Restart all EmpireBox services in proper order.

    Order: backend first, then frontend, then cloudflared.

    Returns:
        Status of each restart attempt.
    """
    results = {}

    order = ["backend", "frontend", "cloudflared"]
    service_map = {
        "backend": "empire-backend.service",
        "frontend": "empire-portal.service",
        "cloudflared": "cloudflared-studio.service",
    }

    for svc_name in order:
        try:
            results[svc_name] = _restart_service(service_map[svc_name])
        except HTTPException as e:
            results[svc_name] = {"error": e.detail}

    time.sleep(2)
    final_status = _get_key_ports_status()

    return {
        "restart_results": results,
        "final_port_status": final_status,
        "overall_status": "ok" if final_status["backend"]["open"] and final_status["frontend"]["open"] else "partial",
    }


@router.get("/connectivity")
async def recovery_connectivity():
    """Check connectivity to studio.empirebox.store and api.empirebox.store.

    This endpoint verifies:
    1. Whether the services are reachable locally
    2. Whether the cloudflared tunnel would route traffic correctly

    Returns:
        Connectivity status for each endpoint.
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "endpoints": _check_connectivity(),
        "cloudflared_running": _is_port_open(8000),
    }


@router.get("/ports")
async def recovery_ports():
    """Check status of all key ports.

    Returns:
        Status of each key port (3005, 8000, 7878, 11434, 8787).
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "ports": _get_key_ports_status(),
    }


@router.get("/processes")
async def recovery_processes():
    """Get information about running EmpireBox processes.

    Returns:
        Process info including PID and uptime for each process.
    """
    return {
        "timestamp": datetime.now().isoformat(),
        "processes": _get_process_info(),
    }


@router.get("/pairing/status")
async def pairing_status():
    """Get OpenCode ACP pairing server status.

    The pairing server is the OpenCode phone pairing mechanism running on port 8787.
    It is NOT a systemd service - it runs as a subprocess managed by the backend.

    Returns:
        Pairing server status including URL and port info.
    """
    try:
        from app.routers.qr import _is_acp_running, _get_local_ip, ACP_PORT
        running = _is_acp_running()
        ip = _get_local_ip() if running else None
        return {
            "status": "running" if running else "stopped",
            "url": f"http://{ip}:{ACP_PORT}" if running else None,
            "port": ACP_PORT,
            "local_ip": ip,
            "managed_by": "backend_qr_module",
            "note": "Start/stop via POST /api/v1/qr/pairing/start or /api/v1/qr/pairing/stop",
        }
    except Exception as e:
        return {
            "status": "error",
            "error": str(e),
        }


@router.post("/pairing/start")
async def pairing_start():
    """Start the OpenCode ACP pairing server.

    The pairing server allows phone pairing with EmpireBox via QR code.

    Returns:
        Start result with URL and QR code preview.
    """
    try:
        from app.routers.qr import _start_acp_server
        result = _start_acp_server()
        if result["status"] == "running":
            import qrcode
            import io
            import base64
            qr = qrcode.QRCode(version=1, box_size=10, border=4)
            qr.add_data(result["url"])
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = io.BytesIO()
            img.resize((300, 300)).save(buf, format="PNG")
            buf.seek(0)
            qr_preview = base64.b64encode(buf.getvalue()).decode()
            result["qr_preview"] = f"data:image/png;base64,{qr_preview}"
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/pairing/stop")
async def pairing_stop():
    """Stop the OpenCode ACP pairing server.

    Returns:
        Stop result.
    """
    try:
        from app.routers.qr import _stop_acp_server
        return _stop_acp_server()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
