# HANDOFF · session close 2026-08-30

**This document outranks the project corpus and the 2026-08-29 handoff.**
`CLAUDE.md` (both copies), `STATE_v8.md` and `DOCTRINE.md` are stale. The
2026-08-29 handoff is correct except where §1 below corrects it — and those
corrections matter, because acting on the stale version cost four turns of
re-litigation this session.

```
repo    ~/empire-repo-main        branch  feature/drawing-standard
HEAD    d886ddb                   pushed  yes
live data root  ~/empire-data     backend 127.0.0.1:8000
```

**Nothing is in flight.** Three dispatches written and hashed, none running.

---

## §1 · Corrections to the 2026-08-29 handoff

**R6 REV G governs at $2,390.80. It stands as issued. No REV H.**
The prior handoff §4 says the governing total is $2,302.40 and that REV G
"needs reissuing as REV H if it went out." It went out, and the founder has
ruled it stands. Both statements in §4 are superseded.

**The $2,276.40 change-order invoice is void.** It was rendered in Claude's
container from a `client.py` carrying $75.00 for shop supplies; all six
copies on EmpireDell carry $95.00. It also applied 30% to cabinetry. Two
independent errors that happened to land near a plausible number. Every
assertion in the generator passed — they checked the arithmetic chain, never
the provenance of the input. **Do not send it. Do not patch it.**

**The 30% markup applies to Amazon-sourced lighting only, not to cabinetry
materials.** Founder ruling, this session. `client_change_order.py` applies
one `MARKUP` constant to both `MATSUB` and `LEDSUB`; that is now wrong. The
ruling governs new work — it does not reprice REV G.

**The birch ply cleat was deleted, not zeroed.** `birch=68.00` sits in RATES
with no MAT row consuming it. Under the money rule it should be a line at
$0.00 with `no_charge: true` and a reason, so it prints under NOT BILLED by
name. Applies to future work; REV G is closed.

**There are zero real payments in the books.** The prior handoff says the
payments table holds 1 row. It does — and D48 STEP 1 established that row is
a test fixture (`reference='test'`, part of the CF-2026-002 lifecycle test).
The founder is taking payments directly through Stripe. Nothing recorded.

---

## §2 · What landed

Six commits, all pushed.

| | |
|---|---|
| `42194ad` | D48 STEP 1 — schema rebuild, ruling-A migration, STOP 2 |
| `d205445` | D48 STEP 2 — seven trust-mode writers hardened; STEP 1 made reproducible |
| `5933fed` | Becky D42 harness rescued from `/tmp` |
| `202a005` | Becky format pass — 8 of 15 slots settled |
| `1e93664` | D-COVER dispatch written |
| `022fd7e` | McLean cover fix — OPEN ITEMS count, trailing separator |
| `88eec2a` | Becky rebuild after D-COVER — **pack deliverable** |
| `d886ddb` | D-COVER-2 dispatch written |

---

## §3 · D48 — what it found

**STEP 1.** Schema rebuilt: `invoices.customer_id`, `payments.invoice_id`,
`jobs.customer_id` all NOT NULL with FK. Five chain orphans reparented to a
tombstone customer (`4ea5a8c917600732`, labelled TEST RESIDUE — the identity
was unrecoverable, no name survived on any row). FK violations 173 → 168, all
remaining ones non-chain. Backup at
`~/empire-data/empire.db.bak-D48-20260829-220122`, sha256 `d44360ec…68c8b5`.

**STEP 2 corrected a premise I had wrong.** NOT NULL is enforced by SQLite
unconditionally; `PRAGMA foreign_keys` gates only REFERENCES. And all seven
writers use the `get_db` factory, which sets the pragma. So none of them could
write a NULL customer — STEP 1 had already closed that. What they did instead
was raise uncaught `IntegrityError` → HTTP 500. Corruption channel became an
availability failure. The fix was still right; the reason was different.

**Four findings larger than the fixes:**

**quote→job has never functioned in production.** `lifecycle_service.py:127`
sends `status='quoted'`, not in the `jobs.status` CHECK. Line 128 sends
`business_unit` into the `job_type` column, also not in that CHECK. Verified
against a live-DB copy; production CHECKs are byte-identical to `init_db.py`.
Not degraded — never worked. Encoded as `xfail(strict=True)`.

**The suite has zero coverage of `lifecycle_service`.** No test imports it.
This is why both D48 Δ=0 results were vacuous: nothing exercised the
constraints, so adding them changed nothing.

**STEP 1 existed only in the live DB file until STEP 2 fixed it.**
`init_db.py` still said `customer_id TEXT`, and the test-schema builder never
created `invoices` or `jobs` at all. One `init_db()` from evaporating.

**FK enforcement covers 10 of 84 connections.** The constraints are declared,
not enforced, in the running backend. D50.

**H79 logged** — `jobs_unified.py:1147` `create_job` returns the created row
via `SELECT * FROM jobs ORDER BY created_at DESC LIMIT 1`. Second-granularity
timestamps; observed returning an unrelated fixture job.

**197 of 199 quotes** have NULL `customer_id`, so quote→invoice raises. The
refusal is now honest (400, actionable) but the function is not restored.
Backfill is a follow-on; no quote data was touched.

---

## §4 · Becky — deliverable

Quote `739556e1` / EST-2026-262 · **$4,084.05** · out-of-state, exempt ·
governed by issued **NELMA-814** · $95/width.

**Customer of record is Lauren Bassett (LB Design).** Becky is the end client
at 4600 Fieldstone. Same structure as R6 — Lauren carries both jobs, and
prices issued to Lauren govern across them.

Pack at `reference/becky/Becky_client_pack.pdf` — gitignored (`.gitignore:88`
excludes `reference/**/*.pdf`), so it exists only on EmpireDell. Text extracts
and PNGs are committed.

Settled this session: brand now Nelma's Workroom by Empire · `BECKY · BECKY`
fixed · schedule ROOM column reads LIVING ROOM / DINING / STUDY · stray inch
mark gone · trailing separator gone · OPEN ITEMS reads 3/2/3 instead of
0/0/0 · 8 of 15 dimension slots filled (LENGTH 105″ all rooms, HEADING pinch
pleat on ripplefold, W1 6 widths, W2 4 widths).

**Benches — option 1.** Construction rule on W1's check list, no separate
sheet: *2 ea, Ryann style, 22 × 18 × 15. Box joint frame. One continuous
fabric wrap, no channels, no tufting, no caps. COM Vervain PINDO 04, bolt
0086, 5.00 yd — customer supplied, no fabric line.*

**Before cutting:** goods ordered against 98″, cutting at 105″. Railroaded
122″ face carries the drop so yardage should not move — **measure the bolt.**
This is on the pack as a note; nobody has measured.

**Still missing:** the $4,084.05 quotation document. The pack is a
field-measurement set with no line items and no total. That third family has
no rendered artifact, and it is what carries the benches commercially.

---

## §5 · Dispatches written, none run

**D-COVER-2** — `641ef83c70c269ee83ecc16a39377f085bd555a588d70065168f5e279ae370d4`
A `{"settled": True}` marker on check items that the cover's count filters
out. The bench block inflates W1's OPEN ITEMS by one because `check` is the
only multi-line field available. Needs a McLean byte-identity proof. Small.

**D49 · Sourced items** — `c71dc53894517eec11406a9a469ffba200e45a91eca36a91eb38afae3e0cdad4`
Now has a settled rule to implement: 30% on Amazon-sourced items, not on
cabinetry, adjustable by the founder at any time. **That last clause means the
rate must be snapshotted onto the issued document, not read live** — otherwise
changing 30% to 35% silently reprices every invoice already in a client's
hands. Versioned rate table, invoice stores its version. R6's change order is
the reference case for `open_book` visibility. STEP 0a is the gate: can MAX
look up a price at all today?

**D47 · One repository** — drafted, not hashed, not presented.

---

## §6 · Ruled but not written

- **D50 · FK enforcement** — route all 84 `sqlite3.connect` sites through the
  factory at `db/database.py`. Patching call sites is instruction-shaped; the
  85th one written next month silently disables it. Load-bearing: D48's
  constraints are not enforced in the running backend until this lands.
- **`label_station.py:52`** — connects to a hardcoded production path at
  import, tripping conftest's guard, so `app.main` cannot be imported under
  test. No E2E can reach the chain through the production door. **High
  priority** — this plus the `lifecycle_service` coverage gap is why two Δ=0
  results proved nothing.
- **W1 CHECK defects** — product decision on whether `status='quoted'` becomes
  an allowed value or the writer sends `pending`, and whether `job_type` stops
  receiving `business_unit` or the CHECK widens.
- **D48 STEP 3/4** — three-path proof plus the negative. Blocked from proving
  much until `label_station` lands.

---

## §7 · Open, unruled

**Stripe — the largest one.** Zero real payments recorded while money moves.
Founder ruled MAX may create invoices but nothing else. Two mechanisms make
that a boundary rather than an instruction: a **restricted key** (write on
payment links, nothing else) and **payment links rather than Stripe Invoices**
— the latter emails the customer on finalize, which would be a send without
the founder. Webhooks are separate and are what makes a paid invoice ever read
as paid.

**Generators live in `reference/`.** R6's five were in `reference/recovered/`
— the only surviving copy, unversioned until this session. Becky's harness was
in `/tmp` for three days. The McLean generator, which produces client-facing
packs for multiple jobs, sits in `reference/mclean/`. None of this belongs in
a reference path. The `presentation/woodwork/` port either did not happen or
did not land.

**`CLAUDE.md` auto-loads every session** — both `~/Downloads/CLAUDE.md` and
`~/empire-repo-main/CLAUDE.md`, despite explicit instructions to disregard it.
One session cited it as authority after confirming it had been disregarded.
Delete or rewrite. Corpus regeneration is still unbuilt.

**Bypass permissions is on** in Claude Code. Every gate this session held
because M3 chose to stop, not because anything prevented it from writing.

**Also open:** H79 · `payments_v2` read by six aggregates that silently return
$0 (H78) · 27 dead endpoints · MarketForge hardcoded literal · accounts
payable · double-entry · `/chat/stream` privilege divergence · Telegram dead
while its status endpoint returns 200.

---

## §8 · Client

- **Willard** — $1,450 deposit · CO-1 $7,500 void and unpriced · $900 tracks
  against a KEEP TRACKS / NO HARDWARE note · the client presentation carrying
  `MARKUP REGISTER · INTERNAL` went out · none of it is in the books
- **Becky** — pack deliverable, quotation document missing, bolt unmeasured
- **R6** — closed, reference only. REV G stands at $2,390.80
- **Eduardo Arias** EST-2026-114 — awaiting field measures and FR cert
- **Hudson & Crane** — two shades at 32½″ leave 5″ of a 70″ opening uncovered
- **Bozzuto** EST-2026-111 — sent, unverified, **do not raise proactively**
- **Rolling workbench** — next after R6; founder has the material list

---

## §9 · The lesson this session paid for twice

**Arithmetic gates are not provenance gates.** The R6 invoice asserted
`MATSUB + LEDSUB → GOODS → GOODSELL → TOTAL` and every assertion passed. None
of them could prove `MATSUB` came from anywhere real, and it hadn't. The same
shape appeared in D48: a passing test suite proving nothing because no test
reached the constraint. A green result answers only the question it was
written to ask.

**Rescue before you need to.** R6's generators had to be recovered. Becky's
harness was rescued with three days to spare. The McLean generator is still
in a reference directory.

---

## §10 · First moves

1. **Stripe.** Zero real payments is worth more than any remaining schema
   work. A correct chain with no inbound money is still an empty ledger.
2. **D-COVER-2** if you want the pack fully clean — small, hashed, ready.
3. **`label_station.py`** — unblocks every E2E test of the chain.
4. **Becky's quotation document** — $4,084.05 with no artifact, and it is
   what carries the benches.
5. **Delete or rewrite `CLAUDE.md`** before the next session opens on it.
