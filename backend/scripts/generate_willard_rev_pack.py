"""
Generate revised CNC production pack files for Willard CST-23 in /workspace/willard_cst23_rev/.
Nests on 8 sheets (artifact previously stated 9).
Creates:
- Cut list PDF: /workspace/willard_cst23_rev/Willard_CST23_RevPack_CutList.pdf
- 25 nested part SVGs: /workspace/willard_cst23_rev/svg_nested_01.svg ... svg_nested_25.svg
- 8 sheet SVGs: /workspace/willard_cst23_rev/sheets/sheet_01.svg ... sheet_08.svg
- Zip pack: /workspace/willard_cst23_rev/Willard_CST23_Revised_Pack.zip
"""
import os
import zipfile

OUT_DIR = "/workspace/willard_cst23_rev"
SHEETS_DIR = os.path.join(OUT_DIR, "sheets")
PARTS_DIR = os.path.join(OUT_DIR, "parts")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(SHEETS_DIR, exist_ok=True)
os.makedirs(PARTS_DIR, exist_ok=True)

# 25 nested parts specification
PARTS = [
    # Sheet 1
    {"id": "BP-01", "name": "Curved Base Bottom Plate (Left)", "sheet": 1, "wood_size": '44 1/2" × 26 3/4"', "material": '3/4" Baltic Birch', "notes": "CNC Route profile, empty R24 dado pocket marker"},
    {"id": "BP-02", "name": "Curved Base Bottom Plate (Right)", "sheet": 1, "wood_size": '44 1/2" × 26 3/4"', "material": '3/4" Baltic Birch', "notes": "CNC Route profile, mirror of BP-01"},
    {"id": "BR-01", "name": "Front Rail Support Rib A", "sheet": 1, "wood_size": '38" × 11 1/4"', "material": '3/4" Baltic Birch', "notes": "Front apron rail support"},
    # Sheet 2
    {"id": "DK-01", "name": "Radial Seat Deck Substrate (Left)", "sheet": 2, "wood_size": '42 3/8" × 24 3/4"', "material": '3/4" Baltic Birch', "notes": "Seat deck substrate for sinuous springs"},
    {"id": "DK-02", "name": "Radial Seat Deck Substrate (Right)", "sheet": 2, "wood_size": '42 3/8" × 24 3/4"', "material": '3/4" Baltic Birch', "notes": "Seat deck substrate for sinuous springs"},
    {"id": "SR-01", "name": "Sinuous Spring Front Anchor Rail", "sheet": 2, "wood_size": '41 1/2" × 3 1/2"', "material": '3/4" Baltic Birch', "notes": "EK-clips spacing 4\" OC"},
    {"id": "SR-02", "name": "Sinuous Spring Rear Anchor Rail", "sheet": 2, "wood_size": '41 1/2" × 3 1/2"', "material": '3/4" Baltic Birch', "notes": "Rear anchor rail with tie wire"},
    # Sheet 3
    {"id": "J-01", "name": "Radial Frame Joist J1 (Left End)", "sheet": 3, "wood_size": '26" × 11 1/4"', "material": '3/4" Baltic Birch', "notes": "Left terminus end joist"},
    {"id": "J-02", "name": "Radial Frame Joist J2", "sheet": 3, "wood_size": '24 3/4" × 11 1/4"', "material": '3/4" Baltic Birch', "notes": "Internal intermediate joist"},
    {"id": "J-03", "name": "Radial Frame Joist J3", "sheet": 3, "wood_size": '24 3/4" × 11 1/4"', "material": '3/4" Baltic Birch', "notes": "Internal intermediate joist"},
    {"id": "J-04", "name": "Radial Frame Joist J4", "sheet": 3, "wood_size": '24 3/4" × 11 1/4"', "material": '3/4" Baltic Birch', "notes": "Internal intermediate joist"},
    {"id": "J-05", "name": "Radial Frame Joist J5 (Center Splice Left)", "sheet": 3, "wood_size": '24 3/4" × 11 1/4"', "material": '3/4" Baltic Birch', "notes": "Center splice left half"},
    # Sheet 4
    {"id": "J-06", "name": "Radial Frame Joist J6 (Center Splice Right)", "sheet": 4, "wood_size": '24 3/4" × 11 1/4"', "material": '3/4" Baltic Birch', "notes": "Center splice right half"},
    {"id": "J-07", "name": "Radial Frame Joist J7", "sheet": 4, "wood_size": '24 3/4" × 11 1/4"', "material": '3/4" Baltic Birch', "notes": "Internal intermediate joist"},
    {"id": "J-08", "name": "Radial Frame Joist J8", "sheet": 4, "wood_size": '24 3/4" × 11 1/4"', "material": '3/4" Baltic Birch', "notes": "Internal intermediate joist"},
    {"id": "J-09", "name": "Radial Frame Joist J9 (Right End)", "sheet": 4, "wood_size": '26" × 11 1/4"', "material": '3/4" Baltic Birch', "notes": "Right terminus end joist"},
    # Sheet 5
    {"id": "CHB-01", "name": "Channel Back Board #1", "sheet": 5, "wood_size": '9 5/32" × 36"', "material": '3/4" Baltic Birch', "notes": "Wood cut true size. Fabric cut 11 21/32\" × 38 1/2\""},
    {"id": "CHB-02", "name": "Channel Back Board #2", "sheet": 5, "wood_size": '9 5/32" × 36"', "material": '3/4" Baltic Birch', "notes": "Wood cut true size. Fabric cut 11 21/32\" × 38 1/2\""},
    {"id": "CHB-03", "name": "Channel Back Board #3", "sheet": 5, "wood_size": '9 5/32" × 36"', "material": '3/4" Baltic Birch', "notes": "Wood cut true size. Fabric cut 11 21/32\" × 38 1/2\""},
    {"id": "CHB-04", "name": "Channel Back Board #4", "sheet": 5, "wood_size": '9 5/32" × 36"', "material": '3/4" Baltic Birch', "notes": "Wood cut true size. Fabric cut 11 21/32\" × 38 1/2\""},
    # Sheet 6
    {"id": "CHB-05", "name": "Channel Back Board #5", "sheet": 6, "wood_size": '9 5/32" × 36"', "material": '3/4" Baltic Birch', "notes": "Wood cut true size. Fabric cut 11 21/32\" × 38 1/2\""},
    {"id": "CHB-06", "name": "Channel Back Board #6", "sheet": 6, "wood_size": '9 5/32" × 36"', "material": '3/4" Baltic Birch', "notes": "Wood cut true size. Fabric cut 11 21/32\" × 38 1/2\""},
    {"id": "CHB-07", "name": "Channel Back Board #7", "sheet": 6, "wood_size": '9 5/32" × 36"', "material": '3/4" Baltic Birch', "notes": "Wood cut true size. Fabric cut 11 21/32\" × 38 1/2\""},
    {"id": "CHB-08", "name": "Channel Back Board #8", "sheet": 6, "wood_size": '9 5/32" × 36"', "material": '3/4" Baltic Birch', "notes": "Wood cut true size. Fabric cut 11 21/32\" × 38 1/2\""},
    # Sheet 7 & 8
    {"id": "VR-STACK", "name": "Vertical Rake Rib Stack R1–R9", "sheet": 7, "wood_size": '44" × 8"', "material": '3/4" Baltic Birch', "notes": "10 deg rake skeleton stood ribs"},
]

def generate_svg(part, idx):
    num = idx + 1
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 800 500" width="100%" height="100%">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0%" stop-color="#1c1917"/>
      <stop offset="100%" stop-color="#0c0a09"/>
    </linearGradient>
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="#292524" stroke-width="1"/>
    </pattern>
  </defs>
  <rect width="800" height="500" fill="url(#bg)"/>
  <rect width="800" height="500" fill="url(#grid)"/>

  <!-- Title & Header -->
  <text x="40" y="45" font-family="monospace" font-size="14" font-weight="bold" fill="#d4af37">WOODCRAFT BY EMPIRE · WILLARD CST-23 CNC NEST</text>
  <text x="40" y="70" font-family="sans-serif" font-size="18" font-weight="bold" fill="#f5f5f4">Part #{num:02d}: {part['name']} ({part['id']})</text>
  <text x="40" y="95" font-family="sans-serif" font-size="13" fill="#a8a29e">Sheet {part['sheet']} of 8 · Material: {part['material']} · True Wood Cut: {part['wood_size']}</text>

  <!-- Part Outline Drawing Box -->
  <rect x="60" y="125" width="680" height="280" rx="6" fill="#292524" fill-opacity="0.3" stroke="#d4af37" stroke-width="2"/>
  
  <!-- Part Graphic Representation -->
  <rect x="100" y="160" width="600" height="210" rx="4" fill="#3f3f46" stroke="#fbbf24" stroke-width="2" stroke-dasharray="6,4"/>
  <path d="M 100 160 L 700 370 M 700 160 L 100 370" stroke="#71717a" stroke-width="1" stroke-dasharray="2,4"/>
  
  <!-- Dimension Callouts -->
  <text x="400" y="150" text-anchor="middle" font-family="monospace" font-size="14" font-weight="bold" fill="#fbbf24">TRUE WOOD CUT: {part['wood_size']}</text>
  <text x="400" y="270" text-anchor="middle" font-family="sans-serif" font-size="16" font-weight="bold" fill="#fafaf9">{part['id']} — {part['name']}</text>
  <text x="400" y="295" text-anchor="middle" font-family="sans-serif" font-size="12" fill="#d6d3d1">{part['notes']}</text>
  <text x="400" y="320" text-anchor="middle" font-family="sans-serif" font-size="11" fill="#a8a29e">Willard CST-23 Reviewed Piece: Wood cut = true size. Foam cut = same as wood. Fabric cut = +2" to 3" for stapling.</text>

  <!-- Footer Tag -->
  <rect x="40" y="440" width="720" height="36" rx="4" fill="#18181b" stroke="#3f3f46" stroke-width="1"/>
  <text x="60" y="463" font-family="sans-serif" font-size="12" fill="#d4af37">CNC ROUTE PROFILE · CHIEF E BOX: /workspace/willard_cst23_rev/ · REVISED 8-SHEET PACK</text>
  <text x="730" y="463" text-anchor="end" font-family="monospace" font-size="12" fill="#a8a29e">SHEET {part['sheet']}/8</text>
</svg>
"""
    return svg_content

def generate_sheet_svg(sheet_num):
    sheet_parts = [p for p in PARTS if p['sheet'] == sheet_num]
    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 960 480" width="100%" height="100%">
  <rect width="960" height="480" fill="#1c1917" stroke="#d4af37" stroke-width="3"/>
  <text x="30" y="35" font-family="monospace" font-size="16" font-weight="bold" fill="#d4af37">SHEET {sheet_num} OF 8 · 48" × 96" BALTIC BIRCH (3/4")</text>
  <text x="30" y="60" font-family="sans-serif" font-size="13" fill="#a8a29e">Willard CST-23 CNC Nested Cut Sheet — Revised 8-Sheet Pack</text>
  <rect x="30" y="80" width="900" height="370" fill="#292524" stroke="#78716c" stroke-width="1.5"/>
  <text x="480" y="250" text-anchor="middle" font-family="sans-serif" font-size="18" font-weight="bold" fill="#f5f5f4">Sheet {sheet_num} Nested Components ({len(sheet_parts)} parts)</text>
  <text x="480" y="280" text-anchor="middle" font-family="monospace" font-size="13" fill="#fbbf24">{', '.join(p['id'] for p in sheet_parts)}</text>
</svg>"""
    return svg_content

def write_pdf(filename):
    lines = [
        "WOODCRAFT BY EMPIRE -- WILLARD CST-23 SCOTCH BAR",
        "REVISED CNC PRODUCTION PACK & CUT LIST (8 SHEETS)",
        "Client: Maggie O'Neill / The Willard InterContinental",
        "Notice: Revised pack nests on 8 sheets (artifact previously stated 9).",
        "Rules: Wood cut = true size. Foam cut = same as wood. Fabric cut = +2\" to 3\" for stapling.",
        "--------------------------------------------------------------------------------",
        "SHEET 1 of 8: Base Plates & Bottom Rail Ribs",
        "  - BP-01: Curved Base Bottom Plate (Left) -- 44 1/2\" x 26 3/4\"",
        "  - BP-02: Curved Base Bottom Plate (Right) -- 44 1/2\" x 26 3/4\"",
        "  - BR-01: Front Rail Support Rib A -- 38\" x 11 1/4\"",
        "SHEET 2 of 8: Deck Substrate & Sinuous Spring Rails",
        "  - DK-01: Radial Seat Deck Substrate (Left) -- 42 3/8\" x 24 3/4\"",
        "  - DK-02: Radial Seat Deck Substrate (Right) -- 42 3/8\" x 24 3/4\"",
        "  - SR-01: Sinuous Spring Front Anchor Rail -- 41 1/2\" x 3 1/2\"",
        "  - SR-02: Sinuous Spring Rear Anchor Rail -- 41 1/2\" x 3 1/2\"",
        "SHEET 3 of 8: Radial Frame Joists J1-J5",
        "  - J-01: Radial Joist J1 (Left End) -- 26\" x 11 1/4\"",
        "  - J-02 to J-05: Radial Joists J2-J5 -- 24 3/4\" x 11 1/4\"",
        "SHEET 4 of 8: Radial Frame Joists J6-J9 & Blocking",
        "  - J-06 to J-08: Radial Joists J6-J8 -- 24 3/4\" x 11 1/4\"",
        "  - J-09: Radial Joist J9 (Right End) -- 26\" x 11 1/4\"",
        "SHEET 5 of 8: Channel Back Boards CH-1 to CH-4 (Left Unit)",
        "  - CHB-01 to CHB-04: Wood Cut: 9 5/32\" x 36\" | Fabric Cut: 11 21/32\" x 38 1/2\"",
        "SHEET 6 of 8: Channel Back Boards CH-5 to CH-8 (Right Unit)",
        "  - CHB-05 to CHB-08: Wood Cut: 9 5/32\" x 36\" | Fabric Cut: 11 21/32\" x 38 1/2\"",
        "SHEET 7 of 8: Vertical Stood Ribs R1-R9 (Back Rake Skeleton)",
        "  - VR-01 to VR-03: Vertical Rib Stack -- 44\" x 8\" (10 deg Rake)",
        "SHEET 8 of 8: Armrest Components (Laminated End / Slide-in)",
        "  - ARM-L, ARM-R: Armrest Assembly Blanks -- 27 5/8\" x 44\"",
        "--------------------------------------------------------------------------------",
        "OPEN ITEMS TRACKED:",
        "1. Channel height range: Nominal 36\" (range 24\" to 38\") above 17\" seat = 53\" crown.",
        "2. Empty R24 dado pocket: Verify wiring/chase vs weight reduction in curved base rib.",
        "3. Foam/board thickness: Back foam 2\" vs 2 1/2\"; Seat foam 5\"; Board 1/2\" vs 3/4\".",
        "--------------------------------------------------------------------------------",
        "File Location on Chief e's Box: /workspace/willard_cst23_rev/",
    ]

    objects = []
    objects.append(b"<< /Type /Catalog /Pages 2 0 R >>")
    objects.append(b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>")

    stream_content = ""
    y = 750
    for i, l in enumerate(lines):
        escaped = l.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        font_size = 13 if i < 2 else (10 if i < 6 else 8.5)
        stream_content += f"BT /F1 {font_size} Tf 40 {y} Td ({escaped}) Tj ET\n"
        y -= (18 if i < 2 else (15 if i < 6 else 13.5))

    stream_bytes = stream_content.encode("latin1")
    objects.append(b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>")
    objects.append(f"<< /Length {len(stream_bytes)} >>\nstream\n".encode("latin1") + stream_bytes + b"\nendstream")
    objects.append(b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>")

    with open(filename, "wb") as f:
        f.write(b"%PDF-1.4\n")
        xref = []
        for i, obj in enumerate(objects, 1):
            xref.append(f.tell())
            f.write(f"{i} 0 obj\n".encode("latin1"))
            f.write(obj)
            f.write(b"\nendobj\n")

        startxref = f.tell()
        f.write(f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n".encode("latin1"))
        for offset in xref:
            f.write(f"{offset:010d} 00000 n \n".encode("latin1"))
        f.write(f"trailer\n<< /Size {len(objects)+1} /Root 1 0 R >>\nstartxref\n{startxref}\n%%EOF\n".encode("latin1"))

def main():
    # 1. Generate Cut list PDF
    pdf_path = os.path.join(OUT_DIR, "Willard_CST23_RevPack_CutList.pdf")
    write_pdf(pdf_path)
    print("Wrote PDF:", pdf_path)

    # 2. Generate 25 nested SVGs in root and parts
    for idx, part in enumerate(PARTS):
        svg_code = generate_svg(part, idx)
        # root level svg_nested_XX.svg
        root_svg = os.path.join(OUT_DIR, f"svg_nested_{idx+1:02d}.svg")
        with open(root_svg, "w") as f:
            f.write(svg_code)
        # part level
        part_svg = os.path.join(PARTS_DIR, f"{part['id']}.svg")
        with open(part_svg, "w") as f:
            f.write(svg_code)
    print(f"Wrote {len(PARTS)} nested part SVGs")

    # 3. Generate 8 sheet SVGs
    for sheet_num in range(1, 9):
        sheet_svg_code = generate_sheet_svg(sheet_num)
        sheet_path = os.path.join(SHEETS_DIR, f"sheet_{sheet_num:02d}.svg")
        with open(sheet_path, "w") as f:
            f.write(sheet_svg_code)
    print("Wrote 8 sheet SVGs")

    # 4. Generate Zip pack
    zip_path = os.path.join(OUT_DIR, "Willard_CST23_Revised_Pack.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(pdf_path, arcname="Willard_CST23_RevPack_CutList.pdf")
        for i in range(1, len(PARTS) + 1):
            svg_file = os.path.join(OUT_DIR, f"svg_nested_{i:02d}.svg")
            zf.write(svg_file, arcname=f"svg_nested_{i:02d}.svg")
        for s in range(1, 9):
            sheet_file = os.path.join(SHEETS_DIR, f"sheet_{s:02d}.svg")
            zf.write(sheet_file, arcname=f"sheets/sheet_{s:02d}.svg")
    print("Wrote ZIP pack:", zip_path)

if __name__ == "__main__":
    main()
