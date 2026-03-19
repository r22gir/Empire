# MAX Sync Status — Web vs Telegram

**Date:** 2026-03-18
**Purpose:** Document what is shared and what is separate between MAX on the web (Command Center) and MAX on Telegram (@Empire_Max_Bot)
**Overall:** 95% unified. Needs conversation merge and Telegram systemd fix.

---

## Shared vs Separate

| Component | Status | Details |
|-----------|--------|---------|
| AI routing chain | **SHARED** | Same chain: xAI Grok -> Claude -> Groq -> OpenClaw -> Ollama. Both channels use identical fallback logic. |
| Memory store | **SHARED** | Same SQLite database. Memories created on web are visible on Telegram and vice versa. 205 memories total. |
| Tools | **SHARED** | All 37 tools available on both channels. Tool executor is the same code path. |
| Desks | **SHARED** | All 18 desks accessible from both channels. Desk routing (Atlas->Opus, Raven/Phoenix->Sonnet, others->Grok) is identical. |
| System prompt | **SHARED** | Same base system prompt with ecosystem catalog summary. Channel-specific tweaks add Telegram formatting hints (shorter responses, emoji usage) for the bot. |
| Conversation history | **SEPARATE** | Web conversations stored in `founder/` directory. Telegram conversations stored in `telegram/` directory. No cross-channel history visibility. |
| Session context | **SEPARATE** | Web sessions use localStorage + backend `/analysis-sessions/`. Telegram has no session persistence beyond conversation history files. |

---

## Service Status

| Service | Status | Details |
|---------|--------|---------|
| Backend (FastAPI) | **RUNNING** | Port 8000, serves both web and Telegram |
| Command Center (Next.js) | **FAILING** | systemd service in exit-code restart loop. Manual `npm run dev` works. |
| Telegram Bot | **NOT RUNNING** | No systemd service configured. Must be started manually. Bot code exists and works when launched. |
| Cloudflare Tunnel | **RUNNING** | `studio.empirebox.store` -> CC, `api.empirebox.store` -> backend |

---

## What Needs to Happen

### 1. Fix Telegram Bot systemd Service
The bot has no systemd unit file. Create one:
- Service: `empire-telegram-bot.service`
- ExecStart: Python script that runs the Telegram bot polling loop
- Restart: `on-failure`
- After: `empire-backend.service`

### 2. Fix Command Center systemd Service
Currently in a restart loop with exit-code failure. Likely causes:
- Node.js version mismatch
- Missing `node_modules` (needs `npm install`)
- Port 3005 already in use
- Environment variables not loaded

### 3. Merge Conversation History
Both channels should be able to see recent conversation context from the other:
- Option A: Merge into single conversation store with channel tags
- Option B: Keep separate but load last N messages from both channels into context
- Recommendation: Option B is simpler and preserves existing structure

### 4. Telegram Session Persistence
Add session save/restore for Telegram conversations so multi-turn analysis workflows (photo -> measure -> quote) can survive bot restarts.

---

## Unification Checklist

| Item | Done | Notes |
|------|------|-------|
| Shared AI routing | YES | Same code path |
| Shared memory DB | YES | Single SQLite |
| Shared tools | YES | 37 tools, same executor |
| Shared desks | YES | 18 desks, same routing |
| Shared system prompt | YES | Base shared, channel tweaks |
| Conversation merge | NO | Separate directories |
| Telegram systemd | NO | No unit file |
| CC systemd fix | NO | Restart loop |
| Telegram session persistence | NO | No session save |
| Cross-channel notifications | NO | Not started |

**Unification progress: 5/10 items complete (50%)**

The core AI brain is fully shared. What's missing is operational infrastructure (systemd services) and conversation continuity across channels.
