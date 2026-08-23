"""R6 - what plugs into what. One cabinet, enlarged."""
import io, cairosvg
from pypdf import PdfWriter, PdfReader
PW,PH=792,612
INK,HAIR,MUTED,GOLD,RED,PAPER="#4E5257","#DEDAD3","#96907F","#B8912F","#B4553C","#FBFAF7"
def txt(x,y,s,size=8,anchor="start",fill=None,mono=False,bold=False):
    f="DejaVu Sans Mono" if mono else "DejaVu Sans"
    b=' font-weight="bold"' if bold else ''
    return (f'<text x="{x:.1f}" y="{y:.1f}" font-family="{f}" font-size="{size}" '
            f'fill="{fill or INK}" text-anchor="{anchor}"{b}>{s}</text>')
def r_(x,y,w,h,fill,st=INK,sw=1,dash=None,rx=0):
    d=f' stroke-dasharray="{dash}"' if dash else ''
    return (f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="{rx}" '
            f'fill="{fill}" stroke="{st}" stroke-width="{sw}"{d}/>')
def line(x1,y1,x2,y2,st=INK,sw=1,dash=None):
    d=f' stroke-dasharray="{dash}"' if dash else ''
    return f'<line x1="{x1:.1f}" y1="{y1:.1f}" x2="{x2:.1f}" y2="{y2:.1f}" stroke="{st}" stroke-width="{sw}"{d}/>'
def arrow(x1,y1,x2,y2,c=RED,sw=2.0):
    import math
    a=math.atan2(y2-y1,x2-x1)
    return (line(x1,y1,x2,y2,c,sw)+
      f'<path d="M {x2:.1f} {y2:.1f} L {x2-9*math.cos(a-.38):.1f} {y2-9*math.sin(a-.38):.1f} '
      f'L {x2-9*math.cos(a+.38):.1f} {y2-9*math.sin(a+.38):.1f} Z" fill="{c}"/>')
def plug(x,y,c=RED):
    return (r_(x-5,y-6,10,12,"#F7F5F1",c,1.2,rx=2)+
            f'<rect x="{x-2.6}" y="{y-3}" width="1.6" height="6" fill="{c}"/>'
            f'<rect x="{x+1}" y="{y-3}" width="1.6" height="6" fill="{c}"/>')

o=[f'<rect width="{PW}" height="{PH}" fill="#ffffff"/>',
   f'<rect x="28" y="26" width="{PW-56}" height="{PH-52}" fill="none" stroke="{HAIR}"/>',
   txt(40,52,"What Plugs Into What",13.5,bold=True),
   txt(40,68,"one base cabinet, enlarged \u00b7 the mountable strip is the hub \u00b7 ONE 10 ft cord leaves",8.0,fill=MUTED),
   txt(PW-40,52,"REV G",13.5,"end"),txt(PW-40,68,"WOODCRAFT BY EMPIRE WORKROOM",7.2,"end",MUTED),
   line(28,80,PW-28,80,HAIR)]

# ── cabinet box ──
CX,CY,CW,CH=248,150,344,290
o.append(r_(CX,CY,CW,CH,PAPER,INK,1.6))
o.append(r_(CX,CY,CW,22,"#8E6248","#3E2819",1))
o.append(txt(CX+CW/2,CY+15,"CABINET TOP",7.0,"middle","#F6EFE7",mono=True))
o.append(txt(CX-8,CY+CH+16,"INSIDE THE BASE CABINET",7.4,"start",MUTED,mono=True))
# wall at left
o.append(line(CX-96,CY-20,CX-96,CY+CH+30,MUTED,2))
o.append(txt(CX-102,CY+CH+30,"WALL",6.6,"end",MUTED,mono=True))

# ── outlet on the wall ──
oy=CY+226
o.append(r_(CX-111,oy-19,30,38,"#F7F5F1",INK,1.4,rx=3))
for dy in (-9,9):
    o.append(f'<circle cx="{CX-96}" cy="{oy+dy}" r="3.4" fill="{INK}"/>')
o.append(txt(CX-96,oy+54,"EXISTING OUTLET",6.6,"middle",INK,mono=True,bold=True))
o.append(txt(CX-96,oy+65,"two receptacles",6.0,"middle",MUTED,mono=True))

# ── 1 · Legrand in the top ──
o.append(r_(CX+140,CY+4,150,15,"#1F1F1F","#0D0D0D",1.2,rx=2))
o.append(txt(CX+215,CY-8,"1  LEGRAND POWER CENTRE",7.4,"middle",bold=True))
o.append(txt(CX+215,CY+40,"recessed in the top \u00b7 outlets + USB face up",6.4,"middle",MUTED,mono=True))
# its own cord, SHORT, staying inside
o.append(line(CX+176,CY+19,CX+176,CY+190,RED,2))
o.append(plug(CX+176,CY+198))
o.append(txt(CX+186,CY+164,"6 ft cord",6.4,"start",RED,mono=True))
o.append(txt(CX+186,CY+175,"stays inside",6.4,"start",RED,mono=True))
# switched pigtail
o.append(line(CX+272,CY+19,CX+310,CY+19,"#B2913F",1.8))
o.append(line(CX+310,CY+19,CX+310,CY-18,"#B2913F",1.8))
o.append(txt(CX+316,CY-22,"switched \u2192 SCONCE",6.4,"start","#B2913F",mono=True))

# ── 2 · the mountable strip, the hub ──
SX,SY=CX+54,CY+206
o.append(r_(SX,SY,232,34,"#F2EFE9","#B9B2A6",1.6,rx=4))
for i in range(3):
    cx=SX+50+i*60
    o.append(r_(cx-16,SY+8,32,18,"#E4E0D8","#B9B2A6",.9,rx=2))
    o.append(f'<rect x="{cx-5}" y="{SY+12}" width="3" height="9" fill="#8A8F96"/>')
    o.append(f'<rect x="{cx+2}" y="{SY+12}" width="3" height="9" fill="#8A8F96"/>')
o.append(txt(SX+116,SY-10,"2  MOUNTABLE STRIP \u2014 THE HUB",7.4,"middle",bold=True))
o.append(txt(SX+116,SY+50,"screwed to the cabinet floor \u00b7 10 ft cord \u00b7 always on",6.4,"middle",MUTED,mono=True))
# the ONE cord out
o.append(line(SX,SY+17,CX-82,SY+17,RED,2.4))
o.append(line(CX-82,SY+17,CX-82,oy,RED,2.4))
o.append(plug(CX-82,oy,RED))
o.append(txt((SX+CX-82)/2,SY+6,"THE ONE CORD OUT",6.8,"middle",RED,mono=True,bold=True))
o.append(txt(CX-76,oy-30,"grommet",6.0,"start",RED,mono=True))

# ── 3 · Hue supply ──
HX,HY=CX+34,CY+112
o.append(r_(HX,HY,86,44,"#C9A85C","#7A6228",1.4,rx=3))
o.append(txt(HX+43,HY+27,"HUE SUPPLY",6.8,"middle",INK,mono=True,bold=True))
o.append(txt(HX+43,HY-8,"3  + CONTROLLER",7.4,"middle",bold=True))
o.append(line(HX+30,HY+44,HX+30,SY))
o.append(plug(HX+30,SY-6,RED))
o.append(line(HX+30,HY+44,HX+30,SY-12,RED,2))
# low voltage up the chase
o.append(line(HX+62,HY,HX+62,CY+30,GOLD,2,dash="4 3"))
o.append(txt(HX+68,CY+44,"low voltage",6.4,"start",GOLD,mono=True))
o.append(txt(HX+68,CY+54,"up the chase",6.4,"start",GOLD,mono=True))

# ── arrows showing direction of feed ──


# ── the sentence ──
o.append(r_(40,CY+CH+56,712,60,"#FFF9F0",GOLD,1.4))
o.append(txt(56,CY+CH+76,"IN ONE SENTENCE",8.2,bold=True,fill=GOLD))
o.append(txt(56,CY+CH+93,"The strip is screwed inside the cabinet and its cord is the only thing that leaves. The power centre and the",7.4))
o.append(txt(56,CY+CH+106,"lighting supply both plug into that strip, inside the cabinet. The sconce plugs into the power centre's own pigtail.",7.4))

# ── left column: the order ──
o.append(txt(40,110,"ORDER OF WORK",8.6,bold=True))
for i,t in enumerate(["1. Screw the strip to the","   cabinet floor.","",
    "2. Run its cord out the","   grommet, down the wall,","   to the outlet.","",
    "3. Plug the power centre","   into the strip.","",
    "4. Plug the lighting supply","   into the strip.","",
    "5. Plug the sconce into the","   power centre's pigtail."]):
    o.append(txt(40,128+i*11.6,t,6.9,fill=(INK if t[:2].strip().rstrip('.').isdigit() else MUTED)))
o.append(txt(40,330,"WHY THIS WAY",8.6,bold=True,fill=RED))
for i,t in enumerate(["One cord per cabinet, not","two. Everything else","connects inside, where it","cannot be seen or kicked.","",
    "The power centre only needs","a 6 ft cord \u2014 it reaches the","strip a foot away.","",
    "Left run 3.6 ft, right 8.1 ft.","The 10 ft cord covers both."]):
    o.append(txt(40,348+i*11.6,t,6.9,fill=MUTED))
o.append(line(28,PH-46,PW-28,PH-46,HAIR))
o.append(txt(40,PH-32,"R6 Walnut Sofa Surround \u00b7 Woodcraft \u2014 Philipp &amp; Naomi",6.8,fill=MUTED))
o.append(txt(PW-40,PH-32,"HOOK-UP \u00b7 2026-08-18",6.8,"end",MUTED))

svg=(f'<svg xmlns="http://www.w3.org/2000/svg" width="{PW}" height="{PH}" viewBox="0 0 {PW} {PH}">'
     +"".join(o)+'</svg>')
b=io.BytesIO(); cairosvg.svg2pdf(bytestring=svg.encode(),write_to=b,dpi=72); b.seek(0)
w=PdfWriter(); w.add_page(PdfReader(b).pages[0])
with open("/mnt/user-data/outputs/R6-hookup-detail.pdf","wb") as f: w.write(f)
cairosvg.svg2png(bytestring=svg.encode(),write_to="/home/claude/hk.png",scale=1.8)
print("ok")
