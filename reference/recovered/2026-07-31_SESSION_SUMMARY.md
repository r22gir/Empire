# Session Summary — Label Station, Part Labels & Shop Drawings

*For import into the Workroom Claude Project. Written so a future session can pick up
cold. Every figure below was verified by tool call during the session, not inferred.*

---

## 1. What was built

Three separable systems came out of this session. Two are food-business specific; the
third and fourth are directly reusable for Empire Workroom.

| # | System | State | Reusable for Workroom? |
|---|---|---|---|
| 1 | **Weigh & Label** web app — price by weight, print a label | **Live** at `label.empirebox.store/label/` | Only if you sell by weight |
| 2 | **Delicias Tolimenses** landing page — QR destination | Built, **not deployed** | No — template only |
| 3 | **Thermal part-label generator** — Python/PIL | Working, R6 | **Yes — directly** |
| 4 | **Shop drawing set generator** — SVG → PDF | Working, 4 sheets | **Yes — directly** |

Deliverable files: `label_generator.py`, `drawing_set_generator.py`,
`weigh-and-label.html`, `label_station.py`, `delicias-tolimenses.html`,
`sofa-surround-drawings.pdf`, `R6-part-*.png`.

---

## 2. Thermal part labels — the reusable recipe

`label_generator.py`. This is the piece most worth carrying into Workroom: any cut part,
any job, gets a label that traces back to the cut sheet.

### Hard specs, learned the hard way

- **320 × 240 dots = 40 × 30 mm at 203 dpi.** Render at exactly one image pixel per
  printer dot. Oversampling let the phone app rescale, and rescaling is what lets it crop.
- **12-dot (1.5 mm) quiet margin on all four sides.** Thermal heads cannot reach the edge
  and the roll wanders. Drawing edge-to-edge got the shop bar shaved off in print.
- **1-bit PNG, pure black and white.** No greys — thermal heads dither them to mush.
- **PIL rectangles are inclusive.** `X1 = W - MARGIN - 1`, not `W - MARGIN`, or you lose
  a dot on the right edge.
- **Print density 7–8 in Katasymbol, not the default 4.** A washed-out label is almost
  always the density setting, not the file.
- **Reversed (white-on-black) bars are heat-hungry** — the shop bar runs ~76% solid. If
  density 8 still prints light, switch the bar to black-on-white with a heavy rule.

### Layout that works

Big part letter in its own left column (~13 mm tall, readable across a bench), vertical
divider, then designation over L and W dimensions right-aligned so digits stack column to
column. One design per part *type*; print N copies. Saving 30 images to Photos is far
slower than printing one image 30 times.

### Workflow (iPhone, no computer)

App renders → **long-press → Save to Photos** → open Katasymbol → print from camera roll.
This is deliberate, not unfinished: **iOS Safari has no Web Bluetooth and browsers have no
raw sockets**, so no web app can drive a Bluetooth label printer directly. The only way to
remove the step is an AirPrint printer (Brother QL-810W, ~$170).

---

## 3. Shop drawing sets — the reusable recipe

`drawing_set_generator.py`. Produces a 4-sheet PDF: presentation, dimensioned
elevations + plan, isometric, hardware detail.

### Pipeline

```
python (real inches)  →  SVG string  →  cairosvg.svg2pdf(dpi=72)  →  pypdf merge
```

- **`dpi=72` is essential** — one SVG unit becomes one PostScript point. Default 96 dpi
  silently shrinks Letter to 594 × 459 pt.
- Pages built at **792 × 612 pt = 11 × 8.5 in landscape**.
- All sheets read from **one set of module-level constants**, so they cannot drift apart.

### Isometric projection

Viewer front-right-above, `y = 0` at wall and increasing toward viewer:

```python
sx = k * cos(30) * (x - y)
sy = k * (sin(30) * (x + y) - z)
```

Visible faces are **top, front, right**. Draw back-to-front by hand — furniture behind and
ghosted first, cabinetry last. Distinct fills per face orientation are what make it read
as solid rather than wireframe.

**Two isometric failures worth remembering.** First attempt was bare panels floating in
white space — no ground plane, no context furniture, so it looked like a wireframe. Second
attempt had the bounding box driven by the carpet plane, so the cabinetry filled only 44%
of the sheet; computing the bbox from *actually drawn* points fixed it to 93%.

### Verification discipline — the part that actually mattered

Do not eyeball drawings. Three checks used repeatedly, each of which caught a real error:

1. **Assert the geometry before drawing.** `assert LEV + BASE_H + TOWER_H == H_TOT`.
2. **Compare drawn area to computed area.** Caught two missing parts in a nest.
3. **Project a known corner, rasterise, sample that pixel.** Confirmed the base units were
   actually rendering in front of the ghosted sofa rather than assuming the draw order was
   right.

Also: **regex over your own generated markup misses whitespace variants.** A rect check
silently skipped two parts because the source had extra spaces between attributes.

---

## 4. Reference job — walnut sofa surround

Kept because it is the worked example behind both generators.

**Overall 126" W × 109" H × 17 31/32" D.** Walnut plywood, 23/32" actual.

| Stack | |
|---|---|
| levelers | 1/2" |
| base unit | 20 1/4" |
| shelf tower | 88 1/4" |
| **total** | **109"** |

- Bay 80" clear, sofa 79" — 1/2" a side
- Overhead box 24" high × 8" deep, underside at 85" AFF
- Tower shelves at 85, 71, 57, 43, 29 (14" pitch) + top cap at 109 — bottom gap 8 1/4"
- Base: 2" toe kick + 18 1/4" full-overlay door
- Doors 23" × 18 1/4", **zero reveal** — flush with the carcass sides

### Part schedule (R6, 32 pieces)

| | Part | Qty | L | W |
|---|---|---|---|---|
| A | Shelf Side Panel Left | 2 | 88 1/4" | 8" |
| B | Shelf Side Panel Right | 2 | 88 1/4" | 8" |
| C | Base Unit Bottom | 2 | 21 9/16" | 17 1/4" |
| D | Base Unit Top | 2 | 21 9/16" | 17 1/4" |
| E | Shelf | 12 | 21 9/16" | 8" |
| F | Base Unit Side Panel Left | 2 | 20 1/4" | 17 1/4" |
| G | Base Unit Side Panel Right | 2 | 20 1/4" | 17 1/4" |
| H | Door Left | 1 | 18 1/4" | 23" |
| I | Door Right | 1 | 18 1/4" | 23" |
| J | Base Unit Back (inset) | 2 | 18 13/16" | 21 9/16" |
| K | Overhead Panel | 2 | 80" | 8" |
| L | Toe Kick | 2 | 21 9/16" | 2" |

### Carcass arithmetic to reuse

- **Inner width** = overall − 2 × thickness. Top, bottom and shelves all take this.
- **Inset back** = inner width × (height − 2 × thickness).
- **Overall depth** = carcass depth **+ door thickness** when the door is full overlay.
  This was missed once and caught by the founder.
- **0.71" stock is 23/32" (0.7188), not 13/16" (0.8125).** Those differ by 3/32", which is
  3/16" across a carcass. 18 mm is 0.7087 if the caliper really reads 0.709.

### Hardware — frameless full overlay

**No inside post or centre stile.** That is a face-frame detail. The hinge plate screws
straight to the inside face of the side panel. 35 mm cup, 13 mm deep, cup centre 7/8" from
the door edge, 0 mm mounting plate, two hinges per door. **Pivot sits at the front outer
corner of the side panel**, not the door edge. Door is wider than tall here, so the load is
cantilevered — consider a third hinge.

---

## 5. EmpireDell / infrastructure ground truth

Verified 2026-07-26. Where a belief was wrong, the correction is stated so it does not get
re-learned. See also `CLAUDE_label_station.md` and `DEPLOY_LABEL_STATION.md`.

- **Cloudflare tunnel `empire-main` is DASHBOARD-MANAGED.** `empire-main-local.yml` is
  decorative — editing it changes nothing. `ExecStart` uses `--config` not `--token`, which
  looks local; the tell is `version=N` in the cloudflared log. **Add hostnames via Zero
  Trust → Networks → Tunnels → Routes.** This cost about an hour.
- `/home/rg/empire-repo-main` and `/ssd/rg/empire-repo-main` are the **same filesystem**
  (bind mount). `/home/rg/empire-repo` is the **main worktree** — it owns the shared
  git object store and the live venv/data. Treating it as drift (the pre-2026-08-24
  read) destroys every local branch and stash on the box. Correction:
  `reports/2026-08-24_D23_stale_fork_census.md`.
- Real FastAPI entry is **`backend/app/main.py`**. `backend/main.py` is a 26-line stub;
  adding routers there is dead code.
- The live backend is a **hand-started process, not systemd**. `empire-backend.service`
  points at the legacy tree and is inactive. **On reboot systemd starts the wrong code.**
  Largest known fragility.
- `sqlite3` CLI is not installed — use `venv/bin/python3 -c "import sqlite3; ..."`.
- `curl -I` sends HEAD; FastAPI GET-only routes answer **405**. That is correct, not a
  failure.

---

## 6. Working conventions that earned their keep

- **Verify an edit landed; never assume a replacement matched.** A silent no-op string
  replacement shipped a broken catalog sync — the target function had been rewritten in an
  earlier pass, the patch matched nothing, no error raised. Grep after editing.
- **Say when something is wrong rather than working around it.** The 24" overhead / tower
  shelf misalignment was exactly one material thickness; the depth omission was one door
  thickness. Both were caught by the founder, not by me — both would have been caught
  earlier by asserting against the construction logic instead of the drawing.
- Agents must **never email clients**. Automated mail is internal-to-founder only.
- Prefer stopping and reporting over improvising when reality contradicts the brief.

---

## 7. Open items

1. **systemd / supervision** — give the label station its own unit and port so an
   EmpireBox restart or reboot does not take down label printing. Top infrastructure risk.
2. **QR placeholder** — labels still encode `https://example.com/menu`. Replace before
   selling anything. Keep the URL under ~47 characters for a crisp code at 203 dpi.
3. **Bare-hostname redirect** — Cloudflare Redirect Rule, `label.empirebox.store` path `/`
   → `/label/`, 301. Without it the bare hostname downloads a JSON file.
4. **Landing page not deployed** — `delicias-tolimenses.html`. Photos are Wikimedia CC
   BY-SA placeholders; replace with real food photos. Order email is a placeholder;
   Cloudflare Email Routing is the cheapest route to a working address.
5. **Sofa access** — 79" sofa in an 80" bay. Confirm it can be placed before the towers go
   in; at 1/2" a side it will not slide past them afterwards.
6. **Door swing** — needs 23" clear. Check against the sofa arm; may want 165° hinges.

---

## 8. Adapting to Empire Workroom

The two generators transfer with almost no change:

- **`label_generator.py`** — swap the `PARTS` table. Drapery and upholstery cut parts want
  the same treatment: a letter that ties back to the cut sheet, the designation, and two
  dimensions. For drapery you would likely want *finished width × finished length* rather
  than L/W, and possibly a fabric/room field. The layout has room for one more line if the
  designation is short.
- **`drawing_set_generator.py`** — the elevation, plan and title-block machinery is
  generic. The isometric routine is furniture-specific but the projection is not.
- The **EMPIRE_DRAWING_STANDARD** discipline held up well here: assumptions printed in a
  notes block, no invented dimensions, layout math that closes. Worth extending the
  standard to require the three verification checks in §3.
