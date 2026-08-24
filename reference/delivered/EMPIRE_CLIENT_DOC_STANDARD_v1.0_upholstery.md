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
