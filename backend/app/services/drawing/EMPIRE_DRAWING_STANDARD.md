# EMPIRE WORKROOM DRAWING STANDARD v1.0

Standard for every shop drawing produced by Drawing Studio / drawing-router.
Reference implementation: `willard_drawing.py` (reportlab, vector PDF).
First document produced to this standard: ONeil_Willard_Bench_Panel_Drawings.pdf (2026-07-13).

## Hard rules (violations = automatic rejection)

1. **Spec fidelity.** Every dimension on the sheet comes from the founder's spec
   or is explicitly labeled `ASSUMED` and repeated in the NOTES/ASSUMPTIONS block.
   NEVER invent dimensions, cushions, features, or quantities. If an input is
   missing, STOP and ask — do not default from a template.
2. **One sheet per physical piece.** Multi-piece jobs = multi-sheet set,
   title-blocked "SHEET n of N". Never merge separate deliverables into one object.
3. **The math must close.** Any subdivided dimension (channels, pleats, panels,
   slats) must include a printed LAYOUT MATH line proving segments + gaps = overall
   (e.g. `8 × 10-49/64" + 7 × 1/8" = 87" — FLUSH BOTH ENDS`). Prefer exact
   fractions in 1/64" or better.
4. **Curved pieces show the curve.** Plan view is mandatory for any curved item;
   label arc-length dimensions as such ("87 inches ALONG BACK SIDE OF CURVE") and
   radius as ASSUMED + FIELD VERIFY unless the founder supplied it.
5. **No output without real rendering.** If the drawing pipeline is unreachable,
   say so. ASCII art, described drawings, or fabricated tool output are
   enforcement violations (runtime_truth_enforcer).

## Required views per sheet

- **PLAN VIEW** — mandatory when footprint is non-rectangular or curved.
- **FRONT ELEVATION** — always. For curved pieces, developed (unrolled) and labeled so.
- **SIDE ELEVATION or SECTION** — always. Wall-mounted pieces use a MOUNTING
  SECTION showing height AFF, mounting method, and adjacent pieces ghosted (dashed).
- **ISOMETRIC** — assembly context when the job has 2+ pieces or the founder asks.
  Note "(plan curve not shown)" if the iso is simplified.

## Title block (right column, every sheet)

EMPIRE WORKROOM / CUSTOM UPHOLSTERY & FABRICATION
5124 Frolich Ln, Hyattsville, MD 20781 / (703) 213-6484 / workroom@empirebox.store

Rows, in order: CLIENT, SITE, SHEET n of N, ITEM, DIMENSIONS, item-specific rows
(LEGS / CHANNELS / REVEALS / etc.), MATERIAL, DATE, DRAWN BY, STATUS.
STATUS is `FOR FOUNDER REVIEW` until PIN approval, then `APPROVED`.

Below the rows: **NOTES / ASSUMPTIONS — CONFIRM:** every assumption the drawing
makes, one per line. An empty assumptions block on a job with any unspecified
detail is itself a violation of rule 1.

## Drafting conventions

- Landscape letter, 18pt border, black linework on white.
- Upholstered areas: caramel-family fill tints (or job material tint); exposed
  wood: brown fill; walls/ghosts: gray dashed.
- Dimension lines: thin (0.6pt) with end ticks; extension lines gray 0.4pt.
- View labels: bold, underlined, centered under/over the view.
- Fonts: Helvetica family only. Fractions as text ("10-49/64\"") — never Unicode
  fraction glyphs.

## Companion mockup (when requested)

Photo-composite over the client's site photo when one exists: overlay the
proposed piece(s), preserve foreground occluders, label EXISTING vs PROPOSED,
caption "concept visualization only". Never present a mockup as photoreal or
as-built.

## Pipeline contract

drawing-router input = structured spec JSON (client, site, sheets[], each sheet:
item, views[], dims{}, assumptions[]). Missing required dims => return a
question, not a drawing. Output = vector PDF + per-sheet SVG. Stale dims from
prior jobs must never leak into a new handoff (clear handoff state per job).
