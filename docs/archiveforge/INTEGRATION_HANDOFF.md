# ArchiveForge — Integration Handoff

**Branch:** `feature/archiveforge-life`
**V1 Engine:** LIFE Listing Engine (LIFE weekly magazines, 1936–1972)
**Status:** Local verification complete — build passes, TypeScript clean

---

## Files Created

### Backend
| File | Purpose |
|---|---|
| `backend/app/routers/archiveforge.py` | Full ArchiveForge API — 15 endpoints, LIFE reference fixture, archive CRUD, listing draft generator |
| `backend/app/main.py` (+1 line) | Registered `archiveforge` router under `/api/v1/archiveforge` |

### Frontend
| File | Purpose |
|---|---|
| `empire-command-center/app/components/screens/ArchiveForgePage.tsx` | 7-section wizard: Intake → Reference → Photos → Archive → Condition → Listing → Inventory |
| `empire-command-center/app/lib/types.ts` (+1 line) | Added `'archive'` to `EcosystemProduct` type |
| `empire-command-center/app/components/layout/LeftNav.tsx` (+2 lines) | Added ArchiveForge nav item (Ecosystem section) |
| `empire-command-center/app/page.tsx` (+2 lines) | Added import + `case 'archive':` route |

---

## Shared Files Modified (Minimal Isolated Touches)

### `backend/app/main.py`
```python
# Added after relistapp registration:
load_router("app.routers.archiveforge", "/api/v1", ["archiveforge"])
```
**Impact:** Low — standard router registration, same pattern as all other products.

### `empire-command-center/app/lib/types.ts`
```typescript
# Added 'archive' to EcosystemProduct union type
export type EcosystemProduct = 'owner' | 'workroom' | ... | 'archive';
```
**Impact:** Minimal — type-level only, no runtime behavior change for existing products.

### `empire-command-center/app/components/layout/LeftNav.tsx`
```tsx
// Added to icon imports:
Archive,
// Added to Ecosystem section NAV items:
{ id: 'archive', name: 'ArchiveForge', icon: <Archive size={16} />, status: 'active', color: '#06b6d4' },
```
**Impact:** Low — adds one nav item, no existing items modified.

### `empire-command-center/app/page.tsx`
```tsx
import ArchiveForgePage from './components/screens/ArchiveForgePage';
// Added to product switch:
case 'archive': return <ArchiveForgePage />;
```
**Impact:** Low — standard product route pattern, matches RelistApp and all other products.

---

## Backend API Summary

All endpoints live under `/api/v1/archiveforge`:

| Method | Route | Purpose |
|---|---|---|
| GET | `/reference` | Search LIFE reference DB by date/volume/issue/keyword |
| GET | `/reference/{id}` | Get specific reference issue |
| GET | `/reference/all` | List all 15 reference issues |
| GET | `/archives` | List all archive items (filterable by status/tier/box) |
| POST | `/archives` | Create new archive intake record |
| GET | `/archives/{id}` | Get specific archive item |
| PATCH | `/archives/{id}` | Update archive fields (partial update) |
| PATCH | `/archives/{id}/status` | Transition status with validation |
| DELETE | `/archives/{id}` | Delete archive item |
| POST | `/archives/{id}/listing-draft` | Generate MarketForge-ready listing draft |
| GET | `/inventory` | Spreadsheet-friendly inventory summary |
| GET | `/inventory/export` | Export inventory as JSON (for CSV conversion) |
| GET | `/stats` | Dashboard counts by status and tier |
| POST | `/boxes` | Register a new box code |
| GET | `/boxes` | List all registered box codes |
| GET | `/drafts` | List all saved listing drafts |

### Database Tables (prefix `ag_`)
- `ag_archives` — physical archive items
- `ag_listing_drafts` — saved listing drafts
- `ag_box_registry` — box code registry

All created in the shared `backend/data/empire.db` SQLite with `ag_` prefix to avoid collisions.

---

## LIFE Reference Data (Local Fixture)

15 canonical LIFE magazine issues covering 1936–1972, all with manually researched facts:
- `LIFE_REFERENCE_ISSUES` constant in `archiveforge.py` (lines 20–160)
- Source: historical public record — first issues, WWII milestones, JFK assassination, moon landing, etc.
- Reference cover images from Wikimedia Commons (public domain)
- All comp values are researched estimates, clearly labeled

---

## What Works End-to-End (V1)

- ✅ 7-step wizard navigation with progress indicators
- ✅ Reference issue search with keyword/date/volume scoring
- ✅ Reference vs actual image separation (two distinct roles)
- ✅ Physical archive tracking: source box → processed box with status transitions
- ✅ Valid status transitions enforced (invalid transitions return 409)
- ✅ Box convention support: A-RARE-01, B-[era], C-BULK-01, HOLD-01, SOLD-STAGING-01
- ✅ Condition scoring (1–5 scale with labels)
- ✅ Tier assignment (A/B/C with guidance)
- ✅ Auto-fill listing title and description from archive data
- ✅ Item specifics preview
- ✅ MarketForge-ready payload generated (JSON)
- ✅ Listing draft saved locally (draft only — no publishing)
- ✅ Inventory spreadsheet view with filters (status, tier, search)
- ✅ Stats dashboard (counts by status and tier)
- ✅ Box registry

---

## What Is NOT Yet Implemented (V1 Gaps)

1. **No server-side image storage** — actual listing images stored as data URIs in V1 (browser-local only). Real implementation needs S3/blob storage upload endpoint.
2. **No live eBay/Amazon/MarketForge API push** — listing drafts are generated locally, not published. MarketForge `POST /listings` integration needed.
3. **No background worker** — price monitoring, auto-relist, inventory sync not applicable to physical print (different from RelistApp digital arbitrage).
4. **No authentication** — all endpoints are open in V1. Auth middleware should be added for multi-user.
5. **Limited LIFE reference data** — 15 issues. Should expand to cover all notable issues 1936–1972.
6. **No PDF/export of listing** — listing draft could be exported as PDF.
7. **No batch operations** — multi-item intake, bulk status update not implemented.

---

## Next 3 Tasks for ArchiveForge

### Task 1: Server-Side Image Storage
Add `POST /archiveforge/upload` endpoint that accepts multipart image uploads and stores them on disk (or S3). Update frontend to call this instead of using data URIs. This is the primary blocker for real usage.

### Task 2: Expand LIFE Reference Database
Grow from 15 to 50+ canonical reference issues covering: all WWII milestone issues, all 1960s presidential issues, notable cultural/science covers, rare variant covers. Add `PUT /archiveforge/reference/{id}` admin endpoint to update reference data.

### Task 3: MarketForge Draft Push
Wire `POST /archiveforge/archives/{id}/listing-draft` to actually call MarketForge's `POST /listings` endpoint when ready. Add a "Review & Push" step in the wizard that shows the complete draft and lets user confirm before MarketForge publish.

---

## Integration Notes for Codex/Main Branch Merge

When merging `feature/archiveforge-life` into `main`:

1. **Router registration** (`main.py`): The `load_router` line is already minimal and isolated — no risk to other routers.
2. **Type change** (`types.ts`): Adding `'archive'` to `EcosystemProduct` is a type-level addition — safe.
3. **Nav change** (`LeftNav.tsx`): Adding one nav item — safe, no existing items affected.
4. **Route change** (`page.tsx`): Standard product switch case — safe pattern.
5. **Database**: `ag_*` prefixed tables don't conflict with `ra_*` (RelistApp), `ac_*`, or any other prefixed tables in the shared SQLite DB.

**No MAX core changes.** No VendorOps touches. No shared pricing config changes. No background worker changes.
