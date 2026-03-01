# Visual Product Mockup Engine — Technical Specification
## WorkroomForge → Expanding to All Empire Product Lines

**Version:** 1.0
**Date:** February 27, 2026
**Status:** Spec Ready for Implementation

---

## 1. Overview

The Visual Product Mockup Engine allows customers and founders to upload a photo of any room, window, bed, or piece of furniture — and instantly see professional window treatments, bedding, upholstery, and soft furnishings rendered onto the real space. The system extracts the target item from the photo, applies selected products and fabrics, and regenerates the image showing exactly how the finished product will look in the customer's actual room.

**Core Principle:** The customer sees their room with the finished product before a single stitch is sewn.

**Revenue Impact:** Eliminates "I can't visualize it" objections, accelerates customer approval, enables remote consultations, and builds a portfolio automatically.

---

## 2. Product Lines Covered

### 2.1 Window Treatments (WorkroomForge Primary)
- Drapes & curtains (pinch pleat, ripple fold, grommet, rod pocket, tab top)
- Sheers & semi-sheers
- Roman shades (flat, hobbled, balloon, Austrian)
- Roller shades & solar shades
- Cellular/honeycomb shades
- Woven wood/bamboo shades
- Shutters (plantation, café)

### 2.2 Valances & Cornices
- Box pleat valances
- Kingston/London valances
- Board-mounted cornices (straight, shaped, upholstered)
- Swags & jabots/cascades
- Rod-pocket valances
- Balloon valances

### 2.3 Bedding
- Duvets & duvet covers
- Bedspreads & coverlets
- Bed skirts (tailored, gathered, box pleat)
- Euro shams & decorative pillows
- Headboards (upholstered)
- Bolsters & throws
- Coordinated bedding sets (full ensemble view)

### 2.4 Upholstery & Soft Furnishings
- Sofa reupholstery (cushions, arms, back, skirt)
- Chair reupholstery
- Slipcovers
- Cushion covers (piping/welting options)
- Bench/banquette cushions
- Outdoor cushions & furniture covers

### 2.5 Decorative
- Table runners & placemats
- Throw pillows (accent/decorative)
- Ottoman covers

---

## 3. Core Engine — Three-Stage Pipeline

### Stage 1: Extract & Segment

Customer uploads a photo of their room/window/furniture. The AI identifies and isolates the target item.

```
Photo Upload
    ↓
Object Detection (identify windows, beds, sofas, chairs)
    ↓
Segmentation (extract precise outline/mask of target item)
    ↓
Outputs:
  ├── Clean mask/silhouette of the item
  ├── Line drawing/outline (optional — for technical reference)
  ├── Room context preserved (everything except the target item)
  └── Dimensional estimates (relative proportions)
```

**AI Options for Segmentation:**
- **Primary:** Gemini 2.5 conversational segmentation (can segment by description: "the window on the left wall")
- **Fallback:** Meta SAM-2 (Segment Anything Model) via Replicate API
- **On-device (future):** MediaPipe Interactive Segmenter for instant mobile segmentation

**Key Capability:** User can click or describe which item to target. "The big window behind the couch" → AI knows exactly which object to segment.

### Stage 2: Design & Configure

User selects product type and fabric/material.

```
Product Selection
    ↓
├── Treatment Type (drapes, roman shade, cornice, etc.)
├── Style Options (pleat style, mount type, fullness, etc.)
├── Fabric Selection:
│   ├── Basic Color Fill (solid colors — immediate, no API needed)
│   ├── Fabric Code Import (enter supplier code → pull from website)
│   └── Photo Upload (photograph of physical swatch)
├── Hardware Selection (rod, track, rings, finials — for window treatments)
└── Configuration Details:
    ├── Stack direction (left, right, split)
    ├── Length (sill, below sill, floor, puddle)
    ├── Fullness (standard 2x, generous 2.5x, minimal 1.5x)
    ├── Lining (unlined, lined, blackout, interlining)
    └── Mount (inside, outside, ceiling)
```

**Fabric Selection — Three Tiers:**

| Tier | Method | Speed | Quality |
|------|--------|-------|---------|
| **Quick** | Basic color fill (solid color palette) | Instant | Good for concept |
| **Standard** | Fabric code → scrape supplier image | 5-10 sec | Realistic pattern |
| **Premium** | Upload swatch photo → AI texture extraction | 10-15 sec | Most accurate |

**Fabric Code Triangulation:**
1. Customer says "Kravet 36922.16" or "Robert Allen Boucle Luxe Driftwood"
2. System searches supplier website for that fabric code
3. Pulls fabric image, pattern repeat, color info
4. Applies to mockup with correct scale and repeat

### Stage 3: Render & Reimagine

AI generates the final mockup — the original room with the selected product rendered in place.

```
Segmented Room + Product Config + Fabric
    ↓
AI Image Generation (inpainting/compositing)
    ↓
Outputs:
  ├── Full room render with product installed
  ├── Before/after comparison (slider)
  ├── Close-up detail view (fabric texture, pleats, folds)
  └── Multiple options side-by-side (up to 4)
```

**AI Options for Rendering:**
- **Primary:** Stable Diffusion XL inpainting (self-hosted or Replicate API)
- **Alternative:** GPT-4o image editing (good for quick concept renders)
- **Alternative:** PromeAI / Spacely AI APIs (specialized for interior design)
- **Fallback:** Composite overlay (non-AI — faster, less realistic, works offline)

---

## 4. Fabric System

### 4.1 Basic Color Palette (Built-In — No External Dependencies)

Pre-loaded solid colors organized by category:

```
Whites & Creams:  Pure White, Ivory, Cream, Eggshell, Linen White, Pearl
Neutrals:        Beige, Taupe, Sand, Greige, Mushroom, Stone
Grays:           Light Gray, Silver, Dove, Charcoal, Slate, Graphite
Blues:            Sky, Powder, Cornflower, Navy, Royal, Teal, Ocean
Greens:          Sage, Olive, Hunter, Emerald, Mint, Forest
Reds/Pinks:      Blush, Rose, Coral, Burgundy, Crimson, Wine
Yellows/Golds:   Butter, Gold, Honey, Amber, Champagne, Marigold
Browns:          Tan, Camel, Chocolate, Espresso, Walnut, Cognac
Purples:         Lavender, Lilac, Plum, Eggplant, Amethyst, Aubergine
Blacks:          True Black, Onyx, Jet, Off-Black
```

Each color includes:
- Hex value for digital display
- RGB for rendering
- Visual weight hint (light/medium/heavy — affects drape simulation)
- Sheen level (matte, satin, silk) — affects light reflection in render

### 4.2 Fabric Code Import (Supplier Integration)

Supported workflow:
1. User enters fabric code (e.g., "Kravet 36922.16")
2. Backend constructs search URL for supplier website
3. Scrapes or API-fetches fabric swatch image + metadata
4. Extracts: image, pattern repeat dimensions, fiber content, width, price/yard
5. Caches locally for reuse

**Target Suppliers (DC market):**
- Kravet / Lee Jofa / Brunschwig & Fils
- Robert Allen / Beacon Hill
- Fabricut / S. Harris / Vervain
- Schumacher
- Duralee
- Greenhouse Fabrics
- Sunbrella (outdoor)

**Data Extracted Per Fabric:**
```json
{
  "code": "Kravet 36922.16",
  "name": "Boucle Luxe Driftwood",
  "supplier": "Kravet",
  "image_url": "https://...",
  "swatch_image": "<cached locally>",
  "pattern_repeat_h": 0,
  "pattern_repeat_v": 0,
  "width_inches": 54,
  "fiber_content": "100% Polyester",
  "price_per_yard": 89.00,
  "color_family": "neutral",
  "weight": "medium",
  "suitable_for": ["drapery", "upholstery", "pillows"]
}
```

### 4.3 Photo Swatch Upload

For fabrics not in digital catalogs:
1. User photographs physical swatch
2. AI extracts texture, pattern, color
3. Generates a tileable texture from the swatch photo
4. Applies to mockup with correct repeat and scale

---

## 5. Product-Specific Rendering Rules

### 5.1 Window Treatments — Drapes

**Rendering must account for:**
- Pleat style affects fabric fold pattern (pinch pleat = defined folds, ripple fold = wave pattern)
- Fullness ratio determines how much fabric shows (2x = standard)
- Stack-back: when open, drapes stack to the sides — show this correctly
- Floor length vs puddle vs floating (1/2" above floor)
- Leading edge and return to wall
- Lining visibility from exterior (white lining default)
- Light interaction: sheers show light through, blackout blocks all

**Configuration options shown in mockup:**
- Open position (stacked to sides)
- Closed position (covering window)
- Partially open (one panel drawn)

### 5.2 Roman Shades

- Flat fold pattern when lowered
- Stacking/folding pattern when raised
- Hobbled style shows continuous soft folds
- Show inside-mount vs outside-mount difference
- Light gap visualization for inside mount

### 5.3 Cornices & Valances

- Board-mounted cornices show as solid structure above window
- Shaped cornice shows custom bottom edge profile
- Valance shows fabric drape/pleats above window
- Combined: cornice over drapes, valance over shades

### 5.4 Bedding

- Show full bed ensemble from multiple angles (straight-on, 3/4 view)
- Coordinate multiple fabrics: duvet + shams + skirt + pillows
- Each element can have different fabric
- Show how bedding drapes over mattress edge
- Pillow arrangement options (sleeping pillows, euros, decorative, bolster)

### 5.5 Upholstery

- Different fabric zones: seat cushion, back, arms, skirt
- Piping/welting can be contrasting fabric
- Show tufting, channeling, or smooth options
- Cushion fill affects how fabric drapes (down vs foam)

---

## 6. User Interface — Mockup Studio

### 6.1 In Command Center (MAX Integration)

Mockup Studio is a canvas mode within the Response Canvas system:

```
User: "Show me what roman shades would look like on Mrs. Henderson's living room windows"
    ↓
MAX: Activates Mockup Canvas Mode
    ↓
1. Loads customer photo (from CRM or request upload)
2. Segments windows automatically
3. Shows product selector (treatment type, color/fabric)
4. Renders mockup in real-time
5. Offers: "Try another fabric?" / "Compare options?" / "Generate quote?"
```

**Canvas Layout (Mockup Mode):**
```
┌─────────────────────────────────────────────────────┐
│ [Before]          [After]            [Compare]       │
│ ┌──────────────────────────────────────────────────┐ │
│ │                                                  │ │
│ │           Room Photo / Mockup Display            │ │
│ │        (with before/after slider overlay)        │ │
│ │                                                  │ │
│ └──────────────────────────────────────────────────┘ │
│                                                      │
│ ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐ │
│ │ Option A │ │ Option B │ │ Option C │ │ Option D │ │
│ │ (thumb)  │ │ (thumb)  │ │ (thumb)  │ │ (thumb)  │ │
│ └──────────┘ └──────────┘ └──────────┘ └──────────┘ │
│                                                      │
│ Product: [Pinch Pleat Drapes ▼]  Fabric: [███ Navy]  │
│ Length:  [Floor ▼]  Mount: [Outside ▼]  Fullness: 2x │
│                                                      │
│ [💾 Save] [📤 Send to Customer] [📋 Generate Quote]  │
└─────────────────────────────────────────────────────┘
```

### 6.2 Customer-Facing View (Future — WorkroomForge Website)

Simplified version for customer self-service:
- Upload photo
- Pick treatment type from visual menu
- Pick colors (basic palette only — no supplier codes)
- See mockup
- Request consultation with full mockup attached
- No pricing shown (consultation required for quotes)

### 6.3 Telegram Integration

- Customer sends photo via Telegram to MAX bot
- MAX responds: "I can show you how different treatments would look. What type are you interested in?"
- Customer selects from quick-reply buttons
- MAX generates mockup and sends as image
- Customer approves → triggers consultation scheduling

---

## 7. Integration with Quote System

The mockup flows directly into the estimate/quote workflow:

```
Mockup Approved by Customer
    ↓
Auto-populate quote with:
├── Product type & style from mockup config
├── Fabric code, price/yard, yardage calculation
├── Window/furniture dimensions (from photo estimate + on-site verify)
├── Hardware requirements
├── Labor estimate based on product complexity
├── Installation details
└── Total with tax, deposit schedule
    ↓
Generate PDF Quote (per Quote System spec)
    ↓
Send to customer via email/Telegram
```

**Yardage Calculation (auto from mockup config):**
```
Drape Yardage = (Finished Width × Fullness × Number of Panels) / Fabric Width
              + Pattern Repeat Waste
              + Hem & Header Allowance

Example:
  Window: 72" wide, floor length (96")
  Fabric: 54" wide, 12" vertical repeat
  Style: Pinch pleat, 2.5x fullness, 2 panels
  
  Cut length = 96" + 16" (header/hem) + 12" (repeat) = 124" per panel
  Total width = 72" × 2.5 = 180" → 180/54 = 3.33 → 4 widths
  Yardage = (124" × 4) / 36" = 13.78 → 14 yards
  + 10% waste = 15.4 → 16 yards
```

---

## 8. AI Recommendations Engine

### 8.1 Style Matching
Based on room analysis (furniture style, colors, architecture):
- "This room has traditional architecture — I'd recommend pinch pleat drapes or a tailored cornice"
- "The modern furniture suggests clean lines — ripple fold or roller shades would complement well"

### 8.2 Color Coordination
Based on room colors extracted from photo:
- "Your wall color (warm gray) pairs well with navy, gold, or sage fabrics"
- "The existing furniture is warm-toned — avoid cool whites, try ivory or cream instead"

### 8.3 Upsell Suggestions
Contextual add-on recommendations:
- "This window would look even better with a cornice over the drapes"
- "Adding matching throw pillows would tie the bedding to the window treatments"
- "Consider a roman shade under the drapes for light control"

### 8.4 Light & Privacy Analysis
Based on window orientation and room type:
- "This is a bedroom — blackout lining recommended"
- "East-facing window — morning light may need solar shades"
- "Street-level window — consider a sheer for daytime privacy"

---

## 9. Portfolio & Marketing Integration

### 9.1 Before/After Auto-Capture
Every completed mockup generates:
- Before photo (original)
- After render (with treatment)
- Side-by-side comparison image
- Metadata: product type, fabric, style

### 9.2 Portfolio Builder
- Auto-save to portfolio gallery organized by product type
- Tag with: room type, style, fabric, price range
- Watermark with WorkroomForge branding
- Export for Instagram, website, marketing

### 9.3 Customer Testimonial Pairing
- Link completed project photos (actual installation) with original mockup
- "Here's what we showed them → here's what we delivered"
- Powerful proof of accuracy for marketing

### 9.4 SocialForge Integration
- Auto-generate social posts from mockups
- "Before/after transformation" content format
- Hashtag and caption generation
- Schedule across platforms

---

## 10. Technical Architecture

### 10.1 New Components

| Component | Purpose | Priority |
|-----------|---------|----------|
| `MockupStudio.tsx` | Main mockup interface, canvas mode | Phase 1 |
| `PhotoUploader.tsx` | Upload & manage customer room photos | Phase 1 |
| `SegmentationEngine.ts` | AI segmentation orchestration | Phase 1 |
| `ProductSelector.tsx` | Treatment type & style picker | Phase 1 |
| `ColorPalette.tsx` | Basic color fill selector | Phase 1 |
| `FabricCodeLookup.tsx` | Supplier code search & import | Phase 2 |
| `SwatchUploader.tsx` | Physical swatch photo processing | Phase 2 |
| `MockupRenderer.ts` | AI rendering orchestration | Phase 1 |
| `BeforeAfterSlider.tsx` | Comparison slider overlay | Phase 1 |
| `OptionGrid.tsx` | Side-by-side option comparison (up to 4) | Phase 1 |
| `MockupToQuote.ts` | Auto-populate quote from mockup config | Phase 2 |
| `YardageCalculator.ts` | Fabric yardage computation | Phase 2 |
| `PortfolioManager.tsx` | Save & organize completed mockups | Phase 3 |
| `TelegramMockup.ts` | Send/receive mockups via Telegram bot | Phase 3 |
| `StyleRecommender.ts` | AI style & color recommendations | Phase 3 |

### 10.2 API Endpoints (Backend — FastAPI)

```
POST   /api/mockup/upload          — Upload room photo
POST   /api/mockup/segment         — Segment target item from photo
POST   /api/mockup/render          — Generate mockup with product + fabric
GET    /api/mockup/{id}            — Get mockup by ID
GET    /api/mockup/customer/{id}   — All mockups for a customer
POST   /api/mockup/compare         — Generate comparison grid
POST   /api/mockup/to-quote        — Convert mockup to quote draft

POST   /api/fabric/lookup          — Search fabric by supplier code
POST   /api/fabric/upload-swatch   — Upload and process physical swatch
GET    /api/fabric/colors           — Get basic color palette
GET    /api/fabric/cache/{code}    — Get cached fabric data

POST   /api/portfolio/save         — Save mockup to portfolio
GET    /api/portfolio               — Get all portfolio items
POST   /api/portfolio/export       — Export for social media
```

### 10.3 Data Models

```python
# Mockup
class Mockup(BaseModel):
    id: str
    customer_id: str | None
    original_photo: str          # path to uploaded photo
    segmentation_mask: str       # path to generated mask
    product_type: str            # "drapes", "roman_shade", "cornice", etc.
    product_config: dict         # style, mount, length, fullness, etc.
    fabric: FabricSelection
    rendered_image: str          # path to final mockup
    options: list[str]           # paths to alternative renders
    status: str                  # "draft", "approved", "quoted", "ordered"
    created_at: datetime
    quote_id: str | None

# Fabric Selection
class FabricSelection(BaseModel):
    method: str                  # "color", "code", "swatch"
    color_hex: str | None        # for basic color fill
    supplier_code: str | None    # for fabric code import
    supplier_name: str | None
    swatch_image: str | None     # for uploaded swatch
    pattern_repeat_h: float | None
    pattern_repeat_v: float | None
    width_inches: float | None
    price_per_yard: float | None
    name: str | None

# Portfolio Item
class PortfolioItem(BaseModel):
    id: str
    mockup_id: str
    before_image: str
    after_image: str
    comparison_image: str
    product_type: str
    fabric_name: str
    room_type: str               # "living_room", "bedroom", "dining", etc.
    style_tags: list[str]
    customer_testimonial: str | None
    actual_install_photo: str | None
    published: bool
    created_at: datetime
```

### 10.4 Data Flow

```
Customer Photo → Upload API → Storage
    ↓
Segmentation API → Gemini 2.5 / SAM-2 → Mask + Outline
    ↓
Product Config (user selections) + Fabric Selection
    ↓
Render API → SD XL Inpaint / GPT-4o / Composite Engine
    ↓
Mockup Result → Display in Canvas / Send via Telegram
    ↓
Customer Approves → Quote System → PDF → Send
    ↓
Portfolio Auto-Save → Marketing Pipeline
```

### 10.5 External Services Required

| Service | Purpose | Cost Model |
|---------|---------|------------|
| Gemini 2.5 API | Image segmentation | Per-request |
| Replicate (SAM-2) | Fallback segmentation | Per-second compute |
| Stable Diffusion XL | Mockup rendering (inpainting) | Self-hosted or Replicate |
| GPT-4o | Quick concept renders | Per-request |
| xAI Grok | Already integrated for MAX | Existing plan |

---

## 11. Implementation Priority

### Phase 1 — MVP (Build First)
1. Photo upload and storage
2. Basic segmentation (Gemini API — segment window from room photo)
3. Basic color fill palette (solid colors applied to treatment shape)
4. Simple composite rendering (overlay treatment silhouette with color on room)
5. Before/after slider
6. Integration with Response Canvas as a new mode
7. Support for: drapes, roman shades, roller shades (most common products)

### Phase 2 — Fabric Intelligence
8. Fabric code lookup (Kravet, Robert Allen, Fabricut — top 3 suppliers first)
9. AI-powered inpainting renders (realistic fabric on window)
10. Swatch photo upload and texture extraction
11. Pattern repeat visualization
12. Side-by-side comparison grid (up to 4 options)
13. Yardage calculator wired to mockup config
14. Quote system integration (mockup → quote draft)
15. Add product types: cornices, valances, bedding

### Phase 3 — Full Platform
16. Upholstery mockups (sofa, chair reupholstery)
17. Full bedding ensemble rendering (coordinated sets)
18. AI style recommendations engine
19. Customer-facing web view (WorkroomForge site)
20. Telegram bot mockup flow
21. Portfolio builder + marketing export
22. SocialForge integration
23. Light/privacy analysis
24. Customer approval workflow (link → approve → triggers quote)

---

## 12. Performance Requirements

- Photo upload: accept up to 20MB, auto-compress/resize to 2048px max
- Segmentation: < 10 seconds
- Basic color fill render: < 2 seconds (client-side composite)
- AI inpainting render: < 30 seconds (acceptable for quality)
- Comparison grid generation: < 45 seconds for 4 options
- All renders cached — regenerate only on config change
- Mobile-friendly: responsive layout, touch-friendly controls

---

## 13. Example Scenarios

**Scenario 1: "Mrs. Henderson wants drapes for her living room"**
→ Upload living room photo → AI segments the 3 windows → Select pinch pleat drapes → Try Navy blue (basic color) → Customer says "I like Kravet 36922.16" → Enter fabric code → System pulls fabric image → Re-render with actual fabric pattern → Before/after comparison → Customer approves → Generate quote with 16 yards Kravet 36922.16 at $89/yd + labor

**Scenario 2: "Show me cornice options for the dining room"**
→ Load dining room photo from CRM → Segment window → Show 3 cornice shapes (straight, scalloped, arched) → Apply Champagne gold from basic palette → Customer picks scalloped → Add matching drapes underneath → Final render shows complete window treatment → Save to portfolio

**Scenario 3: Customer sends photo via Telegram**
→ Customer: [sends living room photo] → MAX: "Beautiful space! I can show you how different window treatments would look. What are you thinking?" → Customer: "Roman shades" → MAX: "What color family?" → [Shows color grid buttons] → Customer picks "Sage" → MAX: [generates mockup, sends image] → "Here's how sage roman shades would look. Want to try another color or schedule a consultation?"

**Scenario 4: "Redesign the Henderson master bedroom"**
→ Upload bedroom photo → AI segments: windows + bed → Select for windows: roman shades in linen white → Select for bed: duvet in sage, euro shams in ivory, bed skirt in sage → Render full room with coordinated ensemble → Customer sees complete vision → Generate combined quote: window treatments + bedding package

**Scenario 5: Portfolio marketing post**
→ Completed installation: customer sends "after" photo → System loads original mockup → Auto-generates: mockup vs reality comparison → Caption: "What we showed them vs what we delivered" → Export to SocialForge → Schedule Instagram post

---

## 14. Competitive Advantage

Most window treatment companies show generic catalog photos. With this system, WorkroomForge shows THEIR room, THEIR windows, with the ACTUAL fabric they're considering. This is the difference between:

- ❌ "Here's a stock photo of pinch pleat drapes in a similar room"
- ✅ "Here's YOUR living room with Kravet 36922.16 pinch pleat drapes on YOUR windows"

No local DC competitor has this capability. This positions WorkroomForge as the premium, technology-forward custom workroom — while also being faster to quote and easier for customers to approve.

---

## 15. Future Enhancements (Post-MVP)

- **AR Preview:** Customer holds phone up to window, sees treatment in real-time via camera
- **3D Fabric Simulation:** Realistic drape physics — heavier fabrics hang differently
- **Multi-Room Packages:** Design entire home's window treatments with coordinated scheme
- **Designer Portal (LuxeForge):** Designers use mockup tool for their clients
- **Measurement from Photo:** Use reference objects (outlet plates, credit cards) to estimate dimensions
- **Automated Reordering:** Track fabric usage, auto-suggest reorders for popular fabrics
- **Voice-Driven:** "Show me something warmer" → AI adjusts fabric color temperature
- **Seasonal Refresh:** "Show me summer sheers" vs "Show me winter blackouts" for the same windows
