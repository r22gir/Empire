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

## Document Template Engine (P1-T) — master status, 2026-08-21

### G2 collision gate (synthesized portrait)

- **G2 status as of 2026-08-21:** **LIVE** since commit `1c56eb0`
  (2026-08-20). The gate has been reading real bboxes since the
  `placed_local` → `placed_global` wiring fix in `assemble.py`.
  Pre-`1c56eb0`, the gate ran on an empty accumulator (every gate
  trivially passed) — **four rounds of tuning on 8/20 fixed that**.
- **9 "REAL" entries from `reports/2026-08-20_g2_triage.md`:** all
  closed by 2026-08-21. The triage's classification was by bbox
  arithmetic, not by looking. After rasterising the cover at 150 DPI
  and cropping the sheet-index region, none of the 9 were real
  text-on-text overprints — they were a single root cause
  (chrome T()'s y-bbox over-estimates by ~7pt).
- **8pt chrome tolerance** at `gates.py:61` is a **workaround for
  the chrome T() y-bbox measurement bug**, not a typographic
  decision. Tagged in the source comment so nobody later treats it
  as a considered design value.

### Open items from 2026-08-20

- **H68 · Model-side fabrication from filename + STATE.md cues**
  (OPEN — founder decision, NOT a patch). 2026-08-20 19:11.
  MAX fabricated a 10-file renderer list under a non-existent
  directory. The fabrication is real (no `file_read` was ever
  called) but the underlying cause is the model treating contextual
  cues as proof. Four mitigation options in `claude/BACKLOG_UPDATE_
  2026-08-20.md` H68. Founder's decision. **Not in this lane.**

- **H69 · Tool-card footer overstates execution status** (OPEN —
  display bug, clear correct answer). 2026-08-20. The footer
  `parseToolBlocks` at `empire-command-center/.../ChatScreen.tsx:12`
  extracts tool-call names from the model's RESPONSE TEXT, not from
  the actual executed list. Founder read the footer as proof MAX
  had tried to read the file. **Same class as the ✅ Verified badge
  on stale output** — UI element overstating its own certainty. Not
  in this lane.

- **H70 · Per-class collision tolerance (CLOSED, shipped
  `b10af10`)** — chrome (letterspaced header/footer, label/value
  pairs) gets 8pt; body text keeps 1.2pt. Tagged in the source as
  a workaround. Negative fixture proves the chrome tolerance does
  not hide real body-text overprints.

- **H71 · chrome T() y-bbox over-estimates height by ~7pt**
  (OPEN — P1-T·d, NOT in this lane). The chrome T() function
  estimates height as `size × 0.78 ascender + size × 0.24
  descender = 1.02 × size`, when the real glyph extent is closer to
  `0.65 × size`. The 0.78 ascender factor claims the ascender
  extends ~78% of the way to the next line. Three rounds of
  tuning were spent on a phantom because nobody cropped the raster
  until asked. **Doctrine:** a gate that measures by approximation
  will invent defects and hide real ones. Fix is to measure the
  real glyph extent (PIL metrics or a font config). P1-T·d.

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
