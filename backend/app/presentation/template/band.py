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

from typing import Callable, List, Tuple, Union
import base64
import mimetypes
import os

from app.presentation.template.chrome import (
    GOLD, HAIR, INK, MUTE, SANS, MONO,
    RECT, LINE, T, wrap, section,
)
from app.presentation.template.spec import normalize_check_lines


# A data row value is either a typed string ("99\"") OR a callable
# that takes a panel and returns the formatted string. Callables are
# the mechanism for "this value derives from panel['h']" — the body
# layer passes a panel to a lambda and the result is rendered.
# Per founder correction (2026-08-19): one measurement written
# three ways was the defect. This makes the third copy derivable.
DataValue = Union[str, Callable[[dict], str]]


# Band geometry (per McLean reference lines 795-796)
VP  = (30.0, 100.0, 762.0, 386.0)   # drawing viewport
BAND = (30.0, 402.0, 762.0, 562.0)  # reference band (photos | data | check)


def render_band(photos: List[Tuple[str, str]],
                data_rows: List[Tuple[str, DataValue]],
                check_lines: List[str],
                fabric_strip: str,
                placed: list = None,
                panel: dict = None) -> List[str]:
    """Render the three-zone reference band.

    Args:
      photos        : list of (asset_path, caption). Missing paths
                      are handled by the caller (band layer assumes
                      the asset has been loaded + embedded by the
                      intake path; if the path is the literal string
                      "NO SITE PHOTO ON FILE", we render the empty
                      placeholder).
      data_rows     : list of (label, value) for the FIELD DATA zone.
                      `value` may be a string OR a callable taking
                      a panel (per founder 2026-08-19 data-row
                      derivation fix). If callable, the caller
                      passes `panel` so the value is formatted from
                      the source float — never typed twice.
      check_lines   : list of strings for the FIELD CHECK zone.
      fabric_strip  : single-line string for the fabric/heading strip.
      placed        : OPTIONAL list of placed text boxes (Amendment 5).
      panel         : OPTIONAL panel dict for derived data rows.

    Returns:
      SVG fragments for the three zones + fabric strip.
    """
    out: List[str] = []
    bx0, by0, bx1, by1 = BAND
    # Normalize check_lines so a plain str is ONE bullet, never
    # character-iterated (Field Check letter-stack defect).
    check_lines = normalize_check_lines(check_lines)
    shots = list(photos or [])
    body_t = by0 + 19
    ph_h = (by1 - body_t) - 24
    GAPZ = 18.0
    DATA_W = 188.0

    def _photo_size(fn: str):
        if not fn or not os.path.isfile(fn):
            return None
        try:
            from PIL import Image
            with Image.open(fn) as im:
                return im.size
        except Exception:
            return None

    def _embed_image(fn: str, x: float, y: float, w: float, h: float) -> str:
        """Embed JPEG/PNG as data-URI <image> (McLean reference pattern)."""
        if not fn or not os.path.isfile(fn):
            return ""
        try:
            with open(fn, "rb") as f:
                b64 = base64.b64encode(f.read()).decode("ascii")
        except OSError:
            return ""
        mime, _ = mimetypes.guess_type(fn)
        if mime not in ("image/jpeg", "image/png", "image/webp", "image/gif"):
            mime = "image/jpeg"
        return (
            f'<image x="{x:.2f}" y="{y:.2f}" width="{w:.2f}" height="{h:.2f}" '
            f'preserveAspectRatio="xMidYMid slice" '
            f'xlink:href="data:{mime};base64,{b64}"/>'
        )

    # Photo zone width: fit each readable shot to ph_h, cap the zone.
    # Missing / unreadable paths are skipped (band still shows caption-
    # only only when path resolves — otherwise empty → NO SITE PHOTO).
    fitted: List[List] = []  # [fn, cap, w, h]
    for fn, cap in shots:
        size = _photo_size(fn)
        if size is None:
            # Keep a caption-only slot so the job still names the fabric
            # even when the thumb path is wrong — but use a placeholder
            # box (no fake image bytes).
            iw, ih = 100, 100
            use_fn = ""
        else:
            iw, ih = size
            use_fn = fn
        h = ph_h
        w = (iw / ih * h) if ih else h
        fitted.append([use_fn, cap, w, h, fn])  # keep original fn for debug
    # trim trailing bookkeeping — store as [fn_or_empty, cap, w, h]
    fitted = [[f[0], f[1], f[2], f[3]] for f in fitted]

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
    any_embedded = False
    for fn, cap, w, h in fitted:
        img = _embed_image(fn, px, body_t, w, h) if fn else ""
        if img:
            out.append(img)
            any_embedded = True
        else:
            # Empty frame — path missing or unreadable
            out.append(RECT(px, body_t, w, h, "#f3efe4", HAIR, 1.0, dash="4 4"))
        out.append(RECT(px, body_t, w, h, "none", INK, 0.9))
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
        # Per founder 2026-08-19: data row values may be a callable
        # deriving from a panel (e.g. lambda p: _fmt_in(p["h"])).
        # Resolve once — never typed twice.
        if callable(b):
            if panel is None:
                resolved = "—"  # defensive: spec didn't pass panel
            else:
                resolved = b(panel)
        else:
            resolved = b
        vy = y + lead
        for ln in wrap(resolved, wrapn)[:2]:
            _t, _b = T(dx, vy, ln, size=val_s, anchor="start",
                       fill=INK, font=SANS,
                       bold=("not tagged" not in resolved
                             and "not recorded" not in resolved))
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
