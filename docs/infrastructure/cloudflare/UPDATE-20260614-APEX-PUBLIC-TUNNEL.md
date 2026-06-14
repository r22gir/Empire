# Cloudflare Infrastructure Update: Apex Public Tunnel

- Module: Cloudflare / public edge infrastructure
- Date: 2026-06-14
- Current state: EmpireBox apex and `www` public landing are live after Gate 1.
- Last verified timestamp/source: 2026-06-14, Founder-provided Gate 1 launch context and prior launch reports.

## What Changed

The public edge now routes `empirebox.store` and `www.empirebox.store` to the EmpireBox public landing experience while keeping internal and operator surfaces protected.

## Live URLs / Surfaces

- `https://empirebox.store/`
- `https://www.empirebox.store/`

## Public / Private Boundaries

Public:

- apex landing
- `www` landing

Private/protected:

- public internal paths return 404
- operator hostnames remain Cloudflare Access protected
- internal APIs are not broadly exposed

## Commits Involved

- `9deeff42a4fd435b2c4eae1d48fd2ba83e7f5289` for public landing source reconciliation.
- Later Gate 1 launch and Phase 1 updates were committed and pushed to the release candidate branch per Founder context.

## Runtime / Tunnel / Service State

Founder context confirms Cloudflare/DNS and tunnel execution completed for public launch. This document does not change tunnel config, DNS, Access policies, or running services.

## Tests / Checks Performed

Reported checks:

- apex public landing live
- `www` public landing live
- public internal paths 404
- ApostApp preserved
- operator hostnames protected

## Approvals Consumed

- Gate 1 public launch approvals were consumed in the launch workflow.
- This documentation/UI update consumes `APPROVE CODEX IMPLEMENTATION`.

## Known Risks

- Access policy/session verification for Luxe/Forge remains a follow-up.
- CORS hardening remains a separate workstream.

## Follow-Up Work

- Keep infrastructure updates under `docs/infrastructure/cloudflare/`.
- Re-check route boundaries before Gate 3 PR.

## Next Approvals

- `APPROVE CLOUDFLARE/DNS CHANGE` for any future DNS/Cloudflare edits
- `APPROVE SERVICE RESTART` for service/tunnel reloads
- `APPROVE GATE 3 PRODUCTION PR` for production PR work

