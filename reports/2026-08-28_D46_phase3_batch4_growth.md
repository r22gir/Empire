# D46 · Phase 3 Batch 4 — GROWTH / CHANNELS sidebar (7 items)

**Date:** 2026-08-28
**Branch:** `feature/drawing-standard` @ `e4f220e`
**Probe:** live HTTP GET.

---

## 1. SocialForge — `kind=product` → `SocialForgePage`

**File:** `empire-command-center/app/components/screens/SocialForgePage.tsx`
**API base:** `${API}/socialforge`

| Endpoint | Status |
|---|---|
| `GET /api/v1/socialforge/dashboard` | 200 — **ALIVE** |
| `GET /api/v1/socialforge/posts` | 200 — **ALIVE** |
| `GET /api/v1/socialforge/accounts` | 200 — **ALIVE** |

All alive.

---

## 2. MarketForge — `kind=product` → `MarketForgePage`

**File:** `empire-command-center/app/components/screens/MarketForgePage.tsx`

The page has a **URL bug**:
- Line 56: `const _API_BASE = API.replace('/api/v1', '');` — strips the `/api/v1` prefix
- Line 57: `const LISTINGS_URL = ${_API_BASE}/listings;`
- Line 58: `const ORDERS_URL = ${_API_BASE}/preorders/;`

So MarketForgePage fetches `http://localhost:8000/listings` (no `/api/v1/relist/` prefix). The backend router is `relistapp.py` with `prefix="/relist"` — so the correct URL is `http://localhost:8000/api/v1/relist/listings`.

| Endpoint (as the page calls it) | Status |
|---|---|
| `GET http://localhost:8000/listings` | **404 — DEAD (URL bug)** |
| `GET http://localhost:8000/preorders/` | **404 — DEAD (URL bug)** |
| **Correct URL:** `GET /api/v1/relist/listings` | 200 — would work |

The dispatch observed "Failed to fetch listings: 401" — the 401 might be from a previous deploy where the URL was different, or with auth headers. With the current code, the page fetches a 404 silently (`.catch(() => {})`).

**"MARKETPLACES 5 — All connected":** This is **HARDCODED** in `MarketForgePage.tsx:33-35`:
```js
const MARKETPLACE_LIST = ['eBay', 'Poshmark', 'Mercari', 'Amazon', 'Etsy'];
// line 291: <KPI label="Marketplaces" value={String(MARKETPLACE_LIST.length)} sub="All connected" />
```
The "5" is `MARKETPLACE_LIST.length`, the "All connected" sub-label is the literal string. No actual connection state is queried.

---

## 3. SupportForge — `kind=product` → `SupportForgePage`

**File:** `empire-command-center/app/components/screens/SupportForgePage.tsx`

| Endpoint | Status |
|---|---|
| `GET /api/v1/tickets/?per_page=100` | 200 — **ALIVE** |
| `GET /api/v1/kb/articles?per_page=100` | **500 — server error** |
| `GET /api/v1/kb/categories` | **500 — server error** |

**2 DEAD endpoints (500).** `/kb/articles` and `/kb/categories` both return 500 (internal server error, not 404). The KB module is wired but failing server-side. SupportForge's knowledge-base tab would be empty/broken.

---

## 4. ShipForge — `kind=product` → `ShipForgePage`

| Endpoint | Status |
|---|---|
| `GET /api/v1/shipments` | **404 — DEAD** |
| `GET /api/v1/shipments/dashboard` | **404 — DEAD** |

**2 DEAD endpoints.** ShipForge endpoints don't exist at this path. (Need to verify whether they exist under a different prefix.)

---

## 5. AMP — `kind=product` → `AmpLanding`

| Endpoint | Status |
|---|---|
| `GET /api/v1/amp/dashboard` | **404 — DEAD** |
| `GET /api/v1/amp/posts` | **404 — DEAD** |

**2 DEAD endpoints.** AMP sidebar item may be unreachable.

---

## 6. ArchiveForge — `kind=product` → `ArchiveForgePage`

| Endpoint | Status |
|---|---|
| `POST /api/v1/archiveforge/projects` | 405 (GET — POST-only) — **ALIVE (right method)** |
| `POST /api/v1/archiveforge/search` | 405 (GET — POST-only) — **ALIVE (right method)** |

Both ArchiveForge endpoints return 405 to GET. They are POST-only, so alive.

---

## 7. TranscriptForge — `kind=product` → `TranscriptForgePage`

| Endpoint | Status |
|---|---|
| `GET /api/v1/transcripts` | **404 — DEAD** |
| `GET /api/v1/transcripts/dashboard` | **404 — DEAD** |

**2 DEAD endpoints.** TranscriptForge endpoints don't exist at this path.

---

## Batch 4 summary

- 7 sidebar items mapped.
- **DEAD endpoints: 10 total**
  - MarketForge: `/listings`, `/preorders/` (404 — URL bug; `/api/v1/relist/listings` works)
  - SupportForge: `/kb/articles` (500), `/kb/categories` (500)
  - ShipForge: `/shipments`, `/shipments/dashboard` (404)
  - AMP: `/amp/dashboard`, `/amp/posts` (404)
  - TranscriptForge: `/transcripts`, `/transcripts/dashboard` (404)

- **Sidebars with no live endpoints:** ShipForge, AMP, TranscriptForge.

Not pushed. Continuing to batch 5.