"""content/window_openings.py — Window-opening panel renderer.

Family-specific content renderer (per dispatch: "family-specific,
not general"). Ported from McLean reference lines 602-744
(`resolve_items` + `draw_panel`).

Three opening kinds are handled:
  - window  : glazed rectangle (with optional `inner` unit outer + glass
              inner)
  - door    : floor-to-floor rectangle (or partial when tagged)
  - fireplace: stone surround + firebox rectangle

Ghost walls (untagged width) draw dashed and label themselves
"WALL WIDTH NOT TAGGED". Untagged sill heights draw a hatched zone
below the opening labelled "SILL TO FLOOR NOT TAGGED".

Pure renderer — takes `(panel, ox_pt, oy_floor_pt, k_pt_per_inch)`,
returns SVG fragments. No side effects, no module-global state.
"""
from __future__ import annotations

from typing import List

from app.presentation.template.chrome import (
    CREAM, FIREBX, FRAME, GLASS, GLASS2, GOLD, HAIR, INK, MOULD,
    DOORF, DOORS, MUTE, STONE, SANS, MONO,
    RECT, LINE, T, hdim, vdim, VDIM_STEP, _fmt_in,
)


def resolve_items(panel: dict) -> List[dict]:
    """Give every item an x. Untagged spacing distributes evenly.

    Port of reference line 603-616. Items without an explicit `x`
    are placed evenly between the placed items. Returns a copy of
    the items list with `x` filled in for all items.
    """
    items = [dict(i) for i in panel.get("items", [])]
    free = [i for i in items if "x" not in i]
    if free:
        used = sum(i["w"] for i in items if "x" in i)
        span = panel["w"] - used - sum(i["w"] for i in free)
        gap = span / (len(free) + 1)
        cur = gap
        for i in items:
            if "x" not in i:
                i["x"] = cur
                cur += i["w"] + gap
    return items


def draw_panel(panel: dict, ox: float, oy_floor: float, k: float,
               placed: list = None) -> str:
    """Render a panel (a wall or room front).

    Args:
      panel    : the panel dict (with items, dims_top, dims_bot, dim_h, ...)
      ox       : panel left edge in PDF points
      oy_floor : floor line y in PDF points
      k        : pt-per-inch scale factor
      placed   : OPTIONAL list of placed text boxes (Amendment 5).
                 If provided, every emitted text string is appended
                 so the gate can read the bbox at draw time.

    Returns:
      Concatenated SVG fragments. Pure renderer — no side effects
      beyond the optional `placed` list mutation.
    """
    out: List[str] = []
    W, H = panel["w"], panel["h"]
    top = oy_floor - H * k
    ghost = panel.get("ghost_wall", False)

    # Wall body
    out.append(RECT(ox, top, W * k, H * k,
                    "#f3efe4" if ghost else CREAM,
                    HAIR if ghost else INK,
                    1.0 if ghost else 1.3,
                    dash="5 4" if ghost else None))
    said = any("NOT TAGGED" in str(d[-1])
               for key in ("dims_top", "dims_bot")
               for d in panel.get(key, []))
    ghost_note = None
    if (ghost and not said and not panel.get("no_ghost_note")):
        ghost_note = "WALL WIDTH NOT TAGGED"

    # Top band (moulding / header / overhead)
    if panel.get("top_band"):
        bh, blab = panel["top_band"]
        out.append(RECT(ox, top, W * k, bh * k, MOULD, GOLD, 0.9))
        if W * k > 74:
            if placed is not None:
                _t, _b = T(ox + 6, top + bh * k / 2 + 3.0, blab,
                           size=7.4, anchor="start", fill="#6d5720",
                           font=MONO, bold=True, ls=0.5)
                out.append(_t); placed.append(_b)
            else:
                out.append(T(ox + 6, top + bh * k / 2 + 3.0, blab,
                               size=7.4, anchor="start", fill="#6d5720",
                               font=MONO, bold=True, ls=0.5)[0])

    # Dashed vertical divisions (center wall)
    for d in panel.get("divisions", []):
        out.append(LINE(ox + d * k, top + 4, ox + d * k, oy_floor - 4,
                        MUTE, 0.8, "5 4"))

    items = resolve_items(panel)
    for i in items:
        ix = ox + i["x"] * k
        iw = i["w"] * k
        if i["v"]:
            head, ih = i["v"]
            iy = oy_floor - head * k
            ihp = ih * k
        else:                       # schematic vertical placement
            band = panel["top_band"][0] * k if panel.get("top_band") else 0.0
            iy = top + band + H * k * 0.055
            ihp = (oy_floor - iy) - H * k * 0.055
        if i["kind"] == "window":
            out.append(RECT(ix, iy, iw, ihp, GLASS, FRAME, 1.2))
            out.append(RECT(ix + 2.2, iy + 2.2, iw - 4.4, ihp - 4.4,
                           GLASS2, FRAME, 0.6))
            if i.get("inner"):      # unit outer + window inner
                m = (i["w"] - i["inner"]) / 2 * k
                out.append(RECT(ix + m, iy + m, iw - 2 * m, ihp - 2 * m,
                               GLASS, FRAME, 1.0))
            if not i["v"]:          # mark schematic head/sill
                out.append(LINE(ix, iy, ix + iw, iy, GOLD, 0.9, "3 3"))
                out.append(LINE(ix, iy + ihp, ix + iw, iy + ihp,
                                GOLD, 0.9, "3 3"))
            if i.get("w_est"):      # width never tagged - whole outline dashed
                out.append(RECT(ix, iy, iw, ihp, "none", GOLD, 1.1,
                               dash="3 3"))
                if placed is not None:
                    _t, _b = T(ix + iw / 2, iy + ihp / 2,
                               "WIDTH NOT TAGGED", size=7.6, anchor="middle",
                               fill="#8a6f22", font=MONO, ls=0.5)
                    out.append(_t); placed.append(_b)
                else:
                    out.append(T(ix + iw / 2, iy + ihp / 2,
                                  "WIDTH NOT TAGGED", size=7.6,
                                  anchor="middle", fill="#8a6f22",
                                  font=MONO, ls=0.5)[0])
        elif i["kind"] == "door":
            out.append(RECT(ix, iy, iw, ihp + (oy_floor - iy - ihp),
                            DOORF, DOORS, 1.2))
            if iw > 34:
                _t, _b = T(ix + iw / 2, (iy + oy_floor) / 2,
                           i.get("tag", "DOOR"), size=8.4, anchor="middle",
                           fill="#6b5c3f", font=MONO, bold=True, ls=0.6)
                out.append(_t); placed.append(_b)
                # Note: placed arg is optional — caller without it doesn't append
        elif i["kind"] == "fireplace":
            out.append(RECT(ix, oy_floor - H * k * 0.66, iw,
                            H * k * 0.66, STONE, MUTE, 1.1))
            out.append(RECT(ix + iw * 0.22, oy_floor - H * k * 0.42,
                            iw * 0.56, H * k * 0.36, FIREBX, FIREBX, 1.0))
            _t, _b = T(ix + iw / 2, oy_floor - H * k * 0.70, "FIREPLACE",
                       size=8.2, anchor="middle", fill=MUTE, font=MONO,
                       bold=True, ls=0.6)
            out.append(_t); placed.append(_b)

    if ghost_note:
        if placed is not None:
            _t, _b = T(ox + W * k / 2, top + 0 + 16, ghost_note,
                       size=6.8, anchor="middle", fill=MUTE, font=MONO,
                       ls=0.4)
            out.append(_t); placed.append(_b)

    # Hatched unknown zone below sill
    if panel.get("open_bottom"):
        hy = oy_floor
        out.append(RECT(ox, hy, W * k, 16, "none", HAIR, 0.8, dash="3 3"))
        for xx in range(0, int(W * k), 7):
            out.append(LINE(ox + xx, hy + 16, ox + xx + 8, hy, HAIR, 0.6))
        if placed is not None:
            _t, _b = T(ox + W * k / 2, hy + 30, "SILL TO FLOOR NOT TAGGED",
                       size=7.4, anchor="middle", fill=MUTE, font=MONO,
                       ls=0.4)
            out.append(_t); placed.append(_b)

    # Floor line
    if not panel.get("open_bottom"):
        out.append(LINE(ox - 6, oy_floor, ox + W * k + 6, oy_floor,
                        INK, 1.8))
    else:
        out.append(LINE(ox - 4, oy_floor, ox + W * k + 4, oy_floor,
                        MUTE, 1.0, "6 3"))

    # Panel label
    _t, _b = T(ox + W * k / 2, top - 40, panel["label"], size=9.5,
               anchor="middle", fill=INK, font=MONO, bold=True, ls=1.2)
    out.append(_t); placed.append(_b) if placed is not None else None

    # Dimension runs
    for d in panel.get("dims_top", []):
        if isinstance(d[0], str):
            idx = int(d[0][1:])
            it = items[idx]
            out.append(hdim(ox + it["x"] * k, ox + (it["x"] + it["w"]) * k,
                            top - 12, d[1],
                            flag=("UNTAG" in d[1])))
        else:
            out.append(hdim(ox + d[0] * k, ox + d[1] * k, top - 12, d[2],
                            flag=("UNTAG" in d[2] or "TAG" in d[2])))
    base = oy_floor + (40 if panel.get("open_bottom") else 22)
    for d in panel.get("dims_bot", []):
        if isinstance(d[0], str):
            idx = int(d[0][1:])
            it = items[idx]
            out.append(hdim(ox + it["x"] * k, ox + (it["x"] + it["w"]) * k,
                            base, d[1], above=False))
        else:
            full = (abs(d[0]) < 0.01 and abs(d[1] - W) < 0.01)
            lvl = base + (28 if (full and len(panel["dims_bot"]) > 1) else 0)
            out.append(hdim(ox + d[0] * k, ox + d[1] * k, lvl, d[2],
                            above=False,
                            flag=("NOT TAGGED" in d[2])))
    if panel.get("dim_h") or panel.get("h") is not None:
        # Per founder correction (2026-08-19): display strings are
        # FORMATTED from the float (panel["h"]), never typed. The
        # hand-typed panel["dim_h"] is no longer the source — gates.py
        # G-dim-h verifies it equals _fmt_in(panel["h"]).
        h_text = (_fmt_in(panel["h"]) if panel.get("h") is not None
                  else panel["dim_h"])
        out.append(vdim(top, oy_floor, ox - 24, h_text))
    for n, d in enumerate(panel.get("dims_right", [])):
        out.append(vdim(oy_floor - d[1] * k, oy_floor - d[0] * k,
                        ox + W * k + 24 + n * VDIM_STEP, d[2], left=False))
    return "".join(out)
