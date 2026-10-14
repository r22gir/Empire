"""Shadow-mode confidence scorer + optional answer cascade for Max.

Default / unset MAX_CONFIDENCE_GATE=shadow: score and log, never change
behavior. Gate on: low-confidence answers escalate (retry with a stronger
local reasoning/tool check, then ask the founder). High-confidence answers
proceed. Optional included-model nudge only when quota remains (no
auto-credits). Low-score cases can be filed as proposed improvements
(draft only — never approved).

Never sends email or WhatsApp. Founder ask is in-reply text plus an
optional founder_inbox row. Tests must set EMPIRE_DATA_DIR / EMPIRE_TASK_DB
to temp paths.
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
from logging.handlers import RotatingFileHandler
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
_FILE_MARKER = "_empire_confidence_file"

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

CASCADE_PROCEED = "proceed"
CASCADE_RETRY = "retry"
CASCADE_ASK_FOUNDER = "ask_founder"

_HEDGE_RE = re.compile(
    r"\b(?:I think|probably|might be|I['’]m not sure|I believe|possibly|"
    r"it seems|I['’]m guessing|not certain|could be)\b",
    re.IGNORECASE,
)

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


def cascade_enabled() -> bool:
    """True only when the founder turned the real gate on. Unset is shadow."""
    return gate_mode() == "on"


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


def log_path() -> Path:
    override = (os.getenv("MAX_CONFIDENCE_LOG") or "").strip()
    if override:
        return Path(override)
    return data_root() / "logs" / "confidence.log"


def ensure_confidence_file_logging() -> Path:
    """Rotating file + journald (propagate). Never logs tokens."""
    dest = log_path()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest_key = str(dest.resolve()) if dest.parent.exists() else str(dest)
    already = False
    for handler in logger.handlers:
        if getattr(handler, _FILE_MARKER, False) and getattr(handler, "baseFilename", "") == dest_key:
            already = True
            break
    if not already:
        handler = RotatingFileHandler(
            dest, maxBytes=5 * 1024 * 1024, backupCount=7, encoding="utf-8",
        )
        handler.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s",
            datefmt="%Y-%m-%dT%H:%M:%S%z",
        ))
        setattr(handler, _FILE_MARKER, True)
        logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    logger.propagate = True
    return dest


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
        try:
            ensure_confidence_file_logging()
        except Exception:
            pass
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
        try:
            ensure_confidence_file_logging()
        except Exception:
            pass
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


def _tool_entries(tool_results: Any) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for item in tool_results or []:
        if isinstance(item, dict):
            entries.append(item)
            continue
        entries.append({
            "tool": getattr(item, "tool", None),
            "success": getattr(item, "success", None),
            "error": getattr(item, "error", None),
        })
    return entries


def _answer_quality_score(answer: str, tool_results: Any = None) -> float:
    raw = (answer or "").strip()
    if not raw:
        return 0.12
    score = 0.78
    hedges = len(_HEDGE_RE.findall(raw))
    if hedges:
        score -= min(0.36, 0.12 * hedges)
    if len(raw) < 20:
        score = min(score, 0.48)
    entries = _tool_entries(tool_results)
    if entries:
        fails = [row for row in entries if row.get("success") is False]
        oks = [row for row in entries if row.get("success") is True]
        if fails and not oks:
            score = min(score, 0.30)
        elif oks and not fails:
            score = max(score, 0.80)
        elif fails:
            score = min(score, 0.50)
    return max(0.05, min(0.98, score))


def score_answer(
    text: str,
    answer: str,
    *,
    chosen_path: str | None = None,
    tool_results: Any = None,
    edition: str | None = None,
    requester: str | None = None,
    persist: bool = True,
    correction: bool = False,
) -> dict[str, Any]:
    """Score a finished reply. Does not change the answer."""
    intent = score_intent(
        text,
        chosen_path=chosen_path,
        edition=edition,
        requester=requester,
        persist=False,
        correction=correction,
    )
    ans_score = _answer_quality_score(answer, tool_results)
    score = min(float(intent.get("score") or 0), ans_score)
    low = score < low_threshold()
    record = {
        **intent,
        "kind": "answer",
        "score": round(score, 3),
        "answer_score": round(ans_score, 3),
        "would_gate": bool(low),
        "gated_action": intent.get("gated_action") or (
            clarifying_question(
                str(intent.get("chosen_path") or "other"),
                intent.get("scores") or heuristic_intent_scores(text),
                text,
            ) if low else ""
        ),
        "behavior_changed": False,
        "context": {
            "answer_score": round(ans_score, 3),
            "tool_names": [
                str(row.get("tool") or "")
                for row in _tool_entries(tool_results)
                if row.get("tool")
            ][:12],
        },
    }
    if persist and is_enabled():
        try:
            ensure_confidence_file_logging()
        except Exception:
            pass
        _store(record)
        _log_event(record)
    return record


def decide_cascade(record: dict[str, Any] | None, *, attempt: int = 0) -> str:
    """Pure decision. Unset / shadow / off always proceed."""
    if not cascade_enabled():
        return CASCADE_PROCEED
    if not record or not record.get("would_gate"):
        return CASCADE_PROCEED
    if int(attempt or 0) <= 0:
        return CASCADE_RETRY
    return CASCADE_ASK_FOUNDER


def stronger_check(
    text: str,
    answer: str,
    record: dict[str, Any] | None = None,
    tool_results: Any = None,
) -> dict[str, Any]:
    """One local retry: tool evidence + quality gate + quota-safe nudge.

    Never calls a live model unless MAX_CONFIDENCE_MODEL_CHECK is on and
    MiniMax quota remains. Never spends auto-credits. Never sends.
    """
    base = record or {}
    nudge = optional_model_nudge(text, base.get("scores") or heuristic_intent_scores(text))
    quality_level = ""
    try:
        from app.services.max.quality_gate import validate_response

        quality_level = str(
            getattr(validate_response(answer or "", tool_results=tool_results or []), "level", "")
            or ""
        ).lower()
    except Exception:
        quality_level = ""
    retry_record = score_answer(
        text,
        answer,
        chosen_path=base.get("chosen_path"),
        tool_results=tool_results,
        edition=base.get("edition"),
        persist=False,
    )
    aligned = retry_record.get("chosen_path") == retry_record.get("best_path")
    if quality_level in {"verified", "high"} and aligned and float(retry_record.get("score") or 0) < 0.72:
        retry_record = dict(retry_record)
        retry_record["score"] = round(max(float(retry_record.get("score") or 0), 0.72), 3)
        retry_record["would_gate"] = retry_record["score"] < low_threshold()
        retry_record["gated_action"] = "" if not retry_record["would_gate"] else retry_record.get("gated_action")
    return {
        "record": retry_record,
        "nudge": nudge,
        "quality_level": quality_level,
        "auto_credits": False,
        "answer": answer,
    }


def founder_ask_text(record: dict[str, Any] | None, text: str = "") -> str:
    """In-chat founder question. Never an email or WhatsApp send."""
    question = ((record or {}).get("gated_action") or "").strip()
    if not question:
        scores = (record or {}).get("scores") or heuristic_intent_scores(text)
        chosen = str((record or {}).get("chosen_path") or "other")
        question = clarifying_question(chosen, scores, text)
    return (
        "I need a call from you before I continue.\n\n"
        f"{question}"
    )


def _file_founder_ask(record: dict[str, Any], text: str = "") -> dict[str, Any] | None:
    """Local founder_inbox only. Fail-open. Never email / WhatsApp / Telegram."""
    try:
        from app.services.max.desks import founder_inbox

        key = _dedupe_key(record)
        return founder_inbox.add(
            task_id=f"conf-{key}",
            title=f"Max needs a call: {record.get('chosen_path') or 'answer'}",
            description=(
                f"{record.get('gated_action') or ''}\n"
                f"score={record.get('score')} chosen={record.get('chosen_path')} "
                f"best={record.get('best_path')}\n"
                f"{(text or record.get('text') or '')[:400]}"
            ),
            priority="high",
            reason="low_confidence_cascade",
            source="confidence_cascade",
        )
    except Exception:
        logger.info("confidence founder inbox file skipped", exc_info=True)
        return None


def apply_answer_cascade(
    text: str,
    answer: str,
    *,
    chosen_path: str | None = None,
    tool_results: Any = None,
    edition: str | None = None,
    requester: str | None = None,
    persist: bool = True,
    retry_fn: Any = None,
    ask_founder_fn: Any = None,
) -> dict[str, Any]:
    """Score a reply and, only when the gate is on, escalate low confidence.

    Unset / shadow / off: score_intent log only (today's shadow mode). The
    answer is returned unchanged. retry_fn / ask_founder_fn are never called.
    """
    mode = gate_mode()
    original = answer
    if mode != "on":
        record = score_intent(
            text,
            chosen_path=chosen_path,
            edition=edition,
            requester=requester,
            persist=persist,
        )
        return {
            "answer": original,
            "original_answer": original,
            "action": CASCADE_PROCEED,
            "behavior_changed": False,
            "retried": False,
            "asked_founder": False,
            "mode": mode,
            "score": record,
            "attempts": [record],
            "auto_credits": False,
            "founder_inbox": None,
        }

    record = score_answer(
        text,
        original,
        chosen_path=chosen_path,
        tool_results=tool_results,
        edition=edition,
        requester=requester,
        persist=persist,
    )
    result: dict[str, Any] = {
        "answer": original,
        "original_answer": original,
        "action": CASCADE_PROCEED,
        "behavior_changed": False,
        "retried": False,
        "asked_founder": False,
        "mode": mode,
        "score": record,
        "attempts": [record],
        "auto_credits": False,
        "founder_inbox": None,
    }
    if decide_cascade(record, attempt=0) != CASCADE_RETRY:
        if persist:
            _persist_cascade(result, text)
        return result

    retry_answer = original
    retry_record = record
    if retry_fn is not None:
        try:
            retry_answer = retry_fn(text, original, record, tool_results)
        except Exception:
            logger.info("confidence cascade retry_fn failed", exc_info=True)
            retry_answer = original
        retry_record = score_answer(
            text,
            retry_answer if isinstance(retry_answer, str) else original,
            chosen_path=chosen_path,
            tool_results=tool_results,
            edition=edition,
            requester=requester,
            persist=persist,
        )
    else:
        checked = stronger_check(text, original, record, tool_results)
        retry_record = checked.get("record") or record
        retry_answer = checked.get("answer") if isinstance(checked.get("answer"), str) else original
        result["auto_credits"] = False
        result["nudge"] = checked.get("nudge")
    result["retried"] = True
    result["attempts"].append(retry_record)
    result["score"] = retry_record

    if decide_cascade(retry_record, attempt=1) == CASCADE_PROCEED:
        changed = retry_answer != original
        result["answer"] = retry_answer
        result["action"] = CASCADE_PROCEED
        result["behavior_changed"] = bool(changed)
        if persist:
            _persist_cascade(result, text)
        return result

    question = founder_ask_text(retry_record, text)
    inbox = None
    if ask_founder_fn is not None:
        try:
            inbox = ask_founder_fn(retry_record, text, question)
        except Exception:
            logger.info("confidence cascade ask_founder_fn failed", exc_info=True)
    else:
        inbox = _file_founder_ask(retry_record, text)
    result["answer"] = question
    result["action"] = CASCADE_ASK_FOUNDER
    result["behavior_changed"] = True
    result["asked_founder"] = True
    result["founder_inbox"] = inbox
    if persist:
        _persist_cascade(result, text)
    return result


def apply_reply_cascade(
    user_text: str,
    answer: str,
    *,
    tool_results: Any = None,
    chosen_path: str | None = None,
    persist: bool = True,
) -> dict[str, Any]:
    """Shared /chat and /chat/stream entry. Fail-open wrapper."""
    try:
        return apply_answer_cascade(
            user_text,
            answer,
            chosen_path=chosen_path,
            tool_results=tool_results,
            persist=persist,
        )
    except Exception:
        logger.warning("confidence reply cascade failed", exc_info=True)
        return {
            "answer": answer,
            "original_answer": answer,
            "action": CASCADE_PROCEED,
            "behavior_changed": False,
            "retried": False,
            "asked_founder": False,
            "mode": gate_mode(),
            "score": {"score": 0.0, "would_gate": False, "error": True},
            "auto_credits": False,
            "error": True,
        }


def cascade_public_meta(hit: dict[str, Any] | None) -> dict[str, Any]:
    """Safe response-metadata subset. No message text, no tokens."""
    row = hit or {}
    score = row.get("score") if isinstance(row.get("score"), dict) else {}
    return {
        "mode": row.get("mode") or gate_mode(),
        "action": row.get("action") or CASCADE_PROCEED,
        "behavior_changed": bool(row.get("behavior_changed")),
        "would_gate": bool(score.get("would_gate")),
        "score": score.get("score"),
        "retried": bool(row.get("retried")),
        "asked_founder": bool(row.get("asked_founder")),
    }


def _persist_cascade(result: dict[str, Any], text: str) -> None:
    if not is_enabled():
        return
    score = result.get("score") if isinstance(result.get("score"), dict) else {}
    record = {
        "kind": "cascade",
        "text": (text or "")[:500],
        "chosen_path": score.get("chosen_path"),
        "best_path": score.get("best_path"),
        "score": float(score.get("score") or 0),
        "scores": score.get("scores") or {},
        "would_gate": bool(score.get("would_gate")),
        "gated_action": (score.get("gated_action") or "")[:240],
        "edition": score.get("edition") or process_edition(),
        "family_flag": bool(score.get("family_flag")),
        "mode": result.get("mode") or gate_mode(),
        "correction": False,
        "behavior_changed": bool(result.get("behavior_changed")),
        "context": {
            "cascade_action": result.get("action"),
            "behavior_changed": bool(result.get("behavior_changed")),
            "retried": bool(result.get("retried")),
            "asked_founder": bool(result.get("asked_founder")),
            "auto_credits": False,
        },
    }
    try:
        ensure_confidence_file_logging()
    except Exception:
        pass
    try:
        _store(record)
        _log_event(record)
    except Exception:
        logger.info("confidence cascade persist skipped", exc_info=True)


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
    cascade_changed = False
    cascade_asked = 0
    cascade_retried = 0
    for r in rows:
        ctx = {}
        raw_ctx = r.get("context_json")
        if raw_ctx:
            try:
                parsed = json.loads(raw_ctx)
                if isinstance(parsed, dict):
                    ctx = parsed
            except Exception:
                ctx = {}
        if ctx.get("behavior_changed"):
            cascade_changed = True
        if ctx.get("asked_founder"):
            cascade_asked += 1
        if ctx.get("retried"):
            cascade_retried += 1
    mode = gate_mode()
    return {
        "days": days,
        "mode": mode,
        "behavior_changed": bool(mode == "on" and cascade_changed),
        "total": n,
        "low_confidence": len(low),
        "unfiled_low": sum(1 for r in low if not r.get("improvement_id")),
        "corrections": len(corrections),
        "family_low_flagged": len(family),
        "cascade_asked_founder": cascade_asked,
        "cascade_retried": cascade_retried,
        "avg_score": round(sum(float(r.get("score") or 0) for r in rows) / n, 3) if n else 0,
        "paths": paths,
        "threshold": low_threshold(),
        "auto_credits": False,
        "note": (
            "Shadow mode: scores vs founder corrections (frustration/edits). "
            "Validate here before enabling a real gate. No auto-credits."
            if mode != "on"
            else (
                "Gate on: low-confidence answers retry once (local stronger "
                "check; no auto-credits) then ask the founder. High-confidence "
                "answers proceed."
            )
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
