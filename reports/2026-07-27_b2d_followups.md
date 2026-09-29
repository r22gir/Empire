# B2d Follow-Ups — Rescue List (2026-07-27)

**Why this file exists:** The original "Pause B2d follow-up tasks for next session" task never completed before this session's memory was at risk of being lost. Per DISPATCH 1 directive (2026-07-27), the B2d follow-up list is being written to this file so it survives across sessions.

**Commit reference for the paused items:**
- B2d commit (the last paused era): `1c1ec66` — "hotfix B2d: Empire sheet style + fabric registry + re-authored gates"
- Golden port commit: `7dc23f3` — "hotfix golden-port: translate golden_flatfold.py → b2_renderers.py + re-author QC gates for golden v10 layout"
- This file's likely port-status update commit: `033d2e4` (golden-port stop-gate report) — written from this session

**Important:** The golden port (`7dc23f3`) rewrote `b2_renderers.py` (+1050/−712) and re-authored `b2_qc.py`. Many B2d-era paused items are now DEAD (resolved by the port). Each item below states explicitly whether the golden port resolved it.

---

## B2d-era follow-up items (per the paused task list)

### 1. B2d follow-ups: visual tweaks after founder re-verify
- **Files:** `backend/app/services/drawing/templates/b2_renderers.py`, `reports/2026-07-25_b2d.md`
- **Why paused (2026-07-26):** Wait for founder eyeball verification of the B2d sheet before visual tweaks
- **Status post-golden-port:** **DEAD.** The golden port (commit `7dc23f3`) is the founder-approved replacement for the B2d layout. The visual tweaks would now apply to the golden v10 layout, not B2d. If tweaks are needed, they should be folded into a future golden-layout iteration (the next round of golden refinement). The B2d report file is now historical (kept as `reports/2026-07-25_b2d.md` per the "Reports SHOW renders" doctrine — superseded by the golden report `reports/2026-07-26_golden_port.md`).
- **Action if resurrected:** N/A — if a tweak is needed, open a new task against the golden port, not B2d.

### 2. GP1/GP2 LuxeForge intake audit then fix
- **Files:** `backend/app/routers/luxeForge_intake*.py` (search the repo), `backend/app/main.py`, `backend/app/services/max/`, `backend/app/services/max/ecosystem_catalog.py`, `backend/app/db/`
- **Why paused (2026-07-26):** Per STATE.md §ACTIVE DIRECTIVES, GP1/GP2 was queued as "after B2d verify" — sequentially after the sheet standard settled.
- **Status post-golden-port:** **ALIVE — NOT RESOLVED.** The golden port was a rendering-side change; LuxeForge intake is a separate revenue path. Per DISPATCH 2 (2026-07-27) the founder has now escalated GP1/GP2 to immediate priority and provided the break-map directive. **This is the highest-value item on the board.** A fresh session will execute DISPATCH 2 immediately after DISPATCH 1 reports in.
- **Action if resurrected:** Read DISPATCH 2 (in the founder's 2026-07-27 terminal message) for the full break-map directive. The session that does this MUST be a fresh M3 session that can verify via curl, db query, etc. — NOT a "synthesized" follow-up.

### 3. Family rollout: Drapery → Bench/Banquette → Valance → Cornice → Headboard
- **Files:** `backend/app/services/drawing/templates/` (Drapery.py, BenchCurved.py, Valance.py, Cornice.py, HeadboardChannel.py already exist as templates), `backend/app/services/drawing/templates/registry.py`
- **Why paused (2026-07-26):** "One family/feature per commit" — the family rollout is sequenced to inherit the golden-port template; each family should commit its port as a separate change. The plan is: Drapery first (largest palette, first to inherit), then Bench → Valance → Cornice → Headboard.
- **Status post-golden-port:** **READY — WAITING ON FOUNDER VERDICT.** The golden port establishes the layout + doctrine template that every family will inherit. Per DISPATCH 1's "Verdict" rule: "PASS → family rollout unblocks (Drapery first)." So the rollout unblocks as soon as the founder signs off the golden port.
- **Action if resurrected:** Once founder passes the golden verdict, do Drapery first. The Drapery template (`backend/app/services/drawing/templates/drapery.py` if it exists; check the templates dir) should be ported using the SAME 10-rule doctrine + the 2 new QC rules. The family-specific fabric motif (drape pleats vs flat-folds) is the only meaningful divergence from the flat-fold template.

### 4. Drawing/file delivery: GET /api/v1/drawings/{filename}
- **Files:** `backend/app/routers/drawings.py` (search), `backend/app/main.py`
- **Why paused (2026-07-26):** Per STATE.md §ACTIVE DIRECTIVES, this is queued after the golden port verifies (so any new file-delivery hooks can use the new layout signature).
- **Status post-golden-port:** **ALIVE — NOT RESOLVED.** Drawing/file delivery is independent of the layout; it touches routing, the canonical `data/drawings/` path, and the QC "traversal-safe filename" rule (per CLAUDE.md CANONICAL PATHS).
- **Action if resurrected:** Search the routers for a `GET /api/v1/drawings/{filename}` route. Verify the route is wired in `backend/app/main.py` (the real app — `backend/main.py` is a 26-line stub and any change there is dead code). Add a traversal-safe handler if missing. Add a test that does an E2E GET against a real PDF on disk.

### 5. Remaining ledger: Hotfixes 4.3–4.6, Items 5/6/7/1e
- **Files:** various — must be re-discovered from STATE.md
- **Why paused (2026-07-26):** Cross-referenced from STATE.md; the prior M3 session was operating in single-lane mode and these were queued after the drawing rollout.
- **Status post-golden-port:** **UNKNOWN — these were never re-discovered in the current session.** They are items on STATE.md that were referenced but never re-stated in full. **The current session cannot reconstruct them with confidence**; a fresh session with STATE.md access should re-derive them.
- **Action if resurrected:** Read STATE.md fresh, identify the 4 hotfixes (4.3, 4.4, 4.5, 4.6) and 4 items (5, 6, 7, 1e) by their original descriptions. Treat the descriptions as authoritative — do NOT infer from filenames or commit messages alone.

### 6. Label Station deployment: BLOCKED
- **Files:** `/home/rg/label-station/DEPLOY_LABEL_STATION.md` (does NOT exist on this machine), `backend/app/modules/static/weigh-and-label.html` (DO NOT TOUCH — see DISPATCH 1 reason below), `backend/app/modules/label_station.py` (does NOT exist on this machine)
- **Why blocked (2026-07-26):** Files missing from `/home/rg/label-station/` directory.
- **Status post-golden-port:** **NOW LIVE — DO NOT EXECUTE.** Per DISPATCH 1 (2026-07-27), the founder verified the label station is ALREADY deployed and live at `https://label.empirebox.store/label/api/health` (returns `{"ok":true,"module":"label_station","max_products":10}`). The live build is AHEAD of `DEPLOY_LABEL_STATION.md` and has configurable QR tokens, Brother AirPrint support, shareable setup links, and multiple label stock sizes. **Re-deploying the July-26 file would silently regress the tool.** Two tasks on the prior task list ("Read DEPLOY_LABEL_STATION.md" and "Execute Label Station deployment") were STALE and have been struck per DISPATCH 1.
- **Action if resurrected:** NONE — this item is now complete. The corresponding B2d-era tasks "Read DEPLOY_LABEL_STATION.md" and "Execute Label Station deployment" have been marked as deprecated and removed from the active task list.

---

## Additional paused items from STATE.md §ACTIVE DIRECTIVES that were NOT in the prior task list

The following items appear in STATE.md but were not on the session's active task list when it paused. Including them here for completeness — a fresh session may re-derive them from STATE.md before resuming work.

- **M3 session health check (`/model`):** Check MiniMax M3 — the directive states "model can silently downgrade". Before any new work in a future session, run `/model` to confirm M3.
- **OpenClaw / OpenCode cleanup:** Per CLAUDE.md ENVIRONMENT NOTES, OpenClaw (localhost:7878) has a 7k+ queue backlog and OpenCode daemon should stay dead. If any new session sees them active, kill them.

---

## What this file is NOT

This is NOT a task list to execute in order. It is a **rescue manifest** — a record of what was paused, what was resolved, and what is alive. A fresh session that opens this file should:

1. Read CLAUDE.md (canonical paths + doctrine)
2. Read STATE.md (current directives)
3. Re-derive any active items from STATE.md (do NOT trust this file as the authoritative task list — STATE.md is)
4. Strike items that are dead (the golden port resolved many visual/layout items)
5. For alive items, plan the work in single-lane mode

**Truth rule:** this file is honest about what is known. It is intentionally NOT padded with reconstructions. Where a B2d-era item is uncertain (e.g., the contents of Hotfix 4.3), the file says so. An honest gap beats an invented task.
