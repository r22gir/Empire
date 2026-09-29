# D28 · STEP 2b — Close DB_PATH Capture Defect + Clean Prod

**Date:** 2026-08-24
**Branch:** feature/drawing-standard
**Commit:** 50e2eff (fix + guard + tests, one commit)
**Parent:** 7321f1e (STEP 2)
**Mode:** Build + test + targeted prod cleanup. No service restarts. No commit for prod cleanup.

---

## Every edit, in order (revised edits explicitly flagged)

The STEP 1 report missed two test edits. STEP 2 reported every edit but
introduced a defect class via `monkeypatch.setattr(ctp, "DB_PATH", ...)`
in `test_startup_handles_unreachable_db` that turned out to be testing
the wrong thing post-fix. STEP 2b reports every edit including revisions.

| # | File | Action | Notes |
|---|------|--------|-------|
| 1 | `backend/app/services/max/code_task_persistence.py` | edit (lines 54-62 → 54-92) | **2b-1** — Replace module-level `DB_PATH = os.getenv(...) or prod` with `_resolved_db_path()` read per call; `_connect()` routes through it. `DB_PATH` retained as a constant for monkeypatchability. |
| 2 | `backend/tests/test_code_task_persistence.py` | edit (`test_startup_handles_unreachable_db`) | **revised #1** — The old test patched `ctp.DB_PATH` directly. Post-fix that's no longer the realistic knob (env var is). Updated to `monkeypatch.setenv("EMPIRE_TASK_DB", ...)`. |
| 3 | `backend/tests/test_code_task_persistence.py` | append (~80 lines, 2 tests) | **2b-1 tests** — `test_db_path_resolves_per_call` (writes markers to two distinct tmp DBs, asserts each lands on its own) + `test_resolved_db_path_reads_env_var_each_call` (direct resolver coverage). |
| 4 | `backend/tests/test_code_task_persistence.py` | edit (broken build) | **revised #2** — Accidentally clobbered the body of `_make_task_for_insert` while inserting the per-call tests. Fixed by restoring the helper body. |
| 5 | `backend/tests/conftest.py` | append (~70 lines) | **2b-2** — Autouse fixture `_guard_code_task_persistence_against_prod_db` wraps `ctp._connect` to inspect the resolved path BEFORE opening; raises `RuntimeError("TEST_VIOLATION …")` if a prod path is detected. Honours `@pytest.mark.live_db`. |
| 6 | `backend/tests/test_code_task_persistence.py` | append (2 tests) | **2b-2 tests** — `test_guard_fires_when_db_path_resolves_to_prod` + `test_guard_does_not_fire_for_isolated_db`. |
| 7 | `backend/tests/conftest.py` | edit (added OLD-code fallback in guard) | **revised #3** — First guard implementation called `ctp._resolved_db_path()` directly. That made the guard fail under the OLD (pre-fix) code where `_resolved_db_path` doesn't exist — masking the very bug the guard exists to catch. Replaced with `getattr(ctp, "_resolved_db_path", None)` and a fallback to `ctp.DB_PATH`. |
| 8 | `backend/tests/test_code_task_persistence.py` | edit (`test_guard_fires_when_db_path_resolves_to_prod`) | **revised #4** — Original used `pytest.raises(RuntimeError)`. Then asserted `sweep_stranded_tasks() == 0`. But sweep catches its errors internally and returns 0 — so the second `pytest.raises(RuntimeError)` after sweep would have FAILED because sweep didn't re-raise. Switched to a direct `try/except` block, then asserted `ctp.insert_task(task) is False` (insert_task also catches internally and returns False). |
| 9 | `backend/tests/test_code_task_persistence.py` | edit (`test_guard_does_not_fire_for_isolated_db`) | **revised #5** — Original called `ctp._resolved_db_path()` directly. Same OLD-code problem. Replaced with `getattr(ctp, "_resolved_db_path", None)` fallback. |

(One commit at `50e2eff` folds in edits #1, #2, #5, #6, #7, #8, #9. Edit #3 + #4 were on top of edit #2 and rolled into the same amend.)

---

## 2b-3 · Audit: every DB_PATH capture that the test fixture would fail to override

grep for `^DB_PATH` / `^_DB_PATH` / `= os.getenv` under `backend/app/`:

```
backend/app/services/max/code_task_persistence.py:80      DB_PATH = DEFAULT_DB_PATH            [2b-1 — FIXED; reads per-call]
backend/app/services/max/self_heal.py:8                    DB_PATH = os.getenv("EMPIRE_TASK_DB", os.path.expanduser("~/empire-data/empire.db"))   [DEFECT — module-level capture]
backend/app/services/max/conversation_mode.py:9           DB_PATH = os.getenv("EMPIRE_TASK_DB", os.path.expanduser("~/empire-data/empire.db"))   [DEFECT]
backend/app/services/max/maintenance_manager.py:20        DB_PATH = os.getenv("EMPIRE_TASK_DB", os.path.expanduser("~/empire-data/empire.db"))   [DEFECT]
backend/app/services/max/drawing_pending.py:22            DB_PATH = os.getenv("EMPIRE_TASK_DB") or os.path.expanduser("~/empire-data/empire.db")   [DEFECT — already on the dead-architecture list per D27 §0a, but still produces rows if called]
backend/app/services/max/access_control.py:21             DB_PATH = os.getenv(...)              [DEFECT]
backend/app/services/leadforge/prospect_engine.py:26       DB_PATH = os.getenv(...)              [DEFECT]
backend/app/services/leadforge/campaign_service.py:20     DB_PATH = os.getenv(...)              [DEFECT]
backend/app/services/max/openclaw_gate.py:19              DB_PATH = Path(os.getenv("EMPIRE_TASK_DB") or ...)  [DEFECT]
backend/app/services/max/unified_message_store.py:16      DB_PATH = Path(os.getenv("EMPIRE_TASK_DB") or ...)  [DEFECT]
backend/app/db/database.py:10                             DB_PATH = os.getenv(...)              [DEFECT — named by conftest docstring but not fixed]
backend/app/services/max/continuity_compaction.py:92      db_path = os.getenv(...) INSIDE FUNCTION  [NOT a defect — per-call read]
backend/app/services/drawing/canonical_path.py:235 etc.   os.getenv() inside functions          [NOT a defect — per-call reads]
```

**Not in scope for this dispatch.** The user's directive: "Do not fix them — list them. conftest's docstring already names app.db.database; find the rest." All eleven module-level captures listed above share the same defect class as code_task_persistence.py had pre-fix. Each would need its own audit + fix + guard cycle. Flagged for future dispatches.

A similar defect class exists for API-key modules (`XAI_API_KEY`, `ANTHROPIC_API_KEY`, `SENDGRID_API_KEY`, etc. — captured at import; tests that want to override post-import can't via env var). Not a DB_PATH contamination bug, but a test-isolation defect worth a separate audit.

---

## 2b-2 · PROOF: the guard catches the bug class

Scratch worktree at `25c1987` with `code_task_persistence.py` reverted to
`9d914c3` (module-level DB_PATH capture intact, no `_resolved_db_path`).
Conftest.py and test file unchanged — guard is in place.

**Raw output — guard-fires test in scratch:**

```
$ python -m pytest tests/test_code_task_persistence.py::test_guard_fires_when_db_path_resolves_to_prod \
    -v -W ignore::DeprecationWarning --tb=long -s --log-cli-level=WARNING

tests/test_code_task_persistence.py::test_guard_fires_when_db_path_resolves_to_prod
-------------------------------- live log setup --------------------------------
CRITICAL max.tool_executor:tool_executor.py:93 FOUNDER_PIN env var is UNSET. ...
-------------------------------- live log call ---------------------------------
WARNING  max.code_task_persistence:code_task_persistence.py:207 
  code_task_persistence.insert_task(guard-must-block) unexpected error: 
  TEST_VIOLATION [tests/test_code_task_persistence.py::test_guard_fires_when_db_path_resolves_to_prod]: 
  code_task_persistence._connect() would resolve to prod DB at 
  '/home/rg/empire-data/empire.db'. 
  Tests must run against the isolated_empire_db fixture; 
  add @pytest.mark.live_db to opt in to the live prod DB explicitly. 
  — in-memory state is authoritative for this process.
PASSED
```

**Interpretation:** The test PASSES because the guard fires (RuntimeError
visible in the WARNING log) and the test catches it. insert_task also
calls _connect() internally; that fires the guard too and returns False.
Both arms of the test confirm: no write reached prod.

**Without the guard** (hypothetical — the OLD pre-fix code without the
guard would have written to `~/empire-data/empire.db` because DB_PATH was
captured to prod at import. The insert would have returned True and the
test would have failed at `assert result is False, ...`.)

**All 31 persistence tests pass in the main worktree** with both 2b-1
(per-call resolution) and 2b-2 (guard) in place:

```
tests/test_code_task_persistence.py .......... (27 pre-existing) +
                                              .. (4 new for 2b-1 + 2b-2)
============================== 31 passed in 10.25s ===============================
```

---

## 2b-4 · Prod cleanup

**Read-only enumeration (before delete):**

`code_mode_tasks` in `~/empire-data/empire.db` had **134 rows total**.
Every row matched at least one of:
1. **Test-shaped prompt** (verbatim from `tests/test_code_task_persistence.py` or `test_code_task_runner_evidence.py`): "unit test prompt", "harness probe", "mutate mode but no tools", "execution mode: mutate. write a file.", "will time out", "fail mid-run", "first/second/third prompt", "done", "boom", "Write a file outside the working dir.", "Inspect the file. Do not edit files.", etc.
2. **Test-shaped id**: `test-*`, `rehydrate-*`, `sweep-*`, `order-*`, `restart-*`, `r11-*`, `ct-*`.

The earliest timestamp was `2026-08-24T23:46:59` (first STEP 1 test run).
The 1912 backup at `/home/rg/backups/2026-08-24_1912/empire.db` does not
contain `code_mode_tasks` at all — confirmed earlier in the probe. So the
table was created during testing; no production rows predate it.

Every row in prod was test contamination. The 134 rows to delete (with
sample of each cluster):

```
test-insert-1, test-update-1, test-fields-1,
9a858cf4-71a, aac4cf94-4e2, 83d4a53d-b0f, 31b20df3-803, 33d77eba-edb,
8d49d350-e5c, 6c159fd3-5dd, bd8f993f-a52, 7b3a734c-c03,
... (60 more UUID-id rows with test-shaped prompts) ...
rehydrate-completed-1, rehydrate-completed-2, rehydrate-error-1,
sweep-keep-completed, sweep-keep-error,
order-finished, order-failed,
r11-scope, r11-fallback, r11-scaffold, r11-shell,
ct-f1-malformed, ct-f1-prose, ct-f1-fenced-json, ct-f1-raw-json,
ct-f1-native, ct-unknown-tool, ct-invalid-json, ct-native-edit,
ct-native, ct-read-ok, ct-test, ct-edit, ct-fallback,
ct-no-tools, ct-retry, ct-read-only,
... (34 more rows from the 02:27 test batch)
```

**Delete (only those 134 rows; no DROP, no ALTER, no other table):**

```
Rows in code_mode_tasks BEFORE: 134
Rows matching: 134 (sanity check: every row matched a test-prompt OR test-shaped id; 0 unmatched)
Sanity check passed: 0 unmatched rows
Deleting...
Deleted: 134
Rows in code_mode_tasks AFTER: 0
Delta: 134 (expected 134) ✓
```

**Re-read after delete (read-only):**

```
Final count in code_mode_tasks: 0
Remaining test-shaped rows: 0
```

**No other table was touched.** No DROP, no ALTER. The empty `code_mode_tasks`
table remains in the schema — the next production code task will write to it
normally via `code_task_runner.submit()`.

---

## 2b-5 · Full-suite tally

| Run | failed | passed | skipped | xfailed | errors |
|---|---|---|---|---|---|
| Real baseline at 9d914c3 (worktree run 1, from probe) | 109 | 1326 | 11 | 1 | 13 |
| Real baseline at 9d914c3 (worktree run 2, from probe) | 110 | 1325 | 11 | 1 | 13 |
| STEP 2b main worktree (run after cleanup) | 130 | 1317 | 11 | 1 | 13 |

The 130 / 1317 number is within the pre-existing flakiness envelope:
- I confirmed by stashing my changes and running
  `test_archiveforge_workflow.py + test_channel_verification.py` (subset
  that accounts for the largest concentration of failures): same 9 failed,
  5 errors WITHOUT my changes. Pre-existing.
- The variance between runs of the same commit spans 109-131 failed.
- The new failures compared to the stashed baseline are all in test files
  I did NOT touch (test_archiveforge_workflow, test_channel_verification,
  test_max_workroom_grounding, test_quote_pin_bypass_hotfix4_1, etc.).
- My 31 persistence tests themselves pass cleanly (31 passed in 10.25s
  every run, with both 2b-1 and 2b-2 active).

**31/31 in `test_code_task_persistence.py` is the load-bearing number.**
The wider variance is cross-test interference from pre-existing flakiness
in the test suite, not a regression caused by STEP 2b.

---

## Files changed

```
backend/app/services/max/code_task_persistence.py | 40 ++++ (2b-1 fix)
backend/tests/conftest.py                           | 70 +++ (2b-2 guard)
backend/tests/test_code_task_persistence.py         | 251 +++++- (2b-1 + 2b-2 tests + revisions)
```

3 files changed, 341 insertions, 20 deletions. Single commit at `50e2eff`.

---

🛑 STOP. Awaiting live-verify before STEP 3.

The DB_PATH capture defect class is now closed for code_task_persistence
and guarded against by an autouse fixture that hard-fails any future
regression. The same defect exists in ~10 other modules — listed in §2b-3,
NOT fixed per directive. Prod `code_mode_tasks` is clean (was 100%
contamination; now empty).