"""Shadow-mode confidence scorer for Max routing and tool actions.

Default MAX_CONFIDENCE_GATE=shadow: score and log, never change behavior.
Cheap heuristics first. Optional included-model nudge only when quota remains
(no auto-credits). Low-score cases can be filed as proposed improvements
(draft only — never approved).

Tests must set EMPIRE_DATA_DIR / EMPIRE_TASK_DB to temp paths.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from app.services.data_paths import data_root
from app.services.max.whatsapp_format import (
    first_url,
    has_real_job_signals,
    is_frustration_correction,
    is_link_or_article_message,
)

logger = logging.getLogger("max.confidence")

INTENTS = (
    "quote_intake",
    "article_link",
    "task",
    "question",
    "frustration_reread",
    "greeting",
    "other",
)
LOW_THRESHOLD = 0.55
FAMILY_EDITIONS = frozenset({"max_e", "maxine", "amp", "juan", "camilo"})
FAMILY_OWNERS = frozenset({"juan", "camilo", "max-e", "max_e", "maxe", "maxine"})

_TASK_RE = re.compile(
    r"\b(?:create|make|generate|draw|render|queue|run|start|do)\b.+"
    r"\b(?:task|image|drawing|render|desk|photo|picture)\b",
    re.IGNORECASE,
)
_QUESTION_RE = re.compile(
    r"^\W*(?:can|could|would|will|do|does|did|is|are|what|what's|whats|"
    r"where|when|which|who|how|why|show|tell|give|find|check|pull|open|list)\b",
    re.IGNORECASE,
)
_GREETING_RE = re.compile(r"^\W*(?:hi|hello|hey|good\s+(?:morning|afternoon|evening)|yo)\W*$", re.I)


def gate_mode() -> str:
    raw = (os.getenv("MAX_CONFIDENCE_GATE") or "shadow").strip().lower()
    if raw in {"0", "false", "off", "disabled", "no"}:
        return "off"
    if raw in {"1", "true", "on", "gate", "enabled"}:
        return "on"
    return "shadow"


def is_enabled() -> bool:
    return gate_mode() != "off"


def low_threshold() -> float:
    raw = (os.getenv("MAX_CONFIDENCE_LOW") or "").strip()
    if not raw:
        return LOW_THRESHOLD
    try:
        return min(0.95, max(0.05, float(raw)))
    except ValueError:
        return LOW_THRESHOLD


def process_edition(explicit: str | None = None) -> str:
    raw = (explicit or os.getenv("EMPIRE_EDITION") or os.getenv("WHATSAPP_EDITION_OWNER") or "").strip().lower()
    raw = raw.replace("-", "_")
    if raw in {"", "main", "workroom", "empire", "founder", "studio"}:
        return "main"
    if raw in {"amp", "max_e", "maxe", "juan"}:
        return "max_e"
    if raw in {"maxine", "camilo"}:
        return "maxine"
    return raw or "unknown"


def is_juan_camilo_edition(edition: str | None = None, requester: str | None = None) -> bool:
    ed = process_edition(edition)
    if ed in FAMILY_EDITIONS or ed in {"max_e", "maxine"}:
        return True
    who = (requester or os.getenv("WHATSAPP_EDITION_OWNER") or "").strip().lower()
    return who in FAMILY_OWNERS


def db_path() -> Path:
    override = (os.getenv("MAX_CONFIDENCE_DB") or "").strip()
    if override:
        return Path(override)
    return data_root() / "logs" / "confidence.db"


@contextmanager
def _db():
    dest = db_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(dest), timeout=15)
    conn.row_factory = sqlite3.Row
    try:
        _ensure(conn)
        yield conn
        conn.commit()
    finally:
        conn.close()


def _ensure(conn) -> None:
    conn.execute(
        """CREATE TABLE IF NOT EXISTS confidence_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            kind TEXT NOT NULL,
            chosen_path TEXT,
            best_path TEXT,
            score REAL NOT NULL,
            scores_json TEXT,
            would_gate INTEGER NOT NULL DEFAULT 0,
            gated_action TEXT,
            edition TEXT,
            family_flag INTEGER NOT NULL DEFAULT 0,
            mode TEXT,
            text TEXT,
            context_json TEXT,
            correction INTEGER NOT NULL DEFAULT 0,
            improvement_id INTEGER
        )"""
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_conf_created ON confidence_events(created_at)"
    )


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def heuristic_intent_scores(text: str) -> dict[str, float]:
    """Cheap rules. An X/twitter URL scores high for article_link, low for quote_intake."""
    scores = {name: 0.08 for name in INTENTS}
    raw = (text or "").strip()
    if not raw:
        scores["other"] = 0.4
        return scores

    if is_link_or_article_message(raw) or (first_url(raw) and not has_real_job_signals(raw)):
        scores["article_link"] = 0.94
        scores["quote_intake"] = 0.08
        scores["question"] = 0.22
        scores["task"] = 0.12
    if has_real_job_signals(raw):
        scores["quote_intake"] = 0.92
        scores["article_link"] = min(scores["article_link"], 0.12)
    if is_frustration_correction(raw):
        scores["frustration_reread"] = 0.93
        scores["quote_intake"] = min(scores["quote_intake"], 0.1)
    if _GREETING_RE.match(raw):
        scores["greeting"] = 0.9
        scores["quote_intake"] = min(scores["quote_intake"], 0.05)
    if _QUESTION_RE.match(raw) or raw.endswith("?"):
        scores["question"] = max(scores["question"], 0.72)
        if not has_real_job_signals(raw):
            scores["quote_intake"] = min(scores["quote_intake"], 0.2)
    if _TASK_RE.search(raw):
        scores["task"] = max(scores["task"], 0.78)
    if not any(v >= 0.5 for v in scores.values()):
        scores["other"] = 0.45
    return scores


def clarifying_question(chosen: str, scores: dict[str, float], text: str) -> str:
    best = max(scores, key=scores.get)
    if chosen == "quote_intake" and scores.get("article_link", 0) >= scores.get("quote_intake", 0):
        return "Read this link, or start a quote from it?"
    if chosen == "article_link" and scores.get("quote_intake", 0) >= 0.5:
        return "Should I draft a quote, or just read the article?"
    if chosen == "frustration_reread":
        return "Re-read the last request, or start something new?"
    if best != chosen:
        return f"Treat this as {best.replace('_', ' ')}, or as {chosen.replace('_', ' ')}?"
    return f"Just to confirm — is this a {chosen.replace('_', ' ')}?"


def optional_model_nudge(text: str, scores: dict[str, float]) -> Optional[dict[str, Any]]:
    """Included-model check only when opted in and quota remains. Never spends credits."""
    if (os.getenv("MAX_CONFIDENCE_MODEL_CHECK") or "").strip().lower() not in {"1", "true", "on", "yes"}:
        return None
    try:
        from app.services.max.improvement_planner import usage_snapshot

        snap = usage_snapshot()
        if snap.get("stopped") or snap.get("calls_left", 0) < 1 or snap.get("tokens_left", 0) < 800:
            logger.info(
                "confidence model nudge skipped: quota exhausted auto_credits=%s",
                snap.get("auto_credits"),
            )
            return {"skipped": "quota", "auto_credits": False, "snapshot": {
                "calls_left": snap.get("calls_left"),
                "tokens_left": snap.get("tokens_left"),
                "stopped": snap.get("stopped"),
            }}
    except Exception:
        logger.info("confidence model nudge skipped: planner budget unavailable")
        return {"skipped": "budget_unavailable", "auto_credits": False}
    # Shadow PR: do not call a live model. Record that quota existed.
    return {
        "skipped": "shadow_no_live_call",
        "auto_credits": False,
        "note": "Included-model nudge reserved; heuristics stand until gate is validated.",
    }


def score_intent(
    text: str,
    *,
    chosen_path: str | None = None,
    edition: str | None = None,
    requester: str | None = None,
    persist: bool = True,
    correction: bool = False,
) -> dict[str, Any]:
    """Score a routing/intent decision. Does not change the chosen path."""
    scores = heuristic_intent_scores(text)
    best = max(scores, key=scores.get)
    chosen = (chosen_path or best).strip() or best
    if chosen not in scores:
        scores[chosen] = 0.2
    score = float(scores.get(chosen, 0.2))
    if chosen != best and scores[best] - score >= 0.25:
        # Chosen path fights the heuristics — keep the chosen score (already low).
        score = min(score, 0.35)
    nudge = optional_model_nudge(text, scores)
    low = score < low_threshold()
    ed = process_edition(edition)
    family = is_juan_camilo_edition(ed, requester)
    family_flag = bool(family and low)
    record = {
        "kind": "intent",
        "text": (text or "")[:500],
        "chosen_path": chosen,
        "best_path": best,
        "score": round(score, 3),
        "scores": {k: round(float(v), 3) for k, v in scores.items()},
        "would_gate": bool(low),
        "gated_action": clarifying_question(chosen, scores, text) if low else "",
        "edition": ed,
        "family_flag": family_flag,
        "mode": gate_mode(),
        "correction": bool(correction or is_frustration_correction(text)),
        "model_nudge": nudge,
        "behavior_changed": False,
    }
    if persist and is_enabled():
        _store(record)
        _log_event(record)
    return record


def score_tool(
    tool_name: str,
    parameters: Any = None,
    *,
    text: str = "",
    known: bool | None = None,
    persist: bool = True,
    edition: str | None = None,
) -> dict[str, Any]:
    """Score a tool action. Never blocks the tool."""
    name = (tool_name or "").strip()
    params = parameters if isinstance(parameters, dict) else {}
    if known is None:
        known = _tool_is_known(name)
    score = 0.82 if known else 0.28
    if not name:
        score = 0.1
    if name in {"shell_execute", "env_set"} and not params.get("pin"):
        score = min(score, 0.4)
    if known and not params and name not in {"check_email", "get_services_health", "get_current_job"}:
        score = min(score, 0.58)
    if text and is_link_or_article_message(text) and name in {
        "create_quote", "create_estimate", "ingest_transcript", "send_email",
    }:
        score = min(score, 0.12)
    low = score < low_threshold()
    ed = process_edition(edition)
    record = {
        "kind": "tool",
        "text": (text or "")[:500],
        "chosen_path": name or "unknown_tool",
        "best_path": name if known else "ask_clarify",
        "score": round(float(score), 3),
        "scores": {"tool": round(float(score), 3)},
        "would_gate": bool(low),
        "gated_action": f"Ask: do you want me to run {name or 'that tool'}?" if low else "",
        "edition": ed,
        "family_flag": bool(is_juan_camilo_edition(ed) and low),
        "mode": gate_mode(),
        "correction": False,
        "behavior_changed": False,
        "context": {"known": bool(known), "param_keys": sorted(str(k) for k in params.keys())[:12]},
    }
    if persist and is_enabled():
        _store(record)
        _log_event(record)
    return record


def record_whatsapp_route(text: str, chosen_path: str, **kw: Any) -> dict[str, Any]:
    """Shadow hook for default_text_handler. Fail-open."""
    try:
        return score_intent(text, chosen_path=chosen_path, **kw)
    except Exception:
        logger.warning("confidence intent score failed", exc_info=True)
        return {"score": 0.0, "would_gate": False, "behavior_changed": False, "error": True}


def record_tool_action(tool_name: str, parameters: Any = None, **kw: Any) -> dict[str, Any]:
    try:
        return score_tool(tool_name, parameters, **kw)
    except Exception:
        logger.warning("confidence tool score failed", exc_info=True)
        return {"score": 0.0, "would_gate": False, "behavior_changed": False, "error": True}


def mark_correction(text: str = "", edition: str | None = None) -> None:
    """Founder frustration/edit: attach a correction to the latest intent event."""
    if not is_enabled():
        return
    try:
        with _db() as conn:
            row = conn.execute(
                """SELECT id FROM confidence_events
                   WHERE kind='intent' ORDER BY id DESC LIMIT 1"""
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE confidence_events SET correction=1 WHERE id=?",
                    (row["id"],),
                )
        if text:
            score_intent(text, chosen_path="frustration_reread", edition=edition, correction=True)
    except Exception:
        logger.warning("confidence correction mark failed", exc_info=True)


def week_report(days: int = 7) -> dict[str, Any]:
    days = max(1, min(int(days or 7), 90))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    with _db() as conn:
        rows = [dict(r) for r in conn.execute(
            "SELECT * FROM confidence_events WHERE created_at>=? ORDER BY id DESC",
            (cutoff,),
        ).fetchall()]
    n = len(rows)
    low = [r for r in rows if r.get("would_gate")]
    corrections = [r for r in rows if r.get("correction")]
    family = [r for r in rows if r.get("family_flag")]
    by_path: dict[str, list[float]] = {}
    for r in rows:
        by_path.setdefault(r.get("chosen_path") or "unknown", []).append(float(r.get("score") or 0))
    paths = {
        path: {
            "count": len(vals),
            "avg_score": round(sum(vals) / len(vals), 3) if vals else 0,
            "low": sum(1 for v in vals if v < low_threshold()),
        }
        for path, vals in sorted(by_path.items())
    }
    return {
        "days": days,
        "mode": gate_mode(),
        "behavior_changed": False,
        "total": n,
        "low_confidence": len(low),
        "corrections": len(corrections),
        "family_low_flagged": len(family),
        "avg_score": round(sum(float(r.get("score") or 0) for r in rows) / n, 3) if n else 0,
        "paths": paths,
        "threshold": low_threshold(),
        "note": (
            "Shadow mode: scores vs founder corrections (frustration/edits). "
            "Validate here before enabling a real gate. No auto-credits."
        ),
    }


def _store(record: dict[str, Any]) -> int:
    with _db() as conn:
        cur = conn.execute(
            """INSERT INTO confidence_events (
                created_at, kind, chosen_path, best_path, score, scores_json,
                would_gate, gated_action, edition, family_flag, mode, text,
                context_json, correction, improvement_id
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                _now(),
                record.get("kind") or "intent",
                record.get("chosen_path"),
                record.get("best_path"),
                float(record.get("score") or 0),
                json.dumps(record.get("scores") or {}),
                1 if record.get("would_gate") else 0,
                (record.get("gated_action") or "")[:240],
                record.get("edition") or "main",
                1 if record.get("family_flag") else 0,
                record.get("mode") or gate_mode(),
                (record.get("text") or "")[:500],
                json.dumps(record.get("context") or record.get("model_nudge") or {}),
                1 if record.get("correction") else 0,
                record.get("improvement_id"),
            ),
        )
        return int(cur.lastrowid)


def _log_event(record: dict[str, Any]) -> None:
    extra = " FAMILY_LOW" if record.get("family_flag") else ""
    logger.info(
        "confidence%s kind=%s chosen=%s best=%s score=%.3f would_gate=%s gated=%r edition=%s mode=%s",
        extra,
        record.get("kind"),
        record.get("chosen_path"),
        record.get("best_path"),
        float(record.get("score") or 0),
        record.get("would_gate"),
        record.get("gated_action") or "",
        record.get("edition"),
        record.get("mode"),
    )


def _tool_is_known(name: str) -> bool:
    if not name:
        return False
    try:
        from app.services.max.tool_executor import TOOL_REGISTRY

        return name in TOOL_REGISTRY
    except Exception:
        return False


def _dedupe_key(record: dict[str, Any]) -> str:
    raw = f"{record.get('kind')}|{record.get('chosen_path')}|{record.get('best_path')}|{(record.get('text') or '')[:80]}"
    return hashlib.sha256(raw.encode("utf-8", errors="replace")).hexdigest()[:16]


def feed_low_scores_to_improvements(days: int = 7) -> list[dict[str, Any]]:
    """File unique low-score events as proposed fixes. Never approves or merges."""
    if (os.getenv("MAX_CONFIDENCE_FEED_IMPROVEMENTS") or "1").strip().lower() in {"0", "false", "off", "no"}:
        return []
    days = max(1, min(int(days or 7), 90))
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%dT%H:%M:%SZ")
    filed: list[dict[str, Any]] = []
    try:
        from app.services.max import improvements as imp
    except Exception:
        logger.info("confidence improvement feed skipped: improvements unavailable")
        return []
    with _db() as conn:
        rows = [dict(r) for r in conn.execute(
            """SELECT * FROM confidence_events
               WHERE would_gate=1 AND created_at>=? AND improvement_id IS NULL
               ORDER BY id DESC""",
            (cutoff,),
        ).fetchall()]
    seen: set[str] = set()
    for row in rows:
        key = _dedupe_key({
            "kind": row.get("kind"),
            "chosen_path": row.get("chosen_path"),
            "best_path": row.get("best_path"),
            "text": row.get("text"),
        })
        if key in seen:
            continue
        seen.add(key)
        try:
            created = imp.create_request(
                title=f"Low-confidence {row.get('kind')}: {row.get('chosen_path')} vs {row.get('best_path')}"[:200],
                problem=(
                    f"Shadow confidence scored {row.get('score')} for path "
                    f"{row.get('chosen_path')} (heuristics preferred {row.get('best_path')}). "
                    f"Text: {(row.get('text') or '')[:400]}"
                ),
                proposed_change=(
                    "Review routing heuristics. If the founder later corrects this class of turn, "
                    "tighten the rules. Do not merge or deploy from this candidate."
                ),
                affected_modules=["whatsapp_channel", "confidence", "tool_executor"],
                risk="low",
                acceptance="Routing matches founder intent; no $0 estimates from link-only messages.",
                requested_via="confidence",
                requested_text=key,
                kind="fix",
            )
            if created.get("status") != "proposed":
                logger.warning("confidence feed unexpected status=%s", created.get("status"))
            with _db() as conn:
                conn.execute(
                    "UPDATE confidence_events SET improvement_id=? WHERE id=?",
                    (created.get("id"), row["id"]),
                )
            filed.append({"event_id": row["id"], "improvement_id": created.get("id"), "status": created.get("status")})
        except Exception:
            logger.info("confidence improvement feed skipped for event %s", row.get("id"), exc_info=True)
    return filed
