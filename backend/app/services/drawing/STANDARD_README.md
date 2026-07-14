# Empire Workroom Drawing & Mockup — Standard & Golden Reference Index

This directory is the canonical home for the drawing system. Phase A
(Sprint 1d, 2026-07-14) commits the standard and the golden output
bundle. After Phase A, no file outside this directory is referenced by
the system. The original source `~/incoming/` is preserved for archive
purposes only.

## The Standard (source of truth)

- **`EMPIRE_DRAWING_STANDARD.md`** — v1.0. Every hard rule, every
  required view, every drafting convention. Read this first.
- **`_legacy_willard_reference.py`** — the original reportlab
  implementation (was `willard_drawing.py` in `~/incoming/`). Read
  this second as the reference implementation that the new pipeline
  will generalize.

## Golden outputs (acceptance targets)

Each Phase writes tests that assert the new pipeline produces a PDF
matching these — bit-for-bit tolerance, asserted via pdfplumber.

### Sheet-rendering acceptance (Phase B)

| Source file in this directory | Origin | What it asserts |
|---|---|---|
| `golden_reference_willard.pdf` | `ONeil_Willard_Bench_Panel_Drawings.pdf` | Curved bench + armrest + channel panel sheets pass; layout-math closes in 1/64"s. |
| `golden_templates_10sheet.pdf` | `Empire_Workroom_Drawing_Templates_COMPLETE.pdf` | 10-family template coverage pass. |

### Estimate-format acceptance (Phase D)

| File | Origin | What it asserts |
|---|---|---|
| `golden_estimate.pdf` | `EST-2026-110_ONeil_Willard.pdf` | Per-line prices only, deposit line, field-verify note. |

### Mockup-rendering acceptance (Phase C tier-1)

| File | Origin | Tier | What it asserts |
|---|---|---|---|
| **`golden_presentation_board.png`** | `ONeil_Willard_Presentation_Board.png` | **Tier-1 reference** (default for every soft-goods/upholstery quote). | Deterministic orthographic elevation with true-scale pattern + material chips + yardage legend. |
| `golden_presentation_board_v1.png` | `ONeil_Willard_Mockup.png` | Tier-1 v1 (legacy mockup reference). | Same shape; preserved for diff comparison during Phase C development. |
| `golden_presentation_board_proposed.png` | `ONeil_Willard_Proposed_only.png` | Tier-1 with proposed-only accent. | Same sheet without "EXISTING" layer. |
| `golden_drapery_composite.png` | `Drapery_PinchPleat_Gold_Mockup.png` | Tier-2 composite reference. | Photo composite with VP perspective from two founder-clicked reference lines, rings on rod, ~10% ambient blend. |
| `golden_drapery_proposed.png` | `Drapery_PinchPleat_Gold_Proposed.png` | Tier-2 proposed-only. | Same composite without EXISTING layer. |

## Phase index (which file goes with which phase)

| Phase | Reads from | Golden assertion |
|---|---|---|
| A (this commit) | `EMPIRE_DRAWING_STANDARD.md`, all golds | golden files present + routing fixes (no-default-dims, pending jobs, theater-detector WARNING-only) |
| B (geometry templates) | `_legacy_willard_reference.py`, `golden_reference_willard.pdf`, `golden_templates_10sheet.pdf`, `MEASUREMENT_REQUIREMENTS` in `app/data/product_catalog.py` | new templates reproduce `golden_templates_10sheet.pdf` |
| C (mockup engine) | `golden_presentation_board.png` (tier-1), `golden_drapery_composite.png` (tier-2) | new mockup reproduces tier-1 (Phase A) for every soft-goods/upholstery quote |
| D (estimate + yardage + photo) | `golden_estimate.pdf`, `golden_drapery_proposed.png` | new estimate PDF matches `golden_estimate.pdf`; photo composite matches `golden_drapery_composite.png` |

## After Phase A

No path outside this directory is referenced by the running system.
The original source at `~/incoming/` remains as a private archive and
should NOT be cited by code, comments, or tests.
