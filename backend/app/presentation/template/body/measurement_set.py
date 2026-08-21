"""body/measurement_set.py — measurement-set body layer.

This is the PROVEN reference body layer (P1-T·b). Ported from
McLean reference `room_sheet()` (lines 809-950), `cover()`
(lines 954-1067), and `schedule_sheet()` (lines 1071-1126).

Sheet set: cover + 9 room elevations + schedule = 11 sheets.

KEY AMENDMENTS APPLIED HERE:
  - Amendment 1: chrome() takes TWO distinct fields (header_tagline,
    footer_letterhead). POWERED BY ... appears ONCE in header; full
    business address appears ONCE in footer letterhead. The split is
    enforced by `chrome()` parameter list.
  - Amendment 4: cover() and schedule_sheet() both read
    `count_openings(spec)` from spec.py — ONE derivation, consumed
    by both. The 21/22 split in McLean RevA cannot reappear.
  - Amendment 5: every emitted text string is recorded in the
    `placed` list (per Amendment 5 draw-time bboxes). chrome.py's T()
    returns `(svg, box)`; body builders append to placed.
  - Amendment 6: chrome.vdim() breaks the dimension line at mid-height
    and emits the number horizontally — no rotated text transforms.
  - Amendment 7: photos are per-job upload (spec.photos). Missing
    photos degrade to "NO SITE PHOTO ON FILE". The intake path
    (photos.py) is separate; build(spec) is pure.
  - Amendment 8 (measurement_set scope): "FABRIC: TBC - CONFIRM BEFORE
    CUT" is the pre-election placeholder. measurement_set is the only
    type that keeps this — estimate, invoice, presentation_sheet,
    board carry the swatch (deferred).

Builders are PURE FUNCTIONS: `build(spec)` returns SVG fragments,
no side effects. State (the `placed` list) is sheet-scoped.
"""
from __future__ import annotations

from typing import List

from app.presentation.template.spec import JobSpec, count_openings
from app.presentation.template.chrome import (
    GOLD, HAIR, INK, MUTE, SANS, MONO, SERIF,
    RECT, LINE, T, wrap, chrome, page, PlacedBox,
)
from app.presentation.template.band import render_band, BAND
from app.presentation.template.content.window_openings import (
    resolve_items, draw_panel,
)
from app.presentation.template.gates import (
    gate_bounds, gate_collisions, gate_layout_math,
    gate_counts, gate_rev_address,
)


# Sheet geometry (per McLean reference lines 795-796) — re-exported
# for body builders that need viewport math.
VP = (30.0, 100.0, 762.0, 386.0)


def _section(o, x, y, w, label):
    """Section-header primitive (per McLean reference lines 799-806)."""
    sz, ls = 8.5, 1.5
    avg_char_w = sz * 0.55
    while (avg_char_w * len(label) + ls * max(len(label) - 1, 0)) > w and sz > 5.6:
        sz -= 0.25
        ls = max(0.4, ls - 0.12)
        avg_char_w = sz * 0.55
    _t, _b = T(x, y, label, sz, "start", GOLD, MONO, bold=True, ls=ls)
    o.append(_t)
    o.append(LINE(x, y + 5, x + w, y + 5, GOLD, 0.9))
    return y + 19


def room_sheet(spec: JobSpec, room: dict, no: int, total: int,
               placed: List[PlacedBox]) -> Tuple[str, List[PlacedBox]]:
    """Render one room sheet.

    Pure function: takes spec + room data, returns full SVG page.
    `placed` is sheet-scoped state (passed in by assemble.py) — every
    text string emitted here is appended to `placed` for the gates.
    """
    placed_local = []  # sheet-scoped (Amendment 5)
    o: List[str] = []
    o.extend(chrome(
        sheet_no=no,
        total=total,
        right_title=room["name"],
        header_tagline=spec.header_tagline,
        footer_letterhead=spec.address.footer_letterhead(),
        rev=spec.rev,
        date=spec.date,
        status=spec.status,
        placed=placed_local,
    ))
    _t, _b = T(30, 66, room["name"], size=15.0, anchor="start",
               fill=INK, font=SERIF, bold=True, ls=0.8)
    o.append(_t); placed_local.append(_b)
    _t, _b = T(30, 84, room["sub"], size=8.2, anchor="start",
               fill=MUTE, font=SANS, italic=True)
    o.append(_t); placed_local.append(_b)

    # Drawing viewport
    x0, y0, x1, y1 = VP
    o.append(RECT(x0, y0, x1 - x0, y1 - y0, "#fbf8f1", HAIR, 1.0))
    for ax, ay, sx, sy in ((x0, y0, 16, 16), (x1, y1, -16, -16)):
        o.append(LINE(ax, ay, ax + sx, ay, GOLD, 1.6))
        o.append(LINE(ax, ay, ax, ay + sy, GOLD, 1.6))

    panels = room["panels"]
    nright = max((len(p.get("dims_right", [])) for p in panels), default=0)
    has_h = any(p.get("dim_h") for p in panels)
    from app.presentation.template.chrome import VDIM_GUTTER, VDIM_STEP
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
    avail_h = (y1 - y0) - up - down - 34.0
    k = min(avail_w / tot_w_in, avail_h / max_h_in)
    block = max_h_in * k
    extent = block + up + down
    floor = y0 + (y1 - y0 - 34.0 - extent) / 2 + up + block
    ox = x0 + pad_l + (avail_w - tot_w_in * k) / 2
    for p in panels:
        o.append(draw_panel(p, ox, floor, k, placed_local))
        ox += p["w"] * k + gap

    # Layout-math closure line + scale strip
    o.append(LINE(x0 + 10, y1 - 30, x1 - 10, y1 - 30, HAIR, 0.6))
    _t, _b = T(x0 + 10, y1 - 18, "LAYOUT MATH", size=7.2,
               anchor="start", fill=GOLD, font=MONO, bold=True, ls=1.2)
    o.append(_t); placed_local.append(_b)
    _t, _b = T(x0 + 88, y1 - 18, room["math"], size=7.6,
               anchor="start",
               fill=GOLD if room.get("math_flag") else INK,
               font=MONO, ls=0.2)
    o.append(_t); placed_local.append(_b)
    _t, _b = T(x1 - 10, y1 - 6,
               f"SCALE 1\" = {k:.3f} PT   ·   WALL GEOMETRY AT TRUE SCALE"
               f"   ·   UNTAGGED SPACING DRAWN EVEN AND MARKED",
               size=6.2, anchor="end", fill=MUTE, font=MONO, ls=0.4)
    o.append(_t); placed_local.append(_b)

    # Reference band. Per founder 2026-08-19: data row values may
    # be callables deriving from a panel — pass the primary panel
    # so render_band can resolve them. The room's first panel
    # is used as the "primary" (rooms with one panel — typical;
    # rooms with multiple panels share a common height).
    photos = spec.photos.get(room["key"], [])
    primary_panel = room["panels"][0] if room.get("panels") else None
    o.extend(render_band(
        photos=photos,
        data_rows=room.get("data", []),
        check_lines=room.get("check", []),
        fabric_strip=(
            "NOT YET ELECTED   ·   FABRIC: TBC - CONFIRM BEFORE CUT   ·   "
            "LINING: TBC   ·   HEADING: TBC   ·   HARDWARE: TBC   ·   "
            "MOUNT: NOT RECORDED ON FIELD SHEET"
        ),
        placed=placed_local,
        panel=primary_panel,
    ))

    placed.extend(placed_local)
    return page("".join(o)), placed


def cover(spec: JobSpec, total: int, placed: List[PlacedBox]) -> Tuple[str, List[PlacedBox]]:
    """Cover sheet. Reads `count_openings(spec)` from spec — one source.

    Amendment 4 fix: McLean RevA printed 21 (counts drawn windows) and
    22 (sums SCHEDULE qtys). The new engine reads `count_openings(spec)`
    ONCE and uses it for both cover index AND schedule.
    """
    placed_local = []
    o: List[str] = []
    o.extend(chrome(
        sheet_no=1, total=total, right_title="COVER · INDEX",
        header_tagline=spec.header_tagline,
        footer_letterhead=spec.address.footer_letterhead(),
        rev=spec.rev, date=spec.date, status=spec.status,
        placed=placed_local,
    ))
    _t, _b = T(30, 78, spec.project, size=26.0, anchor="start",
               fill=INK, font=SERIF, bold=True, ls=1.2)
    o.append(_t); placed_local.append(_b)
    _t, _b = T(30 + 250, 78,
               f"FOR {spec.client}  ·  {spec.client_loc}", size=9.0,
               anchor="start", fill=MUTE, font=MONO, bold=True, ls=1.4)
    o.append(_t); placed_local.append(_b)
    _t, _b = T(30, 98, "WINDOW & DRAPERY FIELD MEASUREMENTS", size=9.0,
               anchor="start", fill=GOLD, font=MONO, bold=True, ls=2.2)
    o.append(_t); placed_local.append(_b)
    o.append(LINE(30, 108, 762, 108, HAIR, 1.0))

    # Left: job block
    y = 132
    _t, _b = T(30, y, "JOB", size=7.0, anchor="start",
               fill=GOLD, font=MONO, bold=True, ls=1.4)
    o.append(_t); placed_local.append(_b)
    o.append(LINE(30, y + 4, 250, y + 4, GOLD, 0.8))
    y += 16
    addr_full = spec.address.footer_letterhead()
    for a, b in [("CLIENT", spec.client + "  ·  " + spec.client_loc),
                 ("HOUSE", spec.project),
                 ("WORKROOM", spec.header_tagline + "  ·  " + addr_full),
                 ("PRODUCTION", "EMPIRE WORKROOM"),
                 ("SOURCE", spec.source),
                 ("REVISION", f"REV {spec.rev}  ·  {spec.date}"),
                 ("SHEETS", f"{total} — cover, {len(spec.rooms)} room elevations, schedule"),
                 ("STATUS", spec.status)]:
        _t, _b = T(30, y, a, size=5.6, anchor="start",
                   fill=MUTE, font=MONO, ls=0.5)
        o.append(_t); placed_local.append(_b)
        _t, _b = T(30, y + 10, b, size=7.6, anchor="start",
                   fill=INK, font=SANS)
        o.append(_t); placed_local.append(_b)
        y += 26
        o.append(LINE(30, y - 8, 250, y - 8, HAIR, 0.5))

    y += 6
    _t, _b = T(30, y, "READ THIS SET AS", size=7.0, anchor="start",
               fill=GOLD, font=MONO, bold=True, ls=1.4)
    o.append(_t); placed_local.append(_b)
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
            _t, _b = T(30, y, ln, size=6.4, anchor="start",
                       fill=INK, font=SANS)
            o.append(_t); placed_local.append(_b)
            y += 8.0
        y += 4

    # Center/right: index
    ix = 300
    _t, _b = T(ix, 132, "SHEET INDEX", size=7.0, anchor="start",
               fill=GOLD, font=MONO, bold=True, ls=1.4)
    o.append(_t); placed_local.append(_b)
    o.append(LINE(ix, 136, 762, 136, GOLD, 0.8))
    yy = 152
    _t, _b = T(ix, yy, "SHT", size=5.4, anchor="start",
               fill=MUTE, font=MONO, ls=0.6)
    o.append(_t); placed_local.append(_b)
    _t, _b = T(ix + 38, yy, "ROOM", size=5.4, anchor="start",
               fill=MUTE, font=MONO, ls=0.6)
    o.append(_t); placed_local.append(_b)
    _t, _b = T(ix + 250, yy, "OPENINGS", size=5.4, anchor="start",
               fill=MUTE, font=MONO, ls=0.6)
    o.append(_t); placed_local.append(_b)
    _t, _b = T(762, yy, "OPEN ITEMS", size=5.4, anchor="end",
               fill=MUTE, font=MONO, ls=0.6)
    o.append(_t); placed_local.append(_b)
    yy += 6
    o.append(LINE(ix, yy, 762, yy, HAIR, 0.6))
    yy += 14
    rows: List[tuple] = [("01", "COVER · INDEX · HOW TO READ", "—", "—")]
    for n, r in enumerate(spec.rooms, start=2):
        wins = sum(1 for p in r["panels"]
                   for i in p.get("items", [])
                   if i["kind"] == "window")
        rows.append((f"{n:02d}", r["name"], str(wins) if wins else "wall",
                     str(len(r["check"]))))
    # Amendment 4: total from spec.count_openings(spec) — ONE source.
    total_openings = count_openings(spec)
    rows.append((f"{len(spec.rooms)+2:02d}", "OPENING SCHEDULE · ALL ROOMS",
                 str(total_openings), "—"))
    for a, b, c_, d in rows:
        _t, _b = T(ix, yy, a, size=7.2, anchor="start",
                   fill=GOLD, font=MONO, bold=True, ls=0.6)
        o.append(_t); placed_local.append(_b)
        _t, _b = T(ix + 38, yy, b, size=7.4, anchor="start",
                   fill=INK, font=SANS)
        o.append(_t); placed_local.append(_b)
        _t, _b = T(ix + 250, yy, c_, size=7.2, anchor="start",
                   fill=INK, font=MONO)
        o.append(_t); placed_local.append(_b)
        _t, _b = T(762, yy, d, size=7.2, anchor="end",
                   fill=MUTE, font=MONO)
        o.append(_t); placed_local.append(_b)
        yy += 9
        o.append(LINE(ix, yy - 3, 762, yy - 3, HAIR, 0.4))
        yy += 8

    # Open items at a glance
    oy = yy + 16
    _t, _b = T(ix, oy, "OPEN AT A GLANCE", size=7.0, anchor="start",
               fill=GOLD, font=MONO, bold=True, ls=1.4)
    o.append(_t); placed_local.append(_b)
    o.append(LINE(ix, oy + 4, 762, oy + 4, GOLD, 0.8))
    oy += 16
    for c in ["Living Room center wall does not close - 225\" tagged against "
              "222\" overall.",
              "Living Room left wall leaves 54¼\" untagged at the door bank.",
              "Formal Living bay moulding band scales 4½\" against 2½\" tagged.",
              "Head and sill heights are untagged in five rooms - no finished "
              "lengths can be set.",
              "Mount condition is not recorded anywhere in the set."]:
        for j, ln in enumerate(wrap(c, 74)):
            if j == 0:
                _t, _b = T(ix, oy, "▪", size=5.4, anchor="start",
                           fill=GOLD, font=SANS)
                o.append(_t); placed_local.append(_b)
            _t, _b = T(ix + 10, oy, ln, size=6.4, anchor="start",
                       fill=INK, font=SANS)
            o.append(_t); placed_local.append(_b)
            oy += 8.4
        oy += 2.6

    # Legend strip
    ly = 470
    _t, _b = T(30, ly, "LEGEND", size=7.0, anchor="start",
               fill=GOLD, font=MONO, bold=True, ls=1.4)
    o.append(_t); placed_local.append(_b)
    o.append(LINE(30, ly + 4, 762, ly + 4, GOLD, 0.8))
    ly += 14
    from app.presentation.template.chrome import (
        GLASS as _GL, DOORF as _DF, MOULD as _MD, CREAM as _CR,
    )
    lg: List[tuple] = [(_GL, "#2a3d52", "GLAZED OPENING - WIDTH TAGGED"),
                       (_DF, "#8a7a5c", "DOOR / DOOR BANK"),
                       (_MD, "#b8912f", "MOULDING, HEADER OR OVERHEAD BAND"),
                       (_CR, "#20241f", "WALL AT TRUE SCALE"),
                       ("#fbf8f1", "#cdc4b0", "GHOST - WIDTH NOT TAGGED")]
    lx = 30
    for f, st, lab in lg:
        o.append(RECT(lx, ly, 14, 10, f, st, 1.0))
        _t, _b = T(lx + 19, ly + 8.0, lab, size=5.6, anchor="start",
                   fill=INK, font=MONO, ls=0.3)
        o.append(_t); placed_local.append(_b)
        lx += 19 + len(lab) * 5.6 * 0.55 + 22  # approx
    ly += 24
    o.append(LINE(30, ly + 4, 46, ly + 4, GOLD, 1.2, "3 3"))
    _t, _b = T(54, ly + 6.6,
               "DASHED GOLD EDGE = HEAD OR SILL NOT FIELD-TAGGED, "
               "PLACEMENT SCHEMATIC", size=5.6, anchor="start",
               fill=INK, font=MONO, ls=0.3)
    o.append(_t); placed_local.append(_b)
    _t, _b = T(430, ly + 6.6, "GOLD DIMENSION = CLOSURE OPEN, SEE LAYOUT MATH",
               size=5.6, anchor="start", fill=GOLD, font=MONO, ls=0.3)
    o.append(_t); placed_local.append(_b)

    placed.extend(placed_local)
    return page("".join(o)), placed


def schedule_sheet(spec: JobSpec, no: int, total: int,
                   placed: List[PlacedBox]) -> Tuple[str, List[PlacedBox]]:
    """Schedule sheet. Reads `count_openings(spec)` — Amendment 4."""
    placed_local = []
    o: List[str] = []
    o.extend(chrome(
        sheet_no=no, total=total, right_title="OPENING SCHEDULE",
        header_tagline=spec.header_tagline,
        footer_letterhead=spec.address.footer_letterhead(),
        rev=spec.rev, date=spec.date, status=spec.status,
        placed=placed_local,
    ))
    _t, _b = T(30, 66, "OPENING SCHEDULE", size=15.0, anchor="start",
               fill=INK, font=SERIF, bold=True, ls=0.8)
    o.append(_t); placed_local.append(_b)
    _t, _b = T(30, 82,
               "All rooms - one line per opening type - as field-recorded "
               "1 July 2026", size=7.6, anchor="start",
               fill=MUTE, font=SANS, italic=True)
    o.append(_t); placed_local.append(_b)

    cols = [(30, "ROOM"), (196, "MARK"), (240, "QTY"), (276, "WIDTH"),
            (352, "HEIGHT"), (424, "HEAD / OVERHEAD CONDITION")]
    y = 112
    for x, lab in cols:
        _t, _b = T(x, y, lab, size=5.8, anchor="start",
                   fill=GOLD, font=MONO, bold=True, ls=1.2)
        o.append(_t); placed_local.append(_b)
    o.append(LINE(30, y + 5, 762, y + 5, GOLD, 1.0))
    y += 19
    for i, (room, mark, qty, w, h, note) in enumerate(spec.schedule):
        if i % 2 == 0:
            o.append(RECT(26, y - 9, 740, 18, "#efe9db"))
        _t, _b = T(30, y, room, size=7.4, anchor="start",
                   fill=INK, font=SANS, bold=True)
        o.append(_t); placed_local.append(_b)
        _t, _b = T(196, y, mark, size=7.2, anchor="start",
                   fill=GOLD, font=MONO, bold=True)
        o.append(_t); placed_local.append(_b)
        _t, _b = T(240, y, str(qty), size=7.2, anchor="start",
                   fill=INK, font=MONO)
        o.append(_t); placed_local.append(_b)
        # P1-T·c fix: T() takes str; w and h from SCHEDULE rows can be
        # int or str. Convert explicitly. (qty already wrapped at 401.)
        # The h fallback ("not" / "ref" check) was also broken on int h
        # — convert first.
        h_str = str(h)
        _t, _b = T(276, y, str(w), size=7.2, anchor="start",
                   fill=INK, font=MONO)
        o.append(_t); placed_local.append(_b)
        _t, _b = T(352, y, h_str, size=7.2, anchor="start",
                   fill=MUTE if "not" in h_str or "ref" in h_str else INK,
                   font=MONO)
        o.append(_t); placed_local.append(_b)
        _t, _b = T(424, y, note, size=6.6, anchor="start",
                   fill=MUTE, font=SANS)
        o.append(_t); placed_local.append(_b)
        y += 22
    o.append(LINE(30, y - 12, 762, y - 12, HAIR, 0.8))
    # Amendment 4: total from spec.count_openings(spec).
    total_openings = count_openings(spec)
    _t, _b = T(240, y + 2, str(total_openings), size=8.0, anchor="start",
               fill=GOLD, font=MONO, bold=True)
    o.append(_t); placed_local.append(_b)
    _t, _b = T(30, y + 2, "TOTAL OPENINGS RECORDED", size=7.0,
               anchor="start", fill=INK, font=MONO, bold=True, ls=0.8)
    o.append(_t); placed_local.append(_b)

    # Open items
    y += 34
    _t, _b = T(30, y, "OPEN BEFORE QUOTING", size=7.0, anchor="start",
               fill=GOLD, font=MONO, bold=True, ls=1.4)
    o.append(_t); placed_local.append(_b)
    o.append(LINE(30, y + 4, 762, y + 4, GOLD, 0.8))
    y += 16
    opens = [
      "Living Room center wall: tagged segments total 225\" against a 222\" "
      "overall. 3\" unresolved.",
      "Living Room left wall: 54¼\" at the door bank is untagged. Door bank "
      "width governs the panel count.",
      "Formal Living bay: moulding band scales 4½\" but is tagged 2½\". "
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
        _t, _b = T(30, y, "▪", size=5.4, anchor="start",
                   fill=GOLD, font=SANS)
        o.append(_t); placed_local.append(_b)
        for ln in lines:
            _t, _b = T(40, y, ln, size=6.6, anchor="start",
                       fill=INK, font=SANS)
            o.append(_t); placed_local.append(_b)
            y += 8.4
        y += 3.4

    placed.extend(placed_local)
    return page("".join(o)), placed
