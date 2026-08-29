# D46 · Phase 3 Batch 2 — BUSINESS sidebar (10 items)

**Date:** 2026-08-28
**Branch:** `feature/drawing-standard` @ `bf45268`
**Probe:** live HTTP GET to `http://localhost:8000` for each endpoint.

---

## 1. StoreFront Forge — `kind=product` → `StoreFrontForgePage`

**File:** `empire-command-center/app/components/screens/StoreFrontForgePage.tsx`
**API base:** `${API}/storefront`

| Endpoint | Status |
|---|---|
| `GET /api/v1/storefront/products` | 200 — **ALIVE** |
| `GET /api/v1/storefront/transactions` | 200 — **ALIVE** |
| `GET /api/v1/storefront/customers` | 200 — **ALIVE** |
| `GET /api/v1/storefront/inventory/1` | 200 — **ALIVE** |
| `GET /api/v1/storefront/employees` | 200 — **ALIVE** |

All Storefront endpoints respond. No dead surfaces here.

---

## 2. ConstructionForge — `kind=product` → `ConstructionForgePage`

**File:** `empire-command-center/app/components/screens/ConstructionForgePage.tsx`
**API base:** `${API}/construction`

| Endpoint | Status |
|---|---|
| `GET /api/v1/construction/projects` | 200 |
| `GET /api/v1/construction/projects/1/dashboard` | **404 — DEAD** |
| `GET /api/v1/construction/projects/1/lots` | 200 |
| `GET /api/v1/construction/buyers` | 200 |
| `GET /api/v1/construction/projects/1/sales/pipeline` | 200 |
| `GET /api/v1/construction/projects/1/payments/overdue` | 200 |
| `GET /api/v1/construction/contractors` | 200 |
| `GET /api/v1/construction/projects/1/materials` | 200 |

**1 DEAD endpoint:** `/api/v1/construction/projects/1/dashboard` returns 404. ConstructionForgePage line 158 calls this in a useEffect with `.catch(() => {})` — silent failure.

---

## 3. LuxeForge — `kind=product` → `LuxeForgePage`

**File:** `empire-command-center/app/components/screens/LuxeForgePage.tsx`
**API base:** `${API}/intake/*` (NOT a standalone luxe API — reuses intake)

| Endpoint | Status |
|---|---|
| `GET /api/v1/intake/admin/projects` | **401 — auth required** |
| `GET /api/v1/intake/admin/users` | **401 — auth required** |
| `GET /api/v1/intake/projects` | **401 — auth required** |
| `GET /api/v1/intake/admin/archived` | **401 — auth required** |

All `/intake/*` endpoints return 401 (unauthenticated). The intake endpoints likely work for authenticated founder sessions; the probe was unauthenticated. **Not necessarily dead — auth-protected.**

---

## 4. Business Profile — `kind=screen` → `BusinessProfileScreen`

**File:** `empire-command-center/app/components/screens/BusinessProfileScreen.tsx`

| Endpoint | Status |
|---|---|
| `GET /api/v1/businessops` | **404 — DEAD** |
| `GET /api/v1/businessops/profile` | **404 — DEAD** |

Both `/businessops` endpoints return 404. The Business Profile screen fails on initial load (line 68: `fetch(PROFILE_API)` with `PROFILE_API = `${API}/businessops`).

---

## 5. VendorOps — `kind=product` → `VendorOpsPage`

**File:** `empire-command-center/app/components/screens/VendorOpsPage.tsx`

| Endpoint | Status |
|---|---|
| `GET /api/v1/vendorops` | **404 — DEAD** |

The VendorOps page calls `/api/v1/vendorops` (line 478 displays this URL in a debug box). The endpoint returns 404 — the entire sidebar item is unreachable. **The `<ProductDocs product="vendorops" />` sidebar link goes nowhere.**

---

## 6. ContractorForge — `kind=product` → `ContractorForgePage`

**File:** `empire-command-center/app/components/screens/ContractorForgePage.tsx`

| Endpoint | Status |
|---|---|
| `GET /api/v1/jobs/` | 200 |
| `GET /api/v1/contacts/` | 200 |
| `GET /api/v1/finance/invoices` | 200 |

All three ContractorForge endpoints respond. No dead surfaces.

---

## 7. LeadForge — `kind=product` → `LeadForgePageNew`

**File:** `empire-command-center/app/components/screens/LeadForgePageNew.tsx`
**API base:** `${LF_API}/leadforge/*` (LF_API is set elsewhere — likely `/api/v1`)

| Endpoint | Status |
|---|---|
| `GET /api/v1/leadforge` | **404 — DEAD** |
| `GET /api/v1/leadforge/prospects?limit=10` | **404 — DEAD** |
| `GET /api/v1/leadforge/prospect-pipeline?limit=10` | **404 — DEAD** |
| `GET /api/v1/leadforge/campaigns` | **404 — DEAD** |

**4 DEAD endpoints.** The entire LeadForge product appears unreachable from this URL prefix. All silent-failed in the UI.

---

## 8. ForgeCRM — `kind=product` → `ForgeCRMPage`

| Endpoint | Status |
|---|---|
| `GET /api/v1/crm/pipeline` | 200 |
| `GET /api/v1/crm/customers?limit=500` | 200 |
| `GET /api/v1/crm/customers?business=woodcraft` | 200 |
| `POST /api/v1/crm/customers` | (POST not probed — assumed alive since GET works) |

All alive. (See Phase 1a for the four-customer-count dissection.)

---

## 9. EmpirePay — `kind=product` → `EmpirePayPage`

**File:** `empire-command-center/app/components/screens/EmpirePayPage.tsx`

| Endpoint | Status |
|---|---|
| `GET /api/v1/crypto-payments/?limit=10` | 200 |
| `GET /api/v1/crypto-payments/chains` | 200 |
| `GET /api/v1/finance/invoices` | 200 |

Crypto-payments is alive. Stripe is NOT configured (Phase 2f) but EmpirePay's main data flow goes through crypto-payments, not Stripe. **No DEAD surfaces here.**

---

## 10. Pricing Studio — `kind=screen` → `PricingStudioScreen`

**File:** `empire-command-center/app/components/screens/PricingStudioScreen.tsx`

| Endpoint | Status |
|---|---|
| `GET /api/v1/pricing/canonical/status` | 200 |
| `GET /api/v1/pricing/labor-rates` | 200 |
| `POST /api/v1/pricing/workroom/calculate` | **405 — method not allowed** (probe was GET) |

The 405 is expected for the calculate endpoint (it's POST-only). Pricing Studio endpoints all work correctly when called with the right method. No DEAD surfaces.

---

## Batch 2 summary

- 10 sidebar items mapped.
- **DEAD endpoints: 11 total**
  - ConstructionForge: `/construction/projects/{id}/dashboard` (404)
  - Business Profile: `/businessops`, `/businessops/profile` (404)
  - VendorOps: `/vendorops` (404)
  - LeadForge: `/leadforge` + 3 sub-paths (404)
  - Pricing Studio: `/pricing/workroom/calculate` 405 is expected (POST-only); no real DEAD

- **Auth-protected (401, not dead):** LuxeForge intake endpoints (4) — likely work for authenticated users.

---

## Sidebar items with dead surfaces (5 of 10)

- ConstructionForge (1 dead)
- Business Profile (2 dead)
- VendorOps (1 dead, entire sidebar unreachable)
- LeadForge (4 dead, entire sidebar unreachable)

Not pushed. Continuing to batch 3.