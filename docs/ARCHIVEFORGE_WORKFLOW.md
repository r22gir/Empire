# ArchiveForge Workflow (Stable/Live)

Last updated: May 14, 2026

## Operator Path (UI)

Entry URL:

- Local: `http://localhost:3005/archiveforge-life`
- Public: `https://studio.empirebox.store/archiveforge-life`

Legacy compatibility:

- `/archiveforge` redirects to `/archiveforge-life`

## End-to-End Flow

1. Identify issue (Step 1)
   - Use date + keyword search against `/api/v1/archiveforge/reference/search`
   - Select the matched LIFE reference issue
2. Confirm reference (Step 2)
   - Reference cover shown for comparison only
3. Upload actual item photos (Step 3)
   - Uploads to `/api/v1/archiveforge/uploads/{archive_id}`
4. Physical archive tracking (Step 4)
   - Source box / destination box / location
   - Status transitions via `/api/v1/archiveforge/archives/{id}/status`
5. Condition + tier (Step 5)
   - Condition score, tier, comp range, defects, notes
6. Listing builder (Step 6)
   - Generate/edit listing text
   - Save draft via `/api/v1/archiveforge/archives/{id}/save-draft`
7. Review & publish (Step 7)
   - Validate title/description/photos/status
   - Set required MarketForge fields on the archive:
     - `marketforge_category_id` (UUID)
     - `marketforge_ships_from_zip` (5-digit ZIP)
   - Publish status banner from `/api/v1/archiveforge/publish-status?archive_id={id}`
   - Push endpoint: `/api/v1/archiveforge/push/{id}?approval_confirmed=true` (manual explicit action only)
8. Inventory view
   - `/api/v1/archiveforge/archives`, `/stats`, `/inventory`

## Publish Safety

- Publish is manual and explicit in Step 7; no auto publish.
- `approval_confirmed=true` is required or publish returns HTTP 400.
- Missing/invalid MarketForge fields block publish with HTTP 409 and persisted status `blocked_missing_marketforge_fields`.
- ArchiveForge publish target is internal staged route only:
  - `http://localhost:8000/marketplace/products`
- External host targets are blocked by publish-status safety checks.
- Successful publish means internal product record creation in `mf_products`, not external marketplace go-live.

## API Smoke Commands

Run local smoke:

```bash
cd ~/empire-repo
./scripts/smoke_archiveforge.sh
```

Public checks:

```bash
curl -s https://studio.empirebox.store/api/v1/archiveforge/publish-status | python3 -m json.tool
curl -s https://studio.empirebox.store/api/v1/archiveforge/stats | python3 -m json.tool
curl -s "https://studio.empirebox.store/api/v1/archiveforge/archives?limit=3" | python3 -m json.tool
```

## Manual Browser Verification (lightweight)

Because frontend e2e test tooling is not configured in this repo, use this manual check:

1. Open `http://localhost:3005/archiveforge` and verify redirect to `/archiveforge-life`.
2. Create an archive item in the life workflow.
3. Save draft and move status to `READY_TO_LIST`.
4. Upload at least one photo.
5. In Review & Publish:
   - leave MarketForge fields blank and verify publish is blocked with clear validation
   - enter valid UUID + ZIP and save fields
   - verify publish requires explicit approval path and succeeds only after trigger
6. Confirm saved item appears in list/detail pages.
7. Confirm no core-flow “coming soon” blocker text is shown.

## MAX Guidance Behavior

MAX now supports two ArchiveForge response modes:

- Intake-prefill requests:
  - routed to Hermes prefill workflow (`life_magazine_intake`)
- Informational ArchiveForge requests:
  - returns truthful ArchiveForge status/workflow summary (not fake draft output)

## Guardrail Rule

Never represent core ArchiveForge workflow as complete unless browser flow and API flow both pass:

- create
- photo upload
- status transitions
- listing draft save
- review/publish gate
- delete cleanup
