"""ReportLab PDF Diagram Renderer for Material Nesting Layouts.

Generates professional Empire Workroom branded diagram sheets (11x17 landscape):
- Page 1: Materials & Totals Summary Sheet (cut list counts, sheets/rolls, yardages, yield %, offcuts, double-width comparisons)
- Page 2..N: Plywood / Board Sheet Layout Diagrams (one diagram per 48" x 96" sheet with placed pieces, labels, dimensions, offcuts)
- Page N+1..M: Foam Sheet / Bun Layout Diagrams (per thickness with placed parts, bun dimensions, yield %)
- Page M+1..P: Fabric Roll Layout Diagrams (54" standard and 110"+ comparisons, placed channel cuts, seat cuts, roll yardage)
- Page P+1..Q: Dacron Roll Layout Diagrams (placed wrap cuts)
"""
from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Dict, Any, List, Optional
from reportlab.lib.colors import HexColor, Color
from reportlab.lib.pagesizes import letter, landscape
from reportlab.pdfgen import canvas

from app.services.drawing.mockup_engine.canvas_helpers import (
    draw_chrome, format_in, format_yd,
    INK, MUT, GOLD, PAPER, WHITE, GRAY_LINE, WOOD_FILL, WOOD_DARK
)

def simplify_part_name(name: str, material: str = "Board") -> str:
    """Format piece label cleanly to fit inside part rectangles without mid-word truncation."""
    clean = name.replace("Marley's ", "").replace("Substrate Board", "Board").replace("Face Fabric", "Fabric").replace("2\" foam", "Foam").replace("Foam 2\"", "Foam")
    # Patterns like "U Bench Ch 1 (12 9/16") Board" -> "U Ch 1 (12 9/16")"
    clean = clean.replace("Bench ", "").replace("Channel ", "Ch ")
    # Replace verbose component suffixes
    for suffix in [" Substrate Board", " Board", " Foam", " Fabric", " Dacron Wrap", " Dacron"]:
        if clean.endswith(suffix):
            clean = clean[:-len(suffix)]
            break
    # Add short material hint if useful
    if "Seat" in clean:
        # e.g. "U Seat Main #1"
        return f"{clean} – {material}"
    return clean


def draw_fitted_text(
    c: canvas.Canvas,
    text: str,
    sub_text: str,
    cx: float,
    cy: float,
    max_w: float,
    max_h: float,
    part_idx: Optional[int] = None,
    text_color: Color = WHITE,
) -> None:
    """Draw text inside a part box ensuring it never clips, overflows, or truncates mid-word.
    If the full text cannot fit even at small font sizes, display clean index number (#N).
    """
    if max_w < 12 or max_h < 8:
        return

    # Check if we can fit at reasonable font size
    font_name = "Helvetica-Bold"
    for font_size in (7.0, 6.0, 5.5, 5.0, 4.5):
        w = c.stringWidth(text, font_name, font_size)
        if w <= max_w - 4 and (font_size * 2.2 <= max_h or not sub_text):
            c.setFont(font_name, font_size)
            c.setFillColor(text_color)
            if sub_text and max_h >= font_size * 2.2:
                c.drawCentredString(cx, cy + font_size * 0.35, text)
                c.setFont("Helvetica", max(4.0, font_size - 1.0))
                c.drawCentredString(cx, cy - font_size * 0.85, sub_text)
            else:
                c.drawCentredString(cx, cy - font_size * 0.35, text)
            return

    # If sub_text alone fits:
    if sub_text and c.stringWidth(sub_text, "Helvetica", 5.0) <= max_w - 4 and max_h >= 10:
        c.setFont("Helvetica", 5.0)
        c.setFillColor(text_color)
        c.drawCentredString(cx, cy - 1.5, sub_text)
        return

    # If neither fits, and part_idx is provided, display piece index badge
    if part_idx is not None and max_w >= 14 and max_h >= 10:
        badge = f"#{part_idx}"
        c.setFont("Helvetica-Bold", 6.0)
        c.setFillColor(text_color)
        c.drawCentredString(cx, cy - 2.0, badge)

from app.services.drawing.mockup_engine.generator import render_pdf_to_png_previews


def render_nesting_pdf(
    nest_data: Dict[str, Any],
    output_pdf_path: str,
    client_name: str = "Marley's",
    client_address: str = "Hyattsville, MD",
    quote_number: str = "EST-2026-299",
    project_name: str = "Marley's channel backs",
) -> str:
    """Render comprehensive multi-sheet Material Nesting & Cut List Diagram PDF."""
    out_dir = Path(output_pdf_path).parent
    out_dir.mkdir(parents=True, exist_ok=True)

    # 11x17 landscape: 17 * 72 = 1224 pt, 11 * 72 = 792 pt
    W, H = 1224.0, 792.0
    c = canvas.Canvas(output_pdf_path, pagesize=(W, H))

    totals = nest_data["totals"]
    nest_res = nest_data["nesting_results"]
    pieces_str = ", ".join(nest_data.get("pieces", ["Custom Pieces"]))

    board_sheets = nest_res.get("board", {}).get("sheets", [])
    
    foam_nest = nest_res.get("foam", {})
    foam_sheets_all = []
    for thk_name, thk_data in foam_nest.get("by_thickness", {}).items():
        for s in thk_data.get("sheets", []):
            foam_sheets_all.append((thk_name, s))

    fabric_res = nest_res.get("fabric", {}).get("result", {})
    dacron_res = nest_res.get("dacron", {}).get("result", {})

    # Calculate total pages
    # Page 1: Summary Sheet
    # Next pages: Board sheets (1 per sheet)
    # Next pages: Foam sheets (1 or 2 per page, or 1 per sheet)
    # Next page: Fabric roll diagram
    # Next page: Dacron roll diagram
    # To keep diagrams crisp and readable:
    # 1 summary page + board sheets (up to 7) + foam sheets + fabric page + dacron page
    total_pages = 1 + len(board_sheets) + min(len(foam_sheets_all), 6) + 1 + 1

    cur_page = 1

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 1: TOTALS & SPECIFICATION SUMMARY SHEET
    # ════════════════════════════════════════════════════════════════════════
    draw_chrome(
        c, W, H,
        title="MATERIAL NESTING & OPTIMIZATION REPORT",
        subtitle=f"Cut lists, sheet layouts, roll yardage & yield calculations · {pieces_str}",
        page=cur_page,
        total=total_pages,
        client_name=client_name,
        client_address=client_address,
        doc_kind="MATERIAL NEST",
        quote_tag=f"{quote_number} · SHOP USE",
        footer_text="EMPIRE WORKROOM · Material Nesting Engine · True 2D Guillotine & Skyline Optimization",
    )

    # Left Column: Totals Summary Cards
    card_x = 48
    card_y = H - 120
    card_w = 340

    c.setFillColor(WHITE)
    c.setStrokeColor(GRAY_LINE)
    c.rect(card_x, card_y - 280, card_w, 280, stroke=1, fill=1)

    c.setFillColor(INK)
    c.setFont("Times-Bold", 14)
    c.drawString(card_x + 16, card_y - 26, "PROJECT MATERIAL REQUIREMENTS")

    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(MUT)
    c.drawString(card_x + 16, card_y - 42, "OPTIMIZED QUANTITIES (ALL DIMENSIONS IN FRACTIONS)")

    rows = [
        ("Substrate Board (Plywood)", f"{totals['board_sheets']} Sheets ({totals['board_sheet_size']}, {totals['board_thickness_fraction']})", f"Yield: {totals['board_avg_yield_pct']}%"),
        ("Foam Total Buns/Sheets", f"{totals['foam_total_sheets']} Sheets", "Across 2\" foam buns"),
        ("Fabric Total (54\" Roll / 53\" Usable)", totals['fabric_total_yards_fraction'], f"Yield: {totals['fabric_yield_pct']}% (incl. 10% waste)"),
        ("Dacron Poly Wrap", totals['dacron_total_yards_fraction'], f"{totals['dacron_roll_width_fraction']} roll (incl. 10% waste)"),
    ]

    yy = card_y - 70
    for label, val, sub in rows:
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(card_x + 16, yy, label)
        c.setFont("Helvetica-Bold", 10.5)
        c.drawRightString(card_x + card_w - 16, yy, val)
        c.setFillColor(MUT)
        c.setFont("Helvetica", 7.5)
        c.drawString(card_x + 16, yy - 12, sub)
        c.setStrokeColor(HexColor("#EEEEEE"))
        c.line(card_x + 16, yy - 18, card_x + card_w - 16, yy - 18)
        yy -= 42

    # Double Width Comparison Card
    dw_card_y = card_y - 300
    c.setFillColor(WHITE)
    c.setStrokeColor(GRAY_LINE)
    c.rect(card_x, dw_card_y - 180, card_w, 180, stroke=1, fill=1)

    c.setFillColor(INK)
    c.setFont("Times-Bold", 12)
    c.drawString(card_x + 16, dw_card_y - 24, "DOUBLE-WIDTH FABRIC COMPARISON")
    c.setFont("Helvetica", 8)
    c.setFillColor(MUT)
    c.drawString(card_x + 16, dw_card_y - 38, "Railroading & extra-wide roll savings (110\" to 120\" goods)")

    dw_y = dw_card_y - 62
    c.setFont("Helvetica-Bold", 8)
    c.setFillColor(INK)
    c.drawString(card_x + 16, dw_y, "Roll Width")
    c.drawString(card_x + 110, dw_y, "Usable")
    c.drawString(card_x + 180, dw_y, "Total Yardage")
    c.drawRightString(card_x + card_w - 16, dw_y, "Yield %")
    c.setStrokeColor(GRAY_LINE)
    c.line(card_x + 16, dw_y - 4, card_x + card_w - 16, dw_y - 4)
    dw_y -= 16

    # 54" standard baseline
    c.setFont("Helvetica", 8)
    c.drawString(card_x + 16, dw_y, '54" (Standard)')
    c.drawString(card_x + 110, dw_y, '53"')
    c.setFont("Helvetica-Bold", 8.5)
    c.drawString(card_x + 180, dw_y, totals['fabric_total_yards_fraction'])
    c.setFont("Helvetica", 8)
    c.drawRightString(card_x + card_w - 16, dw_y, f"{totals['fabric_yield_pct']}%")
    dw_y -= 18

    for roll_label, info in totals.get("double_width_fabric_comparisons", {}).items():
        c.drawString(card_x + 16, dw_y, roll_label)
        c.drawString(card_x + 110, dw_y, format_in(info["usable_width_in"]))
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(card_x + 180, dw_y, info["total_yards_fraction"])
        c.setFont("Helvetica", 8)
        c.drawRightString(card_x + card_w - 16, dw_y, f"{info['yield_pct']}%")
        dw_y -= 18

    c.setFillColor(HexColor("#2E6930"))
    c.setFont("Helvetica-Bold", 8)
    c.drawString(card_x + 16, dw_y - 6, "Wide goods reduce yardage by eliminating row splits (compare totals above)")

    # Right Column: Upholstery & Construction Engineering Rules
    r_x = card_x + card_w + 28
    r_w = W - r_x - 48
    r_y = card_y

    c.setFillColor(WHITE)
    c.setStrokeColor(GRAY_LINE)
    c.rect(r_x, r_y - 480, r_w, 480, stroke=1, fill=1)

    c.setFillColor(INK)
    c.setFont("Times-Bold", 14)
    c.drawString(r_x + 20, r_y - 28, "RAFAEL'S UPHOLSTERY & FABRICATION SPECIFICATIONS")

    rules = [
        ("Channel-Back Distribution:", "Channels stay ~12\" wide. Each run is partitioned into the nearest whole number of equal channels (zero leftover end strips). Marley's U: 37 3/4\" -> 3 equal, 249 3/4\" -> 21 equal, 48 1/2\" -> 4 equal. Marley's L: 95 3/8\" -> 8 equal, 107 3/4\" -> 9 equal. Combined project: 45 channels total."),
        ("Channel Wood & Foam Cut:", "WOOD CUT = true size, no add-ons: length = net back height (Marley's 26 3/4\"), width = finished channel width. FOAM CUT = exactly the wood cut size. Board is cut from 1/2\" plywood."),
        ("Channel Fabric Cut:", "FABRIC CUT = foam size + 2 to 3\" for stapling (3\" default) in width and length, always shown as a separate size from the wood cut (12\" channel: wood 12\" x 26 3/4\", fabric 15\" x 29 3/4\"). 3 channel cuts fit per 53\" usable roll width."),
        ("Seat Cushion Construction:", "18\" deep seat = 2\" back thickness + 16\" seat cushion. Front cushion overhang is 1 1/4\" (>= 1\"). Seat wrapped over 2\" high-density foam on 1/2\" plywood base."),
        ("Seat Fabric Cuts:", "Seat fabric cut width = 25 1/4\" (fits 2 seat runs side-by-side in 53\" roll width). Total linear seat run length = 539 1/8\" + 14 3/8\" pull allowance = 553 1/2\", yielding 276 3/4\" roll length = 7 11/16 yd."),
        ("Yardage Validation Calculation:", "Computed from the nested cut list: channel fabric cuts + seat runs, plus 10% shop waste, rounded UP to the nearest 1/2 yd (see yardage total above)."),
    ]

    ry = r_y - 65
    for title, desc in rules:
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", 8.5)
        c.drawString(r_x + 20, ry, title)
        c.setFillColor(MUT)
        c.setFont("Helvetica", 8)
        
        # Word wrap description
        words = desc.split()
        line = ""
        line_y = ry - 14
        for w in words:
            if c.stringWidth(line + " " + w, "Helvetica", 8) < (r_w - 40):
                line = (line + " " + w).strip()
            else:
                c.drawString(r_x + 20, line_y, line)
                line_y -= 12
                line = w
        if line:
            c.drawString(r_x + 20, line_y, line)
            line_y -= 12
        ry = line_y - 12

    c.showPage()
    cur_page += 1

    # ════════════════════════════════════════════════════════════════════════
    # PAGE 2..N: PLYWOOD / BOARD SHEET DIAGRAMS (48" x 96" Sheets)
    # ════════════════════════════════════════════════════════════════════════
    for sheet_idx, sheet in enumerate(board_sheets):
        draw_chrome(
            c, W, H,
            title=f"BOARD CUT DIAGRAM — SHEET {sheet['sheet_index']} OF {len(board_sheets)}",
            subtitle=f"48\" x 96\" x {totals['board_thickness_fraction']} Plywood · 1/8\" Kerf · Guillotine Best Area Fit · Yield: {sheet['yield_pct']}%",
            page=cur_page,
            total=total_pages,
            client_name=client_name,
            client_address=client_address,
            doc_kind="BOARD LAYOUT",
            quote_tag=f"{quote_number} · SHEET {sheet['sheet_index']}",
            footer_text=f"EMPIRE WORKROOM · Sheet {sheet['sheet_index']}: {len(sheet['placed_parts'])} parts placed · Offcuts: {len(sheet.get('offcuts', []))} usable rects",
        )

        # Draw sheet boundary
        # Sheet is 48" W x 96" L. Map to landscape diagram area.
        # Max display area: 850 pt W x 480 pt H
        # Scale: 96" along width -> 850 / 96 = 8.85 pt/in
        # Let's orient sheet with 96" along X (horizontal) and 48" along Y (vertical)
        scale = 8.0  # pt per inch (96" * 8.0 = 768 pt, 48" * 8.0 = 384 pt)
        diag_ox = 80
        diag_oy = 135
        sheet_disp_w = 96.0 * scale
        sheet_disp_h = 48.0 * scale

        # Draw outer sheet outline
        c.setFillColor(PAPER)
        c.setStrokeColor(INK)
        c.setLineWidth(1.5)
        c.rect(diag_ox, diag_oy, sheet_disp_w, sheet_disp_h, stroke=1, fill=1)

        # Dimension strings for full sheet
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(INK)
        c.drawCentredString(diag_ox + sheet_disp_w / 2, diag_oy + sheet_disp_h + 10, '96" SHEET LENGTH')
        c.saveState()
        c.translate(diag_ox - 18, diag_oy + sheet_disp_h / 2)
        c.rotate(90)
        c.drawCentredString(0, 0, '48" SHEET WIDTH')
        c.restoreState()

        # Draw placed parts
        # Parts were placed on 48" width x 96" length (packer coordinates: x in [0, 48], y in [0, 96])
        # Transpose to diagram: diag_x = diag_ox + p.y * scale, diag_y = diag_oy + p.x * scale
        for p_i, p in enumerate(sheet["placed_parts"]):
            px = diag_ox + p.y * scale
            py = diag_oy + p.x * scale
            pw = p.length * scale
            ph = p.width * scale

            c.setFillColor(WOOD_FILL)
            c.setStrokeColor(WOOD_DARK)
            c.setLineWidth(0.8)
            c.rect(px, py, pw, ph, stroke=1, fill=1)

            # Clean semantic label inside part without mid-word truncation
            lbl = simplify_part_name(p.name, material="Board")
            sub_lbl = f"{format_in(p.width)} x {format_in(p.length)}"
            draw_fitted_text(
                c, text=lbl, sub_text=sub_lbl,
                cx=px + pw / 2, cy=py + ph / 2,
                max_w=pw, max_h=ph, part_idx=p_i + 1,
                text_color=WHITE,
            )

        # Draw offcuts (usable free rects)
        for off in sheet.get("offcuts", []):
            ox = diag_ox + off["y"] * scale
            oy = diag_oy + off["x"] * scale
            ow = off["length"] * scale
            oh = off["width"] * scale
            if ow > 20 and oh > 20:
                c.setStrokeColor(HexColor("#888888"))
                c.setLineWidth(0.5)
                c.setDash(2, 2)
                c.rect(ox, oy, ow, oh, stroke=1, fill=0)
                c.setDash()
                c.setFillColor(MUT)
                c.setFont("Helvetica", 6)
                c.drawCentredString(ox + ow / 2, oy + oh / 2 - 2, f"OFFCUT {format_in(off['width'])}x{format_in(off['length'])}")

        # Sheet parts schedule table at bottom
        sched_y = diag_oy - 45
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(INK)
        c.drawString(diag_ox, sched_y, f"PARTS ON SHEET {sheet['sheet_index']} ({len(sheet['placed_parts'])} items):")
        c.setFont("Helvetica", 7.5)
        sched_items = [f"#{i+1}. {simplify_part_name(p.name, 'Board')}: {format_in(p.width)} x {format_in(p.length)}" for i, p in enumerate(sheet["placed_parts"])]
        # Display in 3 columns
        col_w = 320
        for i, item in enumerate(sched_items):
            cx = diag_ox + (i % 3) * col_w
            cy = sched_y - 14 - (i // 3) * 11
            if cy > 35:
                c.drawString(cx, cy, f"• {item}")

        c.showPage()
        cur_page += 1

    # ════════════════════════════════════════════════════════════════════════
    # PAGE N..M: FOAM SHEETS / BUNS (2" Foam Buns)
    # ════════════════════════════════════════════════════════════════════════
    # Sample up to 6 foam sheets for PDF presentation
    foam_sample = foam_sheets_all[:6]
    for idx, (thk_name, sheet) in enumerate(foam_sample):
        draw_chrome(
            c, W, H,
            title=f"FOAM CUT DIAGRAM — {thk_name.upper()} BUN {idx + 1} OF {len(foam_sheets_all)}",
            subtitle=f"{format_in(sheet['sheet_width'])} x {format_in(sheet['sheet_length'])} High-Density Foam Bun · Hot Wire Cut · Yield: {sheet['yield_pct']}%",
            page=cur_page,
            total=total_pages,
            client_name=client_name,
            client_address=client_address,
            doc_kind="FOAM LAYOUT",
            quote_tag=f"{quote_number} · FOAM {idx + 1}",
            footer_text=f"EMPIRE WORKROOM · Foam Bun {idx + 1}: {len(sheet['placed_parts'])} pieces cut from {format_in(sheet['sheet_width'])} x {format_in(sheet['sheet_length'])} bun",
        )

        scale = 7.4
        diag_ox = 80
        diag_oy = 135
        sheet_disp_w = sheet["sheet_length"] * scale
        sheet_disp_h = sheet["sheet_width"] * scale

        c.setFillColor(PAPER)
        c.setStrokeColor(HexColor("#3A7CA5"))
        c.setLineWidth(1.5)
        c.rect(diag_ox, diag_oy, sheet_disp_w, sheet_disp_h, stroke=1, fill=1)

        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(INK)
        c.drawCentredString(diag_ox + sheet_disp_w / 2, diag_oy + sheet_disp_h + 10, f"{format_in(sheet['sheet_length'])} BUN LENGTH")
        c.saveState()
        c.translate(diag_ox - 18, diag_oy + sheet_disp_h / 2)
        c.rotate(90)
        c.drawCentredString(0, 0, f"{format_in(sheet['sheet_width'])} BUN WIDTH")
        c.restoreState()

        for p_i, p in enumerate(sheet["placed_parts"]):
            px = diag_ox + p.y * scale
            py = diag_oy + p.x * scale
            pw = p.length * scale
            ph = p.width * scale

            c.setFillColor(HexColor("#B0E0E6"))
            c.setStrokeColor(HexColor("#4682B4"))
            c.setLineWidth(0.8)
            c.rect(px, py, pw, ph, stroke=1, fill=1)

            lbl = simplify_part_name(p.name, material="Foam")
            sub_lbl = f"{format_in(p.width)} x {format_in(p.length)}"
            draw_fitted_text(
                c, text=lbl, sub_text=sub_lbl,
                cx=px + pw / 2, cy=py + ph / 2,
                max_w=pw, max_h=ph, part_idx=p_i + 1,
                text_color=INK,
            )

        # Foam parts schedule table at bottom
        sched_y = diag_oy - 45
        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(INK)
        c.drawString(diag_ox, sched_y, f"PARTS ON BUN {idx + 1} ({len(sheet['placed_parts'])} items):")
        c.setFont("Helvetica", 7.5)
        sched_items = [f"#{i+1}. {simplify_part_name(p.name, 'Foam')}: {format_in(p.width)} x {format_in(p.length)}" for i, p in enumerate(sheet["placed_parts"])]
        col_w = 320
        for i, item in enumerate(sched_items):
            cx = diag_ox + (i % 3) * col_w
            cy = sched_y - 14 - (i // 3) * 11
            if cy > 35:
                c.drawString(cx, cy, f"• {item}")

        c.showPage()
        cur_page += 1

    # ════════════════════════════════════════════════════════════════════════
    # FABRIC ROLL DIAGRAM (Dynamic based on fabric roll width)
    # ════════════════════════════════════════════════════════════════════════
    fab_roll_w = fabric_res.get("roll_width", 54.0)
    fab_usable_w = fabric_res.get("usable_width", 53.0)
    fab_net_len = fabric_res.get("net_length_in", 1048.5)

    draw_chrome(
        c, W, H,
        title=f"FABRIC ROLL CUT DIAGRAM — {format_in(fab_roll_w)} ROLL ({format_in(fab_usable_w)} USABLE)",
        subtitle=f"Total Roll Yardage: {totals['fabric_total_yards_fraction']} · Channel Cuts + Seat Runs · Yield: {totals['fabric_yield_pct']}%",
        page=cur_page,
        total=total_pages,
        client_name=client_name,
        client_address=client_address,
        doc_kind="FABRIC ROLL",
        quote_tag=f"{quote_number} · FABRIC ROLL",
        footer_text=f"EMPIRE WORKROOM · Total Net Length: {format_in(fab_net_len)} · Total Billed: {totals['fabric_total_yards_fraction']} (incl. 10% waste)",
    )

    # Roll diagram display:
    # Wrap into horizontal strip bands across the sheet
    placed_fab = fabric_res.get("placed_parts", [])
    max_part_len = max([p.y + p.length for p in placed_fab], default=fab_net_len)
    
    # Scale and bands depending on width and length
    if fab_roll_w > 90.0:
        # Double width roll (110", 118", 120"): net length ~400-450", height ~110-120"
        # Fits on 1 or 2 bands
        num_bands = 2 if max_part_len > 260.0 else 1
        band_len = math.ceil(max_part_len / num_bands / 50.0) * 50.0
        scale_fab = min(930.0 / band_len, 280.0 / (num_bands * fab_usable_w))
        strip_h = fab_usable_w * scale_fab
        band_gap = 50.0
        start_y = H - 180 - strip_h
    else:
        num_bands = 3
        band_len = 380.0
        scale_fab = 2.45
        strip_h = fab_usable_w * scale_fab
        band_gap = 60.0
        start_y = H - 265

    for band_idx in range(num_bands):
        by0 = band_idx * band_len
        by1 = (band_idx + 1) * band_len
        
        band_x = 80
        band_y = start_y - band_idx * (strip_h + band_gap)

        # Roll usable width band
        c.setFillColor(PAPER)
        c.setStrokeColor(HexColor("#8B4513"))
        c.setLineWidth(1.0)
        c.rect(band_x, band_y, band_len * scale_fab, strip_h, stroke=1, fill=1)

        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(INK)
        c.drawString(band_x, band_y + strip_h + 4, f"SECTION {band_idx + 1}: {format_in(by0)} to {format_in(by1)} ({format_yd(by0 / 36)} to {format_yd(by1 / 36)})")
        c.saveState()
        c.translate(band_x - 16, band_y + strip_h / 2)
        c.rotate(90)
        c.drawCentredString(0, 0, f"{format_in(fab_usable_w)} USABLE")
        c.restoreState()

        # Render pieces falling in this band
        for p in placed_fab:
            p_len_start = p.y
            p_len_end = p.y + p.length
            if p_len_end > by0 and p_len_start < by1:
                # Clip to band for visual drawing
                draw_x = band_x + max(0.0, p_len_start - by0) * scale_fab
                draw_w = (min(by1, p_len_end) - max(by0, p_len_start)) * scale_fab
                draw_y = band_y + p.x * scale_fab
                draw_h = p.width * scale_fab

                c.setFillColor(HexColor(p.color_hex or "#9A5B2E"))
                c.setStrokeColor(HexColor("#5E3518"))
                c.setLineWidth(0.6)
                c.rect(draw_x, draw_y, draw_w, draw_h, stroke=1, fill=1)

                # Check if piece is split across boundary
                is_split = (p_len_start < by0) or (p_len_end > by1)
                is_main_segment = (p_len_start >= by0) or (draw_w >= 100)

                # Draw label cleanly inside box
                if is_split and not is_main_segment:
                    # Trailing continuation segment
                    lbl = "(cont.)"
                    sub_lbl = ""
                else:
                    if "Ch " in p.name:
                        lbl = "Ch Cut 18\"x34\""
                        sub_lbl = "(cont.)" if is_split else ""
                    else:
                        lbl = simplify_part_name(p.name, "Fabric")
                        sub_lbl = f"{format_in(p.width)} x {format_in(p.length)}" + (" (cont.)" if is_split else "")

                draw_fitted_text(
                    c, text=lbl, sub_text=sub_lbl,
                    cx=draw_x + draw_w / 2, cy=draw_y + draw_h / 2,
                    max_w=draw_w, max_h=draw_h,
                    text_color=WHITE,
                )

    c.showPage()
    cur_page += 1

    # ════════════════════════════════════════════════════════════════════════
    # DACRON ROLL DIAGRAM (60" Roll)
    # ════════════════════════════════════════════════════════════════════════
    draw_chrome(
        c, W, H,
        title=f"DACRON POLYESTER WRAP — {totals['dacron_roll_width_fraction']} ROLL",
        subtitle=f"Total Roll Yardage: {totals['dacron_total_yards_fraction']} · Wrap for All Channel Backs and Seat Cushions",
        page=cur_page,
        total=total_pages,
        client_name=client_name,
        client_address=client_address,
        doc_kind="DACRON ROLL",
        quote_tag=f"{quote_number} · DACRON ROLL",
        footer_text=f"EMPIRE WORKROOM · Best Roll Width: {totals['dacron_roll_width_fraction']} (yields {totals['dacron_total_yards_fraction']} vs 30\" roll)",
    )

    band_len_dac = 340.0
    scale_dac = 2.6
    strip_h_dac = 60.0 * scale_dac

    placed_dac = dacron_res.get("placed_parts", [])

    for band_idx in range(2):
        by0 = band_idx * band_len_dac
        by1 = (band_idx + 1) * band_len_dac
        band_x = 80
        # Start layout well below header & title block
        band_y = H - 295 - band_idx * (strip_h_dac + 75)

        c.setFillColor(PAPER)
        c.setStrokeColor(HexColor("#4682B4"))
        c.setLineWidth(1.0)
        c.rect(band_x, band_y, band_len_dac * scale_dac, strip_h_dac, stroke=1, fill=1)

        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(INK)
        c.drawString(band_x, band_y + strip_h_dac + 4, f"DACRON SECTION {band_idx + 1}: {format_in(by0)} to {format_in(by1)}")
        c.saveState()
        c.translate(band_x - 16, band_y + strip_h_dac / 2)
        c.rotate(90)
        c.drawCentredString(0, 0, f"{totals['dacron_roll_width_fraction']} ROLL WIDTH")
        c.restoreState()

        for p in placed_dac:
            p_len_start = p.y
            p_len_end = p.y + p.length
            if p_len_end > by0 and p_len_start < by1:
                draw_x = band_x + max(0.0, p_len_start - by0) * scale_dac
                draw_w = (min(by1, p_len_end) - max(by0, p_len_start)) * scale_dac
                draw_y = band_y + p.x * scale_dac
                draw_h = p.width * scale_dac

                c.setFillColor(HexColor("#F0F8FF"))
                c.setStrokeColor(HexColor("#B0C4DE"))
                c.setLineWidth(0.6)
                c.rect(draw_x, draw_y, draw_w, draw_h, stroke=1, fill=1)

                is_split = (p_len_start < by0) or (p_len_end > by1)
                is_main_segment = (p_len_start >= by0) or (draw_w >= 100)
                if is_split and not is_main_segment:
                    lbl = "(cont.)"
                    sub_lbl = ""
                else:
                    lbl = "Dacron Wrap"
                    sub_lbl = "(cont.)" if is_split else ""

                draw_fitted_text(
                    c, text=lbl, sub_text=sub_lbl,
                    cx=draw_x + draw_w / 2, cy=draw_y + draw_h / 2,
                    max_w=draw_w, max_h=draw_h,
                    text_color=INK,
                )

    c.showPage()
    c.save()

    return output_pdf_path
