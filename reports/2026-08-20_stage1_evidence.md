# Stage 1 Stop-Gate Report — F2, F3, F4

**As of:** 2026-08-20 11:18 EDT
**Branch:** `feature/drawing-standard`
**Map reference:** `reports/2026-08-20_codetask_map.md` (commit `45273c1`)

This is the 🛑 stop-gate report after Stage 1 (Evidence). Stage 2 (Scorer) and
later stages are **not** started until the founder eyeballs this.

## What the dispatch asked

> F2 · PERSIST THE RESPONSE ON EVERY FAILURE PATH.
> F3 · MAKE max.code_task ACTUALLY LOG. … FIND THE ACTUAL REASON before
>      adding a handler — do not paper over it with a new sink and call it fixed.
>      Then give max.code_task an explicit handler at INFO+ that survives
>      uvicorn's config.
> F4 · Remove or correct the no-op basicConfig in
>      chat_backup_scheduler.py:16.

## F3 — root cause found, not papered over

**The reason `max.code_task` ERROR never appeared in journalctl**

Empirical test (in-process, with `python3`):
```
root has handlers: False
ct has handlers: False
ct propagate: True
ct effective level: 30 (WARNING)
ct.error('TEST') → emits to stderr ✓
```

`logger.error()` from `max.code_task` was **capable** of writing to stderr.
So the problem was not level-filtering and not propagation.

Direct evidence from the live unit (the canonical repo file says one thing, the
installed unit says another):
```
$ systemctl --user cat empire-backend.service | grep -E 'Standard(Out|Err)or'
(repo file says: StandardOutput=journal / StandardError=journal)
$ systemctl --user show empire-backend.service | grep -E 'Standard(Out|Err)or'
StandardOutput=journal
StandardError=inherit      ← LIVE
```

The live unit at `~/.config/systemd/user/empire-backend.service` does NOT
include a `StandardError=journal` line. Systemd's default for a missing
`StandardError=` is `inherit`. So:

* `stdout` → journald → journalctl ✓ (uvicorn's "access" handler writes here)
* `stderr` → inherited → NOT journaled ✗ (where `logger.error()` lands)

That is why only access logs were visible during the 02:38–02:42 failure
window — and why nine `logger.error` calls produced nothing. The repo unit
file (`systemd/empire-backend.service`) has the correct `StandardError=journal`
line, but the installed unit was generated from a different source and never
picked up the fix.

The infra rules say not to modify live systemd units. So the fix lives in
code: `code_task_runner.py` now attaches an explicit `StreamHandler` to the
`max.code_task` logger that writes to **stdout** — the stream that IS
journaled.

## F3 fix — what changed

`backend/app/services/max/code_task_runner.py`:

* At module import, attach a `StreamHandler(stream=sys.stdout)` to
  `logging.getLogger("max.code_task")` at `INFO+`, with a formatter that
  prefixes the line with `max.code_task`. Idempotent (a marker attribute on
  the handler prevents double-attach). Sets `logger.propagate = False` so we
  do not double-log via the broken stderr path.
* The reason is documented in the source comment so the next person does not
  strip this as dead code.

## F2 fix — what changed

`backend/app/services/max/code_task_runner.py`:

* New `CodeTask` fields: `last_response_text`, `last_function_calls_summary`,
  `last_parse_outcome`. Captured once per model response by a new helper
  `_capture_response_evidence(task, response, tool_calls)` called inside the
  execute loop right after the response is parsed.
* New helper `_format_failure_evidence(task, final_outcome)` returns a
  structured string with provider, model, supports_tool_calls, attempts,
  failure reason, the raw response text (truncated at 4000 chars, original
  length preserved), `response.function_calls` summary, and the parse
  outcome (which formats were attempted and matched).
* **All six failure branches** plus the two outer except clauses now set
  `task.result = _format_failure_evidence(...)` before `return` / exit.
* `to_dict()` includes the new fields so they reach the JSON layer.
* `openclaw_worker.py` line 843: the `code_task.state == ERROR` branch now
  passes `result=result_text` to its `ExecutionResult`, so the worker's
  `_update_task(...)` writes the populated `result` to the DB.

## F4 fix — what changed

`backend/app/services/chat_backup_scheduler.py`:

* Removed `logging.basicConfig(level=logging.INFO)`. It is a no-op when
  uvicorn has already configured the root logger (which it has), so it
  silently does nothing and only misleads a reader into thinking logging is
  configured. Replaced with a comment explaining where logging is actually
  owned.

## Live verification

Backend restarted via `systemctl --user restart empire-backend` (the only
approved restart method).

Submitted one real code task (id `7378`) through the API:
```
POST /api/v1/openclaw/tasks
{
  "title": "STAGE1-F2-F3 verification task (retry)",
  "description": "Write hello to /tmp/codetask_f2_evidence.txt with content
                  hello-stage1-f2-f3. Then edit it to hello-stage1-f2-f3-done.
                  Do not edit repo files. Do not commit.",
  "desk": "codeforge",
  "priority": 5,
  "source": "manual-code-task"
}
```

Worker processed it. `status: "failed"`. The DB row now has populated
`result` (truncated for readability):

```
result: "Final outcome: completed without actual file changes
Provider used: openclaw
Model used: openclaw
Supports tool calls: True
Prompt attempts: 2
Failure reason: Code task completed without actual file changes
                 (provider=openclaw, model=openclaw, attempts=2)

Last model response text:
## Summary
- **shell_execute is restricted** on this surface (L3 PIN-gated). All 3 attempts
   were blocked before execution — no commands ran, so no output exists to report.
- Per security policy, I won't ask for or echo a founder PIN in the chat channel
   — PIN entry happens only through the portal approval flow. …
- **Ollama is not available** — noted; anything relying on it
   (RecoveryForge image classification fallback) won't work until it's back.
- No pending founder task to continue, so I'm concluding here. …

Last response.function_calls:
absent (response.function_calls is None)

Last parse outcome:
native: matched=False count=0; parse_tool_blocks: attempted=True matched=False;
   effective_tool_calls_after_merge=0"
error: "Code task completed without actual file changes
        (provider=openclaw, model=openclaw, attempts=2)"
```

journalctl during the run (before fix this window was empty):
```
Aug 20 11:17:51 EmpireDell python3[577760]: 2026-08-20 11:17:51,004 INFO max.code_task
        Code task 64346ad7-194 submitted: DB-backed OpenClaw CodeForge execution task.
Aug 20 11:18:10 EmpireDell python3[577760]: 2026-08-20 11:18:10,123 ERROR max.code_task
        Code task 64346ad7-194 had no actual file changes
Aug 20 11:18:10 EmpireDell python3[577760]: Task #7378 failed truthfully via code_task_runner:
        Code task completed without actual file changes (provider=openclaw, model=openclaw, attempts=2)
```

Three things were wrong before this change:
* No `max.code_task` INFO line (logger was silent).
* No `max.code_task` ERROR line (same reason — root cause: stderr inherited,
  not journaled).
* DB row `result` was NULL on failure (only `error` was set).

All three are fixed and visible.

## Tests

`pytest tests/test_code_task_runner_evidence.py tests/test_openclaw_worker.py`
```
29 passed, 1 deselected, 129 warnings
```

The 1 deselected test (`test_git_ops_supports_diff_check_command_forms`) is a
pre-existing failure unrelated to this work: it asserts
`calls[0][:3] == ["git", "diff", "--check"]` but the actual call is
`["git", "-C", "/home/rg/empire-repo", "diff", "--check"]`. The test
fixture was written before the cwd flag was added to the runner. Per
Doctrine rule 7, pre-existing failures need stash-proof before changing, and
this dispatch is not about that test.

## Files changed

| File | Lines | Purpose |
|---|---|---|
| `backend/app/services/chat_backup_scheduler.py` | -2 / +5 | F4 — remove no-op basicConfig |
| `backend/app/services/max/code_task_runner.py` | +152 | F2 — evidence helpers, dataclass fields, capture in loop, populate result on every failure path. F3 — explicit stdout handler at INFO+ |
| `backend/app/services/openclaw_worker.py` | +1 | F2 — pass `result=result_text` in the `state == ERROR` branch so the populated result reaches the DB |

Total: 158 lines added, 2 deleted, across 3 files.

## Not done in Stage 1

* F1 (scorer fix in `code_task_runner.py:399`) — Stage 2.
* F5 / F6 (badge counter + retry budget) — Stage 4.
* Repo unit file `systemd/empire-backend.service` is already correct; the
  installed live unit at `~/.config/systemd/user/empire-backend.service`
  diverges. Fixing the installed unit is an infra change and is not in
  scope of this dispatch; the code fix in `code_task_runner.py` makes the
  journalctl visibility independent of the unit's `StandardError=` line.

## Stop point

Per dispatch: do not proceed to Stage 2 until a failure explains itself.
**A failure now explains itself** — task 7378's DB row has populated `result`,
and journalctl shows the corresponding `max.code_task` lines. Awaiting
founder eyeball before starting Stage 2 (F1 scorer fix + fixture tests).