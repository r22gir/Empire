# DISPATCH 2026-08-22B — DB TRUTH + LIVE FORK (READ ONLY)
**To:** M3 (Claude Code, EmpireDell)
**Predecessor:** `RESTORE_PROBE_2026-08-22.md` — read it first, do not re-run it.
**Repo doctrine:** `~/empire-repo-main` is THE repo (`feature/drawing-standard`).
`~/empire-repo` is the fork. **NEW FINDING: the fork is NOT frozen — it is being
written to hourly.** Nothing in this dispatch deletes, moves, or disables it.

---

## HARD RULES

1. **READ ONLY.** No writes except the one report file. No installs, no service
   restarts/enables/disables/masks, no config edits, no `git` beyond
   `status`/`log`/`show`/`worktree list`. **Do not stop, disable, or mask
   `empire-openclaw.service`** — we are diagnosing it, not fixing it yet.
2. **Raw output only.** Paste stdout/stderr. A failed command is data.
3. **Do not fix anything.** Founder rules on remedies after this report.
4. Known false alarms — do not chase: `max/memory.md` always shows modified
   (nightly brain_sync); `FOUNDER_PIN env var is UNSET` prints at import in any
   non-unit context, the PIN IS set (H59).
5. `sqlite3` CLI is NOT installed. Use `~/empire-repo-main/backend/venv/bin/python`
   with `sqlite3` and `mode=ro` URIs.
6. If any step needs a credential or unlock you lack, say so and skip it.

---

## PART A — WHICH FILE DOES EACH MODEL ACTUALLY BIND TO?

**The contradiction to resolve.** `lsof` showed the backend holding exactly one
DB open — `empire-data/empirebox.db`, 278 KB, 18 of 20 tables empty. Yet the
corridor APIs returned 49 quotes, 171 customers, 155 inventory items — data that
lives in `empire-data/empire.db` (24 MB), which the process does NOT hold open.
Data cannot come from a file nothing reads. Find the reader.

### A1 — Default engine

```
sed -n '1,60p' ~/empire-repo-main/backend/app/database.py
grep -rn 'DATABASE_URL' ~/empire-repo-main/backend/app --include='*.py' | head -30
grep -rn 'DATABASE_URL\|EMPIRE_DB\|empire.db\|empirebox.db' ~/empire-repo-main/backend/.env 2>/dev/null
```
Report the resolved default URL and where the value comes from (env vs literal).

### A2 — Every engine in the codebase

```
grep -rn 'create_engine\|create_async_engine' ~/empire-repo-main/backend/app --include='*.py'
grep -rn 'sessionmaker\|SessionLocal\|async_session' ~/empire-repo-main/backend/app --include='*.py' | head -40
grep -rn "connect(.*\.db\|sqlite3.connect" ~/empire-repo-main/backend/app --include='*.py' | head -40
```
**`sqlite3.connect(...)` calls matter as much as SQLAlchemy engines** — raw
connections are invisible to a snapshot `lsof` and are the most likely
explanation for the contradiction.

### A3 — Corridor model → file map

For each of the six corridor capabilities, trace the route handler to the
session/connection it uses and report the DB FILE it resolves to. Use the exact
routes the predecessor probe confirmed:

| Capability | Route that returned data |
|---|---|
| quotes | `/api/v1/quotes-v2/stats`, `/api/v1/quotes` |
| jobs | `/api/v1/jobs/dashboard`, `/api/v1/jobs/active` |
| finance | `/api/v1/finance/dashboard`, `/api/v1/invoices` |
| payments | `/api/v1/payments/history` |
| crm | `/api/v1/crm/customers` |
| inventory | `/api/v1/inventory/items` |

Deliver this table — one row per capability, no blanks:

```
CAPABILITY | ROUTER FILE:LINE | SESSION/CONN USED | RESOLVED DB FILE | READ PATH | WRITE PATH
```

If read and write resolve to different files for any capability, say so in
capitals. That is the failure mode we are hunting.

### A4 — Catch the open in flight

`lsof` snapshots miss short-lived connections. Sample continuously while issuing
read-only GETs:

```
BPID=$(pgrep -f 'uvicorn.*8000' | head -1); echo "backend pid=$BPID"
( for i in $(seq 1 120); do
    lsof -p $BPID 2>/dev/null | grep -Eo '/home/rg/[^ ]*\.db' 
    sleep 0.25
  done ) | sort | uniq -c | sort -rn > /tmp/dbwatch.txt &
WATCH=$!
sleep 1
for r in "/api/v1/quotes?limit=5" "/api/v1/crm/customers?limit=5" \
         "/api/v1/invoices?limit=5" "/api/v1/inventory/items?limit=5" \
         "/api/v1/jobs/active" "/api/v1/payments/history"; do
  curl -sL -o /dev/null -w "%{http_code} $r\n" "http://localhost:8000$r"
done
wait $WATCH
cat /tmp/dbwatch.txt
```

Report every distinct `.db` path observed and its hit count. **If `empire.db`
appears here, hypothesis (a) holds — per-request connections, benign-but-messy.
If it never appears, something else is serving that data and we need to know
what.**

### A5 — Which file is actually fresh

```
stat -c '%n  size=%s  mtime=%y' /home/rg/empire-data/empire.db /home/rg/empire-data/empirebox.db /home/rg/empire-data/intake.db
ls -la /home/rg/empire-data/*.db-wal /home/rg/empire-data/*.db-shm 2>/dev/null
```
A live `-wal` on `empire.db` with a recent mtime is direct evidence of active
writes. Report both files' WAL state.

**PART A verdict, required:**
`DEFAULT ENGINE = <file>` · `CORRIDOR READS = <file(s)>` ·
`CORRIDOR WRITES = <file(s)>` · `AMBIGUOUS WRITE PATH: YES/NO` ·
`SAFE TO WRITE RECORDS: YES/NO`

---

## PART B — WHO IS WRITING INTO THE FORK RIGHT NOW?

The predecessor found fork files modified TODAY: `openclaw_worker_heartbeat.json`
10:19, `brain/memories.db` (14.9 MB) 10:00, `brain/token_usage.db` 09:30,
`brain/unified_messages.db` 08:00, `reports/morning_brief.json` 07:30,
`max/memory.md` 8/21 23:00. **The fork is a live tree, not an archive.**

### B1 — Identify the writers

```
sudo -n true 2>/dev/null && SUDO=sudo || SUDO=
$SUDO lsof +D /home/rg/empire-repo/backend/data 2>/dev/null | head -40
$SUDO fuser -v /home/rg/empire-repo/backend/data/brain/*.db 2>&1 | head -20
for p in $(pgrep -f 'openclaw|server.py|scheduler|brain_sync|max'); do
  echo "--- pid $p ---"; ps -o pid,cmd -p $p --no-headers; ls -l /proc/$p/cwd 2>/dev/null
done
```
If `lsof +D` needs privileges you don't have, say so and rely on cwd + unit files.

### B2 — Config that points at the fork

```
grep -rn 'empire-repo/' /etc/systemd/system/*.service ~/.config/systemd/user/*.service 2>/dev/null | grep -v 'empire-repo-main'
grep -rn "empire-repo/" ~/empire-repo-main/backend/app --include='*.py' | grep -v 'empire-repo-main' | head -30
grep -rn 'brain\|BRAIN_DIR\|DATA_DIR\|memories.db' ~/empire-repo-main/backend/app/services --include='*.py' | head -30
```
For every hit: is the fork path hardcoded, env-derived, or a stale default?

### B3 — Brain split check

Compare fork brain DBs against any canonical counterparts:
```
ls -la /home/rg/empire-data/brain/ 2>/dev/null
ls -la /home/rg/empire-repo/backend/data/brain/
```
Then row counts for both sides of `memories.db` and `unified_messages.db` using
the read-only venv-python pattern. **Question to answer plainly: is MAX's memory
split across two trees, and which side is current?**

---

## PART C — REBOOT TRAP, FULLY MAPPED

Diagnose only. **Do not enable, disable, mask, unmask, or restart anything.**

```
systemctl cat empire-openclaw.service
systemctl show empire-openclaw.service -p WorkingDirectory -p ExecStart -p UnitFileState -p FragmentPath
systemctl cat empire-backend.service 2>&1 | head -40
systemctl show empire-backend.service -p UnitFileState -p FragmentPath -p DropInPaths
ls -la /etc/systemd/system/empire-*.service.d/ ~/.config/systemd/user/empire-*.service.d/ 2>/dev/null
systemctl list-unit-files 'empire*' --all
```

Then answer, one line each:
- What starts the backend on boot today? (masked unit → what actually starts pid 652663?)
- What starts OpenClaw on boot, from which tree, with which Python?
- Does the fork's venv still satisfy `openclaw/server.py` imports? Check without
  running it: `~/empire-repo/backend/venv/bin/python -c "import sys; print(sys.version)"`
  and `head -40 ~/empire-repo/openclaw/server.py` to list its imports.
- **If the machine rebooted right now, what comes up and what doesn't?**

---

## PART D — SALVAGE MANIFEST (INVENTORY, NOT MOVEMENT)

Do not copy or move anything. Build the manifest that a later dispatch will act on.

### D1 — Client-value files stranded in the fork

For each asset below, determine whether canonical has a DB row that owns it.
Search canonical `empire.db` for the filename, the bare ID, and the quote number.

```
/home/rg/empire-repo/uploads/arch_drawings/drawing_e1dc49d9.{svg,pdf}
/home/rg/empire-repo/uploads/arch_drawings/drawing_f459fe28.{svg,pdf}
/home/rg/empire-repo/uploads/arch_drawings/drawing_4d6deab6.{svg,pdf}
/home/rg/empire-repo/backend/data/uploads/documents/EST-2026-111_Presentation_Boards-2_20260716_200003.pdf
/home/rg/empire-repo/backend/data/uploads/images/IMG_1041_20260716_201718.jpeg
/home/rg/empire-repo/backend/data/photos/quote/52/cc_20260716_*.jpeg
```

Search pattern (read-only, adapt table list to what exists):
```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
con = sqlite3.connect("file:/home/rg/empire-data/empire.db?mode=ro", uri=True)
needles = ["drawing_e1dc49d9","drawing_f459fe28","drawing_4d6deab6",
           "EST-2026-111","IMG_1041","cc_20260716","quote/52"]
tabs = [r[0] for r in con.execute(
    "SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
for t in tabs:
    cols = [c[1] for c in con.execute(f'PRAGMA table_info("{t}")')]
    text_cols = [c for c in cols]
    for n in needles:
        for c in text_cols:
            try:
                hits = con.execute(
                    f'SELECT COUNT(*) FROM "{t}" WHERE CAST("{c}" AS TEXT) LIKE ?',
                    (f"%{n}%",)).fetchone()[0]
                if hits:
                    print(f"{t}.{c}  ~{n}  hits={hits}")
            except Exception:
                pass
con.close()
PY
```

Report per asset: `OWNED BY CANONICAL (table.column, row id)` or `ORPHAN — no
canonical row references this file`.

**EST-2026-111 note:** that quote is with the client and its outcome is not this
dispatch's business. What matters here is only whether its presentation PDF and
photos are reachable from canonical or exist solely in the fork.

### D2 — Live-data files that must NOT be treated as salvage

Separate list. These are being written now and are not candidates for a copy-and-
delete salvage — moving them would break running services:
```
backend/data/brain/{memories,token_usage,unified_messages}.db
backend/data/max/{memory.md,session_handoff.json,supermemory_scaffold.jsonl,openclaw_worker_heartbeat.json}
backend/data/reports/morning_brief.json
backend/data/{empire.db,intake.db} + -wal/-shm
```
Report each with current mtime and, where B1 identified it, the owning process.

### D3 — Manifest totals

```
ACTIVE (written in last 24h, do not touch): <count>, <total MB>
STRANDED CLIENT ASSETS (orphan, safe to copy later): <count>, <total MB>
OWNED BY CANONICAL (already reachable, no action): <count>
```

---

## PART E — DOES HERMES HAVE AN EXECUTION ENGINE, OR ONLY A HAND?

**Founder decision this feeds.** OpenClaw was the original task-automation
vehicle and is now dormant (+27 tasks in 57 days; the morning brief prints
`Tasks: 0 open` daily). The candidate replacement is Hermes. The question is
NOT which one we prefer — it is whether Hermes has a durable queue, retry, and
scheduling, or is a request/response bridge with no autonomous loop. **Measure
both. Do not recommend.**

### E1 — Hermes surface
```
curl -s -m 5 http://localhost:3000/health; echo
curl -s -m 5 http://localhost:3000/openapi.json | head -c 300; echo
ls -la ~/.hermes/ 2>/dev/null
find ~ -maxdepth 4 -iname '*hermes*' -type d 2>/dev/null | head
```
If there is no `/openapi.json`, locate and report the route table from source.

### E2 — Does it have a task store?
`~/.hermes/empire.db` was found by the predecessor probe. Enumerate it:
```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
con = sqlite3.connect("file:/home/rg/.hermes/empire.db?mode=ro", uri=True)
for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    print(f"{t:<40} {n}")
con.close()
PY
```
Report whether any table resembles a queue (status, retry_count, scheduled_at,
attempts, worker_id). **A memory or log table is not a queue. Say which it is.**

### E3 — Comparable activity, last 30 days
Same window, same columns, all three systems:
```
SYSTEM      | STORE                        | TOTAL | LAST 30d | OK 30d | FAIL 30d | LAST SUCCESS
OpenClaw    | empire.db openclaw_tasks     |       |          |        |          |
MAX desks   | <locate execution table>     |       |          |        |          |
Hermes      | ~/.hermes/empire.db <table>  |       |          |        |          |
```
For MAX desks, find the backing execution/history table (`desk_configs` exists;
that is config, not history). If a system has no execution store at all, write
`NO EXECUTION STORE` — that is the most informative possible answer.

### E4 — Scheduling and retry, by code
```
grep -rn 'APScheduler\|scheduler\|cron\|retry\|backoff' ~/empire-repo-main/backend/app/services/max --include='*.py' | head -20
grep -rn 'scheduler\|queue\|retry' ~/empire-repo-main/backend/app/services --include='*.py' | grep -i hermes | head -20
```
`scheduler.py:287` is the known nightly `brain_sync` site — report what else
that scheduler owns, since it is the strongest evidence of a working loop.

**PART E verdict, required:**
`HERMES DURABLE QUEUE: Y/N` · `RETRY: Y/N` · `SCHEDULER: Y/N` ·
`ROLE OBSERVED: engine / bridge / unclear`

---

## PART F — THE INTAKE ROW THAT EXISTS ONLY IN THE FORK

Predecessor counts: canonical `intake.db` = 504 projects / 654 users. Fork
`intake.db` = **505 / 655**. The fork is AHEAD by one of each. Intake is the
customer front door, so a fork-only intake project may be a real customer
inquiry that fork deletion would destroy.

```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
canon = sqlite3.connect("file:/home/rg/empire-data/intake.db?mode=ro", uri=True)
fork  = sqlite3.connect("file:/home/rg/empire-repo/backend/data/intake.db?mode=ro", uri=True)
for table in ("intake_projects", "intake_users"):
    cols = [c[1] for c in fork.execute(f'PRAGMA table_info("{table}")')]
    key = "id" if "id" in cols else cols[0]
    c_ids = {r[0] for r in canon.execute(f'SELECT "{key}" FROM "{table}"')}
    f_ids = {r[0] for r in fork.execute(f'SELECT "{key}" FROM "{table}"')}
    only_fork, only_canon = f_ids - c_ids, c_ids - f_ids
    print(f"=== {table} === fork-only={len(only_fork)} canon-only={len(only_canon)}")
    print("columns:", cols)
    for i in list(only_fork)[:5]:
        row = fork.execute(f'SELECT * FROM "{table}" WHERE "{key}"=?', (i,)).fetchone()
        print("FORK-ONLY ROW:", dict(zip(cols, row)))
canon.close(); fork.close()
PY
```

Report the full fork-only row(s): customer name, date, and whether canonical
holds the same inquiry under a different id. **Do not copy it anywhere in this
run — identify only.**

Then run the same ID set-difference (not COUNT comparison) on `empire.db` for
`quotes_v2`, `customers`, `invoices`, `jobs`. The predecessor concluded
"0 fork-only rows" from counts alone, which cannot detect a fork-only row
offset by a canonical-only row. Confirm or correct that conclusion.

**PART F verdict, required:**
`FORK-ONLY INTAKE ROWS: <n>` · `FORK-ONLY BUSINESS ROWS: <n>` ·
`FORK DELETION WOULD DESTROY UNIQUE DATA: YES/NO`

---

## REPORT

Write to `~/DB_TRUTH_FORK_2026-08-22B.md`:

```
## PART A — DB BINDING
<A1..A5 raw output>
<corridor model→file table>
VERDICT: DEFAULT=<> READS=<> WRITES=<> AMBIGUOUS=<Y/N> SAFE TO WRITE=<Y/N>

## PART B — FORK WRITERS
<raw output>
WRITERS IDENTIFIED: <process → path>
BRAIN SPLIT: <yes/no, which side current>

## PART C — REBOOT TRAP
<raw output>
ON REBOOT: <what comes up, what doesn't, from which tree>

## PART D — SALVAGE MANIFEST
<per-asset ownership verdicts>
<D2 active list>
<D3 totals>

## PART E — TASK ENGINES
<E1..E4 raw output>
<three-system activity table>
VERDICT: QUEUE=<> RETRY=<> SCHEDULER=<> ROLE=<>

## PART F — FORK-ONLY ROWS
<set-difference output, full fork-only rows>
VERDICT: INTAKE=<n> BUSINESS=<n> DESTROYS UNIQUE DATA=<Y/N>

## VERIFIED
## INFERRED
## COULD NOT PROBE
```

The VERIFIED / INFERRED split is mandatory — anything not backed by pasted
output goes under INFERRED. The predecessor report did this correctly; hold that
standard.

**Print at the end:** report path, plus these three lines — they gate every
repair dispatch after this one:
```
SAFE TO WRITE RECORDS: YES/NO
FORK DELETION WOULD DESTROY UNIQUE DATA: YES/NO
HERMES ROLE OBSERVED: engine / bridge / unclear
```
