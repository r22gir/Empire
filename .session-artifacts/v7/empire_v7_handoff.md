# Empire v7.0 Handoff — Competitive to Dominant

**Date:** 2026-04-04
**Score:** 6.5/10 → estimated 8.5-9.0/10
**Truth Check:** 30/30 passing

---

## Block 1: Client Portal

**How tokens work:** Each client gets a unique secure token link (no login required). Token is generated via `POST /api/v1/portal/generate` with customer_id and optional quote_id/job_id. Links expire after 30 days by default.

**What clients see:** Quote with line items, photos, drawings, production status with progress bar, invoice with payment history, approve/pay buttons.

**Auto-notifications:** When production stage changes, `notify_on_stage_change()` logs the event and can email the client if a portal token exists.

**New table:** `client_portal_tokens` (token, customer_id, permissions, access tracking)
**New endpoints:** 7 at `/api/v1/portal/*`
**New screen:** `/portal/[token]` (public, branded)

---

## Block 2: Production Board

**Kanban stages:** pending → fabric_ordered → fabric_received → cutting → sewing → finishing → qc → complete → delivered

**Color coding:** Red = overdue, Yellow = due within 2 days, Green = on track, Gray = no due date

**Advance flow:** Click "Advance →" on any card → moves to next stage → logs to production_log → notifies client if portal exists

**New endpoints:** Enhanced `/work-orders/production-board` with urgency/stage_counts, `/work-orders/overdue`
**New screen:** `/workroom/production`

---

## Block 3: Stripe Payments

**Keys:** Test keys in `.env` (sk_test_..., pk_test_...). To go live: replace with sk_live_ and pk_live_ from Stripe dashboard.

**Webhook setup:** Create webhook at https://dashboard.stripe.com/webhooks pointing to `https://api.empirebox.store/api/v1/payments/webhook`. Set STRIPE_WEBHOOK_SECRET in .env.

**Payment flow:** Portal pay button → create PaymentIntent → Stripe processes → webhook fires → records to payments table → updates invoice status

**Auto-reminders:** `POST /payments/send-reminders` checks all unpaid invoices and sends reminders for overdue and upcoming-due.

**New endpoints:** `/payments/create-intent`, `/payments/overdue`, `/payments/send-reminders`, `/payments/send-reminder/{id}`

---

## Block 4: One-Click Lifecycle

**Status cascades:**
- `quote_approved` → create job + send portal link
- `deposit_paid` → update quote to ordered + create work order
- `work_order_complete` → create invoice
- `invoice_paid` → complete job + update customer LTV

**Daily actions:** Prioritized list of everything needing attention: quotes to send, deposits to collect, work orders to create, overdue invoices, complete WOs to invoice.

**Quick stats:** Revenue MTD, active jobs, pending quotes, pipeline value, in production count.

**New endpoints:** `/lifecycle/cascade`, `/lifecycle/daily-actions`, `/lifecycle/quick-stats`

---

## Block 5: Financial Dashboards

**Dashboard:** Revenue/expenses/profit MTD+YTD, AR aging, expense breakdown, recent invoices.

**Drill-down endpoints:**
- `/finance/revenue-by-category` — grouped by item type (drapery, upholstery, etc.)
- `/finance/revenue-by-client` — top clients with lifetime value
- `/finance/ar-aging` — individual invoices in aging buckets
- `/finance/job-profitability/{id}` — revenue vs costs per job
- `/finance/monthly-comparison` — month-over-month with % change

**New screen:** `/workroom/finance` with KPI cards, bar charts, tables

---

## Block 6: Daily Ops + Ecosystem Sync

**Daily Ops screen:** `/workroom/ops` — founder's morning view with greeting, quick stats, prioritized actions, production overview. Auto-refreshes every 60s.

**MAX self-awareness updates:**
- `ecosystem_catalog.py` → v7.0 with new tables, endpoints, screens
- `capability_registry.json` → 5 new capabilities (portal, payments, dashboard, production, daily_ops)
- `system_prompt.py` → version 7.0, v7.0 features section

---

## What Still Needs

- Bank reconciliation / QuickBooks sync
- Multi-user with role-based access
- Mobile native app
- Stripe live keys (currently test mode)
- Full email sending for auto-notifications (currently logging)
- More production data (WOs and items) to populate boards

---

## Founder Test Commands

```
MAX, send portal link to [customer name]
MAX, show active portal links
MAX, show production board
MAX, what's overdue?
MAX, how much revenue this month?
MAX, who owes us money?
MAX, show P&L for this year
MAX, what are today's priorities?
MAX, show daily actions
```
