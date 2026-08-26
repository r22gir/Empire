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
import tempfile
from pathlib import Path

import pytest

# D33 — set EMPIRE_TASK_DB at conftest LOAD TIME, before pytest
# collects test modules. Module-level DB_PATH captures in
# backend/app/ (21 modules per §1b) bind to whatever EMPIRE_TASK_DB
# is at import time. If we wait until the session fixture runs,
# collection has already imported app modules with EMPIRE_TASK_DB
# unset, so DB_PATH captures ~/empire-data/empire.db. Fix: pre-set
# a tmp path here so every module-level capture resolves to the
# test DB.
#
# The path is keyed on os.getpid() so parallel pytest invocations
# don't collide. The session-scoped isolated_empire_db fixture
# builds the schema on this same path.
_PRE_COLLECTION_DB_PATH = os.path.join(
    tempfile.gettempdir(),
    f"empire_test_d33_pid{os.getpid()}.db",
)
os.environ.setdefault("EMPIRE_TASK_DB", _PRE_COLLECTION_DB_PATH)

# Default safety knob: tests should never write to the prod DB unless
# they explicitly opt out. We block write-path calls that point at the
# real prod path.
_PROD_PATHS = (
    "empire-data/empire.db",
    "empire-data\\empire.db",
    "/empire-data/empire.db",
    # D34: also match the legacy 2026-07-08 mirror at
    # ~/empire-repo/backend/data/empire.db. No current code writes
    # to it (verified D34 STEP 2), but the guard should fail loud
    # on any future regression that does.
    "empire-repo/backend/data/empire.db",
    "empire-repo\\backend\\data\\empire.db",
    "/empire-repo/backend/data/empire.db",
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
def isolated_empire_db():
    """Session-scope: build schema on the pre-collected tmp DB path.

    D33: the path is set at conftest load time (see top of file) so
    that module-level DB_PATH captures in backend/app/ resolve to
    this test DB even when the producing module is imported at
    collection time, before any fixture runs. The fixture's job is
    reduced to building the schema (no data) on the pre-set path.
    """
    db_path = _PRE_COLLECTION_DB_PATH

    # Build schema (no data) on the tmp DB.
    _build_empty_empire_db(db_path)

    yield db_path

    # Cleanup (best-effort).
    try:
        os.remove(db_path)
    except OSError:
        pass


@pytest.fixture(autouse=True)
def _truncate_test_db_between_tests(isolated_empire_db, request):
    """Function-scope autouse: wipe data tables between tests so each
    starts clean. Honors @pytest.mark.live_db as an explicit override."""
    # Honor the opt-out for tests that genuinely need the live DB.
    if "live_db" in request.keywords or "e2e_live" in request.keywords:
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
    if "live_db" in request.keywords or "e2e_live" in request.keywords:
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
    if "live_db" in request.keywords or "e2e_live" in request.keywords:
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


# D33 — process-wide sqlite3.connect hard guard.
#
# The §1b audit found 21 modules under backend/app/ with module-level
# `DB_PATH = os.getenv("EMPIRE_TASK_DB", ~/empire-data/empire.db)` captures.
# The pre-D33 guard (`_guard_db_modules_against_prod_db`) wraps
# `module._connect` for code_task_persistence and chat_session only —
# it does not catch the other 19 modules, and it does not catch direct
# `sqlite3.connect("~/empire-data/empire.db")` calls from a test.
#
# This guard closes both gaps by wrapping `sqlite3.connect` itself
# in the test process. ANY code path that calls `sqlite3.connect()`
# with a path that resolves to a prod DB will fail this test loudly,
# naming the offending test and the path. It cannot be satisfied by
# a test that simply avoids the DB — the check runs at the lowest
# possible layer, so a test that reaches sqlite3.connect at all must
# target the test DB.
#
# Skipped for tests with @pytest.mark.live_db (explicit opt-in).
# The schema-build call inside `isolated_empire_db` runs in the
# session fixture's setup, BEFORE this autouse function fixture
# starts, so the guard does not interfere with test-DB construction.
def _sqlite3_connect_prod_guard_enabled(request) -> bool:
    # Exempt `live_db` (legacy opt-in) AND `e2e_live` (D34 opt-in via
    # EMPIRE_E2E_BASE_URL). The e2e_live path is gated by the
    # `_skip_e2e_unless_opted_in` fixture above, which refuses to run
    # the test unless the env var is set — so any e2e_live test that
    # reaches this guard is one the founder explicitly opted in to.
    return "live_db" not in request.keywords and "e2e_live" not in request.keywords


@pytest.fixture(autouse=True)
def _sqlite3_connect_prod_guard(request):
    """D33: process-wide hard guard on sqlite3.connect. Any connect()
    call in the test process whose target path matches a prod DB path
    raises a RuntimeError naming the offending test and the path.

    Catches:
      - module-level DB_PATH captures (21 modules per §1b) — the
        captured DB_PATH flows into sqlite3.connect() at call time.
      - direct `sqlite3.connect("~/empire-data/empire.db")` from a
        test or fixture.
      - any future regression where a test or module bypasses the
        isolated_empire_db fixture.
    """
    if not _sqlite3_connect_prod_guard_enabled(request):
        yield
        return

    import sqlite3 as _sqlite3
    real_connect = _sqlite3.connect
    node_id = request.node.nodeid

    def _guarded_connect(database, *args, **kwargs):
        path_str = str(database) if database else ""
        for prod_path in _PROD_PATHS:
            if prod_path in path_str:
                raise RuntimeError(
                    f"TEST_VIOLATION [{node_id}]: "
                    f"sqlite3.connect({database!r}) targets a prod DB. "
                    f"Tests must use the isolated_empire_db fixture; "
                    f"add @pytest.mark.live_db to opt in to the live "
                    f"prod DB explicitly."
                )
        return real_connect(database, *args, **kwargs)

    _sqlite3.connect = _guarded_connect
    try:
        yield
    finally:
        _sqlite3.connect = real_connect


def pytest_configure(config):
    """Register the live_db marker so its absence doesn't error."""
    config.addinivalue_line(
        "markers",
        "live_db: opt this test in to running against the live prod "
        "empire.db (use sparingly; most tests should use the "
        "isolated_empire_db session fixture).",
    )
    # D34: register the e2e_live marker — the gate that pairs with
    # the EMPIRE_E2E_BASE_URL opt-in (see _skip_e2e_unless_opted_in).
    config.addinivalue_line(
        "markers",
        "e2e_live: this test makes HTTP calls to a live backend. "
        "It is skipped unless the runner exports EMPIRE_E2E_BASE_URL "
        "to the backend URL it intends to drive.",
    )


@pytest.fixture(autouse=True)
def _skip_e2e_unless_opted_in(request):
    """D34: gate the 17 E2E tests (the dangerous case) behind an
    explicit opt-in. The marker `e2e_live` flags tests that make
    HTTP calls to a live backend at the default API_BASE/BACKEND
    (:8000). Default suite runs MUST skip these — the live backend
    is the production process and any HTTP call mutates prod.

    Opt-in: set EMPIRE_E2E_BASE_URL to the backend URL the runner
    intends to drive (e.g. http://127.0.0.1:8000 for the prod
    backend; http://127.0.0.1:9999 for a separate test backend).
    When set, the 17 tests run. When unset, they skip.

    Note: the marker does not change test logic — it changes only
    whether the test is eligible to run. The full body of every
    test is unchanged.
    """
    if "e2e_live" not in request.keywords:
        yield
        return
    if os.environ.get("EMPIRE_E2E_BASE_URL"):
        yield
        return
    pytest.skip(
        f"E2E test gated by EMPIRE_E2E_BASE_URL env var. "
        f"Default suite runs skip these tests to avoid writes to "
        f"the live backend. Set EMPIRE_E2E_BASE_URL to a backend "
        f"URL (e.g. http://127.0.0.1:8000) to opt in."
    )


def pytest_collection_modifyitems(config, items):
    """D34: auto-mark journey tests as live_db so the legacy-mirror
    substring added to _PROD_PATHS doesn't break their read-only
    assertions. These tests deliberately read
    ~/empire-repo/backend/data/empire.db (a 2026-07-08 frozen
    snapshot, NOT a live DB) — verified D34 STEP 2. They don't
    write, but the guard fires on sqlite3.connect itself, so the
    existing live_db exemption is the correct knob."""
    for item in items:
        # `item.module.__name__` resolves to "tests.test_journey_linkage"
        # under the `backend/tests/` collection root — match the suffix.
        if item.module.__name__.endswith((
            ".test_journey_linkage",
            ".test_journey_review_queue",
        )):
            item.add_marker(pytest.mark.live_db)
