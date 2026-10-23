# Willard area-layout mock proof (2026-10-23)

Format reference only. Not a live job. No real client data.

## NO-GO review (PR #225)

Re-line keeps the old path by default:

- `$145` / window through 8 ft, then `$20` / ft overage
- `install_per_window` still means the window rate (72" = `$145`)
- Header-B groups: Installation / Preparation / Construction / Materials
- `track_hours` is the founder per-quote hourly override (sample `$4,736.20` / `$2,368.10` / `$2,574.10`)

New fabrication keeps the Willard area layout and `$245` / 8 ft install + `$325` / 8 ft complete track. Hourly install/track is unreachable unless the founder sets an explicit per-quote override. Default tool calls never pass hours.

Designer name and markup come from job/quote metadata only (no hardcoded names). Every money value goes through `money_round` (half-up).

## What Max produces now

`draft_estimate_and_presentation` → `draft_packet`:

- Re-line → Header-B portrait estimate
- New-fab → `client_simple` (default client) + detailed `client` + `internal`

`generate_quote_pdf` defaults to `client_simple` when the quote is tagged Willard.

The simple client sheet is one short line per area plus its client price, an Includes line, “Fabric provided by client”, then grand total / deposit / balance. No qty, rates, widths, yardage, or group subtotals.

Mock opening (invented names, same dimensions as the format fixture):

- Wall 249 5/16" · finished length 93 5/16"
- Sheers 189 3/8"
- New fabrication: 2.5× fullness, 54" main goods, 110" sheer goods

## Structure (new-fab)

| Area | Group | Item | Qty | Base |
|---|---|---|---|---|
| A. MAIN DRAPERY | Labor | Drapes | 12 widths | $1,140.00 |
| | Materials | Fabric | 37 yd | COM |
| | Materials | Lining | 37 yd | $388.50 |
| | Materials | Track | 21 ft | $853.13 |
| | Materials | Batons | 2 | $50.30 |
| | Materials | Hem | 1 | COM |
| | Installation | Install | 21 ft | $643.13 |
| B. SHEERS | Labor | Sheers | 5 widths | $475.00 |
| | Materials | Fabric | 15 yd | COM |
| | Materials | Track | 16 ft | $650.00 |
| | Materials | Batons | 2 | $50.30 |
| | Installation | Install | 16 ft | $490.00 |

No hourly line. Carriers are included in the complete track. Client column is base × 1.20. Internal adds RATE / AMOUNT / MARKUP 20% / TOTAL and MARKUP 20% (DESIGNER).

## Totals

| | Amount |
|---|---|
| Base | $4,740.36 |
| Client (+20%) | $5,688.43 |
| Designer share | $948.07 |

Half-up cents: `21 × $40.625 = $853.125 → $853.13`, `21 × $30.625 = $643.125 → $643.13`.

## PDF overlap fixes

- GRAND TOTAL sits on its own row below the A. MAIN DRAPERY / B. SHEERS rollup (no collision with the B. SHEERS summary value).
- Footer status is `PRELIMINARY` so it does not run into the left address line.

## Artifacts

- `reports/proof/willard-revc-mock/EST-MOCK-WILLARD-client-simple.pdf` (default client)
- `reports/proof/willard-revc-mock/client-simple-1.png`
- `reports/proof/willard-revc-mock/EST-MOCK-WILLARD-client.pdf` (detailed)
- `reports/proof/willard-revc-mock/client-1.png`
- `reports/proof/willard-revc-mock/EST-MOCK-WILLARD-internal.pdf`
- `reports/proof/willard-revc-mock/internal-1.png`

## Tests

```
PYTHONPATH=backend python3 -m pytest backend/tests/test_rafael_estimate_format.py backend/tests/test_workroom_packet.py -q
# 23 passed
```
