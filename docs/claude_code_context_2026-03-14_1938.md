# Session — 2026-03-14 19:38
Source: Claude Code (auto)

It looks like I need file write permission for `intake_auth.py`. Could you approve the write permission when prompted? I'm fixing two bugs:

1. **`intake_auth.py`** — Room key `room_name` → `name` (matches what `_build_rooms_html` expects), `treatment_type` → `treatmentType`, and generates `line_items` from room data instead of passing empty `[]`
2. **`quotes.py:1409`** — `room["name"]` → `room.get("name", "Room")` for defensive safety

Both fixes are minimal and targeted at the two E2E test failures (empty quote + PDF KeyError crash).

## System State (auto-captured 2026-03-14 19:38)

### Services Running
- :8000 Backend API ✓
- :3077 RecoveryForge ✓
- :7878 OpenClaw ✓
- :11434 Ollama ✓

### Git
- Branch: main
- Last commit: 9176793 Phase 1: Stripe payments, email templates, pricing page, crypto invoices, rate limiting
- Uncommitted files: 5


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
