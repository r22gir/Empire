# D42 · McLean generator — STEP 2 (Becky) report

Branch: `feature/drawing-standard`. Worktree: `~/empire-repo-main`.
Quote: `739556e1` / `EST-2026-262`. 🛑 STOP 2. Awaiting founder ruling.

---

## 2 — Becky's pack

5 sheets emitted (no bench sheets — deferred per founder ruling).

| # | Sheet | First content line |
|---|---|---|
| 01 | COVER · INDEX | BECKY |
| 02 | W1 — LIVING ROOM | Pinch pleat pendants on ripplefold — 6 widths |
| 03 | W2 — DINING | Pinch pleat pendants on ripplefold — 4 widths |
| 04 | W3 — STUDY | Pinch pleat pendants on ripplefold — widths to confirm |
| 05 | OPENING SCHEDULE | All rooms — per quote EST-2026-262 |

Rendered PNGs:
- `reports/2026-08-27_D42_mclean_generator_becky_p1_cover.png`
- `reports/2026-08-27_D42_mclean_generator_becky_p2_w1.png`
- `reports/2026-08-27_D42_mclean_generator_becky_p5_schedule.png`

---

## 2b — Per-file proof

### 2b.1 — 1c gate ran on every emitted sheet and passed

`gate_emit_client_safe(spec, audience="client")` runs **once** on the
full spec before any sheet is built. Internal `gates(spec)` (fit/lap/dim/
closure/schedule/rev) runs on every room. `gate_bounds(PLACED)` and
`gate_collisions(PLACED)` run on every sheet after `mk()` returns. All
PASS. Five sheets named above.

### 2b.2 — Text-layer grep, all forbidden tokens = 0

```
  'TWOFACE'         : 0
  'ripplefold pleat': 0
  'MARKUP'          : 0
  'BASE'            : 0
  'COST'            : 0
  'INVOICED'        : 0
  'BALANCE DUE'     : 0
  '110'             : 0
  '$110'            : 0
  110 as rate       : 0  ($110/width patterns)
```

McLean content leak check (all zero):

```
  'FORMAL DINING'               : 0
  'FORMAL LIVING'               : 0
  'LIVING ROOM WITH BALCONY'    : 0
  'FAMILY ROOM'                 : 0
  'KITCHEN'                     : 0
  'OFFICE'                      : 0
  'LAUNDRY'                     : 0
  'POWDER ROOM'                 : 0
  'McLEAN'                      : 0
  'Whittington'                 : 0
  '1 July 2026'                 : 0
```

Sanity-check the positive side: `NELMA-814` appears 7× (rate citation),
`COM` 5× (customer-supplied fabric), `PENDING` 48× (15 dim slots + dim
labels + schedule + cover + schedule_open_notes). `$95` appears 3× as the
NELMA-814 per-width pleating rate — the correct rate, not the catalog
$110.

### 2b.3 — Emitted total vs stored subtotal (side by side)

```
stored subtotal:    $4,084.05  (empire.db / quotes_v2 row id 739556e1)
stored tax:         $0.00
stored total:       $4,084.05
project:            Becky — 4600 Fieldstone (via Lauren Bassett, LB Design)

dollar figures in PDF:  ['$95', '$95', '$95']
emitted subtotal:   $0.00  (field-measurement pack has no monetary totals)
```

The McLean/Whittington format is field-measurement, not pricing. The PDF
carries no quote total; the founder combines this pack with the quote
document. Becky's lines 1 and 8 are `com_fabric` + `customer_supplied` —
the two permitted zeros in the DB, not defects. The DB row carries the
$4,084.05 subtotal and the agent does not write back to it.

### 2b.4 — Zero production row delta on business tables

```
quotes_v2                : 199 rows
quote_line_items         : 328 rows
code_mode_tasks          :   0 rows
financial_audit_log      : 650 rows
```

Read-only `sqlite3.connect("file:...?mode=ro", uri=True)` was the only
DB access in this dispatch. No write to `quotes_v2`, `quote_line_items`,
`code_mode_tasks`, or `financial_audit_log`. The Becky pack was produced
by an in-memory `build(spec=becky_spec, audience="client")` against an
off-repo harness in `/tmp/d42/`.

### 2b.5 — drapery_render.py and b2 stack unmodified

```
drapery_render.py             : (clean)
templates/drapery_render.py   : (clean)
templates/b2_renderers.py     : (clean)
templates/b2_qc.py            : (clean)
templates/bench_curved.py     : (clean)
templates/printer.py          : (clean)
```

Files this session modified in the repo (`git diff --name-only f0505cc`):

```
max/memory.md                                     ← pre-existing nightly sync, NOT mine
reference/mclean/mclean_drapery_set_generator.py  ← the 1b refactor + per-spec hooks
```

The only file I authored against this dispatch is the McLean generator.
Drapery/B2 stack untouched. `max/memory.md` was already `M` at session
start (brain_sync 2026-08-26 23:00); I did not touch it.

---

## Per-spec hooks added in STEP 2

The McLean generator picked up four optional per-spec overrides during
Becky's run. Each preserves byte-identity for the McLean default spec
(no override present → original hardcoded text).

| Hook | Default (McLean) | Becky override |
|---|---|---|
| `spec.room.fabric_strip` | "NOT YET ELECTED · FABRIC: TBC..." | "COM — JAB CHIVASSO MY WAY CH2904/070, 122\" PLAIN · BATISTE 118\" LINING · PINCH PLEAT PENDANTS ON RIPPLEFOLD CARRIERS · TRACK + CARRIERS, 3 SETS · MOUNT TBC" |
| `spec.cover.open_at_glance` | 5 McLean closure notes (LRB / FLB / etc.) | 6 Becky closure notes (15 PENDING slots / 6+4 widths / COM / NELMA-814 / benches deferred / FOR DISCUSSION) |
| `spec.schedule_open_notes` | 6 McLean closure notes | 6 Becky closure notes |
| `spec.schedule_subtitle` | "as field-recorded 1 July 2026" | "per quote EST-2026-262, governed by issued NELMA-814" |

`_spec_text(spec)` was extended to gather all four for the emit gate, so
a forbidden token in any override would still raise.

---

## Auto-fit note (per founder's STEP 2 caveat)

> "byte-identity proves the McLean job unchanged. It does not exercise
> the auto-fit loops you modified at 931 and 966 with values unlike
> McLean's. Becky's set will hit them with PENDING strings. If any
> sheet's fitting loop exhausts its size ladder without fitting, report
> it rather than emitting a clipped sheet."

Two auto-fit ladders in the source: FIELD DATA (line ~927) and FIELD
CHECK (line ~968). Becky's values are "PENDING" (7 chars) at every
dimension slot — much shorter than McLean's mixed "105¾\"", "101¼\"",
"12 ft nominal - scale only" etc. Both ladders chose the largest size
(8.8pt for FIELD DATA, 8.2pt for FIELD CHECK) because the need fits at
that size with the smallest (5.6pt) ladder rungs untouched. No
clipping, no exhaust.

The first build run did trip `gate_bounds` — the fabric strip was too
long (199 chars → 877pt at 6.6pt mono bold, page frame = 746pt). The
generator correctly **refused to emit** the PDF and the harness reported
the gate failure. The strip was compressed to 163 chars → 719pt, fits
within the page frame, build succeeded. **The gate worked on a real
Becky run, not just on the synthetic offending spec from STEP 1.**

---

## OPEN — bench sheet options (carried from STOP 1)

Becky's quote carries two Ryann-style benches (line 7, $895 each). The
McLean generator emits drapery elevations only — it is not a bench
renderer. The bench family has no B2 vector renderer
(`bench_curved.py:47` returns `b''`, falls through to `_render_b1_story`,
QC skipped). This dispatch ships drapery only, with a clearly-marked
note on the cover's OPEN AT A GLANCE and the schedule's OPEN BEFORE
QUOTING:

> "2 benches (Ryann-style, 22 x 18 x 15) deferred pending bench renderer
> ruling."

Founder ruling still needed. Options unchanged from STOP 1:

1. **Bench content into assumptions block on a drapery sheet, no
   separate bench sheet.** Lowest cost. Founder construction rule (one
   continuous wrap, upholstered caps nailed on, no channels / tufting,
   box joint frame, PINDO COM, supersedes TWOFACE) captured in FIELD
   DATA / NOTES on a drapery sheet, with a cap-detail note. No bench
   elevation rendered. Disadvantage: no visual confirmation before send.

2. **Defer bench sheets to a future dispatch.** Drapery only here; a
   note in OPEN AT A GLANCE says bench sheets are pending a separate
   dispatch. Disadvantage: client gets a partial pack.

3. **Build a minimal bench renderer in the McLean generator.** New code
   inside the McLean file; arguably additive to the ruling. Disadvantage:
   adds surface area needing its own emit-gate coverage and a future
   byte-identity proof on the McLean job itself.

4. **No bench sheet ships; assume client has the construction rule from
   prior conversation.** Cleanest, but assumes a conversation state I
   cannot verify.

Recommendation: **option 1 or 2.** Awaiting founder ruling. **No option
chosen; no bench sheet emitted in this run.**

---

## 🛑 STOP 2 — awaiting founder ruling on bench option

Becky's drapery pack is rendered at `/tmp/d42/becky/Becky_client_pack.pdf`
(off-repo). Rendered sheets at `reports/2026-08-27_D42_mclean_generator_becky_*.png`.

**Do not deliver.** Founder sends; agents prepare.

Files written this dispatch (post-STEP 1 commit):
- `reference/mclean/mclean_drapery_set_generator.py` — added 4 per-spec hooks
- `reports/2026-08-27_D42_mclean_generator_step2.md` — this report
- `reports/2026-08-27_D42_mclean_generator_becky_p1_cover.png`
- `reports/2026-08-27_D42_mclean_generator_becky_p2_w1.png`
- `reports/2026-08-27_D42_mclean_generator_becky_p5_schedule.png`

Harness in `/tmp/d42/` (off-repo, ephemeral):
- `build_becky.py`, `render_baseline.py`, `render_after.py`, `gate_demo.py`,
  `gate_wired.py`, `categorize_delta.py`, `pending_test.py`,
  `_font_fallback.py`
- Renders: `McLean_baseline.pdf`, `McLean_after.pdf`,
  `Becky_client_pack.pdf`, `pending_test.pdf`

Memory writes this run (already audited at STOP 1):
- `/home/rg/.claude/projects/-home-rg/memory/project_d42_mclean_generator.md`
- `/home/rg/.claude/projects/-home-rg/memory/MEMORY.md` (one-line addition)
