#!/usr/bin/env python3
"""Empire Workroom shop drawings — Maggie O'Neil / The Willard Hotel.
Sheet 1: Curved bench. Sheet 2: Channel wall panel."""
import math
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.colors import HexColor, black, white
from reportlab.pdfgen import canvas

PAGE = landscape(letter)          # 792 x 612 pt
W, H = PAGE
CARAMEL = HexColor("#E3B884")
CARAMEL_LT = HexColor("#F1D9BC")
GRAY = HexColor("#888888")
LGRAY = HexColor("#CCCCCC")
DIM = HexColor("#333333")

OUT = "/home/claude/ONeil_Willard_Bench_Panel_Drawings.pdf"
c = canvas.Canvas(OUT, pagesize=PAGE)

# ---------------------------------------------------------------- helpers
def dim_h(x1, x2, y, label, above=True, fs=8):
    """Horizontal dimension line with ticks."""
    c.saveState()
    c.setStrokeColor(DIM); c.setLineWidth(0.6)
    c.line(x1, y, x2, y)
    for x in (x1, x2):
        c.line(x, y - 4, x, y + 4)
        # 45-degree tick
        c.line(x - 2.5, y - 2.5, x + 2.5, y + 2.5)
    c.setFont("Helvetica", fs); c.setFillColor(DIM)
    ty = y + 3 if above else y - fs - 1
    c.drawCentredString((x1 + x2) / 2, ty, label)
    c.restoreState()

def dim_v(x, y1, y2, label, right=True, fs=8):
    """Vertical dimension line with ticks."""
    c.saveState()
    c.setStrokeColor(DIM); c.setLineWidth(0.6)
    c.line(x, y1, x, y2)
    for y in (y1, y2):
        c.line(x - 4, y, x + 4, y)
        c.line(x - 2.5, y - 2.5, x + 2.5, y + 2.5)
    c.setFont("Helvetica", fs); c.setFillColor(DIM)
    c.saveState()
    c.translate(x + (9 if right else -4), (y1 + y2) / 2)
    c.rotate(90)
    c.drawCentredString(0, 0, label)
    c.restoreState()
    c.restoreState()

def ext_line(x1, y1, x2, y2):
    c.saveState(); c.setStrokeColor(GRAY); c.setLineWidth(0.4)
    c.setDash(1, 0); c.line(x1, y1, x2, y2); c.restoreState()

def view_label(x, y, text):
    c.saveState()
    c.setFont("Helvetica-Bold", 10); c.setFillColor(black)
    c.drawCentredString(x, y, text)
    c.setLineWidth(1); c.line(x - 60, y - 3, x + 60, y - 3)
    c.restoreState()

def title_block(sheet_no, item_name, dims_line, extra_rows, notes):
    """Right-hand column title block + notes."""
    bx, bw = W - 250, 226
    by, bh = 36, 336
    c.saveState()
    c.setLineWidth(1.2); c.rect(bx, by, bw, bh)
    y = by + bh - 26
    c.setFont("Helvetica-Bold", 15)
    c.drawCentredString(bx + bw / 2, y, "EMPIRE WORKROOM")
    y -= 12
    c.setFont("Helvetica", 7)
    c.drawCentredString(bx + bw / 2, y, "CUSTOM UPHOLSTERY & FABRICATION")
    y -= 9
    c.drawCentredString(bx + bw / 2, y, "5124 Frolich Ln, Hyattsville, MD 20781")
    y -= 9
    c.drawCentredString(bx + bw / 2, y, "(703) 213-6484  |  workroom@empirebox.store")
    y -= 8
    c.setLineWidth(0.8); c.line(bx, y, bx + bw, y)
    y -= 14
    rows = [
        ("CLIENT:", "Maggie O'Neil"),
        ("SITE:", "The Willard Hotel"),
        ("SHEET:", sheet_no),
        ("ITEM:", item_name),
        ("DIMENSIONS:", dims_line),
    ] + extra_rows + [
        ("MATERIAL:", "Caramel faux leather"),
        ("DATE:", "07/13/2026"),
        ("DRAWN BY:", "Empire Workroom"),
        ("STATUS:", "FOR FOUNDER REVIEW"),
    ]
    for k, v in rows:
        c.setFont("Helvetica-Bold", 7.5); c.drawString(bx + 8, y, k)
        c.setFont("Helvetica", 7.5)
        # wrap long values
        maxw = bw - 92
        words, line = v.split(), ""
        for w_ in words:
            t = (line + " " + w_).strip()
            if c.stringWidth(t, "Helvetica", 7.5) <= maxw:
                line = t
            else:
                c.drawString(bx + 84, y, line); y -= 10; line = w_
        c.drawString(bx + 84, y, line)
        y -= 13
    c.setLineWidth(0.8); c.line(bx, y + 5, bx + bw, y + 5)
    y -= 8
    c.setFont("Helvetica-Bold", 8); c.drawString(bx + 8, y, "NOTES / ASSUMPTIONS — CONFIRM:")
    y -= 11
    c.setFont("Helvetica", 7)
    for n in notes:
        for seg in wrap(n, bw - 20, 7):
            c.drawString(bx + 10, y, seg); y -= 9
        y -= 2
    c.restoreState()

def wrap(text, maxw, fs):
    words, out, line = text.split(), [], ""
    for w_ in words:
        t = (line + " " + w_).strip()
        if c.stringWidth(t, "Helvetica", fs) <= maxw:
            line = t
        else:
            out.append(line); line = w_
    out.append(line)
    return out

def border():
    c.setLineWidth(1.5); c.rect(18, 18, W - 36, H - 36)

# ================================================================ SHEET 1
border()

# ---- PLAN VIEW (curved bench), top-left region -------------------------
# Assumed wall radius 120". Back arc length 87" -> angle 41.54 deg.
Rb, depth = 120.0, 26.0
theta = 87.0 / Rb                     # radians
half = theta / 2
Rf = Rb - depth
S = 3.4                               # pt per inch (plan)
# center of arcs — place so back-arc crown lands at y=545 (inside border)
cx = 265
cy = 545 - Rb * 3.4                   # crown = cy + Rb*S
def pt(r, ang):                       # ang measured from +90deg center
    return (cx + r * S * math.sin(ang), cy + r * S * math.cos(ang))

c.saveState()
# filled bench body between arcs
p = c.beginPath()
a0, a1 = -half, half
steps = 40
first = pt(Rb, a0)
p.moveTo(*first)
for i in range(steps + 1):
    p.lineTo(*pt(Rb, a0 + (a1 - a0) * i / steps))
for i in range(steps + 1):
    p.lineTo(*pt(Rf, a1 - (a1 - a0) * i / steps))
p.close()
c.setFillColor(CARAMEL_LT); c.setStrokeColor(black); c.setLineWidth(1.4)
c.drawPath(p, stroke=1, fill=1)

# seat front edge welt line (slightly inset arc)
p2 = c.beginPath()
for i in range(steps + 1):
    x, y = pt(Rf + 2.0, a0 + (a1 - a0) * i / steps)
    if i == 0: p2.moveTo(x, y)
    else: p2.lineTo(x, y)
c.setLineWidth(0.5); c.setStrokeColor(GRAY); c.drawPath(p2)

# leg positions (plan, dashed squares under seat): 6 legs along centerline
c.setDash(2, 2); c.setStrokeColor(GRAY); c.setLineWidth(0.7)
Rc = Rb - depth / 2
for i in range(6):
    ang = a0 + (a1 - a0) * (0.08 + 0.84 * i / 5)
    lx, ly = pt(Rc, ang)
    ls = 2.5 * S
    c.rect(lx - ls / 2, ly - ls / 2, ls, ls)
c.setDash(1, 0)

# wall reference arc behind back
p3 = c.beginPath()
for i in range(steps + 1):
    x, y = pt(Rb + 1.5, a0 - 0.06 + (a1 - a0 + 0.12) * i / steps)
    if i == 0: p3.moveTo(x, y)
    else: p3.lineTo(x, y)
c.setDash(4, 3); c.setStrokeColor(GRAY); c.setLineWidth(0.8); c.drawPath(p3)
c.setDash(1, 0)
c.setFont("Helvetica-Oblique", 7); c.setFillColor(GRAY)
wx, wy = pt(Rb + 6, half * 0.9)
c.drawString(wx - 30, wy + 4, "WALL LINE (FIELD VERIFY CURVATURE)")

# ARMREST at left end: 4" along back curve, full depth, 6"-24" AFF
arm_a1 = a0                      # bench left end
arm_a0 = a0 - 4.0 / Rb           # armrest extends 4" beyond
pa = c.beginPath()
pa.moveTo(*pt(Rb, arm_a0))
for i in range(11):
    pa.lineTo(*pt(Rb, arm_a0 + (arm_a1 - arm_a0) * i / 10))
for i in range(11):
    pa.lineTo(*pt(Rf, arm_a1 - (arm_a1 - arm_a0) * i / 10))
pa.close()
c.setFillColor(HexColor("#D9A868")); c.setStrokeColor(black); c.setLineWidth(1.2)
c.drawPath(pa, stroke=1, fill=1)
lax, lay = pt(Rf - 4, arm_a0)
c.setFont("Helvetica-Bold", 7); c.setFillColor(DIM)
c.drawString(lax - 12, lay - 16, 'ARMREST 4"')
c.drawString(lax - 12, lay - 25, 'TOP 24" AFF')
# dimension: back arc 87 + overall 91
c.setFont("Helvetica-Bold", 9); c.setFillColor(DIM)
c.drawCentredString(cx, cy + Rb * S + 10, '87" BENCH ALONG BACK CURVE  ·  91" OVERALL W/ ARMREST')
# depth dimension: RADIAL — perpendicular to the curve
ang_d = 0.26
import math as _m
p_in, p_out = pt(Rf, ang_d), pt(Rb, ang_d)
c.saveState()
c.setStrokeColor(DIM); c.setLineWidth(0.6)
c.line(p_in[0], p_in[1], p_out[0], p_out[1])
dxv, dyv = _m.sin(ang_d), _m.cos(ang_d)      # radial direction
pxv, pyv = -dyv, dxv                          # perpendicular for ticks
for q in (p_in, p_out):
    c.line(q[0] - pxv * 4, q[1] - pyv * 4, q[0] + pxv * 4, q[1] + pyv * 4)
midx, midy = (p_in[0] + p_out[0]) / 2, (p_in[1] + p_out[1]) / 2
c.translate(midx, midy)
c.rotate(90 - _m.degrees(ang_d))
c.setFont("Helvetica", 8); c.setFillColor(DIM)
c.drawCentredString(0, 4, '26" SEAT DEPTH (RADIAL)')
c.restoreState()
# radius note
c.setFont("Helvetica-Oblique", 7.5); c.setFillColor(GRAY)
c.drawCentredString(cx, cy + Rf * S - 26, 'PLAN RADIUS R120" (BACK) — ASSUMED, FIELD VERIFY')
c.restoreState()
view_label(cx, cy + Rf * S - 46, "PLAN VIEW — CONCAVE CURVE TO WALL")

# ---- FRONT ELEVATION (developed), bottom-left --------------------------
Se = 3.2
ex0, ey = 52, 80                      # armrest left edge
arm_w, arm_h = 4 * Se, 18 * Se        # armrest: 6"-24" AFF
ex = ex0 + arm_w                      # bench left edge
ew, body_h, leg_h = 87 * Se, 11 * Se, 6 * Se
# legs (6 square legs, 2.5")
leg_w = 2.5 * Se
leg_xs = [ex + 4, ex + ew * 0.2, ex + ew * 0.4, ex + ew * 0.6 - leg_w,
          ex + ew * 0.8 - leg_w, ex + ew - leg_w - 4]
c.setFillColor(HexColor("#8B6534")); c.setStrokeColor(black); c.setLineWidth(0.9)
for lx in leg_xs:
    c.rect(lx, ey, leg_w, leg_h, stroke=1, fill=1)
# upholstered body
c.setFillColor(CARAMEL); c.setLineWidth(1.4)
c.roundRect(ex, ey + leg_h, ew, body_h, 4, stroke=1, fill=1)
# armrest: independent piece, 6" AFF to 24" AFF, left side
c.setFillColor(HexColor("#D9A868")); c.setLineWidth(1.4)
c.roundRect(ex0, ey + leg_h, arm_w, arm_h, 3, stroke=1, fill=1)
dim_v(ex0 - 14, ey, ey + leg_h + arm_h, '24" AFF', right=False)
dim_h(ex0, ex0 + arm_w, ey + leg_h + arm_h + 8, '4"', above=True)
# dims
dim_h(ex, ex + ew, ey - 14, '87"', above=False)
dim_h(ex0, ex + ew, ey - 34, '91" OVERALL', above=False)
dim_v(ex + ew + 14, ey, ey + leg_h + body_h, '17" OVERALL', right=True)
dim_v(ex + ew + 34, ey, ey + leg_h, '6" LEG', right=True)
dim_v(ex + ew + 34, ey + leg_h, ey + leg_h + body_h, '11" BODY', right=True)
ext_line(ex + ew, ey, ex + ew + 38, ey)
ext_line(ex + ew, ey + leg_h, ex + ew + 38, ey + leg_h)
ext_line(ex + ew, ey + leg_h + body_h, ex + ew + 38, ey + leg_h + body_h)
c.setFont("Helvetica", 7); c.setFillColor(DIM)
c.drawString(ex, ey - 28, 'LEGS: CUSTOM SQUARE EXPOSED WOOD, 2.5" SQ (ASSUMED) × 6" H MAX — QTY 6')
view_label(ex + ew / 2, ey + leg_h + body_h + 16, "FRONT ELEVATION (DEVELOPED)")

# ---- SIDE ELEVATION, bottom-middle-right (left of title block) ----------
sx, sy = 402, 80
sw = 26 * Se
c.setFillColor(HexColor("#8B6534")); c.setLineWidth(0.9)
c.rect(sx + 3, sy, leg_w, leg_h, stroke=1, fill=1)
c.rect(sx + sw - leg_w - 3, sy, leg_w, leg_h, stroke=1, fill=1)
# armrest face (26" deep, 6"-24" AFF) occludes bench from this side
c.setFillColor(HexColor("#D9A868")); c.setLineWidth(1.4)
c.roundRect(sx, sy + leg_h, sw, arm_h, 4, stroke=1, fill=1)
# bench seat line beyond (dashed)
c.setDash(3, 2); c.setStrokeColor(GRAY); c.setLineWidth(0.8)
c.line(sx + 2, sy + leg_h + body_h, sx + sw - 2, sy + leg_h + body_h)
c.setDash(1, 0)
c.setFont("Helvetica-Oblique", 6); c.setFillColor(GRAY)
c.drawString(sx + 4, sy + leg_h + body_h + 3, 'SEAT 17" BEYOND (DASHED)')
dim_h(sx, sx + sw, sy - 14, '26"', above=False)
dim_v(sx - 14, sy, sy + leg_h + arm_h, '24" AFF', right=False)
dim_v(sx + sw + 14, sy + leg_h, sy + leg_h + arm_h, '18" PIECE', right=True)
view_label(sx + sw / 2, sy + leg_h + arm_h + 16, "LEFT SIDE ELEV. — ARMREST")

# ---- ISOMETRIC ASSEMBLY VIEW (curved, center-right) ---------------------
iso_ox, iso_oy, iso_s = 300, 220, 2.0
SAG = 19.5  # drawn at 2.5x true sagitta (7.8") so the curve reads clearly
def sagf(x):
    t = (x - 43.5) / 43.5
    return SAG * (1 - t * t)
def iso(x, y, z):
    yy = y + sagf(x)
    return (iso_ox + (x * 0.95 + yy * 0.45) * iso_s,
            iso_oy + (z * 1.0 + yy * 0.28) * iso_s)
def band(y0, z0, z1, fill, lw=0.9, x0=0, x1=87, samples=28):
    """Curved band face at constant depth y0 between heights z0..z1."""
    p = c.beginPath()
    pts_top = [iso(x0 + (x1 - x0) * i / samples, y0, z1) for i in range(samples + 1)]
    pts_bot = [iso(x1 - (x1 - x0) * i / samples, y0, z0) for i in range(samples + 1)]
    p.moveTo(*pts_top[0])
    for q in pts_top[1:] + pts_bot:
        p.lineTo(*q)
    p.close()
    c.setFillColor(fill); c.setStrokeColor(black); c.setLineWidth(lw)
    c.drawPath(p, stroke=1, fill=1)
def slab(y0, y1, z, fill, lw=0.9, samples=28):
    """Curved horizontal face at height z between depths y0..y1."""
    p = c.beginPath()
    front = [iso(87 * i / samples, y0, z) for i in range(samples + 1)]
    back = [iso(87 - 87 * i / samples, y1, z) for i in range(samples + 1)]
    p.moveTo(*front[0])
    for q in front[1:] + back:
        p.lineTo(*q)
    p.close()
    c.setFillColor(fill); c.setStrokeColor(black); c.setLineWidth(lw)
    c.drawPath(p, stroke=1, fill=1)

CAR_TOP = HexColor("#EDC79B"); CAR_FRONT = HexColor("#DDA96C"); CAR_SIDE = HexColor("#C08B4E")
WOOD = HexColor("#8B6534")
# panel (behind, follows wall curve): front at depth 27, thickness 2, z 17..41
slab(27, 29, 41, CAR_TOP)                      # panel top
band(27, 17, 41, CAR_FRONT)                    # panel front (curved)
# panel right end cap
p = c.beginPath()
p.moveTo(*iso(87, 27, 17)); p.lineTo(*iso(87, 29, 17))
p.lineTo(*iso(87, 29, 41)); p.lineTo(*iso(87, 27, 41)); p.close()
c.setFillColor(CAR_SIDE); c.setLineWidth(0.9); c.drawPath(p, stroke=1, fill=1)
# channel seams on curved panel front
c.setStrokeColor(HexColor("#9a7443")); c.setLineWidth(0.7)
step = 86.125 / 8 + 0.125
for i in range(1, 8):
    xx = i * step - 0.0625
    a = iso(xx, 27, 17.5); b = iso(xx, 27, 40.5)
    c.line(a[0], a[1], b[0], b[1])
# bench body z 6..17 (curved)
slab(0, 26, 17, CAR_TOP)                       # seat top
band(0, 6, 17, CAR_FRONT)                      # bench front (curved)
# bench right end cap
p = c.beginPath()
p.moveTo(*iso(87, 0, 6)); p.lineTo(*iso(87, 26, 6))
p.lineTo(*iso(87, 26, 17)); p.lineTo(*iso(87, 0, 17)); p.close()
c.setFillColor(CAR_SIDE); c.setLineWidth(0.9); c.drawPath(p, stroke=1, fill=1)
# legs (front row of 3, following the curve)
for lx in (2, 42.25, 82.5):
    band(2, 0, 6, WOOD, 0.6, x0=lx, x1=lx + 2.5, samples=4)
# ARMREST at left end: x -4..0, depth 0..26, z 6..24
ARM_F = HexColor("#D9A868"); ARM_T = HexColor("#E8C089"); ARM_S = HexColor("#B98A50")
# INSIDE face (x=0 plane, exposed above the seat, z 17..24)
p = c.beginPath()
p.moveTo(*iso(0, 0, 17)); p.lineTo(*iso(0, 26, 17))
p.lineTo(*iso(0, 26, 24)); p.lineTo(*iso(0, 0, 24)); p.close()
c.setFillColor(HexColor("#C69660")); c.setStrokeColor(black); c.setLineWidth(0.9)
c.drawPath(p, stroke=1, fill=1)
# top slab
p = c.beginPath()
tf = [iso(-4 + 4 * i / 8, 0, 24) for i in range(9)]
tb = [iso(0 - 4 * i / 8, 26, 24) for i in range(9)]
p.moveTo(*tf[0])
for q in tf[1:] + tb:
    p.lineTo(*q)
p.close()
c.setFillColor(ARM_T); c.setStrokeColor(black); c.setLineWidth(0.9)
c.drawPath(p, stroke=1, fill=1)
# (outer x=-4 cap is a hidden face in this projection — not drawn)
# front band
band(0, 6, 24, ARM_F, 0.9, x0=-4, x1=0, samples=4)
# labels
c.setFont("Helvetica", 7); c.setFillColor(DIM)
la = iso(-8, 0, 20); c.drawRightString(la[0] - 2, la[1], '24" ARM')
la = iso(90, 0, 11); c.drawString(la[0] + 3, la[1], '17" BENCH')
la = iso(90, 27, 30); c.drawString(la[0] + 3, la[1], '24" PANEL')
la = iso(44, 0, -4); c.drawCentredString(la[0], la[1] - 6, '87" ALONG BACK CURVE')
view_label(iso_ox + 105, iso_oy - 24, "ISOMETRIC — ASSEMBLY (CURVED)")
c.setFont("Helvetica-Oblique", 6.5); c.setFillColor(GRAY)
c.drawCentredString(iso_ox + 105, iso_oy - 34, 'curve exaggerated for clarity — true sagitta 7-13/16" at R120"')

title_block(
    "1 of 2",
    "CURVED BENCH + LEFT ARMREST",
    '87" W (back arc) × 26" D × 17" H',
    [("ARMREST:", 'Left (facing): 4" W × 26" D, curved'),
     ("ARM HT:", '6"–24" AFF (18" piece, no legs)'),
     ("LEGS:", '6 sq. exposed wood, 6" max'),
     ("BACK:", "NONE — see Sheet 2 wall panel")],
    [
        'Bench replaces existing curved tufted banquette in wall alcove.',
        'Armrest: independent piece on bench LEFT side, follows curve; top 7" above seat.',
        'Overall 91" along back curve (87" + 4" arm) — CONFIRM fits site, else arm goes inside 87".',
        'Curve radius R120" assumed — FIELD VERIFY wall curvature before build.',
        'Leg cross-section 2.5" sq and qty 6 assumed — confirm.',
    ],
)
c.showPage()

# ================================================================ SHEET 2
border()
# ---- PANEL ELEVATION ----------------------------------------------------
Sp = 5.0
pw, ph = 87 * Sp, 24 * Sp
px, py = 55, 300
# backer
c.setFillColor(CARAMEL_LT); c.setStrokeColor(black); c.setLineWidth(1.4)
c.rect(px, py, pw, ph, stroke=1, fill=1)
# channels: 8 @ 10-49/64" (10.765625"), reveals 7 @ 1/8"
ch_in, rv_in = 86.125 / 8, 0.125
ch_w, rv = ch_in * Sp, rv_in * Sp
x = px
for i in range(8):
    c.setFillColor(CARAMEL); c.setLineWidth(0.9)
    c.roundRect(x, py + 2, ch_w, ph - 4, 6, stroke=1, fill=1)
    c.setFont("Helvetica", 7); c.setFillColor(HexColor("#7a5a33"))
    c.drawCentredString(x + ch_w / 2, py + ph / 2 - 3, f"C{i+1}")
    x += ch_w + rv
# dims
dim_h(px, px + pw, py + ph + 16, '87" OVERALL', above=True)
dim_h(px, px + ch_w, py - 14, '10-49/64" CHANNEL (TYP \u00d7 8)', above=False)
c.setFont("Helvetica", 7.5); c.setFillColor(DIM)
c.drawString(px + ch_w + 8, py - 37, '1/8" REVEAL (TYP \u00d7 7)')
ext_line(px + ch_w, py, px + ch_w, py - 40)
ext_line(px + ch_w + rv, py, px + ch_w + rv, py - 40)
dim_v(px - 16, py, py + ph, '24"', right=False)
c.setFont("Helvetica-Bold", 8.5); c.setFillColor(DIM)
c.drawString(px, py - 56, 'LAYOUT MATH: 8 \u00d7 10-49/64" (10.766") CHANNELS + 7 \u00d7 1/8" REVEALS = 86.125" + 0.875" = 87" — FLUSH BOTH ENDS')
view_label(px + pw / 2, py + ph + 36, "WALL PANEL — FRONT ELEVATION")

# ---- MOUNTING SECTION (small, lower-left) -------------------------------
mx, my = 80, 90
# wall
c.setFillColor(LGRAY); c.setLineWidth(1)
c.rect(mx, my, 8, 130, stroke=1, fill=1)
# panel section (2" thick) mounted on wall, bottom at 17" AFF
Sm = 2.6
p_th = 2 * Sm
p_h = 24 * Sm
floor_y = my
seat_y = floor_y + 17 * Sm
c.setFillColor(CARAMEL)
c.rect(mx + 8, seat_y, p_th, p_h, stroke=1, fill=1)
# floor line
c.setLineWidth(1.6); c.line(mx - 12, floor_y, mx + 150, floor_y)
c.setFont("Helvetica", 7); c.setFillColor(DIM)
c.drawString(mx + 120, floor_y - 8, "FL")
# bench ghost
c.setDash(3, 2); c.setStrokeColor(GRAY); c.setLineWidth(0.8)
c.rect(mx + 8 + p_th + 4, floor_y + 6 * Sm, 26 * Sm, 11 * Sm)
c.setDash(1, 0)
c.setFont("Helvetica-Oblique", 6.5); c.setFillColor(GRAY)
c.drawString(mx + 8 + p_th + 8, floor_y + 12 * Sm, "BENCH (SHEET 1)")
dim_v(mx + 8 + p_th + 4 + 26 * Sm + 14, floor_y, seat_y, '17" AFF', right=True)
dim_v(mx + 8 + p_th + 4 + 26 * Sm + 14, seat_y, seat_y + p_h, '24" PANEL', right=True)
view_label(mx + 90, my + 150 + 40, "MOUNTING SECTION")
c.setFont("Helvetica", 7); c.setFillColor(DIM)
c.drawString(mx - 10, my - 22, 'PANEL BOTTOM AT 17" AFF (SEAT LINE) — ASSUMED, CONFIRM')
c.drawString(mx - 10, my - 33, 'FRENCH CLEAT MOUNT (ASSUMED). PANEL THICKNESS 2" (ASSUMED).')

title_block(
    "2 of 2",
    "UPHOLSTERED CHANNEL WALL PANEL",
    '87" W × 24" H, wall-mounted',
    [("CHANNELS:", '8 @ 10-49/64" W \u00d7 24" H, vertical'),
     ("REVEALS:", '7 @ 1/8" between channels')],
    [
        'Mounted behind Sheet 1 bench; reads as bench back. Top of assembly ~41" AFF.',
        'Panel bottom at 17" AFF (seat line) — ASSUMED, confirm.',
        'FIELD VERIFY wall curvature — if curved, panel to be segmented/kerfed to follow wall.',
        'French cleat mounting and 2" panel thickness assumed — confirm.',
    ],
)
c.showPage()
c.save()
print("wrote", OUT)
