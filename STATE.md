# STATE.md — EmpireBox Live Snapshot (v8)
As of: 2026-08-20 (evening) · Maintainer: founder + strategic Claude · M3 executes
Replaces v7 (2026-08-19 late). `claude/DOCTRINE.md` is how work is done ·
`claude/BACKLOG_UPDATE_*.md` are the register deltas · this is the orientation page.

## THE GOAL — founder, 2026-08-19
**MAX is to take strategic Claude's place.** Not assist — replace. The honesty
layer, the expensive part, is built and has now held under two days of real
pressure. What he lacked was SIGHT, and most of that was fixed today.

## ⚠️ THE FINDING OF 2026-08-20 — read this before diagnosing MAX again

**Six separate layers sat between the founder and the model, each silently
deciding what MAX could see, say or do. Every one of them first looked like MAX
being unreliable. None of them was.**

| # | Layer | What it did | Status |
|---|---|---|---|
| 1 | H52 prompt selector | 40-keyword substring match routed "ordinary" turns to a compact prompt with **NO TOOL ROSTER AT ALL**. MiniMax has no native function calls, so compact + MiniMax = the model could not see a single tool | **RETIRED** `b01b78a` |
| 2 | H53 replay block | tool-result scaffolding appended on `role="user"` — MAX correctly read it as prompt injection and refused founder authorization | **FIXED** `28dcb42` |
| 3 | H62 PIN gate | substring match on "pin" hard-blocked a question about a document *pin* | **NARROWED** `b9e43c2` — context-anchored, 14/14 |
| 4 | H63 chat auto-reroute | silently **rewrote `file_read` → `run_desk_task`**; the model never saw a `file_read` result. Naming the tool did not help — the rewrite happened downstream of intent | **CLOSED** `a22ce96` — reads pass, writes still route |
| 5 | H64 pre-search guard | same `[SYSTEM:]`-on-user-channel shape, second site; also re-queried "answer using only verified data" **when there was no data** | **CLOSED** `e9c18cc` |
| 6 | H65 / H66 | third and fourth sites of the same shape (inter-round follow-up, factual_guard) | **CLOSED** `c67dce0`, `1cdfacc` |
| 7 | H67 round_results | UnboundLocalError at router.py:2677/:3445 — read before init. Fires whenever a response contains malformed tool blocks on the first loop iteration. Latent since f97d808, 2026-07-16, 39 days | **CLOSED** `abc3619` — AST regression guard |

**Regression guard `1cdfacc`:** an AST walk over `backend/app/` fails CI if any
`AIMessage(role="user", ...)` carries a `[SYSTEM:` prefix. Handles f-strings and
concatenation. A fifth site cannot be added silently.

**The lesson, and it is now DOCTRINE:** *when a model behaves badly, check what
it was given before concluding what it is.* Six for six. MAX refused to
fabricate throughout — no invented commits, no chat-entered PIN accepted, no
claimed access he lacked.

**Corrected diagnosis, for the record.** On 8/19 MAX proposed reading from
`~/empire-repo` and, asked where the belief came from, said honestly that he did
not know. Strategic Claude concluded he was confabulating. **He was not** — the
literal string `Code: ~/empire-repo/` was in his system prompt at
`system_prompt.py:497`. He was reporting what he had been told. Fixed `88814b2`.

## ⚠️ H68 — THE ONE FAILURE THAT WAS NOT ENVIRONMENTAL — OPEN, FOUNDER DECISION

2026-08-20 19:11. MAX quoted `codetask_stage3_clean.txt` (80 bytes, two
lines) as a multi-paragraph task brief, and invented a ten-file renderer list
under `backend/app/services/drawings/` — a directory that does not exist.
**He never called `file_read`.** The journal confirms no such tool call on
that turn.

Trigger: filename cue ("stage3", "clean") + STATE.md mentioning "drawing
standard" + `git status` untracked list + no tool result grounding the
response. Any three of four suffice.

Why the honesty layer did not fire: the anti-fabrication rule depends on the
model recognising it lacks proof. It felt it had proof. The output was
confident, well-structured markdown — the *shape* of a real brief.

**Every other failure in this sweep was environmental — blinded, rewritten,
or forged upstream — and MAX reasoned correctly on bad inputs. This one is
not.** It bears directly on the handoff goal: an orchestrator that
confabulates from a filename cannot hold the strategic role regardless of how
clean the plumbing is.

Four options, founder's decision, no recommendation recorded: (a) tighten the
system prompt · (b) runtime gate on confident-fabrication shapes · (c) change
the model · (d) accept and design around it.

Full analysis is in claude/BACKLOG_UPDATE_2026-08-20.md.

## ✅ CODE EXECUTION RESTORED — dead 106 days
**2026-05-06 → 2026-08-20.** The founder's week-old open question — *what broke
MAX's coding, removed capability or deliberate gate?* — is **ANSWERED: neither.**

`parse_tool_blocks` (`tool_executor.py:175`) honours three response formats.
`code_task_runner.py:399` scored the result by reading `response.function_calls`
alone. **A model replying in valid JSON was parsed successfully and scored as
having emitted nothing.** Two places deciding one fact; one wrong; invisible
because only one was consulted (DOCTRINE rule 12).

Why it survived three months: **every failure branch discarded the model's
response.** `task.result` was set in exactly one place — the happy path. 5,931
verdicts, zero evidence. And the nine `logger.error` calls never reached
journalctl because the *installed* unit was missing `StandardError=journal`
while the repo unit had it.

- **Proof:** `reports/2026-08-20_stage3_liveproof.md`. Task 7380 appended to a
  file; md5 mutated, exact-match content, **the file actually changed on disk.**
- **Second proof:** task 7379 targeted `/tmp` and was **refused by H57 Phase 3's
  canonical-root guard** — a gate built the previous day catching a live write
  outside the repo. The dispatch named `/tmp`; the guard was right and the
  instruction was wrong.
- Commits: `e854621` · `91b3ca0` · `ccfb576` · `a663e43` · `9bb2d6e`

## H57 — CANONICAL ROOT, THREE PHASES
Phase 1 map `994cf75` · Phase 2 WIP `13119fc` · Phase 3 `59d356d`, `3b34a86`.

**The 8/19 finding restated: MAX's tools were pointed at the stale fork.**
`ALLOWED_ROOTS` explicitly *authorised* `~/empire-repo`; `_file_read`/`_file_write`
defaulted to it; his git context was built from it; and **`quotes.py` and
`openclaw_worker.py` were writing client uploads, generated quote files and
drawings into a tree nobody reads.** Fixed: one validator, `.empire-canonical`
marker, path argument removed.

An audit correction found a real gap during Phase 3 — the resolver returned a
valid-looking path to a nonexistent directory *inside* canonical when `..`
collapsed lexically. Now refuses `..` segments outright.

**Phase 2 remains WIP.** Two bench fixtures parked under **H58** — the template
demands a plain `height` and rejects a message carrying *seat height* and *back
height*, which is more specific, not less. **Do not edit those fixtures to
pass.**

## H61 — CONFIG ON DISK ≠ CONFIG IN FORCE (nine instances)
A recurring class, now named. Repo unit vs installed unit · `ALLOWED_ROOTS` ·
`git_ops` hardcoded cwd (H57 Phase 3 missed it) · the stale-fork path in the
prompt body · the stale fork's venv, diverging since March and missing
`pdfplumber`/`pdfminer.six`/`pypdfium2` · a `.env.local` with a live xAI key
tracked since February.

**Doctrine: source-of-record must be source-of-force. An install-path audit is
owed and has not been done.**

## ✅ SECURITY — key revoked, repo pushed
A live `XAI_API_KEY` sat in a tracked `founder_dashboard/.env.local` since
February. Revoked by the founder; file untracked and gitignored (`e3c361a`).
Historical copies are inert.

**`feature/drawing-standard` now has an upstream** — `git@github.com:r22gir/Empire.git`.
Before 2026-08-20 the branch had never been pushed: everything lived on one
disk with a 72% root partition. **Check `.env` and `backend/data/` before any
first push** — that is now a standing rule.

## PORTAL SURFACE — still drifting, still undispatched
V1 currency truncates (`$8,599.6`) · V2 five test rows in the live quote list ·
V3 customers 5 vs 100 · V4 outstanding $34,391 vs aging $5,965 · V5 accepted
quotes reads 0 despite Bozzuto approved · V6 orphaned $4,175 receivable (I9 made
visible) · V7 EST-2026-113 exists as a PDF but not in the store.
**The visible-fixes dispatch is written and has never been fired.**

## OPENCLAW — a graveyard, not a queue
7,379 rows: **5,933 failed, 1,439 done, 0 pending.** The "7,372 queued" badge
counts every row ever written and has read as active work for months (**F5**,
open). 5,895 of the failures came in a three-day burst, May 4–6.
**Do not purge the rows** — they are the record and the fixture source. Filter.

## INFRASTRUCTURE — GREEN
Reboot proof passed 8/17. Backend `:8000` = user unit `empire-backend`; restart
is `systemctl --user restart empire-backend` and nothing else. Four tunnels
supervised; Hermes `:8787` never stopped. Kernel pinned 6.8.0-31. Disk 72%.
**I13/I14 closed 8/19** — a single Google account security event took OAuth, the
browser lockout and both founder addresses together, and returned them together.
**E1 two-way email is unblocked; `check_inbox` has still never been tested live.**

## DOCUMENT TEMPLATE ENGINE (P1-T) — PAUSED AT ·c
Standard pin **`1813c59043b7b05f87626dd4e66a3487`** (`e0035b4`), 8 amendments.
Layers separated, G5 catches the McLean 21-vs-22 split with a committed fixture.
**Untouched since 8/19 afternoon.**
Two founder corrections stand: **MAX is one door among several** (the engine is
a service layer), and **job media carries forward** intake → quote → invoice.
Whether the camera writes to the same canonical store as LuxeForge intake is
**still unverified** and outranks the rest if wrong.

## LIVE CLIENT WORK — founder handles all client communication
- **Bozzuto EST-2026-111 $8,599.60 APPROVED — unsent since 7/31.**
- **McLean / Whittington (C7)** — 11 sheets, 24 openings after the founder ruled
  the centre wall is three windows. Re-render through the template engine.
- **INOUYE / Hudson & Crane** — blocked on the drapery rod/opening width.
- **R6 / WoodCraft** — three cutting gates. **Willard** — $1,450 deposit unpaid.

## NEXT — in order

**H68** — *founder decision*, NOT a task. Pick (a) tighten prompt, (b) runtime
gate, (c) change model, or (d) accept. Every other line below is a task;
this one is the decision that scopes the rest of the handoff.

1. **H57 Phase 2** finish (bench fixtures belong to H58 — do not edit to pass)
2. **P1-T·c** builder interface — the M-lane depends on it
3. **H62** — `shell_execute` PIN-gated with no working unlock surface, reported
   three times; it partially re-blocks what code restoration opened
4. **H61 install-path audit** — nine instances found, nobody has swept
5. **V1/V2** visible fixes — dispatched, never fired
6. **F5/F6** badge counter and retry budget
7. **Retire the drawing router** (H57) — the design verdict stands: anything
   deciding before the model runs guesses with less information than the model
8. **Four hand-maintained tool registries** — same class as the two
   `DRAWING_KEYWORDS` lists
9. **Re-run the audit test** — MAX reads the R3 dispatch and `fc42fe3` himself.
   Answer key published before the test existed. **This is the handoff proof.**

## GOTCHAS
Stale fork `~/empire-repo` — any reference is drift (nine instances) · Cloudflare
ingress is in the Zero Trust dashboard, not YAML · files born in chat reach the
machine by DOWNLOAD, never paste · **`sqlite3` CLI is NOT installed** — use the
venv's Python · use `~/empire-repo-main/backend/venv` only · a negative fixture
that fails for the wrong reason proves nothing · **the task list is not
evidence; the live system is.**
