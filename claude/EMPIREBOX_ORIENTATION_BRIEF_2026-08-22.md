# EMPIREBOX ORIENTATION BRIEF
**Written 2026-08-22 · strategic Claude · from two read-only probes, Drive
history, and founder rulings this session**

Read this before diagnosing anything. It replaces the assumption — held for
months and wrong — that the system is broken and needs restoring.

---

## 1 · THE CORRECTION THAT REFRAMES EVERYTHING

**`~/empire-repo` is not a "stale fork." It was production.**

Per `EMPIREBOX_CURRENT_TRUTH_2026-05-14`: stable/live ran from `~/empire-repo`
on `feature/v10.0`, backend :8000, portal :3005, serving
`studio.empirebox.store`. The *test* lane was `~/empire-repo-v10` on :8010/:3010.

When canonical later moved to `~/empire-repo-main` (`feature/drawing-standard`),
`~/empire-repo` became **the previous production lane** — not drift. The nine
logged "incidents" of referencing it include people correctly remembering where
production used to live.

**Consequence for language:** stop saying fork/drift/eradicate. The accurate
frame is **an unfinished lane migration**. Two services and one hardcoded path
never moved. That is a much smaller problem, and it is the actual problem.

---

## 2 · FOUNDING INTENT (unchanged, per founder 2026-08-22)

EmpireBox is the **Founder Edition command center** controlling the Forge
products, run by an Office AI Agent. OpenClaw was the original agent. The
ContractorForge landing page was never the product.

Two real businesses anchor it: **Empire Workroom** (drapery/upholstery,
Hyattsville MD) and **WoodCraft by Empire** (CNC woodwork).

**Founder ruling, 2026-08-22 — the product question, finally answered:**
> *"Now it is my product, but always with the vision to sell."*

Operative consequences:
- Build **single-tenant**, but never in a way that makes multi-tenancy
  expensive later. The `business` column doctrine (Workroom vs WoodCraft as
  data, never hardcoded) is the pattern that protects this. Keep it absolute.
- **Deferred:** multi-tenant isolation, white-label, GDPR export tooling,
  LuxeForge subscription tiers/Stripe price IDs, the shop directory.
- **NOT deferred** (cheap now, expensive later): hardcoded JWT secret with a
  default fallback; unauthenticated admin endpoints; the duplicate-send loop.
- **Pricing is parked.** The March tier structure ($49/$149/$399,
  LuxeForge $19/$49) was drawn from a March codebase audit and the founder has
  ruled it needs reassessment once operational. Do not treat it as current.

**LuxeForge intake is core and stays.** 504 intake projects, 654 users, feeding
quotes. Only the *subscription billing layer* is deferred — not the front door.

---

## 3 · WHAT IS ACTUALLY TRUE RIGHT NOW (verified 2026-08-22)

### The business layer works
- Backend :8000 serves from `~/empire-repo-main/backend`. 1,086 routes.
- All six corridor capabilities return real data: **49 quotes / $84,888**,
  8 jobs, **32 invoices / $34,391 outstanding**, live Stripe payments,
  171 customers, 155 inventory items.
- MAX healthy: 17 desks, Telegram connected, email channel live.
- **Email is the working intake path.** Willard fabric/drawings/sofa,
  McLean-Whittington with photo sets, Hudson & Crane INOUYE via Nelma — every
  active job arrived through `max@empirebox.store`.
- The founder-send guard is enforced in code (F4 policy): quotes go to the
  founder, CC'd, never straight to the client.

### The truth layer, resolved
| File | Role | State |
|---|---|---|
| `~/empire-data/empire.db` | **the real corridor DB** | 24 MB, live WAL, 132 tables |
| `~/empire-data/empirebox.db` | SQLAlchemy default engine | 278 KB, empty, stale since Jun 25 — **vestigial** |
| `~/empire-data/intake.db` | intake | 466 KB, stale Jun 23 |

Corridor handlers use raw `sqlite3.connect` per request via `EMPIRE_TASK_DB`
→ `empire.db`. **224 opens in 30 s of traffic.** The `lsof` contradiction was a
snapshot artifact. Reads and writes are the same file. **No ambiguous write
path. Safe to write records.**

`payments/history` hits the Stripe API directly — no DB involved.

### The automation layer never landed
This is the real gap, and it is the founding premise.

| System | Store | Reality |
|---|---|---|
| **OpenClaw** | `openclaw_tasks` 7,390 | 5,945 failed lifetime. **+27 tasks in 57 days.** Dormant. |
| **MAX desks** | `atlas_tasks` 130 | 1 task in last 30 days. |
| **Hermes** | `kanban.db` | Real durable queue schema — `claim_lock`, `claim_expires`, `worker_pid`, `max_retries`, `consecutive_failures`, `task_runs`. **1 task, 0 runs, ever.** |

**MAX's `AsyncIOScheduler` is the only loop actually running:** daily_brief
08:00, check_overdue_tasks 09:00, sales_followup Mon 10:00, weekly_report
Fri 17:00, brain_sync 23:00, expire_crypto_payments q15m. It is cron-style —
a scheduler, not a general task engine.

**No canonical code calls Hermes for task execution.** The integration does not
exist.

---

## 4 · THE UNFINISHED MIGRATION — four artifacts, precise

1. **`unified_message_store.py:16`** hardcodes
   `~/empire-repo/backend/data/brain/unified_messages.db`. Canonical code
   writes MAX's memory into the old tree. **This is why the old lane is still
   alive.**
2. **`scheduler.py:300`** `brain_sync` path resolution falls back to the legacy
   fork path (no `MAX_MEMORY_PATH` set), writing `max/memory.md` there nightly.
3. **System `empire-openclaw.service`** — points at the old tree, enabled,
   `WantedBy=multi-user.target`, failing `EADDRINUSE` on 7878 in a
   **~70,000-cycle restart loop**, because the *canonical user unit* holds the
   port. Vestigial, journal-churning, does no work.
4. **`empire-backend-feature.service`** (:8020) points at the old venv. The
   main user backend unit's text also references it but is saved by a
   `zz-canonical-venv.conf` drop-in — **fragile**: remove the drop-in and it
   silently reverts.

### ⚠️ THE BRAIN IS SPLIT AND THE OLD TREE IS CURRENT

| | canonical (Jun 23) | old tree (Aug 22) | delta |
|---|---|---|---|
| memories | 21,933 | **25,714** | +3,781 |
| conversation_summaries | 623 | **802** | +179 |
| unified_messages | 21,808 | **22,854** | +1,046 |
| token_usage | 57,533 | **58,841** | +1,308 |

**The 2026-08-22B report's gate line `FORK DELETION WOULD DESTROY UNIQUE DATA:
NO` is correct for business tables and WRONG for the brain.** Its own VERIFIED
#6 documents the split. Deleting the old tree today destroys two months of
MAX's memory.

**MIGRATION ORDER IS FORCED: copy the brain FIRST, repoint the code SECOND.**
Repointing first silently reverts MAX to a June memory.

Business tables carry no such risk: 0 fork-only quotes/invoices/jobs; the 11
fork-only customers are `@test.com` / `555-` audit rows; the 1 fork-only intake
project is a BreakMap smoke test (`probe-29127@breakmap.local`).

---

## 5 · REPAIR SEQUENCE (proposed — founder rules before any execution)

**R0 — protective pair. Do first, per the 2026-06-26 assessment, still undone.**
Rotate the API token logged 29× to disk. **Run the backup script that has never
been run.** Cheap insurance where bad luck converts directly into catastrophe.

**R1 — brain migration.** Copy old-tree brain DBs to canonical position, verify
row counts match, THEN fix `unified_message_store.py:16` and set
`MAX_MEMORY_PATH`. Restart backend. Re-verify counts and that new writes land
canonical. This is the move that lets the old lane finally go quiet.

**R2 — kill the zombie unit.** Mask system `empire-openclaw.service`. Repoint
`empire-backend-feature.service`. Fix the main user unit's ExecStart in the unit
itself rather than relying on a drop-in.

**R3 — cheap security, while still cheap.** JWT default fallback → env, no
default. Auth on the unauthenticated admin endpoints. Investigate the
duplicate-send loop (EST-2026-111 fired 5× in 73 s on 8/16).

**R4 — the frozen brief.** Every morning brief 8/15–8/22 reports
`Inbox: 194 items` — identical for eight days. Stuck or hardcoded. A daily brief
carrying a fake figure trains the founder to stop reading it.

**R5 — the automation decision (founder ruling required).** Neither OpenClaw
nor Hermes is an autonomous engine today. Hermes has the *correct schema* and
zero mileage; OpenClaw has mileage and an 80% failure history. Wiring MAX's
desks to Hermes' existing queue is likely cheaper than reviving OpenClaw — but
it is a **build**, not a switch, and it should not start until R0–R2 are done.

**R6 — module registry reconciliation.** ~24 modules in code, 7 in the
authoritative registry, 22 in the catalog. Assign each: live / dev / dormant /
abandoned. The 2026-06-26 assessment called this the single highest-leverage
move — it is simultaneously the fix for "MAX doesn't know itself," the
foundation autonomy requires, and the forcing function for the portfolio
decision. Still undone.

---

## 6 · STANDING RULES CONFIRMED THIS SESSION

- **Founder sends; agents prepare.** Never offer to send client
  communications; never present "send it" as an option. Enforced in code (F4).
- **Bozzuto EST-2026-111 is SENT**, awaiting client response, may take weeks.
  Do not flag it.
- **Authority hierarchy** (`EMPIREBOX_CURRENT_TRUTH_2026-05-14` §9): live
  runtime → active-branch files → docs on branch → tests → git history →
  Drive reports → old PDFs. The May "Navigator v3 Strategic Synthesis" PDF and
  the navigator HTML rank near the bottom; probe output ranks at the top.
- **The May PDF's diagnostics were partly real and its citations are
  polluted** (TikTok clips, Hermès handbag pages cited for our Hermes). Test
  its file:line claims; ignore its "industry validation" layer and its
  90-day Temporal/OPA/CQRS roadmap, which is an unranked proposal, not findings.
- **Map before fix. Verified vs inferred, per claim. A scoped test count is
  never suite green.** (DOCTRINE)
- **Check what a model was given before concluding what it is.** Six for six on
  2026-08-20. MAX has not fabricated across two probe cycles.

---

## 7 · THE QUESTION STILL OPEN

From the 2026-06-26 assessment, unanswered on paper:
**does the platform serve the businesses, or has the platform become the
business?**

The founder's product ruling (§2) answers ownership but not time allocation.
With ~20 modules carrying "dev" status and a two-business production load,
R6 forces the answer. Until then, every session re-litigates scope.
