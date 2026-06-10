"""Drawing Studio API — generate architectural bench drawings (SVG + PDF)."""

from fastapi import APIRouter, Response, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import os
import re
import json
import logging
import tempfile
import httpx
import uuid

from app.services.business_routing import route_to_for_item_type
from app.services.drawing import provider_status
from app.services.drawing import yardage

router = APIRouter()
log = logging.getLogger("drawings")

XAI_API_KEY = os.getenv("XAI_API_KEY", "")


# ── Default-style inference for parametric template families ─────────
# These are the "best first style" for each item_type that has a
# parametric template available. Used by /drawings/generate when the
# caller does not pass an explicit style_key but the item_type maps to
# one of the 10 supported parametric families.
DEFAULT_STYLE_FOR_ITEM_TYPE = {
    "window": "pinch_pleat",
    "drapery": "pinch_pleat",
    "curtain": "pinch_pleat",
    "shade": "flat_roman",
    "roman": "flat_roman",
    "roman_shade": "flat_roman",
    "blind": "flat_roman",
    "valance": "straight_cornice",
    "cornice": "straight_cornice",
    "sofa": "tuxedo",
    "chair": "club",
    "ottoman": "rectangular",
    "headboard": "straight",
    "cushion": "box",
    "pillow": "square",
    "bedding": "duvet",
    "slipcover": "tight_fit",
    "wall_panel": "fabric",
    "banquette": "straight",
    "shelving": "open",
    "shelf": "open",
    "murphy_bed": "vertical",
    "desk": "writing",
    "storage_bench": "hinged_top",
    "table": "dining",
    "millwork": "crown_molding",
    "commercial": "restaurant_booth",
}


def _default_style_for(item_type: str) -> Optional[str]:
    if not item_type:
        return None
    return DEFAULT_STYLE_FOR_ITEM_TYPE.get(item_type.lower().strip())


@router.get("/drawings/files/{filename}")
async def serve_drawing_file(filename: str):
    """Serve generated drawing files (SVG, PDF)."""
    base_dir = os.path.expanduser("~/empire-repo/uploads/arch_drawings")
    file_path = os.path.join(base_dir, filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Drawing file not found")
    # Determine media type
    if filename.endswith(".svg"):
        media_type = "image/svg+xml"
    elif filename.endswith(".pdf"):
        media_type = "application/pdf"
    elif filename.endswith(".png"):
        media_type = "image/png"
    else:
        media_type = "application/octet-stream"
    return FileResponse(file_path, media_type=media_type)


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
        render_straight,
        render_l_shape,
        render_u_shape,
    )

    svg = _render(req)
    return {"svg": svg, "bench_type": req.bench_type, "name": req.name}


@router.post("/drawings/bench/pdf")
async def generate_bench_pdf(req: BenchRequest):
    """Generate a PDF bench drawing from dimensions."""
    from app.services.vision.bench_renderer import drawings_to_pdf

    svg = _render(req)
    output_path = os.path.join(
        tempfile.gettempdir(),
        f"bench_{req.bench_type}_{req.name.replace(' ', '_')}.pdf",
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


@router.post("/drawings/bench/dxf")
async def generate_bench_dxf(req: BenchRequest):
    """Generate a DXF (CNC) file for a bench or banquette.

    Returns 501 Not Implemented if the optional `ezdxf` package is not
    installed, or 200 with application/dxf body otherwise. Uses the same
    dimensions as /drawings/bench and /drawings/bench/pdf; the DXF is
    built from the bench renderer's BenchModel + Part geometry.
    """
    from app.services.vision.bench_renderer import (
        BenchModel,
        generate_dxf,
        render_straight,
        render_l_shape,
        render_u_shape,
    )

    width_in = req.lf * 12
    panel_style = req.panel_style if req.panel_style != "flat" else "vertical_channels"

    # Build a BenchModel that matches the SVG renderer output
    model = BenchModel(
        name=req.name,
        width=width_in,
        depth=req.seat_depth,
        seat_h=req.seat_height,
        back_h=req.back_height,
        panel_style=panel_style,
        quote_num=req.quote_num or "",
    )

    # L-shape and U-shape benches use a single BenchModel for the longest
    # leg; the full multi-leg cut list would require a richer model. We
    # surface that as a 200 with a "single_leg" note so the CNC operator
    # knows to add additional legs.
    note = None
    if req.bench_type in ("l_shape", "u_shape"):
        note = (
            f"DXF currently exports a single-leg cut list. For {req.bench_type} benches, "
            "additional leg panels are not yet emitted; this is a known limitation."
        )

    # Also render the matching SVG so the operator can compare CNC parts to
    # the 4-quadrant drawing. We use the same helper as /drawings/bench.
    if req.bench_type == "l_shape":
        long_in = req.leg1_length * 12 if req.leg1_length > 0 else width_in * 0.6
        _ = render_l_shape(
            req.name,
            long_in,
            width_in - long_in,
            req.seat_depth,
            req.seat_height,
            req.back_height,
            quote_num=req.quote_num,
            panel_style=panel_style,
        )
    elif req.bench_type == "u_shape":
        back_in = req.back_length * 12 if req.back_length > 0 else width_in * 0.45
        side_in = req.left_depth * 12 if req.left_depth > 0 else width_in * 0.275
        _ = render_u_shape(
            req.name,
            back_in,
            side_in,
            req.seat_depth,
            req.seat_depth,
            req.seat_height,
            req.back_height,
            quote_num=req.quote_num,
            panel_style=panel_style,
        )
    else:
        _ = render_straight(
            req.name,
            width_in,
            req.seat_depth,
            req.seat_height,
            req.back_height,
            quote_num=req.quote_num,
            panel_style=panel_style,
        )

    base_dir = os.path.expanduser("~/empire-repo/uploads/arch_drawings")
    os.makedirs(base_dir, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", req.name).strip("_") or "bench"
    out_path = os.path.join(base_dir, f"{safe_name}_{req.bench_type}.dxf")

    result_path = generate_dxf(model, out_path)
    if result_path is None:
        raise HTTPException(
            status_code=501,
            detail={
                "error": "dxf_dependency_missing",
                "package": "ezdxf",
                "reason": "Install the optional `ezdxf` package to enable DXF export.",
            },
        )

    with open(result_path, "rb") as f:
        dxf_bytes = f.read()

    headers = {
        "Content-Disposition": f'attachment; filename="{safe_name}_{req.bench_type}.dxf"',
    }
    if note:
        headers["X-DXF-Note"] = note

    return Response(
        content=dxf_bytes,
        media_type="application/dxf",
        headers=headers,
    )


class YardageRequest(BaseModel):
    item_type: str = "generic"
    dimensions: dict = {}
    notes: str = ""


@router.post("/drawings/yardage")
async def estimate_yardage(req: YardageRequest):
    """First-pass fabric-yardage estimate for a Workroom item.

    This is a planning estimate, not a procurement quote. The response
    always includes `confidence` ("first_pass" or "fallback") and a
    `notes` field documenting what assumptions were made.

    Supports a wide set of Workroom item types (drapery, roman shade,
    cornice, cushion, pillow, sofa, chair, ottoman, headboard, bedding,
    banquette, slipcover). Unknown types fall back to a generic
    upholstery estimator and the response is marked `confidence=fallback`.
    """
    if not req.item_type:
        raise HTTPException(
            status_code=422,
            detail={"error": "missing_item_type", "reason": "item_type is required"},
        )

    result = yardage.estimate(req.item_type, req.dimensions or {})
    result["input"] = {
        "item_type": req.item_type,
        "dimensions": req.dimensions or {},
        "notes": req.notes or "",
    }
    return result


def _render(req: BenchRequest) -> str:
    from app.services.vision.bench_renderer import (
        render_straight,
        render_l_shape,
        render_u_shape,
    )

    width_in = req.lf * 12
    d = req.seat_depth
    sh = req.seat_height
    bh = req.back_height

    ps = req.panel_style if req.panel_style != "flat" else "vertical_channels"

    if req.bench_type == "l_shape":
        long_in = req.leg1_length * 12 if req.leg1_length > 0 else width_in * 0.6
        short_in = req.leg2_length * 12 if req.leg2_length > 0 else width_in * 0.4
        return render_l_shape(
            req.name,
            long_in,
            short_in,
            d,
            sh,
            bh,
            quote_num=req.quote_num,
            panel_style=ps,
        )
    elif req.bench_type == "u_shape":
        back_in = req.back_length * 12 if req.back_length > 0 else width_in * 0.45
        side_in = req.left_depth * 12 if req.left_depth > 0 else width_in * 0.275
        side_d = req.right_depth if req.right_depth > 0 else d
        return render_u_shape(
            req.name,
            back_in,
            side_in,
            d,
            side_d,
            sh,
            bh,
            quote_num=req.quote_num,
            panel_style=ps,
        )
    else:
        return render_straight(
            req.name, width_in, d, sh, bh, quote_num=req.quote_num, panel_style=ps
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
    if not provider_status.xai_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "vision_provider_unavailable",
                "provider": "xai",
                "reason": provider_status.unavailable_reason("xai"),
            },
        )

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            res = await client.post(
                "https://api.x.ai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {XAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "grok-4-fast-non-reasoning",
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {"type": "image_url", "image_url": {"url": req.image}},
                                {"type": "text", "text": SKETCH_EXTRACT_PROMPT},
                            ],
                        }
                    ],
                    "max_tokens": 2000,
                    "temperature": 0.2,
                },
            )
    except httpx.HTTPError as e:
        log.error(f"Vision API transport error: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "error": "vision_provider_transport",
                "provider": "xai",
                "reason": str(e),
            },
        )
    if res.status_code != 200:
        log.error(f"Vision API error: {res.text[:300]}")
        # 401/403/429 are provider-side outages from the caller's perspective
        if res.status_code in (401, 403, 429):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "vision_provider_rejected",
                    "provider": "xai",
                    "upstream_status": res.status_code,
                },
            )
        raise HTTPException(res.status_code, "Vision API error")

    try:
        content = (
            res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
        )
    except (ValueError, KeyError) as e:
        raise HTTPException(502, f"Vision response shape invalid: {e}")

    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        raise HTTPException(500, "Could not parse AI response")

    return json.loads(m.group(0))


class FurnitureAnalyzeRequest(BaseModel):
    image: str  # base64 image data
    provider: str = "grok"  # "grok" or "claude"
    generate_drawings: bool = True
    generate_fabrication: bool = False


@router.post("/drawings/analyze-furniture")
async def analyze_furniture(req: FurnitureAnalyzeRequest):
    """Multi-object furniture analysis — detects ALL items in a photo/sketch.

    Returns items with classifications, dimensions, per-item drawings, and
    optional fabrication data. Upgrades analyze-sketch from single to multi-item.
    """
    # Truthful 503 if the requested provider is unconfigured, OR if every
    # possible provider is unconfigured (so the analyzer has no fallback).
    if not provider_status._provider_configured(req.provider):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "vision_provider_unavailable",
                "provider": req.provider,
                "reason": provider_status.unavailable_reason(req.provider),
            },
        )
    all_unavail = provider_status.all_unavailable(["grok", "claude"])
    if all_unavail:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "vision_all_providers_unavailable",
                "providers": ["grok", "claude"],
                "reason": all_unavail,
            },
        )

    from app.services.vision.furniture_analyzer import (
        analyze_image,
        get_fabrication_data,
        enrich_with_fabric,
    )

    try:
        result = await analyze_image(req.image, provider=req.provider)
    except Exception as e:
        log.error(f"Furniture analysis failed: {e}")
        raise HTTPException(503, f"Analysis failed: {e}")

    if result.error:
        # Map analyzer errors that indicate provider issues to 503
        low = (result.error or "").lower()
        if any(
            token in low
            for token in (
                "invalid_grant",
                "credit",
                "unauthorized",
                "rate limit",
                "quota",
                "401",
                "403",
                "429",
            )
        ):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "vision_provider_rejected",
                    "upstream_error": result.error,
                },
            )
        raise HTTPException(500, result.error)

    response = result.to_dict()

    # Optional fabrication data
    if req.generate_fabrication:
        fab_data = [get_fabrication_data(item) for item in result.items]
        response["fabrication"] = fab_data

    # Fabric enrichment (always attempt)
    try:
        response["fabric_matches"] = enrich_with_fabric(result.items)
    except Exception:
        response["fabric_matches"] = []

    return response


@router.post("/drawings/analyze-furniture/pdf")
async def analyze_furniture_pdf(req: FurnitureAnalyzeRequest):
    """Multi-object furniture analysis with PDF output."""
    if not provider_status._provider_configured(req.provider):
        raise HTTPException(
            status_code=503,
            detail={
                "error": "vision_provider_unavailable",
                "provider": req.provider,
                "reason": provider_status.unavailable_reason(req.provider),
            },
        )
    all_unavail = provider_status.all_unavailable(["grok", "claude"])
    if all_unavail:
        raise HTTPException(
            status_code=503,
            detail={
                "error": "vision_all_providers_unavailable",
                "providers": ["grok", "claude"],
                "reason": all_unavail,
            },
        )

    from app.services.vision.furniture_analyzer import analyze_image, analysis_to_pdf

    try:
        result = await analyze_image(req.image, provider=req.provider)
    except Exception as e:
        log.error(f"furniture analysis transport failure: {e}")
        raise HTTPException(503, f"Analysis failed: {e}")

    if result.error:
        low = (result.error or "").lower()
        if any(
            token in low
            for token in (
                "invalid_grant",
                "credit",
                "unauthorized",
                "rate limit",
                "quota",
                "401",
                "403",
                "429",
            )
        ):
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "vision_provider_rejected",
                    "upstream_error": result.error,
                },
            )
        raise HTTPException(500, result.error)

    if not result.drawings:
        raise HTTPException(422, "No drawings generated")

    output_path = analysis_to_pdf(result)

    with open(output_path, "rb") as f:
        pdf_bytes = f.read()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": 'attachment; filename="furniture_analysis.pdf"'
        },
    )

    try:
        result = await analyze_image(req.image, provider=req.provider)
    except Exception as e:
        log.error(f"Furniture analysis failed: {e}")
        raise HTTPException(500, f"Analysis failed: {e}")

    if result.error:
        raise HTTPException(500, result.error)

    response = result.to_dict()

    # Optional fabrication data
    if req.generate_fabrication:
        fab_data = [get_fabrication_data(item) for item in result.items]
        response["fabrication"] = fab_data

    # Fabric enrichment (always attempt)
    try:
        response["fabric_matches"] = enrich_with_fabric(result.items)
    except Exception:
        response["fabric_matches"] = []

    return response


class GeneralDrawingRequest(BaseModel):
    name: str = "Drawing"
    item_type: str = "generic"
    dimensions: dict = {}
    notes: str = ""
    # Bench-specific (only used when item_type == "bench")
    bench_type: str = "straight"
    lf: float = 0
    rate: float = 0
    quote_num: str = ""


class DrawingAssetRequest(BaseModel):
    name: str = "Drawing"
    item_type: str = "generic"
    route_to: Optional[str] = None
    svg: str
    room_id: Optional[str] = None
    item_id: Optional[str] = None
    assigned_room_id: Optional[str] = None
    assigned_item_id: Optional[str] = None
    item_key: Optional[str] = None
    quote_id: Optional[str] = None
    dimensions: dict = {}
    notes: str = ""


@router.post("/drawings/assets")
async def save_drawing_asset(req: DrawingAssetRequest):
    """Persist a generated SVG as a quote/job attachable drawing asset."""
    if "<svg" not in req.svg:
        raise HTTPException(status_code=400, detail="SVG drawing content required")

    base_dir = os.path.expanduser("~/empire-repo/uploads/arch_drawings")
    os.makedirs(base_dir, exist_ok=True)
    safe_type = (
        re.sub(r"[^a-zA-Z0-9_-]+", "_", req.item_type or "drawing").strip("_")
        or "drawing"
    )
    filename = f"{safe_type}_{uuid.uuid4().hex[:10]}.svg"
    file_path = os.path.join(base_dir, filename)
    with open(file_path, "w", encoding="utf-8") as f:
        f.write(req.svg)

    route_to = route_to_for_item_type(req.item_type, req.route_to)
    assigned_room_id = req.assigned_room_id or req.room_id
    assigned_item_id = req.assigned_item_id or req.item_id
    item_key = req.item_key or assigned_item_id

    asset = {
        "id": filename.rsplit(".", 1)[0],
        "name": req.name,
        "item_type": req.item_type,
        "route_to": route_to,
        "url": f"/api/v1/drawings/files/{filename}",
        "filename": filename,
        "assigned_room_id": assigned_room_id,
        "assigned_item_id": assigned_item_id,
        "item_key": item_key,
        "dimensions": req.dimensions,
        "notes": req.notes,
        "created_at": datetime.utcnow().isoformat(),
    }
    return {"status": "saved", "asset": asset}


class UniversalDrawingRequest(BaseModel):
    user_text: str = ""
    params: dict = {}


def _estimate_lf(dimensions: dict, lf: float) -> float:
    """Estimate linear feet from dimension values when lf is 0."""
    if lf > 0:
        return lf
    max_inches = 0
    for label, value in dimensions.items():
        val_str = str(value).strip().rstrip("\"'").strip()
        try:
            inches = float(re.sub(r"[^0-9.]", "", val_str))
            label_lower = label.lower()
            if any(kw in label_lower for kw in ["height", "ht", "depth", "deep"]):
                continue
            if inches > max_inches:
                max_inches = inches
        except (ValueError, TypeError):
            continue
    if max_inches > 0:
        return max_inches / 12
    return 6


def _render_general(req: GeneralDrawingRequest) -> tuple[str, str]:
    """Route to the correct renderer. Returns (svg, resolved_type)."""
    from app.services.vision.drawing_service import (
        classify_item,
        render_measurement_diagram,
    )

    # Smart classification — use item_type as hint but verify
    classification = classify_item(
        user_text=req.item_type,
        item_name=req.name,
    )
    resolved_type = classification["type"]

    if resolved_type == "bench" or req.item_type == "bench":
        from app.services.vision.bench_renderer import (
            render_straight,
            render_l_shape,
            render_u_shape,
        )

        lf = _estimate_lf(req.dimensions, req.lf)
        width_in = lf * 12
        if "u" in req.bench_type:
            return render_u_shape(req.name, width_in, quote_num=req.quote_num), "bench"
        elif "l" in req.bench_type:
            return render_l_shape(req.name, width_in, quote_num=req.quote_num), "bench"
        else:
            return render_straight(req.name, width_in, quote_num=req.quote_num), "bench"
    else:
        svg = render_measurement_diagram(
            name=req.name,
            item_type=resolved_type,
            dimensions=req.dimensions,
            notes=req.notes,
        )
        return svg, resolved_type


@router.post("/drawings/generate")
async def generate_universal_drawing(req: UniversalDrawingRequest):
    """Universal drawing endpoint — smart classification routes to correct renderer.

    Accepts user_text (what the user asked for) and params (dimensions, name, etc).
    Returns SVG + classification info.
    """
    return _render_universal_drawing(req)


def _render_universal_drawing(req: UniversalDrawingRequest) -> dict:
    """Render the universal drawing request once for preview and PDF paths."""
    from app.services.vision.drawing_service import classify_item, generate_drawing
    from app.services.vision.parametric_templates import render_template_instance

    params = req.params or {}
    user_text = req.user_text or ""
    name = params.get("name", "")
    style_key = params.get("style_key") or params.get("template_key")
    explicit_item_type = (params.get("item_type") or "").lower().strip() or None

    if style_key:
        template_result = render_template_instance(style_key, params)
        if template_result:
            return {
                **template_result,
                "classification": {
                    "type": template_result["item_type"],
                    "renderer": "parametric_template",
                    "views": 4,
                    "confidence": 1.0,
                },
            }

    # Classify
    classification = classify_item(
        user_text=user_text,
        item_name=name,
        description=params.get("description", ""),
        filename=params.get("filename", ""),
    )

    resolved_type = classification["type"]
    # Prefer the caller's explicit item_type when the classifier falls back to
    # "generic" — the user usually knows what they asked for.
    if explicit_item_type and resolved_type in ("generic", ""):
        resolved_type = explicit_item_type
    # Also prefer the caller's explicit item_type when the classifier is
    # unconfident. The classifier's `confidence` field is a human-readable
    # string ("high"/"medium"/"low") in most paths; coerce safely so a
    # TypeError never escapes this route.
    if explicit_item_type and explicit_item_type != resolved_type:
        try:
            conf = float(classification.get("confidence", 1.0))
        except (TypeError, ValueError):
            conf = 1.0
        if conf < 0.7:
            resolved_type = explicit_item_type
    # Finally: when the caller's explicit item_type IS one of the parametric
    # families we now default to (e.g. banquette, chair, shelving, table),
    # always prefer it over a classifier that collapsed it to a generic
    # "bench" or "millwork" — the user named a parametric family, so render
    # parametric, not the shared 2-view fallback.
    if explicit_item_type and _default_style_for(explicit_item_type):
        resolved_type = explicit_item_type

    # NEW: try parametric template as default for the 10 supported families
    # (drapery, roman_shade, cornice_valance, banquette, chair, shelving,
    # cabinet_carcass, nightstand, entertainment_center, wall_unit, desk_table).
    # This makes parametric the primary rendering path; we fall through to
    # bench_renderer / drawing_service only when no parametric template
    # exists for the resolved type.
    if resolved_type not in ("bench",):
        default_style = _default_style_for(resolved_type)
        if default_style:
            template_params = {**params, "item_type": resolved_type}
            template_result = render_template_instance(default_style, template_params)
            if template_result:
                return {
                    **template_result,
                    "classification": {
                        "type": template_result["item_type"],
                        "renderer": "parametric_template",
                        "views": 4,
                        "confidence": 1.0,
                        "default_style": default_style,
                    },
                }

    if resolved_type == "bench":
        # Route to bench_renderer (4-quadrant professional)
        from app.services.vision.bench_renderer import (
            render_straight,
            render_l_shape,
            render_u_shape,
        )

        # Detect bench subtype from text
        all_text = f"{user_text} {name}".lower()
        if any(kw in all_text for kw in ["u-shape", "u shape", "u_shape", "booth"]):
            bench_sub = "u_shape"
        elif any(kw in all_text for kw in ["l-shape", "l shape", "l_shape"]):
            bench_sub = "l_shape"
        else:
            bench_sub = "straight"

        width = params.get("width", 120)
        depth = params.get("depth", 20)
        seat_h = params.get("seat_height", 18)
        back_h = params.get("back_height", 18)

        if bench_sub == "u_shape":
            svg = render_u_shape(
                name or "Bench",
                width,
                depth_in=depth,
                seat_h_in=seat_h,
                back_h_in=back_h,
            )
        elif bench_sub == "l_shape":
            short = params.get("short", params.get("depth", width * 0.5))
            svg = render_l_shape(
                name or "Bench",
                width,
                short,
                depth_in=depth,
                seat_h_in=seat_h,
                back_h_in=back_h,
            )
        else:
            svg = render_straight(
                name or "Bench",
                width,
                depth_in=depth,
                seat_h_in=seat_h,
                back_h_in=back_h,
            )

        return {
            "svg": svg,
            "item_type": "bench",
            "bench_type": bench_sub,
            "classification": classification,
            "name": name,
        }

    # Non-bench: use drawing_service renderers
    result = generate_drawing(
        name=name,
        description=params.get("description", ""),
        dimensions=params.get("dimensions", {}),
        item_type=resolved_type,
        notes=params.get("notes", ""),
        user_text=user_text,
        params=params,
    )
    return {
        "svg": result["svg"],
        "item_type": result["item_type"],
        "classification": classification,
        "name": result["name"],
    }


@router.post("/drawings/generate/pdf")
async def generate_universal_drawing_pdf(req: UniversalDrawingRequest):
    """Generate a PDF from the same SVG used by /drawings/generate."""
    from app.services.vision.bench_renderer import drawings_to_pdf

    result = _render_universal_drawing(req)
    svg = result.get("svg") or ""
    if "<svg" not in svg:
        raise HTTPException(status_code=422, detail="No SVG drawing generated")

    params = req.params or {}
    name = result.get("name") or params.get("name") or "drawing"
    item_type = result.get("template") or result.get("item_type") or "drawing"
    safe_name = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(name)).strip("_") or "drawing"
    safe_type = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(item_type)).strip("_") or "drawing"
    output_path = os.path.join(
        tempfile.gettempdir(), f"drawing_{safe_type}_{safe_name}.pdf"
    )
    drawings_to_pdf([{"name": name, "svg": svg, "lf": 0}], output_path)

    with open(output_path, "rb") as f:
        pdf_bytes = f.read()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="drawing_{safe_type}.pdf"'
        },
    )


@router.post("/drawings/general")
async def generate_general_drawing(req: GeneralDrawingRequest):
    """Generate an SVG drawing for any item type."""
    svg, resolved_type = _render_general(req)
    return {"svg": svg, "item_type": resolved_type, "name": req.name}


@router.post("/drawings/general/pdf")
async def generate_general_pdf(req: GeneralDrawingRequest):
    """Generate a PDF drawing for any item type."""
    from app.services.vision.bench_renderer import drawings_to_pdf

    svg, resolved_type = _render_general(req)

    output_path = os.path.join(
        tempfile.gettempdir(),
        f"drawing_{resolved_type}_{req.name.replace(' ', '_')}.pdf",
    )
    drawings_to_pdf([{"name": req.name, "svg": svg, "lf": req.lf}], output_path)

    with open(output_path, "rb") as f:
        pdf_bytes = f.read()

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="drawing_{resolved_type}.pdf"'
        },
    )


class ProjectSheetRequest(BaseModel):
    title: str = "BUILT-IN BENCHES"
    quote_num: str = ""
    benches: list = []


@router.post("/drawings/project-sheet")
async def generate_project_sheet(req: ProjectSheetRequest):
    """Generate a multi-bench project sheet SVG."""
    from app.services.vision.bench_renderer import render_project_sheet

    svg = render_project_sheet(req.benches, title=req.title, quote_num=req.quote_num)
    return {"svg": svg}


@router.post("/drawings/project-sheet/pdf")
async def generate_project_sheet_pdf(req: ProjectSheetRequest):
    """Generate a multi-bench project sheet PDF."""
    from app.services.vision.bench_renderer import render_project_sheet, drawings_to_pdf

    svg = render_project_sheet(req.benches, title=req.title, quote_num=req.quote_num)
    output_path = os.path.join(
        tempfile.gettempdir(), f"project_sheet_{req.quote_num or 'benches'}.pdf"
    )
    drawings_to_pdf([{"name": req.title, "svg": svg, "lf": 0}], output_path)
    with open(output_path, "rb") as f:
        pdf_bytes = f.read()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="project_sheet.pdf"'},
    )


# ============================================================
# AI PARAMETRIC DRAWING ENGINE — two-stage pipeline
# ============================================================


class AIBenchRequest(BaseModel):
    bench_type: str = "bench_straight"  # bench_straight, bench_l_shape, bench_u_shape
    label: str = "BENCH"
    dimensions: dict = {}
    options: dict = {}


@router.post("/drawings/ai/bench")
async def generate_ai_bench(req: AIBenchRequest):
    """Generate a bench drawing — redirects to professional bench_renderer.py.

    Legacy endpoint: frontend used to call this for AI parametric pipeline.
    Now routes to the 4-quadrant professional renderer (1200x850, no rotated text).
    """
    from app.services.vision.bench_renderer import (
        render_straight,
        render_l_shape,
        render_u_shape,
    )

    # Parse bench_type: "bench_straight" → "straight"
    bt = req.bench_type.replace("bench_", "")
    dims = req.dimensions or {}
    width_in = float(dims.get("width", dims.get("total_length", 120)))
    if width_in < 50:
        width_in = width_in * 12  # convert feet to inches
    depth = float(dims.get("seat_depth", dims.get("depth", 20)))
    seat_h = float(dims.get("seat_height", 18))
    back_h = float(dims.get("back_height", 18))

    if "u" in bt:
        svg = render_u_shape(
            req.label, width_in, depth_in=depth, seat_h_in=seat_h, back_h_in=back_h
        )
    elif "l" in bt:
        svg = render_l_shape(
            req.label, width_in, depth_in=depth, seat_h_in=seat_h, back_h_in=back_h
        )
    else:
        svg = render_straight(
            req.label, width_in, depth_in=depth, seat_h_in=seat_h, back_h_in=back_h
        )

    return {"svg": svg, "label": req.label}


@router.post("/drawings/ai/bench/pdf")
async def generate_ai_bench_pdf(req: AIBenchRequest):
    """Generate bench PDF — redirects to professional bench_renderer.py."""
    from app.services.vision.bench_renderer import (
        render_straight,
        render_l_shape,
        render_u_shape,
        drawings_to_pdf,
    )

    bt = req.bench_type.replace("bench_", "")
    dims = req.dimensions or {}
    width_in = float(dims.get("width", dims.get("total_length", 120)))
    if width_in < 50:
        width_in = width_in * 12
    depth = float(dims.get("seat_depth", dims.get("depth", 20)))
    seat_h = float(dims.get("seat_height", 18))
    back_h = float(dims.get("back_height", 18))

    if "u" in bt:
        svg = render_u_shape(
            req.label, width_in, depth_in=depth, seat_h_in=seat_h, back_h_in=back_h
        )
    elif "l" in bt:
        svg = render_l_shape(
            req.label, width_in, depth_in=depth, seat_h_in=seat_h, back_h_in=back_h
        )
    else:
        svg = render_straight(
            req.label, width_in, depth_in=depth, seat_h_in=seat_h, back_h_in=back_h
        )

    output_path = os.path.join(
        tempfile.gettempdir(), f"ai_bench_{req.label.replace(' ', '_')}.pdf"
    )
    drawings_to_pdf([{"name": req.label, "svg": svg, "lf": 0}], output_path)

    with open(output_path, "rb") as f:
        pdf_bytes = f.read()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="bench_drawing.pdf"'},
    )


class AIProjectSheetRequest(BaseModel):
    benches: list = []
    layout: dict = {}


@router.post("/drawings/ai/project-sheet")
async def generate_ai_project_sheet(req: AIProjectSheetRequest):
    """Generate multi-bench project sheet via AI pipeline."""
    # Truthful 503 when no draftsman provider is configured. The AI draftsman
    # silently returns {} when both Claude and OpenAI keys are missing; we
    # surface that as 503 *before* burning a request per bench.
    if not provider_status.draftsman_providers_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "draftsman_providers_unavailable",
                "providers_checked": ["anthropic", "openai"],
                "reason": "Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is set",
            },
        )

    from app.services.drawing.ai_draftsman import build_bench_prompt, call_draftsman
    from app.services.drawing.parametric_renderer import render_project_sheet
    from app.services.drawing.validator import validate_drawing, inject_defaults

    bench_drawings = []
    for bench in req.benches:
        try:
            prompt = build_bench_prompt(
                bench.get("type", "bench_straight"),
                bench.get("dimensions", {}),
                bench.get("label", "BENCH"),
                bench.get("options", {}),
            )
            drawing_json = await call_draftsman(prompt)
        except Exception as e:
            log.error(f"draftsman call failed for bench: {e}")
            raise HTTPException(
                status_code=503,
                detail={"error": "draftsman_transport", "reason": str(e)},
            )
        if not drawing_json:
            # call_draftsman returns {} when every provider failed. Surface
            # this as 503 instead of 422 so the cause is clear.
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "draftsman_returned_empty",
                    "reason": "All configured draftsman providers failed to produce JSON",
                    "providers_attempted": provider_status.draftsman_providers_configured(),
                },
            )
        is_valid, errors = validate_drawing(drawing_json)
        if is_valid:
            drawing_json = inject_defaults(drawing_json)
            bench_drawings.append(drawing_json)
        else:
            log.warning(f"Skipping invalid bench: {errors}")

    if not bench_drawings:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "no_valid_bench_drawings",
                "reason": "Every bench in the request produced invalid AI draftsman output",
            },
        )

    svg = render_project_sheet(bench_drawings, req.layout)
    return {"svg": svg, "count": len(bench_drawings)}


@router.post("/drawings/ai/project-sheet/pdf")
async def generate_ai_project_sheet_pdf(req: AIProjectSheetRequest):
    """Generate project sheet PDF via AI pipeline."""
    if not provider_status.draftsman_providers_configured():
        raise HTTPException(
            status_code=503,
            detail={
                "error": "draftsman_providers_unavailable",
                "providers_checked": ["anthropic", "openai"],
                "reason": "Neither ANTHROPIC_API_KEY nor OPENAI_API_KEY is set",
            },
        )

    from app.services.drawing.ai_draftsman import build_bench_prompt, call_draftsman
    from app.services.drawing.parametric_renderer import render_project_sheet
    from app.services.drawing.validator import validate_drawing, inject_defaults
    from app.services.vision.bench_renderer import drawings_to_pdf

    bench_drawings = []
    for bench in req.benches:
        try:
            prompt = build_bench_prompt(
                bench.get("type", "bench_straight"),
                bench.get("dimensions", {}),
                bench.get("label", "BENCH"),
                bench.get("options", {}),
            )
            drawing_json = await call_draftsman(prompt)
        except Exception as e:
            log.error(f"draftsman call failed for bench: {e}")
            raise HTTPException(
                status_code=503,
                detail={"error": "draftsman_transport", "reason": str(e)},
            )
        if not drawing_json:
            raise HTTPException(
                status_code=503,
                detail={
                    "error": "draftsman_returned_empty",
                    "providers_attempted": provider_status.draftsman_providers_configured(),
                },
            )
        is_valid, _ = validate_drawing(drawing_json)
        if is_valid:
            bench_drawings.append(inject_defaults(drawing_json))

    if not bench_drawings:
        raise HTTPException(
            status_code=422,
            detail={"error": "no_valid_bench_drawings"},
        )

    layout = req.layout or {"title": "BUILT-IN BENCHES"}
    svg = render_project_sheet(bench_drawings, layout)

    output_path = os.path.join(tempfile.gettempdir(), "ai_project_sheet.pdf")
    drawings_to_pdf(
        [{"name": layout.get("title", "BENCHES"), "svg": svg, "lf": 0}], output_path
    )

    with open(output_path, "rb") as f:
        pdf_bytes = f.read()
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="ai_project_sheet.pdf"'},
    )


# ── PRODUCT CATALOG API ──────────────────────────────────────────


@router.get("/drawings/catalog")
async def get_product_catalog(business_unit: str = None, mode: str = None):
    """Browse the full product catalog — 18 categories, 204+ styles."""
    from app.services.vision.product_catalog import PRODUCT_CATALOG, get_total_styles
    from app.services.vision.renderer_registry import (
        RENDERER_MAP,
        get_renderer,
        get_business_unit as get_biz,
    )
    from app.services.vision.parametric_templates import get_template_for_style

    # Renderer mode truth — which modes produce genuinely different output
    RENDERER_MODE_TRUTH = {
        "_render_bench_straight": {
            "presentation": "active",
            "shop": "active",
            "construction": "active",
        },
        "_render_bench_l": {
            "presentation": "active",
            "shop": "active",
            "construction": "active",
        },
        "_render_bench_u": {
            "presentation": "active",
            "shop": "active",
            "construction": "active",
        },
        "render_straight": {
            "presentation": "active",
            "shop": "active",
            "construction": "active",
        },
        "render_l_shape": {
            "presentation": "active",
            "shop": "active",
            "construction": "active",
        },
        "render_u_shape": {
            "presentation": "active",
            "shop": "active",
            "construction": "active",
        },
        "render_window": {"presentation": "active", "shop": "active"},
        "_render_chair": {"presentation": "active", "shop": "planned"},
        "_render_sofa": {"presentation": "active", "shop": "planned"},
        "_render_ottoman": {"presentation": "active", "shop": "planned"},
        "_render_table": {"presentation": "active", "shop": "planned"},
        "render_millwork": {
            "presentation": "active",
            "shop": "planned",
            "construction": "planned",
        },
        "render_cushion": {"presentation": "active", "shop": "planned"},
        "render_headboard": {"presentation": "active"},
        "render_generic": {"presentation": "active"},
        "_render_slipcover": {"presentation": "active"},
        "_render_bedding": {"presentation": "active"},
        "_render_wall_panel": {"presentation": "active"},
        "_render_commercial": {
            "presentation": "active",
            "shop": "planned",
            "construction": "planned",
        },
    }

    categories = []
    for cat_key, cat_info in PRODUCT_CATALOG.items():
        if business_unit and cat_info.get("business_unit") != business_unit:
            continue
        if mode and mode not in cat_info.get("modes", []):
            continue

        styles = []
        for style_key in cat_info.get("styles", []):
            renderer = get_renderer(style_key)
            renderer_name = (
                renderer.__name__ if hasattr(renderer, "__name__") else str(renderer)
            )
            parametric_template = get_template_for_style(style_key, cat_key)
            # Determine readiness
            if parametric_template:
                readiness = "dedicated"
            elif "generic" in renderer_name:
                readiness = "fallback"
            elif "bench" in renderer_name:
                readiness = "dedicated"
            elif "window" in renderer_name:
                readiness = "dedicated"
            elif "furniture_2view" in renderer_name or "millwork" in renderer_name:
                readiness = "shared_renderer"
            else:
                readiness = "shared_renderer"

            # Mode truth per renderer
            mode_truth = RENDERER_MODE_TRUTH.get(
                renderer_name, {"presentation": "active"}
            )
            mode_status = {}
            for m in cat_info.get("modes", ["presentation"]):
                if parametric_template and m in {"presentation", "shop"}:
                    mode_status[m] = "active"
                else:
                    mode_status[m] = mode_truth.get(m, "planned")

            styles.append(
                {
                    "style_key": style_key,
                    "style_name": style_key.replace("_", " ").title(),
                    "renderer": renderer_name,
                    "readiness": readiness,
                    "business_unit": cat_info.get("business_unit", "workroom"),
                    "modes": cat_info.get("modes", ["presentation"]),
                    "mode_status": mode_status,
                }
            )

        categories.append(
            {
                "key": cat_key,
                "name": cat_key.replace("_", " ").title(),
                "business_unit": cat_info.get("business_unit", "workroom"),
                "style_count": len(styles),
                "modes": cat_info.get("modes", ["presentation"]),
                "styles": styles,
            }
        )

    workroom_count = sum(1 for c in categories if c["business_unit"] == "workroom")
    woodcraft_count = sum(1 for c in categories if c["business_unit"] == "woodcraft")

    return {
        "total_categories": len(categories),
        "total_styles": sum(c["style_count"] for c in categories),
        "business_unit_counts": {
            "workroom": workroom_count,
            "woodcraft": woodcraft_count,
        },
        "categories": categories,
    }


@router.get("/drawings/catalog/search")
async def search_catalog(q: str = ""):
    """Search product catalog by style name, category, or keyword."""
    from app.services.vision.product_catalog import PRODUCT_CATALOG
    from app.services.vision.renderer_registry import get_renderer

    if not q or len(q) < 2:
        return {"results": [], "query": q}

    query = q.lower().strip()
    results = []

    for cat_key, cat_info in PRODUCT_CATALOG.items():
        for style_key in cat_info.get("styles", []):
            searchable = (
                f"{cat_key} {style_key} {cat_info.get('business_unit', '')}".lower()
            )
            if query in searchable:
                renderer = get_renderer(style_key)
                results.append(
                    {
                        "category": cat_key,
                        "style_key": style_key,
                        "style_name": style_key.replace("_", " ").title(),
                        "business_unit": cat_info.get("business_unit", "workroom"),
                        "modes": cat_info.get("modes", []),
                        "renderer": renderer.__name__
                        if hasattr(renderer, "__name__")
                        else "generic",
                    }
                )

    return {"results": results[:50], "query": q, "total": len(results)}


# ─────────────────────────────────────────────────────────────────────
# D2 — Drawing intake schema (NEW). See REPORT-d1-drawing-workflow-research.md
# and REPORT-d1-addendum-animated-diagram.md for context.
#
# Thin route: all schema/enums/helpers live in
# backend/app/services/drawing/intake_schema.py. This block only:
#   1. imports the schema
#   2. exposes ONE new route: POST /drawings/intake
#   3. computes intake_id, received_at, calls the helpers
#
# D2 is the schema gate only; it does NOT call any renderer. The
# actual render is a D4–D6 concern.
# ─────────────────────────────────────────────────────────────────────
import uuid
from datetime import datetime, timezone

from app.services.drawing.intake_schema import (
    DrawingIntakeRequest as _D2Request,
    DrawingIntakeResponse as _D2Response,
    Category as _Category,
    missing_fields_for as _missing_fields_for,
    default_qa_status_for as _default_qa_status_for,
    build_warnings as _build_warnings,
    is_animation_mode as _is_animation_mode,
)


@router.post("/drawings/intake", response_model=_D2Response)
def drawings_intake(req: _D2Request) -> _D2Response:
    """D2 — Structured drawing intake. Returns the populated response.

    This is the schema gate, not a renderer. The response includes the
    per-category required-dim table, the missing-field list, and the
    default QA status. Downstream consumers (D4 fab_qa, future renderers)
    use the same response shape.
    """
    # Per-category required + missing
    required = _D2Request.model_fields["category"].default  # placeholder; replaced below
    cat: _Category = req.category
    missing = _missing_fields_for(cat, req.dimensions)
    # Re-derive required list from the schema (cleanly)
    from app.services.drawing.intake_schema import REQUIRED_DIMS_BY_CATEGORY
    required_list = REQUIRED_DIMS_BY_CATEGORY.get(cat.value, [])

    # Compute default QA status (lowercase per Founder)
    default_status = _default_qa_status_for(
        req.output_mode, req.source_type, req.dimensions, missing, cat
    )

    # Guardrail: animation modes NEVER resolve to shop_ready
    if _is_animation_mode(req.output_mode) and default_status == "shop_ready":
        # This branch is a safety net; default_qa_status_for already
        # never returns shop_ready for animation modes, but we re-assert
        # to make the contract explicit.
        default_status = "review_ready"

    # Build warnings
    warnings = _build_warnings(
        req.output_mode,
        cat,
        req.source_type,
        has_animation_spec=req.animation_spec is not None,
    )

    # Echo the user-supplied warnings (if any) without overriding computed
    if req.warnings:
        warnings = list(warnings) + [w for w in req.warnings if w not in warnings]

    # Category-supported check (for now, all 13 categories are supported;
    # future D4/D6 may mark some as "shop: planned" with a different
    # response). Today we report supported.
    category_unsupported = False

    return _D2Response(
        intake_id=str(uuid.uuid4()),
        received_at=datetime.now(timezone.utc).isoformat(),
        business_unit=req.business_unit,
        category=req.category,
        output_mode=req.output_mode,
        source_type=req.source_type,
        per_category_required_fields=required_list,
        per_category_missing_fields=missing,
        default_qa_status=default_status,
        category_unsupported=category_unsupported,
        warnings=warnings,
    )
