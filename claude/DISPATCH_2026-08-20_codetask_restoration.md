# DISPATCH — CODE TASK RESTORATION (dead since 2026-05-06)

Authored 2026-08-20. Map is committed at `45273c1`
(`reports/2026-08-20_codetask_map.md`). This is Phase 2: the fix.

**One-line summary of three months of failure:** `parse_tool_blocks` handles
all three advertised response formats correctly, and then
`code_task_runner.py:399` scores the result by reading `response.function_calls`
alone. A model that replies in valid JSON is parsed successfully and recorded
as having emitted nothing.

**Every failure branch discards the model's response.** `task.result` is set
in exactly one place — line 870, the happy path. 5,931 rows carry a verdict
and no evidence. That is why this survived for three months in plain sight.

**The logs that should have caught it never emitted**, despite the calls
being at ERROR level.

---

## THE FINDINGS THIS FIXES

| # | Finding | Location |
|---|---|---|
| **F1** | Scorer reads only `response.function_calls`; parser honours 3 formats. JSON-replying models score as zero tool calls | `code_task_runner.py:399` vs `tool_executor.py:175` |
| **F2** | `task.result` set ONLY on the happy path. Six failure branches record `error` and drop the response | `code_task_runner.py:870`; branches at 799-810, 834-844, 852-859, 861-868, 877-882, 884-889 |
| **F3** | `max.code_task` ERROR lines never reach journalctl during confirmed failures | `code_task_runner.py:23`; nine `logger.error` sites |
| **F4** | `logging.basicConfig` in `chat_backup_scheduler.py:16` is a silent no-op — root already has a uvicorn handler | `chat_backup_scheduler.py:16` |
| **F5** | "7,372 queued" counts every row ever written. Actual pending: **zero** | badge/status source, TBD |
| **F6** | Retry budget spends 4 attempts on a structurally impossible operation | `MAX_NO_TOOL_RETRIES` |

**Evidence base, do not re-derive:** 5,931 failed / 1,439 done / 0 pending.
May 4–6 = 5,895 of the failures. Last success ever `2026-05-06 07:24:55`, and
it was a *Read file*, not a write. Same failure under `xai/grok-4-fast`,
`openclaw/openclaw`, `groq/llama-3.3-70b`, `unknown/none` — four providers,
identical outcome, which is what rules out the May 2 MiniMax switch
(`c2d870c`, `34b1609`, `215db5e`, `e0a66a9`) as the mechanism. It explains the
timing of the burst only.

---

## PASTE INTO M3 (fresh session)

```
Check /model first — confirm M3. Read CLAUDE.md, then STATE.md (v7), then
claude/DOCTRINE.md, then reports/2026-08-20_codetask_map.md (commit
45273c1). Repo ~/empire-repo-main, branch feature/drawing-standard.

INFRA: backend restart is `systemctl --user restart empire-backend` and
NOTHING else. Never hand-start uvicorn or bind :8000. Never stop
opencode-remote.service (HERMES).

TASK: restore code-task execution. Your own map found the cause. Work in
order — F2 and F3 FIRST, because they are what makes F1 verifiable. 🛑 STOP
between stages.

--- STAGE 1 · EVIDENCE (F2 + F3) — do this BEFORE the scorer fix ---

Rationale: if you fix the scorer first and it does not work, you will be
back where the last three months were — a verdict with no evidence. Make
the system able to explain itself, THEN change behaviour.

F2 · PERSIST THE RESPONSE ON EVERY FAILURE PATH.
  All six failure branches must record what the model actually returned:
  the raw response text, `response.function_calls` (or its absence), the
  output of `parse_tool_blocks`, and which parse formats were attempted and
  matched. Truncate sensibly for storage; do not truncate away the part
  that matters.
  This is not optional polish. A failure path that discards its evidence
  guarantees the failure survives — that is the whole lesson of this map.

F3 · MAKE max.code_task ACTUALLY LOG.
  Nine logger.error sites (771, 809, 821, 831, 843, 858, 867, 882, 889)
  produced NOTHING in journalctl during a confirmed failure window
  (2026-08-20 02:38-02:42, 8 real failures, only health polls in the log).
  ERROR outranks the root WARNING level, so level filtering alone does not
  explain it. FIND THE ACTUAL REASON before adding a handler — do not
  paper over it with a new sink and call it fixed.
  Then give max.code_task an explicit handler at INFO+ that survives
  uvicorn's config.

F4 · Remove or correct the no-op basicConfig in
  chat_backup_scheduler.py:16. A logging call that silently does nothing is
  worse than none — it reads as configured.

🛑 STOP. Report where the ERROR lines were going, and show a NEW failure row
with populated `result`. Do not proceed to Stage 2 until a failure explains
itself.

--- STAGE 2 · THE SCORER (F1) ---

code_task_runner.py:399:
  task.supports_tool_calls = bool(response.function_calls) if
      response.function_calls is not None else supports_native_tools

The prompt at lines 228-236 promises THREE valid formats: native call, raw
JSON with a top-level "tool" field, fenced JSON block. parse_tool_blocks
(tool_executor.py:175) honours all three. Line 399 reads only the native
field. A model answering in format 2 or 3 is parsed successfully and scored
as having emitted nothing.

FIX: the scorer reads the PARSED RESULT, not the raw provider field. One
source of truth for "did the model emit an executable action" — the parser.
Never two places deciding the same fact. (DOCTRINE rule 12.)

TESTS, each with a fixture reproducing a real provider shape:
  - native function_call → scored as tool call ✅
  - raw JSON `{"tool":"file_read","args":{...}}` with no native call →
    scored as tool call ✅  (THIS IS THE BUG — it must FAIL before the fix)
  - fenced ```json block → scored as tool call ✅
  - prose with no action → scored as NO tool call ✅ (must still fail)
  - malformed JSON → NO tool call, and the raw text is persisted per F2

The negative fixtures must fail for the RIGHT reason. State which fixture
trips which condition.

🛑 STOP.

--- STAGE 3 · LIVE PROOF ---

Submit ONE real code task through the actual path — something trivial and
reversible, e.g. append a comment line to a scratch file under /tmp. Then
report:
  - the openclaw_tasks row, including populated `result`
  - the journalctl lines it produced
  - whether the file actually changed on disk

A passing test suite is not proof here. Three months of failures were
"successful" completions that wrote nothing. THE FILE MUST ACTUALLY CHANGE.

🛑 STOP with the row, the log, and the diff.

--- STAGE 4 · THE COUNTERS (F5 + F6), only after Stage 3 passes ---

F5 · The "7,372 queued" badge counts every row ever written. Zero tasks are
  pending. It has been reading as active work for months and is on the
  founder's screen. Find the source and make it count actual pending work.

F6 · Retry budget: 4 attempts against a structurally impossible operation is
  what turned one bug into 5,931 rows. Retries should stop when the failure
  is deterministic — the same failure reason twice is not worth a third
  attempt. (DOCTRINE rule 26, applied to the machine rather than the agent.)

DO NOT purge the 5,931 historical rows. They are the record of this
investigation and the negative-fixture source. If the badge needs them out
of the way, filter — never delete.

🛑 STOP. Report found/changed/tests/commit.
```

---

## WHAT THIS DOES NOT DECIDE

**Whether MAX should have code execution at all** is still the founder's open
question. This dispatch restores the capability and proves it works; it does
not settle whether to use it.

Arguments on the record, unresolved:
- **For:** the M-lane needs an orchestrator that can act, not only draft.
- **Against:** this is the capability that produced the quote fabrications,
  and M3 through Claude Code has been doing the work well.

A working, observable code path is worth having either way — if it is
retired later, it should be retired knowingly rather than left failing
silently.

## DOCTRINE ADDITIONS EARNED HERE

- **A failure path that discards the evidence guarantees the failure
  survives.** Persist what you saw, not only what you concluded. 5,931
  verdicts, zero evidence, three months.
- **Never let two places decide the same fact.** The parser and the scorer
  disagreed on "did the model emit a tool call," and the disagreement was
  invisible because only one of them was consulted.
- **A logging call that silently does nothing is worse than none** — it
  reads as configured. (`basicConfig` no-op, F4.)
