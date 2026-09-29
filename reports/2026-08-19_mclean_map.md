# P1-T·a — McLean Reference Map (2026-08-19)

Read-only mapping of `reference/mclean/mclean_drapery_set_generator.py`
(1,201 lines, md5 `181eb61df2ccfbf4b5802d606d4cf436`) and
`McLean_Whittington_Drapery_Elevations_RevA.pdf` (md5
`f882144aefc03745533fdaae95ea86b4`, parked at `/data/reference/mclean/`,
**not** in the repo per founder ruling).

Reference job: McLean / Whittington Design. Window & Drapery field
measurement set. 9 rooms, 11 sheets (cover + 9 room elevations +
schedule), RevA 19 Aug 2026.

Fonts verified (REQUIRED FIRST CHECK): DejaVu Sans / Sans Mono / Serif
all resolve via fontconfig to `/usr/share/fonts/truetype/dejavu/*.ttf`.
Metrics are trustworthy.

---

## §1 LAYER MAP

Every function classified per dispatch categories.

### CHROME (reusable on every document type)

| Symbol | Lines | Role |
|---|---|---|
| `_font()` | 71-76 | Truetype loader + LRU cache. Maps `(font, bold, italic)` → file. Pure font-resolution primitive. |
| `tw()` | 79-82 | Advance-width measurement (letter-spacing included). Used by every text primitive. |
| `PLACED` | 85 | Module-level list — text bbox capture at draw time. **THIS IS THE AMENDMENT-5 PLACED LIST** in its original form. Must be reset per sheet (currently done in `build()` line 1168 — note: per the new engine this becomes sheet-scoped state inside the builder, not module-global). |
| `esc()` | 88-89 | XML entity escaping. |
| `T()` | 92-106 | Text primitive. Emits `<text>` SVG. **`track=True` records bbox into `PLACED`** — this is the draw-time-bbox mechanism that Amendment 5 mandates we retire the parse-back for. |
| `RECT()` | 109-112 | Rect primitive. |
| `LINE()` | 115-118 | Line primitive. |
| `hdim()` | 121-130 | Horizontal dimension primitive (slash ticks, architect style). |
| `vdim()` | 133-147 | **Vertical dimension primitive — breaks line at mid-height, number horizontal** (Amendment 6 doctrine). This is the proven implementation we must port. |
| `VDIM_GUTTER`, `VDIM_STEP` | 150-151 | Vertical-dimension gutter/stack-pitch constants. Per Amendment 6 "port that sizing logic, do not reinvent it." |
| `page()` | 774-777 | SVG page wrapper. |
| `wrap()` | 780-789 | Text word-wrap utility. |

### CHROME-SHEET (header band + footer band + chrome per sheet)

| Symbol | Lines | Role |
|---|---|---|
| `chrome(sheet_no, total, right_title)` | 748-771 | Renders full header band (letterhead, divider line, powered-by, client, sheet number, rev+date, gold rule) and footer band (letterhead · powered-by · locale, status, sheet / total, gold rule). **NOTE: this still prints `POWERED BY EMPIRE WORKROOM` in BOTH header and footer (lines 755 and 765)** — Amendment 1 says the footer drops it. Header keeps it. |
| `JOB` dict | 158-170 | Single source of all job-level constants (letterhead, locale, rev, date, status). Per Rule 1 of the standard: every sheet reads from this. |

### BAND (reference band: photos | data | check)

| Symbol | Lines | Role |
|---|---|---|
| `VP`, `BAND` | 795-796 | Sheet-layout geometry constants — drawing viewport box + reference-band box. **Per-ROOM (varies by `room_sheet()`), not per-content-family.** |
| `section()` | 799-806 | Section-header primitive (draws gold rule + MONO-bold label that shrinks to fit width). Used by both data zone and field-check zone. |
| The reference band itself | 861-943 (inside `room_sheet`) | Three-zone band: photos (left) | field data (center) | field check (right). Layout depends on photo widths + DATA_W. **This is the BAND layer — must become a separate function for reuse across room sheets.** |

### BODY (elevation viewport — drawing the room's openings)

| Symbol | Lines | Role |
|---|---|---|
| `room_sheet(r, no, total)` | 809-950 | The complete room sheet. Composes: chrome → title block → viewport frame → panel draws → layout-math → reference band → fabric strip. **This is a BODY function** (per-room). The viewport-layout math (lines 821-849, computing k scale, pad_l/pad_r gutters from `nright` and `has_h`) is the part that the dispatch says "port that sizing logic". |

### CONTENT (window-opening panel renderer — family-specific)

| Symbol | Lines | Role |
|---|---|---|
| `resolve_items(p)` | 603-616 | Distributes untagged items evenly in panel width. CONTENT utility (panel). |
| `draw_panel(p, ox, oy_floor, k)` | 619-744 | The single content renderer. Handles windows (with `inner` for unit+glass), doors, fireplaces, ghost walls, top-band (moulding), bottom band, dimensions, hatched unknown sill. **This is the CONTENT layer** — must become `content/window_openings.py` per dispatch. Family-specific (window/door/fireplace), not general. |

### CONTENT (cover + schedule — sheet-level content)

| Symbol | Lines | Role |
|---|---|---|
| `cover(total)` | 954-1067 | Cover sheet. Job block (left) + sheet index + open items at a glance + legend strip. **Counts `wins = sum(1 for p in r["panels"] for i in p.get("items", []) if i["kind"] == "window")` (line 1012-1013) but reports `str(sum(r[2] for r in SCHEDULE))` (line 1017) — DIFFERENT DERIVATIONS, this is the 21/22 split bug Amendment 4 targets**. |
| `schedule_sheet(no, total)` | 1071-1126 | Schedule sheet. `tot = sum(r[2] for r in SCHEDULE)` (line 1096) — derived from SCHEDULE only. **Independent of `cover()`'s count → Amendment-4 violation.** |

### GATES

| Symbol | Lines | Role |
|---|---|---|
| `gates()` | 536-599 | Six pre-emit closure gates (item fit, overlap, dim-runs-inside-panel, dim closure, schedule agrees with drawn, one rev). **`sched = sum(q for row in SCHEDULE for q in [row[2]])` (line 593) is broken — `for q in SCHEDULE` is `for _ in SCHEDULE`; the inner `[row[2]]` extracts only one row's qty. The next line re-does it correctly. Lines 592-593 are dead code.** Note: gates report closure failures (not invented), but do NOT call out the 21/22 cover-index split. **Amendment-4 gate is INFO-only and "emitted anyway" per dispatch audit.** |
| `gate_bounds(placed, frame=16.0)` | 1130-1135 | Text bbox out-of-page check. |
| `gate_collisions(placed, tol=1.2)` | 1138-1149 | Text bbox pairwise overlap check. |

### BUILD (orchestration)

| Symbol | Lines | Role |
|---|---|---|
| `build(out_path)` | 1152-1197 | Runs gates, calls each sheet builder with `PLACED.clear()` between sheets, runs text gates, emits via cairosvg → pypdf. **Uses `sys.exit(1)` on failure (Amendment-C: must be replaced with structured refusal `SpecIncomplete(missing=[...])` or `GateReport(failures=[...])` for MAX orchestration). Mutates module-global `PLACED` between sheets (Amendment: builders must be pure and independently callable; state must be sheet-scoped inside the builder).** |
| `if __name__ == "__main__"` | 1200-1201 | Hardcoded `out_path = "/mnt/user-data/outputs/..."`. |

### Resists classification

- **`chrome()` writes `POWERED BY EMPIRE WORKROOM` in BOTH header band and footer band.** Per Amendment 1 the footer drops it. This is a per-line tweak inside an otherwise-reusable chrome — the layering will fight back here unless we pass an option to chrome (e.g., `footer_drops_poweredby=True` for the new engine) or split into two chrome helpers (header-chrome + footer-chrome with their own rules).
- **`JOB["poweredby"]`** is referenced from `chrome()` line 755 (header) and line 765 (footer). The data lives in JOB; the display decision lives in chrome. Cross-layer.
- **`PLACED.clear()` inside `build()`** is the boundary between "builder is pure" and "build() is impure". The new engine must move PLACED inside each sheet builder (or pass an explicit accumulator) to satisfy Amendment-C (pure builders).
- **`schedule_sheet()` and `cover()` independently count openings.** This is the Amendment-4 defect. The layer split (CONTENT vs sheet-level) makes this *easy* to fix (one derivation function `count_openings(spec)` consumed by both); the reference has them embedded inside their respective sheet functions. The split will require extracting the count derivation.

---

## §2 ENVIRONMENT

### Hardcoded paths

| Path | Line | Role | Notes |
|---|---|---|---|
| `/usr/share/fonts/truetype/dejavu/` | 53 | Font directory | **VERIFIED exists on EmpireDell; all three faces resolve via fontconfig.** |
| `/home/claude/ph/` | 500 (`PHOTO_DIR`) | Source photo directory | **NOT a founder-approved path — looks like a sandbox assumption from a previous session.** Per Amendment 7 photos are per-job upload; the path should come from the job spec / asset intake, not be a module-level constant. |
| `/mnt/user-data/outputs/` | 1158, 1201 | Output PDF path | **NOT a founder-approved path.** `/mnt/user-data/` doesn't exist on EmpireDell (data lives at `/home/rg/empire-data/` and `/data/`). This will crash on `build()` here. Must be parameterized. |
| `/usr/share/fonts/truetype/dejavu/` | 53 | (same as above) | — |

### Sandbox assumptions

| Assumption | Line | Notes |
|---|---|---|
| `cairosvg` installed | 21 | SVG → PDF conversion. Must be in requirements. |
| `pypdf` installed | 22 | PDF merging / metadata. Must be in requirements. |
| `PIL` (Pillow) installed | 51 | `ImageFont.truetype` + `Image.open`. Must be in requirements. |
| `base64` stdlib | 522 | (stdlib, fine.) |
| `cairosvg.svg2pdf(dpi=72)` produces letter-sized output | 1184 | Implicit. |
| Output directory `/mnt/user-data/outputs/` exists & writable | 1158 | **Will fail here.** |
| PHOTO_DIR `/home/claude/ph/` exists & readable | 522 | **Will fail on EmpireDell.** The reference's `photo()` function has `with open(PHOTO_DIR + fn, "rb")` — a hard `open()` call, no graceful missing-photo handling in the open path (note: Laundry has empty PHOTOS list `[]` and the rendered band handles it via the `if not fitted` branch on line 903 — but that's only because PHOTOS["LA"] is `[]`. If PHOTOS["FD"] pointed to a missing file, `photo()` would crash on line 523. **The dispatch's "no crash" requirement is NOT met by this reference.** |
| All 9 PHOTOS exist at PHOTO_DIR | 502-512 | (Same.) |

### Fonts — VERIFIED

```
DejaVu Sans      → DejaVuSans.ttf        (Book)
DejaVu Sans Mono → DejaVuSansMono.ttf    (Book)
DejaVu Serif     → DejaVuSerif.ttf       (Book)
```

Bold / Italic / BoldItalic variants all map to existing `.ttf` files in
`/usr/share/fonts/truetype/dejavu/`. The reference's `_FACE` dict
(Lines 54-67) is a faithful map of the directory.

---

## §3 DUPLICATION — every place a number is typed twice

| Number | First typed | Second typed | Notes |
|---|---|---|---|
| `99"` (Formal Dining opening width) | Line 181 (`"w": 99.0`) | Line 182 (`"99\""` in `dims_top`) | **Both occurrences are derived from the same logical source — the field sheet.** Acceptable per Rule 1, but `dims_top` could be computed from `items[0].w`. |
| `99"` (Living Room right wall window) | Line 288 (`"w": 99.0`) | Line 289 (`"99\""` in `dims_bot`) | Same pattern. |
| `187"` (Living Room left wall overall) | Line 265 (`"w": 187.0`) | Line 273 (`"187\" OVERALL"` in `dims_bot`) | Same. |
| `222"` (Living Room center wall overall) | Line 276 (`"w": 222.0`) | Line 281 (`"222\" OVERALL"`) | **THIS IS THE TAGGED OVERALL vs PARTS SUM.** Per Amendment 2 the parts sum (225") wins. **The reference does not enforce this — both numbers are typed, the 222 stays on the sheet but is the WRONG number for the wall geometry. McLean RevA printed 222 in the center wall elevation AND 225 in the LAYOUT MATH; the dispatch says "the build continues" with the parts sum.** |
| `110.25` (ceiling heights — FD, FLB, FLR, FR, KD, OF, LA, PR) | Lines 180, 207, 239, 287, 318, 326, 358, 386, 430, 461 | — | **Typed once per room. No cross-room derivation.** (Per Rule 1 a single source would be cleaner, but no double-typing here.) |
| `110½"` rendered as `110\u00bd"` | Lines 207, 239, 287, etc. (8+ rooms) | — | **Repeated text — fine, the rendered form is the canonical one and `wrap()` handles wrapping.** |
| `114¼"` rendered as `114\u00bc"` (Living Room left/center walls) | Lines 274, 282 | — | Same. |
| `106"` (bottom of moulding) | Lines 215, 240 | — | Repeated for FLB and FLR. Cross-room but each room has its own value source. |
| `12 ft` (FR runs) | Lines 319, 329, 335 | — | Same nominal value, three rooms in the same set. Not double-typed as a number, just as a phrase. |
| `43"` (FLR, FR, LA, PR window widths) | Lines 241, 320, 432, 462 | — | **Four rooms carry a `43"` window.** Amendment 4 says "every quantity appearing in more than one place in a set is computed once" — these are FOUR PLACES but each is a per-room field measurement, not a duplication of a quantity (it's "the same value happens to recur in four rooms" not "the same value was typed twice"). Acceptable. |
| `27"` (FLB bay sashes; LRB-1 windows) | Lines 208-211 (FLB), 266-268 (LRB-1) | — | Same — two rooms. Not a duplication. |
| `15"` overhead (LA, PR) | Lines 428, 458 | — | Same. |
| `110¼"` = `110\u00bc"` ceiling heights (5 rooms) | Lines 207, 287, 318, 358, 386, 461 | — | The literal string `110\u00bc"` is typed six times. **This IS a real duplication candidate** — one constant `_CEILING_HEIGHT_FLAT_IN = 110.25` would express the intent. |
| `43\" × 79\"` window dims (LA, PR) | Lines 428, 462 | — | Same — duplicated literal. |
| Cover-index count derivation | Line 1012-1013 (counts drawn windows) vs Line 1017 (sums SCHEDULE qtys) | — | **THE AMENDMENT-4 BUG.** `cover()` derives one number from the rooms; `schedule_sheet()` derives another from SCHEDULE. They disagree in McLean RevA (21 vs 22). Per Amendment 4 the new engine must have ONE `count_openings(spec)` derivation consumed by both. |
| Open items list | Lines 1032-1038 (cover `OPEN AT A GLANCE`) and lines 1105-1117 (schedule `OPEN BEFORE QUOTING`) | — | **Both sheets enumerate the same set of founder-action items.** Per Amendment-4 spirit this should be one derivation (`collect_open_items(spec)`) consumed by both. The two lists aren't byte-identical (cover is more terse, schedule is more verbose) but they enumerate the same set. |
| Letterhead string "NELMA'S WORKROOM" | Lines 164 (JOB dict), 752 (chrome header), 765 (chrome footer) | — | Typed 3× in the source. Acceptable: JOB is the single source, chrome reads it. |
| `POWERED BY EMPIRE WORKROOM` | Lines 164 (JOB), 755 (chrome header), 765 (chrome footer) | — | Typed 3×. **Amendment 1 says footer drops this; JOB entry is still needed for the header.** |
| Locale string `"HYATTSVILLE MD"` | Line 165 (JOB), 766 (chrome footer) | — | 2×. After Amendment 1 the footer letterhead zone renders the full address `"5124 FROLICH LN · HYATTSVILLE MD 20781"` (a 3-part address). The locale alone won't appear in the footer; the full address is the new single source. **The reference needs the address amended in the spec / chrome footer.** |
| Status string `"FOR DISCUSSION - NOT FOR CONSTRUCTION"` | Line 169 (JOB), 767 (chrome footer) | — | 2×. OK. |
| Sheet dimensions `PW=792, PH=612` | Line 25 | — | Once. OK. |

---

## §4 D-R3 AUDIT — 6 items confirmed against source

| # | Question | Status | Evidence |
|---|---|---|---|
| 1 | Are grommet / rod_pocket constants PRINTED on the notes block marked ASSUMED — FOUNDER VERIFY? | **NO** (silently missing). The constants exist in source (`drape_render.py` lines 62-63) and are marked `# ASSUMED — FOUNDER VERIFY` *in code comments* — but `_get_assumptions` in `b2_renderers.py` lines 1942-1983 builds the NOTES block content from `{Slat, Mount, Fabric}` keys, not from heading. **The notes block does NOT include a "grommet / rod_pocket ASSUMED — FOUNDER VERIFY" row.** A founder viewing the sheet sees no warning that two of the four supported heading styles are running on ASSUMED constants. **This is an invented-constant-without-warning defect; per Rule 1 / Rule 2 of the standard, the notes block MUST print the warning.** |
| 2 | Does each heading style set its own DRAPE_PROJECTION_IN entry? | **YES.** `drapery_render.py` line 59-63: `pinch_pleat=(2.0,3.0)`, `ripplefold=(3.5,4.5)`, `grommet=(3.0,4.0)`, `rod_pocket=(2.5,3.5)`. Used at line 397 in the side-section depth lookup. All four entries exist. |
| 3 | Unknown SKU → neutral gray + "FABRIC: TBC — CONFIRM BEFORE CUT"? | **YES** for the elevation (line 243-244 sets `fabric_color = #9aa0a3` neutral gray). **YES** for the NOTES block (`b2_renderers.py` line 1958-1959: `if not is_known(fabric_sku): out.append(fallback_label())` and `_fabric_reg.fallback_label()` returns `"FABRIC: TBC — CONFIRM BEFORE CUT"`). Both paths handled. |
| 4 | Spec-level hex override, pattern field, repeat direction drawn per orientation, orientation printed in the title column? | **Partial.** `fabric_registry.Fabric` carries `base_color_hex`, `pattern_class` (floral/geometric/solid/texture/stripe), `width_in`, `repeat_in`, and (D-R3-4) `orientation` + `source_url`. The title column shows `orientation` row (`b2_renderers.py` line 768-769). **MISSING: pattern field rendered as motif marks (only `solid` is rendered — `drape_render.py` uses `fabric_color` directly without branching on `pattern_class` for motif decoration). MISSING: repeat direction drawn per orientation — the renderer does not flip motif repeat for railroaded fabric. MISSING: spec-level hex override (a `spec["fabric_hex"]` field would let the founder/client specify a custom color for an unknown SKU; currently unknown SKU always uses neutral gray). **Three of four sub-items implemented; one (motif rendering) is missing.** |
| 5 | Does DETAIL A carry a spacing dimension and a stated magnification? | **YES.** `drape_render.py` line 614 header: `f"DETAIL A — PLAN VIEW ({mag:.1f}× · pleat {pleat_real_w:.1f}\" real)"` — magnification stated. Lines 627-635 draw a spacing dim between two adjacent pleats with `gap_sheet:.2f\"` label. **Both present.** |
| 6 | Does the sail negative fixture still trip on plumb/uniform ONLY? | **YES (verified).** Ran the fixture through `enforce_b2_qc` — first failure is `B2 QC (drapery-plumb) FAIL: top-band avg depth = 0.618" (sheet), bottom-band avg depth = 0.378" (sheet) (ratio 38.8% > 15%); drape TAPERS (must be uniform)`. The sail-shape defect is caught by `drapery-uniform-depth` (top-band vs bottom-band ratio). Other gates pass first. The fixture passes the strict assertion. **NOTE:** my initial map draft said "regressed by chance" without checking. Verified it is correct — updating the audit fold-in below. |

---

## RESISTS CLASSIFICATION — items the layering will fight

(See §1 "Resists classification" for the structural fights.)

## AUDIT FOLD-IN SUMMARY

| D-R3 audit item | Status |
|---|---|
| 1 — grommet/rod_pocket PRINTED marked ASSUMED | **FAIL** (silent missing in NOTES block) |
| 2 — each heading has its DRAPE_PROJECTION_IN entry | PASS |
| 3 — unknown SKU → neutral gray + "FABRIC: TBC — CONFIRM BEFORE CUT" | PASS (both elevation + NOTES) |
| 4 — spec hex override / pattern field / repeat-direction / orientation printed | **PARTIAL** (orientation printed; pattern field exists but not rendered; repeat direction not flipped per orientation; spec hex override absent) |
| 5 — DETAIL A spacing dim + stated magnification | PASS |
| 6 — sail fixture trips plumb/uniform ONLY | **PASS** (verified — fires `drapery-uniform-depth` cleanly) |

**One D-R3 audit item failed (1).** Item 1 is a silent defect — the
sheets print, the tests pass, the founder sees no warning. Item 6 was
corrected after verifying against the live fixture.

---

🛑 **STOP — P1-T·a map complete.**

Awaiting founder go-ahead for **P1-T·b · SEPARATE THE LAYERS** (build
`backend/app/presentation/template/{chrome,band,body,content,gates,
spec,assemble}.py` per the dispatch layering).
