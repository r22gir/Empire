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
    draw_chrome, draw_scale_bar, draw_legend, draw_casework_legend, format_in,
    INK, PAPER, WHITE, MUT, GOLD
)
from app.services.drawing.mockup_engine.renderers import (
    render_plan_view, render_elevation_segment, render_casework_elevation, render_side_section
)


from app.services.drawing.mockup_engine.spec import PieceSpec
from app.services.drawing.mockup_engine.canvas_helpers import (
    draw_chrome, draw_scale_bar, draw_legend, draw_casework_legend, format_in,
    INK, PAPER, WHITE, MUT, GOLD
)
from app.services.drawing.mockup_engine.renderers import (
    render_plan_view, render_elevation_segment, render_casework_elevation, render_side_section
)
from app.config.workroom_billing import get_workroom_billing, client_facing_website
from app.services.drawing.bench_quote_bridge import sheet_chrome


def _pick_optimal_scale(
    view_type: str,
    shape: str,
    max_w_in: float,
    max_h_in: float,
    avail_w_pt: float,
    avail_h_pt: float,
) -> Tuple[float, str]:
    """Pick the largest standard architectural scale that fits in the available box.

    Standard architectural scales:
    1-1/2" = 1'-0" (factor = 1.5 * 72 / 12 = 9.0)
    1" = 1'-0"     (factor = 1.0 * 72 / 12 = 6.0)
    3/4" = 1'-0"   (factor = 0.75 * 72 / 12 = 4.5)
    1/2" = 1'-0"   (factor = 0.5 * 72 / 12 = 3.0)
    3/8" = 1'-0"   (factor = 0.375 * 72 / 12 = 2.25)
    1/4" = 1'-0"   (factor = 0.25 * 72 / 12 = 1.5)
    """
    scales = [
        ("1-1/2\" = 1'-0\"", 1.5),
        ("1\" = 1'-0\"", 1.0),
        ("3/4\" = 1'-0\"", 0.75),
        ("1/2\" = 1'-0\"", 0.5),
        ("3/8\" = 1'-0\"", 0.375),
        ("1/4\" = 1'-0\"", 0.25),
    ]

    for label, factor in scales:
        pt_per_in = factor * 72.0 / 12.0
        needed_w = max_w_in * pt_per_in
        needed_h = max_h_in * pt_per_in
        if needed_w <= avail_w_pt and needed_h <= avail_h_pt:
            return pt_per_in, f"{label}  (print at 100%)"

    # Fallback to 1/4"
    return 0.25 * 72.0 / 12.0, "1/4\" = 1'-0\"  (print at 100%)"


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
    chrome_data = sheet_chrome("woodcraft" if is_woodcraft else "workroom")
    billing = get_workroom_billing(spec.billed_by if getattr(spec, "billed_by", None) else ("woodcraft" if is_woodcraft else "empire_workroom"))

    company = chrome_data.get("company") or ("WOODCRAFT BY EMPIRE" if is_woodcraft else "EMPIRE WORKROOM")
    tagline = chrome_data.get("tagline") or ("CUSTOM CNC & ARCHITECTURAL MILLWORK" if is_woodcraft else "CUSTOM UPHOLSTERY & FABRICATION")
    address = chrome_data.get("address") or billing.address
    phone = billing.phone or "(703) 213-6484"
    website = client_facing_website(billing.website or "workroom.empirebox.store")
    contact_info = f"{phone} · {website}"

    shape = spec.footprint.shape

    # Determine total pages needed
    if spec.casework:
        total_pages = 2  # Page 1: Plan & Specs; Page 2: Front Elevation of Casework
    elif shape == "u_shape":
        total_pages = 2  # Page 1: Plan view; Page 2: Front elevations (U Main, U Left, U Right)
    elif shape == "l_shape":
        total_pages = 2  # Page 1: Plan view; Page 2: Front elevations (L Long, L Short)
    else:
        total_pages = 2  # Page 1: Plan view; Page 2: Front Elevation & Side Section

    # Calculate optimal scales
    # Available area on Page 1: width ~ 450 pt (beside legend) or 680 pt
    max_plan_w = 0.0
    if spec.casework:
        max_plan_w = spec.casework.overall_width_in
    elif shape == "u_shape":
        seg_dict = {seg.name.lower(): seg.length_in for seg in spec.footprint.segments}
        max_plan_w = seg_dict.get("main", 249.75)
    elif shape == "l_shape":
        seg_dict = {seg.name.lower(): seg.length_in for seg in spec.footprint.segments}
        max_plan_w = seg_dict.get("short", 95.375)
    else:
        max_plan_w = spec.footprint.overall_width_in or (spec.footprint.segments[0].length_in if spec.footprint.segments else 36.0)

    # For page 1 plan view:
    # If U-bench is large (250"), 3/8" fits 650pt width
    # If single chair (32"), 1-1/2" or 1" fits comfortably!
    avail_w_p1 = 440.0 if not spec.casework else 460.0
    avail_h_p1 = 340.0
    if max_plan_w > 180.0:
        avail_w_p1 = 660.0  # Plan spans above or with compact legend
        avail_h_p1 = 180.0

    max_plan_h = spec.cushion.seat_depth_in + spec.footprint.back_thickness_in
    if spec.casework:
        max_plan_h = spec.casework.overall_depth_in
    elif shape == "u_shape":
        seg_dict = {seg.name.lower(): seg.length_in for seg in spec.footprint.segments}
        max_plan_h = max(seg_dict.get("left", 37.75), seg_dict.get("right", 48.5))
    elif shape == "l_shape":
        seg_dict = {seg.name.lower(): seg.length_in for seg in spec.footprint.segments}
        max_plan_h = seg_dict.get("long", 107.75)

    s_plan, scale_label_p1 = _pick_optimal_scale("plan", shape, max_plan_w, max_plan_h, avail_w_p1, avail_h_p1)

    # Subtitle based on true piece specifications
    if spec.casework:
        sub_title = f'{spec.casework.wood_species}  ·  {spec.casework.finish}  ·  {len(spec.casework.boxes)} Carcass Bays'
    else:
        # Dynamic back style subtitle
        b_style = spec.back.style
        if b_style == "channel":
            b_desc = f'{format_in(spec.back.channel_width_in)} vertical channels'
        elif b_style in ("tufted", "button_tufted"):
            sp_x = spec.back.tuft_spacing_x_in or 6.0
            sp_y = spec.back.tuft_spacing_y_in or 6.0
            b_desc = f'Diamond tufted (~{format_in(sp_x)} x {format_in(sp_y)})'
        elif b_style in ("padded_modules", "basketweave"):
            b_desc = 'Padded modular back'
        else:
            b_desc = 'Plain smooth back'

        arm_desc = f"  ·  {format_in(spec.arm.arm_width_in)} arms" if getattr(spec, "arm", None) and spec.arm.has_arms else ""
        sub_title = (
            f'Seat depth {format_in(spec.cushion.seat_depth_in)}  ·  net back {format_in(spec.back.net_back_height_in)}  ·  '
            f'{b_desc}{arm_desc}  ·  {spec.material.name}, {spec.material.color_name}'
        )

    # ==========================================
    # PAGE 1: PLAN VIEW & QUOTED RUNS / OVERVIEW
    # ==========================================
    page_1_title = f"{spec.name.upper()} · PLAN VIEW (looking down)"
    draw_chrome(
        c, W, H,
        title=page_1_title,
        subtitle=sub_title,
        page=1,
        total=total_pages,
        company=company,
        tagline=tagline,
        address=address,
        contact_info=contact_info,
        client_name=spec.client_name,
        client_address=getattr(spec, "client_address", "") or "",
        quote_tag=f"{spec.quote_number} · {spec.status}",
        footer_text=f"{company} · {spec.project_name} · {spec.material.name if not spec.casework else spec.casework.wood_species} · drawn from quoted dimensions",
    )

    c.setFillColor(INK)
    c.setFont("Times-Bold", 11)
    c.drawString(40, H - 105, f"{spec.name.upper()} — PLAN")

    # Render plan view
    render_plan_view(c, spec, ox=60, top=H - 150, scale=s_plan)

    # Legend / Schedule
    if spec.casework:
        lx, ly = W - 280, H - 150
        draw_casework_legend(
            c, lx, ly,
            wood_species=spec.casework.wood_species,
            wood_finish=spec.casework.finish,
            boxes=spec.casework.boxes,
            materials=spec.casework.materials,
            notes=[
                'Carcass boxes constructed to WoodCraft architectural millwork standard.',
                'Field dimensions and wall plumb to be confirmed on site.',
            ] + spec.notes,
            col_width=230.0,
        )
    else:
        runs: list[Tuple[str, float]] = []
        if spec.footprint.segments:
            for seg in spec.footprint.segments:
                runs.append((f"{spec.name} {seg.name}", seg.length_in))
        elif spec.footprint.overall_width_in:
            runs.append((f"{spec.name} width", spec.footprint.overall_width_in))

        # Position legend beside drawing or bottom-right
        lx, ly = W - 310, H - 300 if max_plan_w > 180 else H - 150
        back_c = HexColor(spec.material.color_hex)
        seat_c = HexColor(spec.material.seat_color_hex)

        b_style = spec.back.style
        if b_style == "channel":
            b_lbl = f'{format_in(spec.back.channel_width_in)} channel back, {spec.material.color_name}'
        elif b_style in ("tufted", "button_tufted"):
            b_lbl = f'tufted back, {spec.material.color_name}'
        else:
            b_lbl = f'{b_style} back, {spec.material.color_name}'

        draw_legend(
            c, lx, ly,
            back_color=back_c,
            seat_color=seat_c,
            back_label=b_lbl,
            seat_label=f"seat cushion, plain {spec.material.color_name}",
            runs=runs,
            notes=[
                f'Back band in plan drawn {format_in(spec.footprint.back_thickness_in)} thick for legibility only.',
                'Corner/hand orientation as drawn; confirm on site.',
            ] + spec.notes,
            col_width=180.0,
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
        address=address,
        contact_info=contact_info,
        client_name=spec.client_name,
        client_address=getattr(spec, "client_address", "") or "",
        quote_tag=f"{spec.quote_number} · {spec.status}",
        footer_text=f"{company} · {spec.project_name} · {spec.material.name if not spec.casework else spec.casework.wood_species} · drawn from quoted dimensions",
    )

    if spec.casework:
        # Scale for casework elevation (overall width e.g. 108" / height 84")
        avail_elev_w = 660.0
        avail_elev_h = 320.0
        s_elev, scale_lbl_elev = _pick_optimal_scale(
            "elev", "straight",
            spec.casework.overall_width_in, spec.casework.overall_height_in,
            avail_elev_w, avail_elev_h
        )
        # Position so casework elevation fits neatly above scale bar and below title
        elev_y = 60 + (340.0 - spec.casework.overall_height_in * s_elev) / 2
        render_casework_elevation(c, spec, x=60, y=elev_y, scale=s_elev)
        draw_scale_bar(c, 60, 40, s_elev, scale_lbl_elev)
    elif shape == "u_shape":
        seg_dict = {seg.name.lower(): seg.length_in for seg in spec.footprint.segments}
        m_len = seg_dict.get("main", 249.75)
        l_len = seg_dict.get("left", 37.75)
        r_len = seg_dict.get("right", 48.5)

        s_elev, scale_lbl_elev = _pick_optimal_scale("elev", "straight", m_len, 35.0, 660.0, 160.0)
        y = H - 210
        render_elevation_segment(c, spec, 60, y, s_elev, m_len, "U MAIN")
        render_elevation_segment(c, spec, 60, y - 150, s_elev, l_len, "U LEFT")
        render_elevation_segment(c, spec, 330, y - 150, s_elev, r_len, "U RIGHT")
        draw_scale_bar(c, 60, 40, s_elev, scale_lbl_elev)
    elif shape == "l_shape":
        seg_dict = {seg.name.lower(): seg.length_in for seg in spec.footprint.segments}
        sh_len = seg_dict.get("short", 95.375)
        lg_len = seg_dict.get("long", 107.75)

        s_elev, scale_lbl_elev = _pick_optimal_scale("elev", "straight", max(sh_len, lg_len), 35.0, 660.0, 125.0)
        elev_h = 35.0 * s_elev
        render_elevation_segment(c, spec, 60, H - 245, s_elev, lg_len, "L LONG")
        render_elevation_segment(c, spec, 60, H - 245 - elev_h - 45, s_elev, sh_len, "L SHORT")
        draw_scale_bar(c, 60, 40, s_elev, scale_lbl_elev)
    else:
        # Straight bench / Chair / Single piece
        w = spec.footprint.overall_width_in or (spec.footprint.segments[0].length_in if spec.footprint.segments else 36.0)
        total_h = spec.cushion.seat_height_in + spec.back.net_back_height_in
        # Use a generous scale like 1" = 1'-0" or 3/4" = 1'-0"
        s_elev, scale_lbl_elev = _pick_optimal_scale("elev", "straight", w, total_h, 320.0, 320.0)
        render_elevation_segment(c, spec, 60, H - 320, s_elev, w, spec.name.upper())
        if spec.include_section:
            render_side_section(c, spec, 450, H - 320, s_elev)
        draw_scale_bar(c, 60, 40, s_elev, scale_lbl_elev)

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
