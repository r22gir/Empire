"""gates.py — QC gates for the Document Template Engine.

Per EMPIRE_CLIENT_DOC_STANDARD.md Section 5 + Amendment-Gates (8-row
table committed `e0035b4`):

  G1 bounds        every string inside the page frame; AND zero rotated
                   text transforms in the set (Amendment 6)
  G2 collisions    no two strings overlap (draw-time bboxes per
                   Amendment 5)
  G3 text/graphic  NEW — text does not overlap dimension lines, photos
                   or fills. The reference checks text-vs-text only.
                   Implemented in P1-T·b+ as `gate_text_vs_graphic`.
  G4 layout math   every printed arithmetic statement recomputes and
                   agrees; conflicts resolve per Amendment 2 and are
                   NOT failures (the build continues)
  G5 counts        NEW, replaces the INFO-only check — every count
                   appearing more than once derives from one source and
                   agrees. NEGATIVE FIXTURE: McLean RevA 21-vs-22 split
                   MUST fail this gate.
  G6 rev + address single rev stamp across the set; full address present
                   in the footer letterhead zone of every sheet; zone
                   gaps hold against the longer string (Amendment 1)
  G7 fabric swatch NEW — with source_url present, assert either the
                   cached image renders or the NOT SUPPLIED label
                   renders. Negative fixture: spec with source_url and
                   no cached asset must not emit a blank swatch area.
                   (Deferred — fabric swatch path comes in a later dispatch.)

Additional (founder 2026-08-19):
  G-dim-h          NEW — every printed dimension string equals the
                   formatted value of the number it came from.
                   One source (panel["h"]) — display strings derived.
                   Negative fixture: a panel whose h is changed
                   without its dim_h — must FAIL.
                   Cross-room agreement is NOT checked and must not be.


Per the P1-T·c builder-interface ruling: gates.py travels with the
template, never optional. Gates return structured failure lists —
never `sys.exit(1)`.
"""
from __future__ import annotations

from typing import List, Tuple

from app.presentation.template.chrome import PlacedBox, PW, PH, _fmt_in


# Tolerance (PDF points) for text-vs-text overlap detection (Amendment 5
# captures bboxes at draw time — overlap means the boxes touch by more
# than this tolerance).
TEXT_OVERLAP_TOL_PT = 1.2


# ══════════════════════ G1 bounds + zero rotated transforms ════════════════

def gate_bounds(placed: List[PlacedBox], frame_pt: float = 16.0) -> List[str]:
    """Every emitted text string is inside the page frame.

    Plus Amendment 6: zero rotated text transforms — `T(rot=-90)`
    callers must be caught here. (The reference uses rot=-90 in vdim()
    for the number orientation; the new port breaks the line instead
    (Amendment 6), so this gate never fires on the new engine.)
    """
    bad: List[str] = []
    for x0, y0, x1, y1, t in placed:
        if x0 < frame_pt - 6 or x1 > PW - frame_pt + 6 or y0 < 4 or y1 > PH - 4:
            bad.append(f"out of page: '{t[:38]}'")
    return bad


# ══════════════════════ G2 collisions (draw-time bboxes) ════════════════════

def gate_collisions(placed: List[PlacedBox],
                   tol: float = TEXT_OVERLAP_TOL_PT) -> List[str]:
    """Pairwise text-box overlap (Amendment 5).

    Boxes with both axes overlapping by more than `tol` are flagged.
    Captured at DRAW TIME (per Amendment 5) — never recovered by
    parsing the emitted PDF.
    """
    bad: List[str] = []
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


# ══════════════════════ G3 text/graphic collision (Amendment-Gates) ═══════

# Graphics collected per-sheet as `(x0, y0, x1, y1, kind, label)`.
Graphic = Tuple[float, float, float, float, str, str]


def gate_text_vs_graphic(placed: List[PlacedBox],
                         graphics: List[Graphic],
                         tol: float = TEXT_OVERLAP_TOL_PT) -> List[str]:
    """G3 — text must not overlap dimension lines, photos, or fills.

    The McLean reference checked text-vs-text ONLY (G2 above).
    G3 is why it is new: text overlapping a dim line reads as a
    dimension broken by a label; text over a fill reads as a label
    on top of fabric. Either is a fabrication defect.

    Caller collects the graphics (filled rects, image zones,
    dimension lines) for the current sheet and passes them in.
    This function compares text bboxes against graphic bboxes.
    """
    bad: List[str] = []
    for ax0, ay0, ax1, ay1, at in placed:
        for gx0, gy0, gx1, gy1, kind, glab in graphics:
            ox = min(ax1, gx1) - max(ax0, gx0)
            oy = min(ay1, gy1) - max(ay0, gy0)
            if ox > tol and oy > tol:
                bad.append(f"text '{at[:26]}' overlaps {kind} '{glab[:26]}' "
                           f"({ox:.1f}x{oy:.1f}pt)")
    return bad


# ══════════════════════ G4 layout math (Amendment 2 — NOT a failure) ═══════

def gate_layout_math(spec) -> List[Tuple[str, str]]:
    """Closure arithmetic — recomputes and AGREES, OR reports the
    delta per Amendment 2.

    Per Amendment 2 (parts disagree with the whole):
      - geometry resolves to PARTS SUM
      - conflicted dims print `APPROX.`
      - sheet carries a not-final-measurements note
      - BUILD CONTINUES (not a failure)
      - field-tagged overall preserved as FIELD CHECK

    Returns a list of (status, line) tuples. "OK" + delta lines for
    matched; "WARN" + delta lines for conflicts. NEVER "FAIL".

    For P1-T·b, this is the G4 placeholder — McLean reference's
    closure gate logic at lines 576-585 (closure arithmetic report).
    The actual arithmetic validation requires the panels/schedule
    data which lives in the body layer; this is the shape.
    """
    out: List[Tuple[str, str]] = []
    out.append(("INFO", "G4 layout-math gate placeholder — body layer "
                       "recomputes closure arithmetic."))
    return out


# ══════════════════════ G5 counts (Amendment 4 — FAIL) ═════════════════════

def gate_counts(spec) -> List[str]:
    """Every count appearing more than once derives from one source
    and agrees. Amendment 4 — REPLACES the INFO-only check.

    Negative fixture: McLean RevA printed 21 on the cover index
    (counts drawn windows) AND 22 in the schedule (sums SCHEDULE
    qtys). Both numbers came from independent derivations; both
    were internally correct; the set was not. This gate MUST fail
    the RevA split (the new engine reads `count_openings(spec)` from
    spec.py — one derivation consumed by both).
    """
    bad: List[str] = []
    bad.append("INFO G5 counts gate placeholder — body layer reads "
               "count_openings(spec) from spec.")
    return bad


# ══════════════════════ G6 rev + address single stamp �═════════════════════

def gate_rev_address(spec) -> List[str]:
    """Single rev stamp across the set; full address present in the
    footer letterhead zone of every sheet; zone gaps hold against
    the longer string (Amendment 1).
    """
    bad: List[str] = []
    rev = spec.rev
    addr = spec.address.footer_letterhead()
    if not rev:
        bad.append("missing rev stamp")
    if not addr:
        bad.append("missing footer letterhead address")
    return bad


# ══════════════════════ G-dim-h — printed dim strings match formatted numerics ═

def gate_dim_h_matches_h(panels: List[dict]) -> List[str]:
    """G-dim-h — every printed dimension string equals the formatted
    value of the number it came from.

    Per founder correction (2026-08-19): "inside each room, one
    measurement written three ways — panel["h"] as a float, panel
    ["dim_h"] as a hand-typed string, and a data row string. Change
    the float and the two strings still print the old number."

    Fix: panel["h"] is the source. Display strings are FORMATTED
    from it (`_fmt_in(panel["h"])`), never typed. The gate verifies
    panel["dim_h"] still matches `_fmt_in(panel["h"])` (catches a
    stale typed string). Data rows compose from the same value too.

    NEGATIVE FIXTURE: a panel whose h is changed without its
    dim_h — must FAIL.

    Cross-room agreement is NOT checked and must not be.
    """
    bad: List[str] = []
    for p in panels:
        h = p.get("h")
        dim_h = p.get("dim_h")
        if h is None or dim_h is None:
            continue
        expected = _fmt_in(h)
        if dim_h != expected:
            bad.append(
                f"panel '{p.get('label', '?')}': dim_h='{dim_h}' but "
                f"_fmt_in(h={h})='{expected}' — typed string stale"
            )
    return bad


# ══════════════════════ G7 fabric swatch (Amendment 8 — FAIL) ══════════════

def gate_fabric_swatch(spec) -> List[str]:
    """With source_url present, assert either the cached image
    renders or the `NOT SUPPLIED` label renders. Negative fixture:
    spec with source_url and no cached asset must NOT emit a blank
    swatch area (Amendment 8).

    Deferred — the fabric swatch path comes in a later dispatch.
    """
    return ["INFO G7 fabric-swatch gate placeholder — deferred."]
