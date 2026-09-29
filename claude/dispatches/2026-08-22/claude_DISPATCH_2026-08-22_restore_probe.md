# DISPATCH — RESTORE PROBE (READ ONLY)
**Date:** 2026-08-22
**To:** M3 (Claude Code, EmpireDell)
**From:** Claude (strategic) via founder
**Reference target:** `empire_ecosystem_navigator_v3_enhanced.html` — 63 nodes, 205 edges

---

## PURPOSE

Establish the ACTUAL current state of the Empire ecosystem so it can be diffed
against the navigator's recorded working state. This is a mapping run, not a
repair run.

## HARD RULES

1. **READ ONLY.** No writes. No migrations. No `pip install`. No service
   restarts. No config edits. No `git` operations other than `status` / `log`.
2. **Raw output only.** Paste actual stdout/stderr. Do not summarize, do not
   describe what a command "would" show, do not fill gaps from memory.
3. **If a command fails, report the failure verbatim** and continue to the next
   step. A failed probe is data.
4. **Do not fix anything you find.** Note it and move on. Founder rules on
   sequencing.
5. If any step would require a credential, PIN, or unlock you do not have,
   say so explicitly and skip it. Do not attempt to bypass.
6. Known false alarm: `FOUNDER_PIN env var is UNSET` prints at import in any
   non-unit context. The PIN IS set. Do not burn probes on it (H59).

---

## STEP 1 — PROCESS AND SERVICE INVENTORY

```
systemctl list-units --type=service --state=running --no-pager
systemctl status empire-portal.service --no-pager -l | head -30
ps aux | grep -Ei 'uvicorn|fastapi|node|next|ollama|python.*max|opencode' | grep -v grep
ss -tlnp 2>/dev/null | sort -t: -k2 -n
```

Report every listening port with its owning process.

## STEP 2 — BACKEND API REACHABILITY AND ROUTE INVENTORY

Do NOT assume route paths. Discover them.

```
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/
curl -s http://localhost:8000/openapi.json | head -c 400
curl -s http://localhost:8000/openapi.json | python3 -c "
import sys, json
try:
    spec = json.load(sys.stdin)
except Exception as e:
    print('OPENAPI PARSE FAILED:', e); raise SystemExit
paths = spec.get('paths', {})
print('ROUTE COUNT:', len(paths))
for p in sorted(paths):
    methods = ','.join(sorted(m.upper() for m in paths[p]))
    print(f'{methods:22} {p}')
"
```

If `/openapi.json` 404s, try `/docs`, `/redoc`, `/api/openapi.json` and report
which (if any) responds. Report the full route list — do not truncate it.

## STEP 3 — TRUTH LAYER REALITY

Locate the databases before querying them.

```
find ~ -maxdepth 4 -name 'empire.db' -o -maxdepth 4 -name 'intake.db' 2>/dev/null
```

**GOTCHA (H-record): the `sqlite3` CLI is NOT installed on EmpireDell.** Use
the venv's Python — and only the real repo's venv:
`~/empire-repo-main/backend/venv` (the stale fork's venv has been diverging
since March).

For each DB found, report path, size, mtime, then tables + row counts:

```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
for path in ["<DB_PATH_1>", "<DB_PATH_2>"]:
    print("=== "+path+" ===")
    try:
        con = sqlite3.connect("file:"+path+"?mode=ro", uri=True)
        rows = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        ).fetchall()
        for (t,) in rows:
            n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
            print(f"{t:<40} {n}")
        con.close()
    except Exception as e:
        print("ERROR:", e)
PY
```

(`mode=ro` keeps this run read-only at the connection level.)

**This is the single most important step.** Row counts tell us whether the
corridor has real history in it or whether we are looking at empty scaffolding.

Also locate JSON stores and env/config:

```
find ~ -maxdepth 5 -name '*.json' -path '*store*' 2>/dev/null | head -40
ls -la ~/.env* 2>/dev/null
find ~ -maxdepth 3 -name '.env' 2>/dev/null
```

For any `.env` found: report **key names only**. Never print values.

## STEP 4 — CORRIDOR SMOKE (GET ONLY)

Using ONLY route paths discovered in Step 2, issue read-only GETs against the
quote → job → finance → payment → CRM corridor. For each, report status code
and the first 300 bytes of the body.

Target capabilities, in this order:
1. quotes
2. jobs
3. finance / invoices
4. payments
5. crm / customers
6. inventory

Template:
```
curl -s -o /tmp/r.json -w "%{http_code} %{size_download}b " "http://localhost:8000<ROUTE>"; head -c 300 /tmp/r.json; echo
```

If a capability has no matching route in the Step 2 inventory, state
"NO ROUTE FOUND" for it. Do not guess a path.

## STEP 5 — ORCHESTRATOR SURFACE

```
find ~ -maxdepth 4 -iname '*max*' -type d 2>/dev/null | head -20
```

Report: is MAX running (from Step 1), what config file governs it, what model
string that config names, and the mtime of that config. Key names and model
string only — no secrets.

Do not start MAX. Do not send it a prompt.

## STEP 6 — REPO STATE

```
cd ~/empire-repo-main && git status --porcelain=v1 && git log --oneline -12 && git worktree list
```

Report uncommitted work explicitly. Per HANDOFF_2026-08-20 doctrine:
`~/empire-repo-main` and `~/empire-repo` are LINKED worktrees on the same
`feature/drawing-standard` branch sharing one object store (pre-2026-08-24
framing called `~/empire-repo` a "stale fork"; that read was wrong — see
H72/H73 and `reports/2026-08-24_D23_stale_fork_census.md`). Do not touch
either beyond these read commands. Known false positive: `max/memory.md`
always shows modified (nightly brain_sync) — report it but do not treat it as
uncommitted work.

---

## STEP 7 — NAMED HYPOTHESES FROM THE MAY RECORD (CONFIRM OR RETIRE)

Drive holds a diagnosis dated 2026-05-02/07 (`max.log`, Navigator v3 Strategic
Synthesis PDF). Each item below is a HYPOTHESIS from that record, ~3.5 months
old. For each: run the probe, paste output, and mark CONFIRMED STILL / FIXED
SINCE / CANNOT VERIFY. Do not fix any of them in this run.

**H-A — MAX dies on import (launch method).**
May log: `ImportError: attempted relative import with no known parent package`
at `backend/app/services/max/__init__.py:2`, plus
`No module named app.services.max.orchestrator`. Pattern says MAX was launched
as a script, not with `python -m`.
```
grep -rn 'services.max' ~/empire-repo-main --include='*.service' 2>/dev/null
grep -rn 'services/max' ~/empire-repo-main/*.sh ~/empire-repo-main/backend/*.sh 2>/dev/null | head
sed -n '1,10p' ~/empire-repo-main/backend/app/services/max/__init__.py
ls ~/empire-repo-main/backend/app/services/max/
```
Report: how is MAX actually launched (unit file / script / manual), and does
`orchestrator.py` exist in that directory.

**H-B — Frontend hardcodes localhost:8000.**
May record: `app/workroom/page.tsx:13`, `app/hermes/page.tsx:11`,
`app/openclaw/page.tsx:11`, `app/orchestration/page.tsx:12`.
```
grep -rn 'localhost:8000' ~/empire-repo-main/empire-command-center/app --include='*.tsx' | head -20
```

**H-C — CraftForge lazy import path off by one directory.**
May record: `import('../business/craftforge/QuoteBuilderSection')` should be
`../components/business/craftforge/...`.
```
grep -rn 'business/craftforge/QuoteBuilderSection' ~/empire-repo-main/empire-command-center/app 2>/dev/null
```

**H-D — Drawing router early-returns instead of handing off.**
May record: `backend/app/routers/max/router.py:1391–1398`,
`drawing_handoff.ready == False` → JSON error string.
```
sed -n '1380,1410p' ~/empire-repo-main/backend/app/routers/max/router.py 2>/dev/null
```

**H-E — OpenClaw health.**
May record: healthy on :7878 with 62 queued tasks.
```
curl -s -m 5 http://localhost:7878/health
```

**H-F — Data layer identity conflict.**
The May PDF claims PostgreSQL / Redis / S3-MinIO as the data layer. The
navigator's truth layer is `empire.db` / `intake.db` / JSON stores. Both cannot
be the operative truth. Step 1's port listing (5432, 6379, 9000) plus Step 3's
DB findings resolve this. State explicitly which stores are actually live and
actually populated.

**H-G — Which repo lane serves production.**
The May P0 fixes all target `~/empire-repo-v10` on port 8010. Current doctrine
(HANDOFF_2026-08-20): `~/empire-repo-main` is THE repo; `~/empire-repo` is a
stale fork whose venv has been diverging since March. Establish which checkout
each live process actually serves from.
```
ls -d ~/empire-repo ~/empire-repo-main ~/empire-repo-v10 2>&1
curl -s -o /dev/null -w "%{http_code}\n" -m 5 http://localhost:8010/health
```
Report which checkout the running :8000 process (from Step 1) is actually
serving from (`ls -l /proc/<PID>/cwd`).

**Source caution, for the record:** the May PDF's file:line diagnostics read as
genuine audit output and are worth testing. Its "industry validation" layer is
not — the reference list is padded with unrelated links (TikTok clips, Hermès
handbag pages cited for our Hermes service, the Empire pentest framework cited
for our Empire). Treat only the concrete diagnostics as candidate facts; treat
the 90-day Temporal/OPA/CQRS roadmap as an unranked proposal awaiting founder
ruling, not as findings.

---

## STEP 8 — DOWNLOADS FOLDER SCAN (READ ONLY)

The founder's Downloads folder may hold newer exports, audits, navigator
builds, or client docs that post-date the May record and the current repo
state. Inventory it — do not move, rename, or delete anything.

```
DL=~/Downloads
ls -la "$DL" | head -5
find "$DL" -maxdepth 2 -newermt '2026-05-01' \
  \( -iname '*empire*' -o -iname '*navigator*' -o -iname '*max*' \
     -o -iname '*ecosystem*' -o -iname '*restore*' -o -iname '*audit*' \
     -o -iname '*probe*' -o -iname '*dispatch*' -o -iname '*state*' \
     -o -iname '*handoff*' -o -iname '*migration*' -o -iname '*willard*' \
     -o -iname '*woodcraft*' -o -iname '*quote*' -o -iname '*invoice*' \) \
  -printf '%TY-%Tm-%Td %TH:%TM  %10s  %p\n' 2>/dev/null | sort -r | head -60
```

Then a full-extension census so nothing relevant hides behind an unmatched name:

```
find "$DL" -maxdepth 2 -type f -newermt '2026-05-01' -printf '%f\n' 2>/dev/null \
  | sed 's/.*\.//' | sort | uniq -c | sort -rn | head -15
```

For each hit that looks like a state/audit/spec document (md, txt, json, html,
log — NOT binaries, NOT media):

```
echo "=== <path> ==="; stat -c '%y %s bytes' "<path>"; head -c 600 "<path>"; echo
```

Cap at the 15 most recent relevant files. For PDFs/xlsx/images, report name,
size, mtime only — no extraction in this run. If `~/Downloads` doesn't exist,
check `~/downloads` and `/home/*/Downloads`, and report what you found.

In the report, add a section:

```
## STEP 8 — DOWNLOADS
<file inventory with dates/sizes>
<600-byte heads of relevant text docs>
NEWER THAN REPO: <any doc that appears to post-date HEAD or the May record>
DUPLICATES OF KNOWN DOCS: <anything matching Drive/project files we already hold>
```

Flag explicitly anything that looks like (a) a newer navigator build, (b) a MAX
config or log newer than May 7, (c) client-facing documents that never made it
into the repo or Drive.

---

## STEP 9 — STALE FORK SALVAGE INVENTORY (READ ONLY)

Per STATE_v8/H57, MAX's runtime was writing client uploads, generated quotes,
and drawings into the stale fork `~/empire-repo` until fix `88814b2`
(2026-08-19/20). Before eradication of the fork ever runs, inventory what of
client value is stranded there. **Do not delete, move, or "clean up" anything.**

```
find ~/empire-repo -type f -newermt '2026-05-01' \
  \( -path '*upload*' -o -path '*quote*' -o -path '*drawing*' -o -path '*data*' \
     -o -name '*.pdf' -o -name '*.png' -o -name '*.db' -o -name '*.json' \) \
  -printf '%TY-%Tm-%Td %TH:%TM  %10s  %p\n' 2>/dev/null | sort -r | head -80
```

For any `.db` in the fork: report path/size/mtime and table row counts using
the same read-only venv-python pattern as Step 3, and note any table whose
count differs from its counterpart in the canonical DB — that difference is
data that exists ONLY in the fork.

Also confirm the reboot trap:
```
systemctl cat empire-backend.service 2>/dev/null | grep -E 'ExecStart|WorkingDirectory'
systemctl is-enabled empire-backend.service 2>/dev/null
```
If ExecStart points into `~/empire-repo` (the fork) and the unit is enabled,
state plainly: **A REBOOT STARTS THE WRONG CODE.**

Report section:
```
## STEP 9 — STALE FORK SALVAGE
<file inventory>
<fork DB row counts vs canonical, deltas flagged>
REBOOT TRAP: <unit ExecStart target + enabled state + plain verdict>
STRANDED CLIENT VALUE: <yes/no + what>
```

---

## REPORT FORMAT

Return one file: `RESTORE_PROBE_2026-08-22.md`

```
## STEP 1 — SERVICES
<raw output>
## STEP 2 — ROUTES
<raw output, full route list>
## STEP 3 — TRUTH LAYER
<raw output, per DB, with row counts>
## STEP 4 — CORRIDOR
<per capability: route used, status, body head, or NO ROUTE FOUND>
## STEP 5 — ORCHESTRATOR
<raw output>
## STEP 6 — REPO
<raw output>
## STEP 7 — HYPOTHESES
<per hypothesis H-A..H-G: probe output + verdict CONFIRMED STILL / FIXED SINCE / CANNOT VERIFY>
## STEP 8 — DOWNLOADS
<inventory + heads + NEWER THAN REPO + DUPLICATES OF KNOWN DOCS>
## STEP 9 — STALE FORK SALVAGE
<inventory + DB deltas + REBOOT TRAP verdict + STRANDED CLIENT VALUE>

## VERIFIED
- <things you ran a command for and saw the output of>

## INFERRED
- <anything you concluded but did not directly observe>

## COULD NOT PROBE
- <steps skipped, with the reason>
```

The VERIFIED / INFERRED split is mandatory. Anything not backed by pasted
output belongs under INFERRED. An empty VERIFIED section is an acceptable
report; a padded one is not.

---

## WHAT HAPPENS NEXT

Claude diffs this report against the navigator's 63 nodes and produces a
node-by-node status table: WORKING / DEGRADED / DOWN / UNPROBED. Restoration
sequencing follows from that table, Tier 0 first. Founder rules on scope
before any repair dispatch is written.
