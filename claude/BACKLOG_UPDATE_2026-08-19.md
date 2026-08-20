# BACKLOG UPDATE — 2026-08-19 (late)

**Apply this to `claude/BACKLOG.md`.** Issued as a delta rather than a full
rewrite so nothing already in the register is silently lost. Also bump the
register header — it still reads "As of 2026-08-05 (v3)" while carrying
content through 8/19.

---

## THE GOAL, RECORDED

**Founder 2026-08-19: MAX is to REPLACE strategic Claude, not assist it.**

This reorders everything. The H52–H55 sweep stops being maintenance and
becomes the build. Every failure observed tonight was a SENSORY failure —
he could not read the repo, could not trust his own context, could not
receive the message through the door. None was a character failure: under
four consecutive refusals he never fabricated a tool run, never invented an
audit, and admitted honestly that he did not know where a wrong belief came
from.

**`claude/DOCTRINE.md` is NEW and is part of this update.** It is the
judgement that has to transfer with the tools. 34 rules, each with its scar
named.

---

## CLOSED TODAY

| ID | Resolution |
|---|---|
| **I13** | ✅ Gmail OAuth restored. **E1 two-way email UNBLOCKED** — design locked, `check_inbox` still never tested live |
| **I14** | ✅ Founder authorization working (opened and closed same day) |
| — | Single-root-cause hypothesis **CONFIRMED**: OAuth, browser lockout and both founder addresses failed and recovered together — a Google account security event |
| **A5** | ✅ Closed by writing DOCTRINE.md + this update. Two founder rulings existed only in chat and would have been dropped by the port |

---

## NEW ITEMS

### V-LANE · PORTAL SURFACE (new lane, from founder screenshots 8/19)

The register tracked infrastructure while the surface the business runs on
drifted. None of these were previously known.

| ID | Item | Status |
|---|---|---|
| V1 | **Currency truncates everywhere** — `$8,599.6`, `$1,312.4`, `$362.7`. One formatter, all surfaces, client-facing | **DISPATCHED** — `DISPATCH_2026-08-19_visible_fixes.md`. ⚠️ Scope correction: the formatter must be SHARED with the document engine (estimates and invoices print money too) or we build a second one |
| V2 | **Test junk in the live quote list** — `1cfix-rej`, `1cfix-pin`, `1cfix-reject`, `Bulk1` ×2. Five of twenty; inflates the $22,066.94 headline | **DISPATCHED** — same file. **RECURRENCE**: `d5402aa` purged 14 rows + added teardown. Establish re-created vs never-purged BEFORE deleting, or it returns |
| V3 | Overview says **5 customers**, Customers page says **100** (filters sum to 100 — 100 is truth) | MAPPED, unverified |
| V4 | **Outstanding $34,391** vs AR aging **$5,965** — ~$28.5k unexplained between two tiles on one screen | MAPPED, unverified |
| V5 | **Accepted Quotes reads 0** despite Bozzuto EST-2026-111 approved through the PIN modal | MAPPED — approval never wrote back, or the field is never set |
| V6 | Collections: **"Unknown customer · no email · $4,175 overdue"** — orphaned receivable | MAPPED. **This is I9 made visible** (`PRAGMA foreign_keys = 0`). No longer theoretical |
| V7 | **EST-2026-113** (H&C drapery) exists as a PDF, never entered the canonical store | MAPPED |

### H-LEDGER ADDITIONS

| ID | Item | Status |
|---|---|---|
| **H57** | 🔴 **Drawing router eats MAX's door.** `any(keyword in lowered)` — literal SUBSTRING, PRE-MODEL, `drawing_intent.py:335`. "what is a drawing" never reached MAX; a long document paste never reached MAX. Also catches *withdrawing*/*redrawing*. **`pending_drawing_jobs` (SQLite) persists a half-formed spec across turns with no release — the reported "freeze"** | Phase 1 map `994cf75` (all 5 questions answered, file:line). Phase 2 **WIP `13119fc`** — question-form + long-paste suppression, word-boundary matching, pending-release, 22 new tests. **5 legacy tests failing, 2 unread.** ⚠️ Two were misdiagnosed as fixture problems — see H58 |
| **H58** | **Template-truth rejects MORE specific input.** A bench message carrying SEAT HEIGHT and BACK HEIGHT is refused for lacking a plain "height". M3 proposed editing the fixture to add `36 high` — that would hide a real intake failure. The template is wrong, not the fixture | NEW, map only. May belong to the drawing engine rather than H57 |
| **H59** | **`FOUNDER_PIN env var is UNSET` prints at import in ANY non-unit context** (tests, ad-hoc scripts). The PIN IS set in the unit (I10). A false security alarm as the default — it cost M3 a dozen probes on 8/19 | NEW, small |
| **H60** | **Second `DRAWING_KEYWORDS` list** at `openclaw_worker.py:1277`, different contents. Duplicated routing outside the canonical layer | NEW — log, do not fix |
| **H53** | ⚠️ **ESCALATED — now makes AUTHORIZATION IMPOSSIBLE.** MAX reported a `[SYSTEM]` block in founder messages the founder never typed (F1 replay scaffolding reading as injection). He then could not distinguish the founder's real authorization from the injection and refused repeatedly. With H55 there is no path through | **Reproduced live 8/19.** Now the FIRST item in the sweep |

### C-LANE

| ID | Item | Status |
|---|---|---|
| **C7** | **McLean / Whittington Design** — 11 sheets, 22→**24** openings (founder ruled the centre wall is THREE windows: 77½ / 69¼ / 78¼), field-measured 1 July, RevA issued 19 Aug | NEW. Re-render through the template engine as the P1-T·f acceptance test, then send. **Unknown whether RevA already went out** — decides REV A reissue vs REV B. Also a second candidate for C3 |

---

## P1-T · DOCUMENT TEMPLATE ENGINE (supersedes P1 architecture)

Standard pin **`1813c59043b7b05f87626dd4e66a3487`** (`e0035b4`) — replaces
`e6fde3cd…` wherever it is recorded. **8 amendments**, all founder rulings
8/19. Commits: `b55a9f6` · `948a1fc` · `e0035b4` · `938131a` · `75a3ac8` ·
`efdcbcf`. Currently at **P1-T·c** (builder interface).

**G5 now catches the McLean 21-vs-22 split with a committed fixture** — the
defect cannot return silently.

**Two founder corrections that change scope:**

1. **MAX is ONE DOOR AMONG SEVERAL, not the system.** The engine is a
   SERVICE LAYER; MAX, the portal, the CRM, the quoting system and future
   modules all call the same `build(spec)`. No door gets its own copy.
   P1-T·g is therefore "point the EXISTING portal buttons at the shared
   layer", not "add buttons".
2. **JOB MEDIA carries forward.** The camera icon uploads photos, videos and
   3D scans of the item quoted, and that media travels intake → quote →
   invoice → other documents. **Media belongs to the JOB, not the document.**
   This corrects P1-T·b. Amendment 7's blur moves to MEDIA INGEST; Amendment
   8's swatch collapses into the same store. **UNVERIFIED and outranks the
   rest if wrong: does the camera write to the SAME canonical store as
   LuxeForge intake, or a second one?**

**Open ruling needed:** video and 3D scans in a PDF — labelled still frame,
or a reference marker pointing at the asset?

---

## DESIGN VERDICT — RETIRE THE DRAWING ROUTER

Strategic position, 8/19: **the router should be retired, not tuned.**
Anything deciding before the model runs guesses with strictly less
information than the model has. Every patch narrows one failure and leaves
the structure. Correct shape: MAX receives every message and CALLS the
drawing tool; missing dimensions return `SpecIncomplete(missing=[...])` and
he asks conversationally. `pending_drawing_jobs` then disappears — the
conversation IS the state — and H60's second keyword list goes with it.

Sequenced AFTER P1-T·c proves the builder interface on documents. Same
pattern; prove it once.

---

## D-LANE

D-R4 corrections stand, plus two defects the P1-T·a map verified in
`fc42fe3`: **grommet/rod_pocket constants are NOT printed as ASSUMED** (an
honesty-doctrine violation in shipped code), and **the fabric model is
half-built** (pattern stored but never rendered, repeat direction not
flipped for railroaded, no spec-level hex override). The drapery R3 eyeball
was never given and may be **moot** if drapery re-renders through the
template engine.

---

## RECOMMENDED ORDER — replaces the stale 8/05 block entirely

The old order block still says H4x "FIRES NEXT" (closed 8/16), golden
corrections pending (shipped), and reboot proof pending (passed 8/17).
Delete it.

**Now — finish what is in flight**
1. **P1-T·c** builder interface (running)
2. **H57 Phase 2** — commit the WIP, resolve the 5 failures WITHOUT editing
   fixtures to pass, then Phase 3 (canonical root)
3. **V1 + V2** visible fixes — dispatched, unfired

**Then — the client-visible four** (founder set aside 8/19; all short)
4. Bozzuto — one email, $8,599.60 approved since 7/31
5. McLean re-render + send (doubles as P1-T·f acceptance)
6. Hudson & Crane — the width number
7. R6 — the three cutting gates

**Then — the handoff build** (the goal)
8. **H53** — he cannot hold a thread while his own context lies to him
9. **H57 Phase 3** — canonical root, structural
10. **H55** — founder-attested provenance, only meaningful after H53
11. **The coding question** — capability removed in the GPT-5.5 rewrite, or a
    deliberate gate after the quote fabrications? **Founder answer still
    outstanding.** It decides repair vs policy reversal
12. **Re-run the audit test** — same pair (R3 dispatch vs `fc42fe3`), same
    answer key published before the test existed. If MAX reads both from the
    repo himself and finds the two real defects, the handoff is PROVEN

**Then**
13. Retire the drawing router
14. E1 two-way email (now unblocked)
15. Portal faults V3–V7
16. Woodwork engine — check template overlap first, do not build two chrome
    layers
17. Family rollout — Bench/Banquette

**Housekeeping, ongoing:** stale-fork eradication (8G) · `.hermes/state.db`
2.8G · I7 TranscriptForge · I9 FK enforcement (now visible as V6) · the ~90
unproven test errors · H59.

---

## OPEN QUESTIONS

1. **What broke MAX's coding?** (blocks the restoration lane)
2. **What is the AI desk's shape?** MAX, Harry, M3, Atlas, Luna/Kai, Orion
3. **Does the camera write to the canonical media store?** (outranks P1-T
   scope if not)
4. **Video / 3D in documents** — still frame or reference marker?
5. **Did McLean RevA go to Whittington?** (REV A vs REV B)
6. **Is C3 Hudson & Crane, Whittington, or dead?**
7. **Detail A** — keep with a stated job, or delete?
8. **What is OpenClaw actually doing?** A 7,363-item queue with no owner, and
   `openclaw_worker.py` commits and PUSHES to git. Nobody has looked. Ten
   minutes, warranted by the write access alone
