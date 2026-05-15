# Hermes Knowledge Artifact Layer (v10)

Date: 2026-05-15  
Lane: `v10-test` (`feature/v10.0-test-lane`, `3010/8010`)

## Purpose

Artifact Mode is the MAX output/review layer.  
Hermes Knowledge Artifact Layer is the persistence/retrieval layer.

This layer stores high-value MAX/Hermes/OpenClaw outputs as durable artifacts with:
- sanitized HTML
- metadata + provenance
- extracted text
- review status
- supersede history

## What Existed Before This Phase

1. Artifact generation/parsing/safe preview existed in chat UI and MAX backend parser.
2. Approval/reject/request-changes existed as local React state only.
3. Hermes memory bridge existed (`CONTEXT.md`, `MEMORY.md`, `USER.md`, `DRAFTS`, `SCHEDULED`, `BROWSER_ACTIONS`).
4. No durable artifact persistence contract existed for search/get/status/supersede/export.

## What Changed In This Phase

Backend additions:
- `backend/app/services/max/hermes_artifact_layer.py`
- `backend/app/routers/hermes_artifacts.py`
- `backend/app/main.py` loads `/api/v1/hermes/artifacts/*`
- `/api/v1/max/status` includes `hermes_artifact_layer` status

Frontend additions:
- Artifact action button: **Save to Hermes Memory**
- Persist result/error feedback in Artifact Actions panel
- Viewer footer now reflects optional persistence

Tests added:
- `backend/tests/test_hermes_artifact_layer.py`
- `backend/tests/test_hermes_artifact_layer_api.py`

## Storage Layout

Root:
- `~/empire-box-memory/ARTIFACTS/`

Scaffolded directories:
- `index.jsonl`
- `max/`
- `hermes/`
- `openclaw/`
- `modules/workroom/`
- `modules/woodcraft/`
- `modules/archiveforge/`
- `modules/marketforge/`
- `modules/relistapp/`
- `modules/drawing-studio/`
- `modules/vendorops/`
- `modules/socialforge/`
- `modules/apostapp/`
- `modules/crm/`
- `modules/ai-model-control/`
- `modules/system/`

Per-artifact files:
- `artifact.html` (sanitized)
- `metadata.json`
- `extracted.txt`
- `summary.txt`
- `provenance.json`

## Metadata Contract

Each artifact stores:
- `id`
- `title`
- `artifact_type`
- `module`
- `source_agent` (`max|hermes|openclaw|founder`)
- `created_at`
- `updated_at`
- `lane`
- `branch`
- `commit`
- `approval_status` (`draft|approved|rejected|changes_requested|superseded`)
- `safety_status`
- `provenance`
- `supersedes`
- `superseded_by`
- `tags`
- `retrieval_keywords`
- `source_prompt_hash`
- `source_files`
- `source_endpoints`

## Retrieval Contract

Service functions:
- `hermes_artifact_write`
- `hermes_artifact_search`
- `hermes_artifact_get`
- `hermes_artifact_update_status`
- `hermes_artifact_supersede`
- `hermes_artifact_export`

API routes:
- `GET /api/v1/hermes/artifacts/status`
- `POST /api/v1/hermes/artifacts/write`
- `POST /api/v1/hermes/artifacts/search`
- `GET /api/v1/hermes/artifacts/{id}`
- `POST /api/v1/hermes/artifacts/{id}/status`
- `POST /api/v1/hermes/artifacts/supersede`
- `GET /api/v1/hermes/artifacts/{id}/export`

Search filters:
- `query`
- `module`
- `artifact_type`
- `approval_status`
- `tags`
- `date_from/date_to`
- `current_only`
- `include_superseded`

`current_only=true` excludes superseded records.

## Security Model

HTML safety:
- strips `<script>`, `<link>`, `<iframe>`, `<form>`, `<object>`, `<embed>`
- strips event-handler attributes (`onclick`, etc.)
- strips external `href/src/action` URLs
- strips `meta http-equiv=refresh`

UI preview safety remains sandboxed (no scripts, no same-origin, no forms).

## Truth Hierarchy

Artifacts are supporting context only and never primary truth.

Order:
1. runtime
2. repo truth
3. database truth
4. module docs
5. approved artifacts
6. session context
7. model opinion

## Approval Lifecycle

1. Artifact created as `draft` (or explicit incoming status).
2. Reviewer may set status (`approved/rejected/changes_requested`).
3. Replacement artifact can supersede prior artifact:
   - old -> `superseded`
   - new tracks `supersedes=[old_id]`

## Known Limitations

1. MAX tool executor is not yet wired to automatically call artifact search/get tools in prompts.
2. Artifact persistence is currently manual via API/UI action, not auto-ingest.
3. No signed approval identity yet; status updates are trusted application actions.
4. No cross-lane sharing; this implementation is lane-local and v10-only.

## Next Recommended Phase

1. Add explicit MAX tool bindings for artifact search/get/update in `tool_executor`.
2. Add founder-authenticated approval actor metadata.
3. Add artifact ranking weights (freshness + approval + module relevance).
4. Add artifact packet templates for ArchiveForge/Workroom/MarketForge.
