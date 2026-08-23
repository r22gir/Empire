# DISPATCH R13 — WOODWORK INTO THE FRAMEWORK

**All seven sources are now committed** at `reference/recovered/r6_woodwork/`
(commit `f937a75`): `arch.py`, `client.py`, `present.py`, `shop.py`, `lab.py`,
`power2.py`, `hookup.py`. They produced the delivered R6 REV G client pack.
Until 2026-08-23 they existed only in a chat log — see DOCTRINE §VIII.

**The 2026-08-18 dispatch is the porting guide, and it is wrong about the
target path.** It specifies `backend/app/services/presentation/`. That does not
exist. The live framework is **`backend/app/presentation/template/`** — 13
files, 2,223 lines, committed `938131a` and `bceaa12`, with `spec.py`,
`chrome.py`, `band.py`, `gates.py`, body builders and content modules. It is an
in-progress port of the McLean generator. **Woodwork lands there. Do not create
a second architecture.**

Phase 1 maps and stops. Phases 2 and 3 on founder go.

---

## PASTE INTO M3 (fresh session)

```
Check /model first — confirm M3. Read CLAUDE.md fully. Repo ~/empire-repo-main,
branch feature/drawing-standard (HEAD f937a75 or later).

PATH DOCTRINE — SUPERSEDES CLAUDE.md: ~/empire-repo is NOT a stale fork. It is
the FROZEN main worktree holding the shared git object store; ~/empire-repo-main
is a LINKED worktree. Deleting ~/empire-repo destroys both. Never write to it.

INFRA: backend restart = `systemctl --user restart empire-backend` ONLY, and
only where a phase says so. sqlite3 CLI is NOT installed — use
~/empire-repo-main/backend/venv/bin/python3. Never commit max/memory.md. No
email in any phase. Never print API key values.

READ FIRST, all three, in full:
  EMPIRE_CLIENT_DOC_STANDARD.md          — §3 spec object, §4 rules, §5 six
                                           gates, §6 implementation path
  claude/claude_DISPATCH_2026-08-18_woodwork_presentation.md
                                         — the porting guide. Its target path
                                           is WRONG (see below); everything
                                           else stands.
  reference/recovered/r6_woodwork/*.py   — the seven sources

--- PHASE 1 · MAP (read-only, 🛑) ---

1. WHICH SOURCE IS CANONICAL? The directory holds near-duplicate pairs:
     arch.py (28772) == architectural_set_rev_G.py (28772)  — byte-identical
     client.py (20089) vs client_change_order.py (20440)     — DIFFER
     present.py (21148) vs presentation_rev_G.py (20898)     — DIFFER
     shop.py (10662) vs shop_set_internal.py (10563)         — DIFFER
     lab.py (5518) vs label_generator_revG.py (5334)         — DIFFER
   For each differing pair: diff them, say what changed, and determine WHICH
   ONE produced the delivered REV G document. The delivered PDF is the
   arbiter — its numbers are given in step 3. Report the canonical file per
   pair. Do not guess; check the numbers.

2. THE SPEC DRIFT — this is a live defect, not a porting detail. Three files
   carry the identical docstring "One RATES/SPEC block drives both", and each
   has its OWN S=dict that disagrees with the others:
     client_change_order.py   LABOR_HRS=7.5
     presentation_rev_G.py    LABOR_HRS=5.5
     shop_set_internal.py     LABOR_HRS=5.5
   The delivered REV G client pack states 7.5 h at $95.00 = $712.50. Find every
   other field that differs across the seven SPEC blocks and list them. This
   list is the argument for a single spec.py, and it is the round's first
   finding.

3. ACCEPTANCE NUMBERS — from the delivered REV G pack, hand-verified. Any port
   must reproduce these exactly:
     overall height        114 1/2"   (26 1/4 base top + 88 1/4 tower)
     overhead bay width     19 3/32"  ((80 - 5x0.72) / 4)
     overhead box height    13 11/16" (12 1/4 + 2x0.72)
     overhead usable depth   6 17/32" (8 - 3/4 - 23/32)
     plinth side rail       14 31/32" (17.97 - 2x1.5)
     shelf undersides       38 1/2 · 51 15/32 · 64 7/16 · 77 13/32 · 90 3/8 AFF
     cabinetry materials    $343.00
     LED goods              $948.00
     labour                 $712.50   (7.5 h x $95)
     TOTAL                  $2,390.80
   Run each canonical generator from step 1 and report which of these it
   actually produces. A generator that does not reproduce the delivered numbers
   is not the canonical one — revisit step 1 if so.

4. THE TARGET FRAMEWORK. Tree backend/app/presentation/template/ and report,
   file by file: what spec.py's dataclass requires, what gates.py implements
   against EMPIRE_CLIENT_DOC_STANDARD §5's six gates (Bounds, Collisions,
   Integrity, Anchors, Rev, Derived) — ENFORCED / PARTIAL / ABSENT each — and
   what the body/ builder contract is. Paste one builder's signature.

5. THE GAP. What would a woodwork body need that the framework does not have?
   The 08-18 dispatch lists five builders (architectural, client_pack,
   presentation, shop_internal, labels). Map each to the framework's existing
   body/ shape. Report which are a mechanical port, which need a new module,
   and which need a framework change. Do not build anything.

6. THE CLIENT_FORBIDDEN GATE IS WRONG AS SPECIFIED — verify and report. The
   08-18 dispatch says client builders must assert none of
   {"cost","margin","markup_amount","at cost","shop cost"} appear in their
   output. The DELIVERED REV G client pack contains "at cost" TWICE — on the
   presentation sheet ("29 items · $948.00 at cost") and as sheet 4's subtitle
   ("Two schedules, at cost · marked up on the next sheet"). It is a change
   order with transparent cost plus 30% handling; showing cost is the point.
   As written, that gate would REFUSE TO EMIT THE GOLDEN REFERENCE. Confirm
   this against the PDF and propose the correct rule — the real constraint is
   no SHOP cost, no margin, no method. Report; do not implement.

7. RENDERING STACK. arch/client/present/shop use cairosvg + pypdf; lab uses
   PIL; willard_drawing.py (also in reference/recovered/) uses reportlab; the
   framework's printer.py uses reportlab. Report which stack the framework's
   chrome.py targets and what a cairosvg-origin port has to cross. The 7/31
   session summary records that cairosvg dpi=72 is essential — the default 96
   silently shrinks Letter to 594x459pt. Verify that trap still applies.

🛑 STOP. Report: found / changed ("none — map only") / verified vs inferred /
report hash. Recommend the smallest correct port and state its risk.

--- PHASE 2 · PORT (founder go only) ---

Scope from Phase 1. Constraints that hold regardless:
8. ONE spec object. Lift SPEC out of all seven files. Fields the founder has
   not field-verified become printed assumptions, not defaults. Seed the R6
   assumptions as fixtures: COM leg height, wall-to-wall width, baseboard
   height, LED street prices, labour rate. SpecIncomplete lists EVERY missing
   field at once — no partial builds, no silent defaults.
9. Do NOT weaken TestDoctrineGuard. Do NOT create
   backend/app/services/presentation/ — the framework is
   backend/app/presentation/template/.
10. Client/shop separation is structural, not stylistic. shop_internal carries
    cost, margin and method; client builders carry none of the last two. Use
    the corrected rule from step 6, not the one in the 08-18 dispatch.
11. House voice, carried as constants — the founder corrected each of these
    during the R6 session: never "glued" (use set/affixed/fitted); "cove
    fascia" not "cove trim"; never "mitre/mitred"; no "scribe allowance"; never
    "as you requested" for something the client did not specify (use "we
    assessed the options and specified…"); "shelving unit/towers/compartments"
    not "bookshelf". Client documents do not name what is NOT being done.
12. Geometry verification is RASTER, not vector. The 7/31 summary's three
    checks are the method: assert geometry before drawing; compare drawn area
    to computed area; project a known corner, rasterise, sample that pixel.
13. Full suite, pre-change baseline first, post-change, failures you caused
    named separately. One commit per family. 🛑 after each.

--- PHASE 3 · ACCEPTANCE (founder go only) ---

14. Rebuild the R6 REV G pack through the framework, invoked as MAX would
    invoke it. Every number in step 3 must match exactly. Report each one
    PASS/FAIL against the delivered PDF.
15. Rasterise and check against EMPIRE_CLIENT_DOC_STANDARD §5's six gates.
    Report each with pixel evidence.
16. You do not decide whether it is good enough. Produce the artifact, report
    your own QC honestly including what you think is wrong with it, and hand it
    to the founder. He judges format and voice. Do not claim it matches his
    standard — show it and let him say.
🛑 STOP.

REPORT: reports/<YYYY-MM-DD>_<HHMMSS>_R13_woodwork_port.md using the REAL clock
time you start. All phases in ONE file. Hash LAST, rename to include it, report
the value, and COMMIT it.
```

---

## NOTES FOR THE FOUNDER

- **Step 2 is the finding that justifies the whole round.** Three files claim a
  shared spec block and three files disagree about labour hours. The delivered
  document says 7.5; two generators say 5.5. That is a $190 discrepancy between
  what the client was told and what two of the sheets compute. One spec object
  is not tidiness — it is the fix.
- **Step 6 matters more than it looks.** The gate as specified in the 08-18
  dispatch would refuse to emit your own golden reference, because a change
  order legitimately shows cost. A negative fixture that fails for the wrong
  reason proves nothing — this program has paid for that lesson before.
- **Step 1 must be settled before anything else.** Four of five pairs differ and
  only one of each produced the delivered pack. Porting the wrong revision
  would rebuild the 5.5-hour version.
- **The 08-18 dispatch's target path is wrong** and I have said so explicitly.
  Left uncorrected, M3 would create a second architecture beside the live one —
  the exact thing that dispatch's own §0 stop-gate warns against.
- **Not in this lane:** R12's drawing-router freeze fix, the third
  DRAWING_KEYWORDS pipeline at openclaw_worker.py:1284, the five drapery
  families still at B1, the tools-accuracy pass, the registry, token rotation,
  the seven-week-stale Drive backup.
