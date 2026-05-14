# ArchiveForge Status (Stable/Live)

Last updated: May 14, 2026
Repo: `~/empire-repo`
Branch: `feature/v10.0`
Runtime commit (MAX status): `dd57341`

## Runtime Truth

- Local backend: `http://localhost:8000`
- Local frontend: `http://localhost:3005`
- Public studio: `https://studio.empirebox.store`
- Public API path: `https://studio.empirebox.store/api/v1/archiveforge/*`
- API domain used by frontend in public mode: `https://api.empirebox.store/api/v1`

## Routes and Pages

- Primary route: `/archiveforge-life` (full production workflow)
- Legacy route: `/archiveforge` now redirects to `/archiveforge-life` (no stub/fake flow)

## Backend Endpoints (live)

Mounted under `/api/v1/archiveforge`:

- Reference: `/reference`, `/reference/search`, `/reference/{id}`, `/reference/all`
- Archive CRUD: `/archives` (GET/POST), `/archives/{id}` (GET/PATCH/DELETE)
- Workflow: `/archives/{id}/status`, `/archives/{id}/rebox`
- Listing: `/archives/{id}/listing-draft`, `/archives/{id}/save-draft`, `/drafts`
- Photos: `/uploads/{archive_id}` (GET/POST), `/photo/{photo_id}` (GET/DELETE)
- Inventory: `/inventory`, `/inventory/export`, `/stats`
- Publish: `/publish-status`, `/push/{archive_id}`

## Database Tables (verified in `backend/data/empire.db`)

- `ag_archives`
- `ag_archive_photos`
- `ag_listing_drafts`
- `ag_box_registry`
- `mf_products` (local MarketForge product target used by ArchiveForge push)

## Capability Matrix

| Capability | Status | Notes |
|---|---|---|
| Dashboard loads | ✅ | Step UI loads in browser |
| Intake/create item | ✅ | `POST /archives` |
| Photo upload | ✅ | persisted file + DB row |
| Metadata edit | ✅ | `PATCH /archives/{id}` |
| OCR/analysis hook clarity | ✅ | not required for core flow; no fake OCR claim in core path |
| Google Books/cover lookup | ✅ | API + curated fallback, confidence shown |
| LIFE issue workflow | ✅ | step-by-step flow verified in browser |
| Cover relevance | ✅ | ranking/date-keyword scoring; irrelevant fallback suppressed |
| Listing draft generation/save | ✅ | `listing-draft` + `save-draft` live |
| Pricing/comps | ⚠️ partial | manual comp fields supported; no fake live comps claim in core flow |
| Listing review | ✅ | Step 7 review panel |
| Publish path gate | ✅ | explicit manual step/button; publish-status surfaced |
| Save item | ✅ | persisted in `ag_archives` |
| Search/list inventory | ✅ | list + stats + filters |
| Detail page/data | ✅ | `GET /archives/{id}` |
| Delete/update safety | ✅ | delete now removes dependent rows/files safely |
| UI error clarity | ✅ | validation and publish errors displayed |
| MAX ArchiveForge truth | ✅ | status/workflow answers are truthful, prefill still routed correctly |
| Public route health | ✅ | studio `/archiveforge-life` + `/api/v1/archiveforge/*` reachable |
| Docs current | ✅ | this status + workflow doc updated |

## Fixes Applied In This Cycle

1. Fixed delete failure (`500`) in archive core flow by deleting child rows/files before parent archive delete.
2. Replaced legacy `/archiveforge` stub page with redirect to `/archiveforge-life`.
3. Updated MAX direct route behavior for ArchiveForge informational prompts so it returns truthful workflow/status instead of generic “no draft created.”

## Verified Tests

- Backend smoke: `./scripts/smoke_archiveforge.sh` (PASS)
- Local browser workflow (headless Playwright runner): intake → photos → status transitions → draft → review/publish (PASS)
- Public browser smoke: `https://studio.empirebox.store/archiveforge-life` loads Step 1 (PASS)
- Public API smoke:
  - `GET /api/v1/archiveforge/publish-status` (200)
  - `GET /api/v1/archiveforge/stats` (200)
  - `GET /api/v1/archiveforge/archives?limit=3` (200)
- MAX prompts validated:
  - “What is ArchiveForge?”
  - “Help me process a LIFE magazine in ArchiveForge.”
  - “Can ArchiveForge publish to marketplace yet?”
  - “What ArchiveForge features are working?”

## Gated / Known Limitations

- Publish is explicit/manual in Step 7; never automatic.
- MarketForge payload still uses placeholder `category_id` and `ships_from_zip` defaults in current router payload builder.
- No claim of live external comps pipeline in core workflow; manual comp fields are supported.

## Rollback

If rollback is required, revert these files:

- `backend/app/routers/archiveforge.py`
- `backend/app/routers/max/router.py`
- `backend/tests/test_max_truth_guardrails.py`
- `empire-command-center/app/archiveforge/page.tsx`
- `scripts/smoke_archiveforge.sh`
- `docs/ARCHIVEFORGE_STATUS.md`
- `docs/ARCHIVEFORGE_WORKFLOW.md`
