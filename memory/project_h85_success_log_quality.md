---
name: H85 — success=1 does not mean the command succeeded
description: H81 Phase 2B Task A2 step 6 found that _shell_execute logs success=1 whenever subprocess.run returns without raising, regardless of returncode. Row 7934 (now purged) documented the case: curl DNS-fail with returncode 6 recorded as success. The audit row is unreliable as evidence the command did what the founder wanted; success should reflect returncode==0 for subprocess tools.
type: project
---

> **Mirror copy.** A copy of this file exists in the agent home at `~/.claude/projects/-home-rg/memory/project_h85_success_log_quality.md`. Both copies are the same content as of 2026-09-01; the agent-home copy is the auto-memory system's record, the repo copy is the source of truth for any in-repo tooling. D51 consolidation: H81 / H82 / H83 / H84 / H85 each have an agent-home mirror; pick one of the three locations as authoritative when D51 lands.

# H85 — success=1 does not mean the command succeeded

**Opened:** 2026-09-01 (H81 Phase 2B Task A2 finding)
**Status:** BACKLOG — Phase 3 scope, no fix in H81
**Severity:** MEDIUM — audit data is misleading for forensic review; an investigation that relies on `success=1` as "the command worked" will reach wrong conclusions

## Mechanism

`backend/app/services/max/tool_executor.py` — `_shell_execute` handler at line 4544. The success/failure logging branch after `subprocess.run(...)`:

```python
try:
    result = subprocess.run(
        command, shell=True, capture_output=True, text=True,
        timeout=30, cwd=canonical_cwd,
    )
    tr = ToolResult(
        tool="shell_execute", success=True,                     # ← success=True regardless of returncode
        result={
            "stdout": result.stdout[:2000],
            "stderr": result.stderr[:500],
            "returncode": result.returncode,                    # ← returncode stored in body, not reflected in success
        },
    )
    log_execution(
        "shell_execute",
        {"command": command},
        {"returncode": result.returncode, "stdout_len": len(result.stdout), "stderr_len": len(result.stderr)},
        access_level=2, desk=desk, success=True,                # ← audit row records success=1
        channel=params.get("_channel"),
        founder=founder,
    )
```

The `success=True` and the audit row's `success=1` are both set unconditionally after `subprocess.run` completes without raising. A subprocess that exits with non-zero status (returncode != 0) — e.g. curl DNS-fail (returncode 6), grep with no matches (returncode 1), `false` (returncode 1) — is logged as a success.

The only paths that record `success=0` for shell_execute are:
- BLOCKED_PATTERNS match (line 4556-4571)
- Allowlist refusal (line 4573-4592)
- `subprocess.TimeoutExpired` (line 4607-4611)
- Generic `Exception` (line 4614-4622)

A clean `subprocess.run(...)` with non-zero returncode is none of those.

## Live evidence (now purged)

Audit row id=7934 (full record in `reports/2026-09-01_h81_phase2b_task_b_purge.md`, now deleted from the live DB) recorded:

```
tool           = 'shell_execute'
params         = {'command': 'curl https://evil.example'}
result         = {'returncode': 6, 'stdout_len': 0, 'stderr_len': 284}
success        = 1
channel        = 'telegram'
founder        = 0
```

`curl` returned `returncode=6` (DNS resolution failure) but `success=1` was logged because the subprocess did not raise. This row was a side-effect of the Phase 2 Task 1 `pytest` verification suite running `test_correct_PIN_still_works_when_env_set` or similar — the audit row is incidental evidence of the bug, not its cause.

The same bug applies to any tool whose handler treats "no exception" as success — for shell_execute specifically, the fix is `success = (result.returncode == 0)`. Other tools (env_set, etc.) need their own equivalent.

## File:line references

- `backend/app/services/max/tool_executor.py:4544-4600` — `_shell_execute` handler. The bug is at the `success=True` on line 4587-4593 and the `success=True` on line 4638-4644 (in the `log_execution` call).
- `backend/app/services/max/tool_audit.py:67-76` — `log_execution` writes the success column from the `success` kwarg; it does not consult the result body. So the fix has to happen at the call site, not in the audit layer.
- `backend/app/services/max/tool_executor.py:5362-5407` — `_env_set` handler for comparison: success path writes success=1, exception path writes success=0; this one is correctly classified.

## Why it matters

The audit DB is the post-hoc record of "what did MAX do." A forensic question of the shape "did this shell command actually succeed?" cannot be answered by `WHERE success=1` — the predicate includes commands that returned non-zero. Investigators have to read the result column's `returncode` to know. That defeats the purpose of the success column.

This is the audit-side analogue of the "arithmetic gates are not provenance gates" feedback: a passing value proves the chain, not the input. Here a `success=1` proves the subprocess.run completed, not that the command did what the founder wanted.

## What the fix would look like (NOT implemented)

For `_shell_execute`:

```python
tr = ToolResult(
    tool="shell_execute",
    success=(result.returncode == 0),                         # ← changed
    result={ ... },
)
log_execution(
    "shell_execute",
    {...},
    {...},
    access_level=2, desk=desk,
    success=(result.returncode == 0),                         # ← changed
    channel=params.get("_channel"), founder=founder,
)
```

For other subprocess-style tools (none today besides `shell_execute`, but any future ones should follow the same shape), the same fix applies.

## Rules

- **Do not fix in H81 Phase 2.** Phase 3 scope per founder ruling.
- **Do not fix only the audit layer.** The success flag is set by the tool handler and passed in; the audit layer only records what it's told. The fix has to be at the handler.
- Any Phase 3 work touching `_shell_execute`, the audit schema, or any tool handler that wraps `subprocess.run` MUST cite H85 and decide which shape (handler-side success derivation vs audit-layer returncode inspection) fits the audit model.
