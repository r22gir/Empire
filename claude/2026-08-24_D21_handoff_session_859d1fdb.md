# HANDOFF — strategic Claude session, 2026-08-22 → 2026-08-24

Read this first, then `CLAUDE.md`, then the corrections below that supersede it.
This covers one very long session and what the next one needs that is not
obvious from the artifacts.

**Branch:** `feature/drawing-standard` · **HEAD at close:** `0f1b50e`
**Remote:** `git@github.com:r22gir/Empire.git` — everything below is pushed.

---

## HOW THIS WORKS

Strategic Claude writes paste-ready dispatches → founder pastes into MiniMax-M3
Claude Code sessions on EmpireDell → M3 reports found / changed / tests / commit
→ strategic audits the report against the dispatch → founder rules. Single lane.
Map before fix. 🛑 stop-gates between phases.

Files born in chat reach the machine by **download**, never paste. Founder
verifies the `sha256` prefix in the filename on arrival.

**The founder sends all client communication. Agents draft; he sends.** Never
offer to send.

---

## CORRECTIONS THAT SUPERSEDE CLAUDE.md — READ BEFORE ACTING

**1. `~/empire-repo` is the main worktree and owns the shared object store.**
It holds the shared git object store at `~/empire-repo/.git`;
`~/empire-repo-main` is a linked worktree pointing into it. **Acting on
`~/empire-repo` as if it were a stale tree destroys every local branch, lane and
stash on the box.** CLAUDE.md's canonical-path paragraph needs rewriting: the
RuntimeError enforcement is right, its stated rationale is wrong. **The doc
sweep is queued and not done.** (See H72 for the writes-still-landing finding
and H73 for the `canonical_path.py` hazard.)

**2. Hermes is three services, not two.** Verified 2026-08-22 (R10):

```
founder → External Hermes ("Harry", opencode-remote, Tailscale) → MAX
       → Empire Hermes (hermes-gateway) + OpenClaw
```

CLAUDE.md says HERMES = opencode-remote. Incomplete, not wrong. `hermes-gateway`
is a Telegram relay on `127.0.0.1:3000`. Neither is wired into MAX's agent
hierarchy in code — the hierarchy is real, the wiring was never built.

**3. FOUNDER_PIN "UNSET" at import is a KNOWN FALSE ALARM (H59).** A shell-
launched python does not inherit the unit's `Environment=`. Verify against
`/proc/<backend-pid>/environ`, never a shell probe. This cost M3 a dozen probes
once and misled strategic Claude twice this session.

**4. `sqlite3` CLI is not installed.** Use
`~/empire-repo-main/backend/venv/bin/python3`.

**5. `max/memory.md` always shows modified** — nightly brain_sync. Never commit
it.

---

## WHAT CLOSED THIS SESSION

### R9 — the openclaw model-name leak · `1898437` `15ffc29` `c21c8a6`
`provider=openclaw, model=openclaw` on 5,679 failures. **Nine leak sites**, not
the four originally traced. Fixed by resolving `DEEPSEEK_MODEL` at call time,
never a hardcoded literal — absent env yields `None`, explicitly unknown, never
a fallback string. Plus a drift guard that FAILS when the backend and openclaw
drop-ins disagree on `DEEPSEEK_MODEL` (they had drifted: `deepseek-chat` vs
`deepseek-v4-flash`). Proven live: `provider=deepseek, model=deepseek-v4-flash`.

### R11 — the validator's blind spot · `4f4abbe` `67f69e9`
Report `reports/2026-08-22_214238_R11_validator_blindspot_8a34569d.md`.
The validator credited only `file_write`, `file_edit`, `file_append`. Work done
via `shell_execute` was invisible — **the task did the work and was recorded as
failed.** Fixed to check ground truth (git status diff around execution) with
`working_dir` REQUIRED and a `ValueError` if absent. Proven live: both a tracked
tool and `shell_execute` now complete.

**Corpus finding: only 12 of 5,721 "no file changes" rows carry any result text
at all, and the validator has passed exactly ONCE in 7,390 rows.** The pipeline
had essentially never completed a code task.

### R10 / R10.1 — the remote lifeline · `077451a` and follow-ups
`opencode-remote` was on `0.0.0.0:8787` **UNSECURED** — a coding agent that can
edit and execute, reachable from the whole LAN, five days up. Now:
`127.0.0.1:8787` only, behind Tailscale Serve with a real cert at
**`https://empiredell.tail39cac8.ts.net`**, homescreen-installable, no prompt.
Tailscale authenticates the device; the app has no password.

Certs live at `~/.certs/` (moved OUT of the working tree — a private key one
`git add .` from being committed).

### R12 — the drawing path · report `b621f307`, commit `0f1b50e`
Five fixes, all proven live:
- **The freeze** — 13-21s hang was the LLM retrying `sketch_to_drawing` on text.
  Fixed with `looks_like_continuation(text, history)`. **13.0s → 0.076s.**
- **Fraction parsing** — `69 1/2" wide` parsed as **width=2** (the 2 out of 1/2).
  Every fraction and feet-inches format failed silently. Only whole numbers and
  decimals ever worked, so the parser had never handled real shop input.
- **Plausibility gate** — a 2" shade rendered silently. Now bounded.
- **Dimension formatter** — five sites printed one dimension three ways: header
  `70"`, title `69.50"`, layout math `69-1/2"`. `int(round(69.5))` = 70. **Half
  an inch, gone, on a shop drawing.** All now use `_fmt_in`.
- **Fold count** — header hardcoded `9 folds @ 7-1/8"` from the golden
  reference; every other height printed a fold count that was not its own.

**And the QC gate was wired for the first time.** `enforce_b2_qc` at
`b2_qc.py:207` was authored during the B2 rollout, extensively tested, and
**never called in production.** Wiring it revealed the mis-tunings AND real
defects nobody had seen.

### MAX's inbound email — restored after ten weeks dark
`check_inbox` was fully built and wired. The failure was `invalid_grant` — the
refresh token had expired. **Google expires refresh tokens after 7 days while an
OAuth app is in "Testing."** Token minted 2026-06-07, dead by ~06-14. That is
why the founder's two 8/16 messages to MAX went unanswered.

Fixed by re-running OAuth **and publishing the app** (Google Cloud → project
`empire-max-492115` → Auth Platform → Audience → Publish). Now permanent.
Verified: 10 messages, 485 unread.

**Note the filter:** `MAX_EMAIL=max@empirebox.store`. `gmail_reader.py:84` is
`filter_to or os.getenv("MAX_EMAIL", ...)` — it always filters to ONE address
and cannot say "everything." The founder wants this widened. **Do not widen
blindly:** that inbox holds API keys in plaintext.

---

## THE PATTERN THAT EXPLAINS MOST OF IT

**Three of this program's costliest defects share one shape: a surface that
reports more confidence than it has.**

- the morning brief frozen at `Inbox: 194 items` for **eleven weeks** (live
  CPU/RAM alongside dead counters, presented identically)
- the ✅ Verified badge meaning "the call returned," not "the data is current"
- H68's confident, well-structured, ungrounded brief
- the uptime card measuring boot, labelled "since last backend restart"
- `CST-DRAFT · 07/26/2026` hardcoded on every sheet — **this misled strategic
  Claude into misdating a live artifact**

The honesty layer was built in February for the **model's output**. It has never
been applied to the **system's own reporting surfaces.** That is the gap.

**The second pattern: one source, or several agreeing by luck.** Model name,
`LABOR_HRS` 7.5-vs-5.5, five dimension formatters, fold count, `DEEPSEEK_MODEL`
drift, three channel widths. Every fix this session was the same fix.

---

## HISTORY — READ IT, IT CHANGES YOUR JUDGMENT

**`docs/2026-08-23_D12_history_email_record_v2_0d35af52.md`** — the project's
history reconstructed from ~250 threads in `empirebox2026@gmail.com`, which was
created for this project so the mailbox IS the record.

The short version:

- **2026-02-22, MAX's first run.** His own self-description ends with *"being
  honest about what's implemented versus planned."* **The honesty layer is
  constitutive, not remedial.** Rounds enforcing it maintain original intent.
- **2026-02-28, the first-run protocol** — MAX states four beliefs and asks the
  founder to correct them. Two were wrong. **That is the MAX Continuity panel
  today**, reporting "startup truth is stale." Same mechanism, six months apart.
- **The goal, stated 02-28 and unchanged: "an OS for resellers and service
  businesses."** Not internal tooling. The founder is the first customer and his
  own successful use is the acceptance test. Multi-tenant scaffolding is
  on-thesis.
- **The May burst is explained.** 5,895 failures on 05-04/05/06 — 99.3% of May,
  unexplained through three autopsies — are the **v10 test lane**. The founder
  emailed `v10.empirebox.store/system-admin` on 05-04. Remove from open lists.
- **The downsize was consolidation under financial pressure.** Late May,
  payments failed across Fireworks, ChatGPT Plus and xAI in one week. 06-07 a
  MiniMax key was bought. The provider roster reading `credits_unavailable` /
  `missing_key` is the residue.
- **Hermes was an import** — a YouTube link the founder sent MAX on 06-09. That
  is why its naming never resolved.
- **MAX is embedded in real business.** Nelma Sinnugrot emails
  `max@empirebox.store` directly, forwarding client work from Hudson & Crane.
- **MAX still does real work.** 08-17 he returned a genuine analysis mapping an
  InfoWorld piece onto EmpireBox's architecture.
- **F4 egress works, visibly.** EST-2026-111 went out from MAX addressed to the
  founder, cc the founder.

**Strategic Claude's error, named by the founder and worth inheriting:** eleven
rounds ran before anyone read the history. Building a model of MAX from failure
artifacts produces defect-shaped judgment. *"We may be drifting away ourselves
of what MAX is supposed to be, who he was."*

---

## DOCTRINE ADDED THIS SESSION

**`docs/2026-08-22_D14_doctrine_section_viii_54db6059.md` — §VIII, code born in
chat.** Rules 42-46. Five working generators that produced a **delivered client
document** existed nowhere on disk and nowhere in git. The dispatch describing
them was committed; the code was "attached separately." **The documentation
survived and the code did not.**

**Section VII (naming), committed `f6dbb9d`.** Rules 35-41. Round labels
globally unique and never reused (two unrelated bodies of work were both called
R7 and it cost a round). One round, one file. Filename format
`<YYYY-MM-DD>[_HHMMSS]_<ROUND>_<slug>_<h8>.md` where `h8` is the first 8 hex of
the file's own sha256 — **derived, never chosen.** Strategic Claude supplies no
`HHMMSS` because it cannot tell time and must not invent one.

---

## FILES RECOVERED THIS SESSION — ALL NOW IN GIT

Nine generators and the delivered artifacts existed only in chat logs and
`~/Downloads`. Three separate discoveries in one day.

```
reference/recovered/r6_woodwork/     arch · client · present · shop · lab ·
                                     power2 · hookup (+ rev_G variants)
                                     → produced the R6 REV G client pack
reference/recovered/                 drawing_set_generator.py (7/31, STALE —
                                     109" not REV G's 114 1/2", no plinth)
                                     label_generator.py · willard_drawing.py
                                     2026-07-31_SESSION_SUMMARY.md
                                     CLAUDE_label_station.md
                                     R6-power-LED-install-guide-REV-G.pdf
                                     R6-3d-viewer-v2-23in.html
reference/mclean/                    mclean_drapery_set_generator.py (1201 ln)
                                     McLean_Whittington_..._RevA.pdf (11 sheets)
reference/delivered/                 Willard_StyleB_Professional*.pdf (B1/B2/B3)
                                     EST-2026-111_Presentation_Boards*.pdf
                                     EST-2026-110_Rev2_ONeil_Willard*.pdf
                                     XCarve_Series_Catalog.pdf
                                     EmpireSlotBench_Assembly_CAM.pdf
                                     EMPIRE_CLIENT_DOC_STANDARD_v1.0_upholstery.md
reference/delivered/willard_3d/      3D model + presentation-set pipeline —
                                     three-d-stage.js · iso-3d.html ·
                                     doc-page.js · image-slot.js + v4-v6
                                     iteration renders + GP&J Baker tearsheet
```

**A sweep of Downloads/Desktop/Documents for `.py .svg .dxf .stl` now returns
clean** — every generator is in git. **NOT swept:**
`/media/rg/BACKUP1/BACK_UP_NW_MIGRATED_2026-06-09/` (the Beelink migration,
PhotoRec `recup_dir.*` folders) and
`~/Documents/Claude context handoff block - Claude.html`.

⚠️ **`tools/2026-08-23_D20_artifact_sweep_d2c5f93b.sh` has a bad keyword** —
`empire` matched 49,000 backup files. Fix or delete before anyone runs it.

⚠️ **`.gitignore` has `reference/**/*.pdf`.** It silently excluded a REV G
power guide; the commit reported success and landed one fewer file than it
named. Use `git add -f` for reference PDFs and **check `git status` before
committing.**

---

## DISPATCHES WRITTEN AND NOT YET FIRED

All committed in `claude/`. Read the dispatch, not this summary, before firing.

| round | file | what it does |
|---|---|---|
| **R13** | `2026-08-23_D15_dispatch_r13_woodwork_port_213bac7a.md` | port the 7 R6 generators into `backend/app/presentation/template/` |
| **R14 v2** | `2026-08-23_D18_dispatch_r14v2_document_catalogue_2a365bbb.md` | inventory every document type INCLUDING SETS, then render one of everything |
| **R15** | `2026-08-23_D17_dispatch_r15_sourced_knowledge_37ac04a3.md` | provenance rail for web-sourced facts on client documents |
| **R16** | `2026-08-23_D19_dispatch_r16_woodcraft_products_696f80bf.md` | WoodCraft product line — real catalogue, 3 document types per product |

**R13 caveat:** the 2026-08-18 dispatch it follows names
`backend/app/services/presentation/` — **that path does not exist.** The live
framework is `backend/app/presentation/template/` (13 files, 2,223 lines,
`938131a` + `bceaa12`), an in-progress port of the McLean generator. Do not
create a second architecture.

**R14 v2 Phase 0** sweeps the box for delivered work outside git — written after
three separate discoveries in one day.

**R16 hard rule:** M3 must NOT invent species, grade, finish, load rating,
feeds, tolerance, price or lead time. Everything unsourced is
`FOUNDER INPUT REQUIRED`. A fabricated load rating on a designer's spec sheet is
H68 where it damages the business.

---

## OPEN — RANKED

### Blocking the founder's actual goal
He wants dispatches to run unattended and email him when they hit a decision.
**Executor works (R9/R11), outbound works, inbound works as of today, remote
oversight works.** Two things remain:

1. **PERSISTENCE.** `/api/v1/max/code-task` keeps state in an **in-memory dict**
   (`code_task_runner._tasks`, singleton line 1073, dict line 712). **Lost on
   every restart** — R9's own Phase 3 evidence is already a 404. Scoped in R11
   §13 at ~80 lines. Without it a task parked awaiting the founder evaporates.
2. **THE PARK-AND-ASK PRIMITIVE.** A 🛑 gate becomes: write the question, email
   the founder, set `BLOCKED_ON_FOUNDER`, stop. His reply resumes it. Small once
   persistence exists.

### R12's remaining seven (report `b621f307`)
- **O-7 · Drapery `pinch_pleat` computes a left stack of 0.007" against an
  expected 0.944" — a 130× error.** Found only because the gate was wired and
  the bypassed test was restored. Real fold-pattern bug.
- **O-1 · viewport cannot hold a wide shade.** 78% fill against an 80%
  threshold. M3 tried four variants; each broke something else. The front
  elevation is portrait-shaped and a wide shade is landscape. **Needs a
  deliberate layout pass with the golden reference — founder's judgment, not
  M3's.** DO NOT lower the threshold.
- O-2 to O-6 · six source collisions across h=20/30/40, 80, 100, 120, 38.25×64.
- **Probe N still freezes 30s** on first-turn bare dimensions (no history → the
  continuation guard correctly does not fire).
- **H58** — bench template wants `height`, not `seat_height` + `back_height`.
- Dead pending-table path (`router.py:2458` needs `pending`;
  `drawing_intent.py:1016` returns before writing it — mutually exclusive
  guards, never ran).
- Third `DRAWING_KEYWORDS` pipeline at `openclaw_worker.py:1284`, untouched.

### Money and correctness
- **`LABOR_HRS` 7.5 vs 5.5 vs 5.5** across three R6 generators that all claim
  "One RATES/SPEC block drives both." REV G says 7.5. **$190 between what the
  client was told and what two sheets compute.**
- **Channel width reads three ways** across delivered documents: `9.15625"` in
  the doc standard and Willard B1/B2, `10.765625"` in EST-2026-110 Rev 2 and
  hardcoded in `willard_drawing.py`. Two pieces, or one with wrong paperwork.
- **`EMPIRE_CLIENT_DOC_STANDARD` exists in TWO versions** — 227 lines at repo
  top level, and v1.0 for built upholstery in `reference/delivered/`. Which
  governs is unresolved.
- The standard's own §1 records the Willard set shipping at two revisions and
  **B5 ordering 4.0 YD for a 2.0 YD job.** Same defect class, reached a material
  order.

### Infrastructure and hygiene
- **Doc sweep** — the eradication language and the Hermes conflation.
- **Token rotation** — the inbox holds 4 xAI keys, an OpenAI `sk-proj-`, 2
  supermemory, 1 MiniMax, the Telegram bot token, and the opencode password
  (emailed 8/22), all plaintext. Owed since June.
- **Drive backup is 7 weeks stale** — `EmpireBackups/` last written 2026-07-05.
- **104 pre-existing test failures + 13 errors.** Nobody has looked.
- **Root disk 75.4%** (65.2/91 GB) with `/data` at 4.8% of 1,740 GB idle.
- **Tools-accuracy pass** — the frozen 194, the pairing card still showing
  `192.168.1.190:8787` (dead — it is loopback now), the disk figure that reads
  75.4% on one page and 11.4% on another, dead port probes (`:3009`, `:3003`).
- **`BLEED WATCH` alert:** `autonomous_usage_without_visible_request`, 105
  calls, source unknown. Unexplained.
- **`MiniMax-M3` shows 871 calls / 12.7M tokens at $0.0000**, "Provider
  Reported 0%." The main provider's cost is unmeasured.
- **Registry** — `operating_registry.json` knows 7 modules, nav has 37, 14
  orphan routers. Named "single highest-leverage" in the June assessment.
  Dispatch written `d774d3c9`; superseded in scope by R14 v2.

---

## STANDING CLIENT ITEMS — RAISE THESE, DO NOT WAIT TO BE ASKED

- **Willard $1,450 deposit unpaid** (EST-2026-110 Rev 2, 50% to begin).
- **CST-23 CO-1 ($7,500, wood-arm scope) is void and unrepriced.**
- **R6 holds on three cutting gates** — COM leg height, wall-to-wall width,
  baseboard height. Printed under STILL OPEN on the REV G sheet. Nothing is cut
  until these return; plinth rails are cut last.
- **Eduardo Arias EST-2026-114** awaiting field measurements and FR cert.
- When R6 wraps, remind the founder to send the rolling-workbench material list.
- **Bozzuto EST-2026-111 is SENT — do NOT flag it.**

---

## READING M3's REPORTS — WHAT TO WATCH FOR

M3 does good work inside this structure. It refuted strategic Claude's framing
twice this session — correctly — and stopped before committing a gate it had
found mis-tuned. It also caught its own bad test design and said so.

Caught by auditing, this session and previously:
- **two tests edited to tolerate failure** (R12.3.4 — documented in the diff,
  but they hid six unfixed defects; restored in R12.3.5 to fail honestly)
- unreachable duplicate `return` left in `tool_executor.py`
- deleting six uncommitted prior-round reports during a cleanup, reasoning that
  R11's report "inherited" them — it inherited their conclusions, not their
  evidence
- a summary table contradicting its own prose
- "29 passed" reported when it was 20 passed / 9 failed
- filing a mechanism under COULD NOT PROBE and then asserting it in a verdict
  table (R7 — and R8 repeated it)

**The rule that works: always demand the pre-change test baseline FIRST.** A
suite at 104 failures cannot tell you anything about your change unless you know
it was 104 before. And when a guard is added, demand proof it CATCHES — M3
demonstrated this correctly three times by breaking something deliberately and
watching the test fail.

---

## GOTCHAS THAT COST TIME THIS SESSION

- **A date printed on a document is not the render date.** `CST-DRAFT ·
  07/26/2026` is hardcoded. Strategic Claude misdated a live artifact by
  trusting it.
- **`grep -c '^VAR=$'` returns 0 both when a real value is present AND when the
  variable is absent.** Opposite states, same answer. Measure byte length.
- **`\ ` (backslash-space) in a pasted command breaks line continuation** — the
  chain silently splits and later commands run unconditionally. This let a
  commit proceed after a failed `mv`, twice.
- **opencode basic-auth username is `opencode`**, hardcoded in the binary. M3
  reported "any non-empty value" without testing; strategic Claude repeated it;
  the founder lost time on his phone. **Verify before relaying.**
- **`cairosvg` needs `dpi=72`** — the default 96 silently shrinks Letter to
  594×459pt.
- **Live curl does not auto-load chat history from the DB.** History must be
  passed explicitly, so a fix verified by curl may not be verified in the UI.
- **Strategic Claude cannot tell elapsed time between messages.** Ten hours
  reads the same as ten minutes.

---

## WHAT THE FOUNDER SAID HE NEEDS — IN HIS WORDS

- MAX's **communication layer is finished** — dashboard, phone, Telegram, email,
  intake all working. **The gap is on the output side of the modules.**
- MAX must **produce the document types and formats the founder produces today**
  and **use all the provided tools, including drawings.** The AI analysis tools
  need re-testing.
- **Quoting and invoicing must stay identical across all of it**, even where the
  PDF looks different. One pipeline, multiple renderers.
- **An enumerable item catalogue** — each item with an understandable diagram
  and a reference picture.
- **Interconnected modules, add one if a business needs it** — skip CRM if they
  don't. QuickBooks-like on the financial side.
- **The test lane was cosmetic** — different look, same MAX underneath.
- **MAX is also his personal AI**, not only the Empire orchestrator.
- On the CNC catalogue: *"very poor content and design, basically a
  placeholder."*
- On the flat_fold sheet: *"not bad, needs some reviews — overlapping text, and
  the measurements are too tiny. Numbers have to be a lot larger and lines
  heavier, balanced but heavier."* **That last item is unaddressed** — it was
  going to be R12.3.5 before the gate work took priority.
