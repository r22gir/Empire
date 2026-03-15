# Session — 2026-03-15 11:40
Source: Claude Code (auto)

It looks like write permissions to `~/.claude-context/` are being blocked. Can you approve the write permission when the prompt comes up? Or you can save it manually — I'll output the summary here and you can run `cctx save` to capture it:

---

**Empire Session Summary 2026-03-15**

**What Was Worked On:**
1. **OpenClaw v2.0.0 restart verified** — full provider chain live (grok -> claude -> groq -> ollama), Grok responding as primary
2. **RecoveryForge Layers 1-2 done** — 69,413 images scanned, deduped to 18,716, presorted (18,472 need AI). LLaVA downloaded (4.7GB). Layer 3 ready to launch.
3. **AI Cost Allocation research** — no multi-tenant strategy exists. Single $50/month global budget. Biggest open question for SaaS pricing.
4. **MAX autonomy audit** — scheduled tasks work, but shell execution and chat-to-task dispatch are disconnected. OpenClaw bridge needs wiring into desks (~2-3hr build).
5. **Launcher identified** — green EmpireLaunch icon is correct. OpenClaw :7878 missing from it, must start manually.

**Next Steps After Reboot:** EmpireLaunch icon -> start OpenClaw manually -> start overnight classify -> continue dev work.

## System State (auto-captured 2026-03-15 11:40)

### Services Running
- :8000 Backend API ✓
- :3077 RecoveryForge ✓
- :7878 OpenClaw ✓
- :11434 Ollama ✓

### Git
- Branch: main
- Last commit: 718222d Auto-save session context 2026-03-14 22:02
- Uncommitted files: 8


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

## Business Names (CORRECT — do not use other names)
- **Empire Workroom** = drapery & upholstery business (NOT "RG's Drapery")
