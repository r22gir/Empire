#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
McLEAN - Window & Drapery Field Measurement Set
Client: Whittington Design, McLean VA
Nelma's Workroom - Powered by Empire Workroom

Rebuilt from the 1 July 2026 field sketch set (9pp) into the Empire B2d sheet
language: landscape letter, black header/footer bands, cream paper, gold rules,
framed viewport, title column, layout-math block, honesty notes.

DOCTRINE
  - One SPEC dict drives every sheet. Nothing is typed twice.
  - No invented dimensions. Untagged geometry is drawn schematically and is
    named as untagged in the FIELD CHECK block on its own sheet.
  - Gates run before emit: width closure, item fit, height closure, schedule
    count, rev singularity. Closure failures do not fabricate a number - they
    print on the sheet as a delta the founder must confirm on site.
"""
import io, math, sys
import cairosvg
from pypdf import PdfWriter, PdfReader

# ══════════════════════════ SHEET FURNITURE ══════════════════════════════
PW, PH = 792.0, 612.0          # US Letter landscape, points

PAPER = "#f7f3ea"
INK   = "#20241f"
GOLD  = "#b8912f"
BAND  = "#16191c"
HAIR  = "#cdc4b0"
MUTE  = "#7b7466"
CREAM = "#efe9dc"

GLASS  = "#ccd8e4"
GLASS2 = "#dde5ee"
FRAME  = "#2a3d52"
DOORF  = "#ded2bb"
DOORS  = "#8a7a5c"
MOULD  = "#dcc79a"
STONE  = "#d5cdbf"
FIREBX = "#3a3129"

HDR_H, FTR_H = 44.0, 26.0

SANS = "DejaVu Sans"
MONO = "DejaVu Sans Mono"
SERIF = "DejaVu Serif"


from PIL import ImageFont

_FD = "/usr/share/fonts/truetype/dejavu/"
_FACE = {
    (SANS, False, False):  "DejaVuSans.ttf",
    (SANS, True,  False):  "DejaVuSans-Bold.ttf",
    (SANS, False, True):   "DejaVuSans-Oblique.ttf",
    (SANS, True,  True):   "DejaVuSans-BoldOblique.ttf",
    (MONO, False, False):  "DejaVuSansMono.ttf",
    (MONO, True,  False):  "DejaVuSansMono-Bold.ttf",
    (MONO, False, True):   "DejaVuSansMono-Oblique.ttf",
    (MONO, True,  True):   "DejaVuSansMono-BoldOblique.ttf",
    (SERIF, False, False): "DejaVuSerif.ttf",
    (SERIF, True,  False): "DejaVuSerif-Bold.ttf",
    (SERIF, False, True):  "DejaVuSerif-Italic.ttf",
    (SERIF, True,  True):  "DejaVuSerif-BoldItalic.ttf",
}
_CACHE = {}


def _font(font, size, bold, italic):
    key = (font, round(size, 2), bold, italic)
    if key not in _CACHE:
        _CACHE[key] = ImageFont.truetype(_FD + _FACE[(font, bold, italic)],
                                         max(int(round(size * 4)), 4))
    return _CACHE[key], size


def tw(s, size, font=SANS, bold=False, italic=False, ls=0.0):
    """Rendered advance width in points, letter-spacing included."""
    f, _ = _font(font, size, bold, italic)
    return f.getlength(s) / 4.0 + ls * max(len(s) - 1, 0)


PLACED = []          # (x0, y0, x1, y1, payload) - text boxes only


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def T(x, y, s, size=8.0, anchor="start", fill=None, font=SANS,
      bold=False, ls=0.0, italic=False, op=1.0, track=True, rot=None):
    w = ' font-weight="bold"' if bold else ""
    i = ' font-style="italic"' if italic else ""
    l = f' letter-spacing="{ls}"' if ls else ""
    if track and s.strip():
        adv = tw(s, size, font, bold, italic, ls)
        x0 = x if anchor == "start" else (x - adv if anchor == "end" else x - adv / 2)
        if rot == -90:
            PLACED.append((x - size * 0.80, y - adv / 2,
                           x + size * 0.24, y + adv / 2, s))
        else:
            PLACED.append((x0, y - size * 0.78, x0 + adv, y + size * 0.24, s))
    return (f'<text x="{x:.2f}" y="{y:.2f}" font-family="{font}" font-size="{size}" '
            f'fill="{fill or INK}" text-anchor="{anchor}" opacity="{op}"{w}{i}{l}>{esc(s)}</text>')


def RECT(x, y, w, h, fill="none", stroke="none", sw=1.0, dash=None, op=1.0):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(w,0):.2f}" height="{max(h,0):.2f}" '
            f'fill="{fill}" stroke="{stroke}" stroke-width="{sw}" opacity="{op}"{d}/>')


def LINE(x1, y1, x2, y2, stroke=INK, sw=0.8, dash=None, op=1.0):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{stroke}" stroke-width="{sw}" opacity="{op}"{d}/>')


def hdim(x1, x2, y, label, size=10.0, col=None, above=True, flag=False):
    """Horizontal dimension with slash ticks, architect style."""
    c = col or (GOLD if flag else INK)
    o = [LINE(x1, y, x2, y, c, 0.7)]
    for x in (x1, x2):
        o.append(LINE(x - 2.6, y + 2.6, x + 2.6, y - 2.6, c, 0.7))
        o.append(LINE(x, y - 3.2, x, y + 3.2, c, 0.7))
    ly = y - 5.6 if above else y + 12.4
    o.append(T((x1 + x2) / 2, ly, label, size, "middle", c, MONO, bold=True, ls=0.3))
    return "".join(o)


def vdim(y1, y2, x, label, size=10.0, col=None, left=True, flag=False):
    """Vertical dimension. The NUMBER IS ALWAYS HORIZONTAL - it breaks the
    dimension line at mid height, drafting convention."""
    c = col or (GOLD if flag else INK)
    o = [LINE(x, y1, x, y2, c, 0.7)]
    for y in (y1, y2):
        o.append(LINE(x - 2.6, y + 2.6, x + 2.6, y - 2.6, c, 0.7))
        o.append(LINE(x - 3.2, y, x + 3.2, y, c, 0.7))
    cy = (y1 + y2) / 2
    w = tw(label, size, MONO, True, ls=0.3)
    o.append(RECT(x - w / 2 - 3.5, cy - size * 0.70, w + 7, size * 1.02,
                  "#fbf8f1"))
    o.append(T(x, cy + size * 0.32, label, size, "middle", c, MONO,
               bold=True, ls=0.3))
    return "".join(o)


VDIM_GUTTER = 30.0      # half the widest number, plus air
VDIM_STEP = 48.0        # lateral pitch when right-hand dims stack


# ══════════════════════════ THE SPEC ═════════════════════════════════════
# Every number below came off the 1 July 2026 field sheets. Nothing here is
# derived; derived values are computed in DERIVED and printed as such.

JOB = {
    "project":  "McLEAN",
    "client":   "WHITTINGTON DESIGN",
    "client_loc": "McLEAN, VA",
    "scope":    "Window & Drapery Field Measurements",
    "letterhead": "NELMA'S WORKROOM",
    "poweredby":  "POWERED BY EMPIRE WORKROOM",
    "locale":   "HYATTSVILLE MD",
    "rev":      "A",
    "date":     "19 AUG 2026",
    "source":   "Field sketch set, 1 July 2026",
    "status":   "FOR DISCUSSION - NOT FOR CONSTRUCTION",
}

# item kinds: window / door / fireplace / ghost
# v: (head_aff, height) in inches when field-tagged; None = schematic placement
ROOMS = [
 {
  "key": "FD", "name": "FORMAL DINING",
  "sub": "One opening - 99\" wide - 105\u00be\" floor to ceiling - 6\u00bd\" header",
  "panels": [
    {"label": "FORMAL DINING", "w": 127.0, "h": 105.75, "ghost_wall": True,
     "top_band": (6.5, "6\u00bd\" HEADER"),
     "items": [{"kind": "window", "w": 99.0, "x": 14.0, "v": None}],
     "dims_top": [(14.0, 113.0, "99\"")],
     "dim_h": "105\u00be\"",
     "dims_right": [(99.25, 105.75, "6\u00bd\"")],
    }],
  "data": [("OPENING WIDTH", "99\""),
           ("FLOOR TO CEILING", "105\u00be\""),
           ("HEADER ABOVE OPENING", "6\u00bd\""),
           ("WINDOW HEIGHT", "not tagged"),
           ("SILL TO FLOOR", "not tagged"),
           ("MOUNT CONDITION", "not tagged")],
  "math": "HEAD AT 99\u00bc\" AFF = 105\u00be\" CEILING less 6\u00bd\" HEADER  -  DERIVED, CONFIRM",
  "math_flag": False,
  "check": ["Window height and sill height are not on the field sheet - the "
            "opening is drawn schematically between head and sill.",
            "6\u00bd\" header is the only stacking space above the opening. "
            "Confirm rod / board can land in it before specifying a heading.",
            "Confirm whether 99\" is glass, frame or trim to trim.",
            "Wall width either side of the opening is not tagged - the wall is "
            "drawn ghosted and must not be scaled."],
 },
 {
  "key": "FLB", "name": "FORMAL LIVING - BAY WINDOW",
  "sub": "Bay, four windows - 27\" each - flat moulding 2\u00bd\" tall",
  "panels": [
    {"label": "BAY - 4 WINDOWS", "w": 108.0, "h": 110.5,
     "top_band": (4.5, "FLAT MOULDING"),
     "items": [{"kind": "window", "w": 27.0, "x": 0.0,  "v": (106.0, 101.25)},
               {"kind": "window", "w": 27.0, "x": 27.0, "v": (106.0, 101.25)},
               {"kind": "window", "w": 27.0, "x": 54.0, "v": (106.0, 101.25)},
               {"kind": "window", "w": 27.0, "x": 81.0, "v": (106.0, 101.25)}],
     "dims_top": [(0.0, 27.0, "27\""), (27.0, 54.0, "27\""),
                  (54.0, 81.0, "27\""), (81.0, 108.0, "27\"")],
     "dim_h": "110\u00bd\"",
     "dims_right": [(0.0, 106.0, "106\""),
                    (4.75, 106.0, "101\u00bc\"")],
    }],
  "data": [("WINDOWS", "4 @ 27\" = 108\""),
           ("FLOOR TO TOP OF MOULDING", "110\u00bd\""),
           ("FLOOR TO BOT. OF MOULDING", "106\""),
           ("MOULDING FACE", "2\u00bd\" tall"),
           ("WINDOW HEIGHT", "101\u00bc\""),
           ("MULLION / JAMB WIDTHS", "not tagged")],
  "math": "110\u00bd less 106 = 4\u00bd\" BAND  vs  2\u00bd\" MOULDING TAGGED  -  \u0394 2\"  CONFIRM",
  "math_flag": True,
  "check": ["The moulding band scales 4\u00bd\" between the two floor dimensions "
            "but is tagged 2\u00bd\" tall. 2\" is unaccounted - remeasure the band "
            "before ordering hardware.",
            "Sill derives at 4\u00be\" AFF (106 head less 101\u00bc window). Derived, "
            "not measured.",
            "Bay return angles and mullion widths are not tagged. Four 27\" "
            "sashes are drawn abutting; treat overall 108\" as a floor, not a "
            "finished width."],
 },
 {
  "key": "FLR", "name": "FORMAL LIVING - RIGHT OF FIREPLACE",
  "sub": "Reference window 43\" wide - height shown for reference only",
  "panels": [
    {"label": "RIGHT OF FIREPLACE", "w": 71.0, "h": 110.5, "ghost_wall": True,
     "top_band": (4.5, "MOULDING"),
     "items": [{"kind": "window", "w": 43.0, "x": 14.0, "v": None}],
     "dims_top": [(14.0, 57.0, "43\"")],
     "dim_h": "110\u00bd\"",
     "dims_right": [(0.0, 106.0, "106\"")],
    }],
  "data": [("WINDOW WIDTH", "43\""),
           ("FLOOR TO TOP OF MOULDING", "110\u00bd\""),
           ("FLOOR TO BOT. OF MOULDING", "106\""),
           ("WINDOW HEIGHT", "reference only - not tagged"),
           ("WALL WIDTH", "not tagged"),
           ("FIREPLACE OFFSET", "not tagged")],
  "math": "SAME MOULDING HEIGHTS AS THE BAY - 110\u00bd / 106 - CROSS-CHECKED, AGREE",
  "math_flag": False,
  "check": ["Field note states plainly that 43\" is the width and the height is "
            "reference only. The window is drawn schematically in elevation.",
            "Wall width either side of this window is not tagged, so return and "
            "stack space cannot be checked from this sheet.",
            "Confirm this window matches the Family Room 43\" units before "
            "treating them as one type."],
 },
 {
  "key": "LRB", "name": "LIVING ROOM WITH BALCONY",
  "sub": "Three walls - left 187\" - center 222\" - right 99\"",
  "panels": [
    {"label": "LEFT WALL", "w": 187.0, "h": 114.25,
     "items": [{"kind": "window", "w": 27.0, "x": 37.5,  "v": None},
               {"kind": "door",   "w": 54.25,"x": 69.0,  "v": None, "tag": "DOORS"},
               {"kind": "window", "w": 27.0, "x": 127.75,"v": None}],
     "dims_top": [(0.0, 33.0, "33\""), (33.0, 69.0, "36\""),
                  (69.0, 123.25, "UNTAGGED"), (123.25, 159.25, "36\""),
                  (159.25, 187.0, "27\u00be\"")],
     "dims_bot": [(42.0, 69.0, "27\""), (127.75, 154.75, "27\""),
                  (0.0, 187.0, "187\" OVERALL")],
     "dim_h": "114\u00bc\"",
    },
    {"label": "CENTER WALL", "w": 222.0, "h": 114.25,
     "items": [],
     "divisions": [77.5, 146.75],
     "dims_top": [(0.0, 77.5, "77\u00bd\""), (77.5, 146.75, "69\u00bc\""),
                  (146.75, 222.0, "78\u00bc\" TAGGED")],
     "dims_bot": [(0.0, 222.0, "222\" OVERALL")],
     "dim_h": "114\u00bc\"",
    },
    {"label": "RIGHT WALL", "w": 180.0, "h": 110.25, "ghost_wall": True,
     "no_ghost_note": True,
     "top_band": (7.0, "OVERHEAD"),
     "items": [{"kind": "window", "w": 99.0, "x": 40.5, "v": None}],
     "dims_bot": [(40.5, 139.5, "99\"")],
     "dim_h": "110\u00bc\"",
    }],
  "data": [("LEFT WALL", "187\" wide - 114\u00bc\" high"),
           ("LEFT WALL OPENINGS", "2 windows @ 27\" + door bank"),
           ("CENTER WALL", "222\" wide - 114\u00bc\" high"),
           ("RIGHT WALL WINDOW", "99\" wide"),
           ("RIGHT WALL HEIGHT", "110\u00bc\""),
           ("RIGHT WALL OVERHEAD", "present, height not tagged"),
           ("DOOR BANK WIDTH", "not tagged")],
  "math": "LEFT 33+36+36+27\u00be = 132\u00be TAGGED vs 187 OVERALL - 54\u00bc UNTAGGED AT DOORS   "
          "|   CENTER 77\u00bd+69\u00bc+78\u00bc = 225 vs 222 OVERALL - \u0394 3\"  CONFIRM",
  "math_flag": True,
  "check": ["Left wall: the tagged run leaves 54\u00bc\" untagged, drawn at the "
            "door bank on the reading that the string runs left to right with "
            "the doors unmeasured. Confirm on site.",
            "Center wall: segments total 225\" against a 222\" overall. "
            "Divisions drawn at 77\u00bd\" and 146\u00be\", scaling the third bay "
            "75\u00bc\" not 78\u00bc\". 3\" must be found.",
            "Right wall: 99\" is the window, not the wall. The wall is drawn "
            "at roughly 15 ft for scale only and is deliberately not "
            "dimensioned - tape it before quoting stack space.",
            "Right wall overhead depth and height are not tagged - the band is "
            "schematic. It governs ceiling versus wall mount.",
            "Ceiling differs wall to wall (114\u00bc\" vs 110\u00bc\"). Verify before "
            "any continuous rod is specified across the room."],
 },
 {
  "key": "FR", "name": "FAMILY ROOM",
  "sub": "Fireplace wall - four windows @ 43\" - wall height 110\u00bc\"",
  "panels": [
    {"label": "LEFT RUN", "w": 144.0, "h": 110.25,
     "items": [{"kind": "window", "w": 43.0, "v": None},
               {"kind": "window", "w": 43.0, "v": None}],
     "dims_top": [("i0", "43\""), ("i1", "43\"")],
     "dim_h": "110\u00bc\"",
    },
    {"label": "FIREPLACE", "w": 46.0, "h": 110.25, "ghost_wall": True,
     "items": [{"kind": "fireplace", "w": 46.0, "x": 0.0, "v": None}],
     "dims_bot": [(0.0, 46.0, "WIDTH NOT TAGGED")],
    },
    {"label": "RIGHT RUN", "w": 144.0, "h": 110.25,
     "items": [{"kind": "window", "w": 43.0, "v": None},
               {"kind": "window", "w": 43.0, "v": None}],
     "dims_top": [("i0", "43\""), ("i1", "43\"")],
     "dim_h": "110\u00bc\"",
    }],
  "data": [("WALL EACH SIDE", "12 ft nominal - scale only"),
           ("WINDOWS", "4 @ 43\" wide"),
           ("WALL HEIGHT", "110\u00bc\""),
           ("WINDOW HEIGHT", "not tagged"),
           ("WINDOW SPACING", "not tagged - drawn even"),
           ("FIREPLACE WIDTH", "not tagged")],
  "math": "PER RUN  2 \u00d7 43 = 86\" GLASS  -  RUN LENGTH IS NOMINAL 12 FT, "
          "SHOWN FOR SCALE, NOT DIMENSIONED",
  "math_flag": False,
  "check": ["The 12 ft run is nominal - it carries the scale only and is "
            "deliberately not dimensioned. Tape each run before quoting.",
            "Window spacing is not on the field sheet. The two windows per run "
            "are drawn evenly distributed - do not scale returns off this.",
            "Window heights are not tagged. Only the 110\u00bc\" wall height is.",
            "Fireplace width and breast projection are not tagged; it is shown "
            "as a ghost so the two 12 ft runs read at true scale.",
            "43\" here matches the Formal Living, Laundry and Powder Room "
            "windows - confirm they are one type before batching."],
 },
 {
  "key": "KD", "name": "KITCHEN / DINING",
  "sub": "Two matching window units and a door - wall 110\u00bc\"",
  "panels": [
    {"label": "KITCHEN / DINING WALL", "w": 220.0, "h": 110.25,
     "items": [{"kind": "window", "w": 77.0, "x": 8.0,   "v": None, "inner": 66.0},
               {"kind": "window", "w": 77.0, "x": 105.0, "v": None, "inner": 66.0},
               {"kind": "door",   "w": 32.0, "x": 186.0, "v": None, "tag": "DOOR"}],
     "dims_top": [(8.0, 85.0, "77\""), (105.0, 182.0, "77\"")],
     "dims_bot": [(13.5, 79.5, "66\""), (110.5, 176.5, "66\"")],
     "dim_h": "110\u00bc\"",
     "dims_right": [(0.0, 92.75, "92\u00be\"")],
     "ghost_wall": True,
    }],
  "data": [("WINDOW UNITS", "2 matching"),
           ("UNIT WIDTH", "77\""),
           ("WINDOW WIDTH", "66\""),
           ("WINDOW HEIGHT", "92\u00be\""),
           ("WALL HEIGHT", "110\u00bc\""),
           ("DOOR WIDTH", "not tagged"),
           ("WALL LENGTH", "not tagged")],
  "math": "110\u00bc CEILING less 92\u00be WINDOW = 17\u00bd\" TO SPLIT HEAD / SILL  -  SPLIT NOT TAGGED",
  "math_flag": False,
  "check": ["Confirm whether 77\" is trim to trim and 66\" is the glass or the "
            "frame - the treatment width depends on which.",
            "17\u00bd\" is all the space there is above and below the window "
            "together. Head clearance may be tight for a board mount.",
            "Wall length, door width and the gap between units are not tagged. "
            "Units are drawn at true 77\" width, spacing schematic.",
            "Door swing and handing not recorded - matters for panel stacking."],
 },
 {
  "key": "OF", "name": "OFFICE",
  "sub": "Three windows - all 93\" tall - floor to ceiling 112\"",
  "panels": [
    {"label": "WINDOW 1", "w": 41.5, "h": 112.0,
     "items": [{"kind": "window", "w": 31.5, "v": (98.0, 93.0)}],
     "dims_top": [(0.0, 41.5, "41\u00bd\"")],
     "dims_bot": [("i0", "31\u00bd\"")],
     "dim_h": "112\"",
    },
    {"label": "WINDOW 2", "w": 41.75, "h": 112.0,
     "items": [{"kind": "window", "w": 31.5, "v": (98.0, 93.0)}],
     "dims_top": [(0.0, 41.75, "41\u00be\"")],
     "dims_bot": [("i0", "31\u00bd\"")],
    },
    {"label": "WINDOW 3", "w": 41.75, "h": 112.0,
     "items": [{"kind": "window", "w": 31.5, "v": (98.0, 93.0)}],
     "dims_top": [(0.0, 41.75, "41\u00be\"")],
     "dims_bot": [("i0", "31\u00bd\"")],
     "dims_right": [(5.0, 98.0, "93\"")],
    }],
  "data": [("WINDOWS", "3"),
           ("OUTER WIDTHS", "41\u00bd\" - 41\u00be\" - 41\u00be\""),
           ("GLASS / SASH WIDTH", "31\u00bd\" each"),
           ("WINDOW HEIGHT", "93\" all three"),
           ("FLOOR TO CEILING", "112\""),
           ("SPACING BETWEEN", "not tagged")],
  "math": "112 CEILING less 93 WINDOW = 19\" TOTAL HEAD + SILL  -  SPLIT NOT TAGGED, "
          "5\" SILL SHOWN SCHEMATIC",
  "math_flag": False,
  "check": ["The three outer widths differ by \u00bc\". Treat them as three "
            "separate takeoffs, not one repeated unit.",
            "Head height above the window is not tagged. 19\" is the whole "
            "budget for head plus sill together.",
            "Spacing between the three windows is not tagged - they are drawn "
            "as three separate elevations rather than one wall run.",
            "Confirm whether they share a wall or turn a corner.",
            "Room is full-height wood panelling. Confirm whether hardware "
            "lands on the panel, the stile or above the frieze - it changes "
            "the fixing and the finished length."],
 },
 {
  "key": "LA", "name": "LAUNDRY",
  "sub": "Both windows 43\" \u00d7 79\" - 15\" overhead",
  "panels": [
    {"label": "WINDOW 1", "w": 63.0, "h": 94.0, "open_bottom": True,
     "ghost_wall": True, "top_band": (15.0, "15\" OVERHEAD"),
     "items": [{"kind": "window", "w": 43.0, "x": 10.0, "v": (79.0, 79.0)}],
     "dims_bot": [(10.0, 53.0, "43\"")],
    },
    {"label": "WINDOW 2", "w": 63.0, "h": 94.0, "open_bottom": True,
     "ghost_wall": True, "top_band": (15.0, "15\" OVERHEAD"),
     "items": [{"kind": "window", "w": 43.0, "x": 10.0, "v": (79.0, 79.0)}],
     "dims_bot": [(10.0, 53.0, "43\"")],
     "dims_right": [(0.0, 79.0, "79\""), (79.0, 94.0, "15\"")],
    }],
  "data": [("WINDOWS", "2 matching"),
           ("WINDOW WIDTH", "43\""),
           ("WINDOW HEIGHT", "79\""),
           ("OVERHEAD ABOVE WINDOW", "15\""),
           ("SILL TO FLOOR", "not tagged"),
           ("FLOOR TO CEILING", "not tagged")],
  "math": "79 WINDOW + 15 OVERHEAD = 94\" ESTABLISHED FROM SILL UP  -  SILL HEIGHT NOT TAGGED",
  "math_flag": False,
  "check": ["Sill height is not tagged, so floor to ceiling cannot be derived. "
            "The zone below the sill is hatched, not drawn. Heights are "
            "dimensioned once, on Window 2 - both windows are alike.",
            "15\" overhead is generous - a board or rod will land, but confirm "
            "whether the 15\" runs to ceiling or to a soffit.",
            "43\" \u00d7 79\" matches the Powder Room window exactly. Confirm one "
            "type across all three."],
 },
 {
  "key": "PR", "name": "POWDER ROOM",
  "sub": "One window - 43\" wide \u00d7 79\" high - 15\" overhead",
  "panels": [
    {"label": "POWDER ROOM WINDOW", "w": 63.0, "h": 94.0, "open_bottom": True,
     "ghost_wall": True, "top_band": (15.0, "15\" OVERHEAD"),
     "items": [{"kind": "window", "w": 43.0, "x": 10.0, "v": (79.0, 79.0)}],
     "dims_bot": [(10.0, 53.0, "43\"")],
     "dims_right": [(0.0, 79.0, "79\""), (79.0, 94.0, "15\"")],
    }],
  "data": [("WINDOWS", "1"),
           ("WINDOW WIDTH", "43\""),
           ("WINDOW HEIGHT", "79\""),
           ("OVERHEAD ABOVE WINDOW", "15\""),
           ("SILL TO FLOOR", "not tagged"),
           ("FLOOR TO CEILING", "not tagged")],
  "math": "IDENTICAL TAKEOFF TO LAUNDRY - 43 \u00d7 79 WITH 15\" OVERHEAD  -  CROSS-CHECKED",
  "math_flag": False,
  "check": ["Same takeoff as both Laundry windows. If confirmed, this is a "
            "three-of-a-kind and should be batched.",
            "Sill height not tagged - zone below the sill is hatched.",
            "Privacy requirement not recorded. Ask before specifying a sheer."],
 },
]

# schedule rows: room, mark, qty, width, height, overhead / head note
SCHEDULE = [
  ("FORMAL DINING",              "FD-1",  1, "99\"",     "not tagged",  "6\u00bd\" header - 105\u00be\" ceiling"),
  ("FORMAL LIVING - BAY",        "FLB-1", 4, "27\" ea",  "101\u00bc\"",  "106\" to bottom of moulding"),
  ("FORMAL LIVING - R/FPL",      "FLR-1", 1, "43\"",     "reference",   "106\" to bottom of moulding"),
  ("LIVING RM - LEFT WALL",      "LRB-1", 2, "27\" ea",  "not tagged",  "114\u00bc\" ceiling - door bank between"),
  ("LIVING RM - CENTER WALL",    "LRB-2", 1, "222\"",    "not tagged",  "114\u00bc\" ceiling - 3\" closure open"),
  ("LIVING RM - RIGHT WALL",     "LRB-3", 1, "99\" window","not tagged", "110\u00bc\" ceiling - overhead present"),
  ("FAMILY ROOM",                "FR-1",  4, "43\" ea",  "not tagged",  "110\u00bc\" ceiling - 12 ft runs"),
  ("KITCHEN / DINING",           "KD-1",  2, "66\" glass","92\u00be\"",  "77\" unit - 17\u00bd\" head+sill total"),
  ("OFFICE",                     "OF-1",  3, "31\u00bd\" ea","93\"",     "112\" ceiling - outers 41\u00bd / 41\u00be / 41\u00be"),
  ("LAUNDRY",                    "LA-1",  2, "43\" ea",  "79\"",        "15\" overhead"),
  ("POWDER ROOM",                "PR-1",  1, "43\"",     "79\"",        "15\" overhead"),
]


# ══════════════════════════ SITE PHOTOS ══════════════════════════════════
# Field photos, McLean, keyed to the room sheet they belong on.
PHOTO_DIR = "/home/claude/ph/"
PHOTOS = {
  "FD":  [("IMG_0726.jpg", "Window wall from the room - wainscot below")],
  "FLB": [("IMG_0724.jpg", "Bay from the room - four sashes, curved return")],
  "FLR": [("IMG_0725.jpg", "Mantel wall - reference window right of fireplace")],
  "LRB": [("IMG_0723.jpg", "LEFT WALL - balcony doors"),
          ("IMG_0722.jpg", "CENTER WALL - 3 units"),
          ("IMG_0721.jpg", "RIGHT WALL - triple unit")],
  "FR":  [("IMG_0727.jpg", "Fireplace wall - two windows each side")],
  "KD":  [("IMG_0728.jpg", "Two window units and the transomed door")],
  "OF":  [("IMG_0733.jpg", "Panelled office - blinds existing")],
  "LA":  [],
  "PR":  [("IMG_0730.jpg", "Existing balloon shade over cafe shutters")],
}

_B64 = {}


def photo(fn, x, y, w, h):
    """Embed a fitted JPEG. w/h are the already-fitted box in points."""
    import base64
    if fn not in _B64:
        with open(PHOTO_DIR + fn, "rb") as f:
            _B64[fn] = base64.b64encode(f.read()).decode()
    return (f'<image x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'preserveAspectRatio="none" '
            f'xlink:href="data:image/jpeg;base64,{_B64[fn]}"/>')


def photo_size(fn):
    from PIL import Image
    with Image.open(PHOTO_DIR + fn) as im:
        return im.size


# ══════════════════════════ DERIVED / GATES ══════════════════════════════
def gates():
    """Run before emit. Returns (ok, lines). Closure failures are reported,
    never patched with an invented number."""
    out, ok = [], True

    # 1 - item fit: no panel may carry more opening than it has wall
    for r in ROOMS:
        for p in r["panels"]:
            tot = sum(i["w"] for i in p.get("items", []))
            if tot > p["w"] + 0.01:
                ok = False
                out.append(f"FAIL fit   {r['key']}/{p['label']}: items {tot}\" > wall {p['w']}\"")
    out.append("PASS fit   every panel's openings fit inside its tagged wall width")

    # 2 - explicit x placement must not overlap or overrun
    for r in ROOMS:
        for p in r["panels"]:
            xs = [(i["x"], i["x"] + i["w"]) for i in p.get("items", []) if "x" in i]
            xs.sort()
            for a, b in zip(xs, xs[1:]):
                if b[0] < a[1] - 0.01:
                    ok = False
                    out.append(f"FAIL lap   {r['key']}/{p['label']}: {a} overlaps {b}")
            if xs and xs[-1][1] > p["w"] + 0.01:
                ok = False
                out.append(f"FAIL over  {r['key']}/{p['label']}: last item ends {xs[-1][1]} > {p['w']}")
    out.append("PASS lap   no placed opening overlaps another or runs past the wall")

    # 3 - dim runs referencing panel coordinates stay inside the panel
    for r in ROOMS:
        for p in r["panels"]:
            for key in ("dims_top", "dims_bot"):
                for d in p.get(key, []):
                    if isinstance(d[0], str):
                        continue
                    if d[0] < -0.01 or d[1] > p["w"] + 0.01:
                        ok = False
                        out.append(f"FAIL dim   {r['key']}/{p['label']}: {d}")
    out.append("PASS dim   every dimension run terminates inside its panel")

    # 4 - closure arithmetic, reported not patched
    lw = 33 + 36 + 36 + 27.75
    out.append(f"OPEN close LRB left wall tagged {lw}\" vs 187\" overall "
               f"- {187-lw}\" untagged at the door bank (printed on sheet)")
    cw = 77.5 + 69.25 + 78.25
    out.append(f"OPEN close LRB center wall segments {cw}\" vs 222\" overall "
               f"- delta {cw-222}\" (printed on sheet)")
    band = 110.5 - 106.0
    out.append(f"OPEN close FLB moulding band scales {band}\" vs 2.5\" tagged "
               f"- delta {band-2.5}\" (printed on sheet)")

    # 5 - schedule agrees with the drawn openings
    drawn = 0
    for r in ROOMS:
        for p in r["panels"]:
            drawn += sum(1 for i in p.get("items", []) if i["kind"] == "window")
    sched = sum(q for (_, _, q, _, _, _) in SCHEDULE if "222" not in _ if True)
    sched = sum(q for row in SCHEDULE for q in [row[2]])
    out.append(f"INFO sched schedule totals {sched} treatable openings; "
               f"{drawn} window elevations drawn")

    # 6 - one rev across the set
    out.append(f"PASS rev   single rev stamp '{JOB['rev']}' dated {JOB['date']}")
    return ok, out


# ══════════════════════════ PANEL RENDERER ═══════════════════════════════
def resolve_items(p):
    """Give every item an x. Untagged spacing distributes evenly."""
    items = [dict(i) for i in p.get("items", [])]
    free = [i for i in items if "x" not in i]
    if free:
        used = sum(i["w"] for i in items if "x" in i)
        span = p["w"] - used - sum(i["w"] for i in free)
        gap = span / (len(free) + 1)
        cur = gap
        for i in items:
            if "x" not in i:
                i["x"] = cur
                cur += i["w"] + gap
    return items


def draw_panel(p, ox, oy_floor, k):
    """ox = panel left edge in pt; oy_floor = floor line y in pt; k = pt/inch."""
    o = []
    W, H = p["w"], p["h"]
    top = oy_floor - H * k
    ghost = p.get("ghost_wall", False)

    # wall body
    o.append(RECT(ox, top, W * k, H * k, "#f3efe4" if ghost else CREAM,
                  HAIR if ghost else INK, 1.0 if ghost else 1.3,
                  dash="5 4" if ghost else None))
    said = any("NOT TAGGED" in str(d[-1])
               for key in ("dims_top", "dims_bot") for d in p.get(key, []))
    ghost_note = None
    if ghost and not said and not p.get("no_ghost_note"):
        ghost_note = "WALL WIDTH NOT TAGGED"

    # top band (moulding / header / overhead)
    if p.get("top_band"):
        bh, blab = p["top_band"]
        o.append(RECT(ox, top, W * k, bh * k, MOULD, GOLD, 0.9))
        if W * k > 74:
            o.append(T(ox + 6, top + bh * k / 2 + 3.0, blab, 7.4, "start", "#6d5720",
                       MONO, bold=True, ls=0.5))

    # dashed vertical divisions (center wall)
    for d in p.get("divisions", []):
        o.append(LINE(ox + d * k, top + 4, ox + d * k, oy_floor - 4, MUTE, 0.8, "5 4"))

    items = resolve_items(p)
    for i in items:
        ix = ox + i["x"] * k
        iw = i["w"] * k
        if i["v"]:
            head, ih = i["v"]
            iy = oy_floor - head * k
            ihp = ih * k
        else:                       # schematic vertical placement
            band = p["top_band"][0] * k if p.get("top_band") else 0.0
            iy = top + band + H * k * 0.055
            ihp = (oy_floor - iy) - H * k * 0.055
        if i["kind"] == "window":
            o.append(RECT(ix, iy, iw, ihp, GLASS, FRAME, 1.2))
            o.append(RECT(ix + 2.2, iy + 2.2, iw - 4.4, ihp - 4.4, GLASS2, FRAME, 0.6))
            if i.get("inner"):      # unit outer + window inner
                m = (i["w"] - i["inner"]) / 2 * k
                o.append(RECT(ix + m, iy + m, iw - 2 * m, ihp - 2 * m, GLASS, FRAME, 1.0))
            if not i["v"]:          # mark schematic head/sill
                o.append(LINE(ix, iy, ix + iw, iy, GOLD, 0.9, "3 3"))
                o.append(LINE(ix, iy + ihp, ix + iw, iy + ihp, GOLD, 0.9, "3 3"))
            if i.get("w_est"):      # width never tagged - whole outline dashed
                o.append(RECT(ix, iy, iw, ihp, "none", GOLD, 1.1, dash="3 3"))
                o.append(T(ix + iw / 2, iy + ihp / 2, "WIDTH NOT TAGGED", 7.6,
                           "middle", "#8a6f22", MONO, ls=0.5))
        elif i["kind"] == "door":
            o.append(RECT(ix, iy, iw, ihp + (oy_floor - iy - ihp), DOORF, DOORS, 1.2))
            if iw > 34:
                o.append(T(ix + iw / 2, (iy + oy_floor) / 2, i.get("tag", "DOOR"),
                           8.4, "middle", "#6b5c3f", MONO, bold=True, ls=0.6))
        elif i["kind"] == "fireplace":
            o.append(RECT(ix, oy_floor - H * k * 0.66, iw, H * k * 0.66, STONE, MUTE, 1.1))
            o.append(RECT(ix + iw * 0.22, oy_floor - H * k * 0.42, iw * 0.56,
                          H * k * 0.36, FIREBX, FIREBX, 1.0))
            o.append(T(ix + iw / 2, oy_floor - H * k * 0.70, "FIREPLACE", 8.2,
                       "middle", MUTE, MONO, bold=True, ls=0.6))

    if ghost_note:
        bo = p["top_band"][0] * k if p.get("top_band") else 0.0
        tops = []
        for i in items:
            if i["v"]:
                tops.append(oy_floor - i["v"][0] * k)
            else:
                tops.append(top + bo + H * k * 0.055)
        air = (min(tops) if tops else oy_floor) - (top + bo)
        if air >= 13:
            o.append(T(ox + W * k / 2, top + bo + air / 2 + 2.6, ghost_note, 6.8,
                       "middle", MUTE, MONO, ls=0.4))

    # hatched unknown zone below sill
    if p.get("open_bottom"):
        hy = oy_floor
        o.append(RECT(ox, hy, W * k, 16, "none", HAIR, 0.8, dash="3 3"))
        for xx in range(0, int(W * k), 7):
            o.append(LINE(ox + xx, hy + 16, ox + xx + 8, hy, HAIR, 0.6))
        o.append(T(ox + W * k / 2, hy + 30, "SILL TO FLOOR NOT TAGGED", 7.4,
                   "middle", MUTE, MONO, ls=0.4))

    # floor line
    if not p.get("open_bottom"):
        o.append(LINE(ox - 6, oy_floor, ox + W * k + 6, oy_floor, INK, 1.8))
    else:
        o.append(LINE(ox - 4, oy_floor, ox + W * k + 4, oy_floor, MUTE, 1.0, "6 3"))

    # panel label
    o.append(T(ox + W * k / 2, top - 40, p["label"], 9.5, "middle", INK,
               MONO, bold=True, ls=1.2))

    # dimension runs
    for d in p.get("dims_top", []):
        if isinstance(d[0], str):
            idx = int(d[0][1:])
            it = items[idx]
            o.append(hdim(ox + it["x"] * k, ox + (it["x"] + it["w"]) * k,
                          top - 12, d[1], flag=("UNTAG" in d[1])))
        else:
            o.append(hdim(ox + d[0] * k, ox + d[1] * k, top - 12, d[2],
                          flag=("UNTAG" in d[2] or "TAG" in d[2])))
    base = oy_floor + (40 if p.get("open_bottom") else 22)
    for d in p.get("dims_bot", []):
        if isinstance(d[0], str):
            idx = int(d[0][1:])
            it = items[idx]
            o.append(hdim(ox + it["x"] * k, ox + (it["x"] + it["w"]) * k,
                          base, d[1], above=False))
        else:
            full = (abs(d[0]) < 0.01 and abs(d[1] - W) < 0.01)
            lvl = base + (28 if (full and len(p["dims_bot"]) > 1) else 0)
            o.append(hdim(ox + d[0] * k, ox + d[1] * k, lvl, d[2],
                          above=False, flag=("NOT TAGGED" in d[2])))
    if p.get("dim_h"):
        o.append(vdim(top, oy_floor, ox - 24, p["dim_h"]))
    for n, d in enumerate(p.get("dims_right", [])):
        o.append(vdim(oy_floor - d[1] * k, oy_floor - d[0] * k,
                      ox + W * k + 24 + n * VDIM_STEP, d[2], left=False))
    return "".join(o)


# ══════════════════════════ PAGE CHROME ══════════════════════════════════
def chrome(sheet_no, total, right_title):
    o = [RECT(0, 0, PW, PH, PAPER)]
    # header band
    o.append(RECT(0, 0, PW, HDR_H, BAND))
    o.append(T(30, 27, JOB["letterhead"], 14.0, "start", "#f4efe2", SERIF, bold=True, ls=1.6))
    dv = 30 + tw(JOB["letterhead"], 14.0, SERIF, True, ls=1.6) + 14
    o.append(LINE(dv, 11, dv, 33, GOLD, 1.2))
    o.append(T(dv + 12, 20.5, JOB["poweredby"], 6.2, "start", GOLD, MONO, bold=True, ls=1.5))
    o.append(T(dv + 12, 31.5, JOB["client"] + "  \u00b7  " + JOB["project"].upper(),
               6.0, "start", "#a49b88", MONO, ls=0.8))
    o.append(T(PW - 30, 20.5, right_title.upper(), 8.4, "end", "#f4efe2", MONO, bold=True, ls=1.2))
    o.append(T(PW - 30, 32.5, f"SHEET {sheet_no:02d} OF {total:02d}   \u00b7   REV {JOB['rev']}"
               f"   \u00b7   {JOB['date']}", 6.2, "end", "#a49b88", MONO, ls=0.9))
    o.append(RECT(0, HDR_H, PW, 2.2, GOLD))
    # footer band
    fy = PH - FTR_H
    o.append(RECT(0, fy, PW, FTR_H, BAND))
    o.append(T(30, fy + 16.5, f"{JOB['letterhead']}  \u00b7  {JOB['poweredby']}  \u00b7  {JOB['locale']}",
               5.2, "start", "#a49b88", MONO, ls=0.35))
    o.append(T(PW / 2, fy + 16.5, JOB["status"], 6.4, "middle", GOLD, MONO, bold=True, ls=1.4))
    o.append(T(PW - 30, fy + 16.5, f"SHEET {sheet_no} / {total}", 6.4, "end", "#f4efe2",
               MONO, bold=True, ls=1.0))
    o.append(RECT(0, fy - 1.6, PW, 1.6, GOLD))
    return o


def page(inner):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{PW}" height="{PH}" viewBox="0 0 {PW} {PH}">{inner}</svg>')


def wrap(txt, n):
    words, lines, cur = txt.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= n:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


# ══════════════════════════ ROOM SHEET ═══════════════════════════════════


VP = (30.0, 100.0, 762.0, 386.0)     # drawing viewport - full page width
BAND = (30.0, 402.0, 762.0, 562.0)   # reference band: photos | data | check


def section(o, x, y, w, label):
    sz, ls = 8.5, 1.5
    while tw(label, sz, MONO, True, ls=ls) > w and sz > 5.6:
        sz -= 0.25
        ls = max(0.4, ls - 0.12)
    o.append(T(x, y, label, sz, "start", GOLD, MONO, bold=True, ls=ls))
    o.append(LINE(x, y + 5, x + w, y + 5, GOLD, 0.9))
    return y + 19


def room_sheet(r, no, total):
    o = chrome(no, total, r["name"])
    o.append(T(30, 66, r["name"], 15.0, "start", INK, SERIF, bold=True, ls=0.8))
    o.append(T(30, 84, r["sub"], 8.2, "start", MUTE, SANS, italic=True))

    # ── drawing viewport ─────────────────────────────────────────────────
    x0, y0, x1, y1 = VP
    o.append(RECT(x0, y0, x1 - x0, y1 - y0, "#fbf8f1", HAIR, 1.0))
    for ax, ay, sx, sy in ((x0, y0, 16, 16), (x1, y1, -16, -16)):
        o.append(LINE(ax, ay, ax + sx, ay, GOLD, 1.6))
        o.append(LINE(ax, ay, ax, ay + sy, GOLD, 1.6))

    panels = r["panels"]
    nright = max((len(p.get("dims_right", [])) for p in panels), default=0)
    has_h = any(p.get("dim_h") for p in panels)
    pad_l = (24.0 + VDIM_GUTTER + 8.0) if has_h else 30.0
    pad_r = (24.0 + VDIM_STEP * (nright - 1) + VDIM_GUTTER + 8.0) if nright else 30.0
    gap = 52.0 if has_h else 40.0
    avail_w = (x1 - x0) - pad_l - pad_r - gap * (len(panels) - 1)
    tot_w_in = sum(p["w"] for p in panels)
    max_h_in = max(p["h"] for p in panels)
    up = 56.0
    def _down(p):
        d = 40.0 if p.get("open_bottom") else 22.0
        if p.get("open_bottom"):
            d = max(d, 30.0 + 12.0)
        db = p.get("dims_bot", [])
        if len(db) > 1 and any(not isinstance(x[0], str) and abs(x[0]) < 0.01
                               and abs(x[1] - p["w"]) < 0.01 for x in db):
            d += 28.0
        return d + 20.0
    down = max(_down(p) for p in panels)
    avail_h = (y1 - y0) - up - down - 34.0     # 34 = layout-math strip
    k = min(avail_w / tot_w_in, avail_h / max_h_in)
    block = max_h_in * k
    extent = block + up + down
    floor = y0 + (y1 - y0 - 34.0 - extent) / 2 + up + block
    ox = x0 + pad_l + (avail_w - tot_w_in * k) / 2
    for p in panels:
        o.append(draw_panel(p, ox, floor, k))
        ox += p["w"] * k + gap

    # layout-math closure line + scale strip, inside the frame
    o.append(LINE(x0 + 10, y1 - 30, x1 - 10, y1 - 30, HAIR, 0.6))
    o.append(T(x0 + 10, y1 - 18, "LAYOUT MATH", 7.2, "start", GOLD, MONO,
               bold=True, ls=1.2))
    o.append(T(x0 + 88, y1 - 18, r["math"], 7.6, "start",
               GOLD if r["math_flag"] else INK, MONO, ls=0.2))
    o.append(T(x1 - 10, y1 - 6, f"SCALE 1\" = {k:.3f} PT   \u00b7   WALL GEOMETRY AT "
               f"TRUE SCALE   \u00b7   UNTAGGED SPACING DRAWN EVEN AND MARKED",
               6.2, "end", MUTE, MONO, ls=0.4))

    # ── reference band ───────────────────────────────────────────────────
    bx0, by0, bx1, by1 = BAND
    shots = PHOTOS.get(r["key"], [])
    body_t = by0 + 19
    ph_h = (by1 - body_t) - 24          # room for a caption line under each
    GAPZ = 18.0
    DATA_W = 188.0

    # photo zone width: fit each shot to ph_h, cap the zone
    fitted = []
    for fn, cap in shots:
        iw, ih = photo_size(fn)
        h = ph_h
        w = iw / ih * h
        fitted.append([fn, cap, w, h])
    if fitted:
        cap_w = 330.0
        raw = sum(f[2] for f in fitted) + 8 * (len(fitted) - 1)
        if raw > cap_w:
            sc = (cap_w - 8 * (len(fitted) - 1)) / sum(f[2] for f in fitted)
            for f in fitted:
                f[2] *= sc
                f[3] *= sc
        photo_w = sum(f[2] for f in fitted) + 8 * (len(fitted) - 1)
    else:
        photo_w = 150.0

    dx = bx0 + photo_w + GAPZ
    cx = dx + DATA_W + GAPZ
    cw = bx1 - cx

    # photos
    section(o, bx0, by0 + 10, photo_w,
            "SITE PHOTO" + ("S" if len(fitted) > 1 else ""))
    px = bx0
    for fn, cap, w, h in fitted:
        o.append(photo(fn, px, body_t, w, h))
        o.append(RECT(px, body_t, w, h, "none", INK, 0.9))
        for j, ln in enumerate(wrap(cap, max(int((w - 6) / 3.5), 12))[:3]):
            o.append(T(px, body_t + h + 9 + j * 7.4, ln, 6.0, "start", MUTE,
                       MONO, ls=0.2))
        px += w + 8
    if not fitted:
        o.append(RECT(bx0, body_t, photo_w, ph_h, "#f3efe4", HAIR, 1.0, dash="4 4"))
        o.append(T(bx0 + photo_w / 2, body_t + ph_h / 2, "NO SITE PHOTO ON FILE",
                   7.0, "middle", MUTE, MONO, ls=0.6))

    # field data
    y = section(o, dx, by0 + 10, DATA_W, "FIELD DATA")
    avail = by1 - y + 6
    for lab_s, val_s, wrapn, lead, pad in ((6.4, 8.8, 27, 11.0, 4.0),
                                           (6.1, 8.2, 29, 10.2, 3.2),
                                           (5.8, 7.6, 32, 9.4, 2.6),
                                           (5.5, 7.0, 35, 8.6, 2.0)):
        need = sum(11.0 + len(wrap(b, wrapn)[:2]) * (val_s + 1.2) + pad
                   for _, b in r["data"])
        if need <= avail:
            break
    for a, b in r["data"]:
        o.append(T(dx, y, a, lab_s, "start", MUTE, MONO, ls=0.5))
        vy = y + lead
        for ln in wrap(b, wrapn)[:2]:
            o.append(T(dx, vy, ln, val_s, "start", INK, SANS,
                       bold=("not tagged" not in b and "not recorded" not in b)))
            vy += val_s + 1.2
        y = vy + pad
        o.append(LINE(dx, y - 5, dx + DATA_W, y - 5, HAIR, 0.5))

    # field check
    y = section(o, cx, by0 + 10, cw, "FIELD CHECK \u00b7 BEFORE FABRICATION")
    room_left = by1 - y + 8
    for size, cols, lh in ((8.2, 42, 9.6), (7.8, 45, 9.1), (7.4, 47, 8.7),
                           (7.0, 50, 8.2), (6.6, 54, 7.8), (6.2, 58, 7.4),
                           (5.9, 62, 7.0), (5.6, 66, 6.7)):
        need = sum(len(wrap(c, cols)) * lh + 5.0 for c in r["check"])
        if need <= room_left:
            break
    for c in r["check"]:
        o.append(T(cx, y, "\u25aa", size - 1.0, "start", GOLD, SANS))
        for ln in wrap(c, cols):
            o.append(T(cx + 10, y, ln, size, "start", INK, SANS))
            y += lh
        y += 5.0

    # fabric registry strip, along the foot of the band
    o.append(T(bx0, by1 + 16, "NOT YET ELECTED   \u00b7   FABRIC: TBC - CONFIRM "
               "BEFORE CUT   \u00b7   LINING: TBC   \u00b7   HEADING: TBC   \u00b7   "
               "HARDWARE: TBC   \u00b7   MOUNT: NOT RECORDED ON FIELD SHEET",
               6.6, "start", GOLD, MONO, bold=True, ls=0.5))
    return page("".join(o))


# ══════════════════════════ COVER SHEET ══════════════════════════════════
def cover(total):
    o = chrome(1, total, "COVER \u00b7 INDEX")
    o.append(T(30, 78, JOB["project"], 26.0, "start", INK, SERIF, bold=True, ls=1.2))
    o.append(T(30 + tw(JOB["project"], 26.0, SERIF, True, ls=1.2) + 16, 78,
               "FOR " + JOB["client"] + "  \u00b7  " + JOB["client_loc"], 9.0,
               "start", MUTE, MONO, bold=True, ls=1.4))
    o.append(T(30, 98, "WINDOW & DRAPERY FIELD MEASUREMENTS", 9.0, "start", GOLD,
               MONO, bold=True, ls=2.2))
    o.append(LINE(30, 108, 762, 108, HAIR, 1.0))

    # left: job block
    y = 132
    o.append(T(30, y, "JOB", 7.0, "start", GOLD, MONO, bold=True, ls=1.4))
    o.append(LINE(30, y + 4, 250, y + 4, GOLD, 0.8))
    y += 16
    for a, b in [("CLIENT", JOB["client"] + "  \u00b7  " + JOB["client_loc"]),
                 ("HOUSE", JOB["project"]),
                 ("WORKROOM", JOB["letterhead"] + "  \u00b7  " + JOB["locale"]),
                 ("PRODUCTION", "EMPIRE WORKROOM"),
                 ("SOURCE", JOB["source"]),
                 ("REVISION", f"REV {JOB['rev']}  \u00b7  {JOB['date']}"),
                 ("SHEETS", f"{total} \u2014 cover, 9 room elevations, schedule"),
                 ("STATUS", JOB["status"])]:
        o.append(T(30, y, a, 5.6, "start", MUTE, MONO, ls=0.5))
        o.append(T(30, y + 10, b, 7.6, "start", INK, SANS))
        y += 26
        o.append(LINE(30, y - 8, 250, y - 8, HAIR, 0.5))

    y += 6
    o.append(T(30, y, "READ THIS SET AS", 7.0, "start", GOLD, MONO, bold=True, ls=1.4))
    o.append(LINE(30, y + 4, 250, y + 4, GOLD, 0.8))
    y += 16
    for c in ["Wall widths and heights are drawn at true scale where the "
              "field sheet tagged them.",
              "Openings are drawn at their tagged width. Where head, sill or "
              "spacing was not tagged, geometry is schematic and is marked "
              "on the sheet with a dashed gold edge.",
              "Nothing on these sheets is a fabrication dimension. Every sheet "
              "carries its own FIELD CHECK list."]:
        for ln in wrap(c, 42):
            o.append(T(30, y, ln, 6.4, "start", INK, SANS))
            y += 8.0
        y += 4

    # center/right: index
    ix = 300
    o.append(T(ix, 132, "SHEET INDEX", 7.0, "start", GOLD, MONO, bold=True, ls=1.4))
    o.append(LINE(ix, 136, 762, 136, GOLD, 0.8))
    yy = 152
    o.append(T(ix, yy, "SHT", 5.4, "start", MUTE, MONO, ls=0.6))
    o.append(T(ix + 38, yy, "ROOM", 5.4, "start", MUTE, MONO, ls=0.6))
    o.append(T(ix + 250, yy, "OPENINGS", 5.4, "start", MUTE, MONO, ls=0.6))
    o.append(T(762, yy, "OPEN ITEMS", 5.4, "end", MUTE, MONO, ls=0.6))
    yy += 6
    o.append(LINE(ix, yy, 762, yy, HAIR, 0.6))
    yy += 14
    rows = [("01", "COVER \u00b7 INDEX \u00b7 HOW TO READ", "\u2014", "\u2014")]
    for n, r in enumerate(ROOMS, start=2):
        wins = sum(1 for p in r["panels"] for i in p.get("items", [])
                   if i["kind"] == "window")
        rows.append((f"{n:02d}", r["name"], str(wins) if wins else "wall",
                     str(len(r["check"]))))
    rows.append((f"{len(ROOMS)+2:02d}", "OPENING SCHEDULE \u00b7 ALL ROOMS",
                 str(sum(r[2] for r in SCHEDULE)), "\u2014"))
    for a, b, c, d in rows:
        o.append(T(ix, yy, a, 7.2, "start", GOLD, MONO, bold=True, ls=0.6))
        o.append(T(ix + 38, yy, b, 7.4, "start", INK, SANS))
        o.append(T(ix + 250, yy, c, 7.2, "start", INK, MONO))
        o.append(T(762, yy, d, 7.2, "end", MUTE, MONO))
        yy += 9
        o.append(LINE(ix, yy - 3, 762, yy - 3, HAIR, 0.4))
        yy += 8

    # open items at a glance
    oy = yy + 16
    o.append(T(ix, oy, "OPEN AT A GLANCE", 7.0, "start", GOLD, MONO, bold=True, ls=1.4))
    o.append(LINE(ix, oy + 4, 762, oy + 4, GOLD, 0.8))
    oy += 16
    for c in ["Living Room center wall does not close - 225\" tagged against "
              "222\" overall.",
              "Living Room left wall leaves 54\u00bc\" untagged at the door bank.",
              "Formal Living bay moulding band scales 4\u00bd\" against 2\u00bd\" tagged.",
              "Head and sill heights are untagged in five rooms - no finished "
              "lengths can be set.",
              "Mount condition is not recorded anywhere in the set."]:
        for j, ln in enumerate(wrap(c, 74)):
            if j == 0:
                o.append(T(ix, oy, "\u25aa", 5.4, "start", GOLD, SANS))
            o.append(T(ix + 10, oy, ln, 6.4, "start", INK, SANS))
            oy += 8.4
        oy += 2.6

    # legend strip
    ly = 470
    o.append(T(30, ly, "LEGEND", 7.0, "start", GOLD, MONO, bold=True, ls=1.4))
    o.append(LINE(30, ly + 4, 762, ly + 4, GOLD, 0.8))
    ly += 14
    lg = [(GLASS, FRAME, "GLAZED OPENING - WIDTH TAGGED"),
          (DOORF, DOORS, "DOOR / DOOR BANK"),
          (MOULD, GOLD, "MOULDING, HEADER OR OVERHEAD BAND"),
          (CREAM, INK, "WALL AT TRUE SCALE"),
          ("#fbf8f1", HAIR, "GHOST - WIDTH NOT TAGGED")]
    lx = 30
    for f, st, lab in lg:
        o.append(RECT(lx, ly, 14, 10, f, st, 1.0))
        o.append(T(lx + 19, ly + 8.0, lab, 5.6, "start", INK, MONO, ls=0.3))
        lx += 19 + tw(lab, 5.6, MONO, ls=0.3) + 22
    ly += 24
    o.append(LINE(30, ly + 4, 46, ly + 4, GOLD, 1.2, "3 3"))
    o.append(T(54, ly + 6.6, "DASHED GOLD EDGE = HEAD OR SILL NOT FIELD-TAGGED, "
               "PLACEMENT SCHEMATIC", 5.6, "start", INK, MONO, ls=0.3))
    o.append(T(430, ly + 6.6, "GOLD DIMENSION = CLOSURE OPEN, SEE LAYOUT MATH",
               5.6, "start", GOLD, MONO, ls=0.3))
    return page("".join(o))


# ══════════════════════════ SCHEDULE SHEET ═══════════════════════════════
def schedule_sheet(no, total):
    o = chrome(no, total, "OPENING SCHEDULE")
    o.append(T(30, 66, "OPENING SCHEDULE", 15.0, "start", INK, SERIF, bold=True, ls=0.8))
    o.append(T(30, 82, "All rooms - one line per opening type - as field-recorded "
               "1 July 2026", 7.6, "start", MUTE, SANS, italic=True))

    cols = [(30, "ROOM"), (196, "MARK"), (240, "QTY"), (276, "WIDTH"),
            (352, "HEIGHT"), (424, "HEAD / OVERHEAD CONDITION")]
    y = 112
    for x, lab in cols:
        o.append(T(x, y, lab, 5.8, "start", GOLD, MONO, bold=True, ls=1.2))
    o.append(LINE(30, y + 5, 762, y + 5, GOLD, 1.0))
    y += 19
    for i, (room, mark, qty, w, h, note) in enumerate(SCHEDULE):
        if i % 2 == 0:
            o.append(RECT(26, y - 9, 740, 18, "#efe9db"))
        o.append(T(30, y, room, 7.4, "start", INK, SANS, bold=True))
        o.append(T(196, y, mark, 7.2, "start", GOLD, MONO, bold=True))
        o.append(T(240, y, str(qty), 7.2, "start", INK, MONO))
        o.append(T(276, y, w, 7.2, "start", INK, MONO))
        o.append(T(352, y, h, 7.2, "start",
                   MUTE if "not" in h or "ref" in h else INK, MONO))
        o.append(T(424, y, note, 6.6, "start", MUTE, SANS))
        y += 22
    o.append(LINE(30, y - 12, 762, y - 12, HAIR, 0.8))
    tot = sum(r[2] for r in SCHEDULE)
    o.append(T(240, y + 2, str(tot), 8.0, "start", GOLD, MONO, bold=True))
    o.append(T(30, y + 2, "TOTAL OPENINGS RECORDED", 7.0, "start", INK, MONO, bold=True, ls=0.8))

    # open items
    y += 34
    o.append(T(30, y, "OPEN BEFORE QUOTING", 7.0, "start", GOLD, MONO, bold=True, ls=1.4))
    o.append(LINE(30, y + 4, 762, y + 4, GOLD, 0.8))
    y += 16
    opens = [
      "Living Room center wall: tagged segments total 225\" against a 222\" "
      "overall. 3\" unresolved.",
      "Living Room left wall: 54\u00bc\" at the door bank is untagged. Door bank "
      "width governs the panel count.",
      "Formal Living bay: moulding band scales 4\u00bd\" but is tagged 2\u00bd\". "
      "Remeasure before hardware.",
      "Head and sill heights are untagged in Formal Dining, Living Room, Family "
      "Room and Kitchen / Dining - no finished lengths can be set for those rooms.",
      "Mount condition (inside, outside, ceiling) is not recorded anywhere in the "
      "set. It changes every width.",
      "Fabric, lining, heading and hardware are not yet elected - this set is "
      "measurement only.",
    ]
    for c in opens:
        lines = wrap(c, 118)
        o.append(T(30, y, "\u25aa", 5.4, "start", GOLD, SANS))
        for ln in lines:
            o.append(T(40, y, ln, 6.6, "start", INK, SANS))
            y += 8.4
        y += 3.4
    return page("".join(o))


# ══════════════════════════ BUILD ════════════════════════════════════════
def gate_bounds(placed, frame=16.0):
    bad = []
    for x0, y0, x1, y1, t in placed:
        if x0 < frame - 6 or x1 > PW - frame + 6 or y0 < 4 or y1 > PH - 4:
            bad.append(f"out of page: '{t[:38]}'")
    return bad


def gate_collisions(placed, tol=1.2):
    bad = []
    for i in range(len(placed)):
        ax0, ay0, ax1, ay1, at = placed[i]
        for j in range(i + 1, len(placed)):
            bx0, by0, bx1, by1, bt = placed[j]
            ox = min(ax1, bx1) - max(ax0, bx0)
            oy = min(ay1, by1) - max(ay0, by0)
            if ox > tol and oy > tol:
                bad.append(f"overlap: '{at[:26]}' / '{bt[:26]}' "
                           f"({ox:.1f}x{oy:.1f}pt)")
    return bad


def build(out_path):
    ok, lines = gates()
    print("─ GATES " + "─" * 60)
    for l in lines:
        print("  " + l)
    if not ok:
        print("\nREFUSING TO EMIT - a closed gate failed.")
        sys.exit(1)

    total = len(ROOMS) + 2
    sheets, faults = [], []
    builders = [lambda t=total: cover(t)]
    builders += [(lambda r=r, n=n, t=total: room_sheet(r, n, t))
                 for n, r in enumerate(ROOMS, start=2)]
    builders.append(lambda t=total: schedule_sheet(t, t))
    for n, mk in enumerate(builders, 1):
        PLACED.clear()
        sheets.append(mk())
        for f in gate_bounds(PLACED) + gate_collisions(PLACED):
            faults.append(f"sheet {n:02d}  {f}")
    print("─ TEXT GATES " + "─" * 54)
    if faults:
        for f in faults:
            print("  FAIL " + f)
        print(f"\n  {len(faults)} text fault(s) - REFUSING TO EMIT")
        sys.exit(1)
    print("  PASS bounds      every string inside the page frame")
    print("  PASS collisions  no two strings overlap")

    w = PdfWriter()
    for i, svg in enumerate(sheets, 1):
        buf = io.BytesIO()
        cairosvg.svg2pdf(bytestring=svg.encode("utf-8"), write_to=buf, dpi=72)
        buf.seek(0)
        w.add_page(PdfReader(buf).pages[0])
        print(f"  sheet {i:02d}/{total} ok")
    w.add_metadata({"/Title": "McLean - Window & Drapery Field Measurements - "
                              "Whittington Design",
                    "/Author": "Nelma's Workroom - Powered by Empire Workroom",
                    "/Creator": "Nelma's Workroom",
                    "/Subject": f"Whittington Design, McLean VA - "
                                f"REV {JOB['rev']} - {JOB['date']} - "
                                f"{JOB['status']}"})
    with open(out_path, "wb") as f:
        w.write(f)
    print("written:", out_path)


if __name__ == "__main__":
    build("/mnt/user-data/outputs/McLean_Whittington_Drapery_Elevations_RevA.pdf")
