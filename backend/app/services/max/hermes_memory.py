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
    phase2 = {}
    try:
        from app.services.max.hermes_phase2 import ensure_hermes_phase2_scaffold

        phase2 = ensure_hermes_phase2_scaffold()
    except Exception as exc:
        phase2 = {"error": str(exc)}
    phase3 = {}
    try:
        from app.services.max.hermes_phase3 import ensure_hermes_phase3_scaffold

        phase3 = ensure_hermes_phase3_scaffold()
    except Exception as exc:
        phase3 = {"error": str(exc)}
    return {
        "root": str(root),
        "skills_dir": str(skills_path()),
        "created": created,
        "phase2": phase2,
        "phase3": phase3,
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

    status = {
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
    try:
        from app.services.max.hermes_phase2 import get_phase2_status

        status["phase2"] = get_phase2_status()
    except Exception as exc:
        status["phase2"] = {"error": str(exc)}
    try:
        from app.services.max.hermes_phase3 import get_phase3_status

        status["phase3"] = get_phase3_status()
    except Exception as exc:
        status["phase3"] = {"error": str(exc)}
    return status


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
    try:
        from app.services.max.hermes_phase2 import render_phase2_summary_for_prompt

        phase2_summary = render_phase2_summary_for_prompt(compact=compact)
    except Exception:
        phase2_summary = ""
    try:
        from app.services.max.hermes_phase3 import render_phase3_summary_for_prompt

        phase3_summary = render_phase3_summary_for_prompt(compact=compact)
    except Exception:
        phase3_summary = ""

    if compact:
        context_excerpt = _compact_excerpt(context_text, 60) or "awaiting a verified refresh."
        lines = [
            "### Hermes Memory Bridge (supporting only)",
            f"- Truth hierarchy: {hierarchy}.",
            "- Read order: CONTEXT.md -> MEMORY.md -> USER.md.",
            "- CONTEXT.md is MAX-written after verified sessions.",
            f"- CONTEXT: {context_excerpt}",
            "- MEMORY.md and USER.md are supporting only.",
        ]
        if phase2_summary:
            lines.append(f"- {phase2_summary}")
        if phase3_summary:
            lines.append(f"- {phase3_summary}")
        return "\n".join(lines)

    lines = [
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
    ]
    if phase2_summary:
        lines.extend(["", phase2_summary])
    if phase3_summary:
        lines.extend(["", phase3_summary])
    return "\n".join(lines)


def build_hermes_support_packet(
    task_title: str,
    task_description: str,
    target_repo: str = "~/empire-repo-v10",
    target_branch: str = "feature/v10.0-test-lane",
) -> dict[str, Any]:
    """Build a structured Hermes support packet to attach to an OpenClaw task.

    Hermes does NOT execute code. It provides a guidance packet that helps the
    OpenClaw/CodeForge worker execute correctly by clarifying:
    - intake fields expected
    - missing measurement checklist
    - quote package checklist
    - browser/form/page extraction plan
    - approval checkpoints
    - safety notes
    - v10 test-lane boundaries

    This packet is stored as task metadata and is included in the task description
    when the task is queued.
    """
    from datetime import datetime, timezone

    packet_id = f"hermes_support_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
    return {
        "packet_id": packet_id,
        "hermes_role": "support_guidance_only",
        "hermes_does_not": ["write code", "modify files", "commit directly", "access memory"],
        "hermes_does": [
            "attach structured guidance to task",
            "provide intake field checklist",
            "clarify measurement requirements",
            "outline quote package requirements",
            "document approval checkpoints",
            "warn about safety boundaries",
        ],
        "task_title": task_title,
        "task_description": task_description,
        "target": {
            "repo": target_repo,
            "branch": target_branch,
            "write_scope": "v10_test_lane_only",
            "stable_repo_blocked": True,
            "canonical_memory_blocked": True,
        },
        "checklists": {
            "intake_fields": [
                "customer_name — full name",
                "customer_email — contact",
                "customer_phone — for follow-up",
                "product_type — drapery / upholstery / CNC / other",
                "room_measurements — width x height per window/space",
                "material_preference — if specified by customer",
                "budget_range — if provided",
                "timeline — when needed by",
                "photos — reference images uploaded",
            ],
            "measurement_requirements": [
                "Width: measure at 3 points (top, middle, bottom), use narrowest",
                "Height: measure at 3 points (left, center, right), use longest",
                "Depth: for drapery, measure wall-to-window face depth",
                "Rod/track width: end-to-end measurement",
                "Mounting type: inside mount vs outside mount",
                "Special shapes: arch, bay, corner — requires diagram",
            ],
            "quote_package_checklist": [
                "line_item_per_product — itemized pricing",
                "material_cost — fabric/material alone",
                "labor_cost — fabrication + installation",
                "hardware_cost — rods, tracks, brackets",
                "tax_and_permits — if applicable",
                "total_quote — single grand total",
                "validity_period — quote expires date",
                "payment_terms — deposit + balance",
                "revised_quote_triggers — what requires re-quote",
            ],
            "approval_checkpoints": [
                "founder_approval_required — for quotes over threshold",
                "customer_approval_signature — written/email confirmation",
                "material_selection_approval — customer picks from catalog",
                "final_measurement_confirmation — on-site before fabrication",
                "change_order_approval — any scope change needs sign-off",
            ],
            "browser_page_extraction": [
                "URL of source page",
                "Form fields visible on page",
                "Required vs optional fields",
                "Any authentication requirements",
                "API endpoint if form POSTs directly",
            ],
        },
        "safety_notes": [
            "Hermes is read-only guidance — never modifies code or data",
            "All file changes must go through OpenClaw/CodeForge on v10 test-lane only",
            "Stable repo (~/empire-repo) requires explicit founder promotion approval",
            "Canonical memory writes require founder channel authorization (web_cc / telegram / email)",
            "v10 test-lane is: ~/empire-repo-v10 on branch feature/v10.0-test-lane",
            "Never commit directly to main, master, or feature/v10.0 without explicit approval",
        ],
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "hermes_version": "phase1_v1",
    }


def render_task_support_packet(packet: dict[str, Any]) -> str:
    """Render a Hermes support packet as a readable markdown string for attachment to task description."""
    lines = [
        "## Hermes Support Packet",
        f"*Packet ID: {packet.get('packet_id')}*",
        f"*Hermes role: {packet.get('hermes_role')}*",
        "",
        "**IMPORTANT: Hermes does NOT write code or modify files. It provides guidance only.**",
        "",
        f"**Task:** {packet.get('task_title')}",
        f"**Description:** {packet.get('task_description')}",
        "",
        "### Target Environment",
        f"- Repo: `{packet.get('target', {}).get('repo')}`",
        f"- Branch: `{packet.get('target', {}).get('branch')}`",
        f"- Write scope: `{packet.get('target', {}).get('write_scope')}`",
        f"- Stable repo blocked: `{packet.get('target', {}).get('stable_repo_blocked')}`",
        f"- Canonical memory blocked: `{packet.get('target', {}).get('canonical_memory_blocked')}`",
        "",
    ]

    checklists = packet.get("checklists", {})
    for section, items in checklists.items():
        section_title = section.replace("_", " ").title()
        lines.append(f"### {section_title}")
        for item in items:
            lines.append(f"- [ ] {item}")
        lines.append("")

    lines.append("### Safety Notes")
    for note in packet.get("safety_notes", []):
        lines.append(f"- ⚠️ {note}")
    lines.append("")

    return "\n".join(lines)


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


# ── HermesMemoryBridge: MVP triad interface ───────────────────────────────────

class HermesMemoryBridge:
    """
    MVP implementation of the Hermes memory bridge for the MAX→Hermes→OpenClaw triad.
    Provides context assembly, draft creation, and approval gate management.
    """

    def __init__(self):
        self._db_path = Path.home() / "empire-repo-v10" / "backend" / "data" / "empire.db"

    async def assemble_context(
        self,
        task_type: str,
        entity_type: str,
        client_id: Optional[str] = None,
        desk: Optional[str] = None,
    ) -> dict:
        """Assemble context for a task. Returns context dict with id and metadata."""
        import uuid
        context_id = str(uuid.uuid4())[:8]
        return {
            "context_id": context_id,
            "task_type": task_type,
            "entity_type": entity_type,
            "client_id": client_id,
            "desk": desk,
            "assembled_at": datetime.now(timezone.utc).isoformat(),
            "truth_hierarchy": TRUTH_HIERARCHY,
        }

    async def create_draft(
        self,
        draft_type: str,
        base_data: Optional[dict] = None,
    ) -> dict:
        """Create a draft record. Returns draft dict with id and status."""
        import uuid
        draft_id = f"draft_{uuid.uuid4().hex[:12]}"
        return {
            "id": draft_id,
            "type": draft_type,
            "status": base_data.get("status", "draft") if base_data else "draft",
            "data": base_data or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    async def create_approval_gate(
        self,
        action: str,
        draft_id: str,
        level: str = "L1",
        timeout_minutes: int = 15,
    ) -> dict:
        """Create an approval gate for a draft. Returns gate dict."""
        import uuid
        gate_id = f"gate_{uuid.uuid4().hex[:12]}"
        return {
            "id": gate_id,
            "action": action,
            "draft_id": draft_id,
            "level": level,
            "status": "pending",
            "timeout_minutes": timeout_minutes,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
