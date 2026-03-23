"""
Pattern Template Generator API — mathematically accurate sewing patterns.
Generates interactive previews and printable PDF templates.
Includes saved pattern template CRUD for persistent storage.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional, List
import json
import logging

from app.db.database import get_db, dict_row, dict_rows

logger = logging.getLogger(__name__)
router = APIRouter(tags=["patterns"])


class SphereRequest(BaseModel):
    diameter: float = 9.39
    circumference: Optional[float] = None  # Alternative input
    num_gores: int = 8
    seam_allowance: float = 0.5
    pillow_cover: bool = False
    pillow_reduction: float = 0.5
    project_name: str = ""


class CylinderRequest(BaseModel):
    diameter: float = 6.0
    length: float = 18.0
    seam_allowance: float = 0.5
    end_cap_style: str = "flat"  # flat, gathered, piped
    zipper: bool = True
    piping: bool = False
    project_name: str = ""


class BoxCushionRequest(BaseModel):
    width: float = 20.0
    depth: float = 20.0
    thickness: float = 4.0
    seam_allowance: float = 0.5
    corner_radius: float = 0.0
    zipper_in_back: bool = True
    welt: bool = False
    t_cushion: bool = False
    t_arm_width: float = 6.0
    t_arm_depth: float = 4.0
    project_name: str = ""


class KnifeEdgeRequest(BaseModel):
    width: float = 18.0
    height: float = 18.0
    shape: str = "square"  # square, rectangle, round, oval
    seam_allowance: float = 0.5
    zipper: bool = True
    project_name: str = ""


@router.get("/shapes")
async def list_shapes():
    """List available pattern shapes with descriptions."""
    return [
        {
            "id": "sphere", "name": "Sphere (Gore Panels)",
            "description": "Ball/sphere from gore panels — pillows, poufs, decorative balls",
            "icon": "circle",
            "inputs": ["diameter", "num_gores", "seam_allowance", "pillow_cover"],
        },
        {
            "id": "cylinder", "name": "Cylinder (Bolster)",
            "description": "Bolster pillows, neckrolls, arm rolls — tube with end caps",
            "icon": "cylinder",
            "inputs": ["diameter", "length", "seam_allowance", "end_cap_style", "zipper"],
        },
        {
            "id": "box_cushion", "name": "Box Cushion",
            "description": "Seat cushions, bench cushions — top/bottom panels with boxing strip",
            "icon": "square",
            "inputs": ["width", "depth", "thickness", "seam_allowance", "corner_radius", "zipper_in_back", "welt", "t_cushion"],
        },
        {
            "id": "knife_edge", "name": "Knife Edge Cushion",
            "description": "Throw pillows, flat cushions — two panels sewn together",
            "icon": "minimize-2",
            "inputs": ["width", "height", "shape", "seam_allowance", "zipper"],
        },
    ]


@router.post("/sphere")
async def create_sphere_pattern(req: SphereRequest):
    """Generate sphere gore pattern."""
    import math
    from app.services.pattern_generator import generate_sphere, result_to_dict

    diameter = req.diameter
    if req.circumference and not req.diameter:
        diameter = req.circumference / math.pi
    elif req.circumference:
        diameter = req.circumference / math.pi

    if diameter <= 0 or diameter > 100:
        raise HTTPException(400, "Diameter must be between 0 and 100 inches")
    if req.num_gores not in (4, 6, 8, 10, 12):
        raise HTTPException(400, "Number of gores must be 4, 6, 8, 10, or 12")

    result = generate_sphere(
        diameter=diameter,
        num_gores=req.num_gores,
        seam_allowance=req.seam_allowance,
        pillow_cover=req.pillow_cover,
        pillow_reduction=req.pillow_reduction,
    )
    return result_to_dict(result)


@router.post("/sphere/pdf")
async def sphere_pdf(req: SphereRequest):
    """Generate printable PDF for sphere pattern."""
    import math
    from app.services.pattern_generator import generate_sphere, generate_pdf

    diameter = req.diameter
    if req.circumference:
        diameter = req.circumference / math.pi

    result = generate_sphere(
        diameter=diameter, num_gores=req.num_gores,
        seam_allowance=req.seam_allowance, pillow_cover=req.pillow_cover,
        pillow_reduction=req.pillow_reduction,
    )
    pdf_bytes = generate_pdf(result, req.project_name)
    return Response(content=pdf_bytes, media_type="application/pdf",
                   headers={"Content-Disposition": f'attachment; filename="sphere_pattern_{req.num_gores}gore.pdf"'})


@router.post("/cylinder")
async def create_cylinder_pattern(req: CylinderRequest):
    """Generate cylinder/bolster pattern."""
    from app.services.pattern_generator import generate_cylinder, result_to_dict

    if req.diameter <= 0 or req.diameter > 100:
        raise HTTPException(400, "Diameter must be between 0 and 100 inches")
    if req.length <= 0 or req.length > 200:
        raise HTTPException(400, "Length must be between 0 and 200 inches")

    result = generate_cylinder(
        diameter=req.diameter, length=req.length,
        seam_allowance=req.seam_allowance, end_cap_style=req.end_cap_style,
        zipper=req.zipper, piping=req.piping,
    )
    return result_to_dict(result)


@router.post("/cylinder/pdf")
async def cylinder_pdf(req: CylinderRequest):
    """Generate printable PDF for cylinder pattern."""
    from app.services.pattern_generator import generate_cylinder, generate_pdf

    result = generate_cylinder(
        diameter=req.diameter, length=req.length,
        seam_allowance=req.seam_allowance, end_cap_style=req.end_cap_style,
        zipper=req.zipper, piping=req.piping,
    )
    pdf_bytes = generate_pdf(result, req.project_name)
    return Response(content=pdf_bytes, media_type="application/pdf",
                   headers={"Content-Disposition": f'attachment; filename="bolster_pattern.pdf"'})


@router.post("/box-cushion")
async def create_box_cushion_pattern(req: BoxCushionRequest):
    """Generate box cushion pattern."""
    from app.services.pattern_generator import generate_box_cushion, result_to_dict

    if req.width <= 0 or req.depth <= 0 or req.thickness <= 0:
        raise HTTPException(400, "All dimensions must be positive")

    result = generate_box_cushion(
        width=req.width, depth=req.depth, thickness=req.thickness,
        seam_allowance=req.seam_allowance, corner_radius=req.corner_radius,
        zipper_in_back=req.zipper_in_back, welt=req.welt,
        t_cushion=req.t_cushion, t_arm_width=req.t_arm_width, t_arm_depth=req.t_arm_depth,
    )
    return result_to_dict(result)


@router.post("/box-cushion/pdf")
async def box_cushion_pdf(req: BoxCushionRequest):
    """Generate printable PDF for box cushion pattern."""
    from app.services.pattern_generator import generate_box_cushion, generate_pdf

    result = generate_box_cushion(
        width=req.width, depth=req.depth, thickness=req.thickness,
        seam_allowance=req.seam_allowance, corner_radius=req.corner_radius,
        zipper_in_back=req.zipper_in_back, welt=req.welt,
        t_cushion=req.t_cushion, t_arm_width=req.t_arm_width, t_arm_depth=req.t_arm_depth,
    )
    pdf_bytes = generate_pdf(result, req.project_name)
    return Response(content=pdf_bytes, media_type="application/pdf",
                   headers={"Content-Disposition": f'attachment; filename="box_cushion_pattern.pdf"'})


@router.post("/knife-edge")
async def create_knife_edge_pattern(req: KnifeEdgeRequest):
    """Generate knife edge cushion pattern."""
    from app.services.pattern_generator import generate_knife_edge, result_to_dict

    result = generate_knife_edge(
        width=req.width, height=req.height, shape=req.shape,
        seam_allowance=req.seam_allowance, zipper=req.zipper,
    )
    return result_to_dict(result)


@router.post("/knife-edge/pdf")
async def knife_edge_pdf(req: KnifeEdgeRequest):
    """Generate printable PDF for knife edge cushion pattern."""
    from app.services.pattern_generator import generate_knife_edge, generate_pdf

    result = generate_knife_edge(
        width=req.width, height=req.height, shape=req.shape,
        seam_allowance=req.seam_allowance, zipper=req.zipper,
    )
    pdf_bytes = generate_pdf(result, req.project_name)
    return Response(content=pdf_bytes, media_type="application/pdf",
                   headers={"Content-Disposition": f'attachment; filename="knife_edge_pattern.pdf"'})


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# SAVED PATTERN TEMPLATES — CRUD
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

from app.services.pattern_generator import (
    generate_sphere, generate_cylinder, generate_box_cushion,
    generate_knife_edge, generate_pdf, result_to_dict,
)

GENERATORS = {
    "sphere": generate_sphere,
    "cylinder": generate_cylinder,
    "box_cushion": generate_box_cushion,
    "knife_edge": generate_knife_edge,
}


class SavePatternRequest(BaseModel):
    name: str
    shape_type: str  # sphere, cylinder, box_cushion, knife_edge
    dimensions: dict  # the input params (diameter, num_gores, etc.)
    customer_id: Optional[str] = None
    job_id: Optional[str] = None
    quote_id: Optional[str] = None
    notes: str = ""


class UpdatePatternRequest(BaseModel):
    name: Optional[str] = None
    customer_id: Optional[str] = None
    job_id: Optional[str] = None
    quote_id: Optional[str] = None
    notes: Optional[str] = None
    dimensions: Optional[dict] = None


def _generate_result_json(shape_type: str, dimensions: dict) -> str:
    """Generate pattern result from shape_type + dimensions, return as JSON string."""
    gen_fn = GENERATORS.get(shape_type)
    if not gen_fn:
        raise HTTPException(400, f"Unknown shape_type: {shape_type}. Must be one of: {list(GENERATORS.keys())}")
    try:
        result = gen_fn(**dimensions)
        return json.dumps(result_to_dict(result))
    except TypeError as e:
        raise HTTPException(400, f"Invalid dimensions for {shape_type}: {e}")


def _row_to_pattern(row: dict) -> dict:
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
    # Remove raw JSON columns from response
    out.pop("dimensions_json", None)
    out.pop("result_json", None)
    return out


@router.post("/save")
async def save_pattern(req: SavePatternRequest):
    """Save a pattern template. Generates the pattern result and stores everything."""
    result_json = _generate_result_json(req.shape_type, req.dimensions)
    dimensions_json = json.dumps(req.dimensions)

    with get_db() as conn:
        cursor = conn.execute(
            """INSERT INTO saved_patterns (name, shape_type, dimensions_json, result_json,
               customer_id, job_id, quote_id, notes)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (req.name, req.shape_type, dimensions_json, result_json,
             req.customer_id, req.job_id, req.quote_id, req.notes),
        )
        # Fetch the created row
        row = conn.execute(
            "SELECT * FROM saved_patterns WHERE rowid = ?", (cursor.lastrowid,)
        ).fetchone()
        return _row_to_pattern(dict_row(row))


@router.get("/saved")
async def list_saved_patterns(
    shape_type: Optional[str] = Query(None),
    customer_id: Optional[str] = Query(None),
    job_id: Optional[str] = Query(None),
    quote_id: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
):
    """List saved pattern templates with optional filters."""
    query = "SELECT * FROM saved_patterns WHERE deleted_at IS NULL"
    params: list = []

    if shape_type:
        query += " AND shape_type = ?"
        params.append(shape_type)
    if customer_id:
        query += " AND customer_id = ?"
        params.append(customer_id)
    if job_id:
        query += " AND job_id = ?"
        params.append(job_id)
    if quote_id:
        query += " AND quote_id = ?"
        params.append(quote_id)
    if search:
        query += " AND (name LIKE ? OR notes LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like])

    query += " ORDER BY updated_at DESC"

    with get_db() as conn:
        rows = conn.execute(query, params).fetchall()
        return [_row_to_pattern(r) for r in dict_rows(rows)]


@router.get("/saved/{pattern_id}")
async def get_saved_pattern(pattern_id: str):
    """Get a single saved pattern template by ID."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM saved_patterns WHERE id = ? AND deleted_at IS NULL",
            (pattern_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Saved pattern not found")
    return _row_to_pattern(dict_row(row))


@router.put("/saved/{pattern_id}")
async def update_saved_pattern(pattern_id: str, req: UpdatePatternRequest):
    """Update a saved pattern template. Re-generates result if dimensions changed."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM saved_patterns WHERE id = ? AND deleted_at IS NULL",
            (pattern_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Saved pattern not found")
        existing = dict_row(existing)

        updates = []
        params = []

        if req.name is not None:
            updates.append("name = ?")
            params.append(req.name)
        if req.customer_id is not None:
            updates.append("customer_id = ?")
            params.append(req.customer_id)
        if req.job_id is not None:
            updates.append("job_id = ?")
            params.append(req.job_id)
        if req.quote_id is not None:
            updates.append("quote_id = ?")
            params.append(req.quote_id)
        if req.notes is not None:
            updates.append("notes = ?")
            params.append(req.notes)
        if req.dimensions is not None:
            shape_type = existing["shape_type"]
            result_json = _generate_result_json(shape_type, req.dimensions)
            updates.append("dimensions_json = ?")
            params.append(json.dumps(req.dimensions))
            updates.append("result_json = ?")
            params.append(result_json)

        if not updates:
            raise HTTPException(400, "No fields to update")

        updates.append("updated_at = CURRENT_TIMESTAMP")
        params.append(pattern_id)

        conn.execute(
            f"UPDATE saved_patterns SET {', '.join(updates)} WHERE id = ?",
            params,
        )

        row = conn.execute(
            "SELECT * FROM saved_patterns WHERE id = ?", (pattern_id,)
        ).fetchone()
        return _row_to_pattern(dict_row(row))


@router.delete("/saved/{pattern_id}")
async def delete_saved_pattern(pattern_id: str):
    """Soft-delete a saved pattern template."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT id FROM saved_patterns WHERE id = ? AND deleted_at IS NULL",
            (pattern_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Saved pattern not found")

        conn.execute(
            "UPDATE saved_patterns SET deleted_at = CURRENT_TIMESTAMP WHERE id = ?",
            (pattern_id,),
        )
    return {"status": "deleted", "id": pattern_id}


@router.post("/saved/{pattern_id}/duplicate")
async def duplicate_saved_pattern(pattern_id: str):
    """Duplicate a saved pattern template. Clears customer/job/quote links, appends ' (copy)' to name."""
    with get_db() as conn:
        existing = conn.execute(
            "SELECT * FROM saved_patterns WHERE id = ? AND deleted_at IS NULL",
            (pattern_id,),
        ).fetchone()
        if not existing:
            raise HTTPException(404, "Saved pattern not found")
        existing = dict_row(existing)

        new_name = existing["name"] + " (copy)"
        cursor = conn.execute(
            """INSERT INTO saved_patterns (name, shape_type, dimensions_json, result_json, notes)
               VALUES (?, ?, ?, ?, ?)""",
            (new_name, existing["shape_type"], existing["dimensions_json"],
             existing["result_json"], existing["notes"]),
        )
        row = conn.execute(
            "SELECT * FROM saved_patterns WHERE rowid = ?", (cursor.lastrowid,)
        ).fetchone()
        return _row_to_pattern(dict_row(row))


@router.get("/saved/{pattern_id}/pdf")
async def saved_pattern_pdf(pattern_id: str):
    """Regenerate and return PDF for a saved pattern."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM saved_patterns WHERE id = ? AND deleted_at IS NULL",
            (pattern_id,),
        ).fetchone()
    if not row:
        raise HTTPException(404, "Saved pattern not found")
    row = dict_row(row)

    shape_type = row["shape_type"]
    dimensions = json.loads(row["dimensions_json"])

    gen_fn = GENERATORS.get(shape_type)
    if not gen_fn:
        raise HTTPException(500, f"Unknown shape_type in saved pattern: {shape_type}")

    result = gen_fn(**dimensions)
    pdf_bytes = generate_pdf(result, row["name"])
    safe_name = row["name"].replace(" ", "_").replace("/", "_")
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}_pattern.pdf"'},
    )
