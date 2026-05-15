"""Inspect-only runtime truth checks for MAX live-state claims."""
from __future__ import annotations

import socket
import subprocess
import re
from datetime import datetime, timezone
from typing import Any

import httpx

from app.services.max.lane_runtime_metadata import get_lane_git_metadata


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
    "what services are online",
    "services are online",
    "which services are online",
    "service health",
    "services online",
    "what is online",
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

# External/public topics that should NOT trigger what's-new summary.
# These indicate the user is asking about the world, not EmpireBox/MAX.
WHATS_NEW_NEGATIVE_GUARDS = [
    # Countries / conflict zones
    "iran", "israel", "ukraine", "russia", "china", "taiwan",
    "korea", "north korea", "south korea", "syria", "lebanon",
    "gaza", "palestine", "haiti", "venezuela", "pakistan",
    "afghanistan", "iraq", "yemen", "sudan", "myanmar",
    # War / conflict
    "war ", "war today", "war in ", "the war", "conflict",
    # Financial markets
    "stock market", "markets today", "stock news", "trading day",
    "nasdaq", "dow jones", "s&p", "crypto today", "bitcoin",
    "market today", "financial news",
    # Tech / companies (external)
    "openai", "google", "microsoft", "apple", "meta ", "amazon",
    "nvidia", "tesla", "facebook", "twitter", "x corp",
    "ai news", "tech news", "startup news",
    # News / current events
    "news today", "headlines", "breaking news", "current events",
    "today's news", "in the news",
    # Weather
    "weather in", "weather like", "forecast for", "rain in",
    "snow in", "temperature in",
    # General current-awareness
    "happened today", "what happened in", "what's happening in",
    "latest on", "recent news in",
    # Sports
    "football", "basketball", "soccer", "sports",
]

# Anchor signals that confirm the user IS asking about EmpireBox/MAX.
# Presence of ANY anchor allows what's-new to run even with negative guards.
WHATS_NEW_ANCHORS = [
    "empirebox", "empire box", "empire-box",
    "max status", "max what's new", "max new",
    "system status", "system what's new",
    "v10 status", "v10 what's new",
    "in empire", "in max ", "on empirebox",
    "for empirebox", "empirebox status",
    "backend status", "frontend status",
    "what's new in v10", "whats new in v10",
    "what's new in empire", "whats new in empire",
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

    # Check for positive signal
    matched_signal = None
    for signal in WHATS_NEW_SIGNALS:
        normalized_signal = signal.replace("\u2019", "'").replace("\u2018", "'")
        if normalized_signal in text:
            if signal in _SHORT_SIGNALS:
                pattern = r"(?<![a-z0-9])" + re.escape(normalized_signal) + r"(?![a-z0-9])"
                if re.search(pattern, text):
                    matched_signal = signal
                    break
            else:
                matched_signal = signal
                break

    if not matched_signal:
        return False

    # Check for anchor signal — if present, always allow (Empire/MAX/system question)
    for anchor in WHATS_NEW_ANCHORS:
        if anchor in text:
            return True

    # Check negative guards — if any match, this is a public-world question
    # do NOT run what's-new summary
    for guard in WHATS_NEW_NEGATIVE_GUARDS:
        if guard in text:
            return False

    return True


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
    lane_meta = get_lane_git_metadata()
    return {
        "hash": lane_meta.get("commit") or "",
        "branch": lane_meta.get("branch") or "",
        "message": lane_meta.get("message") or "",
        "lane": lane_meta.get("lane"),
        "worktree_path": lane_meta.get("worktree_path"),
        "source_path_used": lane_meta.get("source_path_used"),
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
    lane_meta = get_lane_git_metadata()
    commit = _git_commit()
    lane = lane_meta.get("lane") or "unknown"
    active_backend_port = int(lane_meta.get("expected_backend_port") or 8000)
    active_frontend_port = int(lane_meta.get("expected_frontend_port") or 3005)
    public_base_url = lane_meta.get("public_base_url")

    service_map = {
        "main": ("empire-backend.service", "empire-portal.service"),
        "stable": ("empire-backend.service", "empire-portal.service"),
        "feature-v10": ("empire-backend-feature.service", "empire-portal-feature.service"),
        "v10-test": ("empire-backend-v10.service", "empire-portal-v10.service"),
    }
    backend_unit, frontend_unit = service_map.get(lane, ("empire-backend.service", "empire-portal.service"))
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
    backend_service = _service_status(backend_unit)
    frontend_service = _service_status(frontend_unit)
    stable_backend_service = _service_status("empire-backend.service")
    stable_frontend_service = _service_status("empire-portal.service")

    # Active lane checks (git freshness + route checks must use the active lane backend)
    local_api_git = _http_json(f"http://127.0.0.1:{active_backend_port}/api/v1/git")
    local_backend_root = _http_status(f"http://127.0.0.1:{active_backend_port}/")
    local_frontend_root = _http_status(f"http://127.0.0.1:{active_frontend_port}/")
    local_memory_bank = _http_status(
        f"http://127.0.0.1:{active_backend_port}/api/v1/chats/memory-bank?channel=all&limit=1"
    )

    # Explicit lane checks for stable and v10 side-by-side visibility
    local_stable_backend_root = _http_status("http://127.0.0.1:8000/")
    local_stable_frontend_root = _http_status("http://127.0.0.1:3005/")
    local_v10_backend_root = _http_status("http://127.0.0.1:8010/")
    local_v10_frontend_root = _http_status("http://127.0.0.1:3010/")

    public_api_git = None
    public_backend_root = None
    public_frontend_root = None
    public_memory_bank = None
    if public and public_base_url:
        public_api_git = _http_json(f"{public_base_url}/api/v1/git")
        public_backend_root = _http_status(f"{public_base_url}/")
        public_frontend_root = _http_status(f"{public_base_url}/")
        public_memory_bank = _http_status(f"{public_base_url}/api/v1/chats/memory-bank?channel=all&limit=1")
    elif public:
        public_api_git = {"ok": False, "error": f"public_base_url_unavailable_for_lane:{lane}"}
        public_backend_root = {"ok": False, "error": "public_base_url_unavailable"}
        public_frontend_root = {"ok": False, "error": "public_base_url_unavailable"}
        public_memory_bank = {"ok": False, "error": "public_base_url_unavailable"}

    def _extract_commit_hash(payload: dict[str, Any] | None) -> str | None:
        if not isinstance(payload, dict):
            return None
        data = payload.get("data")
        if not isinstance(data, dict):
            return None
        current = data.get("current_commit")
        if isinstance(current, dict) and current.get("hash"):
            return str(current.get("hash"))
        for key in ("local_commit", "last_commit_hash", "commit"):
            value = data.get(key)
            if value:
                return str(value)
        return None

    local_hash = _extract_commit_hash(local_api_git)
    public_hash = None
    if public_api_git:
        public_hash = _extract_commit_hash(public_api_git)

    local_commit_mismatch = bool(local_hash and commit["hash"] and local_hash != commit["hash"])
    public_commit_mismatch = bool(public and public_hash and commit["hash"] and public_hash != commit["hash"])

    mismatch_reason = lane_meta.get("mismatch_reason")
    if local_commit_mismatch:
        mismatch_reason = (
            f"local_commit_mismatch current_commit={commit['hash']} local_commit={local_hash} "
            f"source_path={lane_meta.get('source_path_used')} lane={lane}"
        )
    elif public_commit_mismatch:
        mismatch_reason = (
            f"public_commit_mismatch current_commit={commit['hash']} public_commit={public_hash} "
            f"public_base_url={public_base_url}"
        )

    public_check_unavailable = bool(public and public_api_git and not public_api_git.get("ok"))
    if public_check_unavailable and not mismatch_reason:
        mismatch_reason = f"public_check_unavailable lane={lane} reason={public_api_git.get('error', 'unavailable')}"

    if local_commit_mismatch or public_commit_mismatch or lane_meta.get("mismatch_reason"):
        freshness_status = "mismatch"
    elif public_check_unavailable:
        freshness_status = "public_unavailable"
    elif local_hash and commit["hash"] and (not public or not public_hash or public_hash == commit["hash"]):
        freshness_status = "ok"
    else:
        freshness_status = "partial"

    stale_or_broken: list[str] = []
    if not backend_service["active"] or not _port_open("127.0.0.1", active_backend_port) or not local_backend_root["ok"]:
        stale_or_broken.append(f"active_backend_port_{active_backend_port}_unhealthy")
    if not frontend_service["active"] or not _port_open("127.0.0.1", active_frontend_port) or not local_frontend_root["ok"]:
        stale_or_broken.append(f"active_frontend_port_{active_frontend_port}_unhealthy")
    if local_commit_mismatch:
        stale_or_broken.append("local_api_commit_mismatch")
    if public_commit_mismatch:
        stale_or_broken.append("public_api_commit_mismatch")
    if public and public_backend_root and public_backend_root.get("ok") is False and not public_check_unavailable:
        stale_or_broken.append("public_api_unhealthy")
    if public and public_frontend_root and public_frontend_root.get("ok") is False and not public_check_unavailable:
        stale_or_broken.append("public_studio_unhealthy")

    return {
        "skill": "empire-runtime-truth-check",
        "callable": "empire_runtime_truth_check",
        "mode": "inspect_only",
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "current_commit": commit,
        "lane": lane,
        "worktree_path": lane_meta.get("worktree_path"),
        "source_path_used": lane_meta.get("source_path_used"),
        "expected_worktree_path": lane_meta.get("expected_worktree_path"),
        "expected_backend_port": active_backend_port,
        "expected_frontend_port": active_frontend_port,
        "registry": registry_info,
        "startup_health": startup_health,
        "openclaw_gate": openclaw_gate,
        # Stable backend on port 8000 (empire-backend.service)
        "backend_port_8000": {
            "port": 8000,
            "service": "empire-backend.service",
            "service_active": stable_backend_service.get("active", False),
            "port_open": _port_open("127.0.0.1", 8000),
            "local_root_status": local_stable_backend_root.get("status_code"),
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
            "service_active": stable_frontend_service.get("active", False),
            "port_open": _port_open("127.0.0.1", 3005),
            "local_root_status": local_stable_frontend_root.get("status_code"),
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
            "local_commit": local_hash,
            "api_matches_current_commit": bool(local_hash and local_hash == commit["hash"]),
            "memory_bank_route": local_memory_bank,
        },
        "public_freshness": {
            "api_git": public_api_git,
            "public_commit": public_hash,
            "api_matches_current_commit": bool(public_hash and public_hash == commit["hash"]) if public else None,
            "api_root": public_backend_root,
            "studio_root": public_frontend_root,
            "memory_bank_route": public_memory_bank,
        },
        "git_freshness": {
            "lane": lane,
            "worktree_path": lane_meta.get("worktree_path"),
            "source_path_used": lane_meta.get("source_path_used"),
            "branch": commit.get("branch"),
            "current_commit": commit.get("hash"),
            "startup_commit": (startup_health or {}).get("running_commit_hash") if isinstance(startup_health, dict) else None,
            "local_commit": local_hash,
            "public_commit": public_hash,
            "public_base_url": public_base_url,
            "expected_backend_port": active_backend_port,
            "expected_frontend_port": active_frontend_port,
            "freshness_status": freshness_status,
            "mismatch_reason": mismatch_reason,
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

    def _extract_hash(api_git_payload: dict[str, Any] | None) -> str | None:
        if not isinstance(api_git_payload, dict):
            return None
        data = api_git_payload.get("data")
        if not isinstance(data, dict):
            return None
        current = data.get("current_commit")
        if isinstance(current, dict) and current.get("hash"):
            return str(current.get("hash"))
        for key in ("local_commit", "last_commit_hash", "commit"):
            value = data.get(key)
            if value:
                return str(value)
        return None

    public_git = public.get("api_git") or {}
    local_git = local.get("api_git") or {}
    public_hash = public.get("public_commit") or _extract_hash(public_git)
    local_hash = local.get("local_commit") or _extract_hash(local_git)
    git_freshness = result.get("git_freshness") or {}

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
        f"- Active lane: {result.get('lane')} | worktree={result.get('worktree_path')} | source_path={result.get('source_path_used')}",
        f"- Expected active ports: backend={result.get('expected_backend_port')} frontend={result.get('expected_frontend_port')}",
        f"- Registry: version={(result.get('registry') or {}).get('registry_version')} loaded_at={(result.get('registry') or {}).get('loaded_at')} last_error={(result.get('registry') or {}).get('last_error')}",
        f"- OpenClaw gate: state={openclaw_gate.get('state')} allowed={openclaw_gate.get('allowed')} reason={openclaw_gate.get('reason')}",
        f"- Stable Backend (port 8000): {'UP' if b8000.get('port_open') else 'DOWN'} | systemd={b8000.get('service_active')} | http={b8000.get('local_root_status')}",
        f"- v10 Test Backend (port 8010): {'UP' if b8010.get('port_open') else 'DOWN/not started'} | {b8010.get('service', 'dev server')}",
        f"- Stable Frontend (port 3005): {'UP' if f3005.get('port_open') else 'DOWN'} | systemd={f3005.get('service_active')} | http={f3005.get('local_root_status')}",
        f"- v10 Test Frontend (port 3010): {'UP' if f3010.get('port_open') else 'DOWN/not started'} | {f3010.get('service', 'dev server')}",
        f"- Local API commit: {local_hash} matches_current={local.get('api_matches_current_commit')}",
        f"- Public API commit: {public_hash if public_hash else 'unavailable'} matches_current={public.get('api_matches_current_commit')}",
        f"- Public API root: {(public.get('api_root') or {}).get('status_code')} | Public Studio root: {(public.get('studio_root') or {}).get('status_code')}",
        f"- Lane git freshness: status={git_freshness.get('freshness_status')} mismatch_reason={git_freshness.get('mismatch_reason')}",
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
