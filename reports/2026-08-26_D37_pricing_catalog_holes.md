# D37 / H77 — Pricing Catalog Holes (Engine Zero-Guard)

**Date:** 2026-08-26
**Branch:** `feature/drawing-standard`
**HEAD before:** `c452fa2` (D36 H76)
**HEAD after:** see commit footers below
**Author:** Claude (D37 dispatch)
**Defect number:** **H77** — next free after H76 (D36)

---

## 1. Summary

The pricing engine (`backend/app/services/pricing/engine.py`) had a defect class
shared with H76: certain workroom line pricers silently returned `$0.00` when a
required input was missing or zero. The output flowed downstream as a
"customer-facing price" the business could be held to. Eleven pricers were
affected.

D37 closes the defect at the engine layer with a new helper
(`_require_positive`) that refuses to price a category when a required input is
absent, zero, or non-numeric. The error names the category and the offending
key, so the founder sees what's missing without guessing. The fix is locked in
by 47 new tests in `tests/test_d37_pricing_zero_guard.py` and exercised against
invoice #814 in `tests/test_d37_invoice_814_proof.py`.

Two notes the founder flagged for the report, no code change needed:

1. **`hardware_rings.packs` is now required.** Under the old default
   (`packs = widths`), `{"widths": 4}` would price 4 packs at $35 each
   ($140). Under the new rule, the same payload raises. **Three prod
   `quote_line_items` rows have `category='hardware_rings'`: all three
   supply `packs` explicitly** (4, 120, 4). No prod row relied on the
   default. **One code artifact relies on the default:**
   `backend/app/services/max/tool_executor.py:4625` carries a JSON
   example for the `create_engine_quote` tool:
   `{"category": "hardware_rings", "inputs": {"widths": 4}}`. That
   example would now raise. **This is an interface change** — recorded
   as such, not a bug. Future calls must supply `packs` explicitly.
2. **`quote_service.py:83-87` left unchanged.** The engine now raises
   first for the eleven named categories, so the caller-side hole is
   unreachable through them. But the caller's `any(v != 0 ...)` check
   still passes a supplied-but-zero input for anything the engine does
   not cover (e.g. any future category added without a `_require_positive`
   wiring). The `proposed_price <= 0` belt-and-suspenders at line 83
   catches the actual zero result in that case, but the first-pass check
   is incomplete. **Recorded as an open hole, not as closed.** A future
   dispatch should tighten that `any()` to `any(v not in (None, "", 0))`
   or equivalent.

---

## 2. Defect: H77 — silent $0.00 from workroom line pricers

### 2.1 Affected pricers (eleven)

Each of the following returned `$0.00` silently when its required input(s)
were missing or zero. (The `price_fabric` companion for roman shades was
included as `fabric_only`.)

| Pricer | Required input(s) | Old silent-zero path |
|---|---|---|
| `price_roman_shade`     | `width_in`, `height_in`          | `_positive` defaulted both to 0 → sqft=0 → proposed=0 |
| `price_fabric` (fabric_only) | `price_per_yard`, `yards_needed` | both defaulted to 0 → 0×0=0 |
| `price_cover`           | `unit_price`                      | `unit_price` defaulted to 0 → qty×0=0 |
| `price_valance`         | `width_in`                        | width defaulted to 0 → lineal_ft=0 |
| `price_cornice`         | `width_in`                        | same |
| `price_labor`           | `hours`                           | hours defaulted to 0 |
| `price_pillow`          | `unit_price`                      | defaulted to 0 → qty×0=0 |
| `price_hardware_rod`    | `width_in`                        | width defaulted to 0 |
| `price_hardware_ripplefold_track` | `width_in`             | same |
| `price_hardware_rings`  | `packs`                           | defaulted to `widths` (interface change — see §1) |
| `price_hardware_brackets` | `width_in` OR explicit `count`  | either-or rule; either path raises |

### 2.2 Fix — `_require_positive`

```python
def _require_positive(inputs: dict[str, Any], key: str, *, category: str) -> float:
    raw = inputs.get(key)
    if raw is None or raw == "":
        raise PricingInputError(
            f"{category}: required input '{key}' is missing — refusing to price to 0.00"
        )
    try:
        value = float(raw)
    except (TypeError, ValueError):
        raise PricingInputError(
            f"{category}: required input '{key}' must be numeric (got {raw!r})"
        )
    if value <= 0:
        raise PricingInputError(
            f"{category}: required input '{key}' must be > 0 (got {value}) — refusing to price to 0.00"
        )
    return value
```

Each affected pricer was rewritten to call this helper for its required input(s).
A D37/H77 comment block sits at each call site.

### 2.3 Demonstrated raises

Direct invocation (verbatim from the dev console):

```
roman_shade (no inputs)           : roman_shade: required input 'width_in' is missing — refusing to price to 0.00
roman_shade (zero dims)           : roman_shade: required input 'width_in' must be > 0 (got 0.0) — refusing to price to 0.00
fabric_only (no inputs)           : fabric_only: required input 'price_per_yard' is missing — refusing to price to 0.00
fabric_only (zero rate)           : fabric_only: required input 'price_per_yard' must be > 0 (got 0.0) — refusing to price to 0.00
cover (no unit_price)             : cover: required input 'unit_price' is missing — refusing to price to 0.00
cover (zero unit_price)           : cover: required input 'unit_price' must be > 0 (got 0.0) — refusing to price to 0.00
valance (no width_in)             : valance: required input 'width_in' is missing — refusing to price to 0.00
cornice (no width_in)             : cornice: required input 'width_in' is missing — refusing to price to 0.00
labor (no hours)                  : labor: required input 'hours' is missing — refusing to price to 0.00
pillow (no unit_price)            : pillow: required input 'unit_price' is missing — refusing to price to 0.00
hardware_rod_1_1_8 (no width_in)  : hardware_rod_1_1_8: required input 'width_in' is missing — refusing to price to 0.00
hardware_ripplefold_track         : hardware_ripplefold_track: required input 'width_in' is missing — refusing to price to 0.00
hardware_rings (no packs)         : hardware_rings: required input 'packs' is missing — refusing to price to 0.00
hardware_brackets (no width/count): hardware_brackets: required input 'width_in' is missing — refusing to price to 0.00
drapery (unknown lining)          : unknown lining_type 'batiste_118'
```

Each raise is mirrored by a `pytest.raises` assertion in
`tests/test_d37_pricing_zero_guard.py` (47 parametrized cases).

---

## 3. STEP 1 founder rulings — confirmed in code

| Rule | Result |
|---|---|
| **R1** ripplefold stays $110/width | `engine.py:1118` unchanged. `test_invoice_814_item_2/3` confirms 6 widths × $110 = $660.00 and 4 widths × $110 = $440.00. |
| **R2** regular drapery $95/width | `engine.py:1112` unchanged. |
| **R4** blackout $12.95/yd | `engine.py:1126` unchanged. |
| **R5** premiere_satin $9.95/yd | `engine.py:1127` unchanged. |
| **R10** cover founder-editable, $0 placeholder unreachable | `_require_positive(unit_price, ...)` enforced at engine layer; the `$0.00` placeholder in `PRICING_SPECS["cover"]["base_unit"]` is a UI hint, not a price the engine will ever emit. |
| **R11** fabric_only both inputs required | `_require_positive(price_per_yard, ...)` + `_require_positive(yards_needed, ...)` enforced. |
| **R12** roman_shade companion fabric_only required | Same wiring as `price_fabric` — both inputs required. |
| **R3, R6, R7, R8, R9, R13** HELD | No new categories added. No stubs. No placeholders. The held keys refuse to price. |

---

## 4. STEP 3 — invoice #814 line-by-line

Paper invoice has seven items. Per founder directive, items 2 and 3 are a
structural reference (engine prices ripplefold by width count at the
configured rate — $110/w per R1), and items 1, 4, 5, 6, 7 are gaps with no
category.

| # | Invoice line item | Paper $ | Engine can reach? | Engine output | Status |
|---|---|---|---|---|---|
| 1 | COM fabric, 6 yd (no rate) | "included" | **Cannot.** No `customer_supplied` flag in the engine. The engine has no concept of a free-supplied material line. With zero-guard active, a `fabric_only` line with `price_per_yard=0` raises — desired behaviour, not a defect. | raises `PricingInputError` | **GAP (R13 HELD)** |
| 2 | Ripplefold, 6 widths × $95 | $570.00 | **Yes.** Engine prices by width count. At $110/width (R1 ruling), output is **$660.00**. | `price_workroom_line('drapery', {W=120, L=96, ripplefold, 2.5, 54})` → `proposed_price = 660.0` | **STRUCTURAL MATCH** (legacy $95 → $110 structural-divergence is correct) |
| 3 | Ripplefold, 4 widths × $95 | $380.00 | **Yes.** Engine prices by width count. At $110/width, output is **$440.00**. | `price_workroom_line('drapery', {W=75, L=96, ripplefold, 2.5, 54})` → `proposed_price = 440.0` | **STRUCTURAL MATCH** |
| 4 | Batiste 118" lining, 16 yd × $9.95 | $159.20 | **Cannot.** Two reasons: (a) `batiste_118` is absent from `PRICING_SPECS["drapery"]["linings"]` — drapery engine raises on unknown lining keys (engine.py:651); (b) lining yardage is computed (`widths × ceil(length/36)`), not accepted as a free-form 16-yd input. | raises `PricingInputError("unknown lining_type 'batiste_118'")` | **GAP (R3, R6 HELD)** |
| 5 | Hardware, 3 sets × $249.95 | $749.85 | **Cannot.** No `hardware_set` category. The four `hardware_*` categories compute from window width — none accepts "N sets × $/set". | raises `PricingClassificationError` | **GAP (R7 HELD)** |
| 6 | Installation, 3 sets × $145.00 | $435.00 | **Cannot.** No `installation` line pricer. `install_cost` exists as a sub-component inside `price_workroom_item` only. | raises `PricingClassificationError` | **GAP (R8 HELD)** |
| 7 | Benches, 2 × $895.00 | $1,790.00 | **Cannot.** No `bench` category in `WORKROOM_LINE_PRICERS`. The `upholstery` alias routes through `price_workroom_item`'s composite formula, not a flat $/each. | raises `PricingClassificationError` | **GAP (R9 HELD)** |
| | **Paper subtotal** | **$4,084.05** | n/a | n/a | n/a |
| | **Engine subtotal (items 2 + 3 only)** | n/a | $1,100.00 | `$660.00 + $440.00 = $1,100.00` | Items 1, 4, 5, 6, 7 are gaps — see status column. |

Each gap is locked by an explicit `pytest.raises` assertion in
`tests/test_d37_invoice_814_proof.py` — the test is the assertion that the
gap exists.

---

## 5. Suite delta

| Metric | Baseline (1f) | After STEP 3 | Δ |
|---|---|---|---|
| passed | 1329 | **1384** | +55 (47 zero-guard + 8 invoice proof) |
| failed | 132 | **132** | 0 (same pre-existing failures, unrelated) |
| errors | 13 | **13** | 0 |
| skipped | 28 | **28** | 0 |
| xfailed | 1 | **1** | 0 |
| `test_canonical_pricing_engine.py` | 12 passed | 12 passed | 0 |
| `test_d37_pricing_zero_guard.py` | (new) | 47 passed | +47 |
| `test_d37_invoice_814_proof.py` | (new) | 8 passed | +8 |

The 132 failed and 13 errored tests are identical to baseline — they
pre-date this dispatch and were not touched. Focused D37-only suite:
**67 passed** (`test_canonical_pricing_engine` + `test_d37_pricing_zero_guard` +
`test_d37_invoice_814_proof`).

---

## 6. Production safety

**Production DB row counts — unchanged across the entire D37 session:**

```
chat_session_turns: 394    customers: 557    quotes_v2: 198    jobs: 10
invoices: 33              intake_users: 654 atlas_tasks: 136
```

No `quotes_v2` rows were created by this work. No test in
`test_d37_pricing_zero_guard.py` or `test_d37_invoice_814_proof.py`
touches a `quote_line_items` row. All tests run against the
`isolated_empire_db` tmp path (D33 guard) with the autouse `_truncate_*`
fixture wiping data tables between cases.

---

## 7. Code change set

| File | Δ |
|---|---|
| `backend/app/services/pricing/engine.py` | +44 lines: `_require_positive` helper + 11 pricer rewrites with D37/H77 comment blocks |
| `backend/tests/test_d37_pricing_zero_guard.py` | new file, 232 lines, 47 cases |
| `backend/tests/test_d37_invoice_814_proof.py` | new file, 121 lines, 8 cases |
| `backend/app/services/quote_service.py` | unchanged (hole remains — see §1 note 2) |
| `backend/app/services/max/tool_executor.py:4625` | unchanged — the JSON example still shows `{"widths": 4}` (no packs) for `hardware_rings`. Recorded as a stale doc artifact; future calls must supply `packs` explicitly. |

---

## 8. Open items for a later dispatch

- **R3, R6, R7, R8, R9, R13** held. Add categories only when the founder rules.
- **`quote_service.py:73-76`** open hole for engine-uncovered categories.
  Tighten the `any()` predicate to exclude 0.
- **`tool_executor.py:4625`** stale `hardware_rings` JSON example (no `packs`).
  Update once a follow-up dispatch lands.

---

**Commit footers (to be filled in after the two commits land):**
- code: `fix(pricing): H77 D37 — engine-level zero-guard on 11 workroom line pricers`
- docs: `docs(d37): H77 pricing catalog holes report`
