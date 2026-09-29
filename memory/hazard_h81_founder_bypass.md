---
name: H81 — founder flag bypasses dangerous-tools gate from Command Center
description: is_founder_message() returns True for ANY Command Center channel with no identity check; the chat/stream handlers pass founder=True into execute_tool, which skips the PIN gate entirely on shell_execute and env_set. Effective ungating of the two remaining dangerous tools from web. NOT fixed in D52 per founder directive; separate dispatch.
type: project
---

> **Mirror copy.** A copy of this file exists in the agent home at `~/.claude/projects/-home-rg/memory/hazard_h81_founder_bypass.md`. Both copies are the same content as of 2026-09-01; the agent-home copy is the auto-memory system's record, the repo copy is the source of truth for any in-repo tooling. D51 consolidation: H81 / H82 / H83 / H84 / H85 each have an agent-home mirror; pick one of the three locations as authoritative when D51 lands.

# H81 — founder flag bypasses dangerous-tools gate from Command Center

**Opened:** 2026-08-31 (D52 Phase 0 audit)
**Status:** OPEN — separate dispatch, not D52
**Severity:** HIGH — `shell_execute` and `env_set` are effectively ungated from web

## Mechanism

`backend/app/services/max/guardrails.py:96-118` — `is_founder_message(message_context)`:
```python
if channel in ("web", "web_cc", "cc", "command_center", "command-center"):
    return True
```
Any Command Center channel variant returns True. There is no identity check
(no auth token, no user_id match, no session validation). Telegram requires
`_FOUNDER_CHAT_ID` match — web does not.

## How founder=True flows

Call sites that pass `founder=True` into `execute_tool(...)` (chat + stream + approvals):
- `backend/app/routers/max/router.py:2897` (chat tool loop) — from `founder = is_founder_message(msg_ctx)` at line 2190
- `backend/app/routers/max/router.py:3732` (stream tool loop) — from line 3300
- `backend/app/routers/max/router.py:2985` (chat post-search reroute)
- `backend/app/routers/max/router.py:3616` (stream post-search reroute)
- `backend/app/routers/max/router.py:5300` / `5323` (approval flow)
- `backend/app/services/max/code_task_runner.py:860` / `1046`
- `backend/app/services/max/telegram_bot.py:500`

## Why it matters

`tool_executor.py:459` — the dangerous-tools PIN gate is wrapped in `if founder:`,
so the entire `DANGEROUS_TOOLS` check (`shell_execute`, `env_set`) is skipped for
founder messages. After D52, `db_query` is also ungated, but `db_query` is now
read-only at the connection level (`mode=ro` URI). `shell_execute` and `env_set`
have no such defence.

**Result:** Any caller that can reach the Command Center `/api/v1/max/chat` or
`/api/v1/max/chat/stream` endpoint over the network with `channel="web"` (or any
CC variant) can invoke `shell_execute` and `env_set` without a PIN.

## Why H74 (D45) didn't fix this

H74 (D45, 2026-08-28) closed the empty-channel default that walked past every
privilege gate. It narrowed `is_founder_message` to require a non-empty
channel. It did NOT add identity verification for the web channels — those
still return True unconditionally.

## What the fix would look like (NOT implemented)

A correct fix requires an identity check on the web channel — session cookie,
auth header, or signed token from the Command Center portal. The
`_FOUNDER_CHAT_ID` pattern from Telegram (chat_id match) is the template.
Until that exists, **defence-in-depth options** that don't require new identity:
1. Strip `founder=True` for `shell_execute` / `env_set` specifically — let the
   per-tool access controller + PIN gate run even for founder messages on
   those two tools.
2. Require an env-var passcode on web channels for `shell_execute` / `env_set`
   (mirror FOUNDER_PIN behaviour but web-specific).
3. Audit log every `shell_execute` / `env_set` call to a separate file and
   alert on any non-founder chat_id / session_id source — purely detective.

Option (1) is the smallest blast-radius change.

## Rules

- **Do NOT fix in D52.** Per founder directive, D52 closes db_query read access
  + H80 separately. H81 is its own dispatch.
- **Do not reference H81 as closed in MEMORY.md or CLAUDE.md** until the
  separate dispatch lands and verifies.
- Any new work touching `is_founder_message`, `founder=` kwarg on
  `execute_tool`, or the DANGEROUS_TOOLS PIN gate MUST cite H81.