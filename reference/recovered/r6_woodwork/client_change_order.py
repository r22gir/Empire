"""R6 REV G - material list + client proposal. One RATES/SPEC block drives both."""
import io, math, cairosvg
from pypdf import PdfWriter, PdfReader
import re as _re
S=dict(rev="G",date="2026-08-18",job="R6 Walnut Sofa Surround",
 client="Woodcraft \u2014 Philipp &amp; Naomi",brand="WOODCRAFT BY EMPIRE WORKROOM",
 MARKUP=0.30, LABOR_HRS=7.5, LABOR_RATE=95.0)
RATES=dict(wal44=16.00, wal84=20.00, panel=82.00, birch=68.00,
           glue=18.00, spline=12.00, pin=9.00, abras=22.00, finish=34.00)
MAT=[
 ("Walnut 4/4 S2S","solid edging, cove fascia, leveler pads \u00b7 0.94 BF net, 2 with waste","board ft",2,RATES["wal44"]),
 ("Walnut 8/4","plinth frames \u00b7 8 rails + 8 leg blocks \u00b7 3.8 BF net","board ft",6,RATES["wal84"]),
 ("Birch ply 3/4","french cleat pair, hidden behind the overhead","part sheet",1,RATES["birch"]),
 ("Leg mounting hardware","8 sets \u00b7 threaded insert + hanger bolt","lot",1,28.00),
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
 ("Plinth frames \u2014 mill and assemble","8 rails, 8 leg blocks, 2 frames squared",2.0),
 ("Leg mounts + fit frames","bore 8, hang the cabinets on them",0.5),
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

# ══════════════════ CLIENT · ANSWERS, THEN PRICE ══════════════════
def qa(o,y,n,q,a,extra=None,flag=None):
    o.append(f'<circle cx="49" cy="{y-4}" r="9" fill="{INK}"/>')
    o.append(txt(49,y,n,8.2,"middle","#fff",bold=True))
    o.append(txt(70,y,q,8.2,bold=True))
    yy=y+14
    for ln in a:
        o.append(txt(70,yy,ln,7.1)); yy+=11.4
    if extra:
        for ln in extra:
            o.append(txt(70,yy,ln,7.0,fill=MUTED)); yy+=11
    if flag:
        o.append(txt(70,yy,flag,7.0,fill=RED)); yy+=11
    o.append(line(40,yy+2,600,yy+2,HAIR,.4))
    return yy+14

def c1():
    o=[]
    o.append(txt(40,106,"YOUR QUESTIONS \u2014 THE UNIT",9.6,bold=True))
    o.append(txt(40,119,"answered in the order you asked them",7.2,fill=MUTED))
    y=146
    y=qa(o,y,"1","Height of base cabinet \u2014 can it be raised?",
      ["Yes, and it is. The unit now stands on 4\u2033 round tapered legs matching your sofa,",
       "with a 2\u2033 solid walnut bar above them. The base top lands at 26 1/4\u2033 \u2014 2\u2033 below the",
       "28 1/4\u2033 sofa arm, which is the relationship a table beside a sofa wants."],
      ["Towers are untouched; the unit grows to 114 1/2\u2033 overall rather than being cut down."])
    y=qa(o,y,"2","Wood backing for the overhead \u2014 page 1 or page 3?",
      ["Page 3. Full walnut back, inset behind the box the same way the tower backs are."])
    y=qa(o,y,"3","Inside height of the overhead \u2014 24\u2033 feels large.",
      ["Agreed. The box comes down to 13 11/16\u2033 and is divided into four compartments,",
       "each 19 3/32\u2033 wide \u00d7 12 1/4\u2033 high \u2014 the same opening height as the tower shelves,",
       "so the horizontal rhythm carries across the whole piece."],
      ["It also removes the sag risk: the longest unsupported span drops from 80\u2033 to 19 3/32\u2033.",
       "Plants belong in the compartments, not on top \u2014 the top is 114 1/2\u2033 and unreachable."])
    y=qa(o,y,"4","Baseboard, and will the doors open?",
      ["The base now sits 6\u2033 off the floor, clear of any normal baseboard, so the unit goes",
       "tight to the wall with no notching. Only the legs meet the floor, in front of the trim.",
       "The doors open fully with the unit against the wall."],
      ["Blum\u2019s CLIP top specification governs a minimum reveal measured in millimetres, not",
       "inches. We hold a scribe allowance for the wall itself, not for hinge clearance."])
    y=qa(o,y,"5","Depth of shelves \u2014 can they be deeper?",
      ["The shelves are dadoed into assembled towers, so the plywood itself cannot grow.",
       "What changes is the edge itself: the veneer tape is replaced with 1/8\u2033 solid",
       "walnut on every exposed plywood edge \u2014 shelves, stiles, overhead."],
      ["Honestly stated: no depth is added anywhere. What you gain is an edge that takes",
       "a proper arris and will never sand through \u2014 tape is 0.020\u2033, this is six times that."])
    return page("".join(o),1,5,"Answers \u2014 The Unit",
        "Woodcraft \u00b7 questions of 12 August","FOR YOUR APPROVAL")

def c2():
    o=[]
    o.append(txt(40,106,"YOUR QUESTIONS \u2014 ELECTRICAL",9.6,bold=True))
    y=132
    y=qa(o,y,"1","Plugging in \u2014 can it handle the load?",
      ["Total lighting draw is 0.64 A. Plug-in is entirely adequate; no new circuit needed."])
    y=qa(o,y,"2","Are the sconces and shelf lighting independent?",
      ["Yes \u2014 and you need only one physical switch, not two. Each base cabinet carries a",
       "recessed power centre whose face button switches that sconce alone."],
      ["The shelf lighting is a smart system and must stay powered for the app and remote to",
       "reach it, so its switch is the wireless dimmer that comes with it \u2014 on, off, dim, scenes.",
       "A second hard toggle on the shelves would break the colour matching entirely."])
    y=qa(o,y,"4","An accessible outlet on both sides, USB A and C.",
      ["The sofa fills the bay, so anything on the inner faces would be blocked. Instead each",
       "base cabinet top takes a recessed Legrand centre: two outlets, USB-A and USB-C, set",
       "right into the surface beside the arm."],
      ["The unit you linked was USB-A only; we have specified the A+C version of the same product."])
    y=qa(o,y,"6","Where does it all plug in?",
      ["Everything runs from the single existing outlet 36\u2033 from the left wall, behind the sofa.",
       "Inside each base cabinet a strip is screwed to the floor. The power centre and the lighting",
       "supply both plug into it there, and its 10 ft cord is the only thing that leaves the cabinet \u2014",
       "straight to its own receptacle. One cord per side, behind the sofa, nothing on top."],
      ["The duplex has two receptacles, so each side is entirely independent \u2014 no strip at the wall",
       "and nothing chained. Each side draws 0.41 A of lighting; even with a laptop and a phone",
       "plugged in it is under 10% of the circuit."])
    y=qa(o,y,"5","The LED system \u2014 colour temperature, matched to the sconces.",
      ["You set two priorities \u2014 adjustable colour temperature, and sconces that match the",
       "shelves. We assessed the options against those and specified Philips Hue. Concealed",
       "coves run under all twelve shelves and all four overhead compartments, the source",
       "behind a solid walnut fascia so nothing reads from the room but the light."],
      ["Hue was not the only candidate. H\u00e4fele Loox is the better cabinet product and costs less,",
       "but its sconce bulbs sit in a separate app \u2014 matching Kelvin by eye across two systems is",
       "a nuisance you would live with daily. Hue puts both on one scene \u2014 warm through cool,",
       "dimmable, from the app or the physical remote."])
    return page("".join(o),2,5,"Answers \u2014 Electrical",
        "Question 3 deferred at your request","FOR YOUR APPROVAL")

def c2b():
    o=[]
    o.append(txt(40,108,"DRAPERY TRACK",9.6,bold=True))
    o.append(txt(40,128,"We hold 6\u2033 of clear wall at the right end of the unit for the track. Track selection,",7.4))
    o.append(txt(40,141,"height and stacking are the designer\u2019s to assess \u2014 we are reserving the space, not",7.4))
    o.append(txt(40,154,"specifying the treatment.",7.4))
    o.append(txt(40,206,"CONFIRMED SINCE YOUR EMAIL",9.2,bold=True,fill=GOLD))
    for i,t in enumerate(["Ceiling height 136\u2033 \u2014 field 3D scan. The unit is 114 1/2\u2033, leaving 21 1/2\u2033 clear.",
        "Door clearance \u2014 Blum\u2019s specification is a reveal in millimetres. The unit sits tight",
        "to the wall and the doors still open fully. No side gap is required.",
        "Power \u2014 the existing outlet 36\u2033 from the left wall serves the whole installation."]):
        o.append(txt(40,224+i*13,"\u2022 " if i!=2 else "  ",7.3))
        o.append(txt(52 if i!=2 else 52,224+i*13,t,7.3))
    o.append(r_(40,296,560,88,"#FFF9F0",GOLD,1.2))
    o.append(txt(56,316,"STILL OPEN",8.4,bold=True,fill=GOLD))
    for i,t in enumerate(["Wall-to-wall width \u2014 for the scribe allowance, not for door clearance.",
        "Confirmation that 6\u2033 at the right end is enough for the track.",
        "Eight legs, COM \u2014 the only material you supply. See the note below.",
        "Baseboard height, to confirm it sits under the 6\u2033 base."]):
        o.append(txt(56,334+i*12.6,"\u2022 "+t,7.2))
    o.append(r_(40,398,560,92,"#FFF9F0",RED,1.3))
    o.append(txt(56,418,"COM LEGS \u2014 ONE DIMENSION WE NEED",8.4,bold=True,fill=RED))
    o.append(txt(56,436,"The unit and the sofa stand on the same floor, so their legs have to match or the two",7.3))
    o.append(txt(56,449,"pieces read as sitting on different planes. Please confirm EITHER the finished leg height,",7.3))
    o.append(txt(56,462,"floor to the underside of the frame it bolts to, OR the sofa\u2019s own floor-to-frame dimension",7.3))
    o.append(txt(56,475,"measured on the delivered piece. We set the plinth rail to suit so both bottoms align.",7.3))
    o.append(txt(40,508,"WHAT HAPPENS NEXT",9.2,bold=True))
    for i,t in enumerate(["On your approval we cut the overhead, mill the edging and fascia, and order the lighting.",
        "Nothing is cut before then \u2014 the towers, doors and carcasses stay as built. The plinth rails",
        "are cut last, once the leg dimension above is confirmed."]):
        o.append(txt(40,526+i*13,t,7.3))
    return page("".join(o),3,5,"Confirmations & Next Steps",
        "what has been settled, and what we still need","FOR YOUR APPROVAL")

def c3():
    o=[]
    o.append(txt(40,106,"A \u00b7 CABINETRY",9.4,bold=True))
    o.append(txt(40,119,"solid walnut, hardware and finish for the added work",7.0,fill=MUTED))
    o.append(txt(40,138,"ITEM",6.2,fill=MUTED,mono=True)); o.append(txt(430,138,"QTY",6.2,"end",MUTED,mono=True))
    o.append(txt(520,138,"UNIT",6.2,"end",MUTED,mono=True)); o.append(txt(600,138,"AMOUNT",6.2,"end",MUTED,mono=True))
    o.append(line(40,142,600,142,HAIR))
    for i,(nm,d_,u,q,p) in enumerate(MAT):
        yy=156+i*18.6
        o.append(txt(40,yy,nm,7.3,bold=True)); o.append(txt(40,yy+9,d_,6.3,fill=MUTED))
        o.append(txt(430,yy+3,f'{q} {u}',7.0,"end",mono=True))
        o.append(txt(520,yy+3,f'${p:,.2f}',7.0,"end",mono=True))
        o.append(txt(600,yy+3,f'${q*p:,.2f}',7.2,"end",mono=True))
        o.append(line(40,yy+12,600,yy+12,HAIR,.4))
    y=156+len(MAT)*18.6+4
    o.append(txt(40,y,"Cabinetry",7.6,bold=True)); o.append(txt(600,y,f'${MATSUB:,.2f}',8.0,"end",bold=True))
    yb=y+30
    o.append(txt(40,yb,"B \u00b7 LIGHTING, POWER & CONTROL",9.4,bold=True))
    o.append(txt(40,yb+13,"supplied, installed and tested by us \u00b7 tap any product name for the listing",7.0,fill=MUTED))
    o.append(txt(40,yb+32,"ITEM",6.2,fill=MUTED,mono=True)); o.append(txt(430,yb+32,"QTY",6.2,"end",MUTED,mono=True))
    o.append(txt(520,yb+32,"UNIT",6.2,"end",MUTED,mono=True)); o.append(txt(600,yb+32,"AMOUNT",6.2,"end",MUTED,mono=True))
    o.append(line(40,yb+36,600,yb+36,HAIR))
    for i,(nm,d_,u_,q,p) in enumerate(LED):
        yy=yb+50+i*17.4
        o.append(txt(40,yy,nm,7.2,fill="#2B5AA0")); o.append(txt(300,yy,d_,6.3,fill=MUTED))
        o.append(txt(430,yy,str(q),7.0,"end",mono=True))
        o.append(txt(520,yy,f'${p:,.2f}',7.0,"end",mono=True))
        o.append(txt(600,yy,f'${q*p:,.2f}',7.2,"end",mono=True))
        LINKS.append((3,40,yy-7,40+len(nm)*3.9,yy+3,u_))
        o.append(line(40,yy+4,600,yy+4,HAIR,.4))
    yl=yb+50+len(LED)*17.4+4
    o.append(txt(40,yl,"Lighting, power and control",7.6,bold=True))
    o.append(txt(600,yl,f'${LEDSUB:,.2f}',8.0,"end",bold=True))
    o.append(r_(628,96,124,220,"#FFF9F0",GOLD,1.2))
    o.append(txt(638,114,"NOT BILLED",7.8,bold=True,fill=GOLD))
    NN=["Walnut plywood \u2014 already on hand.","","Legs \u2014 supplied by you.","",
        "Original contracted scope \u2014 unchanged and not re-billed.","",
        "Lighting prices are current street prices, confirmed at order."]
    def wr(t,cap=22):
        out=[];cur=""
        for w_ in t.split():
            if len(cur+" "+w_)>cap and cur: out.append(cur);cur=w_
            else: cur=(cur+" "+w_).strip()
        if cur: out.append(cur)
        return out or [""]
    yy=132
    for t in NN:
        for ln in wr(t): o.append(txt(638,yy,ln,6.5)); yy+=11
    return page("".join(o),4,5,"Breakdown \u2014 Materials",
        "Two schedules, at cost \u00b7 marked up on the next sheet","FOR YOUR APPROVAL")

def c4():
    o=[]
    o.append(txt(40,110,"A \u00b7 LABOUR \u2014 WORK ADDED AFTER DESIGN APPROVAL",9.4,bold=True))
    o.append(line(40,120,600,120,HAIR))
    for i,(n_,d_,h) in enumerate(SCOPE):
        yy=138+i*19
        o.append(txt(40,yy,n_,7.6)); o.append(txt(300,yy,d_,6.9,fill=MUTED))
        o.append(txt(600,yy,f'{h:.1f} h',7.6,"end",mono=True))
        o.append(line(40,yy+5,600,yy+5,HAIR,.4))
    y2=138+len(SCOPE)*19+8
    o.append(txt(40,y2,f'{S["LABOR_HRS"]:.1f} hours at ${S["LABOR_RATE"]:,.2f}/hr',8.0,bold=True))
    o.append(txt(600,y2,f'${LAB:,.2f}',8.6,"end",bold=True))
    yg=y2+42
    o.append(txt(40,yg,"B \u00b7 SUMMARY",9.4,bold=True))
    o.append(line(40,yg+10,600,yg+10,HAIR))
    rows=[("Cabinetry materials",MATSUB,False),
          ("Lighting, power and control",LEDSUB,False),
          ("Materials, total",GOODS,True),
          (f'Handling and procurement, {S["MARKUP"]*100:.0f}%',GOODS*S["MARKUP"],False),
          ("Materials, billed",GOODSELL,True),
          (f'Labour \u00b7 {S["LABOR_HRS"]} h at ${S["LABOR_RATE"]:,.2f}',LAB,False)]
    for i,(n_,v,bold) in enumerate(rows):
        yy=yg+30+i*20
        o.append(txt(40,yy,n_,7.6,bold=bold,fill=(INK if bold else MUTED)))
        o.append(txt(600,yy,f'${v:,.2f}',8.0 if bold else 7.6,"end",mono=True,bold=bold))
        o.append(line(40,yy+6,600,yy+6,HAIR,.5 if bold else .3))
    yt=yg+30+len(rows)*20+14
    o.append(r_(40,yt,560,50,PAPER,INK,1.5))
    o.append(txt(58,yt+32,"TOTAL \u2014 CHANGE ORDER",11,bold=True))
    o.append(txt(582,yt+32,f'${TOTAL:,.2f}',17,"end",bold=True))
    o.append(r_(628,110,124,200,PAPER,HAIR,1))
    o.append(txt(638,130,"WHAT THIS COVERS",7.6,bold=True))
    NN=["Only work added after you approved the design.","",
        "The original contract is unchanged and is not re-billed.","",
        "Legs are yours to supply.","",
        "Walnut plywood already on hand is not charged."]
    def wr(t,cap=22):
        out=[];cur=""
        for w_ in t.split():
            if len(cur+" "+w_)>cap and cur: out.append(cur);cur=w_
            else: cur=(cur+" "+w_).strip()
        if cur: out.append(cur)
        return out or [""]
    yy=148
    for t in NN:
        for ln in wr(t): o.append(txt(638,yy,ln,6.5)); yy+=11
    o.append(line(40,PH-96,600,PH-96,HAIR))
    o.append(txt(40,PH-78,"Approved",7.4,fill=MUTED))
    o.append(line(40,PH-60,300,PH-60,INK,.9)); o.append(line(330,PH-60,470,PH-60,INK,.9))
    o.append(txt(40,PH-50,"Signature",6.4,fill=MUTED)); o.append(txt(330,PH-50,"Date",6.4,fill=MUTED))
    return page("".join(o),5,5,"Breakdown \u2014 Labour & Total",
        f'{S["LABOR_HRS"]} h at ${S["LABOR_RATE"]:,.2f} \u00b7 materials + {S["MARKUP"]*100:.0f}%',"FOR YOUR APPROVAL")

LINKS=[]
sheets=[c1(),c2(),c2b(),c3(),c4()]
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
w.add_metadata({"/Title":"R6 REV G Change Order - Client"})
with open("/mnt/user-data/outputs/R6-CLIENT-change-order-rev-G.pdf","wb") as f: w.write(f)
for i,sv in enumerate(sheets,1):
    cairosvg.svg2png(bytestring=sv.encode(),write_to=f"/home/claude/C{i}.png",scale=1.7)
print(f"4 sheets \u00b7 total ${TOTAL:,.2f}")
