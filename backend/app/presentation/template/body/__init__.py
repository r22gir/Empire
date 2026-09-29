"""body/__init__.py — body layer (one module per DOCUMENT TYPE).

Per the dispatch's TWO-AXES rule:
  DOCUMENT TYPE  = what kind of document (5 listed in P1-T·d)
  CONTENT FAMILY = what is being drawn or priced

This package has one module per document type:
  - measurement_set.py  (P1-T·b PROVEN — port from McLean)
  - estimate.py         (scaffold — SpecIncomplete until fixtures land)
  - invoice.py          (scaffold — SpecIncomplete until fixtures land)
  - presentation_sheet.py (scaffold — SpecIncomplete until fixtures land)
  - board.py            (scaffold — SpecIncomplete until fixtures land)

`measurement_set` × `window_openings` is the only PROVEN axis pair
in P1-T·b. Other pairs are scaffolds; do NOT invent their body
layouts from imagination — raise SpecIncomplete until the fixtures
land.
"""
