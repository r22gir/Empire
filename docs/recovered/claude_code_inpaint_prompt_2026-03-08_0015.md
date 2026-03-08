## MEGA TASK: Inpainting Service + PDF Redesign + Style/Scope Wiring

Read this ENTIRE prompt before coding. This is a multi-file implementation.

---

### PART 1: New file — backend/app/services/max/inpaint_prompts.py

Separate prompt library. Every treatment type × 3 tiers × style variants.

```
WINDOW_PROMPTS structure:
{
    "roman-shade": {
        "A": "Simple flat roman shade, {color} solid cotton fabric, basic white cassette headrail, inside mount, clean minimal look, natural lighting, photorealistic, {style_modifier}",
        "B": "Textured linen roman shade, {color} woven fabric with subtle pattern, decorative cassette headrail, clean horizontal folds, photorealistic, {style_modifier}",
        "C": "Luxury damask roman shade, {color} heavy silk fabric, ornate gilded cassette headrail, blackout lined, rich texture, photorealistic, {style_modifier}",
    },
    "ripplefold": { ... A/B/C for each },
    "pinch-pleat": { ... },
    "grommet": { ... },
    "rod-pocket": { ... },
    "roller-shade": { ... },
}

UPHOLSTERY_PROMPTS structure:
{
    "A": "Reupholstered {furniture_type} in {color} solid cotton fabric, clean lines, {details}, photorealistic, {style_modifier}",
    "B": "Reupholstered {furniture_type} in {color} textured linen, {details}, professional quality, photorealistic, {style_modifier}",
    "C": "Reupholstered {furniture_type} in {color} premium velvet, {details}, luxury showroom quality, photorealistic, {style_modifier}",
}

STYLE_MODIFIERS = {
    "farmhouse": "rustic farmhouse aesthetic, warm wood tones, natural textiles, shiplap and reclaimed wood accents, cozy country feel",
    "mid-century-modern": "mid-century modern style, clean geometric lines, tapered legs, organic curves, walnut and teak tones, minimal ornamentation",
    "traditional": "traditional classic style, ornate details, rich wood furniture, symmetrical layout, crown molding, elegant and formal",
    "contemporary": "contemporary modern style, neutral palette, sleek surfaces, minimal decoration, open and airy feel",
    "coastal": "coastal beach style, light blues and whites, natural fiber textures, weathered wood, relaxed airy feel",
    "industrial": "industrial loft style, exposed brick, metal accents, raw materials, Edison bulbs, urban warehouse feel",
    "bohemian": "bohemian eclectic style, layered textiles, rich colors, mixed patterns, plants, globally inspired decor",
    "transitional": "transitional style, blend of traditional and contemporary, neutral tones, clean lines with subtle ornamentation",
    "": "professional interior, clean and well-lit, Architectural Digest quality",  # default when no style selected
}

NEGATIVE_PROMPTS = {
    "roman-shade": "NO curtain rod, NO rings, NO drapery hardware, NO grommets, NO pinch pleats, NO blinds",
    "ripplefold": "NO roman shade, NO roller shade, NO blinds, NO valance, NO rings",
    "pinch-pleat": "NO ripplefold, NO roman shade, NO grommets, NO casual drape",
    "grommet": "NO pinch pleat, NO roman shade, NO roller shade",
    "rod-pocket": "NO rings, NO grommets, NO roman shade, NO track",
    "roller-shade": "NO curtain rod, NO fabric drape, NO rings, NO roman shade",
}

# Clean mockup prompts (inspirational, NOT using customer photo)
CLEAN_MOCKUP_PROMPTS = {
    "roman-shade": {
        "A": "Professional interior design photo of a beautiful room with {color} roman shade on window, {style_modifier}, magazine quality, bright natural light",
        "B": "High-end interior design photo, elegant {color} textured roman shade, {style_modifier}, Architectural Digest quality",
        "C": "Luxury showroom photo, premium {color} silk roman shade with ornate details, {style_modifier}, editorial photography",
    },
    # ... same structure for all treatment types
}
```

Fill out ALL treatment types completely. Don't leave any as "...". Every combination must work.

---

### PART 2: New file — backend/app/services/max/inpaint_service.py

Core inpainting service with all optimizations:

```python
class InpaintService:
    """Smart mockup generation: inpainted customer photos + clean mockups."""
    
    async def generate_all_mockups(self, photo_b64, rooms, style, scope, xai_key, stability_key=None):
        """Main entry point. Returns mockup data for all tiers."""
        
        # 1. Preprocess: resize to max 1024x1024, convert to PNG bytes
        photo_bytes = self._preprocess_image(photo_b64)
        
        # 2. ONE Grok Vision call — get bounding boxes for ALL windows AND furniture
        regions = await self._detect_regions(photo_bytes, xai_key)
        # Cache this — don't call again
        
        # 3. Generate masks with PIL
        window_mask = self._render_mask(photo_bytes, regions, target_type="window", padding=0.12)
        furniture_mask = self._render_mask(photo_bytes, regions, target_type="furniture", padding=0.12)
        
        # 4. Build all tasks (up to 12: 3 tiers × 2 types × 2 styles = inpainted + clean)
        tasks = []
        for tier in ["A", "B", "C"]:
            if window_mask:
                # Inpainted customer photo (window)
                tasks.append(self._inpaint_with_router(photo_bytes, window_mask, 
                    treatment_type, color, tier, style, "window"))
                # Clean aspirational mockup (window)
                tasks.append(self._generate_clean_mockup(
                    treatment_type, color, tier, style, "window", xai_key))
            if furniture_mask:
                # Inpainted customer photo (furniture)
                tasks.append(self._inpaint_with_router(photo_bytes, furniture_mask,
                    furniture_type, color, tier, style, "furniture"))
                # Clean aspirational mockup (furniture)
                tasks.append(self._generate_clean_mockup(
                    furniture_type, color, tier, style, "furniture", xai_key))
        
        # 5. Run ALL in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 6. Quality check each result
        verified = await self._quality_check_all(results, xai_key)
        
        # 7. Save to disk + generate thumbnails
        saved = self._save_all(verified, quote_id)
        
        return saved
    
    async def _inpaint_with_router(self, photo, mask, prompt_args):
        """Try Pixazo → Stability → Grok fallback."""
        
        # Try 1: Pixazo (FREE)
        result = await self._try_pixazo(photo, mask, prompt)
        if result: return {"image": result, "provider": "pixazo", "cost": 0.00}
        
        # Try 2: Stability AI (FREE under $1M)
        result = await self._try_stability(photo, mask, prompt)
        if result: return {"image": result, "provider": "stability", "cost": 0.00}
        
        # Try 3: Grok image gen (last resort, no inpainting)
        result = await self._try_grok(prompt)
        if result: return {"image": result, "provider": "grok", "cost": 0.00}
        
        return None
    
    def _preprocess_image(self, b64_data):
        """Resize to max 1024x1024, return PNG bytes."""
        
    def _render_mask(self, photo_bytes, regions, target_type, padding=0.12):
        """PIL: white rectangles on black canvas for target regions. Add padding %."""
        
    async def _detect_regions(self, photo_bytes, xai_key):
        """ONE Grok Vision call: return bounding boxes for all windows + furniture."""
        # Prompt asks for JSON with regions array
        # Each region: label, type (window/furniture), x_pct, y_pct, w_pct, h_pct
        
    async def _try_pixazo(self, photo, mask, prompt):
        """Pixazo free inpainting API."""
        
    async def _try_stability(self, photo, mask, prompt):
        """Stability AI inpainting API."""
        # POST https://api.stability.ai/v2beta/stable-image/edit/inpaint
        # Multipart: image, mask, prompt, output_format=png
        
    async def _try_grok(self, prompt):
        """Grok grok-imagine-image — generates new room (no inpainting)."""
        
    async def _generate_clean_mockup(self, item_type, color, tier, style, category, xai_key):
        """Generate aspirational mockup (NOT using customer photo). Uses Grok image gen."""
        # This is the inspirational/magazine-style image
        # Uses CLEAN_MOCKUP_PROMPTS from inpaint_prompts.py
        
    async def _quality_check_all(self, results, xai_key):
        """Quick Grok Vision check: does the image show the correct treatment?"""
        # If NO → retry with 20% more padding
        # Max 1 retry per image
        
    def _save_all(self, results, quote_id):
        """Save full-res + 400px thumbnail to backend/data/generated/"""
        # Full: {quote_id}_{tier}_{type}.png
        # Thumb: {quote_id}_{tier}_{type}_thumb.png
        # Return dict with URLs, provider, cost per image
```

Implement ALL methods fully. Don't leave stubs.

---

### PART 3: Modify — backend/app/services/max/tool_executor.py

In create_quick_quote (around lines 669-762):

1. Import InpaintService from inpaint_service
2. Replace the entire grok-imagine-image block
3. Call inpaint_service.generate_all_mockups() with:
   - photo_refs[0]["data_uri"] (customer photo)
   - rooms data (windows + upholstery)
   - style (from params, default "")
   - scope (from params, default "full")
   - API keys
4. Attach results to design_proposals:
   - dp["inpainted_image_url"] = inpainted customer photo URL
   - dp["clean_mockup_url"] = aspirational mockup URL
   - dp["mockup_provider"] = "pixazo" / "stability" / "grok"
   - dp["mockup_cost"] = 0.00
5. Store total mockup cost in quote metadata (for dashboard display)

### SCOPE selector changes line items:
- scope="full": include fabric + lining + fabrication + hardware + installation + old treatment removal + surface prep
- scope="fabric-only": include fabric + lining + fabrication labor only (no hardware, no installation, no removal)
- scope="hardware-upgrade": include hardware + motorization + installation only (keep existing fabric)

Add scope parameter to create_quick_quote params. Default "full".

### STYLE selector changes:
- Passed to inpaint_prompts.py via {style_modifier}
- Changes mockup look (farmhouse vs modern vs coastal etc.)
- Changes AI commentary tone and recommendations

Add style parameter to create_quick_quote params. Default "".

---

### PART 4: Modify — backend/app/routers/quotes.py — PDF CARD LAYOUT

Redesign the proposal section of the PDF. Each tier is ONE tight card:

```
┌──────────────────────────────────────────────────────────────────┐
│  OPTION A · Essential                                    $386   │
│──────────────────────────────────────────────────────────────────│
│  ┌─────────────────────┐  ┌─────────────────────┐              │
│  │ [Inpainted Photo]   │  │ [Clean Mockup]      │              │
│  │ "Your Room"         │  │ "Inspiration"       │              │
│  │ 280x200px           │  │ 280x200px           │              │
│  └─────────────────────┘  └─────────────────────┘              │
│──────────────────────────────────────────────────────────────────│
│  Grade A cotton fabric in white. Simple clean roman shade with  │
│  standard lining for light filtering. Inside mount to showcase  │
│  the wood trim. Perfect for everyday use.                       │
│──────────────────────────────────────────────────────────────────│
│  Fabric — Essential Grade in white (2.1 yds)          $52.50   │
│  Lining — Standard (2.1 yds)                          $16.80   │
│  Fabrication — Roman Shade (1 width × 3.0hr)         $150.00   │
│  Hardware — Cassette (4.0 ft)                         $60.00   │
│  Professional Installation                            $85.00   │
│──────────────────────────────────────────────────────────────────│
│  Subtotal $364.30  ·  Tax (6%) $21.86  ·  Total      $386.16  │
└──────────────────────────────────────────────────────────────────┘
```

CSS/HTML rules for proposal cards:
- page-break-inside: avoid — NEVER split a card across pages
- Max card height: fits on one page with margins
- Two images side by side (inpainted + clean mockup), 280px wide each
- Left image labeled "Your Room" (inpainted), right labeled "Inspiration" (clean)
- AI commentary: max 3 sentences, directly under images
- Line items: compact table, no extra spacing
- Totals: one line at bottom (Subtotal · Tax · Total)
- Card border: 1px solid #ddd, border-radius 8px, subtle shadow
- Tier color accent: green (A/Essential), gold (B/Designer), purple (C/Premium)

### REMOVE from current PDF:
- Duplicate "Site Photo" + "Current — Before" — show original photo ONCE at top, before all cards
- Separate "Design Proposals" mockup gallery page — mockups are now inside each card
- Excessive whitespace between sections
- SVG drawing duplicated alongside the photo (show SVG drawing ONCE in the overview, not repeated per proposal)

### PDF structure should be:
```
Page 1: Header + Customer Info + Original Photo + Window/Furniture Summary Table + SVG Drawing
Page 2: Option A Card (complete — images, commentary, line items, total)
Page 3: Option B Card (complete)
Page 4: Option C Card (complete)
Page 5: Terms + Signature + Footer
```

Compact. No wasted pages. Each card is self-contained.

---

### PART 5: Modify — WorkroomForge style/scope selectors

Find where the style selector (farmhouse, mid-century, etc.) and scope selector (full reno, fabric only) exist in the WorkroomForge UI.

Wire them so they:
1. Send the selected style and scope in the API call to create_quick_quote
2. The values flow through to inpaint_prompts.py (style changes mockup look)
3. The values flow through to tool_executor.py (scope changes line items)
4. The values flow through to quotes.py (AI commentary reflects style + scope)

Check: grep -rn "style\|farmhouse\|mid.century\|scope\|full.reno\|fabric.only" ~/empire-repo/workroomforge/src/ --include="*.tsx" --include="*.ts" | grep -v node_modules

Wire whatever exists. If the UI components exist but don't send data, fix the API call. If the options don't exist in the UI yet, note what needs to be added (don't build UI, just note it).

---

### PART 6: Dashboard cost indicator

In the Founder Dashboard, when viewing a quote that used inpainting:
- Show a small badge/tag: "Mockups: Pixazo (FREE)" or "Mockups: Stability ($0.18)"
- This is ONLY visible in the dashboard, NEVER in the client PDF
- Read from quote.mockup_metadata.provider and quote.mockup_metadata.total_cost
- Display in the quote detail view or chat response

---

### TESTING:

After all implementation:

1. Restart backend:
   fuser -k 8000/tcp 2>/dev/null; sleep 2
   cd ~/empire-repo/backend && source venv/bin/activate
   python -m uvicorn app.main:app --host 0.0.0.0 --port 8000

2. Verify new modules load:
   python -c "from app.services.max.inpaint_service import InpaintService; print('OK')"
   python -c "from app.services.max.inpaint_prompts import WINDOW_PROMPTS, STYLE_MODIFIERS; print('OK')"

3. Test inpainting (if a test image exists):
   curl -X POST http://localhost:8000/api/v1/max/chat \
     -H "Content-Type: application/json" \
     -d '{"message": "create a quick quote for a 48x60 roman shade, white, farmhouse style"}'

4. Check outputs:
   ls ~/empire-repo/backend/data/generated/
   ls ~/empire-repo/backend/data/quotes/pdf/

5. Verify Pixazo endpoint works:
   Test the Pixazo API separately before integrating

### IMPORTANT:
- Pixazo API: research the exact endpoint URL and parameters before coding. Check https://www.pixazo.ai/models/text-to-image/stable-diffusion-inpainting-api
- Stability API: POST https://api.stability.ai/v2beta/stable-image/edit/inpaint (multipart form)
- Client PDF: CLEAN — no provider info, no cost info, just beautiful mockups
- Dashboard: shows provider + cost for RG's eyes only
- One Grok Vision call for ALL masks (cached)
- All mockups generated in parallel (asyncio.gather)
- 12% mask padding default, 20% on retry
- Resize photos to 1024x1024 max
- Save thumbnails at 400px for Telegram
- page-break-inside: avoid on ALL cards
