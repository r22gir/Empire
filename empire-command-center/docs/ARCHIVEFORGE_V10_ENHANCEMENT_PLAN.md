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
- Stable regression: `curl localhost:3005/archiveforge` — 200 ✅
