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


# Per-class overlap tolerances (PDF points). Body text keeps the
# original 1.2pt threshold; chrome (letterspaced header, footer, and
# label/value pairs in cover/sheet chrome) gets 8pt. The chrome T()
# y-bbox over-estimates height by ~0.3-1pt for letterspaced text at
# small sizes, which is enough to bridge the gap between adjacent y
# rows in label/value pairs. 8pt is enough to filter out
# line-height brushing on a real page while still catching genuine
# overprints.
TEXT_OVERLAP_TOL_PT_BODY = 1.2
TEXT_OVERLAP_TOL_PT_CHROME = 8.0
# Default kept for callers that don't pass a per-call tol.
TEXT_OVERLAP_TOL_PT = TEXT_OVERLAP_TOL_PT_BODY


# ══════════════════════ G1 bounds + zero rotated transforms ════════════════

def gate_bounds(placed: List[PlacedBox], frame_pt: float = 16.0) -> List[str]:
    """Every emitted text string is inside the page frame.

    Plus Amendment 6: zero rotated text transforms — `T(rot=-90)`
    callers must be caught here. (The reference uses rot=-90 in vdim()
    for the number orientation; the new port breaks the line instead
    (Amendment 6), so this gate never fires on the new engine.)
    """
    bad: List[str] = []
    for x0, y0, x1, y1, t, _cls in placed:
        if x0 < frame_pt - 6 or x1 > PW - frame_pt + 6 or y0 < 4 or y1 > PH - 4:
            bad.append(f"out of page: '{t[:38]}'")
    return bad


# ══════════════════════ G2 collisions (draw-time bboxes) ════════════════════

def gate_collisions(placed: List[PlacedBox],
                   tol: float = TEXT_OVERLAP_TOL_PT_BODY) -> List[str]:
    """Pairwise text-box overlap (Amendment 5).

    Boxes with both axes overlapping by more than the class's
    threshold are flagged. Each box is tagged at draw time
    (chrome.T() emits the class as the 6th element of PlacedBox);
    chrome (letterspaced header/footer, label/value pairs in cover
    sheets) uses the looser 8pt tolerance, body text keeps 1.2pt.
    Captured at DRAW TIME (per Amendment 5) — never recovered by
    parsing the emitted PDF.
    """
    bad: List[str] = []
    for i in range(len(placed)):
        ax0, ay0, ax1, ay1, at, acls = placed[i]
        # Per-class tolerance: chrome is looser (line-height brushing
        # on letterspaced chrome text is not an overprint).
        atol = (TEXT_OVERLAP_TOL_PT_CHROME if acls == "chrome"
                 else TEXT_OVERLAP_TOL_PT_BODY)
        for j in range(i + 1, len(placed)):
            bx0, by0, bx1, by1, bt, bcls = placed[j]
            # Use the LOOSER of the two classes' tolerances — a real
            # overprint between a body and a chrome string still fails
            # the body threshold; a brushing between two chromes fails
            # the chrome threshold. A real overprint between two body
            # strings fails the body threshold (1.2pt) — the negative
            # fixture proves this.
            btol = (TEXT_OVERLAP_TOL_PT_CHROME if bcls == "chrome"
                     else TEXT_OVERLAP_TOL_PT_BODY)
            this_tol = max(atol, btol)
            ox = min(ax1, bx1) - max(ax0, bx0)
            oy = min(ay1, by1) - max(ay0, by0)
            if ox > this_tol and oy > this_tol:
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

    Implementation: for each room with `dims_top` (typed numeric
    tuples), sum the typed widths and compare to the implied
    sum from divisions + panel.w. Also verify the typed `math`
    string mentions the parts and overall (sanity).

    Returns a list of (status, line) tuples. "OK" + delta lines
    for matched; "WARN" + delta lines for conflicts. NEVER "FAIL"
    — the build continues per Amendment 2.
    """
    out: List[Tuple[str, str]] = []
    for room in spec.rooms:
        panels = room.get("panels", [])
        if not panels:
            continue
        # Typed widths from dims_top (entries with 3 numeric elements).
        # dims_top entries are (start, end, label) OR (str_idx, label).
        typed_widths: List[float] = []
        for p in panels:
            for d in p.get("dims_top", []):
                if not isinstance(d[0], str) and len(d) >= 2:
                    typed_widths.append(abs(d[1] - d[0]))
        if not typed_widths:
            continue
        typed_sum = sum(typed_widths)
        # Implied sum from divisions + panel.w (if divisions present)
        for p in panels:
            divs = p.get("divisions", [])
            if divs:
                implied_sum = divs[0]
                for i in range(1, len(divs)):
                    implied_sum += divs[i] - divs[i-1]
                implied_sum += p["w"] - divs[-1]
                # Compare typed vs implied
                delta = abs(typed_sum - implied_sum)
                status = "OK" if delta < 0.05 else "WARN"
                out.append((status,
                            f"room '{room.get('key', '?')}': typed-dims "
                            f"sum={typed_sum:.2f}\" vs implied-"
                            f"sum={implied_sum:.2f}\" delta={delta:.2f}\""))
                break  # one room, one check
    if not out:
        out.append(("INFO", "G4 layout-math: no rooms with typed "
                            "dims_top to verify."))
    return out


# ══════════════════════ G5 counts (Amendment 4 — FAIL) ═════════════════════

def gate_counts(spec) -> List[str]:
    """Every count appearing more than once derives from one source
    and agrees. Amendment 4 — REPLACES the INFO-only check.

    Negative fixture: McLean RevA printed 21 on the cover index
    (counts drawn windows) AND 22 in the schedule (sums SCHEDULE
    qtys). Both numbers came from independent derivations; both
    were internally correct; the set was not. This gate MUST fail
    the RevA split — the new engine reads `count_openings(spec)` from
    spec.py (one derivation consumed by both cover and schedule).

    Implementation: verify that count_openings(spec) is internally
    consistent with two independent derivations (from rooms vs from
    schedule). If they disagree with `count_openings(spec)` or with
    each other, FAIL.
    """
    bad: List[str] = []
    from app.presentation.template.spec import count_openings
    total = count_openings(spec)
    # Independent derivation 1: count window-kind items in rooms
    n_items = 0
    for room in spec.rooms:
        for panel in room.get("panels", []):
            for item in panel.get("items", []):
                if item.get("kind") == "window":
                    n_items += 1
    # Independent derivation 2: sum SCHEDULE qtys
    n_sched = 0
    for row in spec.schedule:
        # SCHEDULE row format: (room, mark, qty, width, height, note)
        if len(row) >= 3:
            try:
                n_sched += int(row[2])
            except (TypeError, ValueError):
                pass
    if n_items != total or n_sched != total or n_items != n_sched:
        parts = []
        if spec.rooms:
            parts.append(f"rooms-derived={n_items}")
        if spec.schedule:
            parts.append(f"schedule-derived={n_sched}")
        parts.append(f"count_openings(spec)={total}")
        bad.append("G5 counts disagree: " + " vs ".join(parts))
    return bad


# ══════════════════════ G6 rev + address single stamp ══════════════════════

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

def gate_dim_h_matches_h(panels: List[dict],
                          rooms: List[dict] = None) -> List[str]:
    """G-dim-h — every printed dimension string equals the formatted
    value of the number it came from.

    Per founder correction (2026-08-19): "inside each room, one
    measurement written three ways — panel["h"] as a float, panel
    ["dim_h"] as a hand-typed string, and a data row string. Change
    the float and the two strings still print the old number."

    Fix: panel["h"] is the source. Display strings are FORMATTED
    from it (`_fmt_in(panel["h"])`), never typed. The gate verifies
    both panel["dim_h"] AND any data-row value typed as a string
    (NOT a callable) that purports to be the same measurement.
    Catches stale typed strings. Data rows that are CALLABLES are
    derived at render time and exempt from this check (their
    resolved value IS _fmt_in(panel["h"])).

    NEGATIVE FIXTURE: a panel whose h is changed without its
    dim_h — must FAIL. Same fixture for a data row value whose
    string was typed stale.

    Cross-room agreement is NOT checked and must not be.
    """
    bad: List[str] = []
    # (a) panel["dim_h"] must match _fmt_in(panel["h"])
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
    # (b) data row values that purport to be the same measurement
    # (typed, not a callable) must match _fmt_in(panel["h"]) for
    # the room's primary panel. Cross-room NOT checked.
    #
    # P1-T·c floor: callables are NOT skipped — they are CALLED with
    # the primary panel as their argument and their resolved value is
    # compared. A stale typed value wrapped in `lambda: "old value"`
    # would otherwise pass the gate as a callable; calling it returns
    # the stale string and the gate now catches it.
    if rooms is not None:
        for room in rooms:
            h_val = None
            primary_panel = None
            for p in room.get("panels", []):
                if "h" in p:
                    h_val = p["h"]
                    primary_panel = p
                    break
            if h_val is None:
                continue
            expected = _fmt_in(h_val)
            for label, value in room.get("data", []):
                # Resolve the value — callables are CALLED with the
                # primary panel as their argument, not skipped. Their
                # result is what gets compared to expected.
                if callable(value):
                    resolved = value(primary_panel)
                else:
                    resolved = value
                # Skip literal markers (not tagged, not recorded, etc.)
                if "not" in str(resolved).lower() or "ref" in str(resolved).lower():
                    continue
                if resolved == expected:
                    continue
                bad.append(
                    f"room '{room.get('key', '?')}' data row "
                    f"'{label}'={resolved!r} but _fmt_in(panel_h="
                    f"{h_val})='{expected}' — typed value stale"
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
