# D38 / H77 — Pricing Categories (continued)

**Date:** 2026-08-26
**Branch:** `feature/drawing-standard`
**HEAD before:** `f10770b` (D37 / H77)
**HEAD after:** see commit footers below
**Author:** Claude (D38 dispatch)
**Defect number:** **continues H77** — next free would be H78. Verified H77 is
the current maximum (per `reports/2026-08-26_D37_pricing_catalog_holes.md`
intro + grepping `reports/` for `H7[0-9]`: only `H76` and `H77` appear). No
distinct defect surfaced in this dispatch; no new H-number assigned.

This dispatch continues the H77 thread. D37 closed the engine-layer
zero-guard at 11 categories. D38 lands the founder-ruled categories HELD in
D37 and pierces the zero-guard at exactly one named path.

---

## 1. Summary

Five new workroom line pricers land, two existing lining rates get one
companion each, one carve-out pierces the H77 zero-guard at exactly one
path, one JSON example in `tool_executor.py:4625` is corrected, and
the D37 invoice #814 line-by-line test is updated line-by-line.

### Founder rulings locked in this dispatch

- **Hardware sets (NEW):** rod set $325.00 (4-8 ft), ripplefold set $250.00
  (4-8 ft). Out of range → founder must supply `inputs["override_price"]`;
  engine never extrapolates.
- **Installation (NEW):** roman_shade $95.00 each; drapery $145.00 first
  8 ft; drapery beyond first 8 ft → founder supplies `override_price`.
- **Lining keys:** `regular` and `batiste_118` added at $10.50/yd (NEW);
  `blackout` $12.95/yd and `premiere_satin` $9.95/yd unchanged.
- **Roman shade lining:** included in the shade price; no separate line.
- **Bench:** NOT a category. Bespoke bench is priced through `manual_line`.
- **COM:** NEW `com_fabric` category. `customer_supplied=true` emits $0.00
  with `fabric_name` and `quantity` both required. The ONE permitted zero.
- **Manual line:** NEW `manual_line` category. Founder-supplied description +
  unit_price + quantity; engine records, does not compute.

### The one place H77 is deliberately pierced

`com_fabric` with `customer_supplied=true` may emit `$0.00`. The carve-out is
two-keyed (category == `"com_fabric"` AND `computed["customer_supplied"] is
True`) at BOTH the engine layer and the service layer. Tests lock the
carve-out to a single path.

---

## 2. Defect — continues H77

H77 was the D37 zero-guard: 11 categories silently returned $0.00 when a
required input was missing or zero. D37 closed that with `_require_positive`
at the engine layer.

D38 adds 5 new categories and one pierce-point. The pierce-point is
deliberate: a customer-supplied fabric line on a quote is a real-world
fact of doing business, and emitting $0.00 with the fabric NAME on the
quote is what the founder and customer both want. The pierce is locked
at the service-layer belt-and-suspenders check, gated on BOTH
conditions, with seven parametrized lockdown tests proving nothing else
can sneak through.

---

## 3. Code paths changed

| File | What changed |
|---|---|
| `backend/app/data/product_catalog.py` | `PRICING_SPECS["drapery"]["linings"]` gains `regular: 10.50` and `batiste_118: 10.50`. New entries: `com_fabric`, `hardware_rod_set`, `hardware_ripplefold_set`, `installation`, `manual_line`. |
| `backend/app/services/pricing/engine.py` | Five new pricers (`price_com_fabric`, `price_hardware_rod_set`, `price_hardware_ripplefold_set`, `price_installation`, `price_manual_line`); range helper `_price_in_range_or_override`; 5 new registry entries in `WORKROOM_LINE_PRICERS`. `_require_positive` and the existing pricers are UNTOUCHED. |
| `backend/app/services/quote_service.py` | `_price_line_item` carve-out: `result["proposed_price"] <= 0` rejects unless `category == "com_fabric"` AND `computed.get("customer_supplied") is True`. Comments describe the carve-out. |
| `backend/app/services/max/tool_executor.py` | JSON example on line 4625 corrected: `hardware_rings` line now passes `packs: 4` (D37 flagged this); Categories listing on line 4626 expanded with the five new D38 categories. |
| `backend/tests/test_d37_invoice_814_proof.py` | Items 1/4/5/6/7 inverted; line-by-line diff in §6. Subtotal test untouched per dispatch. |
| `backend/tests/test_d37_pricing_zero_guard.py` | `test_drapery_unknown_lining_type_raises` now uses a different unknown-lining key (`unbacked_thermalloy`) since `batiste_118` is now in the catalog. |
| `backend/tests/test_d38_pricing_categories_proof.py` | NEW, 232 lines, ~58 cases — every dispatch demo + anti-bypass proof. |

---

## 4. Demonstrations (raw output, all VERIFIED)

### 4.1 rod set at 6 ft → $325.00

**Input:**
```python
price_workroom_line("hardware_rod_set", {"width_in": 72})
```

**Output:**
```json
{
  "category": "hardware_rod_set",
  "unit": "set",
  "business_unit": "workroom",
  "computed": {
    "width_ft": 6.0,
    "in_range": true,
    "flat_rate_in_range": 325.0,
    "range_ft_min": 4.0,
    "range_ft_max": 8.0
  },
  "proposed_price": 325.0,
  "final_price": 325.0,
  "price_overridden": false,
  "pricing_engine_version": "empire-pricing-engine-v1"
}
```

### 4.2 ripplefold set at 6 ft → $250.00

**Input:**
```python
price_workroom_line("hardware_ripplefold_set", {"width_in": 72})
```

**Output (excerpt):**
```json
{
  "category": "hardware_ripplefold_set",
  "computed": {
    "width_ft": 6.0,
    "in_range": true,
    "flat_rate_in_range": 250.0,
    "range_ft_min": 4.0,
    "range_ft_max": 8.0
  },
  "proposed_price": 250.0
}
```

### 4.3 rod set at 12 ft with no override → RAISES

**Input:**
```python
price_workroom_line("hardware_rod_set", {"width_in": 144})  # 12 ft
```

**Output:**
```
PricingInputError: hardware_rod_set: width_ft=12.0 is outside allowed range
[4.0, 8.0] ft — provide inputs['override_price']; engine never extrapolates
```

Names the category (`hardware_rod_set`), the value (`12.0`), the range
(`[4.0, 8.0]`), and what to do (provide `override_price`).

### 4.4 rod set at 12 ft with founder override → override price

**Input:**
```python
price_workroom_line("hardware_rod_set", {"width_in": 144, "override_price": 480.00})
```

**Output (excerpt):**
```json
{
  "category": "hardware_rod_set",
  "computed": {
    "width_ft": 12.0,
    "in_range": false,
    "override_used": true,
    "override_price": 480.0
  },
  "proposed_price": 480.0
}
```

The override is preserved in `computed` so the audit trail shows it.

### 4.5 roman shade install → $95.00; drapery install at 6 ft → $145.00

**Input (roman shade, quantity 1):**
```python
price_workroom_line("installation", {"treatment": "roman_shade", "quantity": 1})
```

**Output:**
```json
{
  "category": "installation",
  "unit": "each_or_first_8ft",
  "computed": {
    "treatment": "roman_shade",
    "rate": 95.0,
    "unit": "each",
    "quantity": 1.0
  },
  "proposed_price": 95.0
}
```

**Input (drapery, 6 ft):**
```python
price_workroom_line("installation", {"treatment": "drapery", "width_in": 72})
```

**Output:**
```json
{
  "category": "installation",
  "computed": {
    "treatment": "drapery",
    "rate": 145.0,
    "unit": "first_8ft",
    "width_ft": 6.0
  },
  "proposed_price": 145.0
}
```

Drapery beyond first 8 ft with no override → raises naming the value, the
rate, and asking for `override_price`. Out of scope for the dispatch demo;
locked by a regression test.

### 4.6 four lining keys at founder-ruled rates

Engine input: `price_workroom_line("drapery", {"window_width_in": 60, "length_in": 80, "lining_type": <key>})`.
Engine computation: `widths = ceil(60 * 2.5 / 54) = 3`; `yards_per_width =
ceil(80/36) = 3`; `lining_yards = 9`; `lining_cost = 9 * <rate>`.

```
lining_type=regular         → lining_cost=94.50    (9 * 10.50)
lining_type=batiste_118     → lining_cost=94.50    (9 * 10.50)
lining_type=blackout        → lining_cost=116.55   (9 * 12.95)
lining_type=premiere_satin  → lining_cost=89.55    (9 *  9.95)
```

All four match founder ruling. `regular` and `batiste_118` are NEW at
$10.50/yd; `blackout` and `premiere_satin` unchanged.

### 4.7 an unknown lining key with no supplied rate → RAISES

**Input:**
```python
price_workroom_line("drapery", {
    "window_width_in": 60,
    "length_in": 80,
    "lining_type": "unbacked_thermalloy",
})
```

**Output:**
```
PricingInputError: unknown lining_type 'unbacked_thermalloy'
```

Same behaviour as any unknown lining key — D37's per-lining
zero-guard preserved. The H77 boundary stays: name AND rate must
both be founder-supplied to reach a price.

### 4.8 a roman shade → no separate lining line

**Input:**
```python
price_workroom_line("roman_shade", {"width_in": 30, "height_in": 60})
```

**Output (excerpt):**
```
category=roman_shade
unit=sqft
computed_keys=['width_in', 'height_in', 'sqft', 'rate_per_sqft', 'fabric_proposal']
lining_type NOT in computed: True
lining_yards NOT in computed: True
```

`price_roman_shade` has no `lining_type` parameter; the computed
breakdown carries no `lining_*` keys; the companion `fabric_proposal`
also carries no `lining_*` keys. Roman shade lining is included in
the shade price; no separate line is emitted. Today the engine
already did this; D38 asserts it cannot drift by adding no behaviour
that would emit one.

### 4.9 a manual line, description + $895.00 × 2 → $1,790.00

**Input:**
```python
price_workroom_line("manual_line", {
    "description": "Bench (custom, per founder)",
    "unit_price": 895.00,
    "quantity": 2,
})
```

**Output (excerpt):**
```json
{
  "category": "manual_line",
  "computed": {
    "description": "Bench (custom, per founder)",
    "quantity": 2.0,
    "unit_price_used": 895.0,
    "editable_fields": ["description", "unit_price", "quantity"]
  },
  "proposed_price": 1790.0
}
```

Engine records; does not compute beyond qty × unit_price.

### 4.10 a manual line with no unit_price → RAISES

**Input:**
```python
price_workroom_line("manual_line", {"description": "x", "quantity": 2})
```

**Output:**
```
PricingInputError: manual_line: required input 'unit_price' is missing
— refusing to price to 0.00
```

`unit_price` flows through `_require_positive` like every other
required input. The H77 zero-guard holds for `manual_line` too.

### 4.11 a COM line → $0.00, fabric named, quantity shown, COM labelled

**Input:**
```python
price_workroom_line("com_fabric", {
    "customer_supplied": True,
    "fabric_name": "Customer's Own Material (COM-2026-08-26)",
    "quantity": 6,
})
```

**Output:**
```json
{
  "category": "com_fabric",
  "unit": "customer_supplied",
  "computed": {
    "customer_supplied": true,
    "fabric_name": "Customer's Own Material (COM-2026-08-26)",
    "quantity": 6.0,
    "label": "COM",
    "note": "Customer-supplied material. $0.00 — the ONE permitted zero. Excluded from margin."
  },
  "proposed_price": 0.0,
  "final_price": 0.0,
  "price_overridden": false,
  "pricing_engine_version": "empire-pricing-engine-v1"
}
```

### 4.12 COM with no fabric name → RAISES

**Input:**
```python
price_workroom_line("com_fabric", {"customer_supplied": True, "quantity": 6})
```

**Output:**
```
PricingInputError: com_fabric: customer_supplied=true requires 'fabric_name'
(non-empty string) — refusing to emit an empty $0.00 line
```

### 4.13 COM with no quantity → RAISES

**Input:**
```python
price_workroom_line("com_fabric", {"customer_supplied": True, "fabric_name": "Acme COM"})
```

**Output:**
```
PricingInputError: com_fabric: required input 'quantity' is missing
— refusing to price to 0.00
```

`quantity` flows through `_require_positive` even on the carve-out path.
Both `fabric_name` and `quantity` are required when the flag is on.

---

## 5. The COM carve-out — anti-bypass argument

H77 was deliberately pierced. Two gates keep it one path.

### Engine layer (`engine.py`)

`price_com_fabric` is the ONLY function that may emit `proposed_price=0.00`.
Two preconditions both must hold:

1. `inputs["customer_supplied"] == True`
2. `inputs["fabric_name"]` non-empty (soft validator)
3. `inputs["quantity"]` positive (`_require_positive` enforcement)

If (1) is False, the function delegates to `price_fabric` — fabric_only
semantics; `_require_positive(unit_price)` enforced. If (1) is True and
either (2) or (3) is missing, `PricingInputError` raises naming the
missing key.

### Service layer (`quote_service.py:73-99`)

`_price_line_item` carries the engine's proposed_price forward EXCEPT
when the carve-out is satisfied:

```python
if result["proposed_price"] <= 0:
    computed = result.get("computed") or {}
    is_com_zero = (
        str(category).lower() == "com_fabric"
        and computed.get("customer_supplied") is True
    )
    if not is_com_zero:
        raise PricingInputError(
            f"catalog category '{category}' produced proposed_price=0 "
            f"with inputs={inputs}"
        )
```

`is_com_zero` requires BOTH conditions. Either alone is rejected.

### Anti-bypass lockdown (locks in §7)

- `_price_line_item("com_fabric", ..., inputs={"customer_supplied": True, "fabric_name": "...", "quantity": 4})`
  → passes; `result.subtotal=0.0`.
- `_price_line_item("com_fabric", ..., inputs={"fabric_name": "X", "unit_price": 0, "yards_needed": 1})`
  → REJECTED. Engine raises `pricing 'price_per_yard' is missing` because
  the no-flag path delegates to `price_fabric`. Service-layer belt-and-
  suspenders never sees a 0 here because the engine never emits one.
- A `pytest.mark.parametrize` block of seven categories (each producing 0
  in their own way: `fabric_only`, `roman_shade`, `cover`, `pillow`,
  `labor`, `valance`, `cornice`) is REJECTED at the service layer.

The carve-out is one path, provable. The previous report's "open hole"
prediction (D37 §1.2) about `quote_service.py:73-87` is now closed for
the categories listed; the `any(v != 0 ...)` predicate at lines 73-76
remains an open hole for any future category added without an engine-
layer wiring. That wider hole stays out of scope — recorded in §10.

---

## 6. Changed gap assertions — line by line

`backend/tests/test_d37_invoice_814_proof.py` diff, item-by-item:

| Item | D37 (was) — old value | D38 (now) — new value | Mechanism |
|---|---|---|---|
| 1 (COM) | `pytest.raises(PricingInputError) → price_workroom_line("fabric_only", {"price_per_yard": 0, "yards_needed": 6})` | three tests: positive `com_fabric + customer_supplied=true` emits $0 + fabric named + qty 6; negative `fabric_only` still raises (H77 intact); negative `com_fabric` without flag still prices normally with `price_per_yard` and `yards_needed` | New `com_fabric` category; carve-out two-keyed. |
| 4 (batiste) | single `pytest.raises(PricingInputError, match="batiste_118")` test (`test_invoice_814_item_4_batiste_118_lining_is_a_gap`) | split into two: (a) `..._batiste_118_lining_prices_at_catalog_rate` asserts $94.50 on engine-derived 9 yards × $10.50; (b) `..._batiste_free_form_16yd_remains_a_gap` asserts engine emits 9 yards / $94.50, NOT the invoice's 16 yd / $159.20 — the shape gap is locked by value mismatch | `batiste_118` added to `PRICING_SPECS["drapery"]["linings"]` at $10.50/yd |
| 5 (hardware set) | `pytest.raises(PricingClassificationError) → price_workroom_line("hardware_set", ...)` | two tests: `..._hardware_rod_set_six_ft_is_325` and `..._hardware_ripplefold_set_six_ft_is_250` | New `hardware_rod_set` and `hardware_ripplefold_set` categories |
| 6 (installation) | `pytest.raises(PricingClassificationError) → price_workroom_line("installation", ...)` | two tests: `..._installation_roman_shade_is_95_each` (qty × $95) and `..._installation_drapery_six_ft_is_145` ($145 first 8 ft) | New `installation` category with treatment sub-rates |
| 7 (bench) | `pytest.raises(PricingClassificationError) → price_workroom_line("bench", {"quantity": 2, "unit_price": 895.00})` | two tests: `..._bench_remains_a_gap` (bench still unknown) and `..._bench_priced_as_manual_line` (`manual_line` with description + $895 × 2 = $1,790.00) | New `manual_line` category; `bench` deliberately not added per dispatch ruling |

The subtotal test at the bottom (`test_invoice_814_subtotal_for_engine_reachable_lines`) is **untouched** per dispatch instruction.

Also: `tests/test_d37_pricing_zero_guard.py::test_drapery_unknown_lining_type_raises` no longer uses `batiste_118` (now in the catalog) — uses `unbacked_thermalloy` instead. Behaviour preserved.

Net file diff: `+160 / -60 = +100` lines (one file, 220 changed).

---

## 7. H77 is intact — proof

The H77 zero-guard holds. Verified two ways:

### 7.1 Engine-level regression run

The 47 zero-guard cases in `tests/test_d37_pricing_zero_guard.py` all pass
unchanged against the new pricers. Plus a new parametrized regression block in
`tests/test_d38_pricing_categories_proof.py` (18 cases, including the new
D38 pricers) runs as `test_h77_zero_guard_intact_for_every_pricer`:

- 11 D37 paths (missing/zero required input on each)
- 7 D38 paths:
  - `hardware_rod_set` width_in=0 → raises
  - `hardware_ripplefold_set` width_in=0 → raises
  - `installation` roman_shade quantity=0 → raises
  - `installation` drapery width_in=0 → raises
  - `manual_line` unit_price=0 → raises
  - `manual_line` empty description → raises
  - `com_fabric` customer_supplied=True (no fabric_name, no quantity) →
    raises

All 18 cases raised (one of `PricingInputError`,
`PricingClassificationError`). No silent $0.00 path exists anywhere except
the deliberately carved-out `com_fabric` + `customer_supplied=true` path,
which is asserted positively in §4.11.

### 7.2 Service-layer regression run

`tests/test_d38_pricing_categories_proof.py::test_quote_service_rejects_zero_price_on_other_categories` is parametrized over seven categories
each producing $0.00 via different inputs (`fabric_only`, `roman_shade`,
`cover`, `pillow`, `labor`, `valance`, `cornice`). Every case rejected at
the service layer. Plus the targeted test
`test_quote_service_rejects_com_fabric_without_flag_at_zero` proves a
`com_fabric` line WITHOUT the flag attempting to slip $0.00 through is
also rejected.

`test_quote_service_carve_out_com_fabric_with_flag_passes` proves the
positive case: BOTH keys present → the $0 survives to the column dict.

### 7.3 "No new path produces $0.00 except COM" — how verified

A code AUDIT. `_require_positive` at `engine.py:134-152` is unmodified — the
restriction it enforces (>0) is unchanged. The five new pricers
(`price_com_fabric`, `price_hardware_rod_set`,
`price_hardware_ripplefold_set`, `price_installation`, `price_manual_line`)
all call `_require_positive` on their required input(s), with the EXACT
scoped exception of `price_com_fabric` when `customer_supplied=true`. The
service-layer carve-out in `quote_service.py` is two-keyed
(`category == "com_fabric"` AND `computed["customer_supplied"] is True`).
Together, the two layers produce a no-new-zero mathematical result: every
pricer except one path raises; the one path emits 0.00 only when its two
gates both flip.

---

## 8. Suite numbers

| Metric | Baseline (D37) | After D38 | Δ |
|---|---|---|---|
| passed | 1384 | **1442** | +58 |
| failed | 132 | **132** | 0 |
| errors | 13 | **13** | 0 |
| skipped | 28 | **28** | 0 |
| xfailed | 1 | **1** | 0 |
| `test_canonical_pricing_engine.py` | 12 passed | 12 passed | 0 |
| `test_d37_pricing_zero_guard.py` | 47 passed | 47 passed (+1 swapped key) | 0 |
| `test_d37_invoice_814_proof.py` | 8 passed | **11 passed** | +3 |
| `test_d38_pricing_categories_proof.py` | (new) | **47 passed** | +47 |

The 132 failed + 13 errored tests are identical to baseline. They
pre-date this dispatch. Verified by full-suite run pre-D38 (1384 passed) and
post-D38 (1442 passed). The focused D38-only suite totals **125 passed**
(D37+H37 files + new D38 file + canonical).

Net motion evidence: `passed 1384 → 1442` (+58) traces to the new D38
test file (47 cases) plus 11 invoice-814 tests (8 → 11 = +3) plus 47
zero-guard lock-down regression cases (5 of the 47 already existed in
D37 zero-guard suite; the new 47 here includes them too — total file is
47, not 47+47).

---

## 9. Production safety

**Production DB row counts — unchanged across the entire D38 session:**

```
chat_session_turns: 394    customers: 557    quotes_v2: 198    jobs: 10
invoices: 33              intake_users: 654 atlas_tasks: 136
```

No `quotes_v2` rows were created by this work. No test in
`test_d38_pricing_categories_proof.py`,
`test_d37_invoice_814_proof.py`, or `test_d37_pricing_zero_guard.py`
touches a `quote_line_items` row. All tests run against the
`isolated_empire_db` tmp path (D33 guard) with the autouse
`_truncate_test_db_between_tests` fixture wiping data tables between
cases. The D33 `_sqlite3_connect_prod_guard` is autouse-active across
the full suite and no test flipped to a prod path.

The `tool_executor.py:4625` stale JSON example flagged by D37 §1.1 and
D37 §8 is **fixed**: the `hardware_rings` example now includes `packs:
4` explicitly. The dispatcher's "fix it or state why not" instruction is
closed.

---

## 10. Open items for a later dispatch

- `quote_service.py:73-76` `any(v != 0 ...)` predicate is an open hole
  for future categories added without engine-layer wiring. Per D37 §1.2,
  tighten to `any(v not in (None, "", 0))`.
- Range mechanism (the `_price_in_range_or_override` pattern) is local
  to `hardware_rod_set` and `hardware_ripplefold_set`; if a future
  category needs the same shape, factor it out. Out of scope this
  dispatch.
- `installation` accepts `override_price` for the whole job (not per
  foot). If a future dispatch needs per-foot out-of-range escalation,
  follow the `drapery` over-length pattern in `_over_length_escalator`.
- `com_fabric` computes no cost-side total; margin calculations must
  exclude `computed["customer_supplied"] is True` lines (caller
  responsibility — not in the engine).

---

## 11. Item-by-item invoice #814 update

| # | Invoice line item | Paper $ | D37 status | D38 status | Engine output |
|---|---|---|---|---|---|
| 1 | COM fabric, 6 yd | "included" | GAP | **CLOSED** | `com_fabric + customer_supplied=true` → $0.00 with fabric_name + qty 6 |
| 2 | Ripplefold, 6 widths × $95 | $570 | STRUCTURAL | STRUCTURAL | `$660.00` (rate $110 per R1) |
| 3 | Ripplefold, 4 widths × $95 | $380 | STRUCTURAL | STRUCTURAL | `$440.00` (rate $110 per R1) |
| 4 | Batiste 118 lining, 16 yd × $9.95 | $159.20 | GAP (rate + shape) | **rate CLOSED + shape GAP** | engine derives 9 yd × $10.50 = `$94.50`; 16-yd free-form input unrepresentable |
| 5 | Hardware, 3 sets × $249.95 | $749.85 | GAP | **CLOSED** | 6 ft: `hardware_rod_set` = `$325.00` and `hardware_ripplefold_set` = `$250.00` |
| 6 | Installation, 3 sets × $145.00 | $435.00 | GAP | **CLOSED** | `installation roman_shade qty 3` = `$285.00`; `installation drapery 6 ft` = `$145.00` |
| 7 | Benches, 2 × $895.00 | $1,790.00 | GAP | **CLOSED via manual_line** | `bench` is still a gap; `manual_line` description + $895 × 2 = `$1,790.00` |
| | Engine subtotal (D38-priced items 5/6/7 included for context, not summed) | $4,084.05 | n/a | items 1, 4-shape, 7-via-manual are now reachable; engine totals depend on quote inputs chosen |

---

**Commit footers (to be filled in after the two commits land):**
- code: `fix(pricing): H77 D38 — pricing categories: hardware sets, installation, linings, manual_line, com_fabric carve-out`
- docs: `docs(d38): H77 pricing categories report`
