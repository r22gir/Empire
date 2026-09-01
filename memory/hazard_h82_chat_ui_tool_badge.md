---
name: H82 — chat UI renders Tool badge per prose tool block, independent of execution success
description: parseToolBlocks() in ChatScreen.tsx renders a "Tool: <name>" badge for every tool block found in the model's streamed prose, with no reference to whether the underlying tool call succeeded. Partial fix for H80 (Mechanism A in D52) catches the SSE tool_result event path; this prose path remains. Separate dispatch.
type: project
---

> **Mirror copy.** A copy of this file exists in the agent home at `~/.claude/projects/-home-rg/memory/hazard_h82_chat_ui_tool_badge.md`. Both copies are the same content as of 2026-09-01; the agent-home copy is the auto-memory system's record, the repo copy is the source of truth for any in-repo tooling. D51 consolidation: H81 / H82 / H83 / H84 / H85 each have an agent-home mirror; pick one of the three locations as authoritative when D51 lands.

# H82 — chat UI renders Tool badge from model prose, success-independent

**Opened:** 2026-09-01 (D52 Phase 4 verification)
**Status:** OPEN — separate dispatch, not D52
**Severity:** MEDIUM — user-visible receipt that implies success on a failed tool call

## Mechanism

`empire-command-center/app/components/screens/ChatScreen.tsx:601-602`:
```typescript
const { cleanContent, toolCalls } = msg.role === 'assistant'
  ? parseToolBlocks(msg.content)
  : { cleanContent: msg.content, toolCalls: [] };
```

`parseToolBlocks(content)` at `ChatScreen.tsx:12-26`:
```typescript
const cleaned = content.replace(/```(?:tool)?\s*\n?\s*(\{[\s\S]*?\})\s*\n?```/g, (_, json) => {
  try {
    const parsed = JSON.parse(json);
    if (parsed.tool) {
      toolCalls.push(parsed);   // ← every tool block in the prose becomes a badge
      return '';                  // remove from visible content
    }
  } catch { }
  return _;
});
```

`toolCalls.map((tc, k) => ...)` at `ChatScreen.tsx:627-668` renders each one as a
generic "Tool: {tc.tool}" badge at line 665.

The tool blocks reach `msg.content` via the SSE `text` events from the backend
stream path (`backend/app/routers/max/router.py:3653`, `:3701`, `:3799`,
`:3805`). These `safe_chunk` values come straight from `ai_router.chat_stream`
and are NOT stripped before yielding. `strip_tool_blocks` is used elsewhere in
the stream path (lines 3793, 3817, 3827, 3896) but only on conversation history
and ledger persistence — never on the `text` SSE events the user receives.

## Why H80's Mechanism A only partly caught this

D52 added `db_query` to `VERIFICATION_REQUIRED_TOOLS` (Mechanism C — load-bearing)
and added `if entry.get("success"):` to the SSE `tool_result` event emission at
`router.py:3753-3754` (Mechanism A — half-fix). The SSE `tool_result` event is
one of two paths the chat UI uses to render a "Tool: <name>" badge. The other
path is `parseToolBlocks(msg.content)`, which is purely client-side and
success-agnostic.

**Result after D52:** A failed round-0 db_query call still produces a
"Tool: db_query" badge in the Command Center chat UI, even though the SSE
`tool_result` event for the same call is correctly suppressed. The badge
arrives via the model's prose, not via the SSE event.

**Observed in founder verification on 2026-09-01:** A round-0 failed db_query
("no such column: customer_name") and a round-1 successful retry both rendered
"Tool: db_query" badges in the chat UI. Two badges total. The miss badge came
from `parseToolBlocks`; the hit badge came from both `parseToolBlocks` AND the
SSE `tool_result` event.

## Why the post-gen backstop does not catch this

D52's Mechanism C gates the response *content* via
`_apply_truth_guardrails` → `runtime_truth_failures` → `_tool_failure_reason`
on db_query failure. This stops fabricated invoice numbers in the model's
prose. It does NOT stop badge emission — badges are a separate UI artifact
rendered from prose structure, not from response content the backstop
inspects.

## Candidate fix — Option α (server-side strip_tool_blocks on streamed text)

Apply `strip_tool_blocks(safe_chunk)` to each `text` SSE event before yielding.
The four yield sites in the stream path:

| line | context |
|---|---|
| 3653 | main chat-stream text chunk from `ai_router.chat_stream` |
| 3701 | tool-block-error recovery text path |
| 3799 | text gap emitted before followup stream |
| 3805 | followup stream text chunks |

After the fix, the frontend's `parseToolBlocks` finds no tool blocks in
`msg.content` and `toolCalls` is empty for the prose path. The only badge
source becomes the SSE `tool_result` event, which Mechanism A already filters
to successes only.

**User-visible content is unchanged** — `parseToolBlocks` was already removing
tool blocks from the display content via the `return '';` line. Stripping
them server-side is a no-op for visible text. It only changes which path
emits the badge.

## Other options (NOT recommended)

**Option β — cross-reference toolCalls against toolResults in the frontend.**
Couples the badge to the SSE event presence. A slow-arriving SSE event would
briefly suppress a legitimate badge.

**Option γ — render tool blocks as a different visual when SSE event missing.**
Most expressive but most work. Frontend gets a refactor; backend changes are
zero. Consider only if Option α has unwanted side-effects.

## Recommendation

Option α. Smallest blast-radius, no frontend coupling, no race condition.
Backend-only change in `router.py`. Survives any future frontend rewrite.

## Rules

- **Do NOT fix in D52.** Per founder directive 2026-09-01, D52 closed db_query
  read access + H80 (round-aware halt + SSE event filter). H82 is its own
  dispatch.
- **Do not weaken Mechanism C.** The `db_query` entry in
  `VERIFICATION_REQUIRED_TOOLS` is load-bearing for H80. Removing it would
  re-open the fabrication path. Any work that touches
  `VERIFICATION_REQUIRED_TOOLS` MUST cite H82 if it removes `db_query`.
- **Same shape as H68 (file-content template detection) and H74 (empty-channel
  default).** Each was about a specific shape that the model emitted which
  bypassed a gate. H82 is about a specific shape (` ```tool ... ``` ` block in
  prose) that the UI renders without verification.