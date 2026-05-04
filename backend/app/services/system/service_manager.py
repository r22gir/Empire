"""
EmpireBox Service Manager — Unified process control for all Empire services.
Lightweight subprocess management with port conflict detection.
"""
import os
import signal
import subprocess
import psutil
import json
from pathlib import Path
from typing import Dict, Optional
import fcntl


class ServiceManager:
    """Manages lifecycle of Empire services as child processes."""

    def __init__(self):
        self.services = {
            "v10_backend": {
                "port": 8010,
                "cmd": "cd ~/empire-repo-v10/backend && source ~/empire-repo/backend/venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8010 --reload",
                "cwd": "~/empire-repo-v10/backend",
            },
            "v10_frontend": {
                "port": 3010,
                "cmd": "cd ~/empire-repo-v10/empire-command-center && npm run dev -- -p 3010",
                "cwd": "~/empire-repo-v10/empire-command-center",
            },
            "stable_backend": {
                "port": 8000,
                "cmd": "cd ~/empire-repo/backend && source ~/empire-repo/backend/venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload",
                "cwd": "~/empire-repo/backend",
            },
            "stable_frontend": {
                "port": 3005,
                "cmd": "cd ~/empire-repo/empire-command-center && npm run dev -- -p 3005",
                "cwd": "~/empire-repo/empire-command-center",
            },
            "openclaw": {
                "port": 7878,
                "cmd": "cd ~/empire-repo-v10/backend && source ~/empire-repo/backend/venv/bin/activate && python -m app.services.openclaw.worker",
                "cwd": "~/empire-repo-v10/backend",
            },
            "telegram_bot": {
                "port": None,
                "cmd": "cd ~/empire-repo-v10/backend && source ~/empire-repo/backend/venv/bin/activate && python run_telegram_bot.py",
                "cwd": "~/empire-repo-v10/backend",
            },
            "cloudflare_tunnel": {
                "port": None,
                "cmd": "cloudflared tunnel run v10-empirebox",
                "cwd": os.path.expanduser("~"),
            },
            "ollama": {
                "port": 11434,
                "cmd": "ollama serve",
                "cwd": os.path.expanduser("~"),
            },
        }
        self.pid_file = Path.home() / ".empire_service_pids.json"

    def _load_pids(self) -> dict:
        """Load persisted PID map from disk."""
        if self.pid_file.exists():
            try:
                with open(self.pid_file) as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}

    def _save_pids(self, pids: dict):
        """Persist PID map to disk."""
        with open(self.pid_file, "w") as f:
            json.dump(pids, f, indent=2)

    def get_status(self) -> dict:
        """Get running status of all services."""
        pids = self._load_pids()
        status = {}
        for name, config in self.services.items():
            port = config.get("port")
            pid = pids.get(name)
            is_running = False
            conflicting_pid = None

            # Check by PID first
            if pid and psutil.pid_exists(pid):
                try:
                    proc = psutil.Process(pid)
                    is_running = proc.is_running() and proc.status() != psutil.STATUS_ZOMBIE
                except psutil.NoSuchProcess:
                    is_running = False

            # Fallback: check port if not running by PID
            if not is_running and port:
                for conn in psutil.net_connections(kind="inet"):
                    if conn.laddr.port == port and conn.status == "LISTEN":
                        is_running = True
                        conflicting_pid = conn.pid
                        break

            info = {
                "status": "online" if is_running else "offline",
                "port": port,
                "pid": pid,
            }
            if conflicting_pid and not is_running:
                info["conflict_pid"] = conflicting_pid
            status[name] = info
        return status

    def _kill_process_group(self, pid: int) -> bool:
        """Kill a process and its entire process group."""
        try:
            pgid = os.getpgid(pid)
            os.killpg(pgid, signal.SIGTERM)
            return True
        except (ProcessLookupError, PermissionError):
            # Fallback to single process kill
            try:
                os.kill(pid, signal.SIGTERM)
                return True
            except ProcessLookupError:
                return True  # Already dead
            except PermissionError:
                return False

    def _check_port_conflict(self, port: int) -> Optional[int]:
        """Check if a port is occupied. Returns PID of conflicting process or None."""
        for conn in psutil.net_connections(kind="inet"):
            if conn.laddr.port == port and conn.status == "LISTEN":
                return conn.pid
        return None

    def start_service(self, name: str, force: bool = False) -> dict:
        """Start a service. If force=True, kill conflicting processes first."""
        if name not in self.services:
            return {"error": f"Service '{name}' not found", "available": list(self.services.keys())}

        config = self.services[name]
        pids = self._load_pids()

        # Check for port conflict
        if config.get("port"):
            conflict_pid = self._check_port_conflict(config["port"])
            if conflict_pid:
                if force:
                    self._kill_process_group(conflict_pid)
                else:
                    return {
                        "error": f"Port {config['port']} is already in use",
                        "conflict_pid": conflict_pid,
                        "hint": "Use force=true to kill the conflicting process",
                    }

        # Start the process
        try:
            cwd = os.path.expanduser(config["cwd"])
            proc = subprocess.Popen(
                config["cmd"],
                shell=True,
                cwd=cwd,
                start_new_session=True,
                preexec_fn=os.setsid,
            )
            pids[name] = proc.pid
            self._save_pids(pids)
            return {"status": "started", "pid": proc.pid, "name": name, "port": config.get("port")}
        except Exception as e:
            return {"error": f"Failed to start {name}: {str(e)}"}

    def stop_service(self, name: str) -> dict:
        """Stop a service by killing its process group."""
        if name not in self.services:
            return {"error": f"Service '{name}' not found"}

        pids = self._load_pids()
        pid = pids.get(name)

        if pid:
            if psutil.pid_exists(pid):
                success = self._kill_process_group(pid)
                if success:
                    del pids[name]
                    self._save_pids(pids)
                    return {"status": "stopped", "name": name}
                else:
                    return {"error": f"Permission denied to kill PID {pid}", "name": name}
            else:
                # PID file stale
                del pids[name]
                self._save_pids(pids)
                return {"status": "already_stopped", "name": name, "note": "stale PID file cleaned"}

        return {"status": "already_stopped", "name": name}

    def restart_service(self, name: str) -> dict:
        """Restart a service (stop then start with force)."""
        if name not in self.services:
            return {"error": f"Service '{name}' not found"}
        self.stop_service(name)
        return self.start_service(name, force=True)

    def get_service_info(self, name: str) -> dict:
        """Get detailed info about a specific service."""
        if name not in self.services:
            return {"error": f"Service '{name}' not found"}
        config = self.services[name]
        status = self.get_status()
        return {
            "name": name,
            "port": config.get("port"),
            "cmd": config["cmd"],
            **status.get(name, {}),
        }


# Singleton instance
service_manager = ServiceManager()
