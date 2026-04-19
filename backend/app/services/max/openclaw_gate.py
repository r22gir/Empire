"""Bounded OpenClaw pre-delegation health gate."""
from __future__ import annotations

import os
import sqlite3
import time
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import httpx


GATE_TTL_SECONDS = 20
OPENCLAW_URL = os.getenv("OPENCLAW_URL", "http://localhost:7878").rstrip("/")
DB_PATH = Path.home() / "empire-repo" / "backend" / "data" / "empire.db"

GATE_MESSAGES = {
    "healthy": "OpenClaw healthy - delegating task now.",
    "degraded": "OpenClaw degraded ({reason}) - delegation blocked. Will retry when healthy.",
    "unknown": "OpenClaw status unknown - running in inspect-only mode. Manual delegation available.",
    "unavailable": "OpenClaw unavailable - task queued locally. Will delegate when service restores.",
}

_cache: dict[str, Any] = {"checked_at_monotonic": 0.0, "result": None}


@dataclass
class OpenClawGateResult:
    state: str
    allowed: bool
    reason: str
    checked_at: str
    cache_ttl_seconds: int
    cache_age_seconds: float
    health_endpoint: str
    health_status_code: int | None = None
    queue_ready: bool | None = None
    queue_stats: dict[str, Any] | None = None
    recent_task_viability: dict[str, Any] | None = None
    founder_message: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _message_for(state: str, reason: str) -> str:
    template = GATE_MESSAGES.get(state, GATE_MESSAGES["unknown"])
    return template.format(reason=reason or "unknown")


def _queue_snapshot(db_path: Path = DB_PATH) -> tuple[bool, dict[str, Any], dict[str, Any]]:
    try:
        with sqlite3.connect(db_path) as conn:
            rows = conn.execute("SELECT status, COUNT(*) FROM openclaw_tasks GROUP BY status").fetchall()
            stats = {row[0]: row[1] for row in rows}
            stats["total"] = sum(stats.values())
            recent = conn.execute(
                """SELECT status, COUNT(*)
                   FROM openclaw_tasks
                   WHERE created_at >= datetime('now', '-24 hours')
                   GROUP BY status"""
            ).fetchall()
            recent_stats = {row[0]: row[1] for row in recent}
            recent_stats["total"] = sum(recent_stats.values())
        return True, stats, recent_stats
    except Exception as exc:
        return False, {"error": str(exc)}, {"error": str(exc)}


def _build_result(
    state: str,
    reason: str,
    status_code: int | None,
    queue_ready: bool | None,
    queue_stats: dict[str, Any] | None,
    recent_task_viability: dict[str, Any] | None,
    health_endpoint: str,
    cache_age_seconds: float = 0.0,
) -> OpenClawGateResult:
    return OpenClawGateResult(
        state=state,
        allowed=state == "healthy",
        reason=reason,
        checked_at=datetime.now(timezone.utc).isoformat(),
        cache_ttl_seconds=GATE_TTL_SECONDS,
        cache_age_seconds=round(cache_age_seconds, 3),
        health_endpoint=health_endpoint,
        health_status_code=status_code,
        queue_ready=queue_ready,
        queue_stats=queue_stats,
        recent_task_viability=recent_task_viability,
        founder_message=_message_for(state, reason),
    )


def check_openclaw_gate(force: bool = False, timeout: float = 2.0) -> OpenClawGateResult:
    """Return a cached four-state delegation gate result.

    Healthy results only allow delegation inside the TTL. Once expired, the
    caller gets a fresh health check instead of silently trusting stale health.
    """
    now = time.monotonic()
    cached = _cache.get("result")
    checked_at = float(_cache.get("checked_at_monotonic") or 0.0)
    if cached is not None and not force and now - checked_at < GATE_TTL_SECONDS:
        data = cached.to_dict()
        data["cache_age_seconds"] = round(now - checked_at, 3)
        return OpenClawGateResult(**data)

    health_endpoint = f"{OPENCLAW_URL}/health"
    queue_ready, queue_stats, recent_viability = _queue_snapshot()
    state = "unknown"
    reason = "health check not completed"
    status_code = None

    try:
        resp = httpx.get(health_endpoint, timeout=timeout)
        status_code = resp.status_code
        if resp.status_code != 200:
            state = "degraded"
            reason = f"health endpoint returned {resp.status_code}"
        elif not queue_ready:
            state = "degraded"
            reason = f"queue not ready: {queue_stats.get('error', 'unknown')}"
        else:
            state = "healthy"
            reason = "health endpoint and local queue ready"
    except httpx.ConnectError:
        state = "unavailable"
        reason = "connection refused"
    except httpx.TimeoutException:
        state = "unknown"
        reason = f"health check timed out after {timeout}s"
    except Exception as exc:
        state = "unknown"
        reason = str(exc)

    result = _build_result(
        state=state,
        reason=reason,
        status_code=status_code,
        queue_ready=queue_ready,
        queue_stats=queue_stats,
        recent_task_viability=recent_viability,
        health_endpoint=health_endpoint,
    )
    _cache.update({"checked_at_monotonic": now, "result": result})
    return result


def clear_openclaw_gate_cache() -> None:
    _cache.update({"checked_at_monotonic": 0.0, "result": None})


def openclaw_gate_metadata(gate: OpenClawGateResult) -> dict[str, Any]:
    return {
        "openclaw_gate_state": gate.state,
        "openclaw_gate_allowed": gate.allowed,
        "openclaw_gate_reason": gate.reason,
        "openclaw_gate_checked_at": gate.checked_at,
        "openclaw_gate_cache_ttl_seconds": gate.cache_ttl_seconds,
    }
