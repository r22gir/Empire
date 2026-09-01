---
name: H84 — access control skipped for unresolvable users
description: H81 Phase 2B Task A2 step 1 showed that a non-founder caller with resolve_user() returning None skips the entire access_controller permission block (deny/locked/confirm/pin), because the flow is gated on `if user:`. In production the same path means any caller the controller cannot identify passes through the permission layer untouched and lands on the PIN gate alone. The PIN gate currently catches it; matters in Phase 3 where unidentified callers stop being impossible.
type: project
---

> **Mirror copy.** A copy of this file exists in the agent home at `~/.claude/projects/-home-rg/memory/project_h84_access_control_skip.md`. Both copies are the same content as of 2026-09-01; the agent-home copy is the auto-memory system's record, the repo copy is the source of truth for any in-repo tooling. D51 consolidation: H81 / H82 / H83 / H84 / H85 each have an agent-home mirror; pick one of the three locations as authoritative when D51 lands.

# H84 — access control skipped for unresolvable users

**Opened:** 2026-09-01 (H81 Phase 2B Task A2 finding)
**Status:** BACKLOG — Phase 3 scope, no fix in H81
**Severity:** not active today — the dangerous-tools PIN gate (`FOUNDER_PIN` env var, fail-closed at `tool_executor.py:512`) catches the cases that the access-controller skip would otherwise let through. Becomes relevant in Phase 3 if Phase 3 introduces per-user identity that this path then bypasses silently.

## Mechanism

`backend/app/services/max/tool_executor.py` — the `else:` branch (non-founder) of the access_controller block:

```python
else:
    # Access control check (non-founder users)
    if access_context and access_controller:
        user = access_context.get("user")
        if user:                                  # ← the load-bearing gate
            level = int(access_controller.classify_tool(tool_name))
            action, _ = access_controller.check_permission(user, tool_name, desk)
            if action == "deny":
                ... return ToolResult(success=False, error="Access denied: ...")
            if action == "locked":
                ... return ToolResult(success=False, error="Account locked ...")
            if action == "confirm":
                ... return ToolResult(success=False, error="__ACCESS_PENDING__confirm__...")
            if action == "pin":
                ... return ToolResult(success=False, error="__ACCESS_PENDING__pin__...")
```

When `user` is `None` (because `access_context["user"]` is unset, OR `access_controller.resolve_user(...)` returned `None`), the entire `if user:` block is skipped. The caller passes through to the dangerous-tools PIN gate below (`if tool_name in DANGEROUS_TOOLS:`) without the access_controller having classified them or attached any pending-session machinery.

### How `user` ends up `None`

Two paths:

1. **`access_context` is `None`.** The chat handlers build `_ac_context` only when `access_controller.resolve_user(...)` returns truthy (`router.py:2732-2739`). For founder, `resolve_user("", "web")` returns None today, so `_ac_context = None`. The handler passes `access_context=_ac_context` into `execute_tool`, where `access_context and access_controller:` is False, and the entire permission flow is skipped.

2. **`access_context` is set but `user` is falsy.** Would require `access_context.get("user")` to return None or {} — possible in tests, possible if a future code path builds access_context without a user.

In the live chat path, founder calls hit path (1) — and that is the post-Task-1 intent (founder skips permission flow). The dangerous-tools PIN gate then runs uniformly for founder as well.

The H84 concern: any non-founder caller the controller cannot identify lands on the dangerous-tools PIN gate *with whatever access_context was passed in*. If access_context has a matching `pin`, the dangerous-tools gate approves. The access_controller's role-based permission decisions (deny / locked / confirm) are entirely bypassed.

## File:line references

- `backend/app/services/max/tool_executor.py:470-472` — the `if user:` gate that skips permission flow
- `backend/app/routers/max/router.py:2732-2739` — chat handler's `_ac_context = None` path when `resolve_user` returns None
- `backend/app/services/max/access_control.py:114-126` — `resolve_user` returns `dict_row(row)` which is `None` when the row is missing
- `backend/app/routers/max/router.py:2742-2756` — chat handler's `_extracted_pin` extraction from the body (the body-supplied PIN path that becomes access_context["pin"])

## Why it matters

Today the dangerous-tools PIN gate (`FOUNDER_PIN` env var) catches anything that gets past this skip — non-founder dangerous-tool calls with no PIN refuse; founder dangerous-tool calls also require PIN after H81 Phase 2 Task 1. So H84 is not an active hole.

In Phase 3, when per-user identity becomes load-bearing for chat-endpoint authorization, the silent skip becomes load-bearing in the wrong direction: a caller the controller cannot identify would land on the dangerous-tools gate without ever being classified. If the per-user gate's classification is what Phase 3 introduces, then H84 is exactly the bypass it would have to close.

## What the fix would look like (NOT implemented)

Either:
- Make `if user:` raise / log-and-default-deny when `access_context` is provided but `user` is missing.
- Treat `user is None` as a deny in `access_controller.check_permission` itself (so the gate is always classified, never silently skipped).
- Or invert the structure so the access-controller block always runs and only the permission *outcome* depends on identity.

Phase 3 design decides which shape fits the credential chosen.

## Rules

- **Do not fix in H81 Phase 2.** Phase 3 scope per founder ruling.
- **Do not remove the `if user:` gate as a workaround.** The gate correctly handles path (1) for founder today. Removing it would force all callers through a permission flow that doesn't apply.
- Any Phase 3 work touching `access_controller`, `resolve_user`, or the access-context construction in chat handlers MUST cite H84 and decide whether path (1) stays as the founder-skip or becomes a deny.
