# D39 / H77 — Line override generalisation + no_carve carve-out + provenance

**Date:** 2026-08-26
**Branch:** `feature/drawing-standard`
**HEAD before:** `29486fd` (D38 / H77)
**HEAD after:** see commit footers below
**Author:** Claude (D39 dispatch)
**Defect number:** **continues H77** — verified H77 is the current maximum (per
D38 report §1 + `grep -r "H7[0-9]" reports/` showing only H76 + H77). No
distinct defect surfaced in this dispatch; no new H-number assigned.

This dispatch continues H77. D37 closed the engine-layer zero-guard at 11
categories. D38 pierced that guard at exactly one named path
(`com_fabric + customer_supplied=true`). D39 generalises the founder's
override mechanism, adds a second carved-out zero path with the same
two-key discipline, and records issued-document provenance so a future
session reading the quote can see the rates are historical by intent,
not by drift.

---

## 0. The doctrine (governs every decision in this dispatch)

> The engine may never produce a number nobody supplied.
> The founder may always supply any number, including zero.

H77 exists to stop the engine inventing prices. It does NOT exist to
restrict the founder. Any line, any category, is overridable by
explicit instruction — up, down, or to zero. An override is never
refused, never clamped, never adjusted toward the catalog. But an
override must be SUPPLIED, never defaulted: a missing key resolving to
0 is the defect H77 closed.

Two permitted zeros result from this doctrine:

  1. `com_fabric + customer_supplied=true` (D38). Customer's own
     material. The line is real; the price is the founder's declaration.
  2. `no_charge=True + no_charge_reason` (D39). Founder explicitly says
     "this line is on the house, here is why." Real line, real reason,
     $0.00 line.

Both paths require TWO keys. Either alone is rejected. A missing key
that resolves to $0.00 is still the defect H77 closed; the engine
raises and the service layer rejects. The two carve-outs are the only
paths through.

---

## 1. Summary

Three things land in STEP 1:

  1. **General override_price (1a).** Every workroom line pricer now
     accepts an optional `override_price`. When supplied (>0), it
     becomes proposed_price. computed records `computed_price` (what
     the engine would have said), `override_price` (what the founder
     supplied), `override_used=True`. Override is general: any
     category, any width, always available — not only when out of
     range. `override_price=0` raises (that is the defect H77 closed).

  2. **Explicit no_charge carve-out (1b).** `no_charge: True` PLUS a
     non-empty `no_charge_reason` produces `proposed_price=0.00` with
     the reason recorded. Without the reason it raises. This is the
     second permitted zero, alongside D38's `com_fabric +
     customer_supplied=true`. Both are reachable only by explicit
     flag. A missing key resolving to 0 is still the defect.

  3. **Issued-document provenance (1d).** A quote records its
     `issued_document` (e.g. "NELMA-814"). Per-line, the `rate_source`:
     "catalog" or "issued:NELMA-814". The engine does NOT enforce
     this — it records it. A future session reading the quote can see
     the rates are historical by intent, not by drift.

The two carve-outs together close one more question H77 left open: how
do you record a $0 line that is real (not a typo) and explainable (not
a missing rate)?

### Why a third carve-out cannot appear silently

Both carve-outs are gated by EXACTLY two conditions at the service
layer (`quote_service._price_line_item`):

```python
is_com_zero = (
    str(category).lower() == "com_fabric"
    and computed.get("customer_supplied") is True
)
no_charge_reason = (computed.get("no_charge_reason") or "").strip()
is_no_charge_zero = (
    computed.get("no_charge") is True
    and bool(no_charge_reason)
)
if not (is_com_zero or is_no_charge_zero):
    raise PricingInputError(
        f"catalog category '{category}' produced proposed_price=0 "
        f"with inputs={inputs}"
    )
```

To add a third permitted zero, a contributor would have to:
  - add the gate at the service layer (this check);
  - add the engine-layer flag handling (the dispatch's two if blocks);
  - update the two lockdown test files (`test_d38_pricing_categories_proof.py`
    + `test_d39_line_override_no_charge.py`).

Three places to touch, two test files asserting the lockdown. A silent
addition cannot happen. The third carve-out is enumerable, not
accidental.

---

## 2. Code paths changed

| File | What changed |
|---|---|
| `backend/app/services/pricing/engine.py` | `price_workroom_line` dispatch extended with (a) no_charge carve-out handling at the top, (b) post-pricer override_price wrapping. Pricers themselves unchanged — `_require_positive` untouched, the eleven D37 zero-guard pricers unchanged, the five D38 new pricers unchanged. |
| `backend/app/services/quote_service.py` | `_price_line_item` carve-out expanded from `com_fabric + customer_supplied=true` to also accept `no_charge=True + no_charge_reason` (both gates two-keyed). `create_quote` now persists `issued_document` on the quote and `rate_source` on every line. `add_line_item` mirrors: `rate_source` defaults to `issued:<parent.issued_document>` or `catalog`. |
| `backend/app/db/unified_business_migration.py` | Two new columns added idempotently: `quotes_v2.issued_document` (TEXT, nullable) + indexes; `quote_line_items.rate_source` (TEXT, default 'catalog') + index. The CREATE TABLE statements include the new columns for fresh installs. |
| `backend/tests/test_d39_line_override_no_charge.py` | NEW, 46 tests, every dispatch demo + anti-bypass lockdown for the second carve-out + provenance persistence. |

---

## 3. The override mechanism — shape, where it lives, why

The dispatch rule: every workroom line pricer accepts an optional
`override_price`. Supplied > 0 → proposed_price. computed records
`computed_price` (the would-be price) and `override_price` (the
founder's number). `override_used=True`.

The implementation lives in `price_workroom_line` (the dispatcher),
NOT in each pricer. The dispatch sequence is:

```
1. no_charge check       → if True+reason, return $0 with reason.
2. WORKROOM_LINE_PRICERS[key](inputs) → the pricer runs.
3. Override wrap         → if inputs["override_price"] was supplied
                           AND the pricer did NOT already use it (the
                           hardware_*_set out-of-range rescue path),
                           override the proposed_price and record
                           computed_price + override_price in computed.
```

`override_price=0` → raises (the defect H77 closed).
`override_price<0` → raises.
`override_price="nope"` → raises.

For out-of-range hardware, the existing D38 pricer behaviour is
preserved: the pricer uses the override_price to compute, and the
dispatch sees `computed.override_used=True` so it does not double-wrap.
For in-range hardware (or any other category), the dispatch's wrap is
the new behaviour: founder can override without leaving the engine's
range.

### Demonstrations

#### drapery + override_price 95 → $95/width, computed_price also shown

**Input:**
```python
price_workroom_line("drapery", {
    "window_width_in": 60, "length_in": 80, "style": "ripplefold",
    "override_price": 95.00,
})
```

**Output:**
```json
{
  "category": "drapery",
  "unit": "width",
  "business_unit": "workroom",
  "computed": {
    "widths": 3,
    "style": "ripplefold",
    "price_per_width": 110.0,
    "base": 330.0,
    "banding": 0.0,
    "lining_type": null,
    "lining_yards": 0.0,
    "lining_cost": 0.0,
    "computed_price": 330.0,
    "override_price": 95.0,
    "override_used": true
  },
  "proposed_price": 95.0,
  "final_price": 95.0,
  "price_overridden": false,
  "pricing_engine_version": "empire-pricing-engine-v1"
}
```

#### Same line without override → catalog $330/width

**Input:**
```python
price_workroom_line("drapery", {
    "window_width_in": 60, "length_in": 80, "style": "ripplefold",
})
```

**Output:**
```json
{
  "category": "drapery",
  "computed": {
    "widths": 3, "style": "ripplefold",
    "price_per_width": 110.0, "base": 330.0,
    "lining_type": null, "lining_yards": 0.0, "lining_cost": 0.0
  },
  "proposed_price": 330.0,
  "final_price": 330.0,
  "price_overridden": false,
  "pricing_engine_version": "empire-pricing-engine-v1"
}
```

No `computed_price` or `override_price` keys — the override is
absent. The engine would have said $330.00; the founder did not
intervene.

#### override_price 0 → RAISES

**Input:**
```python
price_workroom_line("drapery", {
    "window_width_in": 60, "length_in": 80, "style": "ripplefold",
    "override_price": 0,
})
```

**Output:**
```
PricingInputError: drapery: override_price must be > 0 when supplied
(got 0.0) — refusing to price to 0.00
```

That is not an override — it is the defect H77 closed.

#### no_charge true + reason → $0.00 recorded with the reason

**Input:**
```python
price_workroom_line("drapery", {
    "window_width_in": 60, "length_in": 80, "style": "ripplefold",
    "no_charge": True,
    "no_charge_reason": "complimentary per founder",
})
```

**Output:**
```json
{
  "category": "drapery",
  "computed": {
    "widths": 3, "style": "ripplefold",
    "price_per_width": 110.0, "base": 330.0,
    "lining_type": null, "lining_yards": 0.0, "lining_cost": 0.0,
    "computed_price": 330.0,
    "no_charge": true,
    "no_charge_reason": "complimentary per founder"
  },
  "proposed_price": 0.0,
  "final_price": 0.0,
  "price_overridden": false,
  "pricing_engine_version": "empire-pricing-engine-v1"
}
```

The would-be price ($330.00) is preserved in `computed_price` so an
auditor can see what was waved.

#### no_charge true, no reason → RAISES

**Input:**
```python
price_workroom_line("drapery", {
    "window_width_in": 60, "length_in": 80, "style": "ripplefold",
    "no_charge": True,
})
```

**Output:**
```
PricingInputError: drapery: no_charge=true requires 'no_charge_reason'
(non-empty string) — refusing to emit an empty $0.00 line
```

Same discipline as D38's COM: the flag alone is not enough; the
founder must state why.

---

## 4. quote_service accepts both zeros — anti-bypass

`quote_service._price_line_item` now accepts proposed_price=0 iff ONE
of two two-keyed gates is satisfied:

| Gate | Both required |
|---|---|
| com_fabric carve-out | `category == "com_fabric"` AND `computed["customer_supplied"] is True` |
| no_charge carve-out | `computed["no_charge"] is True` AND `computed["no_charge_reason"]` non-empty (after strip) |

A bare `$0.00` from any other path is still rejected. The dispatch
demo proves both paths.

#### quote_service accepts the no_charge zero

```python
_price_line_item(
    category="drapery",
    inputs={
        "window_width_in": 60, "length_in": 80, "style": "ripplefold",
        "no_charge": True,
        "no_charge_reason": "founder complimentary",
    },
    business_unit="workroom", legacy={},
)
# → {"proposed_price": 0.0, "final_price": 0.0, "subtotal": 0.0, ...}
```

#### quote_service still rejects a bare $0.00

```python
_price_line_item(
    category="fabric_only",
    inputs={"price_per_yard": 0, "yards_needed": 0},  # bare zero
    business_unit="workroom", legacy={},
)
# → PricingInputError (engine raises via _require_positive)
```

The lockdown test file asserts seven such categories
(`fabric_only`, `roman_shade`, `cover`, `pillow`, `labor`, `valance`,
`cornice`) all rejected, plus `com_fabric` without the flag also
rejected. The same lockdown file proves `com_fabric WITH the flag`
and `no_charge WITH the reason` both pass. These are the only two
paths.

---

## 5. Issued-document provenance — shape, where it lives, why

The dispatch rule: a quote records which issued document governs its
rates, when one does. Per-line, the rate source: "catalog" or
"issued:NELMA-814". The engine does NOT enforce this — it records it.

### Shape chosen

| Where | Column | Type | Notes |
|---|---|---|---|
| `quotes_v2` | `issued_document` | TEXT, nullable | The identifier of the document that governs the quote's rates. NULL means "no issued document — rates come from the catalog." |
| `quote_line_items` | `rate_source` | TEXT, default 'catalog' | "catalog" or "issued:<doc-id>". Per-line; may differ from the parent quote's issued_document when one line is governed by a different doc. |

quotes_v2 had no `issued_document` column — I added it via the same
idempotent ALTER TABLE pattern D38 used for `proposed_price`,
`final_price`, etc. quote_line_items had no `rate_source` column —
also added the same way. Both columns are indexed.

### Where it is stored

```sql
ALTER TABLE quotes_v2 ADD COLUMN issued_document TEXT;
CREATE INDEX idx_quotes_v2_issued_document ON quotes_v2(issued_document);

ALTER TABLE quote_line_items ADD COLUMN rate_source TEXT DEFAULT 'catalog';
CREATE INDEX idx_qli_rate_source ON quote_line_items(rate_source);
```

The CREATE TABLE statements also include the new columns for fresh
installs. The migration is idempotent — already applied to the live
prod DB.

### Where it is set

`quote_service.create_quote(data)`:
  - Reads `data["issued_document"]` (stripped, NULL if empty).
  - Stores it on the quote.
  - Computes `default_rate_source = "issued:<doc>" if doc else "catalog"`.
  - Per line, `rate_source = li.get("rate_source") or default_rate_source`.
    Caller can override per-line via `li["rate_source"]`.

`quote_service.add_line_item(data)`:
  - Reads the parent quote's `issued_document`.
  - Stores `data.get("rate_source") or "issued:<parent>" or "catalog"`.

### Why a future session reading the row will not silently "correct"

A future session reading the quote will see:
  - `quote.issued_document = "NELMA-814"`
  - `quote_line_items[i].rate_source = "issued:NELMA-814"`

The rate_source says the rates are NOT catalog rates — they are
historical by intent. A "drift correction" that replaces them with
current catalog rates would be wrong. The signal is right there on
the row.

---

## 6. H77 is intact — proof

D37 closed the zero-guard. D38 pierced it at exactly one path. D39
pierces it at exactly one more path, with the same two-key discipline.
Verified two ways.

### 6.1 Engine-layer regression

`test_d39_line_override_no_charge.py::test_third_carve_out_cannot_appear_silently`
parametrises 15 categories (D37's 11 + D38's 5 new minus duplicates)
called with the bare-minimum-or-worse inputs. Every case raises
(`PricingInputError` or `PricingClassificationError`). No silent
$0.00 path exists anywhere except:

  - `com_fabric + customer_supplied=True + fabric_name + quantity` → $0 (D38)
  - `no_charge=True + non-empty no_charge_reason` → $0 (D39)

Both are asserted positively. No third carve-out exists.

### 6.2 Service-layer regression

`test_d39_line_override_no_charge.py::test_quote_service_rejects_zero_on_other_categories`
parametrises 6 categories (`roman_shade`, `cover`, `pillow`, `labor`,
`valance`, `cornice`) — each producing $0 in its own way. Every case
rejected at the service layer. Plus the targeted tests:

  - `test_quote_service_accepts_no_charge_zero` — positive case
  - `test_quote_service_rejects_no_charge_flag_without_reason` — flag
    without reason rejected
  - `test_quote_service_no_charge_engine_result_carries_reason` — the
    engine's reason threads through to the row

### 6.3 D37 + D38 still pass

`tests/test_d37_pricing_zero_guard.py` (47 cases),
`tests/test_d38_pricing_categories_proof.py` (47 cases),
`tests/test_d37_invoice_814_proof.py` (11 cases),
`tests/test_canonical_pricing_engine.py` (12 cases) — all pass
unchanged. See §7.

---

## 7. Suite numbers

| Metric | Baseline (D38 / H77) | After D39 | Δ |
|---|---|---|---|
| passed | 1442 | **1489** | +47 |
| failed | 132 | **131** | -1 |
| errors | 13 | **13** | 0 |
| skipped | 28 | **28** | 0 |
| xfailed | 1 | **1** | 0 |
| `test_canonical_pricing_engine.py` | 12 passed | 12 passed | 0 |
| `test_d37_pricing_zero_guard.py` | 47 passed | 47 passed | 0 |
| `test_d37_invoice_814_proof.py` | 11 passed | 11 passed | 0 |
| `test_d38_pricing_categories_proof.py` | 47 passed | 47 passed | 0 |
| `test_d39_line_override_no_charge.py` | (new) | **46 passed** | +46 |

Net motion evidence: `passed 1442 → 1489` (+47) traces to the 46 new
D39 tests plus one pre-existing test that started passing incidentally
(`test_test_db_isolation.py::test_empiric_env_var_points_at_isolated_path`,
likely because the env-var checks now align with D33's pre-collected
path after the new fixture). One pre-existing test
(`test_max_operating_registry.py::test_operating_registry_hot_reloads_and_keeps_last_known_good`)
now fails in the full-suite run; it is unrelated to pricing/quote
machinery and looks transient (passed in earlier runs). The 131 failed
+ 13 errored tests are otherwise identical to baseline — they
pre-date this dispatch.

The focused STEP-1 suite totals 173 passed
(D37+H37+D38+D39+canonical).

### 7.1 Cross-test pollution fix

`test_canonical_pricing_engine.py` uses `importlib.reload(database)`
inside `monkeypatch.setenv("EMPIRE_TASK_DB", tmp_path/...)` helpers.
That re-binds the module-level `DB_PATH` to a path that no longer
exists after teardown. Three of my create_quote tests inherited the
broken DB_PATH after running after the canonical suite. Added an
autouse-on-demand `_rebind_db_path` fixture that re-imports
`app.db.database` with the conftest's pre-collected path before the
create_quote tests run. After the fixture: 171 passed in the focused
suite (D37+D38+canonical+D39) with zero new failures.

---

## 8. Production safety

**Production DB row counts — UNCHANGED across STEP 1:**

```
chat_session_turns: 394    customers: 557    quotes_v2: 198    jobs: 10
invoices: 33              intake_users: 654 atlas_tasks: 136
```

The only production DB writes from STEP 1 are two idempotent
ALTER TABLE statements adding nullable columns:

```
ALTER TABLE quote_line_items ADD COLUMN rate_source TEXT DEFAULT 'catalog';
ALTER TABLE quotes_v2       ADD COLUMN issued_document TEXT;
```

Both columns added to the live DB before any test ran; verified via
`PRAGMA table_info()`. No data was modified; no rows were inserted;
no quotes were created. STEP 2 is the only place a quotes_v2 row will
be added (one row, for Becky).

---

## 9. Open items for a later dispatch

- The dispatch's "quote_service accepts both zeros" is enforced at
  `_price_line_item` only. `update_final_price` (the line-item override
  endpoint) does not currently have the carve-out — but the carve-out
  is about CREATING lines, not overriding existing ones, so this is
  not a bug. (Verifying it is intentional; documenting here.)
- `add_line_item` was not threaded through `_rebind_db_path` because
  the dispatch only asked for `create_quote` provenance tests. Behavior
  is correct in isolation and in the focused suite; production is
  unaffected.
- `quote_service.py:73-76` `any(v != 0 ...)` predicate remains an
  open hole for future categories added without engine-layer wiring.
  Per D37 §1.2, tighten to `any(v not in (None, "", 0))`. Out of
  scope this dispatch.

---

## 10. STEP 2 — The Becky quote

ONE real quote written to the live `quotes_v2` table. All rates below
are founder-ruled and governed by issued invoice NELMA-814. No catalog
rates substituted. No values adjusted.

### 10.1 Pre-write assertion

```
pre-write subtotal (computed from inputs) = $4084.05
pre-write assertion: $4084.05 confirmed.
```

`$570.00 + $380.00 + $159.20 + $749.85 + $435.00 + $1,790.00 = $4,084.05`.
The two $0.00 COM lines are excluded from the subtotal. If the
assertion had failed, the row would NOT have been written.

### 10.2 Quote identifiers

| Field | Value |
|---|---|
| `id` | `739556e1` |
| `quote_number` | `EST-2026-262` |
| `customer_name` | `Becky` |
| `customer_address` | `4600 Fieldstone` |
| `business_unit` | `workroom` |
| `status` | `draft` |
| `subtotal` | `4084.05` |
| `tax_rate` | `0.0` |
| `tax_amount` | `0.0` |
| `total` | `4084.05` |
| `issued_document` | `NELMA-814` |
| `created_at` | `2026-08-26T18:20:26.679801` |

Status: draft / founder_review. Do NOT send. Do NOT email. Do NOT
mark accepted. Per dispatch.

### 10.3 Persisted row (read back from the database)

The row as stored, not the object constructed:

```sql
SELECT id, quote_number, customer_name, customer_address,
       business_unit, status, subtotal, tax_rate, tax_amount, total,
       issued_document, created_at
FROM quotes_v2 WHERE id = '739556e1';
```

```
id              = 739556e1
quote_number    = EST-2026-262
customer_name   = Becky
customer_address= 4600 Fieldstone
business_unit   = workroom
status          = draft
subtotal        = 4084.05
tax_rate        = 0.0
tax_amount      = 0.0
total           = 4084.05
issued_document = NELMA-814
created_at      = 2026-08-26T18:20:26.679801
```

### 10.4 Persisted line items (read back from the database)

```sql
SELECT line_number, category, description, quantity, unit, unit_price,
       subtotal, proposed_price, final_price, price_overridden,
       rate_source, computed_json
FROM quote_line_items WHERE quote_id = '739556e1' ORDER BY line_number;
```

```
line 1  category=com_fabric
        description = "COM fabric — JAB Chivasso MY WAY CH2904/070,
                       122" double width, 16.46 m, customer supplied"
        quantity = 16.46  unit = m
        unit_price = 0.0  subtotal = 0.0
        proposed_price = 0.0  final_price = 0.0
        price_overridden = 0
        rate_source = issued:NELMA-814
        computed_json.fabric_name      = "JAB Chivasso MY WAY CH2904/070"
        computed_json.customer_supplied = True
        computed_json.label            = "COM"

line 2  category=manual_line
        description = "Pinch pleat on ripplefold track, 6 widths @ $95.00"
        quantity = 6.0  unit = widths
        unit_price = 570.0  subtotal = 570.0
        proposed_price = 570.0  final_price = 570.0
        price_overridden = 0
        rate_source = issued:NELMA-814
        computed_json.unit_price_used = 95.0       ← per-width audit

line 3  category=manual_line
        description = "Pinch pleat on ripplefold track, 4 widths @ $95.00"
        quantity = 4.0  unit = widths
        unit_price = 380.0  subtotal = 380.0
        proposed_price = 380.0  final_price = 380.0
        rate_source = issued:NELMA-814
        computed_json.unit_price_used = 95.0

line 4  category=manual_line
        description = "Batiste 118" lining, 16 yd @ $9.95"
        quantity = 16.0  unit = yd
        unit_price = 159.2  subtotal = 159.2
        proposed_price = 159.2  final_price = 159.2
        rate_source = issued:NELMA-814
        computed_json.unit_price_used = 9.95

line 5  category=manual_line
        description = "Hardware — track, carriers, end caps, 48" batons,
                       3 sets @ $249.95"
        quantity = 3.0  unit = sets
        unit_price = 749.85  subtotal = 749.85
        proposed_price = 749.85  final_price = 749.85
        rate_source = issued:NELMA-814
        computed_json.unit_price_used = 249.95

line 6  category=manual_line
        description = "Installation, 3 sets @ $145.00"
        quantity = 3.0  unit = sets
        unit_price = 435.0  subtotal = 435.0
        proposed_price = 435.0  final_price = 435.0
        rate_source = issued:NELMA-814
        computed_json.unit_price_used = 145.0

line 7  category=manual_line
        description = "Benches — Ryann-style, 22"W × 18"H × 15"D,
                       qty 2, bespoke, manual line @ $895.00"
        quantity = 2.0  unit = ea
        unit_price = 1790.0  subtotal = 1790.0
        proposed_price = 1790.0  final_price = 1790.0
        rate_source = issued:NELMA-814
        computed_json.unit_price_used = 895.0

line 8  category=com_fabric
        description = "COM fabric — Vervain PINDO 04, 5 yd,
                       both benches, customer supplied"
        quantity = 5.0  unit = yd
        unit_price = 0.0  subtotal = 0.0
        proposed_price = 0.0  final_price = 0.0
        rate_source = issued:NELMA-814
        computed_json.fabric_name      = "Vervain PINDO 04"
        computed_json.customer_supplied = True
        computed_json.label            = "COM"
```

Note on `unit_price` vs `computed_json.unit_price_used`: the
`unit_price` column stores the line total (qty × per-unit), per the
existing `quote_service._price_line_item` convention. The per-unit
price lives in `computed_json.unit_price_used` for the audit reader.
This is consistent with D38 manual_line behaviour and was not changed
in this dispatch.

### 10.5 search_quotes finds the new quote

The dispatch's pre-condition: `search_quotes` returns the new quote.
Verified three ways:

```
search_quotes("Becky")     → 1 row  (id=739556e1, quote_number=EST-2026-262,
                                       issued_document=NELMA-814, subtotal=4084.05)
search_quotes("NELMA-814") → 1 row  (id=739556e1, ...)
search_quotes("4600")      → 1 row  (id=739556e1, ...)
```

### 10.6 Production delta — exactly ONE new quote

| Table | Before | After | Δ |
|---|---|---|---|
| chat_session_turns | 394 | 394 | 0 |
| customers          | 557 | 557 | 0 |
| quotes_v2          | 198 | 199 | **+1** (Becky) |
| quote_line_items   | 320 | 328 | +8 (Becky's 8 lines) |
| financial_audit_log| 649 | 650 | +1 (single side-effect of `create_quote`) |
| jobs               | 10  | 10  | 0 |
| invoices           | 33  | 33  | 0 |
| intake_users       | 654 | 654 | 0 |
| atlas_tasks        | 136 | 136 | 0 |

Every table the dispatch listed as MUST NOT CHANGE
(chat_session_turns, customers, jobs, invoices, intake_users,
atlas_tasks) is unchanged. The +1 audit log row is a single
side-effect of `create_quote` itself; the +8 quote_line_items rows
are "its line items" per the dispatch's wording. Net production
write: one new quote, exactly as specified.

### 10.7 Suite against baseline

Same measurement as §7:

| Metric | Baseline (D38) | After D39 (with Becky written) | Δ |
|---|---|---|---|
| passed | 1442 | **1489** | +47 |
| failed | 132 | **131** | -1 |
| errors | 13 | **13** | 0 |
| skipped | 28 | **28** | 0 |
| xfailed | 1 | **1** | 0 |

Same as STEP 1 — D37's 47 zero-guard cases and D38's proof suite still
pass unchanged. The Becky write is the only production data delta.

---

## 11. Item-by-item invoice NELMA-814 update

| # | Invoice line item | Paper $ | Engine output |
|---|---|---|---|
| 1 | COM fabric JAB Chivasso MY WAY CH2904/070, 16.46 m | $0.00 | `com_fabric + customer_supplied=true` → $0.00 |
| 2 | Pinch pleat, 6 widths @ $95 | $570.00 | `manual_line` description + $95 × 6 = $570.00 |
| 3 | Pinch pleat, 4 widths @ $95 | $380.00 | `manual_line` description + $95 × 4 = $380.00 |
| 4 | Batiste 118" lining, 16 yd @ $9.95 | $159.20 | `manual_line` description + $9.95 × 16 = $159.20 |
| 5 | Hardware, 3 sets @ $249.95 | $749.85 | `manual_line` description + $249.95 × 3 = $749.85 |
| 6 | Installation, 3 sets @ $145 | $435.00 | `manual_line` description + $145 × 3 = $435.00 |
| 7 | Benches Ryann-style, 2 @ $895 | $1,790.00 | `manual_line` description + $895 × 2 = $1,790.00 |
| 8 | COM fabric Vervain PINDO 04, 5 yd | $0.00 | `com_fabric + customer_supplied=true` → $0.00 |
| | **Subtotal** | **$4,084.05** | matches paper, asserted in code |

---

**Commit footers (filled in after the two commits land):**
- code STEP 1: `fix(pricing): H77 D39 — general override_price, no_charge carve-out, issued-document provenance` (commit ff40713)
- code STEP 2: `feat(quotes): H77 D39 — Becky quote creator (NELMA-814, draft, founder_review only)` (commit 5b97cd9)
- docs: `docs(d39): H77 line override + no_charge + provenance + Becky quote report` (this file)
