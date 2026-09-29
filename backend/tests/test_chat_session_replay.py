"""PHASE 2 · F1 tests — chat_session.py + replay helper.

The H48 root was that router.py:2366 (chat) and :3132 (stream) only
passed ``{role, content}`` from request.history into the messages array,
silently dropping the ``tool_results`` field from previous turns. The
fix introduces a server-side session store
(``app.services.max.chat_session``) and a shared helper
(``app.routers.max.router._build_replay_messages``) used by both doors.

These tests cover the helper in isolation (no live backend needed) and
the windowing + sweep behavior of the session table.
"""
from __future__ import annotations

import json
import os

# Use the local AIMessage (app.services.max.ai_router) instead of
# langchain_core — that package is not installed in this repo. The
# AIMessage is a dataclass with `role` as a plain string, so role
# identity checks ("system" vs "user") work directly.
from app.services.max.ai_router import AIMessage


# Use the canonical DB path; the module under test already derives this
# from ``EMPIRE_TASK_DB`` or ``~/empire-data/empire.db``.
os.environ.setdefault("EMPIRE_TASK_DB", os.path.expanduser("~/empire-data/empire.db"))


def test_record_and_load_roundtrip():
    """record_turn + load_recent_turns returns the same data."""
    from app.services.max import chat_session

    conv = "test-roundtrip-001"
    # Clean any prior rows from previous test runs
    chat_session._connect().execute(
        "DELETE FROM chat_session_turns WHERE conversation_id = ?", (conv,)
    ).connection.commit()

    chat_session.record_turn(
        conv, "user", "search_quotes for status proposal", None
    )
    chat_session.record_turn(
        conv,
        "assistant",
        "Found 4 quotes: EST-2026-006, EST-2026-005, EST-2026-003, EST-2026-082-c9aa",
        [{"tool": "search_quotes", "success": True, "result": {"quotes": [{"id": "1", "quote_number": "EST-2026-006"}]}}],
    )

    recent = chat_session.load_recent_turns(conv, max_turns=3)
    assert len(recent) == 2, f"expected 2 turns, got {len(recent)}"
    assert recent[0]["role"] == "user"
    assert recent[1]["role"] == "assistant"
    assert recent[1]["tool_results"][0]["tool"] == "search_quotes"
    assert recent[1]["tool_results"][0]["result"]["quotes"][0]["quote_number"] == "EST-2026-006"


def test_replay_block_includes_tool_results():
    """format_replay_block emits a system-style block with the raw JSON."""
    from app.services.max import chat_session

    conv = "test-replay-block-001"
    chat_session._connect().execute(
        "DELETE FROM chat_session_turns WHERE conversation_id = ?", (conv,)
    ).connection.commit()

    chat_session.record_turn(
        conv, "user", "search_quotes for status proposal", None
    )
    chat_session.record_turn(
        conv,
        "assistant",
        "Found 4 quotes.",
        [{"tool": "search_quotes", "success": True, "result": {"quotes": [{"quote_number": "EST-2026-006"}]}}],
    )

    recent = chat_session.load_recent_turns(conv, max_turns=3)
    block = chat_session.format_replay_block(recent)

    assert "[SYSTEM: Prior-turn tool results" in block
    assert "search_quotes" in block
    assert "EST-2026-006" in block
    assert "OK" in block  # success status


def test_replay_block_handles_empty_history():
    """No prior turns → empty block (no leak)."""
    from app.services.max import chat_session

    block = chat_session.format_replay_block([])
    assert block == ""


def test_replay_block_marks_failures():
    """A failed tool result surfaces ``FAIL`` and the error string."""
    from app.services.max import chat_session

    conv = "test-fail-001"
    chat_session._connect().execute(
        "DELETE FROM chat_session_turns WHERE conversation_id = ?", (conv,)
    ).connection.commit()

    chat_session.record_turn(
        conv, "user", "search_quotes", None
    )
    chat_session.record_turn(
        conv,
        "assistant",
        "Sorry, search failed.",
        [{"tool": "search_quotes", "success": False, "error": "DB connection refused"}],
    )

    recent = chat_session.load_recent_turns(conv, max_turns=3)
    block = chat_session.format_replay_block(recent)
    assert "FAIL" in block
    assert "DB connection refused" in block


def test_sweep_caps_to_retain_turns():
    """Beyond RETAIN_TURNS, old rows are dropped."""
    from app.services.max import chat_session

    conv = "test-sweep-001"
    chat_session._connect().execute(
        "DELETE FROM chat_session_turns WHERE conversation_id = ?", (conv,)
    ).connection.commit()

    # Record well past RETAIN_TURNS
    for i in range(chat_session.RETAIN_TURNS + 5):
        chat_session.record_turn(conv, "user", f"msg {i}", None)
        chat_session.record_turn(conv, "assistant", f"reply {i}", None)

    rows = chat_session._connect().execute(
        "SELECT COUNT(*) AS c FROM chat_session_turns WHERE conversation_id = ?", (conv,)
    ).fetchone()["c"]
    assert rows <= chat_session.RETAIN_TURNS, f"expected <= {chat_session.RETAIN_TURNS}, got {rows}"


def test_load_recent_turns_clamps_to_max_turns():
    """load_recent_turns respects the max_turns argument."""
    from app.services.max import chat_session

    conv = "test-clamp-001"
    chat_session._connect().execute(
        "DELETE FROM chat_session_turns WHERE conversation_id = ?", (conv,)
    ).connection.commit()

    for i in range(8):
        chat_session.record_turn(conv, "user", f"m{i}", None)
        chat_session.record_turn(conv, "assistant", f"r{i}", None)

    recent = chat_session.load_recent_turns(conv, max_turns=2)
    assert len(recent) == 2


def test_build_replay_messages_includes_replay_block():
    """The shared helper used by both /chat and /chat/stream includes the
    prior-turn tool_results replay block, AND the current user message,
    in the order: history → replay block → current message."""
    # Build a minimal fake AIMessage substitute so we don't need the
    # router import (which would pull in the full backend).
    from app.services.max import chat_session

    conv = "test-helper-001"
    chat_session._connect().execute(
        "DELETE FROM chat_session_turns WHERE conversation_id = ?", (conv,)
    ).connection.commit()

    chat_session.record_turn(
        conv, "user", "search_quotes", None
    )
    chat_session.record_turn(
        conv, "assistant", "Found 4 quotes.",
        [{"tool": "search_quotes", "success": True, "result": {"quotes": [{"quote_number": "EST-2026-006"}]}}],
    )

    # Import the helper. It lives in router.py; we test it in isolation.
    from app.routers.max.router import _build_replay_messages

    windowed_history = [
        {"role": "user", "content": "search_quotes"},
        {"role": "assistant", "content": "Found 4 quotes."},
    ]
    messages = _build_replay_messages(
        windowed_history, conv, "What was the raw JSON?"
    )

    # Three messages: history-1, history-2, replay-block, current
    assert len(messages) == 4, f"expected 4 messages, got {len(messages)}"
    assert messages[0].role == "user" and messages[0].content == "search_quotes"
    assert messages[1].role == "assistant" and messages[1].content == "Found 4 quotes."
    assert messages[2].role == "system" and "[SYSTEM: Prior-turn tool results" in messages[2].content
    assert "EST-2026-006" in messages[2].content
    assert messages[3].role == "user" and messages[3].content == "What was the raw JSON?"


def test_build_replay_messages_no_conversation_id():
    """Without conversation_id, the helper degrades to the pre-fix shape."""
    from app.routers.max.router import _build_replay_messages

    messages = _build_replay_messages(
        [{"role": "user", "content": "hi"}], None, "follow-up"
    )
    assert len(messages) == 2
    assert messages[0].role == "user"
    assert messages[1].role == "user" and messages[1].content == "follow-up"


def test_record_turn_no_conversation_id_is_noop():
    """record_turn with no conversation_id must not crash or write."""
    from app.services.max import chat_session

    # Just check it doesn't throw
    chat_session.record_turn(None, "user", "hi", None)
    chat_session.record_turn("", "user", "hi", None)


# ── H53 FIX tests (2026-08-19) ─────────────────────────────────────

def test_replay_block_empty_when_no_tool_results():
    """H53 NEGATIVE FIXTURE 1: a turn with ZERO prior tool results
    renders NO replay block at all — not even the [SYSTEM:] header.
    Absence must look like absence.
    """
    from app.services.max import chat_session

    block = chat_session.format_replay_block([
        {"turn_index": 1, "role": "user",
         "content": "what is the status of the registry?",
         "tool_results": []},
        {"turn_index": 2, "role": "assistant",
         "content": "Let me check.",
         "tool_results": []},
    ])
    assert block == "", (
        f"replay block must be empty when no tool_results present, "
        f"got: {block[:80]!r}"
    )


def test_replay_block_empty_when_turns_have_only_no_results():
    """H53 variant: even with multiple turns, if NONE has tool_results
    (all []), the block is empty.
    """
    from app.services.max import chat_session

    block = chat_session.format_replay_block([
        {"turn_index": i, "role": "user" if i % 2 == 0 else "assistant",
         "content": "x", "tool_results": []}
        for i in range(1, 7)
    ])
    assert block == ""


def test_replay_block_emitted_when_any_turn_has_results():
    """H53 POSITIVE FIXTURE 5: real prior tool results still replay
    correctly across turns (F1, 430e071). When AT LEAST ONE turn has
    tool_results, the block renders (with the [SYSTEM:] header).
    """
    from app.services.max import chat_session

    block = chat_session.format_replay_block([
        {"turn_index": 1, "role": "user", "content": "search_quotes",
         "tool_results": None},
        {"turn_index": 2, "role": "assistant", "content": "Found 1.",
         "tool_results": [{"tool": "search_quotes", "success": True,
                          "result": {"quotes": [{"quote_number": "EST-2026-006"}]},
                          "result_preview": '{"quotes": [{"quote_number": "EST-2026-006"}]}'}]},
    ])
    assert "[SYSTEM: Prior-turn tool results" in block
    assert "EST-2026-006" in block


def test_build_replay_messages_uses_role_system():
    """H53 FIX (router.py:154): the replay block is appended with
    role='system' (not role='user'). MAX must never see system-
    prompt content in the user channel — that shape triggered the
    correct prior refusal.
    """
    from app.routers.max.router import _build_replay_messages

    msgs = _build_replay_messages(
        windowed_history=[],
        conversation_id=None,  # no replay injection
        current_message="hello",
    )
    # No conversation_id → no replay block at all (correct)
    assert all(m.role != "user" or "SYSTEM:" not in m.content
               for m in msgs), (
        "replay block leaked as user-channel content"
    )


def test_build_replay_messages_replay_block_is_system_message():
    """H53 FIX: when conversation_id + recent tool_results exist,
    the replay block must be SystemMessage, NOT HumanMessage.
    """
    from app.routers.max.router import _build_replay_messages
    from app.services.max import chat_session
    from app.routers.max.router import _build_replay_messages

    import os
    os.environ.setdefault(
        "EMPIRE_TASK_DB",
        os.path.expanduser("~/empire-data/empire.db"),
    )

    conv = "test-h53-role-system"
    # Clean and seed
    chat_session._connect().execute(
        "DELETE FROM chat_session_turns WHERE conversation_id = ?", (conv,)
    ).connection.commit()
    chat_session.record_turn(
        conv, "user", "search_quotes", None,
    )
    chat_session.record_turn(
        conv, "assistant", "Found 1.",
        [{"tool": "search_quotes", "success": True,
          "result": {"quotes": [{"quote_number": "EST-2026-006"}]},
          "result_preview": '{"quotes": [{"quote_number": "EST-2026-006"}]}'}],
    )

    msgs = _build_replay_messages(
        windowed_history=[],
        conversation_id=conv,
        current_message="hello",
    )
    # The replay block must be role="system" (the [SYSTEM:]
    # scaffolding is NOT user-channel content). The current user
    # message is role="user" by design — that's the founder's
    # turn and is correct. Scope the check to the replay block
    # (the one with [SYSTEM:] in content), not to all role="user"
    # messages (which would falsely flag the founder's turn).
    replay_block = next(
        (m for m in msgs if "[SYSTEM:" in m.content), None
    )
    assert replay_block is not None, (
        f"replay block must exist when recent tool_results are "
        f"present. Got msgs: {[(m.role, m.content[:40]) for m in msgs]}"
    )
    assert replay_block.role == "system", (
        f"replay block must be role='system' (H53 fix). "
        f"Got role={replay_block.role!r}"
    )
    # The current founder turn stays role='user' (correct).
    current_turn = msgs[-1]
    assert current_turn.role == "user", (
        f"founder's current turn must be role='user' (correct). "
        f"Got role={current_turn.role!r}"
    )


def test_no_tool_results_yet_returns_only_current_message():
    """H53: a turn with conversation_id but NO recorded tool_results
    anywhere yet still routes only the current user message —
    no fabricated replay header.
    """
    from app.routers.max.router import _build_replay_messages
    from app.services.max import chat_session
    from app.routers.max.router import _build_replay_messages

    import os
    os.environ.setdefault(
        "EMPIRE_TASK_DB",
        os.path.expanduser("~/empire-data/empire.db"),
    )

    conv = "test-h53-no-tool-results-yet"
    chat_session._connect().execute(
        "DELETE FROM chat_session_turns WHERE conversation_id = ?", (conv,)
    ).connection.commit()
    # Seed with user + assistant but NO tool_results on either.
    chat_session.record_turn(
        conv, "user", "what is the registry?", None,
    )
    chat_session.record_turn(
        conv, "assistant", "Let me check that.", None,
    )

    msgs = _build_replay_messages(
        windowed_history=[],
        conversation_id=conv,
        current_message="thanks",
    )
    sys_msgs = [m for m in msgs if m.role == "system"]
    hum_msgs = [m for m in msgs if m.role == "user"]
    assert not sys_msgs, (
        f"no tool_results → no system scaffolding → replay block must "
        f"NOT exist. Got {len(sys_msgs)} system msgs."
    )
    assert len(hum_msgs) == 1, (
        f"only the current user message should land as user. "
        f"Got {len(hum_msgs)}: {[m.content[:50] for m in hum_msgs]}"
    )
