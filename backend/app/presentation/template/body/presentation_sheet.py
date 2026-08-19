"""body/presentation_sheet.py — presentation-sheet body scaffold.

Per the dispatch's P1-T·d: presentation_sheet is one of FIVE
document types. Only measurement_set has a proven reference in P1-T·b.
For the other four, build the TYPE SCAFFOLD against shared chrome
and raise SpecIncomplete until their fixtures land. Do NOT invent
their body layouts from imagination.
"""
from __future__ import annotations

from app.presentation.template.spec import JobSpec, SpecIncomplete


def build(spec: JobSpec) -> str:
    """Presentation-sheet body — SCAFFOLD ONLY. Raises SpecIncomplete.

    Client-facing single or short set. Fixture deferred.
    """
    raise SpecIncomplete(missing=[
        "presentation_sheet.body — fixture not yet built (deferred)",
    ])
