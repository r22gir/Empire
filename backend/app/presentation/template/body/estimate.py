"""body/estimate.py — estimate body scaffold.

Per the dispatch's P1-T·d: estimate is one of FIVE document types.
Only measurement_set has a proven reference in P1-T·b. For the
other four, build the TYPE SCAFFOLD against shared chrome and raise
SpecIncomplete until their fixtures land. Do NOT invent their body
layouts from imagination.

Per P1-T·c: builders are pure functions returning SVG fragments or
a structured SpecIncomplete refusal.
"""
from __future__ import annotations

from app.presentation.template.spec import JobSpec, SpecIncomplete


def build(spec: JobSpec) -> str:
    """Estimate body — SCAFFOLD ONLY. Raises SpecIncomplete.

    The estimate body must read from the canonical quote store
    through the shared `resolve_quote()` — never a copy, never legacy
    JSON directly. That fixture is not in P1-T·b scope; it lives in
    a later dispatch (likely the W2/S3 woodwork engine dispatch that
    shares this template layer).
    """
    raise SpecIncomplete(missing=[
        "estimate.body — fixture not yet built; reads from canonical "
        "quote store via shared resolve_quote() (deferred)",
    ])
