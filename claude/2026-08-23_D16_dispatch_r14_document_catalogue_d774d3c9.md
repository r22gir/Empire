# DISPATCH R14 — THE DOCUMENT CATALOGUE

**Founder's ask, 2026-08-23:** a list of every document EmpireBox produces —
drawings, quotes, invoices, estimates, change orders, presentations, board
sheets, field measurement sets, labels — **and what each one actually looks
like when MAX hands it over.** Not a description. The rendered file.

**Why this round comes before R13.** R13 ports the R6 woodwork generators into
`backend/app/presentation/template/`. Knowing the full document set first tells
us what that framework has to hold. Porting one family into a framework sized
for one family is how you end up with six frameworks.

**Why it matters commercially.** The stated goal since February is *"an OS for
resellers and service businesses"*, sold by module. A customer buying the
drapery module needs to know which documents it produces. Nobody has ever
written the set down.

**What is already known — verify, do not inherit:**

- Six B1 families, 46 product types: drapery (15), roman shades (9), valance
  (14), cornice (5), bench/banquette (2), channel headboard (1).
  **Only roman shades renders a B2 sheet.** The other five output text/tables.
- Three delivered artifacts exist as ground truth:
  `reference/recovered/` R6 REV G client pack (7 sheets),
  `reference/mclean/McLean_Whittington_Drapery_Elevations_RevA.pdf` (11 sheets),
  `backend/data/drawings/flat_fold_335c9c58.pdf` (B2, 1 sheet).
- **EST-2026-111 went out in TWO different templates** — "Quote … please find
  your quote attached" and "Estimate … Estimate Total: $8599.60". Two formats,
  one document, both live. That is a finding waiting to be confirmed.
- `EMPIRE_CLIENT_DOC_STANDARD.md` §5 defines six QC gates. They are enforced
  for roman shades only.

Phase 1 inventories. Phase 2 **renders one of everything**. That is the
deliverable.

---

## PASTE INTO M3 (fresh session)

```
Check /model first — confirm M3. Read CLAUDE.md fully. Repo ~/empire-repo-main,
branch feature/drawing-standard (HEAD 19381c3 or later).

PATH DOCTRINE — SUPERSEDES CLAUDE.md: ~/empire-repo is NOT a stale fork. It is
the MAIN WORKTREE — it owns the shared object store and still receives data writes under backend/data/ holding the shared git object store; ~/empire-repo-main
is a LINKED worktree. Deleting ~/empire-repo destroys both. Never write to it.

INFRA: backend restart = `systemctl --user restart empire-backend` ONLY, and
only where a phase says so. sqlite3 CLI is NOT installed — use
~/empire-repo-main/backend/venv/bin/python3. Never commit max/memory.md.
Never print API key values.

NEVER SEND EMAIL. Not a test, not to the founder, not to a seeded address. This
round renders documents; it does not deliver them. If any code path could reach
an external recipient, read it and report it — do not execute it. The founder
sends all client communication.

USE SYNTHETIC DATA ONLY. Render with made-up client names and dimensions. Do
NOT render a real client's quote or invoice. Never print prospect contact
details.

READ FIRST: EMPIRE_CLIENT_DOC_STANDARD.md and EMPIRE_DRAWING_STANDARD.md.

--- PHASE 1 · INVENTORY (read-only, 🛑) ---

1. THE DOCUMENT TYPES. Enumerate every distinct document EmpireBox can produce.
   Walk the code, not memory. Cover at minimum: shop drawings (B1 and B2),
   field measurement sets, presentation sheets, client packs / change orders,
   architectural sets, shop-internal sets, part labels, quotes, estimates,
   invoices, board/mount sheets, 3D viewers, install guides. There will be some
   you find that are not on this list — include them. For each report:

     name · what it is for · which module or family produces it ·
     generator file:line · output format (PDF/PNG/HTML) ·
     B1 numeric or B2 vector · does it have QC gates ·
     CAN MAX INVOKE IT FROM CHAT (yes / script-only / dead) ·
     is there a reference artifact on disk, and where

   The "can MAX invoke it" column is the one that matters. Be exact: name the
   tool, or say script-only.

2. QUOTES, ESTIMATES AND INVOICES — the pair that goes out most often and the
   one nobody has looked at. Find every quote/estimate/invoice generator and
   template. Report:
     - how many DISTINCT templates exist for each
     - which one MAX actually uses when asked for a quote
     - whether quote, estimate and invoice share one renderer or three
     - whether the numbers come from one source or are recomputed per template
   EST-2026-111 went out on 2026-08-17 under TWO templates — "Quote EST-2026-111
   — please find your quote attached" and "Estimate EST-2026-111 … Estimate
   Total: $8599.60". Find both call sites. If there are genuinely two quote
   documents, say so plainly and name which is canonical.

3. HARDWARE AND SPECIFICATION FIELDS. The flat_fold B2 title column shows
   `FABRIC: TBC` then three unlabeled "—" rows and "STANDARD". The McLean
   footer names FABRIC / LINING / HEADING / HARDWARE / MOUNT explicitly.
   Report: what the spec object accepts today for rod, board, brackets, rings,
   lift system, lining, heading, mount type, finish — EXISTS / PLACEHOLDER /
   ABSENT for each. Can MAX populate any of them from chat? Show the
   title_block code that emits those blank rows.

4. ONE SOURCE OR MANY? For any figure that appears in more than one document —
   a dimension, a price, a labour rate, a hardware spec — does it come from one
   place? The R6 generators claim "One RATES/SPEC block drives both" and carry
   three disagreeing SPEC blocks (LABOR_HRS 7.5 vs 5.5 vs 5.5). Report any
   other instance of the same shape you find. This is the defect class that
   matters most.

5. THE GAP LIST. Which document types have no generator at all? Which have a
   generator MAX cannot reach? Which produce text/tables where the founder
   expects a B2 sheet? Rank by how far each is from client-ready.

🛑 STOP. Report the inventory as a table, plus found / changed ("none —
inventory only") / verified vs inferred / report hash.

--- PHASE 2 · RENDER ONE OF EVERYTHING (founder go only) ---

The deliverable. Not descriptions — files.

6. For EVERY document type in the Phase 1 inventory that has a working
   generator, render ONE example with synthetic data into
   `reports/catalogue/<YYYY-MM-DD>/`. Name each file so the type is obvious.
   Where a family has many product types, render one representative — but
   render at least one per FAMILY, all six, so the founder can see the B1/B2
   gap with his own eyes rather than reading about it.

7. Include quote, estimate and invoice. If there are two quote templates,
   render BOTH so the difference is visible side by side.

8. For anything that cannot be rendered, do not skip it silently — produce a
   one-line entry saying which document type it is and exactly what blocks it
   (missing spec field, dead tool, no generator). A gap the founder can see is
   worth more than a gap he has to ask about.

9. Write `reports/catalogue/<YYYY-MM-DD>/INDEX.md`: one row per document,
   linking the rendered file, naming the generator, and stating MAX-reachable
   or not. This index is the catalogue.

10. Commit the index and every rendered artifact. PDFs under reports/ are NOT
    covered by the reference/**/*.pdf ignore, but VERIFY with `git status`
    before committing and use `git add -f` if anything is silently excluded —
    that has already cost one file this week.

11. You do not judge fidelity. Render, index, report your own QC honestly
    including what you think is wrong with each, and hand the folder to the
    founder. He decides which are client-ready.
🛑 STOP.

REPORT: reports/<YYYY-MM-DD>_<HHMMSS>_R14_document_catalogue.md using the REAL
clock time you start. Both phases in ONE file. Hash LAST, rename to include it,
report the value, and COMMIT it.
```

---

## NOTES FOR THE FOUNDER

- **Phase 2 is the round.** At the end you have a folder containing one of
  every document EmpireBox produces, and you can tell in an afternoon which are
  client-ready, which are close, and which do not exist. That is not currently
  knowable from any document or any person.
- **Step 2 is where I expect the worst news.** Two live templates for one quote
  is already evidenced in your own sent mail. Quotes and invoices go out more
  than anything else and have had the least attention this week.
- **Step 4 is the defect class.** `LABOR_HRS` 7.5 in one generator and 5.5 in
  two others, all three claiming a shared spec block, is a $190 difference
  between what the client was told and what two sheets compute. If that shape
  appears anywhere else — a price, a dimension, a hardware spec — it will
  surface here.
- **Step 3 answers the hardware question directly.** The blank rows on the B2
  sheet suggest the slots were reserved and never filled. If the spec cannot
  carry a rod or a mount type, no amount of drawing work makes these sheets
  shop-ready.
- **Synthetic data only, and no email.** This round renders quotes and
  invoices. Nothing goes to a real client and nothing leaves the machine.
- **Not in this lane:** R12.1 (fraction parsing + plausibility gate), R13
  (woodwork port), the five B1 families needing B2 treatment, the hardcoded
  `CST-DRAFT · 07/26/2026` date stamp, probe N's 30s first-turn freeze, H58.
