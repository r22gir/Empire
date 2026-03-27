"""Drawing Studio API — generate architectural bench drawings (SVG + PDF)."""
from fastapi import APIRouter, Response
from pydantic import BaseModel
from typing import Optional
import os
import tempfile

router = APIRouter()


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
