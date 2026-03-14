---
name: empire-core
description: Core knowledge about the Empire ecosystem — repo structure, ports, services, conventions, and safety rules. Always loaded.
version: 1.0.0
metadata:
  openclaw:
    emoji: "🏰"
---

# Empire Core Knowledge

You are MAX's execution agent for the Empire ecosystem. You operate on EmpireDell (Intel Xeon E5-2650 v3, 32GB RAM, 20 cores).

## Critical Safety Rules
- NEVER run `sensors-detect` — crashes EmpireDell
- NEVER use `pkill -f` with broad patterns — caused system crash Feb 24
- NEVER touch GPU config (Quadro K600, nouveau driver, unstable)
- ALWAYS activate venv before Python work: `source ~/empire-repo/backend/venv/bin/activate`
- ALWAYS commit with descriptive messages, push to main branch
- File naming convention: Name_YYYY-MM-DD_HHMM.ext

## Repository Structure
- **Repo**: ~/empire-repo (github.com/r22gir/Empire, main branch)
- **Backend**: ~/empire-repo/backend/app/ (FastAPI, Python 3.12, port 8000)
- **Empire App**: ~/empire-repo/empire-app/ (Next.js, port 3000)
- **Command Center**: ~/empire-repo/empire-command-center/ (Next.js, port 3005)
- **WorkroomForge**: ~/empire-repo/workroomforge/ (port 3001)
- **LuxeForge**: ~/empire-repo/luxeforge_web/ (port 3002)
- **AMP**: ~/empire-repo/amp/ (port 3003)
- **RelistApp**: ~/empire-repo/relistapp/ (port 3007)
- **Founder Dashboard**: ~/empire-repo/founder_dashboard/ (port 3009)
- **OpenClaw**: ~/Empire/openclaw/ (port 7878)
- **Ollama**: localhost:11434
- **Venv**: ~/empire-repo/backend/venv/bin/activate

## Backend Routers
- Costs: backend/app/routers/costs.py
- Vision: backend/app/routers/vision.py
- Finance: backend/app/routers/finance.py
- CRM: backend/app/routers/customer_mgmt.py
- Inventory: backend/app/routers/inventory.py
- Jobs: backend/app/routers/jobs.py
- Social: backend/app/routers/social.py
- Intake auth: backend/app/routers/intake_auth.py

## MAX Services
- AI router: backend/app/services/max/ai_router.py
- Tool executor: backend/app/services/max/tool_executor.py
- Telegram bot: backend/app/services/max/telegram_bot.py
- Desks: backend/app/services/max/desks/
- Memory: backend/app/services/max/brain/memory_store.py
- Token tracker: backend/app/services/max/token_tracker.py
- TTS: backend/app/services/max/tts_service.py

## Public URLs
- https://studio.empirebox.store (Command Center + Intake)
- https://api.empirebox.store (Backend API)

## AI Routing Priority
xAI Grok → Claude → Groq → OpenClaw → Ollama

## Design System
- Warm off-white theme (#f5f3ef), gold accents (#b8960c)
- All buttons 44px+ for tablet
- 4 tabs: MAX (gold) / Workroom (green) / CraftForge (yellow) / Platform (blue)

## When executing tasks:
1. Read the relevant files FIRST before making changes
2. Make minimal, targeted edits — don't rewrite entire files
3. Test after changes (run the dev server, hit the API)
4. Commit with clear message: "fix: description" or "feat: description"
5. Report results back through the gateway
