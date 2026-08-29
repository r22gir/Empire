# D46 · Phase 3 Batch 6 — MORE sidebar (7 items)

**Date:** 2026-08-28
**Branch:** `feature/drawing-standard` @ `82bd07f`
**Probe:** live HTTP GET.

---

## 1. RelistApp — `kind=product` → `RelistAppPage`

**File:** `empire-command-center/app/components/screens/RelistAppPage.tsx`
**API base:** `${API}/relist`

| Endpoint | Status |
|---|---|
| `GET /api/v1/relist/analytics/dashboard` | 200 — **ALIVE** |
| `GET /api/v1/relist/sources` | 200 — **ALIVE** |
| `GET /api/v1/relist/deals` | 200 — **ALIVE** |
| `GET /api/v1/relist/listings` | 200 — **ALIVE** |
| `GET /api/v1/relist/orders` | 200 — **ALIVE** |
| `GET /api/v1/relist/services` | 200 — **ALIVE** |
| `POST /api/v1/relist/scout/run` | 405 (GET — POST-only) — **ALIVE** |

All alive.

**Note:** MarketForgePage calls `${_API_BASE}/listings` (without `/api/v1/relist/` prefix — see batch 4) and gets 404. The correct path is `/api/v1/relist/listings` which RelistApp uses correctly.

---

## 2. LLCFactory — `kind=product` → `LLCFactoryPage`

| Endpoint | Status |
|---|---|
| `GET /api/v1/llcfactory/dashboard` | 200 — **ALIVE** |
| `GET /api/v1/llcfactory/services` | 200 — **ALIVE** |
| `GET /api/v1/llcfactory/packages` | 200 — **ALIVE** |
| `GET /api/v1/llcfactory/orders` | 200 — **ALIVE** |
| `GET /api/v1/llcfactory/customers` | 200 — **ALIVE** |
| `GET /api/v1/llcfactory/documents` | (not probed) |
| `POST /api/v1/llcfactory/name-check` | (not probed) |

All probed endpoints alive.

---

## 3. ApostApp — `kind=product` → `ApostAppPage`

| Endpoint | Status |
|---|---|
| `GET /api/v1/apostapp/orders` | 200 — **ALIVE** |
| `POST /api/v1/apostapp/forms/generate` | 405 (GET — POST-only) — **ALIVE** |
| `GET /api/v1/apostapp/public/packages` | 200 — **ALIVE (public)** |
| `POST /api/v1/apostapp/public/verify` | 405 (GET — POST-only) — **ALIVE (public)** |

All probed endpoints alive.

---

## 4. EmpireAssist — `status=dev` → `EmpireAssistPage`

**File:** `empire-command-center/app/components/screens/EmpireAssistPage.tsx`

| Endpoint | Status |
|---|---|
| `GET /api/v1/costs/transactions?limit=20` | 200 — **ALIVE** |
| `GET /api/v1/empireassist/tasks` | **404 — DEAD** |

**1 DEAD endpoint.** EmpireAssist's main fetches go to `/costs/*` which work, but `/empireassist/tasks` returns 404. EmpireAssist is `status='dev'` per LeftNav.tsx:122.

---

## 5. VetForge — `status=planned` → `VetForgePage`

**File:** `empire-command-center/app/components/screens/VetForgePage.tsx`

**No endpoints.** VetForgePage is a 20-line "Coming soon" placeholder. No API calls, no data fetches. Status='planned' in LeftNav.

---

## 6. PetForge — `status=planned` → `PetForgePage`

**File:** `empire-command-center/app/components/screens/PetForgePage.tsx`

**No endpoints.** Same as VetForge — placeholder page. Status='planned'.

---

## 7. Developer Panel — `status=dev` → `DevPanel`

| Endpoint | Status |
|---|---|
| `GET /api/v1/dev/status` | 200 — **ALIVE** |
| `GET /api/v1/dev/git` | 200 — **ALIVE** |
| `GET /api/v1/dev/audit?limit=20` | 200 — **ALIVE** |
| `GET /api/v1/dev/health` | 200 — **ALIVE** |

All alive. Status='dev' per LeftNav.tsx:125.

---

## Batch 6 summary

- 7 sidebar items mapped.
- **1 DEAD endpoint:** `/api/v1/empireassist/tasks` (404). EmpireAssist's main /costs/* flow works.
- **2 placeholder pages:** VetForge and PetForge (status='planned', no endpoints).

Not pushed. Continuing to phase 3b (endpoint overlap).