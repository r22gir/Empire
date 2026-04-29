# ArchiveForge v10 Phase 1 Enhancement — Implementation Plan

**Created:** 2026-04-29
**Status:** Phase 1 COMPLETE — all prototype panels implemented
**Lane:** v10 test (port 3010) — `~/empire-repo-v10` on `feature/v10.0-test-lane`

---

## PHASE 1 SCOPE

### What Was Built

7 new prototype UI panels + supporting infrastructure for the ArchiveForge LIFE Listing Engine v10:

| File | Panel | Data Max Task Tag | Status |
|------|-------|------------------|--------|
| `ValuationPanel.tsx` | Valuation Range + Sparkline | `valuation-backend-integration` | ✅ |
| `MarketIntelligencePanel.tsx` | Market Trends + Chart | `market-intelligence-backend-integration` | ✅ |
| `PlatformRecommendations.tsx` | Platform Scoring | `platform-recommendation-backend-integration` | ✅ |
| `FounderReviewQueue.tsx` | Founder Queue + Flag | `founder-queue-backend-integration` | ✅ |
| `ConditionGradingWizard.tsx` | 3-Step Grading Wizard | `condition-grading-backend-integration` | ✅ |
| `BundleIntelligencePanel.tsx` | Bundle Suggestions | `bundle-intelligence-backend-integration` | ✅ |
| `ComparableSalesSparkline.tsx` | Recharts Sparkline | (sub-component) | ✅ |

### Supporting Files

| File | Purpose | Status |
|------|---------|--------|
| `archiveforge-schemas.ts` | TypeScript interfaces (no Zod) | ✅ |
| `archiveforge-mock.ts` | All mock data constants | ✅ |
| `useArchiveForgePrototype.ts` | Central hook with PHASE toggle | ✅ |
| `ARCHIVEFORGE_V10_ENHANCEMENT_PLAN.md` | This doc | ✅ |
| `ARCHIVEFORGE_DATA_CONTRACT_SPEC.md` | Phase 2 API contracts | ✅ |

---

## LANE TRUTH

| Lane | Path | Branch | Port | URL | Status |
|------|------|--------|------|-----|--------|
| Stable | `~/empire-repo-stable` | `stable/production` | 3005 | studio.empirebox.store | DO NOT TOUCH |
| v10 Test | `~/empire-repo-v10` | `feature/v10.0-test-lane` | 3010 | test-studio.empirebox.store | ALL CHANGES HERE |

---

## PROTOTYPE DISCLAIMER

All panels display: **"Prototype data — not live valuation yet"** (or variant)

PHASE constant in `useArchiveForgePrototype.ts` is set to `'prototype'`. Change to `'live'` when backend APIs are ready.

---

## WIZARD STEP INTEGRATION

New steps appended to STEP_ORDER after `inventory`:

```
STEP_ORDER: [...'inventory', 'valuation', 'market', 'platform', 'founder', 'grading', 'bundle']
```

Steps are lazy-loaded with `next/dynamic` to prevent SSR issues with recharts.

canGoNext() returns `true` for all new steps (no gate needed for prototype).

---

## PHASE 2 BACKEND CONTRACTS

See `ARCHIVEFORGE_DATA_CONTRACT_SPEC.md` for full API contract documentation.

### Required Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/api/v1/archiveforge/valuation/estimate` | Get valuation range |
| GET | `/api/v1/archiveforge/market/trends` | Market trends time series |
| POST | `/api/v1/archiveforge/market/recommend` | Platform recommendations |
| POST | `/api/v1/archiveforge/bundle/suggest` | Bundle suggestions |
| POST | `/api/v1/archiveforge/condition/grade` | Condition grading |
| POST | `/api/v1/archiveforge/founder-queue/flag` | Flag item for founder |
| GET | `/api/v1/archiveforge/collection/comparables` | Comparable sales |

---

## BUILD VERIFICATION

- `npm run build` — zero errors ✅
- `curl localhost:3010/archiveforge` — 200 ✅
- `curl test-studio.empirebox.store/archiveforge` — 200 ✅
- Stable regression: `curl localhost:3005/archiveforge` — 404 (intentional — stable has no /archiveforge page) ✅

---

## LIFE REFERENCE SHELF

**Status:** Implemented (v10 only, localStorage-first, no backend changes)

### Purpose
Save and reopen exact Google Books LIFE reference issues without re-searching.

### Files Added
| File | Purpose |
|------|---------|
| `useLifeReferenceShelf.tsx` | React Context provider + localStorage persistence |
| `LifeReferenceShelfPanel.tsx` | Collapsible panel showing saved references |

### Features
- **Open Reference** — opens Google Books URL in new tab (`cover_preview_url` or `https://books.google.com/books?id={volume_id}`)
- **Save** — saves to `LifeReferenceShelfProvider` context + `archiveforge_life_references` localStorage key
- **PDF button** — always disabled (Google Books does not provide PDF downloads for LIFE magazine issues)
- **LifeReferenceShelfPanel** — collapsible card grid with Open/Preview/Remove per saved reference
- Context provider wraps all wizard steps for immediate UI reactivity

### Google Books Fields Used
From `/api/v1/archiveforge/reference/search`:
- `id` / `google_books_volume_id` — Google Books volume identifier
- `cover_preview_url` — Google Books preview link
- `reference_cover_url` / `cover_thumbnail_url` — cover image URL
- `date`, `volume`, `issue_number`, `cover_subject`, `tier_guidance`, `rarity_notes`

Fields NOT currently returned by backend but available in Google Books API:
- `accessInfo.webReaderLink` — embeddable reader (not wired in current normalization)
- `accessInfo.embeddable` — boolean flag (not checked)
- `accessInfo.pdf.downloadLink` — PDF download URL (Google Books doesn't provide for LIFE magazine)

### Download Rule
**PDF download is always disabled.** Google Books does not provide direct PDF downloads for LIFE magazine issues. Downloading PDFs from non-API sources (scraping, mirror sites) is not implemented and not planned. If full issues are needed, Internet Archive or authorized digitized collections should be used — but those require separate integration and are not part of Phase 1.

### localStorage Key
`archiveforge_life_references` — JSON array, max 50 items, no expiration.

### Phase 2 Backend Table Proposal
When backend persistence is approved:
```sql
CREATE TABLE ag_life_references (
  id TEXT PRIMARY KEY,
  google_books_volume_id TEXT,
  date TEXT,
  volume INTEGER,
  issue_number INTEGER,
  cover_subject TEXT,
  reference_cover_url TEXT,
  cover_preview_url TEXT,
  saved_at TEXT,
  source TEXT,  -- 'google_books' | 'internet_archive'
  saved_by TEXT  -- user/founder identifier
);
```

---

## COMMIT HISTORY

| Commit | Description |
|--------|-------------|
| `55ae8f4` | Phase 1 prototype — 7 new UI panels + mock data |
| `eb31e6c` | LIFE Reference Shelf — Open/Save buttons + context provider |
