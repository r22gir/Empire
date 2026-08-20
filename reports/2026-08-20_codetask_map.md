# Code-Task Execution Map (2026-08-20, WIP)

**STOP — Phase 1 read-only map, NO FIXES.** Per the dispatch: "MAP ONLY"
and "NO FIXES. NO EDITS OUTSIDE THE REPORT."

## Q1 — WHERE does the code task actually execute, and where does it log?

**Code-task execution runs IN-PROCESS inside the openclaw worker.** Path:

- `openclaw_worker.py:796` — `code_task = code_task_runner.submit(prompt)`
  is called from inside `_execute_code_task` (line 784)
- `openclaw_worker.py:808-817` — polls `code_task.state` until
  `RUNNING`/`COMPLETED`/`ERROR`, blocking on `CODE_TASK_TIMEOUT`
- `code_task_runner.py:590` — `self._running[task.id] =
  asyncio.create_task(self._execute(task))` — schedules `_execute`
  on the CURRENT event loop (the openclaw worker event loop)
- `code_task_runner.py:594` — `async def _execute(self, task)` is
  the loop that drives Atlas → parse → execute → feed back
- `code_task_runner.py:23` — `logger = logging.getLogger("max.code_task")`
- `chat_backup_scheduler.py:16` — `logging.basicConfig(level=logging.INFO)`
  is the ONLY logging config call in the repo, called once at module
  import. It configures the ROOT logger IF root has no handlers (no-op
  if uvicorn/main already configured handlers).
- `main.py:20` — `validation_logger = logging.getLogger("max.validation")`
  does NOT do basicConfig — main.py does not configure logging.

**Verdict:** Code-task logs go to `max.code_task` via stderr/whatever
root handler uvicorn configured. They are NOT going to a separate file or
process; they share the backend's stdout/stderr/journalctl. **The code-task
code path does NOT execute in any separate process or unit — it shares the
empire-backend process.**

## Q2 — IS the protocol satisfiable?

**No — for any model that uses the JSON forms (formats 2 or 3), the
scoring is broken by line 399.** The protocol at lines 226-236
advertises three formats:

```
Valid formats are:
  1. Native function/tool call if supported.
  2. Raw JSON object with a top-level "tool" field.
  3. A fenced JSON block with one JSON object.
```

The retry message at lines 278-282 shows three examples (the third in
a fenced block, the second as a bare JSON object).

**But line 661 falls through to `parse_tool_blocks(response_text)` ONLY if
`not tool_calls` is true**, where `tool_calls` was populated from native
function_calls at line 653-660. A model replying with formats 2/3
(native function_calls is None) — parses JSON. That's fine.

**The actual scoring failure is line 399:**
```python
task.supports_tool_calls = bool(response.function_calls) if response.function_calls is not None else supports_native_tools
```

- Native function_call response → `response.function_calls = [...]` →
  `supports_tool_calls = True`
- Raw JSON response → `response.function_calls = None` → `supports_tool_calls = False`
- Fenced JSON response → same, `supports_tool_calls = False`

**`supports_tool_calls` is False for any model that uses JSON forms** —
so a JSON-emitting model is recorded as if it had emitted no tool calls.

`force_one_tool_call = task.execution_mode != "read_only"` (line 623).

`MAX_NO_TOOL_RETRIES = 2` (line 28). The condition at line 799:
```python
if force_one_tool_call and no_tool_retries >= MAX_NO_TOOL_RETRIES and not executed_tool_calls:
```

A JSON-emitting model fails `force_one_tool_call and not executed_tool_calls`
for 2 retries → marked "selected code model did not emit executable tool
calls" → ERROR state. Even though the model DID emit — in JSON form — the
scoreboard read it as zero.

A model emitting JSON in a fenced block IS in `parse_tool_blocks`'s coverage
range (line 175 of tool_executor.py: "fenced blocks or raw JSON"). The
function CALLS that parse_tool_blocks but the SCORING doesn't recognise
that those calls happened.

## Q3 — WHY is `result` NEVER PERSISTED on failure?

**Found it: the early-return paths at lines 799-822 (and 834-844, 852-859, 861-868)**
all set `task.error = task.failure_reason` and return — **none of them set
`task.result`.**

`task.result` is set in EXACTLY ONE PLACE: **line 870:**
```python
task.result = _compose_verified_summary(task)
task.state = CodeTaskState.COMPLETED
task.completed_at = datetime.utcnow().isoformat()
```

This is the happy-path only — inside the `if executed_tool_calls: ... else:
...` branch where the task actually completed successfully. The
exception handler at line 877 (asyncio.TimeoutError) and line 884 (Exception)
also set ONLY `task.error`, never `task.result`.

**Effect:** every one of the 5931 rows in the openclaw_tasks table has
`result=None` (because the early-return paths set only `error`, and the
happy-path branch sets `result` to a summary string). The model's actual
response content is discarded entirely on failure — only the error string
persists.

The 5931 errors that say "Code task completed without actual file changes"
(5574 occurrences, lines 834-844) and "selected code model did not emit
executable tool calls" (158 occurrences, lines 799-810) have `result=None`
and only a short failure reason. The 5,894 May 4-6 burst rows are exactly
this pattern.

## Q4 — Does the parser honour all three advertised formats?

**The parser DOES. The scorer does NOT.** Trace:

| Path | Where | Behaviour |
|------|-------|------------|
| Format 1 (native function call) | `response.function_calls` (set by provider) | `tool_calls` populated from native calls at line 653-660. `supports_tool_calls=True`. |
| Format 2 (raw JSON with top-level "tool") | `parse_tool_blocks(response_text)` line 662 | `tool_calls` populated from raw JSON. `supports_tool_calls=False` (line 399). |
| Format 3 (fenced JSON block) | Same — `parse_tool_blocks` handles both (line 175 docstring) | Same as Format 2. |

`parse_tool_blocks` at tool_executor.py:175-204 is the single parser.
It handles formats 2 AND 3 (raw JSON OR fenced JSON). Format 1 is
handled separately at line 653-660 (`response.function_calls`).

**All three are PARSED. But `task.supports_tool_calls` is set ONLY by line 399
based on `response.function_calls is not None` — so the scorer registers
JSON-only models as if they had emitted no tool calls.**

## Summary table

| Question | Answer |
|----------|--------|
| Q1 execution | In-process in openclaw worker → code_task_runner.submit → asyncio.create_task → _execute. Log via `max.code_task` Python logger → stderr/whatever root handler → journalctl. Same process as the API. |
| Q2 satisfiable | The PARSER handles all three formats. The SCORER at line 399 sets `supports_tool_calls = bool(response.function_calls) is not None else supports_native_tools`. JSON-only models are mis-scored as zero tool calls. `MAX_NO_TOOL_RETRIES = 2`. A model emitting valid JSON in either format fails after 2 retries with "selected code model did not emit executable tool calls". |
| Q3 result discarded | `task.result` is set ONLY in the happy-path branch at line 870. All failure paths (lines 799-810, 834-844, 852-859, 861-868, 877-882, 884-889) early-return with `task.error` only. The 5931 rows have `result=None` because that's how the code was written — not a display bug, an architectural data discard. |
| Q4 parser honours formats | Parser (parse_tool_blocks) handles formats 2 & 3. Format 1 is native. But scorer reads ONLY native `response.function_calls`. JSON-only models are registered as zero tool calls — silent. |

## The single root-cause observation

Lines 653-662 and 399 in code_task_runner.py say different things about
the same response:
- 653-662 says: "we got at least one tool call" (parsed or native)
- 399 says: "supports_tool_calls = bool(native-only)" — false unless native

The model's actual tool-call list (`executed_tool_calls`) is built from
EITHER path correctly (line 724 — `_tool_record(tc, result, ...)` runs
regardless of source). But the SCORING of `supports_tool_calls` reads
only native, and the SUCCESS-PATH at line 870 only runs if
`executed_tool_calls` is non-empty AND `verified_commit_hash` is set
— which requires a successful `git_ops` commit.

So a model that runs `file_read` only gets `executed_tool_calls` populated
but never enters the success branch (no commit was attempted). That is
the path producing the 5,894 burst entries.

## What the dispatch said vs what the code does

Dispatch: "5,574 occurrences: 'Code task completed without actual file
changes'." That string is at line 815:
```python
f"Code task completed without actual file changes "
f"(provider={...}, model={...}, attempts={...})"
```

Path to that error: line 834 (else branch of `if task.execution_mode ==
"read_only":`). `executed_tool_calls` is non-empty (line 724 appended it)
BUT `task.files_changed` is empty (no file_write/file_edit/file_append/git
succeeded). → ERROR set.

Dispatch: "158: 'selected code model did not emit executable tool
calls'". That string is at line 802 (`force_one_tool_call and
no_tool_retries >= MAX_NO_TOOL_RETRIES and not executed_tool_calls`).
Path: model replied with prose (no native functions and no parseable JSON).
That's 158 of 5931.

Both errors come from the same place: the model either did not execute
write tools OR did not produce parseable tool calls. The scorer's
"not parseable" verdict is `result=None` — even though
`response.content` (the model's actual reply text) was available in memory
and could have been recorded as `task.result = response.content` for
diagnostic purposes.

## What the founder's session evidence supports

- 5931 rows of `error` populated, 0 rows of `result` populated: confirmed
  by direct query (per dispatch's evidence gathering).
- 5,574 rows saying "without actual file changes" — matches line 815
  branch.
- 158 rows saying "did not emit executable tool calls" — matches line 802
  branch.
- 4 providers show same failure — confirmed by dispatch (not provider-
  specific).
- May 2 commits c2d870c et al. switched MAX to MiniMax — that is the
  trigger timing, not the mechanism.

## Open questions the dispatch did NOT ask but should be noted

1. `parse_tool_blocks` is invoked on lines 662, but only when the
   NATIVE function_calls path was empty. A model that mixes native +
   JSON (rare but possible) would get only the native calls — the JSON
   ones are skipped because line 661 checks `if not tool_calls:`.

2. The `fallback_actions = _synthesize_tool_actions_from_prompt`
   path at line 672-680 infers tool calls from the prompt text via
   regex. When the model emits "use file_edit on backend/X" as prose,
   the regex catches "file_edit" and synthesizes an action from the
   path. That's a second chance, but only if the regex catches the
   right tool — and only if the path is in the prompt.

3. `executed_tool_calls` is populated correctly (line 724) but
   `task.result` is never set on any failure path. Even saving the
   LAST model response content (which is in memory when we set task.error)
   would have made the 5931 failures debuggable.

4. The `task.failure_reason` strings at lines 802/815/838 include
   the prompt_attempts count — but no model name, no response text, no
   response.function_calls count. The information to diagnose the 5,574
   "no file changes" failures was discarded at the moment of error set.

## Stop point

STOP. Per dispatch: "NO FIXES. NO EDITS OUTSIDE THE REPORT." Report is
ready. Map answers are above with file:line for every claim. The single
architectural observation: `task.result` is set in exactly ONE place
(line 870, happy path), and the verdict-only failure path is why the
5,894-row burst was never diagnosed.

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
