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


SKETCH_EXTRACT_PROMPT = """You are a professional workroom estimator analyzing a hand-drawn sketch, measurement drawing, or photo of an item that needs custom fabrication.

FIRST: Identify what type of item this is:
- bench, banquette, booth (seating)
- window, drapery, curtain, shade, blind, valance, cornice (window treatment)
- pillow, bolster, cushion
- chair, sofa, ottoman, headboard (upholstery)
- table, desk, console
- other

THEN: Extract ALL dimensions and details visible. Read every number, label, and annotation.

Return ONLY valid JSON (no markdown):
{
    "item_type": "bench" | "window" | "pillow" | "upholstery" | "table" | "generic",
    "name": "descriptive name from the sketch",
    "dimensions": {
        "label1": "value with units (e.g. 72\\")",
        "label2": "value with units"
    },
    "notes": "any text, labels, or notes visible on the sketch",
    "quote_num": "any quote/estimate number visible or empty string",
    "bench_details": {
        "bench_type": "straight" | "l_shape" | "u_shape",
        "total_length_ft": 0,
        "seat_depth_in": 20,
        "seat_height_in": 18,
        "back_height_in": 18,
        "panel_style": "flat",
        "leg1_length_ft": 0,
        "leg2_length_ft": 0,
        "back_length_ft": 0,
        "left_depth_ft": 0,
        "right_depth_ft": 0
    }
}

IMPORTANT: The "dimensions" dict should contain ALL measurements found, using the labels written on the sketch. The bench_details section is ONLY populated if item_type is "bench"."""


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


class GeneralDrawingRequest(BaseModel):
    name: str = "Drawing"
    item_type: str = "generic"  # bench, window, pillow, upholstery, table, generic
    dimensions: dict = {}
    notes: str = ""
    # Bench-specific (only used when item_type == "bench")
    bench_type: str = "straight"
    lf: float = 0
    rate: float = 0
    quote_num: str = ""


def _estimate_lf(dimensions: dict, lf: float) -> float:
    """Estimate linear feet from dimension values when lf is 0."""
    if lf > 0:
        return lf
    # Look for the longest inch dimension and convert to feet
    max_inches = 0
    for label, value in dimensions.items():
        val_str = str(value).strip().rstrip('"\'').strip()
        try:
            inches = float(re.sub(r'[^0-9.]', '', val_str))
            # Skip values that look like heights (seat height, back height)
            label_lower = label.lower()
            if any(kw in label_lower for kw in ['height', 'ht', 'depth', 'deep']):
                continue
            if inches > max_inches:
                max_inches = inches
        except (ValueError, TypeError):
            continue
    if max_inches > 0:
        return max_inches / 12
    return 6  # Default fallback


def _render_general(req: GeneralDrawingRequest) -> str:
    """Route to the correct renderer based on item type."""
    from app.services.vision.drawing_service import render_measurement_diagram

    if req.item_type == "bench":
        from app.services.vision.bench_renderer import (
            render_straight, render_l_shape, render_u_shape,
        )
        lf = _estimate_lf(req.dimensions, req.lf)
        if "u" in req.bench_type:
            return render_u_shape(req.name, lf, req.rate, quote_num=req.quote_num)
        elif "l" in req.bench_type:
            return render_l_shape(req.name, lf, req.rate, quote_num=req.quote_num)
        else:
            return render_straight(req.name, lf, req.rate, quote_num=req.quote_num)
    else:
        return render_measurement_diagram(
            name=req.name,
            item_type=req.item_type,
            dimensions=req.dimensions,
            notes=req.notes,
        )


@router.post("/drawings/general")
async def generate_general_drawing(req: GeneralDrawingRequest):
    """Generate an SVG drawing for any item type."""
    svg = _render_general(req)
    return {"svg": svg, "item_type": req.item_type, "name": req.name}


@router.post("/drawings/general/pdf")
async def generate_general_pdf(req: GeneralDrawingRequest):
    """Generate a PDF drawing for any item type."""
    from app.services.vision.bench_renderer import drawings_to_pdf

    svg = _render_general(req)

    output_path = os.path.join(
        tempfile.gettempdir(), f"drawing_{req.item_type}_{req.name.replace(' ', '_')}.pdf"
    )
    drawings_to_pdf([{"name": req.name, "svg": svg, "lf": req.lf}], output_path)

    with open(output_path, "rb") as f:
        pdf_bytes = f.read()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="drawing_{req.item_type}.pdf"'
        },
    )
