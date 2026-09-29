# R1 BRAIN MIGRATION — 2026-08-22

## Phase 0 — SAFETY NET (DONE)
## Phase 1 — BRAIN WRITERS (DONE, with addendum)
## Phase 2 — COPY (DONE)
## Phase 3 — VERIFICATION GATE (PASS)
## Phase 4 — REPOINT THE CODE (DONE, commit e07881c, pushed)

## Phase 5 — PROVE NEW WRITES LAND CANONICAL

### 5.0 — git push
```
$ cd ~/empire-repo-main && git push origin feature/drawing-standard
To github.com:r22gir/Empire.git
   95d94bc..e07881c  feature/drawing-standard -> feature/drawing-standard
```
Commit pushed. Not on a single disk anymore.

### 5.1 — Baseline mtimes (before traffic)

**CANONICAL `/home/rg/empire-data/brain/`:**
| File | mtime |
|---|---|
| memories.db | 2026-08-22 12:25:16 |
| token_usage.db | 2026-08-22 11:30:31 |
| unified_messages.db | 2026-08-22 08:00:03 |
| ~/empire-repo-main/max/memory.md | 2026-08-20 16:49:48 |

(Note: `memories.db` already at 12:25 because the backend's first import ran `init_db()` (idempotent CREATE TABLE) after Phase 4 daemon-reload. This is expected — it proves the writer path is already live on canonical.)

**OLD LANE `/home/rg/empire-repo/`:**
| File | mtime |
|---|---|
| backend/data/brain/memories.db | 2026-08-22 11:30:27 |
| backend/data/brain/token_usage.db | 2026-08-22 11:30:31 |
| backend/data/brain/unified_messages.db | 2026-08-22 08:00:03 |
| max/memory.md (branch-3 candidate) | 2026-08-22 03:00:02 |
| backend/data/max/memory.md (backup, was freeze-breaker) | 2026-08-21 23:00:00 |
| backend/data/max/supermemory_scaffold.jsonl | 2026-08-19 22:42:50 |
| backend/data/max/session_handoff.json | 2026-08-19 22:42:50 |

### 5.2 — Traffic (real chat that fires unified_message_store)

```
$ curl -X POST http://localhost:8000/api/v1/max/chat \
    -H 'Content-Type: application/json' \
    -d '{"message":"Phase 5 verification ping — record this turn…","channel":"web","conversation_id":"r1-verify"}'

{"response":"**Phase 5 verification ping — honest report (no fabrication)**\n\n**✅ Verified against live data:**\n- Canonical brain path `/home/rg/empire-data/brain/` exists…"}
```
HTTP 200, response delivered. This call went through:
- `unified_store.add_message(...)` → writes to unified_messages.db
- Token tracking → writes to token_usage.db
- Possibly memory extraction → writes to memories.db

### 5.3 — Post-traffic mtimes (after 20s settle)

**CANONICAL** — ALL ADVANCED:
| File | mtime (new) | Δ |
|---|---|---|
| memories.db | 2026-08-22 12:28:03 | +3 min from baseline |
| token_usage.db | 2026-08-22 12:27:59 | ~57 min from copy-time baseline |
| unified_messages.db | 2026-08-22 12:27:59 | ~4.5 hours from checkpoint baseline |
| max/memory.md | 2026-08-20 16:49:48 | UNCHANGED (only `brain_sync` writes this; runs at 23:00) |

**OLD LANE** — ALL FROZEN at pre-Phase-2 timestamps:
| File | mtime | Δ |
|---|---|---|
| backend/data/brain/memories.db | 2026-08-22 11:30:27 | UNCHANGED |
| backend/data/brain/token_usage.db | 2026-08-22 11:30:31 | UNCHANGED |
| backend/data/brain/unified_messages.db | 2026-08-22 08:00:03 | UNCHANGED |
| max/memory.md (branch-3 candidate) | 2026-08-22 03:00:02 | UNCHANGED |
| backend/data/max/memory.md (backup) | 2026-08-21 23:00:00 | UNCHANGED |
| backend/data/max/supermemory_scaffold.jsonl | 2026-08-19 22:42:50 | UNCHANGED |
| backend/data/max/session_handoff.json | 2026-08-19 22:42:50 | UNCHANGED |

### 5.4 — Counts (proof beyond mtimes)

| Table | Before traffic | After traffic | Δ |
|---|---|---|---|
| CANONICAL `memories.memories` | 25717 | **25724** | +7 |
| CANONICAL `token_usage.token_usage` | 58842 | **58845** | +3 |
| CANONICAL `unified_messages.unified_messages` | 22854 | **22856** | +2 |
| OLD LANE  `memories.memories` | 25717 | 25717 | 0 |
| OLD LANE  `token_usage.token_usage` | 58842 | 58842 | 0 |
| OLD LANE  `unified_messages.unified_messages` | 22854 | 22854 | 0 |

Canonical advanced on all three tables. Old lane is at the exact Phase 2 copy row counts.

### 5.5 — Corridor sanity
```
200 /api/v1/quotes-v2/stats
200 /api/v1/crm/customers?limit=5
200 /api/v1/jobs/dashboard
```

### 5.6 — OpenClaw heartbeat (R2 scope, expected to advance)
```
backend/data/max/openclaw_worker_heartbeat.json  mtime=2026-08-22 12:28:21
```
The live openclaw worker (PID under `/home/rg/empire-repo/openclaw`) writes its heartbeat here directly. The dispatch explicitly excludes `empire-openclaw.service` (R2). This file advancing is expected and out of R1 scope.

### 5.7 — Phase 5 verdict

| Check | Result |
|---|---|
| Canonical `memories.db` advanced | ✅ (+7 rows) |
| Canonical `token_usage.db` advanced | ✅ (+3 rows) |
| Canonical `unified_messages.db` advanced | ✅ (+2 rows) |
| Canonical `max/memory.md` advanced | ⏸ unchanged (brain_sync is nightly at 23:00; tonight's run will prove it lands canonical) |
| Old lane `brain/memories.db` frozen | ✅ (mtime still 11:30:27 from before Phase 2) |
| Old lane `brain/token_usage.db` frozen | ✅ (mtime still 11:30:31 from before Phase 2) |
| Old lane `brain/unified_messages.db` frozen | ✅ (mtime still 08:00:03 from before Phase 2) |
| Old lane `max/memory.md` (branch-3 candidate) frozen | ✅ (mtime still Aug 22 03:00:02) |
| Old lane `backend/data/max/memory.md` (backup) frozen | ✅ (mtime still Aug 21 23:00:00) |
| Old lane `supermemory_scaffold.jsonl` frozen | ✅ (mtime still Aug 19 22:42:50) |
| Old lane `session_handoff.json` frozen | ✅ (mtime still Aug 19 22:42:50) |
| Corridor endpoints | ✅ all 200 |
| Writer missed | **NONE** |

**The migration is COMPLETE.** Canonical advances. Old lane is frozen across all R1-scoped files. The only old-lane file still advancing is `openclaw_worker_heartbeat.json`, which is R2 scope.

---

## FINAL REPORT

```
PHASE REACHED: 5/5
BRAIN COUNTS CANONICAL: memories=25724 summaries=N/A unified=22856 tokens=58845
OLD LANE FROZEN: YES (all 7 R1-scoped files at pre-Phase-2 timestamps)
COMMIT: e07881c (pushed to origin/feature/drawing-standard)
```

## VERIFIED
- Phase 3 count gate (4 tables ≥ dispatch baseline)
- Phase 3 integrity check (all 3 DBs `ok`)
- Phase 4 backend health (HTTP 200, `/api/v1/max/health` healthy, 17 desks)
- Phase 4 `/proc` env proof (MAX_MEMORY_PATH, EMPIRE_BRAIN_DIR, EMPIRE_DATA_DIR all present in PID 955477)
- Phase 5 traffic → canonical advance (+7, +3, +2 rows across the three brain DBs)
- Phase 5 old lane frozen (mtimes match pre-Phase-2 to the second)
- Phase 5 corridor endpoints (200 across /quotes-v2/stats, /crm/customers, /jobs/dashboard)
- Phase 4 commit `e07881c` pushed to `origin/feature/drawing-standard`

## INFERRED
- Branch-3 fallback at `~/empire-repo/max/memory.md` was written to once (Aug 22 03:00) by some mechanism between Aug 21 23:00 brain_sync and now — I cannot determine what from these logs. With branch 3 removed in commit `e07881c`, no future brain_sync can land there.
- The openclaw_worker_heartbeat.json will continue to advance in old lane until the worker is relocated (R2). Out of R1 scope per dispatch.

## COULD NOT PROBE
- What process created `~/empire-repo/max/memory.md` at Aug 22 03:00 with the April 28 AUTO-SYNC content. Logs don't reveal it.
- Why `unified_messages.db` main file shows mtime 08:00:03 (WAL artifact, explained in Phase 1 addendum — confirmed by Phase 3 integrity ok and Phase 5 row counts).

## ROLLBACK STATE — clean

**Phase 2/3 rollback path** (canonical corrupted):
```bash
cd /home/rg/empire-data/brain
for f in memories token_usage unified_messages; do mv -v "$f.db.pre-R1-20260822" "$f.db"; done
systemctl --user restart empire-backend.service
```
Old-lane files still at pre-Phase-2 state, can be re-copied if needed.

**Phase 4/5 rollback path** (code change broken):
```bash
cd ~/empire-repo-main
git revert e07881c
# Remove the two Environment= lines from zz-canonical-venv.conf
systemctl --user daemon-reload && systemctl --user restart empire-backend.service
```

**Everything else** (worst case): snapshot in `~/backups/pre-R1-2026-08-22/` (6 files, 99MB) + `.pre-R1-20260822` originals in canonical + pre-Phase-2 state of old lane.

---
