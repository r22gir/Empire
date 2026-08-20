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