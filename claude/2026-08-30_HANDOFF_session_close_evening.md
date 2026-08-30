# HANDOFF · session close 2026-08-30 (evening)

**This document outranks the project corpus and both earlier handoffs.**
`CLAUDE.md` (both copies), `STATE_v8.md` and `DOCTRINE.md` are stale. The
2026-08-30 morning handoff is correct except where §1 corrects it.

```
repo    ~/empire-repo-main        branch  feature/drawing-standard
HEAD    0aeae8f                   pushed  NO — four commits local only
live data root  ~/empire-data     backend 127.0.0.1:8000
```

**Nothing is in flight.** R6 is finished. One dispatch fully executed.

---

## §1 · Corrections to the morning handoff

**R6 governs at $2,276.40, not $2,390.80.** The morning handoff's §1 says
"REV G governs at $2,390.80. It stands as issued." That figure is two founder
decisions old. Both reductions are founder rulings and both stand:

| cabinetry | change | total |
|---|---|---|
| $343.00 | first pricing of the plinth frame | $2,390.80 |
| $275.00 | birch ply cleats deleted, cut from 0.72 walnut on hand (−$68) | $2,302.40 |
| **$255.00** | plinth rails 1-1/2 → 1-1/4, 8/4 buy 6 BF → 5 BF (−$20) | **$2,276.40** |

Labour never moved (7.5 h × $95.00 = $712.50). Lighting never moved ($948.00).
The whole gap is the two cabinetry reductions.

**The $2,276.40 invoice is NOT void.** The morning handoff calls it void on two
grounds and both fail against the artifact. It says the render used a
`client.py` carrying $75.00 shop supplies — but the PDF prints $255.00
cabinetry, which already contains the collapsed $95.00 line. It says the render
wrongly applied 30% to cabinetry — but $2,390.80 and $2,302.40 are both computed
that way too, so it cannot be what distinguishes it. The document was correct;
the figure it was compared against was stale.

**The `$75 → $95` item is not a rate.** It is the shop supplies and finish lot —
five consumable rows (glue, splines, pins, abrasives, finish) collapsed into one
$95.00 line. It sits inside all three cabinetry figures.

**Founder switched to US spelling mid-session on 18 Aug.** Any generator
rendering `Labour` / `cheque` predates that. Both surviving copies did.

---

## §2 · What landed

Four commits, **none pushed**.

| | |
|---|---|
| `c4c1b8f` | R6: land invoice generator, correct source to governing REV G total |
| `fc78f20` | R6: fill founder fields, live payment link, remove check option |
| `4f707d1` | R6 invoice: bring into house sheet language |
| `0aeae8f` | MAX: disable runtime .env override from stale tree (pulled live Stripe key) |

---

## §3 · The live Stripe key — closed

**`~/empire-repo/backend/.env` held `STRIPE_SECRET_KEY=sk_live_…`** — a
full-access live key, in the tree the corpus calls stale, unencrypted, since
May.

**It was reachable by voice command.** `tool_executor.py:4726`, inside
`_reset_max_state`, called:

```python
load_dotenv(os.path.expanduser("~/empire-repo/backend/.env"), override=True)
```

Founder-triggered by "MAX reset", "reset yourself", "clear cache" — through
Telegram, `/chat`, any desk. It fired at runtime and **overrode the
systemd-supplied environment** with the stale tree's values. Every downstream
`os.getenv("STRIPE_SECRET_KEY")` after that point pointed at production money.

`MEMORY.md` said `STRIPE ✓ (test keys)`. **That was false**, and it is the file
that auto-loads every session.

**Closed:** key rotated twice (the first roll did not take — the dashboard still
showed a May creation date) · the `load_dotenv` line commented out and committed
at `0aeae8f` · the stale `.env`'s `STRIPE_SECRET_KEY` blanked · eleven `.env`
backups in that directory still carry the dead key and were **not** deleted ·
new key placed in `~/.config/empirebox/empire-backend-secrets.env` at `0600` ·
backend restarted and confirmed on `200`.

**Still open:** the key in the secrets file is a **standard full-access**
`sk_live`. It can charge, refund and pay out, and MAX can reach it. §7 of the
morning handoff wanted payment-links-only. A restricted key (`rk_live_`) is the
mechanism; it has not been created.

**`MEMORY.md` still says test keys.** Correct it before the next session.

---

## §4 · R6 — finished

**Invoice `INV-2026-119` · $2,276.40 · due on receipt · approved 27 Aug 2026.**
Rendered at
`reference/recovered/r6_woodwork/out/R6-INVOICE-change-order.pdf`
(gitignored — `out/` added to `.gitignore` this session).

Payment link `https://buy.stripe.com/14A14gdGWgaBgMzeWlg7e01`, QR live and
scanning, clickable link annotation on the printed URL.

**FOUNDER-PENDING: nobody has confirmed the Stripe page shows $2,276.40.**
Not verifiable from EmpireDell. Do this before sending.

**What the six phases actually found:**

- `invoice_change_order.py` **did not exist in the repo**. It had only ever
  existed as a chat artifact. Now committed.
- Both generators wrote to `/mnt/user-data/outputs/` and `/home/claude/` —
  Claude container paths. **They had never run on EmpireDell.** Fixed to a
  local `out/`.
- `invoice_change_order.py` loaded the literal name `"client.py"`, and a
  *different* `client.py` sits in that directory computing **$2,302.40**. The
  generator would silently have loaded it. Now pinned by path and by hash.
- `client_change_order.py` on EmpireDell was at the **$2,390.80** revision.
  Neither reduction had ever been applied to it.
- Importing `client_change_order.py` **re-rendered the approved client change
  order** as a side effect. Now behind `if __name__ == "__main__"`.

**Hardening now in place:** `CLIENT_SHA` pinned to `abdc03a3…` (refuses on any
byte change) · `GOVERNING_TOTAL = 2276.40` assert · completeness gate refusing
any block character in `INV` or a non-live `PAY_URL` · birch cleat renders at
$0.00 by name with its reason. **All five gates were proven by deliberate
tampering**, refusals captured verbatim.

**The deps were never missing.** An earlier session reported `cairosvg`, `segno`
and `pypdf` absent; that check ran under bare `python3`. They are all present in
`backend/venv`. **Use `~/empire-repo-main/backend/venv/bin/python3` for these
generators.**

---

## §5 · Invoice numbering — decided, but the series is broken

**`INV-2026-119`**, parallel to the estimate series (`EST-2026-114`).

The `invoices` table is **not a usable numbering source**: 33 rows, **all
`draft`**, three incompatible formats (`INV-2026-006`, `INV-2026-0010`,
`INV-0033`), and most of it test data — "E2E Test Client", "H46-test",
"Woodcraft Test Client", four rows in the founder's own name. `id` and
`invoice_number` are not in step. **No R6 row exists**; `INV-2026-119` is not
in the database.

`sqlite3` is not installed. Use `~/empire-repo-main/backend/venv/bin/python3`
with the `sqlite3` module.

---

## §6 · House sheet language — found, not documented

`EMPIRE_CLIENT_DOC_STANDARD.md` specifies sheets, the spec object, QC gates and
a fixed footer. **It contains no colour palette.** The six constants are
hardcoded and duplicated in every generator:

```python
INK,HAIR,MUTED,GOLD,RED,PAPER = "#4E5257","#DEDAD3","#96907F","#B8912F","#B4553C","#FBFAF7"
```

There *is* a house page frame, implemented in code in both
`drawing_set_generator.py` and `client_change_order.py`: hairline border inset
28/26 · title 40/52 at 13.5pt · subtitle 40/68 · right marker PW-40/52 · brand
line PW-40/68 · rule at y=80 · rule at PH-46 · footer left job·client, centre
RED status marker, right sheet·date.

The invoice had none of it. `4f707d1` brought it into the frame.

**Founder ruling: the shared-module extraction is PENDING, not now.** Pull
`page()`, the six colours and the helpers into one module both generators
import. This is also the groundwork for MAX ever rendering in house style —
**MAX currently has no brand tokens at all.**

**Known cosmetic debt, founder said omit:** Date/Terms now float alone below the
header rule, and there is ~45pt of dead space between that rule and BILL TO.
The header block was not tightened when the rule moved up 22pt.

---

## §7 · Behaviour notes on M3

**`CLAUDE.md` auto-loaded again**, in the same session that was told it was
stale. Observed directly: "Loaded CLAUDE.md". §7 of the morning handoff already
names this; it is still unfixed.

**M3 reasoned about whether the founder's own generators were malware** at least
four times across two sessions — files named in the dispatch, in the founder's
own repo. Judgment spent there is judgment not spent on the numbers.

**Twice it asserted a visual layout was clean** with the supporting tool output
collapsed and unviewable. Both times the founder or strategic Claude had to
render the PDF independently. **A layout claim without a visible render is not
evidence.**

**Good behaviour worth keeping:** it stopped correctly at every gate; it caught
its own failure to restore state between two refusal tests and redid them; it
re-read a file rather than forcing a patch when an edit failed; it refused to
identify or edit the unknown `client.py`.

**Strategic Claude erred too** — three times in one stretch asserting repo state
from a transcript fragment without asking for the command. Also typed a derived
board-foot figure (`3.2 BF net`) that was not derivable from anything recorded;
caught and reverted before it reached a dispatch.

---

## §8 · Client

- **R6** — **DONE.** `INV-2026-119`, $2,276.40, live link, founder to verify
  the Stripe amount and send. Founder sends.
- **Willard** — $1,450 deposit · CO-1 $7,500 void and unpriced · $900 tracks
  against a KEEP TRACKS / NO HARDWARE note · the client presentation carrying
  `MARKUP REGISTER · INTERNAL` went out · none of it is in the books
- **Becky** — pack delivered; the $4,084.05 quotation document still has no
  artifact, and it is what carries the benches
- **Eduardo Arias** EST-2026-114 — awaiting field measures and FR cert
- **Hudson & Crane** — two shades at 32½″ leave 5″ of a 70″ opening uncovered
- **Bozzuto** EST-2026-111 — sent, unverified, **do not raise proactively**
- **Rolling workbench** — next after R6; founder has the material list

**Unresolved on R6:** whether the copy that physically went to the client shows
$2,390.80. If so, this invoice is $114.40 lower — in their favour, but worth a
line rather than a surprise.

---

## §9 · The lesson this session paid for

**A stale figure costs more than a wrong one.** Four turns were spent
re-litigating $2,390.80 against a generator that was simply two rulings behind.
The morning handoff's void ruling was itself built on that stale comparison. The
fix is not more assertions — it is that the governing figure and the source that
produces it must move together, which is what `GOVERNING_TOTAL` plus the
`CLIENT_SHA` pin now enforce.

**Provenance gates need the right name.** The arithmetic gate could not see
where `MATSUB` came from; the new gate could not either, until it was pointed at
`client_change_order.py` by path rather than at whatever `client.py` happened to
sit beside it. **Naming the wrong file correctly is still wrong.**

**Rescue before you need to, again.** R6's invoice generator existed nowhere but
a chat artifact. Had that conversation been lost, the only recoverable form of
this document would have been a PDF.

---

## §10 · First moves

1. **PUSH.** Four commits are local only, including the security fix and R6's
   only copy of the invoice generator.
2. **Verify the Stripe page shows $2,276.40**, then send `INV-2026-119`.
3. **Restricted key** (`rk_live_`) scoped to payment links, replacing the
   full-access `sk_live` MAX can currently reach.
4. **Stripe webhooks.** If the client pays tomorrow, nothing records it. The
   books stay empty.
5. **Correct `MEMORY.md`** — it says Stripe is on test keys. It is not.
6. **`label_station.py:52`** — unblocks every E2E test of the chain.
7. Shared style module (§6) · `CLAUDE.md` deletion or rewrite · D-COVER-2 ·
   D49 · D50 FK enforcement · Becky's quotation document.

**Loose ends:** eleven `.env` backups in `~/empire-repo/backend/` still carry
the dead `sk_live` · `max/memory.md` has been showing as modified all session
and nobody has looked at it · two `.bak` files and `uploads/EST-2026-261-mock.pdf`
sit untracked in the tree · `settings.json` in `~/.claude/` is 353 KB with seven
rotated backups, which is an accumulator, not a settings file.

---

*Founder sends. Nothing here goes to a client without explicit approval.*
