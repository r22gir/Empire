"""template/__init__.py — Document Template Engine (P1-T·b, P1-T·c).

Per EMPIRE_CLIENT_DOC_STANDARD.md + 8 founder amendments.

Layering (per P1-T·b dispatch):
  chrome.py       page chrome (header, footer, palette, type scale,
                  letterspacing, dimension primitives — Amendment 6
                  vertical-dim number-horizontal rule)
  spec.py         JobSpec + Address + SpecIncomplete + derived
                  (Amendment 4 ONE-source counts)
  content/
    window_openings.py  P1-T·b proven content renderer (panels)
  band.py         three-zone reference band (photos | data | check)
  body/
    measurement_set.py  P1-T·b PROVEN (cover + room sheets + schedule)
    estimate.py         scaffold (SpecIncomplete)
    invoice.py          scaffold (SpecIncomplete)
    presentation_sheet.py  scaffold (SpecIncomplete)
    board.py            scaffold (SpecIncomplete; mockup overlay pending)
  gates.py        pre-emit QC gates (G1..G7 per Amendment-Gates)
  assemble.py     orders sheets, stamps one rev, refuses mixed-rev

Two axes (do NOT collapse):
  DOCUMENT TYPE   = what kind of document (5)
  CONTENT FAMILY  = what is being drawn/priced

P1-T·b proven pair: measurement_set × window_openings.

P1-T·c (Builder interface): `build(spec) -> BuildResult` is the
canonical entry point callable by ANY door — MAX, the portal, the
CRM, the quoting system. The four non-measurement-set document
types are SCAFFOLDS that raise SpecIncomplete; `build()` delegates
to their per-type builder. Pure function: each call creates fresh
local accumulators (no module-global state). Idempotent — calling
twice produces identical output. `sys.exit(1)` is never an option;
SpecIncomplete is the only refusal path.
"""
from app.presentation.template.spec import (
    JobSpec, Address, SpecIncomplete, count_openings,
)
from app.presentation.template.assemble import (
    BuildResult, assemble, BODY_BUILDERS,
)


def build(spec: JobSpec) -> BuildResult:
    """P1-T·c canonical entry point. Pure function.

    Delegates to `assemble(spec)` for measurement_set (the proven
    reference) and to the per-type `body.<type>.build()` for the
    other four document types (which raise SpecIncomplete until their
    fixtures land).

    Raises:
        SpecIncomplete: spec is missing required fields, or the
                        document type is one of the four scaffolds
                        whose fixture has not yet been built.

    Returns:
        BuildResult with `pdf_bytes`, `gate_report`, `derived`.
    """
    if spec.document_type == "measurement_set":
        return assemble(spec)
    return _delegate(spec)


def _delegate(spec: JobSpec) -> BuildResult:
    """Delegate to a non-measurement-set body builder.

    All four other types are SCAFFOLDS — they raise SpecIncomplete.
    """
    body_type = spec.document_type
    if body_type == "estimate":
        from app.presentation.template.body import estimate as _b
    elif body_type == "invoice":
        from app.presentation.template.body import invoice as _b
    elif body_type == "presentation_sheet":
        from app.presentation.template.body import presentation_sheet as _b
    elif body_type == "board":
        from app.presentation.template.body import board as _b
    else:
        raise SpecIncomplete(missing=[f"document_type '{body_type}'"])
    return _b.build(spec)  # raises SpecIncomplete


__all__ = [
    "JobSpec", "Address", "SpecIncomplete", "count_openings",
    "BuildResult", "assemble", "BODY_BUILDERS",
    "build",
]
