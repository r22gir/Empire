"""UNITS CHECK: confirm gate converts pixels → real inches."""
import sys, io
sys.path.insert(0, '/home/rg/empire-repo-main/backend')
from app.services.drawing.templates import render_spec
from app.services.drawing.templates.drapery_render import _compute_drapery_scale, DRAPE_PROJECTION_IN

pdf = render_spec({
    'product_type': 'pinch_pleat',
    'dims': {'width': 87, 'height': 84, 'returns': 4, 'fullness': 2.5},
    'fabric_sku': 'BP10814-2',
})
import pdfplumber
with pdfplumber.open(io.BytesIO(pdf)) as p:
    page0 = p.pages[0]
    img = page0.to_image(resolution=150).original

SIDE_X_IN, SIDE_Y_IN, SIDE_W_IN, SIDE_H_IN = 5.19, 0.86, 2.49, 6.26
DPI = 150
page_h = img.height
vp_x0 = int(round(SIDE_X_IN * DPI))
vp_x1 = int(round((SIDE_X_IN + SIDE_W_IN) * DPI))
vp_y0 = int(round(page_h - ((SIDE_Y_IN + SIDE_H_IN) * DPI)))
vp_y1 = int(round(page_h - (SIDE_Y_IN * DPI)))
side = img.crop((vp_x0, vp_y0, vp_x1, vp_y1))
print(f'side crop: {side.size}')

bg = (247, 243, 234)
depths, fronts = [], []
for y in range(side.height):
    leftmost, rightmost = None, None
    for x in range(side.width):
        p = side.load()[x, y]
        if len(p) >= 4 and p[3] == 0:
            continue
        d = abs(p[0]-bg[0])+abs(p[1]-bg[1])+abs(p[2]-bg[2])
        if d > 30:
            if leftmost is None: leftmost = x
            rightmost = x
    if leftmost is not None and rightmost is not None and rightmost > leftmost:
        depths.append((rightmost - leftmost) / DPI)
        fronts.append(leftmost / DPI)

import statistics
mean_depth_sheet = statistics.mean(depths)
stddev_front_sheet = statistics.pstdev(fronts)
print(f'n fabric rows: {len(depths)}')
print(f'mean depth (sheet\"): {mean_depth_sheet:.4f}')
print(f'front-edge x stddev (sheet\"): {stddev_front_sheet:.4f}')
