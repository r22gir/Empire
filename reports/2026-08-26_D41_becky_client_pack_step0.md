# D41 · Becky client pack — STEP 0 map

Branch: `feature/drawing-standard`. Worktree: `~/empire-repo-main`.
Quote id: `739556e1` (row id in `quotes_v2`). Quote number: `EST-2026-262`.

## 0a — Quote as stored (READ-ONLY)

Source: `~/empire-data/empire.db`, `quotes_v2`, opened with
`file:...?mode=ro` + `uri=True`. No writes performed.

Header:
- `id` = `739556e1`
- `quote_number` = `EST-2026-262`
- `customer_name` = `Becky`
- `customer_address` = `4600 Fieldstone`
- `business_unit` = `workroom`
- `job_id` = **empty** (no job linked)
- `project_name` = `Becky — 4600 Fieldstone (via Lauren Bassett, LB Design)`
- `project_description` = `Custom drapery, 3 sets of pinch pleat pendants on ripplefold tracks, 2 Ryann-style benches. Rates governed by issued invoice NELMA-814 (out-of-state; tax exempt).`
- `status` = `draft`
- `subtotal` = `4084.05`
- `tax_rate` = `0.0`
- `tax_amount` = `0.0`
- `total` = `4084.05`
- `location` = empty; out-of-state, tax exempt per project_description and notes
- `pricing_mode` = empty
- `notes` (truncated) = `Issued by founder 2026-08-26 against paper invoice NELMA-814. Out-of-state, tax exempt. Status: draft / founder_review. Do NOT send. Do NOT email. Do NOT mark accepted. Created by D39 dispatch (H77).`
- `expires_at` = `2026-09-25T18:20:26.682747`
- `deposit_required` = `2042.03` (50%); `deposit_paid` = `0.0`
- `balance_due` = `4084.05`

8 lines (every one carries `rate_source = 'issued:NELMA-814'`):

| # | desc | qty | unit | subtotal | category | `unit_price_used` (in `computed_json`) |
|---|---|---:|---|---:|---|---|
| 1 | COM — JAB Chivasso MY WAY CH2904/070, 122" double width, 16.46 m | 16.46 | m | 0.00 | com_fabric | n/a (zero) |
| 2 | Pinch pleat on ripplefold track, 6 widths @ $95 | 6 | widths | 570.00 | manual_line | 95.00 |
| 3 | Pinch pleat on ripplefold track, 4 widths @ $95 | 4 | widths | 380.00 | manual_line | 95.00 |
| 4 | Batiste 118" lining, 16 yd @ $9.95 | 16 | yd | 159.20 | manual_line | 9.95 |
| 5 | Hardware — track, carriers, end caps, 48" batons, 3 sets @ $249.95 | 3 | sets | 749.85 | manual_line | 249.95 |
| 6 | Installation, 3 sets @ $145.00 | 3 | sets | 435.00 | manual_line | 145.00 |
| 7 | Benches — Ryann-style, 22"W × 18"H × 15"D, qty 2, manual line @ $895.00 | 2 | ea | 1790.00 | manual_line | 895.00 |
| 8 | COM — Vervain PINDO 04, 5 yd, both benches | 5 | yd | 0.00 | com_fabric | n/a (zero) |

Sum = `4084.05`. Subtotal = `4084.05`. Total = `4084.05`.
**All 8 assertions match** (lines 1, 8 → $0.00; lines 2-7 → expected values).

Lines 1 and 8 carry `customer_supplied = true` in their `computed_json` and
are explicitly labelled "ONE permitted zero … Excluded from margin".

`unit_price_used` is **not a column** on `quote_line_items` — it lives
inside `computed_json`. Lines 2, 3, 5, 6, 7 carry `unit_price_used`
exactly as expected; line 4's `unit_price_used = 9.95` is the per-yard
batiste rate, not the per-width pleating rate. The 6-widths and 4-widths
are pinned to `$95/width` per NELMA-814, **not** the catalog `$110`.

Tax treatment: `tax_rate = 0.0`, `tax_amount = 0.0`. Out-of-state / tax
exempt per `project_description` and `notes`.

## 0b — Field data for W1, W2, W3 (READ-ONLY)

Searched exhaustively — none of the canonical field-data stores holds
this job:

| Store | Count or finding |
|---|---|
| `job_documents` | 0 rows total |
| `quote_photos` | 0 rows total |
| `quotes_v2.photos_json` for this row | `None` |
| `quotes_v2.measurements_json` | `None` |
| `quotes_v2.rooms_json` | `None` |
| `quotes_v2.design_proposals_json` | `None` |
| `quotes_v2.ai_mockups_json` | `None` |
| `quotes_v2.ai_outlines_json` | `None` |
| `quotes_v2.job_id` | empty (no job linked) |
| `jobs` (quote_id = '739556e1') | 0 rows |
| `backend/data/drawings/` (360 PDFs) | none named Becky / Fieldstone / NELMA / 739556 / Lauren |
| `backend/data/notes_uploads/` | no entries |
| `backend/data/chats/founder/bf191085.json` (the founder/MAX conversation that produced the quote) | no per-window widths, lengths, deductions, mounts, or headings — only the NELMA line totals |

Universal text search across every TEXT/JSON column in every table for
`739556e1 | Becky | NELMA-814 | 4600 Fieldstone | Lauren Bassett |
EST-2026-262` returned only the `quotes_v2` row, `quotes_v2` notes, and
founder chat logs — **no measurement record exists anywhere on disk.**

**Per-opening result:**

| Opening | Width | Length | Deduction | Mount | Heading |
|---|---|---|---|---|---|
| W1 | **NOT FOUND** | **NOT FOUND** | **NOT FOUND** | **NOT FOUND** | **NOT FOUND** |
| W2 | **NOT FOUND** | **NOT FOUND** | **NOT FOUND** | **NOT FOUND** | **NOT FOUND** |
| W3 | **NOT FOUND** | **NOT FOUND** | **NOT FOUND** | **NOT FOUND** | **NOT FOUND** |

Per the directive, every NOT FOUND becomes **PENDING** in the
CONFIRM BEFORE FABRICATION band; the set still builds.

## 0c — Renderer and QC constants (READ-ONLY)

`backend/app/services/drawing/templates/b2_qc.py` constants
(lines 84–87):

```
MARGIN_IN          = 0.32
HEADER_BAND_H_IN   = 0.92
FOOTER_BAND_H_IN   = 0.42
TITLE_X_IN_MIN     = 7.90
```

Lines 1367 and 1381 verbatim:

```
1367    # Both v10 and R2 used a hand-tuned nudge (golden source line 61:
1381    # Negative fixture: a PDF with the golden source's +0.72 nudge AND
```

(lines 1368–1373 and 1381–1383 continue — they describe the *rejected*
case: a PDF containing the +0.72 nudge + a long street address fails
gate R3-1 because gaps shrink below `MIN_FOOTER_GAP_IN = 0.15`.)

`+0.72` live occurrences across `backend/app/services/drawing/`:

| File | Line | Verdict |
|---|---|---|
| `b2_qc.py` | 1368 | comment only |
| `b2_qc.py` | 1381 | comment only |
| `b2_renderers.py` | 594 | comment: "Pre-R3-1 R1 had `ls_text(c, W/2+0.72, ...)`" |

No executable line emits `+0.72`. The replacement (`R3-1` computed
zone widths + min-gap enforcement) is the live footer path in
`b2_renderers.py:572 _render_footer_band`. **The renderer this set will
use does NOT emit the +0.72 nudge.** No fixture failure on that basis.

### Renderers that actually build these sheets

Family dispatch (`backend/app/services/drawing/templates/printer.py:331-349`):

| Family | Module / entry | Path | `b2_qc` enforced? |
|---|---|---|---|
| Roman Shades | `b2_renderers.render_roman_shades_vector` (`b2_renderers.py:1094`) | B2 vector | yes |
| **Drapery** | `drapery_render.render_drapery` (`drapery_render.py:640`) | vector (own panel/pleat anatomy, NOT Roman-shades ladder) | yes (line 365) |
| **Bench / Banquette** | `bench_curved.BenchCurvedTemplate` (`bench_curved.py:47`) | `render_drawing` returns `b''` per `base.py:26-28` docstring — **NOT IMPLEMENTED** | no — printer.py:342-349 falls through to `_render_b1_story` (textual preview, QC skipped) |
| All other families | B1 textual preview path | — | no |

`printer.py:268` (comment) confirms: "bench/banquette, headboard_channel
land in B2 follow-on." Bench B2 vector renderer is **not yet shipped**.

Naming files that build drapery vs built-upholstery sheets today:

- **Drapery:** `templates/drapery_render.py` (`render_drapery` → `_render_drapery_vector` → `_render_drapery_front` / `_render_drapery_side`).
- **Built-upholstery / bench:** `templates/bench_curved.py` (geometry family — `BenchCurvedTemplate`). Renders via `_render_b1_story` in `templates/printer.py:397`, which is the B1 textual preview path. **The B2 vector renderer for the bench family does not exist.** Any bench sheet emitted today goes through the B1 textual path, which is the path the QC gate does NOT measure.

Four function names sharing one spec is **not** four renderers — only
`render_roman_shades_vector` and `render_drapery` are real B2 vector
renderers. Bench is the B1 story path. Confirmed by reading the
`render_drawing` contract in `templates/base.py:25-28`.

## 0d — Format reference (READ-ONLY)

The "McLean/Whittington reference" describes:

- serif display type
- gold corner tabs on viewports
- three-column FIELD DATA / TREATMENT / FIELD CHECK base band
- layout-math row inside the viewport frame
- gold status strip
- black footer band

What already exists in `b2_renderers.py` / `b2_qc.py` / `EMPIRE_DRAWING_STANDARD.md`:

| Feature | Status |
|---|---|
| Landscape letter, framed viewports | ✓ implemented |
| Black header/footer bands, cream paper, gold #b8912f, ink #20241f | ✓ palette (line 87), bands implemented |
| Uppercase letterspaced type | ✓ via `ls_text` |
| "FOR DISCUSSION — NOT FOR CONSTRUCTION" footer disclaimer | ✓ required by b2_qc gate 3 (line 1227-1270) |
| Layout-math row | ✓ exists — rendered separately (`_render_layout_math`, line 1933); not inside the viewport frame |
| Notes / assumptions block | ✓ required by EMPIRE_DRAWING_STANDARD.md rule 1 |
| Title column (right side) | ✓ implemented |
| **Serif display type** | ✗ — Helvetica only (`ls_text` line 263); `parametric_renderer.py:38` uses "Arial, Helvetica, sans-serif". No Times/Playfair/Garamond references anywhere in `services/drawing/`. |
| **Gold corner tabs on viewports** | ✗ — no tab/gold-corner markers in renderer |
| **Three-column FIELD DATA / TREATMENT / FIELD CHECK base band** | ✗ — base band is a single NOTES/ASSUMPTIONS column |
| **Gold status strip** | ✗ — gold exists as a colour; "FOR DISCUSSION" lives inside the black footer band, not on a dedicated gold strip |
| **Layout-math row inside the viewport frame** | ✗ — currently rendered as a separate row in the title column |

`EMPIRE_DRAWING_STANDARD.md` v1.0 (the project's binding standard) calls
for "Helvetica family only" — explicitly sans-serif. The McLean/Whittington
format would replace, not extend, that choice. **None of the six
McLean/Whittington-specific items above is currently implemented in the
renderer.**

The current binding gold is `reports/2026-07-26_golden_reference_v10.pdf`
(Roman-shades-only) per CLAUDE.md — there is no McLean/Whittington
golden reference PDF in the repo, and no v11/pitch drapery golden.

## Findings to rule on at STOP 1

1. **Field data: 0/15 fields** (3 openings × 5 dims). All W1/W2/W3
   dim fields are PENDING per the directive's PENDING rule. The set
   must still build.
2. **`+0.72` finding: NEGATIVE.** The live renderer does not emit the
   nudge; only the negative fixture test (`b2_qc` line 1381) describes
   a PDF that would fail. No QC failure predicted from this axis.
3. **Bench renderer gap:** the bench family has no B2 vector renderer.
   A bench sheet emitted today goes through the B1 textual preview path,
   which `printer.py:349` excludes from `b2_qc`. STEP 2's claim of
   "per-sheet QC gate pass" requires either (a) a bench B2 vector
   renderer, or (b) a founder ruling on what "QC green" means for a
   bench sheet on the B1 path. As-is, STEP 2's bench rows will report
   "QC not applied" — not a pass.
4. **McLean/Whittington format:** none of the six distinctive features
   is implemented. Implementing them is a renderer rewrite, not a
   parameter tweak. Founder ruling needed: build to existing B2 gold
   (v10) or build to McLean/Whittington (significant new code).
5. **Renderer identification:** drapery = `drapery_render.py:640
   render_drapery` (vector, QC-gated). Bench = `bench_curved.py:47
   BenchCurvedTemplate` (geometry only; B1 story path; QC skipped).
   These are the two real files building sheets on this job. Other
   same-name functions are not separate renderers.

🛑 **STOP 1.** Awaiting founder ruling on items 1-5 before STEP 1.