"""R6 REV G - material list + client proposal. One RATES/SPEC block drives both."""
import io, math, cairosvg
from pypdf import PdfWriter, PdfReader
import re as _re
S=dict(rev="G",date="2026-08-18",job="R6 Walnut Sofa Surround",
 client="Woodcraft \u2014 Philipp &amp; Naomi",brand="WOODCRAFT BY EMPIRE WORKROOM",
 MARKUP=0.30, LABOR_HRS=5.5, LABOR_RATE=95.0)
RATES=dict(wal44=16.00, wal84=20.00, panel=82.00, birch=68.00,
           glue=18.00, spline=12.00, pin=9.00, abras=22.00, finish=34.00)
MAT=[
 ("Walnut 4/4 S2S","solid edging, cove fascia, leveler pads \u00b7 0.94 BF net, 2 with waste","board ft",2,RATES["wal44"]),
 ("Walnut 8/4","spacer bar, 2 @ 23 \u00d7 2 \u00d7 1 1/2","board ft",2,RATES["wal84"]),
 ("Birch ply 3/4","french cleat pair, hidden behind the overhead","part sheet",1,RATES["birch"]),
 ("Shop supplies and finish","adhesive, splines, fasteners, abrasives, matched finish","lot",1,95.00),
]
LED=[
 ("Hue Lightstrip Plus base kit 2 m","controller + PSU \u00b7 one per side","https://www.amazon.com/dp/B08CKJWSFS",2,100.00),
 ("Hue Lightstrip extension 1 m","3 per side \u00b7 confirm V4 on the listing","https://www.amazon.com/dp/B0167H31CI",6,30.00),
 ("Litcessory jumper V4 MICRO, short","5 per side, between shelves","https://www.amazon.com/s?k=Litcessory+micro+6-pin+V4",10,7.00),
 ("Litcessory jumper V4 MICRO, long","2 per side, tower to overhead","https://www.amazon.com/s?k=Litcessory+micro+6-pin+V4+6ft",4,11.00),
 ("Legrand power centre, 10 ft cord","one per base cabinet \u00b7 both reach the 36\u2033 outlet","https://www.amazon.com/dp/B08WHYFYPT",2,130.00),
 ("Hue Dimmer V2 + 2 White Ambiance A19","sconce bulbs AND the remote","https://www.amazon.com/dp/B09PZW227V",1,70.00),
 ("Hue Bridge","scenes, remote, colour matching","https://www.amazon.com/dp/B016H0QZ7I",1,60.00),
 ("VIPWELL mountable surge strip","screwed inside each base cabinet \u00b7 always-on","https://www.amazon.com/dp/B0FM73BMPY",2,18.00),
 ("Ultra-thin flat-plug surge strip","at the wall outlet, behind the sofa","https://www.amazon.com/dp/B09JK3B1NC",1,28.00),
 ("Styrene lampshade diffuser sheet","white/tan \u00b7 covers the lit reveal","https://www.amazon.com/s?k=styrene+lampshade+liner+sheet",1,28.00),
]


SCOPE=[  # extra-scope work, the 5.5 h
 ("Overhead rebuilt to four bays","dividers, dados, back panels",2.0),
 ("Solid walnut edging","94 lin ft, applied and flush-trimmed",1.5),
 ("Concealed cove lighting, 16 runs","fit, wire and test before close",1.5),
 ("Spacer bar fit + leveler pads","to the new base height",0.5),
]
MATSUB=sum(q*p for _,_,_,q,p in MAT)
LEDSUB=sum(q*p for _,_,_,q,p in LED)
LEDSELL=LEDSUB*(1+S["MARKUP"])
GOODS=MATSUB+LEDSUB
GOODSELL=GOODS*(1+S["MARKUP"])
MATSELL=MATSUB*(1+S["MARKUP"])
LAB=S["LABOR_HRS"]*S["LABOR_RATE"]
TOTAL=GOODSELL+LAB
assert abs(sum(h for _,_,h in SCOPE)-S["LABOR_HRS"])<1e-9, "scope hours must total LABOR_HRS"
PW,PH=792,612
INK,HAIR,MUTED,GOLD,RED,PAPER="#4E5257","#DEDAD3","#96907F","#B8912F","#B4553C","#FBFAF7"
_ENT=_re.compile(r'&(?!(?:#\d+|#x[0-9A-Fa-f]+|[A-Za-z]+);)')
def esc(t): return _ENT.sub('&amp;',str(t))
def fr(x,d=32):
    from math import gcd
    n=round(x*d); w=n//d; r=n%d
    if r==0: return f'{w}"'
    g=gcd(r,d); return (f'{w} ' if w else '')+f'{r//g}/{d//g}"'
def txt(x,y,s,size=8,anchor="start",fill=None,mono=False,bold=False):
    s=esc(s); f="DejaVu Sans Mono" if mono else "DejaVu Sans"
    b=' font-weight="bold"' if bold else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{f}" font-size="{size}" '
            f'fill="{fill or INK}" text-anchor="{anchor}"{b}>{s}</text>')
def r_(x,y,w,h,fill,st=INK,sw=1):
    return f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" fill="{fill}" stroke="{st}" stroke-width="{sw}"/>'
def line(x1,y1,x2,y2,st=INK,sw=1):
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{st}" stroke-width="{sw}"/>'
def page(body,n,tot,title,sub,foot):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW}" height="{PH}" viewBox="0 0 {PW} {PH}">'
      f'<rect width="{PW}" height="{PH}" fill="#ffffff"/>'
      f'<rect x="28" y="26" width="{PW-56}" height="{PH-52}" fill="none" stroke="{HAIR}"/>'
      +txt(40,52,title,13.5,bold=True)+txt(40,68,sub,8.0,fill=MUTED)
      +txt(PW-40,52,f'REV {S["rev"]}',13.5,"end")+txt(PW-40,68,S["brand"],7.2,"end",MUTED)
      +line(28,80,PW-28,80,HAIR)+line(28,PH-46,PW-28,PH-46,HAIR)
      +txt(40,PH-32,f'{S["job"]} \u00b7 {S["client"]}',6.8,fill=MUTED)
      +txt(PW/2,PH-32,foot,6.8,"middle",RED,bold=True)
      +txt(PW-40,PH-32,f'SHEET {n} / {tot} \u00b7 {S["date"]}',6.8,"end",MUTED)
      +body+'</svg>')

# ══════════════════ INTERNAL · SHOP SET ══════════════════
def sh1():
    o=[]
    o.append(txt(40,106,"A \u00b7 SOLID WALNUT",9.2,bold=True))
    WAL=[("M","Spacer bar",2,'23 \u00d7 2 \u00d7 1 1/2',"8/4"),
         ("N","Round tapered leg \u2014 COM, by client",8,'4 \u00d7 2 1/4 dia',"\u2014"),
         ("P","Leveler pad",4,'4 \u00d7 2 \u00d7 0.91',"4/4"),
         ("U","Edging, shelf / cap",12,'20 \u00d7 3/4 \u00d7 1/8',"4/4"),
         ("V","Edging, side stile",4,'88 1/4 \u00d7 3/4 \u00d7 1/8',"4/4"),
         ("W","Edging, overhead",2,'80 \u00d7 3/4 \u00d7 1/8',"4/4"),
         ("X","Edging, upright",5,'12 1/4 \u00d7 3/4 \u00d7 1/8',"4/4"),
         ("Y","Cove fascia, tower",12,'20 9/16 \u00d7 3/4 \u00d7 1/8',"4/4"),
         ("Z","Cove fascia, overhead",4,'18 3/32 \u00d7 3/4 \u00d7 1/8',"4/4")]
    o.append(txt(40,122,"TAG",6.2,fill=MUTED,mono=True)); o.append(txt(70,122,"PART",6.2,fill=MUTED,mono=True))
    o.append(txt(268,122,"QTY",6.2,"end",MUTED,mono=True)); o.append(txt(430,122,"SIZE",6.2,"end",MUTED,mono=True))
    o.append(line(40,126,430,126,HAIR))
    for i,(t,n,q,sz,g) in enumerate(WAL):
        yy=138+i*14.4
        o.append(txt(40,yy,t,7.2,bold=True,mono=True)); o.append(txt(70,yy,n,7.0))
        o.append(txt(268,yy,str(q),7.0,"end",mono=True)); o.append(txt(430,yy,sz,6.8,"end",mono=True))
        o.append(line(40,yy+4,430,yy+4,HAIR,.4))
    o.append(txt(40,278,"Net 0.94 BF of 4/4 and 0.96 BF of 8/4 \u2014 1/8\u2033 stock resaws 3 to a board.",6.9,fill=MUTED))
    o.append(txt(40,289,"BUY 2 BF of 4/4, 2 BF of 8/4. Legs are COM.",6.9,fill=MUTED))
    o.append(txt(40,314,"B \u00b7 SHEET GOODS \u00b7 walnut ply already on hand",9.2,bold=True))
    PLY=[("Q","Tower back panel",2,'88 1/4 \u00d7 22 1/16','0.72 walnut ply'),
         ("T","Overhead back, per bay",4,'19 3/32 \u00d7 12 1/4','0.72 walnut ply'),
         ("R","Overhead top / bottom",2,'80 \u00d7 6 17/32','0.72 walnut ply'),
         ("S","Overhead upright",5,'12 1/4 \u00d7 6 17/32','0.72 walnut ply'),
         ("AA","French cleat, 45\u00b0",2,'80 \u00d7 4','0.75 birch \u2014 buy')]
    o.append(txt(40,330,"TAG",6.2,fill=MUTED,mono=True)); o.append(txt(70,330,"PART",6.2,fill=MUTED,mono=True))
    o.append(txt(268,330,"QTY",6.2,"end",MUTED,mono=True)); o.append(txt(430,330,"SIZE",6.2,"end",MUTED,mono=True))
    o.append(line(40,334,430,334,HAIR))
    for i,(t,n,q,sz,m) in enumerate(PLY):
        yy=348+i*15.4
        o.append(txt(40,yy,t,7.2,bold=True,mono=True)); o.append(txt(70,yy,n,7.0))
        o.append(txt(268,yy,str(q),7.0,"end",mono=True)); o.append(txt(430,yy,sz,6.8,"end",mono=True))
        o.append(line(40,yy+4,430,yy+4,HAIR,.4))
    o.append(txt(40,440,"Panel plan \u00b7 24 \u00d7 96 project panels from stock",8.4,bold=True))
    for i,t in enumerate(["Panel 1 \u2014 tower back Q (88 1/4 of the 96)","Panel 2 \u2014 tower back Q",
        "Panel 3 \u2014 four overhead backs T, two rows of two",
        "Panel 4 \u2014 overhead top and bottom R, side by side",
        "Panel 5 \u2014 five uprights S, with spare",
        "Birch offcut \u2014 both cleats AA, ripped at 45\u00b0 from one 8\u2033 strip"]):
        o.append(txt(40,456+i*12,"\u2022 "+t,6.9))
    o.append(txt(40,536,"C \u00b7 SHOP COST \u2014 DO NOT SEND TO CLIENT",8.8,bold=True,fill=RED))
    o.append(txt(40,552,f'Shop materials ${MATSUB:,.2f} \u00b7 LED ${LEDSUB:,.2f} \u00b7 goods ${GOODS:,.2f}',7.2))
    o.append(txt(40,564,f'Billed at +{S["MARKUP"]*100:.0f}% = ${GOODSELL:,.2f}, plus {S["LABOR_HRS"]} h = ${TOTAL:,.2f}',7.2))
    # right column
    o.append(r_(452,96,300,128,"#FFF9F0",GOLD,1.2))
    o.append(txt(464,114,"AS-BUILT GEOMETRY \u2014 CONFIRMED",7.8,bold=True,fill=GOLD))
    for i,t in enumerate(["Five shelves, six openings. Undersides at",
        "38 1/2 \u00b7 51 15/32 \u00b7 64 7/16 \u00b7 77 13/32 \u00b7 90 3/8 AFF.",
        "Five openings at 12 1/4, top 22 9/16 stated.",
        "Shelf positions FIXED. Clears sum 1/8\u2033 short of 88 1/4 \u2014 measure.",
        "Overall 114 1/2\u2033. Towers untrimmed at 88 1/4.",
        "Base top 26 1/4 = 4\u2033 leg + 2\u2033 bar + 20 1/4 carcass.",
        "Dados 1/4 deep \u00d7 23/32 wide, shelves and uprights.",
        "Overhead usable depth 6 17/32 after the cleat."]):
        o.append(txt(464,130+i*11.6,t,6.6))
    o.append(txt(452,248,"D \u00b7 SEQUENCE",9.0,bold=True,fill=RED))
    for i,t in enumerate(["1. Back panels fitted and pinned.",
        "2. Source set at the back of each shelf underside.",
        "3. Wire both sides. TEST ALL SIXTEEN LIT.",
        "4. Only then fit the fascia, closing the cove.",
        "5. Face trim last \u2014 stiles run full height, bands butt to them.",
        "",
        "We now supply the LED, so a dead strip behind a pinned",
        "panel is our warranty problem. Test twice."]):
        o.append(txt(452,266+i*12.4,t,7.0,fill=(RED if i>=6 else INK)))
    o.append(txt(452,378,"E \u00b7 OPEN",9.0,bold=True))
    for i,t in enumerate(["Ceiling 136\u2033 confirmed by field scan \u2014 21 1/2\u2033 clear above the unit.",
        "Wall-to-wall width \u2014 scribe allowance only.",
        "Client to supply 8 legs, COM to the sofa.",
        "Curtain track position."]):
        o.append(txt(452,396+i*12.4,"\u2022 "+t,7.0))
    return page("".join(o),1,1,"Shop Set \u2014 Materials, Geometry, Sequence",
        "Everything the bench needs \u00b7 costs and open items included","INTERNAL \u2014 NOT FOR CLIENT")

sv=sh1()
b=io.BytesIO(); cairosvg.svg2pdf(bytestring=sv.encode(),write_to=b,dpi=72); b.seek(0)
w=PdfWriter(); w.add_page(PdfReader(b).pages[0])
w.add_metadata({"/Title":"R6 REV G Shop Set - INTERNAL"})
with open("/mnt/user-data/outputs/R6-SHOP-internal-rev-G.pdf","wb") as f: w.write(f)
cairosvg.svg2png(bytestring=sv.encode(),write_to="/home/claude/SH.png",scale=1.7)
print("shop set ok")
