# ArchiveForge Status (Stable/Live)

Last updated: May 14, 2026
Repo: `~/empire-repo`
Branch: `feature/v10.0`

## Runtime Truth

- Local backend: `http://localhost:8000`
- Local frontend: `http://localhost:3005`
- Public studio: `https://studio.empirebox.store`
- Public API: `https://studio.empirebox.store/api/v1/archiveforge/*`
- Primary UI route: `/archiveforge-life`
- Legacy route: `/archiveforge` redirects to `/archiveforge-life` (HTTP 307)

## Publish Safety Truth

ArchiveForge publish is **internal staged publish**, not external marketplace publish.

When publish succeeds:

1. ArchiveForge posts to internal `POST /marketplace/products`.
2. `marketforge_products.py` writes a row to SQLite table `mf_products`.
3. Archive row is updated with `marketforge_listing_id`, push status, and timestamps.

There is no direct external marketplace API call in this flow.

## Publish Guardrails (Current)

- `approval_confirmed=true` is required on `/api/v1/archiveforge/push/{archive_id}`.
- Publish is blocked with `409` if these fields are missing/invalid on the archive:
  - `marketforge_category_id` (must be UUID)
  - `marketforge_ships_from_zip` (must be 5-digit ZIP)
- External MarketForge targets are blocked by host allowlist in publish-status logic.
- Push status `blocked_missing_marketforge_fields` is persisted when publish is rejected for missing/invalid MarketForge fields.

## Data Model

Verified tables in `backend/data/empire.db`:

- `ag_archives`
- `ag_archive_photos`
- `ag_listing_drafts`
- `ag_box_registry`
- `mf_products`

`ag_archives` now includes:

- `marketforge_category_id`
- `marketforge_ships_from_zip`

## Capability Snapshot

| Capability | Status | Notes |
|---|---|---|
| Intake / save / list / detail | ✅ | create + edit + list + detail live |
| Listing draft generation + save | ✅ | both endpoints live |
| Review + publish UI | ✅ | includes required publish fields and validation |
| Publish approval gate | ✅ | explicit approval query required |
| Placeholder publish defaults removed | ✅ | no silent fallback category/ZIP defaults |
| External publish route protection | ✅ | external host blocked |
| Public ArchiveForge API routing | ✅ | studio `/api/v1/archiveforge/*` returns 200 |

## Verification Results

Local tests:

- `backend/venv/bin/pytest backend/tests/test_archiveforge_workflow.py -q` → **13 passed**
- `backend/venv/bin/pytest backend/tests/test_max_truth_guardrails.py -q` → **14 passed**
- `bash scripts/smoke_archiveforge.sh` → **PASS**
- `cd empire-command-center && npm run build` → **PASS**

Public smoke:

- `GET https://studio.empirebox.store/api/v1/archiveforge/publish-status` → 200
- `GET https://studio.empirebox.store/api/v1/archiveforge/stats` → 200
- `GET https://studio.empirebox.store/api/v1/archiveforge/archives?limit=3` → 200
- `GET https://studio.empirebox.store/archiveforge-life` → 200

v10 parity check:

- `GET https://test-studio.empirebox.store/api/v1/archiveforge/publish-status` now reports target `http://localhost:8010/marketplace/products`.

## Known Limitations

- Marketplace publish remains internal staged only by design until founder-approved external integration is explicitly enabled.
- No automatic category inference fallback is used for publish; operator must provide category UUID and ship ZIP.
