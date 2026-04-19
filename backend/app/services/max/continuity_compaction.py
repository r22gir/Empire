"""Structured MAX continuity compaction and session handoff packets."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.max.operating_registry import get_registry_load_info
from app.services.max.surface_identity import normalize_surface


CONTEXT_TOKEN_THRESHOLD = 120_000
HANDOFF_PATH = Path.home() / "empire-repo" / "backend" / "data" / "max" / "session_handoff.json"

COMPACTION_POLICY = {
    "threshold_tokens": CONTEXT_TOKEN_THRESHOLD,
    "triggers": [
        "context approaches threshold",
        "session handoff",
        "explicit founder request: compact now/save state",
    ],
    "tiers": {
        "tier_1": [
            "current_task",
            "founder_surface_identity",
            "registry_version",
            "last_runtime_truth_result",
        ],
        "tier_2": [
            "product_statuses_currently_in_play",
            "known_limitations_or_degraded_dependencies",
            "most_recent_delegated_task_state",
        ],
        "tier_3": [
            "last_meaningful_founder_intent_summary",
            "recent_session_history_summary",
        ],
    },
}


def _summarize(value: Any, limit: int = 700) -> Any:
    if value is None:
        return None
    if isinstance(value, str):
        return value[:limit]
    text = json.dumps(value, default=str, sort_keys=True)
    return text[:limit]


def build_session_handoff_packet(
    *,
    current_task: str,
    channel: str = "web",
    last_runtime_truth_result: dict[str, Any] | None = None,
    product_statuses: dict[str, Any] | None = None,
    known_limitations: list[str] | None = None,
    delegated_task_state: dict[str, Any] | None = None,
    last_founder_intent: str | None = None,
    recent_session_history: Any = None,
    last_evaluation_score: dict[str, Any] | None = None,
    active_skills: list[str] | None = None,
    omitted_note: str | None = None,
) -> dict[str, Any]:
    registry = get_registry_load_info()
    surface = normalize_surface(channel)
    active_skills = active_skills or ["empire_runtime_truth_check"]

    return {
        "schema": "max-session-handoff-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "trigger_policy": COMPACTION_POLICY["triggers"],
        "tier_1": {
            "current_task": current_task,
            "founder_surface_identity": surface,
            "registry_version": registry.get("registry_version"),
            "last_runtime_truth_result": last_runtime_truth_result,
        },
        "tier_2": {
            "product_statuses_currently_in_play": product_statuses or {},
            "known_limitations_or_degraded_dependencies": known_limitations or [],
            "most_recent_delegated_task_state": delegated_task_state or {},
            "omitted_note": omitted_note,
        },
        "tier_3": {
            "last_meaningful_founder_intent_summary": _summarize(last_founder_intent),
            "recent_session_history_summary": _summarize(recent_session_history),
        },
        "last_evaluation_score": last_evaluation_score,
        "currently_active_skills": active_skills,
        "open_tasks_or_delegated_task_state": delegated_task_state or {},
        "current_registry_version": registry.get("registry_version"),
    }


def write_session_handoff_packet(packet: dict[str, Any], path: Path = HANDOFF_PATH) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, indent=2, sort_keys=True), encoding="utf-8")
    return path


def read_session_handoff_packet(path: Path = HANDOFF_PATH) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        tier_1 = data.get("tier_1") or {}
        required = {"current_task", "founder_surface_identity", "registry_version", "last_runtime_truth_result"}
        if not required.issubset(tier_1.keys()):
            return None
        return data
    except Exception:
        return None


def restore_session_handoff(path: Path = HANDOFF_PATH) -> dict[str, Any]:
    packet = read_session_handoff_packet(path)
    if not packet:
        return {"restored": False, "reason": "no valid handoff packet"}
    return {
        "restored": True,
        "tier_1": packet["tier_1"],
        "last_evaluation_score": packet.get("last_evaluation_score"),
        "currently_active_skills": packet.get("currently_active_skills", []),
        "open_tasks_or_delegated_task_state": packet.get("open_tasks_or_delegated_task_state", {}),
        "current_registry_version": packet.get("current_registry_version"),
    }


def render_handoff_for_prompt(limit: int = 1200) -> str:
    packet = read_session_handoff_packet()
    if not packet:
        return ""
    compact = {
        "current_task": packet.get("tier_1", {}).get("current_task"),
        "surface": packet.get("tier_1", {}).get("founder_surface_identity"),
        "registry_version": packet.get("current_registry_version"),
        "last_evaluation_score": packet.get("last_evaluation_score"),
        "open_tasks": packet.get("open_tasks_or_delegated_task_state"),
    }
    return json.dumps(compact, sort_keys=True, default=str)[:limit]
