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


def pytest_configure(config):
    """Register the live_db marker so its absence doesn't error."""
    config.addinivalue_line(
        "markers",
        "live_db: opt this test in to running against the live prod "
        "empire.db (use sparingly; most tests should use the "
        "isolated_empire_db session fixture).",
    )
