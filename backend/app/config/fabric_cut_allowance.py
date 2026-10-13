"""Fabric cut allowance by foam thickness — editable shop table.

Rafael's rule
-------------
- Wood / board cut is true size.
- Foam cut equals the wood cut.
- Fabric cut is a separately labeled size. Its allowance depends on foam
  thickness. There is no single fixed seam (never “+ 4" for every job”).

How to edit
-----------
Add, remove, or change rows in FABRIC_CUT_ALLOWANCE_BY_FOAM_THICKNESS.
Each row is inches of foam → extra inches added to EACH wood dimension
(width and length) to produce the fabric cut.

``status``:
  - ``confirm_with_rafael`` — default starter row, not signed off
  - ``confirmed`` — Rafael approved this allowance

If foam thickness is missing, or there is no row for that thickness,
the cut list prints ``needs foam thickness`` and does not guess.
"""
from __future__ import annotations

from typing import Any, Optional

# Extra inches added to each wood dimension for the fabric cut.
# Starter wrap = 2 × foam thickness + 1" sew. All defaults are unconfirmed.
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
    for row in FABRIC_CUT_ALLOWANCE_BY_FOAM_THICKNESS:
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
