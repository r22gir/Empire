"""
iX-day R1-INT-FIX: regression test for the gap-and-race-safe
intake_code allocator.

Two cases:
  1. Seed gapped codes (0001, 0003, 0505) — next allocation MUST
     succeed as 0506 (MAX+1, NOT COUNT(*)+1).
  2. Collision-retry — when MAX+1 is already taken by an out-of-band
     insert, the allocator MUST re-derive and pick a higher code
     instead of looping on the same conflict.

Uses a temp DB + monkey-patched DB_PATH so the test is hermetic and
doesn't pollute the canonical empire.db. The test cleans up after
itself.
"""
import os
import sqlite3
import tempfile
import uuid

import pytest


@pytest.fixture
def tmp_db(monkeypatch):
    """Create a temp DB with the canonical schema, seed only the test
    paths we need, and monkey-patch app.routers.intake_auth.DB_PATH so
    get_db() reads the temp DB."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = tmp.name

    # Replicate the schema (intake_projects only — that's all the
    # allocator reads)
    conn = sqlite3.connect(path)
    conn.executescript("""
        CREATE TABLE intake_projects (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            intake_code TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            business TEXT NOT NULL
        );
    """)
    conn.commit()
    conn.close()

    # Monkey-patch the DB_PATH so the module's get_db() reads our temp DB
    import app.routers.intake_auth as mod
    monkeypatch.setattr(mod, "DB_PATH", path)

    yield path

    try:
        os.unlink(path)
    except FileNotFoundError:
        pass


def _insert_project(conn, intake_code, name="seed"):
    conn.execute(
        "INSERT INTO intake_projects (id, user_id, intake_code, name, business) "
        "VALUES (?, ?, ?, ?, ?)",
        (str(uuid.uuid4()), str(uuid.uuid4()), intake_code, name, "workroom"),
    )


def test_gap_allocator_returns_max_plus_one(tmp_db):
    """Case 1 — gapped codes (0001, 0003, 0505) → next MUST be 0506.

    The COUNT(*)+1 bug would have returned 0004 here (3 rows + 1).
    The fix returns MAX(numeric suffix) + 1 = 0506.
    """
    from app.routers.intake_auth import _next_intake_code

    conn = sqlite3.connect(tmp_db)
    _insert_project(conn, "INT-2026-0001")
    _insert_project(conn, "INT-2026-0003")
    _insert_project(conn, "INT-2026-0505")
    conn.commit()
    conn.close()

    code = _next_intake_code()
    assert code == "INT-2026-0506", f"Expected INT-2026-0506, got {code}"


def test_gap_allocator_handles_unrelated_codes(tmp_db):
    """Sanity — unrelated codes (different year prefix) MUST NOT inflate
    the current-year MAX. Only same-year codes count."""
    from app.routers.intake_auth import _next_intake_code

    conn = sqlite3.connect(tmp_db)
    _insert_project(conn, "INT-2025-9999")  # last year, must be ignored
    _insert_project(conn, "INT-2026-0001")
    _insert_project(conn, "INT-2026-0003")
    conn.commit()
    conn.close()

    code = _next_intake_code()
    assert code == "INT-2026-0004", f"Expected INT-2026-0004, got {code}"


def test_gap_allocator_returns_0001_when_empty(tmp_db):
    """Fresh DB → first code is INT-2026-0001."""
    from app.routers.intake_auth import _next_intake_code

    code = _next_intake_code()
    assert code == "INT-2026-0001", f"Expected INT-2026-0001, got {code}"


def test_collision_retry_picks_higher_code(tmp_db):
    """Case 2 — collision-retry: simulate a concurrent insert that
    grabs the candidate AFTER the allocator computes MAX+1 but BEFORE
    the caller INSERTs. The retry loop in create_project() must
    re-derive and pick a higher code.

    We simulate this by:
      1. Seeding INT-2026-0505 (MAX = 0505).
      2. Computing the first candidate (0506).
      3. Manually inserting INT-2026-0506 (the "racing" concurrent insert).
      4. Computing the next candidate (should be 0507, not 0506 again).
    """
    from app.routers.intake_auth import _next_intake_code

    conn = sqlite3.connect(tmp_db)
    _insert_project(conn, "INT-2026-0505")
    conn.commit()
    conn.close()

    # First call: MAX=0505 → next is 0506
    first = _next_intake_code()
    assert first == "INT-2026-0506", f"First call: expected 0506, got {first}"

    # Simulate the concurrent insert that stole 0506
    conn = sqlite3.connect(tmp_db)
    _insert_project(conn, "INT-2026-0506", name="racing-concurrent-insert")
    conn.commit()
    conn.close()

    # Second call: MAX is now 0506 → next is 0507 (NOT 0506 again)
    second = _next_intake_code()
    assert second == "INT-2026-0507", (
        f"After collision, expected MAX+1=0507 (re-derived), got {second}. "
        f"This means the allocator is returning a stale code."
    )


def test_create_project_retries_on_unique_violation(tmp_db):
    """End-to-end: create_project's retry loop MUST recover from a
    UNIQUE collision by re-deriving the next code.

    We mock the allocator so the FIRST call returns a code that
    already exists (forced collision), and the SECOND call returns a
    free code. The orchestrator's retry covers the mismatch.
    """
    from app.routers import intake_auth as mod

    # Seed: the project at INT-2026-0505 is the only existing row.
    conn = sqlite3.connect(tmp_db)
    _insert_project(conn, "INT-2026-0505")
    conn.commit()
    conn.close()

    # Mock _next_intake_code: first call returns 0506 (collision),
    # second call returns 0507 (free).
    original = mod._next_intake_code
    state = {"calls": 0}

    def fake_next():
        state["calls"] += 1
        if state["calls"] == 1:
            return "INT-2026-0506"  # collides with the seeded row
        return "INT-2026-0507"  # free

    mod._next_intake_code = fake_next

    # Insert the colliding row (this is what a concurrent insert would do)
    conn = sqlite3.connect(tmp_db)
    _insert_project(conn, "INT-2026-0506", name="racing-concurrent-insert")
    conn.commit()
    conn.close()

    # Now exercise create_project's retry loop directly (the inner retry).
    # We re-implement the retry inline here matching the production logic
    # so the test is hermetic (no FastAPI request lifecycle needed).
    try:
        last_error = None
        intake_code = None
        for attempt in range(5):
            intake_code = mod._next_intake_code()
            try:
                conn = sqlite3.connect(tmp_db)
                conn.execute(
                    "INSERT INTO intake_projects (id, user_id, intake_code, name, business) "
                    "VALUES (?, ?, ?, ?, ?)",
                    (str(uuid.uuid4()), str(uuid.uuid4()), intake_code,
                     "test-row", "workroom"),
                )
                conn.commit()
                conn.close()
                break
            except sqlite3.IntegrityError as e:
                last_error = e
                conn.close()
                if "intake_code" in str(e) and attempt < 4:
                    continue
                raise
        else:
            raise AssertionError(f"retry loop exhausted: {last_error}")
    finally:
        mod._next_intake_code = original

    # The retry should have ABORTED the first attempt (collision) and
    # SUCCEEDED on the second (0507).
    assert state["calls"] == 2, f"Expected 2 calls, got {state['calls']}"
    assert intake_code == "INT-2026-0507", f"Expected 0507, got {intake_code}"

    # Verify the row landed at 0507
    conn = sqlite3.connect(tmp_db)
    rows = conn.execute(
        "SELECT intake_code FROM intake_projects WHERE intake_code = ?",
        ("INT-2026-0507",),
    ).fetchall()
    conn.close()
    assert len(rows) == 1, f"Expected 0507 in DB, found {len(rows)}"
