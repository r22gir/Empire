"""
Custom Shape Builder API — non-standard upholstery pieces.
L-shaped benches, U-shaped booths, curved banquettes, and more.
Provides presets, geometry calculation with SVG generation, and save/load via saved_patterns table.
"""
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import Optional, List
import json
import math
import logging

from app.db.database import get_db, dict_row, dict_rows

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/custom-shapes", tags=["custom-shapes"])

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SHAPE PRESETS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SHAPE_PRESETS = {
    "straight_bench": {
        "label": "Straight Bench",
        "dimensions": {
            "length": 48.0,
            "depth": 20.0,
            "height": 4.0,
            "seatback": False,
            "cushion_count": 1,
        },
    },
    "l_bench": {
        "label": "L-Shaped Bench",
        "dimensions": {
            "length_a": 60.0,
            "length_b": 48.0,
            "depth": 20.0,
            "height": 4.0,
            "corner_type": "square",
            "seatback_a": False,
            "seatback_b": False,
            "cushion_count_a": 1,
            "cushion_count_b": 1,
        },
    },
    "u_booth": {
        "label": "U-Shaped Booth",
        "dimensions": {
            "length_a": 48.0,
            "length_b": 60.0,
            "length_c": 48.0,
            "depth": 20.0,
            "height": 4.0,
            "cushion_count_a": 1,
            "cushion_count_b": 1,
            "cushion_count_c": 1,
        },
    },
    "curved_banquette": {
        "label": "Curved Banquette",
        "dimensions": {
            "radius": 48.0,
            "arc_degrees": 120.0,
            "depth": 20.0,
            "height": 4.0,
            "cushion_count": 1,
        },
    },
    "semicircle": {
        "label": "Semicircle Bench",
        "dimensions": {
            "diameter": 48.0,
            "height": 4.0,
            "cushion_count": 1,
        },
    },
    "round_ottoman": {
        "label": "Round Ottoman",
        "dimensions": {
            "diameter": 36.0,
            "height": 4.0,
        },
    },
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# REQUEST / RESPONSE MODELS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class CalculateRequest(BaseModel):
    shape_type: str
    dimensions: dict


class SaveShapeRequest(BaseModel):
    name: str
    shape_type: str
    dimensions: dict
    customer_id: Optional[str] = None
    job_id: Optional[str] = None
    notes: str = ""


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# GEOMETRY CALCULATORS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

FABRIC_WIDTH = 54  # standard upholstery fabric width in inches
SEAM_ALLOWANCE = 0.5  # inches per seam


def _fabric_yardage(surface_sq_in: float) -> float:
    """Estimate fabric yardage from surface area (inches²) on 54″ fabric, with seam allowance."""
    # Add ~15% for seam allowances and waste
    adjusted = surface_sq_in * 1.15
    linear_inches = adjusted / FABRIC_WIDTH
    return round(linear_inches / 36, 2)


def _calc_straight_bench(dims: dict) -> dict:
    length = dims.get("length", 48)
    depth = dims.get("depth", 20)
    height = dims.get("height", 4)
    cushion_count = dims.get("cushion_count", 1)

    area = length * depth
    perimeter = 2 * (length + depth)
    # Surface area: top + bottom + 4 sides (boxing)
    boxing_area = perimeter * height
    total_surface = 2 * area + boxing_area

    pieces = [
        {"name": "Top panel", "width": length, "height": depth, "quantity": 1, "notes": "Main seat surface"},
        {"name": "Bottom panel", "width": length, "height": depth, "quantity": 1, "notes": "Underside"},
        {"name": "Front boxing", "width": length, "height": height, "quantity": 1, "notes": "Front edge strip"},
        {"name": "Back boxing", "width": length, "height": height, "quantity": 1, "notes": "Back edge strip"},
        {"name": "Side boxing", "width": depth, "height": height, "quantity": 2, "notes": "Left and right ends"},
    ]
    if cushion_count > 1:
        pieces.append({"name": "Divider boxing", "width": depth, "height": height,
                        "quantity": cushion_count - 1, "notes": "Between cushion sections"})

    svg = _svg_straight_bench(length, depth)

    return {
        "linear_feet": round(perimeter / 12, 2),
        "square_footage": round(area / 144, 2),
        "fabric_yardage_54": _fabric_yardage(total_surface),
        "pieces": pieces,
        "svg": svg,
    }


def _calc_l_bench(dims: dict) -> dict:
    la = dims.get("length_a", 60)
    lb = dims.get("length_b", 48)
    depth = dims.get("depth", 20)
    height = dims.get("height", 4)

    # L-shape area: two rectangles minus the overlapping corner
    area = (la * depth) + (lb * depth) - (depth * depth)
    # Perimeter of L-shape (outer)
    perimeter = 2 * (la + lb) - 2 * depth + 2 * depth  # simplifies to 2*(la+lb)
    # More accurately: outer walk around L
    perimeter = la + depth + (la - depth) + (lb - depth) + lb + depth
    # = la + depth + la - depth + lb - depth + lb + depth = 2*la + 2*lb
    # But inner corner adds two segments
    perimeter = 2 * la + 2 * lb  # outer perimeter of L footprint

    boxing_area = perimeter * height
    total_surface = 2 * area + boxing_area

    pieces = [
        {"name": "Leg A top panel", "width": la, "height": depth, "quantity": 1, "notes": "Long arm seat surface"},
        {"name": "Leg B top panel", "width": lb - depth, "height": depth, "quantity": 1,
         "notes": "Short arm seat surface (minus corner overlap)"},
        {"name": "Leg A bottom panel", "width": la, "height": depth, "quantity": 1, "notes": "Long arm underside"},
        {"name": "Leg B bottom panel", "width": lb - depth, "height": depth, "quantity": 1, "notes": "Short arm underside"},
        {"name": "Front boxing", "width": la + lb - depth, "height": height, "quantity": 1,
         "notes": "Outer front edge (continuous or 2-piece)"},
        {"name": "Back boxing", "width": la + lb - depth, "height": height, "quantity": 1,
         "notes": "Inner/back edge"},
        {"name": "End boxing", "width": depth, "height": height, "quantity": 2, "notes": "Open ends"},
    ]

    svg = _svg_l_bench(la, lb, depth)

    return {
        "linear_feet": round(perimeter / 12, 2),
        "square_footage": round(area / 144, 2),
        "fabric_yardage_54": _fabric_yardage(total_surface),
        "pieces": pieces,
        "svg": svg,
    }


def _calc_u_booth(dims: dict) -> dict:
    la = dims.get("length_a", 48)
    lb = dims.get("length_b", 60)
    lc = dims.get("length_c", 48)
    depth = dims.get("depth", 20)
    height = dims.get("height", 4)

    # U-shape: three rectangles minus two corner overlaps
    area = (la * depth) + (lb * depth) + (lc * depth) - 2 * (depth * depth)
    perimeter = 2 * (la + lb + lc) - 4 * depth + 4 * depth  # walk around
    # Outer perimeter of U: top of left arm + across back + top of right arm + inner return
    perimeter = la + lb + lc + (la - depth) + (lb - 2 * depth) + (lc - depth) + 2 * depth
    # Simplified: 2*(la+lb+lc) - 2*depth
    perimeter = 2 * (la + lb + lc) - 2 * depth

    boxing_area = perimeter * height
    total_surface = 2 * area + boxing_area

    pieces = [
        {"name": "Left arm top", "width": la, "height": depth, "quantity": 1, "notes": "Left arm seat"},
        {"name": "Center top", "width": lb - 2 * depth, "height": depth, "quantity": 1, "notes": "Center seat"},
        {"name": "Right arm top", "width": lc, "height": depth, "quantity": 1, "notes": "Right arm seat"},
        {"name": "Left arm bottom", "width": la, "height": depth, "quantity": 1, "notes": "Left arm underside"},
        {"name": "Center bottom", "width": lb - 2 * depth, "height": depth, "quantity": 1, "notes": "Center underside"},
        {"name": "Right arm bottom", "width": lc, "height": depth, "quantity": 1, "notes": "Right arm underside"},
        {"name": "Boxing strip", "width": perimeter, "height": height, "quantity": 1,
         "notes": "Full perimeter boxing (may be cut in sections)"},
    ]

    svg = _svg_u_booth(la, lb, lc, depth)

    return {
        "linear_feet": round(perimeter / 12, 2),
        "square_footage": round(area / 144, 2),
        "fabric_yardage_54": _fabric_yardage(total_surface),
        "pieces": pieces,
        "svg": svg,
    }


def _calc_curved_banquette(dims: dict) -> dict:
    radius = dims.get("radius", 48)
    arc_deg = dims.get("arc_degrees", 120)
    depth = dims.get("depth", 20)
    height = dims.get("height", 4)

    arc_rad = arc_deg * math.pi / 180
    outer_arc = radius * arc_rad
    inner_radius = radius - depth
    inner_arc = inner_radius * arc_rad

    # Top area: annular sector
    area = 0.5 * arc_rad * (radius ** 2 - inner_radius ** 2)
    # Perimeter: outer arc + inner arc + 2 radial ends
    perimeter = outer_arc + inner_arc + 2 * depth

    boxing_area = perimeter * height
    total_surface = 2 * area + boxing_area

    pieces = [
        {"name": "Top panel (curved)", "width": round(outer_arc, 1), "height": depth, "quantity": 1,
         "notes": f"Curved seat — {arc_deg}° arc, cut from template"},
        {"name": "Bottom panel (curved)", "width": round(outer_arc, 1), "height": depth, "quantity": 1,
         "notes": "Matching underside"},
        {"name": "Outer boxing (curved)", "width": round(outer_arc, 1), "height": height, "quantity": 1,
         "notes": "Outer curved edge strip"},
        {"name": "Inner boxing (curved)", "width": round(inner_arc, 1), "height": height, "quantity": 1,
         "notes": "Inner curved edge strip"},
        {"name": "End boxing", "width": depth, "height": height, "quantity": 2, "notes": "Radial end caps"},
    ]

    svg = _svg_curved_banquette(radius, arc_deg, depth)

    return {
        "linear_feet": round(perimeter / 12, 2),
        "square_footage": round(area / 144, 2),
        "fabric_yardage_54": _fabric_yardage(total_surface),
        "pieces": pieces,
        "svg": svg,
    }


def _calc_semicircle(dims: dict) -> dict:
    diameter = dims.get("diameter", 48)
    height = dims.get("height", 4)
    radius = diameter / 2

    area = 0.5 * math.pi * radius ** 2
    # Perimeter: half-circle arc + diameter straight edge
    arc = math.pi * radius
    perimeter = arc + diameter

    boxing_area = perimeter * height
    total_surface = 2 * area + boxing_area

    pieces = [
        {"name": "Semicircle top", "width": diameter, "height": radius, "quantity": 1,
         "notes": "Semicircular seat — cut from template"},
        {"name": "Semicircle bottom", "width": diameter, "height": radius, "quantity": 1,
         "notes": "Matching underside"},
        {"name": "Curved boxing", "width": round(arc, 1), "height": height, "quantity": 1,
         "notes": "Curved outer edge strip"},
        {"name": "Straight boxing", "width": diameter, "height": height, "quantity": 1,
         "notes": "Flat back edge strip"},
    ]

    svg = _svg_semicircle(diameter)

    return {
        "linear_feet": round(perimeter / 12, 2),
        "square_footage": round(area / 144, 2),
        "fabric_yardage_54": _fabric_yardage(total_surface),
        "pieces": pieces,
        "svg": svg,
    }


def _calc_round_ottoman(dims: dict) -> dict:
    diameter = dims.get("diameter", 36)
    height = dims.get("height", 4)
    radius = diameter / 2

    area = math.pi * radius ** 2
    circumference = math.pi * diameter
    perimeter = circumference

    boxing_area = circumference * height
    total_surface = 2 * area + boxing_area

    pieces = [
        {"name": "Circle top", "width": diameter, "height": diameter, "quantity": 1,
         "notes": "Round top — cut as circle"},
        {"name": "Circle bottom", "width": diameter, "height": diameter, "quantity": 1,
         "notes": "Round bottom — cut as circle"},
        {"name": "Boxing strip", "width": round(circumference, 1), "height": height, "quantity": 1,
         "notes": "Full circumference band"},
    ]

    svg = _svg_round_ottoman(diameter)

    return {
        "linear_feet": round(perimeter / 12, 2),
        "square_footage": round(area / 144, 2),
        "fabric_yardage_54": _fabric_yardage(total_surface),
        "pieces": pieces,
        "svg": svg,
    }


CALCULATORS = {
    "straight_bench": _calc_straight_bench,
    "l_bench": _calc_l_bench,
    "u_booth": _calc_u_booth,
    "curved_banquette": _calc_curved_banquette,
    "semicircle": _calc_semicircle,
    "round_ottoman": _calc_round_ottoman,
}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SVG GENERATORS (top-down views with dimension annotations)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

SVG_STYLE = 'fill="none" stroke="#333" stroke-width="1"'
LABEL_STYLE = 'font-family="Arial, sans-serif" font-size="12" fill="#333" text-anchor="middle"'
DIM_LINE_STYLE = 'stroke="#999" stroke-width="0.5" stroke-dasharray="4,2"'

MARGIN = 30  # margin around shape for dimension labels


def _svg_wrap(content: str, width: float, height: float) -> str:
    vw = width + 2 * MARGIN
    vh = height + 2 * MARGIN
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {vw} {vh}" '
        f'width="{vw}" height="{vh}">'
        f'{content}</svg>'
    )


def _dim_h(x1: float, x2: float, y: float, label: str) -> str:
    """Horizontal dimension line with label."""
    mx = (x1 + x2) / 2
    return (
        f'<line x1="{x1}" y1="{y}" x2="{x2}" y2="{y}" {DIM_LINE_STYLE}/>'
        f'<line x1="{x1}" y1="{y - 3}" x2="{x1}" y2="{y + 3}" {DIM_LINE_STYLE}/>'
        f'<line x1="{x2}" y1="{y - 3}" x2="{x2}" y2="{y + 3}" {DIM_LINE_STYLE}/>'
        f'<text x="{mx}" y="{y - 5}" {LABEL_STYLE}>{label}</text>'
    )


def _dim_v(x: float, y1: float, y2: float, label: str) -> str:
    """Vertical dimension line with label."""
    my = (y1 + y2) / 2
    return (
        f'<line x1="{x}" y1="{y1}" x2="{x}" y2="{y2}" {DIM_LINE_STYLE}/>'
        f'<line x1="{x - 3}" y1="{y1}" x2="{x + 3}" y2="{y1}" {DIM_LINE_STYLE}/>'
        f'<line x1="{x - 3}" y1="{y2}" x2="{x + 3}" y2="{y2}" {DIM_LINE_STYLE}/>'
        f'<text x="{x - 10}" y="{my + 4}" {LABEL_STYLE} text-anchor="end">{label}</text>'
    )


def _svg_straight_bench(length: float, depth: float) -> str:
    ox, oy = MARGIN, MARGIN
    body = (
        f'<rect x="{ox}" y="{oy}" width="{length}" height="{depth}" {SVG_STYLE} fill="#f0ebe3"/>'
        + _dim_h(ox, ox + length, oy + depth + 18, f'{length}"')
        + _dim_v(ox - 15, oy, oy + depth, f'{depth}"')
    )
    return _svg_wrap(body, length, depth)


def _svg_l_bench(la: float, lb: float, depth: float) -> str:
    ox, oy = MARGIN, MARGIN
    # L-shape: leg A goes right, leg B goes down. Corner at top-right area.
    # Draw as polygon
    points = (
        f"{ox},{oy} "
        f"{ox + la},{oy} "
        f"{ox + la},{oy + lb} "
        f"{ox + la - depth},{oy + lb} "
        f"{ox + la - depth},{oy + depth} "
        f"{ox},{oy + depth}"
    )
    body = (
        f'<polygon points="{points}" {SVG_STYLE} fill="#f0ebe3"/>'
        # Dimension: length_a across top
        + _dim_h(ox, ox + la, oy - 15, f'{la}" (A)')
        # Dimension: length_b down right side
        + _dim_v(ox + la + 15, oy, oy + lb, f'{lb}" (B)')
        # Dimension: depth on left
        + _dim_v(ox - 15, oy, oy + depth, f'{depth}"')
    )
    total_w = la
    total_h = lb
    return _svg_wrap(body, total_w, total_h)


def _svg_u_booth(la: float, lb: float, lc: float, depth: float) -> str:
    ox, oy = MARGIN, MARGIN
    # U-shape: left arm down, center across bottom, right arm up
    points = (
        f"{ox},{oy} "
        f"{ox + depth},{oy} "
        f"{ox + depth},{oy + la - depth} "
        f"{ox + lb - depth},{oy + lc - depth} "
        f"{ox + lb - depth},{oy} "
        f"{ox + lb},{oy} "
        f"{ox + lb},{oy + lc} "
        f"{ox},{oy + la}"
    )
    body = (
        f'<polygon points="{points}" {SVG_STYLE} fill="#f0ebe3"/>'
        # Dim: lb across top
        + _dim_h(ox, ox + lb, oy - 15, f'{lb}" (B)')
        # Dim: la on left
        + _dim_v(ox - 15, oy, oy + la, f'{la}" (A)')
        # Dim: lc on right
        + _dim_v(ox + lb + 15, oy, oy + lc, f'{lc}" (C)')
        # Dim: depth
        + _dim_h(ox, ox + depth, oy + max(la, lc) + 18, f'{depth}"')
    )
    total_w = lb
    total_h = max(la, lc)
    return _svg_wrap(body, total_w, total_h)


def _svg_curved_banquette(radius: float, arc_deg: float, depth: float) -> str:
    inner_r = radius - depth
    arc_rad = arc_deg * math.pi / 180

    # Center the arc, opening downward. Start angle to end angle centered.
    # We'll place the center at (radius + MARGIN, radius + MARGIN)
    cx = radius + MARGIN
    cy = radius + MARGIN

    start_angle = math.pi / 2 - arc_rad / 2
    end_angle = math.pi / 2 + arc_rad / 2

    def polar(r, angle):
        return (cx + r * math.cos(angle), cy - r * math.sin(angle))

    # Outer arc: start to end
    o_start = polar(radius, start_angle)
    o_end = polar(radius, end_angle)
    # Inner arc: end to start (reverse)
    i_start = polar(inner_r, end_angle)
    i_end = polar(inner_r, start_angle)

    large_arc = 1 if arc_deg > 180 else 0

    path = (
        f'M {o_start[0]},{o_start[1]} '
        f'A {radius},{radius} 0 {large_arc},1 {o_end[0]},{o_end[1]} '
        f'L {i_start[0]},{i_start[1]} '
        f'A {inner_r},{inner_r} 0 {large_arc},0 {i_end[0]},{i_end[1]} '
        f'Z'
    )

    # Label at midpoint of outer arc
    mid_angle = math.pi / 2
    label_pt = polar(radius + 15, mid_angle)
    inner_label_pt = polar(inner_r - 15, mid_angle)
    arc_len = round(radius * arc_rad, 1)

    body = (
        f'<path d="{path}" {SVG_STYLE} fill="#f0ebe3"/>'
        f'<text x="{label_pt[0]}" y="{label_pt[1]}" {LABEL_STYLE}>R={radius}"</text>'
        f'<text x="{cx}" y="{cy + 5}" {LABEL_STYLE}>{arc_deg}°</text>'
        f'<text x="{inner_label_pt[0]}" y="{inner_label_pt[1]}" {LABEL_STYLE}>{depth}" deep</text>'
    )

    vw = 2 * radius
    vh = 2 * radius
    return _svg_wrap(body, vw, vh)


def _svg_semicircle(diameter: float) -> str:
    r = diameter / 2
    ox = MARGIN
    oy = MARGIN + r

    # Semicircle: flat edge at top, arc below
    path = (
        f'M {ox},{oy} '
        f'A {r},{r} 0 0,0 {ox + diameter},{oy} '
        f'L {ox},{oy}'
    )

    body = (
        f'<path d="{path}" {SVG_STYLE} fill="#f0ebe3"/>'
        + _dim_h(ox, ox + diameter, oy - r - 15, f'{diameter}"')
        # Radius annotation
        + f'<line x1="{ox + r}" y1="{oy}" x2="{ox + r}" y2="{oy + r}" {DIM_LINE_STYLE}/>'
        + f'<text x="{ox + r + 10}" y="{oy + r / 2 + 4}" {LABEL_STYLE} text-anchor="start">R={r}"</text>'
    )

    return _svg_wrap(body, diameter, r)


def _svg_round_ottoman(diameter: float) -> str:
    r = diameter / 2
    cx = MARGIN + r
    cy = MARGIN + r

    body = (
        f'<circle cx="{cx}" cy="{cy}" r="{r}" {SVG_STYLE} fill="#f0ebe3"/>'
        # Diameter line across
        + f'<line x1="{cx - r}" y1="{cy}" x2="{cx + r}" y2="{cy}" {DIM_LINE_STYLE}/>'
        + f'<text x="{cx}" y="{cy - 5}" {LABEL_STYLE}>{diameter}"</text>'
    )

    return _svg_wrap(body, diameter, diameter)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# ROUTES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

@router.get("/presets")
async def get_presets():
    """Return the 6 shape presets with default dimensions."""
    return SHAPE_PRESETS


@router.post("/calculate")
async def calculate_shape(req: CalculateRequest):
    """Calculate geometry, fabric estimates, cut list, and SVG for a custom shape."""
    calc_fn = CALCULATORS.get(req.shape_type)
    if not calc_fn:
        raise HTTPException(
            400,
            f"Unknown shape_type: {req.shape_type}. Must be one of: {list(CALCULATORS.keys())}",
        )
    try:
        result = calc_fn(req.dimensions)
    except Exception as e:
        logger.exception("Shape calculation failed")
        raise HTTPException(400, f"Calculation error for {req.shape_type}: {e}")
    return {"shape_type": req.shape_type, "dimensions": req.dimensions, **result}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SAVED CUSTOM SHAPES — CRUD (reuses saved_patterns table)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _row_to_shape(row: dict) -> dict:
    """Convert a DB row to an API-friendly dict, parsing JSON fields."""
    if not row:
        return None
    out = dict(row)
    if out.get("dimensions_json"):
        out["dimensions"] = json.loads(out["dimensions_json"])
    else:
        out["dimensions"] = {}
    if out.get("result_json"):
        out["result"] = json.loads(out["result_json"])
    else:
        out["result"] = None
    out.pop("dimensions_json", None)
    out.pop("result_json", None)
    return out


@router.post("/save")
async def save_shape(req: SaveShapeRequest):
    """Save a custom shape to the database. Calculates result and stores everything."""
    calc_fn = CALCULATORS.get(req.shape_type)
    if not calc_fn:
        raise HTTPException(
            400,
            f"Unknown shape_type: {req.shape_type}. Must be one of: {list(CALCULATORS.keys())}",
        )
    try:
        result = calc_fn(req.dimensions)
    except Exception as e:
        raise HTTPException(400, f"Calculation error for {req.shape_type}: {e}")

    dimensions_json = json.dumps(req.dimensions)
    result_json = json.dumps(result)

    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO saved_patterns (name, shape_type, dimensions_json, result_json,
               customer_id, job_id, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (req.name, req.shape_type, dimensions_json, result_json,
             req.customer_id, req.job_id, req.notes),
        )
        row = conn.execute(
            "SELECT * FROM saved_patterns WHERE rowid = ?", (cursor.lastrowid,)
        ).fetchone()
        return _row_to_shape(dict_row(row))


@router.get("/saved")
async def list_saved_shapes(
    shape_type: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """List saved custom shapes with optional filters. Only returns custom shape types."""
    custom_types = list(CALCULATORS.keys())
    placeholders = ",".join("?" * len(custom_types))

    query = f"SELECT * FROM saved_patterns WHERE deleted_at IS NULL AND shape_type IN ({placeholders})"
    params: list = list(custom_types)

    if shape_type:
        query += " AND shape_type = ?"
        params.append(shape_type)
    if customer_id:
        query += " AND customer_id = ?"
        params.append(customer_id)
    if job_id:
        query += " AND job_id = ?"
        params.append(job_id)
    if search:
        query += " AND (name LIKE ? OR notes LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like])

    query += " ORDER BY updated_at DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_row_to_shape(r) for r in dict_rows(rows)]


@router.get("/saved/{shape_id}")
async def get_saved_shape(shape_id: str):
    """Get a single saved custom shape by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM saved_patterns WHERE id = ? AND deleted_at IS NULL",
            (shape_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Saved custom shape not found")
    return _row_to_shape(dict_row(row))


@router.delete("/saved/{shape_id}")
async def delete_saved_shape(shape_id: str):
    """Soft-delete a saved custom shape."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM saved_patterns WHERE id = ? AND deleted_at IS NULL",
            (shape_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Saved custom shape not found")
        conn.execute(
            "UPDATE saved_patterns SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
            (shape_id,),
        )
    return {"status": "deleted", "id": shape_id}
