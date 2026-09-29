# HANDOFF — 2026-08-26 (session close)

Read this before `CLAUDE.md`, `STATE_v8.md`, `DOCTRINE.md`, or anything in the
Claude project corpus. **Where they disagree with this document, this document
wins.** The corpus is four days stale — see §7.

Repo `~/empire-repo-main`, branch `feature/drawing-standard`, HEAD `5cc64ab`,
pushed and matching origin.

---

## 1 · WHAT LANDED THIS SESSION

Twenty commits. Five H-numbers touched, four closed.

| ID | Lane | Outcome |
|---|---|---|
| **D31** | H74 channel escalation — Phase 0 map | `ae0ea89` |
| **D32** | H74 corrections — Phase 0.5 | `17349be`. Reversed D31 §0g. |
| **D33** | H75 test isolation | `56d0b7e`, `cec92de`. Premise was wrong. |
| **D34** | H75 E2E live-backend writes | `e995055`, `c982fb6`. Opt-in gate. |
| **D35** | H76 Atlas completion signal — map | `b4fd795` |
| **D36** | H76 error path fix | `a6467a9`, `c452fa2` |
| **D37** | H77 pricing zero-guard | `a0742a7`, `f10770b` |
| **D38** | H77 pricing categories | `467f9e5`, `2c06432` |
| **D39** | H77 line override + Becky quote | `ff40713`, `5b97cd9`, `e2d4d18` |
| **D40** | H68 receipt gate | `0a8ce66`, `8345bc8`, `5cc64ab` |

Plus `19230df` (D28/D29 evidence trail), `5b419be` (D20 artifact script),
`29486fd` (gitignore fix).

**H74 — channel privilege escalation.** `/api/v1/max/code-task` reachable
unauthenticated because `channel` is a request-body field and `is_founder_message`
returns True for `""`. Mapped, corrected, evidence bounded. All 90 external POSTs
traced to the founder's own Starlink, Verizon and OVH-VPN sessions. **Design
defect, not an incident** — within a 12-day journal window; the Bypass policy is
older and nothing recovers hostname for successful requests. Fix not yet ruled.

**H75 — test isolation.** The carried premise (tests write to production via
module-level `DB_PATH` capture) was **dormant**, and the count was 21 modules not
9. The live defect was different: 17 E2E tests curl the running backend, which
writes to production on their behalf. Closed with `EMPIRE_E2E_BASE_URL` opt-in
gating plus a guard extended to the legacy mirror path. Default suite runs now
produce **zero production delta, proven**.

**H76 — Atlas completion signal.** No error path anywhere in the delegation
chain: `base_desk.ai_call` returned `""` on exception, `_chat_via_selected_routing`
returned success-shaped responses on total provider failure, `_log_async_task`
wrote `completed` regardless, and the notifier forwarded `task.result[:200]`
unchecked. 133 rows, all `error IS NULL`, blast-radius sample 0 of 5 real
deliverables. Also: `codeforge` was **absent from `KEYWORD_MAP` entirely**, so
code tasks could never route to it — 19 went elsewhere, 5 returned ForgeDesk's
quoting template. All four closed, verified on the live backend after restart.

**H77 — pricing engine.** Could return `$0.00` silently on 11 categories. Now
raises, naming category and missing input. Then: hardware sets, installation,
four lining rates, `manual_line`, `com_fabric`, general per-line override,
`no_charge`, and issued-document provenance.

**H68 — MAX fabrication.** Receipt-required gate, Option C. File-content claims
without a `file_read` receipt are blocked; mill specs get provenance at the
document boundary rather than inline. **A response claiming "I called file_read"
with empty `tool_results` is blocked** — the receipt must be in the tool results,
not the prose.

**Also landed:** port 8000 no longer binds `0.0.0.0` (`--host 127.0.0.1`,
verified on the running process via `ss`). The TTS 503 message now names actual
missing providers instead of a hardcoded `XAI_API_KEY`.

---

## 2 · THE BECKY QUOTE — THE DELIVERABLE

`quotes_v2` id **`739556e1`**, quote_number **`EST-2026-262`**, subtotal
**$4,084.05**, status **draft**, governed by issued invoice **NELMA-814**.
Out-of-state, tax exempt. Eight line items, all `rate_source = issued:NELMA-814`.
`search_quotes` finds it three ways.

| # | Line | Total |
|---|---|---|
| 1 | COM — JAB Chivasso MY WAY CH2904/070, 122" double width, 16.46 m | $0.00 |
| 2 | Pinch pleat on ripplefold track, 6 widths @ $95 | $570.00 |
| 3 | Pinch pleat on ripplefold track, 4 widths @ $95 | $380.00 |
| 4 | Batiste 118" lining, 16 yd @ $9.95 | $159.20 |
| 5 | Hardware — track, carriers, end caps, 48" batons, 3 sets @ $249.95 | $749.85 |
| 6 | Installation, 3 sets @ $145.00 | $435.00 |
| 7 | Benches — Ryann-style 22×18×15, qty 2, bespoke manual line @ $895 | $1,790.00 |
| 8 | COM — Vervain PINDO 04, 5 yd, both benches | $0.00 |

Subtotal asserted in code before the row was written.

**Job facts established this session:**
- Fabric: **Carlucci TWOFACE is superseded by PINDO** for the benches. Drapery is
  JAB Chivasso MY WAY CH2904/070 — **310 cm / 122", sheer, 60% polyester / 40%
  linen, tabby weave, plain (no repeat)**, fetched by hand from the mill site.
- PINDO 04, 5 yd, covers **both** benches. That is the whole COM line.
- Treatment is **pinch pleat pendants on ripplefold roller carriers** — the track
  hardware on line 5 is correct for that. Do not describe as ripplefold pleat.
- Width count stays 6 and 4.
- Bench construction (founder-dictated, verified): one continuous fabric piece
  wraps top and both sides, stapled underneath; second piece covers the bottom;
  front and back faces carry **upholstered caps nailed on** (not metal nail-head
  trim); box joint frame. No channels, no tufting.
- **All fabric on this job is COM.**

**Caveat for the record:** every priced line went through `manual_line`, not the
category pricers. Prices are correct and audited (`unit_price_used` per line),
and this is legitimate under the issued-document rule — but the drapery,
hardware, installation and lining pricers built in D38 have **not** been proven
end-to-end on a real quote.

---

## 3 · DOCTRINE ESTABLISHED THIS SESSION

**This is the most important section.** These decisions exist only in
conversation. Rates can be re-derived from the catalog; doctrine cannot.

**The money rule, both halves:**
> The engine may never produce a number nobody supplied.
> The founder may always supply any number, including zero.

Silence is the defect; instruction is authority. An override must be *supplied*,
never *defaulted* — `override_price: 0` raises, because zero is the absence of an
override, not an override. Zero has its own explicit door (`no_charge: true` plus
a reason).

**The issued-document rule:**
> Where an estimate or invoice has been issued to a client, the prices on that
> document govern that job. The catalog governs new work only.

This is why Becky prices at $95/width while the catalog stays $110. **A future
session must not "correct" an issued job to current rates.**

**PENDING never blocks:**
> A missing fact marks the item PENDING. It does not stop the document. The
> founder must always be able to get an estimate, a board or a drawing out, and
> to say "default" or "basic" and have the system proceed.

Alongside the money rule: the system may not fabricate, **and it may not
stonewall**.

**Production database:**
> Never restore, copy over, or replace the production DB while the backend is
> running. Delete test rows by identifier instead.

D33 did this under an instruction that was too broad. It cost nothing only
because nobody was using MAX at the time.

**Gates:**
> A gate the model can satisfy by claiming a tool call is not a gate.
> An instruction in a prompt is not a mechanism.

**Two permitted zeros, enumerable:** `com_fabric + customer_supplied`, and
`no_charge + reason`. Both two-keyed at engine and service layers. A third
appearing means H77 is gone.

---

## 4 · PENDING — TECHNICAL

**Ready to draft:**
- **D41 — Becky documents.** Presentation board + drawings for `739556e1`.
  **House format confirmed** (McLean/Whittington: serif display, gold corner tabs
  on viewports, three-column FIELD DATA / TREATMENT / FIELD CHECK base band,
  layout-math row inside the viewport frame, gold status strip, black footer).
  Bench cap detail **not** required to be drawn this round — a note is
  acceptable. Swatch placeholders where photos don't exist.

**Rulings outstanding:**
- **H74 fix option** — five in D31 §0f. Must cover BOTH predicates
  (`guardrails.is_founder_message` and `founder_auth.is_founder_message`).
  Sequencing note: D31 ranks code-task above `/max/chat`, but `/max/chat` grants
  `shell_execute`/`env_set`/`db_query` with no PIN branch. **Do not sequence off
  that table.**
- **R3, R6, R7, R8, R9, R13 remainders** — mostly ruled; hardware over 8 ft and
  under 4 ft are founder-supplied per instance by design.

**No dispatch yet:**
- Model consolidation to M3 (D36's error path is in, so failures now surface)
- **C2 gate hole** — chat desks substitute template strings when the AI result is
  empty or short (`if ai_result and len(ai_result) > 50` → template). A template
  is non-empty and is not the no-provider sentinel, so it **passes D36's C2
  gate**. Same defect class, one layer over.
- `quote_service.py:73-76` — the `any()` predicate still passes a
  supplied-but-zero input for categories the engine doesn't cover
- `openclaw_tasks` — 1443 of 7390 completed (19.5%); the other 80% unexamined
- H73 → H72 — `canonical_path.py:141` hardcodes `empire-repo` as bad root; must
  precede the 38-writer correction
- Chat attachments not visible or openable in MAX history — makes every
  image-derived claim unauditable, and no receipt gate can cover the vision path
- P1-T·d — chrome `T()` y-bbox over-estimates ~7pt (H71); 8pt tolerance is a
  workaround

**Founder-side:**
- **Shop computer Access login.** DNS resolves correctly to Cloudflare
  (`104.21.4.9`, `172.67.131.113`), policy `R1C2V2-Founder-Email` is correct with
  both addresses. **Untried: incognito window** — a stale `CF_Authorization`
  cookie produces exactly this symptom. Deferred by founder until back at the
  shop.
- `luxe` Access Path narrowing — D32 §5a produced the corrected minimal path set
- Report D35's `EST-2026-262` collision: MAX fabricated that number on 08-25, the
  guard caught it, and the sequential allocator has now assigned it to Becky's
  real quote. A future session reading D35 must not conclude the fabrication was
  real.

**Loose:**
- `uploads/EST-2026-261-mock.pdf` — an estimate number matching no client record,
  untracked, unexplained. Second orphan PDF this week.
- `max/memory.md` — regenerated nightly by `brain_sync` while tracked in git.
  Needs a gitignore decision.
- `~/empire-data/empire.db?mode=ro` — zero-byte file created 08-25 09:49 by a
  URI-style connect string passed without `uri=True`. Needs an H-number.
- Backup at `~/empire-data/empire.db.bak-D34-20260825-2250` can be removed after
  a few days.

---

## 5 · HELD QUESTIONS — DO NOT DROP UNTIL DISMISSED

The founder asked these to be tracked explicitly.

**Hardware (now known, not assumed).** Xeon E5-2650 v3, 20 threads, 31 GB RAM,
Quadro K600 979 MB. **GPU unusable for inference** — 2013 Kepler, under 1 GB.
Treat as CPU-only. 21 GB available.

**Ollama — recommendation: leave off.** A 7B on this CPU gives 3–6 tokens/sec and
worse tool-calling. Narrow exception: desk-routing classification. **Nobody knows
why `MAX_DISABLE_OLLAMA=true` was set** — answer that before ever reversing it.

**Voice conversation lane.** Founder wants mic-open conversation, not per-message
playback. Feasible shape: **local STT (`faster-whisper` small) + local TTS
(Piper) + M3 remote.** Both run comfortably on this box; cuts two of four network
hops. Needs VAD, auto-send, auto-play, barge-in, a toggle and visible state.
Real risk is latency, not hardware — several seconds reads very differently in
voice than in text; streaming TTS sentence-by-sentence is the difference between
a demo and something usable.
**Blocked on one ten-second test: click the speaker icon under a MAX message and
confirm audio comes out.** D40 verified TTS is *configured* (MiniMax primary),
not that it *synthesizes*.

**Document standard — mostly done, and an earlier read in this session was
wrong.** There IS a documented standard: `EMPIRE_DRAWING_STANDARD.md`,
`STANDARD_README.md`, `templates/registry.py`, `base.py`, per-treatment modules,
`fabric_registry.py`, `validator.py`, and `b2_qc.py` which encodes the format as
constants (`MARGIN_IN 0.32`, `HEADER_BAND_H_IN 0.92`, `FOOTER_BAND_H_IN 0.42`,
`TITLE_X_IN_MIN 7.90`) versioned against "golden v10" **and checks output against
them**. Renderers share; they do not duplicate.
Open: supersession marking on delivered PDFs (five `Willard_StyleB_Professional`
variants, three `EST-2026-111_Presentation_Boards` variants, no marker saying
which went to the client); whether the golden files are one standard or
successive versions (v10, R2, B2d all named); P1-T·d for H71.

---

## 6 · PENDING — CLIENT (UNTOUCHED THIS SESSION)

- **Willard InterContinental** (Maggie O'Neill): $1,450 deposit outstanding;
  CST-23 CO-1 (wood-arm bench, $7,500) void and needs repricing; Round Robin Bar
  track query open ("KEEP TRACKS / NO HARDWARE"); payment reconciliation open
- **Eduardo Arias** EST-2026-114 — awaiting field measurements and FR certificate
- **Hudson & Crane** (Jaye Langmaid) — coverage gap: 70" opening not fully
  covered by two shades at 32½"; yardage may be short for longer finished lengths
- **R6 Walnut Sofa Surround** (Philipp & Naomi via Lauren) — parked at founder's
  request. Three geometry conflicts and an $88.40 total discrepancy, none
  resolvable by assumption. Cutting gated on COM leg height, wall-to-wall width,
  baseboard height.
- **Bozzuto EST-2026-111** — status genuinely unverified. The D30 handoff says
  SENT; `STATE.md` says unsent since 7/31. Neither cites evidence. **Do not
  assert either.**
- **Rolling workbench** — next WoodCraft job after R6. Founder has a material list
  to hand over.

---

## 7 · CORPUS REGENERATION — A LANE, NOT A CHORE

The Claude project corpus and the repo's `STATE_v8.md` / `DOCTRINE.md` /
`HANDOFF_2026-08-20.md` are from ~2026-08-20. **Nothing from D28 onward is in
them.** A cold session reading the corpus would believe `~/empire-repo` is a
stale fork (it is the MAIN WORKTREE), that Bozzuto is confirmed unsent, and would
have none of §3's doctrine.

`scripts/stamp_provenance.py` exists and stamps exports with branch, commit and
export date. **What's missing is the generation step** — nothing assembles
`STATE.md` and `DOCTRINE.md` from reports and commits. That is why this is manual
and four days behind.

The lane: a script that regenerates state and doctrine from the report series,
runs the stamper, and writes to a known output path for upload. Then updating the
corpus is one command.

---

## 8 · METHOD NOTES

**What worked.** Map before fix, every time — D33's premise was wrong and only a
read-only phase caught it. Raw output over narration: D33 reported 39 and 17
guard fires, D34 pasted the grep and found 18. Demonstrated not asserted: every
guard in this session was proven by a deliberately-offending case, not by a green
suite. Founder rules; the dispatch presents options without recommending.

**What went wrong, three times, all mine.** I asserted a file existed after a
`cp` I never saw run. I built a two-message case on the wrong router file. I read
"four independent renderers" off four function names when they share a spec.
**All three were greps or inferences treated as proof** — the exact failure this
session spent twenty commits closing in the machine. A grep is a pointer, not a
finding.

**Also worth carrying:** the `:0` port discriminator. uvicorn's proxy middleware
sets `port = 0` when it substitutes a forwarded client, so `IP:0` in the access
log means external-via-tunnel and a real port number means genuine socket peer.
That single detail settled H74's attribution question and appears in neither
report.

**Standing rules.** Founder sends all client communication; Claude prepares only.
Dispatches are single-lane, sha256-verified, paste-ready inline, with explicit 🛑
gates. Per-file proof of closure, not aggregate counts. A test edited during a
run is a finding, not a step.

---

## 9 · SUITE BASELINE

At `5cc64ab`: **1511 passed / 130 failed / 28 skipped / 1 xfailed / 13 errors.**
Two known flakes, both pre-existing and unrelated:
`test_max_operating_registry.py::test_operating_registry_hot_reloads_and_keeps_last_known_good`
(clock-sensitive) and `test_vision_mmx_cli.py::test_call_vision_materializes_raw_base64_without_statting_as_path`.

Default runs produce zero production delta. The 17 `e2e_live` tests skip unless
`EMPIRE_E2E_BASE_URL` is set — **do not set it casually; it writes to production
through the live backend.**

Production row counts at close: `chat_session_turns` 402, `customers` 557,
`quotes_v2` 199, `jobs` 10, `invoices` 33, `intake_users` 654, `atlas_tasks` 136.

---

## 10 · FIRST MOVES FOR THE NEXT SESSION

1. **Restart the backend and ping MAX chat.** D40's gate was smoke-tested against
   a process running pre-D40 code. `systemctl --user restart empire-backend`,
   then POST to `/api/v1/max/chat`. D36 needed exactly this and it mattered.
2. **Click the speaker icon under a MAX reply.** Ten seconds, and it unblocks or
   kills the entire voice lane.
3. **D41 — the Becky documents.** House format, `739556e1`, board and drawings.
4. Then either the H74 fix ruling, or the C2 gate hole, or corpus regeneration.
