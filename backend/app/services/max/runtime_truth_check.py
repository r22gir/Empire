"""Inspect-only runtime truth checks for MAX live-state claims."""
from __future__ import annotations

import socket
import subprocess
import re
from datetime import datetime, timezone
from typing import Any

import httpx


INTENT_SIGNALS = [
    "runtime truth",
    "runtime status",
    "status only",
    "product status",
    "product-status",
    "current_commit",
    "current commit",
    "current status",
    "current runtime",
    "max status",
    "commit is running",
    "what commit",
    "live commit",
    "local commit",
    "public commit",
    "is archiveforge live",
    "is transcriptforge live",
    "is this live",
    "why don't i see the fix",
    "website not loading",
    "did the new build deploy",
    "did that push",
    "did it push",
    "was it pushed",
    "is the latest code running",
    "latest status",
    "latest commit",
    "latest code",
    "latest build",
    "latest runtime",
    "nothing changed",
    "still seeing old version",
    "is studio/api current",
    "did it restart",
    "did the update go live",
    "is it live",
    "is it broken",
    "is it fixed",
    "is max broken",
    "is max fixed",
    "what's new",
    "whats new",
    "what is new",
    "what changed",
    "what's new today",
    "whats new today",
    "what changed today",
    "what is new today",
    "today's status",
    "todays status",
]


def _normalize_intent_text(message: str | None) -> str:
    text = (message or "").lower().strip()
    text = text.replace("’", "'").replace("`", "'")
    text = re.sub(r"\s+", " ", text)
    return text


def should_run_runtime_truth_check(message: str | None) -> bool:
    text = _normalize_intent_text(message)
    return any(signal in text for signal in INTENT_SIGNALS)


def _run(cmd: list[str], timeout: int = 5) -> dict[str, Any]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "ok": proc.returncode == 0,
            "returncode": proc.returncode,
            "stdout": proc.stdout.strip(),
            "stderr": proc.stderr.strip(),
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc), "stdout": "", "stderr": ""}


def _git_commit() -> dict[str, Any]:
    short = _run(["git", "rev-parse", "--short", "HEAD"])
    message = _run(["git", "log", "--oneline", "-1"])
    return {
        "hash": short.get("stdout", ""),
        "message": message.get("stdout", ""),
    }


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def _service_status(unit: str) -> dict[str, Any]:
    active = _run(["systemctl", "--user", "is-active", unit])
    pid = _run(["systemctl", "--user", "show", unit, "--property=MainPID,ActiveEnterTimestamp", "--no-pager"])
    props: dict[str, str] = {}
    for line in (pid.get("stdout") or "").splitlines():
        if "=" in line:
            key, value = line.split("=", 1)
            props[key] = value
    return {
        "unit": unit,
        "active": active.get("stdout") == "active",
        "state": active.get("stdout") or active.get("stderr") or active.get("error", ""),
        "pid": props.get("MainPID", ""),
        "active_since": props.get("ActiveEnterTimestamp", ""),
    }


def _http_json(url: str, timeout: float = 4.0) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
        data: Any
        try:
            data = resp.json()
        except Exception:
            data = resp.text[:300]
        return {"ok": resp.status_code < 400, "status_code": resp.status_code, "data": data}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _http_status(url: str, timeout: float = 4.0) -> dict[str, Any]:
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
        return {"ok": resp.status_code < 400, "status_code": resp.status_code, "bytes": len(resp.content)}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def run_runtime_truth_check(public: bool = True) -> dict[str, Any]:
    """Return current runtime status without changing services.

    Checks stable (8000/3005) and v10 test (8010/3010) separately so MAX
    can report which is up/down without confusion.
    """
    commit = _git_commit()
    registry_info = {}
    startup_health = None
    try:
        from app.services.max.operating_registry import get_registry_load_info
        registry_info = get_registry_load_info()
        from app.services.max.startup_health import read_startup_health_record
        startup_health = read_startup_health_record()
    except Exception as exc:
        registry_info = {"last_error": str(exc)}
    try:
        from app.services.max.openclaw_gate import check_openclaw_gate
        openclaw_gate_result = check_openclaw_gate()
        openclaw_gate = openclaw_gate_result.to_dict()
    except Exception as exc:
        openclaw_gate = {"state": "unknown", "allowed": False, "reason": str(exc)}
    backend_service = _service_status("empire-backend.service")
    frontend_service = _service_status("empire-portal.service")

    # Check stable ports
    local_api_git = _http_json("http://127.0.0.1:8000/api/v1/dev/git")
    local_backend_root = _http_status("http://127.0.0.1:8000/")
    local_frontend_root = _http_status("http://127.0.0.1:3005/")
    local_memory_bank = _http_status("http://127.0.0.1:8000/api/v1/chats/memory-bank?channel=all&limit=1")

    # Check v10 test lane ports (8010 = backend, 3010 = frontend)
    local_v10_backend_root = _http_status("http://127.0.0.1:8010/")
    local_v10_frontend_root = _http_status("http://127.0.0.1:3010/")

    public_api_git = None
    public_backend_root = None
    public_frontend_root = None
    public_memory_bank = None
    if public:
        public_api_git = _http_json("https://api.empirebox.store/api/v1/dev/git")
        public_backend_root = _http_status("https://api.empirebox.store/")
        public_frontend_root = _http_status("https://studio.empirebox.store/")
        public_memory_bank = _http_status("https://api.empirebox.store/api/v1/chats/memory-bank?channel=all&limit=1")

    local_hash = (local_api_git.get("data") or {}).get("last_commit_hash") if isinstance(local_api_git.get("data"), dict) else None
    public_hash = None
    if public_api_git and isinstance(public_api_git.get("data"), dict):
        public_hash = public_api_git["data"].get("last_commit_hash")

    stale_or_broken: list[str] = []
    if not backend_service["active"] or not _port_open("127.0.0.1", 8000) or not local_backend_root["ok"]:
        stale_or_broken.append("backend_port_8000_unhealthy")
    if not frontend_service["active"] or not _port_open("127.0.0.1", 3005) or not local_frontend_root["ok"]:
        stale_or_broken.append("frontend_port_3005_unhealthy")
    if local_hash and commit["hash"] and local_hash != commit["hash"]:
        stale_or_broken.append("local_api_commit_stale")
    if public and public_hash and commit["hash"] and public_hash != commit["hash"]:
        stale_or_broken.append("public_api_commit_stale")
    if public and public_backend_root and not public_backend_root["ok"]:
        stale_or_broken.append("public_api_unhealthy")
    if public and public_frontend_root and not public_frontend_root["ok"]:
        stale_or_broken.append("public_studio_unhealthy")

    return {
        "skill": "empire-runtime-truth-check",
        "callable": "empire_runtime_truth_check",
        "mode": "inspect_only",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "current_commit": commit,
        "registry": registry_info,
        "startup_health": startup_health,
        "openclaw_gate": openclaw_gate,
        # Stable backend on port 8000 (empire-backend.service)
        "backend_port_8000": {
            "port": 8000,
            "service": "empire-backend.service",
            "service_active": backend_service.get("active", False),
            "port_open": _port_open("127.0.0.1", 8000),
            "local_root_status": local_backend_root.get("status_code"),
        },
        # v10 test backend on port 8010 (not systemd — dev server)
        "backend_port_8010": {
            "port": 8010,
            "service": "v10 test backend (dev server, not systemd)",
            "service_active": None,  # not systemd-managed
            "port_open": _port_open("127.0.0.1", 8010),
            "local_root_status": local_v10_backend_root.get("status_code"),
        },
        # Stable frontend on port 3005 (empire-portal.service)
        "frontend_port_3005": {
            "port": 3005,
            "service": "empire-portal.service",
            "service_active": frontend_service.get("active", False),
            "port_open": _port_open("127.0.0.1", 3005),
            "local_root_status": local_frontend_root.get("status_code"),
        },
        # v10 test frontend on port 3010 (not systemd — dev server)
        "frontend_port_3010": {
            "port": 3010,
            "service": "v10 test frontend (dev server, not systemd)",
            "service_active": None,  # not systemd-managed
            "port_open": _port_open("127.0.0.1", 3010),
            "local_root_status": local_v10_frontend_root.get("status_code"),
        },
        "local_freshness": {
            "api_git": local_api_git,
            "api_matches_current_commit": bool(local_hash and local_hash == commit["hash"]),
            "memory_bank_route": local_memory_bank,
        },
        "public_freshness": {
            "api_git": public_api_git,
            "api_matches_current_commit": bool(public_hash and public_hash == commit["hash"]) if public else None,
            "api_root": public_backend_root,
            "studio_root": public_frontend_root,
            "memory_bank_route": public_memory_bank,
        },
        "restart_required": bool(stale_or_broken),
        "stale_or_broken": stale_or_broken,
        "repair_capability": "inspect_only_no_restart",
    }


def _wants_key_only(message: str | None) -> bool:
    text = (message or "").lower()
    return (
        "key-only" in text
        or "key only" in text
        or "current_commit only" in text
        or "current commit only" in text
    )


def format_runtime_truth_check(result: dict[str, Any], message: str | None = None) -> str:
    """Format runtime truth check result into human-readable text.

    Reports stable vs v10 test lane separately so MAX never says
    a generic 'frontend down' without specifying which port.
    """
    commit = result.get("current_commit", {})
    openclaw_gate = result.get("openclaw_gate") or {}
    stale = result.get("stale_or_broken") or []
    startup = result.get("startup_health") or {}

    # Extract port-specific status
    b8000 = result.get("backend_port_8000", {})
    b8010 = result.get("backend_port_8010", {})
    f3005 = result.get("frontend_port_3005", {})
    f3010 = result.get("frontend_port_3010", {})
    local = result.get("local_freshness", {})
    public = result.get("public_freshness", {})

    public_hash = None
    public_git = public.get("api_git") or {}
    if isinstance(public_git.get("data"), dict):
        public_hash = public_git["data"].get("last_commit_hash")

    local_hash = None
    local_git = local.get("api_git") or {}
    if isinstance(local_git.get("data"), dict):
        local_hash = local_git["data"].get("last_commit_hash")

    if _wants_key_only(message):
        return "\n".join(
            [
                f"current_commit: {commit.get('hash')}",
                f"local_api_commit: {local_hash}",
                f"public_api_commit: {public_hash}",
                f"backend_8000_active: {b8000.get('service_active')}",
                f"frontend_3005_active: {f3005.get('service_active')}",
                f"v10_backend_8010_open: {b8010.get('port_open')}",
                f"v10_frontend_3010_open: {f3010.get('port_open')}",
                f"openclaw_gate: {openclaw_gate.get('state')}",
                f"stale_or_broken: {', '.join(stale) if stale else 'none'}",
            ]
        )

    def _svc(label, svc_info):
        """Format a service entry with port label and status."""
        active = svc_info.get("service_active")
        port_open = svc_info.get("port_open")
        status_code = svc_info.get("local_root_status")
        svc_name = svc_info.get("service", "")
        status = []
        if active is not None:
            status.append(f"systemd={'active' if active else 'inactive'}")
        if port_open is not None:
            status.append(f"port_open={port_open}")
        if status_code:
            status.append(f"http={status_code}")
        return f"{label} ({svc_name}): {' | '.join(status)}"

    lines = [
        "Runtime truth check completed.",
        f"- Mode: {result.get('mode')} ({result.get('repair_capability')})",
        f"- Current repo commit: {commit.get('hash')} ({commit.get('message')})",
        f"- Registry: version={(result.get('registry') or {}).get('registry_version')} loaded_at={(result.get('registry') or {}).get('loaded_at')} last_error={(result.get('registry') or {}).get('last_error')}",
        f"- OpenClaw gate: state={openclaw_gate.get('state')} allowed={openclaw_gate.get('allowed')} reason={openclaw_gate.get('reason')}",
        f"- Stable Backend (port 8000): {'UP' if b8000.get('port_open') else 'DOWN'} | systemd={b8000.get('service_active')} | http={b8000.get('local_root_status')}",
        f"- v10 Test Backend (port 8010): {'UP' if b8010.get('port_open') else 'DOWN/not started'} | {b8010.get('service', 'dev server')}",
        f"- Stable Frontend (port 3005): {'UP' if f3005.get('port_open') else 'DOWN'} | systemd={f3005.get('service_active')} | http={f3005.get('local_root_status')}",
        f"- v10 Test Frontend (port 3010): {'UP' if f3010.get('port_open') else 'DOWN/not started'} | {f3010.get('service', 'dev server')}",
        f"- Local API commit: {local_hash} matches_current={local.get('api_matches_current_commit')}",
        f"- Public API commit: {public_hash} matches_current={public.get('api_matches_current_commit')}",
        f"- Public API root: {(public.get('api_root') or {}).get('status_code')} | Public Studio root: {(public.get('studio_root') or {}).get('status_code')}",
        f"- Restart required by this check: {result.get('restart_required')}",
    ]
    startup_hash = startup.get("running_commit_hash") if isinstance(startup, dict) else None
    if startup_hash and commit.get("hash") and startup_hash != commit.get("hash"):
        lines.append(
            f"- Memory/startup truth was stale: prior startup commit {startup_hash} differs from live commit {commit.get('hash')}; live runtime truth wins."
        )
    if stale:
        lines.append(f"- Stale/broken findings: {', '.join(stale)}")
    else:
        lines.append("- Stale/broken findings: none detected by this inspect-only check")
    return "\n".join(lines)
