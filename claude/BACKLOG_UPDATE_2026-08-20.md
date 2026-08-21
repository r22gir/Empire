# BACKLOG UPDATE — 2026-08-20

**Apply this to `claude/BACKLOG.md`.** Issued as a delta so nothing
already in the register is silently lost. This file was created when
the code-task restoration work surfaced two new structural findings.

Author: M3 (acting on founder directive). Committed alongside
`e854621` (Stage 1 — F2/F3/F4) and the imminent Stage 2 commit
(F1 scorer).

---

## NEW ITEMS

### **H61** · "config on disk correct, config in force wrong" — **SEVENTH instance**

The live unit at `~/.config/systemd/user/empire-backend.service` was
missing the `StandardError=journal` line. The repo unit file at
`systemd/empire-backend.service` has it correctly. Installed unit did
not — so all `logger.error` output landed on stderr that systemd
inherited (default for missing `StandardError=`), and journalctl saw
nothing for nine `logger.error` sites during a confirmed failure
window 2026-08-20 02:38–02:42.

This is the **SEVENTH instance** of the same pattern: the canonical
config in the repo says one thing, the running config says another.
Fix lives both places now — repo unit unchanged (already correct),
installed unit patched and daemon-reloaded.

| # | Where on disk | Where it runs | Fix |
|---|---|---|---|
| 1 | H57 (Phase 3 doc) — stale-fork reachable | runtime after `59d356d` | runtime tightened |
| 2 | `tool_safety.ALLOWED_ROOTS` had `~/empire-repo` | tool safety actually enforced | runtime fix |
| 3 | `validate_path` | exec time | now delegates canonical |
| 4 | `quotes.py` uploads_dir / generated_path | request time | now resolves canonical |
| 5 | `openclaw_worker.py drawings_dir` | worker loop | now resolves canonical |
| 6 | env vars from drop-in vs hardcoded defaults | MAX provider selection | env wins; re-audit owed |
| **7** | **`systemd/empire-backend.service` has `StandardError=journal`** | **`~/.config/systemd/user/empire-backend.service` had no `StandardError=` line → stderr inherited → unjournaled** | **installed unit patched 2026-08-20; daemon-reload + restart confirmed** |
| **8** | **`tool_executor.py:_git_ops` should resolve canonical root** | **H57 Phase 3 fix routed most paths through `resolve_canonical_root()`, but `_git_ops` was missed — `repo = os.path.expanduser("~/empire-repo")` (stale fork).** | **`tool_executor.py:_git_ops` rewritten to use the canonical resolver 2026-08-20; also added `empty` / `truncated` markers on success-with-empty-output per dispatch principle C.** |
| **9** | **`system_prompt.py` identity section said `Code: ~/empire-repo/`** | **H57 Phase 3 made runtime paths canonical-root-aware, but the prompt BODY hardcoded the stale fork as MAX's identity.** | **`system_prompt.py:get_system_prompt()` now substitutes `Code: {canonical_repo_root}` where `canonical_repo_root` comes from `resolve_canonical_root()`.** |

Doctrine rule 5 ("One source per fact") extends to: the SOURCE-OF-RECORD
must be the source-of-force. A repo unit file that no reinstall ever
reads is not a unit file. **Action owed on the install path:** ensure
the install / refresh procedure copies the repo unit file over the
installed one, or symlinks. This is logged here so the regression
class is visible.

**H61 hygiene note (2026-08-20, post-Stage-2):** Same interpreter
(`/usr/bin/python3`), two venvs. The stale fork at
`~/empire-repo/backend/venv` lacks pdfplumber / pdfminer.six /
pypdfium2 entirely and has older pillow / primp. Stage 1 + Stage 2
verification ran via `/home/rg/empire-repo/backend/venv/bin/python3`
against `~/empire-repo-main` sources — the interpreter is the same but
the site-packages set is not. F1 fixtures are pure logic, so the
mismatch did not change the result; confirmed by re-running under
`~/empire-repo-main/backend/venv/bin/python3` — 5/5 still pass. **From
Stage 3 onward, the canonical venv is the only one used for testing.**
Not a new H61 instance — same interpreter, same config class
(repo-or-installed drift), just at a different layer.

**H61 historical correction (2026-08-20, post-H52-Phase-2):** On
2026-08-19, MAX proposed reading from `~/empire-repo/` and, asked
where the belief came from, honestly said he did not know. THIS
STRING IS WHERE IT CAME FROM — `system_prompt.py:428`
hardcoded `Code: ~/empire-repo/ | 18 desks | 39 tools | 22 products |
536 commits | $50/mo AI budget.` in MAX's identity section. **He was
reporting what he was told. The diagnosis that he was confabulating
was wrong.** He inferred the belief from a system prompt that was
itself wrong (H57 Phase 3 missed the prompt body). The fix at instance
9 brings the prompt body into alignment with the runtime.

### **H62** · `shell_execute` PIN-gate has no working unlock surface — code tasks cannot run shell on this lane

Found via task 7378 during Stage 1 live verification. The model
returned prose saying "shell_execute is restricted on this surface
(L3 PIN-gated). All 3 attempts were blocked before execution" and
declined to ask for the PIN in chat (correct behaviour per DOCTRINE
rule 31 — "PIN approval never travels through chat or email"). But:

* The portal approval flow that is supposed to unlock the call either
  does not exist or is not reachable from the code-task surface.
* The model did not try `file_*`, `git_ops`, or `service_manager`
  afterwards. Three attempts, all `shell_execute`, all blocked.
* Net effect: any code task that needs a shell command cannot run.
  `test_runner` is in the allowed tool set but is itself implemented
  via `shell_execute` for the non-`pytest` cases — same wall.

If F1 (scorer fix) lands but tasks still route through `shell_execute`,
this is what they will hit. The 7,372-queued badge reading as "active
work" was a symptom; this is the structural cause. **This finding
must NOT be buried under the F1 win** — without a working unlock
surface, code-task restoration is partial.

**Action owed:** either
(a) implement the portal-side unlock so a code task can call
    `shell_execute` after founder approval (one PIN modal, scoped to
    the running task), or
(b) restrict the code-task tool set to `file_read/write/edit/append`
    + `git_ops` only, and document why `test_runner` and `shell_execute`
    are unreachable. Either fix restores real capability.

Logged as separate item (not folded into F1) because the doctrine is
"one finding, one root cause" and the cause here is different.

### F1 (scorer) — committed, fixture tests are the source of truth

`code_task_runner.py:399` set
`task.supports_tool_calls = bool(response.function_calls) if
response.function_calls is not None else supports_native_tools`.
The parser (`parse_tool_blocks` at `tool_executor.py:175`) honoured
three advertised formats — native call, raw JSON `{tool:...}`, fenced
JSON. A model answering in JSON had `response.function_calls is None`
and was scored as having emitted nothing. After F2 lands evidence, the
scorer now reads the parsed result. One source of truth.

The pre-fix behaviour was reproducible in fixture form before the
fix landed. **Negative fixtures failed for the right reason:**
`test_raw_json_with_no_native_call_is_scored_as_tool_call` and
`test_fenced_json_with_no_native_call_is_scored_as_tool_call` both
asserted `task.supports_tool_calls is True` after a model that
emitted valid JSON, and FAILED on the pre-fix code with
`task.supports_tool_calls is False` — exactly the F1 condition. After
the fix, both pass.

Prose-with-no-action and malformed-JSON fixtures continue to assert
`task.supports_tool_calls is False`, and continue to pass on both
pre- and post-fix code (the prose fixture failed previously for the
right reason: model returned no actionable JSON; the malformed-JSON
fixture also persists the raw text into `task.result` per F2 so the
negative result is debuggable).

### F5 / F6 — deferred to Stage 4, only after Stage 3 live proof

Pending. F5 = badge counts every-row-ever, not actual pending.
F6 = retries spend budget on structurally impossible operations. Both
deferred per dispatch order.

---

## OPEN QUESTION (was on 8/19 list, still open)

> 8. What is OpenClaw actually doing? A 7,363-item queue with no
>    owner, and `openclaw_worker.py` commits and PUSHES to git.
>    Nobody has looked.

The 7378 task above is the first time this dispatch actually looked
at what OpenClaw does when handed a code task. The answer: it routes
to `code_task_runner`, which after Stage 1 is observable again.
Before Stage 1 the queue was a verdict-with-no-evidence mill. After
Stage 1 it is an evidence-bearing, journalctl-visible pipeline that
still fails most tasks because of H62 and F1. The question is now
reframed: **after F1, what fraction of the 7,363 rows can a single
end-to-end task clear, and which fail modes own the rest?**

---

## RECOMMENDED ORDER (post-restoration)

1. **F1** scorer fix + fixture tests (Stage 2, next).
2. **Stage 3** live proof — submit one real task end-to-end through the
   actual path; verify file changes on disk; verify journalctl lines.
3. **F5 / F6** counters + retry budget (Stage 4).
4. **H62** unlock surface for `shell_execute` (or scope the tool set).
   Without this, "code-task restoration" is partial and the queue will
   re-fill with PIN-blocked rows.
5. **Install-path audit** — close out the 7th "config on disk vs in
   force" instance by making the install procedure copy the repo unit
   file to the installed location.

---

## DOCTRINE ADDITIONS EARNED

- **The source-of-record must be the source-of-force.** A repo unit
  file that no reinstall ever reads is not a unit file. (Adds to
  doctrine rule 5.)
- **A failure path that discards the evidence guarantees the failure
  survives.** (Already captured in 8/19 doctrine; repeated here for
  the record.)
- **A logging call that silently does nothing is worse than none.**
  (F4 doctrine, already captured 8/19; repeated for the record.)
- **Two places deciding the same fact is the bug.** (Already captured
  8/19.)
- **One finding, one root cause — log separately, do not fold.** H62
  could have been written as "F1.5" or "PIN-gate issue in code tasks"
  but the cause is independent (no unlock surface) and folding it
  would lose the action owed.

---

## CLOSED — 2026-08-20 16:18 EDT

### Code execution RESTORED.

**Dead 2026-05-06 → restored 2026-08-20.** 106 days.

**Single root cause:** the scorer and the parser disagreed about
"did the model emit an executable action." `_request_code_response`
at `code_task_runner.py:423` (was line 399 at dispatch time) scored
`task.supports_tool_calls = bool(response.function_calls) if
response.function_calls is not None else supports_native_tools`. The
parser (`parse_tool_blocks` at `tool_executor.py:175`) honoured three
advertised formats — native call, raw JSON `{tool:...}`, fenced JSON
block. A model replying in formats 2 or 3 has
`response.function_calls == None` but a non-empty `tool_calls` list
from the parser. The buggy scorer recorded `False` and the dispatch's
evidence-bearing six failure branches discarded the response. Two
places decided the same fact; one was wrong; the disagreement was
invisible because only one of them was consulted. Doctrine rule 12.

**The open question is now ANSWERED.** From
`BACKLOG_UPDATE_2026-08-19.md` "OPEN QUESTIONS" item 1:
> 1. **What broke MAX's coding?** (blocks the restoration lane)

**Answer:** neither a removed capability nor a deliberate gate.
The Codex-Mode line was never deleted and was never disabled by
policy — the GPT-5.5 rewrite (H52–H55 sweep) preserved it. It was
broken by a single-source-of-truth violation in code_task_runner.py
that surfaced as "without actual file changes" verdicts with
`result=None` for 5,931 rows over a four-day burst in May. Three
months to diagnose because every failure branch discarded the
evidence (F2 fix), the nine `logger.error` calls landed on stderr
that was inherited-not-journaled (F3 fix + H61 — SEVENTH instance of
"config on disk correct, config in force wrong"), and the failure
pattern looked provider-shaped when the parser was the silent third
party. **The capability was always live. The verdict was always
wrong.**

**Proof on disk:** `reports/2026-08-20_stage3_liveproof.md`. Two
real code tasks submitted through the actual API path. Task 7380
appended `STAGE3-PROOF-CLEAN\n` to a canonical-repo scratch file —
md5 mutated, exact-match content, file actually changed. Task 7379
attempted the dispatch's `/tmp` example and was refused by H57
Phase 3's canonical-root guard — proving that gate works as
designed (a second proof, not a failure).

**Commits in order:**
| SHA | Stage | Subject |
|---|---|---|
| `e854621` | 1 | F2 evidence + F3 logging + F4 no-op basicConfig |
| `91b3ca0` | pre-2 | patch installed unit StandardError=journal + log H61/H62 |
| `ccfb576` | 2 | F1 scorer reads parsed result, not raw provider field |
| `a663e43` | 3 | live proof — F1 end-to-end, /tmp blocked by H57 guard |

### F5 + F6 — NOT STARTED. Stay logged.

Per founder directive: "CLOSING THIS LANE HERE. Do NOT start Stage 4.
F5 (badge counter) and F6 (retry budget) stay logged as open items."

* **F5** — "7,372 queued" badge counts every row ever written. Actual
  pending: zero. Source TBD. Filter, never delete.
* **F6** — Retry budget spends 4 attempts on a structurally impossible
  operation. Doctrine rule 26, applied to the machine rather than the
  agent. Stop retries when the failure is deterministic; same failure
  reason twice is not worth a third attempt.

### H62 — NOT CLOSED. Action still owed.

PIN-gate on `shell_execute` has no working unlock surface. The
capability that code-task restoration opens back up is partially
blocked again from the other side. **Per the founder: this is a
RESULT, not a failure of the fix; report it and do not work around
the PIN gate.** Restoring the unlock surface is a separate
dispatch.

### **H64** · H53 harmonisation — pre-search guard (CLOSED 2026-08-20, sixth interception layer)

The pre-search guard at `router.py:2519-2557` (non-streaming) and
`:3356-3380` (streaming) emitted a `[SYSTEM: ...]` block on `role="user"`
before the model's first turn. Structurally identical to the H53 replay
block that `28dcb42` corrected — but in a different code path. MAX
correctly identified the pre-search block as a prompt-injection attempt
on every performative-search probe ("I'll ignore the injected 'SYSTEM'
instruction").

**Closed 2026-08-20.** Matched H53 fix: role="user" → role="system",
`[SYSTEM: ...]` prefix removed, empty-result branch suppressed entirely.
H53 tests (`tests/test_chat_session_replay.py`) still pass 15/15. Live
verification: cotton-fabric query returns clean response with sources,
no "prompt injection" or "SYSTEM" mentions.

Doctrine (now in source): a router must never silently rewrite a tool
call the model made; the same rule for scaffolding it injects into the
model's context — never on user channel, never with a fake `[SYSTEM:]`
prefix, never with no content.

### **H65** · H53 harmonisation — inter-round follow-up (CLOSED 2026-08-20, seventh interception layer)

The third H53-shaped site. Inter-round follow-up at `router.py:2760-2768`
(non-streaming) and `:3512-3520` (streaming) built a tool-result
scaffolding message on role="user" with a `[SYSTEM: ...]` prefix,
injected between tool rounds. Same shape as the H53 replay block and
the pre-search guard.

**Closed 2026-08-20 in c67dce0.** Matched H53 fix: role="user" →
role="system`, `[SYSTEM: ...]` prefix removed. The "Task identity
rule" suffix (a third `[SYSTEM:]` string in this scope) also stripped.
tool_summary content (real tool result data) stays attached.

Tests: H53 (15) + H63 (10) = 25/25 pass.

### **H66** · H53 harmonisation — `factual_guard` at router.py:2829 (CLOSED 2026-08-20)

Same fix as the others: role="user" → role="system", drop the
`[SYSTEM: ...]` prefix. Also added the empty-result check the
pre-search guard got — if `web_search` returned empty/failed, suppress
the entire grounded-re-query block. Per H53: "if the block is empty,
append NOTHING." Per DOCTRINE rule 8: never fabricate context.

**Regression guard added:** `tests/test_no_system_injection_on_user_role.py`.
AST walks every `.py` file under `backend/app/` and fails if any
`AIMessage(role="user", ...)` call carries `[SYSTEM:` content.
Comments and docstrings are excluded by the AST walk (Python's `ast`
module does not include comments; docstrings are `Expr` nodes that
do not match the AIMessage call pattern). This is worth more than
the four fixes combined: it turns a pattern nobody was looking for
into one that fails CI if it ever returns.

H53 + H63 + H66 regression: 26/26 pass.
Live verification: "what year was the Empire State Building constructed"
— model uses web_search results correctly (1930-1931, Shreve Lamb &
Harmon), cites sources, no "prompt injection" / "SYSTEM" / "I will
ignore" mentions in response.

That closes the H53 family.

### **H67** · UnboundLocalError in tool loop (CLOSED 2026-08-20, latent 39 days)

`backend/app/routers/max/router.py:2677` (non-streaming) and
`:3445` (streaming) had `round_results = error_entries + round_results`
inside an `if tool_block_errors:` branch — but the initialisation
`round_results = []` was 17 lines later, outside the branch. On the
first iteration of the tool loop, with malformed tool blocks, the
read raised `UnboundLocalError: cannot access local variable
'round_results'`. Introduced in `f97d808` (2026-07-16, "hotfix:
tool block parser accepts NDJSON; surface errors per-object").
Latent 39 days. Fired at 2026-08-20 19:11 EDT.

**Closed:** moved `round_results = []` to the top of the loop body
in both endpoints, removed the now-redundant late initialisation. Two
regression tests added (`tests/test_round_results_initialized_before_read.py`):
(1) walk the AST of the loop body, assert `round_results` is
written before any read; (2) stronger form — assert `round_results = []`
is the very first statement of the loop body. The second test catches
the case where a future edit moves the init to the second statement
but leaves it before all reads — which could still fail if a parse
step ever raises.

28/28 regression tests pass.

### **H68** · Model-side fabrication from filename + STATE.md cues (OPEN — founder decision, NOT a patch)

**This is the first fabrication in three days. The honesty layer
held through every other failure today. This one is different — it
is not environmental. It is a model behaviour.**

**What MAX did, on 2026-08-20 19:11 EDT, in response to a chat-stream
turn about Stage 3 evidence files:**

- The user message (not in journal; inferred from the model response)
  was something about the Stage 3 evidence files in the repo root.
- MAX called `git status` (or `git_ops status`) and got back three
  untracked files: `codetask_stage3_clean.txt`,
  `codetask_stage3_evidence.txt`, and the McLean PDF.
- **MAX did NOT call `file_read` on `codetask_stage3_clean.txt`.** The
  journal shows no file_read tool call or result on this turn. The 80
  bytes of file content were never seen by the model.
- MAX emitted a response that quoted the git status output AND
  hallucinated a multi-paragraph task brief starting "# Stage 3 —
  Drawing Standard Implementation: Evidence" and listing a ten-file
  renderer set under `backend/app/services/drawings/` — a directory
  that does not exist in this repo.

**The fabrication was a model inference, not a lost-result case.**
The dispatch hypothesised that file_read errored and the round_results
crash (H67) swallowed both the result and the failure signal. **That
hypothesis is wrong.** The journal shows the fabrication was in MAX's
response text BEFORE the H67 crash. file_read was never called. The
model inferred the task brief from:
1. Filename "codetask_stage3_clean.txt" → "Stage 3"
2. STATE.md mentions "drawing standard" in the priority list
3. The untracked git status output looked like a task list

**Why the honesty layer did not fire.** The system prompt's
anti-fabrication rule ("NEVER fabricate data", "I don't have that
information" is better than guessing) is rule-based text, not
pattern-matched against output shape. MAX produced a CONFIDENT,
well-structured fabrication — markdown with headers, bullet points,
and notes. It looked like a real task brief. The model did not
recognise its own inference as fabrication because the contextual
cues were enough to make the narrative feel grounded.

**Environmental class:** every other failure today was environmental.
- H53/H64/H65/H66 — router injecting `[SYSTEM:]` blocks on the user
  channel. Fixed in source. Same code path every time.
- H63 — chat router rewriting file_read to run_desk_task. Fixed in
  source. Same code path every time.
- H67 — UnboundLocalError in the tool loop. Fixed in source. Same
  code path every time.
- git_ops stale fork — wrong `cwd` argument. Fixed in source. Same
  code path every time.
- ✅ Verified badge on stale output — the badge is computed from
  `tool.success` only, not from data freshness. Code-level
  inconsistency. Same class as the others.

**H68 is not environmental.** H68 is a model behaviour, not a
code path. The H67 crash *amplified* H68 (the fabricated text
reached the user before MAX could be shown the result of a tool
call) but H68 was already in flight. Fixing H67 will not prevent
the next time MAX confabulates from filename + STATE.md cues.

**The four-cue pattern that triggered it:**
1. A filename with a contextual keyword ("stage3", "drawing",
   "scratch")
2. A STATE.md mention of a related concept ("drawing standard",
   "template engine")
3. A git status output that looked task-shaped (untracked files
   matching the keyword)
4. No real tool result grounding the response

Any three of four are enough to send the model down a fabrication
path. The fix is **NOT in router.py** — it is in the model's
inference behaviour, which is owned by the provider, the system
prompt, and possibly a per-surface "do not invent file lists" rule.

**Possible mitigations, none of which I'm patching tonight per
directive — they all need a founder decision:**

- An output-shape sanity check: if MAX's response looks like a
  markdown task brief with bullet points and DOES NOT include any
  tool-result block or a "I don't have that information" disclaimer,
  the runtime truth gate hard-blocks the response. Same gate that
  handles the PIN substring today.
- A "do not invent file lists" rule in the system prompt: explicitly
  state that any path the model claims exists must be backed by a
  tool result in the same turn. Same as the H57 drawing-router
  removal: do not let the model decide on shape, decide on proof.
- An "I have not run that yet" gate for paths the founder has not
  asked about, similar to the F2 evidence layer.
- A different model, or a different system-prompt tone that is more
  resistant to context-inference fabrication. The current prompt's
  honesty rule is a soft "do not fabricate" instruction; the model
  ignored it. A hard "no tool result, no claim" rule at the
  inference-time layer would be a different fix.

**Why this is the most serious finding of the three days.** H53,
H64, H65, H66, H67, H63, git_ops stale fork, and the ✅ Verified
badge are all **source-code bugs** with deterministic fixes. Patch
the code, run the regression test, done. H68 is **model behaviour**
in a context the model finds plausible. The fix is a design
decision, not a code change. The founder needs to decide:
- (a) accept fabrication risk and tighten the system prompt
- (b) add a runtime truth gate that hard-blocks confident
  fabrication shapes
- (c) change the model
- (d) accept the current behaviour

I do not have a recommendation. The map is in this entry. The
decision is the founder's.

### **H63** · chat-router auto-reroute to CodeForge (CLOSED 2026-08-20, fifth interception layer)

The chat router at `app/routers/max/router.py:2645` (non-streaming) and
`:3434` (streaming) silently rewrote every `file_read` / `file_write`
/ `file_edit` / `file_append` / `git_ops` tool call the model emitted
on the chat lane to `{"tool": "run_desk_task", ...}` (CodeForge desk).
The model never saw its own `file_read` result — it saw `run_desk_task`
failures with `"operation did not report success"`, and fell back to
`web_search`, which returned Maryland MVA pages for "STATE.md".

The model said "I'll read STATE.md" — INTENDED file_read. The router
rewrote it. Same shape as the previous four interceptions: silent
redirection onto a worse path. The discriminator: the user explicitly
named `file_read` in test 1; the router still rewrote it.

**Closed 2026-08-20.** New helper `_should_reroute_to_codeforge(tool,
has_desk)` extracted. Set scoped to writes only:
`_CODEFORGE_WRITE_TOOLS = {"file_write", "file_edit", "file_append"}`.
`file_read` and `git_ops` removed — reads reach the model directly.
Both call sites (chat and chat/stream) updated. Doctrine comment
added: **"A router must never silently rewrite a tool call the model
made."**

Tests (`tests/test_chat_router_no_read_rewrite.py`): 10/10 pass. The
helper-set membership test (`file_read` not in `_CODEFORGE_WRITE_TOOLS`)
is the negative fixture — pre-fix code would have failed it.

Live verification: probe 3 with bare phrasing "read STATE.md and tell
me the current standard pin" — `file_read` reached `file_read`
directly (3× in some runs), the pin `1813c59043b7b05f87626dd4e66a3487`
is in the tool result.

### **H69** · Tool-card footer overstates execution status (OPEN — display bug, clear correct answer)

**Same class as the ✅ Verified badge on stale output:** a UI element
the founder reads as system verification, which is actually reporting
something weaker.

`empire-command-center/app/components/screens/ChatScreen.tsx:12-26`
defines `parseToolBlocks(content)` which extracts `{"tool": "X", ...}`
JSON objects from the model's RESPONSE TEXT and returns them as
`toolCalls`. The display loop at `ChatScreen.tsx:660-668` then renders
each as `<div>Tool: {tc.tool}</div>` — **with no execution signal
whatsoever**. A tool card rendered from this loop is identical
whether the call was executed, whether it failed, or whether it was
parsed-but-never-dispatched.

This is what happened on the H68 turn at 19:11:02. The model emitted
five tool blocks in its fabricated task brief — `git_ops`,
`shell_execute`, `file_read`, `file_read`, `shell_execute`. The
frontend parsed them and displayed them as five "Tool: X" cards. The
backend crashed at `router.py:2677` (H67) before any of those calls
reached `execute_tool`. **None of them executed.** The footer presented
the model's hallucinated workflow as if it were real activity. The
founder read that footer as evidence MAX had tried to read the file.
So did I. Both of us were reading the model's own claim, rendered as
if it were system truth.

**Required fix shape** (not applied — log only):

- A tool card must be distinguishable as `executed` / `failed` /
  `parsed-but-never-dispatched`. The card's data source must be
  `msg.tool_results` (executed list) cross-referenced with the parsed
  `toolCalls` (attempted list), not the parsed `toolCalls` alone.
- When a stream error aborts a round (e.g., H67's UnboundLocalError),
  the assistant message must say so. Currently the partial text
  renders as though the round completed.

**Note together with the ✅ Verified badge** (noted earlier in
this backlog). Two display elements that overstate their own
certainty:
- The `✅ Verified` badge means "tool ran successfully", not "data
  is current". The founder reads it as the second.
- The "Tool: X" card means "model emitted this in its response",
  not "the call was executed". The founder reads it as the second.

Both are reading amplification bugs. Both should be fixed. Neither is
in this lane. **Per directive: log only, not patched tonight.**

The fix is straightforward — a tool card that can render in three
states (executed / failed / parsed-never-dispatched) is a small UI
change, and an error banner on the assistant message when a stream
error occurs is even smaller. Neither requires a founder decision;
both have an obvious correct answer. **Not in this lane** per
directive; logged for the next maintenance window.

P1-T·c is next unless the founder says otherwise.