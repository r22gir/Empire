# Willard / REV C mock proof (2026-10-23)

Format reference only. Not a live job. No real client data.

## What Max produces now

`draft_estimate_and_presentation` → `draft_packet` → `render_willard_pair`
(client + internal). The same renderer is `generate_quote_pdf` /
`_generate_pdf_for_quote` when the quote is tagged Willard.

Mock opening (invented names, REV C generator dimensions):

- Wall 249 5/16" · finished length 93 5/16"
- Sheers 189 3/8"
- New fabrication: 2.5× fullness, 54" main goods, 110" sheer goods

## Structure (matches the REV C generator)

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

No hourly "track re-center" line. Carriers are included in the complete
track. Client column is base × 1.20. Internal adds RATE / AMOUNT / MARKUP
20% / TOTAL and MARKUP 20% (DESIGNER).

## Totals

| | Amount |
|---|---|
| Base | $4,740.36 |
| Client (+20%) | $5,688.43 |
| Designer share | $948.07 |

The attached REV C draft JSON summed to $4,740.35 / $5,688.42 because
`21 × $40.625 = $853.125` was stored as $853.12 while
`21 × $30.625 = $643.125` was stored as $643.13. Max uses consistent
half-up cents ($853.13 + $643.13). Designer share is the same $948.07.

## Artifacts

- `reports/proof/willard-revc-mock/EST-MOCK-WILLARD-client.pdf`
- `reports/proof/willard-revc-mock/EST-MOCK-WILLARD-internal.pdf`
- `reports/proof/willard-revc-mock/client-1.png`
- `reports/proof/willard-revc-mock/internal-1.png`

## Tests

```
PYTHONPATH=backend python -m pytest backend/tests/test_rafael_estimate_format.py backend/tests/test_workroom_packet.py -q
# 19 passed
```
