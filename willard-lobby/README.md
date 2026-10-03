# Willard InterContinental — lobby soft goods (DRAFT)

McLean house-format presentation and installation set for Maggie O'Neill / Mariella Cruzado (Splendor Styling).

Empire Workroom / Nelma's Workroom letterhead. Cream paper, ink, gold. Every page is watermarked **DRAFT**. Numbers are not locked. **Do not email this pack.**

These sheets were drawn locally with ReportLab. They were not produced by the Max live engine.

## Regenerate

```bash
python3 -m pip install -r willard-lobby/requirements.txt
python3 willard-lobby/generate_willard_lobby_pack.py
```

Outputs:

- `willard-lobby/output/Willard_Lobby_Existing_vs_Proposed_DRAFT.pdf`
- `willard-lobby/output/Willard_Lobby_Installation_Drawings_DRAFT.pdf`
- `willard-lobby/output/previews/*.png`

Photo crops in `assets/` come from Mariella's labeled lobby collage (windows 1–4). The generator refuses to run if those crops are missing.

## What matches Est 838 (issued 18 Sep 2026, total $4,824.09)

Submitted estimate figures control wherever they exist. This pack does not reprice them.

| Opening | Est 838 | Field sheet |
|---|---|---|
| 1 · LOB-1 Concierge window | 1 pair @ 2W × 106" L, main 13 1/2 yd, napped lining 12 1/2 yd, 10 ft ripplefold track, removal / installation. **$1,074.75** | One of two pairs @ 2W. Inside mount ripplefold. |
| 2 · LOB-2 Reception | Same make and price as LOB-1. **$1,074.75** | The second pair. |
| 3 · LIN-1 Lincoln window | 2 stationary panels @ 1 1/2 W × 125 1/2" L, main 12 yd, lining 11 yd, holdbacks, hardware, removal / installation. **$1,210.02** | 2 non-operable panels, 73" × 125 1/2", 1 1/2 W per panel, 12 yd with lining. |
| 4 · LIN-2 Passway | 2 double-sided panels @ 3W × 102 1/2" L (1 1/2 W per face), main 20 yd, lining 18 1/2 yd, 20 rings, holdbacks, hardware, removal / installation. **$1,464.57** | 102 1/2" H, double-sided, 10 rings per panel, 2 panels @ 3W × 102 1/2", 20 yd. |

Main fabric on Est 838 is client supplied: 13 1/2 + 13 1/2 + 12 + 20 = 58 1/2 yd.

The 10 ft track is the priced hardware unit from Invoice 894. It is not a measured opening width.

## What differs

- **Finished length, lobby pairs.** Field sheet says 105" L. Est 838 says 106" L. Both are printed. Nothing here picks a cut length.
- **Lobby opening.** Field sheet: 72 3/16" W × 105 5/8" H, one outside size, for the two pairs together. Est 838 does not state an opening size. The same field size is drawn on windows 1 and 2. Reception was not measured on its own.
- **Lobby lining.** Field sheet: 23 yd for both pairs. Est 838: 12 1/2 + 12 1/2 = 25 yd napped premiere sateen. The submitted quantity stands until Nelma revises it.
- **Lincoln yardage scribble.** The sheet says "12 yd with lining" as one note. Est 838 prices 12 yd main (COM) and 11 yd lining separately. Do not drop the lining.
- **Passway width.** Not on the June 9 sheet and not on Est 838. The passway elevation is diagrammatic and carries no width figure.
- **Est 838 line note** on LOB-1 and LOB-2 says the ripplefold replaces the swag valance. The addendum prices a new swag with the pair. The elevations show that layered reading and mark it unconfirmed.

## Concierge Office is not on Est 838

The same June sheet records an **inside office** opening, separate from photograph 1 / LOB-1:

- Outer width 68 1/4"
- Height 104 1/4"
- A second figure, 68 13/16", marked VALANCE? — not resolved
- Tracks 8 ft × 2, 72 carriers
- Circled $95 per width — a field scribble, not Invoice 894 and not a submitted rate

No pair count, finished length, lining, or fabric. This pack does not invent a treatment or a price. It is called out as a gap (presentation page 6, installation sheet WL-INS-05) and left out of the lobby total. A separate line is possible later.

## Addendum is still DRAFT

Accessories are **not** on Est 838. BALLPARK lines stay labeled BALLPARK. INV 909 anchors (bullion $95.94, leading-edge $210.00, center-tassel unit $95.94) are Nelma-submitted unit rates with finish and style still open.

| | Amount | Status |
|---|---|---|
| Est 838 base | $4,824.09 | Submitted 18 Sep 2026 |
| Addendum new lines | $5,266.34 | DRAFT |
| Of which BALLPARK | $2,531.00 | Not locked |
| Of which INV 909–anchored | $2,735.34 | Unit rates, style/finish open |
| Combined if approved | $10,090.43 | Not a client total |

Sheers are windows 1 and 2 only (4 widths each is an assumption). Window 4 has no valance. Window 3 valance style is not chosen; the scallop is a placeholder marked STYLE TBC.

Holdback cylinders are already on LIN-1 and LIN-2 (4 × $35.94 = $143.76). If bullion replaces them, that credit is not taken here.

## Fabric scribbles

June 9 sheet, not a COM selection: Madalyn 30.50 and 49.95; Holloway 15.40 and 29.95. Scratch figures (139×, 140×, 75× W, 46, 420, 36) are not interpreted and are not prices.

## Drawings

Proposed views are schematic elevations: face fabric, sheer or glass or passway void, and gold for addendum trim. They are not photoreal renders and they are not to scale for the bench.

Existing views are crops of the labeled lobby photograph.

## Files

| Path | Role |
|---|---|
| `generate_willard_lobby_pack.py` | Builds both PDFs and the PNG previews |
| `house.py` | Letterhead, DRAFT watermark, tables |
| `elevations.py` | Schematic elevations |
| `assets/window_1_concierge.png` … `window_4_passway.png` | Photograph crops |
| `assets/lobby_windows_labeled.png` | Source collage |
