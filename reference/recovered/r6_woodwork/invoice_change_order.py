"""R6 - invoice for the approved change order. Totals derived from client_change_order.py."""
import io, importlib.util, contextlib, pathlib, cairosvg, segno
from pypdf import PdfWriter, PdfReader
OUT = pathlib.Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
# -- PROVENANCE GATE ----------------------------------------------------
# This script previously loaded the literal name "client.py". A different,
# unaudited client.py sits in this directory. Name the source explicitly
# and pin its bytes.
import hashlib, sys
CLIENT_PY  = (pathlib.Path(__file__).resolve().parent / "client_change_order.py")
CLIENT_SHA = "abdc03a340384fdf5625f22f00d82b15708e753dcbe8cc96b8b01b5e12f46c25"

if not CLIENT_PY.is_file():
    sys.exit(f"REFUSED - client source not found at {CLIENT_PY}")
_sha = hashlib.sha256(CLIENT_PY.read_bytes()).hexdigest()
if CLIENT_SHA == "PIN_ME":
    sys.exit(f"REFUSED - CLIENT_SHA unset.\n  this file is {_sha}\n"
             f"  pin it once confirmed correct")
if _sha != CLIENT_SHA:
    sys.exit(f"REFUSED - client source changed\n  pinned {CLIENT_SHA}\n  found  {_sha}")

sp=importlib.util.spec_from_file_location("c", str(CLIENT_PY)); C=importlib.util.module_from_spec(sp)
with contextlib.redirect_stdout(io.StringIO()): sp.loader.exec_module(C)
MATSUB,LEDSUB,GOODS,GOODSELL,LAB,TOTAL = C.MATSUB,C.LEDSUB,C.GOODS,C.GOODSELL,C.LAB,C.TOTAL
HRS,RATE,MK = C.S["LABOR_HRS"], C.S["LABOR_RATE"], C.S["MARKUP"]
assert abs(GOODS-(MATSUB+LEDSUB))<1e-9
assert abs(GOODSELL-GOODS*(1+MK))<1e-9
assert abs(LAB-HRS*RATE)<1e-9
assert abs(TOTAL-(GOODSELL+LAB))<1e-9

# -- GOVERNING TOTAL ----------------------------------------------------
# Founder ruling 2026-08-30. Supersedes $2,390.80 and $2,302.40.
#   birch ply cleats deleted, cut from 0.72 walnut on hand    -$68.00
#   rails 1-1/2 -> 1-1/4, 6 BF -> 5 BF of 8/4                 -$20.00
GOVERNING_TOTAL = 2276.40
assert abs(TOTAL - GOVERNING_TOTAL) < 0.005, \
    f"REFUSED - TOTAL ${TOTAL:,.2f} != governing ${GOVERNING_TOTAL:,.2f}"

# -- MARKUP SCOPE -------------------------------------------------------
# R6 predates D49. REV G was issued with 30% on cabinetry AND lighting.
# D49 (lighting only) governs new work. Do not "fix" this document.
MARKUP_SCOPE = "legacy_all_goods"

# ── PAYMENT ─────────────────────────────────────────────────────────────
# Replace PAY_URL with the live Stripe payment link. The QR is generated
# from this string — change it here and nowhere else.
PAY_URL = "https://buy.stripe.com/14A14gdGWgaBgMzeWlg7e01"
PAY_LIVE = "REPLACE" not in PAY_URL          # gates the sheet

def qr_svg(data, x, y, size):
    """Return the QR as absolutely-positioned SVG rects."""
    q = segno.make(data, error='h')
    mods = [list(r) for r in q.matrix]
    n = len(mods)
    px = size / n
    out = [f'<rect x="{x:.2f}" y="{y:.2f}" width="{size:.2f}" height="{size:.2f}" fill="#ffffff"/>']
    for r, row in enumerate(mods):
        c = 0
        while c < n:
            if row[c]:
                c0 = c
                while c < n and row[c]: c += 1
                out.append(f'<rect x="{x + c0*px:.2f}" y="{y + r*px:.2f}" '
                           f'width="{(c - c0)*px:.2f}" height="{px:.2f}" fill="#1A1A1A"/>')
            else:
                c += 1
    return "".join(out), n

INV = dict(no="INV-2026-119", date="30 Aug 2026",
           approved="27 Aug 2026", terms="Due on receipt")
# -- COMPLETENESS GATE --------------------------------------------------
# The red COMPLETE BEFORE SENDING strip was removed once the fields were
# filled. This replaces it. A block character anywhere in INV means a
# founder field was never supplied.
for _k, _v in INV.items():
    if "\u2588" in _v or not _v.strip():
        sys.exit(f"REFUSED - INV['{_k}'] is unfilled: {_v!r}")
if "REPLACE" in PAY_URL or not PAY_URL.startswith("https://buy.stripe.com/"):
    sys.exit(f"REFUSED - PAY_URL is not a live Stripe payment link: {PAY_URL!r}")
PW,PH=612,792
INK,HAIR,MUTED,GOLD,RED,PAPER="#4E5257","#DEDAD3","#96907F","#B8912F","#B4553C","#FBFAF7"
def txt(x,y,s,size=8,anchor="start",fill=None,mono=False,bold=False):
    f="DejaVu Sans Mono" if mono else "DejaVu Sans"
    b=' font-weight="bold"' if bold else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{f}" font-size="{size}" '
            f'fill="{fill or INK}" text-anchor="{anchor}"{b}>{s}</text>')
def r_(x,y,w,h,fill,st=INK,sw=1,dash=None):
    d=f' stroke-dasharray="{dash}"' if dash else ''
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="{st}" stroke-width="{sw}"{d}/>')
def line(x1,y1,x2,y2,st=INK,sw=1):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{st}" stroke-width="{sw}"/>'

o=[f'<rect width="{PW}" height="{PH}" fill="#ffffff"/>']
o.append(f'<rect x="28" y="26" width="{PW-56}" height="{PH-52}" fill="none" stroke="{HAIR}"/>')
# header
o.append(txt(40,52,"INVOICE",13.5,bold=True))
o.append(txt(40,68,"Change order, REV G \u00b7 additional work",8.0,fill=MUTED))
o.append(txt(PW-40,52,INV["no"],13.5,"end"))
o.append(txt(PW-40,68,"WOODCRAFT BY EMPIRE WORKROOM \u00b7 WASHINGTON DC",7.2,"end",MUTED))
o.append(line(28,80,PW-28,80,HAIR))
o.append(txt(PW-40,96,f'Date  {INV["date"]}',7.4,"end",fill=MUTED))
o.append(txt(PW-40,108,f'Terms {INV["terms"]}',7.4,"end",fill=MUTED))
# parties
o.append(txt(48,126,"BILL TO",6.6,fill=MUTED,mono=True))
for i,t in enumerate(["Lauren Bassett","LB Design"]):
    o.append(txt(48,142+i*13,t,8.6,bold=(i==0)))
o.append(txt(320,126,"PROJECT",6.6,fill=MUTED,mono=True))
for i,t in enumerate(["R6 Walnut Sofa Surround","Philipp &amp; Naomi","Change order, REV G"]):
    o.append(txt(320,142+i*13,t,8.6,bold=(i==0)))
o.append(txt(320,185,f'approved {INV["approved"]}',7.4,fill=MUTED))
o.append(line(48,198,PW-48,198,HAIR))
# what this covers
o.append(txt(48,212,"ADDITIONAL WORK \u2014 APPROVED CHANGE ORDER",9.6,bold=True))
o.append(txt(48,228,"Work added after design approval. The original contract is unchanged and is not re-billed.",7.2,fill=MUTED))
# line items
o.append(txt(48,258,"DESCRIPTION",6.6,fill=MUTED,mono=True))
o.append(txt(PW-48,258,"AMOUNT",6.6,"end",MUTED,mono=True))
o.append(line(48,264,PW-48,264,HAIR))
ITEMS=[("Cabinetry materials","solid walnut, hardware, finish",MATSUB),
       ("Lighting, power and control","supplied, installed and tested",LEDSUB)]
y=272
for n,d,v in ITEMS:
    o.append(txt(48,y,n,8.2,bold=True)); o.append(txt(48,y+11,d,6.8,fill=MUTED))
    o.append(txt(PW-48,y+4,f'${v:,.2f}',8.2,"end",mono=True))
    o.append(line(48,y+16,PW-48,y+16,HAIR,.4)); y+=28
o.append(txt(48,y,"Materials, at cost",7.6,fill=MUTED))
o.append(txt(PW-48,y,f'${GOODS:,.2f}',7.6,"end",mono=True)); y+=15
o.append(txt(48,y,f'Handling and procurement, {MK*100:.0f}%',7.6,fill=MUTED))
o.append(txt(PW-48,y,f'${GOODS*MK:,.2f}',7.6,"end",mono=True)); y+=6
o.append(line(48,y,PW-48,y,HAIR)); y+=18
o.append(txt(48,y,"Materials, billed",8.2,bold=True))
o.append(txt(PW-48,y,f'${GOODSELL:,.2f}',8.6,"end",bold=True)); y+=24
o.append(txt(48,y,"Labor",8.2,bold=True))
o.append(txt(48,y+11,f'{HRS:.1f} hours at ${RATE:,.2f} \u00b7 overhead rebuild, plinth frames, edging, lighting',6.8,fill=MUTED))
o.append(txt(PW-48,y+4,f'${LAB:,.2f}',8.2,"end",mono=True))
o.append(line(48,y+16,PW-48,y+16,HAIR,.4)); y+=34
# total
o.append(r_(48,y,PW-96,52,PAPER,INK,1.6))
o.append(txt(66,y+33,"TOTAL DUE",12,bold=True))
o.append(txt(PW-66,y+33,f'${TOTAL:,.2f}',19,"end",bold=True))
y+=66
# not billed
o.append(txt(48,y+14,"NOT BILLED ON THIS INVOICE",8.4,bold=True,fill=GOLD))
for i,t in enumerate(["Walnut plywood - already on hand.",
                      "French cleats - cut from walnut on hand; birch plywood deleted, not charged.",
                      "Legs - supplied by the client, COM.",
                      "Original contracted scope - unchanged and not re-billed."]):
    o.append(txt(48,y+30+i*12.0,"\u2022 "+t,7.2))
y+=68
o.append(line(48,y,PW-48,y,HAIR))
y+=20
o.append(txt(48,y,"TWO WAYS TO PAY",9.2,bold=True))
QS=82
if PAY_LIVE:
    qsvg,_=qr_svg(PAY_URL, 48, y+14, QS)
    o.append(qsvg)
    o.append(r_(48,y+14,QS,QS,"none",HAIR,1))
    o.append(txt(48+QS/2,y+QS+26,"SCAN TO PAY",7.0,"middle",INK,mono=True,bold=True))
else:
    o.append(r_(48,y+14,QS,QS,"#FFF4F0",RED,1.6))
    for i in range(0,int(QS),9):
        o.append(line(48+i,y+14+QS,48+QS,y+14+QS-i,"#F0D8D0",.8))
    o.append(txt(48+QS/2,y+14+QS/2-4,"QR GOES",7.2,"middle",RED,bold=True))
    o.append(txt(48+QS/2,y+14+QS/2+8,"HERE",7.2,"middle",RED,bold=True))
    o.append(txt(48+QS/2,y+QS+26,"NO LIVE LINK YET",6.6,"middle",RED,mono=True,bold=True))
bx=48+QS+28
o.append(txt(bx,y+28,"1  Scan the code",8.0,bold=True))
o.append(txt(bx,y+40,"Card or bank transfer through Stripe. Opens on your phone.",7.0,fill=MUTED))
o.append(txt(bx,y+58,"2  Or use the link",8.0,bold=True))
o.append(txt(bx,y+70,PAY_URL,6.8,fill="#2B5AA0",mono=True))
LINK_BOX=(bx,y+62,bx+len(PAY_URL)*3.6,y+74)
y+=QS+34
o.append(line(28,PH-46,PW-28,PH-46,HAIR))
o.append(txt(40,PH-32,"R6 Walnut Sofa Surround \u00b7 Philipp &amp; Naomi \u00b7 LB Design",6.8,fill=MUTED))
o.append(txt(PW/2,PH-32,"INVOICE \u00b7 DUE ON RECEIPT",6.8,"middle",RED,bold=True))
o.append(txt(PW-40,PH-32,f'REV G \u00b7 {INV["date"]}',6.8,"end",MUTED))
svg=(f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW}" height="{PH}" viewBox="0 0 {PW} {PH}">'
     +"".join(o)+'</svg>')
b=io.BytesIO(); cairosvg.svg2pdf(bytestring=svg.encode(),write_to=b,dpi=72); b.seek(0)
w=PdfWriter(); w.add_page(PdfReader(b).pages[0])
if PAY_LIVE:
    from pypdf.generic import (DictionaryObject, NameObject, ArrayObject,
                               NumberObject, TextStringObject)
    pg=w.pages[0]; ph=float(pg.mediabox.height)
    x0,y0,x1,y1 = LINK_BOX
    ann=DictionaryObject({NameObject("/Type"):NameObject("/Annot"),
        NameObject("/Subtype"):NameObject("/Link"),
        NameObject("/Rect"):ArrayObject([NumberObject(x0),NumberObject(ph-y1),
                                         NumberObject(x1),NumberObject(ph-y0)]),
        NameObject("/Border"):ArrayObject([NumberObject(0)]*3),
        NameObject("/A"):DictionaryObject({NameObject("/S"):NameObject("/URI"),
            NameObject("/URI"):TextStringObject(PAY_URL)})})
    ref=w._add_object(ann); pg[NameObject("/Annots")]=ArrayObject([ref])
w.add_metadata({"/Title":"R6 Invoice - Approved Change Order"})
with open(str(OUT / "R6-INVOICE-change-order.pdf"),"wb") as f: w.write(f)
cairosvg.svg2png(bytestring=svg.encode(),write_to=str(OUT / "inv.png"),scale=1.7)
print(f"invoice \u00b7 TOTAL ${TOTAL:,.2f} \u00b7 pay link {'LIVE' if PAY_LIVE else 'PLACEHOLDER'}")
print(f"  payment link MUST be for ${TOTAL:,.2f} - verify in Stripe before sending")
