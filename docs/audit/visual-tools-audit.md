# Visual Tools Audit — 2026-03-22

## Executive Summary

Comprehensive audit of all diagram, schematic, measurement, and visualization tools in the Empire codebase. 25 SVG diagrams exist and are wired into the Quote Builder. Dynamic measurement components render annotations. Custom Shape Builder and Cushion Design Module are fully implemented. Drapery Hardware Module does not exist and needs to be built.

---

## 1. DIAGRAM BANK — 25 SVG Architectural Diagrams

**Status: ✅ FULLY IMPLEMENTED & WIRED**

**Location:** `empire-command-center/public/diagrams/`

### Files (25 total)

#### Furniture (10)
- `furniture/sofa_3cushion.svg` — 3-cushion sofa
- `furniture/sofa_chesterfield.svg` — Tufted chesterfield
- `furniture/sofa_tuxedo.svg` — Tuxedo arm sofa
- `furniture/chair_wingback.svg` — Wingback chair
- `furniture/chair_club.svg` — Club chair
- `furniture/chair_dining.svg` — Dining chair
- `furniture/bench_straight.svg` — Straight bench
- `furniture/bench_banquette.svg` — Banquette/booth
- `furniture/ottoman_rectangular.svg` — Rectangular ottoman
- `furniture/headboard_tufted.svg` — Tufted headboard

#### Window Treatments (10)
- `window-treatments/drapery_pinch_pleat.svg` — Pinch pleat drapery
- `window-treatments/drapery_ripplefold.svg` — Ripplefold drapery
- `window-treatments/drapery_grommet.svg` — Grommet drapery
- `window-treatments/roman_flat.svg` — Flat roman shade
- `window-treatments/roman_hobbled.svg` — Hobbled roman shade
- `window-treatments/roman_balloon.svg` — Balloon shade
- `window-treatments/valance_swag_jabot.svg` — Swag & jabot valance
- `window-treatments/valance_box_pleat.svg` — Box pleat valance
- `window-treatments/cornice_straight.svg` — Straight cornice
- `window-treatments/cornice_serpentine.svg` — Serpentine cornice

#### Wall Panels (3)
- `wall-panels/wall_panel_flat.svg` — Flat panel
- `wall-panels/wall_panel_diamond_tufted.svg` — Diamond tufted
- `wall-panels/wall_panel_channel.svg` — Channel tufted

#### Cushions (2)
- `cushions/cushion_box_edge.svg` — Box edge cushion
- `cushions/cushion_bolster.svg` — Bolster cushion

### Integration

| Component | File | Purpose |
|-----------|------|---------|
| DiagramMapper | `components/business/catalog/diagramMapper.ts` | Maps 32 keys → SVG paths, labels, categories |
| DiagramCatalog | `components/business/catalog/DiagramCatalog.tsx` | Browsable grid with search, filter, quick-add |
| DiagramViewer | `components/business/catalog/DiagramViewer.tsx` | Renders SVG + optional dimension annotations |
| findDiagramMatch | `diagramMapper.ts` | Fuzzy AI-label → diagram key matching |

**Quote Builder Integration:**
- Import at line 11: `DiagramCatalog, DiagramViewer, findDiagramMatch, DIAGRAM_MAP`
- "Browse Catalog" button in Step 3 (Rooms & Items) → opens modal with full catalog
- `addItemFromCatalog(diagramKey)` adds item to quote with type, category, label
- DiagramViewer renders per-item in edit mode with dimension annotations
- Thumbnails (44×44) shown in quote summary

**Verdict:** Users CAN browse all 25 diagrams, search/filter, and attach to quotes. ✅

---

## 2. FURNITURE SCHEMATICS

**Status: ✅ IMPLEMENTED — Static SVGs + Dynamic Measurement Component**

Static SVGs (10 files) are decorative line-art (viewBox 200×200), showing front elevation with arm/cushion divisions. No embedded dimensions.

Dynamic measurement annotations are rendered by:
- **MeasurementDiagram** (`components/business/quotes/MeasurementDiagram.tsx`) — renders furniture with width/height dimension lines, depth/cushion labels. Scalable, interactive (clickable dimensions).
- **DiagramViewer** — overlays width/height/depth annotations on static SVGs when `showAnnotations=true`

**Verdict:** Diagrams scale with dimensions and show measurement annotations via components. ✅

---

## 3. WINDOW TREATMENT SCHEMATICS

**Status: ✅ IMPLEMENTED — Static SVGs + Dynamic Measurement Component**

Static SVGs (10 files) show mounting boards, fabric drape patterns, pleat visualization, and window frame references. No embedded dimensions.

Dynamic annotations via:
- **MeasurementDiagram** `renderWindow()` — draws window frame, stack space (gold overlay), mount type labels. Shows width (top), height (right), stack space breakdown, sill depth.
- **DiagramViewer** — dimension overlays on static SVGs

**Verdict:** Full measurement annotations for window treatments. ✅

---

## 4. INPAINT / AI VISUALIZATION

**Status: ✅ BACKEND FULLY IMPLEMENTED — Frontend partially wired**

### Backend
- **Inpaint Service:** `backend/app/services/max/inpaint_service.py` (504 lines)
  - Grok Vision region detection → mask rendering → Stability AI inpainting (+ Grok fallback)
  - Returns window_mockups and furniture_mockups with inpainted/clean URLs and thumbnails
- **Vision Router:** `backend/app/routers/vision.py` (606 lines)
  - `POST /analyze-items` — QIS item detection
  - `POST /measure` — Window measurement from photo
  - `POST /outline` — Installation plans
  - `POST /upholstery` — Reupholstery estimates with before/after images
  - `POST /mockup` — 3-tier AI design mockup generation
  - `POST /room-scan` — Multi-window detection
  - `POST /imagine` — Standalone image generation
  - Image generation: Stability AI → Together AI (FLUX.1) → xAI Grok fallback

### Frontend
- `components/business/vision/PhotoAnalysisPanel.tsx` — Photo analysis with vision integration
- `components/screens/VisionAnalysisPage.tsx` — Dedicated vision page

**Verdict:** Inpainting backend is production-ready. Customer window photo → AI mockup showing drapery/roman shades works via `/mockup` endpoint. Frontend wiring exists but not fully polished. ✅

---

## 5. CUSTOM SHAPE BUILDER

**Status: ✅ FULLY IMPLEMENTED — Accessible from Workroom Templates**

### Component
- `components/tools/CustomShapeBuilder.tsx` (835 lines)
- 6 shape presets: straight bench, L-bench, U-booth, curved banquette, semicircle, round ottoman
- Interactive: dimension inputs, seatback toggles, cushion counts, live SVG preview
- Calculates: linear feet, sq footage, fabric yardage, piece cut list, construction notes

### Backend
- `backend/app/routers/custom_shapes.py` (697 lines)
- `POST /calculate` — geometry + fabric + SVG generation
- `POST /save` / `GET /saved` — persist/retrieve shapes

### Mounting
- **TemplateModule** (`components/business/templates/TemplateModule.tsx`) imports CustomShapeBuilder
- **WorkroomPage** mounts TemplateModule at Workroom > Templates tab
- ⚠️ **NOT directly accessible from Quote Builder bench items** — user must go to Workroom > Templates separately

**Verdict:** Fully functional but needs Quote Builder integration for bench items. ⚠️

---

## 6. MEASUREMENT OVERLAY (Architectural Diagrams)

**Status: ✅ IMPLEMENTED for furniture and window treatments**

- **MeasurementDiagram** renders architectural-style diagrams with:
  - Extension lines (dashed), dimension lines (solid with arrows), text labels
  - Three renderers: `renderWindow()`, `renderFurniture()`, `renderCushion()`
  - Interactive: `onDimensionClick` callback for editing
  - Used in Quote Builder measurement entry (line 1647) and PhotoAnalysisPanel

- **Backend diagram_generator.py** generates standalone SVG measurement diagrams for PDFs
  - Full architectural rendering: 460×400px canvas, proportional scaling
  - Dimension callouts: width, height, depth, sill, stack space

**Verdict:** Measurement overlays exist for all item types. ✅

---

## 7. DRAPERY HARDWARE MODULE

**Status: ❌ NOT IMPLEMENTED**

No dedicated UI component exists for:
- Rod type selection (traverse, decorative wood, motorized Somfy/Lutron, track)
- Ring/bracket/finial selection with visual previews
- Installation measurement diagrams (window width, stack-back, return depth, mounting height)
- Motorization configuration

The QuoteBuilderScreen has dropdown fields for `hardwareType`, `finialStyle`, `returnSize`, `stacking` — but these are plain text selects, not a visual module with installation diagrams.

**Verdict:** Needs to be built. ❌

---

## 8. CUSHION DESIGN MODULE

**Status: ✅ FULLY IMPLEMENTED & COMPREHENSIVE**

### Component
- `components/business/upholstery/CushionBuilder.tsx` (1092 lines)
- 9-step wizard: type → dimensions → shape/style → fill → edge → closure → tufting → fabric → preview
- 11 cushion types, material calculations (fabric yardage, foam volume, welt cord, zipper, Dacron)
- Cost breakdown with labor estimates
- Save as template, add to quote

### Diagram
- `components/business/upholstery/CushionDiagram.tsx`
- Multi-view: top, side, front, all views
- Shows tufting patterns, welt details, dimension annotations with custom arrows
- Dynamic scaling

### Mounting
- Imported in QuoteBuilderScreen (line 13): `const CushionBuilder = dynamic(() => import(...))`
- Available in the upholstery workflow

**Verdict:** Production-ready cushion design system. ✅

---

## BUILD PRIORITIES

| Priority | Task | Status |
|----------|------|--------|
| 1 | Diagram bank wired into Quote Builder | ✅ Already done |
| 2 | Measurement annotations on furniture/window diagrams | ✅ Already done (MeasurementDiagram + DiagramViewer) |
| 3 | **Drapery Hardware Module** with installation diagrams | ❌ NEEDS BUILD |
| 4 | Cushion Design Module with cross-section diagrams | ✅ Already done |
| 5 | **Wire Custom Shape Builder into Quote Builder bench items** | ⚠️ NEEDS WIRING |
| 6 | AI visualization for window treatments | ✅ Backend done, frontend partially wired |
