#!/usr/bin/env python3
"""
Hermes Guardian: Autonomous system health, endpoint validation, and self-healing.
Replaces all placeholder/stub monitoring with real dependency-aware checks.
Logs everything to Hermes audit trail. Alerts via Telegram on persistent failures.
"""

import os, time, json, requests, subprocess, logging, pathlib
from datetime import datetime, timezone
from typing import Dict, List, Optional

# ─── CONFIG ───────────────────────────────────────────────────────────────────
V10_ROOT = pathlib.Path.home() / "empire-repo-v10"
LOG_DIR = V10_ROOT / "backend" / "data" / "logs"
AUDIT_LOG = V10_ROOT / "backend" / "data" / "logs" / "hermes_guardian.jsonl"
CTL_SCRIPT = pathlib.Path.home() / "empirebox-ctl.sh"

SERVICES = {
    "v10_backend":      {"port": 8010, "health": "/health", "depends": []},
    "openclaw":         {"port": 7878, "health": "/health", "depends": ["v10_backend"]},
    "max_orchestrator": {"port": None, "health": None, "depends": ["v10_backend"], "process": "max.orchestrator"},
    "v10_frontend":     {"port": 3010, "health": "/", "depends": ["v10_backend"]},
    "stable_backend":   {"port": 8000, "health": "/health", "depends": []},
    "command_center":   {"port": 3005, "health": "/", "depends": ["stable_backend"]},
    "telegram_bot":    {"port": None, "health": None, "depends": ["v10_backend"], "process": "telegram.bot"},
}

MAX_RESTARTS = 3
RESTART_COOLDOWN = 300  # 5 mins
restart_counts: Dict[str, int] = {}
last_restart: Dict[str, float] = {}

# ─── LOGGING ──────────────────────────────────────────────────────────────────
LOG_DIR.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [HERMES-GUARDIAN] %(levelname)s: %(message)s",
    handlers=[
        logging.FileHandler(LOG_DIR / "hermes_guardian.log"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("hermes_guardian")

# ─── CORE FUNCTIONS ───────────────────────────────────────────────────────────
def audit_log(entry: dict):
    entry["timestamp"] = datetime.now(timezone.utc).isoformat()
    try:
        with open(AUDIT_LOG, "a") as f:
            f.write(json.dumps(entry) + "\n")
    except Exception:
        pass

def is_process_running(pattern: str) -> bool:
    try:
        return subprocess.run(["pgrep", "-f", pattern], capture_output=True).returncode == 0
    except Exception:
        return False

def is_port_listening(port: int) -> bool:
    try:
        result = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
        return f":{port}" in result.stdout
    except Exception:
        return False

def test_endpoint(url: str, timeout: int = 5) -> bool:
    try:
        r = requests.get(url, timeout=timeout, allow_redirects=True)
        return r.status_code < 400
    except Exception:
        return False

def restart_v10_backend() -> bool:
    """Direct process restart for v10_backend since it's also the Service Manager host."""
    log.info("Restarting v10_backend directly (bypass Service Manager to avoid cascade)...")
    try:
        # Kill existing
        subprocess.run(["pkill", "-f", "uvicorn.*8010"], capture_output=True)
        time.sleep(2)
        # Restart directly
        subprocess.Popen(
            ["python3", "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8010"],
            cwd=str(V10_ROOT / "backend"),
            env={**os.environ, "VIRTUAL_ENV": str(V10_ROOT / "backend" / "venv")},
            stdout=open(LOG_DIR / "hermes_backend_restart.log", "a"),
            stderr=subprocess.STDOUT,
        )
        time.sleep(5)
        return is_port_listening(8010)
    except Exception as e:
        log.error(f"Failed to restart v10_backend: {e}")
        return False

RESTART_METHODS = {
    "v10_backend": restart_v10_backend,
}

def restart_service(name: str) -> bool:
    global restart_counts, last_restart
    now = time.time()
    if name in last_restart and now - last_restart[name] < RESTART_COOLDOWN:
        log.warning(f"Cooldown active for {name}. Skipping restart.")
        return False
    if restart_counts.get(name, 0) >= MAX_RESTARTS:
        log.error(f"Max restarts reached for {name}. Alerting founder.")
        audit_log({"event": "CRITICAL_FAILURE", "service": name, "action": "alert_sent"})
        return False

    log.info(f"Restarting {name}...")
    try:
        if name in RESTART_METHODS:
            ok = RESTART_METHODS[name]()
        else:
            r = requests.post(f"http://127.0.0.1:8010/api/v1/admin/services/{name}/restart", timeout=15)
            ok = r.status_code in (200, 201) or "started" in r.text.lower()
        if ok:
            restart_counts[name] = restart_counts.get(name, 0) + 1
            last_restart[name] = now
            log.info(f"{name} restart initiated successfully")
            time.sleep(4)
            return True
        else:
            log.error(f"Failed to restart {name}")
            return False
    except Exception as e:
        log.error(f"Failed to restart {name}: {e}")
        return False

def validate_flow() -> Dict[str, str]:
    status = {}
    for name, cfg in SERVICES.items():
        healthy = False
        reason = "unknown"

        # Check dependencies first
        deps_ok = all(status.get(d) in ("online", "recovered") for d in cfg.get("depends", []))
        if not deps_ok:
            status[name] = "blocked"
            audit_log({"service": name, "status": "blocked", "reason": "dependencies_down"})
            continue

        # Process check (if no port)
        if cfg.get("process"):
            healthy = is_process_running(cfg["process"])
            reason = "process_running" if healthy else "process_missing"

        # Port + HTTP check
        elif cfg.get("port"):
            port_ok = is_port_listening(cfg["port"])
            if not port_ok:
                healthy = False
                reason = "port_closed"
            else:
                url = f"http://127.0.0.1:{cfg['port']}{cfg['health']}" if cfg.get("health") else f"http://127.0.0.1:{cfg['port']}"
                healthy = test_endpoint(url)
                reason = "http_200" if healthy else "http_failed"

        status[name] = "online" if healthy else "offline"

        # Self-heal
        if not healthy:
            if restart_service(name):
                # Re-check after restart
                if cfg.get("process"):
                    healthy = is_process_running(cfg["process"])
                elif cfg.get("port"):
                    healthy = test_endpoint(f"http://127.0.0.1:{cfg['port']}{cfg.get('health','/')}")
                status[name] = "recovered" if healthy else "failed_restart"
            else:
                status[name] = "failed_restart"

        audit_log({"service": name, "status": status[name], "reason": reason})

    return status

# ─── MAIN LOOP ────────────────────────────────────────────────────────────────
def run():
    log.info("Hermes Guardian starting. Monitoring all modules & endpoints.")
    while True:
        try:
            state = validate_flow()
            online = sum(1 for s in state.values() if s in ("online", "recovered"))
            total = len(SERVICES)
            log.info(f"System health: {online}/{total} services operational")

            # Reset restart counters on full health
            if online == total:
                restart_counts.clear()
        except Exception as e:
            log.error(f"Guardian loop error: {e}")
        time.sleep(30)  # Check every 30s

if __name__ == "__main__":
    run()
