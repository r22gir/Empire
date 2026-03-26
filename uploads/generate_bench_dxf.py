#!/usr/bin/env python3
"""Generate CAD-style DXF drawing for bench upholstery pieces."""
import ezdxf
from ezdxf.enums import TextEntityAlignment

doc = ezdxf.new('R2010')
msp = doc.modelspace()

# Styling
doc.layers.add('OUTLINE', color=7)  # white
doc.layers.add('DIMENSIONS', color=3)  # green
doc.layers.add('TEXT', color=5)  # blue
doc.layers.add('TITLE', color=1)  # red

def draw_rect(x, y, w, h, layer='OUTLINE'):
    msp.add_lwpolyline(
        [(x, y), (x + w, y), (x + w, y + h), (x, y + h), (x, y)],
        dxfattribs={'layer': layer}
    )

def add_dim_h(x, y, w, offset=-3, layer='DIMENSIONS'):
    """Add horizontal dimension line below a rectangle."""
    msp.add_line((x, y + offset), (x + w, y + offset), dxfattribs={'layer': layer})
    msp.add_line((x, y), (x, y + offset - 1), dxfattribs={'layer': layer})
    msp.add_line((x + w, y), (x + w, y + offset - 1), dxfattribs={'layer': layer})
    msp.add_text(
        f'{w}"',
        dxfattribs={'layer': layer, 'height': 1.5}
    ).set_placement((x + w / 2, y + offset - 1.5), align=TextEntityAlignment.MIDDLE_CENTER)

def add_dim_v(x, y, h, offset=-3, layer='DIMENSIONS'):
    """Add vertical dimension line to the left of a rectangle."""
    msp.add_line((x + offset, y), (x + offset, y + h), dxfattribs={'layer': layer})
    msp.add_line((x, y), (x + offset - 1, y), dxfattribs={'layer': layer})
    msp.add_line((x, y + h), (x + offset - 1, y + h), dxfattribs={'layer': layer})
    msp.add_text(
        f'{h}"',
        dxfattribs={'layer': layer, 'height': 1.5, 'rotation': 90}
    ).set_placement((x + offset - 1.5, y + h / 2), align=TextEntityAlignment.MIDDLE_CENTER)

def add_label(x, y, text, layer='TEXT', height=2.0):
    msp.add_text(
        text,
        dxfattribs={'layer': layer, 'height': height}
    ).set_placement((x, y), align=TextEntityAlignment.MIDDLE_CENTER)

# ============================================================
# Title Block
# ============================================================
msp.add_text(
    'EMPIRE WORKROOM — BENCH UPHOLSTERY CUTTING LAYOUT',
    dxfattribs={'layer': 'TITLE', 'height': 3.5}
).set_placement((60, 130), align=TextEntityAlignment.MIDDLE_CENTER)

msp.add_text(
    'All dimensions in inches | Seam allowance: 0.5" included',
    dxfattribs={'layer': 'TEXT', 'height': 1.5}
).set_placement((60, 124), align=TextEntityAlignment.MIDDLE_CENTER)

# ============================================================
# Piece 1: Seat Cushion Top — 48" x 18"
# ============================================================
sx, sy = 5, 85
sw, sh = 48, 18

draw_rect(sx, sy, sw, sh)
add_dim_h(sx, sy, sw)
add_dim_v(sx, sy, sh)
add_label(sx + sw / 2, sy + sh / 2, 'SEAT CUSHION TOP')
add_label(sx + sw / 2, sy + sh / 2 - 3, '48" x 18"')

# Grain direction arrow
arrow_y = sy + sh / 2
msp.add_line((sx + 3, arrow_y), (sx + 12, arrow_y), dxfattribs={'layer': 'TEXT'})
msp.add_line((sx + 11, arrow_y + 1), (sx + 12, arrow_y), dxfattribs={'layer': 'TEXT'})
msp.add_line((sx + 11, arrow_y - 1), (sx + 12, arrow_y), dxfattribs={'layer': 'TEXT'})
msp.add_text(
    'GRAIN',
    dxfattribs={'layer': 'TEXT', 'height': 1.0}
).set_placement((sx + 7, arrow_y + 1.5), align=TextEntityAlignment.MIDDLE_CENTER)

# ============================================================
# Piece 2: Seat Cushion Bottom — 48" x 18"
# ============================================================
bx, by = 5, 55
bw, bh = 48, 18

draw_rect(bx, by, bw, bh)
add_dim_h(bx, by, bw)
add_dim_v(bx, by, bh)
add_label(bx + bw / 2, by + bh / 2, 'SEAT CUSHION BOTTOM')
add_label(bx + bw / 2, by + bh / 2 - 3, '48" x 18"')

# ============================================================
# Piece 3: Boxing Strip (Front + Sides) — 48" x 4"
# ============================================================
fx, fy = 5, 40
fw, fh = 48, 4

draw_rect(fx, fy, fw, fh)
add_dim_h(fx, fy, fw)
add_dim_v(fx, fy, fh, offset=-4)
add_label(fx + fw / 2, fy + fh / 2, 'BOXING STRIP — FRONT + SIDES')
add_label(fx + fw / 2, fy + fh / 2 - 2, '48" x 4"')

# ============================================================
# Piece 4: Boxing Strip (Back) — 48" x 4"
# ============================================================
bkx, bky = 5, 28
bkw, bkh = 48, 4

draw_rect(bkx, bky, bkw, bkh)
add_dim_h(bkx, bky, bkw)
add_dim_v(bkx, bky, bkh, offset=-4)
add_label(bkx + bkw / 2, bky + bkh / 2, 'BOXING STRIP — BACK')
add_label(bkx + bkw / 2, bky + bkh / 2 - 2, '48" x 4"')

# ============================================================
# Piece 5: Zipper Panel (optional) — 48" x 2"
# ============================================================
zx, zy = 5, 18
zw, zh = 48, 2

draw_rect(zx, zy, zw, zh)
add_dim_h(zx, zy, zw)
add_dim_v(zx, zy, zh, offset=-4)
add_label(zx + zw / 2, zy + zh / 2, 'ZIPPER PANEL (OPTIONAL)')
add_label(zx + zw / 2, zy - 2, '48" x 2"', height=1.2)

# Zipper indicator dashed line
for i in range(0, 46, 3):
    msp.add_line(
        (zx + 1 + i, zy + zh / 2),
        (zx + 2.5 + i, zy + zh / 2),
        dxfattribs={'layer': 'DIMENSIONS'}
    )

# ============================================================
# Cut List / Notes (right side)
# ============================================================
nx, ny = 70, 105

msp.add_text(
    'CUT LIST',
    dxfattribs={'layer': 'TITLE', 'height': 2.5}
).set_placement((nx, ny), align=TextEntityAlignment.LEFT)

notes = [
    '1. Seat Top:      48" x 18"   (x1)',
    '2. Seat Bottom:   48" x 18"   (x1)',
    '3. Boxing Front:  48" x 4"    (x1)',
    '4. Boxing Back:   48" x 4"    (x1)',
    '5. Zipper Panel:  48" x 2"    (x1, optional)',
    '',
    'FABRIC REQUIRED: ~2.5 yards (54" wide)',
    'FOAM: 48" x 18" x 3" HR foam',
    'ZIPPER: 45" #5 nylon coil',
    '',
    'NOTES:',
    '- All pieces include 0.5" seam allowance',
    '- Mark grain direction on all pieces',
    '- Boxing strip: can be one continuous piece',
    '  or joined at corners with 0.5" seam',
    '- Welt cord: ~140" (optional, not shown)',
]

for i, line in enumerate(notes):
    msp.add_text(
        line,
        dxfattribs={'layer': 'TEXT', 'height': 1.3}
    ).set_placement((nx, ny - 4 - (i * 3)), align=TextEntityAlignment.LEFT)

# ============================================================
# Border frame
# ============================================================
msp.add_lwpolyline(
    [(-2, 5), (145, 5), (145, 138), (-2, 138), (-2, 5)],
    dxfattribs={'layer': 'TITLE'}
)

# Footer
msp.add_text(
    'Empire Workroom | Custom Window Treatments & Upholstery | empirebox.store',
    dxfattribs={'layer': 'TEXT', 'height': 1.2}
).set_placement((72, 7), align=TextEntityAlignment.MIDDLE_CENTER)

# ============================================================
# Save
# ============================================================
output_path = 'uploads/bench_upholstery_layout.dxf'
doc.saveas(output_path)
print(f'DXF saved to {output_path}')
