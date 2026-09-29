# D48 · STEP 2 — Writer hardening

`branch=feature/drawing-standard  base=42194ad  NOT COMMITTED (stopped before commit per directive)`

Order followed as ruled: schema reproducibility → baseline → writers.

---

## §0 · Per-founder caveats up front

1. **The running backend still does not enforce FK `REFERENCES` on most paths.** 87 raw
   `sqlite3.connect` sites exist; 10 files set the pragma. The seven writers in scope all use the
   `get_db` factory (pragma ON), but that is a property of *these* writers, not of the app. D50
   still owns the global refactor. **NOT NULL, by contrast, is enforced everywhere** — it needs no
   pragma (measured, §0 of the mapping report).
2. **STEP 1's live-DB constraints were unreproducible until this step.** They existed only in
   `/home/rg/empire-data/empire.db`. `init_db.py` — the DDL that *defines* `invoices` and `jobs` —
   still declared `customer_id TEXT`. One `init_database()` would have silently undone STEP 1.
3. **`create_job_from_quote` (W1) is non-functional in production for reasons unrelated to
   customer_id.** Found while testing; verified against a copy of the live DB. Not fixed — out of
   scope. See §4.1. This is the most consequential new finding in this step.
4. **No production data was touched.** Ruling 4 honoured: no quote backfill, no writes to
   `empire.db`. All probing was done on copies, since deleted.

---

## §1 · Ruling 3 — schema reproducibility (landed first)

### 1.1 `backend/app/db/init_db.py`

Three NOT NULL additions. The table-level `FOREIGN KEY ... REFERENCES` clauses already existed on
all three tables, so only the nullability was missing:

| line | before | after |
|---|---|---|
| 107 | `customer_id TEXT,` | `customer_id TEXT NOT NULL,` (invoices) |
| 133 | `invoice_id TEXT,` | `invoice_id TEXT NOT NULL,` (payments) |
| 195 | `customer_id TEXT,` | `customer_id TEXT NOT NULL,` (jobs) |

**Declared scope addition — flagging rather than burying it.** Production also carries
`is_legacy INTEGER NOT NULL DEFAULT 0` on `invoices`, `payments` and `jobs` (added by STEP 1);
`init_db.py` had it on none. Ruling 3's stated purpose is "so the test schema matches production",
and STEP 4 depends on `is_legacy`, so I added it to all three tables. It is additive with a
default and cannot fail. **Veto it and I will remove it** — it is beyond the literal enumeration
in the ruling.

Production DDL was read read-only (`mode=ro`) and replicated, not invented:

```
invoices: customer_id TEXT NOT NULL REFERENCES customers(id) │ is_legacy INTEGER NOT NULL DEFAULT 0
jobs:     customer_id TEXT NOT NULL REFERENCES customers(id) │ is_legacy INTEGER NOT NULL DEFAULT 0
payments: invoice_id  TEXT NOT NULL REFERENCES invoices(id)  │ customer_id TEXT REFERENCES customers(id)
```

`payments.customer_id` and `jobs.invoice_id` are deliberately left nullable to match production.

### 1.2 `backend/app/db/unified_business_migration.py`

`create_all_tables` did not create `invoices` or `jobs` at all — it builds 10 tables, none of them
chain tables, and `customers` was absent too. Rather than copy the DDL into a second place (two
definitions of `invoices` would be a new divergence defect — the failure mode CLAUDE.md's
chat/stream rule exists to prevent), it now executes `init_db.SCHEMA_SQL` first:

```python
from app.db.init_db import SCHEMA_SQL
conn.executescript(SCHEMA_SQL)
```

Verified safe: the two files define **disjoint** table sets (20 and 10, zero overlap), so nothing
is defined twice and `IF NOT EXISTS` cannot mask a divergence.

### 1.3 `backend/tests/conftest.py` — two consequences of the above

**(a) truncation list.** `_DATA_TABLES` had `invoices`/`jobs` but not `customers` or `payments` —
they had never existed in the test schema, so nothing could have depended on them. Added, ordered
children-before-parents (`payments` → `invoices` → … → `customers`) so the deletes hold under FK
enforcement.

**(b) production column shape.** `jobs_unified.init_schema()` ALTERs `jobs`/`invoices` up to
production shape (`job_number`, `client_name`, `business_unit`, `pipeline_stage`, +30 more). It
runs at **import** time, which under pytest is *before* the session fixture creates the tables — so
every ALTER silently no-opped and the test tables stayed narrower than production. It is now
re-run once inside `isolated_empire_db`, after the tables exist.

I initially had this call in my own test module's fixture. That worked, and it is why 4 unrelated
tests started passing — but only because my module ran first and ALTERed the *session-shared* DB.
**That is test-order dependence, not a fix**, so I moved it into conftest where it is
deterministic. Confirmed order-independent afterwards by running the affected module alone.

### 1.4 Proof — `backend/tests/test_d48_schema_parity.py` (new, 10 tests)

Fails without the change, passes with it:

```
WITHOUT: AssertionError: customers missing from the test schema — chain writers cannot be
         tested against production-shaped constraints
         AssertionError: invoices missing from the test schema — ...
         AssertionError: jobs missing from the test schema — ...
         AssertionError: payments missing from the test schema — ...
         AssertionError: invoices.customer_id absent from test schema
         → 10 failed

WITH:    10 passed
```

Includes an active-firing check, not merely a declaration check:

```
pragma=True:  REJECTED — NOT NULL constraint failed: invoices.customer_id
pragma=False: REJECTED — NOT NULL constraint failed: invoices.customer_id
```

---

## §2 · Baseline re-run — ruling: "expect the baseline to move. That delta is a finding"

Run after §1 landed, before any writer edit:

```
129 failed, 1543 passed, 30 skipped, 1 xfailed, 13 errors in 666.89s
```

**Δ = 0 / 0 / 0 / 0 / 0. The baseline did not move.** You predicted it would. It didn't, and the
reason is the finding:

- **0 tests import `lifecycle_service`.** W1 and W2 — the two writers 500ing for 197 of 199
  quotes — had *no test coverage of any kind*.
- Only **3** test files insert into `invoices`/`jobs` directly; **4** reference the writer routes.
  None supplied a NULL customer.
- `no such table` errors in the run: `quotes_v2` ×22, `code_mode_tasks` ×4, `listings` ×1 —
  **zero** for `invoices`/`jobs`.

So adding a constraint changed nothing because nothing exercised it. **This is the same reason
STEP 1's Δ=0 was vacuous** — I said so at the mapping gate, and the re-run confirms it rather
than refutes it. An unmoved suite here is evidence of missing coverage, not of safety. The tests
in §3 are the first to exercise these writers against production-shaped constraints.

---

## §3 · The writers

### 3.1 Shared guard — `backend/app/services/chain_guard.py` (new)

`MissingCustomerLink(ValueError)` + `require_customer()` / `require_invoice()`. One guard, one
home, per the chat/stream duality rule — not seven inline copies.

It **rejects, never repairs**: it performs no lookup and no creation. Subclassing `ValueError` is
load-bearing — `routers/lifecycle.py:40,60` already maps `ValueError` → HTTP 400, so W1/W2 convert
500 → 400 with **no router change**. A test asserts that subclassing, because if it breaks they
silently 500 again.

### 3.2 Per-writer changes and per-writer proof

Each row's "fails without" is from a run with **only the four writer files reverted** to 42194ad,
schema and tests kept:

| | writer | change | failure without the change |
|---|---|---|---|
| W1 | `lifecycle_service.py` `create_job_from_quote` | guard before INSERT; INSERT now takes guarded var | `IntegrityError: NOT NULL constraint failed: jobs.customer_id` ×2 |
| W2 | `lifecycle_service.py` `create_invoice_from_quote` | guard before INSERT | `IntegrityError: NOT NULL constraint failed: invoices.customer_id` ×2 |
| W3 | `jobs_unified.py` `create_job` | guard **before `get_db()`** so no job_number is consumed by a doomed request; `except` → 400 | `IntegrityError: NOT NULL constraint failed: jobs.customer_id` |
| W4 | `jobs_unified.py` `invoice_from_job` | guard on the value inherited from the job | `IntegrityError: FOREIGN KEY constraint failed` |
| W5 | `finance.py` `create_invoice` | **narrow** — find-or-create untouched; guard placed *after* it | `IntegrityError: NOT NULL constraint failed: invoices.customer_id` ×2 |
| W6 | `finance.py` `create_invoice_from_job` | guard on inherited value | `IntegrityError: FOREIGN KEY constraint failed` |
| W7 | `jobs.py` `create_job` | hardened per ruling 2 despite being unmounted | `IntegrityError: NOT NULL constraint failed: jobs.customer_id` |

**All seven represented. Ten rejection tests, all failing without the change.**

W4 and W6 fail on **FOREIGN KEY** rather than NOT NULL because their fixture job carries
`customer_id = ''` — an empty string satisfies NOT NULL while dangling. That is the exact leak row
from the mapping table (`invalid customer_id, pragma OFF → ACCEPTED`), and it is the only reachable
form of the defect for writers that inherit from a `jobs` row that is now NOT NULL.

**W5 narrowness, verified.** Ruling 1 was "close the both-absent fall-through only". While reading
`_find_or_create_customer_for_invoice` I found it also returns `None` at `finance.py:636` for a
*whitespace-only* name — that passes the `if invoice.customer_name` check at :1399 but resolves to
nothing. A guard placed **after** the find-or-create closes both paths with one check and removes
nothing. Both are covered by tests, plus `test_w5_find_or_create_is_left_intact` which asserts a
new customer is still auto-created from `customer_name` — the regression guard proving smart-mode
behaviour survived.

### 3.3 Rejections firing — shown, not claimed

```
[W] create_job_from_quote
    MissingCustomerLink: create_job_from_quote: refusing to create a chain record with no
    customer. Expected a customer link from quote qnull. Link a customer to that record first.

[W] create_invoice_from_quote
    MissingCustomerLink: create_invoice_from_quote: refusing to create a chain record with no
    customer. Expected a customer link from quote qnull. Link a customer to that record first.

[R] POST /api/v1/jobs  (no customer_id)                    HTTP 400  create_job: refusing …
[R] POST /api/v1/invoices/from-job/jempty                  HTTP 400  invoice_from_job: refusing …
[R] POST /api/v1/finance/invoices  (no id, no name)        HTTP 400  create_invoice: refusing …
[R] POST /api/v1/finance/invoices  (name='   ')            HTTP 400  create_invoice: refusing …
[R] POST /api/v1/finance/invoices/from-job/jempty          HTTP 400  create_invoice_from_job: …
```

Rejection tests also assert **nothing was written**: no `jobs`/`invoices` row, no
`financial_audit_log` row, and for W1 the quote is not left with a dangling `job_id`.

### 3.4 Test-entry caveat

`app.main` cannot be imported under test: `app/modules/label_station.py:52` connects to a
hardcoded production path at import time (pulled in by `main.py:702`), tripping conftest's
prod-write guard. That is the module-level `DB_PATH` defect class the D28 dispatch explicitly
deferred, so **I did not fix it**. The route tests instead mount the real `finance` and
`jobs_unified` router objects at the same `/api/v1` prefix `main.py` uses — real handlers, real
request/response cycle, only `main.py`'s unrelated import side effects skipped. This is weaker
than a full-app E2E door and is called out as such.

---

## §4 · New findings

### 4.1 W1 `create_job_from_quote` cannot insert into `jobs` at all — in production

Two column defects, independent of customer_id, verified against a **copy of the live DB**:

```
status='quoted', job_type='workroom'  -> REJECTED: CHECK constraint failed: status IN (...)
status='quoted' only                  -> REJECTED: CHECK constraint failed: status IN (...)
job_type='workroom' only              -> REJECTED: CHECK constraint failed: job_type IN (...)
both valid                            -> ACCEPTED
```

- `lifecycle_service.py:127` passes `status='quoted'`, which is not in the `jobs.status` CHECK
  (`pending, scheduled, in_progress, on_hold, completed, cancelled`).
- `lifecycle_service.py:128` passes `q.get('business_unit', 'workroom')` into the **`job_type`**
  column, whose CHECK is (`fabrication, installation, repair, consultation, delivery`). A business
  unit is being written into a job-type column — a column misalignment.

Production's CHECKs are byte-identical to `init_db.py`'s. So `POST
/api/v1/lifecycle/quote/{id}/create-job` fails for **every** quote, not merely the 197 without a
customer. My hardening changes its failure for those 197 from a 500 to a clean 400; for the other
2 it still 500s on the CHECK.

Not fixed — STEP 2's scope is the customer link. Encoded as
`@pytest.mark.xfail(strict=True)` with the full diagnosis in the reason, so it **fails loudly the
moment someone repairs it** rather than silently passing. Needs a ruling.

### 4.2 `jobs_unified.py:1147` reads back the wrong row

`create_job` returns `SELECT * FROM jobs ORDER BY created_at DESC LIMIT 1` — with second-granularity
timestamps this returns whichever row shares the newest second, not necessarily the row just
inserted. It returned a *fixture* job in testing. Pre-existing, flagged at the mapping gate, not
fixed. `test_w3_post_jobs_with_customer_still_succeeds` therefore asserts against the stored row
rather than the response body, and says so.

### 4.3 Live outage recorded per ruling 4

**`POST /api/v1/lifecycle/quote/{id}/create-job` and `.../create-invoice` fail for 197 of 199
quotes** (`quotes_v2.customer_id` NULL). Before this step: HTTP 500, uncaught
`sqlite3.IntegrityError`. After: HTTP 400 with an actionable message. **The transition remains
broken until quotes carry customers** — hardening makes the refusal honest, it does not restore
function. Backfill deferred to a follow-on dispatch per your ruling; no quote data touched.

---

## §5 · Test results

**Baseline:** `1543 passed / 129 failed / 30 skipped / 1 xfailed / 13 errors`
**Final:** `1575 passed / 126 failed / 30 skipped / 2 xfailed / 13 errors` in 650.67s

**Δ = passed +32 · failed −3 · skipped 0 · xfailed +1 · errors 0**

Accounted for exactly:

| | |
|---|---|
| +29 passed | new D48 tests (10 schema parity + 19 writer hardening) |
| +1 xfailed | the W1 CHECK finding (§4.1), strict |
| −4 failed | 4 `test_journey_review_queue.py` tests fixed by §1.3(b) — they query `jobs.client_name`, which the test schema never had (`OperationalError: no such column: client_name`) |
| +1 failed | **flake**, not a regression — see below |
| +3 passed net on pre-existing | the 4 above, minus the flake |

**Regression check by name, not by count** (counts can mask offsetting changes):

```
newly PASSING vs baseline (4):
  test_journey_review_queue.py::test_min_confidence_medium_includes_medium_and_high
  test_journey_review_queue.py::test_review_queue_does_not_modify_live_db
  test_journey_review_queue.py::test_review_queue_does_not_touch_legacy_tables
  test_journey_review_queue.py::test_write_review_queue_snapshot_writes_to_gitignored_path

newly FAILING vs baseline (1):
  test_max_operating_registry.py::test_operating_registry_hot_reloads_and_keeps_last_known_good
```

That one is a **confirmed flake**, not caused by this work — same code, consecutive isolated runs:

```
run 1: 1 failed
run 2: 1 passed
```

It is an mtime-sensitive hot-reload test with no connection to schema or chain writers. Effective
failed count is 125. I am reporting it as +1 rather than quietly excluding it.

**D48 files in isolation:** `29 passed, 1 xfailed`.

---

## §6 · Files changed (per-file, not aggregate)

| file | status | change |
|---|---|---|
| `backend/app/db/init_db.py` | M | +3 NOT NULL; +3 `is_legacy` (declared scope addition, §1.1) |
| `backend/app/db/unified_business_migration.py` | M | `create_all_tables` executes `init_db.SCHEMA_SQL` |
| `backend/app/services/chain_guard.py` | **new** | `MissingCustomerLink`, `require_customer`, `require_invoice` |
| `backend/app/services/lifecycle_service.py` | M | W1 + W2 guarded |
| `backend/app/routers/jobs_unified.py` | M | W3 + W4 guarded |
| `backend/app/routers/finance.py` | M | W5 (narrow) + W6 guarded |
| `backend/app/routers/jobs.py` | M | W7 guarded |
| `backend/tests/conftest.py` | M | `_DATA_TABLES` += payments, customers; `init_schema()` top-up |
| `backend/tests/test_d48_schema_parity.py` | **new** | 10 tests |
| `backend/tests/test_d48_writer_hardening.py` | **new** | 19 passed + 1 strict xfail |

Verified no writer still passes an unguarded value: all six remaining
`q.get('customer_id')` / `job.get("customer_id")` / `job.customer_id` occurrences are **guard
arguments**, confirmed line-by-line; every INSERT binds the guarded variable.

`max/memory.md` and `uploads/EST-2026-261-mock.pdf` are pre-existing, unrelated, and not mine to
stage.

---

## §7 · Rulings needed

1. **§4.1 W1 CHECK defects** — `status='quoted'` and `business_unit` written into `job_type`. Own
   dispatch, or fold into D48? It is the difference between quote→job being *honestly refused* and
   *working*.
2. **§1.1 `is_legacy`** — keep the declared scope addition, or strip it back to the literal ruling?
3. **§4.2** read-back defect at `jobs_unified.py:1147` — log as an H-number?
4. **§3.4** `label_station.py:52` blocks full-app testing. Still deferred, or promote it — it now
   blocks production-door E2E for the whole chain?

---

## §8 · Founder rulings received (2026-08-30) — dispositions

| # | ruling | disposition in this dispatch |
|---|---|---|
| 1 | **§4.1 W1 CHECK defects → own dispatch.** Keep `xfail(strict=True)`. The status/job_type CHECK questions are product decisions, not migration cleanup. | xfail retained as-is, strict, with the full diagnosis in its `reason`. No writer logic changed. |
| 2 | **§1.1 `is_legacy` → KEEP.** Parity with production was the purpose of the ruling. Note the addition and its reasoning in the commit message. | Kept on `invoices`, `payments`, `jobs`. Recorded in the commit message. |
| 3 | **§4.2 read-back → log as H-number.** Confident output where correctness is not guaranteed — same family. Do not fix in this dispatch. | Logged as **H79** below. Code untouched; the W3 positive test asserts against the stored row and documents why. |
| 4 | **§3.4 `label_station.py:52` → PROMOTE, own dispatch, high priority.** It blocks importing `app.main` under test, so no E2E can reach the chain through the production door. Combined with zero coverage of `lifecycle_service`, it is why two consecutive Δ=0 results proved nothing. | Not fixed here. Route tests continue to mount the real routers directly, with the limitation stated in §3.4. |

### H-numbers added

- **H79** — `routers/jobs_unified.py:1147` `create_job` returns the created job via
  `SELECT * FROM jobs ORDER BY created_at DESC LIMIT 1`. `created_at` has second granularity, so
  this returns whichever row shares the newest second — not necessarily the row just inserted. It
  **did** return an unrelated fixture job during D48 STEP 2 testing. The response is confidently
  shaped as "the job you just created" while correctness is not guaranteed: same family as the
  truth-gate rule that success claims require a real result. Per founder: log, do not fix in this
  dispatch.

### Promoted to their own dispatches (no H-number assigned — say if you want them numbered)

- **W1 CHECK defects** (§4.1) — product decision on the `jobs.status` and `jobs.job_type` CHECK
  sets versus what `create_job_from_quote` writes. Blocks quote→job ever functioning.
- **`label_station.py:52`** (§3.4) — hardcoded production path at import time; blocks `app.main`
  under test and therefore all production-door E2E for the chain. Founder-marked high priority.

🛑 Committed at the end of STEP 2 per directive. STEP 3 not started.

