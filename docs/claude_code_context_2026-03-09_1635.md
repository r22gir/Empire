# Session — 2026-03-09 16:35
Source: Claude Code auto-memory

# Session Summary — 2026-03-06

## What We Worked On

Continued a large migration/cleanup effort for the Empire platform, picking up from a prior session that ran out of context.

### 1. ~/Empire/ → ~/empire-repo/ Path Migration (Completed)
Fixed all 25+ Python files in the backend that still referenced the old `~/Empire/` paths. Every `.py` file now points to `~/empire-repo/`.

**Files fixed:** tool_executor.py, inbox.py, quote_requests.py, quotes.py, telegram_bot.py, system_prompt.py, monitor.py, scheduler.py, token_tracker.py, ai_router.py, files.py, router.py (max), network_monitor.py, forge_desk.py, it_desk.py, run_telegram_bot.py, run_desk_tasks.py, seed_desk_tasks.py

### 2. Git Data Cleanup (Completed)
- Removed 209 runtime data files from git tracking (`git rm --cached`)
- Files kept on disk, excluded via `.gitignore` (`data/`, `backend/data/`, `*.db`)

### 3. presentation_builder.py Search Fix (Completed)
- Replaced `duckduckgo_search` library with httpx DDG HTML endpoint + Brave API fallback
- Matches the same pattern used in `tool_executor.py`

### 4. Launch Scripts (Created & Fixed)
- **`~/empire-repo/start-empire.sh`** — One-command launcher for all 4 services
  - Uses `venv/bin/python3` directly (not system python)
  - Uses `fuser -k PORT/tcp` for port kills (not broad pkill)
  - Auto-runs `npm install` if `node_modules` missing
  - Uses `npx next dev` for local binary resolution
  - 40s timeout, logs per service, opens browser tabs
- **`~/empire-repo/stop-empire.sh`** — Clean shutdown by port
- **`~/Desktop/Empire.desktop`** — Desktop shortcut

### 5. WorkroomForge .env.local (Created)
- AI photo analysis was failing: "XAI_API_KEY not configured"
- Root cause: WorkroomForge had no `.env.local`
- Created with XAI_API_KEY + NEXT_PUBLIC_API_URL (not committed, gitignored)

### 6. Forge Product Audit (Research Only)
- CraftForge: 2 detailed spec docs, zero code
- 18+ Forge product names catalogued

## Git Commits
1. `05a895b` — Remove tracked data files, .gitignore, fix all ~/Empire/ paths (228 files)
2. `f09aa89` — Fix presentation_builder.py search
3. `544ef93` — Fix launch scripts

## Current State
- All 4 services running and verified
- Zero ~/Empire/ path references remain in backend Python
- Launch/stop scripts working

## What Should Be Done Next
1. **BRAVE_API_KEY** — Blank in `backend/.env`
2. **OPENAI_API_KEY** — Blank in `backend/.env` (needed for TTS)
3. **Hardware info in system_prompt.py** — Still says Beelink/Ryzen, should say EmpireDell/Xeon
4. **Photo upload UX** — Upload buttons in AI Mockup Studio below fold
5. **Git remote URL** — Update to `https://github.com/r22gir/Empire.git`
6. **CraftForge** — Full specs ready, no code yet

## System State (auto-captured 2026-03-09 16:35)

### Services Running
- :8000 Backend API ✓
- :3000 Empire App ✓
- :3001 WorkroomForge ✓
- :3002 LuxeForge ✓
- :3009 Founder Dashboard ✓
- :3077 RecoveryForge ✓
- :11434 Ollama ✓

### Git
- Branch: main
- Last commit: 4a06024 Marathon session complete: Command Center, QB 6 phases, RelistApp, Quote Verification System, AI Cost Tracker, SocialForge, intake portal, desk autonomy, TTS, vision, inpainting, AMP, Cloudflare tunnel, RecoveryForge, context bridge
- Uncommitted files: 0


## Claude Code Memory Snapshot

# Empire Project Memory

## Overview
Empire (EmpireBox v4.0) is a comprehensive AI-powered business automation platform created by user "rg" (GitHub: r22gir/empire). Private repo, 7700+ files, 110 files changed in v4.0 marathon session.

## Origin
Idea inspired by Alex Finn (AI YouTuber) who demos OpenClaw + Ollama + Claude API on a Mac Mini. The founder adapted the concept starting on a Beelink EQR5 as the "Founders Unit."

## Hardware
- **EmpireDell** (primary dev machine): Intel Xeon E5-2650 v3, 32GB RAM, 20 cores, Quadro K600 (nouveau driver — unstable)
- **Beelink EQR5** (retired): data migrated to EmpireDell

## Key Architecture
- Backend: FastAPI (Python 3.12), port 8000
- AI routing: xAI Grok → Claude → Groq → OpenClaw → Ollama
- MAX: 12 AI desks + costs desk, 22+ tools, 205 memories, autonomous scheduler
- Command Center: ~/empire-repo/empire-command-center/ (port 3005, NEW unified Next.js)
- Founder Dashboard: ~/empire-repo/founder_dashboard/ (port 3009, legacy)
- Token tracker: auto-logs ALL AI calls, /api/v1/costs/* (11 endpoints)
- Telegram bot: @Empire_Max_Bot with auto-measure + auto-voice (Grok TTS Rex)
- Cloudflare Tunnel: studio.empirebox.store, api.empirebox.store

## Ecosystem Products
See: memory/empire-ecosystem.md

## Key Paths & Ports
See full port registry: ~/empire-repo/docs/PORT_REGISTRY.md
- Repo: ~/empire-repo (github.com/r22gir/Empire, main branch)
- Backend: ~/empire-repo/backend/app/ (port 8000)
- Command Center: ~/empire-repo/empire-command-center/ (port 3005)
- Empire App: ~/empire-repo/empire-app/ (port 3000)
- WorkroomForge: ~/empire-repo/workroomforge/ (port 3001)
- LuxeForge: ~/empire-repo/luxeforge_web/ (port 3002)
- AMP: ~/empire-repo/amp/ (port 3003)
- RelistApp: ~/empire-repo/relistapp/ (port 3007)
- Founder Dashboard: ~/empire-repo/founder_dashboard/ (port 3009)
- OpenClaw: ~/Empire/openclaw/ (port 7878)
- Ollama: localhost:11434
- Port 3006: RESERVED (CC dev overflow, do not use)
- Venv: ~/empire-repo/backend/venv/bin/activate

## Context Bridge Tools
- `claude-start` — builds master context + launches Claude Code
- `claude-end` — auto-summarizes + saves context (supports --web for browser sessions)
- `cctx` — full context manager (prompt, save, note, status, history, reset, launch)
- Storage: ~/.claude-context/ (project_brief, last_summary, sessions/, notes)
- Session report PDF: ~/empire-repo/docs/Empire_Session_Report_2026-03-08_0400.pdf

## API Keys (backend/.env)
XAI ✓, ANTHROPIC ✓, TELEGRAM ✓, STABILITY ✓, GROQ ✗ (empty), BRAVE ✗ (missing)
