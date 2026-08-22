# DISPATCH R7 — CAMPAIGN MACHINERY + OPENCLAW AUTOPSY
**Date:** 2026-08-22 · **To:** M3 (EmpireDell)
**Mode:** **READ ONLY, ALL PARTS.** No edits, no restarts, no sends, no task
submissions. Nothing here touches a prospect, a campaign, or a queue.

**Predecessors:** `R6_NAV_SWEEP_2026-08-22.md`, `R5_FIXES_2026-08-22.md` §A1
(which correctly overturned the LeadForge "bug" — the router is right as-built).

---

## WHY

The founder wants MAX to delegate tasks that run an outreach campaign against
the **322 scouted prospects** in the `prospects` table. Before that can be
designed, two things must be established with evidence, not preference:

**Question 1 — what does the campaign machinery actually do?**
`campaign_service.py` exists. `lf_prospects` carries `campaign_id` and
`converted_to_lead`. Routes exist for `campaigns`, `enroll`, `execute`, `send`,
`drafts`, `followups`. All at zero rows. The plumbing is built and has never
been run. **Automating a workflow nobody has performed once is how an agent
ends up executing the wrong process at machine speed.**

**Question 2 — what can actually run a task today?**
OpenClaw: 7,390 tasks, 5,945 failed, dormant. Hermes: correct durable-queue
schema, **one task, zero runs, ever**. Nobody has looked at *why* OpenClaw
failed. If those 5,945 failures are one root cause, OpenClaw was misconfigured
and reviving it is hours. If they are hundreds of distinct causes, it is unfit
and Hermes is the rebuild. **That is a query, not an opinion.**

---

## HARD RULES

1. **READ ONLY.** GET only. **Never POST to any campaign, send, enroll,
   execute, promote, or task endpoint** — those mutate, and one of them can
   put mail in front of a real business.
2. **Never send email.** Not a test, not to the founder, not to a seeded
   address. If a code path could reach an external recipient, **read it and
   report it — do not execute it.**
3. **Do not submit a task** to OpenClaw or Hermes. Reading the queue is the
   job.
4. Do not restart anything. Backend PID 967507 and portal :3005 stay up.
5. Never print secrets, PINs, tokens, or **prospect contact details** — report
   counts and shapes, not names/emails/phones of real businesses.
6. Repo `~/empire-repo-main`. `sqlite3` CLI not installed — use
   `~/empire-repo-main/backend/venv/bin/python`.
7. **Say what you verified vs inferred, per claim.** A1 was a successful part
   because it overturned its own premise. Do that again if the evidence says so.

---

## PART 1 — OPENCLAW AUTOPSY: WHAT WERE THE 5,945 FAILURES?

This is the decisive part. Do it first.

### 1.1 — Group the failures
```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3, collections, re
con = sqlite3.connect("file:/home/rg/empire-data/empire.db?mode=ro", uri=True)
cols = [c[1] for c in con.execute('PRAGMA table_info("openclaw_tasks")')]
print("COLUMNS:", cols)
print()
for row in con.execute("SELECT status, COUNT(*) FROM openclaw_tasks GROUP BY status ORDER BY 2 DESC"):
    print(f"  {row[0]:<20} {row[1]}")
print()
# normalise error text so variants collapse into one bucket
def norm(e):
    if not e: return "(null)"
    e = str(e)
    e = re.sub(r'\d+', 'N', e)
    e = re.sub(r"'[^']*'", "'X'", e)
    e = re.sub(r'/[^\s]+', '/PATH', e)
    return e[:160]
c = collections.Counter(norm(r[0]) for r in
    con.execute("SELECT error FROM openclaw_tasks WHERE status LIKE '%fail%' OR error IS NOT NULL"))
print(f"DISTINCT NORMALISED ERROR SHAPES: {len(c)}")
print()
for e, n in c.most_common(25):
    print(f"{n:6}  {e}")
con.close()
PY
```

**This single output answers the question.** If the top 1–3 shapes cover most
of the 5,945, OpenClaw has a handful of root causes. If the distribution is
flat across hundreds of shapes, it is unfit.

### 1.2 — When did it stop working, and what changed?
```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
con = sqlite3.connect("file:/home/rg/empire-data/empire.db?mode=ro", uri=True)
print("=== last 10 tasks that COMPLETED ===")
for r in con.execute("""SELECT id, title, status, created_at, completed_at
                        FROM openclaw_tasks
                        WHERE status IN ('completed','done','success')
                        ORDER BY COALESCE(completed_at, created_at) DESC LIMIT 10"""):
    print(" ", str(r)[:200])
print("\n=== monthly volume + failure rate ===")
for r in con.execute("""SELECT substr(created_at,1,7) m, COUNT(*) total,
                        SUM(CASE WHEN status LIKE '%fail%' THEN 1 ELSE 0 END) failed
                        FROM openclaw_tasks GROUP BY m ORDER BY m"""):
    tot, fail = r[1], r[2] or 0
    print(f"  {r[0]}  total={tot:<6} failed={fail:<6} rate={100*fail/tot if tot else 0:.0f}%")
con.close()
PY
```
**Report the month the failure rate changed.** Then check what changed around
it: `cd ~/empire-repo-main && git log --oneline --since=<that month> --until=<+1mo> -- openclaw/ backend/app/services/max/openclaw_gate.py | head -20`

### 1.3 — What kind of work were they?
```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3, collections
con = sqlite3.connect("file:/home/rg/empire-data/empire.db?mode=ro", uri=True)
print("BY DESK:")
for r in con.execute("SELECT desk, COUNT(*) FROM openclaw_tasks GROUP BY desk ORDER BY 2 DESC LIMIT 15"):
    print(f"  {str(r[0]):<25} {r[1]}")
print("\nBY SOURCE:")
for r in con.execute("SELECT source, COUNT(*) FROM openclaw_tasks GROUP BY source ORDER BY 2 DESC LIMIT 15"):
    print(f"  {str(r[0]):<25} {r[1]}")
print("\nSAMPLE TITLES (5 failed, 5 completed):")
for st in ("fail","complet"):
    for r in con.execute(f"SELECT title FROM openclaw_tasks WHERE status LIKE '%{st}%' LIMIT 5"):
        print(f"  [{st}] {str(r[0])[:110]}")
con.close()
PY
```
**The question this answers:** were these real business tasks, or test/probe
noise from development? A 7,390-task graveyard of dev probes means something
very different from 7,390 failed business operations.

**PART 1 verdict, required:**
`TOP ERROR SHAPE COVERS: <n>% of failures` ·
`DISTINCT ROOT CAUSES (est): <n>` ·
`LAST SUCCESSFUL TASK: <date>` ·
`FAILURES ARE: dev-noise / real-work / mixed` ·
`OPENCLAW VERDICT: misconfigured-and-revivable / unfit / cannot-determine`

🛑 **STOP.** This verdict decides the engine question. Report before Part 2.

---

## PART 2 — HERMES: WHAT WOULD IT TAKE TO USE IT?

### 2.1 — The queue, read
```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
con = sqlite3.connect("file:/home/rg/.hermes/kanban.db?mode=ro", uri=True)
for t in ("tasks","task_runs","task_events"):
    try:
        cols = [c[1] for c in con.execute(f'PRAGMA table_info("{t}")')]
        n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
        print(f"\n=== {t}  rows={n} ===\n{cols}")
        for r in con.execute(f'SELECT * FROM "{t}" LIMIT 3'):
            print("  ", str(r)[:250])
    except Exception as e:
        print(f"\n=== {t} === {e}")
con.close()
PY
```
Read the one task that exists. **What was it, when, did it run, what happened?**

### 2.2 — Is there a worker?
```
curl -s -m 5 http://localhost:3000/health; echo
ps -o pid,etime,cmd -p 1757 2>&1 | head -3
grep -rn 'claim_lock\|worker_pid\|heartbeat\|poll' ~/.hermes/*.py 2>/dev/null | head -20
ls -1 ~/.hermes/ | head -30
```
**The question:** does a Hermes worker process poll that queue, or is the
schema present with nothing draining it? A queue nobody reads is a table.

### 2.3 — What would MAX→Hermes delegation require?
```
grep -rn -i 'hermes' ~/empire-repo-main/backend/app --include='*.py' | grep -v test | head -30
```
Report every canonical touchpoint. **If there are none, say so plainly** — then
"Hermes steps in" is a build, and the report should say roughly what it spans:
a delegation call site, a task schema mapping, a result callback, and a
failure/retry path.

🛑 **STOP.** Report: worker or no worker, integration or none, size of the gap.

---

## PART 3 — THE CAMPAIGN MACHINERY (READ, DO NOT RUN)

### 3.1 — What campaign_service actually does
```
wc -l ~/empire-repo-main/backend/app/services/leadforge/campaign_service.py
grep -n '^class \|^def \|^    def ' ~/empire-repo-main/backend/app/services/leadforge/campaign_service.py
```
Then read the send path in full. **The critical question, answer explicitly:**

> **Can any code path in campaign_service reach an external recipient — a real
> prospect's email or phone — and if so, what gates it?**

```
grep -n -i 'smtp\|send_mail\|sendgrid\|gmail\|to=\|recipient\|twilio\|sms' ~/empire-repo-main/backend/app/services/leadforge/campaign_service.py
grep -rn 'F4\|founder_send\|founder-only\|whitelist' ~/empire-repo-main/backend/app/services --include='*.py' | head -20
```
Doctrine and code both say **founder sends; agents prepare**, enforced by the
F4 policy. Confirm that guard covers the campaign path too, or report that it
does not. **This is the most important finding in Part 3.**

### 3.2 — The campaign tables
```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
con = sqlite3.connect("file:/home/rg/empire-data/empire.db?mode=ro", uri=True)
for (t,) in con.execute("""SELECT name FROM sqlite_master WHERE type='table'
                           AND (name LIKE '%campaign%' OR name LIKE 'lf_%')"""):
    cols = [c[1] for c in con.execute(f'PRAGMA table_info("{t}")')]
    n = con.execute(f'SELECT COUNT(*) FROM "{t}"').fetchone()[0]
    print(f"{t:<28} rows={n}\n   {cols}\n")
con.close()
PY
```

### 3.3 — Are the 322 prospects contactable?
Counts only. **Do not print names, emails, or phone numbers.**
```
~/empire-repo-main/backend/venv/bin/python - <<'PY'
import sqlite3
con = sqlite3.connect("file:/home/rg/empire-data/empire.db?mode=ro", uri=True)
q = lambda s: con.execute(s).fetchone()[0]
print("total                 ", q("SELECT COUNT(*) FROM prospects"))
print("has email             ", q("SELECT COUNT(*) FROM prospects WHERE email IS NOT NULL AND email!=''"))
print("has phone             ", q("SELECT COUNT(*) FROM prospects WHERE phone IS NOT NULL AND phone!=''"))
print("has website           ", q("SELECT COUNT(*) FROM prospects WHERE website IS NOT NULL AND website!=''"))
print("outreach_ready        ", q("SELECT COUNT(*) FROM prospects WHERE outreach_ready=1"))
print()
for r in con.execute("SELECT client_type, COUNT(*) FROM prospects GROUP BY client_type ORDER BY 2 DESC LIMIT 10"):
    print(f"  {str(r[0]):<28} {r[1]}")
print()
for r in con.execute("SELECT outreach_priority, COUNT(*) FROM prospects GROUP BY outreach_priority ORDER BY 2 DESC LIMIT 10"):
    print(f"  priority {str(r[0]):<18} {r[1]}")
con.close()
PY
```
**A campaign is only as big as its contactable set.** If 322 rows carry 40
emails, that is the real campaign size and it changes the whole design.

### 3.4 — What a single manual run would take
From the code, list the exact ordered steps to move ONE prospect from the pool
to a drafted, founder-reviewable outreach message — endpoint by endpoint, with
which are GET and which mutate. **Do not execute any of them.**

🛑 **STOP.** Report the send-gate answer, the contactable counts, and the
manual-run recipe.

---

## REPORT

`~/R7_CAMPAIGN_ENGINE_2026-08-22.md`, section per part, then:
```
## VERIFIED
## INFERRED
## COULD NOT PROBE
```
Print at the end:
```
OPENCLAW: top error shape = <n>% · distinct causes ≈ <n> · verdict = <>
LAST SUCCESSFUL OPENCLAW TASK: <date>
HERMES WORKER POLLING: YES/NO
MAX→HERMES INTEGRATION EXISTS: YES/NO
CAMPAIGN CAN REACH EXTERNAL RECIPIENT: YES/NO — gated by <>
PROSPECTS CONTACTABLE BY EMAIL: <n> of 322
MANUAL RUN STEPS: <n> endpoints, <n> of which mutate
```

**Do not recommend an engine.** Report what each can do. The founder rules.
