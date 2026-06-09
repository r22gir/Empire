# Drawing Quality Standard

**Status:** Read-only planning document. No code changes.
**Date:** 2026-06-08
**Author:** Empire Completion Coordinator
**Purpose:** Define the three drawing-quality tiers Empire Workroom will produce, plus the acceptance criteria for each, so Drawing Quality Sprint 2 has a measurable target.

---

## 1. Three drawing tiers

Every drawing produced by the Empire Drawing Studio will be one of three types. The renderer accepts a `drawing_type` parameter (or derives one from the request context) and produces the corresponding output.

### 1.1 Client Presentation Drawing

**Audience:** Client, prospect, designer. Used in sales conversations, in design reviews, and in proposal PDFs.

**Required elements:**
- Large title block (≥ 30% of the right edge of the page) with:
  - Company logo (Empire Workroom or Empire Woodcraft, distinct)
  - Project name, client name, date
  - Item name + item type
  - Drawing number, revision letter
  - Scale indicator (1:20, 1:50, 1:100)
  - "Client Presentation" badge
- Three views minimum for soft goods (plan, front, isometric)
- Two views minimum for hard goods (plan, front)
- Clean line work: outer edges ≥ 1.5pt, inner edges ≥ 1.0pt, hidden lines dashed
- **No measurements** on the drawing itself (measurements in the proposal document, not on the drawing)
- Material legend: fabric name, fabric SKU, wood species, finish — when known
- Color: full color where it helps (wood tones for millwork, fabric tones for upholstery); monochrome acceptable for soft-goods top-view
- Annotation callouts: cushion labels (numbered), welt/skirt/leg callouts, channel count, zipper placement — when applicable
- "Not to scale" if any dimension is assumed
- "Assumed dimension" tags on any measurement the user did not provide explicitly
- The drawing fills at least 70% of the page area
- "This is a presentation drawing. See shop drawing for fabrication details." footer

**Disallowed:**
- Measurement numbers in inches or cm on the drawing
- Fabrication hardware callouts (those belong on the shop drawing)
- Internal model numbers or cost information

### 1.2 Shop / Fabrication Drawing

**Audience:** Workshop, fabricator, upholsterer. Used to actually build the item.

**Required elements:**
- Same title block format as the client presentation, with:
  - "Shop Drawing" badge
  - Drawing number, revision letter (different from presentation drawing)
  - All dimensions **in both inches and centimeters** (with the larger unit in bold)
- Three views minimum, with dimensions on each view
- **Dimension callouts:**
  - No overlap with each other
  - No overlap with labels
  - No overlap with title block
  - All dimensions labeled with the unit suffix ("24 in" not "24")
- Assumed-dimension warnings: explicit "(assumed)" tag with a note pointing to the model parameter that was inferred
- Material legend: full materials list with SKUs and supplier
- Hardware schedule: list of all hardware (springs, foam density, frame material, webbing) with line-item cost
- Cut list or fabric yardage estimate, with the source quote number
- Tolerance callouts: "±1/8 in" for soft goods, "±1/16 in" for millwork
- "Workroom" or "Woodcraft" badge in the title block (visually distinct, larger than presentation)
- Construction notes panel: list of joinery, edge profile, finishing sequence
- "Not legal advice" disclaimer if the drawing includes government-form-related annotations (rare; mostly for apostille work)

**Disallowed:**
- Marketing copy
- Fabric pattern images (fabric SKU is enough; pattern images go in the proposal)

### 1.3 Measurement-Only Fallback Drawing

**Audience:** Client or prospect who has only rough measurements. Used to get a quote and to show what the item would look like at a high level.

**Required elements:**
- Same title block format as the client presentation, with:
  - "Measurement-Only Drawing" badge (visually distinct from "Client Presentation")
  - "Assumed dimensions" disclaimer in the title block
- Three views minimum (or two for hard goods)
- All dimensions marked "(assumed)" with a different color or shading
- "These dimensions are placeholders. Final quote requires verified measurements." footer
- An "assumed dimensions" list panel: every assumed dimension listed with a placeholder value
- Material legend: empty or "TBD" — make clear nothing is selected yet
- The drawing is intentionally simpler (fewer callouts) to make the "this is not a final design" message clear

**Disallowed:**
- Any annotation that could be mistaken for a commitment (e.g. "wood: walnut" — must be "wood: TBD")
- Any price or cost information

---

## 2. Title Block Specs

### 2.1 Workroom title block (client presentation)

- Background: warm cream (`#FAF6F0`)
- Logo: Empire Workroom wordmark + needle-and-thread icon
- Layout: 4-column grid (logo | project | item | drawing meta)
- Border: thin double-line (2pt outer, 1pt inner)
- Color accent: muted teal (`#2A6F6F`) for the "Client Presentation" badge
- Default size: 320pt wide × 130pt tall
- Position: bottom-right corner, with 20pt margin from page edge

### 2.2 Woodcraft title block (client presentation)

- Background: warm cream (`#FAF6F0`)
- Logo: Empire Woodcraft wordmark + chisel icon
- Layout: 4-column grid (logo | project | item | drawing meta)
- Border: thick single-line (3pt)
- Color accent: warm walnut brown (`#5C3A1E`) for the "Client Presentation" badge
- Default size: 320pt wide × 130pt tall
- Position: bottom-right corner, with 20pt margin from page edge

The two title blocks are **visually distinct**: different logo, different border weight, different accent color, different badge.

### 2.3 Shop drawing title block (Workroom or Woodcraft)

- Same layout as client presentation, but:
  - "Shop Drawing" badge replaces "Client Presentation" badge
  - Larger dimensions panel (right side of title block) with both inches and centimeters
  - Hardware schedule panel below the title block
  - "Not legal advice" disclaimer footer if the drawing references any government forms

---

## 3. Dimension Layout Engine

### 3.1 No-overlap requirement

The dimension layout engine must guarantee that no two dimension labels overlap. Algorithm:

1. Lay out all dimensions naively (current behavior).
2. After the first pass, collect every dimension label's bounding box.
3. If any two bounding boxes overlap, push the lower-priority one away from the higher-priority one along the dimension's perpendicular axis.
4. Priority: outer dimensions > inner dimensions; shop drawing dimensions > presentation dimensions.
5. If a label cannot be pushed without leaving the page, render it in a callout instead of inline (e.g. "see 'A' detail").

### 3.2 No-clip requirement

Every label's bounding box must fit within the page. Algorithm:

1. After layout, check every label's bounding box against the page bounds.
2. If a label clips, the dimension must be re-laid out at a smaller font or a different anchor.

### 3.3 No-truncation requirement

Labels must not be truncated. Algorithm:

1. Render the label at its natural size.
2. If the natural size exceeds the available space, re-render at a smaller font (minimum 9pt).
3. If still too large, split into a callout (e.g. "see detail B").

---

## 4. Material Legend Specs

### 4.1 When to render the material legend

Always, when at least one material is known. If no material is known, render an empty legend with "Materials TBD" text and a count of how many materials are missing.

### 4.2 Format

A horizontal panel below the title block, with one row per material. Each row:

```
[Material name] | [SKU/Code] | [Supplier] | [Color/Finish] | [Cost/Unit] | [Notes]
```

### 4.3 Required materials per item type

| Item type | Materials required |
|---|---|
| bench (upholstered) | Fabric, foam density, frame wood, finish, welt cord, hardware |
| sofa / sectional | Fabric (per cushion), foam density, frame wood, finish, leg material, hardware |
| chair | Fabric, foam density, frame wood, leg material |
| headboard | Fabric, foam density, frame wood, mounting hardware |
| ottoman | Fabric, foam density, frame wood, leg material |
| cushion | Fabric, fill material, welt cord |
| window treatment | Fabric, lining, hardware, mounting |
| millwork (cabinet, desk) | Wood species, finish, hardware, edge profile |
| table | Wood species, finish, hardware, edge profile |

---

## 5. Upholstery Callout Specs

For any upholstered item, render callouts for:

- **Cushion count and labels** — numbered labels on the plan view, with a legend on the side
- **Welt** — callout text "Welt" or "Piping" with a small leader line
- **Skirt** — callout text "Skirt: ___in" with a leader line
- **Legs** — callout text "Leg: [material]" with a leader line
- **Channel count** (channel-back items) — callout text "Channels: N" with a leader line
- **Zipper placement** — small "ZIP" label on the back/bottom of cushion drawings
- **Throw pillows** — labeled separately from seat cushions, with a count

---

## 6. Millwork Callout Specs

For any millwork item, render callouts for:

- **Shelf count and dimensions** — labels on the front view, with a count in the legend
- **Hardware schedule** — list of hinges, pulls, slides, with SKU
- **Edge profile** — small icon + text callout (e.g. "Eased edge", "Bullnose", "Chamfered")
- **Joinery** — small text callout (e.g. "Dovetail", "Pocket screw", "Mortise-and-tenon")
- **Finish** — text callout (e.g. "Polyurethane", "Oil", "Lacquer")
- **Wood species** — text callout (e.g. "Walnut", "Maple", "White oak")

---

## 7. Test / Acceptance Plan

For each acceptance criterion above, a corresponding test should exist. The test pattern is from `test_drawing_repair_sprint_1.py` (read existing tests first, then add).

### 7.1 Required new tests

| Test file | What it covers |
|---|---|
| `test_drawing_quality_sprint_2.py` | Master test file with one assertion per acceptance criterion |
| `test_bench_title_block_workroom.py` | Verify Workroom title block appears on bench PDF |
| `test_bench_title_block_woodcraft.py` | Verify Woodcraft title block appears on Woodcraft items |
| `test_dimension_no_overlap.py` | Verify no-overlap across all renderers |
| `test_dimension_no_clip.py` | Verify no-clip across all renderers |
| `test_assumed_dimension_warning.py` | Verify "(assumed)" tag on inferred dimensions |
| `test_material_legend_present.py` | Verify material legend on upholstered items |
| `test_upholstery_callouts.py` | Verify welt/skirt/leg callouts |
| `test_millwork_callouts.py` | Verify shelf/hardware/edge callouts |
| `test_measurement_only_banner.py` | Verify "Measurement-Only" badge on measurement-only drawings |
| `test_dxf_export_parity.py` | Verify DXF and PDF describe the same item |

### 7.2 Visual snapshot tests (if pytest supports)

If the existing test framework supports visual regression, add a snapshot test for each renderer. The benchmark PDF is the Sprint 1 output; the new PDF should be visibly more polished (title block, callouts, legend).

---

## 8. Do not proceed list (standard phase)

This standard made no code changes, created no branches, ran no tests, and edited no files outside the report outputs. All other repo state is unchanged.
