# H81 Phase 2B · Task B · Proof-row purge

**Date:** 2026-09-01
**Repo:** `~/empire-repo-main` · branch `feature/drawing-standard` · HEAD `dd72de8`
**Audit DB:** `~/empire-repo/backend/data/tool_audit.db` (live, NOT moved this dispatch)
**Pre-purge rows (round 1):** 7,942 → **7,932** (10 deleted)
**Pre-purge rows (round 2):** 7,932 → **7,928** (4 deleted)
**Total deleted across both rounds:** 14 (matches the dispatch's "ten" plus the four pytest leftovers the founder subsequently ruled to purge as the same class of artefact)
**Backups retained:** `tool_audit.db.bak-20260901T181532Z` (pre-round-1, 7,942 rows) and `tool_audit.db.bak-20260901T190316Z` (pre-round-2, 7,932 rows)

---

## B1 — Backups (two, one per round)

### Round 1 backup
```
$ cp -p ~/empire-repo/backend/data/tool_audit.db \
       ~/empire-repo/backend/data/tool_audit.db.bak-20260901T181532Z
backup path:  /home/rg/empire-repo/backend/data/tool_audit.db.bak-20260901T181532Z
backup bytes: 1,929,216 (matches source byte-for-byte; cp -p preserves mode 600 + mtime)
backup opens: yes — 7,942 rows, max id 7942
B1 VERIFIED
```

### Round 2 backup (do not overwrite)
```
$ cp -p ~/empire-repo/backend/data/tool_audit.db \
       ~/empire-repo/backend/data/tool_audit.db.bak-20260901T190316Z
backup path:  /home/rg/empire-repo/backend/data/tool_audit.db.bak-20260901T190316Z
backup bytes: 1,929,216
backup opens: yes — 7,932 rows (post-round-1, pre-round-2 state)
```

### State of all three files at start of round 2
```
src            rows=7932
bak-181532Z    rows=7942   (pre-round-1, frozen)
bak-190316Z    rows=7932   (pre-round-2, frozen)
```

Both backups retained per dispatch B5 ("Do NOT delete the backup. It stays until the founder says otherwise").

---

## B2 — Row identification

The dispatch enumerates IDs **7929-7938** as the ten proof rows to delete. The DB actually contained **fourteen** rows beyond the 7,928 baseline:

- **IDs 7929-7938 (10 rows) — in dispatch purge list.** Written by the four inline `python3 -c "..."` proof scripts during Phase 2 Task 2. All carry `channel='web'` or `channel='telegram'` because the scripts passed `channel=` directly to `execute_tool()`. **DELETED.**
- **IDs 7939-7942 (4 rows) — NOT in dispatch purge list.** Written by the `pytest tests/test_founder_pin_failclosed_hotfix4_2.py` run during Phase 2 Task 1 verification. All carry `channel=None` because the tests do not pass `channel=` to `execute_tool()`. **REMAIN.** See "Open question for founder" at end.

### Full record of every deleted row

#### id=7929 — IN DISPATCH PURGE LIST
```
    id             = 7929
    timestamp      = '2026-09-01T16:17:01.234395'
    tool           = 'shell_execute'
    params         = {'command': 'echo proof_task2_ok'}
    result         = {'returncode': 0, 'stdout_len': 15, 'stderr_len': 0}
    access_level   = 2
    approved_via   = None
    desk           = None
    success        = 1
    duration_ms    = 0
    channel        = 'web'
    founder        = 1
```

#### id=7930 — IN DISPATCH PURGE LIST
```
    id             = 7930
    timestamp      = '2026-09-01T16:17:01.332148'
    tool           = 'env_set'
    params         = {'name': 'H81_TASK2_TEST_VAR'}
    result         = 'set'
    access_level   = 2
    approved_via   = None
    desk           = None
    success        = 1
    duration_ms    = 0
    channel        = 'telegram'
    founder        = 1
```

#### id=7931 — IN DISPATCH PURGE LIST
```
    id             = 7931
    timestamp      = '2026-09-01T16:17:01.394933'
    tool           = 'env_set'
    params         = {'name': ''}
    result         = 'missing_name'
    access_level   = 2
    approved_via   = None
    desk           = None
    success        = 0
    duration_ms    = 0
    channel        = 'web'
    founder        = 1
```

#### id=7932 — IN DISPATCH PURGE LIST
```
    id             = 7932
    timestamp      = '2026-09-01T16:17:50.386919'
    tool           = 'shell_execute'
    params         = {'command': 'echo proof_task2_redo_ok'}
    result         = {'returncode': 0, 'stdout_len': 20, 'stderr_len': 0}
    access_level   = 2
    approved_via   = None
    desk           = None
    success        = 1
    duration_ms    = 0
    channel        = 'web'
    founder        = 1
```

#### id=7933 — IN DISPATCH PURGE LIST
```
    id             = 7933
    timestamp      = '2026-09-01T16:17:50.461529'
    tool           = 'shell_execute'
    params         = {'command': 'rm -rf /tmp/nope'}
    result         = 'blocked:rm -rf /'
    access_level   = 2
    approved_via   = None
    desk           = None
    success        = 0
    duration_ms    = 0
    channel        = 'web'
    founder        = 1
```

#### id=7934 — IN DISPATCH PURGE LIST
```
    id             = 7934
    timestamp      = '2026-09-01T16:17:50.636026'
    tool           = 'shell_execute'
    params         = {'command': 'curl https://evil.example'}
    result         = {'returncode': 6, 'stdout_len': 0, 'stderr_len': 284}
    access_level   = 2
    approved_via   = None
    desk           = None
    success        = 1
    duration_ms    = 0
    channel        = 'telegram'
    founder        = 0
```

(`success=1` with `returncode=6` documents the H85 "success=1 does not mean the command succeeded" finding now in the Phase 3 backlog.)

#### id=7935 — IN DISPATCH PURGE LIST
```
    id             = 7935
    timestamp      = '2026-09-01T16:18:28.944024'
    tool           = 'shell_execute'
    params         = {'command': 'echo proof_task2_final'}
    result         = {'returncode': 0, 'stdout_len': 18, 'stderr_len': 0}
    access_level   = 2
    approved_via   = None
    desk           = None
    success        = 1
    duration_ms    = 0
    channel        = 'web'
    founder        = 1
```

#### id=7936 — IN DISPATCH PURGE LIST
```
    id             = 7936
    timestamp      = '2026-09-01T16:18:29.022686'
    tool           = 'shell_execute'
    params         = {'command': 'rm -rf /tmp/blocked_test'}
    result         = 'blocked:rm -rf /'
    access_level   = 2
    approved_via   = None
    desk           = None
    success        = 0
    duration_ms    = 0
    channel        = 'web'
    founder        = 1
```

#### id=7937 — IN DISPATCH PURGE LIST
```
    id             = 7937
    timestamp      = '2026-09-01T16:18:29.090013'
    tool           = 'env_set'
    params         = {'name': 'H81_TASK2_FINAL_VAR'}
    result         = 'set'
    access_level   = 2
    approved_via   = None
    desk           = None
    success        = 1
    duration_ms    = 0
    channel        = 'telegram'
    founder        = 1
```

#### id=7938 — IN DISPATCH PURGE LIST
```
    id             = 7938
    timestamp      = '2026-09-01T16:18:29.164345'
    tool           = 'env_set'
    params         = {'name': ''}
    result         = 'missing_name'
    access_level   = 2
    approved_via   = None
    desk           = None
    success        = 0
    duration_ms    = 0
    channel        = 'web'
    founder        = 0
```

### Full record of every row NOT in the dispatch list (still present)

#### id=7939 — NOT IN DISPATCH LIST — pytest Task 1 run
```
    id             = 7939
    timestamp      = '2026-09-01T16:26:48.363264'
    tool           = 'shell_execute'
    params         = {'command': 'ls /tmp'}
    result         = {'returncode': 0, 'stdout_len': 40963, 'stderr_len': 0}
    access_level   = 2
    approved_via   = None
    desk           = None
    success        = 1
    duration_ms    = 0
    channel        = None
    founder        = 0
```

#### id=7940 — NOT IN DISPATCH LIST — pytest Task 1 run
```
    id             = 7940
    timestamp      = '2026-09-01T16:26:49.013426'
    tool           = 'shell_execute'
    params         = {'command': 'echo hi'}
    result         = {'returncode': 0, 'stdout_len': 3, 'stderr_len': 0}
    access_level   = 2
    approved_via   = None
    desk           = None
    success        = 1
    duration_ms    = 0
    channel        = None
    founder        = 1
```

#### id=7941 — NOT IN DISPATCH LIST — pytest Task 1 run
```
    id             = 7941
    timestamp      = '2026-09-01T16:27:41.557033'
    tool           = 'shell_execute'
    params         = {'command': 'ls /tmp'}
    result         = {'returncode': 0, 'stdout_len': 40997, 'stderr_len': 0}
    access_level   = 2
    approved_via   = None
    desk           = None
    success        = 1
    duration_ms    = 0
    channel        = None
    founder        = 0
```

#### id=7942 — NOT IN DISPATCH LIST — pytest Task 1 run
```
    id             = 7942
    timestamp      = '2026-09-01T16:27:42.180778'
    tool           = 'shell_execute'
    params         = {'command': 'echo hi'}
    result         = {'returncode': 0, 'stdout_len': 3, 'stderr_len': 0}
    access_level   = 2
    approved_via   = None
    desk           = None
    success        = 1
    duration_ms    = 0
    channel        = None
    founder        = 1
```

---

## B3 — Deletion performed (two rounds)

### Round 1: dispatch-named IDs 7929-7938

```
BEFORE — total rows: 7942
deleting IDs: [7929, 7930, 7931, 7932, 7933, 7934, 7935, 7936, 7937, 7938]
DELETE rowcount: 10
AFTER  — total rows: 7932
difference: 10  (expected: 10)
remaining IDs >= 7929: [7939, 7940, 7941, 7942]
```

### Round 2: pytest leftover IDs 7939-7942 (founder ruling, same class of artefact)

```
BEFORE — total rows: 7932
deleting IDs: [7939, 7940, 7941, 7942]
DELETE rowcount: 4
AFTER  — total rows: 7928
difference: 4  (expected: 4)
expected absolute: 7932 -> 7928  (matches dispatch's stated expectation)
remaining IDs >= 7928: [7928]
  (7928 is the highest pre-Phase-2 baseline row — not a leftover, it was
   already in the DB before Phase 2 began and is the natural top-of-table
   after every Phase 2 row was deleted)
```

Both rounds used explicit ID lists. No WHERE clause on `tool`, no timestamp range. 7,928 rows in total are untouched across both rounds.

---

## B4 — Verification (final state)

### Timestamp range

```
MIN timestamp: 2026-03-17T02:43:38.822907   (matches map Appendix B baseline exactly)
MAX timestamp: 2026-09-01T13:11:04.189331   (last pre-Phase-2 baseline row, NOT a proof row)
```

The MIN is unchanged from the pre-Phase-2 baseline. The MAX is one of the baseline rows; no proof row remains.

### Per-tool counts vs map Appendix B

| tool | map Appendix B | actual | diff |
|---|---:|---:|---:|
| file_read | 6364 | 6364 | +0 |
| git_ops | 574 | 574 | +0 |
| file_write | 431 | 431 | +0 |
| db_query | 322 | 322 | +0 |
| search_conversations | 92 | 92 | +0 |
| file_append | 62 | 62 | +0 |
| service_manager | 47 | 47 | +0 |
| test_runner | 15 | 15 | +0 |
| file_edit | 14 | 14 | +0 |
| project_scaffold | 6 | 6 | +0 |
| package_manager | 1 | 1 | +0 |

**All 11 Appendix B tools match exactly. No real row was touched.**

### Tools present in DB but NOT in Appendix B

```
(none — purge complete)
```

### Count summary

- Pre-purge: 7,942
- Post-round-1: 7,932 (matches dispatch's "expected 7938" minus the 4 pytest leftovers)
- Post-round-2: **7,928** (matches dispatch's stated "expected 7928" exactly)

---

## B5 — Backups retained

```
$ ls -la /home/rg/empire-repo/backend/data/tool_audit.db.bak-*
-rw------- 1 rg rg 1929216 Sep  1 12:27 tool_audit.db.bak-20260901T181532Z  (pre-round-1, 7942 rows)
-rw------- 1 rg rg 1929216 Sep  1 14:16 tool_audit.db.bak-20260901T190316Z  (pre-round-2, 7932 rows)
```

Both backups retained per dispatch B5 ("Do NOT delete the backup. It stays until the founder says otherwise"). The 181532Z backup is NOT overwritten; it preserves the pre-round-1 state including the 10 dispatched-named rows.

---

## Standing-rule compliance note (from the dispatch)

> Any future task proving audit behaviour points `TOOL_AUDIT_DB` (or the equivalent) at a temp file, or uses a fixture DB, and shows the temp path in the report. This is mechanized, not instructed — if there is no env override on the path today, say so and propose one rather than writing to production again. The Phase 2 rows are being purged because the dispatch did not specify isolation. That was the dispatch's defect.

Phase 2B Task B itself is a purge task — it had to operate on the live path because the rows being purged ARE the proof rows. This is the explicit exception the dispatch permits ("the proof needs to remove itself"). All future audit-behavior proofs will use `TOOL_AUDIT_DB=<tempfile>` per the standing rule. No env override exists today; Task A4's proposed override is still pending founder ruling (deferred to Phase 3).

---

## Backlog added by this dispatch

- **The Phase 2 Task 1 pytest suite wrote to the production audit DB.** Rows 7939-7942 (now purged, full records above) prove this happened. Pytest is NOT production-shaped traffic — it is a test run, and a test run writing to the live audit trail is the H61-class failure the standing rule exists to prevent. The rule does not exempt pytest; it is the main thing the rule is for.
- **Distinguishing proof rows from production rows in this incident was incidental, not a mechanism.** The four pytest rows were distinguishable only because `channel=None` (pytest tests do not pass `channel=` to `execute_tool()`). The 10 inline-script rows had `channel='web'` or `channel='telegram'`. There is no general mechanism in the audit DB to distinguish "this row came from a test" from "this row came from production" — both kinds carry the same schema, the same FOUNDER_PIN validation, the same everything. The fix is not "add a column"; it is "pytest must run against a different DB." That is `TOOL_AUDIT_DB` (Task A4 proposal, Phase 3).
- **success=1 does not mean the command succeeded** (H85). Row 7934 documents the case: `subprocess.run` returned non-zero (curl DNS fail, returncode 6) without raising, and my Task 2 logging marked `success=1`. The audit row is therefore unreliable as evidence that the command did what the founder wanted. `success` should reflect `returncode == 0` (or the equivalent for non-subprocess tools). Deferred to Phase 3.
- **access control is skipped for unresolvable users** (H84). Phase 2B Task A showed that founder=False with `resolve_user()` returning `None` skips the entire `access_controller` permission block (deny/locked/confirm/pin) because the flow is gated on `if user:`. In production the same path means any caller the controller cannot identify passes through the permission layer untouched and lands on the PIN gate alone. The PIN gate currently catches it. It matters in Phase 3 where unidentified callers stop being impossible. No hazard file; deferred to Phase 3.

---

*Commit nothing this task — the DB is gitignored and lives outside the repo. Report only. Report at `reports/2026-09-01_h81_phase2b_task_b_purge.md`, not committed.*
