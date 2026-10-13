"""Presentation cut lists for Drawing Studio / quote benches.

Rafael's rule:
- Wood / board cut is true size.
- Foam cut equals the wood cut.
- Fabric cut is a separately labeled size. Allowance comes from the
  foam-thickness table in app.config.fabric_cut_allowance — never a
  single fixed seam. Unknown thickness prints “needs foam thickness”.

Printed sizes use spaced fractions (22 1/2"), never 22-1/2" or decimals.
"""
from __future__ import annotations

from math import gcd

from app.config.fabric_cut_allowance import (
    CONFIRM_WITH_RAFAEL,
    NEEDS_FOAM_THICKNESS,
    lookup_fabric_allowance,
)

WOOD_LABEL = "WOOD CUT — TRUE SIZE"
FOAM_LABEL = "FOAM CUT — MATCHES WOOD"
FABRIC_LABEL = "FABRIC CUT — LABELED SEPARATELY"

RULES = [
    "Wood / board cut is true size.",
    "Foam cut equals the wood cut.",
    "Fabric cut is labeled separately. Allowance depends on foam thickness (config table).",
    "If foam thickness is unknown, fabric cut is “needs foam thickness” — never guessed.",
]


def format_cut_inches(value: float) -> str:
    """Shop fraction with a space: 22.5 → 22 1/2\". Never hyphen or decimal."""
    sixteenths = round(float(value) * 16)
    whole = sixteenths // 16
    rem = sixteenths - whole * 16
    if rem == 0:
        return f'{whole}"' if whole else '0"'
    g = gcd(rem, 16)
    n = rem // g
    d = 16 // g
    if whole:
        return f'{whole} {n}/{d}"'
    return f'{n}/{d}"'


def _size(width: float, length: float) -> str:
    return f"{format_cut_inches(width)} × {format_cut_inches(length)}"


def _runs(model) -> list[tuple[str, float, float]]:
    bench_type = getattr(model, "bench_type", "straight") or "straight"
    depth = float(getattr(model, "depth", 0) or 0)
    if bench_type == "l_shape":
        long = float(getattr(model, "long", 0) or getattr(model, "width", 0) or 0)
        short = float(getattr(model, "short", 0) or 0)
        return [("Long run", long, depth), ("Short run", short, depth)]
    if bench_type == "u_shape":
        back = float(getattr(model, "back", 0) or getattr(model, "width", 0) or 0)
        left = float(getattr(model, "left", 0) or getattr(model, "side", 0) or 0)
        right = float(getattr(model, "right", 0) or getattr(model, "side", 0) or 0)
        return [("Back run", back, depth), ("Left wing", left, depth), ("Right wing", right, depth)]
    return [("Seat", float(getattr(model, "width", 0) or 0), depth)]


def _foam_thickness(model) -> float | None:
    raw = getattr(model, "foam_thickness_in", None)
    if raw in (None, ""):
        raw = getattr(model, "foam_thickness", None)
    if raw in (None, ""):
        return None
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def generate_cut_list(model) -> dict:
    """Wood / foam / fabric rows. Fabric size is table-driven or “needs foam thickness”."""
    allowance = lookup_fabric_allowance(_foam_thickness(model))
    extra = allowance.get("allowance_in")
    wood: list[dict] = []
    foam: list[dict] = []
    fabric: list[dict] = []
    for name, length, width in _runs(model):
        if not length or not width:
            continue
        wood.append({
            "name": name,
            "qty": 1,
            "width": width,
            "length": length,
            "size": _size(width, length),
            "label": WOOD_LABEL,
            "note": "True size. Do not add allowance.",
        })
        foam.append({
            "name": f"{name} foam",
            "qty": 1,
            "width": width,
            "length": length,
            "size": _size(width, length),
            "label": FOAM_LABEL,
            "note": "Equals the wood cut.",
        })
        if extra is None:
            fabric.append({
                "name": f"{name} fabric",
                "qty": 1,
                "width": None,
                "length": None,
                "size": NEEDS_FOAM_THICKNESS,
                "label": FABRIC_LABEL,
                "note": allowance.get("label") or "Needs foam thickness. Do not guess an allowance.",
            })
        else:
            note = (
                f"Fabric cut — labeled separately. "
                f"Allowance {format_cut_inches(extra)} from the foam-thickness table"
            )
            if allowance.get("status") == CONFIRM_WITH_RAFAEL:
                note += " (confirm with Rafael)"
            note += "."
            fabric.append({
                "name": f"{name} fabric",
                "qty": 1,
                "width": width + extra,
                "length": length + extra,
                "size": _size(width + extra, length + extra),
                "label": FABRIC_LABEL,
                "note": note,
            })
    return {
        "wood": wood,
        "foam": foam,
        "fabric": fabric,
        "rules": list(RULES),
        "foam_thickness_in": allowance.get("foam_thickness_in"),
        "fabric_allowance_in": extra,
        "fabric_allowance_status": allowance.get("status"),
        "fabric_allowance_label": allowance.get("label"),
    }


def render_cut_list_sheet(cuts: dict, name: str = "", quote_num: str = "") -> str:
    """Simple SVG shop sheet. Spaced fractions only — no decimal inch labels."""
    rows = []
    y = 70
    for group, heading in (
        (cuts.get("wood") or [], WOOD_LABEL),
        (cuts.get("foam") or [], FOAM_LABEL),
        (cuts.get("fabric") or [], FABRIC_LABEL),
    ):
        if not group:
            continue
        rows.append(
            f'<text x="36" y="{y}" font-family="Helvetica" font-size="13" font-weight="700">{heading}</text>'
        )
        y += 18
        for item in group:
            rows.append(
                f'<text x="36" y="{y}" font-family="Helvetica" font-size="12">'
                f'{item["qty"]} × {item["name"]} — {item["size"]}</text>'
            )
            y += 16
        y += 10
    for rule in cuts.get("rules") or RULES:
        rows.append(
            f'<text x="36" y="{y}" font-family="Helvetica" font-size="11">{rule}</text>'
        )
        y += 16
    height = max(y + 40, 400)
    title = name or "Cut list"
    quote = f"Quote {quote_num}" if quote_num else "Drawing Studio"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="792" height="{height}" viewBox="0 0 792 {height}">'
        f'<rect width="792" height="{height}" fill="#fff"/>'
        f'<text x="36" y="32" font-family="Helvetica" font-size="18" font-weight="700">{title} — cut list</text>'
        f'<text x="36" y="50" font-family="Helvetica" font-size="11">{quote}</text>'
        + "".join(rows)
        + "</svg>"
    )
