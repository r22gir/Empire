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

# ── 2026-10-04 live-data firewall (runs before ANY app import) ─────────────
# Root cause of test traffic in Rafael's live data: shells with the backend
# env loaded export EMPIRE_DATA_DIR / EMPIRE_TASK_DB = ~/empire-data, and the
# D33 block below used os.environ.setdefault, so the live values won. Now:
#   1. every data env var is FORCED to a per-run temp tree (never setdefault),
#   2. a process-wide audit-hook firewall refuses any touch of live data
#      (also in Python subprocesses via a generated sitecustomize),
#   3. conftest refuses to run at all if a data path still resolves live.
# See tests/_live_data_guard.py. There is no opt-out marker for this layer.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import _live_data_guard as _ldg  # noqa: E402

_LIVE_WATCH_BEFORE = _ldg.fingerprint()  # stat-only, before anything runs
_TEST_TMP_ROOT = Path(tempfile.mkdtemp(prefix=f"empire_test_pid{os.getpid()}_"))
_LIVE_GUARD_LOG = _TEST_TMP_ROOT / "live_data_violations.log"
_REDIRECTED_ENV = _ldg.redirect_env(_TEST_TMP_ROOT)
_ldg.write_sitecustomize(_TEST_TMP_ROOT)
_ldg.install(str(_LIVE_GUARD_LOG))

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
# 2026-10-04: forced, not setdefault — a live value exported by the shell
# must never win.
os.environ["EMPIRE_TASK_DB"] = _PRE_COLLECTION_DB_PATH

# D44 — the single-writer reads EMPIRE_DB_PATH / EMPIRE_PHOTOS_DIR via
# canonical_path.py at call time, but app-level imports (e.g. label_station)
# capture DB_PATH at module load. Pre-set these to the same tmp paths so
# collection-time imports do not lock onto prod paths.
_PRE_COLLECTION_PHOTOS_DIR = os.path.join(
    tempfile.gettempdir(),
    f"empire_test_d33_pid{os.getpid()}_photos",
)
os.environ["EMPIRE_DB_PATH"] = _PRE_COLLECTION_DB_PATH
os.environ["EMPIRE_PHOTOS_DIR"] = _PRE_COLLECTION_PHOTOS_DIR
# label_station / accounts read EMPIRE_DB (default: the live empire.db).
os.environ["EMPIRE_DB"] = _PRE_COLLECTION_DB_PATH

# Fail fast: refuse to collect a single test if any data path is still live.
_ldg.assert_isolated()

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
    # D48: `payments` and `customers` only became part of the test schema when
    # create_all_tables started building the chain tables. Ordered
    # children-before-parents so the deletes hold with FKs enforced —
    # payments -> invoices -> customers.
    "payments",
    "invoices",
    "jobs",
    "job_documents",   # D44 — job images landing table
    "payments_v2",
    "financial_audit_log",
    "chart_of_accounts",
    "quotes_v2",
    "customers",
    "schedule_events",
    "pickup_dropoff_logs",
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

    # D48: bring `jobs`/`invoices` up to production shape. jobs_unified runs
    # init_schema() at import time, which under pytest happens *before* this
    # function creates the tables — so its ALTERs silently no-op and the test
    # tables stay narrower than production (no job_number, client_name,
    # business_unit, pipeline_stage, ...). Re-running it here, once, after the
    # tables exist, makes that deterministic for every test rather than a
    # side effect of whichever test module happens to trigger it first.
    try:
        from app.routers.jobs_unified import init_schema as _jobs_unified_init_schema
        _jobs_unified_init_schema()
    except Exception:
        # Never let schema top-up break collection; tests that need the wider
        # columns will fail loudly on their own.
        pass

    try:
        from app.db.init_db import _migrate_schedule_tables
        conn_sched = sqlite3.connect(path)
        _migrate_schedule_tables(conn_sched)
        conn_sched.commit()
        conn_sched.close()
    except Exception:
        pass


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


def _tmp_mirror(path_str: str) -> str:
    """Temp stand-in for a live path.

    HARD roots (~/empire-data, /data/amp, /data/maxine) are never read: they
    map onto the run's temp data tree, the same place the forced env vars
    point (``~/empire-data/X`` -> ``$EMPIRE_DATA_DIR/X``; ``empire.db`` -> the
    isolated schema DB), so hard-coded and env-based code agree.
    SOFT roots (repo data dirs) are readable: files are copied into
    ``<tmp>/mirror/<hash>/<name>`` and directories get an empty copy of their
    sub-directory skeleton (no files) so ``UPLOAD_DIR / category`` still works.
    """
    import hashlib
    import shutil
    norm = os.path.normpath(os.path.abspath(os.path.expanduser(path_str)))
    kind = _ldg.classify(norm)
    if kind == "hard":
        home_data = os.path.normpath(str(_ldg.HOME / "empire-data"))
        if norm in (os.path.join(home_data, "empire.db"),):
            return _PRE_COLLECTION_DB_PATH
        for live, tmp in (
            (home_data, _TEST_TMP_ROOT / "data"),
            ("/data/amp", _TEST_TMP_ROOT / "family-amp"),
            ("/data/maxine", _TEST_TMP_ROOT / "family-maxine"),
        ):
            if norm == live or norm.startswith(live + os.sep):
                dst = Path(tmp) / os.path.relpath(norm, live)
                break
        else:  # realpath-only match (symlink); keep it in a hashed bucket
            dst = _TEST_TMP_ROOT / "mirror" / hashlib.sha1(norm.encode()).hexdigest()[:12] / os.path.basename(norm)
        dst = Path(os.path.normpath(dst))
        if not Path(norm).suffix:
            dst.mkdir(parents=True, exist_ok=True)
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
        return str(dst)
    # Hashed bucket + basename: the mirror path must not contain the live
    # path as a substring (the D33 sqlite guard matches substrings).
    bucket = hashlib.sha1(norm.encode()).hexdigest()[:12]
    dst = _TEST_TMP_ROOT / "mirror" / bucket / (os.path.basename(norm) or "root")
    src = Path(norm)
    if src.is_dir():
        if not dst.exists():
            dst.mkdir(parents=True, exist_ok=True)
            base_depth = norm.count(os.sep)
            for dirpath, dirnames, _files in os.walk(norm):
                if dirpath.count(os.sep) - base_depth >= 2:
                    dirnames[:] = []
                    continue
                for d in dirnames:
                    (dst / os.path.relpath(os.path.join(dirpath, d), norm)).mkdir(parents=True, exist_ok=True)
    else:
        dst.parent.mkdir(parents=True, exist_ok=True)
        if src.is_file() and not dst.exists():
            shutil.copyfile(src, dst)  # soft root: read-only source, temp copy
    return str(dst)


def _redirect_live_module_constants(modules) -> list[str]:
    """Point UPPER_CASE module constants that hold live paths (captured at
    import, e.g. chat dirs, upload dirs, audit files, LIVE_DB in the journey
    tests) at temp mirrors. The audit hook still catches anything missed."""
    import types as _types

    def _live(value) -> bool:
        if not isinstance(value, (str, Path)):
            return False
        sval = str(value)
        return "/" in sval and len(sval) <= 4096 and bool(_ldg.classify(sval))

    def _swap(value):
        new = _tmp_mirror(str(value))
        return Path(new) if isinstance(value, Path) else new

    changed = []
    for mod in modules:
        if mod is None:
            continue
        for name, value in list(vars(mod).items()):
            if name.isupper() and _live(value):
                setattr(mod, name, _swap(value))
                changed.append(f"{mod.__name__}.{name}")
            # Default args captured at def time, e.g.
            # write_review_queue_snapshot(path=REVIEW_QUEUE_PATH).
            elif isinstance(value, _types.FunctionType) and getattr(value, "__module__", None) == mod.__name__:
                d = value.__defaults__
                if d and any(_live(x) for x in d):
                    value.__defaults__ = tuple(_swap(x) if _live(x) else x for x in d)
                    changed.append(f"{mod.__name__}.{name}()")
                kd = value.__kwdefaults__
                if kd and any(_live(x) for x in kd.values()):
                    value.__kwdefaults__ = {k: (_swap(x) if _live(x) else x) for k, x in kd.items()}
                    changed.append(f"{mod.__name__}.{name}(*)")
    return changed


_REDIRECTED_CONSTANTS: list[str] = []


class _AppConstantRedirectFinder:
    """meta_path shim: after any ``app.*`` module executes (including lazy
    imports inside test bodies), rewrite its live-path constants to temp."""

    _active = False

    def find_spec(self, name, path=None, target=None):
        if self._active or not (name == "app" or name.startswith("app.")):
            return None
        self._active = True
        try:
            for finder in sys.meta_path:
                if finder is self or isinstance(finder, _AppConstantRedirectFinder) or not hasattr(finder, "find_spec"):
                    continue
                spec = finder.find_spec(name, path, target)
                if spec is not None:
                    break
            else:
                return None
        finally:
            self._active = False
        loader = spec.loader
        if loader is not None and hasattr(loader, "exec_module") and not getattr(loader, "_ldg_wrapped", False):
            orig = loader.exec_module

            def exec_module(module, _orig=orig):
                _orig(module)
                _REDIRECTED_CONSTANTS.extend(_redirect_live_module_constants([module]))

            try:
                loader.exec_module = exec_module
                loader._ldg_wrapped = True
            except (AttributeError, TypeError):
                pass
        return spec


# Import-time connects (e.g. tool_audit.init_audit_db() runs at import with
# AUDIT_DB still live, before the constant can be rewritten): translate any
# sqlite3.connect target under a live root to its temp mirror. Anything that
# bypasses this wrapper still hits the audit-hook firewall and fails.
_SQLITE_REWRITES: list[str] = []
_real_sqlite3_connect = sqlite3.connect


def _firewall_sqlite3_connect(database, *args, **kwargs):
    if isinstance(database, (str, Path)):
        db = str(database)
        if db.startswith("file:"):
            body, sep, query = db[5:].partition("?")
            if body and _ldg.classify(body):
                _SQLITE_REWRITES.append(body)
                database = "file:" + _tmp_mirror(body) + sep + query
        elif db and db != ":memory:" and _ldg.classify(db):
            _SQLITE_REWRITES.append(db)
            database = _tmp_mirror(db)
    return _real_sqlite3_connect(database, *args, **kwargs)


sqlite3.connect = _firewall_sqlite3_connect

# Same idea for the chmod 600 that DB initialisers run right after connect.
_real_os_chmod = os.chmod


def _firewall_os_chmod(path, mode, *args, **kwargs):
    if isinstance(path, (str, Path)) and _ldg.classify(str(path)):
        _SQLITE_REWRITES.append(f"chmod:{path}")
        path = _tmp_mirror(str(path))
        if not os.path.exists(path):
            return None
    return _real_os_chmod(path, mode, *args, **kwargs)


os.chmod = _firewall_os_chmod

sys.meta_path.insert(0, _AppConstantRedirectFinder())
# Modules already imported by plugins/conftest before this point.
_REDIRECTED_CONSTANTS.extend(_redirect_live_module_constants(
    [m for n, m in list(sys.modules.items()) if n == "app" or n.startswith("app.")]
))

# Test modules whose LIVE_DB constant now points at a temp COPY of the
# frozen ~/empire-repo/backend/data/empire.db snapshot.
_SNAPSHOT_COPY_MODULES: dict[str, str] = {}


def pytest_collection_modifyitems(config, items):
    """2026-10-04: the journey tests used to be auto-marked live_db and read
    ~/empire-repo/backend/data/empire.db directly — and, in shells with the
    backend env loaded, EMPIRE_DB_PATH sent generate_review_queue() to the
    LIVE ~/empire-data/empire.db. They now read a per-run temp COPY of the
    frozen snapshot (LIVE_DB rewritten, EMPIRE_DB_PATH/EMPIRE_TASK_DB pointed
    at the copy for those tests only) and their audit JSON goes to temp."""
    mods = {item.module for item in items}
    mods |= {m for n, m in list(sys.modules.items()) if n == "app" or n.startswith("app.")}
    _REDIRECTED_CONSTANTS.extend(_redirect_live_module_constants(mods))
    for item in items:
        mod = item.module
        live_db = getattr(mod, "LIVE_DB", None) if mod is not None else None
        if isinstance(live_db, (str, Path)) and str(live_db).startswith(str(_TEST_TMP_ROOT)):
            _SNAPSHOT_COPY_MODULES[mod.__name__] = str(live_db)
            # live_db marker = "don't truncate this DB between tests"; it no
            # longer bypasses the firewall, and the DB is a temp copy.
            item.add_marker(pytest.mark.live_db)


@pytest.fixture(autouse=True)
def _point_snapshot_tests_at_copy(request, monkeypatch):
    mod = getattr(request, "module", None)
    copy = _SNAPSHOT_COPY_MODULES.get(getattr(mod, "__name__", ""))
    if copy:
        monkeypatch.setenv("EMPIRE_DB_PATH", copy)
        monkeypatch.setenv("EMPIRE_TASK_DB", copy)
    yield


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    start = getattr(item, "_ldg_blocked_start", None)
    if start is None:
        item._ldg_blocked_start = start = len(_ldg.blocked_connects)
    outcome = yield
    rep = outcome.get_result()
    new = _ldg.blocked_connects[start:]
    if rep.failed and new:
        rep.sections.append(("live-data firewall", "connects to live services were blocked:\n  " + "\n  ".join(sorted(set(new)))))


_ISOLATED_ENV_NAMES = (
    "EMPIRE_TASK_DB", "EMPIRE_DB_PATH", "EMPIRE_DB", "EMPIRE_PHOTOS_DIR", "EMPIRE_DATA_DIR",
    "EMPIRE_BRAIN_DIR", "MAX_MEMORY_PATH", "OPENCLAW_DB_PATH", "EMPIRE_TEST_GUARD_LOG",
    "EMPIRE_MAX_JOURNAL_DB", "EMPIRE_MAX_JOURNAL_ARCHIVE", "COST_TRACKER_DB",
    "MAX_IMPROVE_SPEC_DIR", "VOICE_DOC_SESSIONS_PATH", "CHAT_BACKUP_DIR",
)
_ISOLATED_ENV = {n: os.environ[n] for n in _ISOLATED_ENV_NAMES if n in os.environ}


@pytest.fixture(autouse=True)
def _restore_isolated_env():
    """After every test: put the run's isolated data env back and re-check it.

    Some tests set os.environ["EMPIRE_TASK_DB"] directly, or
    importlib.reload(app.db.database) against their own tmp DB, and never
    restore it, so every later test silently used that stale DB
    (order-dependent 'no such table'). Also fail fast if anything left a
    data var pointing at live data."""
    mod = sys.modules.get("app.db.database")
    before = getattr(mod, "DB_PATH", None) if mod else None
    yield
    for name, value in _ISOLATED_ENV.items():
        if os.environ.get(name) != value:
            os.environ[name] = value
    mod = sys.modules.get("app.db.database")
    if mod is not None and before is not None and getattr(mod, "DB_PATH", None) != before:
        mod.DB_PATH = before
    _ldg.assert_isolated()


@pytest.fixture(autouse=True)
def _live_data_firewall_check(request):
    """Fail the test if it attempted to touch live data, even when the
    code under test swallowed the PermissionError."""
    start = len(_ldg.violations)
    yield
    new = _ldg.violations[start:]
    if new:
        pytest.fail(
            f"{request.node.nodeid} tried to touch live Empire data:\n  " + "\n  ".join(new[:10]),
            pytrace=False,
        )


def pytest_report_header(config):
    return [
        f"live-data firewall: temp root {_TEST_TMP_ROOT}",
        f"live-data firewall: env redirected: {', '.join(sorted(_REDIRECTED_ENV)) or 'none'}",
    ]


def pytest_sessionfinish(session, exitstatus):
    # Any change to a watched live file (the Max session journal) during the
    # run fails the run, whoever wrote it, and is reported.
    watch_changed = _ldg.changed_files(_LIVE_WATCH_BEFORE, _ldg.fingerprint())
    if watch_changed:
        sys.stderr.write(
            "\n[live-data firewall] LIVE FILE CHANGED DURING THE TEST RUN (run marked failed): "
            + ", ".join(watch_changed)
            + f"\n  this pytest process recorded {len(_ldg.violations)} refused access(es); if 0, the"
              " writer was another process (e.g. the live backend serving real traffic) - check its log.\n"
        )
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
    logged = []
    try:
        if _LIVE_GUARD_LOG.exists():
            logged = _LIVE_GUARD_LOG.read_text().splitlines()
    except OSError:
        pass
    refused = [l for l in logged if "LIVE_DATA_VIOLATION" in l]
    blocked = [l for l in logged if "LIVE_SERVICE_BLOCKED" in l]
    if refused or _ldg.violations:
        sys.stderr.write(
            f"\n[live-data firewall] {len(refused) or len(_ldg.violations)} refused live-data access(es):\n  "
            + "\n  ".join((refused or _ldg.violations)[:30]) + "\n"
        )
        session.exitstatus = pytest.ExitCode.TESTS_FAILED
    if blocked:
        from collections import Counter
        c = Counter(l.split("socket.connect -> ", 1)[-1] for l in blocked)
        sys.stderr.write(
            f"\n[live-data firewall] {len(blocked)} connect(s) to live services blocked (not failures by themselves): "
            + ", ".join(f"{k} x{v}" for k, v in c.most_common()) + "\n"
        )
    if _SQLITE_REWRITES:
        sys.stderr.write(
            f"\n[live-data firewall] sqlite connects rewritten to temp mirrors: {len(_SQLITE_REWRITES)} "
            f"({', '.join(sorted(set(_SQLITE_REWRITES))[:8])})\n"
        )
    if _REDIRECTED_CONSTANTS:
        sys.stderr.write(f"[live-data firewall] module constants redirected to temp: {len(_REDIRECTED_CONSTANTS)}\n")
    if not os.environ.get("EMPIRE_TEST_KEEP_TMP"):
        import shutil
        shutil.rmtree(_TEST_TMP_ROOT, ignore_errors=True)
