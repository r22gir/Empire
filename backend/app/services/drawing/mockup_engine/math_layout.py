"""Mathematical layout calculators for channel backs, tufts, modules, and casework."""
from __future__ import annotations

from typing import List, Tuple, Dict, Any


def compute_channels(total_length: float, target_channel_width: float = 12.0) -> Tuple[List[float], float]:
    """Calculate channel segment widths and end trim/remainder.

    Returns:
        (widths_list, end_remainder)
    If remaining width < 1e-6, returns [target_channel_width] * full, 0.0.
    Otherwise splits remainder symmetrically between ends:
        [rem / 2] + [target_channel_width] * full + [rem / 2], rem / 2
    """
    if target_channel_width <= 0:
        return [total_length], 0.0
    full = int(total_length // target_channel_width)
    rem = total_length - full * target_channel_width
    if rem < 1e-6:
        return [target_channel_width] * full, 0.0
    end = rem / 2.0
    return [end] + [target_channel_width] * full + [end], end


def compute_tufts(
    width: float,
    height: float,
    spacing_x: float = 8.0,
    spacing_y: float = 8.0,
) -> Tuple[List[Tuple[float, float]], Dict[str, Any]]:
    """Compute grid of tuft buttons / dimples with symmetric margins."""
    if spacing_x <= 0 or spacing_y <= 0:
        return [], {"rows": 0, "cols": 0}

    nx = max(1, int(round((width - spacing_x) / spacing_x)))
    margin_x = (width - (nx - 1) * spacing_x) / 2.0 if nx > 1 else width / 2.0

    ny = max(1, int(round((height - spacing_y) / spacing_y)))
    margin_y = (height - (ny - 1) * spacing_y) / 2.0 if ny > 1 else height / 2.0

    points = []
    for r in range(ny):
        y = margin_y + r * spacing_y
        for c in range(nx):
            # Diamond offset on alternate rows
            offset_x = (spacing_x / 2.0) if (r % 2 == 1) else 0.0
            x = margin_x + c * spacing_x + offset_x
            if 0 < x < width:
                points.append((x, y))

    return points, {
        "rows": ny,
        "cols": nx,
        "spacing_x": spacing_x,
        "spacing_y": spacing_y,
        "margin_x": margin_x,
        "margin_y": margin_y,
    }


def compute_modules(
    width: float,
    height: float,
    target_mod_w: float = 12.0,
    target_mod_h: float = 8.0,
) -> Tuple[List[Tuple[float, float, float, float]], Dict[str, Any]]:
    """Compute rectangular padded modules / basketweave blocks.

    Returns:
        (list of (x, y, w, h), metadata)
    """
    nx = max(1, int(round(width / target_mod_w)))
    mod_w = width / nx

    ny = max(1, int(round(height / target_mod_h)))
    mod_h = height / ny

    rects = []
    for r in range(ny):
        for c in range(nx):
            rects.append((c * mod_w, r * mod_h, mod_w, mod_h))

    return rects, {"nx": nx, "ny": ny, "mod_w": mod_w, "mod_h": mod_h}
