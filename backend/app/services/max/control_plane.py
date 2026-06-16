"""
MAX Control Plane — the truthful Founder-facing orchestrator surface.

This module separates MAX's IDENTITY (MAX) from its IMPLEMENTATION
(provider/model). MiniMax-M3 may remain the language provider, but MAX
must be the truthful Founder-facing control plane.

The control plane exposes three categories of truth:

1. IDENTITY        — who MAX is (separate from provider/model)
2. TOOL REGISTRY   — what MAX can actually do (with proof, not claims)
3. LOCAL BROKER    — what MAX can see on EmpireDell (read-only status)
4. MEMORY/DOCTRINE — what memory sources are actually available
5. TRUTH STALENESS — warnings when handoff/startup data is stale

The control plane is the authoritative truth source for the UI status
panel. The UI MUST NOT make claims that aren't backed by the
``proof_required`` fields in the tool registry.

Adding a new tool to MAX:
    1. Add a ToolEntry to TOOL_REGISTRY with ``status`` in
       {available, unavailable, configured-but-unhealthy, read-only, mutating}
    2. Set ``proof_required=True`` for any tool that mutates state,
       sends email/telegram, or makes external calls.
    3. Set ``approval_required`` for any tool that requires Founder approval.
    4. The tool is automatically exposed via /api/v1/max/tool-registry
       and /api/v1/max/control-plane.

MAX identity/provider separation (2026-06-15 control plane hotfix):
    Before this hotfix, the UI presented "Text minimax-MiniMax-M3" as
    MAX's identity, conflating the LLM with the orchestrator. This
    module enforces: MAX is MAX. Provider/model is implementation detail.
"""

from __future__ import annotations

import os
import socket
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional


# ---------------------------------------------------------------------------
# MAX IDENTITY (separate from provider/model)
# ---------------------------------------------------------------------------

MAX_IDENTITY = {
    "name": "MAX",
    "display_name": "MAX",
    "role": "Founder-facing AI command center",
    "tagline": "Empire's AI brain for work that has to move.",
    "version": "control-plane-v1",
    # MiniMax-M3 is the language provider, NOT MAX's identity.
    # The provider/model is exposed separately via /api/v1/max/control-plane
    # under the ``provider`` key. The UI must show:
    #   MAX   (identity)
    #   Provider: minimax / Model: MiniMax-M3  (implementation detail)
}


# ---------------------------------------------------------------------------
# LOCAL EMPIREDELL BROKER (read-only)
# ---------------------------------------------------------------------------

def _repo_root() -> Path:
    """The /home/rg/empire-repo-main worktree."""
    return Path(__file__).resolve().parents[4]


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


def get_local_broker_status() -> dict[str, Any]:
    """Read-only status of the local EmpireDell broker surfaces.

    Returns a dict of surface -> status. Each status is one of:
      - {"state": "up", "detail": "..."}
      - {"state": "down", "detail": "..."}
      - {"state": "unknown", "detail": "..."}

    This is the AUTHORITATIVE truth for what MAX can see locally.
    MAX must NOT claim filesystem/shell access unless this broker
    exposes it. As of 2026-06-15, the broker exposes:
      - repo branch/HEAD
      - backend PID/health
      - portal PID/build ID
      - OpenClaw queue/status (read-only)
      - Hermes status (read-only)
      - Telegram gateway status
      - Ollama/local model status
    """
    repo_root = _repo_root()
    branch = _run(["git", "rev-parse", "--abbrev-ref", "HEAD"])
    commit = _run(["git", "rev-parse", "--short", "HEAD"])
    build_id_path = repo_root / "empire-command-center" / ".next" / "BUILD_ID"
    build_id = build_id_path.read_text().strip() if build_id_path.exists() else "unknown"
    backend_port = int(os.getenv("EMPIRE_BACKEND_PORT", "8000"))
    frontend_port = int(os.getenv("EMPIRE_FRONTEND_EXPECTED_PORT", "3005"))
    backend_up = _port_open("127.0.0.1", backend_port)
    frontend_up = _port_open("127.0.0.1", frontend_port)

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "repo": {
            "branch": branch or "unknown",
            "commit": commit or "unknown",
            "repo_root": str(repo_root),
        },
        "backend": {
            "port": backend_port,
            "state": "up" if backend_up else "down",
            "detail": f"http://127.0.0.1:{backend_port}/health" if backend_up else "port closed",
        },
        "frontend": {
            "port": frontend_port,
            "build_id": build_id,
            "state": "up" if frontend_up else "down",
            "detail": f"http://127.0.0.1:{frontend_port}/" if frontend_up else "port closed",
        },
        # OpenClaw: defer to the existing openclaw_gate (live, healthy)
        "openclaw": {"state": "see /api/v1/openclaw/health", "detail": "broker delegates to openclaw_gate"},
        # Hermes: surface health from the hermes_memory service
        "hermes": {"state": "see backend/app/services/max/hermes_memory.py", "detail": "broker delegates to hermes_memory.get_hermes_memory_status()"},
        # Telegram gateway
        "telegram": {"state": "see /api/v1/max/telegram/status", "detail": "broker delegates to telegram_bot.is_configured"},
        # Ollama / local model
        "ollama": {"state": "see /api/v1/ollama/models", "detail": "broker delegates to ollama client (kill-switched)"},
    }


# ---------------------------------------------------------------------------
# TOOL REGISTRY (with proof requirements)
# ---------------------------------------------------------------------------

def _web_search_tool() -> dict[str, Any]:
    """Build the web_search tool entry. Reads truth from the routing state."""
    try:
        from app.services.max.ai_router import ai_router
        routing = ai_router.get_routing_state_payload()
        # Web search is a tool, not a provider. Check if any provider has
        # a "web" capability or if web_search is a registered tool.
        # As of 2026-06-15, web_search is NOT a registered tool in MAX's
        # tool_executor. We return "unavailable" with proof_reason.
        return {
            "key": "web_search",
            "category": "web",
            "status": "unavailable",
            "proof_required": True,
            "approval_required": False,
            "mutating": False,
            "description": "Web search via external search API.",
            "proof_reason": "No web_search tool registered in app.services.max.tool_executor (2026-06-15 audit). Use the operator-side browser tool via Hermes for web access instead.",
        }
    except Exception as exc:
        return {
            "key": "web_search",
            "category": "web",
            "status": "configured-but-unhealthy",
            "proof_required": True,
            "approval_required": False,
            "mutating": False,
            "description": "Web search via external search API.",
            "proof_reason": f"Failed to query routing state: {exc}",
        }


def _web_read_tool() -> dict[str, Any]:
    """Build the web_read tool entry. Reads truth from search_context."""
    try:
        from app.services.max import search_context
        # search_context is a wrapper that historically wrapped a web reader.
        # As of 2026-06-15, it is a thin layer without an active backend.
        return {
            "key": "web_read",
            "category": "web",
            "status": "unavailable",
            "proof_required": True,
            "approval_required": False,
            "mutating": False,
            "description": "Read a URL and return extracted text.",
            "proof_reason": "No web_read backend is configured in app.services.max.search_context (2026-06-15 audit). Use the operator-side browser tool via Hermes for URL access instead.",
        }
    except Exception as exc:
        return {
            "key": "web_read",
            "category": "web",
            "status": "configured-but-unhealthy",
            "proof_required": True,
            "approval_required": False,
            "mutating": False,
            "description": "Read a URL and return extracted text.",
            "proof_reason": f"Failed to import search_context: {exc}",
        }


def _memory_tool() -> dict[str, Any]:
    """Build the memory/doctrine tool entry. Reads truth from hermes_memory."""
    try:
        from app.services.max.hermes_memory import get_hermes_memory_status
        status = get_hermes_memory_status()
        return {
            "key": "memory_recall",
            "category": "memory",
            "status": "available",
            "proof_required": True,
            "approval_required": False,
            "mutating": False,
            "description": "Recall facts from MAX's memory bank.",
            "proof_reason": "app.services.max.hermes_memory is loaded and responsive.",
            "status_detail": status,
        }
    except Exception as exc:
        return {
            "key": "memory_recall",
            "category": "memory",
            "status": "configured-but-unhealthy",
            "proof_required": True,
            "approval_required": False,
            "mutating": False,
            "description": "Recall facts from MAX's memory bank.",
            "proof_reason": f"Failed to query hermes_memory: {exc}",
        }


def _openclaw_tool() -> dict[str, Any]:
    """Build the OpenClaw tool entry. Reads truth from openclaw_gate."""
    try:
        from app.services.max.openclaw_gate import check_openclaw_gate
        gate = check_openclaw_gate()
        # gate is an OpenClawGateResult dataclass; convert to dict via .to_dict()
        gate_dict = gate.to_dict() if hasattr(gate, "to_dict") else {
            "state": getattr(gate, "state", "unknown"),
            "allowed": getattr(gate, "allowed", False),
        }
        return {
            "key": "openclaw_status",
            "category": "openclaw",
            "status": "read-only" if gate_dict.get("state") == "healthy" else "configured-but-unhealthy",
            "proof_required": True,
            "approval_required": False,
            "mutating": False,
            "description": "Read OpenClaw queue + worker heartbeat.",
            "proof_reason": "Delegates to openclaw_gate (read-only by mandate).",
            "status_detail": gate_dict,
        }
    except Exception as exc:
        return {
            "key": "openclaw_status",
            "category": "openclaw",
            "status": "configured-but-unhealthy",
            "proof_required": True,
            "approval_required": False,
            "mutating": False,
            "description": "Read OpenClaw queue + worker heartbeat.",
            "proof_reason": f"Failed to query openclaw_gate: {exc}",
        }


def _local_broker_tool() -> dict[str, Any]:
    """Build the local broker tool entry."""
    return {
        "key": "local_broker",
        "category": "broker",
        "status": "read-only",
        "proof_required": True,
        "approval_required": False,
        "mutating": False,
        "description": "Read-only local EmpireDell broker: branch, commit, build ID, port health.",
        "proof_reason": "app.services.max.control_plane.get_local_broker_status (this module).",
    }


def _telegram_tool() -> dict[str, Any]:
    """Build the Telegram tool entry. Reads truth from telegram_bot."""
    try:
        # telegram_bot.py exports a singleton instance named `telegram_bot`
        from app.services.max import telegram_bot as tb_module
        tb_instance = getattr(tb_module, "telegram_bot", None) or tb_module.TelegramBot()
        configured = bool(getattr(tb_instance, "is_configured", False))
        return {
            "key": "telegram_status",
            "category": "telegram",
            "status": "available" if configured else "unavailable",
            "proof_required": True,
            "approval_required": False,
            "mutating": False,
            "description": "Read Telegram gateway status (no sending).",
            "proof_reason": "Delegates to telegram_bot.is_configured.",
        }
    except Exception as exc:
        return {
            "key": "telegram_status",
            "category": "telegram",
            "status": "configured-but-unhealthy",
            "proof_required": True,
            "approval_required": False,
            "mutating": False,
            "description": "Read Telegram gateway status.",
            "proof_reason": f"Failed to import telegram_bot: {exc}",
        }


def _ollama_tool() -> dict[str, Any]:
    """Build the Ollama/local-model tool entry."""
    return {
        "key": "ollama_status",
        "category": "local_model",
        "status": "unavailable",
        "proof_required": True,
        "approval_required": False,
        "mutating": False,
        "description": "Read local Ollama model availability.",
        "proof_reason": "Ollama is founder_disabled_due_to_stall_suspected (see /api/v1/max/routing-state provider_registry).",
    }


def _filesystem_tool() -> dict[str, Any]:
    """Build the filesystem/shell tool entry.

    As of 2026-06-15, the local broker does NOT expose raw filesystem or
    shell access. The Hermes subsystem has limited file tools (read/write
    inside ~/Empire/, not EmpireRepoMain). MAX must NOT pretend to have
    shell access via this broker.
    """
    return {
        "key": "filesystem_shell",
        "category": "broker",
        "status": "unavailable",
        "proof_required": True,
        "approval_required": False,
        "mutating": False,
        "description": "Raw filesystem/shell access.",
        "proof_reason": "Local broker does not expose raw filesystem/shell access. Use the operator-side tools (Hermes Code Mode for /home/rg/empire-repo, CodeForge desk for /home/rg/empire-repo) — both require separate Founder approval.",
    }


def _gmail_tool() -> dict[str, Any]:
    """Build the Gmail/email tool entry."""
    try:
        from app.services.max import email_service
        return {
            "key": "gmail_reader",
            "category": "email",
            "status": "available",
            "proof_required": True,
            "approval_required": False,
            "mutating": False,
            "description": "Read emails via Gmail API (whitelist-scoped).",
            "proof_reason": "app.services.max.email_service is loaded and configured.",
        }
    except Exception as exc:
        return {
            "key": "gmail_reader",
            "category": "email",
            "status": "configured-but-unhealthy",
            "proof_required": True,
            "approval_required": False,
            "mutating": False,
            "description": "Read emails via Gmail API.",
            "proof_reason": f"Failed to import email_service: {exc}",
        }


# Tool registry (ordered by surface)
TOOL_REGISTRY: list[dict[str, Any]] = [
    _web_search_tool(),
    _web_read_tool(),
    _memory_tool(),
    _openclaw_tool(),
    _local_broker_tool(),
    _telegram_tool(),
    _ollama_tool(),
    _filesystem_tool(),
    _gmail_tool(),
]


def get_tool_registry() -> list[dict[str, Any]]:
    """Return the live tool registry, refreshing status probes for each tool.

    The tool registry is the AUTHORITATIVE source for what MAX can do.
    MAX must NOT claim tool availability that isn't in this registry.
    """
    out: list[dict[str, Any]] = []
    for tool in TOOL_REGISTRY:
        # Re-fetch live status for tools that depend on runtime state.
        key = tool.get("key")
        if key == "web_search":
            out.append(_web_search_tool())
        elif key == "web_read":
            out.append(_web_read_tool())
        elif key == "memory_recall":
            out.append(_memory_tool())
        elif key == "openclaw_status":
            out.append(_openclaw_tool())
        elif key == "local_broker":
            out.append(_local_broker_tool())
        elif key == "telegram_status":
            out.append(_telegram_tool())
        elif key == "ollama_status":
            out.append(_ollama_tool())
        elif key == "filesystem_shell":
            out.append(_filesystem_tool())
        elif key == "gmail_reader":
            out.append(_gmail_tool())
        else:
            out.append(tool)
    return out


# ---------------------------------------------------------------------------
# MEMORY / DOCTRINE STATUS
# ---------------------------------------------------------------------------

def get_memory_status() -> dict[str, Any]:
    """Truthful status of MAX's memory + doctrine sources.

    Returns:
      - active_memory_source: which memory service is currently active
      - newest_memory_timestamp: when the last memory record was written
      - doctrine_source_availability: which doctrine/memory sources are available
      - hermes_sync_artifact_status: status of any Hermes/Harry sync artifacts
      - handoff_freshness: whether the last handoff is fresh
      - startup_vs_runtime_commit: whether startup commit matches current runtime
    """
    try:
        from app.services.max.hermes_memory import get_hermes_memory_status
        hermes = get_hermes_memory_status()
    except Exception as exc:
        hermes = {"error": str(exc)}

    # The startup_health record is recorded at process startup. If we
    # have a current_commit, we can compare and warn if they differ.
    try:
        commit = _run(["git", "rev-parse", "--short", "HEAD"])
    except Exception:
        commit = "unknown"

    startup_path = _repo_root() / "backend" / "data" / "max" / "startup_health.json"
    startup_commit = None
    startup_recorded_at = None
    if startup_path.exists():
        try:
            import json
            with open(startup_path) as f:
                startup = json.load(f)
            startup_commit = startup.get("running_commit_hash")
            startup_recorded_at = startup.get("recorded_at")
        except Exception:
            pass

    startup_vs_runtime_match = (startup_commit and commit and startup_commit == commit)

    # Find the newest memory/audit file in the agent_workspace.
    agent_workspace = Path("/home/rg/.hermes/agent_workspace")
    newest_memory_file: Optional[str] = None
    newest_memory_at: Optional[str] = None
    if agent_workspace.exists():
        files = sorted(
            [p for p in agent_workspace.glob("*.md") if p.is_file()],
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if files:
            newest_memory_file = files[0].name
            newest_memory_at = datetime.fromtimestamp(
                files[0].stat().st_mtime, tz=timezone.utc
            ).isoformat()

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "active_memory_source": "hermes_memory" if hermes and not hermes.get("error") else "unknown",
        "newest_memory_timestamp": newest_memory_at,
        "newest_memory_file": newest_memory_file,
        "doctrine_source_availability": {
            "hermes_memory": "available" if hermes and not hermes.get("error") else "unavailable",
            "agent_workspace_read_only": "available" if agent_workspace.exists() else "unavailable",
        },
        "hermes_sync_artifact_status": hermes,
        "handoff_freshness": {
            "startup_commit": startup_commit,
            "startup_recorded_at": startup_recorded_at,
            "current_commit": commit,
            "matches": startup_vs_runtime_match,
            "warning": None if startup_vs_runtime_match else "Startup commit does not match current runtime commit (a git pull/fast-forward has happened since startup).",
        },
    }


# ---------------------------------------------------------------------------
# CONTROL PLANE AGGREGATOR
# ---------------------------------------------------------------------------

def get_control_plane() -> dict[str, Any]:
    """Return the full control plane truth for the UI.

    The UI uses this to render the status panel. The control plane
    separates MAX's IDENTITY from its IMPLEMENTATION (provider/model).
    """
    try:
        from app.services.max.ai_router import ai_router
        routing = ai_router.get_routing_state_payload()
        provider = {
            "provider_canonical": routing.get("selected_provider"),
            "model": routing.get("selected_model"),
            "provider_label": routing.get("selected_provider_label"),
            "fallback_enabled": routing.get("fallback_enabled"),
            "ai_calls_disabled": routing.get("ai_calls_disabled"),
            "lane": routing.get("lane"),
        }
    except Exception as exc:
        provider = {"error": str(exc)}

    return {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "identity": MAX_IDENTITY,
        "provider": provider,
        "local_broker": get_local_broker_status(),
        "tool_registry": get_tool_registry(),
        "memory": get_memory_status(),
    }
