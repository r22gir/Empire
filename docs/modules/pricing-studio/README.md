# Pricing Studio Documentation

Status: Pending module update.

Pricing Studio now uses the shared module Docs UI pattern. A full current-state document should be added the next time Pricing Studio receives a meaningful engine, route, pricing policy, or UI change.

Current discoverable references:

- Command Center Pricing Studio screen
- pricing API router
- canonical pricing engine tests
- Workroom and WoodCraft module docs used as pricing input context

## Workroom material sell rates (Rafael, 10/4/2026)

Set in Pricing Studio → workroom rules (`GET/POST /api/v1/pricing/workroom/rules`, defaults in
`backend/app/services/pricing/workroom_rules.py`):

- Lining: `lining_per_yard` = **$10.50 / yd**
- Napped lining / interlining (bump): `bump_per_yard` = **$12.50 / yd**

Always the workroom's own rates, never supplier list prices (those exclude freight). Existing quotes are not
repriced. Details: `docs/workroom/RELINE_PRICING.md`.
