# Max golden — McLean Whittington field-measurement set

**Status:** CANONICAL Max drawing / client sheet format (locked 2026-09-25).

**Not golden:** `reference/empire-house-format/` (Marleys EST-2026-272 WIP pack,
including any file named `GOLDEN_Empire_B2_Sheet_Flat_Fold.pdf`). Demoted;
content numbers for Marleys stay separate.

## Artifact

| Path | Role |
|---|---|
| `McLean_Whittington_REV_A.pdf` | Founder-approved 11-sheet set (local; PDFs under `reference/` are gitignored) |
| Desktop: `/home/rg/Desktop/MAX_GOLDEN_McLean_Whittington.pdf` | Same bytes, operator copy |
| Box: `/workspace/empire-house-format/golden/MAX_GOLDEN.pdf` | Same bytes |
| Generator: `reference/mclean/mclean_drapery_set_generator.py` | Source that regenerates this chrome |

**md5:** `f882144aefc03745533fdaae95ea86b4`

**PDF meta**
- Title: McLean - Window & Drapery Field Measurements - Whittington Design
- Author: Nelma's Workroom - Powered by Empire Workroom
- Subject: Whittington Design, McLean VA - REV A - 19 AUG 2026 - FOR DISCUSSION - NOT FOR CONSTRUCTION
- Pages: 11 · Landscape letter 792×612 pt

## Sheet set

| SHT | Room / content |
|---|---|
| 01 | Cover · index · how to read |
| 02–10 | Room elevations (Formal Dining … Powder Room) |
| 11 | Opening schedule · all rooms |

## Visual language (must match)

### Palette
- Paper cream `#f7f3ea` · ink `#20241f` · gold `#b8912f` · band `#16191c`
- Hair `#cdc4b0` · mute `#7b7466` · cream panel `#efe9dc`

### Typography
- Titles: DejaVu Serif bold
- Chrome / labels / LAYOUT MATH: DejaVu Sans Mono (letterspaced)
- Body: DejaVu Sans

### Header band (44 pt dark)
1. **Letterhead** left — `NELMA'S WORKROOM` (serif cream, ~14 pt)
2. Gold vertical rule
3. **POWERED BY EMPIRE WORKROOM** (gold mono) + project line under it (`CLIENT · PROJECT`)
4. Right: room/sheet title · `SHEET nn OF nn · REV X · date`
5. Gold hairline under band

### Footer band (26 pt dark)
1. Left: `NELMA'S WORKROOM · POWERED BY EMPIRE WORKROOM · HYATTSVILLE MD`
2. Center (gold): `FOR DISCUSSION - NOT FOR CONSTRUCTION`
3. Right: `SHEET n / N`
4. Gold hairline above band

### Body conventions
- Large room title (serif) + italic subtitle
- True-scale wall geometry in framed viewport with gold corner ticks
- **LAYOUT MATH** callout (gold label) for derived / closure math
- Gold dashed edges = head or sill not field-tagged (schematic)
- Gold dimension = closure open — see LAYOUT MATH
- Three-zone band: SITE PHOTO | FIELD DATA | FIELD CHECK · BEFORE FABRICATION
- Fabric strip: `NOT YET ELECTED · FABRIC: TBC …` until elected
- Inches + fractions only; no feet
- Nothing invented: untagged → schematic + named in FIELD CHECK

## Scope vs estimates

This golden is the **drawing / field-measurement** standard.

Portrait **estimate** PDFs are a different path (`mclean_estimate_pdf` /
Willard EST-2026-110). Align Nelma / Empire header language toward the same
house chrome; do **not** invent an estimate layout from this field set.

## Code hooks

- Presentation chrome: `backend/app/presentation/template/chrome.py`
- Defaults / proof: `backend/app/services/drawing/max_sheet_chrome.py`
- Spec fields: `JobSpec.letterhead`, `header_tagline`, `locale`, `status`
- Shop drapery B2 lane (`b2_renderers.py`) and upholstery shell still need
  fuller migration; branding language is being pulled toward this set.

## Regenerating proof chrome

```bash
backend/venv/bin/python -m app.services.drawing.max_sheet_chrome \
  --out ~/Desktop/Max_Golden_Chrome_Proof.pdf
```
