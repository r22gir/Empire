# CraftForge SpaceScan & Fabrication Module — Addendum
## Spatial Scanning, Custom Millwork Design, and Multi-Machine Fabrication

**Version:** 1.0
**Date:** February 27, 2026
**Parent Spec:** CRAFTFORGE_SPEC.md
**Status:** Spec Ready for Implementation

---

## 1. Overview

The SpaceScan module extends CraftForge from a design-and-cut tool into a **full spatial design-to-fabrication platform**. Scan a customer's room, design custom built-ins that fit the exact space, show the customer a photorealistic render in their room, generate a quote, then fabricate across multiple machines: X-Carve CNC for wood components, Elegoo Saturn resin printer for hardware/prototypes/details.

**Core Principle:** Scan the space. Design to fit. Show the customer. Quote it. Build it. Install it.

---

## 2. Your Machine Shop

### 2.1 Inventables X-Carve (CNC Router)

```json
{
  "machine": "X-Carve",
  "manufacturer": "Inventables",
  "type": "cnc_router",
  "bed_size": {"x": 750, "y": 750, "z": 65, "unit": "mm"},
  "controller": "grbl",
  "post_processor": "grbl_mm",
  "spindle": {"type": "dewalt_611", "hp": 1.25, "max_rpm": 27000},
  "capabilities": [
    "2d_profiling",
    "pocketing",
    "v_carving",
    "3d_relief_carving",
    "inlays",
    "engraving"
  ],
  "software": ["Easel", "VCarve", "Carveco", "CraftForge"],
  "best_for": [
    "Cabinet door profiles and raised panels",
    "Cornice face shapes",
    "Decorative panels and screen patterns",
    "Sign making",
    "Shelf components with dadoes and rabbets",
    "Furniture details and joints",
    "Inlays and V-carved details"
  ],
  "material_presets": {
    "mdf_3/4": {"feed_rate": 1500, "plunge_rate": 500, "doc": 3.0, "rpm": 18000},
    "plywood_3/4": {"feed_rate": 1200, "plunge_rate": 400, "doc": 2.5, "rpm": 18000},
    "hardwood": {"feed_rate": 800, "plunge_rate": 300, "doc": 1.5, "rpm": 16000},
    "softwood": {"feed_rate": 1500, "plunge_rate": 500, "doc": 3.0, "rpm": 18000},
    "acrylic": {"feed_rate": 1000, "plunge_rate": 300, "doc": 2.0, "rpm": 16000}
  }
}
```

### 2.2 Elegoo Saturn (Large Format Resin 3D Printer)

```json
{
  "machine": "Elegoo Saturn",
  "manufacturer": "Elegoo",
  "type": "resin_3d_printer",
  "technology": "MSLA (Masked Stereolithography)",
  "build_volume": {"x": 192, "y": 120, "z": 200, "unit": "mm"},
  "resolution": {"xy": 0.05, "z": 0.01, "unit": "mm"},
  "capabilities": [
    "high_detail_prints",
    "smooth_surface_finish",
    "functional_prototypes",
    "miniature_models",
    "jewelry_casting_patterns",
    "custom_hardware"
  ],
  "resin_types": [
    "standard (general purpose)",
    "abs_like (tough, functional)",
    "water_washable (easy cleanup)",
    "castable (for metal casting)",
    "flexible (gaskets, bumpers)",
    "clear (transparent parts)"
  ],
  "best_for": [
    "Scale room models for client presentations (1:12, 1:24)",
    "Custom cabinet hardware (knobs, pulls, handles)",
    "Decorative details (rosettes, appliqués, corner blocks)",
    "Prototype brackets and connectors",
    "Miniature furniture mockups for design approval",
    "Mold masters for silicone/resin casting",
    "Custom trim profiles for testing before CNC",
    "Presentation pieces for customer meetings"
  ]
}
```

### 2.3 Multi-Machine Workflow

```
Design Approved by Customer
    ↓
CraftForge Job Planner
    ↓
├── X-Carve Jobs:
│   ├── Shelf panels (plywood, CNC profile cuts)
│   ├── Cabinet doors (raised panel, decorative CNC patterns)
│   ├── Cornice/valance face shapes
│   ├── Decorative panels (geometric patterns, screens)
│   ├── Dado and rabbet joints
│   └── Edge profiles
│
├── Elegoo Saturn Jobs:
│   ├── 1:12 scale model of complete unit (client approval piece)
│   ├── Custom knobs and pulls (print → mold → cast in brass/nickel)
│   ├── Decorative rosettes and appliqués
│   ├── Custom brackets and hidden hardware
│   ├── Corner blocks and trim details
│   ├── Prototype joints (test fit before cutting wood)
│   └── Client presentation miniature
│
├── Manual/Shop Jobs:
│   ├── Frame assembly (pocket screws, dowels, biscuits)
│   ├── Edge banding
│   ├── Sanding and finishing
│   ├── Hardware installation
│   └── On-site installation
│
└── Materials Order:
    ├── Sheet goods (plywood, MDF — with nesting layout)
    ├── Solid wood (face frames, trim)
    ├── Hardware (hinges, slides, shelf pins)
    ├── Resin (for 3D prints)
    ├── Finish materials (stain, paint, poly, lacquer)
    └── Installation supplies (screws, anchors, shims)
```

---

## 3. SpaceScan — Spatial Scanning & Room Capture

### 3.1 Scan Methods

| Method | Device | Accuracy | Speed | Best For |
|--------|--------|----------|-------|----------|
| iPhone/iPad LiDAR | iPhone Pro / iPad Pro | ±1-2cm | 2-5 min | Quick room scans, client homes |
| Photogrammetry | Any phone camera | ±2-5cm | 5-10 min (capture) | When LiDAR not available |
| Manual Measurements | Tape measure + app input | ±1mm | 10-20 min | Precise final measurements |
| Hybrid | LiDAR scan + manual verification | ±2mm | 15 min | Production-ready accuracy |

### 3.2 Scan-to-Model Pipeline

```
Room Scan (LiDAR / Photos / Manual)
    ↓
3D Room Model Generation
    ↓
AI Space Analysis:
├── Wall detection (dimensions, angles, plumb verification)
├── Floor/ceiling heights
├── Window locations and sizes
├── Door locations and swing direction
├── Outlet/switch locations
├── Pipe/duct/vent locations
├── Existing furniture identification
├── Baseboard/crown molding profiles
├── Lighting fixture locations
└── Structural elements (beams, columns, soffits)
    ↓
Clean Room Model (walls, floor, ceiling with all obstacles mapped)
    ↓
Ready for design placement
```

### 3.3 Scan Apps Integration

**Recommended LiDAR scanning apps:**
- **Polycam** — room scanning, mesh export, floor plans
- **Scaniverse** — high quality 3D scans, free
- **3D Scanner App** — point cloud + mesh, measurement tools
- **RoomPlan** (Apple API) — structured room model with object detection
- **Magicplan** — floor plans from LiDAR, measurement reports

**Import formats:** OBJ, STL, PLY, USDZ, glTF, point cloud (LAZ/LAS/E57)

### 3.4 AI Space Analysis Features

Once the room is scanned, AI identifies:

```
Space Intelligence Report:
├── Available wall space: 14'3" × 8'0" (clear wall for built-in)
├── Obstacles:
│   ├── Electrical outlet at 14" from floor, 36" from left
│   ├── Light switch at 48" from floor, 6" from door frame
│   ├── HVAC register at floor level, 24" from right
│   └── Window: 36"×48" centered at 60" from left wall
├── Existing features:
│   ├── Baseboard: 5.5" tall, need to scribe or remove
│   ├── Crown molding: 4" — match profile for integration
│   └── Floor: hardwood, slight slope 1/8" over 8'
├── Structural notes:
│   ├── Wall type: drywall on wood studs (stud finder recommended)
│   └── Ceiling: flat, 8'0" — no soffits
└── Recommendations:
    ├── "This wall can support a full floor-to-ceiling unit"
    ├── "Route outlet to inside of cabinet — add outlet cutout"
    ├── "Leave 2" clearance around HVAC register"
    └── "Window seat opportunity below window"
```

---

## 4. Custom Millwork Designer

### 4.1 Product Types

**Built-In Shelving & Bookcases:**
- Floor-to-ceiling built-ins
- Floating shelves (wall-mounted)
- Window seat with storage below
- Entertainment centers / media walls
- Home office built-ins (desk + shelving)
- Library walls with ladder rail
- Display cases with lighting

**Closet Systems & Organizers:**
- Walk-in closet systems
- Reach-in closet organizers
- Wardrobe units
- Shoe storage
- Drawer inserts and dividers
- Pull-out accessories (tie rack, belt hook, valet)

**Kitchen & Bathroom Cabinetry:**
- Kitchen cabinets (upper, lower, tall/pantry)
- Bathroom vanities
- Kitchen islands
- Butler's pantry
- Laundry room storage
- Mudroom lockers and bench

**Furniture & Custom Pieces:**
- Headboards and bed frames
- Dining tables
- Coffee and end tables
- Desks and workstations
- Benches and banquettes
- Room dividers and screens
- Mantels and surrounds

### 4.2 Parametric Design Engine

Every product type has a parametric template that auto-adjusts to the scanned space.

```
Built-In Bookcase Parameters:
├── Overall: width, height, depth (auto-filled from scan)
├── Sections: number of vertical divisions
├── Shelves:
│   ├── Fixed vs adjustable
│   ├── Spacing (even, graduated, custom)
│   ├── Thickness
│   └── Nosing profile (square, bullnose, ogee — CNC cut)
├── Doors:
│   ├── Which sections have doors
│   ├── Door style (shaker, raised panel, glass, slab)
│   ├── Hinge type (overlay, inset, European)
│   └── Door panel CNC pattern (optional)
├── Drawers:
│   ├── Which sections have drawers
│   ├── Drawer face style (matching doors)
│   ├── Slide type (side mount, undermount, soft-close)
│   └── Dividers/organizers inside
├── Base:
│   ├── Toe kick (recessed)
│   ├── Furniture feet (turned legs, bun feet)
│   └── Platform base
├── Crown:
│   ├── None
│   ├── Simple cap
│   ├── Crown molding (match existing room)
│   └── Built-up crown (multi-piece)
├── Materials:
│   ├── Carcass (plywood, MDF, melamine)
│   ├── Face frame (hardwood, painted MDF)
│   ├── Shelves (plywood, solid wood)
│   ├── Doors (MDF for paint, hardwood for stain)
│   └── Back panel (1/4" plywood, beadboard)
├── Finish:
│   ├── Paint (color)
│   ├── Stain + clear coat
│   ├── Natural + clear coat
│   └── Two-tone (body + accent)
└── Hardware:
    ├── Knobs/pulls (from CraftForge library or 3D print custom)
    ├── Hinges
    ├── Shelf pins
    ├── Drawer slides
    └── Lighting (LED strip, puck lights)
```

### 4.3 Design-in-Space Workflow

```
Step 1: SCAN
    Customer's room scanned → 3D model generated
    ↓
Step 2: PLACE
    Select product type → drag into scanned room
    Auto-snaps to walls, adjusts to fit obstacles
    ↓
Step 3: CONFIGURE
    Adjust parameters: sections, shelves, doors, drawers
    AI suggests: "Based on your books/items, I recommend 12" shelf spacing"
    ↓
Step 4: STYLE
    Select materials, finish, hardware
    CNC patterns for door panels selected from library
    Custom hardware designed or selected
    ↓
Step 5: VISUALIZE
    Photorealistic render of unit IN the customer's actual room
    Before/after comparison
    3D walkthrough of the space with unit installed
    ↓
Step 6: APPROVE
    Customer reviews render
    Optional: 3D print 1:12 scale model on Elegoo Saturn
    Physical miniature handed to customer for approval
    ↓
Step 7: QUOTE
    Auto-generated quote:
    ├── Materials (with sheet nesting optimization)
    ├── CNC time (X-Carve)
    ├── 3D print items (Saturn)
    ├── Assembly labor
    ├── Finishing labor
    ├── Installation labor
    ├── Hardware costs
    ├── Tax
    └── Total with deposit schedule
    ↓
Step 8: FABRICATE
    CraftForge generates all cut files:
    ├── X-Carve: door panels, decorative elements, shelf nosing
    ├── Table saw: carcass panels (cut list from nesting)
    ├── Elegoo Saturn: custom hardware, prototypes, details
    └── Assembly sequence with step-by-step instructions
    ↓
Step 9: INSTALL
    On-site installation
    Before/after photos auto-captured for portfolio
    Customer signs off
    ↓
Step 10: PORTFOLIO
    Mockup vs reality comparison saved
    Marketing content auto-generated
    Review request sent to customer
```

---

## 5. Visualization — Show It in Their Room

### 5.1 Photo Render (AI Inpainting)

```
Original room photo + designed unit
    ↓
AI composites the unit into the photo:
├── Correct perspective and vanishing points
├── Matching lighting and shadows
├── Material textures rendered realistically
├── Reflections on glass doors
├── Objects on shelves (optional staging)
└── Before/after slider
```

**Same tech as Visual Mockup Engine** — shared rendering pipeline.

### 5.2 3D Room View

```
Scanned 3D room model + designed unit
    ↓
Three.js interactive viewer:
├── Orbit around the room
├── Walk through in first person
├── Toggle unit visible/hidden
├── Change materials in real-time
├── Open/close doors and drawers
├── Turn lights on/off
├── Measure anything (click two points)
└── Export screenshots from any angle
```

### 5.3 AR Preview

```
Customer opens phone camera → points at wall
    ↓
AR overlay shows:
├── Unit rendered at actual size on their wall
├── Walk around it, see it from different angles
├── Open doors (tap to interact)
├── Change materials live
├── Confirm it fits (no conflicts with outlets/windows)
└── Screenshot for approval
```

### 5.4 Physical Scale Model (Elegoo Saturn)

```
Design finalized
    ↓
CraftForge auto-generates:
├── 1:12 scale model of complete unit
├── Optional: 1:12 scale room context (walls, floor, window)
├── Split into printable sections (within 192×120×200mm build volume)
├── Assembly pins for multi-part models
├── Print time estimate (typically 4-8 hours)
└── Export as .stl with supports pre-generated
    ↓
Print on Elegoo Saturn
    ↓
Hand to customer at consultation:
"Here's a miniature of exactly what we're building for you"
```

**This is a massive sales closer.** No competitor hands the customer a physical model of their custom built-in. They can hold it, show their spouse, put it on their shelf while they decide.

---

## 6. Elegoo Saturn — Full Integration

### 6.1 Prototyping Pipeline

```
Design any component
    ↓
"Print prototype" button
    ↓
├── Auto-scale to fit Saturn build volume
├── If too large, split with alignment pins
├── Generate supports
├── Estimate print time and resin usage
├── Export .stl or send directly to slicer
    ↓
Test fit, adjust, finalize
    ↓
Cut real version on X-Carve
```

### 6.2 Custom Hardware Design

```
"Design a cabinet pull that matches this Art Deco style"
    ↓
AI generates 4 handle/pull designs
    ↓
User selects and refines
    ↓
Export for Elegoo Saturn:
├── Print in ABS-like resin (functional prototype)
├── Or print in castable resin → lost wax cast in brass/bronze
├── Or print final part in tough resin (functional for light-duty)
    ↓
Install on finished piece
```

**Hardware Library (3D Printable):**
- Cabinet knobs (round, square, geometric, organic, vintage)
- Drawer pulls (bar, cup, ring, bail)
- Decorative brackets and corbels
- Corner blocks and rosettes
- Shelf pins and custom supports
- Cable management clips and grommets
- Custom feet and levelers
- Door catches and stops
- Light fixture mounting brackets
- Custom hooks and hangers

### 6.3 Decorative Details

```
"Add a decorative rosette at the top of each pilaster"
    ↓
AI generates rosette designs matching the unit's style
    ↓
Print on Elegoo Saturn (fine detail at 0.05mm XY)
    ↓
Options:
├── Glue directly to wood piece (resin detail on wood)
├── Use as master → make silicone mold → cast multiples in resin
├── Use as master → make mold → cast in plaster/concrete
└── Paint/finish to match wood (faux wood grain technique)
```

### 6.4 Mold Making Pipeline (Advanced)

```
Print master on Elegoo Saturn (highest detail settings)
    ↓
Create silicone mold from master
    ↓
Cast multiples in:
├── Resin (various colors/finishes)
├── Plaster/hydrocal (architectural details)
├── Concrete (outdoor/heavy applications)
├── Low-melt metal (pewter, tin)
└── Wax → investment cast in brass/bronze (premium hardware)
    ↓
Finish and install
```

This means one 3D printed master can produce unlimited copies of custom hardware, rosettes, appliqués, and decorative details.

---

## 7. Quote System Integration

### 7.1 Auto-Generated Quote from Design

```
Completed Design → Quote Generator:

CUSTOM BUILT-IN BOOKCASE — Henderson Living Room
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Dimensions: 126" W × 96" H × 14" D (floor to ceiling, wall to wall)
Style: Traditional with shaker doors, crown molding

MATERIALS                                          COST
─────────────────────────────────────────────────────
3/4" maple plywood (carcass) — 6 sheets          $  720.00
3/4" MDF (doors, shelves) — 3 sheets             $  135.00
1/4" maple plywood (back panels)                  $   45.00
Poplar (face frames) — 40 board feet              $  160.00
Crown molding — 12 linear feet                    $   84.00
Base shoe molding — 12 linear feet                $   36.00
Edge banding — 100 feet                           $   35.00
                                        Subtotal: $1,215.00

HARDWARE
─────────────────────────────────────────────────────
European hinges (soft-close) × 16                 $  128.00
Drawer slides (undermount, soft-close) × 4        $  120.00
Shelf pins (1/4") — 100 pack                      $   12.00
Custom 3D printed pulls × 12                      $   36.00
LED puck lights × 6                               $   90.00
                                        Subtotal: $  386.00

CNC WORK (X-Carve)
─────────────────────────────────────────────────────
12 shaker door panels — profile + raised panel      4.5 hrs
8 decorative shelf nosing profiles                   1.5 hrs
2 pilaster fluting details                           1.0 hrs
Crown molding returns                                0.5 hrs
                                  Total CNC time:    7.5 hrs
                                            Cost: $  375.00

3D PRINTING (Elegoo Saturn)
─────────────────────────────────────────────────────
12 custom drawer/door pulls                          6.0 hrs
4 decorative rosettes                                3.0 hrs
1:12 scale presentation model                        8.0 hrs
                                Total print time:   17.0 hrs
                              Resin + print cost: $   85.00

LABOR
─────────────────────────────────────────────────────
Design & engineering                    4 hrs     $  300.00
CNC setup & cutting                     8 hrs     $  400.00
Carcass assembly                       12 hrs     $  600.00
Door & drawer assembly                  6 hrs     $  300.00
Sanding & prep                          8 hrs     $  400.00
Finishing (2 coats primer + 2 coats paint)
                                       10 hrs     $  500.00
Delivery                                2 hrs     $  150.00
Installation                            8 hrs     $  600.00
                                        Subtotal: $3,250.00

─────────────────────────────────────────────────────
Materials                                         $1,215.00
Hardware                                          $  386.00
CNC + 3D Printing                                 $  460.00
Labor                                             $3,250.00
─────────────────────────────────────────────────────
SUBTOTAL                                          $5,311.00
Tax (6%)                                          $  318.66
─────────────────────────────────────────────────────
TOTAL                                             $5,629.66

Deposit (50%):      $2,814.83 due at approval
Balance:            $2,814.83 due at installation

Estimated timeline: 3-4 weeks from deposit
```

### 7.2 Quote Accuracy Engine

CraftForge learns from completed jobs:
- Track actual vs estimated material usage
- Track actual vs estimated labor hours
- Adjust future quotes based on real data
- Flag quotes that seem too low or too high
- Seasonal material price adjustments

---

## 8. Implementation Priority — SpaceScan Addendum

### Phase 1 — Room Scan Import (Add to CraftForge Phase 2)
1. Import LiDAR scans (OBJ/USDZ from Polycam/Scaniverse)
2. Wall/floor/ceiling detection
3. Basic measurement extraction
4. Obstacle identification (windows, doors, outlets)

### Phase 2 — Parametric Built-In Designer (Add to CraftForge Phase 3)
5. Bookcase/shelving parametric template
6. Closet system parametric template
7. Cabinet parametric template
8. Place design in scanned room model
9. 3D viewer with orbit/walk-through
10. Material and hardware selection

### Phase 3 — Visualization (Add to CraftForge Phase 3)
11. AI render into original room photo
12. Before/after comparison
13. 1:12 scale model export for Elegoo Saturn
14. AR preview (phone camera overlay)

### Phase 4 — Multi-Machine Fabrication (Add to CraftForge Phase 3-4)
15. X-Carve job generation from design
16. Elegoo Saturn job generation (hardware, prototypes, models)
17. Cut list generation for table saw/manual cuts
18. Assembly instructions generation
19. Integrated quote from design parameters

### Phase 5 — Intelligence (Add to CraftForge Phase 5)
20. Quote accuracy learning from completed jobs
21. Material price tracking and auto-updating
22. Customer preference learning (style, budget patterns)
23. Automated reorder suggestions for common materials

---

## 9. Example Scenarios

**Scenario 1: Henderson living room built-in**
→ Scan living room with iPad LiDAR → AI: "14'3" clear wall, one outlet at 14" height, hardwood floors" → Design floor-to-ceiling bookcase with 5 sections → Shaker doors on bottom 4, open shelves on top → CNC door panels on X-Carve → 3D print custom Art Deco pulls on Saturn → Print 1:12 model for Henderson to approve → Quote: $5,629 → Henderson approves at kitchen table holding the miniature → Build → Install → Before/after photos → Portfolio

**Scenario 2: Master closet redesign**
→ Scan walk-in closet → AI maps: 3 walls, one door, one window, angled ceiling on right → Design: double-hang section, long-hang section, shoe tower, drawer stack, pull-out accessories → All configured to work around window and ceiling angle → Render shows closet organized and full → Customer sees their clothes virtually placed → Quote: $3,800 → Approve → Fabricate

**Scenario 3: Kitchen cabinet doors replacement**
→ Customer wants to reface existing cabinets → Measure all door and drawer fronts (28 doors, 8 drawers) → Select raised panel style with beaded detail → CraftForge batch-generates all 36 pieces → Sheet nesting: 9 sheets of 3/4" MDF → X-Carve cuts all panels over 2 days → 3D print custom knobs (match existing house style) → Paint and install → Quote: $4,200

**Scenario 4: Client can't decide — physical model closes the deal**
→ Customer torn between modern slab doors vs traditional raised panel → Print BOTH versions at 1:12 scale on Saturn → Meeting: "Here, hold both options" → Customer immediately picks raised panel → "I couldn't tell from pictures but holding it, I can feel the detail" → Sale closed

**Scenario 5: Custom home office**
→ Scan spare bedroom → AI: "12'×10' room, one window centered, closet on right" → Design: L-shaped desk built into corner, floating shelves above, closet converted to storage/printer station → CNC cuts desk with cable management channels → 3D print custom USB hub housing and monitor arm bracket → Render shows the home office in the room before building → Quote: $4,100

---

## 10. Competitive Advantage

**No custom millwork shop in DC is doing this:**

| Traditional Shop | CraftForge-Powered Shop |
|-----------------|------------------------|
| Measure with tape, sketch on paper | LiDAR scan, 3D model in minutes |
| Show customer catalog photos | Show customer THEIR room with the unit rendered in it |
| "Trust me, it'll look great" | Hand customer a 1:12 scale physical model |
| Manual cut lists, lots of math | AI-optimized nesting, zero math errors |
| Quote takes days | Quote generated in minutes from design |
| One revision before customer pays more | Unlimited digital revisions before cutting |
| No CNC details — everything manual | CNC-cut door panels, decorative details, precision joints |
| Stock hardware from catalog | Custom 3D-printed hardware matching their style |
| Portfolio is phone photos | Professional before/after renders + reality comparison |

**WorkroomForge becomes a full design-build studio:**
- Window treatments (soft furnishings)
- Cornices and valances (CNC-cut + fabric wrapped)
- Custom built-ins (shelving, bookcases, entertainment centers)
- Closet systems
- Cabinet refacing
- Custom furniture pieces
- All visualized, quoted, and fabricated with AI assistance
