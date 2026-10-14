"""Fabric cut allowance by foam thickness — editable shop table.

Rafael's rule
-------------
- Wood / board cut is true size.
- Foam cut equals the wood cut.
- Fabric cut is a separately labeled size. Its allowance depends on foam
  thickness. There is no single fixed seam (never “+ 4" for every job”).

Allowance table semantics
-------------------------
``allowance_in`` is the extra inches on EACH SIDE of a wood dimension.
Fabric cut = wood + 2 × allowance_in (both sides). Confirmed by Rafael
2026-10-14. The table *amounts* stay ``confirm_with_rafael`` until he
signs a row off.

Starter wrap used to pick the numbers: 2 × foam thickness + 1" sew.
Example: 2" foam → allowance_in = 5. A 12" × 18" wood cut becomes
22" × 28" fabric (12 + 2×5, 18 + 2×5). Fractions only when printed.

How to edit
-----------
Add, remove, or change rows in FABRIC_CUT_ALLOWANCE_BY_FOAM_THICKNESS.
Each row is inches of foam → extra inches added to EACH SIDE of EACH
wood dimension.

``status``:
  - ``confirm_with_rafael`` — default starter row, not signed off
  - ``confirmed`` — Rafael approved this allowance

If foam thickness is missing, or there is no row for that thickness,
the cut list prints ``needs foam thickness`` and does not guess.
"""
from __future__ import annotations

from typing import Any, Optional

# Extra inches on EACH SIDE of each wood dimension (Rafael 2026-10-14).
# Fabric = wood + 2 × allowance_in. Starter wrap numbers = 2 × foam + 1" sew.
# Row amounts stay confirm_with_rafael until signed off.
FABRIC_CUT_ALLOWANCE_BY_FOAM_THICKNESS: list[dict[str, Any]] = [
    {
        "foam_thickness_in": 1.0,
        "allowance_in": 3.0,
        "status": "confirm_with_rafael",
        "label": "1\" foam — wrap both faces + 1\" sew (confirm with Rafael)",
    },
    {
        "foam_thickness_in": 1.5,
        "allowance_in": 4.0,
        "status": "confirm_with_rafael",
        "label": "1 1/2\" foam — wrap both faces + 1\" sew (confirm with Rafael)",
    },
    {
        "foam_thickness_in": 2.0,
        "allowance_in": 5.0,
        "status": "confirm_with_rafael",
        "label": "2\" foam — wrap both faces + 1\" sew (confirm with Rafael)",
    },
    {
        "foam_thickness_in": 3.0,
        "allowance_in": 7.0,
        "status": "confirm_with_rafael",
        "label": "3\" foam — wrap both faces + 1\" sew (confirm with Rafael)",
    },
    {
        "foam_thickness_in": 4.0,
        "allowance_in": 9.0,
        "status": "confirm_with_rafael",
        "label": "4\" foam — wrap both faces + 1\" sew (confirm with Rafael)",
    },
    {
        "foam_thickness_in": 5.0,
        "allowance_in": 11.0,
        "status": "confirm_with_rafael",
        "label": "5\" foam — wrap both faces + 1\" sew (confirm with Rafael)",
    },
    {
        "foam_thickness_in": 6.0,
        "allowance_in": 13.0,
        "status": "confirm_with_rafael",
        "label": "6\" foam — wrap both faces + 1\" sew (confirm with Rafael)",
    },
]

NEEDS_FOAM_THICKNESS = "needs foam thickness"
CONFIRM_WITH_RAFAEL = "confirm_with_rafael"
# How to apply allowance_in. Semantics confirmed Rafael 2026-10-14.
# Table amounts remain confirm_with_rafael until a row is signed off.
ALLOWANCE_APPLY = "per_side"
ALLOWANCE_APPLY_CONFIRMED = "2026-10-14"


def fabric_dimension_in(wood_in: float, allowance_in: float) -> float:
    """Wood size plus allowance on each side. Fractions only when formatted."""
    return float(wood_in) + 2.0 * float(allowance_in)


def _sixteenths(value: float) -> int:
    return round(float(value) * 16)


def lookup_fabric_allowance(foam_thickness_in: Optional[float]) -> dict[str, Any]:
    """Return the table row for this foam thickness, or a needs-thickness result.

    Never invents an allowance. Unknown / unmatched thickness is not guessed.
    """
    if foam_thickness_in is None or foam_thickness_in == "":
        return {
            "foam_thickness_in": None,
            "allowance_in": None,
            "status": NEEDS_FOAM_THICKNESS,
            "label": "needs foam thickness — required before a fabric cut can be sized.",
        }
    try:
        thickness = float(foam_thickness_in)
    except (TypeError, ValueError):
        return {
            "foam_thickness_in": None,
            "allowance_in": None,
            "status": NEEDS_FOAM_THICKNESS,
            "label": "needs foam thickness — required before a fabric cut can be sized.",
        }
    if thickness <= 0:
        return {
            "foam_thickness_in": None,
            "allowance_in": None,
            "status": NEEDS_FOAM_THICKNESS,
            "label": "needs foam thickness — required before a fabric cut can be sized.",
        }
    key = _sixteenths(thickness)
    rows = list(FABRIC_CUT_ALLOWANCE_BY_FOAM_THICKNESS)
    try:
        from app.services.company_setup.store import load_merged

        merged = load_merged()
        fabric = merged.get("fabric") if isinstance(merged.get("fabric"), dict) else {}
        extra = fabric.get("allowance_by_foam_thickness") if isinstance(fabric, dict) else None
        if isinstance(extra, list) and extra:
            rows = [r for r in extra if isinstance(r, dict)] + rows
    except Exception:
        pass
    for row in rows:
        if _sixteenths(row["foam_thickness_in"]) == key:
            return dict(row)
    return {
        "foam_thickness_in": thickness,
        "allowance_in": None,
        "status": NEEDS_FOAM_THICKNESS,
        "label": (
            f"No allowance row for {thickness:g}\" foam. "
            "Add a row in fabric_cut_allowance.py — do not guess."
        ),
    }
