"""
R6 part labels — Woodcraft by Empire Workroom.

320 x 240 dots = 40 x 30 mm at 203 dpi, but the artwork is inset by a 12-dot
(1.5 mm) quiet margin on all sides. Thermal heads cannot reach the very edge
of the stock and the roll wanders a little, so anything drawn to the edge gets
shaved. Content now lives in a 296 x 216 box.
"""
from PIL import Image, ImageDraw, ImageFont

DPI = 203
MM = DPI / 25.4
W, H = round(40 * MM), round(30 * MM)        # 320 x 240
MARGIN = 12                                   # 1.5 mm quiet edge
X0, Y0 = MARGIN, MARGIN
X1, Y1 = W - MARGIN - 1, H - MARGIN - 1       # 307, 227 (PIL rects are inclusive)
CW, CH = X1 - X0, Y1 - Y0                     # 296 x 216

SHOP = "WOODCRAFT BY EMPIRE WORKROOM"
COND = "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"

PARTS = [
    # ── REV G, still to be made ──────────────────────────────────────────
    ("M", "SPACER BAR",                  2, '23"',        '2"'),
    ("P", "LEVELER PAD",                 4, '4"',         '2"'),
    ("Q", "TOWER BACK PANEL",            2, '88 1/4"',    '22 1/16"'),
    ("R", "OVERHEAD TOP / BOTTOM",       2, '80"',        '5 13/16"'),
    ("S", "OVERHEAD UPRIGHT",            5, '12 1/4"',   '5 13/16"'),
    ("AA","FRENCH CLEAT 45 DEG",         2, '80"',        '4"'),
    ("T", "OVERHEAD BACK PER BAY",       4, '19 3/32"',   '12 1/4"'),
    ("U", "FACE TRIM SHELF BAND",       12, '20"',        '1 1/2"'),
    ("V", "FACE TRIM SIDE STILE",        4, '88 1/4"',    '1 1/2"'),
    ("W", "FACE TRIM OVERHEAD BAND",     2, '80"',        '1 1/2"'),
    ("X", "FACE TRIM UPRIGHT",           5, '12 1/4"',   '1 1/2"'),
    ("Y", "LED COVE TRIM TOWER",        12, '20 9/16"',   '3/4"'),
    ("Z", "LED COVE TRIM OVERHEAD",      4, '18 3/32"',   '3/4"'),
]


def f(n):
    return ImageFont.truetype(COND, n)


def sz(d, s, fnt):
    b = d.textbbox((0, 0), s, font=fnt)
    return b[2] - b[0], b[3] - b[1]


def fit(d, s, cap, start, floor=9):
    n = start
    while n > floor:
        fnt = f(n)
        if sz(d, s, fnt)[0] <= cap:
            return fnt
        n -= 1
    return f(floor)


def wrap(d, t, fnt, cap, mx=2):
    lines, cur = [], ""
    for w_ in t.split():
        tr = (cur + " " + w_).strip()
        if sz(d, tr, fnt)[0] <= cap:
            cur = tr
        else:
            if cur:
                lines.append(cur)
            cur = w_
            if len(lines) > mx:
                return None
    if cur:
        lines.append(cur)
    return lines if len(lines) <= mx else None


def make(letter, desig, L, Wd, out):
    img = Image.new("1", (W, H), 1)
    d = ImageDraw.Draw(img)
    pad = 6

    # ── shop bar, inside the margin ──────────────────────────────────────
    bar = 30
    d.rectangle([X0, Y0, X1, Y0 + bar], fill=0)
    fs = fit(d, SHOP, CW - pad * 2, 18, 10)
    sw, sh = sz(d, SHOP, fs)
    d.text((X0 + (CW - sw) // 2, Y0 + (bar - sh) // 2 - 3), SHOP, font=fs, fill=1)

    # ── part letter, its own column ──────────────────────────────────────
    col = X0 + 92
    n = 132 if len(letter) == 1 else 92          # two-char tags need a smaller face
    fl = f(n)
    while sz(d, letter, fl)[0] > 86 and n > 40:
        n -= 4; fl = f(n)
    lw, lh = sz(d, letter, fl)
    d.text((X0 + (92 - lw) // 2, Y0 + bar + (CH - bar - lh) // 2 - 18),
           letter, font=fl, fill=0)
    d.rectangle([col, Y0 + bar + 8, col + 3, Y1 - 6], fill=0)

    # ── right column ─────────────────────────────────────────────────────
    x = col + 11
    cap = X1 - x
    y = Y0 + bar + 8

    fd_ = f(17)
    lines = wrap(d, desig, fd_, cap)
    if lines is None:
        fd_ = f(14)
        lines = wrap(d, desig, fd_, cap) or [desig]
    for ln in lines:
        d.text((x, y), ln, font=fd_, fill=0)
        y += sz(d, ln, fd_)[1] + 5

    y += 3
    d.rectangle([x, y, X1, y + 3], fill=0)          # heavier rule, prints darker
    y += 10

    # ── dimensions ───────────────────────────────────────────────────────
    tag_w = 20
    ncap = cap - tag_w - 4
    n = 34
    while n > 12:
        fn = f(n)
        widest = max(sz(d, v, fn)[0] for v in (L, Wd))
        rh = sz(d, "0", fn)[1]
        if widest <= ncap and (rh + 8) * 2 <= Y1 - y:
            break
        n -= 1
    fn, ft = f(n), f(13)

    for tag, val in (("L", L), ("W", Wd)):
        rh = sz(d, val, fn)[1]
        d.text((x, y + rh - 12), tag, font=ft, fill=0)
        vw = sz(d, val, fn)[0]
        d.text((X1 - vw, y), val, font=fn, fill=0)
        y += rh + 8

    img.save(out, dpi=(DPI, DPI))


total = 0
for l, dg, q, L, Wd in PARTS:
    make(l, dg, L, Wd, f"/mnt/user-data/outputs/R6G-v2-part-{l}.png")
    total += q
    print(f"R6G-v2-part-{l}.png  {dg:<28}{L:>11}{Wd:>11}  x{q}")

print(f"\n{len(PARTS)} designs · {total} pieces")
print(f"{W} x {H} dots, {MARGIN}-dot ({MARGIN/MM:.1f} mm) quiet margin, content {CW} x {CH}")
