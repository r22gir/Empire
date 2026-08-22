# DISPATCH R3 — MAKE MAX'S WORK REACH THE FOUNDER
**Date:** 2026-08-22 · **To:** M3 (EmpireDell)
**Predecessors:** R1 (`e07881c`), R2 Part A (`a683100`), R2 Part B
**Reference:** `EMPIREBOX_ORIENTATION_BRIEF_2026-08-22.md`

---

## WHY THIS DISPATCH EXISTS

Evidence gathered 2026-08-22 from 60 days of Gmail:

- MAX sent **14 non-brief emails in 60 days**. Six were infrastructure tests,
  seven were templated quote sends, and **exactly one was analysis** — a
  substantive InfoWorld piece on 8/17 12:50 that mapped the article onto
  EmpireBox's own architecture by name. That work was good, and **the founder
  did not see it** — it was buried in a 194-item inbox.
- On 8/16 the founder replied to MAX twice, directly:
  `"Can you read this?"` (18:11) and `"Can you read this mesaage Max?"` (18:23).
  **Both threads end there. MAX never replied to either.**
- `EST-2026-111` was sent **ten times** across two templates: 5× at 18:32–18:33
  on 8/16, 3× as "Estimate" variants at 19:21–19:39, 2× at 18:32 on 8/17.
- Every morning brief 8/15 → 8/22 reports `📥 Inbox: 194 items` — identical for
  eight consecutive days.

**The conclusion this dispatch acts on:** MAX's problem is not capability. It is
that MAX cannot see mail sent to it, and the one channel that surfaces its work
to the founder prints a frozen number. Outbound works; inbound has never worked.

Four defects. Each is understood. **None requires investigation before repair —
but each requires diagnosis before edit.**

---

## HARD RULES

1. **🛑 STOP-GATED.** One part at a time. Report and wait.
2. **Map before fix.** Every part begins read-only. Do not edit before reporting
   what you found.
3. **Never send to a client address.** All test sends go to
   `empirebox2026@gmail.com` only. If any code path could put a client address
   in `To:` during a test, **stop and report instead of running it**.
4. **Founder sends; MAX prepares.** Nothing in this dispatch may weaken the F4
   policy that routes client mail through the founder.
5. `sqlite3` CLI is NOT installed — use `~/empire-repo-main/backend/venv/bin/python`.
6. Known false alarm: `FOUNDER_PIN env var is UNSET` at import. The PIN is set.
7. Repo: `~/empire-repo-main`, branch `feature/drawing-standard`. `~/empire-repo`
   is the frozen previous production lane — do not write to it.
8. Restarting `empire-backend.service` IS permitted in this dispatch (R1's
   verification window closed at 23:00 last night). After any restart, re-prove
   the R1 env from `/proc/<pid>/environ`: `MAX_MEMORY_PATH`, `EMPIRE_BRAIN_DIR`.

---

## PART A — `check_inbox`: THE BROKEN LINK

The highest-value fix in the system. Everything downstream of it already works.

### A1 — Find it and read it (READ ONLY)
```
grep -rn 'check_inbox' ~/empire-repo-main/backend --include='*.py'
grep -rn 'def check_inbox\|IMAP\|imaplib\|gmail.*list\|messages().list' ~/empire-repo-main/backend/app --include='*.py' | head -30
grep -rn 'GMAIL_TOKEN_PATH\|GMAIL_CREDENTIALS_PATH\|gmail' ~/empire-repo-main/backend/app/services --include='*.py' | head -30
ls -la ~/.config/empirebox/gmail/ 2>&1
```
Report: is `check_inbox` a tool in the registry, a scheduler job, a route, or
only a function nobody calls? **Is it wired to anything at all?**

### A2 — Can it authenticate? (READ ONLY)
The drop-in sets `GMAIL_TOKEN_PATH` and `GMAIL_CREDENTIALS_PATH`. Verify the
files exist and the token is not expired. **Report key names and expiry only —
never print token values.**
```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import json, os
p = os.path.expanduser("~/.config/empirebox/gmail/token.json")
try:
    d = json.load(open(p))
    print("keys:", sorted(d.keys()))
    print("expiry:", d.get("expiry"))
    print("scopes:", d.get("scopes"))
except Exception as e:
    print("ERROR:", e)
PY
```
**Scopes matter most.** If the token carries only `gmail.send`, inbound read was
never possible — that is the whole bug, and it is a re-auth, not a code fix.

### A3 — Test the read path directly (READ ONLY)
Call whatever read function exists, in-process, against the real mailbox. Do not
send anything. Report the raw result or the raw exception.

Target: the two unanswered threads from 8/16 —
`"Can you read this?"` and `"Can you read this mesaage Max?"`. **If the read
path works now, those messages will come back.** That is the acceptance test.

🛑 **STOP.** Report: wired or not, authenticated or not, scopes, read result.
State plainly whether the failure is **missing scope**, **missing wiring**,
**broken code**, or **never implemented**.

---

## PART B — THE FROZEN BRIEF

`Inbox: 194 items`, identical 8/15 → 8/22. The brief is the only channel that
surfaces MAX's work; a fake number in it trains the founder to stop reading.

### B1 — Find the number's source (READ ONLY)
```
grep -rn 'def send_daily_brief\|daily_brief' ~/empire-repo-main/backend/app/services/max/scheduler.py
sed -n '/def send_daily_brief/,/^    async def /p' ~/empire-repo-main/backend/app/services/max/scheduler.py | head -80
grep -rn 'Inbox:\|inbox_count\|inbox.*items' ~/empire-repo-main/backend/app --include='*.py' | head -20
```
Report the exact expression producing `194`. Is it a live query, a cached value,
a file count, or a literal?

### B2 — Same question for the other two figures
`📋 Tasks: 0 open` and the CPU/RAM/Disk line. Disk moved (81.7% → 72.9%) across
the same window, so at least one figure is live. **Report which of the brief's
figures are live and which are frozen** — that tells us whether the brief is
half-broken or mostly broken.

### B3 — Fix
Make every figure a live query at send time. If a figure cannot be computed
reliably, **print nothing rather than a stale number**. A brief with three
honest lines beats one with five where two lie.

Then trigger a brief manually to `empirebox2026@gmail.com` and paste the body.

🛑 **STOP.** Report source of each figure, the diff, and the test brief body.

---

## PART C — THE DUPLICATE-SEND LOOP

One quote, ten sends, two templates. Client-facing risk.

### C1 — Two senders, or one sender called repeatedly? (READ ONLY)
Two distinct templates went out for the same quote:
- `"Quote EST-2026-111 — Hi {customer}, Please find your quote attached. — MAX"`
- `"Estimate EST-2026-111 — {customer} … Estimate Total: $8599.60"`

```
grep -rn 'Please find your quote attached' ~/empire-repo-main/backend --include='*.py' --include='*.html' --include='*.txt'
grep -rn 'Please find attached your estimate' ~/empire-repo-main/backend --include='*.py' --include='*.html' --include='*.txt'
grep -rn 'def send_quote\|send_estimate\|quote_email' ~/empire-repo-main/backend/app --include='*.py' | head -20
```
Report both call sites and who invokes each.

### C2 — Why five in 73 seconds? (READ ONLY)
Candidates: a retry loop with no idempotency key, a UI double-submit with no
debounce, a route registered twice, or a queue redelivering on a slow ack.
```
grep -rn 'retry\|for attempt\|while.*attempt' <the send module> | head -20
grep -rn 'idempot\|dedupe\|already_sent\|sent_at' ~/empire-repo-main/backend/app --include='*.py' | head -20
```
Check whether any table records a send (`financial_audit_log`, `quotes_v2.sent_at`):
```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
con = sqlite3.connect("file:/home/rg/empire-data/empire.db?mode=ro", uri=True)
for t in ("financial_audit_log",):
    cols = [c[1] for c in con.execute(f'PRAGMA table_info("{t}")')]
    print(t, cols)
    for r in con.execute(f'SELECT * FROM "{t}" ORDER BY rowid DESC LIMIT 10'):
        print(" ", r)
con.close()
PY
```

### C3 — Fix
Add an idempotency guard: a quote may not be emailed twice within a window
unless explicitly forced. Record the send. **Make the second send unreachable,
not merely discouraged.**

Test with `empirebox2026@gmail.com` only. Fire the same send twice and prove the
second is blocked.

🛑 **STOP.** Report root cause, diff, and the blocked-second-send proof.

---

## PART D — PROVIDER FALLBACK

`/api/v1/max/models` (2026-08-22): `minimax` primary, **all other providers
disabled, fallback disabled**. One stall and MAX is dark. The registry backing
this (`operating_registry.json`) has mtime **2026-05-15** — three months
unchanged.

### D1 — Read the config (READ ONLY)
```
~/empire-repo-main/backend/venv/bin/python -m json.tool ~/empire-repo-main/backend/app/services/max/operating_registry.json | head -60
stat -c '%n %y' ~/empire-repo-main/backend/app/services/max/operating_registry.json
curl -s http://localhost:8000/api/v1/max/models | ~/empire-repo-main/backend/venv/bin/python -m json.tool | head -60
grep -rn 'fallback' ~/empire-repo-main/backend/app/services/max --include='*.py' | head -20
```
Report: which providers have credentials present (**key names only, never
values**), which are disabled by policy vs. by missing credentials, and what
`fallback_eligible` actually controls in code.

### D2 — Report, do not change
**This part is diagnosis only.** Enabling a fallback provider changes which
model answers the founder — that is a founder decision, and it interacts with
the H68 fabrication question, which is still open.

Deliver: a table of provider → credential present? → disabled why? → would
enabling it require a code change or only config?

🛑 **STOP.** Report the table. No edits in Part D.

---

## REPORT

`~/R3_MAX_VISIBILITY_2026-08-22.md`, section per part, then:
```
## VERIFIED
## INFERRED
## COULD NOT PROBE
```
Print at the end:
```
CHECK_INBOX ROOT CAUSE: <scope / wiring / code / never implemented>
CHECK_INBOX WORKING NOW: YES/NO
BRIEF FIGURES LIVE: <n of n>
DUPLICATE SEND BLOCKED: YES/NO
FALLBACK: <diagnosis only — founder decision pending>
COMMIT: <hash, pushed>
```

Commit each part separately on `feature/drawing-standard` and push. Never leave
work on a single disk.
