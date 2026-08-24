# DISPATCH R15 — SOURCED KNOWLEDGE ON CLIENT DOCUMENTS

**The hardest requirement in the system, and nothing addresses it today.**

The R6 REV G client pack contains material no template can produce. Read it and
sort what is on those seven sheets:

| what it is | example from REV G | where it comes from |
|---|---|---|
| geometry | overall 114 1/2", bays 19 3/32" | the spec — templates do this |
| arithmetic | $343.00 + $948.00 + 30% + $712.50 = $2,390.80 | the spec — templates do this |
| **sourced product facts** | nine SKUs, street prices, *"Confirm the listing reads V4 — earlier versions use a different connector"* | **the web. Nothing does this.** |
| **manufacturer spec applied** | *"Blum's CLIP top specification governs a minimum reveal measured in millimetres, not inches, so no side gap is required"* | **a hardware datasheet. Nothing does this.** |
| **comparative judgment** | *"Häfele Loox is the better cabinet product and costs less, but its sconce bulbs sit in a separate app"* | **research + judgment. Nothing does this.** |
| **physical reasoning** | 0.64 A total draw, under 10% of circuit; span drops 80" → 19 3/32"; tape 0.020" vs 1/8" solid | **domain knowledge. Nothing does this.** |
| **honest negatives** | *"Honestly stated: no depth is added anywhere."* | **voice + integrity. Nothing does this.** |

**R13 ports geometry and arithmetic into the framework. This round is about
everything else** — and it is the difference between MAX drafting documents and
MAX drafting *these* documents.

**The risk is exactly H68, in the place it costs most.** A fabricated street
price, an invented Blum reveal spec, or a made-up amperage on a sheet a client
signs is worse than a blank field. The founding rule — honesty about what is
known versus assumed — has to extend from dimensions to facts.

Phase 1 maps. Phase 2 builds the provenance rail. Phase 3 is a live test the
founder judges.

---

## PASTE INTO M3 (fresh session)

```
Check /model first — confirm M3. Read CLAUDE.md fully. Repo ~/empire-repo-main,
branch feature/drawing-standard (HEAD 0954016 or later).

PATH DOCTRINE — SUPERSEDES CLAUDE.md: ~/empire-repo is NOT a stale fork. It is
the FROZEN main worktree holding the shared git object store; ~/empire-repo-main
is a LINKED worktree. Never write to it.

INFRA: backend restart = `systemctl --user restart empire-backend` ONLY, and
only where a phase says so. sqlite3 CLI is NOT installed — use
~/empire-repo-main/backend/venv/bin/python3. Never commit max/memory.md.
Never print API key values or lengths — PRESENT/ABSENT and variable names only.
NEVER SEND EMAIL in any phase. The founder sends all client communication.

READ FIRST, both in full:
  reference/recovered/r6_woodwork/client.py and present.py — the generators that
    produced the REV G prose sheets. Study HOW the sourced facts are carried:
    are they hardcoded strings, a data table, or fetched?
  EMPIRE_CLIENT_DOC_STANDARD.md — §4 rule 2 (assumptions are printed) is the
    rule this round extends from dimensions to facts.

--- PHASE 1 · MAP (read-only, 🛑) ---

1. HOW ARE SOURCED FACTS CARRIED TODAY? In client.py and present.py, find every
   externally-sourced claim — the nine product SKUs, prices, the V4 connector
   warning, the Blum reveal specification, the 0.64 A draw, the Häfele
   comparison. For each report: is it a hardcoded literal, a data structure, or
   computed? Quote the code. The 08-18 dispatch says of these files: "Known
   defect carried in all five: they invent. Labour rate, LED prices and cord
   lengths are hardcoded estimates." Verify that claim — is it true, and how
   widely?

2. CAN MAX SEARCH THE WEB AT ALL? Report, with file:line:
     - which search/fetch tools exist in the tool registry
     - whether MAX can invoke them from chat, or they are script-only or dead
     - BRAVE_API_KEY and any other search credential: PRESENT / ABSENT in the
       backend process env (names only, never values, never lengths)
     - whether any code path currently puts fetched web content into a
       generated document
   If the answer is "MAX cannot search", say so plainly — that reframes the
   whole round from "add provenance" to "build the capability first".

3. IS THERE ANY PROVENANCE MECHANISM? Does any spec object, template or
   renderer carry a field for WHERE a value came from and WHEN? Search for
   source, provenance, fetched_at, cited, verified_at, or similar. Report what
   exists — likely nothing — and what the ASSUMPTIONS block currently records
   (it holds field, value, how_to_verify per the 08-18 dispatch; confirm).

4. THE PRODUCT CATALOGUE QUESTION. The nine REV G products are real SKUs with
   real prices. Is there anywhere in the system that stores products —
   lf_prospects, inventory, a materials table, EMPIRE_CATALOG? Report whether a
   product could be stored once with its source and reused across documents, or
   whether every document would re-source it. vision/product_catalog.py exists
   and carries vocabulary — report whether it holds facts or only strings.

5. WHAT WOULD FABRICATION LOOK LIKE HERE? Name the specific failure modes for
   this document type: an invented price, a wrong SKU, a misremembered
   manufacturer spec, an amperage that is plausible but wrong, a comparison to
   a product that does not exist. For each, say what would catch it today.
   Expect the answer to be "nothing" for most — that is the finding.

🛑 STOP. Report: found / changed ("none — map only") / verified vs inferred /
report hash. Recommend the smallest correct first step and state its risk.

--- PHASE 2 · THE PROVENANCE RAIL (founder go only) ---

Do not build a web-search feature in this phase. Build the rail that makes
sourced facts safe, so that whatever fills it — MAX, a search tool, or the
founder typing — cannot lie silently.

6. Every externally-sourced value on a client document carries provenance:
   what it is, where it came from, when it was obtained, and who or what
   obtained it. Design it as a field on the spec, not as prose in a template.
7. A value without provenance CANNOT PRINT AS A FACT. It prints as TBC, or the
   build refuses — founder's ruling on which, ask before implementing. Make the
   wrong thing unreachable, not discouraged: a template that interpolates an
   unsourced value into a client sheet must fail a test, not a review.
8. Provenance ages. A street price obtained three months ago is not a current
   price. Print the date on the sheet alongside the value — REV G already does
   this informally with "Street prices · confirmed at the time of order". Make
   it structural.
9. Regression guard, class-level: a test that FAILS if any client-facing
   builder emits a numeric price, a manufacturer specification, or a product
   SKU that has no provenance record. Guard the class, not the instance.
10. Full suite, pre-change baseline first, post-change, failures you caused
    named separately. One commit. 🛑 after.

--- PHASE 3 · ONE REAL FACT, END TO END (founder go only) ---

11. Take ONE product from the REV G pack — the Hue Lightstrip Plus base kit is
    the cleanest case — and carry it through the rail: sourced, provenance
    recorded, printed on a rendered sheet with its date.
12. Then attempt it WITHOUT provenance and prove the build refuses or prints
    TBC. The negative case is the deliverable. A gate that has only been
    demonstrated passing has not been demonstrated.
13. You do not judge whether the result is client-ready. Render it, report your
    own QC honestly, and hand it to the founder.
🛑 STOP.

REPORT: reports/<YYYY-MM-DD>_<HHMMSS>_R15_sourced_knowledge.md using the REAL
clock time you start. All phases in ONE file. Hash LAST, rename, report the
value, and COMMIT it.
```

---

## NOTES FOR THE FOUNDER

- **Step 2 decides the size of this round.** If MAX cannot search the web at
  all, then R15 is two rounds: build the capability, then the rail. I have told
  M3 to say so plainly rather than assume a tool exists.
- **The rail comes before the capability, deliberately.** Giving MAX web search
  without provenance is how a fabricated price reaches a client sheet. The
  order is not negotiable and it is the same reasoning as auth-before-bind on
  the lifeline.
- **One decision is yours, at step 7:** does an unsourced value print as TBC, or
  does the build refuse? TBC is friendlier and keeps the document flowing;
  refusing is safer and matches the fail-closed doctrine elsewhere. My read is
  TBC for a draft and refuse for anything stamped FOR YOUR APPROVAL — but that
  is your call, and M3 will ask.
- **What this round does NOT attempt:** the judgment and the voice. *"Häfele
  Loox is the better cabinet product and costs less, but…"* is comparative
  reasoning with a recommendation, and *"Honestly stated: no depth is added
  anywhere"* is integrity in prose. Neither is a data problem. If MAX ever
  writes those, it will be because the model can, not because a template can —
  and it will need the same provenance discipline underneath it or it becomes
  confident fiction.
- **Not in this lane:** R13 (woodwork port), R14 (document catalogue), R12.3
  (fold count, collisions, dimension weight), the hardcoded CST-DRAFT date,
  probe N's first-turn freeze, H58.
