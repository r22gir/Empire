# VendorOps Apostille Routing Design (Phase 4A)

**Status:** Read-only design. No code changes, no branches.
**Date:** 2026-06-08
**Author:** Empire Completion Coordinator
**Scope:** `backend/app/routers/vendorops.py`, `backend/app/services/vendorops_alert_runner.py`, `backend/tests/test_vendorops_core.py`, the apostille 12-step lifecycle.

---

## 1. What exists today

### 1.1 VendorOps router (25 routes)

| Method | Path | Purpose |
|---|---|---|
| GET | `/vendorops/plans` | List available plans |
| GET | `/vendorops/status` | Activation status |
| GET | `/vendorops/activation` | Activation state |
| POST | `/vendorops/activation/request-upgrade` | Request a tier upgrade |
| POST | `/vendorops/activation/checkout` | Stripe checkout for upgrade |
| POST | `/vendorops/activation/checkout-complete` | Webhook return target |
| POST | `/vendorops/activation/stripe-webhook` | Stripe webhook |
| GET | `/vendorops/alert-preferences` | Alert preferences |
| PATCH | `/vendorops/alert-preferences` | Update alert preferences |
| GET | `/vendorops/dashboard` | Dashboard summary |
| GET | `/vendorops/max-summary` | MAX-facing summary |
| POST | `/vendorops/max-action` | MAX action |
| POST | `/vendorops/approvals` | Create an approval request |
| POST | `/vendorops/approvals/{approval_id}/approve` | Approve |
| POST | `/vendorops/approvals/{approval_id}/reject` | Reject |
| GET | `/vendorops/approvals` | List approvals |
| POST | `/vendorops/accounts` | Create a vendor account |
| GET | `/vendorops/accounts` | List vendor accounts |
| PATCH | `/vendorops/accounts/{account_id}` | Update a vendor account |
| POST | `/vendorops/subscriptions` | Create a subscription |
| GET | `/vendorops/subscriptions` | List subscriptions |
| PATCH | `/vendorops/subscriptions/{subscription_id}` | Update a subscription |
| GET | `/vendorops/renewal-alerts` | List renewal alerts |
| POST | `/vendorops/renewal-alerts/generate` | Generate renewal alerts |
| POST | `/vendorops/renewal-alerts/deliver` | Deliver renewal alerts |
| GET | `/vendorops/renewal-alerts/runner-status` | Runner status |
| PATCH | `/vendorops/renewal-alerts/{alert_id}/review` | Review an alert |
| POST | `/vendorops/subscriptions/{subscription_id}/cancel` | Cancel a subscription |
| GET | `/vendorops/audit` | Audit log |

### 1.2 VendorOps data model (today)

`vo_accounts` table:
- `id`, `approval_id`, `vendor_name`, **`category`** (TEXT, default `'vendor'` — free-form string)
- `purpose`, `vendor_url`, `notes`, `tier`, `account_status`, `monthly_cost_usd`
- `renewal_date`, `renewal_cadence`
- `credential_ref_hash`, `credential_ref_masked` (no plaintext credentials)
- `credential_owner`, `created_at`, `updated_at`

Other tables: `vo_renewal_alerts`, `vo_alert_preferences`.

### 1.3 Alert runner

`backend/app/services/vendorops_alert_runner.py` is a single-class async runner:

- `VendorOpsAlertRunner` with `interval_seconds` (default 3600 = 1h)
- `start()` — runs `run_once()` in a loop with `asyncio.sleep`
- `run_once(limit=50)` — calls `deliver_renewal_alerts(limit=limit)` from `app.routers.vendorops`
- `status()` — returns `{running, interval_seconds, last_run_at, last_result, last_error}`

**Today's scope:** subscription renewal alerts only. There is no concept of "task", "task status", "task due date", "task SLA", or "task → customer update".

### 1.4 Tests

`test_vendorops_core.py` exists. The Founder's audit doesn't enumerate its contents, but it covers the core account/approval/renewal-alert flow.

### 1.5 Apostille hooks in VendorOps

**None.** The VendorOps router has zero references to apostille or apostapp. The `vo_accounts.category` is a free-form text field, so a vendor can be created with `category="apostille_notary_dc"` today, but the system does not know what to do with that category.

### 1.6 Front-end presence

**No** VendorOps top-level page in `/home/rg/empire-repo-main/empire-command-center/app/`. The 21 routes are invisible to the founder team without manual API calls.

---

## 2. The 12-Step Apostille Operational Lifecycle

Mapped to today's VendorOps primitives (none of these are wired today; this is the design target):

| Step | What happens | VendorOps primitive needed | Apostille data source |
|---|---|---|---|
| 1. Lead received | Customer submits intake form on the apostille landing page | NEW: `apostille_lead` (lightweight record) | apostapp `POST /customers` + `POST /orders` |
| 2. Documents uploaded | Customer uploads documents via the apostille intake form | (no change) | apostapp `POST /orders/{id}/documents` |
| 3. Intake reviewed | Founder reviews the order and verifies documents | NEW: review task (assigned to founder) | apostapp `GET /orders/{id}` |
| 4. Quote issued | Founder generates a quote and emails customer | NEW: `apostille_quote` record | apostapp `GET /pricing-calculator` (Founder runs it manually for v1) |
| 5. Payment received | Customer pays via Zelle/Venmo/wire; founder marks paid | NEW: `apostille_payment` record (free-form string in v1) | apostapp `PUT /orders/{id}` with `{"payment": "..."}` |
| 6. Vendor assigned | Founder assigns a notary / translator / courier / government-office task | NEW: `apostille_task` (the central new entity) | NEW: vendorops `POST /accounts` with `category=apostille_*` |
| 7. Government submission | Vendor physically takes documents to DC/MD/VA Secretary of State | NEW: `apostille_task` (status: in_progress) | (real-world) |
| 8. In progress | Vendor works on the task | NEW: `apostille_task` (status: in_progress, with notes/evidence) | NEW: `PATCH /apostille-tasks/{id}` |
| 9. Completed | Vendor marks the task complete (uploads receipt/certified copy) | NEW: `apostille_task` (status: completed, with evidence_url) | NEW: `PATCH /apostille-tasks/{id}` |
| 10. Customer notified | System sends a customer email (manual in v1) | NEW: customer-update trigger on `task_completed` | (manual in v1) |
| 11. Pickup / shipping | Customer picks up or receives shipping | NEW: `apostille_task` for delivery; status: ready_for_pickup or shipped | (manual in v1) |
| 12. Closed | Founder closes the order | (no change) | apostapp `PUT /orders/{id}` with `{"status": "closed"}` |

**The central new entity is `apostille_task`.** It is what makes the 12-step lifecycle operable in VendorOps.

---

## 3. Vendor Data Model Extension

### 3.1 New `vendor_type` enum

Add a new field to `vo_accounts` (or a separate `vo_vendor_types` table — see implementation note below):

```python
class VendorType(str, Enum):
    NOTARY_DC = "notary_dc"
    NOTARY_MD = "notary_md"
    NOTARY_VA = "notary_va"
    TRANSLATOR_ES_EN = "translator_es_en"
    TRANSLATOR_EN_ES = "translator_en_es"
    COURIER_LOCAL = "courier_local"          # DMV courier (same-day)
    COURIER_NATIONAL = "courier_national"    # USPS, FedEx, UPS
    GOV_OFFICE_DC = "government_office_dc"   # DC Secretary of State
    GOV_OFFICE_MD = "government_office_md"   # MD Secretary of State
    GOV_OFFICE_VA = "government_office_va"   # VA Secretary of State
    GOV_OFFICE_USDA = "government_office_usda"  # US Department of State (federal apostilles)
    PLUMBER = "plumber"  # existing — keep
    ELECTRICIAN = "electrician"  # existing — keep
    VENDOR = "vendor"  # existing — keep as default
```

### 3.2 Implementation note

The existing `vo_accounts.category` is a free-form TEXT field with default `'vendor'`. **Two implementation options:**

**Option A — reuse the `category` field** (lowest risk, recommended for v1):
- Apostille vendor categories are just strings (`apostille_notary_dc`, `apostille_translator_es_en`, etc.)
- No schema change required
- VendorOps API accepts the new strings
- Apostille task endpoints can filter by `category LIKE 'apostille_%'`
- **Trade-off:** the enum is not enforced at the DB level; bad data could enter via direct API calls

**Option B — add a `vendor_type` column** (cleaner, but requires migration):
- Add `vendor_type TEXT NOT NULL DEFAULT 'vendor'`
- Migrate existing rows
- New code can validate the type
- **Trade-off:** requires a migration on the `vo_accounts` table, which the Founder has flagged as "no destructive DB changes" for the sprint

**Recommendation:** Option A for v1 (use the existing `category` field). Defer Option B to v2 after a proper migration plan.

### 3.3 Apostille vendor data model (proposed)

Each apostille vendor record has:
- `id`, `vendor_name`, `category` (e.g., `apostille_notary_dc`)
- `service_area` (text — e.g., "Washington DC and Arlington")
- `languages` (array — e.g., `["en", "es"]`)
- `hourly_rate_usd` (decimal, optional)
- `flat_rate_usd` (decimal, optional)
- `tier` (free, pro, enterprise — reuses existing tier system)
- `account_status` (active, paused, archived — reuses existing)
- `credential_ref_hash` (reuses existing)
- `notes` (free-form text)
- `created_at`, `updated_at`

---

## 4. Apostille Task Schema

### 4.1 New `apostille_task` table

```sql
CREATE TABLE IF NOT EXISTS apostille_tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,             -- references apostapp order
    vendor_id INTEGER,                  -- references vo_accounts.id (nullable: founder handles some steps)
    task_type TEXT NOT NULL,            -- one of: lead, intake_review, quote, payment_received, vendor_assignment, gov_submission, in_progress, completed, customer_notify, pickup_shipping, closed
    status TEXT NOT NULL DEFAULT 'assigned',  -- assigned, in_progress, awaiting_input, completed, failed, cancelled
    due_at TIMESTAMP,                   -- when this task is due
    sla_hours INTEGER,                  -- the SLA window in hours (e.g. 24 for next-day service)
    cost_cents INTEGER DEFAULT 0,       -- the cost of this specific task (vendor cost, not customer-facing)
    notes TEXT,                         -- free-form notes
    evidence_url TEXT,                  -- uploaded receipt/certified copy/screenshot
    assigned_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX idx_apostille_tasks_order_id ON apostille_tasks(order_id);
CREATE INDEX idx_apostille_tasks_vendor_id ON apostille_tasks(vendor_id);
CREATE INDEX idx_apostille_tasks_status ON apostille_tasks(status);
CREATE INDEX idx_apostille_tasks_due_at ON apostille_tasks(due_at);
```

### 4.2 Task type enum (12 values, one per lifecycle step)

```python
class ApostilleTaskType(str, Enum):
    LEAD_RECEIVED = "lead_received"                # step 1
    INTAKE_REVIEW = "intake_review"                # step 3
    QUOTE_ISSUED = "quote_issued"                  # step 4
    PAYMENT_RECEIVED = "payment_received"          # step 5
    VENDOR_ASSIGNMENT = "vendor_assignment"        # step 6
    GOV_SUBMISSION = "gov_submission"              # step 7
    IN_PROGRESS = "in_progress"                    # step 8
    TASK_COMPLETED = "task_completed"              # step 9
    CUSTOMER_NOTIFY = "customer_notify"            # step 10
    PICKUP_SHIPPING = "pickup_shipping"            # step 11
    ORDER_CLOSED = "order_closed"                  # step 12
```

### 4.3 Task status enum

```python
class ApostilleTaskStatus(str, Enum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    AWAITING_INPUT = "awaiting_input"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
```

### 4.4 New API endpoints (proposed)

| Method | Path | Purpose |
|---|---|---|
| POST | `/vendorops/apostille-tasks` | Create a task |
| GET | `/vendorops/apostille-tasks` | List tasks (filter by order_id, vendor_id, status) |
| GET | `/vendorops/apostille-tasks/{task_id}` | Get one task |
| PATCH | `/vendorops/apostille-tasks/{task_id}` | Update a task (status, notes, evidence) |
| POST | `/vendorops/apostille-tasks/{task_id}/assign-vendor` | Assign a vendor to a task |
| POST | `/vendorops/apostille-tasks/{task_id}/complete` | Mark a task complete (uploads evidence) |
| GET | `/vendorops/apostille-tasks/overdue` | List overdue tasks |
| GET | `/vendorops/apostille-tasks/due-soon` | List tasks due in the next 24h |

---

## 5. Reminder / Alert Rules

The existing `vendorops_alert_runner.py` is the right place to extend. Today it only handles subscription renewals. Adding apostille tasks is a natural extension.

### 5.1 New alert rules for apostille tasks

| When | Who | Channel | Message template |
|---|---|---|---|
| 24h before `due_at` | Vendor (if assigned) | Telegram | "Task {task_id} for order {order_id} is due in 24h. View at /vendorops/apostille-tasks/{id}" |
| at `due_at` | Vendor + Founder | Telegram | "Task {task_id} is due now." |
| 24h after `due_at` overdue | Founder | Telegram | "Task {task_id} is OVERDUE. Order {order_id} is at risk." |
| 7d after `due_at` overdue | Founder | Telegram + email | "Task {task_id} is 7 days OVERDUE. Customer impact: {order_id}" |
| on `task_completed` (for customer-facing task types) | Customer | email (manual in v1) | "Your apostille order {order_id} has been [action]. {next-step-text}" |
| on `task_failed` | Founder | Telegram | "Task {task_id} FAILED. Reason: {notes}" |

### 5.2 Implementation

Extend `vendorops_alert_runner.py` with a new method `run_apostille_alerts()` that runs alongside the existing `run_once()` (subscription renewal alerts). Both can be called in the same `start()` loop:

```python
async def start(self):
    if self._running:
        return
    self._running = True
    while self._running:
        try:
            await self.run_once()           # subscription renewals (existing)
            await self.run_apostille_alerts()  # new — apostille tasks
        except Exception as exc:
            self.last_error = str(exc)
        await asyncio.sleep(self.interval_seconds)
```

The `run_apostille_alerts()` method queries the `apostille_tasks` table for tasks in the relevant time windows and dispatches Telegram/email notifications.

---

## 6. Customer Update Triggers

In v1, customer updates are **manual** — the founder sends the email. The system records what was sent so the audit trail is intact.

### 6.1 New `apostille_customer_updates` table (proposed)

```sql
CREATE TABLE IF NOT EXISTS apostille_customer_updates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id TEXT NOT NULL,
    task_id INTEGER,                      -- the task that triggered this update
    update_type TEXT NOT NULL,            -- one of: task_started, task_completed, task_failed, payment_received, order_ready, order_delivered
    channel TEXT NOT NULL,                -- email, sms, telegram (for v1: email only)
    sent_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    sent_by TEXT,                         -- "founder", "system", or vendor name
    message_text TEXT,                    -- the actual message sent
    recipient TEXT                        -- email address, phone, or telegram handle
);
```

### 6.2 In v1

The founder writes the email and presses send in their email client. Then they mark the update in the system: `POST /apostille-customer-updates` with `{"order_id": "...", "update_type": "task_completed", "message_text": "...", "recipient": "customer@example.com"}`. The audit trail is preserved.

### 6.3 In v2 (deferred)

A simple transactional email service (Postmark or SendGrid) sends the email automatically when a `task_completed` event fires. The system pre-fills the message template based on the task type.

---

## 7. Dashboard View (Founder)

A single page in the apostille admin section that shows:

- Open apostille orders (count + list)
- Overdue tasks (count + list, sorted by overdue duration)
- Vendors by type (e.g. "3 notaries in DC, 2 translators, 1 courier")
- Per-vendor queue (e.g. "Notary A has 2 active tasks")
- Today's deadlines (tasks due today)
- This week's deadlines (tasks due in the next 7 days)
- Customer updates pending (in v1: a list of "I should email these customers about this")

The dashboard is a read-only view. All action happens via the existing VendorOps API.

---

## 8. Integration Map

| Apostille step | VendorOps route | Notes |
|---|---|---|
| 1. Lead | (no VendorOps) | Apostille has its own intake |
| 2. Upload | (no VendorOps) | Apostille has its own upload |
| 3. Intake review | `POST /vendorops/apostille-tasks` (type=`intake_review`, vendor=founder) | Founder reviews the order |
| 4. Quote | `POST /vendorops/apostille-tasks` (type=`quote_issued`) | After founder emails the quote |
| 5. Payment | `POST /vendorops/apostille-tasks` (type=`payment_received`, vendor=founder) | After founder marks paid in apostapp |
| 6. Vendor assign | `POST /vendorops/accounts` (category=`apostille_*`) + `POST /vendorops/apostille-tasks` (type=`vendor_assignment`, vendor=new_id) | New vendor created if not exists |
| 7. Gov submission | `POST /vendorops/apostille-tasks` (type=`gov_submission`, vendor=gov_office) | Founder or vendor updates status |
| 8. In progress | `PATCH /vendorops/apostille-tasks/{id}` (status=`in_progress`) | Vendor updates |
| 9. Completed | `POST /vendorops/apostille-tasks/{id}/complete` | Vendor uploads evidence |
| 10. Customer notify | `POST /vendorops/apostille-customer-updates` | Founder records the email they sent |
| 11. Pickup/shipping | `POST /vendorops/apostille-tasks` (type=`pickup_shipping`) | Founder or vendor updates |
| 12. Closed | (no VendorOps) | Apostille has its own close |

---

## 9. Branch / Worktree Proposal

- **Branch:** `feature/vendorops-apostille-routing`
- **Worktree:** `/home/rg/empire-repo-main-vendorops-apostille` (new, from `main` HEAD `2867978`)
- **Files to touch:**
  - `backend/app/routers/vendorops.py` — add 8 new apostille-tasks endpoints
  - `backend/app/services/vendorops_alert_runner.py` — add `run_apostille_alerts()` method, extend `start()` loop
  - New model: `backend/app/models/apostille_vendor_task.py` (or inline in `vendorops.py`)
  - New table: `apostille_tasks` (SQLite migration)
  - New table: `apostille_customer_updates` (SQLite migration)
  - **Do NOT modify** `vo_accounts` schema (use the existing `category` field per Option A)
  - **Do NOT touch** `services/max/*` (read-only)
- **Tests:**
  - `test_vendorops_apostille_routing.py` — 12-step lifecycle end-to-end
  - `test_vendorops_apostille_alerts.py` — 24h-before / at-due / overdue alert triggers
  - `test_vendorops_apostille_customer_updates.py` — audit trail integrity
- **Risk:** **medium** — touches the alert runner which is in production. The new method `run_apostille_alerts()` is additive; the existing `run_once()` is unchanged. The Founder should review the alert messages before they go live.
- **Owner:** Harry or Codex

---

## 10. Do not proceed list (audit phase)

This design made no code changes, created no branches, ran no tests, edited no MAX files, modified no production schemas, and sent no notifications. All other repo state is unchanged.
