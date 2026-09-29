"""body/invoice.py — invoice body scaffold.

Per the dispatch's P1-T·d: invoice is one of FIVE document types.
Only measurement_set has a proven reference in P1-T·b. For the
other four, build the TYPE SCAFFOLD against shared chrome and raise
SpecIncomplete until their fixtures land. Do NOT invent their body
layouts from imagination.
"""
from __future__ import annotations

from app.presentation.template.spec import JobSpec, SpecIncomplete


def build(spec: JobSpec) -> str:
    """Invoice body — SCAFFOLD ONLY. Raises SpecIncomplete.

    The invoice body must read estimate lineage + payment terms and
    status from the canonical quote store. Fixture deferred — likely
    arrives with the W2/S3 woodwork engine dispatch.
    """
    raise SpecIncomplete(missing=[
        "invoice.body — fixture not yet built; reads estimate lineage + "
        "payment terms from canonical quote store (deferred)",
    ])
