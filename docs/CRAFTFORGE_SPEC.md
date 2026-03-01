# CraftForge — Technical Specification
## AI-Powered Wood Design & CNC Platform

**Version:** 1.0
**Date:** February 27, 2026
**Status:** Spec Ready for Implementation
**Parent:** Empire Box Product Line

---

## 1. Overview

CraftForge is an AI-powered platform that turns ideas into CNC-ready designs. Describe what you want in plain English, upload a photo, or 3D scan an existing object — and CraftForge generates professional CAD designs, 3D models, and machine-ready G-code toolpaths. No CAD expertise required.

The platform serves two markets simultaneously:
1. **Internal tool** — powers WorkroomForge custom cornices, valances, headboards, cabinet doors, and furniture details
2. **SaaS product** — sold to woodworkers, makers, sign shops, contractors, and furniture builders who want AI-assisted design and CNC file generation

**Core Principle:** Describe it, scan it, or photograph it → CraftForge designs it → your CNC cuts it.

---

## 2. The Four Pipelines

### Pipeline 1: Text → CNC (AI Design from Description)

The flagship feature. Describe what you want and get CNC-ready files.

```
User: "Victorian style cornice with scalloped bottom edge, 
       72 inches wide, 6 inches tall, 4 inch return"
    ↓
AI Design Engine
    ↓
├── 4 design variations generated (different scallop profiles)
├── 2D vector profile (SVG/DXF)
├── 3D model with depth/relief (STL/OBJ)
├── Dimensioned technical drawing
├── Material requirements (MDF, plywood, etc.)
└── G-code toolpath optimized for user's machine
    ↓
User selects favorite → refines → exports → cuts
```

**What you can describe:**
- Window treatment components: cornices, valance boards, shaped pelmets
- Cabinet doors: raised panel, shaker, flat panel with CNC patterns
- Furniture: headboards, bed frames, table legs, chair backs
- Architectural: crown molding profiles, wall panels, room dividers, screens
- Decorative: rosettes, appliqués, carved panels, relief art
- Signage: dimensional signs, carved letters, logos
- Custom: anything you can describe in words

**AI Design Options per Request:**
- 4 initial concepts (different interpretations of your description)
- Style slider: traditional ↔ contemporary ↔ modern ↔ ornate
- Complexity slider: simple ↔ detailed ↔ intricate
- Each concept fully editable before export

### Pipeline 2: Photo/Image → CNC

Turn any photo into a machinable design.

```
Photo Upload (phone camera, screenshot, Pinterest save, etc.)
    ↓
AI Image Analysis
    ↓
├── Object identification (what is this? cornice, molding, carving, etc.)
├── Style classification (Victorian, Art Deco, Modern, Craftsman, etc.)
├── Geometry extraction
│   ├── 2D: outline/profile extracted as vector (SVG/DXF)
│   ├── 3D: depth map / heightmap generated for relief carving
│   └── Dimensions estimated (with reference object or manual input)
├── Clean vector output ready for CAM
└── G-code generated with selected tooling
```

**Use Cases:**
- Photograph an antique cornice → replicate it on CNC
- Screenshot a Pinterest cabinet door → get the cut file
- Photo of competitor's product → design your version
- Picture of hand carving → convert to repeatable CNC file
- Image of pattern/texture → generate as relief carving
- Customer shows you a photo of what they want → CraftForge makes it real

### Pipeline 3: 3D Scan → CNC

Digitize physical objects and reproduce or modify them.

```
3D Scan Input (phone LiDAR, structured light scanner, touch probe)
    ↓
Mesh Processing
    ↓
├── Raw mesh import (STL, OBJ, PLY)
├── Auto-cleanup: fill holes, smooth surfaces, remove noise
├── Mesh decimation (reduce poly count for faster processing)
├── Symmetry detection and correction
├── Scale verification and adjustment
├── Mirror/duplicate capabilities
└── Export as clean STL → CAM → G-code
```

**Scan Sources Supported:**
- iPhone/iPad LiDAR (via Polycam, Scaniverse, 3D Scanner App)
- Android depth sensors
- Structured light scanners (EinScan, Creality, Revopoint)
- CNC touch probes (ShopBot, GRBL-based)
- Photogrammetry (multiple photos → 3D model)

**Use Cases:**
- Scan antique furniture detail → replicate on CNC
- Scan hand-carved master → produce multiples
- Scan customer's existing molding → match it exactly for addition/repair
- Scan a damaged piece → AI reconstructs the missing parts → CNC cuts replacement
- Scale up or down: scan a 6" rosette → cut it at 24"

### Pipeline 4: Template Library + AI Customization

Pre-built parametric designs that users customize.

```
Browse Template Library
    ↓
├── Category: Cornices, Cabinet Doors, Panels, Signs, Furniture, etc.
├── Select base design
├── Customize with AI:
│   ├── "Make it more ornate"
│   ├── "Change to Art Deco style"
│   ├── "Add a fleur-de-lis at the center"
│   ├── "Scale to 48 inches wide"
│   └── "Adjust depth to 1/4 inch"
├── Parametric controls: width, height, depth, pattern repeat, border
└── Export customized version → G-code
```

---

## 3. Machine Intelligence Layer

### 3.1 Machine Profile System

Every user configures their machine(s). All designs auto-optimize for their specific setup.

```json
{
  "machine_name": "ShopBot PRSalpha 48x96",
  "type": "cnc_router",
  "bed_size": {"x": 48, "y": 96, "z": 6, "unit": "inches"},
  "spindle": {"type": "router", "hp": 3.25, "max_rpm": 18000},
  "controller": "ShopBot",
  "post_processor": "shopbot_sbp",
  "tool_library": [
    {"id": 1, "type": "flat_endmill", "diameter": 0.25, "flutes": 2, "material": "carbide"},
    {"id": 2, "type": "ball_endmill", "diameter": 0.125, "flutes": 2, "material": "carbide"},
    {"id": 3, "type": "v_bit", "angle": 60, "diameter": 0.5, "material": "carbide"},
    {"id": 4, "type": "v_bit", "angle": 90, "diameter": 1.0, "material": "carbide"}
  ],
  "capabilities": ["3axis", "dust_collection", "touch_probe"],
  "material_presets": {
    "mdf": {"feed": 150, "plunge": 75, "doc": 0.125, "rpm": 16000},
    "plywood": {"feed": 120, "plunge": 60, "doc": 0.1, "rpm": 16000},
    "hardwood_soft": {"feed": 100, "plunge": 50, "doc": 0.08, "rpm": 14000},
    "hardwood_hard": {"feed": 80, "plunge": 40, "doc": 0.06, "rpm": 12000}
  }
}
```

**Supported Controllers/Post-Processors:**
- ShopBot (.sbp)
- GRBL (.nc, .gcode)
- Mach3/Mach4 (.nc)
- LinuxCNC (.ngc)
- UCCNC (.nc)
- Carbide Motion (Shapeoko/Nomad)
- Onefinity (Masso)
- Vectric compatible (.crv, .crv3d export)
- Universal G-code (.nc, .gcode)

### 3.2 AI Toolpath Generation

CraftForge generates optimized toolpaths — not just designs.

```
Design Ready
    ↓
AI Toolpath Engine
    ↓
├── Analyze geometry complexity
├── Select optimal tool(s) from user's library
├── Strategy selection:
│   ├── 2D profiling (cut-outs, pockets)
│   ├── V-carving (signs, lettering, decorative)
│   ├── 3D roughing (adaptive clearing, large tool)
│   ├── 3D finishing (raster, spiral, pencil cleanup)
│   └── Combined multi-tool strategy
├── Calculate feeds & speeds for selected material
├── Estimate cut time
├── Generate G-code for user's controller
├── 3D simulation preview (watch the cut before you cut)
└── Export
```

**Smart Features:**
- Auto tool selection based on design detail and user's available bits
- Multi-tool strategies: rough with big bit, finish with small bit
- Tabs/bridges auto-placed for cut-out stability
- Ramp entries to prevent bit breakage
- Climb vs conventional milling selection
- Optimal toolpath ordering to minimize air cutting
- Material waste estimation

### 3.3 Job Time & Cost Estimator

```
Design + Machine Profile + Material Selection
    ↓
├── CNC cut time (roughing + finishing passes)
├── Tool changes required
├── Material needed (board feet, sheet goods)
├── Material cost estimate
├── Bit wear estimate (when to replace)
├── Sanding time estimate
├── Finishing time estimate (stain, paint, lacquer)
├── Total labor time
└── Suggested retail price (with margin)
```

---

## 4. CNC Plan Marketplace

### 4.1 Concept

A marketplace where designers sell CNC-ready files and buyers download and cut them. Think Etsy meets Thingiverse meets CraftForge.

**Revenue Model:**
- Free plans (community, builds audience)
- Paid plans ($5 - $200 depending on complexity)
- Subscription tier: unlimited downloads for $29/mo
- CraftForge takes 15-20% commission on paid plans
- Featured/promoted listings (paid by sellers)

### 4.2 What Gets Sold

Each listing includes:
```
CNC Plan Package:
├── 2D vectors (SVG, DXF)
├── 3D model (STL, OBJ)
├── G-code files (multiple controllers)
├── Dimensioned technical drawings (PDF)
├── Material list & cut list
├── Assembly instructions (if multi-part)
├── Photos of finished piece
├── Estimated cut time per machine type
├── Difficulty rating (beginner/intermediate/advanced)
├── Required tools list
└── License: personal use / commercial use options
```

### 4.3 Marketplace Categories

- **Window Treatments:** Cornice profiles, pelmet shapes, valance boards
- **Cabinet Doors:** Raised panel, shaker, modern, CNC pattern
- **Furniture:** Tables, chairs, beds, shelving, desks
- **Architectural:** Crown molding, wall panels, room dividers, wainscoting
- **Signs:** Business signs, house numbers, directional, decorative
- **Art & Decor:** Relief carvings, wall art, clocks, frames
- **Outdoor:** Garden art, planters, deck components, gates
- **Toys & Games:** Puzzles, toys, game boards
- **Jigs & Fixtures:** CNC jigs, workholding, shop fixtures
- **Templates:** Parametric designs (user sets dimensions, files auto-generate)

### 4.4 Seller Tools

- Upload design files with auto-validation
- Pricing recommendations based on complexity
- Sales analytics dashboard
- Customer reviews and ratings
- Version control (update files, buyers get latest)
- Automatic G-code generation for multiple machine types
- Preview rendering (3D turntable, CNC simulation)

### 4.5 Buyer Experience

- Browse by category, style, material, difficulty, machine compatibility
- Preview in 3D before purchase
- "Will it fit my machine?" — auto-checks against buyer's machine profile
- One-click download in their controller's format
- AI customization: "I bought this plan but need it 20% larger" → AI rescales everything including toolpaths
- Review and share photos of finished cuts

---

## 5. WorkroomForge Integration

CraftForge is deeply integrated with WorkroomForge operations.

### 5.1 Cornice Production Pipeline

```
Customer wants custom cornice (from Visual Mockup Engine)
    ↓
CraftForge receives: shape profile, dimensions, style
    ↓
Generates: CNC-ready cut file for cornice face
    ↓
Adds to cut queue with material requirements
    ↓
CNC cuts cornice shape from MDF/plywood
    ↓
Workroom wraps with fabric (from customer's fabric selection)
    ↓
Install at customer location
```

### 5.2 Automated Cornice Design

```
Input: "Henderson job — upholstered cornice, 72" wide, 
        scalloped bottom, 8" drop, 4" return"
    ↓
CraftForge generates:
├── Cornice face profile (2D cut file)
├── Return pieces (left and right)
├── Mounting board
├── Batting/padding template
├── Fabric cutting template (with pattern alignment)
├── Material list: MDF, batting, fabric yardage
├── Assembly diagram
└── Total cost calculation
```

### 5.3 Cabinet Door Production

For kitchen/furniture clients:
- Select door style from library or design custom
- Input dimensions for each door (batch processing)
- CraftForge generates cut files for entire kitchen
- Nested layout optimizes sheet goods usage
- Batch G-code: cut 20 doors in optimal sequence

### 5.4 Headboard & Furniture

- Custom headboard shapes and carvings
- Bed frame components
- Decorative furniture details (legs, appliqués, rosettes)
- Ties to mockup engine: customer sees headboard in their bedroom → approves → CraftForge generates CNC files

---

## 6. AI Design Engine — Technical Details

### 6.1 Text-to-Design

**Models:**
- Primary: Claude/GPT-4o for understanding design intent and generating specifications
- 3D Generation: Stable Diffusion → depth map → 3D relief model
- Vector Generation: AI generates SVG paths from description
- Parametric: AI sets parameters in pre-built parametric templates

**Process:**
1. User describes design in natural language
2. AI parses: object type, style, dimensions, features, material
3. Generates 4 concept images (different interpretations)
4. User selects favorite
5. AI converts selected concept to:
   - 2D vector profile (SVG/DXF)
   - 3D depth map / relief model (STL)
   - Technical drawing with dimensions
6. User refines (edit points, adjust depths, modify details)
7. Generate toolpath → export G-code

### 6.2 Image-to-Design

**Models:**
- Segmentation: Gemini 2.5 / SAM-2 (isolate object from background)
- Depth estimation: MiDaS / Depth Anything V2 (photo to depth map)
- Vectorization: Potrace / AI-enhanced tracing (raster to clean vectors)
- Style transfer: extract style from one image, apply to another design

**Process:**
1. User uploads photo
2. AI identifies object, classifies style
3. Background removal / object isolation
4. Choice: 2D profile extraction OR 3D relief generation
5. For 2D: auto-trace to clean vectors, user refines
6. For 3D: depth map generation, conversion to relief model
7. Dimension assignment (user inputs or AI estimates)
8. Toolpath generation

### 6.3 Scan-to-Design

**Pipeline:**
1. Import mesh (STL/OBJ/PLY from any scanner)
2. Auto-cleanup: remove noise, fill holes, smooth
3. Alignment and scaling
4. Optional: AI reconstruction of damaged/missing sections
5. Mesh to toolpath (direct STL machining)
6. Or: mesh to parametric model (reverse engineering)
7. Export clean model + G-code

### 6.4 AI Refinement Tools

After initial generation, AI assists with modifications:
- "Make the scrollwork more intricate"
- "Smooth out the top edge"
- "Add a 1/4 inch chamfer on all edges"
- "Mirror this design and add a center medallion"
- "Convert this flat carving to a 3D relief with 1/2 inch depth"
- "Optimize for a V-bit instead of ball nose"

---

## 7. Material Intelligence

### 7.1 Material Database

```
Built-in material library:
├── MDF (3/4", 1/2", 1/4")
├── Plywood (Baltic birch, cabinet grade, marine)
├── Softwoods (pine, cedar, poplar, fir)
├── Hardwoods (oak, maple, walnut, cherry, mahogany, ash)
├── Exotic (teak, purpleheart, padauk, zebrawood)
├── Composites (Corian, PVC board, HDPE, acrylic)
├── Foam (EPS, XPS, EVA — for prototyping)
└── Metal (aluminum, brass — for engraving only)
```

Each material includes:
- Feed/speed recommendations per tool type
- Optimal depth of cut
- Grain direction considerations
- Finishing recommendations
- Cost per board foot / sheet
- Where to buy (local supplier links)

### 7.2 Sheet Nesting

For projects with multiple parts (cabinet doors, furniture components):
- AI optimizes part layout on sheet goods
- Minimizes waste (target < 15% waste)
- Accounts for grain direction (when applicable)
- Generates cut sequence for efficient machining
- Material cost calculation based on optimized layout

### 7.3 Material Calculator

```
Design → Material Calculator:
├── Board feet / sheet goods needed
├── Waste percentage
├── Hardware list (screws, brackets, hinges)
├── Finishing materials (paint, stain, polyurethane)
├── Estimated total material cost
├── Where to buy (links to local/online suppliers)
└── Shopping list exportable as PDF or text
```

---

## 8. Simulation & Preview

### 8.1 3D Design Preview
- Rotate, zoom, pan the design in 3D
- Material texture overlay (see oak vs walnut vs painted)
- Dimension callouts
- Cross-section view
- Before/after: stock material → finished piece

### 8.2 CNC Simulation
- Watch the virtual CNC cut your design
- Toolpath visualization (roughing in one color, finishing in another)
- Speed controls (1x, 5x, 20x, skip to end)
- Tool change indicators
- Collision detection (warn if tool will hit clamps/fixtures)
- Cut time counter

### 8.3 AR Preview (Future)
- Point phone at table/wall/room
- See the finished piece in place at actual size
- Ties into Visual Mockup Engine for WorkroomForge products
- Customer approval before cutting

---

## 9. 3D Print Bridge

Same designs exportable for 3D printing:
- Export STL for FDM/resin printing
- Auto-scale for print bed sizes
- Use for: prototyping before committing wood, small detail pieces, client approval models
- Material: PLA for prototypes, resin for detail
- Print time estimator
- Slicer recommendations

---

## 10. Technical Architecture

### 10.1 Application Structure

CraftForge runs as a standalone app within the Empire ecosystem, accessible from Command Center.

```
~/Empire/craftforge/
├── frontend/          (Next.js 14 + TypeScript + Tailwind)
│   ├── src/
│   │   ├── components/
│   │   │   ├── DesignStudio.tsx       — Main design workspace
│   │   │   ├── TextToDesign.tsx       — Text description input + AI generation
│   │   │   ├── ImageToDesign.tsx      — Photo upload + extraction
│   │   │   ├── ScanImport.tsx         — 3D scan import + cleanup
│   │   │   ├── TemplateLibrary.tsx    — Browse + customize templates
│   │   │   ├── ToolpathGenerator.tsx  — CAM + G-code generation
│   │   │   ├── MachineProfile.tsx     — Machine configuration
│   │   │   ├── MaterialSelector.tsx   — Material database + calculator
│   │   │   ├── NestingEngine.tsx      — Sheet goods optimization
│   │   │   ├── SimulationViewer.tsx   — 3D preview + CNC simulation
│   │   │   ├── Marketplace.tsx        — Browse + buy/sell plans
│   │   │   ├── ProjectManager.tsx     — Save, organize, version projects
│   │   │   └── ExportPanel.tsx        — Download files in any format
│   │   ├── lib/
│   │   │   ├── gcodeGenerator.ts      — G-code generation engine
│   │   │   ├── meshProcessor.ts       — 3D mesh operations
│   │   │   ├── vectorEngine.ts        — SVG/DXF operations
│   │   │   ├── nestingAlgorithm.ts    — Sheet nesting optimization
│   │   │   └── machineProfiles.ts     — Controller/post-processor configs
│   │   └── three/
│   │       ├── DesignViewer.tsx        — Three.js 3D viewer
│   │       ├── CNCSimulator.tsx        — Toolpath simulation
│   │       └── ARPreview.tsx           — AR placement (future)
├── backend/           (FastAPI)
│   ├── routers/
│   │   ├── designs.py                 — CRUD for designs/projects
│   │   ├── generate.py                — AI generation endpoints
│   │   ├── toolpath.py                — G-code generation
│   │   ├── marketplace.py             — Buy/sell/browse plans
│   │   ├── machines.py                — Machine profiles
│   │   └── materials.py               — Material database
│   ├── services/
│   │   ├── ai_design_engine.py        — Text/image/scan to design
│   │   ├── toolpath_engine.py         — CAM computation
│   │   ├── mesh_service.py            — 3D mesh processing
│   │   ├── vector_service.py          — Vector operations
│   │   └── nesting_service.py         — Sheet optimization
│   └── models/
│       ├── design.py                  — Design data model
│       ├── machine.py                 — Machine profile model
│       ├── marketplace_listing.py     — Marketplace listing model
│       └── material.py                — Material data model
└── data/
    ├── templates/                     — Built-in parametric templates
    ├── machines/                      — Pre-configured machine profiles
    ├── materials/                     — Material database
    └── marketplace/                   — User-uploaded plans
```

### 10.2 API Endpoints

```
# Design Generation
POST   /api/v1/craft/generate/text      — Text description → design concepts
POST   /api/v1/craft/generate/image     — Photo upload → design extraction  
POST   /api/v1/craft/generate/scan      — 3D scan → cleaned model
POST   /api/v1/craft/generate/refine    — AI modification of existing design

# Design Management
GET    /api/v1/craft/designs             — List user's designs
POST   /api/v1/craft/designs             — Save new design
GET    /api/v1/craft/designs/{id}        — Get design detail
PUT    /api/v1/craft/designs/{id}        — Update design
DELETE /api/v1/craft/designs/{id}        — Delete design

# Toolpath & Export
POST   /api/v1/craft/toolpath/generate  — Generate G-code from design
GET    /api/v1/craft/toolpath/{id}       — Get generated toolpath
POST   /api/v1/craft/export/{id}         — Export in specified format
POST   /api/v1/craft/simulate/{id}       — Generate simulation data

# Machine Profiles
GET    /api/v1/craft/machines            — List user's machines
POST   /api/v1/craft/machines            — Add machine profile
PUT    /api/v1/craft/machines/{id}       — Update machine
GET    /api/v1/craft/machines/presets     — Pre-built machine configs

# Materials
GET    /api/v1/craft/materials           — Material database
POST   /api/v1/craft/materials/calculate — Material requirements for design
POST   /api/v1/craft/materials/nest      — Nesting optimization

# Marketplace
GET    /api/v1/craft/marketplace         — Browse listings
POST   /api/v1/craft/marketplace         — Create listing (seller)
GET    /api/v1/craft/marketplace/{id}    — Listing detail
POST   /api/v1/craft/marketplace/{id}/buy — Purchase plan
GET    /api/v1/craft/marketplace/my-sales — Seller dashboard

# Templates
GET    /api/v1/craft/templates           — Browse template library
POST   /api/v1/craft/templates/{id}/customize — AI-customize a template
```

### 10.3 External Services

| Service | Purpose | Cost Model |
|---------|---------|------------|
| Claude API | Design intent parsing, descriptions | Per-token |
| GPT-4o | Image analysis, concept generation | Per-request |
| Stable Diffusion | Design concept images, depth maps | Self-hosted or Replicate |
| Depth Anything V2 | Photo to depth map | Self-hosted (open source) |
| Gemini 2.5 | Image segmentation | Per-request |
| Three.js | 3D viewer, simulation (client-side) | Free / open source |
| Potrace | Vector tracing | Free / open source |
| OpenCASCADE | Parametric modeling (if needed) | Free / open source |

### 10.4 Data Models

```python
class Design(BaseModel):
    id: str
    user_id: str
    name: str
    description: str
    source: str                    # "text", "image", "scan", "template", "marketplace"
    category: str                  # "cornice", "cabinet_door", "furniture", etc.
    style: str                     # "victorian", "modern", "craftsman", etc.
    dimensions: dict               # {"width": 72, "height": 8, "depth": 0.75, "unit": "inches"}
    files: DesignFiles
    material: str
    machine_id: str | None
    toolpath_id: str | None
    status: str                    # "draft", "ready", "exported", "cutting", "complete"
    created_at: datetime
    updated_at: datetime

class DesignFiles(BaseModel):
    svg: str | None                # 2D vector profile
    dxf: str | None                # 2D CAD format
    stl: str | None                # 3D model
    obj: str | None                # 3D model (alt)
    gcode: str | None              # Generated toolpath
    preview_image: str             # Rendered preview
    simulation_data: str | None    # CNC simulation
    technical_drawing: str | None  # Dimensioned PDF

class MachineProfile(BaseModel):
    id: str
    user_id: str
    name: str
    type: str                      # "cnc_router", "laser", "3d_printer"
    bed_size: dict                 # {"x": 48, "y": 96, "z": 6}
    spindle: dict                  # {"type": "router", "hp": 3.25, "max_rpm": 18000}
    controller: str                # "grbl", "shopbot", "mach3", etc.
    post_processor: str            # output format
    tools: list[Tool]
    material_presets: dict

class MarketplaceListing(BaseModel):
    id: str
    seller_id: str
    design_id: str
    title: str
    description: str
    category: str
    price: float                   # 0 = free
    license: str                   # "personal", "commercial", "both"
    files: DesignFiles
    photos: list[str]              # photos of finished piece
    difficulty: str                # "beginner", "intermediate", "advanced"
    required_tools: list[str]
    estimated_cut_time: dict       # per machine type
    downloads: int
    rating: float
    reviews: list[dict]
    created_at: datetime
```

---

## 11. Implementation Priority

### Phase 1 — MVP (Internal Tool for WorkroomForge)
1. **Text → 2D Profile** — describe a cornice shape, get SVG/DXF
2. **Basic template library** — 20 cornice profiles, 10 cabinet door styles
3. **Dimension input** — set width, height, depth, returns scaled file
4. **SVG/DXF export** — download files for use in VCarve/Carveco
5. **Material calculator** — MDF/plywood requirements for design
6. **Integration with Command Center** — accessible via MAX canvas
7. **Design storage** — save projects in Empire database

### Phase 2 — AI Design + 3D
8. **Photo → vector extraction** — upload photo, get clean outline
9. **Photo → depth map → 3D relief** — photo to carving-ready model
10. **3D viewer** — Three.js rotate/zoom preview
11. **Text → 3D relief** — describe relief carving, get STL
12. **AI refinement** — "make it more ornate" / "smooth the edges"
13. **Multiple design variations** — 4 concepts per request
14. **Technical drawing generation** — dimensioned PDF

### Phase 3 — CNC Intelligence
15. **Machine profile system** — configure your CNC
16. **G-code generation** — built-in CAM for common operations
17. **Toolpath optimization** — feeds/speeds/strategies
18. **CNC simulation** — 3D preview of cuts
19. **Job time estimator** — accurate cut time predictions
20. **Sheet nesting** — optimize material layout
21. **3D scan import** — STL cleanup and processing

### Phase 4 — Marketplace & SaaS
22. **Marketplace MVP** — browse, upload, download plans
23. **Payment system** — Stripe integration for plan purchases
24. **Seller dashboard** — sales, analytics, reviews
25. **User accounts** — sign up, machine profiles, purchase history
26. **Subscription tier** — unlimited downloads plan
27. **Community features** — ratings, reviews, comments, forums
28. **Public website** — craftforge.com landing page

### Phase 5 — Advanced
29. **AR preview** — see design in real space via phone camera
30. **3D print export** — STL optimized for FDM/resin
31. **Collaborative design** — share and co-edit designs
32. **API for integrators** — other apps can generate CNC files via CraftForge
33. **Mobile app** — scan and design from phone
34. **AI design from voice** — describe to MAX, CraftForge generates

---

## 12. Revenue Streams

| Stream | Model | Target |
|--------|-------|--------|
| SaaS Subscription | $29/mo hobby, $79/mo pro, $199/mo business | Recurring |
| Marketplace Commission | 15-20% on plan sales | Recurring |
| Plan Sales (own designs) | Sell WorkroomForge cornice/door templates | Passive |
| Custom Design Service | Customer describes → we design → flat fee | Per-project |
| Machine Setup Service | Configure CraftForge for customer's CNC | One-time |
| API Access | Per-request pricing for B2B integrations | Usage-based |

### SaaS Tiers

| Feature | Free | Hobby ($29/mo) | Pro ($79/mo) | Business ($199/mo) |
|---------|------|-----------------|--------------|---------------------|
| Template library | 10 free | All templates | All templates | All templates |
| AI generations/mo | 5 | 50 | 200 | Unlimited |
| Machine profiles | 1 | 3 | 10 | Unlimited |
| G-code export | SVG/DXF only | All formats | All formats | All formats |
| Marketplace downloads | Browse only | 5/mo | 25/mo | Unlimited |
| Sheet nesting | — | Basic | Advanced | Advanced |
| Priority support | — | — | Yes | Dedicated |
| API access | — | — | — | Yes |
| White label | — | — | — | Yes |

---

## 13. Competitive Landscape

| Competitor | What They Do | CraftForge Advantage |
|------------|-------------|---------------------|
| Vectric (VCarve/Aspire) | Industry standard CAM software | CraftForge has AI design — they don't. We generate designs, not just toolpaths |
| Carveco | CNC CAM with new AI relief feature | We're full pipeline: idea → design → toolpath → marketplace |
| Easel (Inventables) | Beginner CNC software for X-Carve | We're more powerful but equally easy. Plus marketplace |
| PixelCNC | Image-to-CNC for art/signs | We do text, photo, scan, AND templates. Broader scope |
| Etsy/Thingiverse | Sell/share files | We generate the files + sell them. AI-powered marketplace |
| Toolpath.com | AI-powered CAM for industrial | They target manufacturing. We target makers/woodworkers |

**CraftForge's unique position:** First platform to combine AI design generation + CNC toolpath generation + marketplace, specifically for woodworking and custom fabrication.

---

## 14. Example Scenarios

**Scenario 1: WorkroomForge cornice job**
→ Customer approves cornice mockup from Visual Mockup Engine → CraftForge receives: scalloped profile, 72" wide, 8" drop → Generates CNC cut file → Material calc: 1 sheet 3/4" MDF → Nested with 3 other pending cornice jobs → G-code exported → CNC cuts all 4 cornices in one session → Fabric wrap in workroom → Install

**Scenario 2: Customer shows photo of competitor's cabinet doors**
→ Photo uploaded to CraftForge → AI identifies: raised panel, shaker-adjacent, 3/8" raised center → Generates clean vector profile → User adjusts panel raise depth → Batch input: 22 doors for full kitchen → Sheet nesting: 7 sheets of 3/4" maple plywood → Total cut time: 4.5 hours → Material cost: $840 → Quoted to customer at $3,200

**Scenario 3: Antique molding replication**
→ Contractor scans existing crown molding with iPhone LiDAR → Mesh uploaded to CraftForge → AI cleans up, fills gaps, smooths → Profile extracted → Scaled to match existing (4.5" tall) → G-code for running 16 linear feet on CNC → Material: poplar → Matches the original perfectly for restoration

**Scenario 4: Marketplace sale**
→ Designer creates ornate Victorian cornice profile set (12 variations) → Uploads to CraftForge marketplace → Priced at $45 for personal, $95 for commercial → Photos of 3 finished pieces included → Gets 200 downloads in first month → Revenue: $9,000 → CraftForge commission: $1,800 → Designer nets: $7,200

**Scenario 5: Text-to-design for headboard**
→ User: "Art Deco geometric headboard, king size, 80 inches wide, 48 inches tall, stepped pattern with sunburst center, 3/4 inch MDF, paint grade" → CraftForge generates 4 concepts → User picks #3 → Refines: "make the sunburst larger, reduce the side steps to 3" → Final design exported as DXF + G-code → Estimated cut time: 2 hours 15 minutes → Material: 2 sheets 3/4" MDF

---

## 15. Future Vision

CraftForge becomes the **Canva of CNC** — anyone can create professional CNC-ready designs without CAD expertise, buy/sell designs in a marketplace, and produce custom wood products with their CNC machine.

Long-term:
- **CraftForge Cloud CNC** — remote job submission to partner CNC shops (no machine needed)
- **CraftForge Academy** — AI-guided learning for new CNC users
- **CraftForge Hardware** — branded CNC machines pre-configured with CraftForge software
- **CraftForge Pro Network** — connect customers who need custom work with CraftForge pro shops
- **Integration with lumber suppliers** — order material directly from design
- **Sustainability scoring** — waste optimization, reclaimed wood suggestions
