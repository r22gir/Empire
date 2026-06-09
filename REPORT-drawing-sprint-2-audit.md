# Drawing Quality Sprint 2 — Audit Report (Phase 1A)

**Status:** Read-only audit. No code changes, no branches, no pytest.
**Date:** 2026-06-08
**Author:** Empire Completion Coordinator
**Scope:** `backend/app/services/vision/`, `backend/app/routers/drawings.py`, `backend/tests/test_drawing_repair_sprint_1.py`, `backend/app/services/drawing/yardage.py`, `backend/app/services/quote_engine/yardage_calculator.py`

---

## 1. What exists today

### 1.1 Renderers in `backend/app/services/vision/`

| File | Lines | Public surface | Notes |
|---|---|---|---|
| `bench_renderer.py` | 1,181 | `BenchModel`, `Part`, `model_to_parts`, `generate_tiles`, `generate_shop_sheet`, `generate_dxf`, `render_straight`, `render_l_shape`, `render_u_shape`, plus 15+ private `_dim_*` / `_cushion_label` / `_miter_callout` / `_draw_back_style_2d` helpers | The biggest renderer. DXF export is implemented via `ezdxf` (optional, fails gracefully if not installed). |
| `drawing_service.py` | ~1,000+ | `classify_item`, `classify_input`, `render_window`, `render_cushion`, `render_headboard`, `render_furniture_2view`, `render_millwork`, `render_generic`, `render_measurement_diagram`, `generate_drawing`, `_title_block_small` (auto-detects WoodCraft vs Workroom) | The orchestrator. Has a `BRANDING` dict that the title block reads. |
| `parametric_templates.py` | ~600+ | `TemplateDef` dataclass, `get_template_for_style`, `render_template_instance`, `_apply_style_defaults`, `_chair_family`, `_drapery_family`, plus private `_dim_h`, `_dim_v`, `_line`, `_rect`, `_ellipse`, `_text` | The style/parameter system. Imports `product_catalog` for the style enum. |
| `renderer_registry.py` | ~250+ | `RENDERER_MAP` (built dynamically from `product_catalog`), `get_renderer`, `get_business_unit`, `get_title_block`, `get_supported_styles`, `get_all_renderable_types`, `get_catalog_types`, `get_renderer_stats` | Single dispatch point. Returns `render_generic` as fallback. |
| `primitives.py` | ~500+ | `defs`, `esc`, `rect`, `line`, `text`, `circle`, `dashed_line`, `dim_h`, `dim_v`, `leader`, `title_block`, `material_legend`, `view_label`, `svg_wrap`, `cushion_shape`, `hatch_area` | Shared SVG primitives. **Not used by `bench_renderer.py` and `drawing_service.py` — they have their own private copies of the same primitives (`_rect`, `_line`, `_text`, etc.).** This is a major code-quality issue, not just cosmetic. |
| `product_catalog.py` | n/a (read) | `PRODUCT_CATALOG`, `get_business_unit`, `get_styles`, `get_all_types`, `get_total_styles`, `find_type_for_style` | Source of truth for what items exist, what styles each supports, and which business unit (Workroom vs Woodcraft) owns each. |

### 1.2 Router endpoints in `backend/app/routers/drawings.py`

19 endpoints. The full list (from `@router.*`):

```
GET  /drawings/files/{filename}
POST /drawings/bench
POST /drawings/bench/pdf
POST /drawings/bench/dxf           ← DXF export is here, not "hidden"
POST /drawings/yardage
POST /drawings/analyze-sketch
POST /drawings/analyze-furniture
POST /drawings/analyze-furniture/pdf
POST /drawings/assets
POST /drawings/generate
POST /drawings/generate/pdf
POST /drawings/general
POST /drawings/general/pdf
POST /drawings/project-sheet
POST /drawings/project-sheet/pdf
POST /drawings/ai/bench
POST /drawings/ai/bench/pdf
POST /drawings/ai/project-sheet
POST /drawings/ai/project-sheet/pdf
GET  /drawings/catalog
```

**Confirmed:** DXF export **is wired and reachable** at `POST /drawings/bench/dxf` (it uses `ezdxf`, returns 200 if installed, fails gracefully with a warning if not). The Founder's audit hint "DXF export available but hidden" is **partially true** — it's exposed, but the front-end may not surface it.

### 1.3 Tests in `backend/tests/`

| Test file | What it covers |
|---|---|
| `test_drawing_repair_sprint_1.py` | The Sprint 1 stability pass — basic SVG generation, file size bounds, key elements present. |
| `test_drawing_router_plan_mode.py` | Routing behavior in plan mode. |
| `test_drawing_studio_trust.py` | Studio trust signals (presumably about which renderers are authoritative). |
| `test_max_drawing_intent.py` | MAX intent routing to drawing endpoints. |
| `test_max_image_vision_routing.py` | Vision model routing. |
| `test_ollama_vision_router.py` | Ollama-specific vision tests. |
| `test_vision_mmx_cli.py` | MMX CLI integration. |

**No test asserts visual quality, no-overlap, no-clip, or title-block-distinctness.** Sprint 1 was stability only.

### 1.4 Yardage / fabric — where does it actually live?

| File | Role |
|---|---|
| `backend/app/services/drawing/yardage.py` | Drawing-side yardage calculation. |
| `backend/app/services/quote_engine/yardage_calculator.py` | Quote-side yardage calculation (used for pricing). |
| `backend/app/routers/fabrics.py` | Fabric catalog / management. |

**Yardage is connected to drawing output** via `POST /drawings/yardage`, but the bench renderer's output SVG does **not** include a yardage summary on the drawing itself. The bench PDF shows: plan view, isometric, front elevation, title block, dimensions, cushion labels, Workroom branding. It does **not** show: estimated yardage, fabric SKU, materials list, finish schedule. This is a clear gap between drawing output and quote output.

---

## 2. Per-renderer quality score (subjective, based on code reading)

| Renderer | LoC | Quality assessment (1=crude, 5=client-grade) | Code smells |
|---|---|---|---|
| `render_straight` (bench) | ~250+ | **2/5** — has plan, iso, front, title, dims, cushion labels, but no fabric callouts, no material legend, no assumed-dim warnings, no shop notes panel | Stroke widths hardcoded (`SW_MED` constants), no dimension-overlap detection, cushion labels are placeholders |
| `render_l_shape`, `render_u_shape` | similar | **2/5** | Same as straight + harder to keep dimensions clear in non-rectilinear shapes |
| `render_furniture_2view` (sofa/chair/ottoman/table) | ~125 | **2/5** — two-view only, limited detail | Generic wrapper; little item-specific polish |
| `render_window` (31 styles) | ~150 | **3/5** — has style-aware variants via parametric templates | Better than bench because templates are richer |
| `render_cushion` | ~55 | **2/5** | Title block is generic |
| `render_headboard` | ~55 | **2/5** | Title block is generic |
| `render_millwork` | ~100 | **3/5** | Has material-legend support in primitives but doesn't always use it |
| `render_generic` | ~65 | **1/5** — rectangles only, by design | Fallback for everything not in the catalog |

### 2.1 Per-item-type status (the 10 priority types)

| Type | Exists in `RENDERER_MAP`? | Has parametric template? | Has client-grade output? | Action needed |
|---|---|---|---|---|
| **Bench / banquette** | YES (3 styles: straight, L, U) | YES | **No** | **Rewrite `render_straight` (priority 1).** Same for L/U. |
| **Window treatments** | YES (31 styles) | YES | Partial | Polish, add measurements for all 31 styles, add assumed-dim warning |
| **Cushions / pillows** | YES | YES | Partial | Add welt/skirt/zipper callouts; add fabric label |
| **Sofa / sectional** | YES (`render_furniture_2view("sofa")`) | Partial | Partial | Add 3rd view (top), add cushion/leg labels, add fabric callouts |
| **Chair** | YES (`render_furniture_2view("chair")`) | Partial | Partial | Same as sofa |
| **Headboard** | YES | YES | Partial | Add channel/welt/leg callouts; add fabric callout |
| **Ottoman** | YES (`render_furniture_2view("ottoman")`) | Partial | Partial | Add leg callout, fabric callout |
| **Cabinet / millwork** | YES (`render_millwork`) | YES | Better | Add material legend, add shelf callouts, add hardware schedule |
| **Table / desk** | YES (`render_furniture_2view("table")`) | Partial | Partial | Add leg/stretcher callouts, add wood species callout |
| **Other fallback** | `render_generic` | No | No | Keep as fallback; add banner: "Generic rendering — request specific template" |

---

## 3. Why the current bench PDF looks crude — specific causes

1. **Stroke widths are hardcoded** as `SW_MED` and `SW_LIGHT` constants in `bench_renderer.py`, not derived from a "drawing type" parameter. The same width is used for client-presentation, shop, and measurement-only drawings.
2. **No dimension-overlap detection.** The `_dim_h` / `_dim_v` / `_dim_2d_h` / `_dim_2d_v` functions in `bench_renderer.py` (lines 309–393) draw dimension lines at fixed offsets (`offset_y=20`, `offset_x=20`). If two dimensions are close in space, the text can overlap. There's no collision detection.
3. **No clip detection.** Labels are placed at hardcoded offsets and `anchor="middle"`. If a label is wider than the available space, it spills over the SVG canvas edge.
4. **Cushion labels are placeholder positions.** `_cushion_label(parts, cx, cy, num, size=11)` draws a `1`, `2`, `3`… label at the center of each cushion. The label text is not parameterized — there's no "Cushion 1: 24×18, fabric SKU, welt" annotation.
5. **No material legend on bench drawings.** The `material_legend` primitive exists in `primitives.py:320` but is **not used by `bench_renderer.py`**. Bench PDFs have no fabric list, no wood species, no finish.
6. **No assumed-dimension warnings.** If the user only provided width, the bench PDF shows the width but doesn't say "depth assumed 20in, seat height assumed 18in".
7. **No workroom-vs-woodcraft title block distinctness in the bench output.** The `_title_block_small` in `drawing_service.py:221` calls `get_title_block` from the registry, but the `render_straight` function in `bench_renderer.py` does **not** use `_title_block_small` — it has its own title block rendering. Two title-block code paths means they will diverge.
8. **Primitive duplication.** `bench_renderer.py` has its own `_rect`, `_line`, `_text`, `_dim_h`, `_dim_v` functions (lines 270–393). `drawing_service.py` has its own copy. `primitives.py` has the canonical version. Three copies means the SVG output can look subtly different per renderer.
9. **DXF export uses `ezdxf` (optional).** The fallback when `ezdxf` is not installed is a logged warning — the front-end would need to handle the missing-file case. (Not necessarily a problem if the founder always installs `ezdxf` in the venv.)
10. **Shop-sheet vs PDF ambiguity.** `generate_shop_sheet` (line 153) and `generate_drawing` (in `drawing_service.py`) both exist. The bench PDF endpoint calls one of them, but the relationship between shop sheet and shop drawing is unclear in the API surface.

---

## 4. Acceptance criteria (drawn from the audit)

For each renderer to be considered "client-grade":

- [ ] Title block: large, with company logo, item name, item type, project, date, scale, drawing number, revision
- [ ] Workroom vs Woodcraft title blocks are **visually distinct** (different color, different layout, different logo placement)
- [ ] Three views minimum for soft goods (plan, front, isometric); two views minimum for hard goods (plan, front)
- [ ] Dimension callouts: no overlap with each other, no overlap with labels, no overlap with title block
- [ ] Labels: no clipping, no truncation, font size ≥ 10pt at 1:20 scale
- [ ] Assumed-dimension warnings: explicit "(assumed)" tag on any dimension the user did not provide
- [ ] Material legend: fabric SKU, fabric repeat, wood species, finish, hardware — when applicable
- [ ] Upholstery callouts: channel count, welt/skirt/leg, cushion count, zipper placement — when applicable
- [ ] Millwork callouts: shelf count, hardware schedule, edge profile, joinery — when applicable
- [ ] Export parity: PDF and SVG produce the same drawing
- [ ] Test: at least one snapshot/regression test that fails if the SVG content changes unexpectedly

---

## 5. Sample output matrix

| Type | Current status | Needed improvement | Test/sample required |
|---|---|---|---|
| bench (straight) | Sprint 1 stable, looks crude | Title block polish, no-overlap dims, fabric callouts, assumed-dim warnings, channel/welt/skirt/leg annotations | `test_bench_no_overlap.py`, `test_bench_title_block_workroom.py`, `test_bench_title_block_woodcraft.py`, visual snapshot |
| bench (L-shape) | same | same + 2D collision detection for non-rectilinear geometries | `test_bench_l_shape_collision.py` |
| bench (U-shape) | same | same + even harder collision detection | `test_bench_u_shape_collision.py` |
| window treatment | 31 styles, partial polish | Assumed-dim warnings, fabric callouts, all 31 styles snapshot-tested | `test_window_all_styles.py` |
| cushion | Generic title block | Welt/skirt/zipper callouts, fabric label, dimensions in cm and inches | `test_cushion_callouts.py` |
| sofa / sectional | 2-view only | Add 3rd view (top), cushion/leg labels, fabric callouts, dimensions in cm and inches | `test_sofa_three_view.py` |
| chair | same as sofa | same as sofa | `test_chair_three_view.py` |
| headboard | Generic title block | Channel/welt/leg callouts, fabric callout | `test_headboard_callouts.py` |
| ottoman | Generic | Leg callout, fabric callout | `test_ottoman_callouts.py` |
| cabinet / millwork | Better, has material legend support | Always render material legend, add shelf callouts, add hardware schedule | `test_millwork_legend.py` |
| table / desk | Generic | Leg/stretcher callouts, wood species callout, dimensions in cm and inches | `test_table_callouts.py` |
| generic fallback | Rectangles only | Add a "Generic rendering — request specific template" banner | `test_generic_fallback_banner.py` |

---

## 6. Branch / Worktree Proposal

- **Branch:** `feature/drawing-quality-sprint-2`
- **Worktree:** `/home/rg/empire-repo-main-drawing-sprint-2` (new, from `main` HEAD `2867978`)
- **Files to touch (priority order):**
  1. `backend/app/services/vision/bench_renderer.py` — rewrite `render_straight` first, then `render_l_shape`, then `render_u_shape`
  2. `backend/app/services/vision/drawing_service.py` — add dimension-overlap detection helper, used by all renderers
  3. `backend/app/services/vision/primitives.py` — promote the canonical primitives; mark `bench_renderer.py` / `drawing_service.py` copies as deprecated
  4. `backend/app/services/vision/renderer_registry.py` — extend `get_title_block` to return layout hints (color, logo position) for the two business units
  5. `backend/app/services/vision/parametric_templates.py` — add per-style assumed-dim warnings and material-legend callouts
- **Files NOT to touch:** `bench_renderer.py::generate_dxf` (DXF is correct), `product_catalog.py` (read-only), `furniture_analyzer.py` (separate concern)
- **Tests:** extend `test_drawing_repair_sprint_1.py`, add `test_drawing_quality_sprint_2.py` (one assertion per acceptance criterion)
- **Risk:** **medium** — may require a bench_renderer rewrite; the parametric logic is the largest open question
- **Owner:** Hermes Desktop for the audit + standard (this doc + `DRAWING-QUALITY-STANDARD.md`), then Harry or Codex for implementation

---

## 7. Do not proceed list (audit phase)

This audit made no code changes, created no branches, ran no tests, and edited no files outside the report outputs in `/home/rg/empire-repo-main/EMPIRE-COMPLETION-PLAN.md` and the four sibling `REPORT-*.md` / `STANDARD.md` files written in this batch. All other repo state is unchanged.
