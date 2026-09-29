"""R6 REV G - complete installed system, one sheet. Everything in place."""
import io, math, cairosvg
from pypdf import PdfWriter, PdfReader
PW,PH=792,612
INK,HAIR,MUTED,GOLD,RED,PAPER="#4E5257","#DEDAD3","#96907F","#B8912F","#B4553C","#FBFAF7"
WAL,WALD,WALL_="#8E6248","#6B4632","#A8825F"
LIT="#E8C877"
S=dict(W=126.0,H=114.5,T=.72,BAY_L=23.0,BAY_R=103.0,MOD=23.0,TOWER=88.25,
 BASE_D=17.97,TOWER_D=8.0,BT=26.25,BB=6.0,LEG=4.0,BAR=2.0,DOOR=18.25,
 MID_CLR=12.25,NSH=5,UP=12.25,NUP=5,BAYS=4,
 OUT_X=36.0,OUT_H=15.0,EXIT_H=23.75,PC=(11.5,114.5),
 SC_MID=58.3125,SC_BPH=12.6,SC_PROJ=5.5,SC_SHH=9.0,
 SOFA=(79.0,36.0,37.0),ARM=28.25,SEAT=20.0,SOFA_LEG=4.0)
S["PITCH"]=S["MID_CLR"]+S["T"]
S["SH"]=[S["BT"]+S["MID_CLR"]+i*S["PITCH"] for i in range(S["NSH"])][::-1]
S["bay"]=(80.0-S["NUP"]*S["T"])/S["BAYS"]
S["ohBox"]=S["UP"]+2*S["T"]; S["ohBot"]=S["H"]-S["ohBox"]
def fr(x,d=16):
    from math import gcd
    n=round(x*d); w=n//d; r=n%d
    if r==0: return f'{w}"'
    g=gcd(r,d); return (f'{w} ' if w else '')+f'{r//g}/{d//g}"'
def txt(x,y,s,size=8,anchor="start",fill=None,mono=False,bold=False):
    f="DejaVu Sans Mono" if mono else "DejaVu Sans"
    b=' font-weight="bold"' if bold else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{f}" font-size="{size}" '
            f'fill="{fill or INK}" text-anchor="{anchor}"{b}>{s}</text>')
def r_(x,y,w,h,fill,st=INK,sw=1,dash=None):
    d=f' stroke-dasharray="{dash}"' if dash else ''
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" '
            f'fill="{fill}" stroke="{st}" stroke-width="{sw}"{d}/>')
def line(x1,y1,x2,y2,st=INK,sw=1,dash=None):
    d=f' stroke-dasharray="{dash}"' if dash else ''
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{st}" stroke-width="{sw}"{d}/>'
def dot(x,y,r,f_,st=None):
    e=f' stroke="{st}" stroke-width="0.8"' if st else ''
    return f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{f_}"{e}/>'
def tag(x,y,n,c=INK):
    return dot(x,y,7,c)+txt(x,y+2.6,str(n),7.4,"middle","#fff",bold=True)

o=[f'<rect width="{PW}" height="{PH}" fill="#ffffff"/>',
   f'<rect x="28" y="26" width="{PW-56}" height="{PH-52}" fill="none" stroke="{HAIR}"/>',
   txt(40,52,"Everything Installed",13.5,bold=True),
   txt(40,68,"complete system in place \u00b7 red = mains cord \u00b7 gold = light",8.0,fill=MUTED),
   txt(PW-40,52,"REV G",13.5,"end"),txt(PW-40,68,"WOODCRAFT BY EMPIRE WORKROOM",7.2,"end",MUTED),
   line(28,80,PW-28,80,HAIR)]

k=3.30; ax,ay=236,528
X=lambda v: ax+v*k; Y=lambda v: ay-v*k

# floor + wall
o.append(line(X(-8),Y(0),X(S["W"]+8),Y(0),INK,1.6))
# ── the electrical, drawn in place ──
ox,oy=X(S["OUT_X"]),Y(S["OUT_H"])
o.append(r_(ox-6,oy-9,12,18,"#F7F5F1",INK,1.2))
for dy in (-4,4): o.append(dot(ox,oy+dy,1.9,INK))
for i,cx in enumerate(S["PC"]):
    ex,ey=X(cx),Y(S["EXIT_H"])
    # power centre in the top
    o.append(r_(X(cx-3.2),Y(S["BT"]+.9),6.4*k,.9*k,"#1F1F1F","#0D0D0D",1))
    # in-cabinet strip + supply
    o.append(r_(X(cx-4.5),Y(S["BB"]+4.4),4*k,1.6*k,"#F2EFE9","#B9B2A6",.9))
    o.append(r_(X(cx+0.4),Y(S["BB"]+4.6),3*k,2.0*k,"#C9A85C","#7A6228",.9))
    # cord: out the back, down, along
    o.append(dot(ex,ey,2.6,RED))
    o.append(line(ex,ey,ex,oy,RED,1.5))
    o.append(line(ex,oy,ox+(5 if cx>S["OUT_X"] else -5),oy,RED,1.5))
    # chase up to the shelves
    o.append(line(X(cx-4.5),Y(S["BB"]+6),X(cx-4.5),Y(S["SH"][-1]),GOLD,1.4,dash="3 2"))

o.append('<g opacity="0.62">')
# ── sofa, behind ──
x0=S["BAY_L"]+.5; W_,D_,H_=S["SOFA"]; L=S["SOFA_LEG"]; A=S["ARM"]; ST=S["SEAT"]
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
o.append(r_(X(x0),Y(L+2.2),W_*k,2.2*k,DK,ED,1))
o.append("</g>")
# ── the unit ──
def leg(lx,h,rT=1.15,rB=.52,rake=8,fill=WALD):
    run=h*math.tan(math.radians(rake))
    return (f'<path d="M {X(lx-rT):.1f} {Y(h):.1f} L {X(lx+rT):.1f} {Y(h):.1f} '
            f'L {X(lx+rB+run):.1f} {Y(0):.1f} L {X(lx-rB-run):.1f} {Y(0):.1f} Z" '
            f'fill="{fill}" stroke="#3E2819" stroke-width="0.8"/>')
for bx in (0,S["BAY_R"]):
    for lx in (bx+2.6,bx+S["MOD"]-2.6): o.append(leg(lx,S["LEG"]))
    o.append(r_(X(bx),Y(S["BB"]),S["MOD"]*k,S["BAR"]*k,WAL,"#3E2819",1))
    o.append(r_(X(bx),Y(S["BB"]+S["DOOR"]),S["MOD"]*k,S["DOOR"]*k,WALL_,"#5A3A28",1))
    o.append(r_(X(bx),Y(S["BT"]),S["MOD"]*k,2*k,WALD,"#3E2819",1))
    o.append(r_(X(bx),Y(S["H"]),S["MOD"]*k,S["TOWER"]*k,"#FBFAF7",INK,1.2))
    for z in S["SH"]+[S["H"]]:
        o.append(r_(X(bx+S["T"]),Y(z),(S["MOD"]-2*S["T"])*k,S["T"]*k,WAL,"#5A3A28",.8))
        o.append(line(X(bx+S["T"]+.4),Y(z-S["T"]-.2),X(bx+S["MOD"]-S["T"]-.4),Y(z-S["T"]-.2),LIT,2.2))
o.append(r_(X(S["BAY_L"]),Y(S["H"]),80*k,S["ohBox"]*k,"#FBFAF7",INK,1.2))
o.append(r_(X(S["BAY_L"]),Y(S["H"]),80*k,S["T"]*k,WAL,"#5A3A28",.8))
o.append(r_(X(S["BAY_L"]),Y(S["ohBot"]+S["T"]),80*k,S["T"]*k,WAL,"#5A3A28",.8))
p=0.0
for i in range(S["NUP"]):
    o.append(r_(X(S["BAY_L"]+p),Y(S["ohBot"]+S["T"]+S["UP"]),S["T"]*k,S["UP"]*k,WAL,"#5A3A28",.8))
    if i<S["BAYS"]:
        o.append(line(X(S["BAY_L"]+p+S["T"]+.4),Y(S["H"]-S["T"]-.5),
                      X(S["BAY_L"]+p+S["T"]+S["bay"]-.4),Y(S["H"]-S["T"]-.5),LIT,2.2))
    p+=S["T"]+S["bay"]
# sconces
for fx,sg in ((S["BAY_L"],1),(S["BAY_R"],-1)):
    top=S["SC_MID"]+S["SC_BPH"]/2
    o.append(r_(X(min(fx,fx+sg*.75)),Y(top),.75*k,S["SC_BPH"]*k,"#B2913F","#7A6228",1))
    sxx=fx+sg*.75 if sg>0 else fx-S["SC_PROJ"]
    o.append(r_(X(sxx),Y(top-1),(S["SC_PROJ"]-.75)*k,S["SC_SHH"]*k,"#F4EFE3","#C9C2B0",1))

# ── numbered tags ──
TAGS=[(1,X(S["OUT_X"]),oy+22,"Existing outlet, 36\u2033 from the left wall \u00b7 two receptacles"),
      (2,X(S["PC"][0]),Y(S["BT"]+4.4),"Legrand power centre, flush in the cabinet top"),
      (3,X(S["PC"][0]-6.6),Y(S["BB"]+5.2),"Mountable strip, screwed inside the cabinet"),
      (4,X(S["PC"][0]+4.4),Y(S["BB"]+8.4),"Hue supply + controller"),
      (5,X(S["BAY_L"]+3.4),Y(S["SC_MID"]),"Sconce \u00b7 on the power-centre button"),
      (6,X(11.5),Y(S["SH"][1]-S["T"]-.2),"Concealed cove, 16 runs"),
      (7,X(S["PC"][1]),Y(S["EXIT_H"]),"Cord out the back at 23 3/4\u2033, down and along")]
for n,tx,ty,_ in TAGS: o.append(tag(tx,ty,n,RED if n in (1,2,7) else (GOLD if n in (5,6) else INK)))

# ── key ──
o.append(txt(40,104,"KEY",9.2,bold=True))
for i,(n,_,_,d) in enumerate(TAGS):
    yy=124+i*17
    c = RED if n in (1,2,7) else (GOLD if n in (5,6) else INK)
    o.append(tag(52,yy-3,n,c))
    o.append(txt(66,yy,d,6.9))
o.append(line(40,252,190,252,HAIR))
o.append(txt(40,268,"Red \u2014 120 V mains",6.9,fill=RED))
o.append(txt(40,281,"Gold \u2014 low voltage and light",6.9,fill=GOLD))
o.append(txt(40,306,"Each side is independent:",7.2,bold=True))
for i,t in enumerate(["one receptacle, one power centre,","one strip, one supply.",
                      "","Nothing sits on top of the unit.","Every cord is behind the sofa.",
                      "","Total draw 0.83 A of a 15 A circuit."]):
    o.append(txt(40,322+i*11.4,t,6.9,fill=MUTED))
o.append(line(28,PH-46,PW-28,PH-46,HAIR))
o.append(txt(40,PH-32,"R6 Walnut Sofa Surround \u00b7 Woodcraft \u2014 Philipp &amp; Naomi",6.8,fill=MUTED))
o.append(txt(PW-40,PH-32,"INSTALLED SYSTEM \u00b7 2026-08-18",6.8,"end",MUTED))

svg=(f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW}" height="{PH}" viewBox="0 0 {PW} {PH}">'
     +"".join(o)+'</svg>')
b=io.BytesIO(); cairosvg.svg2pdf(bytestring=svg.encode(),write_to=b,dpi=72); b.seek(0)
w=PdfWriter(); w.add_page(PdfReader(b).pages[0])
with open("/mnt/user-data/outputs/R6-installed-system.pdf","wb") as f: w.write(f)
cairosvg.svg2png(bytestring=svg.encode(),write_to="/home/claude/inst.png",scale=1.8)
print("ok")
