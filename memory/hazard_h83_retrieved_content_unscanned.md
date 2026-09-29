---
name: H83 — retrieved content never scanned by check_input
description: check_input is called on the current message and on chat history, but is NEVER called on tool results returned to the model in this turn, on file contents read mid-turn, on fetched web content, or on the system-prompt envelope. The injection detector has never examined retrieved content — not for founder, not for anyone. Independent of the founder skip H81 Phase 2 Task 3 addressed.
type: project
---

> **Mirror copy.** A copy of this file exists in the agent home at `~/.claude/projects/-home-rg/memory/hazard_h83_retrieved_content_unscanned.md`. Both copies are the same content as of 2026-09-01; the agent-home copy is the auto-memory system's record, the repo copy is the source of truth for any in-repo tooling. D51 consolidation: H81 / H82 / H83 / H84 / H85 each have an agent-home mirror; pick one of the three locations as authoritative when D51 lands.

# H83 — retrieved content never scanned by check_input

**Opened:** 2026-09-01 (H81 Phase 2B Task 0b finding)
**Status:** OPEN — folded into Phase 3 scope per founder ruling
**Severity:** founder rules — backlog item, no separate severity assignment

## Mechanism

`check_input(text, message_context)` in `backend/app/services/max/guardrails.py:140` runs the prompt-injection and blocked-topic pattern scans. It is called from exactly four sites, all in `backend/app/routers/max/router.py`:

| file:line | Caller | What it passes | Founder impact |
|---|---|---|---|
| `router.py:2267` | `/chat` handler | `check_input(request.message, message_context=msg_ctx)` — current message | Founder path triggers; pre-Task-3 the founder skip ran silently here |
| `router.py:2283` | `/chat` history iteration (`for msg in request.history[-3:]`) | `check_input(content)` (no `message_context`) — defaults to `{}` → channel="" → anonymous per H74 | History always scanned as non-founder regardless of caller |
| `router.py:3316` | `/chat/stream` handler | `check_input(request.message, message_context=msg_ctx)` — current message | Founder path triggers (body-supplied channel) |
| `router.py:3337` | `/chat/stream` history iteration | `check_input(content)` — same shape as 2283 | Same as 2283 |

**What `check_input` is NOT called on:**

- Tool results returned to the model in this turn — `file_read`, `db_query`, `web_search`, `web_read`, `search_conversations`, `search_quotes`, `search_contacts` and similar all return tool-result payloads that are passed back to the model as part of the next prompt, but `check_input` is never invoked on those payloads.
- File contents fetched mid-turn (anything the model reads via `file_read` is added to context but never scanned).
- Fetched web content (`web_search` results, `web_read` output) — same.
- Anything in the system-prompt envelope (the system prompt itself, role directives, the prompt-channel directive).
- Anything in the chat history outside the most-recent three messages — `for msg in request.history[-3:]` only scans the tail.

**The H81 Phase 2 Task 3 fix** (which made the founder skip log + scan instead of silently skipping) only changed behaviour for the four call sites above. Retrieved content was never scanned before Task 3 and remains unscanned after Task 3. The Task 3 fix narrowed the founder skip; H83 is independent of that.

## Why it matters

A model that returns tool results to itself in a loop, or that gets fed retrieved content from an external source (file, URL, DB row), can be steered by content that never went through the injection pattern checks. The current scan shape protects the user-input boundary (the chat message) but not the model's perception boundary (what the model sees).

## What the fix would look like (NOT implemented)

A scan at the tool-result surface — each tool handler that returns content to the model would call `check_input` on its own output before returning. This adds a scan on every tool result, which is expensive (every tool handler invocation), and may also double-scan content already in history. A targeted alternative is to scan only the content the model sees for the first time in a given turn — i.e. right before the next model invocation, scan the delta. Either shape is a Phase 3 design decision.

## Rules

- **Do NOT fix in H81 Phase 2.** The Task 3 fix (always scan + log founder input) is the only Phase 2 change. H83 is folded into Phase 3 proper.
- **Do not weaken check_input** as a workaround. Removing or softening the existing scans would make H83 worse.
- Any Phase 3 work that adds tool-result scanning MUST cite H83 and must answer the "what counts as retrieved content" question before scoping — the four-file:line call sites in this hazard file are the floor of what H83 covers; the ceiling is open until scoped.
