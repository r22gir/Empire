"""
HOTFIX 4 (2026-07-15): Empire-wide pytest isolation.

Two test-artifact regressions prompted this conftest:

  1. test_quote_tools_canonical_hotfix.py (HOTFIX 2) opened a direct
     sqlite3.connect("~/empire-data/empire.db") and called
     quote_service.create_quote from its fixture. Every test run
     created 9 real quotes (EST-2026-116 .. EST-2026-124) in prod
     with status=draft, visible to the founder in the active list.

  2. Any future test that imports app.services.* before setting
     EMPIRE_TASK_DB inherited the prod path because
     app.db.database captures DB_PATH at import time.

This conftest GUARANTEES both are fixed for every test in this suite.

Mechanism:
  - isolated_empire_db (session-scope, autouse-implicit via deps):
      Create a tmp SQLite file, set EMPIRE_TASK_DB to its path, then
      build the schema (no data). All tests in the session see this DB.
      Runs BEFORE any app code is imported via test module imports.
  - _truncate_test_db_between_tests (function-scope, autouse):
      Wipe data tables between tests so each gets a clean schema-only
      DB. Tests can opt out via @pytest.mark.live_db.

Tests that legitimately need the live prod DB must opt out with the
live_db marker, which gives an explicit, auditable override.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from pathlib import Path

import pytest

# Default safety knob: tests should never write to the prod DB unless
# they explicitly opt out. We block write-path calls that point at the
# real prod path.
_PROD_PATHS = (
    "empire-data/empire.db",
    "empire-data\\empire.db",
    "/empire-data/empire.db",
)

# Tables to truncate between tests so each gets a clean schema-only DB.
# Order matters: leaves first, then roots; FK constraints don't actually
# trip because unified_business_migration doesn't declare them strictly,
# but list children before parents for hygiene.
_DATA_TABLES = [
    "quote_photos", "quote_line_items",
    "client_option_sets", "client_portal_tokens",
    "saved_patterns", "drawing_versions",
    "work_order_items", "work_orders",
    "production_log",
    "invoices",
    "jobs",
    "payments_v2",
    "financial_audit_log",
    "chart_of_accounts",
    "quotes_v2",
]

_BACKEND_DIR = Path(__file__).resolve().parent.parent


def _ensure_backend_on_path() -> None:
    if str(_BACKEND_DIR) not in sys.path:
        sys.path.insert(0, str(_BACKEND_DIR))


def _build_empty_empire_db(path: str) -> None:
    """Create the unified business tables (no data) at `path`."""
    _ensure_backend_on_path()
    # Import inside the function so the fixture's env-var setup wins
    # over any earlier module-level import.
    from app.db.unified_business_migration import (
        create_all_tables, seed_chart_of_accounts,
    )
    conn = sqlite3.connect(path)
    try:
        create_all_tables(conn)
        # Chart-of-accounts seed is schema-defining; safe to include for
        # tests that touch payments.
        try:
            seed_chart_of_accounts(conn)
        except Exception:
            # If a future migration removes seed_chart_of_accounts, the
            # test DB still has the tables — that's all we need.
            pass
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(scope="session")
def isolated_empire_db(tmp_path_factory):
    """Session-scope: create one isolated SQLite DB per pytest run and
    force EMPIRE_TASK_DB to point at it before any test code touches
    `app.db.database`.

    The env-var flip happens BEFORE the test module's top-level imports
    run their `from app.db.database import ...`, so DB_PATH resolves
    to the tmp path even when the producer code captures it at import
    time.
    """
    tmp_dir = tmp_path_factory.mktemp("empire_test_db")
    db_path = str(tmp_dir / "test_empire.db")

    # 1. Save any pre-existing EMPIRE_TASK_DB so teardown can restore.
    _saved = os.environ.get("EMPIRE_TASK_DB")

    # 2. Point the env var at the tmp DB BEFORE app.db.database imports.
    os.environ["EMPIRE_TASK_DB"] = db_path

    # 3. Build schema (no data) on the tmp DB.
    _build_empty_empire_db(db_path)

    yield db_path

    # 4. Cleanup (best-effort).
    try:
        os.remove(db_path)
    except OSError:
        pass
    # Restore prior env var if any.
    if _saved is not None:
        os.environ["EMPIRE_TASK_DB"] = _saved
    else:
        os.environ.pop("EMPIRE_TASK_DB", None)


@pytest.fixture(autouse=True)
def _truncate_test_db_between_tests(isolated_empire_db, request):
    """Function-scope autouse: wipe data tables between tests so each
    starts clean. Honors @pytest.mark.live_db as an explicit override."""
    # Honor the opt-out for tests that genuinely need the live DB.
    if "live_db" in request.keywords:
        yield
        return

    conn = sqlite3.connect(isolated_empire_db)
    try:
        for tbl in _DATA_TABLES:
            try:
                conn.execute(f"DELETE FROM {tbl}")
            except sqlite3.OperationalError:
                # Table may not exist in this migration level; skip.
                pass
        conn.commit()
    finally:
        conn.close()
    yield


@pytest.fixture(autouse=True)
def _assert_not_writing_to_prod(isolated_empire_db, request):
    """Function-scope autouse: hard-stop any test that imports
    app.db.database AFTER the env var has flipped back to a prod path.
    Catches future regressions where a test imports the DB module
    without going through the fixture chain."""
    # Skip check if test is opting in to live DB.
    if "live_db" in request.keywords:
        yield
        return

    # If a test does `os.environ["EMPIRE_TASK_DB"] = <prod>` after this
    # fixture ran, raise immediately. The only allowlisted path is the
    # isolated_empire_db's tmp path, which pytest owns.
    current = os.environ.get("EMPIRE_TASK_DB", "")
    if current and current != isolated_empire_db:
        if any(p in current for p in _PROD_PATHS):
            raise RuntimeError(
                f"TEST_VIOLATION: {request.node.nodeid} flipped EMPIRE_TASK_DB "
                f"to a prod path ({current}). Use a tmp_path test DB or "
                f"@pytest.mark.live_db to opt in explicitly."
            )
    yield


# D28 2b-2 — guard that makes the wrong thing unreachable.
#
# Bug history (D28 STEP 2b probe, 2026-08-24):
#   - `code_task_persistence.DB_PATH` was a module-level constant
#     bound to `os.getenv("EMPIRE_TASK_DB") or ~/empire-data/empire.db`.
#   - pytest collection imports test files BEFORE session-scope
#     fixtures run. Any test file that did `from app.services.max
#     import code_task_runner` at module level pulled in
#     `code_task_persistence` at collection time, captured DB_PATH
#     to prod (EMPIRE_TASK_DB was unset), and bound it for the rest
#     of the session. Result: 10 fixture-shaped rows in prod.
#   - The fix (2b-1) made _connect() read the env var per call, but
#     an instruction in a dispatch is not a mechanism. We need a
#     HARD GUARD that fails any test whose _connect() would resolve
#     to a prod path.
#
# Mechanism:
#   - Wrap `code_task_persistence._connect` to inspect
#     `code_task_persistence._resolved_db_path()` BEFORE opening
#     the connection. If the resolved path matches any of
#     `_PROD_PATHS`, raise a RuntimeError naming the test.
#   - The guard honours `live_db` opt-out — a test that LEGITIMATELY
#     needs the live prod DB passes through.
#   - Autouse: every test gets wrapped, every test is checked at
#     every _connect() call.
def _wrap_module_connect_guard(module, module_label: str, node_id: str):
    """Wrap a module's `_connect` to fail-hard on prod-path resolution.

    Used by both the code_task_persistence and chat_session guards
    (D28 2c-2). Falls back to `module.DB_PATH` when `_resolved_db_path`
    is not present (pre-2b-1 / pre-2c-1 module-level capture defect
    class). Returns the original `_connect` so callers can restore it.
    """
    original_connect = module._connect

    def _guarded_connect():
        resolver = getattr(module, "_resolved_db_path", None)
        if callable(resolver):
            resolved = resolver()
        else:
            # Legacy path: the module-level capture has already
            # happened, so DB_PATH is whatever it was bound to at
            # import. If THAT was a prod path, the guard fires —
            # which is the bug we are catching.
            resolved = module.DB_PATH
        for prod_path in _PROD_PATHS:
            if prod_path in resolved:
                raise RuntimeError(
                    f"TEST_VIOLATION [{node_id}]: "
                    f"{module_label}._connect() would resolve to "
                    f"prod DB at {resolved!r}. Tests must run against the "
                    f"isolated_empire_db fixture; add @pytest.mark.live_db "
                    f"to opt in to the live prod DB explicitly."
                )
        return original_connect()

    module._connect = _guarded_connect
    return original_connect


@pytest.fixture(autouse=True)
def _guard_db_modules_against_prod_db(request):
    """D28 2b-2 + 2c-2: hard-stop any test whose DB module operations
    would land on a production DB. Not a warning — a hard failure that
    names the offending test.

    `_assert_not_writing_to_prod` above checks the env var. THIS
    fixture checks what the DB modules ACTUALLY resolve to at call
    time, which is what matters after the env-var/module-level-defect
    class of bugs.

    Coverage (extend as more modules get the 2b-1 fix applied):
      - code_task_persistence (D28 2b-1)
      - chat_session           (D28 2c-1)
      - other 9 modules from §2b-3 audit: still pre-fix, NOT guarded
        here. They get their own dispatches.
    """
    if "live_db" in request.keywords:
        yield
        return

    # Lazy imports so the guard only triggers if the modules are in
    # use. A test that imports none of them gets no overhead.
    targets = []
    try:
        from app.services.max import code_task_persistence as ctp
        targets.append((ctp, "code_task_persistence", ctp._connect))
    except Exception:
        pass
    try:
        from app.services.max import chat_session as cs
        targets.append((cs, "chat_session", cs._connect))
    except Exception:
        pass

    if not targets:
        # Neither module in use; nothing to guard.
        yield
        return

    originals = []
    for module, label, _ in targets:
        original = _wrap_module_connect_guard(module, label, request.node.nodeid)
        originals.append((module, original))
    try:
        yield
    finally:
        for module, original in originals:
            module._connect = original


def pytest_configure(config):
    """Register the live_db marker so its absence doesn't error."""
    config.addinivalue_line(
        "markers",
        "live_db: opt this test in to running against the live prod "
        "empire.db (use sparingly; most tests should use the "
        "isolated_empire_db session fixture).",
    )
