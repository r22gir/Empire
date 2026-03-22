"""
Pattern Template Generator API — mathematically accurate sewing patterns.
Generates interactive previews and printable PDF templates.
"""
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from typing import Optional
import logging

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
