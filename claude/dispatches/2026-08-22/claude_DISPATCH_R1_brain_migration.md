# DISPATCH R1 — BRAIN MIGRATION (WRITES · STOP-GATED)
**Date:** 2026-08-22 · **To:** M3 (Claude Code, EmpireDell)
**Predecessors:** `RESTORE_PROBE_2026-08-22.md`, `DB_TRUTH_FORK_2026-08-22B.md`
**Reference:** `EMPIREBOX_ORIENTATION_BRIEF_2026-08-22.md` §4, §5

**This dispatch writes.** Every prior dispatch was read-only. Read all rules
before running anything.

---

## WHAT THIS FIXES AND WHY

MAX's memory is split. The OLD LANE (`~/empire-repo`) holds the CURRENT brain;
canonical (`~/empire-data/brain/`) is two months stale.

| | canonical (Jun 23) | old lane (Aug 22) | delta |
|---|---|---|---|
| memories | 21,933 | **25,714** | +3,781 |
| conversation_summaries | 623 | **802** | +179 |
| unified_messages | 21,808 | **22,854** | +1,046 |
| token_usage | 57,533 | **58,841** | +1,308 |

Cause: canonical code writes to the old lane. One writer is confirmed —
`unified_message_store.py:16` hardcodes
`~/empire-repo/backend/data/brain/unified_messages.db`. **Other writers are
unidentified** (three DBs are fresh, one path is known), which is what Phase 1
resolves.

**ORDER IS FORCED: copy the brain FIRST, repoint the code SECOND.** Repointing
first silently reverts MAX to a June memory.

---

## HARD RULES

1. **🛑 STOP-GATED.** Phases 0–5 run in order. After each 🛑, STOP, report, and
   WAIT for founder go-ahead. Do not chain phases.
2. **DELETE NOTHING.** Old-lane files stay where they are, untouched, for the
   entire dispatch. Canonical originals are RENAMED, never overwritten.
3. **Report raw output.** A failed command is data. Report verbatim, then stop.
4. **If any verification count mismatches, STOP.** Do not "fix up" a partial
   copy. Do not proceed to code changes on unverified data.
5. `sqlite3` CLI is NOT installed. Use
   `~/empire-repo-main/backend/venv/bin/python` with the `sqlite3` module.
6. Known false alarms, do not chase: `max/memory.md` shows modified (that is
   the thing we are fixing); `FOUNDER_PIN env var is UNSET` is a false banner,
   the PIN is set (H59).
7. **Do not touch the system `empire-openclaw.service`** — that is R2, not this.
8. Repo doctrine: `~/empire-repo-main` is THE repo (`feature/drawing-standard`).
   `~/empire-repo` is the PREVIOUS PRODUCTION LANE, currently live. Treat it as
   live data, not garbage.

---

## PHASE 0 — SAFETY NET (must pass before anything else)

The backup script has never been run (2026-06-26 assessment). It may fail for
path, permission, or venv reasons — the tree layout changed under it. **Expect
failure to be a real possibility. Failure here is a valid, useful outcome.**

```
find ~ -maxdepth 4 \( -iname '*backup*.sh' -o -iname '*backup*.py' \) \
  -not -path '*/node_modules/*' -not -path '*/venv/*' 2>/dev/null | head -20
```

For the script that looks canonical: print it in full (`cat`) BEFORE running.
Report what it targets and where it writes. **If it would write into
`~/empire-repo` or delete anything, STOP and report — do not run it.**

If it looks safe, run it. Then verify the artifact:
```
ls -la <backup destination>
```
Confirm: a file exists, non-zero size, timestamp is today.

Additionally, take a belt-and-braces snapshot of exactly what R1 touches:
```
mkdir -p ~/backups/pre-R1-2026-08-22
cp -av /home/rg/empire-repo/backend/data/brain/*.db ~/backups/pre-R1-2026-08-22/
cp -av /home/rg/empire-data/brain/*.db ~/backups/pre-R1-2026-08-22/canon-orig-  2>/dev/null || \
  for f in /home/rg/empire-data/brain/*.db; do cp -av "$f" ~/backups/pre-R1-2026-08-22/canon-orig-$(basename "$f"); done
ls -la ~/backups/pre-R1-2026-08-22/
du -sh ~/backups/pre-R1-2026-08-22/
```

🛑 **STOP.** Report: script found? ran? artifact verified? snapshot sizes.
**If the backup script failed, R1 ENDS HERE** and becomes a backup-repair job.

---

## PHASE 1 — FIND EVERY BRAIN WRITER

One writer is known. Three DBs are fresh in the old lane. **Therefore writers
remain unfound.** Fixing only the known one leaves the migration looking
complete while it is not.

```
grep -rn 'brain/' ~/empire-repo-main/backend --include='*.py' | grep -v 'empire-repo-main' | head -40
grep -rn 'memories\.db\|token_usage\.db\|unified_messages\.db' ~/empire-repo-main/backend --include='*.py'
grep -rn 'empire-repo/' ~/empire-repo-main/backend --include='*.py' | grep -v 'empire-repo-main'
grep -rn 'expanduser\|Path.home()\|os.environ.get.*DB\|DB_PATH\|BRAIN' ~/empire-repo-main/backend/app/services/max --include='*.py' | head -30
```

Also check the OpenClaw worker's heartbeat path and the openclaw tree:
```
grep -rn 'heartbeat\|brain/\|data/max' ~/empire-repo-main/openclaw --include='*.py' 2>/dev/null | head -20
```

And the `brain_sync` resolver, in full:
```
sed -n '280,320p' ~/empire-repo-main/backend/app/services/max/scheduler.py
grep -rn 'MAX_MEMORY_PATH' ~/empire-repo-main --include='*.py' --include='*.conf' --include='*.service' 2>/dev/null
ls -la ~/empire-repo-main/max/ 2>/dev/null
```

Deliver a table — **every** row, no blanks:
```
DB / FILE              | WRITER file:line | PATH SOURCE (hardcode/env/fallback) | FIX REQUIRED
unified_messages.db    |                  |                                     |
memories.db            |                  |                                     |
token_usage.db         |                  |                                     |
max/memory.md          |                  |                                     |
openclaw heartbeat     |                  |                                     |
```

If a writer cannot be found for a fresh DB, say `WRITER NOT FOUND` explicitly.
**Do not guess.** A named gap is fine; an invented answer is not.

🛑 **STOP.** Report the table. Founder rules on scope before any file moves.

---

## PHASE 2 — THE COPY (first writes)

SQLite with an active `-wal` cannot be safely copied with `cp` — you get a torn
file. Checkpoint first, with the backend stopped.

**Expect ~1 minute of backend downtime.** Confirm the founder is ready.

```
# 1. stop the backend
systemctl --user stop empire-backend.service
sleep 3
pgrep -f 'uvicorn.*8000' || echo "backend stopped"

# 2. checkpoint each source DB (old lane)
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
for db in ("memories","token_usage","unified_messages"):
    p = f"/home/rg/empire-repo/backend/data/brain/{db}.db"
    con = sqlite3.connect(p)
    print(db, con.execute("PRAGMA wal_checkpoint(TRUNCATE)").fetchone())
    con.close()
PY

# 3. preserve canonical originals by RENAME (never overwrite)
cd /home/rg/empire-data/brain
for f in memories token_usage unified_messages; do
  [ -f "$f.db" ] && mv -v "$f.db" "$f.db.pre-R1-20260822"
done

# 4. copy old lane -> canonical
cp -av /home/rg/empire-repo/backend/data/brain/memories.db          /home/rg/empire-data/brain/memories.db
cp -av /home/rg/empire-repo/backend/data/brain/token_usage.db       /home/rg/empire-data/brain/token_usage.db
cp -av /home/rg/empire-repo/backend/data/brain/unified_messages.db  /home/rg/empire-data/brain/unified_messages.db
ls -la /home/rg/empire-data/brain/
```

**Do NOT start the backend yet.** Phase 3 verifies before anything runs.

---

## PHASE 3 — VERIFY THE COPY (gate)

```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
EXPECT = {
  ("memories","memories"): 25714,
  ("memories","conversation_summaries"): 802,
  ("unified_messages","unified_messages"): 22854,
  ("token_usage","token_usage"): 58841,
}
ok = True
for (db, table), want in EXPECT.items():
    p = f"/home/rg/empire-data/brain/{db}.db"
    con = sqlite3.connect(f"file:{p}?mode=ro", uri=True)
    got = con.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
    con.close()
    flag = "OK" if got >= want else "**MISMATCH**"
    if got < want: ok = False
    print(f"{db}.{table:<26} got={got:<8} expect>={want:<8} {flag}")
print("\nPHASE 3 GATE:", "PASS" if ok else "FAIL — STOP, DO NOT PROCEED")
PY
```

Also confirm integrity:
```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
for db in ("memories","token_usage","unified_messages"):
    con = sqlite3.connect(f"file:/home/rg/empire-data/brain/{db}.db?mode=ro", uri=True)
    print(db, con.execute("PRAGMA integrity_check").fetchone()[0])
    con.close()
PY
```

🛑 **STOP.**
- **GATE PASS** → report and wait for go-ahead to Phase 4.
- **GATE FAIL** → **ROLLBACK NOW**: restore canonical originals
  (`mv f.db.pre-R1-20260822 f.db`), restart the backend, report. Old-lane files
  are untouched, so nothing is lost. R1 ends; we diagnose the copy.

---

## PHASE 4 — REPOINT THE CODE

Fix **every** writer from the Phase 1 table, not only line 16.

Known, confirmed:
```
sed -n '10,20p' ~/empire-repo-main/backend/app/services/max/unified_message_store.py
```
Change the hardcoded path to resolve canonical — prefer an env var with a
canonical default, no old-lane fallback anywhere:
```python
DB_PATH = Path(os.environ.get(
    "EMPIRE_BRAIN_DIR", os.path.expanduser("~/empire-data/brain")
)) / "unified_messages.db"
```
Apply the same shape to every other writer Phase 1 found.

Set `MAX_MEMORY_PATH` so `scheduler.py:300` stops falling back to the legacy
path. Put it in the systemd drop-in — **never hardcode, never default** (CLAUDE.md):
```
systemctl --user cat empire-backend.service | grep -n 'Environment' 
```
Add to the existing drop-in (do not create a competing one):
```
Environment=MAX_MEMORY_PATH=/home/rg/empire-repo-main/max/memory.md
Environment=EMPIRE_BRAIN_DIR=/home/rg/empire-data/brain
```
Ensure the target directory exists: `mkdir -p ~/empire-repo-main/max`

Then:
```
systemctl --user daemon-reload
systemctl --user start empire-backend.service
sleep 5
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/
curl -s -m 5 http://localhost:8000/api/v1/max/health | head -c 300; echo
```

Verify the env actually reached the process:
```
BPID=$(pgrep -f 'uvicorn.*8000' | head -1)
tr '\0' '\n' < /proc/$BPID/environ | grep -E 'MAX_MEMORY_PATH|EMPIRE_BRAIN_DIR'
```
**Config on disk is not config in force (H61). Prove it from `/proc`.**

Commit on `feature/drawing-standard`, one commit, message naming the fix.

🛑 **STOP.** Report: diff, commit hash, backend health, `/proc` env proof.

---

## PHASE 5 — PROVE NEW WRITES LAND CANONICAL

```
# baseline mtimes
stat -c '%n %y' /home/rg/empire-data/brain/*.db /home/rg/empire-repo/backend/data/brain/*.db

# generate real traffic through MAX's message path (read-only endpoints are fine —
# we need the unified_message_store to fire; use whatever the Phase 1 table shows
# triggers it, e.g. a max chat/status call that records a turn)
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/api/v1/max/health
sleep 20

# compare
stat -c '%n %y' /home/rg/empire-data/brain/*.db /home/rg/empire-repo/backend/data/brain/*.db
```

Report: which side advanced. **Canonical should move; the old lane should be
frozen.** If the old lane still advances, a Phase 1 writer was missed — report
which DB and stop.

Confirm the corridor is unharmed:
```
for r in "/api/v1/quotes-v2/stats" "/api/v1/crm/customers?limit=5" "/api/v1/jobs/dashboard"; do
  curl -sL -o /dev/null -w "%{http_code} $r\n" "http://localhost:8000$r"
done
```

🛑 **STOP.** Report and end. The nightly `brain_sync` check happens tomorrow —
see `R1_VERIFY` below, run by the founder.

---

## ROLLBACK (valid at any phase)

- **Phase 2/3:** `cd /home/rg/empire-data/brain && for f in memories token_usage
  unified_messages; do mv -v "$f.db.pre-R1-20260822" "$f.db"; done` then
  `systemctl --user start empire-backend.service`.
- **Phase 4/5:** `git revert <commit>`, remove the added `Environment=` lines,
  `systemctl --user daemon-reload && systemctl --user restart empire-backend.service`.
- **Anything worse:** everything is in `~/backups/pre-R1-2026-08-22/` and the
  old-lane files were never modified.

---

## REPORT

Write `~/R1_BRAIN_MIGRATION_2026-08-22.md` with a section per phase, then:

```
## VERIFIED
## INFERRED
## COULD NOT PROBE
## ROLLBACK STATE  (clean / partial / rolled back)
```

Print at the end:
```
PHASE REACHED: 0/1/2/3/4/5
BRAIN COUNTS CANONICAL: memories=<> summaries=<> unified=<> tokens=<>
OLD LANE FROZEN: YES/NO
COMMIT: <hash>
```

---

# R1_VERIFY — FOUNDER RUNS THIS TOMORROW (after 23:00 brain_sync)

Not run in this session. `brain_sync` fires once daily at 23:00; only a real
scheduled run proves the resolver fix holds. Manual invocation would test the
function but not the scheduler's path resolution — which is the broken part.

```
echo "--- canonical memory.md (want: last night 23:00) ---"
stat -c '%n %y %s' ~/empire-repo-main/max/memory.md 2>&1
echo "--- old lane memory.md (want: FROZEN at 2026-08-21 23:00) ---"
stat -c '%n %y %s' ~/empire-repo/backend/data/max/memory.md
echo "--- brain DBs: canonical should be advancing, old lane frozen ---"
stat -c '%n %y' /home/rg/empire-data/brain/*.db /home/rg/empire-repo/backend/data/brain/*.db
echo "--- scheduler ran? ---"
journalctl --user -u empire-backend.service --since "yesterday 22:55" | grep -i 'brain_sync\|memory.md' | tail -20
```

**PASS:** canonical `memory.md` timestamped last night 23:00; old-lane brain
files frozen since the migration.
**FAIL:** old lane still advancing → a writer was missed. Nothing is lost;
report the output and we locate it.
