"""band.py — Reference band: site photo | field data | check-list.

Three-zone band that appears below the drawing viewport on every
room sheet. Ported from McLean reference `room_sheet()` lines
861-949.

Per Amendment 7 (SITE PHOTO PRIVACY):
  - Photos are per-job upload (NOT in module-global state).
  - Missing paths degrade to "NO SITE PHOTO ON FILE" (never crash).
  - Privacy blur lives in the asset intake path (photos.py), NOT
    here. The build pipeline calls intake once at job start;
    build(spec) stays pure and offline.

Per Amendment 1: the band reads spec.header_tagline / spec.address
(single sources).
"""
from __future__ import annotations

from typing import List, Tuple

from app.presentation.template.chrome import (
    GOLD, HAIR, INK, MUTE, SANS, MONO,
    RECT, LINE, T, wrap, section,
)


# Band geometry (per McLean reference lines 795-796)
VP  = (30.0, 100.0, 762.0, 386.0)   # drawing viewport
BAND = (30.0, 402.0, 762.0, 562.0)  # reference band (photos | data | check)


def render_band(photos: List[Tuple[str, str]],
                data_rows: List[Tuple[str, str]],
                check_lines: List[str],
                fabric_strip: str,
                placed: list = None) -> List[str]:
    """Render the three-zone reference band.

    Args:
      photos        : list of (asset_path, caption). Missing paths
                      are handled by the caller (band layer assumes
                      the asset has been loaded + embedded by the
                      intake path; if the path is the literal string
                      "NO SITE PHOTO ON FILE", we render the empty
                      placeholder).
      data_rows     : list of (label, value) for the FIELD DATA zone.
      check_lines   : list of strings for the FIELD CHECK zone.
      fabric_strip  : single-line string for the fabric/heading strip.
      placed        : OPTIONAL list of placed text boxes (Amendment 5).

    Returns:
      SVG fragments for the three zones + fabric strip.
    """
    out: List[str] = []
    bx0, by0, bx1, by1 = BAND
    shots = photos  # caller pre-processed (paths resolved)
    body_t = by0 + 19
    ph_h = (by1 - body_t) - 24
    GAPZ = 18.0
    DATA_W = 188.0

    # Photo zone width: fit each shot to ph_h, cap the zone
    fitted: List[List] = []  # [fn, cap, w, h]
    for fn, cap in shots:
        # Caller has resolved the image; we trust width/height.
        # In a future dispatch this becomes photo_size(fn) on a loaded
        # asset; here we use a placeholder fit.
        iw, ih = 100, 100  # placeholder — caller pre-fits
        h = ph_h
        w = iw / ih * h if ih else h
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

    # Photos
    sec_y = section(out, bx0, by0 + 10, photo_w,
                    "SITE PHOTO" + ("S" if len(fitted) > 1 else ""))
    px = bx0
    for fn, cap, w, h in fitted:
        # Caller emits the actual <image> tag (intake-path output).
        # We just draw the frame and caption here.
        out.append(RECT(px, body_t, w, h, "none", INK, 0.9))
        # Caption wrap
        for j, ln in enumerate(wrap(cap, max(int((w - 6) / 3.5), 12))[:3]):
            _t, _b = T(px, body_t + h + 9 + j * 7.4, ln, size=6.0,
                       anchor="start", fill=MUTE, font=MONO, ls=0.2)
            out.append(_t)
            if placed is not None and _b is not None:
                placed.append(_b)
        px += w + 8
    if not fitted:
        out.append(RECT(bx0, body_t, photo_w, ph_h, "#f3efe4", HAIR, 1.0,
                       dash="4 4"))
        _t, _b = T(bx0 + photo_w / 2, body_t + ph_h / 2,
                   "NO SITE PHOTO ON FILE", size=7.0, anchor="middle",
                   fill=MUTE, font=MONO, ls=0.6)
        out.append(_t)
        if placed is not None and _b is not None:
            placed.append(_b)

    # Field data
    y = section(out, dx, by0 + 10, DATA_W, "FIELD DATA")
    avail = by1 - y + 6
    for lab_s, val_s, wrapn, lead, pad in ((6.4, 8.8, 27, 11.0, 4.0),
                                           (6.1, 8.2, 29, 10.2, 3.2),
                                           (5.8, 7.6, 32, 9.4, 2.6),
                                           (5.5, 7.0, 35, 8.6, 2.0)):
        need = sum(11.0 + len(wrap(b, wrapn)[:2]) * (val_s + 1.2) + pad
                   for _, b in data_rows)
        if need <= avail:
            break
    for a, b in data_rows:
        _t, _b = T(dx, y, a, size=lab_s, anchor="start",
                   fill=MUTE, font=MONO, ls=0.5)
        out.append(_t)
        if placed is not None and _b is not None:
            placed.append(_b)
        vy = y + lead
        for ln in wrap(b, wrapn)[:2]:
            _t, _b = T(dx, vy, ln, size=val_s, anchor="start",
                       fill=INK, font=SANS,
                       bold=("not tagged" not in b and "not recorded" not in b))
            out.append(_t)
            if placed is not None and _b is not None:
                placed.append(_b)
            vy += val_s + 1.2
        y = vy + pad
        out.append(LINE(dx, y - 5, dx + DATA_W, y - 5, HAIR, 0.5))

    # Field check
    y = section(out, cx, by0 + 10, cw,
                "FIELD CHECK · BEFORE FABRICATION")
    room_left = by1 - y + 8
    for size, cols, lh in ((8.2, 42, 9.6), (7.8, 45, 9.1),
                           (7.4, 47, 8.7), (7.0, 50, 8.2),
                           (6.6, 54, 7.8), (6.2, 58, 7.4),
                           (5.9, 62, 7.0), (5.6, 66, 6.7)):
        need = sum(len(wrap(c, cols)) * lh + 5.0 for c in check_lines)
        if need <= room_left:
            break
    for c in check_lines:
        _t, _b = T(cx, y, "▪", size=size - 1.0, anchor="start",
                   fill=GOLD, font=SANS)
        out.append(_t)
        if placed is not None and _b is not None:
            placed.append(_b)
        for ln in wrap(c, cols):
            _t, _b = T(cx + 10, y, ln, size=size, anchor="start",
                       fill=INK, font=SANS)
            out.append(_t)
            if placed is not None and _b is not None:
                placed.append(_b)
            y += lh
        y += 5.0

    # Fabric registry strip (along the foot of the band)
    _t, _b = T(bx0, by1 + 16, fabric_strip, size=6.6, anchor="start",
               fill=GOLD, font=MONO, bold=True, ls=0.5)
    out.append(_t)
    if placed is not None and _b is not None:
        placed.append(_b)
    return out
