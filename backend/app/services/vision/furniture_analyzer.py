"""Furniture Analyzer — Multi-object vision pipeline for Empire Workroom.

Analyzes photos/sketches to detect MULTIPLE furniture items, extract dimensions,
generate per-item drawings, and produce fabrication/CNC data.

Entry points: Drawing Studio, Quote Builder, MAX chat, Intake form.
"""

import os
import re
import json
import math
import logging
import tempfile
from dataclasses import dataclass, field, asdict
from typing import Optional

import httpx

log = logging.getLogger("furniture_analyzer")

XAI_API_KEY = os.getenv("XAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")


# ============================================================
# SYSTEM PROMPT — owner's definitive specification
# ============================================================

FURNITURE_ANALYSIS_PROMPT = """You are Empire Workroom's senior estimator with 30 years experience in custom upholstery, window treatments, and millwork.

Analyze this image. It may contain ONE or MULTIPLE furniture items — a room photo, a jobsite walkthrough, a hand-drawn sketch with several pieces, or a single close-up.

For EACH distinct item you detect:

1. CLASSIFY the item:
   - bench, banquette, booth (seating built into a space)
   - window, drapery, curtain, shade, blind, valance, cornice
   - chair, dining_chair, accent_chair
   - sofa, sectional, loveseat
   - ottoman, pouf, footstool
   - cushion, pillow, bolster
   - headboard
   - millwork, cabinet, bookcase, built_in, vanity
   - table, desk, console
   - other

2. EXTRACT every visible measurement. Read ALL numbers, tick marks, and annotations.
   Convert to inches when possible. Label each dimension clearly.

3. ESTIMATE missing dimensions from visual proportions and standard furniture sizes:
   - Standard seat height: 18"
   - Standard seat depth: 20"
   - Standard dining table height: 30"
   - Standard counter height: 36"
   - Standard bar height: 42"
   - Standard door width: 36", height: 80"
   Use these ONLY when no measurement is visible. Mark estimated dims with "(est)".

4. NOTE the condition, existing fabric/material, construction details, and any work needed.

5. For benches/banquettes: determine shape (straight, l_shape, u_shape), cushion layout, back style.

6. For windows: note mount type (inside/outside), stacking direction, number of panels.

7. For millwork: note material (wood species if visible), joinery style, hardware.

Return ONLY valid JSON (no markdown, no commentary):
{
    "items": [
        {
            "id": 1,
            "item_type": "bench",
            "name": "Kitchen Banquette - Left Section",
            "confidence": 0.95,
            "dimensions": {
                "width": "96\\"",
                "seat_depth": "20\\"",
                "seat_height": "18\\"",
                "back_height": "34\\""
            },
            "estimated_dimensions": {
                "seat_height": "18\\" (est)"
            },
            "notes": "Existing vinyl covering, worn. Foam needs replacement.",
            "bench_details": {
                "bench_type": "straight",
                "cushion_count": 4,
                "panel_style": "vertical_channels",
                "channel_count": 6
            },
            "window_details": null,
            "millwork_details": null,
            "fabric_notes": "Customer wants Crypton performance fabric",
            "condition": "fair",
            "work_needed": "reupholster"
        }
    ],
    "room_context": "Residential kitchen breakfast nook",
    "photo_quality": "good",
    "measurement_confidence": "high",
    "total_items": 2
}

RULES:
- Every item gets a unique sequential id starting at 1
- "name" should be descriptive and location-specific (not just "Bench")
- confidence: 0.0-1.0 how sure you are about classification
- Include bench_details ONLY for bench/banquette/booth items
- Include window_details ONLY for window treatment items
- Include millwork_details ONLY for cabinet/millwork items
- All other items: those detail fields are null
- If you see text/labels in the image, include them in notes
- If you see a quote number, include it in notes
- photo_quality: "excellent", "good", "fair", "poor"
- measurement_confidence: "high" (clear measurements visible), "medium" (some visible, some estimated), "low" (mostly estimated from proportions)
"""


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class FurnitureItem:
    """Single detected furniture item with dimensions and metadata."""
    id: int = 0
    item_type: str = "generic"
    name: str = ""
    confidence: float = 0.0
    dimensions: dict = field(default_factory=dict)
    estimated_dimensions: dict = field(default_factory=dict)
    notes: str = ""
    bench_details: Optional[dict] = None
    window_details: Optional[dict] = None
    millwork_details: Optional[dict] = None
    fabric_notes: str = ""
    condition: str = ""
    work_needed: str = ""

    @property
    def all_dimensions(self) -> dict:
        """Merge measured + estimated dimensions (measured takes priority)."""
        merged = dict(self.estimated_dimensions or {})
        merged.update(self.dimensions or {})
        return merged

    def dim_inches(self, key: str, default: float = 0) -> float:
        """Extract numeric inches from a dimension value."""
        val = self.all_dimensions.get(key, "")
        if not val:
            return default
        val_str = str(val).strip().rstrip('"\'').replace("(est)", "").strip()
        try:
            return float(re.sub(r'[^0-9.]', '', val_str))
        except (ValueError, TypeError):
            return default


@dataclass
class AnalysisResult:
    """Complete analysis result for an image."""
    items: list[FurnitureItem] = field(default_factory=list)
    room_context: str = ""
    photo_quality: str = "good"
    measurement_confidence: str = "medium"
    total_items: int = 0
    drawings: list[dict] = field(default_factory=list)  # generated SVGs
    error: str = ""

    def to_dict(self) -> dict:
        return {
            "items": [asdict(item) for item in self.items],
            "room_context": self.room_context,
            "photo_quality": self.photo_quality,
            "measurement_confidence": self.measurement_confidence,
            "total_items": self.total_items,
            "drawings": self.drawings,
            "error": self.error,
        }


# ============================================================
# VISION API CALLS
# ============================================================

async def _call_grok_vision(image_b64: str) -> dict:
    """Call xAI Grok Vision for furniture analysis."""
    if not XAI_API_KEY:
        raise ValueError("XAI_API_KEY not configured")

    async with httpx.AsyncClient(timeout=90.0) as client:
        res = await client.post(
            "https://api.x.ai/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {XAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": "grok-4-fast-non-reasoning",
                "messages": [{"role": "user", "content": [
                    {"type": "image_url", "image_url": {"url": image_b64}},
                    {"type": "text", "text": FURNITURE_ANALYSIS_PROMPT},
                ]}],
                "max_tokens": 4000,
                "temperature": 0.2,
            },
        )

    if res.status_code != 200:
        log.error(f"Grok Vision error ({res.status_code}): {res.text[:300]}")
        raise ValueError(f"Vision API error: {res.status_code}")

    content = res.json().get("choices", [{}])[0].get("message", {}).get("content", "")
    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        raise ValueError("Could not parse Vision AI response as JSON")

    return json.loads(m.group(0))


async def _call_claude_vision(image_b64: str) -> dict:
    """Fallback: call Anthropic Claude for furniture analysis."""
    if not ANTHROPIC_API_KEY:
        raise ValueError("ANTHROPIC_API_KEY not configured")

    # Extract media type and raw base64 from data URL
    if image_b64.startswith("data:"):
        parts = image_b64.split(",", 1)
        media_type = parts[0].split(":")[1].split(";")[0]
        raw_b64 = parts[1]
    else:
        media_type = "image/jpeg"
        raw_b64 = image_b64

    async with httpx.AsyncClient(timeout=90.0) as client:
        res = await client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 4000,
                "messages": [{"role": "user", "content": [
                    {"type": "image", "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": raw_b64,
                    }},
                    {"type": "text", "text": FURNITURE_ANALYSIS_PROMPT},
                ]}],
            },
        )

    if res.status_code != 200:
        log.error(f"Claude Vision error ({res.status_code}): {res.text[:300]}")
        raise ValueError(f"Claude Vision API error: {res.status_code}")

    content = res.json().get("content", [{}])[0].get("text", "")
    m = re.search(r"\{[\s\S]*\}", content)
    if not m:
        raise ValueError("Could not parse Claude Vision response as JSON")

    return json.loads(m.group(0))


# ============================================================
# CORE ANALYSIS PIPELINE
# ============================================================

async def analyze_image(image_b64: str, provider: str = "grok") -> AnalysisResult:
    """Analyze an image for furniture items. Returns AnalysisResult with items and drawings.

    Args:
        image_b64: Base64 image data (with or without data: prefix)
        provider: Vision provider — "grok" (default) or "claude"

    Returns:
        AnalysisResult with detected items, generated drawings, and metadata
    """
    result = AnalysisResult()

    # --- Step 1: Call Vision API ---
    try:
        if provider == "claude":
            raw = await _call_claude_vision(image_b64)
        else:
            raw = await _call_grok_vision(image_b64)
    except Exception as e:
        log.error(f"Vision analysis failed ({provider}): {e}")
        # Try fallback provider
        try:
            fallback = "claude" if provider == "grok" else "grok"
            log.info(f"Falling back to {fallback} vision...")
            raw = await _call_claude_vision(image_b64) if fallback == "claude" else await _call_grok_vision(image_b64)
        except Exception as e2:
            result.error = f"All vision providers failed: {e}, {e2}"
            return result

    # --- Step 2: Parse items ---
    result.room_context = raw.get("room_context", "")
    result.photo_quality = raw.get("photo_quality", "good")
    result.measurement_confidence = raw.get("measurement_confidence", "medium")

    raw_items = raw.get("items", [])
    if not raw_items:
        # Single-item legacy format — wrap in list
        if raw.get("item_type"):
            raw_items = [raw]

    for raw_item in raw_items:
        item = FurnitureItem(
            id=raw_item.get("id", 0),
            item_type=_normalize_type(raw_item.get("item_type", "generic")),
            name=raw_item.get("name", ""),
            confidence=float(raw_item.get("confidence", 0.8)),
            dimensions=raw_item.get("dimensions", {}),
            estimated_dimensions=raw_item.get("estimated_dimensions", {}),
            notes=raw_item.get("notes", ""),
            bench_details=raw_item.get("bench_details"),
            window_details=raw_item.get("window_details"),
            millwork_details=raw_item.get("millwork_details"),
            fabric_notes=raw_item.get("fabric_notes", ""),
            condition=raw_item.get("condition", ""),
            work_needed=raw_item.get("work_needed", ""),
        )
        result.items.append(item)

    result.total_items = len(result.items)

    # --- Step 3: Generate drawings per item ---
    for item in result.items:
        try:
            drawing = _generate_item_drawing(item)
            if drawing:
                result.drawings.append(drawing)
        except Exception as e:
            log.error(f"Drawing generation failed for item {item.id} ({item.item_type}): {e}")
            result.drawings.append({
                "item_id": item.id,
                "name": item.name,
                "error": str(e),
            })

    # --- Step 4: Generate cover sheet if multiple items ---
    if len(result.items) > 1:
        try:
            cover = _generate_cover_sheet(result)
            result.drawings.insert(0, cover)
        except Exception as e:
            log.error(f"Cover sheet generation failed: {e}")

    log.info(f"Furniture analysis complete: {result.total_items} items, {len(result.drawings)} drawings")
    return result


# ============================================================
# TYPE NORMALIZATION
# ============================================================

_TYPE_MAP = {
    "bench": "bench", "banquette": "bench", "booth": "bench", "seating": "bench",
    "window": "window", "drapery": "window", "curtain": "window", "shade": "window",
    "blind": "window", "valance": "window", "cornice": "window",
    "chair": "chair", "dining_chair": "chair", "accent_chair": "chair",
    "sofa": "sofa", "sectional": "sofa", "loveseat": "sofa", "couch": "sofa",
    "ottoman": "ottoman", "pouf": "ottoman", "footstool": "ottoman",
    "cushion": "cushion", "pillow": "cushion", "bolster": "cushion",
    "headboard": "headboard",
    "millwork": "millwork", "cabinet": "millwork", "bookcase": "millwork",
    "built_in": "millwork", "vanity": "millwork",
    "table": "table", "desk": "table", "console": "table",
}


def _normalize_type(raw_type: str) -> str:
    """Normalize AI-returned type to canonical type."""
    return _TYPE_MAP.get(raw_type.lower().strip(), "generic")


# ============================================================
# PER-ITEM DRAWING GENERATION
# ============================================================

def _generate_item_drawing(item: FurnitureItem) -> dict:
    """Route item to appropriate renderer. Returns {item_id, name, svg, item_type}."""
    t = item.item_type

    if t == "bench":
        return _render_bench_drawing(item)
    elif t == "window":
        return _render_window_diagram(item)
    elif t == "millwork":
        return _render_millwork_diagram(item)
    elif t == "chair":
        return _render_chair_diagram(item)
    elif t in ("sofa", "ottoman", "table"):
        return _render_furniture_2view(item)
    elif t == "cushion":
        return _render_cushion_diagram(item)
    elif t == "headboard":
        return _render_headboard_diagram(item)
    else:
        return _render_generic_diagram(item)


def _render_bench_drawing(item: FurnitureItem) -> dict:
    """Route bench items to bench_renderer.py (4-quadrant professional)."""
    from app.services.vision.bench_renderer import (
        render_straight, render_l_shape, render_u_shape,
    )

    bd = item.bench_details or {}
    bench_type = bd.get("bench_type", "straight")
    width = item.dim_inches("width", 120)
    if width < 50:
        width = width * 12  # probably feet, convert to inches
    depth = item.dim_inches("seat_depth", 20)
    seat_h = item.dim_inches("seat_height", 18)
    back_h = item.dim_inches("back_height", 34)
    panel_style = bd.get("panel_style", "vertical_channels")
    channel_count = bd.get("channel_count", 6)
    cushion_width = bd.get("cushion_width", 24)

    if "u" in bench_type:
        svg = render_u_shape(
            item.name, width, depth_in=depth, seat_h_in=seat_h, back_h_in=back_h,
            panel_style=panel_style, channel_count=channel_count,
            cushion_width=cushion_width,
        )
    elif "l" in bench_type:
        svg = render_l_shape(
            item.name, width, depth_in=depth, seat_h_in=seat_h, back_h_in=back_h,
            panel_style=panel_style, channel_count=channel_count,
            cushion_width=cushion_width,
        )
    else:
        svg = render_straight(
            item.name, width, depth_in=depth, seat_h_in=seat_h, back_h_in=back_h,
            panel_style=panel_style, channel_count=channel_count,
            cushion_width=cushion_width,
        )

    return {"item_id": item.id, "name": item.name, "svg": svg, "item_type": "bench"}


def _render_window_diagram(item: FurnitureItem) -> dict:
    """Render window treatment diagram via drawing_service."""
    from app.services.vision.drawing_service import render_measurement_diagram

    svg = render_measurement_diagram(
        name=item.name,
        item_type="window",
        dimensions=item.all_dimensions,
        notes=item.notes,
    )
    return {"item_id": item.id, "name": item.name, "svg": svg, "item_type": "window"}


def _render_millwork_diagram(item: FurnitureItem) -> dict:
    """Render millwork/cabinet diagram via drawing_service."""
    from app.services.vision.drawing_service import render_measurement_diagram

    svg = render_measurement_diagram(
        name=item.name,
        item_type="millwork",
        dimensions=item.all_dimensions,
        notes=item.notes,
    )
    return {"item_id": item.id, "name": item.name, "svg": svg, "item_type": "millwork"}


def _render_chair_diagram(item: FurnitureItem) -> dict:
    """Render chair diagram (front + side elevation) via drawing_service."""
    from app.services.vision.drawing_service import render_measurement_diagram

    svg = render_measurement_diagram(
        name=item.name,
        item_type="chair",
        dimensions=item.all_dimensions,
        notes=item.notes,
    )
    return {"item_id": item.id, "name": item.name, "svg": svg, "item_type": "chair"}


def _render_furniture_2view(item: FurnitureItem) -> dict:
    """Render 2-view diagram for sofa, ottoman, table."""
    from app.services.vision.drawing_service import render_measurement_diagram

    svg = render_measurement_diagram(
        name=item.name,
        item_type=item.item_type,
        dimensions=item.all_dimensions,
        notes=item.notes,
    )
    return {"item_id": item.id, "name": item.name, "svg": svg, "item_type": item.item_type}


def _render_cushion_diagram(item: FurnitureItem) -> dict:
    """Render cushion/pillow diagram via drawing_service."""
    from app.services.vision.drawing_service import render_measurement_diagram

    svg = render_measurement_diagram(
        name=item.name,
        item_type="cushion",
        dimensions=item.all_dimensions,
        notes=item.notes,
    )
    return {"item_id": item.id, "name": item.name, "svg": svg, "item_type": "cushion"}


def _render_headboard_diagram(item: FurnitureItem) -> dict:
    """Render headboard diagram via drawing_service."""
    from app.services.vision.drawing_service import render_measurement_diagram

    svg = render_measurement_diagram(
        name=item.name,
        item_type="headboard",
        dimensions=item.all_dimensions,
        notes=item.notes,
    )
    return {"item_id": item.id, "name": item.name, "svg": svg, "item_type": "headboard"}


def _render_generic_diagram(item: FurnitureItem) -> dict:
    """Render generic measurement diagram for unknown types."""
    from app.services.vision.drawing_service import render_measurement_diagram

    svg = render_measurement_diagram(
        name=item.name,
        item_type="generic",
        dimensions=item.all_dimensions,
        notes=item.notes,
    )
    return {"item_id": item.id, "name": item.name, "svg": svg, "item_type": "generic"}


# ============================================================
# COVER SHEET & PROJECT SUMMARY
# ============================================================

# SVG styling constants (match drawing_service.py)
FONT = "Arial, Helvetica, sans-serif"
BLACK = "#000000"
GRAY = "#666666"
LIGHT_GRAY = "#CCCCCC"
SW_BORDER = 2.0


def _esc(s: str) -> str:
    """Escape HTML entities for SVG text."""
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def _generate_cover_sheet(result: AnalysisResult) -> dict:
    """Generate a cover/summary sheet listing all detected items.

    Single-page 850x1100 portrait SVG with:
    - Title: "FURNITURE ANALYSIS — {room_context}"
    - Table of items with type, name, key dimensions, condition
    - Photo quality and measurement confidence indicators
    - Empire Workroom branding
    """
    W, H = 850, 1100
    parts = []

    # Background & border
    parts.append(f'<rect x="0" y="0" width="{W}" height="{H}" fill="white"/>')
    parts.append(f'<rect x="15" y="15" width="{W-30}" height="{H-30}" fill="none" '
                 f'stroke="{BLACK}" stroke-width="{SW_BORDER}"/>')

    # Header
    y = 55
    parts.append(f'<text x="{W//2}" y="{y}" text-anchor="middle" '
                 f'font-family="{FONT}" font-size="22" font-weight="bold" fill="{BLACK}">'
                 f'FURNITURE ANALYSIS</text>')
    y += 28
    if result.room_context:
        parts.append(f'<text x="{W//2}" y="{y}" text-anchor="middle" '
                     f'font-family="{FONT}" font-size="14" fill="{GRAY}">'
                     f'{_esc(result.room_context)}</text>')
        y += 22

    # Metadata line
    parts.append(f'<text x="40" y="{y}" font-family="{FONT}" font-size="11" fill="{GRAY}">'
                 f'Items: {result.total_items} | '
                 f'Photo: {result.photo_quality} | '
                 f'Measurements: {result.measurement_confidence}</text>')
    y += 8

    # Divider
    y += 10
    parts.append(f'<line x1="30" y1="{y}" x2="{W-30}" y2="{y}" stroke="{LIGHT_GRAY}" stroke-width="1"/>')
    y += 20

    # Column headers
    cols = [40, 60, 200, 460, 620, 740]
    headers = ["#", "Type", "Name", "Key Dims", "Condition", "Work"]
    for cx, hdr in zip(cols, headers):
        parts.append(f'<text x="{cx}" y="{y}" font-family="{FONT}" font-size="11" '
                     f'font-weight="bold" fill="{BLACK}">{hdr}</text>')
    y += 6
    parts.append(f'<line x1="30" y1="{y}" x2="{W-30}" y2="{y}" stroke="{BLACK}" stroke-width="0.75"/>')
    y += 18

    # Item rows
    for item in result.items:
        if y > H - 120:
            parts.append(f'<text x="40" y="{y}" font-family="{FONT}" font-size="11" fill="{GRAY}">'
                         f'... and {result.total_items - item.id + 1} more items</text>')
            break

        # Key dims: pick the 2-3 most important
        key_dims = _summarize_dims(item)

        row_data = [
            str(item.id),
            item.item_type.replace("_", " ").title(),
            _truncate(item.name, 30),
            key_dims,
            item.condition or "—",
            _truncate(item.work_needed, 12) or "—",
        ]
        for cx, val in zip(cols, row_data):
            parts.append(f'<text x="{cx}" y="{y}" font-family="{FONT}" font-size="10" fill="{BLACK}">'
                         f'{_esc(val)}</text>')
        y += 22

        # Light separator between rows
        parts.append(f'<line x1="30" y1="{y - 6}" x2="{W-30}" y2="{y - 6}" '
                     f'stroke="{LIGHT_GRAY}" stroke-width="0.3"/>')

    # Branding at bottom
    parts.append(f'<text x="{W//2}" y="{H-50}" text-anchor="middle" '
                 f'font-family="{FONT}" font-size="14" font-weight="bold" fill="{BLACK}">'
                 f'EMPIRE WORKROOM</text>')
    parts.append(f'<text x="{W//2}" y="{H-35}" text-anchor="middle" '
                 f'font-family="{FONT}" font-size="9" fill="{GRAY}">'
                 f'Custom Upholstery &amp; Window Treatments | 5124 Frolich Ln, Hyattsville, MD 20781</text>')

    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
           f'width="{W}" height="{H}">\n' + "\n".join(parts) + "\n</svg>")

    return {
        "item_id": 0,
        "name": "Cover Sheet",
        "svg": svg,
        "item_type": "cover_sheet",
    }


def _summarize_dims(item: FurnitureItem) -> str:
    """Pick the 2-3 most relevant dimensions for the summary table."""
    dims = item.all_dimensions
    if not dims:
        return "—"

    # Priority keys by type
    priority_keys = {
        "bench": ["width", "seat_depth", "seat_height", "back_height"],
        "window": ["width", "height", "drop"],
        "chair": ["width", "depth", "height", "seat_height"],
        "sofa": ["width", "depth", "height"],
        "cushion": ["width", "depth", "thickness"],
        "headboard": ["width", "height"],
        "millwork": ["width", "height", "depth"],
        "table": ["width", "depth", "height"],
    }

    keys = priority_keys.get(item.item_type, list(dims.keys())[:3])
    parts = []
    for k in keys:
        if k in dims and len(parts) < 3:
            parts.append(f"{k}: {dims[k]}")

    # If we didn't find priority keys, use whatever is available
    if not parts:
        for k, v in list(dims.items())[:3]:
            parts.append(f"{k}: {v}")

    return ", ".join(parts) if parts else "—"


def _truncate(s: str, max_len: int) -> str:
    """Truncate string with ellipsis."""
    if not s:
        return ""
    return s[:max_len - 1] + "…" if len(s) > max_len else s


# ============================================================
# FABRICATION DATA
# ============================================================

CNC_MAX_X = 29  # inches max CNC bed travel
TILE_OVERLAP = 0.5  # inches overlap between tiles


def get_fabrication_data(item: FurnitureItem) -> dict:
    """Generate fabrication/cut data for an item.

    Returns CNC routing info, material estimates, and cut lists.
    Only meaningful for bench, cushion, and millwork items.
    """
    t = item.item_type
    dims = item.all_dimensions

    fab = {
        "item_id": item.id,
        "item_type": t,
        "name": item.name,
        "cut_method": "SAW",  # default
        "parts": [],
        "material_estimate": {},
        "notes": "",
    }

    if t == "bench":
        fab = _bench_fabrication(item, fab)
    elif t == "cushion":
        fab = _cushion_fabrication(item, fab)
    elif t == "millwork":
        fab = _millwork_fabrication(item, fab)

    return fab


def _bench_fabrication(item: FurnitureItem, fab: dict) -> dict:
    """Generate bench fabrication data — seat platform, back panel, cushion cuts."""
    width = item.dim_inches("width", 120)
    depth = item.dim_inches("seat_depth", 20)
    back_h = item.dim_inches("back_height", 34)
    seat_h = item.dim_inches("seat_height", 18)

    bd = item.bench_details or {}
    cushion_width = bd.get("cushion_width", 24)
    cushion_count = math.ceil(width / cushion_width) if cushion_width > 0 else 1

    # Seat platform
    seat_part = {
        "name": "Seat Platform",
        "width": width,
        "depth": depth,
        "material": "3/4\" plywood",
        "cut_method": "CNC" if width <= CNC_MAX_X and depth <= CNC_MAX_X else "SAW",
        "qty": 1,
    }
    if width > CNC_MAX_X:
        seat_part["cut_method"] = "CNC_TILE" if depth <= CNC_MAX_X else "SAW"
        seat_part["tiles"] = _generate_tiles(width, depth)

    fab["parts"].append(seat_part)

    # Back panel
    back_panel_h = back_h - seat_h
    back_part = {
        "name": "Back Panel",
        "width": width,
        "height": back_panel_h,
        "material": "3/4\" plywood",
        "cut_method": "CNC" if width <= CNC_MAX_X and back_panel_h <= CNC_MAX_X else "SAW",
        "qty": 1,
    }
    fab["parts"].append(back_part)

    # Cushion foam
    fab["parts"].append({
        "name": "Seat Cushion Foam",
        "width": cushion_width,
        "depth": depth,
        "thickness": 4,
        "material": "HR foam 2.0 lb",
        "qty": cushion_count,
    })

    # Material estimate
    fab["material_estimate"] = {
        "plywood_sqft": round((width * depth + width * back_panel_h) / 144, 1),
        "foam_sqft": round((cushion_width * depth * cushion_count) / 144, 1),
        "fabric_yards": round((width * (depth + back_panel_h + 12)) / (54 * 36), 1),  # 54" wide fabric
    }

    fab["cut_method"] = "CNC" if max(width, depth, back_panel_h) <= CNC_MAX_X else "SAW"
    return fab


def _cushion_fabrication(item: FurnitureItem, fab: dict) -> dict:
    """Generate cushion fabrication data."""
    width = item.dim_inches("width", 24)
    depth = item.dim_inches("depth", 24)
    thickness = item.dim_inches("thickness", 4)

    fab["parts"].append({
        "name": "Cushion Foam",
        "width": width,
        "depth": depth,
        "thickness": thickness,
        "material": "HR foam 2.0 lb",
        "qty": 1,
    })

    fab["material_estimate"] = {
        "foam_sqft": round(width * depth / 144, 1),
        "fabric_yards": round((width + thickness * 2 + 2) * (depth + thickness * 2 + 2) * 2 / (54 * 36), 1),
    }
    return fab


def _millwork_fabrication(item: FurnitureItem, fab: dict) -> dict:
    """Generate millwork fabrication data."""
    width = item.dim_inches("width", 36)
    height = item.dim_inches("height", 30)
    depth = item.dim_inches("depth", 12)

    # Side panels
    fab["parts"].append({
        "name": "Side Panel",
        "width": depth,
        "height": height,
        "material": "3/4\" hardwood plywood",
        "cut_method": "CNC" if max(depth, height) <= CNC_MAX_X else "SAW",
        "qty": 2,
    })

    # Top/bottom
    fab["parts"].append({
        "name": "Top/Bottom Panel",
        "width": width - 1.5,  # minus 2 side panels
        "depth": depth,
        "material": "3/4\" hardwood plywood",
        "cut_method": "CNC" if max(width - 1.5, depth) <= CNC_MAX_X else "SAW",
        "qty": 2,
    })

    # Back
    fab["parts"].append({
        "name": "Back Panel",
        "width": width - 1.5,
        "height": height - 1.5,
        "material": "1/4\" hardwood plywood",
        "qty": 1,
    })

    fab["material_estimate"] = {
        "plywood_3_4_sqft": round((2 * depth * height + 2 * (width - 1.5) * depth) / 144, 1),
        "plywood_1_4_sqft": round(((width - 1.5) * (height - 1.5)) / 144, 1),
    }

    fab["cut_method"] = "CNC" if max(width, height, depth) <= CNC_MAX_X else "SAW"
    return fab


def _generate_tiles(width: float, depth: float) -> list[dict]:
    """Split a part that exceeds CNC bed into tiles with overlap."""
    tiles = []
    x = 0
    tile_num = 1
    while x < width:
        tile_w = min(CNC_MAX_X, width - x)
        tiles.append({
            "tile": tile_num,
            "x_start": round(x, 2),
            "x_end": round(x + tile_w, 2),
            "width": round(tile_w, 2),
            "depth": round(depth, 2),
        })
        x += tile_w - TILE_OVERLAP
        tile_num += 1
        if tile_w < CNC_MAX_X:
            break
    return tiles


# ============================================================
# FABRIC INTEGRATION
# ============================================================

def enrich_with_fabric(items: list[FurnitureItem]) -> list[dict]:
    """Look up fabric inventory for each item's fabric_notes.

    Queries the Empire database for matching fabrics and returns
    enrichment data (available stock, price/yard, vendor).
    """
    enriched = []
    for item in items:
        entry = {
            "item_id": item.id,
            "fabric_notes": item.fabric_notes,
            "fabric_match": None,
        }

        if item.fabric_notes:
            try:
                from app.db.database import get_db, dict_rows
                db = get_db()
                # Search fabrics table for matching keywords
                keywords = item.fabric_notes.lower().split()
                for kw in keywords:
                    if len(kw) < 3:
                        continue
                    rows = dict_rows(db.execute(
                        "SELECT * FROM fabrics WHERE name LIKE ? OR vendor LIKE ? OR pattern LIKE ? LIMIT 3",
                        (f"%{kw}%", f"%{kw}%", f"%{kw}%"),
                    ))
                    if rows:
                        entry["fabric_match"] = rows
                        break
            except Exception as e:
                log.debug(f"Fabric lookup failed for item {item.id}: {e}")

        enriched.append(entry)

    return enriched


# ============================================================
# MULTI-PAGE PDF EXPORT
# ============================================================

def analysis_to_pdf(result: AnalysisResult, output_path: str = "") -> str:
    """Convert all drawings from an analysis to a multi-page PDF.

    Returns the output file path.
    """
    from app.services.vision.bench_renderer import drawings_to_pdf

    if not output_path:
        output_path = os.path.join(
            tempfile.gettempdir(),
            f"furniture_analysis_{result.total_items}_items.pdf",
        )

    drawing_list = []
    for d in result.drawings:
        if "svg" in d:
            drawing_list.append({
                "name": d.get("name", "Drawing"),
                "svg": d["svg"],
                "lf": 0,
            })

    if drawing_list:
        drawings_to_pdf(drawing_list, output_path)

    return output_path
