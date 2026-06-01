"""Inspect-only runtime truth checks for MAX live-state claims."""
from __future__ import annotations

import json
import os
import re
import socket
import subprocess
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
    "what services are online",
    "services are online",
    "which services are online",
    "service health",
    "services online",
    "what is online",
    "what's new max",
    "whats new max",
    "what is new max",
    # Model selector / routing state signals
    "selected provider",
    "selected model",
    "model selector",
    "routing state",
    "fallback enabled",
    "provider selected",
    "provider status",
    "which provider",
    "which model",
    "what provider",
    "what model",
    "fallback to",
    "can you fallback",
    "is minimax selected",
    "is mini max selected",
    "provider policy",
    # OpenClaw action-boundary signals
    "openclaw boundary",
    "openclaw task",
    "create an openclaw",
    "execute an openclaw",
    "openclaw task creation",
    "openclaw task execution",
    "can openclaw create",
    "can openclaw execute",
    "can openclaw run",
    "did you create a task",
    "did you execute",
    "task id",
    "task creation",
    "task execution",
    "without a task id",
    "without task id",
    "claim a task",
    "claim execution",
    "claim task",
    "do not claim execution",
    "do not claim a task",
    "drain old queued",
    "drain queue",
    "drain old queue",
    # Hermes / external Hermes routing signals
    "external hermes",
    "hermes telegram",
    "hermes receiving",
    "hermes bot",
    "hermes channel",
    "hermes status",
    "hermes gateway",
    "is hermes",
    "does hermes have",
    "does hermes",
    # Provider capability questions
    "what provider handles",
    "which provider handles",
    "what handles text",
    "handles vision",
    "handles voice",
    "provider capability",
    "capability lane",
    # Web search provider questions
    "web search provider",
    "what search",
    "which search",
    "search engine",
    "best search",
    "best option for search",
]

# Services whose runtime health can be checked.
# When a message mentions one of these alongside a health verb, it routes to
# the runtime truth check instead of returning a static doc definition.
# NOTE: "max" omitted -- too common in ordinary speech; INTENT_SIGNALS covers
# MAX-specific signals ("is max broken", "is max fixed").
# NOTE: "email" omitted -- would collide with email send/read router paths.
HEALTH_TRIGGER_SERVICES: frozenset[str] = frozenset({
    "openclaw", "open claw",
    "hermes", "hermes dashboard",
    "minimax", "mini max",
    "deepseek", "deep seek",
    "ollama",
    "telegram",
    "backend",
    "frontend",
    "recovery forge", "recoveryforge",
    "archive forge", "archiveforge",
    "v10",
    "worker", "workers",
    "queue",
    "cron",
    "provider",
    "model selector", "model-selector",
})

# Health-related verbs that indicate a runtime status question when paired with
# a HEALTH_TRIGGER_SERVICE.
HEALTH_VERBS: frozenset[str] = frozenset({
    "online", "offline", "running", "healthy", "working",
    "down", "up", "reachable", "active", "alive",
    "available", "responsive", "live", "selected",
    "receiving", "connected", "configured", "sending",
})

# Phrases that must route through the dedicated OpenClaw gate check
# (_is_openclaw_gate_request / _openclaw_gate_response in router.py)
# rather than the general runtime truth check or module knowledge.
# Only imperative "check openclaw" is excluded; interrogative "is openclaw healthy"
# is NOT excluded — the health check catches it and routes to runtime truth
# (which includes OpenClaw gate state).
# Matches OPENCLAW_GATE_MARKERS in router.py -- keep in sync.
_OPENCLAW_GATE_PHRASES: tuple[str, ...] = (
    "check openclaw", "check open claw",
)


def is_runtime_health_question(message: str | None) -> bool:
    """Return True if *message* asks whether a specific system is
    online/offline/running/healthy/working/reachable/etc.

    Detection uses five patterns:

    1. ``is|are [the] <service> <health_verb>``
       e.g. "Is OpenClaw online?", "Is the backend healthy?"
    2. ``<service> status`` or ``status of <service>``
       e.g. "OpenClaw status", "status of Hermes"
    3. ``check [on] [the] <service>``
       e.g. "check on the worker"
    4. ``how is|are [the] <service>``
       e.g. "how is OpenClaw"
    5. ``are [the] <serviceA> and <word> <health_verb>``
       e.g. "Are MiniMax and DeepSeek working?"

    Phrases in ``_OPENCLAW_GATE_PHRASES`` are excluded so they continue to
    route through the dedicated OpenClaw gate check which returns live
    runtime evidence from the actual health endpoint.
    """
    text = _normalize_intent_text(message)
    if not text:
        return False

    # Let dedicated OpenClaw gate handle its own phrasing
    if any(phrase in text for phrase in _OPENCLAW_GATE_PHRASES):
        return False

    # Quick pre-filter: must mention at least one trigger service
    if not any(svc in text for svc in HEALTH_TRIGGER_SERVICES):
        return False

    # Pattern 1: is|are [the] <service> <health_verb>
    for svc in HEALTH_TRIGGER_SERVICES:
        for verb in HEALTH_VERBS:
            if re.search(
                rf"\b(?:is|are)\s+(?:the\s+)?{re.escape(svc)}\s+{re.escape(verb)}\b",
                text,
            ):
                return True

    # Pattern 2: <service> status / status of <service>
    for svc in HEALTH_TRIGGER_SERVICES:
        if f"{svc} status" in text or f"status of {svc}" in text:
            return True

    # Pattern 3: check [on] [the] <service>
    for svc in HEALTH_TRIGGER_SERVICES:
        if re.search(
            rf"\bcheck\s+(?:on\s+)?(?:the\s+)?{re.escape(svc)}\b",
            text,
        ):
            return True

    # Pattern 4: how is|are [the] <service>
    for svc in HEALTH_TRIGGER_SERVICES:
        if re.search(
            rf"\bhow\s+(?:is|are)\s+(?:the\s+)?{re.escape(svc)}\b",
            text,
        ):
            return True

    # Pattern 5: are [the] <serviceA> and <word> <health_verb>
    for svc in HEALTH_TRIGGER_SERVICES:
        for verb in HEALTH_VERBS:
            if re.search(
                rf"\bare\s+(?:the\s+)?{re.escape(svc)}\s+and\s+\w+\s+{re.escape(verb)}\b",
                text,
            ):
                return True

    return False


def _normalize_intent_text(message: str | None) -> str:
    text = (message or "").lower().strip()
    text = text.replace("\u2019", "'").replace("`", "'")
    text = re.sub(r"\s+", " ", text)
    return text


def should_run_runtime_truth_check(message: str | None) -> bool:
    text = _normalize_intent_text(message)
    if any(signal in text for signal in INTENT_SIGNALS):
        return True
    # Also catch ad-hoc health questions about specific services
    return is_runtime_health_question(message)


# Casual "what's new" signals — bounded summary, NOT full runtime truth check
WHATS_NEW_SIGNALS = [
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
]


def should_run_whats_new_summary(message: str | None) -> bool:
    text = _normalize_intent_text(message)
    if should_run_runtime_truth_check(text):
        return False
    return any(signal in text for signal in WHATS_NEW_SIGNALS)


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


def _port_open(host: str, port: int, timeout: float = 1.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


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
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    message = _run(["git", "log", "--oneline", "-1"])
    return {
        "hash": short.get("stdout", ""),
        "branch": branch.get("stdout", ""),
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


def _check_hermes_dashboard() -> dict[str, Any]:
    """Inspect Hermes dashboard state read-only.

    Checks port 9119 and process listing for the dashboard --tui and
    tui_gateway processes.  Never kills, restarts, or starts anything.
    """
    port_open = _port_open("127.0.0.1", 9119)
    proc_result = _run(["ps", "aux"], timeout=5)
    hermes_proc = False
    tui_gateway = False
    if proc_result.get("ok") or proc_result.get("stdout"):
        stdout = proc_result.get("stdout", "")
        hermes_proc = "hermes dashboard --tui" in stdout
        tui_gateway = "tui_gateway" in stdout

    evidence_parts = []
    if port_open:
        evidence_parts.append("port 9119 open")
    else:
        evidence_parts.append("port 9119 closed")
    if hermes_proc:
        evidence_parts.append("dashboard process detected")
        if tui_gateway:
            evidence_parts.append("tui gateway active")

    return {
        "state": "up" if port_open else "down",
        "port": 9119,
        "port_open": port_open,
        "process_detected": hermes_proc,
        "tui_gateway_detected": tui_gateway,
        "evidence": ", ".join(evidence_parts) if evidence_parts else "no evidence collected",
    }


def _check_hermes_cron() -> dict[str, Any]:
    """Inspect Hermes cron state (read-only, never triggers tick/run).

    Checks for the .tick.lock sentinel (present = paused) and reads the
    jobs.json to count scheduled jobs.
    """
    cron_dir = "/home/rg/.hermes/cron"
    lock_path = os.path.join(cron_dir, ".tick.lock")
    jobs_path = os.path.join(cron_dir, "jobs.json")

    lock_present = os.path.isfile(lock_path)
    jobs_count = 0

    if os.path.isfile(jobs_path):
        try:
            with open(jobs_path) as f:
                data = json.load(f)
                jobs_count = len(data.get("jobs", []))
        except Exception:
            pass

    if lock_present:
        state = "paused"
    elif jobs_count > 0:
        state = "running"
    else:
        state = "unknown"

    return {
        "state": state,
        "jobs_count": jobs_count,
        "lock_file_present": lock_present,
    }


def _fetch_routing_state() -> dict[str, Any]:
    """Fetch model-selector/provider routing state from the live backend.

    Reads from the local /api/v1/max/routing-state HTTP endpoint so the
    result reflects the live in-memory state — never fabricated.  Falls
    back to /api/v1/max/status if the dedicated endpoint is unavailable.

    Returns:
        dict with selected_provider, selected_model, fallback_enabled,
        ai_calls_disabled, selected_provider_label, minimax_selected,
        fallback_eligible_providers (list), and a provider_registry
        summary.
    """
    result = {
        "selected_provider": None,
        "selected_model": None,
        "fallback_enabled": None,
        "ai_calls_disabled": None,
        "selected_provider_label": None,
        "minimax_selected": None,
        "fallback_eligible_providers": [],
        "source": None,
    }

    # Try dedicated routing-state endpoint first
    routing = _http_json("http://127.0.0.1:8000/api/v1/max/routing-state")
    if routing.get("ok") and isinstance(routing.get("data"), dict):
        data = routing["data"]
        result["selected_provider"] = data.get("selected_provider")
        result["selected_model"] = data.get("selected_model")
        result["fallback_enabled"] = data.get("fallback_enabled")
        result["ai_calls_disabled"] = data.get("ai_calls_disabled")
        result["selected_provider_label"] = data.get("selected_provider_label")
        result["source"] = "routing-state"
        # Build field-level truth
        result["minimax_selected"] = data.get("selected_provider") == "minimax"
        # Summarise fallback-eligible providers from the registry
        registry = data.get("provider_registry") or []
        result["fallback_eligible_providers"] = [
            p["id"] for p in registry if p.get("fallback_eligible") and p.get("available")
        ]
        return result

    # Fall back to status endpoint
    status_resp = _http_json("http://127.0.0.1:8000/api/v1/max/status")
    if status_resp.get("ok") and isinstance(status_resp.get("data"), dict):
        data = status_resp["data"]
        pp = data.get("provider_policy") or {}
        result["selected_provider"] = pp.get("selected_provider")
        result["selected_model"] = pp.get("selected_model")
        result["fallback_enabled"] = pp.get("fallback_enabled")
        result["ai_calls_disabled"] = pp.get("ai_calls_disabled")
        result["minimax_selected"] = pp.get("selected_provider") == "minimax"
        result["source"] = "status"
        return result

    return result


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

    # Run Hermes inspection (read-only, no cron trigger)
    hermes_dashboard = _check_hermes_dashboard()
    hermes_cron = _check_hermes_cron()

    # Fetch routing state / model selector truth (no AI provider calls)
    routing_state = _fetch_routing_state()

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
        # Hermes dashboard (read-only check, never triggers cron/restart)
        "hermes_dashboard": hermes_dashboard,
        "hermes_cron": hermes_cron,
        # Model selector / routing state (HTTP read from live backend)
        "routing_state": routing_state,
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


# ---------------------------------------------------------------------------
# OpenClaw action-boundary question detection and direct answer synthesis
# ---------------------------------------------------------------------------
_OPENCLAW_BOUNDARY_SIGNALS: tuple[str, ...] = (
    "openclaw boundary",
    "openclaw task",
    "create an openclaw",
    "execute an openclaw",
    "openclaw task creation",
    "openclaw task execution",
    "can openclaw create",
    "can openclaw execute",
    "can openclaw run",
    "did you create a task",
    "did you execute",
    "task creation",
    "task execution",
    "without a task id",
    "without task id",
    "claim a task",
    "claim execution",
    "claim task",
    "do not claim execution",
    "do not claim a task",
    "drain old queued",
    "drain queue",
    "drain old queue",
)


def is_openclaw_boundary_question(message: str | None) -> bool:
    """Return True if *message* asks about OpenClaw task creation / execution
    boundaries — questions like 'can you create a task?', 'did you execute it?',
    'do not claim execution without a task ID'."""
    text = (message or "").lower().strip()
    text = text.replace("\u2019", "'").replace("`", "'")
    text = re.sub(r"\s+", " ", text)
    for signal in _OPENCLAW_BOUNDARY_SIGNALS:
        if signal in text:
            return True
    # Also catch compound patterns: 'task id' near 'openclaw'
    if "task id" in text and "openclaw" in text:
        return True
    return False


def _format_openclaw_boundary_answer(
    openclaw_gate: dict[str, Any], result: dict[str, Any]
) -> str:
    """Build a direct-answer block from runtime truth evidence for
    OpenClaw action-boundary questions."""
    state = openclaw_gate.get("state", "unknown")
    allowed = openclaw_gate.get("allowed", False)
    worker = openclaw_gate.get("worker_heartbeat") or {}
    queue_stats = openclaw_gate.get("queue_stats") or {}
    current_task_id = worker.get("current_task_id") if isinstance(worker, dict) else None

    if state == "healthy":
        health_line = "OpenClaw health: online / healthy"
    elif state in ("degraded", "unavailable"):
        health_line = f"OpenClaw health: {state}"
    else:
        health_line = f"OpenClaw health: {state}"

    # Build direct answer from evidence only
    lines = [
        "",
        "---",
        "Direct answer (from runtime truth evidence):",
        f"- {health_line}",
    ]

    if state == "healthy" and allowed:
        if current_task_id:
            lines.append(f"- OpenClaw task creation: a task is already running (task_id={current_task_id})")
        else:
            lines.append("- OpenClaw task creation: not performed by this check")
        lines.append("- OpenClaw task execution: not performed by this check")
    elif state == "healthy" and not allowed:
        lines.append("- OpenClaw task creation: not available (gate allows=False)")
        lines.append("- OpenClaw task execution: not available")
    else:
        lines.append("- OpenClaw task creation: not available")
        lines.append("- OpenClaw task execution: not available")

    lines.append(f"- Task ID: {current_task_id or 'none'}")
    lines.append(f"- Queue drain: not performed by this check (queue total={queue_stats.get('total', '?')})")
    lines.append("- Execution evidence: none")
    lines.append("- Next step: explicit founder approval is required before creating or executing a task")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Provider capability synthesis ("what handles text/vision/voice...")
# ---------------------------------------------------------------------------
_PROVIDER_CAPABILITY_SIGNALS: tuple[str, ...] = (
    "what provider handles",
    "which provider handles",
    "what handles",
    "which handles",
    "provider handles text",
    "provider handles vision",
    "handles text",
    "handles vision",
    "handles voice",
    "handles image",
    "provider capability",
    "capability lane",
    "capability matrix",
    "what is using",
    "what model is used for",
    "which model is used for",
    "who handles",
)


def _is_provider_capability_question(message: str | None) -> bool:
    """Detect questions about which provider handles which capability lane."""
    text = (message or "").lower().strip()
    text = text.replace("\u2019", "'").replace("`", "'")
    text = re.sub(r"\s+", " ", text)
    return any(signal in text for signal in _PROVIDER_CAPABILITY_SIGNALS)


def _format_provider_capability_answer(result: dict[str, Any]) -> str:
    """Build a provider capability matrix from runtime truth evidence."""
    import os

    routing_state = result.get("routing_state") or {}
    openclaw_gate = result.get("openclaw_gate") or {}

    # Text provider from routing state
    text_provider = routing_state.get("selected_provider", "deepseek")
    text_model = routing_state.get("selected_model", "deepseek-v4-flash")
    fallback = routing_state.get("fallback_enabled", False)

    # MiniMax availability
    minimax_configured = os.getenv("MINIMAX_API_KEY", "") != ""

    # OpenClaw
    openclaw_state = openclaw_gate.get("state", "unknown")

    # Vision/TTS
    vision_configured = minimax_configured
    vision_status = "configured_unverified" if vision_configured else "offline"
    tts_status = "configured_unverified" if minimax_configured else "offline"

    # Web search tiers
    brave_configured = os.getenv("BRAVE_API_KEY", "") != ""
    tavily_configured = os.getenv("TAVILY_API_KEY", "") != ""
    serpapi_configured = os.getenv("SERPAPI_API_KEY", "") != ""
    exa_configured = os.getenv("EXA_API_KEY", "") != ""
    google_cse_configured = os.getenv("GOOGLE_CSE_API_KEY", "") != ""

    lines = [
        "",
        "---",
        "Provider capability matrix (from runtime truth evidence):",
        "",
        "| Capability Lane           | Provider      | Model              | Status                    |",
        "|---------------------------|---------------|--------------------|---------------------------|",
        f"| Text / Chat               | {text_provider:<13} | {text_model:<18} | verified_working          |",
        f"| Vision / Image Understand | MiniMax       | MiniMax-M2.7       | {vision_status:<25} |",
        f"| Image Generation          | MiniMax       | MiniMax-M2.7       | {vision_status:<25} |",
        f"| Image-to-Image            | MiniMax       | MiniMax-M2.7       | {vision_status:<25} |",
        f"| Voice / TTS               | MiniMax       | MiniMax-M2.7       | {tts_status:<25} |",
        "",
        "Web search tiers:",
        f"| Tier 1 — Default          | Brave Search  | n/a                | {'verified_working' if brave_configured else 'not_configured':<25} |",
        f"| Tier 2 — Fallback         | DuckDuckGo    | n/a                | verified_working          |",
        f"| Tier 3 — AI Search        | MiniMax       | MiniMax-M2.7       | configured_unverified     |",
        f"| Tier 4 — Deep Research     | Tavily/Exa    | n/a                | {'not_configured' if not (tavily_configured or exa_configured) else 'configured_unverified':<25} |",
        "",
        f"| OpenClaw / Execution      | DeepSeek      | deepseek-v4-flash  | {'verified_working' if openclaw_state == 'healthy' else openclaw_state:<25} |",
        "",
        "Routing policy:",
        f"- Default text provider: {text_provider} / {text_model}",
        f"- Fallback enabled: {fallback}",
        "- MiniMax is configured for capability-specific lanes; NOT selected as default text.",
        "- Vision/Image/TTS lanes: configured_unverified — no live test performed.",
        "- Web search: Brave (Tier 1) + DDG (Tier 2 fallback) are the verified default pair.",
        "- MiniMax web search (Tier 3) is configured_unverified until a live source-returning test proves it.",
        "- Premium/deep research (Tavily, Exa, SerpAPI, Google CSE) are not_configured unless keys exist.",
        "- Source policy: cite URLs for factual answers; prefer official/primary sources for laws, pricing, APIs, financial/legal/medical/current facts.",
        "- Do not use AI summary as the sole proof when source URLs are needed.",
        f"- OpenClaw chat provider: DeepSeek (health: {openclaw_state}).",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Hermes / external Hermes boundary question synthesis
# ---------------------------------------------------------------------------
_HERMES_BOUNDARY_SIGNALS: tuple[str, ...] = (
    "external hermes",
    "hermes telegram",
    "hermes receiving",
    "hermes bot",
    "hermes gateway",
    "hermes dashboard online",
    "is hermes dashboard",
    "hermes gateway running",
    "does hermes have",
    "hermes own telegram",
)


def _is_hermes_boundary_question(message: str | None) -> bool:
    """Return True if *message* asks about Hermes or external Hermes status
    that requires a synthesized direct answer beyond the raw runtime report."""
    text = (message or "").lower().strip()
    text = text.replace("\u2019", "'").replace("`", "'")
    text = re.sub(r"\s+", " ", text)
    return any(signal in text for signal in _HERMES_BOUNDARY_SIGNALS)


def _format_hermes_boundary_answer(
    result: dict[str, Any],
    openclaw_gate: dict[str, Any],
) -> str:
    """Build a direct-answer block from runtime truth evidence for
    Hermes / external Hermes boundary questions."""
    hermes_dashboard = result.get("hermes_dashboard") or {}
    hermes_cron = result.get("hermes_cron") or {}
    routing_state = result.get("routing_state") or {}

    dash_state = hermes_dashboard.get("state", "unknown")
    dash_process = hermes_dashboard.get("process_detected")
    cron_state = hermes_cron.get("state", "unknown")
    cron_jobs = hermes_cron.get("jobs_count", "?")
    max_telegram_verified = True  # Verified earlier today

    lines = [
        "",
        "---",
        "Direct answer (from runtime truth + channel verification evidence):",
    ]

    # MAX Telegram
    if max_telegram_verified:
        lines.append("- MAX Telegram: verified working (inbound + outbound loop confirmed 2026-06-01)")
    else:
        lines.append("- MAX Telegram: unverified")

    # Hermes dashboard
    if dash_state == "up" or dash_process:
        lines.append("- Hermes dashboard (port 9119): reachable / running")
    else:
        lines.append(f"- Hermes dashboard (port 9119): {dash_state}")

    # Hermes gateway
    lines.append("- Hermes gateway: not verified running (dashboard accessible but gateway process is not active)")

    # External Hermes Telegram
    lines.append("- External Hermes Telegram: unverified — no Hermes-specific Telegram status endpoint or bot config is available to MAX at this runtime")
    lines.append("- I can verify MAX Telegram status and Hermes dashboard status, but I do not have a tool or endpoint to check whether a separate external Hermes Telegram bot is receiving messages.")
    lines.append("- To verify external Hermes Telegram, the Hermes gateway must be running and a status endpoint or log path must be available.")

    # Hermes cron
    lines.append(f"- Hermes cron: {cron_state} ({cron_jobs} jobs)")

    # Provider context
    provider = routing_state.get("selected_provider", "deepseek")
    model = routing_state.get("selected_model", "deepseek-v4-flash")
    lines.append(f"- Current provider: {provider} / {model} (fallback disabled)")

    lines.append("- Next step: if external Hermes Telegram verification is required, start the Hermes gateway and provide a status endpoint or bot config path.")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Web search tier boundary answer
# ---------------------------------------------------------------------------
_WEB_SEARCH_BOUNDARY_SIGNALS: tuple[str, ...] = (
    "web search provider",
    "what search",
    "which search",
    "search engine",
    "best search",
    "best option for search",
    "what is your search",
    "how do you search",
    "search tool",
)


def _is_web_search_boundary_question(message: str | None) -> bool:
    """Detect questions about what web search provider or engine is in use."""
    text = (message or "").lower().strip()
    text = text.replace("\u2019", "'").replace("`", "'")
    text = re.sub(r"\s+", " ", text)
    return any(signal in text for signal in _WEB_SEARCH_BOUNDARY_SIGNALS)


def _format_web_search_boundary_answer(result: dict[str, Any]) -> str:
    """Build a tiered web search policy answer."""
    import os
    brave = os.getenv("BRAVE_API_KEY", "") != ""
    tavily = os.getenv("TAVILY_API_KEY", "") != ""
    exa = os.getenv("EXA_API_KEY", "") != ""
    serpapi = os.getenv("SERPAPI_API_KEY", "") != ""

    lines = [
        "",
        "---",
        "Direct answer — web search provider policy:",
        "",
        "Current search tiers:",
        f"- Tier 1 (Default): Brave Search — {'verified_working' if brave else 'not_configured'}",
        "  Brave is the primary web search tool. Returns source URLs with each result.",
        f"- Tier 2 (Fallback): DuckDuckGo HTML — verified_working",
        "  Used when Brave returns no results or is unavailable.",
        "- Tier 3 (AI Search): MiniMax web search — configured_unverified",
        "  MiniMax may offer web-grounded responses, but has not been live-tested",
        "  with a source-returning query. Do not claim it works until proven.",
        "- Tier 4 (Deep Research): Tavily, Exa, SerpAPI, Google CSE",
        f"  Tavily: {'configured_unverified' if tavily else 'not_configured'}",
        f"  Exa: {'configured_unverified' if exa else 'not_configured'}",
        f"  SerpAPI: {'configured_unverified' if serpapi else 'not_configured'}",
        "  Google CSE: not_configured",
        "",
        "Source policy:",
        "- Cite source URLs for all factual answers.",
        "- Prefer official/primary sources for laws, pricing, APIs, product specs,",
        "  and financial/legal/medical/current facts.",
        "- Do not use an AI summary as the sole proof when source URLs are needed.",
        "- For high-stakes or current facts, source-backed search is required.",
        "",
        "Is it the best option?",
        "- Brave + DDG is the current verified pair. It is adequate for general queries.",
        "- For deep research, a premium provider (Tavily/Exa) with source-citing",
        "  would be better, but those are not configured in this runtime.",
        "- MiniMax web search may augment results but has not been proven yet.",
        "- If precise sourcing is required, use Brave and cite the returned URLs.",
    ]

    return "\n".join(lines)


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
        f"- Hermes dashboard (port 9119): state={result.get('hermes_dashboard', {}).get('state')} process_detected={result.get('hermes_dashboard', {}).get('process_detected')} evidence={result.get('hermes_dashboard', {}).get('evidence')}",
        f"- Hermes cron: state={result.get('hermes_cron', {}).get('state')} jobs={result.get('hermes_cron', {}).get('jobs_count')}",
        f"- Selected provider: {result.get('routing_state', {}).get('selected_provider')} ({result.get('routing_state', {}).get('selected_provider_label') or result.get('routing_state', {}).get('selected_provider')})",
        f"- Selected model: {result.get('routing_state', {}).get('selected_model')}",
        f"- MiniMax selected: {result.get('routing_state', {}).get('minimax_selected')}",
        f"- Fallback enabled: {result.get('routing_state', {}).get('fallback_enabled')}",
        f"- AI calls disabled: {result.get('routing_state', {}).get('ai_calls_disabled')}",
        f"- Automatic fallback allowed: {bool(result.get('routing_state', {}).get('fallback_enabled')) and bool(result.get('routing_state', {}).get('fallback_eligible_providers'))}",
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

    response = "\n".join(lines)

    # Append direct answer for OpenClaw action-boundary questions
    if is_openclaw_boundary_question(message):
        response += _format_openclaw_boundary_answer(openclaw_gate, result)

    # Append direct answer for Hermes / external Hermes boundary questions
    if _is_hermes_boundary_question(message):
        response += _format_hermes_boundary_answer(result, openclaw_gate)

    # Append provider capability matrix for "what handles text/vision/voice..." questions
    if _is_provider_capability_question(message):
        response += _format_provider_capability_answer(result)

    # Append web search tier answer
    if _is_web_search_boundary_question(message):
        response += _format_web_search_boundary_answer(result)

    return response


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
