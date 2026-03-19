# Session — 2026-03-19 17:12
Source: git log fallback

## Recent Commits (last 2 hours)
7f8fbb7 CraftForge PDF: only show sections with data
4524c7a CraftForge: open existing quotes for viewing/editing

## System State (auto-captured 2026-03-19 17:12)

### Services Running
- :8000 Backend API ✓
- :3005 Command Center ✓
- :3077 RecoveryForge ✓
- :7878 OpenClaw ✓

### Git
- Branch: main
- Last commit: 7f8fbb7 CraftForge PDF: only show sections with data
- Uncommitted files: 2


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
