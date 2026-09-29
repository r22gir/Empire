#!/usr/bin/env python3
"""GOLDEN REFERENCE — Empire B2 sheet style, flat_fold roman shade.
The target M3 ports into b2_renderers.py. Willard sheet language throughout."""
import math, random
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib.units import inch
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

PAGE = landscape(letter); W, H = PAGE
PAPER = HexColor("#f7f3ea")
INK   = HexColor("#20241f")
LIGHT = HexColor("#6f6a5e")
GOLD  = HexColor("#b8912f")
ORANGE= HexColor("#b25a1d")
DIM   = HexColor("#8a6a3a")
EMER  = HexColor("#123a2a")
EMER_D= HexColor("#0c2b1f")
LEAF  = HexColor("#2f7350")
LEAF2 = HexColor("#4a9268")
BLOSS = HexColor("#ead9c0")
CREAM2= HexColor("#efe8d8")

def ls_text(c, x, y, s, size, color=INK, tracking=1.6, bold=True, center=False, right=False):
    """letterspaced uppercase — the Willard signature"""
    f = "Helvetica-Bold" if bold else "Helvetica"
    c.setFont(f, size); c.setFillColor(color)
    s = s.upper()
    total = sum(c.stringWidth(ch, f, size) + tracking for ch in s) - tracking
    if center: x -= total/2
    if right: x -= total
    for ch in s:
        c.drawString(x, y, ch)
        x += c.stringWidth(ch, f, size) + tracking

c = canvas.Canvas("/mnt/user-data/outputs/GOLDEN_flat_fold_empire.pdf", pagesize=PAGE)
c.setTitle("GOLDEN — Empire B2 Sheet — Flat Fold")
c.setLineJoin(1); c.setLineCap(1)
c.setFillColor(PAPER); c.rect(0,0,W,H,fill=1,stroke=0)

M = 0.32*inch                      # outer margin
c.setStrokeColor(INK); c.setLineWidth(1.1)
c.rect(M, M, W-2*M, H-2*M, fill=0, stroke=1)

# ═══ HEADER BAND ═══
BH = 0.92*inch
c.setFillColor(INK); c.rect(M, H-M-BH, W-2*M, BH, fill=1, stroke=0)
ls_text(c, M+0.28*inch, H-M-0.34*inch, "EMPIRE WORKROOM  ·  SHOP DRAWING", 9, HexColor("#cfc8b8"), tracking=2.4)
c.setFont("Helvetica-Bold", 21); c.setFillColor(HexColor("#f7f3ea"))
c.drawString(M+0.27*inch, H-M-BH+0.17*inch, "FLAT FOLD ROMAN SHADE")
ls_text(c, W-M-0.28*inch, H-M-0.34*inch, "CST-DRAFT · 07/26/2026 · REV 0", 8, GOLD, tracking=1.4, right=True)
c.setFont("Helvetica", 8.5); c.setFillColor(HexColor("#cfc8b8"))
c.drawRightString(W-M-0.28*inch, H-M-BH+0.19*inch,
                  "38\" W × 64\" H · 9 folds @ 7-1/8\" · inside mount (ASSUMED 2-1/2\" — VERIFY)")

# ═══ FOOTER BAND ═══
FH = 0.42*inch
c.setFillColor(INK); c.rect(M, M, W-2*M, FH, fill=1, stroke=0)
c.setFont("Helvetica-Bold", 8); c.setFillColor(PAPER)
c.drawString(M+0.28*inch, M+FH/2-3, "EMPIRE WORKROOM · HYATTSVILLE, MD · (703) 213-6484")
ls_text(c, W/2+0.72*inch, M+FH/2-3, "FOR DISCUSSION — NOT FOR CONSTRUCTION", 7.5, ORANGE, tracking=1.2, center=True)
c.setFont("Helvetica-Bold", 8.5); c.setFillColor(PAPER)
c.drawRightString(W-M-0.28*inch, M+FH/2-3, "SHEET B2 · 1 OF 1")

# layout columns
top = H-M-BH-0.14*inch
bot = M+FH+0.12*inch
col_r = W-M-2.62*inch              # title column left edge
frame = lambda x,y,w,h: (c.setStrokeColor(INK), c.setLineWidth(0.8), c.rect(x,y,w,h))

# ═══ VIEWPORT 1 — FRONT ELEVATION (in-room context, 108" ceiling REF) ═══
CEIL, HEAD, SHW_IN, SHH_IN = 108.0, 96.0, 38.0, 64.0
SILL = HEAD - SHH_IN                      # 32" AFF
v1x, v1w = M+0.18*inch, 4.55*inch
v1y, v1h = bot, top-bot
frame(v1x, v1y, v1w, v1h)
ls_text(c, v1x+8, v1y+v1h-16, "FRONT ELEVATION", 8.5, INK, tracking=1.8)
c.setFont("Helvetica", 7); c.setFillColor(LIGHT)
c.drawString(v1x+8, v1y+v1h-27, 'CEILING 108" REF (ASSUMED) · FABRIC: NYMPHEUS VELVET (BP10814-2)')

s = (v1h-0.86*inch)/CEIL
wall_y = v1y + 0.34*inch                  # floor line y
ceil_y = wall_y + CEIL*s
wx0, wx1 = v1x+0.3*inch, v1x+v1w-0.85*inch
# ceiling + floor
c.setStrokeColor(INK); c.setLineWidth(1.2)
c.line(wx0-6, ceil_y, wx1+6, ceil_y)
c.line(wx0-6, wall_y, wx1+6, wall_y)
c.setFillColor(LIGHT); c.setFont("Helvetica-Oblique", 6.3)
c.drawString(wx0-4, ceil_y+3, 'CEILING — 108" REF')
c.drawString(wx0-4, wall_y-9, "FIN. FLOOR")
# window centered
shw, shh = SHW_IN*s, SHH_IN*s
sx = (wx0+wx1)/2 - shw/2
sy = wall_y + SILL*s
# casing
c.setStrokeColor(HexColor("#8a8271")); c.setLineWidth(2.2)
c.rect(sx-4, sy-4, shw+8, shh+8, fill=0, stroke=1)
# mount board (inside, at head)
c.setFillColor(HexColor("#5a4632")); c.setStrokeColor(INK); c.setLineWidth(0.9)
c.rect(sx, sy+shh-4, shw, 4, fill=1, stroke=1)
# fabric field
c.setFillColor(EMER); c.rect(sx, sy, shw, shh, fill=1, stroke=0)
rnd = random.Random(7)
def leaf(cx, cy, L, Wd, rot, col):
    c.saveState(); c.translate(cx,cy); c.rotate(rot)
    c.setFillColor(col)
    p = c.beginPath(); p.moveTo(-L/2, 0)
    p.curveTo(-L/6, Wd/2, L/6, Wd/2, L/2, 0)
    p.curveTo(L/6, -Wd/2, -L/6, -Wd/2, -L/2, 0)
    c.drawPath(p, fill=1, stroke=0)
    c.setStrokeColor(EMER_D); c.setLineWidth(0.35)
    c.line(-L/2*0.8, 0, L/2*0.8, 0); c.restoreState()
def blossom(cx, cy, r):
    for k in range(6):
        a = k*math.pi/3
        c.setFillColor(BLOSS)
        c.circle(cx+r*0.62*math.cos(a), cy+r*0.62*math.sin(a), r*0.42, fill=1, stroke=0)
    c.setFillColor(GOLD); c.circle(cx, cy, r*0.3, fill=1, stroke=0)
for i in range(16):
    leaf(sx+5+rnd.random()*(shw-10), sy+5+rnd.random()*(shh-10),
         9+rnd.random()*10, 5+rnd.random()*4, rnd.random()*180, LEAF if i%2 else LEAF2)
for i in range(5):
    blossom(sx+8+rnd.random()*(shw-16), sy+8+rnd.random()*(shh-16), 3.2+rnd.random()*1.8)
for k in range(1,9):
    fy = sy + shh - k*(shh/9)
    c.setStrokeColor(EMER_D); c.setLineWidth(0.9); c.line(sx, fy, sx+shw, fy)
c.setStrokeColor(INK); c.setLineWidth(1.2); c.rect(sx, sy, shw, shh, fill=0, stroke=1)
c.setFillColor(HexColor("#4a3b2a")); c.rect(sx, sy-3.5, shw, 3.5, fill=1, stroke=1)
# dims: width below; right-side chain floor→sill→head→ceiling
c.setStrokeColor(DIM); c.setLineWidth(0.8); c.setFillColor(DIM); c.setFont("Helvetica-Bold", 7.5)
yd = wall_y-14
c.line(sx, yd, sx+shw, yd)
for x_ in (sx, sx+shw): c.line(x_, yd-3, x_, yd+3); c.line(x_-2.5, yd-2.5, x_+2.5, yd+2.5)
c.drawCentredString(sx+shw/2, yd-10, '38"')
xd = wx1+0.34*inch
c.setLineWidth(0.7); c.setFont("Helvetica", 6.3)
for (ya, yb, lab) in ((wall_y, sy, '32"'), (sy, sy+shh, '64" SHADE'), (sy+shh, ceil_y, '12"')):
    c.line(xd, ya, xd, yb)
    for y_ in (ya, yb): c.line(xd-2.5, y_, xd+2.5, y_)
    c.saveState(); c.translate(xd+7, (ya+yb)/2); c.rotate(90)
    c.drawCentredString(0, 0, lab); c.restoreState()

# ═══ VIEWPORT 2 — SIDE SECTION (inside mount: ALL behind the wall line) ═══
v2x = v1x+v1w+0.14*inch
v2w = col_r - v2x - 0.14*inch
frame(v2x, v1y, v2w, v1h)
ls_text(c, v2x+8, v1y+v1h-16, "SIDE SECTION — RAISED", 8.5, INK, tracking=1.8)
c.setFont("Helvetica", 7); c.setFillColor(LIGHT)
c.drawString(v2x+8, v1y+v1h-27, "INSIDE MOUNT · FLAT FOLDS STACK AT HEAD")
s2 = s
LX = 2.4                                   # lateral exaggeration for depth read
wallx = v2x + 0.62*inch + 1.4*inch         # wall FACE; room to the LEFT
f2 = wall_y; c2 = ceil_y
c.setStrokeColor(INK); c.setLineWidth(1.2)
c.line(v2x+0.24*inch, f2, v2x+v2w-0.2*inch, f2)
c.line(v2x+0.24*inch, c2, v2x+v2w-0.2*inch, c2)
c.setFillColor(LIGHT); c.setFont("Helvetica-Oblique", 6.3)
c.drawString(v2x+0.26*inch, c2+3, 'CEILING')
c.drawString(v2x+0.26*inch, f2-9, 'FLOOR')
hy = f2 + HEAD*s2; sly = f2 + SILL*s2
rev_px = 4.75*s2*LX                        # reveal depth to glass
gx = wallx + rev_px
# wall face above head and below sill (thickness hatched to the right)
c.setLineWidth(1.6)
c.line(wallx, f2, wallx, sly)
c.line(wallx, hy, wallx, c2)
for (ya,yb) in ((f2,sly),(hy,c2)):
    n = max(2,int((yb-ya)/15))
    for hz in range(n):
        yv = ya + (yb-ya)*hz/n
        c.setLineWidth(0.5); c.line(wallx, yv, wallx+7, yv+7)
# reveal returns (head + sill jambs) and glass
c.setLineWidth(1.1)
c.line(wallx, hy, gx, hy)
c.line(wallx, sly, gx, sly)
c.setStrokeColor(HexColor("#7d8a94")); c.setLineWidth(1.2)
c.line(gx, sly+1, gx, hy-1)
c.setFillColor(LIGHT); c.setFont("Helvetica-Oblique", 6.0)
c.saveState(); c.translate(gx+8, (sly+hy)/2); c.rotate(90)
c.drawCentredString(0, 0, 'GLASS'); c.restoreState()
# wall-line callout
c.setStrokeColor(DIM); c.setLineWidth(0.6)
c.line(wallx, hy+18, wallx-26, hy+34)
c.setFillColor(DIM); c.setFont("Helvetica-Bold", 6.0)
c.drawRightString(wallx-28, hy+31, "WALL LINE (FACE)")
# mount board inside the reveal at head
c.setFillColor(HexColor("#5a4632")); c.setStrokeColor(INK); c.setLineWidth(0.9)
c.rect(wallx+3, hy-4, rev_px-6, 4, fill=1, stroke=1)
c.setFillColor(INK); c.setFont("Helvetica-Bold", 6.3)
c.drawRightString(wallx-6, hy-3, 'MOUNT BOARD — INSIDE, 2-1/2"')
# RAISED STACK — flat horizontal flaps, shingle-stacked (per site reference)
stack_h = 7.0*s2*1.9
NF = 8
ft = stack_h/NF
x_back  = gx - 4                       # glass side
x_front = wallx + 5                    # front fold edges: plumb, behind wall line
c.setLineJoin(1); c.setLineCap(1)
for k in range(NF):
    ytop = hy - 5 - k*ft
    jit = (k % 2)*1.2 - 0.6
    col = EMER if k % 2 else HexColor("#175340")
    c.setStrokeColor(col); c.setLineWidth(2.0)
    p = c.beginPath()
    p.moveTo(x_back, ytop)
    p.lineTo(x_front + 4 + jit, ytop - ft*0.42)          # slope down-forward
    p.curveTo(x_front + jit, ytop - ft*0.52,             # rounded front edge
              x_front + jit, ytop - ft*0.78,
              x_front + 4 + jit, ytop - ft*0.88)
    p.lineTo(x_back, ytop - ft)                          # return under
    c.drawPath(p, fill=0, stroke=1)
    c.setStrokeColor(EMER_D); c.setLineWidth(0.5)        # shadow under each flap
    c.line(x_front + 6 + jit, ytop - ft*0.92, x_back - 2, ytop - ft - 0.5)
# hem bar under the bottom flap
yf = hy - 5 - NF*ft
c.setFillColor(HexColor("#4a3b2a")); c.setLineWidth(0.8)
c.rect(x_front - 1, yf - 4, (x_back - x_front)*0.7, 4, fill=1, stroke=1)
c.setFillColor(INK); c.setFont("Helvetica-Bold", 6.3)
c.drawRightString(wallx-6, yf-4, "HEM BAR (RAISED)")
c.setFillColor(DIM)
c.drawRightString(wallx-6, hy-stack_h*0.55, 'STACK 7"')
c.drawRightString(wallx-6, hy-stack_h*0.55-8, '(8 FLAT FOLDS, STACKED)')
# lowered ghost: within the reveal, to the sill
mgx = wallx + rev_px*0.45
c.setStrokeColor(LIGHT); c.setLineWidth(0.7); c.setDash(4,3)
c.line(mgx, yf-10, mgx, sly+2)
c.setDash()
c.setFillColor(LIGHT); c.setFont("Helvetica-Oblique", 6.3)
c.drawRightString(wallx-6, sly+8, 'LOWERED — TO SILL (64" DROP)')
# outside-mount doctrine note
c.setFillColor(LIGHT); c.setFont("Helvetica-Oblique", 6.0)
c.drawString(v2x+0.26*inch, f2+14, "OUTSIDE MOUNT (if specified): board + stack sit PROUD of the wall line.")

# ═══ TITLE COLUMN ═══
tx = col_r + 0.16*inch
frame(col_r, bot, W-M-0.18*inch-col_r, top-bot)
rows = [
    ("PROJECT", "—"),
    ("CLIENT", "—"),
    ("FAMILY", "Roman Shades · Flat Fold"),
    ("DIMENSIONS", '38.00" W × 64.00" H'),
    ("FOLDS", '9 @ 7-1/8"'),
    ("MOUNTING", 'Inside — 2-1/2" ASSUMED'),
    ("FABRIC", "Nympheus Velvet — Emerald"),
    ("", "GP&J Baker BP10814-2"),
    ("", '54" W · 35.46" V-repeat'),
    ("SCALE", '1" = 1\'-4"'),
    ("REV", "0 · 07/26/2026"),
]
ty = top-0.34*inch
for lab, val in rows:
    if lab:
        ls_text(c, tx, ty, lab, 7, LIGHT, tracking=1.5)
    c.setFont("Helvetica-Bold" if lab else "Helvetica", 7.5)
    c.setFillColor(INK)
    c.drawString(tx+0.85*inch, ty, val)
    ty -= 15.5
c.setStrokeColor(HexColor("#c9c2b0")); c.setLineWidth(0.6)
c.line(tx, ty-2, W-M-0.34*inch, ty-2)
# layout math
ty -= 20
ls_text(c, tx, ty, "LAYOUT MATH — RULE 3", 7.5, GOLD, tracking=1.6)
c.setFont("Helvetica", 7.5); c.setFillColor(INK)
for i, l in enumerate(['1 × 38"  =  38"   (target 38")',
                       '9 × 7-1/8"  =  64"   (target 64")',
                       'FLUSH BOTH ENDS · single panel']):
    c.drawString(tx, ty-14-i*11, l)
ty -= 14+3*11+10
c.setStrokeColor(HexColor("#c9c2b0")); c.line(tx, ty, W-M-0.34*inch, ty)
ty -= 16
ls_text(c, tx, ty, "NOTES / ASSUMPTIONS", 7.5, GOLD, tracking=1.6)
c.setFont("Helvetica-Oblique", 7.2); c.setFillColor(INK)
for i, l in enumerate(["· Ceiling 108\" REF + head 96\" ASSUMED — no site",
                       "  photo; if photo provided, use its proportions",
                       "· Mount depth 2-1/2\" ASSUMED — VERIFY at site",
                       "· Fold count/height ASSUMED from std ratio",
                       "· Fabric repeat alignment: one motif drop",
                       "  per shade — confirm at cut",
                       "· CONFIRM ALL before fabrication"]):
    c.drawString(tx, ty-13-i*10.5, l)

c.showPage(); c.save()
print("golden written")
