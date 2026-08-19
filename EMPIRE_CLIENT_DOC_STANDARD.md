# EMPIRE CLIENT DOCUMENT STANDARD v1.0
**Scope:** built-upholstery jobs — banquettes, benches, headboards, wall panels, cornices.
Companion to `EMPIRE_DRAWING_STANDARD.md` (shop drawings). This governs what the **client** receives.

Reference implementation: Willard CST-23 Style B set (07/2026).

---

## 1. THE ONE RULE

**One spec object drives every sheet. Nothing is typed twice.**

Every number on every sheet — dimensions, yardage, fringe runs, cut maps — either lives in
the spec or is *computed* from it. If a dimension changes, every sheet and every order
quantity changes with it, automatically.

*Why this rule exists:* the Willard set shipped with sheets built at two different revisions.
B0–B4 described a two-unit bench (17" seat, 53" overall, fringe front + both sides = 117" run);
the ISO sheets described the final one-piece bench (18" seat, 55" crown, fringe front only ≈ 72").
Sheet B5 therefore ordered **4.0 YD of Rupi 158 for a job that needs ~2.0 YD**, and mapped vinyl
cuts for two outside backs that no longer exist. Both sheets were internally correct. The set
was not. Templates alone would not have caught this; a shared spec would have.

---

## 2. SHEET SET

| Sheet | Title | Contents |
|---|---|---|
| **B0** | Cover · Material Story | Job header, material cards (real fabric/trim images, mill + SKU + width + repeat + FR status), sheet index, key dimensions, open-revision callout |
| **B1** | Elevation & Section | Developed front elevation at stated scale + side section, fully upholstered |
| **B2** | Floor Plan | True radius (never exaggerated), setting-out block, arc/chord/arc-rise, segment schedule |
| **B3** | Assembly Build-Up | Exploded sequence, numbered assembly order |
| **B4** | Foam & Frame | Frame spec (rib spacing, radii, joinery), foam build-up by zone, section detail at typical condition |
| **B5** | Yardage / COM | Per-material cut schedule, calc shown, order quantity, cut-map diagram, COM ship-to |
| **B6** | Flammability | Component compliance table, code path note, documents on file, pending items |
| **ISO-1** | Isometric Views | 3+ camera angles from the parametric model, READ list, current dimensions |
| **ISO-2** | Rear / Site Fit | Rear view, site set sequence, delivery envelope check |

Small jobs may omit B3/B4. **B0, B1, B2, B5, B6 are mandatory** on any job with COM.

---

## 3. SPEC OBJECT

```
project_spec = {
  "rev": "C", "rev_date": "2026-07-17", "quote": "EST-2026-110",
  "client": {...}, "site": {...},
  "geometry": {            # the single source for all sheets
     "build": "one_piece", "wall_cap_in": 87.0, "radius_back_in": 120.0,
     "seat_h_in": 18.0, "cushion_in": 5.0, "crown_h_in": 55.0,
     "depth_overall_in": 34.75, "seat_depth_clear_in": 24.0,
     "channels": {"count": 8, "width_in": 9.15625, "height_in": 36.0},
     "arm": {"width_in": 3.0, "top_h_in": 24.0, "continuous": true},
     "fringe": {"drop_in": 6.0, "header_h_in": 7.0, "runs": ["front"]}
  },
  "materials": [ {role, mill, sku, width_in, repeat_in, fr_status, image}, ... ],
  "assembly": [...], "frame": {...}, "foam": {...},
  "flammability": [...], "site_sequence": [...]
}
```

**Derived — never typed:**
- fringe order = f(runs, arc lengths, +10%)
- velvet panels = f(channel count, channel h, repeat) → nesting basis
- vinyl = f(build, seat/back/arm/end areas, +curve waste)
- chord, arc rise, front-face arc = f(radius, arc length)
- delivery envelope = f(overall W × D × crown)

---

## 4. RULES

1. **True scale on plans.** Curvature exaggeration is permitted on ISO/assembly views only, and must be labeled.
2. **Assumptions are printed.** Anything not field-verified carries an explicit flag with the verification method (e.g. arc rise = string-across-chord check).
3. **Open decisions get a callout box**, not silence — see B0 "REV — CAP RESOLVED".
4. **Materials show real images**, not color swatches, wherever a scan or mill photo exists.
5. **FR status per component**, with the code path stated and pending items listed.
6. **Every sheet carries rev + date.** A set with mixed revs is a defect — assembly must refuse to emit.
7. **Footer is fixed:** letterhead · FOR DISCUSSION — NOT FOR CONSTRUCTION · sheet number.
8. **Yardage sheets show the calc**, not just the answer, so the client/designer can audit it.

---

## 5. QC GATES (automated, pre-ship)

| Gate | Check |
|---|---|
| Bounds | no geometry or text outside the page |
| Collisions | no overlapping text (rotation-aware) |
| Integrity | rendered solids have no interior holes; left/right balance |
| Anchors | every leader terminates on the feature it names (pixel-verified) |
| Rev | all sheets share one rev stamp |
| Derived | recompute all quantities from spec; mismatch = fail |

---

## 6. IMPLEMENTATION PATH (MAX)

- `presentation/` package alongside `drawing/templates/`, one builder per sheet, each taking only `project_spec`.
- 3D views from the parametric mesh module (`empire3d.py` reference implementation) — same spec.
- MAX gathers spec conversationally, calls builders, assembles, runs QC gates, delivers.
- Client-facing delivery remains **founder-manual**. MAX assembles; the founder sends.

---

## AMENDMENTS (2026-08-19)

### AMENDMENT 1 · BUSINESS ADDRESS (footer letterhead)

Full business address on all documents. Single spec key, never typed twice.

```
address = "5124 Frolich Ln"
locale  = "Hyattsville MD 20781"
```

Footer letterhead zone renders:

```
NELMA'S WORKROOM · 5124 FROLICH LN · HYATTSVILLE MD 20781
```

"POWERED BY EMPIRE WORKROOM" is **dropped from the footer** — it already appears in the header band on every sheet. Full address in both places is redundant and doubles collision exposure.

⚠️ The footer letterhead zone has a collision history (R3-1: a long address defeated a hand-tuned W/2+0.72" nudge). The zone-gap gate MUST be re-proven against this longer string, with the pre-amendment layout as the negative fixture.

**Rule 7 amended:** "Footer letterhead zone carries full business address (`NELMA'S WORKROOM · 5124 FROLICH LN · HYATTSVILLE MD 20781`). No `POWERED BY EMPIRE WORKROOM` line — that text already appears in the header band."

---

### AMENDMENT 2 · CONFLICT RULE — parts disagree with the whole

When tagged parts sum to something other than the tagged overall:

1. Geometry resolves to the **PARTS SUM**, not the tagged overall. Parts are the better record — each was measured; the overall is usually one long pull.
2. Every dimension touched by the conflict prints with **`APPROX.`** after it.
3. The sheet carries a note: **not final measurements, verify before fabrication.**
4. **The build continues.** No refusal. No gold alarm.
5. The field-tagged overall is preserved as one quiet line in **FIELD CHECK** — the field record, not a flag. (If a later tape returns the original number we need to know where the parts sum came from.)

Worked example, Living Room centre wall: tagged 222" overall, three windows tagged 77½ + 69¼ + 78¼ = 225". Wall draws 225" APPROX., windows draw true size, FIELD CHECK records "field sheet tagged 222" overall".

**Never squeeze parts to fit a tagged overall.** That is fabrication.

---

### AMENDMENT 3 · APPROX. SCOPE

`APPROX.` attaches to **derived and conflicted** dimensions only. Clean field-tagged dimensions print bare. If every number reads approximate the marker means nothing.

`not tagged` is a DIFFERENT state and is unaffected — untagged still prints as untagged, and untagged geometry still draws schematically with the dashed gold edge.

Consequence: the bay moulding 2" delta and the Living Room 3" delta both become `APPROX.` dimensions and **leave the open-items alarm list**.

---

### AMENDMENT 4 · COUNTS DERIVE ONCE

Any quantity appearing in more than one place in a set is **computed once** and read everywhere. Cover index, schedule totals and per-sheet counts are the same derivation, never independent ones.

Root cause being fixed: McLean RevA prints **21** on the cover index (counts drawn windows) and **22** in the schedule (sums SCHEDULE quantities). The gate that saw it was INFO-only and emitted anyway. After this amendment it is a fail-gate (see Amendment-Gates below).

---

### AMENDMENT 5 · TEXT METRICS ARE RECORDED AT DRAW TIME

Text bounding boxes are captured when the string is placed, **never recovered by parsing the emitted PDF**. Parse-back couples the gate to the reader's tokenisation — that is the exact blind spot that cost the R2→R3 round when a letterspaced label merged into one pdfplumber word.

The McLean reference already does this (its `PLACED` list). Adopt it and **retire the pdfplumber parse-back path in the drawing lane.**

Note: this makes text-vs-text collision detection sound. It does **NOT** cover text-vs-graphic — see gate G3 below.

---

### AMENDMENT 6 · DIMENSION NUMBERS READ HORIZONTALLY

"In all docs make numbers on dimensions horizontal." A vertical dimension **breaks its own line at mid-height** and sets the number horizontally — standard drafting convention. **No rotated type anywhere in any set, any document type.**

Consequence already handled in the reference: gutters and the right-hand stack pitch resize to suit, so stacked vertical numbers clear each other (see the Laundry sheet, 15" and 79"). Port that sizing logic, do not reinvent it.

**GATE:** assert zero rotated text transforms in the emitted set.

---

### AMENDMENT 7 · SITE PHOTO PRIVACY

Any person appearing in a site photo is blurred **before embedding**:

- **Heavy Gaussian blur with a SOFT-FEATHERED mask** — a hard rectangle reads as redaction and looks wrong on a client document.
- The blur is **baked into the JPEG pixels** before embedding, never applied as an SVG/PDF overlay. An overlay can be stripped out of the emitted file; pixels cannot.
- The blurred region covers the person and adjacent floor only. It must **NEVER** cover a window, trim, moulding or anything else the sheet references or dimensions.

Photos are per-job upload. If a photo cannot be processed, it degrades to **`NO SITE PHOTO ON FILE`** rather than embedding unprocessed.

**Rule 4 amended:** "Materials show real images, not color swatches, wherever a scan or mill photo exists — and any person in a site photo is soft-feathered Gaussian-blurred and baked into the pixels before embedding (Amendment 7)."

---

## AMENDMENT-GATES (2026-08-19)

These gates strengthen Section 5's gate table for the amended rules. All have negative fixtures.

| Gate | Check |
|---|---|
| Bounds | every string inside the page frame; AND zero rotated text transforms in the set (Amendment 6) |
| Collisions | no two strings overlap (draw-time bboxes per Amendment 5) |
| **Text/graphic** *(new)* | text does not overlap dimension lines, photos or fills — the reference checks text-vs-text only |
| **Layout math** *(strengthened)* | every printed arithmetic statement recomputes and agrees; conflicts resolve per Amendment 2 and are **NOT failures** (the build continues) |
| **Counts** *(new, replaces INFO-only)* | every count appearing more than once derives from one source and agrees. **Negative fixture:** the McLean RevA 21-vs-22 split MUST fail this gate |
| **Rev + address** *(new)* | single rev stamp across the set; full address present in the footer letterhead zone of every sheet; zone gaps hold against the longer string (Amendment 1) |
| **Photo privacy** *(new)* | every embedded site photo has the privacy blur baked into its pixels; the blurred region does not cover any measurable feature (Amendment 7) |

