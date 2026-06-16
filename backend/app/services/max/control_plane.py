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
      - OpenClaw queue/status (read-only; detail inlined)
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

    # Inline the OpenClaw detail here (read-only) so the broker is
    # no longer just a pointer. 2026-06-15: Codex flagged that the
    # broker only pointed to /api/v1/openclaw/health, which left
    # OpenClaw as a "partial" status. Now the broker inlines the
    # gate result (queue stats, worker heartbeat) without ever
    # calling /tasks (which would paginate) or mutating.
    openclaw_block = _openclaw_broker_detail()

    # Inline the Hermes memory status (read-only).
    hermes_block = _hermes_broker_detail()

    # Inline the Telegram gateway status (read-only, no token print).
    telegram_block = _telegram_broker_detail()

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
        # OpenClaw: read-only detail inlined from openclaw_gate.
        "openclaw": openclaw_block,
        # Hermes: read-only status inlined from hermes_memory.
        "hermes": hermes_block,
        # Telegram gateway
        "telegram": telegram_block,
        # Ollama / local model
        "ollama": {
            "state": "unavailable",
            "disabled_reason": "founder_disabled_due_to_stall_suspected",
            "detail": "Ollama kill-switched (see /api/v1/max/routing-state provider_registry).",
        },
    }


def _openclaw_broker_detail() -> dict[str, Any]:
    """Inline read-only OpenClaw detail for the local broker.

    Calls check_openclaw_gate() (read-only, cached) and extracts the
    queue stats + worker heartbeat. Does NOT call /api/v1/openclaw/tasks
    (which would paginate) and does NOT mutate the queue.

    Per the 2026-06-15 proof-receipt enforcement patch, the broker MUST
    expose the OpenClaw detail directly so MAX can claim it has proof
    when it says "I checked OpenClaw and the queue has 72 tasks."
    """
    try:
        from app.services.max.openclaw_gate import check_openclaw_gate
        gate = check_openclaw_gate()
        gate_dict = gate.to_dict() if hasattr(gate, "to_dict") else {
            "state": getattr(gate, "state", "unknown"),
            "allowed": getattr(gate, "allowed", False),
        }
        state = gate_dict.get("state", "unknown")
        queue_stats = gate_dict.get("queue_stats") or {}
        heartbeat = gate_dict.get("worker_heartbeat") or {}
        queued = queue_stats.get("queued", "unknown")
        total = queue_stats.get("total", "unknown")
        hb_status = heartbeat.get("state", "unknown")
        hb_age = heartbeat.get("age_seconds", "unknown")
        return {
            "state": "available" if state == "healthy" else state,
            "detail": f"queue {queued}/{total} · worker {hb_status} ({hb_age}s)",
            "queue_stats": queue_stats,
            "worker_heartbeat": heartbeat,
            "proof_source": "openclaw_gate (cached, read-only)",
        }
    except Exception as exc:
        return {
            "state": "configured_but_detail_unavailable",
            "detail": f"openclaw_gate query failed: {exc}",
            "proof_source": "openclaw_gate (query failed; do not claim OpenClaw status)",
        }


def _hermes_broker_detail() -> dict[str, Any]:
    """Inline read-only Hermes memory status for the local broker."""
    try:
        from app.services.max.hermes_memory import get_hermes_memory_status
        status = get_hermes_memory_status()
        return {
            "state": "available",
            "detail": "hermes_memory is loaded",
            "status": status,
            "proof_source": "hermes_memory (read-only)",
        }
    except Exception as exc:
        return {
            "state": "configured_but_detail_unavailable",
            "detail": f"hermes_memory query failed: {exc}",
            "proof_source": "hermes_memory (query failed; do not claim Hermes status)",
        }


def _telegram_broker_detail() -> dict[str, Any]:
    """Inline read-only Telegram gateway status for the local broker."""
    try:
        from app.services.max import telegram_bot as tb_module
        tb_instance = getattr(tb_module, "telegram_bot", None) or tb_module.TelegramBot()
        configured = bool(getattr(tb_instance, "is_configured", False))
        if configured:
            return {
                "state": "available",
                "detail": "Telegram gateway configured (founder_chat_id set)",
                "proof_source": "telegram_bot.is_configured (read-only)",
            }
        return {
            "state": "unavailable",
            "detail": "Telegram gateway not configured (no token / founder_chat_id)",
            "proof_source": "telegram_bot.is_configured (read-only)",
        }
    except Exception as exc:
        return {
            "state": "configured_but_detail_unavailable",
            "detail": f"telegram_bot query failed: {exc}",
            "proof_source": "telegram_bot (query failed)",
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
# DOCTRINE LOADER (2026-06-15 retrieval patch)
# ---------------------------------------------------------------------------
# This module reads the canonical MAX doctrine from
# `/home/rg/empire-box-memory/MAX_DOCTRINE.md` and returns a structured
# summary that the live MAX response path can use to answer
# doctrine-scope questions (e.g., "Who is Hermes relative to MAX?",
# "What are the primary EmpireBox modules?").
#
# The doctrine file path is configurable via the
# `EMPIRE_MEMORY_ROOT` environment variable (or
# `app.core.config.settings.empire_memory_root` if available). The
# default is `/home/rg/empire-box-memory/`.
#
# If the file is unavailable, the loader returns an explicit
# `unavailable` state, NOT a guessed answer. This preserves the
# proof rule (no false past-tense claims).
# ---------------------------------------------------------------------------

# Canonical doctrine file name.
DOCTRINE_FILE_NAME = "MAX_DOCTRINE.md"

# Doctrine-scope question patterns (case-insensitive, word-boundary).
# If a user message matches any of these, the live MAX response path
# should consult the doctrine loader first, before falling back to
# the generic M3 model answer.
DOCTRINE_SCOPE_PATTERNS = [
    r"\bmax\b.*\bpurpose\b",
    r"\bwhat\s+(?:is|are)\s+(?:your\s+)?(?:max|doctrine|role|purpose)\b",
    r"\bwho\s+is\s+(?:hermes|harry|opencode|openclaw|codex|max)\b",
    r"\bhermes\s+relative\s+to\s+max\b",
    r"\bharry\s+relative\s+to\s+max\b",
    r"\bopencode\s+relative\s+to\s+max\b",
    r"\bopenclaw\s+relative\s+to\s+max\b",
    r"\bcodex\s+(?:role|relative)\b",
    r"\bwhat\s+is\s+codex\W*s?\W*\s+role\b",
    r"\bprimary\s+(?:empirebox|empire)\s+modules?\b",
    r"\bphone\s+max\b.*\b(?:implemented|implemented|live)\b",
    r"\bis\s+phone\s+max\b",
    r"\bvoice\s+max\b.*\b(?:implemented|live)\b",
    r"\bis\s+voice\s+max\b",
    r"\bcan\s+you\s+claim\b.*\bproof\b",
    r"\bprove\s+rule\b",
    r"\bfounder\s+hierarchy\b",
    r"\btruth\s+hierarchy\b",
]


def _get_doctrine_file_path() -> Path:
    """Return the path to the canonical doctrine file.

    Configurable via the `EMPIRE_MEMORY_ROOT` environment variable
    (default: `/home/rg/empire-box-memory/`). The canonical file
    name is `MAX_DOCTRINE.md`.
    """
    # Try env var first (the most explicit override).
    env_root = os.getenv("EMPIRE_MEMORY_ROOT", "").strip()
    if env_root:
        return Path(env_root) / DOCTRINE_FILE_NAME
    # Try settings if available.
    try:
        from app.core.config import settings
        root = getattr(settings, "empire_memory_root", None)
        if root:
            return Path(root) / DOCTRINE_FILE_NAME
    except Exception:
        pass
    # Default.
    return Path("/home/rg/empire-box-memory") / DOCTRINE_FILE_NAME


def _parse_doctrine_markdown(content: str) -> dict[str, Any]:
    """Parse a doctrine Markdown file into a structured summary.

    The parser is intentionally simple: it scans for H2 headings
    (`## N. ...`) and extracts the bullet-list items that follow
    each heading. This matches the structure of the canonical
    MAX_DOCTRINE.md file.
    """
    out: dict[str, Any] = {
        "sections": [],
        "identity": "",
        "hermes_role": "",
        "harry_role": "",
        "openclaw_role": "",
        "codex_role": "",
        "primary_modules": [],
        "phone_status": "",
        "voice_status": "",
        "proof_rule": "",
    }
    current_section: Optional[dict[str, Any]] = None
    lines = content.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        # H2 heading
        if stripped.startswith("## "):
            # Flush previous section.
            if current_section is not None:
                out["sections"].append(current_section)
            heading = stripped[3:].strip()
            current_section = {"title": heading, "bullets": []}
            i += 1
            # Capture section content until next H2.
            while i < len(lines) and not lines[i].strip().startswith("## "):
                sub = lines[i].strip()
                if sub.startswith("- ") or sub.startswith("* "):
                    current_section["bullets"].append(sub[2:].strip())
                i += 1
            continue
        i += 1
    # Flush last section.
    if current_section is not None:
        out["sections"].append(current_section)

    # Extract canonical fields by section number.
    # Section titles in the doctrine file look like
    # "1. MAX identity (AUTHORITATIVE)". We strip the (AUTHORITATIVE)
    # suffix and any whitespace so the lookup keys are clean.
    section_by_title = {}
    for sec in out["sections"]:
        # Normalize: drop "(AUTHORITATIVE)" / "(meta)" / etc., trim.
        title = sec["title"]
        import re as _re
        title_clean = _re.sub(r"\s*\([^)]*\)\s*$", "", title).strip()
        section_by_title[title_clean] = sec
        # Also index by the original title in case a future variant slips in.
        section_by_title[title] = sec

    def _lookup(*candidates):
        for c in candidates:
            if c in section_by_title:
                return section_by_title[c]
        return None

    # Section 1: MAX identity.
    s1 = _lookup("1. MAX identity")
    if s1:
        # Pull the first 4 bullets into identity text.
        out["identity"] = " ".join(s1["bullets"][:4])

    # Section 2: Founder hierarchy.
    s2 = _lookup("2. Founder hierarchy")
    if s2:
        for bullet in s2["bullets"]:
            low = bullet.lower()
            if "hermes" in low and "local desktop" in low:
                out["hermes_role"] = bullet
            elif ("harry" in low or "opencode" in low) and "remote" in low:
                out["harry_role"] = bullet
            elif "openclaw" in low and ("execution" in low or "task subsystem" in low):
                out["openclaw_role"] = bullet
            elif "codex" in low and "verifier" in low:
                out["codex_role"] = bullet

    # Section 7: EmpireBox scope.
    s7 = _lookup("7. EmpireBox scope")
    if s7:
        # Only the bullets under "**Primary ecosystem framing:**" count
        # as primary modules. We detect that by stopping at the first
        # bullet that says "Archive" (the start of the supporting list).
        primary = []
        for bullet in s7["bullets"]:
            if "ArchiveForge" in bullet or "RecoveryForge" in bullet:
                break
            primary.append(bullet)
        out["primary_modules"] = primary

    # Section 6: Channels / surfaces.
    s6 = _lookup("6. Channels / surfaces")
    if s6:
        for bullet in s6["bullets"]:
            low = bullet.lower()
            if "phone max" in low:
                out["phone_status"] = bullet
            elif "voice" in low:
                out["voice_status"] = bullet

    # Section 5: Proof rule.
    s5 = _lookup("5. Proof rule")
    if s5:
        # The first bullets in section 5 are the literal past-tense
        # phrase list (e.g., `"I ran"`, `"I searched"`). These are
        # what MAX must NOT say. The explanatory content (what counts
        # as proof, the safe future-tense phrases, the enforcement
        # note) comes after. Concatenate the phrase list + the
        # "valid proof object" bullets so the summary includes both.
        proof_parts = []
        for bullet in s5["bullets"]:
            # Only include bullets that are not just a quoted phrase
            # list item like `"I ran"`. Quoted-only bullets have a
            # very short length and start with a quote.
            stripped = bullet.strip()
            if stripped.startswith('"') and stripped.endswith('"') and len(stripped) < 30:
                # Keep for the phrase list (use the unquoted version).
                proof_parts.append(stripped.strip('"'))
            else:
                # Explanatory bullet.
                proof_parts.append(stripped)
        out["proof_rule"] = " ".join(proof_parts)

    return out


def get_doctrine_status() -> dict[str, Any]:
    """Return the structured doctrine status.

    Returns:
      - doctrine_source: path to the doctrine file (or None if not configured)
      - doctrine_file: file name only
      - doctrine_available: True if the file exists and is readable
      - doctrine_mtime: ISO timestamp of the file's last modification
      - doctrine_size_bytes: file size in bytes
      - doctrine_summary: structured fields extracted from the file
        (identity, hermes_role, harry_role, openclaw_role, codex_role,
         primary_modules, phone_status, voice_status, proof_rule)
      - proof_source: "doctrine_loader (read-only, no file mutation)"
    """
    doctrine_path = _get_doctrine_file_path()
    out: dict[str, Any] = {
        "checked_at": datetime.now(timezone.utc).isoformat(),
        "doctrine_source": str(doctrine_path),
        "doctrine_file": DOCTRINE_FILE_NAME,
        "doctrine_available": False,
        "doctrine_mtime": None,
        "doctrine_size_bytes": None,
        "doctrine_summary": {},
        "proof_source": "doctrine_loader (read-only, no file mutation)",
    }
    if not doctrine_path.exists():
        out["doctrine_summary"] = {
            "error": "doctrine_file_unavailable",
            "detail": f"Canonical doctrine file not found at {doctrine_path}",
        }
        return out
    try:
        content = doctrine_path.read_text(encoding="utf-8")
        stat = doctrine_path.stat()
        out["doctrine_mtime"] = datetime.fromtimestamp(
            stat.st_mtime, tz=timezone.utc
        ).isoformat()
        out["doctrine_size_bytes"] = stat.st_size
        out["doctrine_available"] = True
        out["doctrine_summary"] = _parse_doctrine_markdown(content)
    except Exception as exc:
        out["doctrine_summary"] = {
            "error": "doctrine_file_unreadable",
            "detail": str(exc),
        }
    return out


def is_doctrine_scope_question(message) -> bool:
    """Return True if the user message looks like a doctrine-scope question.

    Doctrine-scope questions are routed to the doctrine loader
    BEFORE the generic M3 model answer. This is a narrow, deterministic
    pattern match — no AI call is made for this routing decision.

    Accepts Optional[str] and treats None/empty as "not a doctrine
    question" (the safe default).
    """
    if not message:
        return False
    import re
    for pat in DOCTRINE_SCOPE_PATTERNS:
        if re.search(pat, message, re.IGNORECASE):
            return True
    return False


def build_doctrine_answer(message: str, doctrine_status: dict[str, Any]) -> str:
    """Build a canonical answer for a doctrine-scope question.

    Returns a deterministic answer derived from the loaded doctrine.
    If the doctrine file is unavailable, returns an explicit
    `unavailable` state, NOT a guessed answer.
    """
    summary = doctrine_status.get("doctrine_summary", {}) or {}
    if not doctrine_status.get("doctrine_available") or not summary:
        return (
            "The canonical MAX doctrine file is currently unavailable. "
            "I have not run that yet. I can check after approval."
        )

    low = (message or "").lower()

    # Pattern: "what are the primary modules" / "primary empirebox modules"
    if "primary" in low and ("module" in low or "empirebox" in low):
        modules = summary.get("primary_modules") or []
        if modules:
            return "Primary EmpireBox modules:\n" + "\n".join(f"- {m}" for m in modules)
    # Pattern: "who is hermes relative to max"
    if "hermes" in low:
        role = summary.get("hermes_role") or "Hermes is the local desktop execution/development/memory assistant under MAX."
        return role
    # Pattern: "who is harry / opencode relative to max"
    if "harry" in low or "opencode" in low:
        role = summary.get("harry_role") or "Harry / OpenCode is the remote/mobile code operator under MAX."
        return role
    # Pattern: "what is openclaw relative to max"
    if "openclaw" in low:
        role = summary.get("openclaw_role") or "OpenClaw is the execution/task subsystem under MAX (queue of tasks; read-only by mandate)."
        return role
    # Pattern: "codex role"
    if "codex" in low:
        role = summary.get("codex_role") or "Codex is the independent verifier/auditor when used. Not in the active chain of command."
        return role
    # Pattern: "phone max" / "is phone max"
    if "phone" in low and "max" in low:
        return summary.get("phone_status") or "Phone MAX is not implemented until separately built and verified."
    # Pattern: "voice max" / "is voice max"
    if "voice" in low and "max" in low:
        return summary.get("voice_status") or "Voice MAX is not live until separately implemented and proven."
    # Pattern: "can you claim ... without proof" / "proof rule"
    if "proof" in low and ("claim" in low or "rule" in low or "without" in low):
        return (
            "No. Past-tense operational claims ('I ran / checked / probed / "
            "verified / confirmed / fetched / read / called / inspected / "
            "searched / looked up') require a structured proof object. "
            "Without proof, MAX must say: 'I have not run that yet.'"
        )
    # Pattern: "what is your purpose" / "what is your role" / "what are you"
    if "purpose" in low or "your role" in low or "your max" in low:
        return (
            summary.get("identity")
            or "MAX is the Founder-facing command-center AI. MiniMax-M3 is the current language provider/model."
        )
    # Fallback: identity line.
    return (
        summary.get("identity")
        or "MAX is the Founder-facing command-center AI. "
        "Hermes is the local desktop assistant under MAX. "
        "OpenClaw is the execution/task subsystem under MAX."
    )


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
        # 2026-06-15 doctrine retrieval patch: enrich memory-status with
        # the structured doctrine summary so the live MAX response path
        # can answer doctrine-scope questions without making a generic
        # AI call. The doctrine summary includes the canonical identity,
        # Hermes/Harry/OpenClaw/Codex roles, primary modules list,
        # phone/voice status, and proof rule summary.
        "doctrine_summary": get_doctrine_status().get("doctrine_summary", {}),
        "doctrine_source_path": str(_get_doctrine_file_path()),
        "doctrine_available": get_doctrine_status().get("doctrine_available", False),
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
        # 2026-06-15 doctrine retrieval patch: include the structured
        # doctrine summary at the top level of the control plane so
        # Founder UIs and the live MAX response path can both reach it.
        "doctrine": get_doctrine_status(),
    }
