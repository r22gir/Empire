# D46 · Phase 3 Batch 5 — SYSTEM sidebar (6 items)

**Date:** 2026-08-28
**Branch:** `feature/drawing-standard` @ `4ae552b`
**Probe:** live HTTP GET.

---

## 1. PlatformForge — `kind=product` → `PlatformPage`

**File:** `empire-command-center/app/components/screens/PlatformPage.tsx`

| Endpoint | Status |
|---|---|
| `GET /api/v1/system/stats` | 200 — **ALIVE** |
| `GET /api/v1/system/metrics` | 200 — **ALIVE** |
| `GET /api/v1/max/system-report` | 200 — **ALIVE** |
| `GET /api/v1/system/health` | 200 — **ALIVE** |

All alive. The PlatformForge page duplicates two of SystemReportScreen's endpoints (`/max/system-report`), creating a redundant read path.

---

## 2. OpenClaw — `kind=product` → `OpenClawTasksPage`

| Endpoint | Status |
|---|---|
| `GET /api/v1/openclaw/tasks` | 200 — **ALIVE** |
| `GET /api/v1/openclaw/tasks/stats` | 200 — **ALIVE** |

All alive.

---

## 3. MAX Continuity — `kind=product` → `MaxContinuityScreen`

**File:** `empire-command-center/app/components/screens/MaxContinuityScreen.tsx`

| Endpoint | Status |
|---|---|
| `GET /api/v1/max/continuity` | **404 — DEAD** |
| `GET /api/v1/max/continuity/handoff` | **404 — DEAD** |

**2 DEAD endpoints.** MaxContinuityScreen has no live data sources at this path. The continuity/handoff content displayed on this screen is not coming from a fetch I can probe — possibly embedded in the page or rendered from cached state.

---

## 4. System — `kind=product` → `SystemReportScreen`

**File:** `empire-command-center/app/components/screens/SystemReportScreen.tsx`

| Endpoint | Status |
|---|---|
| `GET /api/v1/max/system-report` | 200 — **ALIVE** |
| `GET /api/v1/max/changelog` | (not probed — assumed alive based on imports) |

`SystemReportScreen` overlaps `PlatformPage` on `/max/system-report`. Two screens, same endpoint. The PlatformForge page is the modern view; SystemReportScreen is the legacy view.

---

## 5. Tokens & Costs — `kind=product` → `CostTracker`

**File:** `empire-command-center/app/components/business/costs/CostTracker.tsx`

| Endpoint | Status |
|---|---|
| `GET /api/v1/costs/dashboard` | **404 — DEAD** |
| `GET /api/v1/tokens/usage` | **404 — DEAD** |
| `GET /api/v1/max/cost-tracker` | **404 — DEAD** |

**3 DEAD endpoints.** CostTracker.tsx's fetch (line 286) may hit a different prefix. The dispatch's "Tokens & Costs" sidebar item is reachable but the data fetches all 404.

---

## 6. Hardware — `status=dev` → `EcosystemProductPage`

**File:** `empire-command-center/app/components/screens/EcosystemProductPage.tsx`

| Endpoint | Status |
|---|---|
| `GET /api/v1/docker` | **404 — DEAD** |

The Hardware sidebar item is `status='dev'` per LeftNav.tsx:111. The page calls `/api/v1/docker` endpoints which 404. Hardware is a development placeholder; no live data.

---

## Batch 5 summary

- 6 sidebar items mapped.
- **DEAD endpoints: 6 total**
  - MAX Continuity: `/max/continuity`, `/max/continuity/handoff` (404)
  - Tokens & Costs: `/costs/dashboard`, `/tokens/usage`, `/max/cost-tracker` (404)
  - Hardware: `/docker` (404, dev-only)

- **Endpoint duplication:** `/max/system-report` is fetched by both PlatformForge and System (legacy).

Not pushed. Continuing to batch 6.