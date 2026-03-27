"""Drawing Studio API — generate architectural bench drawings (SVG + PDF)."""
from fastapi import APIRouter, Response, HTTPException
from pydantic import BaseModel
from typing import Optional
import os
import re
import json
import logging
import tempfile
import httpx

router = APIRouter()
log = logging.getLogger("drawings")

XAI_API_KEY = os.getenv("XAI_API_KEY", "")


class BenchRequest(BaseModel):
    bench_type: str = "straight"  # straight, l_shape, u_shape
    name: str = "Bench"
    lf: float = 10  # linear feet
    rate: float = 0  # $/LF — owner sets pricing
    seat_depth: float = 20
    seat_height: float = 18
    back_height: float = 18
    panel_style: str = "flat"  # flat, vertical_channels, horizontal_channels, tufted
    quote_num: str = ""
    # L-shape specific
    leg1_length: float = 0
    leg2_length: float = 0
    # U-shape specific
    back_length: float = 0
    left_depth: float = 0
    right_depth: float = 0


@router.post("/drawings/bench")
async def generate_bench_svg(req: BenchRequest):
    """Generate an SVG bench drawing from dimensions."""
    from app.services.vision.bench_renderer import (
        render_straight, render_l_shape, render_u_shape,
    )

    svg = _render(req)
    return {"svg": svg, "bench_type": req.bench_type, "name": req.name}


@router.post("/drawings/bench/pdf")
async def generate_bench_pdf(req: BenchRequest):
    """Generate a PDF bench drawing from dimensions."""
    from app.services.vision.bench_renderer import drawings_to_pdf

    svg = _render(req)
    output_path = os.path.join(
        tempfile.gettempdir(), f"bench_{req.bench_type}_{req.name.replace(' ', '_')}.pdf"
    )
    drawings_to_pdf([{"name": req.name, "svg": svg, "lf": req.lf}], output_path)

    with open(output_path, "rb") as f:
        pdf_bytes = f.read()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="bench_drawing_{req.bench_type}.pdf"'
        },
    )


def _render(req: BenchRequest) -> str:
    from app.services.vision.bench_renderer import (
        render_straight, render_l_shape, render_u_shape,
    )

    if req.bench_type == "l_shape":
        return render_l_shape(
            name=req.name,
            lf=req.lf,
            rate=req.rate,
            quote_num=req.quote_num,
        )
    elif req.bench_type == "u_shape":
        return render_u_shape(
            name=req.name,
            lf=req.lf,
            rate=req.rate,
            quote_num=req.quote_num,
        )
    else:
        return render_straight(
            name=req.name,
            lf=req.lf,
            rate=req.rate,
            quote_num=req.quote_num,
        )


SKETCH_EXTRACT_PROMPT = """You are analyzing a hand-drawn sketch or measurement drawing for a custom bench/banquette project.

Extract ALL dimensions and details you can see. Look for:
- Total length (in feet or inches)
- Seat depth, seat height, back height
- Shape: straight, L-shape, U-shape
- Number of sections or areas
- Any labels, names, notes written on the sketch
- Panel style if noted (flat, channels, tufted)

Return ONLY valid JSON (no markdown):
{
    "name": "descriptive name from sketch or 'Bench'",
    "bench_type": "straight" | "l_shape" | "u_shape",
    "total_length_ft": number (convert inches to feet if needed),
    "seat_depth_in": number or 20,
    "seat_height_in": number or 18,
    "back_height_in": number or 18,
    "panel_style": "flat" | "vertical_channels" | "horizontal_channels" | "tufted",
    "leg1_length_ft": number (L-shape leg 1, 0 if straight),
    "leg2_length_ft": number (L-shape leg 2, 0 if straight),
    "back_length_ft": number (U-shape back, 0 if not U),
    "left_depth_ft": number (U-shape left wing, 0 if not U),
    "right_depth_ft": number (U-shape right wing, 0 if not U),
    "quote_num": "any quote/estimate number visible",
    "notes": "any other text or notes visible on the sketch"
}"""


class SketchAnalyzeRequest(BaseModel):
    image: str  # base64 image data


@router.post("/drawings/analyze-sketch")
async def analyze_sketch(req: SketchAnalyzeRequest):
    """Analyze a hand-drawn sketch photo and extract bench dimensions via AI vision."""
    if not XAI_API_KEY:
        raise HTTPException(500, "XAI_API_KEY not configured")

    async with httpx.AsyncClient(timeout=60.0) as client:
        res = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers={"Authorization": f"Bearer {XAI_API_KEY}", "Content-Type": "application/json"},
            json={
                "model": "grok-4-fast-non-reasoning",
                "messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": req.image}},
                    {"type": "text", "text": SKETCH_EXTRACT_PROMPT},
                ]}],
                "max_tokens": 2000,
                "temperature": 0.2,
            },
        )
    if res.status_code != 200:
        log.error(f"Vision API error: {res.text[:300]}")
        raise HTTPException(res.status_code, "Vision API error")

    content = res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        raise HTTPException(500, "Could not parse AI response")

    return json.loads(m.group(0))
