# HANDOFF · session close 2026-08-29 (early AM)

**This document outranks the project corpus.** `CLAUDE.md`, `STATE_v8.md`,
`DOCTRINE.md` and every earlier handoff are stale relative to this. A cold
read of them will be wrong about the worktree, the vision path, the email
lane, the interface, and the books.

Supersedes the 2026-08-28 handoff (`7c182256`), which was written before
D46 reported.

```
repo    ~/empire-repo-main        branch  feature/drawing-standard
HEAD    31e1e3d                   pushed  yes
live data root  ~/empire-data     backend 127.0.0.1:8000
```

**Nothing is in flight.** D46 finished all three phases and pushed. Three
dispatches are written and waiting, none issued.

---

## §1 · The rules that govern

**The money rule.**

> The engine may never produce a number nobody supplied.
> The founder may always supply any number, including zero.

Silence is the defect; instruction is authority. `override_price: 0` raises.
Zero has its own two-keyed door: `no_charge: true` plus a reason. Exactly
two permitted zeros — that one, and `com_fabric` + `customer_supplied`.

**The issued-document rule.**

> Where an estimate or invoice has been issued to a client, the prices on
> that document govern that job. The catalog governs new work only.

**PENDING never blocks.** A missing fact marks the item PENDING; the
document still ships. Do not invent; do not refuse.

**An instruction in a prompt is not a mechanism.** Proven repeatedly. Every
constraint is enforced by code and demonstrated by a test that fails
without it.

**Founder sends; agents prepare.**

**`~/empire-repo` is the main worktree, not a stale fork.** It holds the
single object store for every branch, worktree and stash. Deleting it
destroys the repository. `REPO-TRUTH.md` says otherwise and is wrong.

**New this session — ink and gold.** A value MAX derives rather than
receives is *proposed*, not fact. It renders differently, it is excluded
from anything final, and it stays proposed until the founder accepts.
Established for vision-derived dimensions; extended to researched prices.
Ink is confirmed, gold is not.

---

## §2 · What landed

Five dispatches, all pushed. `31e1e3d`.

**D42** McLean generator parameterized, byte-identical proof, client-safety
emit gate demonstrated firing on a real run.
**D43** Vision decode-verify at the payload boundary; proven end to end on a
real sketch through `mmx_vision`.
**D44** One image landing place, four channels into `job_documents`; email
deliberately unwired.
**D45** H74 closed — empty-string default moved, `/chat` core extracted with
byte-equal output, Option A landed, `CodeTaskRequest.channel` default
dropped, OpenClaw moved off `/max/chat` before it could gain founder.
**D46** Nine read-only reports: the books and the full interface map.

---

## §3 · What D46 found

### The books are nearly empty

| | |
|---|---|
| Payments table | **1 row**, 22 March 2026 |
| Willard in the books | **nothing** — no 897, no 899, no $27, no $900, no $1,450 deposit, no CO-1 |
| Revenue pipeline $28,046.96 | **$9,590.30 real + $18,357.66 fixtures.** `HOTFIX5 Test` alone is 56% |
| `INV-2026-002` | $4,175, 90+ days, customer deleted, quote deleted, **unrecoverable** |
| `quotes_v2.job_id` | **NULL on all 199 rows.** Payment → invoice → quote → job resolves for 0 of 1 payments |
| Foreign keys | **not enforced** — no `PRAGMA foreign_keys=ON` anywhere |
| $0 MTD | correct, not a bug |

**Stripe — corrected.** D46 reported it unconfigured. The founder is
actively taking payments. The true finding is that the backend has no
`STRIPE_SECRET_KEY` and `vo_stripe_events` has 0 rows: **Empire is not
receiving webhooks.** Real money is moving outside the books.

**The founder has ruled: old invoice data is disposable.** Do not build
ceremony around preserving it. What matters is that the new process is
correct; the founder reviews and purges the old later.

### The interface

**~200 views, not 37.** Products render as client-side sub-apps; a
`find page.tsx` scan cannot see them. **27 dead endpoints. 10 of 37 sidebar
items fetch no live data.**

`MARKETPLACES 5 — All connected` is a **hardcoded literal** at
`MarketForgePage.tsx:33-35`. The page also calls `/listings` (404) instead
of `/api/v1/relist/listings` (200).

**Two corrections to earlier analysis.** All four customer counts
(5 / 500 / 100 / 5) are *correct for the queries they run* — different
slices with identical labels and no indication of scope. And Payments (14
callers) and Docs (9 callers) are already **shared components**; only
Customers is genuinely duplicated, 2 of 7+ sharing `CustomerList`.

### The recurring defect

Every H-number descends from the 2026-03-15 hallucination incident: **a
component producing confident output where an error belongs.** Eight
instances now, three of them in the interface layer, which nobody had
audited because it is CSS rather than code.

---

## §4 · Becky — settled, ready to cut

Quote `739556e1` / EST-2026-262 · **$4,084.05** · out-of-state, exempt ·
governed by issued **NELMA-814** (Estimate 814, 4/3/2026, via Lauren
Bassett) · **$95/width**, catalog $110 does not apply.

Two side windows **6 widths** (4 panels @ 1.5W); side large window
**4 widths** (2 panels @ 2W). Finished length **105″** — founder-supplied,
supersedes 98″. Heading **pinch pleat on ripplefold track** — founder
ruling; 814's "Ripplefold" superseded. Face JAB Chivasso **MY WAY
CH2904/070**, 122″ sheer, plain, **railroaded** — 17.20 m on the roll,
16.46 m ordered. Bench COM Vervain **PINDO 04**, bolt 0086, 5.00 yd;
**TWOFACE is dead.** Two Ryann benches 22 × 18 × 15.

**Before cutting:** goods were ordered against 98″ and will cut at 105″.
Railroading means the 122″ width carries the drop, so yardage should not
move — measure the bolt.

**R6:** birch ply french cleat is **no charge**. Cabinetry $343 → $275,
materials $1,291 → $1,223, governing total **$2,302.40**. REV G shows
$2,390.80 and needs reissuing as REV H if it went out. R6 is otherwise
**closed — reference only.**

---

## §5 · Three dispatches written, none issued

Order matters: **D48 rebuilds tables, D49 adds a category to the same
schema.** Run D48 first or they will collide.

**D48 · The spine** — `4583401999f25454109edac2162f2a4e4eacc15e805af2e3c876f76ceb6bd869`
Makes the invoice chain hold. Enables foreign-key enforcement (currently
off, so every declared constraint is decorative). Invoice → customer
mandatory; job and quote optional but recorded. Proves all three paths end
to end: quote → job → invoice, quote → invoice, direct invoice. Plus the
negative — an invoice with no customer must be **rejected**, shown firing.
Legacy rows marked, not deleted, in one pass at STEP 4.

**D49 · Sourced items** — `c71dc53894517eec11406a9a469ffba200e45a91eca36a91eb38afae3e0cdad4`
Lets MAX quote something never sold before — the R6 Amazon-lighting pattern
as a mechanism. New `sourced` line category carrying cost, source, URL,
timestamp and markup. Default **30%**, adjustable per line. Client
visibility per line: `absorbed` (default) · `listed` · `open_book` (the R6
pattern). A researched price without a source **raises**. **STEP 0a is the
gate: can MAX look up a price at all today?** Not assumed — Brave is listed
in Volume I but may be a fossil like the xAI routing D44 found.
**Ordering is explicitly out of scope**, including groundwork.

**D47 · One repository** — drafted, not hashed, not presented. Collapses
the worktree split into a single checkout and corrects `REPO-TRUTH.md`.
Read-only Phase 1, destructive steps gated. Available on request.

---

## §6 · Pending

### Ruled, not executed
- **Becky format pass** — brand reads `EMPIRE WORKROOM · POWERED BY EMPIRE
  WORKROOM` (should be Nelma's Workroom by Empire) · house field renders
  `BECKY · BECKY` · schedule ROOM column shows BECKY on all three rows ·
  cover says OPEN ITEMS 0 while each sheet lists five PENDING · stray inch
  mark on `PENDING"`. Plus §4's settled values — the pack still shows 15
  PENDING slots that are no longer pending.
- **Becky quotation document** — the third family; $4,084.05 has no
  rendered artifact.
- **R6 cleat to $0.00** with `no_charge: true` and a reason.
- **Vision → spec** — sketch to editable per-job spec. MAX fills directly,
  marked vision-derived, unconfirmed until accepted. Spec is a file per job
  connected to the client. Everything upstream is proven.

### Open, unruled
- **Stripe webhooks** — arguably worth more than D48. A correct chain with
  no inbound payments is still an empty ledger.
- **`/chat/stream` privilege divergence** — D45 left it reading the body
  while `/chat` no longer does. Two handlers, same purpose, different
  privilege logic. Next security dispatch.
- **Telegram is dead.** No bot process, zero inbound updates. Separate from
  D45, which is innocent. `/api/v1/max/telegram/status` returns 200 every
  minute regardless — the status lie is arguably worse than the outage.
- **MarketForge** — hardcoded literal plus a URL bug.
- **Marketing lane** — SocialForge, LeadForge, MarketForge as one group,
  with automation producing proposals the founder approves before anything
  goes out. Founder-named direction. Downstream of the books.
- **Accounts payable** — 51 vendors, nothing tracking what Empire owes.
- **Double-entry** — the transaction log is flat, which is why the Willard
  $27 cannot be sourced.
- **Corpus regeneration** — `stamp_provenance.py` exists; the step that
  assembles the corpus does not. Until it does, every session opener needs
  a staleness disclaimer. `CLAUDE.md`, `STATE_v8.md` and `DOCTRINE.md`
  should be deleted from Project knowledge or rewritten.
- **27 dead endpoints**, 10 dead sidebar items.

### H-numbers unallocated
STT 200-on-empty · `empire.db?mode=ro` zero-byte orphan · two unidentified
vision-fixture writers · `quotes_v2.job_id` NULL on 199 rows (D48 addresses)

### Client
- **Willard** — $1,450 deposit · CO-1 $7,500 void and unpriced · $900
  tracks billed against a note reading KEEP TRACKS / NO HARDWARE · **the
  client presentation carrying `MARKUP REGISTER · INTERNAL` went out** ·
  none of it is in the books
- **Eduardo Arias** EST-2026-114 — awaiting field measures and FR cert
- **Hudson & Crane** — two shades at 32½″ leave 5″ of a 70″ opening
  uncovered; quoted as requested, confirm before cutting
- **R6 Walnut** — cutting gated on COM leg height, wall-to-wall, baseboard
- **Bozzuto** EST-2026-111 — sent, unverified, do not raise proactively
- **Rolling workbench** — next after R6; founder has the material list

### Founder-side
Mic toggle in the MAX UI · shop computer Access login, untried: incognito ·
`luxe` Access path narrowing · **SPF record** before the next client email ·
credential cleanup: `FOUNDER_PIN` is in a **pushed** report at
`reports/2026-08-25_D28_step3_end_to_end.md`, API keys in
`~/.config/opencode/*.bak*`

---

## §7 · Interface — eight directions, none chosen

**A** Shop Floor (dark, job rail) · **B** The Bench (light, artifact drawer
with viewers for JPG/HEIC/PDF/SVG/DXF/STL/GLB/OBJ/PLY) · **C** The Sheet
(the house format as the interface; ink is confirmed, gold is not) ·
**D** The Ledger (money-first) · **E** Dispatch (terminal-native) ·
**F** The Wall (job tickets) · **G** Pocket (phone-first) · **H** Atlas
(the ecosystem map as home).

Proposed: six founder destinations — Floor, Max, Money, Customers, Shop,
Atlas — plus three genuinely separate products: LLCFactory (real, twelve
sub-views, a priced catalog — the registry's "Concept · Stub" is wrong),
ApostApp, AMP.

**Pricing Studio is the model every module should follow** — versioned
formulas and rate tables, snapshot-based, `override requires reason: true`,
`unknown category fallback: false`. H77's doctrine rendered as an interface.

Do not start the rebuild until a direction is chosen. D46 Phase 3's
per-batch inventory now exists and should be read first.

---

## §8 · First moves

1. **Read D46's nine reports** if not already read — particularly Phase 2
   (the books) and Phase 3b (endpoint overlap and dead surface).
2. **Issue D48**, hash-verified. It is the prerequisite for everything
   financial and for MAX ever recording an invoice.
3. **Becky format pass** — small, ruled, and the last thing between her
   pack and being sendable.
4. **Push whatever is local.** Every dispatch this week sat unpushed longer
   than it should have.
