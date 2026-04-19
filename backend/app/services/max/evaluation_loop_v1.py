"""Evaluation Loop v1: score MAX responses using trace metadata."""
from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.services.max.evaluation_service import _get_db_path, init_evaluation_schema
from app.services.max.operating_registry import get_registry_load_info
from app.services.max.surface_identity import normalize_surface


LEDGER_DB_PATH = Path.home() / "empire-repo" / "backend" / "data" / "brain" / "unified_messages.db"


def init_score_schema(db_path: Path | None = None) -> None:
    db_path = db_path or _get_db_path()
    init_evaluation_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS max_response_scores (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT NOT NULL,
                source_id TEXT NOT NULL,
                scored_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                channel TEXT,
                surface TEXT,
                registry_version TEXT,
                skill_used TEXT,
                registry_current_score REAL,
                surface_score REAL,
                skill_score REAL,
                truthfulness_score REAL,
                stale_runtime_risk_score REAL,
                delegation_safety_score REAL,
                overall_score REAL,
                reasons TEXT,
                metadata_envelope TEXT,
                UNIQUE(source, source_id)
            )
        """)
        conn.commit()


def _json_loads(value: str | None) -> dict[str, Any]:
    if not value:
        return {}
    try:
        data = json.loads(value)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _eval_candidates(db_path: Path, limit: int) -> list[dict[str, Any]]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT response_id, created_at, channel, model_used, tools_used, tool_results,
                      any_tool_failure, metadata_envelope
               FROM max_response_evaluations
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    candidates = []
    for row in rows:
        candidates.append({
            "source": "eval_db",
            "source_id": row["response_id"],
            "created_at": row["created_at"],
            "channel": row["channel"],
            "model_used": row["model_used"],
            "tools_used": json.loads(row["tools_used"] or "[]"),
            "tool_results": json.loads(row["tool_results"] or "[]"),
            "any_tool_failure": bool(row["any_tool_failure"]),
            "metadata": _json_loads(row["metadata_envelope"]),
        })
    return candidates


def _ledger_candidates(ledger_path: Path, limit: int) -> list[dict[str, Any]]:
    if not ledger_path.exists():
        return []
    with sqlite3.connect(ledger_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT id, created_at, channel, role, model, tool_results, metadata
               FROM unified_messages
               WHERE role IN ('assistant', 'user')
               ORDER BY created_at DESC
               LIMIT ?""",
            (limit,),
        ).fetchall()
    candidates = []
    for row in rows:
        candidates.append({
            "source": "unified_messages",
            "source_id": str(row["id"]),
            "created_at": row["created_at"],
            "channel": row["channel"],
            "model_used": row["model"],
            "tools_used": [],
            "tool_results": json.loads(row["tool_results"] or "[]") if row["tool_results"] else [],
            "any_tool_failure": False,
            "metadata": _json_loads(row["metadata"]),
        })
    return candidates


def _pick_surface_coverage(candidates: list[dict[str, Any]], min_count: int) -> list[dict[str, Any]]:
    picked = []
    seen = set()
    for target in ["web_chat", "telegram", "email"]:
        for candidate in candidates:
            canonical = normalize_surface(candidate.get("channel")).get("canonical_channel")
            key = (candidate["source"], candidate["source_id"])
            if canonical == target and key not in seen:
                picked.append(candidate)
                seen.add(key)
                break
    for candidate in candidates:
        if len(picked) >= min_count:
            break
        key = (candidate["source"], candidate["source_id"])
        if key not in seen:
            picked.append(candidate)
            seen.add(key)
    return picked


def _score_candidate(candidate: dict[str, Any], current_registry_version: str) -> dict[str, Any]:
    metadata = candidate.get("metadata") or {}
    channel = candidate.get("channel")
    normalized = normalize_surface(channel)
    expected_surface = normalized["surface"]
    registry_version = metadata.get("registry_version") or metadata.get("registry") or ""
    surface = metadata.get("surface") or expected_surface
    skill_used = metadata.get("skill_used")
    tool_results = candidate.get("tool_results") or []
    tools_used = candidate.get("tools_used") or []
    any_failure = candidate.get("any_tool_failure") or any(not r.get("success", True) for r in tool_results if isinstance(r, dict))

    registry_current_score = 1.0 if registry_version == current_registry_version else (0.6 if not registry_version else 0.3)
    surface_score = 1.0 if surface == expected_surface else 0.4
    skill_score = 1.0
    if "runtime" in str(candidate.get("model_used", "")).lower() and skill_used != "empire_runtime_truth_check":
        skill_score = 0.5
    if any("openclaw" in str(t).lower() for t in tools_used) and not metadata.get("openclaw_gate_state"):
        skill_score = min(skill_score, 0.6)

    truthfulness_score = 0.7 if any_failure else 0.9
    stale_runtime_risk_score = 1.0 if registry_current_score >= 1.0 else 0.6
    delegation_safety_score = 1.0
    if any("openclaw" in str(t).lower() for t in tools_used):
        delegation_safety_score = 1.0 if metadata.get("openclaw_gate_state") == "healthy" else 0.5

    overall = round((
        registry_current_score * 0.20
        + surface_score * 0.20
        + skill_score * 0.15
        + truthfulness_score * 0.20
        + stale_runtime_risk_score * 0.15
        + delegation_safety_score * 0.10
    ), 3)
    reasons = {
        "expected_surface": expected_surface,
        "registry_version_current": registry_version == current_registry_version,
        "any_tool_failure": any_failure,
        "should_have_invoked_runtime_truth_or_openclaw_gate": skill_score < 1.0 or delegation_safety_score < 1.0,
    }
    return {
        "source": candidate["source"],
        "source_id": candidate["source_id"],
        "channel": channel,
        "surface": surface,
        "registry_version": registry_version,
        "skill_used": skill_used,
        "registry_current_score": registry_current_score,
        "surface_score": surface_score,
        "skill_score": skill_score,
        "truthfulness_score": truthfulness_score,
        "stale_runtime_risk_score": stale_runtime_risk_score,
        "delegation_safety_score": delegation_safety_score,
        "overall_score": overall,
        "reasons": reasons,
        "metadata_envelope": metadata,
    }


def run_evaluation_loop_v1(
    min_count: int = 5,
    db_path: Path | None = None,
    ledger_path: Path = LEDGER_DB_PATH,
) -> dict[str, Any]:
    db_path = db_path or _get_db_path()
    init_score_schema(db_path)
    registry = get_registry_load_info()
    current_version = registry.get("registry_version") or ""

    candidates = _eval_candidates(db_path, limit=80) + _ledger_candidates(ledger_path, limit=500)
    selected = _pick_surface_coverage(candidates, min_count)
    scores = [_score_candidate(candidate, current_version) for candidate in selected]

    with sqlite3.connect(db_path) as conn:
        for score in scores:
            conn.execute(
                """INSERT OR REPLACE INTO max_response_scores
                   (source, source_id, scored_at, channel, surface, registry_version, skill_used,
                    registry_current_score, surface_score, skill_score, truthfulness_score,
                    stale_runtime_risk_score, delegation_safety_score, overall_score,
                    reasons, metadata_envelope)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    score["source"], score["source_id"], datetime.now(timezone.utc).isoformat(),
                    score["channel"], score["surface"], score["registry_version"], score["skill_used"],
                    score["registry_current_score"], score["surface_score"], score["skill_score"],
                    score["truthfulness_score"], score["stale_runtime_risk_score"],
                    score["delegation_safety_score"], score["overall_score"],
                    json.dumps(score["reasons"], sort_keys=True),
                    json.dumps(score["metadata_envelope"], sort_keys=True, default=str),
                ),
            )
        conn.commit()

    surfaces = sorted({normalize_surface(score.get("channel")).get("canonical_channel") for score in scores if score.get("channel")})
    return {
        "scored_count": len(scores),
        "surfaces": surfaces,
        "registry_version": current_version,
        "scores": scores,
    }


def get_recent_scores(limit: int = 10, db_path: Path | None = None) -> list[dict[str, Any]]:
    db_path = db_path or _get_db_path()
    init_score_schema(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(
            """SELECT * FROM max_response_scores ORDER BY scored_at DESC LIMIT ?""",
            (limit,),
        ).fetchall()
    return [
        {
            **dict(row),
            "reasons": _json_loads(row["reasons"]),
            "metadata_envelope": _json_loads(row["metadata_envelope"]),
        }
        for row in rows
    ]
