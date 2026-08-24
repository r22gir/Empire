# DISPATCH R16 — THE WOODCRAFT PRODUCT LINE

**Founder's verdict on the current catalogue, 2026-08-23:** *"very poor content
and design, basically a placeholder — need some real products with more
professional and detailed information, instructions and other relevant
information."*

He is right. `XCarve_Series_Catalog.pdf` lists five designs — stool, shelf
brackets, serving board, wall organizer, plant stand — with sizes, part counts,
nesting dimensions and CAM steps. That is **shop paperwork for someone who
already owns the machine.** It is not a product line. Any X-Carve owner could
make those, which means none of them is a reason to buy from WoodCraft.

**This is a product-development round, not a code round.** Most of the missing
content is trade knowledge — species, grade, finish, load rating, tolerance,
what tears out on the visible face. **M3 MUST NOT INVENT ANY OF IT.** A
fabricated load rating or a made-up finish schedule on a catalogue that goes to
a designer is H68 where it damages the business. M3 builds the framework and
the gaps; the founder fills the trade content.

## FOUNDER CONTEXT ESTABLISHED THIS SESSION

- **Audience is all three:** retail buyer of a finished piece · cut-file buyer
  running their own machine · designer specifying into a job. **Three different
  documents per product**, not one document for three readers.
- **Machine:** X-Carve 1000mm, 750 × 750 mm actual cut area, safe envelope
  700 × 700.
- **3D printer:** Elegoo Saturn Max — RESIN, ~219 × 123 × 250 mm. Precision, not
  production. Resin is wrong for anything that flexes, clips, bears load, or
  lives in sunlight.
- **Material:** the shop BOTH STOCKS AND BUYS PER JOB. So the catalogue must
  state, per product, whether it cuts from stock or is order-first.

## PROPOSED PRODUCT LIST — FOUNDER RULES, M3 DOES NOT DECIDE

Strategic Claude's proposal. The advantage is that WoodCraft sits inside an
upholstery workroom already selling to designers, hotels and property managers.
The CNC line should attach to that rather than compete with generic makers.

**Tier 1 — feeds the workroom's own jobs** (customer already exists; margin is
vertical integration):
- bench and banquette frames — parametric on radius, seat height, channel count
  (the Willard curved bench and R6 towers are the worked examples)
- drapery mounting boards — pre-cut, pre-drilled to a return pattern; used on
  every drapery job
- curved cornice and valance carcasses — kerfed to a field radius; ties to the
  six-family template work
- channel panel substrates — the Willard panel is 8 channels @ 10-49/64"

**Tier 2 — designers specify these in** (sold finished; the spec sheet is the
sales tool):
- floating shelves with concealed cleat, load-rated, solid edge (R6 walnut
  language)
- slat wall panels
- plinths and bases (R6 built 8 rails + 8 leg blocks)

**Tier 3 — retail and cut files:** the Slot Bench survives. It is the only one
of the five that reads as a real product.

**RESIN / STL — a different discipline, different file type:**
- finials and decorative hardware (small, detailed, non-structural, priced by
  design not material)
- presentation-board hardware samples — brackets, rings, mounts a designer holds
- **scale models of the furniture itself** — Saturn Max height prints a 1:12 R6
  wall unit or Willard bench in one piece; on a presentation board that stops
  being a drawing
- shop jigs where precision beats toughness — drill guides, radius templates,
  dogbone coupons, channel spacing gauges
- casting patterns for silicone moulds

**An STL is not an SVG.** Different software, tolerances and failure modes. Each
product states which it is; a product that is both — cut frame plus printed
hardware — needs both manifests and an assembly document tying them together.

---

## PASTE INTO M3 (fresh session)

```
Check /model first — confirm M3. Read CLAUDE.md fully. Repo ~/empire-repo-main,
branch feature/drawing-standard (HEAD 366ad5f or later).

PATH DOCTRINE — SUPERSEDES CLAUDE.md: ~/empire-repo is NOT a stale fork. It is
the FROZEN main worktree holding the shared git object store; ~/empire-repo-main
is a LINKED worktree. Never write to it.

INFRA: backend restart = `systemctl --user restart empire-backend` ONLY, and
only where a phase says so. sqlite3 CLI is NOT installed — use
~/empire-repo-main/backend/venv/bin/python3. Never commit max/memory.md. Never
print API key values. NEVER SEND EMAIL.

THE HARD RULE FOR THIS ROUND — READ TWICE. You must NOT invent trade content.
No species recommendation, no grade, no finish schedule, no load rating, no
feed and speed, no tolerance, no price, no lead time — unless you found it in a
file on this box and can cite file:line, or the founder stated it. Everything
else is a GAP, and a named gap is the deliverable. A catalogue that reaches a
designer carrying a fabricated load rating is worse than no catalogue. When you
do not know, write FOUNDER INPUT REQUIRED and say precisely what is needed.

--- PHASE 1 · WHAT EXISTS (read-only, 🛑) ---

1. THE CURRENT CATALOGUE. Find the generator behind XCarve_Series_Catalog.pdf
   and EmpireSlotBench_Assembly_CAM.pdf. Search the whole box — repo,
   ~/Downloads and subdirectories, /data, /ssd. Report path, line count, and
   whether it is in git. If it is not in git, say so loudly (DOCTRINE §VIII).
2. IS "PARAMETRIC" TRUE? Both sheets claim every design is parametric —
   "new size, new thickness, or a custom variant is a one-line change" and
   "slots re-cut to measure in one minute". Verify. Is there a spec object and
   a generator, or are the five designs hardcoded geometry? Quote the code.
   If the claim is false, that is a finding: the catalogue is promising a
   capability the code does not have.
3. THE FILE MANIFEST. The catalogue promises XCarve_<NAME>.svg (mm-native,
   Easel) and XCarve_<NAME>.dxf (R2000, mm, closed LWPOLYLINEs, layer CUT,
   Vectric). Do those files exist? For which designs? Are they generated or
   hand-made? Report which of the five actually ship files.
4. STL / 3D. Is there ANY mesh or STL generation anywhere in the codebase?
   EMPIRE_CLIENT_DOC_STANDARD §6 references empire3d.py as a parametric mesh
   module — does it exist, what does it produce, and can it export STL? The
   Willard 3D model HTML exists; report what generated it and whether the same
   pipeline could emit a printable mesh.
5. WHAT DOES A PRODUCT NEED THAT NOTHING CARRIES? Compare the current catalogue
   against the R6 REV G client pack — which does carry product identity,
   sourced specifications, comparative reasoning and per-item rationale. List
   every field a real product entry needs and mark each EXISTS / PLACEHOLDER /
   ABSENT: name, description, photo or render, dimensions, material and grade,
   finish options, load rating, hardware, tolerances, assembly steps, tool
   list, time estimate, price, variants, lead time, file manifest.
   Expect most to be ABSENT. That list is Phase 2's specification.
6. WHERE WOULD IT LIVE? The framework is backend/app/presentation/template/
   (13 files, 2223 lines). Report whether a product catalogue is a new body
   builder there, a new content module, or something else. Do NOT create
   backend/app/services/presentation/ — that path does not exist and the
   2026-08-18 dispatch names it wrongly.

🛑 STOP. Report: found / changed ("none — map only") / verified vs inferred /
report hash. State plainly whether the parametric claim is true.

--- PHASE 2 · THE PRODUCT SPEC AND THREE DOCUMENTS (founder go only) ---

7. ONE product spec object, per DOCTRINE and EMPIRE_CLIENT_DOC_STANDARD §1:
   one source drives every document. The Willard set shipped at two revisions
   and ordered 4.0 YD for a 2.0 YD job — that is what two sources costs.
8. THREE document builders off that one spec, because the audiences differ:
     RETAIL SHEET — finished piece. What it is, what it looks like, dimensions,
       material, finish, price, lead time. No CAM, no file manifest.
     CUT-FILE SHEET — buyer runs their own machine. Nesting, stock requirement,
       bit, tabs, inside/outside toolpaths, joinery detail, file manifest,
       assembly. This is closest to what exists today.
     DESIGNER SPEC SHEET — specified into a job. Dimensions, load rating,
       finish schedule, tolerances, lead time, what is COM or client-supplied,
       and a line the designer can paste into a schedule.
   A field the spec does not carry PRINTS AS TBC or the build refuses — founder
   rules which, ask before implementing. Do not default a value into a
   client-facing sheet.
9. Every product states: SVG / DXF / STL / none, and cuts-from-stock or
   order-first. Both were stated by the founder and both are real constraints.
10. Regression guard, class-level: a test that FAILS if any product-facing
    builder emits a load rating, price, finish schedule or material grade with
    no value in the spec. Guard the class.
11. Full suite, pre-change baseline first, post-change, failures you caused
    named separately. One commit per builder. 🛑 after each.

--- PHASE 3 · ONE REAL PRODUCT, END TO END (founder go only) ---

12. The Slot Bench — the only current design the founder called real. Carry it
    through: spec object, all three documents rendered, file manifest verified
    to exist on disk.
13. Then render one product with an INCOMPLETE spec and prove the TBC or the
    refusal fires. The negative case is the deliverable.
14. You do not judge whether it is catalogue-ready. Render, report your own QC
    honestly, list every FOUNDER INPUT REQUIRED gap, and hand it over.
🛑 STOP.

REPORT: reports/<YYYY-MM-DD>_<HHMMSS>_R16_woodcraft_product_line.md using the
REAL clock time you start. All phases in ONE file. Hash LAST, rename, report the
value, and COMMIT it.
```

---

## NOTES FOR THE FOUNDER

- **Step 2 is the one I would watch.** Both CNC sheets claim every design is
  parametric and re-cuts in one minute. If that is a marketing line over
  hardcoded geometry, the catalogue is already promising something the code
  cannot do — and a cut-file customer finds out immediately.
- **Step 5 produces the shopping list of what only you can supply.** Species,
  grade, finish, load rating, tolerance, price, lead time. M3 is forbidden from
  inventing any of it. Expect a long FOUNDER INPUT REQUIRED list; that is the
  round working correctly.
- **Three documents per product is the structural decision.** One sheet cannot
  serve a retail buyer, a cut-file buyer and a designer. Splitting them now is
  cheaper than discovering it after the catalogue ships.
- **The product list above is a proposal, not a plan.** Rule on it before Phase
  2. My reasoning: Tier 1 has a customer who already exists — you — and every
  drapery job needs a mounting board. That is revenue you are currently paying
  someone else for, or cutting by hand.
- **The scale-model idea is the one I would test first.** A 1:12 R6 wall unit on
  the presentation board next to the drawings is something no competitor is
  handing a designer, and the Saturn Max prints it in one piece.
- **Not in this lane:** R12.3, R13, R14 v2, R15.
