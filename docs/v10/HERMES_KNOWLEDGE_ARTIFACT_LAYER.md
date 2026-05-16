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
- `approval_actor_id`
- `approval_actor_type`
- `approval_actor_label`
- `approval_actor_source`
- `approval_timestamp`
- `approval_note`
- `approval_method` (`ui|api|max_internal|openclaw|unknown`)
- `approval_confidence` (`verified_session|local_ui|system_generated|unknown`)
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

Search result ranking metadata:
- `score`
- `matched_fields`
- `freshness_score`
- `approval_weight`
- `module_weight`
- `provenance_weight`
- `stale_warning`

## MAX Retrieval Policy (v10)

MAX uses Hermes artifact retrieval only for memory-oriented questions, including:
- prior decisions ("what did we decide")
- latest design/report/packet requests
- module artifact memory comparisons versus prior plans
- OpenClaw/Codex context preparation prompts

MAX does **not** use artifact memory as primary truth for:
- runtime/service health
- repo/code state
- database truth
- public route/API freshness
- current-events/news queries

Truth precedence remains:
1. runtime
2. repo truth
3. database truth
4. module docs
5. approved + attested + current artifacts
6. approved + current artifacts
7. session context
8. model opinion

By default, artifact retrieval uses:
- `approval_status=approved`
- `current_only=true`

Draft/rejected/superseded artifacts are only returned when explicitly requested.

## Supervised Repair `task_ref` Handshake (v10-only)

For supervised v10 repair recommendations, MAX now issues a one-time `task_ref` token and persists a pending recommendation record before any OpenClaw task creation.

Recommendation response includes:
- `task_ref`
- `task_ref_created_at`
- `task_ref_expires_at`
- recommendation hash + safety gate snapshot
- approval instruction:
  - `Approved task_ref=<TOKEN>. Create exactly one bounded OpenClaw task.`

Stored recommendation fields include lane/branch/commit binding, bounded task scope, allowed/forbidden paths, required tests, and Hermes context IDs used for recommendation grounding.

Creation route behavior:
- requires exact approval phrase with token
- rejects missing/unknown/expired/consumed token
- rejects lane/branch mismatch
- rejects scope tamper attempts
- re-checks safety gates at create time
- builds task payload from stored recommendation (not from a generic template)
- marks token consumed on successful queue

Token policy:
- TTL: 90 minutes
- single-use only
- lane-bound (`v10-test`)
- branch-bound (`feature/v10.0-test-lane`)

## Runtime Truth Integration (Lane-Aware Git Freshness)

Artifact memory must remain below runtime/repo truth, so runtime freshness must be lane-correct.

v10 runtime checks now use lane-aware git metadata from:
- `GET /api/v1/git` (primary)
- `GET /api/v1/dev/git` (compatibility view)

The source is resolved from active backend service context (`EMPIRE_LANE`, `EMPIRE_BACKEND_PORT`, `EMPIRE_FRONTEND_EXPECTED_PORT`, and git top-level from backend cwd), not a hardcoded repo root.

For lane `v10-test`:
- expected worktree: `~/empire-repo-v10`
- expected backend port: `8010`
- expected frontend port: `3010`
- expected public base: `https://test-studio.empirebox.store`

Runtime freshness comparison now avoids false stale results caused by cross-lane repo reads. If public git check is unavailable, freshness reports `public_unavailable` instead of a stale commit claim.

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

Status updates append actor metadata:
- `approval_actor_id`: optional actor/session id
- `approval_actor_type`: `founder|max|openclaw|hermes|unknown`
- `approval_actor_label`: optional display label
- `approval_actor_source`: `verified_session|local_ui|api|max_internal|openclaw|system_generated|unknown`
- `approval_timestamp`: UTC status event timestamp
- `approval_note`: optional status note
- `approval_method`: `ui|api|max_internal|openclaw|unknown`
- `approval_confidence`: `verified_session|local_ui|system_generated|unknown`

Signer-bound approvals are **not** implemented yet.
`verified_session` confidence is only used when a real session actor id is present; otherwise confidence is downgraded to `local_ui`, `system_generated`, or `unknown`.

## Approval Attestation (Signer-Bound Scaffolding)

Each status transition now writes a tamper-evident attestation record:

- `attestation_id`
- `artifact_id`
- `artifact_version_hash`
- `artifact_metadata_hash`
- `artifact_content_hash`
- `approval_status`
- `actor_id`, `actor_type`, `actor_label`, `actor_source`, `actor_session_id`
- `approval_method`, `approval_confidence`
- `attestation_level`
- `attested_at`
- `attestation_note`
- `previous_attestation_hash`
- `attestation_hash`

Supported `attestation_level`:
- `none`
- `local_ui`
- `session_verified`
- `founder_attested`
- `system_generated`
- `imported`

Rules:
- Local UI review defaults to `local_ui`.
- `session_verified` and `founder_attested` require verified session actor evidence.
- MAX/Hermes/OpenClaw internal status events default to `system_generated`.
- Imported/legacy artifacts are backfilled as `imported` when needed.

This is tamper-evident hashing and chain-linking, not legal/cryptographic signing.

## Hash Model

Artifacts maintain:
- `latest_content_hash`
- `latest_metadata_hash`
- `latest_version_hash`
- `latest_attestation_hash`
- `latest_attestation_hash_short`
- `latest_attestation_level`
- `requires_reattestation`
- `is_current`

Hash notes:
- Content hash is based on sanitized HTML + extracted text.
- Metadata hash uses canonical JSON excluding volatile fields (timestamps/history pointers).
- Version hash combines content hash + metadata hash + status + supersede state.
- Attestation hash is deterministic over the attestation payload and links to `previous_attestation_hash`.

If content changes after approval, `requires_reattestation=true` and the artifact is treated as not current until a new attestation is written.

## UI State Reconciliation

Artifact Viewer now distinguishes:
- local-only review state (not persisted)
- persisted Hermes artifact state (artifact id + backend approval status)

When a persisted artifact exists, Approve/Reject/Request Changes updates backend status via:
- `POST /api/v1/hermes/artifacts/{id}/status`

If persistence does not exist yet, review actions remain local-only.

## Known Limitations

1. Artifact persistence is still manual via API/UI action; there is no auto-ingest for all MAX responses.
2. No signed approval identity yet; actor metadata is lightweight and application-level.
3. No cross-lane sharing; this implementation is lane-local and v10-only.
4. Anti-stale rules rely on status/current filters, ranking, and supersede links; no semantic conflict detector yet.

## Next Recommended Phase

1. Add signer-bound approval identity and audit attestations.
2. Add artifact ranking weights (freshness + approval + module relevance).
3. Add semantic stale/conflict detection across artifacts.
4. Add artifact packet templates for ArchiveForge/Workroom/MarketForge.
