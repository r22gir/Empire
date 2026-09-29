# Golden-port Corrections G1 → G1.2 — 2026-08-16

**Branch:** `feature/drawing-standard`
**Status:** 🛑 awaiting founder eyeball G1.2 against `reports/2026-07-26_golden_reference_v10.pdf`
**Reference render (v10, DO NOT modify):** `reports/2026-07-26_golden_reference_v10.pdf`
**Reference R1 (DO NOT modify):** `reports/2026-07-26_golden_port_r1.png`
**Corrected R2 (NEW):** `reports/2026-08-16_golden_port_r2.png`

## Summary

5 founder G1 verdict defects, each with: root cause → fix in `b2_renderers.py` → new/extended
gate in `b2_qc.py` → negative-proof fixture in `test_drawing_vector_b2.py`. All 44 B2 tests
pass (was 34/34 → now 44/44 with 10 new G1 tests).

| # | G1 verdict defect              | Fix location                  | Gate location                | Negative fixture          |
|---|--------------------------------|-------------------------------|------------------------------|---------------------------|
| 1 | Elevation under-fills + scale lie | `b2_renderers.py:140-200, 980-1090` | `b2_qc.py:_check_elevation_scale_truth` | `test_gate1_scale_truth_catches_lie` |
| 2 | Fold stack zigzag/coil          | `b2_renderers.py:1438-1460` (R5/R6) | `b2_qc.py:_check_fold_stack_is_flat`    | `test_gate2_fold_stack_catches_zigzag` |
| 3 | Footer missing FOR DISCUSSION   | `b2_renderers.py:_render_footer_band, ls_text` | `b2_qc.py:_check_footer_for_discussion` | `test_gate3_footer_discussion_catches_missing` |
| 4 | Duplicate viewport captions     | `b2_renderers.py:_draw_viewport_frame` | `b2_qc.py:_check_duplicate_viewport_captions` | `test_gate4_duplicate_captions_catches_double` |
| 5 | Title plural + witnesses        | `b2_renderers.py:_render_header_band, _render_front_elevation` | `b2_qc.py:_check_title_and_witnesses` | `test_gate5_title_plural_caught` |

---

## CORRECTION 1 — Elevation under-fills viewport / scale untrue

**Founder verdict (G1):** "The front elevation floats small (~40% fill) in its frame while the
sheet states SCALE 1" = 1'-4". Root-cause first: is the drawn geometry actually at the stated
scale (then the viewport/margins are wrong), or is the geometry shrunk (then the scale stamp is a
lie)? At 1" = 1'-4", 38" of shade must draw at exactly 38/16 = 2.375 sheet-inches wide."

### Found

`b2_renderers.py:_render_front_elevation` and `_render_side_section` both used a **ROOM-fit
scale**:

```python
s = (SIDE_H_IN - 0.6) / (ROOM_CEIL_IN + ROOM_AFF_MARGIN_IN)   # = 0.0496 (5/114)
```

This scaled the geometry to fit the 108" ceiling + 6" margin into the 5.66" inner viewport,
producing `shw_in = 38 * 0.0496 = 1.886"` and `shh_in = 64 * 0.0496 = 3.18"`. The shade
occupied ~40% of the front-elev width while the SCALE row hardcoded the lie "1\" = 1'-4\""
(scale_factor 0.0625, vs the actual 0.0496).

This is the same bbox-class bug as the isometric 44%-fill failure (HOTFIX B2b) — the
viewport fit was computed from the wrong reference frame.

### Changed

1. **`_compute_shade_scale(geo_w, geo_h, viewport_w_in, viewport_h_in, target_fill=0.90)`**
   (new helper) — computes `s` to fit the SHADE (not the room) into the viewport, target_fill
   ≥ 90% on the height-limited axis (shade is taller than wide).

2. **`render_roman_shades_vector`** computes `scale_factor` ONCE and passes it to front-elev,
   side-section, and the title column's SCALE row.

3. **`_render_front_elevation(..., scale_factor=None)`** — uses the shared scale; positions the
   shade CENTERED between the floor and ceiling POSITIONAL indicators (ceiling/floor lines are
   drawn at viewport top/bottom because the room doesn't fit at the shade-fit scale; model
   heights 108"/32" are LABELS, not dim-line measurements).

4. **`_render_side_section(..., scale_factor=None)`** — same shade-fit scale; ceiling/floor
   positional indicators; sill position clamped to ≥ floor (so the lowered ghost stays on-page).

5. **`_format_scale_row(s)`** (new helper) — formats the SCALE row text from the actual scale
   (e.g. `s=0.0796` → `"1\" = 1'-0-9/16\""`). The title column SCALE row uses this — honest.

6. **`_render_title_column(..., scale_factor=0.0625)`** — accepts and uses the shared scale.

### Gate

`_check_elevation_scale_truth(page)` in `b2_qc.py`:

- **(a) Parse SCALE row + DIMENSIONS row** from the title column. Derive `scale_factor`
  (sheet-inches per model-inch).
- **(a) Measure the SHADE-CASING bbox** (the largest rect in the front-elev viewport,
  which is the window casing +0.10" overshoot). Assert drawn_w ≈ real_w * scale_factor +
  0.10 ±1%; same for height.
- **(b) Assert the shade body (casing minus 0.10") fills ≥ 80% of the front-elev viewport on
  AT LEAST ONE AXIS** (height-limited, since the 38×64 shade is taller than wide).

### Evidence

For the corrected R2 (38"×64" shade at scale 0.0796):
- shade body: 3.025"×5.094" → width fill 67%, **height fill 85%** (≥80% on one axis ✓)
- casing bbox: 3.124"×5.194" → matches expected 3.124"/5.194" ±0.4% ✓
- SCALE row reads "1\" = 1'-0-9/16\"" (matches actual scale 0.0796) ✓

Negative fixture `test_gate1_scale_truth_catches_lie`: synthetic PDF with SCALE row saying
"1\" = 1'-4\"" but geometry drawn at 1/32 scale (half the declared) → Gate 1 fires
"B2 QC (scale-truth) FAIL".

---

## CORRECTION 2 — Fold stack is a zigzag, not shingled flat flaps

**Founder verdict (G1):** "The side-section stack renders as a spring/coil. Doctrine: flat
flaps shingle-stacked, front edges plumb (R5); fold tips emerge BELOW a flat fabric face,
never at the board (R6). Reference shows the target: neat horizontal slats, stack 7"
(8 × 7/8")."

### Found

`b2_renderers.py:_render_side_section` (golden-port R1) drew each flap as a **bezier-curved
path**:

```python
p.moveTo(_P(x_back), _P(ytop))
p.lineTo(_P(x_front + 0.05 + jit), _P(ytop - ft * 0.42))
p.curveTo(_P(x_front + jit), _P(ytop - ft * 0.52),
          _P(x_front + jit), _P(ytop - ft * 0.78),
          _P(x_front + 0.05 + jit), _P(ytop - ft * 0.88))
p.lineTo(_P(x_back), _P(ytop - ft))
```

The bezier curves with the same control-x but descending control-y produced a coil/zigzag
visual — exactly the spring defect the founder flagged.

### Changed

Replaced the bezier paths with **flat horizontal rect primitives** (R5+R6):

```python
for k in range(NF):
    ytop = face_bottom_y - k * ft
    col = EMER if (k % 2 == 0) else EMER_ALT
    c.setFillColor(col); c.setStrokeColor(EMER_D); c.setLineWidth(0.4)
    c.rect(_P(x_front), _P(ytop - flap_h),
           _P(x_back - x_front), _P(flap_h),
           fill=1, stroke=1)
```

Each flap is a horizontal rect: top edge (x_front→x_back, ytop), right edge (x_back, ytop→ytop-ft),
bottom edge (x_back→x_front, ytop-ft), left edge (x_front, ytop-ft→ytop — the PLUMB front edge).
`flap_h = ft * 0.95` leaves a 5% gap between adjacent flaps for the shingled look.

### Gate

`_check_fold_stack_is_flat(page, family)` in `b2_qc.py` (Roman Shades only):

1. Find rects in the SIDE viewport with `width > 40pt` (0.55") and `height ∈ [1pt, 15pt]`
   (the flap-aspect heuristic).
2. Sort by area, take the top N=8 by area (the 8 flap rects, not slat-line or hem rects).
3. Assert the front-edge `x0` range is ≤ 2pt (PLUMB).
4. Assert the height range is ≤ 4pt (all flaps same thickness).
5. Find the flat face rect (tall rect > 50pt height, same x-extent as flaps) — its `y0`
   marks the bottom of the flat fabric face. Assert the lowest flap's `y0` is BELOW
   the face bottom (R6: fold tips emerge below the flat fabric face).

### Evidence

Corrected R2: 8 flat horizontal rects visible in side section. Each flap front-edge x = same
(pixel-aligned plumb). Lowest flap's bottom is BELOW the flat-face bottom (R6 honored).

Negative fixture `test_gate2_fold_stack_catches_zigzag`: synthetic PDF with bezier-curved
"flaps" (the R1 defect — no flat horizontal rects) → Gate 2 fires "B2 QC (fold-stack)
FAIL".

---

## CORRECTION 3 — Footer missing "FOR DISCUSSION — NOT FOR CONSTRUCTION"

**Founder verdict (G1):** "The fixed footer is letterhead · FOR DISCUSSION — NOT FOR
CONSTRUCTION · sheet number. The port dropped the center element."

### Found

`b2_renderers.py:_render_footer_band` had the call to draw the center string but TWO
defects caused it to render OFF-PAGE / INVISIBLE:

1. **`ls_text` units bug** (Correction 3 root cause): the `center=True` path computed
   `x -= total / 2.0` where `total` was in POINTS (from `c.stringWidth`) but `x` was in
   INCHES. For a 30-char labelspaced string at 8pt with tracking=1.2:
   - `total ≈ 200 pt = 2.78 inches` (correct value)
   - but the code subtracted `200` from `x=5.5`, producing `x=-194.5` (off the LEFT edge
     of the page)
   - Result: text was rendered at `x ≈ -7700 pt` (far left), invisible.

2. **Color contrast**: `#b25a1d` orange on `#20241f` INK had ~2:1 contrast — effectively
   unreadable in rasterized PNG even when positioned correctly.

3. **Address too long**: the B2d-era footer had the full street address
   "EMPIRE WORKROOM · 5124 Frolich Ln, Hyattsville, MD 20781 · (703) 213-6484" (~55 chars),
   which would overlap the centered "FOR DISCUSSION" string at any reasonable font size.

### Changed

1. **`ls_text`** — fixed units bug: `x -= total_in / 2.0` where `total_in = total_pt / 72.0`
   (convert points to inches). Same fix for `right=True` path. Now center-anchored text
   lands where it should.

2. **`_render_footer_band`** — brightened the orange to `#e88a2c` for legible contrast on
   INK band.

3. **`_render_footer_band`** — shortened the letterhead to match the golden v10:
   `"EMPIRE WORKROOM · HYATTSVILLE, MD · (703) 213-6484"` (~45 chars, leaves ~0.8" gap to the
   centered FOR DISCUSSION string).

### Gate

`_check_footer_for_discussion(page)` in `b2_qc.py`:

- Footer band y-range (pdfplumber BL coords, MARGIN_IN*72 to (MARGIN_IN+FOOTER_BAND_H_IN)*72).
- Footer center x-range: 30% to 70% of page width (tolerant — the 8pt letterspaced
  "FOR DISCUSSION — NOT FOR CONSTRUCTION" spans roughly 35%–65% at the page center).
- Tolerant regex match: `re.search(r'FOR\s+DISCUSSION', text, re.IGNORECASE)`.

### Evidence

Corrected R2 footer (visible in `reports/2026-08-16_golden_port_r2.png`):
- LEFT: "EMPIRE WORKROOM · HYATTSVILLE, MD · (703) 213-6484"
- CENTER: "FOR DISCUSSION — NOT FOR CONSTRUCTION" (orange)
- RIGHT: "SHEET B2 · 1 OF 1"

Negative fixture `test_gate3_footer_discussion_catches_missing`: synthetic PDF with footer
containing ONLY letterhead + sheet number (no FOR DISCUSSION) → Gate 3 fires
"B2 QC (footer-discussion) FAIL".

---

## CORRECTION 4 — Duplicate viewport captions

**Founder verdict (G1):** "Viewport titles (FRONT ELEVATION, SIDE SECTION, TITLE BLOCK)
render twice — top of frame per doctrine, plus stray small captions at the bottom. Remove
the bottom set."

### Found

`b2_renderers.py:_draw_viewport_frame` drew each viewport frame AND a letterspaced label
at the bottom-left corner:

```python
_draw_letterspaced_string(c, label_text, label_x_in, label_y_in,
                          font="Helvetica-Bold", size=7.5, extra_pts=0.8, fill=INK)
```

The per-viewport renderers (`_render_front_elevation`, `_render_side_section`) ALSO drew
the canonical top-of-frame label. The result: "FRONT ELEVATION" appeared at top-of-frame
AND at bottom-left; same for "SIDE SECTION". The title column had only the bottom-left
label (no top label).

### Changed

Removed the bottom-left letterspaced label call from `_draw_viewport_frame` (kept the
4-line frame). The per-viewport top-of-frame label is the single canonical caption.

The title column viewport has no caption at all — its content (PROJECT/CLIENT/FAMILY
rows) identifies it visually.

### Gate

`_check_duplicate_viewport_captions(page)` in `b2_qc.py`:

- For each of `("FRONT ELEVATION", "side viewport")` and `("SIDE SECTION", "front
  viewport")`: find chars in the viewport bbox, group by y (LINE_Y_TOL_PT=2pt), scan
  each line for the needle substring (tolerant of whitespace via `re.sub(r'\s+', ' ')`).
- Assert exactly 1 match per viewport.
- Note: the gate works around `ls_text`'s char-by-char drawing by grouping chars into
  "lines" using y-tolerance, since pdfplumber's `extract_words` can't bridge the
  letterspacing gap.

### Evidence

Corrected R2: each viewport title appears exactly once (top-of-frame label only).

Negative fixture `test_gate4_duplicate_captions_catches_double`: synthetic PDF with TWO
copies of "FRONT ELEVATION" (top + bottom, the R1 defect) → Gate 4 fires
"B2 QC (duplicate-captions) FAIL".

---

## CORRECTION 5 — Title + witness integrity

**Founder verdict (G1):**
> (a) Sheet title must read FLAT FOLD ROMAN SHADE (singular — match the reference and the
>     family nomenclature exactly).
> (b) The elevation's dimension witnesses (38" bottom, 64" right, 9 @ 7-1/8" left) rendered
>     garbled/rotated-wrong or missing. Restore all three, anchored to the geometry they
>     measure.

### Found

**(a) Title plural**: `_render_header_band` used
```python
big_title = f"{product_type.replace('_', ' ').title()} {family_name}".upper()
```
With `product_type="flat_fold"` and `family_name="Roman Shades"`, this produced
"FLAT FOLD ROMAN SHADES" (plural). Golden v10 and Empire family nomenclature require
singular "FLAT FOLD ROMAN SHADE".

**(b) Witness integrity**: R1 had:
- Bottom "38"" — present but no extension lines (the dim line had tick marks but no
  witness lines from the shade bottom corners to the dim line).
- Right chain "32"/64" SHADE"/12"" — present (rotated) but no extension lines from the
  feature edges to the dim line.
- LEFT "9 @ 7-1/8"" — MISSING entirely (not rendered as a dimension witness).

The dim lines floated without anchoring — the QC dim-witness-borrow gate couldn't catch
this because no two witness lines shared a level (they didn't exist).

### Changed

**(a)** Hardcoded the title to "FLAT FOLD ROMAN SHADE" (singular) per golden v10.

**(b)** Restructured the elevation dimensions in `_render_front_elevation`:

1. **Witness 1 (BOTTOM "38"")** — vertical extension lines from shade bottom corners
   `(sx_in, sy_in)` and `(sx_in+shw_in, sy_in)` DOWN to the dim line at `yd = wall_y_in
   - 0.10`. Dim line spans the shade width. Tick marks at each endpoint.

2. **Witness 2 (LEFT "9 @ 7-1/8"")** — vertical bracket at `xd_left = sx_in - 0.45`,
   spanning the full shade height `sy_in` to `sy_in + shh_in`. Horizontal extension
   lines from shade top-left and bottom-left corners OUT to the bracket. Label rotated
   90° vertical.

3. **Witness 3 (RIGHT "32"/"64" SHADE"/"12"")** — three segments:
   - "64" SHADE" witness: TRUE-SCALED. Vertical extension lines from shade sill and
     head OUT to dim line at `xd_right = wx1_in + 0.40`. Dim line spans the shade
     height.
   - "32"" label: POSITIONAL (floor→sill room height, doesn't fit at shade-fit scale).
   - "12"" label: POSITIONAL (head→ceiling room height, doesn't fit).

### Gate

`_check_title_and_witnesses(page)` in `b2_qc.py`:

**(a) Title** — scan header-band chars (pdfplumber y0 in
`[(PAGE_H-MARGIN-H_BAND)*72, (PAGE_H-MARGIN)*72]`). Assert:
- "FLAT FOLD ROMAN SHADE" (singular) present.
- "FLAT FOLD ROMAN SHADES" (plural) NOT present.

**(b) Witnesses** — scan front-elev viewport chars (x range widened by 0.5" to include
right-side dim line at `xd_right = wx1_in + 0.40`). Assert:
- "38"" present (bottom width witness).
- "9 @ 7-1/8"" present (left fold witness).
- "64"" SHADE" present (right height witness).

### Evidence

Corrected R2:
- Title: "FLAT FOLD ROMAN SHADE" (singular, exact match to golden v10).
- All three witnesses present and anchored to the features they measure.

Negative fixture `test_gate5_title_plural_caught`: synthetic PDF with title
"FLAT FOLD ROMAN SHADES" (plural, the R1 defect) → Gate 5 fires "B2 QC
(title+witnesses) FAIL" with `issue: 'title is PLURAL 'SHADES' (Correction 5a fix)'`.

---

## Test results

**Before this commit (R1):** 34/34 B2 tests passing.
**After this commit (R2):** 44/44 B2 tests passing:
- 34 existing tests (assertions updated to match new footer letterhead format:
  `"EMPIRE WORKROOM · HYATTSVILLE, MD · (703) 213-6484"` instead of full street address)
- 10 new `TestGoldenPortG1Corrections` tests:
  - `test_gate1_scale_truth_passes_on_R2`
  - `test_gate1_scale_truth_catches_lie` (negative fixture for gate 1)
  - `test_gate2_fold_stack_passes_on_R2`
  - `test_gate2_fold_stack_catches_zigzag` (negative fixture for gate 2)
  - `test_gate3_footer_discussion_passes_on_R2`
  - `test_gate3_footer_discussion_catches_missing` (negative fixture for gate 3)
  - `test_gate4_duplicate_captions_passes_on_R2`
  - `test_gate4_duplicate_captions_catches_double` (negative fixture for gate 4)
  - `test_gate5_title_witnesses_passes_on_R2`
  - `test_gate5_title_plural_caught` (negative fixture for gate 5)

**Full B2-related suite:** 197 passed, 5 pre-existing failures unrelated to this commit
(`test_theater_detector_warning_only`, 4 `test_max_drawing_intent` tests — all failing
on the original commit `db98a39` before my changes, per the stash-check).

Test command:
```
cd backend && ./venv/bin/python -m pytest tests/test_drawing_vector_b2.py -v
# 44 passed
```

---

## Commit hashes (after this commit)

| Hash | Description |
|------|-------------|
| `<NEW>` | fix(G1): 5 founder corrections — shade-fit scale, flat flap stack, footer FOR DISCUSSION, dedupe captions, singular title + witnesses |

## Files changed

- `backend/app/services/drawing/templates/b2_renderers.py` — `+150/-45` lines
  - Added `_compute_shade_scale`, `_format_scale_row` helpers
  - Refactored `render_roman_shades_vector` to compute and pass `scale_factor`
  - Refactored `_render_front_elevation`, `_render_side_section`, `_render_title_column`
    to accept `scale_factor`
  - Refactored `_render_footer_band` for shorter letterhead + brighter orange
  - Fixed `ls_text` units bug (center=True / right=True)
  - Replaced bezier-curved flaps with flat horizontal rect primitives
  - Removed bottom-left viewport labels from `_draw_viewport_frame`
  - Hardcoded title to "FLAT FOLD ROMAN SHADE" (singular)
- `backend/app/services/drawing/templates/b2_qc.py` — `+420/-10` lines
  - Imported layout constants from `b2_renderers.py`
  - Added 5 new gate functions + wired into `enforce_b2_qc`
- `backend/tests/test_drawing_vector_b2.py` — `+560/-30` lines
  - Updated 2 header tests for new footer letterhead format
  - Added `TestGoldenPortG1Corrections` class with 10 tests (5 positive + 5 negative fixtures)
  - Added `_make_pile_passes_decorator` helper for negative fixtures

## 🛑 STOP

Awaiting founder eyeball G1.2 against `reports/2026-07-26_golden_reference_v10.pdf`.
Do not start family rollout. Do not regenerate the reference.
