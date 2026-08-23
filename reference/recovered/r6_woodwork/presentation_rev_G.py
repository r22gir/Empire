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
 ("Legrand power centre","one per base cabinet \u00b7 plugs into the strip inside","https://www.amazon.com/dp/B08WHYFYPT",2,120.00),
 ("Hue Dimmer V2 + 2 White Ambiance A19","sconce bulbs AND the remote","https://www.amazon.com/dp/B09PZW227V",1,70.00),
 ("Hue Bridge","scenes, remote, colour matching","https://www.amazon.com/dp/B016H0QZ7I",1,60.00),
 ("CCCEI mountable strip, 10 ft cord","the hub \u2014 screwed inside each cabinet, one per side","https://www.amazon.com/dp/B0DP8G4WG6",2,28.00),
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

# ══════════════════ PRESENTATION + PRODUCT SHEETS ══════════════════
G=dict(W=126.0,T=.72,BAY_L=23.0,BAY_R=103.0,MOD=23.0,TOWER_D=8.0,BASE_D=17.97,
 LEG=4.0,BAR=2.0,CARC=20.25,DOOR=18.25,RAIL=2.0,TOWER=88.25,
 TOP_CLR=22.5625,MID_CLR=12.25,NSH=5,UP=12.25,NUP=5,BAYS=4,
 SOFA=(79.0,36.0,37.0),ARM=28.25,SEAT=20.0,SOFA_LEG=4.0,
 SC_MID=58.3125,SC_BPH=12.6,SC_PROJ=5.5,SC_SHH=9.0,TRIM_F=.75)
G["BB"]=G["LEG"]+G["BAR"]; G["BT"]=G["BB"]+G["CARC"]; G["H"]=G["BT"]+G["TOWER"]
G["PITCH"]=G["MID_CLR"]+G["T"]
G["SH"]=[G["BT"]+G["MID_CLR"]+i*G["PITCH"] for i in range(G["NSH"])][::-1]
G["bay"]=(80.0-G["NUP"]*G["T"])/G["BAYS"]
G["ohBox"]=G["UP"]+2*G["T"]; G["ohBot"]=G["H"]-G["ohBox"]
WAL,WALD,WALL_="#8E6248","#6B4632","#A8825F"

def leg(X,Y,lx,h,rT=1.15,rB=.52,rake=8,fill=WALD):
    run=h*math.tan(math.radians(rake))
    return (f'<path d="M {X(lx-rT):.1f} {Y(h):.1f} L {X(lx+rT):.1f} {Y(h):.1f} '
            f'L {X(lx+rB+run):.1f} {Y(0):.1f} L {X(lx-rB-run):.1f} {Y(0):.1f} Z" '
            f'fill="{fill}" stroke="#3E2819" stroke-width="0.8"/>')

def elevation(ax,ay,k):
    X=lambda v: ax+v*k; Y=lambda v: ay-v*k
    TF=G["TRIM_F"]; o=[line(X(-14),Y(0),X(G["W"]+14),Y(0),INK,1.4)]
    # sofa first, behind
    x0=G["BAY_L"]+.5; W_,D_,H_=G["SOFA"]; L=G["SOFA_LEG"]; A=G["ARM"]; ST=G["SEAT"]
    UP_,MID,DK,ED="#CFC0A8","#BCAA8E","#9E8B70","#6E5D48"
    o.append(r_(X(x0+4),Y(H_),(W_-8)*k,(H_-L-2)*k,UP_,ED,1))
    for i in range(2):
        bx=x0+5+i*((W_-10)/2)
        o.append(r_(X(bx),Y(H_-1.5),((W_-10)/2-1)*k,(H_-ST-3.5)*k,MID,ED,.9))
    for i in range(2):
        sx=x0+5.5+i*((W_-11)/2)
        o.append(r_(X(sx),Y(ST),((W_-11)/2-1)*k,(ST-L-1.5)*k,DK,ED,.9))
    for ax_ in (x0,x0+W_-5.5):
        o.append(r_(X(ax_),Y(A-1.4),5.5*k,(A-L-1.4)*k,MID,ED,1))
        o.append(f'<path d="M {X(ax_):.1f} {Y(A-1.4):.1f} Q {X(ax_):.1f} {Y(A):.1f} '
                 f'{X(ax_+2.75):.1f} {Y(A):.1f} Q {X(ax_+5.5):.1f} {Y(A):.1f} '
                 f'{X(ax_+5.5):.1f} {Y(A-1.4):.1f} Z" fill="{UP_}" stroke="{ED}" stroke-width="1"/>')
    o.append(r_(X(x0),Y(L+2.2),W_*k,2.2*k,DK,ED,1))
    for lx in (x0+2.8,x0+W_-2.8): o.append(leg(X,Y,lx,L,.85,.42,8,"#5A3A28"))
    # unit
    for bx in (0,G["BAY_R"]):
        for lx in (bx+2.6,bx+G["MOD"]-2.6): o.append(leg(X,Y,lx,G["LEG"]))
        o.append(r_(X(bx),Y(G["BB"]),G["MOD"]*k,G["BAR"]*k,WAL,"#3E2819",1))
        o.append(r_(X(bx),Y(G["BB"]+G["DOOR"]),G["MOD"]*k,G["DOOR"]*k,WALL_,"#5A3A28",1))
        o.append(r_(X(bx),Y(G["BT"]),G["MOD"]*k,G["RAIL"]*k,WALD,"#3E2819",1))
        pull=bx+G["MOD"]-2.4 if bx==0 else bx+2.0
        o.append(r_(X(pull),Y(G["BB"]+12),.5*k,4.5*k,"#9AA0A6","#6E747A",.8))
        o.append(r_(X(bx),Y(G["H"]),G["MOD"]*k,G["TOWER"]*k,"#FBFAF7",INK,1.2))
        o.append(r_(X(bx),Y(G["H"]),G["T"]*k,G["TOWER"]*k,WAL,"#5A3A28",.8))
        o.append(r_(X(bx+G["MOD"]-G["T"]),Y(G["H"]),G["T"]*k,G["TOWER"]*k,WAL,"#5A3A28",.8))
        for z in G["SH"]+[G["H"]]:
            o.append(r_(X(bx+G["T"]),Y(z),(G["MOD"]-2*G["T"])*k,G["T"]*k,WAL,"#5A3A28",.8))
            o.append(line(X(bx+TF+.3),Y(z-TF-.15),X(bx+G["MOD"]-TF-.3),Y(z-TF-.15),"#E8C877",1.6))
    o.append(r_(X(G["BAY_L"]),Y(G["H"]),80*k,G["ohBox"]*k,"#FBFAF7",INK,1.2))
    o.append(r_(X(G["BAY_L"]),Y(G["H"]),80*k,G["T"]*k,WAL,"#5A3A28",.8))
    o.append(r_(X(G["BAY_L"]),Y(G["ohBot"]+G["T"]),80*k,G["T"]*k,WAL,"#5A3A28",.8))
    p=0.0
    for i in range(G["NUP"]):
        o.append(r_(X(G["BAY_L"]+p),Y(G["ohBot"]+G["T"]+G["UP"]),G["T"]*k,G["UP"]*k,WAL,"#5A3A28",.8))
        if i<G["BAYS"]:
            o.append(line(X(G["BAY_L"]+p+TF+.4),Y(G["H"]-TF-.5),
                          X(G["BAY_L"]+p+TF+G["bay"]-.4),Y(G["H"]-TF-.5),"#E8C877",1.6))
        p+=G["T"]+G["bay"]
    for fx,sg in ((G["BAY_L"],1),(G["BAY_R"],-1)):
        top=G["SC_MID"]+G["SC_BPH"]/2
        o.append(r_(X(min(fx,fx+sg*.75)),Y(top),.75*k,G["SC_BPH"]*k,"#B2913F","#7A6228",1))
        sx0=fx+sg*.75 if sg>0 else fx-G["SC_PROJ"]
        o.append(r_(X(sx0),Y(top-1),(G["SC_PROJ"]-.75)*k,G["SC_SHH"]*k,"#F4EFE3","#C9C2B0",1))
    return "".join(o)

def p1():
    o=[elevation(268,548,3.05)]
    o.append(txt(40,106,"WALNUT SOFA SURROUND",10.4,bold=True))
    o.append(txt(40,120,f'{fr(G["W"])} \u00d7 {fr(G["H"])} \u00d7 {fr(G["BASE_D"])}',7.4,fill=MUTED))
    SPEC=[("Base top",f'{fr(G["BT"])} AFF'),("Under sofa arm",'2"'),
          ("Legs",'4" round tapered, COM'),("Spacer bar",'2" solid walnut'),
          ("Towers",f'{fr(G["MOD"])} \u00d7 {fr(G["TOWER"])}'),
          ("Shelves",f'5 per tower \u00b7 {fr(G["MID_CLR"])} clear'),
          ("Top opening",f'{fr(G["TOP_CLR"])}'),
          ("Overhead",f'4 bays {fr(G["bay"])} \u00d7 {fr(G["UP"])}'),
          ("Edges",'1/8" solid walnut, flush'),
          ("Lighting",'16 concealed coves, tunable'),
          ("Sconces",'brass + linen, 58 5/16" AFF'),
          ("Power",'2 recessed centres, USB A+C')]
    for i,(a,b_) in enumerate(SPEC):
        yy=148+i*21
        o.append(txt(40,yy,a,6.3,fill=MUTED,mono=True))
        o.append(txt(40,yy+10,b_,7.5,bold=True))
        o.append(line(40,yy+14,196,yy+14,HAIR,.4))
    return page("".join(o),1,2,"Presentation \u2014 REV G",
        "Gold lines mark the concealed coves \u00b7 sofa shown for scale","FINAL DESIGN")

# ── product illustrations, drawn to the real hardware ──────────────────
def rr(x,y,w,h,r,fill,st,sw=1):
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{r}" '
            f'fill="{fill}" stroke="{st}" stroke-width="{sw}"/>')

def ic_strip(x,y):
    """Hue Lightstrip Plus: white flexible tape, warm emitters, inline controller."""
    o=[rr(x+2,y+16,74,9,2,"#FAFAF8","#C9C2B0",1)]
    for i in range(12):
        o.append(f'<circle cx="{x+8+i*6}" cy="{y+20.5}" r="1.9" fill="#F4D68B" stroke="#C9A85C" stroke-width="0.4"/>')
    o.append(rr(x+76,y+13,16,15,2,"#3A3A3A","#1C1C1C",1))          # controller
    o.append(f'<circle cx="{x+84}" cy="{y+20}" r="2.6" fill="#5A5A5A"/>')
    o.append(f'<path d="M {x+2} {y+20} L {x-4} {y+20}" stroke="#4A4E54" stroke-width="1.6"/>')
    return "".join(o)

def ic_ext(x,y):
    """1 m extension: tape plus a 6-pin coupler at one end."""
    o=[rr(x+10,y+16,72,9,2,"#FAFAF8","#C9C2B0",1)]
    for i in range(11):
        o.append(f'<circle cx="{x+16+i*6}" cy="{y+20.5}" r="1.9" fill="#F4D68B" stroke="#C9A85C" stroke-width="0.4"/>')
    o.append(rr(x+2,y+14,10,13,1.5,"#E8E4DC","#B9B2A6",1))
    for i in range(3):
        o.append(f'<rect x="{x+4+i*2.6}" y="{y+17}" width="1.2" height="7" fill="#9AA0A6"/>')
    return "".join(o)

def ic_jumper(x,y):
    """Litcessory 6-pin: flat ribbon with a moulded connector each end."""
    o=[f'<path d="M {x+18} {y+20} Q {x+44} {y+34} {x+70} {y+20}" fill="none" stroke="#E4E0D8" stroke-width="6"/>',
       f'<path d="M {x+18} {y+20} Q {x+44} {y+34} {x+70} {y+20}" fill="none" stroke="#C9C2B0" stroke-width="1"/>']
    for cx in (x+8,x+70):
        o.append(rr(cx,y+14,12,13,1.5,"#F2EFE9","#B9B2A6",1))
        for i in range(3):
            o.append(f'<rect x="{cx+2.4+i*2.8}" y="{y+17}" width="1.3" height="7" fill="#9AA0A6"/>')
    return "".join(o)

def ic_outlet(x,y):
    """Legrand radiant RDSZCBK: black bezel, lamp button, USB A+C, two TR outlets."""
    o=[rr(x+2,y+4,90,40,3,"#1F1F1F","#0D0D0D",1.2)]              # bezel
    o.append(rr(x+5,y+7,84,34,2,"#2B2B2B","#141414",.8))          # face
    # lamp push-button, left
    o.append(rr(x+9,y+13,15,15,2,"#3A3A3A","#141414",.8))
    o.append(f'<circle cx="{x+16.5}" cy="{y+19}" r="3.4" fill="none" stroke="#D8D4CC" stroke-width="1.1"/>')
    o.append(f'<rect x="{x+15.2}" y="{y+22.4}" width="2.6" height="2.4" fill="#D8D4CC"/>')
    # USB-A then USB-C
    o.append(rr(x+28,y+16,11,5,1,"#111","#000",.6))
    o.append(f'<rect x="{x+29.4}" y="{y+18.4}" width="8.2" height="1.4" fill="#4A6FA5"/>')
    o.append(rr(x+28,y+25,11,4,2,"#111","#000",.6))
    o.append(f'<rect x="{x+29.6}" y="{y+26.4}" width="7.8" height="1.2" rx="0.6" fill="#5A5A5A"/>')
    # two tamper-resistant outlets
    for cx in (x+52,x+72):
        o.append(rr(cx-8,y+11,16,20,2,"#3A3A3A","#141414",.8))
        o.append(f'<rect x="{cx-4.4}" y="{y+15}" width="2.2" height="6.4" rx="0.8" fill="#0D0D0D"/>')
        o.append(f'<rect x="{cx+2.2}" y="{y+15}" width="2.2" height="6.4" rx="0.8" fill="#0D0D0D"/>')
        o.append(f'<circle cx="{cx}" cy="{y+26}" r="2.2" fill="#0D0D0D"/>')
    return "".join(o)

def ic_dimmer(x,y):
    """Hue Dimmer V2: white rounded switch, four buttons."""
    o=[rr(x+30,y+3,30,40,5,"#FBFAF8","#C9C2B0",1)]
    o.append(rr(x+34,y+7,22,8,2,"#F2EFE9","#D8D4CC",.7))          # on
    o.append(f'<circle cx="{x+45}" cy="{y+11}" r="2.4" fill="none" stroke="#8A8F96" stroke-width="1"/>')
    o.append(rr(x+34,y+17,22,7,2,"#F2EFE9","#D8D4CC",.7))         # brighter
    o.append(f'<path d="M {x+42} {y+20.5} L {x+48} {y+20.5} M {x+45} {y+18} L {x+45} {y+23}" stroke="#8A8F96" stroke-width="1"/>')
    o.append(rr(x+34,y+26,22,7,2,"#F2EFE9","#D8D4CC",.7))         # dimmer
    o.append(f'<path d="M {x+42} {y+29.5} L {x+48} {y+29.5}" stroke="#8A8F96" stroke-width="1"/>')
    o.append(rr(x+34,y+35,22,6,2,"#F2EFE9","#D8D4CC",.7))         # off
    o.append(f'<circle cx="{x+45}" cy="{y+38}" r="2" fill="none" stroke="#8A8F96" stroke-width="1"/>')
    return "".join(o)

def ic_bridge(x,y):
    """Hue Bridge: white square, round centre button, three status LEDs."""
    o=[rr(x+22,y+6,44,34,6,"#FBFAF8","#C9C2B0",1)]
    o.append(f'<circle cx="{x+44}" cy="{y+20}" r="8.5" fill="#F4F1EB" stroke="#B9B2A6" stroke-width="1"/>')
    o.append(f'<circle cx="{x+44}" cy="{y+20}" r="4" fill="none" stroke="#8A8F96" stroke-width="1.1"/>')
    for i,c in enumerate(("#4C7A4C","#4C7A4C","#4C7A4C")):
        o.append(f'<circle cx="{x+34+i*10}" cy="{y+34}" r="1.8" fill="{c}"/>')
    return "".join(o)

def ic_bulb(x,y):
    """A19 White Ambiance."""
    o=[f'<path d="M {x+44} {y+4} C {x+55} {y+4} {x+59} {y+13} {x+55} {y+22} '
       f'C {x+52} {y+27} {x+51} {y+28} {x+51} {y+31} L {x+37} {y+31} '
       f'C {x+37} {y+28} {x+36} {y+27} {x+33} {y+22} '
       f'C {x+29} {y+13} {x+33} {y+4} {x+44} {y+4} Z" fill="#FBF3DC" stroke="#C9C2B0" stroke-width="1"/>']
    for i in range(3):
        o.append(f'<rect x="{x+37}" y="{y+32+i*3}" width="14" height="2" rx="1" fill="#C9CDD2" stroke="#9AA0A6" stroke-width="0.4"/>')
    o.append(rr(x+39,y+41,10,3,1,"#8A8F96","#6E747A",.6))
    return "".join(o)

def ic_styrene(x,y):
    """Shade-material sheet, warm white, one corner lifted."""
    o=[f'<path d="M {x+14} {y+8} L {x+72} {y+8} L {x+72} {y+40} L {x+14} {y+40} Z" '
       f'fill="#F8F3E6" stroke="#C9C2B0" stroke-width="1"/>']
    o.append(f'<path d="M {x+58} {y+8} L {x+72} {y+22} L {x+72} {y+8} Z" fill="#EDE4CE" stroke="#C9C2B0" stroke-width="1"/>')
    o.append(f'<path d="M {x+58} {y+8} L {x+72} {y+22}" stroke="#B9B2A6" stroke-width="1"/>')
    for i in range(3):
        o.append(f'<line x1="{x+22}" y1="{y+16+i*7}" x2="{x+52}" y2="{y+16+i*7}" stroke="#E4DCC8" stroke-width="1.4"/>')
    return "".join(o)

def ic_powerstrip(x,y):
    o=[rr(x+8,y+14,72,16,3,"#F2EFE9","#B9B2A6",1)]
    for i in range(3):
        cx=x+22+i*20
        o.append(rr(cx-7,y+18,14,9,1.5,"#E4E0D8","#B9B2A6",.7))
        o.append(f'<rect x="{cx-3.4}" y="{y+20}" width="1.8" height="4.4" fill="#8A8F96"/>')
        o.append(f'<rect x="{cx+1.6}" y="{y+20}" width="1.8" height="4.4" fill="#8A8F96"/>')
    o.append(f'<path d="M {x+8} {y+22} L {x-2} {y+22}" stroke="#4A4E54" stroke-width="2"/>')
    return "".join(o)
def ic_cord(x,y):
    o=[f'<path d="M {x+14} {y+20} Q {x+44} {y+38} {x+74} {y+20}" fill="none" stroke="#3A3A3A" stroke-width="3.4"/>']
    o.append(rr(x+6,y+14,10,12,1.5,"#F2EFE9","#B9B2A6",1))
    o.append(f'<rect x="{x+8.6}" y="{y+17}" width="1.6" height="6" fill="#8A8F96"/>')
    o.append(f'<rect x="{x+12}" y="{y+17}" width="1.6" height="6" fill="#8A8F96"/>')
    o.append(rr(x+72,y+13,12,14,1.5,"#3A3A3A","#1C1C1C",1))
    return "".join(o)
ICONS=[ic_strip,ic_ext,ic_jumper,ic_jumper,ic_outlet,ic_dimmer,ic_bridge,
       ic_powerstrip,ic_styrene]
DESC=["Specified after assessing the options against adjustable colour temperature and sconce matching. Cuttable and dimmable; one controller and supply per side, both joined in a single Hue Room.",
 "One-metre extensions that carry the run from tower to overhead. Confirm the listing reads V4 \u2014 earlier versions use a different connector.",
 "Short six-pin jumpers, five per side, bridging the gap between shelves so each cut segment stays on one circuit.",
 "Longer six-pin jumpers, two per side, carrying the run from the top of each tower across to the overhead bays.",
 "Black bezel flush in the cabinet top. Lamp button at the left switches the sconce only; then USB-A, USB-C and two tamper-resistant outlets.",
 "Four buttons \u2014 on, brighter, dimmer, off \u2014 on a magnetic wall plate. Ships with the two sconce bulbs. Scene cycling without reaching for a phone.",
 "The reason this system was chosen: it is what allows shelves and sconces to hold the same colour temperature on one scene.",
 "Screwed to the cabinet floor. The power centre and the lighting supply both plug in here, and its 10 ft cord is the only thing that leaves the cabinet \u2014 straight to its own receptacle.",
 "Warm-white shade material, cut to close the lit reveal. Retained by a 1/4\u2033 walnut strip so the source is never visible from the room."]

def p2():
    o=[]
    o.append(txt(40,106,"SPECIFIED PRODUCTS",9.6,bold=True))
    o.append(txt(40,119,"supplied, installed and tested by the workroom \u00b7 tap any link",7.2,fill=MUTED))
    for i,(nm,short,url,q,pr) in enumerate(LED):
        col=i%2; row=i//2
        x=40+col*366; y=136+row*80
        o.append(r_(x,y,352,72,"#FBFAF7",HAIR,1))
        o.append(r_(x+8,y+7,84,44,"#FFFFFF",HAIR,.8))
        o.append(ICONS[i](x+2,y+4))
        o.append(txt(x+100,y+20,nm,7.3,bold=True))
        o.append(txt(x+100,y+31,f'Qty {q} \u00b7 ${pr:,.2f}',6.4,fill=GOLD,mono=True))
        # wrapped description
        words=DESC[i].split(); lines=[];cur=""
        for w_ in words:
            if len(cur+" "+w_)>40 and cur: lines.append(cur);cur=w_
            else: cur=(cur+" "+w_).strip()
        if cur: lines.append(cur)
        for j,ln in enumerate(lines[:3]):
            o.append(txt(x+100,y+44+j*9.0,ln,6.2,fill=MUTED))
        o.append(txt(x+100,y+69,url.replace("https://www.","")[:42],5.7,fill="#2B5AA0",mono=True))
        LINKS.append((1,x+100,y+62,x+100+len(url)*2.9,y+73,url))
    o.append(line(40,PH-66,PW-40,PH-66,HAIR))
    o.append(txt(40,PH-52,f'{sum(q for _,_,_,q,_ in LED)} items \u00b7 ${LEDSUB:,.2f} at cost \u00b7 priced with the change order',7.4,bold=True))
    o.append(txt(452,PH-52,"Street prices \u00b7 confirmed at the time of order.",6.8,fill=MUTED))
    return page("".join(o),2,2,"Products & Finishes",
        "What goes into the piece \u00b7 links open the product page","FINAL DESIGN")

LINKS=[]
sheets=[p1(),p2()]
w=PdfWriter()
for sv in sheets:
    b=io.BytesIO(); cairosvg.svg2pdf(bytestring=sv.encode(),write_to=b,dpi=72); b.seek(0)
    w.add_page(PdfReader(b).pages[0])
from pypdf.generic import DictionaryObject,NameObject,ArrayObject,NumberObject,TextStringObject
for pi,x0,y0,x1,y1,url in LINKS:
    pg=w.pages[pi]; ph=float(pg.mediabox.height)
    ann=DictionaryObject({NameObject("/Type"):NameObject("/Annot"),
        NameObject("/Subtype"):NameObject("/Link"),
        NameObject("/Rect"):ArrayObject([NumberObject(x0),NumberObject(ph-y1),NumberObject(x1),NumberObject(ph-y0)]),
        NameObject("/Border"):ArrayObject([NumberObject(0),NumberObject(0),NumberObject(0)]),
        NameObject("/A"):DictionaryObject({NameObject("/S"):NameObject("/URI"),
            NameObject("/URI"):TextStringObject(url)})})
    ref=w._add_object(ann)
    if "/Annots" in pg: pg["/Annots"].append(ref)
    else: pg[NameObject("/Annots")]=ArrayObject([ref])
w.add_metadata({"/Title":"R6 REV G Presentation & Products"})
with open("/mnt/user-data/outputs/R6-presentation-rev-G.pdf","wb") as f: w.write(f)
for i,sv in enumerate(sheets,1):
    cairosvg.svg2png(bytestring=sv.encode(),write_to=f"/home/claude/PR{i}.png",scale=1.7)
print(f'presentation ok \u00b7 overall {fr(G["H"])} \u00b7 {len(LED)} products \u00b7 ${LEDSUB:,.2f}')
