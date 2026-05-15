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

Out of scope (next phase):
- signed approval identity model
- enterprise authorization model
- cross-lane synchronization

## Truth Priority

1. runtime  
2. repo truth  
3. database truth  
4. module docs  
5. approved artifacts  
6. session context  
7. model opinion

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

## Safety Constraints

- no script execution from stored HTML
- no external URL execution in stored HTML
- no form/iframe/object/embed storage in final artifact HTML
- UI remains sandboxed for HTML preview
- artifacts are supporting memory only and never override runtime/repo/database/module-doc truth

## Rollback

If needed:
1. stop using `/api/v1/hermes/artifacts/*`
2. keep historical files in `ARTIFACTS/` read-only
3. remove router mount for hermes artifacts in v10 lane only
