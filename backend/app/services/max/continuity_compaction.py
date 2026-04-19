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


def should_handle_continuity_command(message: str) -> bool:
    msg = (message or "").strip().lower()
    return any(
        phrase in msg
        for phrase in {
            "compact now",
            "save state",
            "handoff this session",
            "what were we doing",
            "what were we doing?",
        }
    )


def should_run_continuity_audit(message: str) -> bool:
    msg = (message or "").strip().lower()
    return any(
        phrase in msg
        for phrase in {
            "is max current on this device",
            "is max updated on this device",
            "latest handoff state",
            "what task was active last",
            "what continuity packet is loaded",
            "continuity audit",
        }
    )


def _git_commit() -> str:
    try:
        import subprocess
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], text=True).strip()
    except Exception:
        return ""


def _active_task_state() -> dict[str, Any]:
    db_path = Path.home() / "empire-repo" / "backend" / "data" / "empire.db"
    try:
        import sqlite3
        with sqlite3.connect(db_path) as conn:
            conn.row_factory = sqlite3.Row
            openclaw = conn.execute(
                """SELECT id, title, desk, status, priority, created_at, error
                   FROM openclaw_tasks
                   WHERE status IN ('queued', 'running', 'paused', 'failed')
                   ORDER BY created_at DESC
                   LIMIT 5"""
            ).fetchall()
            tasks = conn.execute(
                """SELECT id, title, desk, status, priority, created_at
                   FROM tasks
                   WHERE status IN ('todo', 'in_progress')
                   ORDER BY created_at DESC
                   LIMIT 5"""
            ).fetchall()
        return {
            "openclaw_tasks": [dict(row) for row in openclaw],
            "max_tasks": [dict(row) for row in tasks],
        }
    except Exception as exc:
        return {"error": str(exc)}


def _latest_score() -> dict[str, Any] | None:
    try:
        from app.services.max.evaluation_loop_v1 import get_recent_scores
        scores = get_recent_scores(limit=1)
        return scores[0] if scores else None
    except Exception:
        return None


def _runtime_truth() -> dict[str, Any]:
    try:
        from app.services.max.runtime_truth_check import run_runtime_truth_check
        return run_runtime_truth_check(public=True)
    except Exception as exc:
        return {"error": str(exc)}


def create_founder_handoff(
    *,
    message: str,
    channel: str = "web",
    history: Any = None,
    path: Path | None = None,
) -> dict[str, Any]:
    """Refresh a founder-visible session handoff packet from current runtime truth."""
    path = path or HANDOFF_PATH
    runtime_truth = _runtime_truth()

    active_state = _active_task_state()
    latest_score = _latest_score()
    packet = build_session_handoff_packet(
        current_task="Founder-requested MAX session continuity handoff",
        channel=channel,
        last_runtime_truth_result={
            "commit": (runtime_truth.get("current_commit") or {}).get("hash") or _git_commit(),
            "restart_required": runtime_truth.get("restart_required"),
            "openclaw_gate": runtime_truth.get("openclaw_gate"),
            "runtime_error": runtime_truth.get("error"),
        },
        product_statuses={
            "max": "continuity handoff refreshed by founder command",
            "openclaw": (runtime_truth.get("openclaw_gate") or {}).get("state"),
        },
        known_limitations=[
            "External Supermemory is not wired; this packet is local repo/runtime continuity.",
            "Legacy history endpoints still coexist beside All Channels.",
        ],
        delegated_task_state=active_state,
        last_founder_intent=message,
        recent_session_history=history or [],
        last_evaluation_score=latest_score,
        active_skills=["empire_runtime_truth_check", "empire_max_continuity_audit"],
    )
    write_session_handoff_packet(packet, path)
    return {
        "packet": packet,
        "path": str(path),
        "runtime_truth": runtime_truth,
        "latest_score": latest_score,
        "active_task_state": active_state,
    }


def audit_continuity_state(channel: str = "web") -> dict[str, Any]:
    packet = read_session_handoff_packet()
    restored = restore_session_handoff()
    registry = get_registry_load_info()
    surface = normalize_surface(channel)
    return {
        "callable": "empire_max_continuity_audit",
        "surface": surface,
        "registry_version": registry.get("registry_version"),
        "handoff_loaded": bool(packet),
        "handoff": restored,
        "latest_score": _latest_score(),
        "active_task_state": _active_task_state(),
        "supermemory_status": "deferred_not_authoritative",
    }


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
