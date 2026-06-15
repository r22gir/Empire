# EmpireBox Public Site Update: Gate 1 Public Launch

- Module: EmpireBox public site
- Date: 2026-06-14
- Current state: Gate 1 public apex launch is complete.
- Last verified timestamp/source: 2026-06-14, Founder-provided launch state and Codex/Hermes/Harry Gate 1 reports.

## What Changed

The R1X public landing route was reconciled into the live release candidate branch while preserving the live apex/FORGE/LUXE middleware boundary. Cloudflare/DNS execution completed after approval, and the public apex and `www` host now serve the EmpireBox landing site.

## Live URLs / Surfaces

- `https://empirebox.store/` is live.
- `https://www.empirebox.store/` is live.
- Public internal paths return 404.
- Operator hostnames remain behind Cloudflare Access.

## Public / Private Boundaries

Public:

- apex landing page
- `www` landing page

Private/protected:

- internal apex paths such as `/intake`, `/admin`, and internal API paths
- operator hostnames including studio, luxe, forge, and hermes

## Commits Involved

- `9deeff42a4fd435b2c4eae1d48fd2ba83e7f5289` added the R1X landing route into the live release candidate branch.
- Later Gate 1 launch and MAX/OpenClaw Phase 1 changes were committed and pushed to the release candidate branch per Founder context.

## Runtime / Tunnel / Service State

Founder context confirms the public apex and `www` host are live after Cloudflare/DNS and tunnel execution. This document does not alter tunnel config or service state.

## Tests / Checks Performed

Reported Gate 1 checks:

- apex landing returned 200
- `www` landing returned 200
- public internal paths returned 404
- ApostApp public routes remained preserved
- operator hostnames remained Cloudflare Access protected

## Approvals Consumed

- `APPROVE CODEX IMPLEMENTATION` for source reconciliation work
- Gate 1 execution approvals were handled in the launch workflow before public launch completion

## Known Risks

- Cloudflare Access behavior for Luxe/Forge/operator flows should continue to be verified separately from public apex launch.
- CORS hardening remains a separate follow-up.

## Follow-Up Work

- Continue preserving public/private route boundaries in every launch change.
- Keep module update docs under `docs/modules/`.
- Proceed to Gate 3 PR only after Founder approval.

## Next Approvals

- `APPROVE GATE 3 PRODUCTION PR` for production PR work
- `APPROVE PUSH` for any future pushed changes
