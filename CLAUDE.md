# CLAUDE CODE — READ THIS FIRST

## Active Session: OpenClaw Autonomous Dev Engine (2026-03-30)
Check progress: cat ~/empire-repo/.claude-progress.md
Resume from the next unchecked block. Do NOT redo completed work.

## Project Essentials
- Backend: FastAPI at ~/empire-repo/backend/app/ (port 8000)
- Frontend: Next.js at ~/empire-repo/empire-command-center/ (port 3005) — NO src/ directory
- Database: ~/empire-repo/backend/data/empire.db
- OpenClaw: port 7878, bridge at /api/v1/openclaw/
- Full context: ~/.claude-context/
- Owner monitoring from PHONE via studio.empirebox.store + Telegram

## OpenClaw Architecture (already working)
- OpenClaw running on :7878 with 32 skills
- Bridge: ~/empire-repo/backend/app/routers/openclaw_bridge.py
- Tool: dispatch_to_openclaw in tool_executor.py
- Skills: ~/.openclaw/workspace/skills/ (empire-core, empire-backend, empire-frontend, empire-social, empire-git)
- Config: ~/.openclaw/openclaw.json (Claude Sonnet + Ollama fallback)
- Endpoint: /chat (NOT /v1/chat/completions)
- Timeout: 300s

## Rules
- Commit + push after every block
- Update .claude-progress.md after every task
- Telegram update to founder after every block
- Never crash the system — test before commit
- One service restart at a time
- Accuracy over speed
