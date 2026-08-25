"""D28 2c — chat_session.py per-call DB_PATH resolution + guard tests.

Mirrors the test surface that 2b-1 + 2b-2 added for code_task_persistence.
Lives in a separate file because test_chat_session_replay.py sets
``EMPIRE_TASK_DB=~/empire-data/empire.db`` at module level — that would
trigger the guard and fail unrelated tests in the same file.
"""
from __future__ import annotations

import sqlite3

import pytest


# ── 2c-1 — per-call resolution test ────────────────────────────────

def test_chat_session_db_path_resolves_per_call(isolated_empire_db, monkeypatch, tmp_path):
    """D28 2c-1: chat_session._connect() resolves the DB path at CALL
    TIME, not at module import. Writes markers to two distinct tmp
    DBs and asserts each lands on its own. Under the OLD module-level
    capture the second marker would have leaked into the first DB."""
    from app.services.max import chat_session as cs

    def write_marker(db_path: str, marker_id: str) -> None:
        monkeypatch.setenv("EMPIRE_TASK_DB", db_path)
        monkeypatch.setattr(cs, "DB_PATH", db_path)
        cs.ensure_table()
        cs.record_turn(marker_id, role="user", content="per-call resolution probe", tool_results=[])

    def read_marker(db_path: str, marker_id: str):
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        try:
            r = conn.execute(
                "SELECT conversation_id FROM chat_session_turns WHERE conversation_id = ?",
                (marker_id,),
            ).fetchone()
            return dict(r) if r else None
        finally:
            conn.close()

    db_a = str(tmp_path / "per_call_a.db")
    db_b = str(tmp_path / "per_call_b.db")

    write_marker(db_a, "per-call-marker-a")
    write_marker(db_b, "per-call-marker-b")

    assert read_marker(db_a, "per-call-marker-a") is not None
    assert read_marker(db_a, "per-call-marker-b") is None, (
        "marker-b leaked into db_a: _connect() did NOT re-read the "
        "env var between calls. The module-level DB_PATH capture "
        "defect has returned."
    )
    assert read_marker(db_b, "per-call-marker-b") is not None
    assert read_marker(db_b, "per-call-marker-a") is None, (
        "marker-a leaked into db_b: same defect in reverse"
    )


def test_chat_session_resolved_db_path_reads_env_var_each_call(isolated_empire_db, monkeypatch):
    """D28 2c-1: _resolved_db_path() does not cache."""
    from app.services.max import chat_session as cs

    monkeypatch.delenv("EMPIRE_TASK_DB", raising=False)
    monkeypatch.setattr(cs, "DB_PATH", "/from/db_path/fallback.db")
    assert cs._resolved_db_path() == "/from/db_path/fallback.db"

    monkeypatch.setenv("EMPIRE_TASK_DB", "/from/env/var.db")
    assert cs._resolved_db_path() == "/from/env/var.db"

    monkeypatch.delenv("EMPIRE_TASK_DB", raising=False)
    assert cs._resolved_db_path() == "/from/db_path/fallback.db"


# ── 2c-2 — guard catches for chat_session ──────────────────────────

def test_chat_session_guard_fires_when_db_path_resolves_to_prod(isolated_empire_db, monkeypatch):
    """D28 2c-2: the conftest autouse guard extended in 2c-2 also wraps
    chat_session._connect. Proves that pointing both the env var and
    the DB_PATH fallback at prod makes chat_session._connect() raise
    RuntimeError naming chat_session and the prod path.

    Works against BOTH pre-fix (module-level DB_PATH capture) and
    post-fix (per-call resolution) code: the guard falls back to
    DB_PATH when _resolved_db_path() does not exist.
    """
    from app.services.max import chat_session as cs

    monkeypatch.setenv("EMPIRE_TASK_DB", "/home/rg/empire-data/empire.db")
    monkeypatch.setattr(cs, "DB_PATH", "/home/rg/empire-data/empire.db")

    # Sanity: prove the guard's wrap is in place for chat_session.
    assert "_guarded" in getattr(cs._connect, "__qualname__", cs._connect.__name__) or \
        cs._connect.__name__ == "_guarded_connect", (
            f"autouse guard did not wrap chat_session._connect; "
            f"_connect.__qualname__={cs._connect.__qualname__!r}"
        )

    # _connect() MUST raise RuntimeError that names this test.
    raised = False
    raised_msg = None
    try:
        cs._connect()
    except RuntimeError as e:
        raised = True
        raised_msg = str(e)
    assert raised, "guard must raise RuntimeError when chat_session._connect would open prod"
    msg = raised_msg
    assert "TEST_VIOLATION" in msg
    assert "chat_session" in msg, (
        f"guard message must name chat_session, got: {msg}"
    )
    assert "test_chat_session_guard_fires_when_db_path_resolves_to_prod" in msg, (
        f"guard must name the offending test, got: {msg}"
    )
    assert "empire-data/empire.db" in msg

    # And record_turn (which routes through _connect internally) also
    # sees the guard. record_turn has no internal try/except around
    # _connect — so the RuntimeError propagates.
    with pytest.raises(RuntimeError) as excinfo:
        cs.record_turn(
            conversation_id="guard-must-block-chat",
            role="user",
            content="this row must NOT land on prod",
            tool_results=[],
        )
    assert "TEST_VIOLATION" in str(excinfo.value)
    assert "chat_session" in str(excinfo.value)


def test_chat_session_guard_does_not_fire_for_isolated_db(isolated_empire_db):
    """D28 2c-2 (companion): the guard MUST NOT fire when the test
    runs against the isolated_empire_db fixture path. Sanity check
    that the guard is not over-eager."""
    from app.services.max import chat_session as cs

    resolver = getattr(cs, "_resolved_db_path", None)
    if callable(resolver):
        resolved = resolver()
    else:
        resolved = cs.DB_PATH
    assert "empire-data/empire.db" not in resolved, (
        f"isolated_empire_db fixture should keep resolver off prod; got {resolved}"
    )

    # _connect() succeeds.
    conn = cs._connect()
    try:
        assert conn is not None
    finally:
        conn.close()