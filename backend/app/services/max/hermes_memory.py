"""Hermes Phase 1 memory bridge beneath MAX registry/runtime truth."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.max.operating_registry import get_registry_load_info, load_operating_registry
from app.services.max.surface_identity import normalize_surface


MEMORY_ROOT_ENV = "EMPIRE_BOX_MEMORY_DIR"
TRUTH_HIERARCHY = ("runtime", "registry", "repo_truth", "hermes_memory", "skills")


def memory_root() -> Path:
    raw = os.getenv(MEMORY_ROOT_ENV)
    if raw:
        return Path(raw).expanduser()
    return Path.home() / "empire-box-memory"


def context_path() -> Path:
    return memory_root() / "CONTEXT.md"


def memory_path() -> Path:
    return memory_root() / "MEMORY.md"


def user_path() -> Path:
    return memory_root() / "USER.md"


def skills_path() -> Path:
    return memory_root() / "SKILLS"


def _default_context() -> str:
    return """# CONTEXT

MAX writes this file after verified sessions.
Hermes reads it first and never writes it.

Truth hierarchy:
runtime > registry > repo truth > Hermes memory > skills

Status:
- Awaiting first verified MAX context refresh.
"""


def _default_memory() -> str:
    return """# MEMORY

Hermes maintains this file.
MAX reads it as supporting recall only.

Do not let this file override:
- live runtime truth
- the operating registry
- verified repo/config truth

Suggested sections:
- validated facts
- recurring failure modes
- lessons learned
"""


def _default_user() -> str:
    return """# USER

Hermes maintains this file.
MAX reads it as founder-preference context only.

Suggested sections:
- tone and response preferences
- escalation preferences
- approval boundaries
- recurring workflow preferences
"""


def ensure_hermes_memory_scaffold() -> dict[str, Any]:
    root = memory_root()
    root.mkdir(parents=True, exist_ok=True)
    skills_path().mkdir(parents=True, exist_ok=True)

    created: list[str] = []
    defaults = {
        context_path(): _default_context(),
        memory_path(): _default_memory(),
        user_path(): _default_user(),
    }
    for path, content in defaults.items():
        if not path.exists():
            path.write_text(content, encoding="utf-8")
            created.append(str(path))
    return {
        "root": str(root),
        "skills_dir": str(skills_path()),
        "created": created,
    }


def _read_text(path: Path, limit: int) -> str:
    try:
        return path.read_text(encoding="utf-8")[:limit].strip()
    except Exception:
        return ""


def _compact_excerpt(text: str, limit: int) -> str:
    parts = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]
    compact = " ".join(parts)
    return compact[:limit]


def read_hermes_memory(
    *,
    context_limit: int = 1600,
    memory_limit: int = 1400,
    user_limit: int = 1000,
) -> dict[str, Any]:
    scaffold = ensure_hermes_memory_scaffold()
    return {
        "root": scaffold["root"],
        "truth_hierarchy": list(TRUTH_HIERARCHY),
        "read_order": ["CONTEXT.md", "MEMORY.md", "USER.md"],
        "context": {
            "path": str(context_path()),
            "authority": "bridge_context_beneath_runtime_registry_and_repo_truth",
            "writer": "max_only",
            "reader": "hermes_then_max_prompt",
            "text": _read_text(context_path(), context_limit),
        },
        "memory": {
            "path": str(memory_path()),
            "authority": "supporting_recall_only",
            "writer": "hermes",
            "reader": "max_prompt",
            "text": _read_text(memory_path(), memory_limit),
        },
        "user": {
            "path": str(user_path()),
            "authority": "supporting_founder_preferences_only",
            "writer": "hermes",
            "reader": "max_prompt",
            "text": _read_text(user_path(), user_limit),
        },
        "skills_dir": str(skills_path()),
    }


def get_hermes_memory_status() -> dict[str, Any]:
    scaffold = ensure_hermes_memory_scaffold()

    def _file_status(path: Path) -> dict[str, Any]:
        exists = path.exists()
        stat = path.stat() if exists else None
        return {
            "path": str(path),
            "exists": exists,
            "mtime": datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc).isoformat() if stat else None,
            "size_bytes": stat.st_size if stat else 0,
        }

    return {
        "root": scaffold["root"],
        "exists": memory_root().exists(),
        "truth_hierarchy": list(TRUTH_HIERARCHY),
        "context": _file_status(context_path()),
        "memory": _file_status(memory_path()),
        "user": _file_status(user_path()),
        "skills_dir": {
            "path": str(skills_path()),
            "exists": skills_path().exists(),
        },
    }


def render_hermes_bridge_for_prompt(*, compact: bool = False) -> str:
    bundle = read_hermes_memory(
        context_limit=420 if compact else 1800,
        memory_limit=220 if compact else 1400,
        user_limit=220 if compact else 1000,
    )
    hierarchy = " > ".join(bundle["truth_hierarchy"])
    context_text = bundle["context"]["text"]
    memory_text = bundle["memory"]["text"]
    user_text = bundle["user"]["text"]

    if compact:
        context_excerpt = _compact_excerpt(context_text, 90) or "awaiting a verified refresh."
        return "\n".join([
            "### Hermes Memory Bridge (supporting only)",
            f"- Truth hierarchy: {hierarchy}.",
            "- Read order: CONTEXT.md -> MEMORY.md -> USER.md.",
            "- CONTEXT.md is MAX-written after verified sessions.",
            f"- CONTEXT: {context_excerpt}",
            "- MEMORY.md and USER.md are supporting only.",
        ])

    return "\n".join([
        "## Hermes Memory Bridge (beneath registry truth)",
        f"Truth hierarchy: {hierarchy}.",
        "Read order:",
        "1. CONTEXT.md — bridge context written by MAX after verified sessions.",
        "2. MEMORY.md — Hermes-maintained supporting recall only.",
        "3. USER.md — Hermes-maintained founder-preference context only.",
        "Hermes does not write CONTEXT.md.",
        "",
        "### CONTEXT.md (bridge; MAX-written)",
        context_text or "_No bridge context available yet._",
        "",
        "### MEMORY.md (supporting recall only)",
        memory_text or "_No supporting memory available._",
        "",
        "### USER.md (supporting preferences only)",
        user_text or "_No founder preference context available._",
    ])


def write_context_from_verified_session(
    *,
    runtime_truth: dict[str, Any],
    packet: dict[str, Any],
    channel: str = "web",
) -> dict[str, Any]:
    ensure_hermes_memory_scaffold()

    registry = load_operating_registry()
    registry_info = get_registry_load_info()
    surface = normalize_surface(channel)
    tier_1 = packet.get("tier_1") or {}
    tier_2 = packet.get("tier_2") or {}

    current_commit = (
        (runtime_truth.get("current_commit") or {}).get("hash")
        or (tier_1.get("last_runtime_truth_result") or {}).get("commit")
        or ""
    )
    openclaw_gate = runtime_truth.get("openclaw_gate") or (tier_1.get("last_runtime_truth_result") or {}).get("openclaw_gate") or {}
    product_statuses = tier_2.get("product_statuses_currently_in_play") or {}
    if not product_statuses:
        product_statuses = {
            item.get("key"): item.get("status")
            for item in registry.get("ecosystem_products", [])
            if item.get("key") in {"max", "relistapp", "finance", "vendorops", "openclaw", "email"}
        }

    active_skill_hooks = [
        item.get("key")
        for item in registry.get("skills", [])
        if item.get("status") == "implemented_callable"
    ]

    lines = [
        "# CONTEXT",
        "",
        "MAX writes this file after verified sessions.",
        "Hermes reads it first and never writes it.",
        "",
        "Truth hierarchy:",
        "runtime > registry > repo truth > Hermes memory > skills",
        "",
        "## Verified Session Snapshot",
        f"- Refreshed at: {datetime.now(timezone.utc).isoformat()}",
        f"- Registry version: {registry_info.get('registry_version')}",
        f"- Running commit hash: {current_commit or 'unknown'}",
        f"- Surface: {surface.get('canonical_channel') or surface.get('surface_key')}",
        f"- OpenClaw gate: {openclaw_gate.get('state') or 'unknown'}",
        f"- Restart required: {(runtime_truth.get('restart_required'))}",
        "",
        "## Active Skill Hooks",
    ]
    if active_skill_hooks:
        lines.extend(f"- {item}" for item in active_skill_hooks)
    else:
        lines.append("- None detected")

    lines.extend([
        "",
        "## Product Statuses In Play",
    ])
    if product_statuses:
        lines.extend(f"- {key}: {value}" for key, value in product_statuses.items())
    else:
        lines.append("- None recorded")

    limitations = tier_2.get("known_limitations_or_degraded_dependencies") or []
    lines.extend([
        "",
        "## Known Limitations",
    ])
    if limitations:
        lines.extend(f"- {item}" for item in limitations)
    else:
        lines.append("- None recorded")

    handoff_summary = {
        "current_task": tier_1.get("current_task"),
        "registry_version": tier_1.get("registry_version"),
        "last_runtime_truth_result": tier_1.get("last_runtime_truth_result"),
    }
    lines.extend([
        "",
        "## Current Verified Handoff Summary",
        "```json",
        json.dumps(handoff_summary, indent=2, sort_keys=True, default=str),
        "```",
        "",
    ])

    target = context_path()
    target.write_text("\n".join(lines), encoding="utf-8")
    return {
        "written": True,
        "path": str(target),
        "registry_version": registry_info.get("registry_version"),
        "commit_hash": current_commit,
        "surface": surface.get("canonical_channel") or surface.get("surface_key"),
    }
