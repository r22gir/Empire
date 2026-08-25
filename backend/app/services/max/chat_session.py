"""Chat session memory — preserves prior-turn tool_results across requests.

PHASE 2 · F1 (H48 fix). The chat/stream handlers rebuild the model's
message context from ``request.history`` only — the ``tool_results`` field
from previous turns is dropped at router.py:2366 and :3132. This module
gives the server a side-channel: store the full tool_results per turn,
and let the next request re-inject them into the messages array so the
model can see what previous turns actually observed.

Windowing:
  - RETAIN_TURNS = 10 (matches the route history window)
  - REPLAY_TURNS = 3  (full-data replay; older turns are summarized)

Storage: SQLite table ``chat_session_turns`` keyed by
``(conversation_id, turn_index)``. Uses the same DB path as the rest of
the MAX services (see ``drawing_pending.py`` for the established pattern).
"""
from __future__ import annotations

import json
import logging
import os
import sqlite3
from typing import Any, Optional

logger = logging.getLogger("max.chat_session")

# D28 2c-1 — per-call resolution of the DB path.
#
# Same defect class as code_task_persistence.py:54 had pre-fix.
# Module-level capture of DB_PATH defeats the test fixture (pytest
# collection imports test files BEFORE session-scope fixtures run).
# During collection, EMPIRE_TASK_DB is unset, so DB_PATH binds to
# the prod fallback. The chat_session_turns table then tries to
# open prod from the test process — fails with
# sqlite3.OperationalError: unable to open database file, which
# surfaced in the STEP 2b probe as 16 cascading failures in
# test_code_task_persistence.py.
#
# Fix mirrors 2b-1 exactly:
#   - _resolved_db_path() reads EMPIRE_TASK_DB at CALL TIME, every
#     call. The fixture's env-var flip is honoured the moment it
#     lands, regardless of import order.
#   - DB_PATH retained as a read-only fallback constant for
#     monkeypatchability (a second pattern for the same defect is
#     worse than either pattern alone).
#   - _connect() routes through _resolved_db_path(). No reader in
#     this module touches DB_PATH directly any more.
DEFAULT_DB_PATH = os.path.expanduser("~/empire-data/empire.db")
# Backwards-compat alias.
DB_PATH = DEFAULT_DB_PATH


def _resolved_db_path() -> str:
    """Read EMPIRE_TASK_DB at call time. Per-call, never captured."""
    return os.getenv("EMPIRE_TASK_DB") or DB_PATH


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_resolved_db_path())
    conn.row_factory = sqlite3.Row
    return conn


RETAIN_TURNS = 10   # how many recent turns to keep before TTL sweep
REPLAY_TURNS = 3    # how many recent turns get full replay in the next request


def ensure_table() -> None:
    """Create chat_session_turns and prune beyond RETAIN_TURNS per conversation."""
    with _connect() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS chat_session_turns (
                conversation_id TEXT NOT NULL,
                turn_index INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                tool_results_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (conversation_id, turn_index)
            );
            CREATE INDEX IF NOT EXISTS idx_chat_session_conv
                ON chat_session_turns(conversation_id, turn_index);
        """)
        conn.commit()


def _next_turn_index(conversation_id: str) -> int:
    """Return the next turn_index for this conversation (0-based)."""
    with _connect() as conn:
        row = conn.execute(
            "SELECT COALESCE(MAX(turn_index), -1) AS m FROM chat_session_turns WHERE conversation_id = ?",
            (conversation_id,),
        ).fetchone()
        return int(row["m"]) + 1


def record_turn(
    conversation_id: Optional[str],
    role: str,
    content: str,
    tool_results: Optional[list[dict]] = None,
) -> None:
    """Persist one turn (user or assistant) keyed by conversation_id.

    Append-only. The next record_turn for the same conversation_id gets
    the next turn_index so we keep a per-conversation timeline.
    """
    if not conversation_id:
        return
    ensure_table()
    tool_results = tool_results or []
    # Strip None and unserializable entries; item-aware truncation at 12KB
    # (PHASE 2 · F5.3 H49): never cut mid-array. Cap raised from 8KB to
    # 12KB so a 6-item quote (with full metadata per item) fits whole.
    sanitized: list[dict] = []
    for entry in tool_results:
        if not isinstance(entry, dict):
            continue
        try:
            blob = json.dumps(entry, default=str)
        except Exception:
            blob = "{}"
        if len(blob) > 12288:
            blob = _maybe_truncate_at_array_boundary(blob, max_chars=12288)
        sanitized.append({**entry, "result_preview": blob})
    index = _next_turn_index(conversation_id)
    with _connect() as conn:
        conn.execute(
            """
            INSERT OR REPLACE INTO chat_session_turns
                (conversation_id, turn_index, role, content, tool_results_json, created_at)
            VALUES (?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                conversation_id,
                index,
                role,
                content[:20000],  # cap content length
                json.dumps(sanitized, default=str),
            ),
        )
        conn.commit()
    _sweep(conversation_id)


def _sweep(conversation_id: str) -> None:
    """Trim to the last RETAIN_TURNS for this conversation."""
    with _connect() as conn:
        conn.execute(
            """
            DELETE FROM chat_session_turns
            WHERE conversation_id = ?
              AND turn_index < (
                SELECT MAX(turn_index) - ? FROM chat_session_turns WHERE conversation_id = ?
              )
            """,
            (conversation_id, RETAIN_TURNS - 1, conversation_id),
        )
        conn.commit()


def load_recent_turns(
    conversation_id: Optional[str],
    max_turns: int = REPLAY_TURNS,
) -> list[dict]:
    """Return the most recent ``max_turns`` for replay.

    Each entry is a dict with role, content, tool_results (list). Empty
    list if conversation_id is missing or no rows.
    """
    if not conversation_id:
        return []
    ensure_table()
    with _connect() as conn:
        rows = conn.execute(
            """
            SELECT turn_index, role, content, tool_results_json
            FROM chat_session_turns
            WHERE conversation_id = ?
            ORDER BY turn_index DESC
            LIMIT ?
            """,
            (conversation_id, max_turns),
        ).fetchall()
    out: list[dict] = []
    for r in rows:
        try:
            tool_results = json.loads(r["tool_results_json"] or "[]")
        except Exception:
            tool_results = []
        out.append(
            {
                "turn_index": int(r["turn_index"]),
                "role": r["role"],
                "content": r["content"],
                "tool_results": tool_results,
            }
        )
    return list(reversed(out))  # oldest-first → newest-last


def summarize_tool_results(tool_results: list[dict]) -> str:
    """Compact one-line summary of a turn's tool_results (used when over budget)."""
    if not tool_results:
        return "(no tool calls)"
    parts = []
    for tr in tool_results:
        tool = tr.get("tool", "?")
        success = tr.get("success", False)
        result = tr.get("result")
        if isinstance(result, dict):
            keys = list(result.keys())[:3]
            keys_str = "{" + ", ".join(keys) + ("…" if len(result) > 3 else "") + "}"
        elif isinstance(result, list):
            keys_str = f"[{len(result)} items]"
        else:
            keys_str = "(scalar)"
        parts.append(f"{tool} {'OK' if success else 'FAIL'} {keys_str}")
    return "; ".join(parts)


def _maybe_truncate_at_array_boundary(preview: str, max_chars: int = 1500) -> str:
    """Truncate a JSON preview at an item boundary when possible.

    The pre-F5.3 truncation cut at a fixed char count, which would
    slice mid-array (e.g. returning only the first `line_items` entry
    of a 6-item quote). The model then lost items 2–6. This is
    item-aware: when the JSON has recognizable item separators
    (`, {` from json.dumps default), we cut at the LAST item
    boundary before the cap so items are never cut mid-record.

    Strategy (best-effort, never raises):
      1. If preview is short enough, return as-is.
      2. Otherwise, find the LAST `, {` (item separator) before the
         cap. Cut there and add a hint.
      3. Count items kept vs total so the model can see "N more
         items truncated" rather than guessing.
      4. If no separator found, fall back to the hard cap.
    """
    if len(preview) <= max_chars:
        return preview
    cut = preview[:max_chars]
    # json.dumps default separator is `, ` (comma + space). Item
    # boundaries in a list of dicts look like `}, {`. We find the
    # LAST `, {` before the cap so we keep complete items.
    sep_idx = cut.rfind(", {")
    if sep_idx > 0:
        # Keep up to and including the `}` BEFORE the separator.
        # The `},{` pattern contains the `}` of the previous item.
        end_idx = sep_idx + 1  # cut AT the comma (keep `}`)
        kept = preview[:end_idx]
        # Count items in the kept prefix.
        # Items in JSON are between `[{` and `}]`; each item except
        # the first is preceded by `, {`.
        kept_items = kept.count(", {") + (1 if "[{" in kept else 0)
        total_items = preview.count(", {") + (1 if "[{" in preview else 0)
        if total_items > kept_items:
            return f"{kept} …[{total_items - kept_items} more items truncated]"
        return f"{kept} …[truncated]"
    return cut + "…[truncated]"


def format_replay_block(recent_turns: list[dict]) -> str:
    """Format a system-style block the model can read to recall prior tool evidence.

    Returns an empty string if there's nothing to replay. The block is
    sized to stay within ~3000 tokens; per-turn tool result JSON is
    capped at 1.5KB. The 1.5KB cap is item-aware (PHASE 2 · F5.3
    H49): we cut at the LAST top-level array close when possible so
    a 6-item quote returns the full line_items array rather than
    cutting mid-array at item 1.

    H53 FIX (2026-08-19): When NO turn in `recent_turns` carries
    any tool_results, the block is NOT emitted at all — even the
    "[SYSTEM: ...]" header line. Absence must look like absence
    (MAX's correct prior refusal was driven by seeing a header line
    with nothing under it; that is the empty-frame failure class).
    """
    if not recent_turns:
        return ""
    # First pass — does ANY turn have tool_results?
    has_any_tool_results = any(
        turn.get("tool_results") for turn in recent_turns
    )
    if not has_any_tool_results:
        # No tool evidence in any prior turn — render nothing.
        # The model has no claim to prior verification; fabricating
        # a "here are your tool results" header with nothing under
        # it would be a prompt-injection shape.
        return ""
    lines = [
        "[SYSTEM: Prior-turn tool results — you saw these in previous turns. "
        "Use them when the user asks about previous verification. Do NOT claim "
        "you saw a tool result that does not appear below. If a tool result is "
        "absent, say so honestly.]"
    ]
    for turn in recent_turns:
        ti = turn.get("turn_index", "?")
        role = turn.get("role", "?")
        # Content preview (first 200 chars) so the model can match tool to intent
        content_preview = (turn.get("content") or "")[:200].replace("\n", " ")
        if len(turn.get("content") or "") > 200:
            content_preview += "…"
        tool_results = turn.get("tool_results") or []
        if not tool_results:
            continue
        lines.append(f"\nTurn {ti} [{role}]: {content_preview}")
        for tr in tool_results:
            tool = tr.get("tool", "?")
            success = tr.get("success", False)
            preview = tr.get("result_preview", "{}")
            # PHASE 2 · F5.3 H49 — item-aware truncation: never cut mid-array.
            # Cap raised to 12KB so a 6-line quote (with full metadata
            # per item) fits whole; larger quotes get item-aware truncation.
            preview = _maybe_truncate_at_array_boundary(preview, max_chars=12288)
            status = "OK" if success else "FAIL"
            err = tr.get("error")
            extra = f" error={err!r}" if err else ""
            lines.append(f"  - {tool} [{status}{extra}]: {preview}")
    return "\n".join(lines)


ensure_table()  # idempotent migration on import
