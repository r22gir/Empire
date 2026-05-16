# ADR: Hermes Knowledge Artifact Layer (v10)

Date: 2026-05-15
Status: accepted (v10 test lane)

## Decision

Implement a v10-only artifact persistence layer that sits beneath runtime/repo/database truth and above transient session context.

Chosen architecture:
- Keep MAX Artifact Mode as presentation/review output layer.
- Add Hermes artifact persistence service + API for durable retrieval and governance.
- Persist sanitized HTML + extracted text + metadata + provenance.
- Preserve explicit truth boundary in service responses.

## Why

Without durable artifacts:
- MAX repeatedly rediscovers context.
- Review packets are not versioned or searchable.
- Approval state is mostly ephemeral.

With this layer:
- important outputs become durable and queryable
- supersede lifecycle becomes explicit
- provenance and source references are retained

## Scope

In scope (this ADR implementation):
- artifact storage scaffold under `~/empire-box-memory/ARTIFACTS`
- write/search/get/update/supersede/export contract
- HTML sanitization and extracted-text generation
- v10 API exposure
- minimal UI save action
- MAX retrieval wiring for artifact-memory questions using internal tool hooks
- default approved/current filtering to reduce stale memory use
- approval identity metadata (actor/source/method/confidence/timestamp/history)
- ranking/reranking with explicit score and matched field metadata
- signer-bound approval attestation scaffolding (tamper-evident hash chain; not cryptographic signing)

Out of scope (next phase):
- signed approval identity model
- enterprise authorization model
- cross-lane synchronization

## Truth Priority

1. runtime
2. repo truth
3. database truth
4. module docs
5. approved + attested + current artifacts
6. approved + current artifacts
7. session context
8. model opinion

Artifacts must never override levels 1-4.

## Consequences

Positive:
- durable review artifacts
- searchable historical packets
- explicit supersede relationships
- MAX can answer prior-decision questions from approved/current artifact memory

Tradeoffs:
- additional storage and metadata maintenance
- requires governance to avoid artifact sprawl
- ranking remains heuristic (not embedding-based reranking yet)

## Runtime Freshness Addendum (2026-05-15)

Because runtime truth outranks artifacts, git freshness checks must be lane-scoped.

Implemented:
- lane-aware metadata helper for branch/commit/worktree resolution
- `GET /api/v1/git` as the canonical lane metadata endpoint
- compatibility `GET /api/v1/dev/git` now backed by the same lane-aware source
- runtime truth check now compares commits using active lane endpoints:
  - local: `http://127.0.0.1:{active_backend_port}/api/v1/git`
  - public: `{lane_public_base}/api/v1/git`

This removes false freshness mismatch reports that occurred when runtime checks read from a parked root worktree or the wrong hostname.

## Safety Constraints

- no script execution from stored HTML
- no external URL execution in stored HTML
- no form/iframe/object/embed storage in final artifact HTML
- UI remains sandboxed for HTML preview
- artifacts are supporting memory only and never override runtime/repo/database/module-doc truth

## Attestation Model Addendum

Attestation levels:
- `none`
- `local_ui`
- `session_verified`
- `founder_attested`
- `system_generated`
- `imported`

Ordering for retrieval/ranking favors:
1. approved + founder_attested + current
2. approved + session_verified + current
3. approved + local_ui + current
4. approved + system_generated + current

Attestation hashes are deterministic/tamper-evident audit records, not legal signatures.

## Rollback

If needed:
1. stop using `/api/v1/hermes/artifacts/*`
2. keep historical files in `ARTIFACTS/` read-only
3. remove router mount for hermes artifacts in v10 lane only
