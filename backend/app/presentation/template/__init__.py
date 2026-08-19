"""template/__init__.py — Document Template Engine (P1-T·b).

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
"""
from app.presentation.template.spec import (
    JobSpec, Address, SpecIncomplete, count_openings,
)
from app.presentation.template.assemble import (
    BuildResult, assemble, BODY_BUILDERS,
)


__all__ = [
    "JobSpec", "Address", "SpecIncomplete", "count_openings",
    "BuildResult", "assemble", "BODY_BUILDERS",
]
