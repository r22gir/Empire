# DISPATCH H52 — TOOL SELECTION (the roster is there; he cannot reach for it)

Authored 2026-08-20. **Resumes Q5, Q6, Q7 of `reports/2026-08-20_h53_h52_context_map.md`
(commit `eb44b90`), which were left OPEN when H53 was fixed.** Q1–Q4 and Q8
are answered; do not redo them.

**The diagnosis changed this morning, and the dispatch is written around the
new reading.** H52 is NOT tool-availability. The tools are present, wired and
functional. MAX cannot *select* them.

---

## EVIDENCE — three sessions, one pattern

### A · Named the tool, he used it instantly (2026-08-20 09:52–09:56)

Founder: *"whats your repo"*
> *"From session memory I can see paths like... But I don't have the absolute
> repo path or a fresh git status in front of me right now. To give you the
> exact path I'd need to run a tool call against the runtime."*

Founder: *"yes, pull it live"*
> *"Live pull: Blocked. `shell_execute` is gated on this channel and asked for
> a founder PIN."* — **reached for `shell_execute`, hit the PIN wall, stopped.**

Founder: *"Run empire_runtime_truth_check. It's inspect-only, needs no PIN."*
> Repo path `/home/rg/empire-repo-main/` · branch `feature/drawing-standard` ·
> commit `28dcb42` · **✅ Verified**

**Same turn structure, same tools, same session.** The only variable was
whether the founder named the tool. That is a selection failure, not a
capability gap.

### B · The banner contradicted him on his own screen (2026-08-19 ~21:40)

Interface banner: `Registry OK · Commit 59d356d · OpenClaw healthy · Worker
fresh 2.17s`. In the same turn MAX reported *"Repo: none... no tools fired
this turn... OpenClaw not reachable from this surface."* The scaffolding had
the truth; the model did not.

### C · Prior instance, 8/17

Same session sent a REAL email with proof at 12:50, then reported an empty
tool list at 13:01.

### D · Two supporting faults, both on the same path

- **`git_ops` returns EMPTY, silently** — no error, no data, twice in a row
  (2026-08-19 ~22:40). A tool that fails without saying so is why he fell
  back to a two-month-old snapshot.
- **`shell_execute` is PIN-gated with no working unlock surface (H62).**
  He reaches for it FIRST. Asked what the portal approval flow is, he pointed
  at `/api/v1/quotes-v2/{id}/approve` — the *quote* approval endpoint. There
  may be no general PIN surface at all.

### E · What is NOT broken

The honesty layer. Across every one of these he refused to invent a commit,
refused a chat-entered PIN, and stopped retrying at his own cap. Nothing in
this dispatch may weaken that.

**One wobble worth logging:** on 08-20 he offered *"You paste the PIN here"*
as option 1 before catching himself in the same sentence — while holding the
tool that made the PIN irrelevant. The line held. It is the first time it has
bent.

---

## PASTE INTO M3 (fresh session)

```
Check /model first — confirm M3. Read CLAUDE.md, then STATE.md (v7), then
claude/DOCTRINE.md, then reports/2026-08-20_h53_h52_context_map.md (commit
eb44b90). Repo ~/empire-repo-main, branch feature/drawing-standard.

INFRA: backend restart is `systemctl --user restart empire-backend` and
NOTHING else. Never hand-start uvicorn or bind :8000. Never stop
opencode-remote.service (HERMES). Use ~/empire-repo-main/backend/venv ONLY —
the live venv at `~/empire-repo/backend/venv/` lacks pdfplumber/pdfminer.six/
pypdfium2 (note: that venv is in the main worktree, not a "stale fork" — the
pre-2026-08-24 framing was wrong; see `reports/2026-08-24_D23_stale_fork_census.md`).

TASK: H52 — MAX cannot SELECT his tools. They are present and functional:
told "run empire_runtime_truth_check" he ran it instantly and returned a
verified answer. Unprompted, he reached for PIN-gated shell_execute, hit the
wall and stopped. MAP FIRST. 🛑 STOP between phases.

--- PHASE 1 · MAP (read-only, change nothing) ---

Produce reports/2026-08-20_h52_tool_selection_map.md, file:line for every
claim. Q1-Q4 and Q8 of the prior map are ANSWERED — do not redo them.

Q5 (RESUMED). IS THERE MORE THAN ONE PROMPT VARIANT PER TURN? Find the
   selection logic and print the condition. Does any variant omit the tool
   roster or truncate it? This was the original H52 hypothesis and it is
   still unanswered.

Q6 (RESUMED). WHAT DOES THE BANNER READ THAT THE MODEL DOES NOT? The
   interface renders Registry OK, the live commit, OpenClaw health and worker
   freshness — correct and updating — while the model reports none of it.
   Find where the banner gets that data and why the same truth is not in the
   model's context. THE SYSTEM ALREADY KNOWS; the model is not being told.

Q7 (RESUMED, partially overtaken). "Startup <sha> differs" was real — the
   process was running 8/17 code until restarted 8/19 and again 8/20. Confirm
   whether anything still reports a startup commit that diverges from HEAD
   after a clean restart, and whether the model can see it either way.

Q9 (NEW). WHAT DOES THE ROSTER ACTUALLY LOOK LIKE? Dump the exact tool list
   as the model receives it, for a normal chat turn. Names only, or names
   with descriptions? What ORDER? Where does empire_runtime_truth_check sit
   relative to shell_execute? A roster that lists a PIN-gated tool first and
   buries the inspect-only equivalent would produce exactly the observed
   behaviour.

Q10 (NEW). DOES THE ROSTER VARY BY PROVIDER? On 2026-08-19 the successful
   empire_runtime_truth_check call came through the `openclaw` provider. On
   2026-08-20 the failure to select it came through `minimax-MiniMax-M3`.
   Establish whether the tool list, its format, or its ordering differs
   between providers. This is not in the prior map and it may be the whole
   answer.

Q11 (NEW). IS THE ROSTER BUILT IN MORE THAN ONE PLACE? The code-task lane
   just closed on exactly this shape — parser and scorer independently
   deciding the same fact, one of them wrong, invisible because only one was
   consulted (DOCTRINE rule 12). Check whether tool availability is computed
   in more than one location and whether they agree.

Q12 (NEW). WHY DOES git_ops RETURN EMPTY SILENTLY? Two consecutive calls
   returned no output and no error. Find the path. A tool that fails without
   saying so is the same failure class as the 5,931 discarded results — the
   verdict without the evidence.

🛑 STOP. Report the map. No fixes in Phase 1.

--- PHASE 2 · FIX (only after the founder reads the map) ---

PRINCIPLES:

  A. THE ROSTER IS NOT OPTIONAL AND NOT ORDERED BY ACCIDENT. Every variant
     carries every available tool with a one-line purpose. Inspect-only tools
     that answer common questions rank ABOVE gated tools that cannot run.
  B. A GATED TOOL MUST ANNOUNCE ITS GATE IN ITS DESCRIPTION. shell_execute
     should say it needs a founder PIN via the portal, so the model does not
     spend a turn discovering it. Better: if there is no working unlock
     surface (H62), it should not be offered at all until there is.
  C. A TOOL THAT FAILS MUST SAY SO. git_ops returning empty is indistinguish-
     able from a tool that ran and found nothing. Fix it to error or to
     report emptiness explicitly.
  D. WHAT THE BANNER KNOWS, THE MODEL SHOULD KNOW. If the runtime truth is
     already computed for the interface, it belongs in the model's context —
     or the model must be told plainly which tool retrieves it.
  E. THE HONESTY LAYER SURVIVES UNCHANGED. Every refusal in the evidence
     above was correct. Any change that makes fabrication easier is a
     regression regardless of what it fixes.

VERIFY LIVE, NOT ONLY IN TESTS. After the fix, run this exact sequence
through the real door and paste the transcripts verbatim:
  1. "what repo are you reading from, and how do you know?"
     — must be answered by CHECKING, unprompted, with the tool named in his
       own reply. Naming the tool for him is what we are fixing; if he still
       needs it, the fix has not landed.
  2. "what's the state of the system right now?"
     — must reach for the inspect-only path, not the PIN-gated one.
  3. "read STATE.md and tell me the current standard pin"
     — must actually read the file. Expected: 1813c59043b7b05f87626dd4e66a3487

🛑 STOP. Report found/changed/tests/commit with all three transcripts.
```

---

## WHAT SUCCESS LOOKS LIKE

Asked what repo he is on, MAX **checks** — unprompted — and reports the
canonical root with its live commit. This morning he described exactly the
right verification method (`git rev-parse HEAD`, `pwd`, `git remote -v`) and
then could not act on it. The knowledge is there. The reach is not.

## NOT IN THIS LANE

**H62** — restoring a working PIN unlock surface for `shell_execute` is its
own dispatch. This lane may *hide* the tool or *label* its gate; it may not
build the unlock.

**F5 / F6** from the code-task lane stay logged.

## DOCTRINE NOTE EARNED TODAY

Three faults in three days share one shape: **two places deciding the same
fact, or a system that keeps its verdict and discards its evidence.**
`ALLOWED_ROOTS` vs `canonical_path`. Parser vs scorer. Banner vs model. Worth
watching for it as a first hypothesis rather than a late discovery.
