# EMPIRE SESSION CONTEXT — 2026-03-07
## For Claude Code — Read this before starting work

---

## SYSTEM STATE (as of end of session)

### What's Running on Empire Dell (Dell Precision Tower 5810)
- **Backend API**: :8000 — FastAPI + Uvicorn, Grok primary AI ✓
- **WorkroomForge**: :3001 — Next.js, AI measurement tools ✓
- **LuxeForge**: :3002 — Next.js, designer portal ✓
- **Founder Dashboard**: :3009 — Next.js, MAX command center ✓
- **Telegram Bot**: Running inside backend, @Empire_Max_Bot ✓
- **Memory API**: /api/v1/memory/* — 97 memories ✓
- Start all: `bash ~/empire-repo/start-empire.sh`
- Stop all: `bash ~/empire-repo/stop-empire.sh`

### Venv Location
`~/empire-repo/backend/venv/bin/activate`

### API Keys (.env)
- `~/empire-repo/backend/.env` — XAI_API_KEY ✓, ANTHROPIC_API_KEY ✓, TELEGRAM tokens ✓, BRAVE_API_KEY ❌ (missing)
- `~/empire-repo/founder_dashboard/.env.local` — XAI_API_KEY ✓
- `~/empire-repo/workroomforge/.env.local` — XAI_API_KEY ✓
- `~/empire-repo/luxeforge_web/.env.local` — XAI_API_KEY ✓

---

## ARCHITECTURE — CORRECTED HIERARCHY

### MAX = Founder's Personal AI Assistant (top layer)
- Brain: 97 memories, context-pack loads on session startup
- 12 AI Desks with named personas: Aria (Marketing), Cipher (Finance), Sage (Legal), Sentinel (IT), Echo (Support), Phoenix (Operations), Atlas (Forge), Nova (Analytics), Rex (Commerce), Ora (Content), Nexus (Research), Vanguard (Strategy)
- Tools: web_search (DDG→Brave), quick_quote, photo_to_quote, present, send_telegram, send_email, etc.
- Channels: Dashboard :3009, Telegram, Claude.ai (context bridge), Terminal

### Empire Workroom = RG's Drapery & Upholstery Business (FULL business)
- Built-in: Finance (QuickBooks REPLACEMENT, not integration), CRM, Inventory, Reporting
- Uses Forge modules: WorkroomForge, LuxeForge, ShipForge, SupportForge, MarketForge, EmpireAssist, SocialForge
- Customers: Emily $22.6K, Sarah $12.4K, Maria $8.9K, Pipeline $31.9K
- Vendors: Rowley, Somfy, Lutron, Kirsch
- Going through Zero to Hero pipeline (status TBD next session)

### CraftForge = RG's Woodwork & CNC Business (FULL business — mirror of Workroom)
- Same full features: Finance, CRM, Inventory, Reporting
- Own tools: Text→CNC, Photo→CNC, 3D Scan→CNC, Marketplace
- Supports Workroom: cornices, valances, headboards, cabinet doors
- External customers: woodworkers, makers, sign shops, furniture builders
- STATUS: Full spec exists (CRAFTFORGE_SPEC.md, CRAFTFORGE_SPACESCAN_ADDENDUM.md), ZERO code built
- Also going through Zero to Hero pipeline (status TBD)

### Empire Platform = SaaS Ecosystem (sells Forge modules to subscribers)
- Tiers: Lite $29/mo, Pro $79/mo, Empire $199/mo
- Products: WorkroomForge, CraftForge, ContractorForge, MarketForge, ShipForge, SupportForge, Empire Wallet, MarketF, SocialForge
- All DUAL-USE: RG dogfoods first, then sells to subscribers
- Zero to Hero pipeline: Intake → LLC → Stripe → Social → Tools → Bot → HERO
- Hardware bundles: Budget $349, Seeker $599, Full Empire $899

### SocialForge = CRITICAL for monetization
- Built into Empire Workroom and CraftForge (not standalone)
- Also sold to subscribers on Platform
- Gateway to revenue — no social = no customers finding you
- Was discussed at length in previous sessions — search copilotforge chat archives
- NEXT PRIORITY after system setup

---

## WHAT WAS BUILT/FIXED THIS SESSION (March 7)

### Quote System — Fully Working
- create_quick_quote: 3-tier proposals (Essential/Designer/Premium) ✓
- PDF generation with WeasyPrint (316KB, SVG drawings, cost breakdown) ✓
- Proposal selection (pick A/B/C, finalizes quote) ✓
- Sent to Telegram automatically ✓
- 55+ generated quote PDFs on disk ✓
- Quote numbering: EST-YYYY-NNN ✓

### Quote PDFs Enhanced
- Original customer photo shown inline above each item ✓
- AI mockup images embedded per design proposal ✓
- Upholstery AI analysis auto-populates from photo ✓
- Channeling and nailhead trim rendering in SVG diagrams ✓
- POST /quotes/{id}/photos endpoint for attaching photos ✓

### Measurement System — Fixed
- DB model rewritten for SQLite compat (was PostgreSQL types) ✓
- Calibration: reference object → pixel-to-real conversion ✓
- Calculate: pixel measurements → real inches ✓
- Export: quote/csv/json formats ✓
- All 5 AI vision routes responding (mockup, outline, measure, upholstery, imagine) ✓
- Polycam GLB scan copied from backup drive ✓

### Photo Upload — Fixed
- Root cause: `import pytesseract` in files.py killed the entire files router
- Removed unused import, all file operations work now ✓
- Paperclip attach, clipboard paste, file browser all functional ✓

### Desk Personas — Restored
- All 12 desk persona names committed: Aria, Cipher, Sage, Sentinel, Echo, Phoenix, Atlas, Nova, Rex, Ora, Nexus, Vanguard
- Commit: ae4b39c

### Launch Script — Working
- start-empire.sh starts all 5 services (Backend, Founder Dashboard, Empire App, WorkroomForge, LuxeForge)
- stop-empire.sh cleanly kills by port
- Desktop shortcut exists

### Architecture Map — Corrected
- PDF: Empire_v4_Architecture_FINAL_2026-03-07.pdf (4 pages)
- Shows correct hierarchy: MAX → Two businesses (Workroom + CraftForge) → Platform

### Command Center Redesign — Mockup Complete
- HTML mockup: Empire_Command_Center_Full_Mockup_2026-03-07.html
- Features: 4 business tabs (MAX/Workroom/CraftForge/Platform), lighter theme, drop-down menus, proposal selection cards, video call popup, notification center, Ctrl+K quick switch, client view mode, EN/ES toggle, collapsible ticker bar, active desks with expand

---

## NEXT SESSION PRIORITIES (in order)

1. **Zero to Hero interview** — Where are Empire Workroom and CraftForge in the pipeline? Which steps done?
2. **SocialForge** — Find all specs/discussions, plan MVP, start building. This is the monetization gateway.
3. **Build unified Next.js app** — Replace 4 separate Next.js servers with single app + tab routing (from mockup)
4. **Brave Search API key** — DDG is rate-limited, need reliable web search
5. **Commit quote/PDF enhancements** — May have uncommitted changes from this session
6. **memory_v4.md** — Copy to ~/empire-repo/backend/data/max/memory.md (correct path)
7. **Missing packages** — pip install apscheduler (MAX Scheduler needs it)

---

## GIT STATUS
- Repo: github.com/r22gir/Empire (main branch)
- Latest commits: ae4b39c (desk personas), ebcf869 (measurement fixes), 4226196 (photo upload fix)
- Check for uncommitted changes: `cd ~/empire-repo && git status`

---

## CRITICAL BANS — EMPIRE DELL
1. pkill node — too broad, use pkill -f next-server or fuser -k PORT/tcp
2. Broad pkill -f in scripts — use port-specific kills
3. Max 3 Next.js dev servers simultaneously (currently running 4 with LuxeForge added — monitor RAM)
4. USB external drive for live I/O — backup only

---

## KEY FILE LOCATIONS
- Backend code: ~/empire-repo/backend/app/
- Tool executor (22 tools): ~/empire-repo/backend/app/services/max/tool_executor.py
- AI router: ~/empire-repo/backend/app/services/max/ai_router.py
- System prompt: ~/empire-repo/backend/app/services/max/system_prompt.py
- Desks: ~/empire-repo/backend/app/services/max/desks/
- Memory store: ~/empire-repo/backend/app/services/max/brain/memory_store.py
- Quote router (1874 lines): ~/empire-repo/backend/app/routers/quotes.py
- Telegram bot: ~/empire-repo/backend/app/services/max/telegram_bot.py
- Memory API: ~/empire-repo/backend/app/routers/memory.py
- CraftForge specs: ~/empire-repo/docs/CRAFTFORGE_SPEC.md, ~/empire-repo/docs/CRAFTFORGE_SPACESCAN_ADDENDUM.md
- Data: ~/empire-repo/backend/data/ (brain/, chats/, quotes/, uploads/, logs/, inbox/)
- CLAUDE.md: ~/empire-repo/CLAUDE.md
- VERSION: ~/empire-repo/VERSION (should say 4.0)
