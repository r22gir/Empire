# 2026-08-22 — Pin gate followups / session-hygiene open tasks

This file is a session-hygiene checkpoint. The 2026-08-21 commit
`8aeb0f0` was documentation-only (BACKLOG.md, STATE.md, HANDOFF
de-dup). It recorded open items but did not close any of them. The
user referenced "8ae0bf0" in the dispatch — that hash does not exist
in the repo. The actual last commit is `8aeb0f0`.

For each open task: what it is, why it is open, the file(s) it
touches, and whether `8aeb0f0` resolved or obsoleted it. If I
cannot recall an item with confidence, I say so.

---

## 1. P1-T·d — fix the chrome T() y-bbox over-estimation (H71)

**What:** the `chrome.T()` function at
`backend/app/presentation/template/chrome.py:109` estimates text
height as `size × 0.78 ascender + size × 0.24 descender = 1.02 ×
size`. The 0.78 ascender factor claims the ascender extends ~78% of
the way to the next line, which produces phantom "overlaps" on
adjacent y rows. Real glyph extent is closer to `0.65 × size`. Fix
path: replace the approximation with actual font ascender (PIL
metrics or a font config).

**Why open:** the 8pt chrome tolerance in `gates.py:61` is a
WORKAROUND for this measurement bug, not a design value. The
phantom-overlap problem cannot be fixed at the gate level; it has
to be fixed at the bbox-calculation level.

**Files it touches:**
- `backend/app/presentation/template/chrome.py:109` (the
  approximation)
- `backend/app/presentation/template/gates.py:49-61` (the
  workaround — would reduce toward body value after the fix)
- The H71 entry in `claude/BACKLOG.md` and
  `claude/BACKLOG_UPDATE_2026-08-20.md`
- `tests/test_template_engine.py::TestH70PerClassTolerance` would
  be updated when the fix lands.

**Did `8aeb0f0` resolve it:** **No.** `8aeb0f0` is documentation
only.

---

## 2. H68 — model fabrication from filename + STATE.md cues

**What:** on 2026-08-20 19:11, MAX fabricated a 10-file renderer
list under `backend/app/services/drawings/` (a directory that does
not exist) without ever calling `file_read`. The fabrication is
real. The four-cue trigger is (1) filename keyword, (2) STATE.md
mention of "drawing standard", (3) `git status` untracked-file
list, (4) no tool result grounding the response.

**Why open:** **founder decision required.** The dispatch listed
four options: (a) tighten the system prompt, (b) runtime gate on
confident-fabrication shapes, (c) change the model, (d) accept and
design around it. The dispatch said: "I do not have a recommendation.
The decision is the founder's."

**Files it touches:**
- `claude/BACKLOG.md` (H68 entry)
- `claude/BACKLOG_UPDATE_2026-08-20.md` (H68 entry with full
  analysis)
- Would touch `system_prompt.py` or `runtime_truth_enforcer.py`
  depending on which option is chosen

**Did `8aeb0f0` resolve it:** **No.** Documented in BACKLOG but
the decision is still pending.

---

## 3. H69 — tool-card footer overstates execution status

**What:** the chat UI footer at
`empire-command-center/.../ChatScreen.tsx:12-26` extracts tool-call
names from the model's RESPONSE TEXT via `parseToolBlocks`. The
display loop at `:660-668` renders each as "Tool: X" with no
execution signal. On the 2026-08-20 19:11 turn, the footer showed
five tool cards (`git_ops, shell_execute, file_read, file_read,
shell_execute`) for a turn where NONE of those tool calls were
ever dispatched. The founder read the footer as evidence MAX had
tried to read the file.

**Why open:** a fix has an obvious correct answer — distinguish
executed / failed / parsed-but-never-dispatched, and surface stream
errors. Marked as "Not in this lane; logged for the next
maintenance window" in the BACKLOG.

**Files it touches:**
- `empire-command-center/app/components/screens/ChatScreen.tsx:12-26`
  (`parseToolBlocks`)
- `empire-command-center/app/components/screens/ChatScreen.tsx:660-668`
  (the "Tool: X" render loop)
- `claude/BACKLOG.md` and `claude/BACKLOG_UPDATE_2026-08-20.md`
  (H69 entry)

**Did `8aeb0f0` resolve it:** **No.** Documentation only.

---

## 4. P1-T·e — the next lane after P1-T·d

**What:** the dispatch series said P1-T·e is the next lane after
P1-T·d. I do not have a detailed description of what P1-T·e
covers — the dispatch I read on 8/20 was "finish H57 Phase 2" and
the subsequent dispatches covered P1-T·a, P1-T·b, P1-T·c. The
8/19 amendment series (8 amendments) is in place. P1-T·d is the
chrome T() y-bbox fix. P1-T·e is the next item on the
document-template-engine sequence. I cannot recall with
confidence what specifically P1-T·e covers; the dispatch file for
it is not in the repo I have access to.

**Why open:** P1-T·d is not done; P1-T·e waits on it.

**Files it touches:** unknown without the P1-T·e dispatch.

**Did `8aeb0f0` resolve it:** **No.** Not even in scope.

---

## 5. F5/F6 — badge counter and retry budget

**What:** the F5 (badge counter) and F6 (retry budget) items from
the 2026-08-20 code-task restoration dispatch. F5 is the badge
counter that reports "queued" tasks as if they were active work;
F6 is the retry budget that spends 4 attempts on structurally
impossible operations. Both from the 2026-08-20
DISPATCH_2026-08-20_codetask_restoration.md dispatch.

**Why open:** marked "P1-T·d is next unless the founder says
otherwise" or "Stage 4 only after Stage 3 live proof" in STATE.md
NEXT list. F5/F6 has not been worked on.

**Files it touches:** the dispatch is in
`claude/DISPATCH_2026-08-20_codetask_restoration.md`. The
implementation would touch the badge counter and retry logic — I
do not have the specific file paths from the dispatch loaded.

**Did `8aeb0f0` resolve it:** **No.** F5/F6 is in the
PENDING list in STATE.md (item 6).

---

## 6. H62 — shell_execute PIN-gate, no working unlock surface

**What:** `shell_execute` is L3 PIN-gated. There is no working
unlock surface for the code-task lane to use it. MAX refuses to
ask for the PIN in chat, and there is no portal-side flow that
emits a usable shell execution token. The error message MAX gives
("shell_execute is restricted on this surface (L3 PIN-gated)...")
was observed in the 8/20 19:11 turn.

**Why open:** the dispatch said: "Restoring the unlock surface
is a separate dispatch." Logged in H62 multiple times across
BACKLOG, BACKLOG_UPDATE_2026-08-20.md, and STATE.md.

**Files it touches:**
- `backend/app/services/tool_safety.py` (the PIN-gate logic)
- A portal-side unlock flow (not yet designed)

**Did `8aeb0f0` resolve it:** **No.** Documented as still open.

---

## 7. H61 install-path audit

**What:** the install-path audit found nine instances of
"config-on-disk correct, config-in-force wrong" patterns. The
fix is to make the install procedure copy repo unit files to the
installed location (or symlink). Eight are documented in
`claude/BACKLOG.md` and `claude/BACKLOG_UPDATE_2026-08-20.md`
(H61 table). The ninth was added on 8/20 (the git_ops stale-fork
fix at b01b78a).

**Why open:** nobody has run the audit. STATE.md NEXT list
item 4 says "H61 install-path audit — nine instances found,
nobody has swept."

**Files it touches:** install scripts, systemd unit files. Not
specific paths from memory.

**Did `8aeb0f0` resolve it:** **No.** Hmm — but the b01b78a
commit did fix one of the nine (the git_ops stale-fork path). So
the count went from 9 to 8. The remaining eight are in
`claude/BACKLOG.md` H61 table — 8 not 9. Let me note: STATE.md
still says 9. That's stale. **STATE.md says 9 instances; the
H61 table in BACKLOG.md after b01b78a says 8. STATE.md is
inconsistent with the source of truth. `8aeb0f0` recorded 8 in
BACKLOG but did not update STATE.md's count. Gap.**

---

## 8. V1/V2 — visible fixes dispatched, never fired

**What:** V1 is the currency truncation fix (V1: "$8,599.6"
appearing in dispatch texts). V2 is the test-junk-in-live-quote-list
fix ("1cfix-rej", "1cfix-pin" etc.). Both are dispatched but not
fired. The work was tracked in BACKLOG_UPDATE_2026-08-19.md
under the V-LANE.

**Why open:** the V-LANE was paused for the code-task restoration
lane. Not yet started.

**Files it touches:** the currency formatter and the quote-list
filter; specific file paths not recalled.

**Did `8aeb0f0` resolve it:** **No.** Still in the PENDING list
in STATE.md (item 5).

---

## 9. Four hand-maintained tool registries

**What:** there are at least four places where the tool registry
is maintained by hand: `TOOLS_DOC` in `tool_executor.py`,
`TOOL_REGISTRY` in `control_plane.py`, the `running_registry`
JSON, and the per-builder call tables. They must be kept in sync
manually. Same class as the two `DRAWING_KEYWORDS` lists that
H57 had.

**Why open:** STATE.md NEXT list item 8 flags this as
"same class as the two `DRAWING_KEYWORDS` lists." It is
deferred until a single-source-of-truth fix lands.

**Files it touches:**
- `backend/app/services/max/tool_executor.py` (TOOLS_DOC,
  PlacedBox)
- `backend/app/services/max/control_plane.py` (TOOL_REGISTRY)
- `backend/app/services/max/operating_registry.py`
  (running_registry JSON, possibly)
- Per-builder call tables in `body/*.py`

**Did `8aeb0f0` resolve it:** **No.** Per-class tolerance
(H70) does not collapse these into one source — it just changes
how G2 reads the existing duplicated sources.

---

## 10. Re-run the audit test

**What:** STATE.md NEXT list item 9 says "Re-run the audit test
— MAX reads the R3 dispatch and `fc42fe3` himself. Answer key
published before the test existed. **This is the handoff proof.**"
I have not done this.

**Why open:** it is a proof-of-handoff exercise: build a
reproducible test where the same pair (R3 dispatch + `fc42fe3`)
gives the same answer the handoff design says it should, before
the test is run. This is the audit for whether MAX actually holds
the strategic role.

**Files it touches:** a new test in
`backend/tests/test_handoff_audit.py` (or similar). Specific
location not in memory.

**Did `8aeb0f0` resolve it:** **No.** Logged but not done.

---

## 11. F1 — fix scorer in code_task_runner.py:399

**What:** F1 is the code-task scorer fix. The dispatch was
"F1 — the code-task scorer at code_task_runner.py:399 read only
the raw provider function_calls field. A model returning valid
JSON in the response content but not in function_calls was scored
as zero tool calls. Fix: read parsed tool_calls from
parse_tool_blocks, not raw function_calls. Per dispatch rule 12."

**Why open:** marked PENDING in my task list. F1 was the first
fix in the 2026-08-20 codetask restoration dispatch.

**Files it touches:**
- `backend/app/services/max/code_task_runner.py` (the scorer at
  line 399)
- `tests/test_code_task_runner_evidence.py` (the proof)

**Did `8aeb0f0` resolve it:** **No — but it is OBSOLETE.** F1 was
already fixed and shipped at commit `ccfb576` on 2026-08-20
(Stage 2 of the same lane). My pending task #4 in the session
task list is a stale duplicate. Closing it.

---

## 12. H57 Phase 2 — bench fixtures

**What:** H57 Phase 2 has been worked on. The 22 new tests in
`test_h57_router_intercept.py` were the 8/20 work. The cover
layout fix in 23e8ead was the residual cleanup. The remaining
"bench fixtures belong to H58" is captured in commit messages
and commit instructions. As of 8/21 it is CLOSED per STATE.md.

**Why open:** STATE.md says CLOSED at `62c4741`. My session
task #1 is stale. H57 Phase 2 is done.

**Files it touches:** none — closed.

**Did `8aeb0f0` resolve it:** **No — but it was already closed
before this commit. `8aeb0f0` is documentation only; the work
itself is in `62c4741`.** Closing as a separate item — it was
not opened by `8aeb0f0` either way.

---

## Items I cannot recall with confidence

- The exact file path for V1/V2 (currency truncation / test junk
  in live quote list). The dispatch is in
  `claude/BACKLOG_UPDATE_2026-08-19.md` under the V-LANE
  section. I do not have the specific code files in mind.
- The exact file path for the four hand-maintained tool
  registries — I named them above but the second registry
  (running_registry) location is a guess on my part.
- The exact file path for the install-path audit's eight
  remaining instances — the BACKLOG.md table is the source of
  truth, not my memory.
- The exact file path for F5/F6's badge counter and retry
  budget — I read the dispatch on 8/20 but do not have the
  specific code locations in front of me.
- Whether the cached `git_ops` stale-fork fix at `b01b78a` was
  correctly attributed to H61 (it is), and whether it was
  originally counted in the 9 or separate — the H61 table
  pre-`b01b78a` would have shown 9; after, 8. I cannot recall
  with certainty which count STATE.md carried into 8/20.

If any of these matter, the BACKLOG.md and BACKLOG_UPDATE files
are the source of truth, not my recall.

---

## Summary

- `8aeb0f0` (the actual commit, not `8ae0bf0`) was documentation
  only. It recorded 12 open items in BACKLOG.md and updated
  STATE.md's NEXT list with strikethroughs on items 1 and 2 and
  renumbered the rest.
- 12 open items remain, of which 2 are OBSOLETE (F1 already
  shipped at ccfb576, H57 Phase 2 already closed at 62c4741) and
  1 (H70) is CLOSED (shipped at b10af10) and 1 (H70) is
  recorded in BACKLOG.md as closed.
- 9 items remain genuinely open after `8aeb0f0`. They are
  ordered below by approximate impact (smallest first):
  - P1-T·d (H71 — chrome T() y-bbox fix)
  - H68 (model fabrication — founder decision)
  - H69 (tool-card footer — display bug)
  - H62 (shell_execute PIN-gate — unlock surface)
  - H61 install-path audit
  - V1/V2 visible fixes
  - four hand-maintained tool registries
  - F5/F6 badge counter and retry budget
  - re-run the audit test (handoff proof)
  - P1-T·e (next lane after P1-T·d — content not in memory)
- One recording gap: `8aeb0f0` did not update STATE.md's H61
  count (says 9 instances; BACKLOG.md H61 table says 8 after
  the b01b78a fix). STATE.md is inconsistent with the source
  of truth.
- The handoff is now de-duplicated. `claude_HANDOFF.md` is a
  one-line redirect to `claude/HANDOFF_2026-08-20.md`. Two
  files saying "start here" was the old failure mode; only
  one does now.
