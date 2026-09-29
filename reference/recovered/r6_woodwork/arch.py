"""R6 REV G architectural set - plan, sections, dimensioned elevations. One SPEC."""
import io, math, cairosvg
from pypdf import PdfWriter, PdfReader
S=dict(rev="G",date="2026-08-17",job="R6 Walnut Sofa Surround",
 client="Woodcraft \u2014 Philipp &amp; Naomi",brand="WOODCRAFT BY EMPIRE WORKROOM",
 W=126.0,T=.72,BACK=.72,BAY_L=23.0,BAY_R=103.0,MOD=23.0,
 TOWER_D=8.0,CARC_D=17.25,BASE_D=17.97,
 LEG=4.0,BAR=2.0,BAR_D=1.5,CARC=20.25,DOOR=18.25,RAIL=2.0,
 TOWER=88.25,TOP_CLR=22.5625,MID_CLR=12.25,NSH=5,UP=12.25,NIN=3,BAYS=4,
 CLEAT_T=.72,CLEAT_H=4.0,
 SOFA=(79.0,36.0,37.0),ARM=28.25,SEAT=20.0,SOFA_LEG=4.0,OPEN_D=86.0,
 SC_MID=58.3125,SC_BPH=12.6,SC_PROJ=5.5,SC_SHW=7.0,SC_SHH=9.0,
 TRIM_T=.125,TRIM_F=.75,COVE_T=.25,COVE_D=.75,COVE_SET=1.0,STRIP_W=.45,
 DADO=.25,WALL_R=6.0)
S["BB"]=S["LEG"]+S["BAR"]; S["BT"]=S["BB"]+S["CARC"]
S["H"]=S["BT"]+S["TOWER"]
S["TB"]=80.0-2*S["T"]                       # top/bottom, between the end uprights
S["bay"]=(S["TB"]-S["NIN"]*S["T"])/S["BAYS"]
S["ohBox"]=S["UP"]+2*S["T"]; S["ohBot"]=S["H"]-S["ohBox"]
S["PITCH"]=S["MID_CLR"]+S["T"]
S["SH"]=[S["BT"]+S["MID_CLR"]+i*S["PITCH"] for i in range(S["NSH"])][::-1]
S["TOP_ACT"]=S["H"]-S["T"]-(S["SH"][0]+S["T"])   # top clear that actually closes 88 1/4
S["CAP"]=S["H"]-S["T"]
S["OH_ZONE"]=S["CLEAT_T"]      # cleats INTERLOCK vertically — one thickness, not two
S["OH_DEEP"]=S["TOWER_D"]-S["OH_ZONE"]-S["BACK"]   # 6 17/32 usable
S["OPEN_MID"]=S["MID_CLR"]
S["UP_CUT"]=S["UP"]+2*S["DADO"]   # inner upright: clear + a dado at each end
S["OPEN_BOT"]=S["MID_CLR"]
assert abs(S["BAYS"]*S["bay"]+S["NIN"]*S["T"]-S["TB"])<1e-9
PW,PH=792,612
INK,HAIR,MUTED,GOLD,RED,PAPER="#4E5257","#DEDAD3","#96907F","#B8912F","#B4553C","#FBFAF7"
WAL,WALD,WALL_="#8E6248","#6B4632","#A8825F"
def fr(x,d=32):
    from math import gcd
    n=round(x*d); w=n//d; r=n%d
    if r==0: return f'{w}"'
    g=gcd(r,d); return (f'{w} ' if w else '')+f'{r//g}/{d//g}"'
import re as _re
_ENT=_re.compile(r'&(?!(?:#\d+|#x[0-9A-Fa-f]+|[A-Za-z]+);)')
def esc(t):
    return _ENT.sub('&amp;', str(t))
def txt(x,y,s,size=8,anchor="start",fill=None,mono=False,bold=False,rot=None):
    s=esc(s)
    f="DejaVu Sans Mono" if mono else "DejaVu Sans"
    b=' font-weight="bold"' if bold else ''
    r=f' transform="rotate({rot} {x:.1f} {y:.1f})"' if rot else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{f}" font-size="{size}" '
            f'fill="{fill or INK}" text-anchor="{anchor}"{b}{r}>{s}</text>')
def r_(x,y,w,h,fill,st=INK,sw=1,dash=None):
    d=f' stroke-dasharray="{dash}"' if dash else ''
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="{st}" stroke-width="{sw}"{d}/>')
def line(x1,y1,x2,y2,st=INK,sw=1,dash=None):
    d=f' stroke-dasharray="{dash}"' if dash else ''
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{st}" stroke-width="{sw}"{d}/>'
def dim(x1,y1,x2,y2,lab,vert=False,size=6.0,off=8,col=None):
    c=col or MUTED; s=line(x1,y1,x2,y2,c,.8)
    if vert:
        for y in (y1,y2): s+=line(x1-3,y,x1+3,y,c,.8)
        s+=txt(x1+off,(y1+y2)/2+2.2,lab,size,"start" if off>0 else "end",c,mono=True)
    else:
        for x in (x1,x2): s+=line(x,y1-3,x,y1+3,c,.8)
        s+=txt((x1+x2)/2,y1+off+2.2,lab,size,"middle",c,mono=True)
    return s
def page(body,n,tot,title,sub,scale=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW}" height="{PH}" viewBox="0 0 {PW} {PH}">'
      f'<rect width="{PW}" height="{PH}" fill="#ffffff"/>'
      f'<rect x="28" y="26" width="{PW-56}" height="{PH-52}" fill="none" stroke="{HAIR}"/>'
      +txt(40,52,title,13.5,bold=True)+txt(40,68,sub,8.0,fill=MUTED)
      +txt(PW-40,52,f'REV {S["rev"]}',13.5,"end")+txt(PW-40,68,S["brand"],7.2,"end",MUTED)
      +line(28,80,PW-28,80,HAIR)+line(28,PH-46,PW-28,PH-46,HAIR)
      +txt(40,PH-32,f'{S["job"]} \u00b7 {S["client"]}',6.8,fill=MUTED)
      +txt(PW/2,PH-32,scale or "DIMENSIONS IN INCHES",6.8,"middle",MUTED,mono=True)
      +txt(PW-40,PH-32,f'A{n} \u00b7 SHEET {n} / {tot} \u00b7 {S["date"]}',6.8,"end",MUTED)
      +body+'</svg>')
def sofa_elev(X,Y,k):
    """Braxton sleeper in front elevation - rolled arms, loose back, seat cushions."""
    x0=S["BAY_L"]+.5; W_,D_,H_=S["SOFA"]; L=S["SOFA_LEG"]; A=S["ARM"]; ST=S["SEAT"]
    UP_="#CFC0A8"; MID="#BCAA8E"; DK="#9E8B70"; ED="#6E5D48"
    o=[]
    # back, behind everything
    o.append(r_(X(x0+4),Y(H_),(W_-8)*k,(H_-L-2)*k,UP_,ED,1))
    # back cushions - two, with a seam
    for i in range(2):
        bx=x0+5+i*((W_-10)/2)
        o.append(r_(bx and X(bx),Y(H_-1.5),((W_-10)/2-1)*k,(H_-ST-3.5)*k,MID,ED,.9))
    # seat cushions - two
    for i in range(2):
        sx=x0+5.5+i*((W_-11)/2)
        o.append(r_(X(sx),Y(ST),((W_-11)/2-1)*k,(ST-L-1.5)*k,DK,ED,.9))
    # rolled arms
    for ax_ in (x0,x0+W_-5.5):
        o.append(r_(X(ax_),Y(A-1.4),5.5*k,(A-L-1.4)*k,MID,ED,1))
        o.append(f'<path d="M {X(ax_):.1f} {Y(A-1.4):.1f} '
                 f'Q {X(ax_):.1f} {Y(A):.1f} {X(ax_+2.75):.1f} {Y(A):.1f} '
                 f'Q {X(ax_+5.5):.1f} {Y(A):.1f} {X(ax_+5.5):.1f} {Y(A-1.4):.1f} Z" '
                 f'fill="{UP_}" stroke="{ED}" stroke-width="1"/>')
    # skirt / frame rail
    o.append(r_(X(x0),Y(L+2.2),W_*k,2.2*k,DK,ED,1))
    for lx in (x0+2.8,x0+W_-2.8):
        o.append(leg(X,Y,lx,L,.85,.42,8,fill="#5A3A28"))
    return "".join(o)

def leg(X,Y,lx,h,rT=1.15,rB=.52,rake=8,fill=WALD):
    run=h*math.tan(math.radians(rake))
    return (f'<path d="M {X(lx-rT):.1f} {Y(h):.1f} L {X(lx+rT):.1f} {Y(h):.1f} '
            f'L {X(lx+rB+run):.1f} {Y(0):.1f} L {X(lx-rB-run):.1f} {Y(0):.1f} Z" '
            f'fill="{fill}" stroke="#3E2819" stroke-width="0.8"/>')

# ═════════ A1 · dimensioned front elevation ═════════
def a1():
    k=3.30; ax,ay=150,506
    X=lambda v: ax+v*k; Y=lambda v: ay-v*k
    o=[line(X(-18),Y(0),X(S["W"]+18),Y(0),INK,1.5)]
    TF=S["TRIM_F"]
    for bx in (0,S["BAY_R"]):
        for lx in (bx+2.6,bx+S["MOD"]-2.6): o.append(leg(X,Y,lx,S["LEG"]))
        o.append(r_(X(bx),Y(S["BB"]),S["MOD"]*k,S["BAR"]*k,WAL,"#3E2819",1))
        for lx in (bx+1.5,bx+S["MOD"]-1.5):        # side rails read as end grain
            o.append(line(X(lx),Y(S["BB"]),X(lx),Y(S["LEG"]),"#3E2819",.7))
        o.append(r_(X(bx),Y(S["BB"]+S["DOOR"]),S["MOD"]*k,S["DOOR"]*k,WALL_,"#5A3A28",1))
        o.append(r_(X(bx),Y(S["BT"]),S["MOD"]*k,S["RAIL"]*k,WALD,"#3E2819",1))
        pull=bx+S["MOD"]-2.4 if bx==0 else bx+2.0
        o.append(r_(X(pull),Y(S["BB"]+12),.5*k,4.5*k,"#9AA0A6","#6E747A",.8))
        o.append(r_(X(bx),Y(S["H"]),S["MOD"]*k,S["TOWER"]*k,PAPER,INK,1.2))
        o.append(r_(X(bx),Y(S["H"]),S["T"]*k,S["TOWER"]*k,WAL,"#5A3A28",.8))
        o.append(r_(X(bx+S["MOD"]-S["T"]),Y(S["H"]),S["T"]*k,S["TOWER"]*k,WAL,"#5A3A28",.8))
        for z in [S["BT"]+d for d in (0,)] + []: pass
        for z in S["SH"]+[S["H"]]:
            o.append(r_(X(bx+S["T"]),Y(z),(S["MOD"]-2*S["T"])*k,S["T"]*k,WAL,"#5A3A28",.8))
    o.append(r_(X(S["BAY_L"]),Y(S["H"]),80*k,S["ohBox"]*k,PAPER,INK,1.2))
    for ex in (S["BAY_L"],S["BAY_R"]-S["T"]):          # END uprights, full box height
        o.append(r_(X(ex),Y(S["H"]),S["T"]*k,S["ohBox"]*k,WAL,"#5A3A28",.9))
    o.append(r_(X(S["BAY_L"]+S["T"]),Y(S["H"]),S["TB"]*k,S["T"]*k,WAL,"#5A3A28",.8))
    o.append(r_(X(S["BAY_L"]+S["T"]),Y(S["ohBot"]+S["T"]),S["TB"]*k,S["T"]*k,WAL,"#5A3A28",.8))
    p=S["T"]+S["bay"]
    for i in range(S["NIN"]):
        o.append(r_(X(S["BAY_L"]+p),Y(S["ohBot"]+S["T"]+S["UP"]),S["T"]*k,S["UP"]*k,WAL,"#5A3A28",.8))
        p+=S["T"]+S["bay"]
    o.insert(1, sofa_elev(X,Y,k))
    for fx,sg in ((S["BAY_L"],1),(S["BAY_R"],-1)):
        top=S["SC_MID"]+S["SC_BPH"]/2
        o.append(r_(X(min(fx,fx+sg*.75)),Y(top),.75*k,S["SC_BPH"]*k,"#B2913F","#7A6228",1))
        sx0=fx+sg*.75 if sg>0 else fx-S["SC_PROJ"]
        o.append(r_(X(sx0),Y(top-1),(S["SC_PROJ"]-.75)*k,S["SC_SHH"]*k,"#F4EFE3","#C9C2B0",1))
    # right dim ladder
    d1=X(S["W"])+18
    for a,b,lab,c in ((0,S["LEG"],fr(S["LEG"]),RED),(S["LEG"],S["BB"],fr(S["BAR"]),GOLD),
                      (S["BB"],S["BT"],fr(S["CARC"]),MUTED),(S["ohBot"],S["H"],fr(S["ohBox"]),MUTED)):
        o.append(dim(d1,Y(a),d1,Y(b),lab,vert=True,off=5,col=c))
    d2=d1+44
    o.append(dim(d2,Y(0),d2,Y(S["BT"]),fr(S["BT"]),vert=True,size=6.2,off=5))
    o.append(dim(d2,Y(S["BT"]),d2,Y(S["H"]),fr(S["TOWER"]),vert=True,size=6.2,off=5))
    d3=X(-18)
    o.append(dim(d3,Y(0),d3,Y(S["H"]),f'{fr(S["H"])} OVERALL',vert=True,size=6.6,off=-5))
    # shelf heights AFF, left
    for z in S["SH"]:
        o.append(line(X(-8),Y(z),X(0),Y(z),MUTED,.6,dash="3 2"))
        o.append(txt(X(-9),Y(z)+2,fr(z),5.8,"end",MUTED,mono=True))
    o.append(txt(X(-9),Y(S["SC_MID"])+2,f'\u2190 {fr(S["SC_MID"])} SCONCE',5.8,"end",GOLD,mono=True))
    ob=(S["SH"][-1]+S["BT"])/2
    o.append(txt(X(S["MOD"]/2),Y(ob),f'{fr(S["OPEN_BOT"])}',6.2,"middle",RED,mono=True))
    for i in range(4):
        mo=(S["SH"][i]+S["SH"][i+1])/2
        o.append(txt(X(S["MOD"]/2),Y(mo),fr(S["OPEN_MID"]),5.6,"middle",MUTED,mono=True))
    o.append(txt(X(S["MOD"]/2),Y((S["CAP"]+S["SH"][0])/2),fr(S["CAP"]-S["SH"][0]-S["T"]),5.6,"middle",MUTED,mono=True))
    o.append(dim(X(0),Y(0)+22,X(S["W"]),Y(0)+22,f'{fr(S["W"])}',size=6.6))
    o.append(dim(X(0),Y(0)+38,X(S["MOD"]),Y(0)+38,fr(S["MOD"]),size=6.0))
    o.append(dim(X(S["BAY_L"]),Y(0)+38,X(S["BAY_R"]),Y(0)+38,'80" CLEAR',size=6.0))
    o.append(dim(X(S["BAY_R"]),Y(0)+38,X(S["W"]),Y(0)+38,fr(S["MOD"]),size=6.0))
    o.append(r_(452,96,300,76,"#FFF9F0",GOLD,1.2))
    o.append(txt(464,114,"SHELF SPACING \u2014 AS BUILT, NOT BEING CHANGED",7.6,bold=True,fill=GOLD))
    o.append(txt(464,128,f'Five shelves. Six openings: top {fr(S["TOP_CLR"])}, five at {fr(S["MID_CLR"])}.',6.8))
    o.append(txt(464,140,f'Tower {fr(S["TOWER"])}. Those clears sum to {fr(88.1325,64)} \u2014 {fr(S["TOWER"]-88.1325,64)} floats.',6.8))
    o.append(txt(464,152,f'Drawn bottom-up from the base top, so the top opening reads',6.8,fill=RED))
    o.append(txt(464,164,f'{fr(S["TOP_ACT"])} here. CONFIRM one measured anchor \u2014 see A4.',6.8,fill=RED))
    return page("".join(o),1,4,"Front Elevation \u2014 Dimensioned",
      f'Overall {fr(S["W"])} \u00d7 {fr(S["H"])} \u00b7 base top {fr(S["BT"])} AFF \u00b7 towers untrimmed at {fr(S["TOWER"])}')

# ═════════ A2 · plan ═════════
def a2():
    k=3.15; ax,ay=104,182
    X=lambda v: ax+v*k; Y=lambda v: ay+v*k
    o=[]
    o.append(txt(40,108,"A \u00b7 PLAN AT THE BASE CABINET",9.2,bold=True))
    o.append(line(X(-6),Y(0),X(S["W"]+S["WALL_R"]+6),Y(0),INK,2))
    o.append(txt(X(-6),Y(0)-6,"WALL",6.0,"start",MUTED,mono=True))
    for bx in (0,S["BAY_R"]):
        o.append(r_(X(bx),Y(0),S["MOD"]*k,S["BASE_D"]*k,PAPER,INK,1.2))
        o.append(r_(X(bx),Y(0),S["MOD"]*k,S["T"]*k,"#DCD3C0",INK,.8))
        o.append(r_(X(bx),Y(0),S["T"]*k,S["BASE_D"]*k,"#DCD3C0",INK,.8))
        o.append(r_(X(bx+S["MOD"]-S["T"]),Y(0),S["T"]*k,S["BASE_D"]*k,"#DCD3C0",INK,.8))
        o.append(r_(X(bx),Y(S["BASE_D"]-S["T"]),S["MOD"]*k,S["T"]*k,WALL_,"#5A3A28",1))
        for lx,lz in ((bx+2.6,2.6),(bx+S["MOD"]-2.6,2.6),(bx+2.6,S["CARC_D"]-2.6),(bx+S["MOD"]-2.6,S["CARC_D"]-2.6)):
            o.append(f'<circle cx="{X(lx):.1f}" cy="{Y(lz):.1f}" r="{1.15*k:.1f}" fill="{WALD}" stroke="#3E2819" stroke-width="0.8"/>')
        RT=1.5
        o.append(r_(X(bx),Y(0),S["MOD"]*k,S["BASE_D"]*k,"none",GOLD,1.2,dash="4 3"))
        o.append(r_(X(bx),Y(0),S["MOD"]*k,RT*k,"none",GOLD,1.0))
        o.append(r_(X(bx),Y(S["BASE_D"]-RT),S["MOD"]*k,RT*k,"none",GOLD,1.0))
        o.append(r_(X(bx),Y(RT),RT*k,(S["BASE_D"]-2*RT)*k,"none",GOLD,1.0))
        o.append(r_(X(bx+S["MOD"]-RT),Y(RT),RT*k,(S["BASE_D"]-2*RT)*k,"none",GOLD,1.0))
        o.append(txt(X(bx+S["MOD"]/2),Y(S["BASE_D"]/2)+3,"PLINTH FRAME",5.6,"middle",GOLD,mono=True))
    o.append(r_(X(S["W"]),Y(-1),S["WALL_R"]*k,1*k,"none",RED,1,dash="3 2"))
    o.append(r_(X(S["W"]+S["WALL_R"]),Y(-2),4*k,26*k,"#EAE5DA",MUTED,1))
    o.append(txt(X(S["W"]+S["WALL_R"]+2),Y(14),"RETURN WALL",5.8,"middle",MUTED,mono=True,rot=90))
    # sofa in plan
    sx=S["BAY_L"]+.5; SW_,SD_=S["SOFA"][0],S["SOFA"][1]
    o.append(r_(X(sx),Y(.5),SW_*k,SD_*k,"#CFC0A8","#6E5D48",1))
    o.append(r_(X(sx),Y(.5),SW_*k,6*k,"#BCAA8E","#6E5D48",.9))
    o.append(r_(X(sx),Y(.5),5.5*k,SD_*k,"#BCAA8E","#6E5D48",.9))
    o.append(r_(X(sx+SW_-5.5),Y(.5),5.5*k,SD_*k,"#BCAA8E","#6E5D48",.9))
    for i in range(2):
        cx=sx+6+i*((SW_-12)/2)
        o.append(r_(X(cx),Y(7),((SW_-12)/2-1)*k,(SD_-8)*k,"#9E8B70","#6E5D48",.8))
    for lx,lz in ((sx+2.8,3),(sx+SW_-2.8,3),(sx+2.8,SD_-2.5),(sx+SW_-2.8,SD_-2.5)):
        o.append(f'<circle cx="{X(lx):.1f}" cy="{Y(lz):.1f}" r="{0.85*k:.1f}" fill="#5A3A28" stroke="#3E2819" stroke-width="0.7"/>')
    o.append(txt(X(sx+SW_/2),Y(SD_+5),"BRAXTON SLEEPER 79 \u00d7 36",6.4,"middle",MUTED,mono=True))
    o.append(r_(X(sx+1),Y(.5),(S["SOFA"][0]-2)*k,S["OPEN_D"]*k,"none",HAIR,1,dash="6 4"))
    o.append(txt(X(sx+S["SOFA"][0]/2),Y(S["OPEN_D"]-6),f'SLEEPER OPEN \u2014 {fr(S["OPEN_D"])} FLOOR DEPTH',6.2,"middle",RED,mono=True))
    o.append(dim(X(0),Y(-12),X(S["W"]),Y(-12),fr(S["W"]),size=6.4))
    o.append(dim(X(S["W"]),Y(-12),X(S["W"]+S["WALL_R"]),Y(-12),fr(S["WALL_R"]),size=6.0,col=RED))
    o.append(dim(X(-8),Y(0),X(-8),Y(S["BASE_D"]),fr(S["BASE_D"]),vert=True,size=6.0,off=-5))
    o.append(dim(X(-8),Y(0),X(-8),Y(S["TOWER_D"]),fr(S["TOWER_D"]),vert=True,size=6.0,off=-5))
    SUB2=[f'the tower is set back {fr(S["BASE_D"]-S["TOWER_D"])}.',
          '2\u2033 \u00d7 1 1/2\u2033 solid walnut. The unit sits on it.',
          'the frame corners.',
          'CONFIRM wall-to-wall before install.',
          'wall when open.']
    o.append(txt(452,388,"B \u00b7 NOTES",9.0,bold=True))
    for i,t in enumerate([
      f'Base carcass {fr(S["BASE_D"])} deep, tower {fr(S["TOWER_D"])} \u2014',
      'Plinth frame (gold) \u2014 front, back and two side rails,',
      'Four legs per cabinet, bolted to blocks let into',
      f'Return wall {fr(S["WALL_R"])} clear of the right end \u2014',
      f'Sleeper needs {fr(S["OPEN_D"])} of clear floor from the']):
        o.append(txt(452,406+i*26,"\u2022 "+t,7.0))
        o.append(txt(460,417+i*26,SUB2[i],6.8,fill=MUTED))
    return page("".join(o),2,4,"Plan","Cut at the base cabinet \u00b7 sleeper swing shown dashed")

# ═════════ A3 · sections ═════════
def a3():
    o=[]
    # A · section through a tower
    k=3.25; ax,ay=132,500
    X=lambda v: ax+v*k; Y=lambda v: ay-v*k
    o.append(txt(40,108,"A \u00b7 SECTION THROUGH A TOWER",9.2,bold=True))
    o.append(txt(40,121,"wall at left \u00b7 looking along the unit",7.0,fill=MUTED))
    o.append(line(X(-2),Y(0),X(S["BASE_D"]+4),Y(0),INK,1.5))
    o.append(line(X(0),Y(-2),X(0),Y(S["H"]+3),MUTED,1.4))
    for lz in (2.6,S["CARC_D"]-2.6): o.append(leg(X,Y,lz,S["LEG"]))
    RT=1.5
    # side rail beyond the cut plane, full depth
    o.append(r_(X(0),Y(S["BB"]),S["BASE_D"]*k,S["BAR"]*k,"#C6A183","#8A6A4E",.9))
    # front and back rails, cut through
    o.append(r_(X(S["BASE_D"]-RT),Y(S["BB"]),RT*k,S["BAR"]*k,WAL,"#3E2819",1.1))
    o.append(r_(X(0),Y(S["BB"]),RT*k,S["BAR"]*k,WAL,"#3E2819",1.1))
    o.append(txt(X(S["BASE_D"])+7,Y(S["BB"]+3.4),"PLINTH FRAME",5.8,"start",INK,mono=True,bold=True))
    o.append(txt(X(S["BASE_D"])+7,Y(S["BB"]+3.4)+9,"front and back rails cut,",5.4,"start",MUTED,mono=True))
    o.append(txt(X(S["BASE_D"])+7,Y(S["BB"]+3.4)+18,"side rail behind, full depth",5.4,"start",MUTED,mono=True))
    o.append(dim(X(S["BASE_D"])+4,Y(S["LEG"]),X(S["BASE_D"])+4,Y(S["BB"]),fr(S["BAR"]),vert=True,size=5.8,off=4))
    o.append(r_(X(0),Y(S["BT"]),S["BASE_D"]*k,S["CARC"]*k,PAPER,INK,1.1))
    o.append(r_(X(0),Y(S["H"]),S["TOWER_D"]*k,S["TOWER"]*k,PAPER,INK,1.1))
    o.append(r_(X(0),Y(S["H"]),S["BACK"]*k,S["TOWER"]*k,"#5A3A28","#3E2819",1))
    for z in S["SH"]+[S["H"]]:
        o.append(r_(X(S["BACK"]),Y(z),(S["TOWER_D"]-S["BACK"])*k,S["T"]*k,"#E8DCC8",INK,.9))
        o.append(r_(X(S["BACK"]),Y(z-S["T"]),S["STRIP_W"]*k,.28*k,"#C9A85C","#7A6228",.8))
        o.append(r_(X(S["BACK"]+S["COVE_SET"]),Y(z-S["T"]),S["COVE_T"]*k,S["COVE_D"]*k,WALD,"#3E2819",.8))
        o.append(r_(X(S["TOWER_D"]),Y(z+S["TRIM_T"]),S["TRIM_T"]*k,(S["T"]+S["TRIM_T"])*k,WALD,"#3E2819",.8))
    o.append(txt(X(S["TOWER_D"])+8,Y(S["SH"][2]),f'\u2190 face trim {fr(S["TRIM_T"])}\u00d7{fr(S["TRIM_F"])}',5.8,"start",WALD,mono=True))
    o.append(txt(X(S["TOWER_D"])+8,Y(S["SH"][2])+9,f'\u2190 cove fascia behind',5.8,"start",GOLD,mono=True))
    o.append(dim(X(-8),Y(0),X(-8),Y(S["H"]),fr(S["H"]),vert=True,size=6.2,off=-5))
    o.append(dim(X(0),Y(0)+18,X(S["BASE_D"]),Y(0)+18,fr(S["BASE_D"]),size=6.0))
    o.append(dim(X(0),Y(0)+34,X(S["TOWER_D"]),Y(0)+34,fr(S["TOWER_D"]),size=6.0))
    # B · dado detail
    dk=52; bx,by=486,220
    BX=lambda v: bx+v*dk; BY=lambda v: by+v*dk
    o.append(txt(452,108,"B \u00b7 DADO \u00b7 SHELF AND OVERHEAD UPRIGHT",9.2,bold=True))
    o.append(txt(452,121,f'{fr(S["DADO"])} deep \u00d7 {fr(S["T"])} wide \u00b7 same for both',7.0,fill=MUTED))
    o.append(r_(BX(0),BY(0),1.6*dk,S["T"]*dk,"#E8DCC8",INK,1.2))
    o.append(r_(BX(.55),BY(0),S["T"]*dk,S["DADO"]*dk,"#fff",INK,1.2))
    o.append(r_(BX(.55),BY(-1.5),S["T"]*dk,1.5*dk,"#DCD3C0",INK,1.2))
    o.append(dim(BX(.55),BY(0)+46,BX(.55+S["T"]),BY(0)+46,fr(S["T"]),size=6.2))
    o.append(dim(BX(1.85),BY(0),BX(1.85),BY(S["DADO"]),fr(S["DADO"]),vert=True,size=6.2,off=5,col=RED))
    o.append(dim(BX(2.5),BY(S["DADO"]),BX(2.5),BY(S["T"]),fr(S["T"]-S["DADO"])+" LEFT",vert=True,size=6.0,off=5))
    o.append(txt(452,300,f'{fr(S["DADO"])} is {100*S["DADO"]/S["T"]:.0f}% of the {fr(S["T"])} panel \u2014 a third is the working',7.0))
    o.append(txt(452,312,"range. Deeper gains nothing: the joint already outlasts the panel.",7.0))
    o.append(txt(452,324,"Tower shelf dados are ALREADY CUT at this depth. Match it.",7.0,fill=RED))
    o.append(txt(452,338,f'A dadoed part is cut CLEAR + 2 \u00d7 {fr(S["DADO"])}. Only the inner',6.9))
    o.append(txt(452,349,f'uprights are dadoed: {fr(S["UP"])} clear \u2192 {fr(S["UP_CUT"])} cut.',6.9))
    o.append(txt(452,360,f'Edging stays {fr(S["UP"])} \u2014 fitted after assembly.',6.9,fill=RED))
    # C · overhead section
    ok=13.5; ox,oy=560,510
    OX=lambda v: ox+v*ok; OY=lambda v: oy-v*ok
    CT=S["CLEAT_T"]; BK=S["BACK"]; TT=S["T"]; CHH=S["CLEAT_H"]
    o.append(txt(452,384,"C \u00b7 FRENCH CLEAT \u00b7 TOP OF THE OVERHEAD",9.2,bold=True))
    o.append(txt(452,396,"unit half lifted \u00b7 engaged position ghosted",6.8,fill=MUTED))
    TOP=5.2                                  # local: top of the overhead
    yTOPC = TOP-TT-0.25                      # cleat pair top, just under the top panel
    yBOTC = yTOPC-CHH                        # cleat pair bottom
    yMID  = yBOTC+1.9                        # where the bevel starts at the wall face
    o.append(line(OX(0),OY(-1.4),OX(0),OY(TOP+0.9),MUTED,1.8))
    o.append(txt(OX(0)-5,OY(TOP+1.0),"WALL",5.8,"end",MUTED,mono=True))
    # back panel \u2014 runs the full height, the cleat bears on it
    o.append(r_(OX(CT),OY(TOP),BK*ok,(TOP+1.2)*ok,"#5A3A28","#3E2819",1))
    o.append(txt(OX(CT+BK)+6,OY(yBOTC+0.7),"back panel \u2014 the unit half",5.6,"start",MUTED,mono=True))
    o.append(txt(OX(CT+BK)+6,OY(yBOTC+0.7)+9,"bears on it for its full height",5.6,"start",MUTED,mono=True))
    # top panel
    o.append(r_(OX(CT+BK),OY(TOP),(S["TOWER_D"]-CT-BK)*ok,TT*ok,WAL,"#3E2819",1))
    o.append(txt(OX(S["TOWER_D"]),OY(TOP-TT)+11,"overhead top panel",5.6,"end",MUTED,mono=True))
    # WALL HALF \u2014 bevel slopes down and outward from the wall
    o.append(f'<path d="M {OX(0):.1f} {OY(yMID-CT):.1f} L {OX(CT):.1f} {OY(yMID):.1f} '
             f'L {OX(CT):.1f} {OY(yBOTC):.1f} L {OX(0):.1f} {OY(yBOTC):.1f} Z" '
             f'fill="#B9B2A6" stroke="#5E6368" stroke-width="1.2"/>')
    o.append(txt(OX(0)-6,OY((yMID+yBOTC)/2)+2,"WALL HALF",6.0,"end",INK,mono=True,bold=True))
    o.append(txt(OX(0)-6,OY((yMID+yBOTC)/2)+11,"bevel RISES away",5.4,"end",MUTED,mono=True))
    o.append(txt(OX(0)-6,OY((yMID+yBOTC)/2)+20,"from the wall",5.4,"end",MUTED,mono=True))
    # engaged position of the unit half, ghosted
    o.append(f'<path d="M {OX(0):.1f} {OY(yMID-CT):.1f} L {OX(CT):.1f} {OY(yMID):.1f} '
             f'L {OX(CT):.1f} {OY(yTOPC):.1f} L {OX(0):.1f} {OY(yTOPC):.1f} Z" '
             f'fill="none" stroke="{MUTED}" stroke-width="0.9" stroke-dasharray="3 2"/>')
    o.append(txt(OX(CT)+6,OY((yMID+yTOPC)/2)+2,"engaged",5.4,"start",MUTED,mono=True))
    # UNIT HALF \u2014 lifted straight up
    L=2.5
    o.append(f'<path d="M {OX(0):.1f} {OY(yMID-CT+L):.1f} L {OX(CT):.1f} {OY(yMID+L):.1f} '
             f'L {OX(CT):.1f} {OY(yTOPC+L):.1f} L {OX(0):.1f} {OY(yTOPC+L):.1f} Z" '
             f'fill="#D8D4CC" stroke="#5E6368" stroke-width="1.2"/>')
    o.append(txt(OX(CT)+6,OY(yTOPC+L)-3,"UNIT HALF",6.0,"start",INK,mono=True,bold=True))
    o.append(txt(OX(CT)+6,OY(yTOPC+L)+6,"matching bevel \u2014 hooks in",5.4,"start",MUTED,mono=True))
    o.append(txt(OX(CT)+6,OY(yTOPC+L)+15,"screwed to the back panel",5.4,"start",MUTED,mono=True))
    # motion
    o.append(line(OX(CT/2),OY(yMID-CT/2+L)-4,OX(CT/2),OY(yMID-CT/2)-8,RED,1.4,dash="4 3"))
    o.append(f'<path d="M {OX(CT/2):.1f} {OY(yMID-CT/2)-2:.1f} L {OX(CT/2)-4.5:.1f} {OY(yMID-CT/2)-10:.1f} '
             f'L {OX(CT/2)+4.5:.1f} {OY(yMID-CT/2)-10:.1f} Z" fill="{RED}"/>')
    o.append(txt(OX(0)-6,OY(yTOPC+L/2),"drops",5.6,"end",RED,mono=True))
    o.append(txt(OX(0)-6,OY(yTOPC+L/2)+9,"straight down",5.6,"end",RED,mono=True))
    # dims
    o.append(dim(OX(0),OY(yBOTC-1.2),OX(CT),OY(yBOTC-1.2),fr(CT),size=6.0,col=RED))
    o.append(txt(OX(CT/2),OY(yBOTC-1.2)+21,"ZONE",5.6,"middle",RED,mono=True))
    o.append(dim(OX(CT),OY(yBOTC-2.0),OX(CT+BK),OY(yBOTC-2.0),fr(BK),size=5.6))
    o.append(dim(OX(CT+BK),OY(yBOTC-1.2),OX(S["TOWER_D"]),OY(yBOTC-1.2),f'{fr(S["OH_DEEP"])} USABLE',size=6.0,col=GOLD))
    o.append(dim(OX(S["TOWER_D"])+16,OY(yBOTC),OX(S["TOWER_D"])+16,OY(yTOPC),fr(CHH),vert=True,size=5.8,off=5))
    o.append(txt(452,PH-58,"The bevel rises away from the wall, so the unit\u2019s weight pulls it IN, not off.",6.8,fill=RED))
    o.append(txt(452,PH-47,f'Both halves in one {fr(CT)} zone \u00b7 + back {fr(BK)} leaves {fr(S["OH_DEEP"])} usable.',6.8,fill=MUTED))
    return page("".join(o),3,4,"Sections & Details","Tower, dado, overhead \u00b7 cove fascia and face trim shown at every shelf")

# ═════════ A4 · overhead plan + schedule ═════════
def a4():
    o=[]
    k=4.6; ax,ay=74,132
    X=lambda v: ax+v*k; Y=lambda v: ay+v*k
    o.append(txt(40,108,"A \u00b7 OVERHEAD \u00b7 FOUR BAYS",9.2,bold=True))
    o.append(r_(X(0),Y(0),80*k,S["ohBox"]*k,PAPER,INK,1.3))
    for ex in (0.0,80.0-S["T"]):
        o.append(r_(X(ex),Y(0),S["T"]*k,S["ohBox"]*k,WALD,"#3E2819",1.2))
    o.append(r_(X(S["T"]),Y(0),S["TB"]*k,S["T"]*k,WAL,"#3E2819",1))
    o.append(r_(X(S["T"]),Y(S["ohBox"]-S["T"]),S["TB"]*k,S["T"]*k,WAL,"#3E2819",1))
    p=S["T"]
    for i in range(S["BAYS"]):
        o.append(line(X(p+.5),Y(S["T"]+.35),X(p+S["bay"]-.5),Y(S["T"]+.35),GOLD,2.2))
        o.append(txt(X(p+S["bay"]/2),Y(S["T"]+S["UP"]/2)+3,f'{i+1}',8.0,"middle",MUTED,mono=True))
        p+=S["bay"]
        if i<S["NIN"]:
            o.append(r_(X(p),Y(S["T"]),S["T"]*k,S["UP"]*k,WALL_,"#3E2819",1))
            p+=S["T"]
    o.append(txt(X(80)+8,Y(S["ohBox"]/2),"END UPRIGHTS",5.8,"start",WALD,mono=True,bold=True))
    o.append(txt(X(80)+8,Y(S["ohBox"]/2)+9,"full box height \u00b7 screwed",5.6,"start",MUTED,mono=True))
    o.append(txt(X(80)+8,Y(S["ohBox"]/2)+18,"from the outside face",5.6,"start",MUTED,mono=True))
    p=S["T"]
    for i in range(S["BAYS"]):
        o.append(dim(X(p),Y(S["ohBox"])+6,X(p+S["bay"]),Y(S["ohBox"])+6,fr(S["bay"]),size=5.8,col=GOLD))
        p+=S["bay"]+(S["T"] if i<S["NIN"] else 0)
    o.append(dim(X(S["T"]),Y(S["ohBox"])+22,X(80-S["T"]),Y(S["ohBox"])+22,f'{fr(S["TB"])} TOP / BOTTOM',size=6.2))
    o.append(dim(X(0),Y(S["ohBox"])+36,X(80),Y(S["ohBox"])+36,'80" BETWEEN TOWERS',size=6.2))
    o.append(dim(X(80)+70,Y(S["T"]),X(80)+70,Y(S["T"]+S["UP"]),fr(S["UP"]),vert=True,size=6.2,off=5))
    
    o.append(txt(40,252,"B \u00b7 DADO INDEX \u00b7 3 inner uprights \u00b7 from the END of the top/bottom",8.8,bold=True))
    p=S["bay"]
    for i in range(S["NIN"]):
        cx=40+i*126
        o.append(r_(cx,260,112,26,PAPER,HAIR,1))
        o.append(txt(cx+8,271,f'INNER UPRIGHT {i+1}',6.0,fill=MUTED,mono=True))
        o.append(txt(cx+8,283,fr(p),8.2,bold=True))
        p+=S["T"]+S["bay"]
    o.append(txt(40,300,"C \u00b7 SCHEDULE \u00b7 PARTS STILL TO MAKE",8.8,bold=True))
    st=S["MOD"]-2*S["T"]-1.0; so=S["bay"]-1.0
    rows=[("M","Plinth rail, front/back","solid walnut",4,'23 \u00d7 2 \u00d7 1 1/2'),
          ("AB","Plinth rail, side","solid walnut",4,'14 31/32 \u00d7 2 \u00d7 1 1/2'),
          ("P","Leg mounting block","solid walnut",8,'4 \u00d7 2 \u00d7 1 1/2'),
          ("Q","Tower back panel","0.703 ply",2,f'{fr(S["TOWER"])} \u00d7 22 1/16'),
          ("R","Overhead top / bottom","0.72 ply",2,f'{fr(S["TB"])} \u00d7 {fr(S["OH_DEEP"])}'),
          ("S","Overhead upright, inner","0.72 ply",S["NIN"],f'{fr(S["UP_CUT"])} \u00d7 {fr(S["OH_DEEP"])}'),
          ("AC","Overhead upright, END","0.72 ply",2,f'{fr(S["ohBox"])} \u00d7 {fr(S["OH_DEEP"])}'),
          ("AA","French cleat, 45\u00b0","0.72 ply",2,f'80 \u00d7 {fr(S["CLEAT_H"])}'),
          ("T","Overhead back, per bay","0.703 ply",S["BAYS"],f'{fr(S["bay"])} \u00d7 {fr(S["UP"])}'),
          ("U","Face trim, shelf band","solid walnut",12,f'20 \u00d7 {fr(S["TRIM_F"])}'),
          ("V","Face trim, side stile","solid walnut",4,f'{fr(S["TOWER"])} \u00d7 {fr(S["TRIM_F"])}'),
          ("W","Edging, overhead top/bottom","solid walnut",2,f'{fr(S["TB"])} \u00d7 {fr(S["TRIM_F"])}'),
          ("X","Edging, inner upright","solid walnut",S["NIN"],f'{fr(S["UP"])} \u00d7 {fr(S["TRIM_F"])}'),
          ("AD","Edging, END upright","solid walnut",2,f'{fr(S["ohBox"])} \u00d7 {fr(S["TRIM_F"])}'),
          ("Y","Cove fascia, tower","solid walnut",12,f'{fr(st)} \u00d7 {fr(S["COVE_D"])}'),
          ("Z","Cove fascia, overhead","solid walnut",S["BAYS"],f'{fr(so)} \u00d7 {fr(S["COVE_D"])}')]
    o.append(txt(40,314,"TAG",6.2,fill=MUTED,mono=True)); o.append(txt(74,314,"PART",6.2,fill=MUTED,mono=True))
    o.append(txt(300,314,"MATERIAL",6.2,fill=MUTED,mono=True))
    o.append(txt(420,314,"QTY",6.2,"end",MUTED,mono=True)); o.append(txt(600,314,"SIZE",6.2,"end",MUTED,mono=True))
    o.append(line(40,318,600,318,HAIR))
    tot=0
    for i,(tg,n_,m_,q,sz) in enumerate(rows):
        yy=330+i*13.2; tot+=q
        o.append(txt(40,yy,tg,7.2,bold=True,mono=True)); o.append(txt(74,yy,n_,7.0))
        o.append(txt(300,yy,m_,6.6,fill=MUTED)); o.append(txt(420,yy,str(q),7.0,"end",mono=True))
        o.append(txt(600,yy,sz,6.8,"end",mono=True))
        o.append(line(40,yy+4,600,yy+4,HAIR,.4))
    o.append(txt(40,330+len(rows)*13.2+10,f'{len(rows)} designs \u00b7 {tot} pieces \u00b7 S is cut {fr(S["UP_CUT"])} \u2014 {fr(S["UP"])} clear + a {fr(S["DADO"])} dado each end',6.8,fill=GOLD))
    o.append(r_(628,300,124,240,"#FFF9F0",GOLD,1.2))
    o.append(txt(638,318,"OPEN",7.8,bold=True,fill=GOLD))
    for i,t in enumerate(["MEASURE THIS:","tower bottom edge to","the first shelf","underside. Your clears",f'sum {fr(88.1325,64)} against an',f'{fr(S["TOWER"])} tower \u2014 1/8\u2033',"floats somewhere.","",
                          "Ceiling 136\u2033 confirmed","\u2014 21 1/2\u2033 clear above.","",
                          "Wall-to-wall width \u2014","confirm 126 + 6 fits.","",
                          "COM legs \u2014 confirm","height so the unit and","sofa bottoms align."]):
        o.append(txt(638,334+i*11.8,t,6.5))
    return page("".join(o),4,4,"Overhead Plan & Schedule",f'Four bays {fr(S["bay"])} \u00d7 {fr(S["UP"])} \u00b7 12 part designs still to make')

sheets=[a1(),a2(),a3(),a4()]
for i,sv in enumerate(sheets,1): assert f'REV {S["rev"]}' in sv
w=PdfWriter()
for sv in sheets:
    b=io.BytesIO(); cairosvg.svg2pdf(bytestring=sv.encode(),write_to=b,dpi=72); b.seek(0)
    w.add_page(PdfReader(b).pages[0])
w.add_metadata({"/Title":"R6 REV G Architectural Set"})
with open("/mnt/user-data/outputs/R6-architectural-set-rev-G.pdf","wb") as f: w.write(f)
for i,sv in enumerate(sheets,1):
    cairosvg.svg2png(bytestring=sv.encode(),write_to=f"/home/claude/A{i}.png",scale=1.7)
print(f'A1-A4  overall {fr(S["H"])}  tower {fr(S["TOWER"])}  oh {fr(S["ohBot"])}-{fr(S["H"])}  bay {fr(S["bay"])}')
