# WoodCraft by Empire — Willard CST-23 3D Assembly Review & Specification

**Project Code:** WC-PRJ-CST23  
**Project Name:** Willard CST-23 Scotch Bar Curved Banquette  
**Client:** Maggie O'Neill / The Willard InterContinental  
**Fabrication Facility:** 5124 Frolich Ln, Hyattsville, MD 20781  
**Status:** Reviewed Custom Piece (Approved Custom Assembly)  
**Claude Artifact Source:** [Willard CST-23 3D Assembly Review](https://claude.ai/artifact/SopYioZ9n3atoMyeC4gnKu)  
**Interactive 3D Assembly Model:** `/woodcraft/willard-cst23`  

---

## 1. Custom Reviewed Piece Status & Fundamental Rules
> **GOVERNING PRINCIPLE:** Willard CST-23 is a reviewed custom piece; general rules do not override it. All dimensions and callouts use **fractions only**.

1. **Wood / Board Cut:** True size, no add-ons (exact nominal dimensions).
2. **Foam Cut:** Exact same dimensions as wood/board cut (`1:1` footprint).
3. **Fabric Cut:** Foam / channel width and height **plus 2" to 3" for stapling allowance** (nominal `2 1/2"` stapling margin).
4. **Schedule Presentation:** Always list wood cut and fabric cut as separate labeled sizes.
5. **Fractions Only:** Fractions only across all cut sheets, schedules, and engineering notes.

---

## 2. 3D Assembly Geometry & Layer Engine

### Key Dimensions
- **Front Radius ($R_{front}$):** `37 1/16"` (`37.07"`)
- **Rear Wall Radius ($R_{rear}$):** `63 13/16"` (`63.82"`) (clears `64 5/16"` wall with `1/2"` clearance)
- **Radial Depth:** `26 3/4"` (`26.75"`)
- **Chord:** `79 7/8"` (`79.87"`)
- **Arc Sweep:** `77.47°` (`1.3522 rad`)
- **Seat Deck Height:** `17"` (nominal) / `18"` (with compression)
- **Seat Cushion Thickness:** Adjustable `1"` to `7"` (nominal `5"` multi-density stack)
- **Channel Count:** `8` vertical wedge channels (`4` per half)
- **Nominal Channel Width:** `9 5/32"` (`9.15625"`)
- **Nominal Channel Height:** `36"` (above `17"` seat = `53"` overall crown)
- **Separation Gap:** `1 1/2"` center split between left and right modules
- **Fringe Drop:** `6"` Fabricut Rupi 158 bullion fringe on header at `7"` AFF (`1"` floor clearance)

### Layer System (Foam & Fabric Controls)
- **Back Rest:**
  - Board Substrate: `3/4"` Baltic birch shaped channels (`CHB-01` to `CHB-08`).
  - Foam Layer: Independent toggle & thickness adjustment (`1/2"` to `4"`, nominal `2"` HR polyurethane foam).
  - Fabric Layer: Independent toggle with **GP&J Baker Nympheus Velvet Emerald BP10814-2**. Sized with `+2 1/2"` stapling wrap.
- **Seat Deck:**
  - Frame / Deck Substrate: `3/4"` Baltic birch deck with 9-gauge sinuous wire springs (`4"` OC).
  - Foam Layer: Independent toggle & thickness adjustment (`1"` to `7"`, nominal `5"` stack).
  - Fabric Layer: Independent toggle with **Keyston Bros Vintage Ale SVI001 Vinyl**. Sized with `+2 1/2"` stapling wrap.
- **Frame Skeleton:** Toggleable CNC radial carcass showing joists `J1` to `J9` and stood ribs `R1` to `R9`.

---

## 3. Armrest Options & Trim Details
- **Laminated END Arm vs Slide-In:**
  - *Option A: Laminated END Arm:* Structural `1 1/2"` profile laminated from Baltic birch blanks with custom nose reveal.
  - *Option B: Slide-In End Panel:* Wall-adjacent flush slide-in terminal panel (`1 1/2"` stock).
- **Face Finish Options:**
  - Upholstered Face (Keyston Bros Vintage Ale vinyl wrap over `1/2"` foam).
  - Exposed Finished Wood (clear coat Baltic birch multiplex edge).
- **Fringe Returns:**
  - Fabricut Rupi 158 `6"` bullion fringe returns along both end arm bases (`27"` linear per side) aligning with front header at `7"` AFF.

---

## 4. Revised CNC Production Nesting Pack (8 Sheets)
> **IMPORTANT REVISION:** The revised CNC production pack nests on **8 sheets** (Claude artifact previously stated 9).

All production CNC cut sheets, nested SVGs, and files are linked on Chief e's box at `/workspace/willard_cst23_rev/`:
- **Cut List PDF:** `/workspace/willard_cst23_rev/Willard_CST23_RevPack_CutList.pdf`
- **Nested SVGs (25 Parts):** `/workspace/willard_cst23_rev/svg_nested_01.svg` through `svg_nested_25.svg`
- **8 Sheet Nest SVGs:** `/workspace/willard_cst23_rev/sheets/sheet_01.svg` through `sheet_08.svg`
- **Complete ZIP Archive:** `/workspace/willard_cst23_rev/Willard_CST23_Revised_Pack.zip`

### Sheet Breakdown (48" × 96" × 3/4" Baltic Birch)
1. **Sheet 1:** Base Plates & Bottom Rail Ribs (`BP-01`, `BP-02`, `BR-01`).
2. **Sheet 2:** Deck Substrate & Sinuous Spring Anchor Rails (`DK-01`, `DK-02`, `SR-01`, `SR-02`).
3. **Sheet 3:** Radial Joists `J1` to `J5` (Left half joist skeleton).
4. **Sheet 4:** Radial Joists `J6` to `J9` (Right half joist skeleton & blocking).
5. **Sheet 5:** Back Channel Boards `CHB-01` to `CHB-04` (Left Unit).
6. **Sheet 6:** Back Channel Boards `CHB-05` to `CHB-08` (Right Unit).
7. **Sheet 7:** Vertical Rake Stood Ribs `VR-01` to `VR-03` (`10°` back rake skeleton).
8. **Sheet 8:** Armrest Blanks Left & Right (`ARM-L`, `ARM-R`).

---

## 5. Tracked Open Items (Fractions Only)

| Item ID | Title | Current Specification | Permitted Range / Scope | Impact & Resolution Directive |
| :--- | :--- | :--- | :--- | :--- |
| **ITEM-1** | **Channel height range** | Nominal `36"` back channel height (above `17"` seat deck = `53"` overall crown height) | `24"` to `38"` | Field wall conditions at The Willard Scotch Bar and the `82"` overall cap require verifying clear height under sconces/moldings. Wood cut and foam cut are 1:1 true size; fabric cut adds `2"` to `3"` for top/bottom stapling. |
| **ITEM-2** | **Empty R24 dado pocket** | `R24"` circular dado pocket located in the curved base rib carcass | `24"` radius pocket | Resolve whether pocket is designated for wiring / LED under-bench light conduit chase, weight reduction, or alignment spline. Do not remove from CNC cut files until confirmed by lead fabricator. |
| **ITEM-3** | **Foam/board thickness** | Back channels: `1/2"` or `3/4"` Baltic birch board + `2"` HR foam. Seat: `5"` multi-density stack. | Back foam: `1"` to `4"` (nominal `2"`). Seat foam: `2"` to `6"` (nominal `5"`). Board: `1/2"` vs `3/4"`. | Affects inside seat depth clearance (`26"` radial) and back rake feel. Changing foam thickness changes fabric wrap dimensions. Foam cut = exact wood board cut size; Fabric cut = channel width + `2"` to `3"` for stapling wrap. |

---

## 6. Sizing Rules & Calculations Reference

```
+---------------------------------------------------------------------------------------+
| WILLARD CST-23 CUT SIZING RULES                                                       |
+---------------------------------------------------------------------------------------+
| 1. Wood/Board Cut = True Size                                                         |
|    Example: 9 5/32" × 36" (CHB-01 to CHB-08)                                          |
|                                                                                       |
| 2. Foam Cut = Same as Wood Cut                                                        |
|    Example: 9 5/32" × 36" × 2" (Channel foam matching backing board)                   |
|                                                                                       |
| 3. Fabric Cut = Channel/Foam Width + 2" to 3" for Stapling                            |
|    Width: 9 5/32" + 2 1/2" = 11 21/32"                                                |
|    Height: 36" + 2 1/2" = 38 1/2"                                                     |
|    Example Fabric Cut: 11 21/32" × 38 1/2"                                            |
|                                                                                       |
| 4. Separate Labeled Sizes:                                                            |
|    Wood / Board Cut (True Size, No Add-ons): 9 5/32" × 36"                            |
|    Foam Cut (Same as Wood Cut): 9 5/32" × 36" × 2"                                    |
|    Fabric Cut (Stapling Allowance Included): 11 21/32" × 38 1/2"                       |
+---------------------------------------------------------------------------------------+
```
