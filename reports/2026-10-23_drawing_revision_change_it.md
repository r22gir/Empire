# Night Lab RED — Max drawing revision applies new specs

**Date:** 2026-10-23  
**Door:** `run_job_drawing_turn` (shared by `/api/v1/max/chat` and `/chat/stream`)  
**Data:** mock Marley's quote / temp drawings dir. No live quotes, sends, or contacts.

## Found

When Rafael said "change it" with new specs (seat cushions Black V001-Raven, backs 12" channel V003-Cognac), the drawing desk could emit a new PDF and say "New drawing" from in-memory values. The generated sheet was not checked. An opaque `job_id` on the chat request could also drop the named job from history.

## Changed

- Max handles the revision itself on the drawing desk.
- Job name + prior specs carry over from history; the new sentence overwrites them.
- A new `job_set_*_REV{letter}_*.pdf` is written (letter bumps A → B).
- Success is claimed only after the **generated PDF text** shows the requested channel width and fabric codes.
- If the sheet misses a requested spec, the reply is "I will not call this a new drawing" and `success` is false.

## Proof (Max chat path)

Before — older 10" / V008-Bittersweet layout (REV A):

- `reports/2026-10-23_drawing_revision_change_it/before-1.png` (U plan)
- Seat V008-Bittersweet, `20 @ 10"` channels

After — `change it: seat cushions to Black V001-Raven, backs 12" channel V003-Cognac` (REV B):

- `reports/2026-10-23_drawing_revision_change_it/after-1.png` (U plan)
- `reports/2026-10-23_drawing_revision_change_it/after-3.png` (elevations)
- Seat V001-Raven Black, back V003-Cognac, `20 @ 12"` / `8 x 12"` channels
- No Spradling / Apex / brand names

## Tests

`PYTHONPATH=backend python3 -m pytest -q backend/tests/test_drawing_revision_change_it.py backend/tests/test_drawing_revision_nightlab.py`

16 passed. Covers spec carry-over, change application, false-success guard (stale PDF text → no "New drawing"), and the shared Max chat door.
