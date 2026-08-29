# D46 · Phase 3 Batch 3 — TOOLS sidebar (3 items)

**Date:** 2026-08-28
**Branch:** `feature/drawing-standard` @ `fb140a4`
**Probe:** live HTTP GET.

---

## 1. Drawing Studio — `kind=product` → `DrawingStudioPage`

**File:** `empire-command-center/app/components/screens/DrawingStudioPage.tsx`

| Endpoint | Status |
|---|---|
| `POST /api/v1/drawings/analyze-furniture` | 405 (GET — POST-only) — **ALIVE (right method)** |
| `POST /api/v1/drawings/analyze-sketch` | 405 (GET — POST-only) — **ALIVE** |
| `POST /api/v1/drawings/bench` | 405 (GET — POST-only) — **ALIVE** |
| `POST /api/v1/drawings/general` | 405 (GET — POST-only) — **ALIVE** |
| `POST /api/v1/drawings/generate` | 405 (GET — POST-only) — **ALIVE** |
| `POST /api/v1/max/chat` (called from DrawingStudio to drive MAX) | 200 — **ALIVE** |

All `/drawings/*` endpoints return 405 to GET (correct — they're POST-only). No DEAD endpoints in Drawing Studio.

---

## 2. AI Vision — `kind=product` → `VisionAnalysisPage`

**File:** `empire-command-center/app/components/screens/VisionAnalysisPage.tsx`

| Endpoint | Status |
|---|---|
| `GET /api/v1/vision/history?limit=10` | **404 — DEAD** |
| `GET /api/v1/crm/customers` | 200 — **ALIVE** |

**1 DEAD endpoint:** `/api/v1/vision/history` returns 404. The Daily Summary widget at `RightPanel.tsx:393` calls the same endpoint. Two callers of a 404. (Both `.catch(() => ...)` — silent failure.)

---

## 3. RecoveryForge — `kind=product` → `RecoveryForgeScreen`

**File:** `empire-command-center/app/components/screens/RecoveryForgeScreen.tsx`

| Endpoint | Status |
|---|---|
| `GET /api/v1/recovery/images?limit=10` | 200 — **ALIVE** |
| `GET /api/v1/recovery/status` | 200 — **ALIVE** |
| `GET /api/v1/recovery/categories` | 200 — **ALIVE** |
| `GET /api/v1/recovery/reanalysis-queue/status` | 200 — **ALIVE** |

All RecoveryForge endpoints respond. No DEAD surfaces.

---

## Batch 3 summary

- 3 sidebar items mapped.
- **1 DEAD endpoint: `/api/v1/vision/history?limit=10`** — used by both AI Vision and Daily Summary widgets.

Not pushed. Continuing to batch 4.