# Money Path Status — 10-Step Revenue Flow

**Date:** 2026-03-18
**Purpose:** Track every step from customer intake to payment received
**Overall:** 6 PASS, 4 PARTIAL — revenue flow works but has two blockers

---

## 2026-05-23 Canonical Pricing Engine Status

**Status:** PASS for backend pricing truth, snapshot preservation, and port 8000 smoke tests. Commit is not yet created; proposed commit is `feat(pricing): add canonical Workroom and Woodcraft pricing snapshots`.

**Purpose:** Empire pricing is now deterministic, explainable, auditable, versioned, and overrideable. AI can classify or suggest, but approved quote/invoice numbers must come from pricing methods, rate/formula versions, explicit inputs, tax policy, deposit policy, and manual overrides with reasons.

**Backend engine:** `backend/app/services/pricing/`
- `engine.py` calculates canonical Workroom and Woodcraft/CraftForge pricing snapshots.
- `invoice_snapshots.py` copies approved quote/design pricing snapshots into invoice creation paths without silently recalculating from current rate tables.
- Versions currently reported by `/api/v1/pricing/canonical/status`: `empire-pricing-engine-v1`, `pricing-formulas-2026.05`, `workroom-rates-2026.05`, `woodcraft-rates-2026.05`.

**Supported Workroom methods:** upholstery, cushions, pillows, drapery/window treatments, fabric/materials, labor, pickup/delivery/install, rush/custom surcharge. Supported formula components include fixed service price, quantity x unit rate, labor hours x rate, fabric yardage, linear foot, square foot, material cost plus markup, minimum charge, and complexity multiplier.

**Supported Woodcraft/CraftForge methods:** sheet goods, board-foot material, CNC/router machine time, design/drawing time, assembly labor, finishing/staining/painting, hardware, delivery/install, waste factor, markup, and complexity multiplier.

**Endpoints added:**
- `GET /api/v1/pricing/canonical/status`
- `POST /api/v1/pricing/workroom/calculate`
- `POST /api/v1/pricing/woodcraft/calculate`

**Snapshot fields:** `business_unit`, `module`, `product_category`, `pricing_method`, `pricing_inputs`, `rate_table_version`, `formula_version`, `calculation_steps`, `calculated_subtotal`, `discount_type`, `discount_amount`, `tax_policy`, `tax_amount`, `deposit_required`, `deposit_amount`, `balance_due`, `override_amount`, `override_reason`, `final_price`, `created_at`, `source_quote_id`, `source_line_item_id`, plus `pricing_engine_version`.

**Quote/design to invoice behavior:** `POST /api/v1/finance/invoices/from-quote/{quote_id}` now uses `build_quote_invoice_source()` and persists invoice-level `pricing_snapshot_json`, `tax_policy_json`, and `pricing_engine_version`. CraftForge `create_invoice_from_design()` now uses `build_design_invoice_source()` and persists the same fields. Line item quantity, unit rate, pricing method, pricing inputs, pricing result, and line-level pricing snapshots are preserved.

**Tax/deposit behavior:** no universal 6% tax is assumed by the canonical engine. Tax is carried as an explicit `tax_policy` object. Existing quote/design tax rates are wrapped as approved source tax policies for backward compatibility. Deposits are deterministic: explicit amount wins, explicit percent calculates against the approved source total, otherwise an existing snapshot deposit amount can be preserved. Manual override requires `override_reason`.

**Safe failure behavior:** unknown product categories return a pricing classification error. Removed unsafe canonical pricing fallbacks such as missing type -> accent chair, wall panel -> headboard, table linen/bedding -> pillow, and 3D scan -> sofa.

**Live status after restart:** stable backend on port 8000 restarted from `/home/rg/empire-repo-main/backend`; `/health`, canonical status, Workroom calculate, Woodcraft calculate, and unknown-category guard all returned expected responses.

**Tests run on 2026-05-23:**
- `tests/test_canonical_pricing_engine.py -q`: 12 passed.
- Workroom + Woodcraft lifecycle targeted tests: 2 passed.
- Backend import compile for pricing/quote/finance/CraftForge files: passed.
- `npm exec tsc -- --noEmit` in `empire-command-center`: passed.
- Known unrelated finance UI contract test still fails because the fixture payment date is `2026-04-12` and the runtime MTD window is May 2026.

**Pricing files changed:** pricing package, data path helper, pricing router, finance quote/design invoice paths, CraftForge design invoice path, quote path helpers, quote service snapshot columns, DB invoice snapshot columns, canonical pricing tests, and `empire-command-center/app/pricing/page.tsx` scaffold.

**Remaining P1 limitations:**
- JSON quote files and SQL `quotes_v2` still coexist and can diverge outside this snapshot-preservation patch.
- Legacy manual invoice/job invoice paths still carry older tax defaults in places; canonical pricing isolates tax policy but does not fully migrate every legacy path.
- Pricing Studio is a scaffold, not a full editor.
- Existing unrelated dirty files in MAX/ArchiveForge/API/LuxeForge need separate review and commit decisions.

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
