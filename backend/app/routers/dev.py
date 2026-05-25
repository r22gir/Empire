"""
Dev API — service status, git info, audit log, and health checks for the Dev Panel.
"""
import os
import socket
import subprocess
import logging
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()
logger = logging.getLogger("dev")

SERVICE_MAP = {
    "backend": {"port": 8000},
    "cc": {"port": 3005},
    "openclaw": {"port": 7878},
    "ollama": {"port": 11434},
    "recoveryforge": {"port": 3077},
    "relistapp": {"port": 3007},
}


def _port_open(port: int) -> bool:
    try:
        with socket.create_connection(("127.0.0.1", port), timeout=2):
            return True
    except (ConnectionRefusedError, TimeoutError, OSError):
        return False


def _get_pid(port: int) -> int | None:
    try:
        r = subprocess.run(
            ["fuser", f"{port}/tcp"],
            capture_output=True, text=True, timeout=5,
        )
        if r.stdout.strip():
            return int(r.stdout.strip().split()[-1])
    except Exception:
        pass
    return None


@router.get("/dev/status")
async def dev_status():
    """All services: name, port, running, pid."""
    services = []
    for name, info in SERVICE_MAP.items():
        port = info["port"]
        running = _port_open(port)
        pid = _get_pid(port) if running else None
        services.append({
            "name": name,
            "port": port,
            "running": running,
            "pid": pid,
        })
    return {"services": services}


@router.get("/dev/git")
async def dev_git():
    """Current git state — derived from runtime code path, not hardcoded paths."""
    # Derive repo root from the running router file path:
    # this file is at .../backend/app/routers/dev.py → 4 levels up = repo root
    router_file = Path(__file__).resolve()
    repo_root = str(router_file.parent.parent.parent.parent)
    backend_cwd = os.getcwd()
    backend_port = 8000

    result = {
        "repo_root": repo_root,
        "backend_cwd": backend_cwd,
        "router_file": str(router_file),
        "backend_port": backend_port,
        "frontend_expected_port": 3005,
        "source_method": "runtime_path",
    }

    try:
        r = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=repo_root, capture_output=True, text=True, timeout=5,
        )
        result["branch"] = r.stdout.strip()
    except Exception:
        result["branch"] = "unknown"

    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_root, capture_output=True, text=True, timeout=5,
        )
        commit_hash = r.stdout.strip()
        result["commit_hash"] = commit_hash
        result["short_commit"] = commit_hash[:7] if commit_hash else ""
    except Exception:
        result["commit_hash"] = ""
        result["short_commit"] = ""

    try:
        r = subprocess.run(
            ["git", "log", "--oneline", "-1"],
            cwd=repo_root, capture_output=True, text=True, timeout=5,
        )
        parts = r.stdout.strip().split(" ", 1)
        result["commit_message"] = parts[1] if len(parts) > 1 else ""
    except Exception:
        result["commit_message"] = ""

    try:
        r = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=repo_root, capture_output=True, text=True, timeout=5,
        )
        lines = [l for l in r.stdout.strip().split("\n") if l.strip()]
        result["uncommitted_count"] = len(lines)
        result["dirty"] = len(lines) > 0
        result["dirty_files"] = lines
    except Exception:
        result["uncommitted_count"] = 0
        result["dirty"] = False
        result["dirty_files"] = []

    result["runtime_lane"] = "stable/main"

    return result


@router.get("/dev/audit")
async def dev_audit(limit: int = 50):
    """Last N tool executions from audit DB."""
    try:
        from app.services.max.tool_audit import get_recent_executions
        executions = get_recent_executions(min(limit, 200))
        return {"executions": executions, "count": len(executions)}
    except Exception as e:
        return {"executions": [], "count": 0, "error": str(e)}


@router.get("/dev/health")
async def dev_health():
    """Combined: all services + critical endpoints."""
    import httpx

    # Services
    services = []
    for name, info in SERVICE_MAP.items():
        port = info["port"]
        running = _port_open(port)
        services.append({"name": name, "port": port, "running": running})

    # Critical endpoints
    endpoints = [
        ("GET", "/health", "Backend Health"),
        ("GET", "/api/v1/max/ai-desks/status", "Desk Status"),
        ("GET", "/api/v1/system/stats", "System Stats"),
        ("GET", "/api/v1/costs/summary", "Cost Summary"),
        ("GET", "/api/v1/finance/dashboard", "Finance"),
        ("GET", "/api/v1/crm/customers", "CRM"),
        ("GET", "/api/v1/inventory/items", "Inventory"),
        ("GET", "/api/v1/recovery/status", "Recovery"),
    ]

    endpoint_results = []
    async with httpx.AsyncClient(timeout=5) as client:
        for method, path, label in endpoints:
            try:
                r = await client.request(method, f"http://localhost:8000{path}")
                ok = 200 <= r.status_code < 500
                endpoint_results.append({"label": label, "path": path, "status": r.status_code, "ok": ok})
            except Exception:
                endpoint_results.append({"label": label, "path": path, "ok": False, "error": "unreachable"})

    passed = sum(1 for s in services if s["running"]) + sum(1 for e in endpoint_results if e.get("ok"))
    failed = sum(1 for s in services if not s["running"]) + sum(1 for e in endpoint_results if not e.get("ok"))

    return {
        "services": services,
        "endpoints": endpoint_results,
        "passed": passed,
        "failed": failed,
    }


@router.get("/dev/crypto-status")
async def dev_crypto_status():
    """
    Admin view: crypto payment stats and configuration status.
    No auth gate — accessed via FOUNDER_PIN in practice.
    """
    try:
        from app.database import SessionLocal
        from app.models.crypto_payment import CryptoPayment
        db = SessionLocal()
        try:
            pending = db.query(CryptoPayment).filter(CryptoPayment.status == "pending").count()
            confirming = db.query(CryptoPayment).filter(CryptoPayment.status == "confirming").count()
            confirmed = db.query(CryptoPayment).filter(CryptoPayment.status == "confirmed").count()
            expired = db.query(CryptoPayment).filter(CryptoPayment.status == "expired").count()
            total = db.query(CryptoPayment).count()
            return {
                "configured": bool(__import__("os").getenv("CRYPTO_MASTER_SEED")),
                "seed_set": bool(__import__("os").getenv("CRYPTO_MASTER_SEED")),
                "totals": {"total": total, "pending": pending, "confirming": confirming, "confirmed": confirmed, "expired": expired},
            }
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}


@router.post("/dev/crypto-expire")
async def dev_crypto_expire():
    """
    Manually trigger stale payment expiration.
    Returns number of payments expired.
    """
    try:
        from app.database import SessionLocal
        from app.services.crypto_payment_service import CryptoPaymentService
        db = SessionLocal()
        try:
            count = CryptoPaymentService.expire_stale_payments(db)
            return {"expired": count}
        finally:
            db.close()
    except Exception as e:
        return {"error": str(e)}
