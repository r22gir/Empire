# D46 · Phase 3 Batch 1 — COMMAND sidebar (4 items)

**Date:** 2026-08-28
**Branch:** `feature/drawing-standard` @ `4c524fc`
**Probe:** live HTTP GET to `http://localhost:8000` for each endpoint.
**DEAD** = the endpoint returned 4xx or 5xx (or did not exist) at probe time.

---

## 1. Owner's Desk — `kind=product` → `DashboardScreen`

**File:** `empire-command-center/app/components/screens/DashboardScreen.tsx`
**Sub-views:** none — single screen ("Empire Command Center" header).
**Endpoint:** `GET /api/v1/max/accuracy/stats?days=7`
**Status:** 200 — **ALIVE**

---

## 2. Empire Workroom — `kind=product` → `WorkroomPage`

**File:** `empire-command-center/app/components/screens/WorkroomPage.tsx`
**Sub-views (NAV_SECTIONS):** overview, finance, invoices, expenses, customers, quotes, inventory, jobs, templates, tasks, analysis, creations, payments, docs

| Sub-view | Component | Endpoint(s) | Status |
|---|---|---|---|
| overview | inline `OverviewSection` | `GET /quotes-v2?limit=20&business=workroom`, `GET /crm/customers?limit=5&sort_by=updated_at&sort_dir=desc&business=workroom`, `GET /finance/dashboard?range=this_month&business=workroom` | 200, 200, 200 — **ALIVE** |
| finance | `FinanceDashboard.tsx` (lazy) | (delegated to `FinanceDashboard`) | **DEFER to BUSINESS batch** |
| invoices | `InvoiceList.tsx` (lazy) | (delegated) | **DEFER to BUSINESS batch** |
| expenses | `ExpenseTracker.tsx` (lazy) | (delegated) | **DEFER to BUSINESS batch** |
| customers | `CustomerList.tsx` (lazy, business='workroom') | `GET /crm/customers?business=workroom` | **ALIVE** (covered Phase 1a) |
| quotes | inline `QuotesSection` | `GET /quotes-v2?limit=20&business=workroom` (same fetch as overview) | **ALIVE** |
| inventory | `InventorySection.tsx` (lazy) | (delegated) | **DEFER** |
| jobs | `JobBoard.tsx` (lazy) | (delegated) | **DEFER** |
| templates | `TemplateModule.tsx` (lazy) | (delegated) | **DEFER** |
| tasks | inline `TasksSection` | `GET /tasks/?limit=4&business=workroom` | 200 — **ALIVE** |
| analysis | inline PhotoAnalysisPanel | (delegated) | **DEFER** |
| creations | inline `CreationsSection` | (delegated) | **DEFER** |
| payments | `PaymentModule product="workroom"` (1 shared component, 14 callers) | `GET /finance/payments?customer_id=&business_unit=` | **ALIVE** (delegated) |
| docs | `ProductDocs product="workroom"` (1 shared component, 9 callers) | (uses docs registry) | **ALIVE** (delegated) |

**Endpoints confirmed live in this batch:** /api/v1/quotes-v2, /api/v1/crm/customers, /api/v1/finance/dashboard, /api/v1/tasks/.

---

## 3. WoodCraft — `kind=product` → `CraftForgePage`

**File:** `empire-command-center/app/components/screens/CraftForgePage.tsx`
**Sub-views:** customers, designs, jobs, dashboard, payments, docs

| Sub-view | Component | Endpoint(s) | Status |
|---|---|---|---|
| dashboard | (default) | `GET /craftforge/dashboard`, `GET /craftforge/jobs?limit=5`, `GET /craftforge/designs?limit=5` | 200, 200, 200 — **ALIVE** |
| customers | (local) | (delegated) | (Phase 3 BUSINESS) |
| designs | (lazy) | `GET /craftforge/designs?limit=5` | 200 — **ALIVE** |
| jobs | (lazy) | `GET /craftforge/jobs?limit=5` | 200 — **ALIVE** |
| payments | `<PaymentModule product="craft" />` | (delegated) | **ALIVE** |
| docs | `<ProductDocs product="craft" />` | (delegated) | **ALIVE** |

---

## 4. Daily Summary — `kind=daily-summary` → `RightPanel` (inline toggle)

**File:** `empire-command-center/app/components/layout/RightPanel.tsx`
**Sub-views:** inline dashboard panel toggled by sidebar — not a navigated page. Fetches happen on render.

**Endpoints (selected):**
- `GET /max/telegram/status` — 200 — **ALIVE**
- `GET /vision/history?limit=8` — **404 — DEAD**
- `GET /tasks/?limit=4&business=...` — 200 — **ALIVE**
- `GET /max/quality/metrics` — 200 — **ALIVE**
- `GET /max/intelligence/brief` — 200 — **ALIVE**
- `GET /max/intelligence/weekly` — 200 — **ALIVE**
- `GET /max/security/stats` — 200 — **ALIVE**
- `GET /max/intelligence/cost-per-desk` — 200 — **ALIVE**

**DEAD endpoint in this batch:** `GET /api/v1/vision/history?limit=8` — returns 404. Used by Daily Summary's vision-history widget. Silent failure (caught by `.then(d => ... || null)` in RightPanel.tsx:393-394).

---

## Batch 1 summary

- 4 sidebar items mapped.
- 1 DEAD endpoint found: `/api/v1/vision/history?limit=8`.
- 1 sidebar item (Empire Workroom) has 14 sub-views; 4 verified alive, 10 deferred to BUSINESS / other batches.

Not pushed. Continuing to batch 2.