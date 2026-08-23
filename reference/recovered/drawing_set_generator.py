"""
Walnut sofa surround — 3-sheet PDF drawing set.

Sheet 1  presentation, front elevation in walnut with sofa and carpet
Sheet 2  dimensioned front elevation, side elevation, plan
Sheet 3  isometric, projected from the same figures

Isometric convention, viewer front-right-above:
    +x width  -> right and down     ( cos30,  sin30)
    +y depth  -> left  and down     (-cos30,  sin30)   y = 0 at wall, + toward viewer
    +z height -> straight up        (0, -1)
Visible faces are therefore TOP, FRONT and RIGHT.
"""
import math, io, cairosvg
from pypdf import PdfWriter, PdfReader

C, S = math.cos(math.radians(30)), math.sin(math.radians(30))
T = 23 / 32

# ── real geometry ────────────────────────────────────────────────────────
W_TOT, H_TOT = 126.0, 109.0
BAY_L, BAY_R = 23.0, 103.0
CARC_D = 17.25
BASE_D = CARC_D + T          # 17 31/32 — door is full overlay on the front
TOWER_D = 8.0
LEV, BASE_H = 0.5, 20.25
BASE_TOP = LEV + BASE_H      # 20.75
KICK = 2.0
OH_BOT, OH_TOP = 85.0, 109.0
TOWER_H = H_TOT - BASE_TOP   # 88.25
# (bottom face, top face). Top cap and the 85" shelf share the exact planes of
# the overhead panels, so the lines run unbroken. Below that, 14" pitch.
SHELVES = [(OH_TOP-T, OH_TOP), (85.0, 85.0+T), (71.0, 71.0+T),
           (57.0, 57.0+T), (43.0, 43.0+T), (29.0, 29.0+T)]
SOFA_W, SOFA_D, SOFA_H = 79.0, 33.0, 33.0

PAGE_W, PAGE_H = 792, 612           # US Letter landscape, points
INK, HAIR, MUTED = "#4E5257", "#DEDAD3", "#96907F"

WAL = dict(top="#8E6248", front="#734B35", side="#563723", edge="#3E2819")
UPH = dict(top="#D2C7B7", front="#C2B6A4", side="#A79B89")
CARPET = "#E7DDCB"


def P(x, y, z, k):
    return (k * C * (x - y), k * (S * (x + y) - z))


_SEEN = []

def poly(pts, k, fill, stroke="#3A2418", sw=0.8, op=1.0):
    proj = [P(*p, k) for p in pts]
    _SEEN.extend(proj)
    d = " ".join(f"{a:.2f},{b:.2f}" for a, b in proj)
    return (f'<polygon points="{d}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}" stroke-linejoin="round" opacity="{op}"/>')


def prism(x0, x1, y0, y1, z0, z1, k, pal, sw=0.8):
    """Top, front and right faces of a box. y0 = nearer the wall."""
    return "".join([
        poly([(x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1)], k, pal["top"],  sw=sw),
        poly([(x1,y0,z0),(x1,y0,z1),(x1,y1,z1),(x1,y1,z0)], k, pal["side"], sw=sw),
        poly([(x0,y1,z0),(x1,y1,z0),(x1,y1,z1),(x0,y1,z1)], k, pal["front"],sw=sw),
    ])


# ═══════════════════════════ SHEET 3 — ISOMETRIC ═════════════════════════
def isometric(k=3.05):
    _SEEN.clear()
    o = []
    # ground plane, kept close to the footprint so it does not dominate the sheet
    o.append(poly([(-9,0,0),(W_TOT+9,0,0),(W_TOT+9,SOFA_D+7,0),(-9,SOFA_D+7,0)],
                  k, CARPET, stroke="#D2C6B0", sw=1.0))
    # wall plane behind, very light
    o.append(poly([(-9,0,0),(W_TOT+9,0,0),(W_TOT+9,0,H_TOT+4),(-9,0,H_TOT+4)],
                  k, "#F2EFE9", stroke="#E2DDD3", sw=1.0))

    # ── towers: two side panels + shelves, drawn back to front ───────────
    for bx in (0.0, BAY_R):
        o.append(prism(bx, bx+T, 0, TOWER_D, BASE_TOP, H_TOT, k, WAL))
        for z0, z1 in SHELVES:
            o.append(prism(bx+T, bx+23-T, 0, TOWER_D, z0, z1, k,
                           dict(top="#7C5238", front="#4A2E20", side="#3E271B"), sw=0.6))
        o.append(prism(bx+23-T, bx+23, 0, TOWER_D, BASE_TOP, H_TOT, k, WAL))

    # ── overhead box ─────────────────────────────────────────────────────
    o.append(prism(BAY_L, BAY_R, 0, TOWER_D, OH_TOP-T, OH_TOP, k, WAL))
    o.append(prism(BAY_L, BAY_R, 0, TOWER_D, OH_BOT, OH_BOT+T, k, WAL))

    # ── base units drawn last so they sit clearly in front of the ghost ──
    for bx in (0.0, BAY_R):
        # carcass with full-overlay door face, front at BASE_D
        o.append(prism(bx, bx+23, 0, BASE_D, LEV+KICK, BASE_TOP, k, WAL))
        # toe kick, set back 3" from the door face
        o.append(prism(bx, bx+23, 0, BASE_D-3, LEV, LEV+KICK, k,
                       dict(top="#4A2E20", front="#3E271B", side="#32200F")))
        # leveler feet
        for fx in (bx+1.5, bx+23-2.5):
            o.append(prism(fx, fx+1, BASE_D-4, BASE_D-3, 0, LEV, k,
                           dict(top="#9C958A", front="#8A8074", side="#6E655B"), sw=0.4))
        px = bx + 23 - 2.6 if bx == 0 else bx + 2.0
        o.append(prism(px, px+0.5, BASE_D, BASE_D+0.6, 9.5, 14.0, k,
                       dict(top="#3A3632", front="#2E2A26", side="#232019"), sw=0.4))

    # ── sofa: reference only, ghosted so the joinery reads in front ──────
    sx0 = BAY_L + 0.5
    sx1 = sx0 + SOFA_W
    GH = dict(top="#EDE9E1", front="#E5DFD5", side="#D9D2C5")
    # drawn back to front: back panel, left arm, seat, right arm
    sofa = "".join([
        prism(sx0,      sx1,     0, 6,      0, SOFA_H, k, GH, sw=0.5),
        prism(sx0,      sx0+8,   6, SOFA_D, 0, 25,     k, GH, sw=0.5),
        prism(sx0+8,    sx1-8,   6, SOFA_D, 0, 16,     k, GH, sw=0.5),
        prism(sx1-8,    sx1,     6, SOFA_D, 0, 25,     k, GH, sw=0.5)])

    # ghost sofa slides in behind everything except the planes
    o.insert(2, sofa)
    xs = [p[0] for p in _SEEN]; ys = [p[1] for p in _SEEN]
    pad = 10
    vb = (min(xs)-pad, min(ys)-pad, max(xs)-min(xs)+2*pad, max(ys)-min(ys)+2*pad)
    return "".join(o), vb


# ═══════════════════════════ page furniture ══════════════════════════════
def titleblock(title, sub, n):
    return f'''
  <rect x="0" y="0" width="{PAGE_W}" height="{PAGE_H}" fill="#ffffff"/>
  <rect x="28" y="26" width="{PAGE_W-56}" height="{PAGE_H-52}" fill="none" stroke="{HAIR}" stroke-width="1"/>
  <text x="40" y="52" font-family="DejaVu Sans" font-size="13.5" font-weight="bold" fill="{INK}">{title}</text>
  <text x="40" y="68" font-family="DejaVu Sans" font-size="8.4" fill="{MUTED}">{sub}</text>
  <text x="{PAGE_W-40}" y="52" text-anchor="end" font-family="DejaVu Sans" font-size="13.5" fill="{INK}">{n} / 4</text>
  <text x="{PAGE_W-40}" y="68" text-anchor="end" font-family="DejaVu Sans" font-size="7.6" fill="{MUTED}">WOODCRAFT BY EMPIRE WORKROOM &#183; WASHINGTON DC</text>
  <line x1="28" y1="80" x2="{PAGE_W-28}" y2="80" stroke="{HAIR}" stroke-width="1"/>'''


def page(inner):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{PAGE_W}" height="{PAGE_H}" '
            f'viewBox="0 0 {PAGE_W} {PAGE_H}">{inner}</svg>')


# ═══════════════════════════ elevation helper ════════════════════════════
def elevation(k, walnut=True, sofa=True):
    """Front elevation in svg units; caller wraps in a transform."""
    def r(x, y, w, h, fill, stroke="#3A2418", sw=1.0):
        return (f'<rect x="{x*k:.2f}" y="{(H_TOT-y-h)*k:.2f}" width="{w*k:.2f}" '
                f'height="{h*k:.2f}" fill="{fill}" stroke="{stroke}" stroke-width="{sw}"/>')
    wf, sh, kick = ("#734B35", "#4A2E20", "#3E271B") if walnut else ("#F7F5F1", "#DDD9D1", "#E9E6DF")
    st = "#3A2418" if walnut else "#8A8F96"
    o = []
    if walnut:
        o.append(f'<rect x="{-8*k:.1f}" y="{H_TOT*k:.1f}" width="{(W_TOT+16)*k:.1f}" height="{9*k:.1f}" fill="{CARPET}" stroke="none"/>')
    for bx in (0.0, BAY_R):
        o.append(r(bx, BASE_TOP, 23, TOWER_H, wf, st))
        for z0, z1 in SHELVES:
            o.append(r(bx+T, z0, 23-2*T, z1-z0, sh, st, 0.7))
        o.append(r(bx, LEV+KICK, 23, BASE_H-KICK, wf, st))
        o.append(r(bx, LEV, 23, KICK, kick, st))
        o.append(r(bx, 0, 23, LEV, "#B9B2A6", st, 0.7))
    o.append(r(BAY_L, OH_TOP-T, BAY_R-BAY_L, T, wf, st))
    o.append(r(BAY_L, OH_BOT, BAY_R-BAY_L, T, wf, st))
    if sofa:
        sx = BAY_L+0.5
        o.append(r(sx, 0, SOFA_W, 26, "#C2B6A4", "#9E9280", 1.0))
        o.append(r(sx+8, 8, SOFA_W-16, 9, "#CEC3B3", "#A79B89", 0.8))
        o.append(r(sx, 0, 8, 21, "#C6BAA9", "#9E9280", 0.9))
        o.append(r(sx+SOFA_W-8, 0, 8, 21, "#C6BAA9", "#9E9280", 0.9))
    return "".join(o)


def dim(x1, y1, x2, y2, label, vert=False, size=7.4, off=9):
    tick = 3.4
    if vert:
        t = (f'<line x1="{x1}" y1="{y1}" x2="{x1}" y2="{y2}" stroke="{MUTED}" stroke-width="0.7"/>'
             f'<line x1="{x1-tick}" y1="{y1}" x2="{x1+tick}" y2="{y1}" stroke="{MUTED}" stroke-width="0.7"/>'
             f'<line x1="{x1-tick}" y1="{y2}" x2="{x1+tick}" y2="{y2}" stroke="{MUTED}" stroke-width="0.7"/>')
        cy = (y1+y2)/2
        t += (f'<text x="{x1-off}" y="{cy}" font-family="DejaVu Sans Mono" font-size="{size}" '
              f'fill="{MUTED}" text-anchor="middle" transform="rotate(-90 {x1-off} {cy})">{label}</text>')
    else:
        t = (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y1}" stroke="{MUTED}" stroke-width="0.7"/>'
             f'<line x1="{x1}" y1="{y1-tick}" x2="{x1}" y2="{y1+tick}" stroke="{MUTED}" stroke-width="0.7"/>'
             f'<line x1="{x2}" y1="{y1-tick}" x2="{x2}" y2="{y1+tick}" stroke="{MUTED}" stroke-width="0.7"/>')
        t += (f'<text x="{(x1+x2)/2}" y="{y1-off*0.55}" font-family="DejaVu Sans Mono" '
              f'font-size="{size}" fill="{MUTED}" text-anchor="middle">{label}</text>')
    return t


def txt(x, y, s, size=8, anchor="start", fill=None, mono=False, bold=False):
    f = "DejaVu Sans Mono" if mono else "DejaVu Sans"
    w = ' font-weight="bold"' if bold else ''
    return (f'<text x="{x}" y="{y}" font-family="{f}" font-size="{size}" '
            f'fill="{fill or INK}" text-anchor="{anchor}"{w}>{s}</text>')


# ═══════════════════════════ SHEET 1 ═════════════════════════════════════
def sheet1():
    k = 3.55
    o = [titleblock("Walnut Sofa Surround &#8212; Presentation",
                    "Walnut plywood, natural finish &#183; light beige carpet &#183; sofa shown 79\" wide", 1)]
    o.append(f'<g transform="translate(56,110)">{elevation(k)}</g>')
    o.append(txt(56+W_TOT*k/2, 110+ (H_TOT+11)*k, "FRONT ELEVATION", 7.4, "middle", MUTED, mono=True))
    x0, y0 = 520, 118
    spec = [("OVERALL", '126" W x 109" H x 17 31/32" D'),
            ("OPENING", '80" clear &#183; 79" sofa'),
            ("OVERHEAD", '24" high x 8" deep'),
            ("TOWERS", '23" W x 88 1/4" H x 8" D'),
            ("BASE UNITS", '23" W x 20 1/4" H'),
            ("BASE DEPTH", 'carcass 17 1/4" + door 23/32"'),
            ("DOORS", 'full overlay, 23" x 18 1/4"'),
            ("TOE KICK", '2" high, grain matched'),
            ("LEVELERS", '1/2" rear adjustable'),
            ("MATERIAL", 'walnut ply, 23/32" actual'),
            ("JOINERY", 'pocket screw, inside mount'),
            ("SHELVES", '6 per tower, 10 3/4" pitch')]
    for i, (a, b) in enumerate(spec):
        yy = y0 + i*31
        o.append(txt(x0, yy, a, 6.4, fill=MUTED, mono=True))
        o.append(txt(x0, yy+12, b, 8.6))
        o.append(f'<line x1="{x0}" y1="{yy+18}" x2="{PAGE_W-40}" y2="{yy+18}" stroke="{HAIR}" stroke-width="0.6"/>')
    return page("".join(o))


# ═══════════════════════════ SHEET 2 ═════════════════════════════════════
def sheet2():
    k = 2.62
    o = [titleblock("Elevations &amp; Plan &#8212; Dimensioned",
                    "All dimensions in inches &#183; material 23/32\" actual &#183; AFF = above finished floor", 2)]
    ox, oy = 74, 118
    o.append(f'<g transform="translate({ox},{oy})">{elevation(k, walnut=False, sofa=False)}</g>')
    o.append(f'<line x1="{ox-14}" y1="{oy+H_TOT*k}" x2="{ox+W_TOT*k+14}" y2="{oy+H_TOT*k}" stroke="{INK}" stroke-width="1.4"/>')
    L, R, TOP, BOT = ox, ox+W_TOT*k, oy, oy+H_TOT*k
    o.append(dim(L-46, TOP, L-46, BOT, '109" OVERALL', vert=True, off=8))
    o.append(dim(L-26, TOP, L-26, oy+(H_TOT-OH_TOP+OH_BOT)*k, '24"', vert=True, off=7))
    o.append(dim(R+22, oy+(H_TOT-BASE_TOP)*k, R+22, BOT, '20 1/4"', vert=True, off=7))
    o.append(dim(L, TOP-16, ox+BAY_L*k, TOP-16, '23"'))
    o.append(dim(ox+BAY_L*k, TOP-16, ox+BAY_R*k, TOP-16, '80"'))
    o.append(dim(ox+BAY_R*k, TOP-16, R, TOP-16, '23"'))
    o.append(dim(L, BOT+26, R, BOT+26, '126"'))
    o.append(txt(ox+BAY_L*k+6, oy+(H_TOT-OH_BOT)*k-4, '85" AFF SHELF LINE', 6.4, fill=MUTED, mono=True))
    o.append(txt(ox+W_TOT*k/2, BOT+44, "FRONT ELEVATION", 7.2, "middle", MUTED, mono=True))

    # ── side elevation ───────────────────────────────────────────────────
    sk = 2.62; sx, sy = 596, 118
    def sr(y, h, d0, d, fill, sw=1.0):
        return (f'<rect x="{sx+d0*sk:.1f}" y="{sy+(H_TOT-y-h)*sk:.1f}" width="{d*sk:.1f}" '
                f'height="{h*sk:.1f}" fill="{fill}" stroke="#8A8F96" stroke-width="{sw}"/>')
    o.append(sr(BASE_TOP, TOWER_H, 0, TOWER_D, "#F7F5F1"))
    o.append(sr(OH_BOT, T, 0, TOWER_D, "#E9E6DF"))
    o.append(sr(OH_TOP-T, T, 0, TOWER_D, "#E9E6DF"))
    o.append(sr(LEV+KICK, BASE_H-KICK, 0, BASE_D, "#F7F5F1"))
    o.append(sr(LEV, KICK, 0, BASE_D, "#E9E6DF"))
    o.append(sr(0, LEV, 1.5, BASE_D-3, "#CFCAC0", 0.7))
    o.append(f'<line x1="{sx-10}" y1="{sy+H_TOT*sk}" x2="{sx+BASE_D*sk+16}" y2="{sy+H_TOT*sk}" stroke="{INK}" stroke-width="1.4"/>')
    o.append(f'<line x1="{sx}" y1="{sy-8}" x2="{sx}" y2="{sy+H_TOT*sk+16}" stroke="{HAIR}" stroke-width="1" stroke-dasharray="6 4"/>')
    o.append(txt(sx-4, sy-12, "WALL", 6.4, "start", MUTED, mono=True))
    o.append(dim(sx, sy+H_TOT*sk+30, sx+BASE_D*sk, sy+H_TOT*sk+30, '17 31/32" OVERALL'))
    o.append(dim(sx, sy-4, sx+TOWER_D*sk, sy-4, '8"'))
    o.append(txt(sx+BASE_D*sk/2, sy+H_TOT*sk+52, "SIDE ELEVATION", 7.2, "middle", MUTED, mono=True))

    # ── plan ─────────────────────────────────────────────────────────────
    pk = 1.62; px, py = 74, 452
    def pr(x, w, d0, d, fill, sw=1.0):
        return (f'<rect x="{px+x*pk:.1f}" y="{py+d0*pk:.1f}" width="{w*pk:.1f}" '
                f'height="{d*pk:.1f}" fill="{fill}" stroke="#8A8F96" stroke-width="{sw}"/>')
    o.append(pr(0, W_TOT, 0, TOWER_D, "#EFEAE1"))
    o.append(pr(0, 23, 0, BASE_D, "#E4DDD1"))
    o.append(pr(BAY_R, 23, 0, BASE_D, "#E4DDD1"))
    o.append(f'<line x1="{px-10}" y1="{py}" x2="{px+W_TOT*pk+10}" y2="{py}" stroke="{INK}" stroke-width="1.6"/>')
    o.append(txt(px, py-6, "WALL", 6.4, "start", MUTED, mono=True))
    o.append(dim(px, py+BASE_D*pk+30, px+23*pk, py+BASE_D*pk+30, '23"', size=6.6))
    o.append(dim(px+BAY_L*pk, py+BASE_D*pk+30, px+BAY_R*pk, py+BASE_D*pk+30, '80"', size=6.6))
    o.append(dim(px+BAY_R*pk, py+BASE_D*pk+30, px+W_TOT*pk, py+BASE_D*pk+30, '23"', size=6.6))
    o.append(dim(px+W_TOT*pk+24, py, px+W_TOT*pk+24, py+BASE_D*pk, '17 31/32"', vert=True, size=6.6, off=7))
    o.append(txt(px+(BAY_L+BAY_R)/2*pk, py+TOWER_D*pk+13, "SOFA ZONE &#183; 79\" MAX", 6.4, "middle", MUTED, mono=True))
    o.append(txt(px+W_TOT*pk/2, py+BASE_D*pk+50, "PLAN", 7.2, "middle", MUTED, mono=True))

    notes = ["1/2\" levelers + 20 1/4\" base + 88 1/4\" tower = 109\" overall.",
             "Base depth is carcass 17 1/4\" plus full-overlay door 23/32\" = 17 31/32\".",
             "Overhead underside 85\" AFF; first tower shelf set to the same line.",
             "Base 20 1/4\" comprises 2\" toe kick and 18 1/4\" door.",
             "Rear levelers adjustable; front bears on carpet."]
    o.append(txt(596, 452, "NOTES", 6.6, fill=MUTED, mono=True))
    for i, n in enumerate(notes):
        o.append(txt(596, 468+i*13, f"{i+1}.  {n}", 7.2))
    return page("".join(o))


# ═══════════════════════════ SHEET 3 ═════════════════════════════════════
def sheet3():
    body, vb = isometric()
    o = [titleblock("Isometric",
                    "30&#176; isometric projected from the dimensioned geometry &#183; sofa and carpet shown for scale", 3)]
    avail_w, avail_h = PAGE_W - 70, PAGE_H - 128
    sc = min(avail_w / vb[2], avail_h / vb[3])
    tx = 35 + (avail_w - vb[2]*sc)/2 - vb[0]*sc
    ty = 92 + (avail_h - vb[3]*sc)/2 - vb[1]*sc
    o.append(f'<g transform="translate({tx:.2f},{ty:.2f}) scale({sc:.4f})">{body}</g>')
    o.append(txt(PAGE_W/2, PAGE_H-44, "ISOMETRIC &#183; VIEWED FROM FRONT RIGHT ABOVE", 7.2, "middle", MUTED, mono=True))
    return page("".join(o))



# ═══════════════════════════ SHEET 4 — HINGE DETAIL ══════════════════════
def sheet4():
    """Three separate diagrams. Frameless full overlay - no inside post."""
    TT = 23/32
    CUP_D, CUP_DEEP, CUP_EDGE = 1.378, 0.512, 0.866    # 35mm, 13mm, 22mm
    o = [titleblock("Door Hardware &#8212; Hinge Detail",
                    "Frameless full overlay &#183; no centre stile or post required &#183; 2 hinges per door", 4)]

    def label(x, y, t, size=6.8, anchor="start"):
        return txt(x, y, t, size, anchor, MUTED, mono=True)

    def leader(x1, y1, x2, y2):
        return (f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{HAIR}" '
                f'stroke-width="0.8"/><circle cx="{x1}" cy="{y1}" r="1.6" fill="{MUTED}"/>')

    # ─────────── A · plan section, door closed ───────────
    k, ax, ay = 42, 108, 190          # ay = the panel front edge line
    def A(x, y, w, h, fill, st="#7E838A", sw=1.0):
        return (f'<rect x="{ax+x*k:.1f}" y="{ay+y*k:.1f}" width="{w*k:.1f}" '
                f'height="{h*k:.1f}" fill="{fill}" stroke="{st}" stroke-width="{sw}"/>')
    o.append(txt(ax-38, ay-72, "A", 12, fill=INK, bold=True))
    o.append(txt(ax-20, ay-72, "PLAN SECTION &#183; DOOR CLOSED", 8.4, fill=INK))
    o.append(A(0, 0, TT, 3.4, "#E4DDD1"))                       # side panel, running back
    o.append(A(-2.4, -TT, 2.4+TT, TT, "#D6C9B4"))               # door, full overlay
    o.append(A(-CUP_EDGE-CUP_D/2, -CUP_DEEP, CUP_D, CUP_DEEP, "#FBFAF7", "#7E838A", 1.2))
    o.append(A(TT, 0.55, 0.30, 1.35, "#CDD2D6", "#7E838A", 1.2))    # mounting plate
    o.append(f'<path d="M{ax+(-CUP_EDGE-0.34)*k:.1f},{ay-0.10*k:.1f} '
             f'L{ax+(-CUP_EDGE+0.34)*k:.1f},{ay-0.10*k:.1f} '
             f'L{ax+(TT+0.30)*k:.1f},{ay+1.00*k:.1f} '
             f'L{ax+(TT+0.30)*k:.1f},{ay+1.42*k:.1f} '
             f'L{ax+(-CUP_EDGE-0.34)*k:.1f},{ay+0.32*k:.1f} Z" '
             f'fill="#DCDFE2" stroke="#7E838A" stroke-width="1.0"/>')
    for fy in (0.85, 1.62):
        o.append(f'<circle cx="{ax+(TT+0.15)*k:.1f}" cy="{ay+fy*k:.1f}" r="2.4" fill="#8A8F96"/>')
    # PIVOT: front outer corner of the side panel - this is what the door swings about
    o.append(f'<circle cx="{ax+TT*k:.1f}" cy="{ay:.1f}" r="4.2" fill="none" stroke="{"#B4553C"}" stroke-width="1.6"/>')
    o.append(f'<circle cx="{ax+TT*k:.1f}" cy="{ay:.1f}" r="1.5" fill="#B4553C"/>')
    o.append(txt(ax+TT*k+10, ay-8, "PIVOT", 6.6, "start", "#B4553C", mono=True))
    o.append(label(ax+TT*k+14, ay+38, "SIDE PANEL 23/32\""))
    o.append(label(ax-2.4*k, ay-TT*k-9, "DOOR 23/32\" &#183; FULL OVERLAY"))
    o.append(label(ax+(-CUP_EDGE-CUP_D/2)*k, ay-CUP_DEEP*k-9, "35 mm CUP, 13 mm DEEP"))
    o.append(label(ax+(TT+0.42)*k, ay+1.28*k, "0 mm PLATE"))
    o.append(dim(ax+(-CUP_EDGE)*k, ay+2.9*k, ax+TT*k, ay+2.9*k, '7/8" TO CUP CENTRE', size=6.4))

    # ─────────── B · plan section, door open 110 ───────────
    bx_, by = 372, 190
    o.append(txt(bx_-38, by-72, "B", 12, fill=INK, bold=True))
    o.append(txt(bx_-20, by-72, "PLAN SECTION &#183; OPEN 110&#176;", 8.4, fill=INK))
    o.append(f'<rect x="{bx_:.1f}" y="{by:.1f}" width="{TT*k:.1f}" height="{3.4*k:.1f}" '
             f'fill="#E4DDD1" stroke="#7E838A" stroke-width="1"/>')
    o.append(f'<rect x="{bx_-2.4*k:.1f}" y="{by-TT*k:.1f}" width="{(2.4+TT)*k:.1f}" '
             f'height="{TT*k:.1f}" fill="none" stroke="{HAIR}" stroke-width="1" stroke-dasharray="5 4"/>')
    px_, py_ = bx_+TT*k, by
    o.append(f'<g transform="rotate(-110 {px_:.1f} {py_:.1f})">'
             f'<rect x="{bx_-2.4*k:.1f}" y="{by-TT*k:.1f}" width="{(2.4+TT)*k:.1f}" '
             f'height="{TT*k:.1f}" fill="#D6C9B4" stroke="#7E838A" stroke-width="1.1"/></g>')
    o.append(f'<path d="M{px_-2.4*k:.1f},{py_-TT*k/2:.1f} A {2.4*k:.1f} {2.4*k:.1f} 0 0 1 '
             f'{px_+0.82*k:.1f},{py_+2.26*k:.1f}" fill="none" stroke="#D8BBAF" '
             f'stroke-width="1.2" stroke-dasharray="6 4"/>')
    o.append(f'<circle cx="{px_:.1f}" cy="{py_:.1f}" r="4.2" fill="none" stroke="#B4553C" stroke-width="1.6"/>')
    o.append(f'<circle cx="{px_:.1f}" cy="{py_:.1f}" r="1.5" fill="#B4553C"/>')
    o.append(txt(px_+10, py_-8, "SAME PIVOT", 6.6, "start", "#B4553C", mono=True))
    o.append(label(bx_-2.3*k, by-TT*k-9, "CLOSED (GHOST)"))
    o.append(label(bx_+0.9*k, by+2.9*k, "SWING CLEARS 23\" &#8212; CHECK"))
    o.append(label(bx_+0.9*k, by+2.9*k+13, "SOFA ARM BEFORE FITTING"))

    # ─────────── C · door elevation, hinge positions ───────────
    ek, ex, ey = 11.0, 610, 128
    dw, dh = 23.0, 18.25
    o.append(txt(ex-30, ey-18, "C", 12, fill=INK, bold=True))
    o.append(txt(ex-12, ey-18, "DOOR ELEVATION &#183; HINGE SETOUT", 8.4, fill=INK))
    o.append(f'<rect x="{ex:.1f}" y="{ey:.1f}" width="{dw*ek:.1f}" height="{dh*ek:.1f}" '
             f'fill="#F7F5F1" stroke="#8A8F96" stroke-width="1.3"/>')
    for hy in (3.0, dh-3.0):
        cy = ey+hy*ek
        o.append(f'<circle cx="{ex+0.875*ek:.1f}" cy="{cy:.1f}" r="{CUP_D/2*ek:.1f}" '
                 f'fill="#FBFAF7" stroke="#7E838A" stroke-width="1.2"/>')
        o.append(f'<circle cx="{ex+0.875*ek:.1f}" cy="{cy:.1f}" r="1.6" fill="#B4553C"/>')
    o.append(dim(ex, ey-14, ex+dw*ek, ey-14, '23"', size=6.8))
    o.append(dim(ex-16, ey, ex-16, ey+3.0*ek, '3"', vert=True, size=6.4, off=7))
    o.append(dim(ex-16, ey+(dh-3.0)*ek, ex-16, ey+dh*ek, '3"', vert=True, size=6.4, off=7))
    o.append(dim(ex+dw*ek+16, ey, ex+dw*ek+16, ey+dh*ek, '18 1/4"', vert=True, size=6.4, off=-16))
    o.append(label(ex+2.0*ek, ey+dh*ek+18, "HINGE SIDE &#8212; CUP CENTRES 7/8\" FROM EDGE"))

    # ─────────── hardware schedule ───────────
    hx, hy0 = 610, 386
    o.append(txt(hx, hy0, "HARDWARE", 8.6, fill=INK, bold=True))
    rows = [("HINGE", "35 mm cup, full overlay, 110&#176;, soft close", "4"),
            ("PLATE", "0 mm cranked mounting plate, screw-on", "4"),
            ("PULL", "Bar pull, 1 per door", "2"),
            ("LEVELER", "Adjustable, 1/2\" nominal, rear", "8"),
            ("SCREWS", "1 1/4\" coarse pocket screw", "~90")]
    o.append(f'<line x1="{hx}" y1="{hy0+8}" x2="{PAGE_W-40}" y2="{hy0+8}" stroke="{HAIR}" stroke-width="0.8"/>')
    for i,(a,b,q) in enumerate(rows):
        yy = hy0+24+i*26
        o.append(txt(hx, yy, a, 6.4, fill=MUTED, mono=True))
        o.append(txt(hx+72, yy, b, 7.6))
        o.append(txt(PAGE_W-40, yy, q, 7.6, "end", mono=True))
        o.append(f'<line x1="{hx}" y1="{yy+7}" x2="{PAGE_W-40}" y2="{yy+7}" stroke="{HAIR}" stroke-width="0.5"/>')

    notes = ["No inside post. A centre stile is a face-frame detail; this carcass is frameless,",
             "so the hinge plate screws straight to the inside face of the side panel.",
             "Pivot sits at the front outer corner of the side panel, marked in red on A and B.",
             "Door is wider than tall, so load is cantilevered — consider a third hinge."]
    o.append(txt(108, 470, "NOTES", 6.4, fill=MUTED, mono=True))
    for i,n in enumerate(notes):
        o.append(txt(108, 486+i*13, n, 7.2))
    return page("".join(o))

# ═══════════════════════════ build ═══════════════════════════════════════
writer = PdfWriter()
for i, mk in enumerate((sheet1, sheet2, sheet3, sheet4), 1):
    buf = io.BytesIO()
    # dpi=72 makes one svg unit equal one PostScript point
    cairosvg.svg2pdf(bytestring=mk().encode(), write_to=buf, dpi=72)
    buf.seek(0)
    writer.add_page(PdfReader(buf).pages[0])
    print(f"sheet {i} ok")

writer.add_metadata({"/Title": "Walnut Sofa Surround - Drawing Set",
                     "/Author": "Woodcraft by Empire Workroom"})
out = "/mnt/user-data/outputs/sofa-surround-drawings.pdf"
with open(out, "wb") as f:
    writer.write(f)
print("written:", out)
