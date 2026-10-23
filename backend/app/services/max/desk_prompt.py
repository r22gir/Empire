"""Desk-aware system prompt builder — cache-stable order.

Fixed content (persona, rules/conduct, tool lists, provider/model pin) comes
first. Changing values (date, live task counts) come last so a provider that
caches the prompt prefix can reuse it across turns.

Behavior of the instructions does not change — only the section order.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.db.database import get_db, dict_row, dict_rows
from .system_prompt import get_system_prompt

logger = logging.getLogger("max.desk_prompt")

# Pin matches DESK_MODEL_ROUTING in ai_router.py. Caching applies only when
# the same provider+model is used for the desk. Do not invent a new model.
DESK_CACHE_PINS: dict[str, dict[str, str]] = {
    "codeforge": {"provider": "minimax", "model": "minimax"},
    "analytics": {"provider": "claude", "model": "claude-sonnet-4-6"},
    "quality": {"provider": "claude", "model": "claude-sonnet-4-6"},
    "innovation": {"provider": "claude", "model": "claude-sonnet-4-6"},
    "forge": {"provider": "minimax", "model": "minimax"},
    "sales": {"provider": "groq", "model": "groq"},
    "costtracker": {"provider": "openai", "model": "gpt-4.1-nano"},
    "it": {"provider": "minimax", "model": "minimax"},
    "marketing": {"provider": "minimax", "model": "minimax"},
    "support": {"provider": "minimax", "model": "minimax"},
}

FIXED_END_MARKER = "=== END FIXED DESK PREFIX ==="
CHANGING_START_MARKER = "=== BEGIN TURN CONTEXT ==="


def resolve_desk_cache_pin(desk_id: str | None) -> Optional[dict[str, str]]:
    if not desk_id:
        return None
    pin = DESK_CACHE_PINS.get(desk_id)
    if not pin:
        return None
    return {"desk_id": desk_id, **pin, "cacheable": True}


def _load_desk_config(desk_id: str) -> dict | None:
    """Load desk configuration from desk_configs table."""
    try:
        with get_db() as conn:
            row = conn.execute(
                "SELECT * FROM desk_configs WHERE desk_id = ? AND is_active = 1",
                (desk_id,),
            ).fetchone()
            return dict_row(row)
    except Exception as e:
        logger.warning(f"Could not load desk config for {desk_id}: {e}")
        return None


def _load_desk_task_counts(desk_id: str) -> dict:
    """Fetch live task status counts for a desk."""
    counts = {"todo": 0, "in_progress": 0, "waiting": 0, "done": 0}
    try:
        with get_db() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) as cnt FROM tasks WHERE desk = ? AND status != 'cancelled' GROUP BY status",
                (desk_id,),
            ).fetchall()
            for r in dict_rows(rows):
                if r["status"] in counts:
                    counts[r["status"]] = r["cnt"]
    except Exception as e:
        logger.debug(f"Could not load task counts for {desk_id}: {e}")
    return counts


def _persona_text(desk_id: str, config: dict | None) -> str:
    if config and config.get("system_prompt"):
        return str(config["system_prompt"]).rstrip()
    try:
        from app.services.max.desks.desk_registry import roster_by_id

        row = roster_by_id().get(desk_id) or {}
        if row:
            return (
                f"You are {row.get('agent')}, the AI agent running the {row.get('name')} "
                f"desk (`{desk_id}`) for Empire Workroom. Scope: {row.get('scope')}"
            )
    except Exception:
        pass
    return get_system_prompt()


def _conduct_section(desk_id: str) -> str:
    try:
        from app.services.max.conduct import get_conduct_prompt

        return (get_conduct_prompt(desk_id) or "").rstrip()
    except Exception:
        return ""


def _tool_section() -> str:
    try:
        from app.services.max.tool_executor import TOOLS_DOC

        return (TOOLS_DOC or "").rstrip()
    except Exception:
        return ""


def _task_summary(desk_id: str, counts: dict) -> str:
    total_open = counts["todo"] + counts["in_progress"] + counts["waiting"]
    return (
        f"Current {desk_id} desk tasks: "
        f"{counts['todo']} to-do, {counts['in_progress']} in progress, "
        f"{counts['waiting']} waiting, {counts['done']} done. "
        f"({total_open} open)"
    )


def _pin_section(pin: Optional[dict[str, str]]) -> str:
    if not pin:
        return ""
    return f"## Provider / model pin\nprovider={pin['provider']} model={pin['model']}"


@dataclass(frozen=True)
class DeskPromptBundle:
    desk_id: str
    text: str
    fixed_prefix: str
    changing_suffix: str
    cache_pin: Optional[dict[str, str]]
    cacheable: bool
    prefix_hash: str


def assemble_desk_prompt_parts(
    *,
    persona: str,
    conduct: str = "",
    tools: str = "",
    pin: Optional[dict[str, str]] = None,
    date_text: str = "",
    live_context: str = "",
    order: str = "cache",
) -> tuple[str, str]:
    """Split fixed vs changing. ``order='legacy'`` is the pre-cache layout."""
    pin_text = _pin_section(pin)
    if order == "legacy":
        # Old get_desk_system_prompt: persona, live context, then conduct+tools.
        changing = f"## Live Context\n{live_context}".rstrip()
        fixed_tail = "\n\n".join(p for p in (conduct, tools) if p)
        changing_full = changing + (("\n" + fixed_tail) if fixed_tail else "")
        return persona.rstrip(), changing_full
    fixed_parts = [persona.rstrip()]
    if conduct:
        fixed_parts.append(conduct)
    if pin_text:
        fixed_parts.append(pin_text)
    if tools:
        fixed_parts.append(tools)
    fixed_parts.append(FIXED_END_MARKER)
    changing_parts = [CHANGING_START_MARKER]
    if date_text:
        changing_parts.append(f"## Turn\nDate: {date_text}")
    if live_context:
        changing_parts.append(f"## Live Context\n{live_context}")
    return "\n\n".join(fixed_parts).rstrip(), "\n\n".join(changing_parts).rstrip()


def build_desk_prompt(
    desk_id: str,
    *,
    now: Optional[datetime] = None,
    task_counts: Optional[dict] = None,
    config: Optional[dict] = None,
    order: str = "cache",
) -> DeskPromptBundle:
    cfg = config if config is not None else _load_desk_config(desk_id)
    counts = task_counts if task_counts is not None else _load_desk_task_counts(desk_id)
    stamp = now or datetime.now()
    date_text = stamp.strftime("%B %d, %Y")
    pin = resolve_desk_cache_pin(desk_id)
    persona = _persona_text(desk_id, cfg)
    conduct = _conduct_section(desk_id)
    tools = _tool_section()
    live = _task_summary(desk_id, counts)
    fixed, changing = assemble_desk_prompt_parts(
        persona=persona,
        conduct=conduct,
        tools=tools,
        pin=pin,
        date_text=date_text,
        live_context=live,
        order=order,
    )
    text = f"{fixed}\n\n{changing}".rstrip() + "\n"
    prefix_hash = hashlib.sha256(fixed.encode("utf-8")).hexdigest()
    return DeskPromptBundle(
        desk_id=desk_id,
        text=text,
        fixed_prefix=fixed,
        changing_suffix=changing,
        cache_pin=pin,
        cacheable=bool(pin),
        prefix_hash=prefix_hash,
    )


def get_desk_system_prompt(desk_id: str) -> str:
    """Build a composite system prompt for a specific desk.

    Cache-stable order when the desk has a stored persona: rules, pin, and
    tool lists first; date and live task counts last. Falls back to the
    general MAX system prompt if the desk is not found — same as before.
    """
    config = _load_desk_config(desk_id)
    if not config or not config.get("system_prompt"):
        return get_system_prompt()
    return build_desk_prompt(desk_id, config=config).text


def assemble_desk_chat_messages(
    desk_id: str,
    user_message: str,
    *,
    history: Optional[list[dict[str, Any]]] = None,
    now: Optional[datetime] = None,
    task_counts: Optional[dict] = None,
    config: Optional[dict] = None,
    order: str = "cache",
) -> dict[str, Any]:
    """Same shape the real chat path sends: system first, user last."""
    bundle = build_desk_prompt(
        desk_id, now=now, task_counts=task_counts, config=config, order=order,
    )
    messages: list[dict[str, str]] = [{"role": "system", "content": bundle.text}]
    for item in history or []:
        role = item.get("role") or "user"
        content = item.get("content") or ""
        if role in {"user", "assistant", "system"} and content:
            messages.append({"role": role, "content": str(content)})
    messages.append({"role": "user", "content": user_message})
    return {
        "desk_id": desk_id,
        "messages": messages,
        "system_prompt": bundle.text,
        "fixed_prefix": bundle.fixed_prefix,
        "changing_suffix": bundle.changing_suffix,
        "cache_pin": bundle.cache_pin,
        "cacheable": bundle.cacheable,
        "prefix_hash": bundle.prefix_hash,
    }


def longest_common_prefix(a: str, b: str) -> str:
    n = min(len(a), len(b))
    i = 0
    while i < n and a[i] == b[i]:
        i += 1
    return a[:i]


def measure_desk_prefix_stability(
    desk_id: str,
    *,
    config: Optional[dict] = None,
    user_a: str = "What is on the desk today?",
    user_b: str = "Need a quote revision for the mock job.",
    date_a: Optional[datetime] = None,
    date_b: Optional[datetime] = None,
    counts_a: Optional[dict] = None,
    counts_b: Optional[dict] = None,
) -> dict[str, Any]:
    """Before/after prefix stability on the real chat-path assembler.

    Two mock turns with different dates, task counts, and user messages.
    ``legacy`` is the old order (live context before conduct/tools).
    ``cache`` is the new order (fixed first, changing last).
    """
    date_a = date_a or datetime(2026, 10, 22, 14, 0, 0)
    date_b = date_b or datetime(2026, 10, 23, 9, 30, 0)
    counts_a = counts_a or {"todo": 2, "in_progress": 1, "waiting": 0, "done": 4}
    counts_b = counts_b or {"todo": 5, "in_progress": 0, "waiting": 1, "done": 7}
    cfg = config if config is not None else {
        "system_prompt": (
            f"You are the {desk_id} desk agent. Follow Empire Workroom rules. "
            "Never invent dimensions. Never send to clients."
        ),
    }

    def _pair(order: str) -> dict[str, Any]:
        first = assemble_desk_chat_messages(
            desk_id, user_a, now=date_a, task_counts=counts_a, config=cfg, order=order,
        )
        second = assemble_desk_chat_messages(
            desk_id, user_b, now=date_b, task_counts=counts_b, config=cfg, order=order,
        )
        lcp = longest_common_prefix(first["system_prompt"], second["system_prompt"])
        fixed_len = len(first["fixed_prefix"])
        sys_len = max(len(first["system_prompt"]), 1)
        prefix_stable = first["prefix_hash"] == second["prefix_hash"]
        tools_in_lcp = "## Available Tools" in lcp
        fixed_marker_in_lcp = "END FIXED DESK PREFIX" in lcp
        return {
            "order": order,
            "lcp_chars": len(lcp),
            "system_chars": sys_len,
            "fixed_prefix_chars": fixed_len,
            "lcp_ratio": round(len(lcp) / sys_len, 4),
            "fixed_covered": len(lcp) >= fixed_len,
            "prefix_hash_stable": prefix_stable,
            "tools_in_lcp": tools_in_lcp,
            "fixed_marker_in_lcp": fixed_marker_in_lcp,
            "cache_hit": bool(first.get("cacheable") and fixed_marker_in_lcp),
            "cache_pin": first.get("cache_pin"),
            "user_last_a": first["messages"][-1]["role"] == "user",
            "user_last_b": second["messages"][-1]["role"] == "user",
        }

    legacy = _pair("legacy")
    cache = _pair("cache")
    return {
        "desk_id": desk_id,
        "before": legacy,
        "after": cache,
        "lcp_gain_chars": cache["lcp_chars"] - legacy["lcp_chars"],
        "cache_hit_before": legacy["cache_hit"],
        "cache_hit_after": cache["cache_hit"],
    }
