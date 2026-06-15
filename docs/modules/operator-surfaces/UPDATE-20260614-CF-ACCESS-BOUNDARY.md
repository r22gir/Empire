# Operator Surfaces Update: Cloudflare Access Boundary

- Module: Operator surfaces
- Date: 2026-06-14
- Current state: Operator hostnames remain Cloudflare Access protected after Gate 1 public launch.
- Last verified timestamp/source: 2026-06-14, Founder-provided Gate 1 launch state and prior Codex/Hermes/Harry reports.

## What Changed

Gate 1 public launch exposed the public EmpireBox apex and `www` landing surface while preserving operator hostname protection.

## Live URLs / Surfaces

Operator hostnames:

- `https://studio.empirebox.store/`
- `https://luxe.empirebox.store/`
- `https://forge.empirebox.store/`
- `https://hermes.empirebox.store/`

These are operator surfaces and should remain protected.

## Public / Private Boundaries

Public:

- `https://empirebox.store/`
- `https://www.empirebox.store/`
- ApostApp public paths

Protected:

- studio
- luxe
- forge
- hermes
- internal APIs
- operator-only intake/admin tooling

## Commits Involved

- Gate 1 source/runtime reconciliation: `9deeff42a4fd435b2c4eae1d48fd2ba83e7f5289`
- Later Gate 1 execution and Phase 1 documentation work were performed on the release candidate branch per Founder context.

## Runtime / Tunnel / Service State

Founder context confirms operator hostnames remain Cloudflare Access protected. This document does not alter Cloudflare Access policies, DNS records, tunnel configs, or services.

## Tests / Checks Performed

Reported checks:

- public apex routes live
- public internal paths return 404
- operator hostnames remain Cloudflare Access protected
- ApostApp preserved

## Approvals Consumed

- Gate 1 execution approvals during launch
- `APPROVE CODEX IMPLEMENTATION` for this docs/UI work

## Known Risks

- Luxe/Forge Access behavior needs continued policy/session verification.
- Any Access policy edit requires explicit approval.

## Follow-Up Work

- Run a separate Cloudflare Access verification/audit if Founder requests it.
- Keep operator boundary docs current after every launch or ingress change.

## Next Approvals

- `APPROVE CLOUDFLARE/DNS CHANGE` before Access/DNS/tunnel edits
- `APPROVE SERVICE RESTART` before any tunnel/service reload
