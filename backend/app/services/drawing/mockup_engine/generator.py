"""Core PDF & PNG preview generator for the parametric mockup engine."""
from __future__ import annotations

import io
import os
import subprocess
from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

from app.services.drawing.mockup_engine.spec import PieceSpec
from app.services.drawing.mockup_engine.canvas_helpers import (
    draw_chrome, draw_scale_bar, draw_legend, format_in,
    INK, PAPER, WHITE, MUT, GOLD
)
from app.services.drawing.mockup_engine.renderers import (
    render_plan_view, render_elevation_segment, render_casework_elevation, render_side_section
)


def render_piece_mockup_pdf(
    spec: PieceSpec,
    output_pdf_path: str,
) -> str:
    """Generate a multi-page, true-scale architectural mockup PDF from a PieceSpec."""
    W, H = landscape(letter)
    c = canvas.Canvas(output_pdf_path, pagesize=landscape(letter))
    c.setTitle(f"{spec.name} Mockup — {spec.quote_number}")
    c.setAuthor("Empire Workroom")

    is_woodcraft = spec.business_unit == "woodcraft" or spec.casework is not None
    company = "WOODCRAFT BY EMPIRE" if is_woodcraft else "EMPIRE WORKROOM"
    tagline = "CUSTOM CNC & ARCHITECTURAL MILLWORK" if is_woodcraft else "CUSTOM UPHOLSTERY & FABRICATION"

    shape = spec.footprint.shape

    # Determine total pages needed
    if spec.casework:
        total_pages = 2  # Page 1: Plan & Side / Specs; Page 2: Front Elevation of Casework
    elif shape == "u_shape":
        total_pages = 2  # Page 1: Plan view; Page 2: Front elevations (U Main, U Left, U Right)
    elif shape == "l_shape":
        total_pages = 2  # Page 1: Plan view; Page 2: Front elevations (L Long, L Short)
    else:
        total_pages = 2  # Page 1: Plan & Elevation; Page 2: Side Section & Detail

    # ==========================================
    # PAGE 1: PLAN VIEW & QUOTED RUNS / OVERVIEW
    # ==========================================
    s_plan = 0.375 * 72 / 12  # 3/8" = 1'-0"
    scale_label_p1 = '3/8" = 1\'-0"  (print at 100%)'

    sub_title = (
        f'Seat depth {format_in(spec.cushion.seat_depth_in)}  ·  net back {format_in(spec.back.net_back_height_in)}  ·  '
        f'{format_in(spec.back.channel_width_in)} vertical channels  ·  {spec.material.name}, {spec.material.color_name}'
        if not spec.casework else
        f'{spec.casework.wood_species}  ·  {spec.casework.finish}  ·  {len(spec.casework.boxes)} Carcass Bays'
    )

    page_1_title = f"{spec.name.upper()} · PLAN VIEW (looking down)"
    draw_chrome(
        c, W, H,
        title=page_1_title,
        subtitle=sub_title,
        page=1,
        total=total_pages,
        company=company,
        tagline=tagline,
        quote_tag=f"{spec.quote_number} · {spec.status}",
        footer_text=f"{company} · {spec.project_name} · {spec.material.name}, {spec.material.color_name} · drawn from quoted dimensions",
    )

    c.setFillColor(INK)
    c.setFont("Times-Bold", 11)
    c.drawString(40, H - 118, f"{spec.name.upper()} — PLAN")

    # Render plan view
    render_plan_view(c, spec, ox=60, top=H - 140, scale=s_plan)

    # Legend & Quoted Runs
    runs: list[Tuple[str, float]] = []
    if spec.footprint.segments:
        for seg in spec.footprint.segments:
            runs.append((f"{spec.name} {seg.name}", seg.length_in))
    elif spec.footprint.overall_width_in:
        runs.append((f"{spec.name} width", spec.footprint.overall_width_in))

    lx, ly = W - 320, H - 320
    back_c = HexColor(spec.material.color_hex)
    seat_c = HexColor(spec.material.seat_color_hex)
    draw_legend(
        c, lx, ly,
        back_color=back_c,
        seat_color=seat_c,
        back_label=f"{spec.back.style} back, {spec.material.color_name} ({spec.material.color_hex})",
        seat_label=f"seat cushion, plain {spec.material.color_name}",
        runs=runs,
        notes=[
            f'Back band in plan drawn {format_in(spec.footprint.back_thickness_in)} thick for legibility only.',
            'Corner/hand orientation as drawn; confirm on site.',
        ] + spec.notes,
    )

    draw_scale_bar(c, 60, 40, s_plan, scale_label_p1)
    c.showPage()

    # ==========================================
    # PAGE 2: FRONT ELEVATIONS & SECTIONS
    # ==========================================
    page_2_title = f"{spec.name.upper()} · FRONT ELEVATIONS"
    if spec.casework:
        sub_title_p2 = f'{spec.casework.wood_species} · Custom Built-In Carcass Details · {format_in(spec.casework.overall_height_in)} Overall Height'
    elif spec.back.style == "channel":
        sub_title_p2 = f'{format_in(spec.back.channel_width_in)} vertical channels on backs · plain seat cushions · {format_in(spec.back.net_back_height_in)} net back'
    elif spec.back.style in ("tufted", "button_tufted"):
        sub_title_p2 = f'Diamond tufted back · plain seat cushions · {format_in(spec.back.net_back_height_in)} net back'
    else:
        sub_title_p2 = f'{spec.back.style.capitalize()} back · plain seat cushions · {format_in(spec.back.net_back_height_in)} net back'
    draw_chrome(
        c, W, H,
        title=page_2_title,
        subtitle=sub_title_p2,
        page=2,
        total=total_pages,
        company=company,
        tagline=tagline,
        quote_tag=f"{spec.quote_number} · {spec.status}",
        footer_text=f"{company} · {spec.project_name} · {spec.material.name}, {spec.material.color_name} · drawn from quoted dimensions",
    )

    if spec.casework:
        s_elev = 0.375 * 72 / 12  # 3/8" = 1'-0"
        render_casework_elevation(c, spec, x=60, y=H - 380, scale=s_elev)
        draw_scale_bar(c, 60, 40, s_elev, '3/8" = 1\'-0"  (print at 100%)')
    elif shape == "u_shape":
        s_elev = 0.375 * 72 / 12
        seg_dict = {seg.name.lower(): seg.length_in for seg in spec.footprint.segments}
        m_len = seg_dict.get("main", 249.75)
        l_len = seg_dict.get("left", 37.75)
        r_len = seg_dict.get("right", 48.5)

        y = H - 210
        render_elevation_segment(c, spec, 60, y, s_elev, m_len, "U MAIN")
        render_elevation_segment(c, spec, 60, y - 150, s_elev, l_len, "U LEFT")
        render_elevation_segment(c, spec, 330, y - 150, s_elev, r_len, "U RIGHT")
        draw_scale_bar(c, 60, 40, s_elev, '3/8" = 1\'-0"  (print at 100%)')
    elif shape == "l_shape":
        s_elev = 0.5 * 72 / 12  # 1/2" = 1'-0"
        seg_dict = {seg.name.lower(): seg.length_in for seg in spec.footprint.segments}
        sh_len = seg_dict.get("short", 95.375)
        lg_len = seg_dict.get("long", 107.75)

        render_elevation_segment(c, spec, 60, H - 230, s_elev, lg_len, "L LONG")
        render_elevation_segment(c, spec, 60, H - 420, s_elev, sh_len, "L SHORT")
        draw_scale_bar(c, 60, 40, s_elev, '1/2" = 1\'-0"  (print at 100%)')
    else:
        # Straight bench / Chair / Single piece
        s_elev = 0.75 * 72 / 12  # 3/4" = 1'-0" for single pieces
        w = spec.footprint.overall_width_in or (spec.footprint.segments[0].length_in if spec.footprint.segments else 36.0)
        render_elevation_segment(c, spec, 60, H - 280, s_elev, w, spec.name.upper())
        if spec.include_section:
            render_side_section(c, spec, 450, H - 280, s_elev)
        draw_scale_bar(c, 60, 40, s_elev, '3/4" = 1\'-0"  (print at 100%)')

    c.showPage()
    c.save()
    return output_pdf_path


def render_pdf_to_png_previews(
    pdf_path: str,
    output_prefix: str,
    dpi: int = 150,
) -> List[str]:
    """Render each page of a PDF file to high-quality PNG preview images using pdftoppm."""
    out_dir = Path(output_prefix).parent
    out_dir.mkdir(parents=True, exist_ok=True)
    base_name = Path(output_prefix).name

    cmd = [
        "pdftoppm",
        "-png",
        "-r", str(dpi),
        pdf_path,
        str(out_dir / base_name),
    ]
    subprocess.run(cmd, check=True)

    # Collect generated files (pdftoppm outputs prefix-1.png, prefix-2.png etc.)
    generated = sorted(out_dir.glob(f"{base_name}-*.png"))
    return [str(p) for p in generated]
