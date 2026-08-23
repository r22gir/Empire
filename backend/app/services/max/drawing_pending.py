"""Sprint 1d Phase A Fix #2 — Pending drawing-job state.

Persists across chat turns so the founder's reply to a missing_dims
question re-enters the drawing flow with the founder-supplied dims.

Schema is created idempotently at import time. Rows expire after
TTL_HOURS (swept on every ensure_table call — no separate cron needed).

Scoped resume-match: only treat the next turn as a continuation reply if
it plausibly answers the pending question (contains a dim-keyword OR
mentions one of the missing keys explicitly). Otherwise the pending job
stays parked for a future real answer.
"""
import json
import os
import re
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any, Optional


DB_PATH = os.getenv("EMPIRE_TASK_DB") or os.path.expanduser("~/empire-data/empire.db")
TTL_HOURS = 24

# Cancel keywords — if a founder reply contains any of these, drop the
# pending job entirely AND skip the drawing flow on this turn.
CANCEL_PATTERNS = re.compile(
    r"\b(cancel|discard|nevermind|stop drawing|abort|forget it|drop it)\b",
    re.IGNORECASE,
)

# Dim-keyword tokens — if a founder reply contains at least one of
# these, it counts as a continuation reply and the pending job merges dims.
DIM_KEYWORDS = re.compile(
    r"\b(width|height|depth|length|drop|diameter|dia|"
    r"seat_height|seat height|seat h|"
    r"back_height|back height|back h|"
    r"head_height|headboard height|"
    r"overall_height|overall_width|"
    r"return|reveal|channel|fold|gather|stack|fullness|"
    r"armrest|panel|rail|rod|pocket)\b",
    re.IGNORECASE,
)


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def ensure_table() -> None:
    """Create pending_drawing_jobs + sweep rows older than TTL_HOURS."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS pending_drawing_jobs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                channel TEXT NOT NULL,
                handoff_json TEXT NOT NULL,
                missing_json TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now')),
                UNIQUE(conversation_id, channel)
            );
            CREATE INDEX IF NOT EXISTS idx_pending_jobs_age
                ON pending_drawing_jobs(created_at);
        """)
        cutoff = (datetime.now(timezone.utc) - timedelta(hours=TTL_HOURS)).isoformat()
        conn.execute(
            "DELETE FROM pending_drawing_jobs WHERE created_at < ?", (cutoff,)
        )
        conn.commit()


def set_pending(conversation_id: str, channel: str, handoff: dict) -> None:
    with _connect() as conn:
        conn.execute("""
            INSERT INTO pending_drawing_jobs
                (conversation_id, channel, handoff_json, missing_json, created_at, updated_at)
            VALUES (?, ?, ?, ?, datetime('now'), datetime('now'))
            ON CONFLICT(conversation_id, channel) DO UPDATE SET
                handoff_json = excluded.handoff_json,
                missing_json = excluded.missing_json,
                updated_at = datetime('now')
        """, (
            conversation_id, channel,
            json.dumps(handoff, default=str),
            json.dumps(handoff.get("missing", [])),
        ))
        conn.commit()


def get_pending(conversation_id: str, channel: str) -> Optional[dict]:
    """Return pending snapshot or None. Returns None if absent OR expired."""
    ensure_table()
    with _connect() as conn:
        row = conn.execute("""
            SELECT handoff_json FROM pending_drawing_jobs
            WHERE conversation_id = ? AND channel = ?
        """, (conversation_id, channel)).fetchone()
        if not row:
            return None
        try:
            return json.loads(row["handoff_json"])
        except (json.JSONDecodeError, TypeError):
            return None


def clear_pending(conversation_id: str, channel: str) -> None:
    with _connect() as conn:
        conn.execute(
            "DELETE FROM pending_drawing_jobs WHERE conversation_id = ? AND channel = ?",
            (conversation_id, channel),
        )
        conn.commit()


def is_cancel_message(text: str) -> bool:
    return bool(CANCEL_PATTERNS.search(text or ""))


# NOTE: an earlier, narrower definition of is_continuation_reply
# lived above this line (used DIM_KEYWORDS only). The active
# definition below uses the _SYNONYMS table and supersedes it. The
# dead copy was removed in PHASE 2 · R12 corrected Option A so the
# next reader is not misled by a redefinition that Python silently
# overwrites at import time.

# Synonym map — founder often says "wide" not "width", "tall" not
# "height", "deep" not "depth". The merger and continuation-match
# both look up the canonical key from any of its synonyms.
_SYNONYMS = {
    "width":  ["width", "wide", "w", "across"],
    "depth":  ["depth", "deep", "d", "front-to-back"],
    "length": ["length", "long", "l", "drop"],
    "height": ["height", "high", "h", "tall"],
    "seat_height":   ["seat_height", "seat height", "seat_h", "seat h"],
    "back_height":   ["back_height", "back height", "back_h", "back h"],
    "head_height":   ["head_height", "headboard height", "headboard_h"],
    "drop":   ["drop", "length", "long"],
    "return": ["return", "returns", "depth"],
    "diameter": ["diameter", "dia"],
}
_DIM_PATTERN = lambda key: r"(?:" + "|".join(re.escape(s) for s in _SYNONYMS.get(key, [key])) + r")"


def _match_dim(text: str, key: str):
    """Return first numeric match in `text` that pairs with any of `key`'s
    synonyms, in either order. Tolerates "dim 17", "dim=17", "dim: 17",
    "17 dim", "17=dim". Returns None if nothing matches.
    """
    t = text or ""
    pat = _DIM_PATTERN(key)
    sep = r"\s*[:=]?\s*"  # optional separator (=, :, or just whitespace)
    # dim → number
    # R12.1 — the value token may include whitespace (e.g.
    # "69 1/2") or hyphen (e.g. "69-1/2") or a feet-inches form.
    # Capture the raw token then route through the central
    # _parse_dimension_value (defined in drawing_intent).) Returns
    # None on anything unparseable so the missing-key path
    # surfaces instead of a silent bogus float.
    # Pre-fix: this regex captured `[\d./]+` which matched "2"
    # in "69 1/2" (the digit after the slash), silently
    # producing width=2 from the founder's typed input.
    m = re.search(rf"\b({pat}){sep}([\d\s./-]+)\b", t, re.IGNORECASE)
    if m:
        from app.services.max.drawing_intent import _parse_dimension_value
        inches = _parse_dimension_value(m.group(2))
        if inches is not None:
            # :g strips trailing zeros — 87.0 → "87", 69.5 stays.
            return f'{inches:g}"'
    # number → dim
    m2 = re.search(rf"\b([\d\s./-]+){sep}({pat})\b", t, re.IGNORECASE)
    if m2:
        from app.services.max.drawing_intent import _parse_dimension_value
        inches = _parse_dimension_value(m2.group(1))
        if inches is not None:
            return f'{inches:g}"'
    return None


def merge_founder_reply(snapshot: dict, reply: str) -> dict:
    """Pull <value><dim-synonym> or <dim-synonym><value> from reply."""
    out = dict(snapshot)
    out["dimensions"] = dict(snapshot.get("dimensions") or {})
    for key in list(out["dimensions"].keys()):
        val = _match_dim(reply or "", key)
        if val is not None:
            out["dimensions"][key] = val
    # Re-derive missing list by intersecting with required_keys.
    required = snapshot.get("required_keys") or []
    out["missing"] = [k for k in required if not out["dimensions"].get(k)]
    return out


def is_continuation_reply(text: str, missing_keys: list) -> bool:
    """Scoped resume-match: only treat the next turn as continuation if
    it plausibly answers the pending question. Contains a dim-synonym OR
    mentions one of the missing keys directly.
    """
    if not text:
        return False
    lower = text.lower()
    # Dim-synonym match (broader than just the keyword list)
    if missing_keys:
        for key in missing_keys:
            for syn in _SYNONYMS.get(key, [key]):
                if re.search(rf"\b{re.escape(syn)}\b", lower, re.IGNORECASE):
                    return True
    # Fallback: numeric + any dim keyword (rough signal)
    if DIM_KEYWORDS.search(text):
        return True
    # Mention missing key directly
    if missing_keys:
        for key in missing_keys:
            syn = key.replace("_", " ")
            if key in lower or syn in lower:
                return True
    return False


# PHASE 2 · R12 corrected Option A — pure continuation guard.
# The pending-table path is dead architecture (set_pending requires
# both `missing` and `tool_payload` to be truthy — mutually
# exclusive in build_drawing_handoff). This helper reads the last
# few assistant turns directly from chat history and detects
# whether the current message is supplying values for a recently
# missing drawing-router turn. Returns a context dict
# {b1_product_type, missing_keys} when the guard fires; None
# otherwise. Pure — no I/O, no state.
def looks_like_continuation(text: str, history) -> "dict | None":
    """Detect a continuation reply via chat-history context.

    Pure function. Returns {"b1_product_type": str,
    "missing_keys": list[str]} when the message plausibly answers a
    recent drawing-router missing-keys turn; otherwise None.

    The pattern matched in the assistant turn is the canonical
    missing-template response emitted by _drawing_render at
    router.py:393-407 ("I have the '<product_type>' product_type
    but I'm still missing: <keys>"). Parsing this string recovers
    both the B1 product_type and the template-required keys.
    """
    if not text or not history:
        return None
    try:
        # Walk the last few assistant turns. We stop at the first
        # matching turn so the most recent missing-keys context
        # wins (a new drawing intent overrides an older one).
        for turn in reversed(list(history)[-3:]):
            if not isinstance(turn, dict):
                continue
            if (turn.get("role") or "").lower() != "assistant":
                continue
            content = (turn.get("content") or "").strip()
            if not content:
                continue
            lower = content.lower()
            # The drawing-router missing-keys response carries the
            # exact phrase "I'm still missing: <key1>, <key2>, ..."
            # — see _drawing_render's ready=False branch.
            m = re.search(
                r"i have the ['\"]?([a-z_]+)['\"]? product_type.*?"
                r"still missing[:\s]+([^\n.]+)",
                lower,
                re.IGNORECASE | re.DOTALL,
            )
            if not m:
                # Not a missing-keys drawing-router turn. If the
                # assistant turn is unrelated (no "missing" / no
                # "product_type"), stop scanning — we don't want
                # to pick up stale context from earlier turns.
                if "missing" not in lower and "product_type" not in lower:
                    return None
                continue
            product_type = m.group(1).strip()
            missing_str = m.group(2).rstrip(",. ").strip()
            missing_keys = [k.strip().rstrip(",") for k in missing_str.split(",") if k.strip()]
            if not product_type or not missing_keys:
                return None
            if not is_continuation_reply(text, missing_keys):
                return None
            return {
                "b1_product_type": product_type,
                "missing_keys": missing_keys,
            }
    except Exception:
        return None
    return None


ensure_table()  # always migrate + sweep on import
