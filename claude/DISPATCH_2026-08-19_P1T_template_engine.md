# DISPATCH P1-T — DOCUMENT TEMPLATE ENGINE (McLean as reference implementation)

Authored 2026-08-19. **Supersedes the architecture section of
`DISPATCH_P1_presentation_engine.md`** — that dispatch had no proven reference
artifact and would have had to invent the sheet language from the standard.
McLean RevA is that artifact: founder-approved, rendered, 11 sheets. P1's
fixtures (Willard ONE-PIECE, Bozzuto board) survive unchanged and are folded in
at P1-T·e.

**Purpose, in the founder's words:** this is the template for any future request
to MAX involving a document of this kind. MAX gets the tools; the template
produces a previously-designed model of document — estimate, invoice,
presentation sheet, board, measurement set — so the output is standardised.

**FRESH Claude Code session.** Single lane. Do not fire alongside the drapery
R4 corrections — R4 renders into the layout this dispatch replaces, so R4 waits.

---

## FOUNDER ACTION BEFORE FIRING

Stage the McLean source zip to EmpireDell by **download, never paste**
(byte-exactness — this rule has been earned three times). It contains
`mclean_drapery_set_generator.py` (1,201 lines) and
`McLean_Whittington_Drapery_Elevations_RevA.pdf`.

Place at `~/empire-repo-main/reference/mclean/`. The nine site JPEGs are
**deliberately not staged** — photos are per-job upload from here on (P1-T·b).

---

## PASTE INTO M3 (fresh session)

```
Check /model first — confirm M3, not a silent downgrade. Read CLAUDE.md fully.
Repo: ~/empire-repo-main, branch feature/drawing-standard. Canonical paths
only; ~/empire-repo is a STALE FORK.

INFRA RULES: backend restart is `systemctl --user restart empire-backend` and
NOTHING else. Never hand-start uvicorn or bind :8000. Never stop
opencode-remote.service (HERMES). The system empire-backend.service is masked
— leave it.

TASK: P1-T — build the Document Template Engine. One spec object in, a
standardised Empire document out, across five document types. The reference
implementation is reference/mclean/mclean_drapery_set_generator.py, which
produced a founder-approved 11-sheet set. Work in phases. STOP at each 🛑.

--- STEP 0 · VERIFY, THEN AMEND, THE STANDARD ---

  md5sum EMPIRE_CLIENT_DOC_STANDARD.md
  # MUST print e6fde3cd1150260834987d760fdf8417 (committed cc2e31b)

If the md5 differs: 🛑 STOP and report. Do not proceed against an unverified
standard and do not regenerate it from memory.

Read it fully, then AMEND it with the five doctrine blocks below. Recommit,
record the NEW md5, and in the SAME COMMIT update the expected md5 inside
claude/DISPATCH_P1_presentation_engine.md — its STEP 0 hard-refuses on
mismatch and will break otherwise. Grep-verify both.

  AMENDMENT 1 · BUSINESS ADDRESS (founder 2026-08-19)
  Full address on all documents. Single spec key, never typed twice.
    address = "5124 Frolich Ln"
    locale  = "Hyattsville MD 20781"
  Footer letterhead zone renders:
    NELMA'S WORKROOM · 5124 FROLICH LN · HYATTSVILLE MD 20781
  "POWERED BY EMPIRE WORKROOM" is DROPPED FROM THE FOOTER — it already
  appears in the header band on every sheet. Full address in both places is
  redundant and doubles collision exposure.
  ⚠️ The footer letterhead zone has a collision history (R3-1: a long address
  defeated a hand-tuned W/2+0.72" nudge). The zone-gap gate MUST be re-proven
  against this longer string, with the pre-amendment layout as the negative
  fixture.

  AMENDMENT 2 · CONFLICT RULE — parts disagree with the whole (founder
  2026-08-19, applies to EVERY occurrence in EVERY document type)
  When tagged parts sum to something other than the tagged overall:
    1. Geometry resolves to the PARTS SUM, not the tagged overall. Parts are
       the better record — each was measured; the overall is usually one long
       pull.
    2. Every dimension touched by the conflict prints with "APPROX." after it.
    3. The sheet carries a note: not final measurements, verify before
       fabrication.
    4. THE BUILD CONTINUES. No refusal. No gold alarm.
    5. The field-tagged overall is preserved as one quiet line in FIELD CHECK
       — the field record, not a flag. (If a later tape returns the original
       number we need to know where the parts sum came from.)
  Worked example, Living Room centre wall: tagged 222" overall, three windows
  tagged 77½ + 69¼ + 78¼ = 225". Wall draws 225" APPROX., windows draw true
  size, FIELD CHECK records "field sheet tagged 222" overall".
  NEVER squeeze parts to fit a tagged overall. That is fabrication.

  AMENDMENT 3 · APPROX. SCOPE
  "APPROX." attaches to DERIVED and CONFLICTED dimensions only. Clean
  field-tagged dimensions print bare. If every number reads approximate the
  marker means nothing.
  "not tagged" is a DIFFERENT state and is unaffected — untagged still prints
  as untagged, and untagged geometry still draws schematically with the dashed
  gold edge.
  Consequence: the bay moulding 2" delta and the Living Room 3" delta both
  become APPROX. dimensions and LEAVE the open-items alarm list.

  AMENDMENT 4 · COUNTS DERIVE ONCE
  Any quantity appearing in more than one place in a set is computed once and
  read everywhere. Cover index, schedule totals and per-sheet counts are the
  same derivation, never independent ones.
  Root cause being fixed: McLean RevA prints 21 on the cover index (counts
  drawn windows) and 22 in the schedule (sums SCHEDULE quantities). The gate
  that saw it was INFO-only and emitted anyway.

  AMENDMENT 5 · TEXT METRICS ARE RECORDED AT DRAW TIME
  Text bounding boxes are captured when the string is placed, never recovered
  by parsing the emitted PDF. Parse-back couples the gate to the reader's
  tokenisation — that is the exact blind spot that cost the R2→R3 round when
  a letterspaced label merged into one pdfplumber word.
  The McLean reference already does this (its PLACED list). Adopt it and
  RETIRE the pdfplumber parse-back path in the drawing lane.
  Note: this makes text-vs-text collision detection sound. It does NOT cover
  text-vs-graphic — see gate G3 below.

  AMENDMENT 6 · DIMENSION NUMBERS READ HORIZONTALLY (founder, McLean session)
  "In all docs make numbers on dimensions horizontal." A vertical dimension
  BREAKS ITS OWN LINE at mid-height and sets the number horizontally —
  standard drafting convention. NO ROTATED TYPE anywhere in any set, any
  document type.
  Consequence already handled in the reference: gutters and the right-hand
  stack pitch resize to suit, so stacked vertical numbers clear each other
  (see the Laundry sheet, 15" and 79"). Port that sizing logic, do not
  reinvent it.
  GATE: assert zero rotated text transforms in the emitted set.

  AMENDMENT 7 · SITE PHOTO PRIVACY (founder, McLean session)
  Any person appearing in a site photo is blurred before embedding.
    - Heavy Gaussian blur with a SOFT-FEATHERED mask — a hard rectangle reads
      as redaction and looks wrong on a client document.
    - The blur is BAKED INTO THE JPEG PIXELS before embedding, never applied
      as an SVG/PDF overlay. An overlay can be stripped out of the emitted
      file; pixels cannot.
    - The blurred region covers the person and adjacent floor only. It must
      NEVER cover a window, trim, moulding or anything else the sheet
      references or dimensions.
  Because photos are now per-job upload (P1-T·b), this is a REQUIRED STEP in
  the photo intake path, not a manual remembering. If a photo cannot be
  processed, it degrades to "NO SITE PHOTO ON FILE" rather than embedding
  unprocessed.

🛑 STOP. Report the new md5, the amended sections, and confirmation that the
P1 dispatch's expected hash was updated in the same commit.

--- P1-T·a · MAP THE REFERENCE (read-only, no refactor yet) ---

Evidence first. Read reference/mclean/mclean_drapery_set_generator.py fully
and produce reports/2026-08-19_mclean_map.md answering:
  - Which functions are CHROME (reusable on every document), which are BAND
    (photo/data/check three-column), which are BODY (elevation viewport),
    which are CONTENT (window-opening panel renderer, family-specific), and
    which are GATES.
  - Every hardcoded path, font path and sandbox assumption. Known so far:
    PHOTO_DIR "/home/claude/ph/", output "/mnt/user-data/outputs/", fonts at
    "/usr/share/fonts/truetype/dejavu/". VERIFY the DejaVu faces exist on
    EmpireDell before anything else — every bounds and collision gate depends
    on those metrics, and a substituted face silently invalidates both.
  - Every place a number is typed twice.
Do not refactor in this step. 🛑 STOP and report the map.

--- P1-T·b · SEPARATE THE LAYERS ---

Create backend/app/presentation/template/ with the layering the map found:

  chrome.py     header band, footer zones, palette, type scale, letterspacing,
                cover + index pattern, rev/date stamping
  band.py       reference band — site photo | field data | check-list
  body/         one per DOCUMENT TYPE (see P1-T·d)
  content/      one per CONTENT FAMILY. Port McLean's panel renderer as
                content/window_openings.py — it is family-specific, not
                general. Drapery, roman, bench/banquette, wall unit are
                siblings added later, NOT this dispatch.
  gates.py      travels with the template, never optional
  spec.py       schema + validation
  assemble.py   orders sheets, stamps one rev across the set, refuses mixed-rev

TWO AXES, kept independent — do not let them collapse into one enum:
  DOCUMENT TYPE  = what kind of document (five, listed in P1-T·d)
  CONTENT FAMILY = what is being drawn or priced
McLean is measurement_set × window_openings. An estimate for the same job is a
different TYPE over the same CONTENT. A drapery presentation sheet is the same
TYPE over different CONTENT. If a change requires touching both axes at once,
the separation is wrong — stop and report rather than working around it.

PHOTOS ARE PER-JOB UPLOAD (founder 2026-08-19). No fixed photo set, nothing
hardcoded. Spec carries a list of (path, caption) per sheet key. A missing
file degrades to "NO SITE PHOTO ON FILE" — never a crash. The reference's
bare open() is the bug being fixed; its empty-list path already renders
correctly (Laundry sheet) and is the model.

Photo intake path (photos.py) does, in order: EXIF transpose · resize to
~1100px longest edge · JPEG q72 optimised · PRIVACY BLUR per Amendment 7 ·
base64 embed. The reference already does everything except the blur as a
repeatable step — port it, add the blur, and make it the only way a photo
enters a document.

--- P1-T·c · BUILDER INTERFACE (this is the MAX seam) ---

Every builder is a pure function:

    build(spec) -> BuildResult

  BuildResult carries: pdf bytes | path, the gate report, and the derived
  quantities used.
  Missing spec data raises SpecIncomplete(missing=[...]) — a STRUCTURED
  refusal listing exactly what is absent.

REPLACE sys.exit(1) EVERYWHERE. A process exit cannot be orchestrated; MAX
must receive either a document or a list of what to go ask the founder for.
Remove module-global mutable state (the reference's PLACED global, cleared
per sheet) — builders must be pure and independently callable.

--- P1-T·d · THE FIVE DOCUMENT TYPES ---

  measurement_set      cover · index · room/elevation sheets · schedule
  estimate             line items, quantities, pricing
  invoice              estimate lineage + payment terms and status
  presentation_sheet   client-facing single or short set
  board                material/finish board (Bozzuto sofa #825 fixture)

These names become tool arguments — do not rename without a founder ruling.
Only measurement_set has a proven reference. Build it fully. For the other
four, build the TYPE SCAFFOLD against shared chrome and raise SpecIncomplete
until their fixtures land; do NOT invent their body layouts from imagination.
estimate and invoice must read the canonical quote store through the shared
resolve_quote() — never a copy, never legacy JSON directly.

--- P1-T·e · GATES (six, all with negative fixtures) ---

  G1 bounds        every string inside the page frame; and ZERO rotated text
                   transforms in the set (Amendment 6)
  G2 collisions    no two strings overlap (draw-time bboxes per Amendment 5)
  G3 text/graphic  NEW — text does not overlap dimension lines, photos or
                   fills. The reference checks text-vs-text only.
  G4 layout math   every printed arithmetic statement recomputes and agrees;
                   conflicts resolve per Amendment 2 and are NOT failures
  G5 counts        NEW, replaces the INFO-only check — every count appearing
                   more than once derives from one source and agrees.
                   NEGATIVE FIXTURE: the current McLean 21-vs-22 split MUST
                   fail this gate.
  G6 rev + address single rev stamp across the set; full address present in
                   the footer letterhead zone of every sheet; zone gaps hold
                   against the longer string (Amendment 1)

A negative fixture that fails for the WRONG reason proves nothing — this cost
an hour previously when a gate was weakened to accommodate a malformed
fixture. For each gate, state which fixture trips it and why.

--- P1-T·f · ACCEPTANCE: REGENERATE McLEAN ---

Feed the McLean spec through the new engine. Expected differences from RevA,
and NOTHING ELSE:
  1. Centre wall carries THREE windows at 77½, 69¼, 78¼ (founder ruling
     2026-08-19). Wall draws 225" APPROX. per Amendment 2; FIELD CHECK
     preserves "field sheet tagged 222" overall".
  2. Set total is 24 openings. Cover index sheet 05 reads 6 (left 2 + centre
     3 + right 1). Schedule LRB-2 goes qty 1 → 3. Both derive from one count.
  3. Footer carries the full address; "POWERED BY EMPIRE WORKROOM" gone from
     the footer only.
  4. Photos absent → "NO SITE PHOTO ON FILE", no crash.
  5. Bay moulding delta and Living Room delta print APPROX. and leave the
     open-items list.
Any OTHER visual difference is a port regression — report it, do not accept it.

--- P1-T·g · REGISTER ONE TOOL, BOTH CHAT DOORS ---

One tool, same pattern as EMPIRE_CATALOG, registered on BOTH doors
(router.py chat and stream paths). Arguments: document type, content family,
spec, photos. Returns BuildResult or SpecIncomplete.

MAX MUST NOT KNOW THE HOUSE VOICE. MAX says "produce the McLean-style
measurement set for job X". MAX does not know the gold hex, the footer zone
gaps, that untagged geometry draws dashed, that conflicts resolve to the parts
sum, or that we write "cove fascia" and never "glued". That is specialist
knowledge belonging to whichever agent owns client documents. Keep the
boundary or it erodes on the first exception.

THEN: full suite green, negative proof shown for every gate, ONE commit,
report found/changed/tests/commit with the new standard md5 stated. 🛑 STOP
for founder eyeball on the regenerated McLean set.
```

---

## RECORDED FOUNDER DOCTRINE (2026-08-19)

- Full business address on all documents: **5124 Frolich Ln, Hyattsville MD 20781**.
- **Conflict rule:** parts sum wins, conflicted dimensions print APPROX., a
  not-final-measurements note appears, the build continues. Every occurrence,
  every document type.
- APPROX. attaches to derived and conflicted dimensions only.
- Living Room centre wall is **three windows** at 77½, 69¼, 78¼ → set total 24.
- Site photos are per-job upload, included for context; never a fixed set.
- **Dimension numbers always read horizontally** — vertical dims break their
  own line at mid-height. No rotated type in any document.
- **People in site photos are blurred** — feathered Gaussian, baked into the
  pixels before embedding, never covering anything measurable.
- Five document types: measurement set · estimate · invoice · presentation
  sheet · board.
- MAX is an orchestrator: he requests the document, the specialist owns the voice.

## STILL OPEN — founder answers needed, none block this dispatch

1. **Detail A** (drapery lane) — keep with a stated job, or delete? Parked
   until the template lands.
2. **Mockup overlay** — founder describes quotes retaining reference pictures
   with treatments overlaid, and the quoting system producing final mockups.
   **Nothing in STATE or BACKLOG records this capability.** Confirm whether it
   exists today or is to be built; it is a large scope difference and must not
   be assumed present.
3. **Did McLean RevA go to Whittington Design?** If still in hand this reissues
   as REV A. If it went out it is REV B and the count change (21/22 → 24) must
   be stated in the transmittal.
4. **C7** — McLean / Whittington Design is a live client job with no register
   entry. 22→24 openings, field-measured 1 July, 11-sheet set issued 19 Aug.
   Also a second candidate for **C3 "DC-metro drapery/romans prospect"**
   alongside Hudson & Crane — settle which, or retire C3.

## BOARD UPDATES ON COMPLETION

- **P1** — architecture section superseded by this dispatch; fixtures survive.
- **W2 / S3** — the R6 woodwork engine dispatch shares this template layer.
  Check for overlap before firing it; do not build two chrome layers.
- **D3** — drapery R4 corrections (D-R4-1…4) unblock once the template lands
  and render into the new layout, not the old one.
- **A5 (new AT-RISK)** — Amendments 6 and 7 were founder rulings that existed
  **only inside a chat session** and appeared in no project file. Both would
  have been silently dropped by this port. The rule "nothing important lives
  in chat" has now been earned a fourth time, and on the strategic side of the
  line rather than M3's. **Standing fix: every founder ruling is written to a
  project file in the session it is made** — not at the end, not next session.
  The dispatch "RECORDED FOUNDER DOCTRINE" block already enforces this for M3;
  the same discipline must apply to any chat session that produces an artifact.

## AUDIT FOLDED IN — verify during P1-T·a

The D-R3 report (commit `fc42fe3`) is thin on six items. M3 is already reading
that code during the map step; confirm rather than assume, and report each:
  1. D-R3-3 — are the grommet / rod_pocket constants actually PRINTED on the
     sheet's notes block marked ASSUMED — FOUNDER VERIFY? An assumed constant
     invisible on the sheet is an invented number.
  2. D-R3-3 — does each heading style set its own DRAPE_PROJECTION_IN entry?
  3. D-R3-4 — unknown SKU → neutral gray + "FABRIC: TBC — CONFIRM BEFORE CUT"?
  4. D-R3-4 — spec-level hex override, pattern field, repeat direction drawn
     per orientation, orientation printed in the title column?
  5. D-R3-2 — does DETAIL A carry a spacing dimension and a stated
     magnification? (Decides whether D-R4-4 is a legibility fix or a rebuild.)
  6. The sail negative fixture was REBUILT this round. Confirm it still trips
     on plumb/uniform ONLY. A negative fixture failing for the wrong reason
     proves nothing — this has already cost an hour once.
Also: "57/57 in tests/test_drawing_vector_b2.py" is ONE FILE, not full suite
green, and the register already carries an open item about ~90 non-drawing
test errors claimed pre-existing WITHOUT stash-proof. **Standing rule: a
scoped test count is never reported as suite green, and "pre-existing"
requires stash-proof.**
