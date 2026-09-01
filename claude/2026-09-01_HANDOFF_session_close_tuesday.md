# HANDOFF · session close 2026-09-01 (Tuesday)

**This document outranks the project corpus and all earlier handoffs.**
`CLAUDE.md` (both copies), `STATE_v8.md` and `DOCTRINE.md` are stale.
The 2026-08-30 evening handoff is correct except where §1 extends it.

```
repo    ~/empire-repo-main        branch  feature/drawing-standard
HEAD    de313a6                   pushed  YES
live data root  ~/empire-data     backend 127.0.0.1:8000
```

**Nothing is in flight.** R6 is closed and invoiced. D52 shipped. Two new
hazards logged and not fixed.

---

## §1 · R6 — CLOSED

**`INV-2026-119` · $2,276.40 · draft · due on receipt.**

- Bill to **Lauren Bassett / LB Design**, c/o Philipp & Naomi
- Approved by client 27 Aug 2026 · invoice dated 30 Aug 2026
- Payment link `https://buy.stripe.com/14A14gdGWgaBgMzeWlg7e01` —
  **founder confirmed the Stripe page shows $2,276.40**
- PDF at `reference/recovered/r6_woodwork/out/R6-INVOICE-change-order.pdf`
  (gitignored) and copied to `~/Downloads/INV-2026-119.pdf`
- DB row `4ff575239f44b97b`, `customer_id` `da405e616eba4f22` (Lauren Bassett),
  `source_type='generator'`, `source_id` = the pinned generator hash

**It has not been sent.** Founder sends.

**Governing chain, verified and pinned:**

    255.00 + 948.00 = 1203.00  ->  x1.30 = 1563.90  +  712.50  =  2276.40

`GOVERNING_TOTAL = 2276.40` asserts in the generator. `CLIENT_SHA` pins
`client_change_order.py` at `abdc03a340384fdf5625f22f00d82b15708e753dcbe8cc96b8b01b5e12f46c25`.
All five gates were proven by deliberate tampering, refusals captured verbatim.

**Commits, all pushed:**

| | |
|---|---|
| `c4c1b8f` | land invoice generator, correct source to governing REV G total |
| `fc78f20` | fill founder fields, live payment link, remove check option |
| `4f707d1` | bring into house sheet language |
| `a21fc0f` | bill to Lauren Bassett / LB Design, name end client in project block |

**Open on R6:** whether the copy that physically went to the client shows
$2,390.80. If so this invoice is $114.40 lower — in their favour, but worth a
line rather than a surprise.

---

## §2 · D52 — MAX can read the database

Commit `de313a6`, pushed. Three files, +48/−15.

**What was wrong.** `db_query` sat in `DANGEROUS_TOOLS` beside `shell_execute`
and `env_set`, so it was PIN-gated. It is the **only** tool that reads the
invoices table — nothing else touches it. So MAX could never answer an invoice
question truthfully. It could only refuse, or invent.

**What shipped:**

- **Read-only by mechanism.** The connection now opens
  `sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)`. SQLite itself refuses
  writes: `OperationalError: attempt to write a readonly database`. Previously
  read-only was enforced by string inspection on a read-write connection — an
  instruction, not a mechanism.
- **Blocklist false positives fixed.** The substring scan blocked
  `SELECT created_at` on `CREATE` and `SELECT updated_at` on `UPDATE`. Two of
  the most common columns in the schema were unqueryable. Now word-boundary
  matched, and four keywords added (`PRAGMA`, `VACUUM`, `REINDEX`, `REPLACE`)
  which are redundant against a read-only connection by design.
- **Ungated.** `DANGEROUS_TOOLS = {"shell_execute", "env_set"}`. Those two
  remain gated. The HOTFIX 4.2 comment block was corrected in three places
  where it still named `db_query`.

**Founder ruling: full read access.** MAX can read any table in `empire.db`.
Gate later if wanted.

**Verified in chat, post-restart:** invoice count 34 ✓ · `INV-2026-119` returns
$2,276.40, draft, correct client, all four line items, and the notes field ✓ ·
`created_at` readable, which was impossible before ✓

---

## §3 · H80 — narration over a failed tool call

**The incident.** Asked "what invoices are outstanding?", MAX returned a
formatted table: `INV-2026-001 | Smith Residence | $1,250.00`,
`INV-2026-002 | Anderson Office | $890.00`, total $2,140.00. Then offered to
send payment reminders to those customers.

None of it was real. `INV-2026-001` does not exist. `INV-2026-002` is real but
is **$4,275.00**, status `partial`, `client_name` NULL. There is a `Jane Smith`
at **$93.00**. **Real fragments, invented rows around them** — which is harder
to catch than pure invention.

It carried a `Tool: db_query` receipt. The tool had fired and returned a **PIN
refusal**. Asked later for the raw SQL, MAX said: *"Let me actually query the
database now instead of trusting my recall."*

It reproduced a second time after D52's ungating, on a different failure:
a query on a nonexistent `customer_name` column returned an error, and MAX
reported **"$270.00, status: paid"** for `INV-2026-119`.

**Why the existing guard missed it.** `should_halt_after_tool_failure` already
existed and already worked — for tools in `VERIFICATION_REQUIRED_TOOLS`. That
set contains `search_invoices`, `search_payments`, `search_customers`, and did
**not** contain `db_query`. `_tool_failure_reason` returned `None`, so no
failure was ever collected. The gate was built, correct, and blind to the one
tool that reads the books.

**The fix — one line plus a round guard:**

- `db_query` added to `VERIFICATION_REQUIRED_TOOLS`. Set membership, not prose
  matching — shape-agnostic, so the next fabrication shape needs no new pattern.
- **Round-aware halt.** `if _tool_round >= 1 and should_halt_after_tool_failure(...)`.
  Round 0 is free so the model can self-correct a typo'd column; rounds 1 and 2
  halt. Strict halting on round 0 would have made every recoverable SQL error
  terminal.
- **The backstop is what makes round 0 safe, and it was verified:**
  `tool_results_list` is initialised once *before* the round loop and
  accumulates across all rounds, so `_apply_truth_guardrails` sees the whole
  turn. A failed `db_query` in any round gates the final response.

**Verified:** the same Q2 that produced "$270.00, paid" now returns $2,276.40
with every line item correct, and the round-0 self-correction is visible in the
transcript.

**Not shipped, deliberately:** a `TOOL_FAILED` prose marker and a no-retry
directive. Both are instructions. Shipping them beside a working mechanism
invites the next reader to think the prose is load-bearing. Add them only if
the mechanism proves insufficient.

---

## §4 · H81 — founder flag is not an identity check · **HIGH**

**Not fixed. Logged only.**

`is_founder_message()` in `guardrails.py:96-118` returns `True` for **any**
Command Center channel — `web`, `web_cc`, `cc`, `command_center`,
`command-center` — with no identity check. The channel name alone is sufficient.

`tool_executor.py:459` wraps the **entire** dangerous-tools branch in
`if founder:`. So `founder=True` skips the PIN check completely.

**Consequence: `shell_execute` and `env_set` are PIN-gated against Telegram and
nothing else.** Anything reaching the backend as `channel="web"` gets shell
execution with no PIN.

Mitigating: port 8000 is bound to `127.0.0.1`. Not mitigating: Tailscale is in
the stack, and a prompt injection through any content MAX reads would run as
founder.

H74 (D45) closed a separate empty-channel default. It did not narrow the
web-is-always-founder rule.

Candidate fixes, smallest blast radius first: strip `founder=True` for
`shell_execute`/`env_set` specifically · a web-specific passcode env var ·
detective audit-log and alert. **Founder rules.**

Logged at `memory/hazard_h81_founder_bypass.md`.

---

## §5 · H82 — the tool badge is not a receipt

**Not fixed. Logged only.**

The chat UI renders a `Tool: X` badge for every tool block it finds in the
**model's own prose** — `parseToolBlocks` in `ChatScreen.tsx:12-26`. It has no
reference to whether the call succeeded, or whether it ran at all.

So the badge has never proven a tool executed. It proves the model wrote a tool
block. Every "Tool: db_query" receipt in this session's fabrications was of this
kind.

D52 filtered the *other* badge source — the `tool_result` SSE event now emits
only on success — so one of two paths is closed.

Candidate fix (Option α): apply `strip_tool_blocks` server-side to the streamed
text before yielding, at `router.py:3653, 3701, 3799, 3805`. The frontend then
never sees the blocks and cannot render a badge from them.

Logged at `memory/hazard_h82_chat_ui_tool_badge.md`.

---

## §6 · What the books actually look like

34 invoices. **`INV-2026-119` is the only one with a real total and a recorded
provenance.** `source_type` is NULL on all 33 others.

`INV-0026` through `INV-0033` all carry `total = 0.0`, including three for
Bozzuto. Most `client_name` values are NULL. Three incompatible numbering
formats coexist: `INV-2026-006`, `INV-2026-0010`, `INV-0033`. `id` and
`invoice_number` are not in step, so `ORDER BY id` does not return the highest
numbers.

`INV-2026-002` shows status `partial` — partially paid — which contradicts
"zero real payments." Either it is test data or the payments picture is wrong.
**Nobody has checked.**

`customer_id` is `NOT NULL REFERENCES customers(id)`, so no invoice can exist
without a customer record. There are 560 customers; Philipp & Naomi are not
among them.

`sqlite3` the binary is not installed. Use
`~/empire-repo-main/backend/venv/bin/python3` with the `sqlite3` module.

---

## §7 · Notes on M3 this session

**Good.** Stopped at every gate. Caught its own failure to restore state between
two refusal tests and redid them. Re-read a file rather than forcing a patch
when an edit failed. Found the footer by content when the dispatch's line
number was stale. Refused to identify or edit the unknown `client.py`. Flagged
an 8pt layout gap as needing founder eyes rather than asserting it fine.

**The H80 root cause was M3's finding, not the dispatch's.** The proposal to add
`db_query` to `VERIFICATION_REQUIRED_TOOLS` — extending an existing mechanism
rather than inventing one — was better than what was asked for.

**Watch.** `CLAUDE.md` auto-loaded again in a session explicitly told it was
stale. It reasoned about whether the founder's own generators were malware at
least four times. It asserted a clean layout twice with the supporting render
collapsed and unviewable — both times the founder had to look.

**Strategic Claude erred too.** Asserted repo state from transcript fragments
without asking for the command, three times in one stretch. Typed a derived
board-foot figure (`3.2 BF net`) that was not derivable from anything recorded;
caught and reverted before it reached a dispatch. Wrote a dispatch naming a file
that did not exist in the repo.

---

## §8 · Client

- **R6** — **CLOSED.** `INV-2026-119` ready to send. Founder sends.
- **Willard** — $1,450 deposit · CO-1 $7,500 void and unpriced · $900 tracks
  against a KEEP TRACKS / NO HARDWARE note · the client presentation carrying
  `MARKUP REGISTER · INTERNAL` went out · none of it is in the books
- **Becky** — pack delivered; the **$4,084.05 quotation document still has no
  artifact**, and it is what carries the benches
- **Eduardo Arias** EST-2026-114 — awaiting field measures and FR cert
- **Hudson & Crane** — two shades at 32½″ leave 5″ of a 70″ opening uncovered
- **Bozzuto** EST-2026-111 — sent, unverified, **do not raise proactively**
- **Rolling workbench** — next job after R6; founder has the material list

---

## §9 · PENDING

### Security — do these first

1. **H81 · founder flag** — `shell_execute` and `env_set` effectively ungated
   from web. HIGH.
2. **Stripe restricted key** (`rk_live_`) scoped to payment links, replacing the
   full-access `sk_live` MAX can reach.
3. **Stripe webhooks** — if the client pays `INV-2026-119` tomorrow, nothing
   records it.
4. **Eleven `.env` backups** in `~/empire-repo/backend/` still carry the dead
   rotated `sk_live`.

### Correctness

5. **H82 · tool badge** — Option α, server-side `strip_tool_blocks` on the four
   stream yield sites.
6. **`label_station.py:52`** — hardcoded production path at import blocks
   `app.main` under test; unblocks every E2E test of the chain.
7. **`INV-2026-002` shows `partial`** — reconcile against "zero real payments."
8. **Invoice numbering series** — three formats, 33 rows without provenance,
   `id` and `invoice_number` out of step.
9. **`_reset_max_state` reports "Environment reloaded"** when nothing reloads
   any more. A message that lies.
10. **D50** FK enforcement across the remaining database connections ·
    **D49** sourced line categories · **D-COVER-2** (written, hashed, ready)

### Build

11. **Vision-fill entry path** — MAX reads a document, proposes customer +
    invoice row, founder verifies, it writes with `source_type='vision_entry'`.
    Reusable for Bozzuto, Becky, Willard. **Founder ruling: this is the plan;
    founder verifies every write.**
12. **Generators should write DB rows, not only PDFs.** R6 needed a bespoke
    script. This is the structural gap that keeps work invisible to MAX.
13. **Shared style module** — extract `page()`, the six colour constants and the
    helpers into one module both generators import. Also the groundwork for MAX
    ever rendering in house style; **MAX currently has no brand tokens at all.**
14. **Becky's quotation document** — $4,084.05, no artifact.

### Housekeeping

15. **`CLAUDE.md`** — delete or rewrite. It auto-loaded again today after being
    told it was stale.
16. **`max/memory.md`** modified across two sessions; nobody has looked.
17. Two `.bak` files and `uploads/EST-2026-261-mock.pdf` untracked in the tree.
18. `~/.claude/settings.json` is 353 KB with seven rotated backups.
19. **Invoice header cosmetics** — `Date` and `Terms` float alone below the
    header rule with ~45pt of dead space above BILL TO. Founder said omit twice.

---

## §10 · Things that will bite if forgotten

- **Launch Claude Code from `~`, not from inside the repo.** Memory writes only
  reach the `-home-rg` scope. There is no memory directory for
  `-home-rg-empire-repo-main`, so a session started inside the repo opens blind.
  No error, no warning.
- **`~/empire-repo` must not be deleted.** It is the main worktree and holds the
  single git object store for every branch and stash. `MEMORY.md` used to say
  "ignore" it; that line has been corrected.
- **Use `~/empire-repo-main/backend/venv/bin/python3`** for the generators and
  any DB work. Bare `python3` is a different environment and lacks `cairosvg`,
  `segno` and `pypdf` — an earlier session wrongly reported them missing because
  it checked the wrong interpreter.
- **A stale frontend tab causes fabrication.** The first H80 incident coincided
  with a Command Center tab frozen at 12:12, all truth badges reading `unknown`,
  and a backend running pre-commit code. A hard refresh and a restart fixed it.
  **Treat `unknown` badges as a stop, not cosmetics.**
- **`MEMORY.md` was corrected this session** — the Stripe line said test keys,
  the config heading said `backend/.env`, the canonical-repo line said to ignore
  `~/empire-repo`, and nine paths were asserted where only two were verified.
  Two backups sit alongside it.

---

## §11 · The lesson

**A gate that has never refused has been written, not tested.** Every gate that
shipped today was proven by deliberate tampering — `GOVERNING_TOTAL` against a
wrong figure, `CLIENT_SHA` against a corrupted hash, the source moved aside, the
completeness gate against a block character, the halt against the exact typo
that caused the fabrication. Each refusal was captured verbatim.

**The H80 guard was correct and blind.** It had been built, it worked, and it
missed because one tool name was absent from one set. The failure was not in the
logic. It was in the inventory. **Check what a mechanism covers, not only that
it exists.**

**A receipt is not proof.** The `Tool: db_query` badge that made three
fabrications look verified was rendered from the model's own prose. It never
consulted whether the call ran. Trust the artifact, not the badge on it.

---

*Founder sends. Nothing here goes to a client without explicit approval.*
