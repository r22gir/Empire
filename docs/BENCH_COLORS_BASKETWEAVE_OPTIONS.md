# Bench Colors + Basketweave Options — DRAFT Test Copy for Approval

> **Status: DRAFT — NOT client-facing. Do not send to clients until Rafael approves.**
> Owner: Rafael / Empire Workroom · Last reviewed: _pending founder approval_
>
> Purpose: single reference for the bench seat/back colors and weave (channel)
> options Empire Workroom actually quotes, built from real repo records
> (past-quote fabric seeds, drawing engine panel styles, final-doc finish
> details). Anything not found in the records is labeled **UNCONFIRMED** below.

## 1. Bench colors actually quoted (from past-quote records)

Source: Ramiro Quote fabric seed — `backend/app/routers/fabrics.py`
(`seed_ramiro_fabrics()`). These are the only seat/back colors pinned in code
today. Cost/yard and margin are `0` in the seed (owner sets pricing), so this
doc lists colors only — no prices.

### Seat fabrics

| Code | Fabric | Color | Where quoted |
|------|--------|-------|--------------|
| V639 | Charlotte Fabrics Cuaderno | **Spruce** | Upstairs Dining (Comedor Arriba) |
| V638 | Charlotte Fabrics V638 | **Teak** | First Floor Dining (Primer Piso Comedor) |
| V1012 | Marine Vinyl II (Kovi Fabrics) | **Hazelnut** | Rear Upstairs Dining (Comedor Arriba Atras) |

### Backing fabrics (pair with seat fabric above)

| Code | Color | Pairs with |
|------|-------|------------|
| NCOP-64 (Douglass) | **Neutral** | V639 Spruce |
| D3191 | **Fawn** | V638 Teak |
| D3222 | **Umber** | V1012 Hazelnut |

### UNCONFIRMED — needs Rafael's call

- No other bench colors were found in past quotes, drawings, or final docs in
  this repo. If clients are being offered additional colors (e.g. COM —
  customer's own material, or other Charlotte/Kovi colorways), add them to the
  table above with the quote that proves it, then update the regression test
  (`backend/tests/test_bench_colors_basketweave_options.py`).
- Client-owned fabric (COM) intake exists (`ClientFabricSubmit` in
  `backend/app/routers/fabrics.py`) — confirm whether COM benches should list
  color options at all or just say "client-supplied."

## 2. Basketweave / channel options (from drawing + final-doc records)

Source: drawing engine — `backend/app/routers/drawings.py` (`BenchRequest.panel_style`)
and `backend/app/services/vision/bench_renderer.py` (`BenchModel`).

### What the drawing engine supports today

| Option key | Label (test copy) | Notes |
|------------|-------------------|-------|
| `vertical_channels` | Vertical channels | Default — `flat` requests render as this |
| `horizontal_channels` | Horizontal channels | Supported panel style |
| `tufted` | Tufted | Supported panel style; final docs also detect tufting buttons |
| `flat` | Flat / plain | Accepted input; renders as `vertical_channels` |

Bench plan shapes (for context, not weave): `straight`, `l_shape`, `u_shape`
(`BenchRequest.bench_type`).

### Finish details that appear on final docs

Source: quote PDF renderer — `backend/app/routers/quotes.py` (furniture-section
builder detects these from AI analysis or notes and draws them on the final
client document): **welting/piping, tufting, flange, skirt, channeling,
nailhead.** If a basketweave bench is quoted with any of these (e.g. welting),
the final doc already renders it — no extra work needed.

### UNCONFIRMED — needs Rafael's call ⚠️

- **No true "basketweave" weave pattern was found anywhere in the repo**
  (no weave-pattern field, swatch, or supplier weave code). The word
  "basketweave" does not appear in code, quotes, or drawings.
- Test copy below is a **proposal only** — approve, edit, or delete:
  - _Option A: Flat weave (plain basketweave)_ — proposed standard
  - _Option B: Chunky / open basketweave_ — proposed upgrade
  - _Option C: Channel-quilted look (via existing `vertical_channels`)_ —
    already renderable today, no new drawing work
- Do NOT quote basketweave-specific pricing until Rafael confirms which (if
  any) of these Empire Workroom actually sews. Pricing fields in the fabric
  seed are all `0` — owner sets pricing.

## 3. Approval checklist (Rafael)

- [ ] Section 1 colors correct? Add/remove rows with proof quote.
- [ ] COM benches: list colors or "client-supplied" only?
- [ ] Section 2: approve/edit/delete the three proposed basketweave options.
- [ ] If a new weave is approved, file a follow-up to add it to
  `BenchRequest.panel_style` + `bench_renderer.py` and re-seed fabrics.
- [ ] After approval: remove this DRAFT banner and mark review date above.

## Provenance (so this doc stays honest)

- Past quotes → `backend/app/routers/fabrics.py::seed_ramiro_fabrics`
- Drawings → `backend/app/routers/drawings.py::BenchRequest`,
  `backend/app/services/vision/bench_renderer.py::BenchModel`
- Final docs → `backend/app/routers/quotes.py` furniture-section builder
  (`is_bench` branch + welting/tufting/flange/skirt/channeling/nailhead detection)
- Regression test → `backend/tests/test_bench_colors_basketweave_options.py`
