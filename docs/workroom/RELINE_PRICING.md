# Drapery re-line pricing (Empire Workroom)

Source of truth for the numbers: `backend/app/services/pricing/workroom_rules.py` (`DEFAULT_RULES`),
editable in Pricing Studio (`GET/POST /api/v1/pricing/workroom/rules`). Line items are built by
`backend/app/services/estimates/workroom_packet.py` (`price_opening`), which Max calls through the
`draft_estimate_and_presentation` tool.

## Material sell rates (Rafael, 10/4/2026)

| Material | Rule key | Sell rate |
|---|---|---|
| Lining | `lining_per_yard` | **$10.50 / yd** |
| Napped lining / interlining (bump) | `bump_per_yard` | **$12.50 / yd** |

Always use the workroom's own sell rates. **Never use supplier list prices** for materials: supplier
lists exclude freight. The same rates are used by the catalog engine (`PRICING_SPECS["drapery"]["linings"]`:
`regular` / `batiste_118` $10.50, `interlining` / `napped_interlining` $12.50), the legacy quote engine
(`pricing_tables.LINING`, `pricing_engine`) and Max's quick estimate (`LINING_RATES`). Blackout, thermal and
premiere satin rates are unchanged. Existing quotes keep the prices they were sent with; only new drafts
use these rates.

## Width count (same for every re-line option)

    (window width x 2 + 11.5") / panels / 48"  -> rounded up to the next half width, per panel

i.e. per 48" finished panel width at 100% fullness. Example: 160" window, 2 panels =
331.5" / 2 / 48 = 3.45 -> 3.5 widths per panel = 7 widths.

## Options

| Option (wording on the estimate) | Labor rule | Labor | Materials |
|---|---|---|---|
| **Re-line with lining and bump** (default) | `reline_per_width` | $150 / width | Lining yd x $10.50 + Bump (napped interlining) yd x $12.50 |
| **Re-line with lining (no bump)** | `reline_no_bump_per_width` | $125 / width | Lining yd x $10.50 only, no bump material |

Lining yards = widths x (finished length + 16" hem allowance) / 36, to 0.1 yd.

The no-bump option was added from Rafael on 10/4/2026 (via Empire Workroom). For the 7-width
example it is 7 x $125 = $875 labor instead of $1,050, and the bump line drops off.

## How Max picks it

Per opening, pass `"bump": false` (or `"reline_type": "no_bump"` / `"lining_only"`). Leaving it out
keeps the standard re-line with bump. Use the no-bump option only when the founder or client asks
for it. Existing quotes are never repriced by this change; only new drafts use the option.
