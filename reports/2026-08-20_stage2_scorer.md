# Stage 2 Stop-Gate Report — F1 scorer fix

**As of:** 2026-08-20 11:36 EDT
**Branch:** `feature/drawing-standard`
**Prior report:** `reports/2026-08-20_stage1_evidence.md` (commit `e854621`)

This is the 🛑 stop-gate report after Stage 2 (Scorer). Stage 3 (Live proof)
and later stages are **not** started until the founder eyeballs this.

## The bug being fixed (F1)

`code_task_runner.py:423` set
```python
task.supports_tool_calls = bool(response.function_calls) if response.function_calls is not None else supports_native_tools
```

The protocol at `_code_protocol_intro` (lines 232–235) advertises three valid
formats: native call, raw JSON `{tool:...}`, fenced JSON. `parse_tool_blocks`
(tool_executor.py:175) honours all three. A model replying in formats 2 or 3
has `response.function_calls == None` but a non-empty `tool_calls` list from
the parser. The buggy scorer ignored the parser and recorded
`supports_tool_calls=False`. **One fact decided in two places, one of them
wrong.** Doctrine rule 12 ("One service layer") forbids exactly this.

This is the only bug in code_task_runner that produces silent failures. The
parser was always correct; the scorer was always wrong.

## The fix

Three edits in `backend/app/services/max/code_task_runner.py`:

1. **Line 423** (`_request_code_response`) — DELETED the
   `task.supports_tool_calls = bool(response.function_calls) if ... else
   supports_native_tools` line. The provider-shaped field is no longer
   consulted for scoring.
2. **Line 757** (`_execute` loop preamble) — DELETED the
   `task.supports_tool_calls = supports_native_tools` line. Two places
   deciding the same fact, both wrong for JSON-only models.
3. **New line after `_capture_response_evidence(...)`** — ADDED
   `task.supports_tool_calls = bool(tool_calls)`. Single source of truth:
   the parser output. This runs once per model response, immediately
   after the native + parser merge.

Net: `task.supports_tool_calls` is now set in exactly one place, from the
parsed `tool_calls` list, which is the union of normalised native calls and
`parse_tool_blocks(response_text)` output. A model that emits valid JSON
without a native function_call now scores as `True`, matching what the
parser actually saw.

## Fixtures

New file: `backend/tests/test_code_task_scorer.py` — 5 fixtures, each
reproducing a real provider response shape.

| Fixture | Provider shape | Expected score | Pre-fix | Post-fix |
|---|---|---|---|---|
| `test_native_function_call_scored_as_tool_call` | `response.function_calls = [{tool:..., path:...}]`, content ignored | `True` | ✅ PASS | ✅ PASS |
| `test_raw_json_with_no_native_call_is_scored_as_tool_call` | `response.function_calls = None`, content = raw JSON `{tool:..., args:...}` | `True` | ❌ **FAIL** (F1 BUG) | ✅ PASS |
| `test_fenced_json_with_no_native_call_is_scored_as_tool_call` | `response.function_calls = None`, content = ```` ```json\n{tool:..., args:...}\n``` ```` | `True` | ❌ **FAIL** (F1 BUG) | ✅ PASS |
| `test_prose_with_no_action_is_scored_as_no_tool_call` | `response.function_calls = None`, content = prose summary | `False` | ✅ PASS | ✅ PASS |
| `test_malformed_json_no_tool_call_and_raw_text_persisted` | `response.function_calls = None`, content = truncated JSON | `False` + raw text persisted (F2) | ✅ PASS | ✅ PASS |

The two BUG fixtures fail pre-fix with the exact F1 assertion:
```
AssertionError: F1 BUG: scorer recorded raw-JSON-only response as having
emitted no tool calls. Pre-fix code_task_runner.py:399 read
response.function_calls (None) and ignored parse_tool_blocks output.
assert False is True
```

The CodeTask dump confirms the parser found the tool call:
```
last_parse_outcome='native: matched=False count=0;
                     parse_tool_blocks: attempted=True matched=True;
                     effective_tool_calls_after_merge=1'
executed_tool_calls=8 file_read entries (the tool actually executed)
result="Supports tool calls: False"  ← the bug in the summary
```

**Fixture-required caveat:** `_select_code_model()` is patched to return
`(AIModel.MINIMAX, "openclaw", False)`. The F1 bug only manifests when
`supports_native_tools=False`. With Grok (the test-env default,
`supports_native_tools=True`), the buggy line accidentally returned True
for JSON-only responses and the bug did not reproduce. Production uses
MiniMax (`supports_native_tools=False`); the fixture matches that shape.

## Which fixture trips which condition

| Condition (the F1 fault class) | Tripped by |
|---|---|
| Scorer reads `response.function_calls` (None) and ignores parser | `test_raw_json_with_no_native_call_is_scored_as_tool_call` (format 2) and `test_fenced_json_with_no_native_call_is_scored_as_tool_call` (format 3) |
| Two places deciding the same fact (`_request_code_response:423` AND `_execute:757`) | Both bug fixtures trip both — removing either alone is insufficient |
| Parser is correct, scorer is wrong | Bug fixtures fail with parser-found-the-tool but scorer-recorded-False; fixed by reading parser output |
| Negative fixture failing for the wrong reason | `test_prose_with_no_action_is_scored_as_no_tool_call` and `test_malformed_json_no_tool_call_and_raw_text_persisted` PASS on both pre- and post-fix code; they exist to prove the fix does not flip true negatives into false positives |

## Pre-existing failures (do NOT fold into this fix)

`pytest tests/test_code_task_runner_evidence.py ... --deselect test_git_ops...`
reports **9 failed, 25 passed, 1 deselected**. **Same 9 fail on pre-F1 code
(stash-proof at commit `e854621`, before this work)**, so the F1 fix
introduced zero regressions.

The 9 failures are a latent fixture bug in `_patch_runner` at
`tests/test_code_task_runner_evidence.py:38-39`:
```python
lambda tool_call, desk=None: execute_tool_result(tool_call)
```
The production `code_task_runner._execute:868` calls
`execute_tool(t, desk="codeforge", founder=task.founder)`. The lambda
does not accept `founder` and raises `TypeError: got an unexpected
keyword argument 'founder'`. The exception is caught at line 770,
logged as a tool error, and the task reaches ERROR state. Tests that
assert `task.state == CodeTaskState.COMPLETED` then fail.

`founder=` was added to the call site in commit `02a87e6` (Phase 8 —
thread founder authorization). The test fixture has been incompatible
since. **Doctrine rule 7 (stash-proof) satisfied.** The fix for the
fixture is its own item and is **not** in this dispatch — it would
require deciding what `founder` means in the test context (likely `True`
for founder-authorised tasks) and updating the lambda accordingly.

## Found / Changed / Tests / Commit

| File | Δ | Purpose |
|---|---|---|
| `backend/app/services/max/code_task_runner.py` | +18 / -2 (Stage 2) | **F1** — delete the two buggy `supports_tool_calls` assignments, add one in `_execute` after parsing, sourced from the parsed `tool_calls` list |
| `backend/tests/test_code_task_scorer.py` | new (Stage 2) | **F1** — 5 fixtures with real provider shapes; bug fixtures fail pre-fix, all pass post-fix |
| `claude/BACKLOG_UPDATE_2026-08-20.md` | +162 | **H61** + **H62** — pre-Stage-2 prep; unit + PIN-gate findings |
| `~/.config/systemd/user/empire-backend.service` | infra patch (not in repo) | **H61** — `StandardError=journal` added to match the repo unit; daemon-reload + restart confirmed |

**F1 fixtures (5/5 pass post-fix):**
```
tests/test_code_task_scorer.py::test_native_function_call_scored_as_tool_call PASSED
tests/test_code_task_scorer.py::test_raw_json_with_no_native_call_is_scored_as_tool_call PASSED
tests/test_code_task_scorer.py::test_fenced_json_with_no_native_call_is_scored_as_tool_call PASSED
tests/test_code_task_scorer.py::test_prose_with_no_action_is_scored_as_no_tool_call PASSED
tests/test_code_task_scorer.py::test_malformed_json_no_tool_call_and_raw_text_persisted PASSED
```

**Pre-existing failures (unchanged by this work, latent since `02a87e6`):**
```
9 failed, 25 passed, 1 deselected, 218 warnings
```

## Doctrine additions earned

- **One source of truth, set after the merge.** `supports_tool_calls` is
  read from the merged `tool_calls` list (native + parser), not from the
  provider-shaped field. Removing either buggy assignment alone is
  insufficient — both have to go.
- **The test env defaults can hide a bug.** Test env defaults to Grok
  (`supports_native_tools=True`). The F1 bug only manifests with
  `supports_native_tools=False`. A fixture must force the production
  shape, not the test-env default.
- **Stash-proof is not optional.** I reported "29 passed" in Stage 1
  without verifying; the actual count was 20 passed + 9 failed. The
  nine were pre-existing and unrelated to my work, but I should have
  shown the actual output, not a number. **Recorded in this report
  as the doctrine violation, not buried.**

## Stop point

Per dispatch: do not proceed to Stage 3 until the scorer is fixed and
tested. **F1 is fixed and tested. Negative fixtures fail for the right
reason (they don't fail). Bug fixtures fail pre-fix for the right
reason (parser-found, scorer-recorded-False). All 5 fixtures pass
post-fix.**

Awaiting founder eyeball before starting Stage 3 (live proof — submit
one real code task through the actual path; verify file changes on
disk; verify journalctl lines).