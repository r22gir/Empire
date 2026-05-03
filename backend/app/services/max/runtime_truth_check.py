"""Inspect-only runtime truth checks for MAX live-state claims."""
from __future__ import annotations

import socket
import subprocess
import re
from datetime import datetime, timezone
from typing import Any

import httpx


# Signals that indicate the user is asking about runtime/deployment status.
# IMPORTANT: These are matched as whole-word patterns to avoid false positives
# on legitimate task-delegation messages like "start OpenClaw working on X" or
# "create an OpenClaw task — is max broken?".
INTENT_SIGNALS = [
    # Explicit runtime-status requests (require exact phrase)
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
    # Deployment / commit queries (require exact phrase)
    "commit is running",
    "what commit",
    "live commit",
    "local commit",
    "public commit",
    "is archiveforge live",
    "is transcriptforge live",
    "is this live",
    "why don’t i see the fix",
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
    # Standalone "how is X running?" style queries (word-boundary matched below)
]

# Short signals (<= 5 chars) must match as whole words to avoid substring noise.
_SHORT_SIGNALS = {"max", "live", "new?"}

# If ANY of these task-delegation keywords appear in the message, do NOT run
# the runtime truth check — route to the AI model for task planning instead.
TASK_DELEGATION_BLOCKLIST = [
    "create ",
    "create an",
    "create a",
    "start ",
    "start an",
    "start a",
    "delegate ",
    "add task",
    "add a task",
    "queue task",
    "submit task",
    "submit a task",
    "send task",
    "run task",
    "start working",
    "start openclaw",
    "start codeforge",
    "start hermes",
    "openclaw task",
    "codeforge task",
    "hermes task",
    "dispatch openclaw",
    "dispatch to openclaw",
    "new task for",
    "new openclaw task",
    "new codeforge task",
    "task for openclaw",
    "task for codeforge",
    "task for hermes",
]


def _normalize_intent_text(message: str | None) -> str:
    text = (message or "").lower().strip()
    # Normalize all quote variants to straight apostrophe U+0027
    text = text.replace("\u2018", "'")   # LEFT SINGLE QUOTATION MARK → straight
    text = text.replace("\u2019", "'")   # RIGHT SINGLE QUOTATION MARK → straight
    text = text.replace("`", "'")        # BACKTICK → straight
    text = re.sub(r"\s+", " ", text)
    return text


def should_run_runtime_truth_check(message: str | None) -> bool:
    text = _normalize_intent_text(message)
    if not text:
        return False

    # Block task-delegation messages — do not intercept task creation/tracking.
    for block in TASK_DELEGATION_BLOCKLIST:
        if block in text:
            return False

    # Normalize each signal the same way before substring matching.
    for signal in INTENT_SIGNALS:
        normalized_signal = signal.replace("\u2019", "'").replace("\u2018", "'")
        if normalized_signal in text:
            # Disambiguate short signals that could be substrings of task words.
            if signal in _SHORT_SIGNALS:
                # Require word-boundary match (preceded/followed by non-alphanumeric).
                pattern = r"(?<![a-z0-9])" + re.escape(normalized_signal) + r"(?![a-z0-9])"
                if re.search(pattern, text):
                    return True
            else:
                return True

    return False


# Casual "what's new" signals — bounded summary, NOT full runtime truth check
WHATS_NEW_SIGNALS = [
    # Core "what's new" patterns
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
    "recent updates",
    "recent changes",
    "status summary",
    # Extended recent activity patterns
    "latest updates",
    "most recent updates",
    "recent activity",
    "recent work",
    "latest changes",
    "latest status",
    "what happened",
    "what happened recently",
    "any new updates",
    "any updates",
    "new updates",
    "updates in empire",
    "empirebox updates",
    "empire updates",
    "ecosystem updates",
    # Time-window recent activity (extracts time_window_hours if passed)
    "last 24 hours",
    "last 48 hours",
    "since yesterday",
    "this morning",
    "last week",
    "recent commits",
    "latest commits",
]


def should_run_whats_new_summary(message: str | None) -> bool:
    text = _normalize_intent_text(message)
    if not text:
        return False
    for block in TASK_DELEGATION_BLOCKLIST:
        if block in text:
            return False
    for signal in WHATS_NEW_SIGNALS:
        normalized_signal = signal.replace("\u2019", "'").replace("\u2018", "'")
        if normalized_signal in text:
            if signal in _SHORT_SIGNALS:
                pattern = r"(?<![a-z0-9])" + re.escape(normalized_signal) + r"(?![a-z0-9])"
                if re.search(pattern, text):
                    return True
            else:
                return True
    return False


def _git_recent_commits(count: int = 5) -> list[dict[str, str]]:
    """Get recent git commits — used for bounded what's new summary."""
    try:
        proc = subprocess.run(
            ["git", "log", f"--oneline", f"-{count}"],
            capture_output=True, text=True, timeout=5,
        )
        if proc.returncode != 0:
            return []
        commits = []
        for line in proc.stdout.strip().splitlines():
            parts = line.split(" ", 1)
            if len(parts) == 2:
                commits.append({"hash": parts[0], "message": parts[1]})
        return commits
    except Exception:
        return []


def _git_recent_commits_v10() -> list[dict[str, str]]:
    """Get recent commits from the v10 repo."""
    v10_path = "/home/rg/empire-repo-v10"
    try:
        proc = subprocess.run(
            ["git", "log", f"--oneline", f"-{5}"],
            capture_output=True, text=True, timeout=5,
            cwd=v10_path,
        )
        if proc.returncode != 0:
            return []
        commits = []
        for line in proc.stdout.strip().splitlines():
            parts = line.split(" ", 1)
            if len(parts) == 2:
                commits.append({"hash": parts[0], "message": parts[1]})
        return commits
    except Exception:
        return []


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


def run_whats_new_summary() -> dict[str, Any]:
    """Bounded what's new summary — only safe, non-invasive checks.

    Limits: recent git commits (live + v10), port status for key services,
    optional OpenClaw task count. No shell sprawl, no DB table scans.
    """
    live_commits = _git_recent_commits(5)
    v10_commits = _git_recent_commits_v10()
    commit = _git_commit()

    # Key port checks (bounded set — no broad scanning)
    ports = {
        "live_backend_8000": _port_open("127.0.0.1", 8000),
        "live_frontend_3005": _port_open("127.0.0.1", 3005),
        "v10_backend_8010": _port_open("127.0.0.1", 8010),
        "v10_frontend_3010": _port_open("127.0.0.1", 3010),
    }

    # Optional OpenClaw task stats (only if OpenClaw is up)
    openclaw_stats = None
    try:
        with httpx.Client(timeout=3.0) as client:
            resp = client.get("http://127.0.0.1:7878/openclaw/tasks/stats", follow_redirects=True)
            if resp.status_code == 200:
                data = resp.json()
                openclaw_stats = {
                    "total": data.get("total", 0),
                    "completed": data.get("completed", 0),
                    "pending": data.get("pending", 0),
                }
    except Exception:
        openclaw_stats = None  # Don't fail on OpenClaw being down

    return {
        "skill": "whats-new-summary",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "live_commit": commit,
        "live_recent_commits": live_commits,
        "v10_recent_commits": v10_commits,
        "ports": ports,
        "openclaw_stats": openclaw_stats,
    }


def format_whats_new_summary(result: dict[str, Any]) -> str:
    """Format what's new summary into a concise user-facing update."""
    commit = result.get("live_commit", {})
    live_commits = result.get("live_recent_commits", []) or []
    v10_commits = result.get("v10_recent_commits", []) or []
    ports = result.get("ports", {})

    lines = ["Here's what's new:\n"]

    # Recent live commits (show top 3)
    if live_commits:
        lines.append("- Recent live changes:")
        for c in live_commits[:3]:
            lines.append(f"  • {c.get('hash', '?')} — {c.get('message', '')}")
    else:
        lines.append("- Live: no recent commits found")

    # Recent v10 commits (show top 2)
    if v10_commits:
        lines.append("- v10 test lane recent changes:")
        for c in v10_commits[:2]:
            lines.append(f"  • {c.get('hash', '?')} — {c.get('message', '')}")

    # Service status
    b8000 = ports.get("live_backend_8000")
    f3005 = ports.get("live_frontend_3005")
    b8010 = ports.get("v10_backend_8010")
    f3010 = ports.get("v10_frontend_3010")
    status_parts = []
    if b8000:
        status_parts.append("Live backend (8000) is up")
    else:
        status_parts.append("Live backend (8000) is down")
    if f3005:
        status_parts.append("Live frontend (3005) is up")
    if b8010:
        status_parts.append("v10 backend (8010) is up")
    if f3010:
        status_parts.append("v10 frontend (3010) is up")
    lines.append(f"- Status: {', '.join(status_parts)}")

    # OpenClaw stats if available
    stats = result.get("openclaw_stats")
    if stats:
        lines.append(
            f"- OpenClaw: {stats.get('total', 0)} tasks ({stats.get('completed', 0)} done, {stats.get('pending', 0)} pending)"
        )

    return "\n".join(lines)
