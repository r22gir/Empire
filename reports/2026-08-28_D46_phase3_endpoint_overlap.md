# D46 · Phase 3b — Endpoint overlap and dead-surface summary

**Date:** 2026-08-28
**Branch:** `feature/drawing-standard` @ `45a1aed`

---

## Endpoints called from more than one product (genuinely shared)

Front-end scan across `empire-command-center/app/components/{screens,business}/` using `${API}/...` patterns, deduplicated:

| Endpoint | Call sites |
|---|---|
| `/crm/customers` | 6 — ForgeCRM (Quick Stats + CustomerList woodcraft), WorkroomPage Customers, SalesScreen, BusinessProfileScreen, SupportForge customers, VisionAnalysisPage |
| `/finance/invoices` (and `/finance/invoices/` with trailing slash) | 9 + 5 = **14 calls** across FinanceDashboard, InvoiceList, EmpirePay, EmpireAssist, BusinessProfile, ContractorForge, EmpirePayPage (also `/finance/invoices?business=woodcraft`) |
| `/finance/dashboard` | 3 — WorkroomPage Overview, FinanceDashboard, ContractorForge |
| `/finance/expenses` | 3 — ExpenseTracker (workroom, woodcraft) + others |
| `/finance/payments?limit=10` | 3 — PaymentModule (workroom, crm) + FinanceDashboard |
| `/finance/customers/` | 4 — FinanceDashboard + InvoiceList customer lookup |
| `/tasks/` | 9 — multiple products' task lists (workroom + cross-product) |
| `/jobs/` | 5 — ContractorForge, EmpireAssist, QuoteReviewScreen, EmpirePayPage, JobBoard |
| `/quotes/` (and `/quotes/` variants) | 5 — multiple quote-creation paths |
| `/pricing/workroom/calculate` | 4 — PricingStudioScreen's main calculation calls |
| `/craftforge/designs/` | 10 — multiple CraftForge sub-views |
| `/transcriptforge/jobs/` | 9 — TranscriptForgePage sub-views |
| `/recovery/images/` | 7 — RecoveryForge sub-views |
| `/recovery/categories` | 2 |
| `/recovery/reanalysis-queue/start` | 2 |
| `/crm/customers/` (with slash) | 3 — CustomerList sub-paths |
| `/crm/customers` (no slash) | 6 (overlaps with above) |
| `/intake/admin/users/` | 3 — LuxeForgePage user mgmt |
| `/intake/admin/projects/` | 2 — LuxeForgePage project mgmt |
| `/quotes-v2/` (the canonical quote store) | 2 — WorkroomPage, ForgeCRMPage |
| `/tickets/` | 5 — SupportForge tickets + others |
| `/patterns/saved/` | 4 — Workroom patterns |
| `/apostapp/orders/` | 3 — ApostAppPage order ops |
| `/openclaw/tasks` | 3 — OpenClawTasksPage + RightPanel + others |
| `/max/telegram/image/` | 2 |
| `/max/pipeline/task/` | 2 |
| `/system/metrics` | 3 — PlatformPage + RightPanel |

### What is genuinely shared vs duplicated

**Genuinely shared (multiple screens → same router, expected reuse):**
- `/crm/customers` — one router (`customer_mgmt.py`), one canonical customers table, all six screens reading the same canonical data. Expected.
- `/finance/invoices` — one router, canonical invoices table. Expected (this is the unified finance table).
- `/tasks/` — one router, shared task list across products. Expected.
- `/quotes-v2/` — one canonical quote store. Expected.
- `/openclaw/tasks` — one router, shared queue. Expected.

**Duplicated surface (multiple screens → separate routers for the same domain):**
- **`/finance/*`** is reached via **two routers**: `backend/app/routers/finance.py` AND `backend/app/routers/jobs_unified.py`. Both define `/invoices`, `/finance/invoices`, `/finance/payments`, etc. (`jobs_unified.py:1573, 1617, 1662, 1821, 1919, 2005, etc.`) — the legacy Jobs router also has invoice endpoints.
- **`/crm/customers`**, **`/finance/dashboard`** are reached from many places, but with DIFFERENT business-filter semantics:
  - ForgeCRM: `/crm/customers?limit=500` (no business filter)
  - Workroom Customers: `/crm/customers?business=workroom` (default limit=100)
  - Workroom Overview: `/crm/customers?limit=5&sort_by=updated_at&sort_dir=desc&business=workroom`
  - ForgeCRM CustomerList: `/crm/customers?business=woodcraft`
  - These are the same router, different query parameters — not a duplication defect, but they paint different pictures of the same canonical data (the 4-customer-count screens in Phase 1a).
- **`/craftforge/designs`** is reached via multiple CraftForge sub-views — same router, same data, same expected reuse.
- **`/recovery/images`** is reached via 7 sub-views — same router.
- **`/transcriptforge/jobs`** is reached via 9 sub-views — same router.
- **`/archiveforge/`** endpoints — but ArchiveForgePage hits 405 (POST-only). Verified alive (right method).
- **`/pricing/workroom/calculate`** is called 4× from PricingStudioScreen — same router, same call, likely sub-action triggers.

### Per the dispatch's question — what is genuinely shared vs what is duplicated

**Genuinely shared (one canonical source, multiple readers):**
- `/crm/*` → `customer_mgmt.py`
- `/finance/*` → `finance.py` (with a duplication onto `jobs_unified.py` for invoice endpoints — legacy)
- `/tasks/` → one router
- `/quotes-v2/` → one router
- `/openclaw/tasks` → one router
- `/craftforge/*`, `/recovery/*`, `/transcriptforge/*` → one router each

**Duplicate routers writing the same domain:**
- `finance.py` and `jobs_unified.py` both expose `/invoices` and `/finance/invoices`
- This is the consolidation debt: invoices endpoints exist in TWO routers

**Duplicated front-end components:**
- `<PaymentModule product="...">` — 14 callers, ONE shared component (`empire-command-center/app/components/business/payments/PaymentModule.tsx`)
- `<ProductDocs product="...">` — 9 callers, ONE shared component (`empire-command-center/app/components/business/docs/ProductDocs.tsx`)
- `<CustomerList business="..." />` — 2 callers, ONE shared component (`empire-command-center/app/components/business/crm/CustomerList.tsx`); the 5+ other products have local Customers implementations

---

## Dead surface — consolidated

All DEAD endpoints found across Phase 3 batches:

| Endpoint | Status | Used by |
|---|---|---|
| `/api/v1/vision/history?limit=10` | 404 | AI Vision + Daily Summary |
| `/api/v1/construction/projects/{id}/dashboard` | 404 | ConstructionForge |
| `/api/v1/businessops` | 404 | Business Profile |
| `/api/v1/businessops/profile` | 404 | Business Profile |
| `/api/v1/vendorops` | 404 | VendorOps (entire sidebar unreachable) |
| `/api/v1/leadforge` | 404 | LeadForge (entire sidebar unreachable) |
| `/api/v1/leadforge/prospects?limit=N` | 404 | LeadForge |
| `/api/v1/leadforge/prospect-pipeline?limit=N` | 404 | LeadForge |
| `/api/v1/leadforge/campaigns` | 404 | LeadForge |
| `/listings` (no /api/v1/relist prefix) | 404 | MarketForge — URL bug |
| `/preorders/` (no /api/v1/relist prefix) | 404 | MarketForge — URL bug |
| `/api/v1/kb/articles?per_page=N` | 500 | SupportForge knowledge base |
| `/api/v1/kb/categories` | 500 | SupportForge knowledge base |
| `/api/v1/shipments` | 404 | ShipForge |
| `/api/v1/shipments/dashboard` | 404 | ShipForge |
| `/api/v1/amp/dashboard` | 404 | AMP |
| `/api/v1/amp/posts` | 404 | AMP |
| `/api/v1/transcripts` | 404 | TranscriptForge |
| `/api/v1/transcripts/dashboard` | 404 | TranscriptForge |
| `/api/v1/max/continuity` | 404 | MAX Continuity |
| `/api/v1/max/continuity/handoff` | 404 | MAX Continuity |
| `/api/v1/costs/dashboard` | 404 | Tokens & Costs |
| `/api/v1/tokens/usage` | 404 | Tokens & Costs |
| `/api/v1/max/cost-tracker` | 404 | Tokens & Costs |
| `/api/v1/docker` | 404 | Hardware (dev-only) |
| `/api/v1/empireassist/tasks` | 404 | EmpireAssist |

**Total DEAD endpoints: 27** across the front-end surface.

### Sidebar items with NO live endpoints (entire surface dead)

- **Business Profile** (BUSINESS, screen) — `/businessops`, `/businessops/profile` both 404
- **VendorOps** (BUSINESS, product) — `/vendorops` 404
- **LeadForge** (BUSINESS, product) — `/leadforge/*` all 404
- **MAX Continuity** (SYSTEM, product) — `/max/continuity/*` all 404
- **Tokens & Costs** (SYSTEM, product) — `/costs/*`, `/tokens/*`, `/max/cost-tracker` all 404
- **ShipForge** (GROWTH, product) — `/shipments/*` all 404
- **AMP** (GROWTH, product) — `/amp/*` all 404
- **TranscriptForge** (GROWTH, product) — `/transcripts/*` all 404
- **Hardware** (SYSTEM, status='dev') — `/docker` 404
- **EmpireAssist** (MORE, status='dev') — `/empireassist/tasks` 404 (other endpoints OK)

10 of 37 sidebar items have NO live data fetches at the surface they advertise. (VetForge + PetForge are placeholder pages with no endpoints — counted separately.)

### Sidebar items with degraded surfaces

- **SupportForge** — KB tab broken (500s); tickets tab OK
- **MarketForge** — listings endpoint URL broken; marketplace count hardcoded

### Auth-protected but not dead (401, not 404)

- **LuxeForge** — 4 `/intake/admin/*` and `/intake/*` endpoints return 401 unauthenticated. Probably work for authenticated sessions.

### Hardcoded data

- `MARKETPLACE_LIST = ['eBay', 'Poshmark', 'Mercari', 'Amazon', 'Etsy']` at MarketForgePage.tsx:33-35 — length 5 and "All connected" label are HARDCODED. No actual connection check.

### Reading-only observation: nothing fixed

Per the standing rule, no code was modified in Phase 3. Dead endpoints, hardcoded lists, duplicate routers, and the 27 DEAD surfaces are reported and left in place for the founder to rule on next steps.

Not pushed.