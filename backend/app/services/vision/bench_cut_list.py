"""Presentation cut lists for Drawing Studio / quote benches.

Wood is true size. Foam matches wood length × width. Fabric is labeled
separately with a seam allowance. Every printed size uses shop fractions
from the live drawing inch formatter — never decimal inches.
"""
from __future__ import annotations

from app.services.drawing.inches import format_inches

FABRIC_SEAM_IN = 4.0

WOOD_LABEL = "WOOD CUT — TRUE SIZE"
FOAM_LABEL = "FOAM CUT — MATCHES WOOD"
FABRIC_LABEL = "FABRIC CUT — LABELED SEPARATELY"

RULES = [
    "Wood is true size.",
    "Foam matches wood length × width.",
    "Fabric is labeled separately and includes a 4\" seam allowance.",
]


def _size(width: float, length: float) -> str:
    return f"{format_inches(width)} × {format_inches(length)}"


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


def generate_cut_list(model) -> dict:
    """Wood / foam / fabric rows. Sizes are fraction strings with no decimals."""
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
            "note": "Matches wood length × width.",
        })
        fabric.append({
            "name": f"{name} fabric",
            "qty": 1,
            "width": width + FABRIC_SEAM_IN,
            "length": length + FABRIC_SEAM_IN,
            "size": _size(width + FABRIC_SEAM_IN, length + FABRIC_SEAM_IN),
            "label": FABRIC_LABEL,
            "note": "Fabric cut — labeled separately; includes 4\" seam allowance.",
        })
    return {
        "wood": wood,
        "foam": foam,
        "fabric": fabric,
        "rules": list(RULES),
    }


def render_cut_list_sheet(cuts: dict, name: str = "", quote_num: str = "") -> str:
    """Simple SVG shop sheet. Fraction sizes only — no decimal inch labels."""
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
