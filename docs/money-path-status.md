# Money Path Status — 10-Step Revenue Flow

**Date:** 2026-03-18
**Purpose:** Track every step from customer intake to payment received
**Overall:** 6 PASS, 4 PARTIAL — revenue flow works but has two blockers

---

## The 10 Steps

| Step | Description | Status | Evidence |
|------|-------------|--------|----------|
| 1 | Customer intake -> CRM | **PASS** | 5 real intake projects exist. CRM has real customer records. `/intake/*` and `/crm/customers` both respond. |
| 2 | Quote creation | **PASS** | 54 quote files in the system. `POST /quotes` creates new quotes with line items, materials, labor. |
| 3 | Quote PDF generation | **PASS** | WeasyPrint generates styled PDFs. Business name, address, and phone now render (commit f78c575). |
| 4 | Email quote via SendGrid | **PASS** | SendGrid API configured. Sends email with PDF attachment. Delivery confirmed in testing. |
| 5 | Quote -> Job conversion | **PASS** | Endpoint exists and responds. However, 0 jobs have been created — needs manual testing of the full conversion flow. |
| 6 | Job tracking on Kanban | **PARTIAL** | JobBoard.tsx renders 4 columns (New, In Progress, Review, Complete). Board is empty — blocked by Step 5 having 0 jobs. |
| 7 | Job -> Invoice | **PASS** | 11 real invoices exist in the system. Invoice creation from job data works. |
| 8 | Invoice PDF generation | **PASS** | WeasyPrint generates invoice PDFs. Business info now included (same fix as quote PDFs). |
| 9 | Payment via Stripe | **PARTIAL** | Stripe test keys configured in `.env`. Checkout endpoint returns 404 — route is not properly registered. Needs routing fix before any payment can process. |
| 10 | Payment confirmation | **PARTIAL** | Webhook handler code exists for Stripe `payment_intent.succeeded` events. Untested with live or test payments because Step 9 is broken. |

---

## Revenue Flow Diagram

```
Customer Intake [PASS]
       |
       v
  Quote Creation [PASS]
       |
       v
  Quote PDF [PASS] --> Email via SendGrid [PASS]
       |
       v
  Quote -> Job [PASS but 0 jobs]
       |
       v
  Kanban Tracking [PARTIAL - empty]
       |
       v
  Job -> Invoice [PASS]
       |
       v
  Invoice PDF [PASS]
       |
       v
  Stripe Payment [PARTIAL - 404] --> Confirmation [PARTIAL - untested]
```

---

## Blockers to First Dollar

1. **Stripe checkout 404** — The `/payments/checkout/*` route is not registered in the FastAPI router. Fix the route inclusion and test with Stripe test keys.
2. **Switch to Stripe live keys** — Currently using `sk_test_*` keys. Must switch to live keys and verify webhook signing secret.
3. **Customer acceptance page** — No `/intake/quote/[id]` page exists for customers to view and accept a quote. They receive the PDF by email but have no way to click "Accept" and trigger payment.
4. **Auto-deposit on acceptance** — When a customer accepts a quote, an invoice should be auto-created with a deposit amount. This logic does not exist yet.

---

## What Works Today (Manual Path)

A human operator can:
1. Enter a customer through intake
2. Create a quote with line items
3. Generate a PDF and email it
4. Manually create an invoice when the customer says yes
5. Generate an invoice PDF

What's missing is the **self-service** path: customer receives email -> clicks link -> views quote -> accepts -> pays deposit -> job auto-created.
