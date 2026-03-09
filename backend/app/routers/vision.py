"""Vision analysis endpoints — window measurement, mockup design, outline, upholstery.

Ported from WorkroomForge (port 3001) so all analysis runs through the backend.
Image generation: Stable Diffusion (Stability AI API or HuggingFace free) → xAI fallback.
"""
import os, json, re, httpx, asyncio, logging, base64, uuid, time
from pathlib import Path
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1/vision", tags=["vision"])
log = logging.getLogger("vision")

XAI_API_KEY = os.getenv("XAI_API_KEY", "")
STABILITY_API_KEY = os.getenv("STABILITY_API_KEY", "")
HF_API_TOKEN = os.getenv("HF_API_TOKEN", "")  # optional, improves rate limits

VISION_MODEL = "grok-4-fast-non-reasoning"

# Where generated images are saved for serving
GENERATED_DIR = Path(__file__).resolve().parent.parent.parent.parent / "data" / "generated"
GENERATED_DIR.mkdir(parents=True, exist_ok=True)


class ImageRequest(BaseModel):
    image: str
    preferences: Optional[str] = None


class AnalyzeItemsRequest(BaseModel):
    image: str
    prompt: str


class ImagineRequest(BaseModel):
    prompt: str


# ── Helpers ─────────────────────────────────────────────────

async def call_vision(prompt: str, image: str, max_tokens: int = 4500) -> dict:
    """Send image + prompt to xAI vision model and parse JSON response."""
    if not XAI_API_KEY:
        raise HTTPException(500, "XAI_API_KEY not configured")
    async with httpx.AsyncClient(timeout=120) as client:
        res = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": VISION_MODEL,
                "messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": image}},
                    {"type": "text", "text": prompt},
                ]}],
                "max_tokens": max_tokens,
                "temperature": 0.3,
            },
        )
    if res.status_code != 200:
        raise HTTPException(res.status_code, f"Vision API error: {res.text[:500]}")
    content = res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        raise HTTPException(500, f"Could not parse AI response")
    return json.loads(m.group(0))


def _save_image_bytes(data: bytes, prefix: str = "gen") -> str:
    """Save raw image bytes to disk, return the serve URL path."""
    fname = f"{prefix}-{int(time.time())}-{uuid.uuid4().hex[:6]}.png"
    (GENERATED_DIR / fname).write_bytes(data)
    return f"/api/v1/vision/images/{fname}"


async def _sd_stability(prompt: str) -> Optional[str]:
    """Generate image via Stability AI API (SD3 / SDXL). Returns local URL or None."""
    if not STABILITY_API_KEY:
        return None
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            # Try SD3 first, fall back to core (SDXL)
            for endpoint in [
                "https://api.stability.ai/v2beta/stable-image/generate/sd3",
                "https://api.stability.ai/v2beta/stable-image/generate/core",
            ]:
                res = await client.post(
                    endpoint,
                    headers={
                        "Authorization": f"Bearer {STABILITY_API_KEY}",
                        "Accept": "image/*",
                    },
                    data={
                        "prompt": prompt[:10000],
                        "output_format": "png",
                        "aspect_ratio": "16:9",
                    },
                    timeout=90,
                )
                if res.status_code == 200 and res.headers.get("content-type", "").startswith("image/"):
                    return _save_image_bytes(res.content, "sd")
                log.warning(f"Stability {endpoint} returned {res.status_code}")
    except Exception as e:
        log.warning(f"Stability AI error: {e}")
    return None


async def _sd_together(prompt: str) -> Optional[str]:
    """Generate image via Together AI (free FLUX.1-schnell). Returns local URL or None."""
    key = os.getenv("TOGETHER_API_KEY", "")
    if not key:
        return None
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            res = await client.post(
                "https://api.together.xyz/v1/images/generations",
                headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
                json={
                    "model": "black-forest-labs/FLUX.1-schnell-Free",
                    "prompt": prompt[:2000],
                    "n": 1,
                    "steps": 4,
                    "width": 1344,
                    "height": 768,
                    "response_format": "b64_json",
                },
                timeout=90,
            )
        if res.status_code == 200:
            data = res.json()
            b64 = data.get("data", [{}])[0].get("b64_json")
            if b64:
                return _save_image_bytes(base64.b64decode(b64), "flux")
        log.warning(f"Together AI returned {res.status_code}: {res.text[:200]}")
    except Exception as e:
        log.warning(f"Together AI error: {e}")
    return None


async def _xai_imagine(prompt: str) -> Optional[str]:
    """Generate image via xAI (fallback). Returns URL or None."""
    if not XAI_API_KEY:
        return None
    for model in ["grok-imagine-image", "grok-2-image-1212"]:
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                res = await client.post(
                    "https://api.x.ai/v1/images/generations",
                    headers={"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"},
                    json={"model": model, "prompt": prompt, "n": 1, "response_format": "url"},
                )
            if res.status_code == 200:
                url = res.json().get("data", [{}])[0].get("url")
                if url:
                    return url
        except Exception:
            continue
    return None


async def generate_image(prompt: str) -> Optional[str]:
    """Generate image using best available provider.
    Priority: Stability AI (SD3/SDXL) → Together AI (FLUX.1-schnell free) → xAI (fallback).
    """
    # 1. Stability AI — best quality, paid
    url = await _sd_stability(prompt)
    if url:
        log.info("Image generated via Stability AI (SD)")
        return url

    # 2. Together AI — free FLUX.1-schnell (open-source)
    url = await _sd_together(prompt)
    if url:
        log.info("Image generated via Together AI (FLUX.1-schnell free)")
        return url

    # 3. xAI — fallback
    url = await _xai_imagine(prompt)
    if url:
        log.info("Image generated via xAI (fallback)")
        return url

    log.warning("All image generation providers failed")
    return None


# ── /analyze-items — QIS item detection for quote builder ──

@router.post("/analyze-items")
async def analyze_items(req: AnalyzeItemsRequest):
    """Run AI vision with a custom prompt (used by QIS item analyzer)."""
    return await call_vision(req.prompt, req.image, max_tokens=6000)


# ── /measure — Window photo analysis ───────────────────────

MEASURE_PROMPT = """You are a professional window treatment installer with 30 years of experience estimating window dimensions from photos. Your estimates go directly into customer quotes — accuracy matters.

MEASUREMENT METHOD:
1. First, identify ALL reference objects visible in the photo
2. Use the MOST RELIABLE reference object to establish a scale ratio (pixels per inch)
3. Apply that ratio to measure the window opening width and height
4. Cross-check with a second reference object if available
5. If no reference objects are visible, use architectural proportions (window aspect ratios, typical sizes for the window type)

REFERENCE OBJECTS (standard US residential dimensions):
- Interior door: 80" tall × 32-36" wide (most common: 80" × 32")
- Door handle/knob: 36" from floor
- Light switch plate: center at 48" from floor, plate is 4.5" × 2.75"
- Electrical outlet plate: center at 12-16" from floor, plate is 4.5" × 2.75"
- Baseboard: 3-5.5" tall (most common: 3.5")
- Crown molding: 3-5" tall
- Standard ceiling height: 96" (8ft) — older homes 108" (9ft)
- Window sill: typically 36" from floor (bathroom: 48-60")
- Dining chair seat: 17-18" from floor, back: 30-34" tall
- Sofa/couch: 30-34" tall at back
- Standard dining table: 30" tall, 60-72" long
- Kitchen counter: 36" tall
- Standard brick: 2.25" tall × 7.5" wide (with mortar: 2.75" × 8")

COMMON WINDOW SIZES (use only as sanity check, NOT primary measurement):
- Single-hung: 24-36" wide × 36-72" tall
- Double-hung: 24-36" wide × 36-72" tall
- Casement: 18-36" wide × 24-72" tall
- Picture window: 48-96" wide × 36-72" tall
- Sliding door: 60-72" wide × 80" tall

IMPORTANT: Measure the WINDOW OPENING (glass area), not the frame or trim. Most residential windows are smaller than people assume — a window that looks "big" is often only 30-36" wide.

Return JSON only:
{
  "width_inches": number,
  "height_inches": number,
  "confidence": number (0-100),
  "window_type": string,
  "reference_objects_used": string[],
  "scale_method": string (describe how you calculated the scale),
  "notes": string,
  "treatment_suggestions": string[]
}"""


@router.post("/measure")
async def measure(req: ImageRequest):
    return await call_vision(MEASURE_PROMPT, req.image)


# ── /outline — Dimensional installation plan ───────────────

OUTLINE_PROMPT = """You are a professional window treatment installer creating a dimensional installation plan.

Analyze this photo and provide precise measurements for installation planning.

Use visible reference objects (doors=80" tall, outlets=4.5" plates, ceiling=96" standard).

Return JSON only:
{
  "window_opening": { "width": number, "height": number },
  "wall_dimensions": { "total_width": number, "ceiling_height": number },
  "clearances": { "above_window": number, "below_window": number, "left_wall": number, "right_wall": number },
  "obstructions": [{ "type": string, "location": string, "distance_from_window": number }],
  "existing_treatments": string | null,
  "mounting_recommendations": {
    "rod_width": number, "mounting_height": number, "mount_type": string,
    "inside_mount_feasible": boolean, "notes": string
  },
  "outline_description": string,
  "reference_objects_used": string[],
  "confidence": number,
  "notes": string
}"""


@router.post("/outline")
async def outline(req: ImageRequest):
    return await call_vision(OUTLINE_PROMPT, req.image)


# ── /upholstery — Furniture reupholstery estimate ──────────

UPHOLSTERY_PROMPT = """You are an expert upholstery estimator with 30+ years of experience.

Analyze this furniture photo for a reupholstery/restoration quote.

Identify ALL visible furniture in the photo and provide detailed estimates.

Return JSON only:
{
  "furniture_type": string,
  "style": string,
  "estimated_dimensions": { "width": number, "depth": number, "height": number },
  "cushion_count": { "seat": number, "back": number, "throw_pillows": number },
  "fabric_yards_plain": number,
  "fabric_yards_patterned": number,
  "has_welting": boolean,
  "has_tufting": boolean,
  "has_channeling": boolean,
  "has_skirt": boolean,
  "has_nailhead": boolean,
  "suggested_labor_type": string,
  "estimated_labor_cost_low": number,
  "estimated_labor_cost_high": number,
  "new_foam_recommended": boolean,
  "confidence": number,
  "questions": string[],
  "all_furniture": [{ "type": string, "condition": string, "recommendation": string, "estimated_cost_low": number, "estimated_cost_high": number }],
  "renovation_proposals": [
    { "tier": string, "description": string, "items": string[], "estimated_total_low": number, "estimated_total_high": number }
  ]
}"""


@router.post("/upholstery")
async def upholstery(req: ImageRequest):
    data = await call_vision(UPHOLSTERY_PROMPT, req.image)
    # Generate before/after image
    ftype = data.get("furniture_type", "furniture")
    style = data.get("style", "classic")
    img_prompt = f"Professional before-and-after split image of {ftype} reupholstery. Left: worn {style} {ftype}. Right: same {ftype} beautifully reupholstered in premium fabric, same angle. Studio lighting, interior design magazine quality."
    data["generated_image"] = await generate_image(img_prompt)
    return data


# ── /mockup — AI design mockup with 3-tier proposals ──────

MOCKUP_PROMPT_BASE = """You are a luxury interior designer specializing in custom window treatments and soft furnishings for high-end residential projects. You have 25+ years of experience creating stunning, functional window solutions.

CRITICAL RULES:
- You are designing WINDOW TREATMENTS ONLY. Do NOT suggest moving, replacing, or rearranging furniture, flooring, or wall decor.
- Keep existing room elements (furniture, art, rugs, paint) exactly as they are — your job is ONLY the windows.
- Each tier MUST be clearly different from the others in treatment type, fabric, hardware, and visual impact.
- Ensure design logic: rods/tracks go BEHIND or ABOVE valances/cornices, never in front. Hardware must be compatible with the treatment style.

Analyze this photo and create a detailed mockup/design proposal for window treatments ONLY.

STEP 1 — ASSESS THE SPACE:
- Room type and function
- Architectural style
- Light exposure and direction
- Existing decor elements — NOTE these but do NOT change them
- Privacy needs

STEP 2 — WINDOW ANALYSIS:
- Window type (single/double hung, casement, picture, bay, arched, sliding door, French door)
- Approximate dimensions from reference objects
- Current treatment (if any)
- How the window is used (needs to open? sliding door access?)

STEP 3 — DESIGN PROPOSALS (3 distinctly different options from budget to luxury):"""

TREATMENT_OPTIONS = """
OPTION 1 — ELEGANT ESSENTIAL (budget-conscious, clean, simple):
- Simple treatment: single-layer panels OR a clean shade/blind
- Standard fabric: cotton, polyester blend, or basic linen in solid colors
- Standard lining (privacy or light-filtering)
- Simple hardware: basic rod with finials OR inside-mount brackets
- NO extras — clean, functional, elegant
- Price range: $200-$600 per window

OPTION 2 — DESIGNER'S CHOICE (mid-range, layered, textured):
- MUST be different treatment type than Option 1
- Mid-range fabric: textured linen, jacquard, subtle pattern, or woven blend
- Blackout or thermal lining + interlining
- Decorative hardware: ornamental rod, rings, or ripplefold track
- ONE extra: sheers behind panels, OR decorative trim, OR contrast banding
- Price range: $600-$1,500 per window

OPTION 3 — ULTIMATE LUXURY (premium, statement, multi-layered):
- MUST be most elaborate — completely different from Options 1 and 2
- FULL LAYERING: sheers + drapery panels + top treatment (cornice, valance, or swag)
- Premium fabric: silk dupioni, Italian velvet, designer embroidered
- Motorization (Lutron or Somfy) for functional layers
- Custom hardware: hand-forged iron, crystal finials, gilded brackets
- Multiple extras: trim, contrast lining reveal, tiebacks, fringe
- Price range: $1,500-$4,000+ per window

DESIGN VALIDATION — Check each proposal:
- Rods/tracks mount ABOVE or BEHIND any valance/cornice
- Hardware style matches treatment
- Fabric weight is appropriate for hardware
- Colors complement existing room palette

Return JSON only:
{
  "room_assessment": {
    "room_type": string, "style": string, "light_level": string,
    "color_palette": string[], "privacy_need": "low" | "medium" | "high"
  },
  "window_info": {
    "type": string, "estimated_width": number, "estimated_height": number,
    "current_treatment": string | null
  },
  "proposals": [{
    "tier": string, "treatment_type": string, "style": string,
    "fabric": string, "lining": string, "hardware": string,
    "extras": string[], "price_range_low": number, "price_range_high": number,
    "visual_description": string, "design_rationale": string
  }],
  "general_recommendations": string[],
  "confidence": number,
  "notes": string
}"""


@router.post("/mockup")
async def mockup(req: ImageRequest):
    pref_text = ""
    if req.preferences:
        pref_text = f"\n\nCLIENT PREFERENCES: {req.preferences}\nIncorporate these preferences into your proposals."

    full_prompt = MOCKUP_PROMPT_BASE + pref_text + TREATMENT_OPTIONS
    analysis = await call_vision(full_prompt, req.image)

    # Generate mockup images for each proposal in parallel
    proposals = analysis.get("proposals", [])
    room_type = analysis.get("room_assessment", {}).get("room_type", "room")
    window_type = analysis.get("window_info", {}).get("type", "window")
    palette = ", ".join(analysis.get("room_assessment", {}).get("color_palette", [])) or "neutral tones"
    light = analysis.get("room_assessment", {}).get("light_level", "natural")

    tier_styles = {
        "Elegant Essential": "Simple, clean, minimal. Single-layer. Standard fabric, solid color. Basic rod. Budget-friendly elegance.",
        "Designer's Choice": "Layered, textured, curated. Multiple elements. Decorative hardware with detailed finials. Mid-range materials.",
        "Ultimate Luxury": "Opulent, grand, multi-layered. Floor-to-ceiling with sheers. Fabric sheen (silk, velvet). Ornate hardware. Top treatment. Luxury magazine quality.",
    }

    async def gen_proposal_image(p: dict, idx: int) -> Optional[dict]:
        tier_style = tier_styles.get(p.get("tier", ""), tier_styles["Elegant Essential"])
        is_valance = "valance" in (p.get("treatment_type", "") or "").lower() or "cornice" in (p.get("treatment_type", "") or "").lower()
        hw_note = (f"The {p.get('hardware', 'mounting board')} is HIDDEN BEHIND the valance/cornice."
                   if is_valance else
                   f"Hardware: {p.get('hardware', 'decorative rod')} mounted 4-6 inches ABOVE the window frame.")
        prompt = " ".join(filter(None, [
            f"PROFESSIONAL interior design photograph of a {room_type} with a {window_type} window.",
            f"WINDOW TREATMENT ONLY (do NOT change furniture or decor):",
            f"Installed: {p.get('treatment_type', 'drapery')} in {p.get('fabric', 'elegant fabric')} fabric, {p.get('style', 'classic')} style.",
            tier_style, hw_note,
            f"Room: {palette} color scheme. {light} light. All existing furniture UNCHANGED.",
            "Photorealistic, straight-on view, 4K sharp focus, Architectural Digest quality.",
            "MOST LUXURIOUS option — visually stunning." if idx == 2 else "",
        ]))
        url = await generate_image(prompt)
        return {"tier": p.get("tier", "Option"), "url": url} if url else None

    tasks = [gen_proposal_image(p, i) for i, p in enumerate(proposals[:3])]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    analysis["generated_images"] = [r for r in results if isinstance(r, dict)]

    return analysis


# ── /imagine — Standalone image generation ─────────────────

@router.post("/imagine")
async def imagine(req: ImagineRequest):
    url = await generate_image(req.prompt)
    if not url:
        raise HTTPException(500, "Image generation failed")
    return {"url": url}


# ── /images/{filename} — Serve generated images ───────────

from fastapi.responses import FileResponse, Response
from datetime import datetime

@router.get("/images/{filename}")
async def serve_image(filename: str):
    path = GENERATED_DIR / filename
    if not path.exists() or not path.is_file():
        raise HTTPException(404, "Image not found")
    return FileResponse(path, media_type="image/png")


# ── /measurements-pdf — Generate PDF with 3D screenshot + measurements ──

class MeasurementsPdfRequest(BaseModel):
    fileName: str = "3D Scan"
    screenshot: str = ""  # base64 data URL
    unit: str = "ft"
    measurements: list = []

@router.post("/measurements-pdf")
async def measurements_pdf(req: MeasurementsPdfRequest):
    """Generate PDF with 3D screenshot and measurement table via WeasyPrint."""
    from weasyprint import HTML as WeasyHTML

    # Extract base64 image
    screenshot_data = req.screenshot
    if screenshot_data.startswith("data:"):
        screenshot_data = screenshot_data.split(",", 1)[1]

    # Build measurement rows
    rows = ""
    for i, m in enumerate(req.measurements):
        rows += f"""<tr>
            <td style="padding:8px;border:1px solid #ddd;text-align:center;font-weight:bold;color:#8B5CF6">#{m.get('id', i+1)}</td>
            <td style="padding:8px;border:1px solid #ddd;text-align:right;font-family:monospace">{m.get('distance_ft', 0):.2f} ft</td>
            <td style="padding:8px;border:1px solid #ddd;text-align:right;font-family:monospace">{m.get('distance_m', 0):.4f} m</td>
            <td style="padding:8px;border:1px solid #ddd;text-align:right;font-family:monospace">{m.get('distance_in', 0):.1f} in</td>
        </tr>"""

    created_date = datetime.now().strftime("%B %d, %Y")
    file_label = req.fileName or "3D Scan"

    html = f"""<!DOCTYPE html>
<html><head><style>
    @page {{ size: letter; margin: 0.75in; }}
    body {{ font-family: 'Segoe UI', system-ui, sans-serif; color: #1a1a2e; margin: 0; padding: 0; }}
    .header {{ border-bottom: 3px solid #D4AF37; padding-bottom: 12px; margin-bottom: 20px; }}
    .header h1 {{ margin: 0; color: #D4AF37; font-size: 22px; }}
    .header p {{ margin: 4px 0 0; color: #888; font-size: 12px; }}
    .screenshot {{ width: 100%; border-radius: 8px; margin: 16px 0; border: 1px solid #eee; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 16px; }}
    th {{ background: #f5f0e1; color: #8B5CF6; padding: 10px 8px; border: 1px solid #ddd; text-align: left; font-size: 12px; }}
    .footer {{ margin-top: 28px; border-top: 1px solid #eee; padding-top: 12px; text-align: center; }}
    .footer p {{ margin: 0; color: #aaa; font-size: 10px; }}
</style></head><body>
<div class="header">
    <h1>3D Measurement Report</h1>
    <p>{file_label} &middot; {created_date}</p>
</div>
{"<img class='screenshot' src='data:image/png;base64," + screenshot_data + "' alt='3D View' />" if screenshot_data else ""}
{f'''<table>
    <thead><tr>
        <th>#</th><th>Feet</th><th>Meters</th><th>Inches</th>
    </tr></thead>
    <tbody>{rows}</tbody>
</table>''' if req.measurements else "<p style='color:#888;font-size:11px;margin-top:12px'>No measurements taken.</p>"}
<div class="footer">
    <p>Empire &middot; 3D Measurement Report</p>
    <p>Generated {created_date}</p>
</div>
</body></html>"""

    pdf_bytes = WeasyHTML(string=html).write_pdf()

    # Save a copy
    pdf_dir = Path.home() / "empire-repo" / "backend" / "data" / "measurements"
    pdf_dir.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r'[^\w.-]', '_', req.fileName or 'scan')
    pdf_path = pdf_dir / f"{safe_name}_{int(time.time())}.pdf"
    pdf_path.write_bytes(pdf_bytes)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_measurements.pdf"'},
    )
