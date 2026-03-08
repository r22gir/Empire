# CraftForge Status Report — 2026-03-08

## Executive Summary

CraftForge has **1,500+ lines of detailed specs** across 2 documents but **ZERO functional code**. Only a placeholder dashboard page (131 lines) exists in the Empire Command Center. No backend, no CNC engine, no templates, no marketplace.

---

## 1. What's Specced

### Two Spec Documents
- **CRAFTFORGE_SPEC.md** (800 lines) — Core platform spec
- **CRAFTFORGE_SPACESCAN_ADDENDUM.md** (693 lines) — Room scanning + multi-machine workflow

### Four CNC Pipelines
| Pipeline | Input | Output | Status |
|----------|-------|--------|--------|
| Text -> CNC | Plain English description | SVG/DXF + STL/OBJ + G-code | Specced only |
| Photo/Image -> CNC | Photo upload | Segmented vectors + cut files | Specced only |
| 3D Scan -> CNC | LiDAR/photogrammetry mesh | Cleaned mesh + toolpaths | Specced only |
| Template Library | Parametric templates | Customized designs + G-code | Specced only |

### Machine Intelligence Layer
- Machine profiles: ShopBot, GRBL, Mach3/4, LinuxCNC, Carbide Motion, Onefinity, Vectric
- AI toolpath generation (auto tool selection, feeds/speeds per material)
- Job time + cost estimator (CNC time, tool changes, material, finishing, retail price)

### CNC Plan Marketplace
- 15-20% commission model, $29/mo subscription tier
- Listings include: SVG/DXF, STL/OBJ, G-code (multi-controller), drawings, material lists
- Seller dashboard with pricing recommendations, analytics, version control

### SpaceScan Module (Addendum)
- Room scanning via iPhone LiDAR, photogrammetry, manual, or hybrid
- AI wall/floor/ceiling/outlet detection
- Custom millwork designer (built-ins, closets, cabinetry, furniture)
- AR preview + 1:12 scale 3D-printed models (Elegoo Saturn)

### SaaS Tiers
| Tier | Price | Limits |
|------|-------|--------|
| Free | $0 | 10 templates, 5 AI gens/mo |
| Hobby | $29/mo | 50 gens, 3 machines |
| Pro | $79/mo | 200 gens, 10 machines |
| Business | $199/mo | Unlimited, API, white label |

### 5-Phase Implementation Plan (from spec)
1. **MVP**: Text->2D profile, 20 cornice templates, 10 cabinet doors, SVG/DXF export
2. **Phase 2**: Photo->vector, Photo->3D relief, Three.js viewer, AI refinement
3. **Phase 3**: Machine profiles, G-code generation, CNC simulation, nesting, 3D scan
4. **Phase 4**: Marketplace, Stripe, seller dashboard, subscriptions
5. **Phase 5**: AR preview, 3D print export, collaborative design, mobile, voice

---

## 2. What Code Exists

### Status: NEAR-ZERO

| Component | Exists? | Details |
|-----------|---------|---------|
| `~/Empire/craftforge/` directory | NO | Does not exist |
| Backend Python code | NO | Zero CraftForge files in backend/ |
| `/api/v1/craft/*` endpoints | NO | None |
| CraftForgePage.tsx (UI) | YES | 131-line placeholder in empire-command-center — all KPI values show "--" |
| Command Center tab | YES | Yellow tab in TopBar.tsx |
| QuickSwitch entry | YES | Ctrl+K shortcut, Hammer icon |
| Brain memory entries | YES | 2 entries in seed_brain.py |
| G-code generation | NO | — |
| Mesh processing | NO | — |
| Template library | NO | — |
| Machine profiles | NO | — |
| CNC marketplace | NO | — |

---

## 3. What It Needs for Empire Workroom (Internal)

CraftForge is the CNC production arm for Empire Workroom custom products:

- **Cornices**: CNC-cut face profiles (scalloped, arched, straight, decorative) from MDF/plywood. Return pieces, mounting boards, batting templates, fabric cutting templates.
- **Valances**: Board-mounted shapes, similar to cornices but different construction.
- **Headboards**: Custom shapes and carvings. King/queen/full sizes. Art Deco, geometric, traditional.
- **Cabinet doors**: Raised panel, shaker, flat panel with CNC patterns. Batch processing for kitchens. Sheet nesting optimization.
- **Furniture details**: Table legs, chair backs, rosettes, appliques.

**Integration flow**: Customer approves Empire Workroom mockup -> CraftForge receives shape/dimensions/style -> generates CNC-ready cut file -> cut queue with material requirements -> X-Carve cuts -> workroom wraps with fabric -> install.

---

## 4. What It Needs for External Customers (SaaS)

- **Woodworkers/makers**: Text-to-CNC design, photo-to-CNC extraction, template library, machine profiles, G-code export
- **Sign shops**: Dimensional sign design, carved letters, logo conversion, V-carve toolpaths
- **Furniture builders**: Full 3D design, multi-component projects, sheet nesting
- **All users**: CNC Plan Marketplace (buy/sell), subscriptions, machine compatibility checks, CNC simulation

---

## 5. Relationship to Empire Workroom

**CraftForge is the wood/CNC mirror of Empire Workroom (fabric/upholstery).** Both are RG's full internal businesses with ALL tools and features. WorkroomForge is the stripped-down SaaS module sold to external customers — it does NOT represent the full feature set.

### Shared QuickBooks-Level Business Management

Both Empire Workroom AND CraftForge get full QB-like capabilities:

| QB-Level Feature | Description |
|-----------------|-------------|
| **Estimates/Quotes** | Multi-tier proposals, PDF generation, customer approval flow |
| **Invoicing** | Convert quotes to invoices, payment tracking, deposit schedules |
| **Customer Management (CRM)** | Contact database, interaction history, preferences, notes |
| **Job/Production Tracking** | Status pipeline (Draft → Approved → In Production → Complete → Installed), scheduling |
| **Inventory Management** | Stock levels, reorder points, vendor catalog, cost tracking |
| **Accounts Receivable** | Outstanding balances, payment history, aging reports |
| **Accounts Payable** | Vendor bills, purchase orders, material costs |
| **Revenue Reporting** | Dashboard KPIs, monthly/quarterly/annual P&L, margins by product |
| **Expense Tracking** | Material costs, labor, overhead, per-job profitability |
| **Shipping/Fulfillment** | EasyPost integration, tracking, delivery confirmation |
| **Vendor Management** | Supplier database, pricing, lead times, order history |
| **Tax Management** | Sales tax calculation, tax reports |
| **Time Tracking** | Labor hours per job, employee productivity |
| **Document Management** | Contracts, photos, specs, PDFs per customer/job |

Empire Workroom applies these to **fabric, drapery, upholstery** jobs.
CraftForge applies these to **wood, CNC, 3D print** jobs — PLUS the CNC-specific features below.

### CraftForge gets ALL Empire Workroom features PLUS CNC + 3D print:

| Feature | Empire Workroom | CraftForge |
|---------|----------------|------------|
| AI photo analysis | YES | YES + Photo-to-CNC |
| AI mockups / inpainting | YES | YES + CNC product visualization |
| Quote system (3-tier PDF) | YES | YES + CNC time/material costs |
| Customer pipeline | YES | YES |
| Measurement tools | YES | YES + 3D scan import |
| Marketplace | YES | YES + CNC Plan Marketplace |
| Shipping integration | YES | YES |
| AI routing (Grok/Claude/Ollama) | YES | YES |
| Tool executor framework | YES | YES + CNC-specific tools |
| Desk personas (12 AI desks) | YES | YES |
| **G-code generation** | — | **NEW** |
| **3D mesh processing** | — | **NEW** |
| **SVG/DXF vector engine** | — | **NEW** |
| **Sheet nesting algorithm** | — | **NEW** |
| **Machine profile system** | — | **NEW** |
| **CNC simulation viewer** | — | **NEW** |
| **Parametric template system** | — | **NEW** |
| **3D scan import/cleanup** | — | **NEW** |
| **SpaceScan room capture** | — | **NEW** |
| **3D printing (Elegoo Saturn)** | — | **NEW** |
| **1:12 scale model generation** | — | **NEW** |

### Backend reuse from Empire Workroom (direct, not stripped down)
| Component | Lines | CraftForge Use |
|-----------|-------|----------------|
| `quotes.py` | 1,874+ | Full quote system + CNC time/material costs |
| `vision.py` | 514 | Full vision pipeline + Photo-to-CNC |
| `marketplace/` routers | ~500 | Full marketplace + CNC plans |
| `ai_router.py` | — | Same AI routing |
| `tool_executor.py` | — | Same framework + CNC tools |
| `inpaint_service.py` | — | Same inpainting + CNC product visualization |
| `shipping_service.py` | — | Same shipping integration |

---

## 6. Architecture Context

- RG runs two full businesses: Empire Workroom (fabric/upholstery) and CraftForge (wood/CNC)
- WorkroomForge is the SaaS MODULE sold to customers — NOT the full Empire Workroom
- Yellow business tab in Command Center UI
- Strategy desk (Vanguard) is working on CraftForge planning
- Priority order: Empire Workroom (revenue) > CraftForge (product) > SocialForge (growth)
- Going through Zero to Hero pipeline
- Not yet in the v4 architecture Mermaid diagram

---

## 7. Key Machines

| Machine | Type | Bed/Volume | Controller |
|---------|------|-----------|------------|
| Inventables X-Carve | CNC Router | 750x750x65mm | GRBL |
| Elegoo Saturn | Resin 3D Printer | 192x120x200mm | ChiTuBox |

---

## 8. Recovered File References

| Source | CraftForge Info |
|--------|----------------|
| Session context Mar 7 | "RG's Woodwork & CNC Business. Full spec exists, ZERO code built." |
| Session context Mar 8 | CraftForge as second business column, CNC pipelines: Text->CNC, Photo->CNC, 3D Scan->CNC |
| Architecture FINAL PDF | CraftForge column with CNC pipeline details, integrated with Empire Platform SaaS tiers |
| Architecture Map PDF | CraftForge "full spec exists, ZERO code" — explicitly noted |
| memory_v4.md | Listed under Specced/Planned only |
| seed_brain.py | Marked "in development" (should be "specced only") |
| Backup drive | No CraftForge files found |

---

*Generated 2026-03-08 by Claude Code*
