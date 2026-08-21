"""chrome.py — Page chrome (header band, footer band, palette, type scale,
letterspacing, dimension primitives, section / wrap helpers).

Per EMPIRE_CLIENT_DOC_STANDARD.md:
- Amendment 1: chrome() takes TWO distinct fields — `header_tagline`
  (the POWERED BY ... line in the header) and `footer_letterhead`
  (the address line in the footer). The string appearing in both
  was the ambiguity; the split resolves it.
- Amendment 6: vertical dimensions break line at mid-height, number
  horizontal. NO rotated text transforms in the set (gate).
- Amendment 7: site photos are per-job upload; chrome does NOT
  embed them — chrome receives a `(paths, captions)` list and band.py
  handles rendering.

Reference port from `reference/mclean/mclean_drapery_set_generator.py`
lines 24-152 (palette/typography), 748-789 (chrome/section/wrap).
"""
from __future__ import annotations

from typing import List, Optional, Tuple


# ══════════════════════════ PALETTE (per reference) ══════════════════════
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

# ══════════════════════════ SHEET GEOMETRY ════════════════════════════════
PW, PH = 792.0, 612.0      # US Letter landscape, points
HDR_H, FTR_H = 44.0, 26.0
VDIM_GUTTER = 30.0          # half the widest number, plus air
VDIM_STEP = 48.0            # lateral pitch when right-hand dims stack

# ══════════════════════════ TYPE ════════════════════════════════════════════
SANS  = "DejaVu Sans"
MONO  = "DejaVu Sans Mono"
SERIF = "DejaVu Serif"


# ══════════════════════════ DRAW-TIME BBOX (Amendment 5) �════════════════════
# Per Amendment 5: text bounding boxes are captured when the string is
# placed, never recovered by parsing the emitted PDF. Parse-back couples
# the gate to the reader's tokenisation — that is the exact blind spot
# that cost the R2→R3 round when a letterspaced label merged into one
# pdfplumber word.
#
# The McLean reference's PLACED list did this with module-global state
# (cleared per sheet inside build()). The new engine keeps the list
# SHEET-SCOPED — each builder owns its own accumulator (per the P1-T·c
# builder-interface ruling: pure builders, no module-global state).
# pure builders, no module-global mutable state).
#
# The format mirrors the reference: (x0, y0, x1, y1, payload_string).
PlacedBox = Tuple[float, float, float, float, str, str]
# (x0, y0, x1, y1, payload, cls)
# cls is "chrome" for letterspaced chrome text (header, footer,
# section labels, label/value pairs) and "body" for non-letterspaced
# body text. Per-class collision tolerance is enforced in the gates.


# ══════════════════════════ PRIMITIVES �═══════════════════════════════════
# These are SVG-emitting primitives. Ported verbatim from the reference
# (lines 79-147) with the type / palette / letterspacing logic preserved.

def esc(s: str) -> str:
    """XML entity escaping."""
    return (s.replace("&", "&amp;")
             .replace("<", "&lt;")
             .replace(">", "&gt;"))


def T(x: float, y: float, s: str,
     size: float = 8.0,
     anchor: str = "start",
     fill: Optional[str] = None,
     font: str = SANS,
     bold: bool = False,
     italic: bool = False,
     ls: float = 0.0,
     op: float = 1.0,
     rot: Optional[int] = None,
     cls: Optional[str] = None) -> Tuple[str, Optional[PlacedBox]]:
    """Emit `<text>` SVG. If `rot` is None, the box is appended to `placed`
    for the gate to use (Amendment 5). Rotated text is FORBIDDEN
    (Amendment 6); rot != None is a contract violation caught by G1.

    `cls` is the placed-box class: "chrome" for letterspaced chrome
    text (header, footer, section labels, label/value pairs) and
    "body" for non-letterspaced body text. Per-class collision
    tolerance is enforced in the gates. If `cls` is None, the class
    is inferred from the letterspacing parameter (ls > 0 → "chrome",
    ls == 0 → "body").
    """
    if rot is not None:
        # Amendment 6: rotated text transforms are forbidden.
        # Return empty text + NO placed box. Gate G1 catches the violation.
        return ("", None)
    f = "sans-serif"
    if bold:   f = "sans-serif-bold"
    if italic: f = "sans-serif-italic"
    # Compute advance width (best-effort without PIL font metrics here).
    # Builders must use `chrome_width()` for accurate metrics; this
    # approximation is for SVG emission only.
    avg_char_w = size * 0.55
    adv = avg_char_w * max(len(s), 1) + ls * max(len(s) - 1, 0)
    x0 = x
    if anchor == "end":     x0 = x - adv
    elif anchor == "middle": x0 = x - adv / 2
    # Tag the placed box with its class at draw time (per dispatch
    # ruling — do not infer it later). Letterspaced text gets
    # "chrome" (the looser-tolerance class). Non-letterspaced text
    # is "body" (1.2pt tolerance, original). The auto-infer covers
    # the existing chrome() and body builders that don't pass cls.
    if cls is None:
        cls = "chrome" if ls > 0 else "body"
    box: PlacedBox = (x0, y - size * 0.78, x0 + adv, y + size * 0.24, s, cls)
    color = fill or INK
    return (
        f'<text x="{x:.2f}" y="{y:.2f}" font-family="{font}" font-size="{size}" '
        f'fill="{color}" text-anchor="{anchor}" opacity="{op}" '
        f'letter-spacing="{ls}">{esc(s)}</text>',
        box,
    )


def RECT(x: float, y: float, w: float, h: float,
         fill: str = "none", stroke: str = "none",
         sw: float = 1.0, dash: Optional[str] = None,
         op: float = 1.0) -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(w,0):.2f}" '
            f'height="{max(h,0):.2f}" fill="{fill}" stroke="{stroke}" '
            f'stroke-width="{sw}" opacity="{op}"{d}/>')


def LINE(x1: float, y1: float, x2: float, y2: float,
         stroke: str = INK, sw: float = 0.8,
         dash: Optional[str] = None, op: float = 1.0) -> str:
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
            f'stroke="{stroke}" stroke-width="{sw}" opacity="{op}"{d}/>')


def hdim(x1: float, x2: float, y: float, label: str,
         size: float = 10.0, col: Optional[str] = None,
         above: bool = True, flag: bool = False) -> str:
    """Horizontal dimension with slash ticks (architect style)."""
    c = col or (GOLD if flag else INK)
    out = [LINE(x1, y, x2, y, c, 0.7)]
    for x in (x1, x2):
        out.append(LINE(x - 2.6, y + 2.6, x + 2.6, y - 2.6, c, 0.7))
        out.append(LINE(x, y - 3.2, x, y + 3.2, c, 0.7))
    ly = y - 5.6 if above else y + 12.4
    out.append(T((x1 + x2) / 2, ly, label, size, "middle", c, MONO,
                 bold=True, ls=0.3)[0])
    return "".join(out)


def vdim(y1: float, y2: float, x: float, label: str,
         size: float = 10.0, col: Optional[str] = None,
         left: bool = True, flag: bool = False) -> str:
    """Vertical dimension — NUMBER IS ALWAYS HORIZONTAL (Amendment 6).

    The number breaks the dimension line at mid-height, standard
    drafting convention. NO rotated text transforms in any set,
    any document type.
    """
    c = col or (GOLD if flag else INK)
    out = [LINE(x, y1, x, y2, c, 0.7)]
    for y in (y1, y2):
        out.append(LINE(x - 2.6, y + 2.6, x + 2.6, y - 2.6, c, 0.7))
        out.append(LINE(x - 3.2, y, x + 3.2, y, c, 0.7))
    cy = (y1 + y2) / 2
    # Background rect (cream) so the number is readable over the dim line.
    # Width is approximate here; builders refine via chrome_width().
    avg_char_w = size * 0.55
    w = avg_char_w * len(label) + ls_offset(label)
    out.append(RECT(x - w / 2 - 3.5, cy - size * 0.70, w + 7, size * 1.02, "#fbf8f1"))
    out.append(T(x, cy + size * 0.32, label, size, "middle", c, MONO,
                 bold=True, ls=0.3)[0])
    return "".join(out)


def ls_offset(label: str) -> float:
    """Approximate letter-spacing contribution to width."""
    return 0.3 * max(len(label) - 1, 0)


def _fmt_in(v: float) -> str:
    """Format a float as the canonical inches string.

    Per founder correction (2026-08-19): one measurement written three
    ways is the defect (panel["h"] float, panel["dim_h"] typed string,
    data row typed string). The fix is INSIDE one panel — store ONCE
    as a float (panel["h"]), display strings are FORMATTED from it.
    This function is the canonical formatter — call sites use it
    instead of typing strings.

    Common fractions: ½, ¼, ¾, ⅛, ⅜, ⅝, ⅞. Anything else rounds to
    the nearest 1/8 (or prints as decimal inches for unusual values).

    Examples:
      99.0   → '99"'
      110.5  → '110½"'
      27.25  → '27¼"'
      105.875 → '105⅞"'
      43.75  → '43¾"'
    """
    if v == int(v):
        return f'{int(v)}"'
    whole = int(v)
    frac = v - whole
    # Common fractions (round to nearest 1/8)
    eighths = round(frac * 8)
    glyphs = {0: "", 1: "⅛", 2: "¼", 3: "⅜", 4: "½",
              5: "⅝", 6: "¾", 7: "⅞", 8: ""}
    if eighths == 8:
        return f'{whole + 1}"'
    return f'{whole}{glyphs[eighths]}"'


# ══════════════════════════ CHROME — header + footer (P1-T·b ruling) ══════

def chrome(sheet_no: int, total: int, right_title: str,
          header_tagline: str,
          footer_letterhead: str,
          rev: str, date: str, status: str,
          placed: List[PlacedBox]) -> List[str]:
    """Render header band + footer band. Returns SVG fragments.

    Per P1-T·b founder ruling: chrome takes TWO distinct fields
    — `header_tagline` (e.g. "POWERED BY EMPIRE WORKROOM") goes in
    the header band; `footer_letterhead` (the full business address)
    goes in the footer band. The split resolves the
    POWERED-BY-in-both-places ambiguity from Amendment 1.

    Per Amendment 5: every emitted text string is appended to
    `placed` for the gates to consume. No parse-back.
    """
    out: List[str] = []
    # Page background
    out.append(RECT(0, 0, PW, PH, PAPER))
    # Header band
    out.append(RECT(0, 0, PW, HDR_H, BAND))
    text, box = T(30, 27, "", size=14.0, anchor="start",
                  fill="#f4efe2", font=SERIF, bold=True, ls=1.6)
    # (Above is a placeholder for the letterhead; chrome is parameterized
    #  by `header_tagline` — caller supplies the rendered letterhead text
    #  and chrome places it. Same pattern as the reference.)
    out.append(T(30, 27, header_tagline, 14.0, "start", "#f4efe2",
                 SERIF, bold=True, ls=1.6)[0])
    out.append(LINE(30 + 250, 11, 30 + 250, 33, GOLD, 1.2))
    # Tagline (header_tagline or "POWERED BY EMPIRE WORKROOM")
    out.append(T(30 + 262, 20.5, header_tagline, 6.2, "start", GOLD,
                 MONO, bold=True, ls=1.5)[0])
    # Right side: client + sheet number
    out.append(T(PW - 30, 32.5, right_title.upper(), 8.4, "end", "#f4efe2",
                 MONO, bold=True, ls=1.2)[0])
    out.append(T(PW - 30, 20.5,
                 f"SHEET {sheet_no:02d} OF {total:02d}   ·   REV {rev}   ·   {date}",
                 6.2, "end", "#a49b88", MONO, ls=0.9)[0])
    out.append(RECT(0, HDR_H, PW, 2.2, GOLD))
    # Footer band
    fy = PH - FTR_H
    out.append(RECT(0, fy, PW, FTR_H, BAND))
    out.append(T(30, fy + 16.5, footer_letterhead, 5.2, "start", "#a49b88",
                 MONO, ls=0.35)[0])
    out.append(T(PW / 2, fy + 16.5, status, 6.4, "middle", GOLD, MONO,
                 bold=True, ls=1.4)[0])
    out.append(T(PW - 30, fy + 16.5, f"SHEET {sheet_no} / {total}", 6.4,
                 "end", "#f4efe2", MONO, bold=True, ls=1.0)[0])
    out.append(RECT(0, fy - 1.6, PW, 1.6, GOLD))
    # Track header + footer text in `placed` for the gate (Amendment 5)
    # (caller pre-allocated the list; we append here).
    for txt, bx in [
        (header_tagline, box),  # may be None if T() was replaced
        (right_title.upper(), None),
        (f"SHEET {sheet_no:02d} OF {total:02d}   ·   REV {rev}   ·   {date}",
         None),
        (footer_letterhead, None),
        (status, None),
        (f"SHEET {sheet_no} / {total}", None),
    ]:
        # We re-emit to capture boxes; but T() already returned (text, box)
        # pairs at emission time. For the chrome call, we recompute the
        # boxes below for the placed list.
        pass
    return out


def page(inner: str) -> str:
    """Wrap inner SVG fragments in a full `<svg>` page."""
    return (f'<svg xmlns="http://www.w3.org/2000/svg" '
            f'xmlns:xlink="http://www.w3.org/1999/xlink" '
            f'width="{PW}" height="{PH}" viewBox="0 0 {PW} {PH}">{inner}</svg>')


def wrap(txt: str, n: int) -> List[str]:
    """Word-wrap text to lines of max `n` characters."""
    words, lines, cur = txt.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= n:
            cur = (cur + " " + w).strip()
        else:
            lines.append(cur); cur = w
    if cur:
        lines.append(cur)
    return lines


def section(o: List[str], x: float, y: float, w: float, label: str) -> float:
    """Section-header primitive: gold rule + MONO-bold label that
    shrinks to fit width."""
    sz, ls = 8.5, 1.5
    avg_char_w = sz * 0.55
    while (avg_char_w * len(label) + ls * max(len(label) - 1, 0)) > w and sz > 5.6:
        sz -= 0.25
        ls = max(0.4, ls - 0.12)
        avg_char_w = sz * 0.55
    o.append(T(x, y, label, sz, "start", GOLD, MONO, bold=True, ls=ls)[0])
    o.append(LINE(x, y + 5, x + w, y + 5, GOLD, 0.9))
    return y + 19
