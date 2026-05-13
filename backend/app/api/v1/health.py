from fastapi import APIRouter
from typing import Dict
import subprocess, time, asyncio
import urllib.request
from datetime import datetime, timezone

router = APIRouter()

def is_process_running(pattern: str) -> bool:
    try:
        return subprocess.run(["pgrep", "-f", pattern], capture_output=True).returncode == 0
    except Exception:
        return False

def check_service_http(name: str, port: int, path: str = "/") -> dict:
    """Check if a service is healthy using socket + HTTP GET."""
    import socket
    url = f"http://127.0.0.1:{port}{path}"

    # Quick socket check
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(2)
    try:
        result = sock.connect_ex(("127.0.0.1", port))
        sock.close()
        if result != 0:
            return {"status": "offline", "latency_ms": None, "port": port}
    except Exception:
        return {"status": "offline", "latency_ms": None, "port": port}

    # HTTP GET check
    try:
        req = urllib.request.Request(url)
        start = time.time()
        with urllib.request.urlopen(req, timeout=5) as resp:
            latency = (time.time() - start) * 1000
            ok = resp.status < 400
            return {"status": "online" if ok else "offline",
                    "latency_ms": round(latency, 2) if ok else None, "port": port}
    except Exception:
        return {"status": "offline", "latency_ms": None, "port": port}


@router.get("/health")
async def system_health() -> Dict:
    """Real endpoint validation - no placeholders. Runs checks in thread pool to avoid blocking."""
    checks = {}

    # Run all HTTP checks concurrently in thread pool
    backend_checks = [
        ("v10_backend", 8010, "/health"),
        ("openclaw", 7878, "/health"),
        ("stable_backend", 8000, "/health"),
    ]
    frontend_checks = [("v10_frontend", 3010, "/"), ("command_center", 3005, "/")]

    all_checks = backend_checks + frontend_checks
    tasks = [asyncio.to_thread(check_service_http, n, p, pt) for n, p, pt in all_checks]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for (name, port, path), result in zip(all_checks, results):
        if isinstance(result, Exception):
            checks[name] = {"status": "offline", "latency_ms": None, "port": port}
        else:
            checks[name] = result

    # Process checks (non-blocking)
    checks["max_orchestrator"] = {
        "status": "online" if is_process_running("max.orchestrator") else "offline",
        "port": None
    }
    checks["telegram_bot"] = {
        "status": "online" if is_process_running("telegram.bot") else "offline",
        "port": None
    }

    online_count = sum(1 for c in checks.values() if c["status"] == "online")
    total_count = len(checks)
    overall = "healthy" if online_count == total_count else "degraded" if online_count > 0 else "critical"

    return {
        "status": overall,
        "online": online_count,
        "total": total_count,
        "services": checks,
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

@router.get("/health/liveness")
async def liveness() -> Dict:
    """Kubernetes-style liveness probe."""
    return {"status": "alive", "service": "hermes-guardian"}

@router.get("/health/ready")
async def readiness() -> Dict:
    """Kubernetes-style readiness probe."""
    result = await asyncio.to_thread(check_service_http, "v10_backend", 8010, "/health")
    ok = result["status"] == "online"
    return {"status": "ready" if ok else "not_ready", "v10_backend": result["status"]}
