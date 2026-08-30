# D48 · STEP 2 — MAPPING GATE (read-only, no edits made)

`branch=feature/drawing-standard  HEAD=42194ad  working tree: no code changes`

Scope: the trust-mode writers that can produce a chain-violating row.
This document is the read-only map required before any edit. **Nothing has been edited.**

---

## §0 · Two corrections to the dispatch premise — verify before you accept the fix

The dispatch says: *"the running backend does not enable FKs (10 of 84 connections). These
writers are the only thing standing between a NULL customer and the database today. Do not
report the constraint as protecting you."*

I did not accept this. I tested it. **Two parts of it do not hold, and the correction changes
what STEP 2 has to do.**

### 0.1 · All seven writers are on the FK-enabled connection path

Every one of the four files imports the factory, not a raw connection:

```
routers/finance.py:14        from app.db.database import get_db, dict_row, dict_rows
routers/jobs.py:12           from app.db.database import get_db, dict_row, dict_rows
routers/jobs_unified.py:24   from app.db.database import get_db, dict_row, dict_rows
services/lifecycle_service.py:11  from app.db.database import get_db
```

`db/database.py:21` sets `PRAGMA foreign_keys=ON`. None of the seven writers appear among the
87 raw `sqlite3.connect` sites. The "10 of 84" figure counts *files containing raw connects*;
these writers are not in that population at all. They are on the pragma-ON path.

### 0.2 · NOT NULL does not need the pragma — the NULL leak is already closed at the DB layer

Measured on a copy of the live DB (`/tmp/d48map.db`), inserting into `invoices`:

| case | pragma | result |
|---|---|---|
| `customer_id = NULL` | ON | REJECTED — `NOT NULL constraint failed: invoices.customer_id` |
| `customer_id = NULL` | **OFF** | **REJECTED** — `NOT NULL constraint failed: invoices.customer_id` |
| `customer_id = 'ghost'` (dangling) | ON | REJECTED — `FOREIGN KEY constraint failed` |
| `customer_id = 'ghost'` (dangling) | **OFF** | **ACCEPTED — LEAK** |

SQLite enforces NOT NULL unconditionally; the pragma only gates `REFERENCES`. So after STEP 1:

- **A NULL customer can no longer reach the database from anywhere.** Not via these writers,
  not via the 87 raw connects.
- **A dangling (non-NULL, non-existent) customer_id still leaks** — but only on connections
  that skip the pragma, which these seven do not.

**Consequence for STEP 2:** the defect these writers carry today is **not** a silent NULL row.
It is an **uncaught `sqlite3.IntegrityError` surfacing as HTTP 500**. The corruption channel
became an availability failure. That is still a defect and still needs the fix the dispatch
asks for — reject cleanly, do not repair — but the justification is different, and the report
should say so rather than repeat a premise I measured to be false.

I am **not** reporting the constraint as protecting me: §0.4 below is the part that is genuinely unprotected.

### 0.3 · The severity is much higher than "a writer might get a NULL"

```
quotes_v2 total rows:                 199
quotes_v2 with customer_id NULL:      197
quotes_v2 with dangling customer_id:    1
jobs with dangling customer_id:         0
```

**197 of 199 quotes carry no customer link.** Both lifecycle writers read `q.get('customer_id')`
straight from that row. Exercised against an isolated copy through the real service functions:

```
probe quote: 0af9ab5f
create_job_from_quote        -> IntegrityError: NOT NULL constraint failed: jobs.customer_id
create_invoice_from_quote    -> IntegrityError: NOT NULL constraint failed: invoices.customer_id
```

`sqlite3.IntegrityError.__mro__` = IntegrityError → DatabaseError → Error → Exception.
It is **not** a `ValueError`, so `routers/lifecycle.py:40,60`'s `except ValueError` does not
catch it. It propagates uncaught. There is no `IntegrityError` handler in `main.py`.

**So `POST /api/v1/lifecycle/quote/{id}/create-job` and `.../create-invoice` return HTTP 500
for 197 of 199 quotes as of commit 42194ad.** STEP 1 closed a corruption hole and opened an
outage on the quote→job and quote→invoice transitions. This is the most important finding of
the pass and it is not in the STEP 1 report.

### 0.4 · STEP 1's schema hardening is not reproducible — it exists only in the live DB file

The NOT NULL/REFERENCES constraints were applied by direct table rebuild against
`/home/rg/empire-data/empire.db`. The DDL that *defines* these tables was never updated:

```
app/db/init_db.py:104   CREATE TABLE IF NOT EXISTS invoices ( ... customer_id TEXT,        <- no NOT NULL, no REFERENCES
app/db/init_db.py:192   CREATE TABLE IF NOT EXISTS jobs (     ... customer_id TEXT,        <- no NOT NULL, no REFERENCES
app/db/unified_business_migration.py — count of "customer_id TEXT NOT NULL": 0
```

Further: `unified_business_migration.create_all_tables()` — the function `tests/conftest.py:118`
uses to build the test schema — **does not create `invoices` or `jobs` at all.** It creates
financial_audit_log, quotes_v2, quote_line_items, quote_photos, work_orders, work_order_items,
production_log, payments_v2, chart_of_accounts, task_activity_new.

Three consequences, all load-bearing for this step:

1. **The test DB has no STEP-1 constraint.** This is why STEP 1 could report Δ=0 on the suite:
   no test could have exercised the constraint, because the constraint was never in the test
   schema. A green suite there proved nothing about the rebuild.
2. **A rejection test written naively will not reproduce prod.** It must build the chain tables
   with the hardened schema, or it tests a fiction. This directly governs dispatch constraint 2.
3. **The constraint is one `init_db.init_database()` away from being silently absent** on any
   rebuilt or newly provisioned database. STEP 1's gain is currently unreproducible.

---

## §1 · Per-writer map

Line numbers in the dispatch are **INSERT-statement sites**, not `def` lines. Both are given.
The dispatch lists seven entries while calling them "six" — `lifecycle_service.py:116` is the
extra one, absent from the STEP 1 report §6 list. All seven are mapped.

Route ownership below is taken from the **live** `/openapi.json`, not from reading `main.py`.
My first reading of the mount order predicted a route collision between `finance.py` and
`jobs_unified.py`; the live spec disproved it — `finance.py` carries its own `/finance` prefix,
so both coexist. The live spec is authoritative and is what is recorded here.

### W1 — `services/lifecycle_service.py:116` (def :83) `create_job_from_quote`

| | |
|---|---|
| customer_id path | `q.get('customer_id')` from the `quotes_v2` row; no check of any kind |
| reachable via | `POST /api/v1/lifecycle/quote/{quote_id}/create-job` (`routers/lifecycle.py:34`) |
| on NULL/absent | INSERT fires → `IntegrityError: NOT NULL constraint failed: jobs.customer_id` |
| caller sees | **HTTP 500.** `except ValueError` at `lifecycle.py:40` does not catch IntegrityError |
| live blast radius | **197 of 199 quotes** |
| side effects on failure | none persist — `get_db` rolls back (`database.py:33`) |

### W2 — `services/lifecycle_service.py:210` (def :173) `create_invoice_from_quote`

| | |
|---|---|
| customer_id path | `q.get('customer_id')` from the `quotes_v2` row; no check |
| reachable via | `POST /api/v1/lifecycle/quote/{quote_id}/create-invoice` (`routers/lifecycle.py:54`) |
| on NULL/absent | `IntegrityError: NOT NULL constraint failed: invoices.customer_id` |
| caller sees | **HTTP 500**, same reason as W1 |
| live blast radius | **197 of 199 quotes** |
| side effects on failure | none persist — rolled back |

### W3 — `routers/jobs_unified.py:1107` (def :1100) `create_job`

| | |
|---|---|
| customer_id path | `job.customer_id` straight off the request body; no check |
| schema | `JobCreateSchema:694` — `customer_id: Optional[str] = None` |
| reachable via | `POST /api/v1/jobs` — **live**, tag `jobs-unified` |
| on NULL/absent | `IntegrityError: NOT NULL constraint failed: jobs.customer_id` |
| caller sees | **HTTP 500** — no try/except anywhere in the handler |
| note | `SELECT * FROM jobs ORDER BY created_at DESC LIMIT 1` at :1147 reads back the newest row rather than the row just written — pre-existing race, unrelated to this step, not being fixed here |

### W4 — `routers/jobs_unified.py:2048` (def :2006) `invoice_from_job`

| | |
|---|---|
| customer_id path | `job.get("customer_id")` inherited from the fetched job row; no check |
| reachable via | `POST /api/v1/invoices/from-job/{job_id}` — **live**, tag `jobs-unified` |
| on NULL/absent | **Cannot produce NULL today**: `jobs.customer_id` is now NOT NULL, so every source job has a value. Currently unreachable as a NULL producer. |
| residual risk | inherits a **dangling** customer_id if one ever exists in `jobs` (0 such rows today). Leaks only on a pragma-off connection; this writer is pragma-on. |
| caller sees | 404 if job missing; otherwise success |
| classification | **trust-mode, but currently latent.** Hardening is defence-in-depth, not an active bug |

### W5 — `routers/finance.py:1426` (def :1391) `create_invoice` — **HYBRID, needs a ruling**

| | |
|---|---|
| customer_id path | `invoice.customer_id`; **if falsy AND `customer_name` present** → `_find_or_create_customer_for_invoice(...)` at :1399-1407 |
| schema | `InvoiceCreate:63` — both `customer_id` and `customer_name` Optional/None |
| reachable via | `POST /api/v1/finance/invoices` — **live**, tag `finance` |
| on NULL/absent | Only when **neither** `customer_id` **nor** `customer_name` is supplied does it fall through with `customer_id = None` → `IntegrityError` |
| caller sees | **HTTP 500** on that path |
| classification | **partly smart already.** Dispatch constraint 1 says do not extend find-or-create; constraint 3 says do not change smart-mode writers. The find-or-create here is pre-existing. See §3 Q1 |

### W6 — `routers/finance.py:1962` (def :1900) `create_invoice_from_job`

| | |
|---|---|
| customer_id path | `job.get("customer_id")` inherited from the job row; no check |
| reachable via | `POST /api/v1/finance/invoices/from-job/{job_id}` — **live**, tag `finance` |
| on NULL/absent | Same as W4 — cannot produce NULL today because `jobs.customer_id` is NOT NULL |
| caller sees | 404 if job missing; otherwise success |
| classification | **trust-mode, latent.** Same shape as W4 |

### W7 — `routers/jobs.py:301` (def :297) `create_job` — **DEAD SURFACE, NOT REACHABLE**

| | |
|---|---|
| customer_id path | `job.customer_id` off the body; no check. `JobCreate:23` — `Optional[str] = None` |
| reachable via | **nothing.** `main.py:179` reads `# load_router("app.routers.jobs", ...) # replaced by jobs_unified` — commented out |
| live confirmation | no POST route tagged `jobs` exists in `/openapi.json`; `POST /api/v1/jobs` is owned by `jobs-unified` |
| classification | **cannot produce a row today.** Hardening it is dead-code maintenance. See §3 Q2 |

### Summary

| | writer | can produce a bad row **today**? | caller sees today |
|---|---|---|---|
| W1 | lifecycle `create_job_from_quote` | no — but **500s on 197/199 quotes** | HTTP 500 |
| W2 | lifecycle `create_invoice_from_quote` | no — but **500s on 197/199 quotes** | HTTP 500 |
| W3 | jobs_unified `create_job` | no — 500s on any customer-less POST | HTTP 500 |
| W4 | jobs_unified `invoice_from_job` | no — latent, source is NOT NULL | 200 |
| W5 | finance `create_invoice` | no — 500s only when id *and* name absent | HTTP 500 |
| W6 | finance `create_invoice_from_job` | no — latent, source is NOT NULL | 200 |
| W7 | jobs `create_job` | **no — unmounted** | n/a |

**None of the seven can write a NULL customer today.** STEP 1 closed that. What they do instead
is fail with a 500 that names an internal SQLite constraint. That is what STEP 2 should convert
into an explicit, typed rejection — which is exactly the dispatch's instruction, arrived at for a
measured reason rather than an assumed one.

### Out of scope, confirmed smart-mode (constraint 3 — not touching)

- `jobs_unified.py:1682` `create_invoice` — unconditional find-or-create at :1670
- `jobs_unified.py:1506` `create_job_from_quote` — find-or-create at :1499

Note `jobs_unified.py:1682` is an **eighth** invoice writer serving live `POST /api/v1/invoices`
and is not named in the dispatch. It is smart-mode, so constraint 3 excludes it. Flagging it so
the omission is a decision, not an oversight.

---

## §2 · Proposed fix — for approval, not yet applied

**Shape.** A single shared guard, imported by all hardened writers, rather than seven inline
copies (CLAUDE.md chat/stream duality doctrine: one logic, one home):

```python
# app/services/chain_guard.py  (new, ~15 lines)
class MissingCustomerLink(ValueError):
    """A chain writer was given no resolvable customer."""

def require_customer(customer_id, *, writer, source):
    if not customer_id:
        raise MissingCustomerLink(
            f"{writer}: cannot create chain record without a customer. "
            f"Source {source} has no customer_id. Link a customer first."
        )
    return customer_id
```

Subclassing `ValueError` is deliberate: `routers/lifecycle.py:40,60` already maps `ValueError`
→ **HTTP 400**, so W1/W2 convert 500→400 with no router change. W3/W5 need an explicit
`except MissingCustomerLink` → `HTTPException(400)` since those handlers have no try block.

**Per writer:**

| writer | change | resulting caller experience |
|---|---|---|
| W1 | guard before INSERT at :115 | 400 + "quote X has no customer_id" (was 500) |
| W2 | guard before INSERT at :209 | 400 + same (was 500) |
| W3 | guard + `except` → 400 | 400 (was 500) |
| W4 | guard on inherited value | 400 instead of latent leak |
| W5 | guard **after** existing find-or-create, replacing only the NULL fall-through | 400 (was 500); find-or-create untouched |
| W6 | guard on inherited value | 400 instead of latent leak |
| W7 | **pending ruling** — see §3 Q2 | — |

Explicitly **not** doing: no find-or-create added anywhere (constraint 1); no smart-mode writer
touched (constraint 3); no change to the `SELECT ... ORDER BY created_at DESC LIMIT 1` race in
W3; no `IntegrityError` handler in `main.py` (that would mask, not reject).

**Tests — constraint 2.** The blocker from §0.4 is that the test schema lacks the constraint and
lacks the tables. So the tests must not rely on the DB to fail; they must assert the *guard*
fires. Plan: one rejection test per hardened writer, each asserting `MissingCustomerLink` /
HTTP 400, plus one test proving the guard fires **before** any INSERT is attempted (no partial
write, no audit-log row). Each will be run against the pre-change code first to show it fails —
per constraint 2, that failure will be pasted into the STEP 2 report, not merely claimed.

**Recommend folding in from §0.4** (ask, not assume — see §3 Q3): update `init_db.py:104,192` to
carry `customer_id TEXT NOT NULL REFERENCES customers(id)` so the constraint is reproducible and
testable. Without it the constraint survives only in one untracked file on disk.

---

## §3 · Questions blocking the edit

**Q1 — W5 `finance.py:1426`.** It already find-or-creates when `customer_name` is given.
Constraint 1 says a writer handed no customer must raise; constraint 3 says don't change
smart-mode writers. Do I (a) leave find-or-create intact and only convert the both-absent
fall-through to a 400 — my recommendation, it is the narrowest reading that satisfies both —
or (b) treat the whole writer as trust-mode and make it raise whenever `customer_id` is absent,
removing the find-or-create?

**Q2 — W7 `routers/jobs.py:301`.** Unmounted and unreachable. Harden it anyway for consistency,
or leave it and record it as dead surface for a deletion dispatch? It cannot produce a row either
way. My recommendation: harden it — it is three lines, and an unmounted router is one uncommented
line away from being live.

**Q3 — §0.4 schema reproducibility.** In or out of STEP 2? Leaving it out means the rejection
tests cannot reproduce prod behaviour and the STEP 1 constraint stays unreproducible. Bringing it
in widens this step beyond writer hardening. My recommendation: in — constraint 2 cannot be
honestly satisfied without it.

**Q4 — the 197/199 outage (§0.3).** Quote→job and quote→invoice are 500ing for essentially every
quote right now. Hardening converts that to a clean 400, which is correct but still a refusal —
the transition stays broken until quotes carry customers. Is backfilling `quotes_v2.customer_id`
a follow-on dispatch, or does it need to happen inside D48? I have **not** touched any data.

---

## §4 · State at the gate

- **No files edited. No code changed. No writes to the live database.**
- All probing used copies: `/tmp/d48map.db`, `/tmp/d48probe.db` (both removed).
- Live backend was read only via `GET /openapi.json`.
- Working tree at `42194ad` carries only pre-existing unrelated changes (`max/memory.md`,
  `uploads/EST-2026-261-mock.pdf`).
- Baseline `1543 / 129 / 30 / 1 / 13` **not yet re-confirmed** — I did not run the suite, since
  the delta is only meaningful once measured either side of an edit. First action after approval.

🛑 **MAPPING GATE** — awaiting rulings on Q1–Q4 before any edit.
