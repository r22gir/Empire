# MAX Reality Check — 2026-03-22

## Test 1: Telegram Bot Status
- **Status:** CONFIGURED (token + chat_id present)
- **Issue:** Conflict error when running multi-worker uvicorn — multiple polling loops started
- **Current:** Running single worker, bot configured but polling conflict needs guard
- **Verdict:** PARTIAL — needs single-instance guard for multi-worker deployment

## Test 2: Web MAX Blocking
- **Test:** `POST /api/v1/max/chat {"message":"ping"}`
- **Result:** Response in ~7s, returns "pong"
- **Model:** claude-sonnet-4-6 (fallback_used: true)
- **Streaming:** `POST /api/v1/max/chat/stream` works, SSE format correct
- **Verdict:** PASS — responds, does not block. Could be faster.

## Test 3: Code Mode
- **Test:** `POST /api/v1/max/code-task` with file read task
- **Result:** Task enters "running" state, reads files successfully
- **Issue:** Blocked on `shell_execute` (security guard working as intended)
- **Issue:** Blocked on `get_services_health`, `get_desk_status` (tools not in allowed list)
- **Verdict:** PARTIAL — works for safe tasks, security guards functional

## Test 4: Cross-channel Memory
- **Test:** `GET /api/v1/chats/cross-channel`
- **Result:** 200 OK, returns cross-channel conversation data
- **Verdict:** PASS

## Test 5: Tool Execution
- **CRM Lookup:** `GET /api/v1/customers/` → 200 OK (with trailing slash)
- **Quote List:** `GET /api/v1/quotes` → 200 OK, returns quotes with full details
- **Service Health:** `GET /api/v1/max/health` → 200 OK, 17 desks online
- **File Read:** Code Mode can read files
- **Memory Search:** `GET /api/v1/chats/cross-channel/search` → 200 OK
- **Verdict:** PASS — 5/5 core tools working

## Test 6: Model Tiering
- **Primary Expected:** xAI Grok (XAI_API_KEY present, 85 chars)
- **Actual:** claude-sonnet-4-6 with `fallback_used: true`
- **Analysis:** Grok is failing silently and falling back to Claude Sonnet
- **GOOGLE_GEMINI_API_KEY:** Missing from .env (needed for Gemini tier)
- **Verdict:** FAIL — Grok not working as primary, falling back to Claude

## Summary

| Test | Result |
|------|--------|
| Telegram Bot | PARTIAL |
| Web MAX Blocking | PASS |
| Code Mode | PARTIAL |
| Cross-channel Memory | PASS |
| Tool Execution | PASS |
| Model Tiering | FAIL |

**Overall: 3 PASS, 2 PARTIAL, 1 FAIL**

## Fixes Applied This Session
1. STT silent catch → now logs errors with `console.warn`
2. Jobs trailing slash bug → added `@router.get("")` decorators
3. Quote PDF decorator → moved from `_discount_html` to `generate_pdf`
4. Quote PDF `Path` import → added `from pathlib import Path`
5. Database backup created: `empire_backup_prelaunch_20260322.db`

## Fixes Still Needed
1. **Grok API:** Investigate why XAI_API_KEY fails silently (key may be invalid/expired)
2. **Telegram guard:** Add single-instance lock for bot polling in multi-worker mode
3. **GOOGLE_GEMINI_API_KEY:** Owner must provide
4. **Code Mode tools:** Add `get_services_health` and `get_desk_status` to allowed tool list
