"""Parametric architectural drawing and mockup engine.

Supports any furniture, upholstery, or millwork/casework piece.
True architectural scale, dimension strings, and real mathematical layout calculations.
"""
from app.services.drawing.mockup_engine.spec import (
    PieceSpec, FootprintSpec, SegmentSpec, BackStyleSpec, CushionSpec,
    MaterialFinishSpec, CaseworkSpec, CarcassBoxSpec,
)
from app.services.drawing.mockup_engine.math_layout import (
    compute_channels, compute_tufts, compute_modules,
)
from app.services.drawing.mockup_engine.presets import (
    marleys_u_and_l_preset, marleys_u_with_curved_corners_preset, straight_bench_preset, l_bench_preset,
    u_bench_preset, single_chair_preset, woodcraft_wall_unit_preset,
)
from app.services.drawing.mockup_engine.generator import (
    render_piece_mockup_pdf, render_pdf_to_png_previews,
)
from app.services.drawing.mockup_engine.renderers_3d import (
    render_3d, build_viewer_html, export_spec_to_glb,
)

__all__ = [
    "PieceSpec",
    "FootprintSpec",
    "SegmentSpec",
    "BackStyleSpec",
    "CushionSpec",
    "MaterialFinishSpec",
    "CaseworkSpec",
    "CarcassBoxSpec",
    "compute_channels",
    "compute_tufts",
    "compute_modules",
    "marleys_u_and_l_preset",
    "marleys_u_with_curved_corners_preset",
    "straight_bench_preset",
    "l_bench_preset",
    "u_bench_preset",
    "single_chair_preset",
    "woodcraft_wall_unit_preset",
    "render_piece_mockup_pdf",
    "render_pdf_to_png_previews",
    "render_3d",
    "build_viewer_html",
    "export_spec_to_glb",
]
