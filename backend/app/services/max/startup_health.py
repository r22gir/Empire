"""Startup/runtime health record for MAX freshness proof."""
from __future__ import annotations

import json
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


STARTUP_HEALTH_PATH = Path.home() / "empire-repo" / "backend" / "data" / "max" / "startup_health.json"


def _run(cmd: list[str], timeout: int = 5) -> str:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.stdout.strip() if proc.returncode == 0 else proc.stderr.strip()
    except Exception as exc:
        return str(exc)


def _port_open(host: str, port: int, timeout: float = 0.5) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def build_startup_health_record() -> dict[str, Any]:
    from app.services.max.operating_registry import get_registry_load_info

    commit = _run(["git", "rev-parse", "--short", "HEAD"])
    registry = get_registry_load_info()
    stale_conditions = []
    if registry.get("last_error"):
        stale_conditions.append("registry_last_known_good_due_to_error")

    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "running_commit_hash": commit,
        "registry_version": registry.get("registry_version"),
        "registry_loaded_at": registry.get("loaded_at"),
        "registry_file_sha256": registry.get("file_sha256"),
        "registry_last_error": registry.get("last_error"),
        "startup_port_observations": {
            "backend_port_8000_open_at_record_time": _port_open("127.0.0.1", 8000),
            "frontend_port_3005_open_at_record_time": _port_open("127.0.0.1", 3005),
        },
        "known_stale_state_conditions": stale_conditions,
    }


def write_startup_health_record() -> dict[str, Any]:
    record = build_startup_health_record()
    STARTUP_HEALTH_PATH.parent.mkdir(parents=True, exist_ok=True)
    STARTUP_HEALTH_PATH.write_text(json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    return record


def read_startup_health_record() -> dict[str, Any] | None:
    try:
        return json.loads(STARTUP_HEALTH_PATH.read_text(encoding="utf-8"))
    except Exception:
        return None
