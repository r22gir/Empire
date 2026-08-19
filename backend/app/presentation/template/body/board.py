"""body/board.py — board body scaffold.

Per the dispatch's P1-T·d: board is one of FIVE document types.
Only measurement_set has a proven reference in P1-T·b. For the
other four, build the TYPE SCAFFOLD against shared chrome and raise
SpecIncomplete until their fixtures land. Do NOT invent their body
layouts from imagination.

Per the dispatch's open item 2 (MOCKUP OVERLAY): "founder describes
quotes retaining reference pictures with treatments overlaid, and
the quoting system producing final mockups. **Nothing in STATE or
BACKLOG records this capability.**" The board scaffold's full
implementation is blocked on this — until the founder confirms
whether mockup overlay exists today or is to be built, do NOT
implement.
"""
from __future__ import annotations

from app.presentation.template.spec import JobSpec, SpecIncomplete


def build(spec: JobSpec) -> str:
    """Board body — SCAFFOLD ONLY. Raises SpecIncomplete.

    Material/finish board (Bozzuto sofa #825 fixture). Mockup overlay
    capability is not recorded in STATE or BACKLOG — founder ruling
    pending before full implementation.
    """
    raise SpecIncomplete(missing=[
        "board.body — fixture not yet built; mockup-overlay capability "
        "not recorded in STATE/BACKLOG (founder ruling pending)",
    ])
