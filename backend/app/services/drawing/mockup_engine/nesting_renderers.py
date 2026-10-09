"""ReportLab PDF Diagram Renderer for Material Nesting Layouts.

Generates professional Empire Workroom branded diagram sheets (11x17 landscape):
- Page 1: Materials & Totals Summary Sheet (cut list counts, sheets/rolls, yardages, yield %, offcuts, double-width comparisons)
- Page 2..N: Plywood / Board Sheet Layout Diagrams (one diagram per 48" x 96" sheet with placed pieces, labels, dimensions, offcuts)
- Page N+1..M: Foam Sheet / Bun Layout Diagrams (per thickness with placed parts, bun dimensions, yield %)
- Page M+1..P: Fabric Roll Layout Diagrams (54" standard and 110"+ comparisons, placed channel cuts, seat cuts, roll yardage)
- Page P+1..Q: Dacron Roll Layout Diagrams (placed wrap cuts)
"""
from __future__ import annotations

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
    c.drawString(card_x + 16, dw_y - 6, "Wide goods save ~60% yardage (12 1/2 yd vs 32 1/2 yd) by eliminating row splits")

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
        ("Channel Board & Foam Cuts:", "Substrate board and 2\" foam cut per channel: length = net back height + 2 1/2\" (Marley's 26 3/4\" + 2 1/2\" = 29 1/4\"), width = finished channel width. Board substrate cut from 1/2\" plywood."),
        ("Channel Fabric Cuts:", "Fabric cut per channel: at least 18\" wide for a 12\" channel (channel width + 2 1/2\" board/foam each side + pull), length = net back + 2 1/2\" wrap top and bottom + pull (Marley's 34\"). Exactly 2 channel cuts fit per 53\" usable roll width (23 cut rows)."),
        ("Seat Cushion Construction:", "18\" deep seat = 2\" back thickness + 16\" seat cushion. Front cushion overhang is 1 1/4\" (>= 1\"). Seat wrapped over 2\" high-density foam on 1/2\" plywood base."),
        ("Seat Fabric Cuts:", "Seat fabric cut width = 25 1/4\" (fits 2 seat runs side-by-side in 53\" roll width). Total linear seat run length = 539 1/8\" + 14 3/8\" pull allowance = 553 1/2\", yielding 276 3/4\" roll length = 7 11/16 yd."),
        ("Yardage Validation Calculation:", "Backs: 45 channel cuts at 2 per width = 23 rows x 34\" = 782\" = 21 3/4 yd. Seats: 7 11/16 yd. Sum: 29 7/16 yd. Adding 10% shop waste = 32.35 yd -> rounded UP to nearest 1/2 yard = exactly 32 1/2 yd."),
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
        scale = 8.2  # pt per inch
        diag_ox = 60
        diag_oy = 130
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
        c.drawRightString(diag_ox - 10, diag_oy + sheet_disp_h / 2, '48" SHEET WIDTH')

        # Draw placed parts
        # Parts were placed on 48" width x 96" length (packer coordinates: x in [0, 48], y in [0, 96])
        # Transpose to diagram: diag_x = diag_ox + p.y * scale, diag_y = diag_oy + p.x * scale
        for p in sheet["placed_parts"]:
            px = diag_ox + p.y * scale
            py = diag_oy + p.x * scale
            pw = p.length * scale
            ph = p.width * scale

            c.setFillColor(WOOD_FILL)
            c.setStrokeColor(WOOD_DARK)
            c.setLineWidth(0.8)
            c.rect(px, py, pw, ph, stroke=1, fill=1)

            # Label inside part
            c.setFillColor(WHITE)
            c.setFont("Helvetica-Bold", 6.5)
            # Truncate label if narrow
            lbl = p.name.replace("Substrate Board", "Board").replace("Marley's ", "")
            if pw > 35 and ph > 15:
                c.drawCentredString(px + pw / 2, py + ph / 2 + 2, lbl[:24])
                c.setFont("Helvetica", 6.0)
                c.drawCentredString(px + pw / 2, py + ph / 2 - 7, f"{format_in(p.width)} x {format_in(p.length)}")
            elif pw > 20 and ph > 10:
                c.drawCentredString(px + pw / 2, py + ph / 2 - 2, f"{format_in(p.width)}")

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
        sched_items = [f"{p.name}: {format_in(p.width)} x {format_in(p.length)}" for p in sheet["placed_parts"]]
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
        diag_ox = 60
        diag_oy = 130
        sheet_disp_w = sheet["sheet_length"] * scale
        sheet_disp_h = sheet["sheet_width"] * scale

        c.setFillColor(PAPER)
        c.setStrokeColor(HexColor("#3A7CA5"))
        c.setLineWidth(1.5)
        c.rect(diag_ox, diag_oy, sheet_disp_w, sheet_disp_h, stroke=1, fill=1)

        c.setFont("Helvetica-Bold", 8)
        c.setFillColor(INK)
        c.drawCentredString(diag_ox + sheet_disp_w / 2, diag_oy + sheet_disp_h + 10, f"{format_in(sheet['sheet_length'])} BUN LENGTH")
        c.drawRightString(diag_ox - 10, diag_oy + sheet_disp_h / 2, f"{format_in(sheet['sheet_width'])} BUN WIDTH")

        for p in sheet["placed_parts"]:
            px = diag_ox + p.y * scale
            py = diag_oy + p.x * scale
            pw = p.length * scale
            ph = p.width * scale

            c.setFillColor(HexColor("#B0E0E6"))
            c.setStrokeColor(HexColor("#4682B4"))
            c.setLineWidth(0.8)
            c.rect(px, py, pw, ph, stroke=1, fill=1)

            c.setFillColor(INK)
            c.setFont("Helvetica-Bold", 6.5)
            lbl = p.name.replace("Foam 2\"", "Foam").replace("Marley's ", "")
            if pw > 35 and ph > 15:
                c.drawCentredString(px + pw / 2, py + ph / 2 + 2, lbl[:24])
                c.setFont("Helvetica", 6.0)
                c.drawCentredString(px + pw / 2, py + ph / 2 - 7, f"{format_in(p.width)} x {format_in(p.length)}")
            elif pw > 20 and ph > 10:
                c.drawCentredString(px + pw / 2, py + ph / 2 - 2, f"{format_in(p.width)}")

        c.showPage()
        cur_page += 1

    # ════════════════════════════════════════════════════════════════════════
    # FABRIC ROLL DIAGRAM (54" Roll / 53" Usable)
    # ════════════════════════════════════════════════════════════════════════
    draw_chrome(
        c, W, H,
        title="FABRIC ROLL CUT DIAGRAM — 54\" ROLL (53\" USABLE)",
        subtitle=f"Total Roll Yardage: {totals['fabric_total_yards_fraction']} · 45 Channel Cuts (18\" x 34\" @ 2/width) + Seat Runs · Yield: {totals['fabric_yield_pct']}%",
        page=cur_page,
        total=total_pages,
        client_name=client_name,
        client_address=client_address,
        doc_kind="FABRIC ROLL",
        quote_tag=f"{quote_number} · FABRIC ROLL",
        footer_text=f"EMPIRE WORKROOM · Total Net Length: {format_in(fabric_res.get('net_length_in', 0))} · Total Billed: {totals['fabric_total_yards_fraction']} (incl. 10% waste)",
    )

    # Roll diagram display:
    # 53" roll width along Y. Total net length ~1080" along X.
    # To fit 1080" across width, wrap into 3 horizontal strip bands across the sheet!
    band_len = 380.0  # inches per strip band
    scale_fab = 2.45   # pt per inch (380" * 2.45 = 931 pt)
    strip_h = 53.0 * scale_fab  # 130 pt

    placed_fab = fabric_res.get("placed_parts", [])

    for band_idx in range(3):
        by0 = band_idx * band_len
        by1 = (band_idx + 1) * band_len
        
        band_x = 80
        band_y = H - 180 - band_idx * (strip_h + 55)

        # Roll usable width band
        c.setFillColor(PAPER)
        c.setStrokeColor(HexColor("#8B4513"))
        c.setLineWidth(1.0)
        c.rect(band_x, band_y, band_len * scale_fab, strip_h, stroke=1, fill=1)

        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(INK)
        c.drawString(band_x, band_y + strip_h + 4, f"SECTION {band_idx + 1}: {format_in(by0)} to {format_in(by1)} ({format_yd(by0 / 36)} to {format_yd(by1 / 36)})")
        c.drawRightString(band_x - 10, band_y + strip_h / 2, '53" USABLE')

        # Render pieces falling in this band
        for p in placed_fab:
            # p.y is position along roll length, p.x is position across roll width (0 to 53)
            # Check if piece overlaps this band
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

                c.setFillColor(WHITE)
                c.setFont("Helvetica-Bold", 5.5)
                if draw_w > 25 and draw_h > 15:
                    lbl = "Ch Cut 18\"x34\"" if "Ch " in p.name else p.name.replace("Marley's ", "")[:18]
                    c.drawCentredString(draw_x + draw_w / 2, draw_y + draw_h / 2 - 2, lbl)

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
        band_y = H - 220 - band_idx * (strip_h_dac + 65)

        c.setFillColor(PAPER)
        c.setStrokeColor(HexColor("#4682B4"))
        c.setLineWidth(1.0)
        c.rect(band_x, band_y, band_len_dac * scale_dac, strip_h_dac, stroke=1, fill=1)

        c.setFont("Helvetica-Bold", 7.5)
        c.setFillColor(INK)
        c.drawString(band_x, band_y + strip_h_dac + 4, f"DACRON SECTION {band_idx + 1}: {format_in(by0)} to {format_in(by1)}")
        c.drawRightString(band_x - 10, band_y + strip_h_dac / 2, totals['dacron_roll_width_fraction'])

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

                c.setFillColor(INK)
                c.setFont("Helvetica", 5.5)
                if draw_w > 20 and draw_h > 15:
                    c.drawCentredString(draw_x + draw_w / 2, draw_y + draw_h / 2 - 2, "Dacron Wrap")

    c.showPage()
    c.save()

    return output_pdf_path
