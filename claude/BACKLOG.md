# BACKLOG — EmpireBox canonical-repo fixes

**This is a STUB register.** The authoritative task register delta is
in `claude/BACKLOG_UPDATE_2026-08-19.md` (already committed alongside
this stub in `claude/`). This stub exists inside the repo so the
stale-fixture list has a home and is not lost in a test-file doc
block.

## H57 Phase 3 follow-up — stale-fixture list (STUB)

**Context:** H57 Phase 3 (commit `59d356d`) made the stale fork
`~/empire-repo/` UNREACHABLE for MAX's tools. The runtime fix is in
place. These test fixtures still encode the OLD default-root
behavior and will FAIL after the runtime fix. They are STALE — not
broken by H57, but visible-because-of-H57. The fix per fixture is
to update the assertion to use the canonical resolver
(`canonical_path.resolve_path_under_canonical_root`).

**Count: 5 named files** below + an undetermined number of "others in
backend/tests/ that hardcode the path" referenced in
`tests/test_h57_canonical_root.py`'s trailing doc block.

**Files asserting the OLD default-root behavior (STALE after H57):**

1. `backend/tests/test_canonical_pricing_engine.py` — asserts path
   patterns under `~/empire-repo/backend/data/quotes`
2. `backend/tests/test_dev_git_runtime_truth.py` — runtime-truth
   checks; may assume stale-fork git cwd
3. `backend/tests/test_drawing_flow_wiring_hotfix4_0.py` —
   references `~/empire-repo/uploads` in source-file inspection
4. `backend/tests/test_openclaw_worker.py` — likely asserts
   stale-fork output paths
5. `backend/tests/test_payments_webhook_fail_closed.py` — uses
   `~/empire-repo/backend/data/apostapp/orders` in path setup

**Disposition:** DO NOT fix in H57. Per dispatch rule "those
assertions encode the bug … rewriting them would hide a real staleness
debt in an unrelated commit." They will be addressed in a separate
lane. The runtime is correct; the fixtures need updating to reflect
the canonical resolver.

**Tracking:** the test file `tests/test_h57_canonical_root.py` had a
trailing doc block with this list — REMOVED here (the list moves
to this register; the test file no longer carries the register).

## Other deferred items (H57 Phase 3 follow-up)

- `backend/app/services/max/self_heal.py:9` —
  `REPO_PATH = "~/empire-repo"` (module-level constant)
- `backend/app/services/max/maintenance_manager.py:21` —
  same
- `backend/app/services/max/code_task_runner.py:301,409,423` —
  paths and cwds to `~/empire-repo`
- `backend/app/services/max/desks/codeforge_desk.py:74` —
  same
- `backend/app/routers/recovery.py:1082,1085` — venv_python, cwd
- `backend/app/routers/apostapp*.py:24,33,39` — BASE_DIRs
- `backend/app/routers/quotes.py:1491` — uploads_dir (FIXED in
  H57 Phase 3 — `resolve_path_under_canonical_root`)
- `backend/app/routers/quotes.py:2818` — generated_path (FIXED)
- `backend/app/services/openclaw_worker.py:1173` — REPO_DIR
- `backend/app/services/openclaw_worker.py:1324` — drawings dir
  (FIXED)

**Per dispatch:** "log only — same class, not MAX's read path, not
writing client data. One lane at a time." These will be addressed in
a separate canonical-repo cleanup pass, NOT in H57.

## What changed in H57 Phase 3

**Runtime (live, in commit `59d356d`):**
- `tool_safety.ALLOWED_ROOTS` removed `~/empire-repo/` (the stale
  fork is no longer a valid root)
- `.empire-canonical` marker created at repo root
- `canonical_path.resolve_canonical_root` added — marker walk-up
  + token verification
- `canonical_path.resolve_path_under_canonical_root` added — the
  single validator
- `validate_path` in `tool_safety.py` now delegates to canonical
  resolver
- `_file_read`, `_file_write`, `_shell_execute` cwd, `system_prompt`
  git cwd, `quotes.py uploads_dir`, `quotes.py generated_path`,
  `openclaw_worker.py drawings_dir` — all resolve via canonical
  resolver

**Runtime follow-up (commit `d55031e`):**
- `..` segment refusal in `resolve_path_under_canonical_root` — a
  path like `backend/data/uploads/../../../etc/passwd` resolves to
  `canonical/etc/passwd` under `Path.resolve()` semantics, which
  was returning OK even though the user clearly INTENDED an escape.
  Fix: refuse any path containing `..` segments BEFORE resolution.
- `from __future__ import annotations` restored at top of
  `canonical_path.py` (had been left mid-file after an earlier
  string slice).

## Stub marker

This file is a STUB. The authoritative register delta is in
`claude/BACKLOG_UPDATE_2026-08-19.md` (already committed in the same
directory). When the merge happens, this stub can be deleted (or
kept as a local shadow — depends on governance preference at that time).
