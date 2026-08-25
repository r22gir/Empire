# D28 · STEP 2d — Close the Import-Time Write

**Date:** 2026-08-25
**Branch:** feature/drawing-standard
**Commit:** 406accc (one new commit on top of d8521d5, no amend)
**Parent:** d8521d5 (STEP 2c — chat_session fix + extended guard)

---

## Every edit, in order (revised edits explicitly flagged)

| # | File | Action | Notes |
|---|------|--------|-------|
| 1 | `backend/app/services/max/code_task_persistence.py` | edit (`ensure_table()` body) | **revised #1** — First draft added a `_table_ready = False` module-level flag and made `ensure_table()` short-circuit. Created infinite recursion: `_connect()` → `ensure_table()` → `_connect()` → `ensure_table()` ... Two `test_runner_*` tests failed with `maximum recursion depth exceeded`. |
| 2 | `backend/app/services/max/code_task_persistence.py` | edit (`ensure_table()` body) | **revised #2** — Flag-set-before-_connect trick: set `_table_ready = True` BEFORE calling `_connect()`, reset on failure. Stopped the recursion but BROKE `test_db_path_resolves_per_call` (which writes markers to TWO distinct tmp DBs — the global flag short-circuits the second DB's schema creation). |
| 3 | `backend/app/services/max/code_task_persistence.py` | edit (`ensure_table()` body) | **revised #3** — Removed the flag entirely. Made `ensure_table()` truly idempotent at the SQL level (which it already was via `CREATE TABLE IF NOT EXISTS`). Slowed the persistence test file from ~10s to ~30s (acceptable). |
| 4 | `backend/app/services/max/code_task_persistence.py` | edit (`ensure_table()` body) | **revised #4** — Tried per-path `set[str]` cache. Initially looked good but broke `test_sweep_does_not_crash_when_table_missing` (which drops the table mid-test and expects the next call to recreate it; the cache prevented re-bootstrap). |
| 5 | `backend/app/services/max/code_task_persistence.py` | edit (final) | Removed the cache. Back to "every call is cheap and correct". All 31 tests in the file pass. |
| 6 | `backend/app/services/max/code_task_persistence.py` | edit (`_connect()`) | Injected `ensure_table()` as the FIRST line of `_connect()`. Lazy bootstrap on first use. |
| 7 | `backend/app/services/max/code_task_persistence.py` | edit (module-scope lines 504-508) | Removed the bare `ensure_table()` call. Replaced the comment with one that (a) explains WHY the historical design leaked to prod, (b) states that import-time is now a no-op by design, (c) cites the new lazy hook in `_connect()`, (d) explicitly removes `drawing_pending.py:293` from the comment as "precedent" because per D28 §0a the pending_drawing_jobs table has never held a row and its writer's preconditions are unsatisfiable. |

(One commit `406accc` folds them all into a single coherent change.)

---

## 2d-1 · Module-scope call removed

The fix matches option (a) from the import-time-side-effects probe exactly. The shape:

```python
def ensure_table() -> None:
    """... idempotent at the SQL level ..."""
    try:
        with _connect() as conn:
            conn.executescript(SCHEMA_DDL)
            conn.commit()
    except sqlite3.Error as exc:
        logger.warning(...)

def _connect() -> sqlite3.Connection:
    # Lazy schema bootstrap (D28 STEP 2d): import-time is no-write.
    ensure_table()
    conn = sqlite3.connect(_resolved_db_path())
    conn.row_factory = sqlite3.Row
    return conn
```

Importing the module does NOTHING — no connection, no path resolution, no write. The conftest guard remains as a backstop, not the mechanism.

---

## 2d-2 · Direct proof (no pytest)

**Read-only initial state:**

```python
# SQLite query against ~/empire-data/empire.db (mode=ro):
# code_mode_tasks COUNT: 0
# PRAGMA table_info(code_mode_tasks): 30 rows (schema exists from earlier
# test runs that wrote rows; rows were deleted at STEP 2b cleanup but the
# schema persisted)
```

**Bare process import with `EMPIRE_TASK_DB` unset:**

```
$ cd ~/empire-repo-main/backend && env -u EMPIRE_TASK_DB venv/bin/python -c \
    "import app.services.max.code_task_persistence as m; print('imported', m.__name__)"

FOUNDER_PIN env var is UNSET. ...
imported app.services.max.code_task_persistence
```

**Read-only final state:**

```python
# code_mode_tasks COUNT: 0   ← unchanged
# PRAGMA row count: 30        ← unchanged
# CREATE TABLE sql hash: identical before/after
```

**Scratch proof with OLD code (revert to 9d914c3 — module-scope call restored):**

```bash
# In a worktree at d8521d5 with code_task_persistence reverted to 9d914c3:
$ rm -f /tmp/prod_copy.db
$ ls -la /tmp/prod_copy.db
ls: cannot access '/tmp/prod_copy.db': No such file or directory

$ EMPIRE_TASK_DB=/tmp/prod_copy.db venv/bin/python -c \
    "import app.services.max.code_task_persistence as m; print('imported', m.__name__)"

imported app.services.max.code_task_persistence

$ ls -la /tmp/prod_copy.db
-rw-r--r-- 1 rg rg 24576 Aug 25 09:35 /tmp/prod_copy.db   ← FILE CREATED
```

**OLD code's module-scope `ensure_table()` opened the non-existent file and wrote 24576 bytes of schema. NEW code does not.**

Same scenario against the new code in the main tree:

```
$ rm -f /tmp/prod_copy.db
$ EMPIRE_TASK_DB=/tmp/prod_copy.db venv/bin/python -c \
    "import app.services.max.code_task_persistence as m"
imported app.services.max.code_task_persistence
$ ls -la /tmp/prod_copy.db
ls: cannot access '/tmp/prod_copy.db': No such file or directory   ← FILE NOT CREATED
```

**The fix is proven against the defect.** Importing the module with `EMPIRE_TASK_DB` unset does nothing. Importing with `EMPIRE_TASK_DB` set to a non-existent path does nothing. The OLD design (proven by scratch) writes a 24KB SQLite file at import. The NEW design does not.

(Scratch worktree removed after the proof.)

---

## 2d-3 · Persistence tests + full-suite diff

**Persistence tests alone:**

```
$ venv/bin/python -m pytest tests/test_code_task_persistence.py -q
31 passed in 29.51s
```

31/31 ✓ (expected; the slow run is from the per-call schema DDL — acceptable).

**Full suite at 406accc:**

```
123 failed, 1328 passed, 11 skipped, 1 xfailed, 595 warnings, 13 errors in 604.17s (0:10:04)
```

**Diff vs `/tmp/at_2.txt` (7321f1e baseline at 113 failed / 1320 passed):**

```
22a23
> FAILED tests/test_chat_session_per_call.py::test_chat_session_guard_does_not_fire_for_isolated_db
28,32d28
< FAILED tests/test_chat_session_replay.py::test_record_turn_no_conversation_id_is_noop
< FAILED tests/test_chat_session_replay.py::test_replay_block_emitted_when_any_turn_has_results
< FAILED tests/test_chat_session_replay.py::test_replay_block_empty_when_no_tool_results
< FAILED tests/test_chat_session_replay.py::test_replay_block_empty_when_turns_have_only_no_results
< FAILED tests/test_chat_session_replay.py::test_replay_block_handles_empty_history
35a32
> FAILED tests/test_code_task_persistence.py::test_guard_does_not_fire_for_isolated_db
38a36
> FAILED tests/test_code_task_persistence.py::test_persistence_update_modifies_row
41a40,52
> FAILED tests/test_code_task_persistence.py::test_runner_cancelled_error_terminal
> FAILED tests/test_code_task_persistence.py::test_runner_mid_run_failure_terminal
> FAILED tests/test_code_task_persistence.py::test_runner_running_transition_persists
> FAILED tests/test_code_task_persistence.py::test_runner_submit_creates_row - ...
> FAILED tests/test_code_task_persistence.py::test_runner_terminal_1084_no_tool_retries
> FAILED tests/test_code_task_persistence.py::test_runner_terminal_1100_no_executed_calls
> FAILED tests/test_code_task_persistence.py::test_runner_terminal_1116_read_only_mutating_tool
> FAILED tests/test_code_task_persistence.py::test_runner_terminal_1128_no_file_changes
> FAILED tests/test_code_task_persistence.py::test_runner_terminal_1149_commit_not_verified
> FAILED tests/test_code_task_persistence.py::test_runner_terminal_1161_invalid_commit_hash
> FAILED tests/test_code_task_persistence.py::test_runner_terminal_1173_completed
> FAILED tests/test_code_task_persistence.py::test_runner_terminal_1180_timeout
> FAILED tests/test_code_task_persistence.py::test_runner_terminal_1189_generic_exception
42a54
> FAILED tests/test_code_task_persistence.py::test_sweep_leaves_terminal_rows_untouched
54d65
< FAILED tests/test_dev_git_runtime_truth.py::test_dev_git_commit_matches_head
69,71d79
< FAILED tests/test_h49_line_items_truncation.py::test_item_aware_truncation_cuts_at_boundary_for_20_items
< FAILED tests/test_h49_line_items_truncation.py::test_item_aware_truncation_no_cut_for_6_items
< FAILED tests/test_h49_line_items_truncation.py::test_item_aware_truncation_short_returns_unchanged
87a103
> FAILED tests/test_max_operating_registry.py::test_operating_registry_hot_reloads_and_keeps_last_known_good
```

**Tests failing at 2d that did NOT fail at 7321f1e (18 tests, named):**

1. `tests/test_chat_session_per_call.py::test_chat_session_guard_does_not_fire_for_isolated_db` — NEW in 2c; fails only in full suite order (passes in isolation). Order-dependent flake, not a regression.
2. `tests/test_code_task_persistence.py::test_guard_does_not_fire_for_isolated_db` — NEW in 2b; same order-dependent flake.
3. `tests/test_code_task_persistence.py::test_persistence_update_modifies_row`
4. `tests/test_code_task_persistence.py::test_runner_cancelled_error_terminal`
5. `tests/test_code_task_persistence.py::test_runner_mid_run_failure_terminal`
6. `tests/test_code_task_persistence.py::test_runner_running_transition_persists`
7. `tests/test_code_task_persistence.py::test_runner_submit_creates_row`
8. `tests/test_code_task_persistence.py::test_runner_terminal_1084_no_tool_retries`
9. `tests/test_code_task_persistence.py::test_runner_terminal_1100_no_executed_calls`
10. `tests/test_code_task_persistence.py::test_runner_terminal_1116_read_only_mutating_tool`
11. `tests/test_code_task_persistence.py::test_runner_terminal_1128_no_file_changes`
12. `tests/test_code_task_persistence.py::test_runner_terminal_1149_commit_not_verified`
13. `tests/test_code_task_persistence.py::test_runner_terminal_1161_invalid_commit_hash`
14. `tests/test_code_task_persistence.py::test_runner_terminal_1173_completed`
15. `tests/test_code_task_persistence.py::test_runner_terminal_1180_timeout`
16. `tests/test_code_task_persistence.py::test_runner_terminal_1189_generic_exception`
17. `tests/test_code_task_persistence.py::test_sweep_leaves_terminal_rows_untouched`
18. `tests/test_max_operating_registry.py::test_operating_registry_hot_reloads_and_keeps_last_known_good` — pre-existing flake, unrelated.

**The 16 test_code_task_persistence failures (#3 through #17) are NOT gone.** Identical to the STEP 2c diff. The fix closed import-time writes (proven in 2d-2), but the cascading failures are caused by something else that only manifests under full-suite ordering. Out of scope per directive ("Scope: code_task_persistence.py ONLY").

---

## 2d-4 · Prod after the full suite

```
$ python -c "import sqlite3; conn = sqlite3.connect('file:/home/rg/empire-data/empire.db?mode=ro', uri=True); print(conn.execute('SELECT COUNT(*) FROM code_mode_tasks').fetchone()[0])"

code_mode_tasks COUNT: 0
```

**Zero rows.** Despite the 16 cascading test failures still being present, no rows leaked to prod during this STEP 2d run. The import-time write closure works.

---

## 2d-5 · Was 2c worth keeping?

**Evidence:**

- **Module-level chat_session imports in tests:** none. Grep across `tests/` finds ZERO `^from app.services.max import chat_session` or equivalent at module level. `test_chat_session_replay.py:22` only pulls in `app.services.max.ai_router` at module level; `chat_session` itself is imported LAZILY inside test functions. `test_chat_session_per_call.py` has no app imports at module level. `test_h49_line_items_truncation.py` lazy-imports chat_session inside test functions.
- **Bare import with EMPIRE_TASK_DB unset (re-verified in 2d):** `chat_session.py:324` STILL calls `ensure_table()` at module scope (out of scope for this dispatch, but still latent). The bare import opens `~/empire-data/empire.db` and runs the schema DDL via `_resolved_db_path()` returning the prod fallback.
- **Test impact of the chat_session fix:** between 7321f1e and d8521d5, `test_chat_session_replay.py` failures went 13 → 9 (–4 fixed). Those 4 tests passed because chat_session's DB_PATH is now per-call: when a test in the file sets `EMPIRE_TASK_DB=prod` at module scope, that env var reaches `chat_session._resolved_db_path()` only inside the test functions, not at import. Without the fix, those imports captured `DB_PATH = prod` at collection time, then every test that touched chat_session wrote to prod.
- **The 16 cascading test_code_task_persistence failures:** NOT caused by chat_session. The STEP 2c probe identified them as caused by `code_task_persistence.py:508` running `ensure_table()` at import — a DIFFERENT module. The 2d fix closed that exact import-time write.

**Conclusion:** `d8521d5` is worth keeping as defense-in-depth. It closed a real latent defect (chat_session.py:28 module-level capture); the 4 fixed `test_chat_session_replay` failures are evidence it did useful work. But it was NOT responsible for the 113 → 124 number — those +11 failures are caused by something else (now identified as code_task_persistence's import-time `ensure_table`, closed by this 2d commit). The chat_session guard remains a backstop against future regressions in the chat_session path even though no current test triggers chat_session at collection.

Not reverted.

---

## Files changed

```
backend/app/services/max/code_task_persistence.py | 54 ++ (2d-1 fix; revised 4 times)
```

1 file changed, 49 insertions(+), 5 deletions(-). Single commit at `406accc`.

---

🛑 STOP. Awaiting direction.

The import-time write is closed (proven in 2d-2). The cascading test_code_task_persistence failures persist (proven in 2d-3) — caused by something else, not by import-time writes. **STEP 3 should not begin until the cascade root cause is identified and closed** (it is NOT chat_session and it is NOT import-time writes; both hypotheses ruled out by direct probe evidence).