# DISPATCH R6 — THE 37-ENTRY NAV SWEEP
**Date:** 2026-08-22 · **To:** M3 (EmpireDell)
**Mode:** **READ ONLY, ALL PARTS.** No edits, no restarts, no writes except the
report. Nothing here changes a module's status — it records what is observably
true so the founder can rule.

---

## WHY

`app/components/layout/LeftNav.tsx` defines 37 nav entries in 6 groups. Each
carries a hardcoded literal:

```typescript
status: 'active' | 'dev' | 'planned'
```

**Nothing derives that from a live check.** 32 entries say `active` because
someone typed `active`. The proof it is fiction: **OpenClaw is marked `active`**
while it has run 27 tasks in 57 days at an ~80% failure rate and the morning
brief has printed `Tasks: 0 open` for eight consecutive days.

Five inventories currently disagree about what EmpireBox contains:

| source | count |
|---|---|
| authoritative registry | 7 |
| catalog | 22 |
| modules in code (2026-06-26 assessment) | ~24 |
| **left nav** | **37** |
| navigator graph nodes | 63 |

The 2026-06-26 assessment named this the single highest-leverage fix: *"An agent
cannot autonomously operate a system it has no accurate map of."* This dispatch
produces the map. **The founder supplies intent afterward; M3 supplies evidence
now.**

---

## HARD RULES

1. **READ ONLY.** GET requests only. **Never POST, PUT, PATCH, or DELETE** —
   a module's page may render fine while its write path is broken, and finding
   that out is not worth creating a record in a live business database.
2. No edits to `LeftNav.tsx` or any status literal. **Do not "correct" the
   statuses.** The gap between claimed and observed IS the deliverable.
3. Do not restart anything. The backend (PID 967507) and portal must stay up.
4. **Never guess a status.** If a module cannot be evaluated, mark it
   `UNKNOWN` and say why. An honest gap beats an invented verdict.
5. Say what you verified vs. inferred, per module.
6. Repo: `~/empire-repo-main`, branch `feature/drawing-standard`.
7. `sqlite3` CLI not installed — use `~/empire-repo-main/backend/venv/bin/python`.

---

## PART 1 — BUILD THE THREE LISTS

### 1.1 — The nav (claimed)
```
sed -n '40,140p' ~/empire-repo-main/empire-command-center/app/components/layout/LeftNav.tsx
```
Extract every entry: `group`, `id`, `name`, `status` (claimed), `kind`
(product / screen / daily-summary), and `screen` if present. **37 rows, none
omitted.**

### 1.2 — What pages actually exist
```
cd ~/empire-repo-main/empire-command-center
ls -1 app/ | sort
find app -maxdepth 2 -name 'page.tsx' | sort
ls -1 app/components/screens/ 2>/dev/null | sort
ls -1 app/components/business/ 2>/dev/null | sort
```
Most nav items are `kind: 'product'` and switch a client-side view rather than
routing — so find the switch that maps a product id to a component:
```
grep -rn "EcosystemProduct" app/lib/types.ts | head
grep -rln "activeProduct ===\|case '" app/components --include='*.tsx' | head
```
**Report which component renders each product id.** If an id has no component,
that is a nav entry pointing at nothing — name it.

### 1.3 — What the backend offers
```
curl -s http://localhost:8000/openapi.json | ~/empire-repo-main/backend/venv/bin/python -c "
import sys, json
paths = sorted(json.load(sys.stdin).get('paths', {}))
print('TOTAL ROUTES:', len(paths))
import collections
pref = collections.Counter(p.split('/')[3] if len(p.split('/'))>3 else p for p in paths)
for k,v in pref.most_common(60): print(f'{v:5}  {k}')
"
```
That prefix histogram is the backend's own module list. **Report it in full** —
it is the third inventory and the only one derived from running code.

🛑 **STOP.** Report the three lists and the two mismatch sets:
- **nav entries with no component or no backend prefix**
- **backend prefixes with no nav entry**

---

## PART 2 — PROBE EACH OF THE 37

For every entry, in nav order. **GET only.**

### 2.1 — Does the screen render?
```
curl -s -o /tmp/p.html -w "%{http_code}" "http://localhost:3005/?product=<id>" ; \
  grep -ciE 'error|exception|not found|__next_error' /tmp/p.html
```
Adjust the URL to however product selection actually works — Part 1.2 tells you
whether it is a query param, a route, or client state only. **If product
selection is client-side only and cannot be driven by URL, say so and fall back
to evaluating the component's data calls statically.** Do not fake a result.

### 2.2 — What backend does it call?
For each module's component, find its fetch calls:
```
grep -rn "fetch(\|api/v1" app/components/business/<module>/ app/components/screens/<Module>* 2>/dev/null | head -10
```
Then GET each discovered route and record status + whether the body carries
real data or an empty envelope (`[]`, `{"items":[]}`, `total: 0`).

### 2.3 — Does it have data?
For modules with an obvious table in `empire.db`, count rows:
```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
con = sqlite3.connect("file:/home/rg/empire-data/empire.db?mode=ro", uri=True)
for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    print(f"{t:<40} {n}")
con.close()
PY
```
Map tables to modules by prefix (`ag_` → ArchiveForge, `sf2_` → StoreFront,
`cf_` → ContractorForge, `mf_` → MarketForge, `lf_` → LeadForge, etc.). **State
the mapping you used** — if a prefix is ambiguous, say so rather than assuming.

### 2.4 — The verdict table

One row per entry. This table is the deliverable.

```
GROUP | ID | NAME | CLAIMED | COMPONENT? | ROUTES? | DATA ROWS | OBSERVED | EVIDENCE
```

`OBSERVED` vocabulary — use exactly these, no others:
- **LIVE** — renders, calls a real route, route returns real data
- **WIRED-EMPTY** — renders and calls a real route, but the data is empty
- **SHELL** — renders, but calls nothing or calls a route that 404s
- **ABSENT** — nav entry with no component behind it
- **UNKNOWN** — could not evaluate; say why

**Flag every row where CLAIMED ≠ OBSERVED.** Expect many. That count is the
headline number of this dispatch.

🛑 **STOP.** Report the table plus the claimed-vs-observed mismatch count.

---

## PART 3 — THE FIVE-WAY RECONCILIATION

### 3.1 — Find the other inventories
```
find ~/empire-repo-main -name 'EMPIRE_MODULE_REGISTRY.md' -o -name '*module*registry*' -o -name 'ecosystem_catalog*' 2>/dev/null
grep -rn '_EMPIRE_MODULES' ~/empire-repo-main/backend/app/routers/max/router.py | head -3
grep -rn 'EMPIRE_CATALOG' ~/empire-repo-main/backend --include='*.py' | head -5
ls -la ~/empire-repo-main/backend/app/services/max/operating_registry.json
```
`CLAUDE_label_station.md` records **three** competing registries — one canonical
plus two marked as drift (`_EMPIRE_MODULES` in `router.py`, and
`empire_module_knowledge.py`). Confirm whether all three still exist and whether
they still disagree.

### 3.2 — The reconciliation table
```
MODULE | in nav? | in registry? | in catalog? | in router _EMPIRE_MODULES? | has backend routes? | has data? | OBSERVED
```
Union of every module named by any source. **Report:**
- modules in **all** inventories (the agreed core)
- modules in the nav only
- modules with backend routes and data but **in no registry** — these are the
  dangerous ones: real, working, and invisible to MAX
- modules in a registry that exist nowhere else

### 3.3 — What MAX itself believes
Read-only, no prompt sent:
```
curl -s http://localhost:8000/api/v1/max/models | head -c 400; echo
~/empire-repo-main/backend/venv/bin/python -m json.tool ~/empire-repo-main/backend/app/services/max/operating_registry.json | head -80
stat -c '%n %y' ~/empire-repo-main/backend/app/services/max/operating_registry.json
```
The registry's mtime was **2026-05-15** — three months unchanged. Confirm, and
report how many modules it lists versus the 37 in the nav.

🛑 **STOP.** Report the reconciliation and the four gap lists.

---

## REPORT

`~/R6_NAV_SWEEP_2026-08-22.md`, section per part, then:
```
## VERIFIED
## INFERRED
## COULD NOT PROBE
```

Print at the end:
```
NAV ENTRIES: 37
CLAIMED ACTIVE: <n>
OBSERVED LIVE: <n>
OBSERVED WIRED-EMPTY: <n>
OBSERVED SHELL: <n>
OBSERVED ABSENT: <n>
OBSERVED UNKNOWN: <n>
CLAIMED != OBSERVED: <n>
REAL+WORKING BUT IN NO REGISTRY: <n>
REGISTRY MODULE COUNT: <n>   (mtime <date>)
```

**Do not recommend which modules to retire.** That is the founder's portfolio
decision. Produce the evidence; he rules.
