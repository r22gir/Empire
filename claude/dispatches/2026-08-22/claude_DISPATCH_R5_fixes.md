# DISPATCH R5 — FOUR FIXES + TWO AUTH PROBES
**Date:** 2026-08-22 · **To:** M3 (EmpireDell)
**Predecessor:** `R6_NAV_SWEEP_2026-08-22.md` (960 lines — read §2.2, §2.3,
and the effort-classification table before starting)
**Scope:** the 4 entries R6 classified as afternoon-scale, plus the 2 it could
not classify without auth. **Explicitly NOT** pay / ship / llc — R6 classified
those as genuine projects and they are out of scope.

---

## WHY THESE SIX

R6 probed all 37 nav entries. Nine claim more than they deliver. Of those:

| entry | R6 verdict | class |
|---|---|---|
| **lead** | WIRED-EMPTY | (a) wrong table in one file — `lf_leads`=0 while `prospects`=322 |
| **support** | WIRED-EMPTY | (a) wrong table/filter — API returns 0 while `sf_tickets`=3 |
| **vision** | SHELL | (b) component calls `/crm/customers`, not its own `/vision/*` (10 routes, working) |
| **amp** | SHELL | (b) 489-line static page, zero fetch calls |
| **luxe** | UNKNOWN | 401 — `intake_projects`=503 behind auth |
| **market** | UNKNOWN | 401 — `listings`=2, `mf_products`=11 behind auth |

Two of these surface data the business already has and cannot see.

---

## HARD RULES

1. **🛑 STOP-GATED.** One part at a time. Report and wait.
2. **Map before fix.** Every part opens read-only. Report what you found
   before editing. If the diagnosis is wrong, the fix is wrong.
3. **No writes to business data.** GET-only against live endpoints. Never
   POST/PUT/PATCH/DELETE to a route that creates or mutates a customer,
   quote, ticket, lead, or listing.
4. **Do not touch** pay, ship, or llc. Out of scope by founder ruling.
5. **Do not edit `LeftNav.tsx` status literals.** Status accuracy is a
   separate decision that follows the registry work.
6. **Never print secrets** — tokens, PINs, API keys. PRESENT/ABSENT only.
7. Repo `~/empire-repo-main`, branch `feature/drawing-standard`. Commit each
   part separately and **push**. Never leave work on one disk.
8. Restart of `empire-backend.service` is permitted **only** where a part
   says so, and only after founder go-ahead in-session.
9. `sqlite3` CLI not installed — use `~/empire-repo-main/backend/venv/bin/python`.
10. Say what you verified vs inferred, per claim.

---

## PART A — LEADFORGE: 322 PROSPECTS THE UI CANNOT SEE

### A1 — Diagnose (read only)
```
grep -rn 'lf_leads\|lf_prospects\|FROM prospects\|"prospects"' ~/empire-repo-main/backend/app --include='*.py' | head -30
```
Find the router serving `/api/v1/leads/` and read its query. Then compare the
two tables' schemas — **this is the crux**:
```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
con = sqlite3.connect("file:/home/rg/empire-data/empire.db?mode=ro", uri=True)
for t in ("lf_leads","lf_prospects","prospects"):
    try:
        cols = [c[1] for c in con.execute(f'PRAGMA table_info("{t}")')]
        n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        print(f"\n=== {t}  rows={n} ===\n{cols}")
        for r in con.execute(f'SELECT * FROM "{t}" LIMIT 3'):
            print("  ", str(r)[:250])
    except Exception as e:
        print(f"\n=== {t} === ERROR {e}")
con.close()
PY
```

**Report before editing:** are `prospects` and `lf_prospects` the same shape?
If the columns differ materially, this is NOT a one-line fix — it is a
migration, and you should say so and stop. **Do not force a query onto a table
whose schema does not match.**

Also check whether anything else writes to `prospects`:
```
grep -rn 'INSERT INTO prospects\|prospects (' ~/empire-repo-main/backend/app --include='*.py' | head
```

🛑 **STOP.** Report: which router, which table it queries, both schemas,
whether they're compatible, and whether the fix is one line or a migration.

### A2 — Fix (only on go-ahead)
Point the reader at the populated table. Add a comment naming the date and why.
Prove it:
```
curl -s "http://localhost:8000/api/v1/leads/?limit=5" | head -c 400; echo
```
Expect real rows, not `{"leads":[],"total":0}`. **Requires a restart** — ask
first. Commit and push.

---

## PART B — SUPPORTFORGE: SAME SHAPE, DIFFERENT ROUTER

### B1 — Diagnose (read only)
`/api/v1/tickets/` returns `{"tickets":[],"total":0}` while `sf_tickets` has 3.
```
grep -rn 'sf_tickets' ~/empire-repo-main/backend/app --include='*.py' | head -20
```
Read the handler. **Three candidate causes — determine which:**
- queries a different table
- has a tenant/business filter excluding the rows
- filters on a status the 3 rows don't have

Dump the rows and see which applies:
```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
con = sqlite3.connect("file:/home/rg/empire-data/empire.db?mode=ro", uri=True)
cols = [c[1] for c in con.execute('PRAGMA table_info("sf_tickets")')]
print(cols)
for r in con.execute('SELECT * FROM sf_tickets'):
    print(dict(zip(cols, r)))
con.close()
PY
```

**If a tenant filter is excluding them, that filter may be correct** and the
rows may be test data. Say which — do not remove a filter that is doing its job.

🛑 **STOP.** Report cause and whether the rows are real or test.

### B2 — Fix (only on go-ahead, and only if the rows are real)
Same pattern as A2. Prove with a GET. Commit and push.

---

## PART C — VISION: WIRED TO THE WRONG ROUTER

`VisionAnalysisPage` fetches only `/crm/customers`. Its own `/api/v1/vision/*`
backend has 10 routes and `/vision/status` returns 567b.

### C1 — Diagnose (read only)
```
grep -rn 'fetch(\|api/v1' ~/empire-repo-main/empire-command-center/app/components/screens/VisionAnalysisPage.tsx
curl -s http://localhost:8000/openapi.json | ~/empire-repo-main/backend/venv/bin/python -c "
import sys, json
paths = json.load(sys.stdin)['paths']
for p in sorted(paths):
    if '/vision/' in p:
        print(','.join(sorted(m.upper() for m in paths[p])), p)
"
curl -s http://localhost:8000/api/v1/vision/status | head -c 400; echo
```
**Then answer the question that decides the fix:** what is the page *supposed*
to do? Read its JSX — does it render analysis results, an upload control, a
history list? Match the component's intent to the available routes.

**If the page renders customer-picking UI and vision is a later step, the
`/crm/customers` call may be correct and the page simply incomplete.** Say so
rather than assuming it is miswired.

🛑 **STOP.** Report the page's intent, the available routes, and which routes
it should call.

### C2 — Fix (only on go-ahead)
Wire the GET-able vision routes. **Do not wire upload/analysis POST routes** —
those mutate and are out of scope. Commit and push. **Portal rebuild required
for frontend changes:** `npm run build` then
`systemctl --user restart empire-portal` — ask before running either.

---

## PART D — AMP: DECISION BEFORE FIX

`app/amp/page.tsx` is 489 lines, zero fetch calls. R6 notes the readiness
registry calls AMP "safe to ship as a customer-facing standalone," suggesting
the real AMP app may deploy separately.

### D1 — Establish what AMP is (read only)
```
sed -n '1,60p' ~/empire-repo-main/empire-command-center/app/amp/page.tsx
grep -rn 'amp' ~/empire-repo-main/EMPIRE-MODULE-READINESS-REGISTRY.md | head -10
curl -s http://localhost:8000/openapi.json | ~/empire-repo-main/backend/venv/bin/python -c "
import sys, json
paths = json.load(sys.stdin)['paths']
for p in sorted(paths):
    if '/amp' in p: print(p)
"
ls -la /home/rg/empire-data/amp.db 2>&1
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
try:
    con = sqlite3.connect("file:/home/rg/empire-data/amp.db?mode=ro", uri=True)
    for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table'"):
        print(t, con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0])
    con.close()
except Exception as e:
    print("ERROR:", e)
PY
```

**Report only — no fix.** Is the CC page meant to be an AMP dashboard, a
marketing lobby, or a link to a separate deployment? The March strategy doc
describes AMP as a Spanish-language personal-growth product on a different
market entirely — which would make a static lobby page correct.

🛑 **STOP.** This one ends in a founder decision, not a patch.

---

## PART E — THE TWO AUTH PROBES

luxe and market both 401. R6 could not classify them. Resolve read-only.

### E1 — How does auth work here?
```
grep -rn 'Depends(\|get_current_user\|require_auth\|Bearer' ~/empire-repo-main/backend/app/routers/intake*.py 2>/dev/null | head -10
grep -rn 'headers\|Authorization\|token' ~/empire-repo-main/empire-command-center/app/components/screens/LuxeForgePage.tsx | head -10
grep -rn 'headers\|Authorization\|token' ~/empire-repo-main/empire-command-center/app/components/screens/MarketForgePage.tsx | head -10
```
**The question:** does the frontend send a token the backend expects, or does
it send nothing? If nothing, that's the bug and it is class (a). If it sends
one and still gets 401, the token is wrong or expired.

### E2 — Probe with a real token
`POST /api/v1/founder-token` issues one — **that endpoint was changed today by
H62 (`66ba3d3`)**, so it also serves as a live check of that fix.

**Ask the founder for the PIN before calling it. Never print the PIN or the
token.** Then GET the two endpoints with the token and report status + whether
the body has data.

```
# founder supplies PIN interactively; do not echo it
# then, with token in a shell var (never printed):
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOK" \
  "http://localhost:8000/api/v1/intake/admin/projects?limit=5"
curl -s -o /dev/null -w "%{http_code}\n" -H "Authorization: Bearer $TOK" \
  "http://localhost:8000/listings?limit=5"
```

🛑 **STOP.** Report: does auth resolve them to LIVE? Reclassify both. And
state plainly whether `/founder-token` worked — that is H62 verified in
production.

---

## REPORT

`~/R5_FIXES_2026-08-22.md`, section per part, then:
```
## VERIFIED
## INFERRED
## COULD NOT PROBE
```
Print at the end:
```
LEAD FIXED: YES/NO/MIGRATION-NEEDED
SUPPORT FIXED: YES/NO/ROWS-WERE-TEST
VISION FIXED: YES/NO/PAGE-INCOMPLETE-BY-DESIGN
AMP: <founder decision pending — what it is>
LUXE RECLASSIFIED: <LIVE / WIRED-EMPTY / still UNKNOWN>
MARKET RECLASSIFIED: <LIVE / WIRED-EMPTY / still UNKNOWN>
FOUNDER-TOKEN ENDPOINT WORKS: YES/NO   (H62 production check)
COMMITS: <hashes, pushed>
```

**A part that ends in "this is not what we thought" is a successful part.**
Three of these six could turn out to be correct as-built. Report that rather
than manufacturing a fix.
