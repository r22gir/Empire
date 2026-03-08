# EMPIRE SESSION CONTEXT — 2026-03-07 (FINAL · 11:55 PM)
## For Claude Code — Read this FIRST before any work

---

## SYSTEM STATE

### Empire Dell (Dell Precision Tower 5810)
- CPU: Xeon E5-2650 v3 (10c/20t @ 2.30GHz)
- RAM: 32GB · Swap: 8GB · Disk: 92GB SSD (64GB free)
- GPU: Nvidia Quadro K600 (1GB, compute 3.0) — uses nouveau driver (UNSTABLE)
- OS: Ubuntu 24.04.4 LTS

### GPU Crash (Mar 7 00:58)
- Root cause: Nouveau GPU driver PTE fault → gnome-shell crash → forced reboot
- NOT OOM, NOT kernel panic, NOT apt updates
- Fix pending: `sudo ubuntu-drivers autoinstall` (proprietary nvidia driver) — do later
- Resolution was messed up after crash, fixed on second reboot

### Services Running
- Backend :8000, WorkroomForge :3001, LuxeForge :3002, Founder Dashboard :3009
- Telegram Bot running inside backend (@Empire_Max_Bot)
- Start all: `bash ~/empire-repo/start-empire.sh`
- Stop all: `bash ~/empire-repo/stop-empire.sh`
- Venv: `~/empire-repo/backend/venv/bin/activate`

### API Keys (backend/.env)
- XAI_API_KEY ✓ (Grok chat + vision + TTS)
- ANTHROPIC_API_KEY ✓
- TELEGRAM_BOT_TOKEN ✓ + TELEGRAM_FOUNDER_CHAT_ID ✓
- STABILITY_API_KEY ✓ (just added)
- BRAVE_API_KEY ❌ (still missing)

### Git
- Repo: github.com/r22gir/Empire (main branch)
- Auth token EXPIRED — need new PAT from github.com/settings/tokens
- Then: `git remote set-url origin https://NEW_TOKEN@github.com/r22gir/Empire.git`
- Multiple uncommitted changes pending

---

## ARCHITECTURE — CORRECTED HIERARCHY

### MAX = Founder's Personal AI Assistant (GOD VIEW)
- Sees ALL data across businesses when in MAX tab
- 12 AI Desks: Aria (Marketing), Cipher (Finance), Sage (Legal), Sentinel (IT), Echo (Support), Phoenix (Operations), Atlas (Forge), Nova (Analytics), Rex (Commerce), Ora (Content), Nexus (Research), Vanguard (Strategy)
- 22 tools, 97 memories, context-pack on startup

### Empire Workroom = RG's Drapery & Upholstery Business (FULL)
- Built-in: Finance (QuickBooks REPLACEMENT), CRM, Inventory, Reporting
- Uses: WorkroomForge, LuxeForge, ShipForge, SupportForge, MarketForge, EmpireAssist, SocialForge
- Customers: Emily $22.6K, Sarah $12.4K, Maria $8.9K · Pipeline $31.9K
- Going through Zero to Hero pipeline (status TBD)

### CraftForge = RG's Woodwork & CNC Business (FULL — mirror of Workroom)
- Same full features: Finance, CRM, Inventory, Reporting
- Own tools: Text→CNC, Photo→CNC, 3D Scan→CNC, Marketplace
- STATUS: Full spec exists, ZERO code built
- Also going through Zero to Hero pipeline (status TBD)

### Empire Platform = SaaS Ecosystem
- Tiers: Lite $29, Pro $79, Empire $199
- All Forge products are DUAL-USE: RG dogfoods first, sells to subscribers

---

## WHAT WAS BUILT/FIXED THIS SESSION

### Vision Router (NEW — 514 lines)
- backend/app/routers/vision.py
- 7 endpoints: /measure, /outline, /upholstery, /mockup, /imagine, /images/{filename}, /measurements-pdf
- Wired into main.py

### Grok TTS — Rex Voice (NEW — LIVE)
- Replaced edge-tts (Microsoft) with xAI Grok TTS API
- Voice: Rex (confident, professional, bilingual EN/ES)
- Endpoint: POST https://api.x.ai/v1/tts with voice_id "rex"
- Tested: 92KB MP3 generated, works on Telegram
- Dashboard endpoint: /api/v1/max/tts returns MP3
- Available voices: Ara, Rex, Sal, Eve, Leo · $0.05/min · 100+ languages

### Telegram Enhancements
- Auto-measure: photo upload calls /vision/measure FIRST, injects dimensions into MAX
- Auto-voice: every reply sends voice note via Grok TTS Rex

### Quote PDF Fixes
- Treatment type enforcement: MAX no longer defaults to ripplefold
- Fabric color in line items: "Fabric — Designer Grade in Navy Blue (8.2 yds)"
- Mockup colors from customer request (not hardcoded)
- Selected proposal shows only chosen option + real totals (not range)
- Duplicate photo fix (site photo vs current-before)

### Measurement System
- Fixed SQLite compat (PostgreSQL types → SQLite)
- LuxeForge calibration endpoints working
- Polycam GLB scan imported from backup drive

### Other
- Launch script works (all 5 services)
- Desk personas restored (12 names)
- Photo upload fixed (pytesseract import removed)
- Architecture PDF created (4 pages, corrected hierarchy)

---

## MEASUREMENT TOOLS AUDIT — 9 EXIST, ONLY 1 USED IN PIPELINE

| Tool | Location | Method | Used? |
|------|----------|--------|-------|
| Vision /measure | vision.py | xAI Grok AI estimation | YES — Telegram |
| Vision /outline | vision.py | xAI Grok install plan | DEFINED, NOT CALLED |
| Vision /upholstery | vision.py | xAI Grok furniture analysis | YES — upholstery |
| WorkroomForge /api/measure | workroomforge API | xAI Grok (duplicate) | WorkroomForge UI only |
| WorkroomForge /api/outline | workroomforge API | xAI Grok install plan | NOT called |
| LuxeForge /calibrate+/calculate | luxeforge_measurements.py | Manual pixel calibration | DISCONNECTED from quotes |
| 3D Viewer | Viewer3D.tsx | Three.js point-to-point on GLB | Dashboard only |
| ContractorForge | photo_measurement.py | OpenCV + MiDaS depth | COMPLETELY UNUSED |
| Vision /measurements-pdf | vision.py | WeasyPrint export | 3D viewer export only |

**Key problem:** Everything relies on Grok AI estimation (least accurate). LuxeForge pixel calibration (most accurate) is disconnected. Need to chain: Grok estimate → auto-calibrate with reference objects → refined measurements.

---

## QUOTE PDF ISSUES (from EST-2026-016 review)

1. **Measurements off** — 48x60 for a ~32x50 window. Vision tools not calibrating properly.
2. **AI mockups wrong** — Show curtain rods on roman shades. Generate new rooms instead of editing customer photo.
3. **$0.00 on page 1** — Summary table shows $0 when design_proposals exist.
4. **Duplicate photo** — Same image on page 2 (site photo) and page 3 (current-before).
5. **Fabric color not in SVG** — Window drawings don't use fabricColor for fill (upholstery does).
6. **Mockup images generic** — Don't use customer's actual photo as base, don't apply correct colors per tier.

---

## INPAINTING PLAN — Pixazo (FREE) + Stability AI (FREE under $1M)

### Smart Cost Router (shows cost on YOUR screen, NOT on client PDF)
1. **Pixazo FREE API** → try first (completely free, SD inpainting)
2. **Stability AI** → fallback (free under $1M revenue via Community License)
3. **Grok image gen** → last resort (generates new room, doesn't use customer photo)

### How It Works
- Customer photo → Grok Vision identifies window/furniture bounding box → PIL renders mask
- Mask + customer photo → Pixazo/Stability inpainting → 3 tier-specific mockups
- Each tier gets a specific prompt (treatment type + fabric color + tier quality level)
- Works for BOTH windows AND furniture/upholstery
- Empire Command Center shows: "Generated via: Pixazo (FREE)" — client never sees this

### Implementation (Claude Code plan ready, not yet coded)
- New file: backend/app/services/max/inpaint_service.py
- Modify: tool_executor.py (replace grok-imagine-image calls)
- Fallback chain: Pixazo → Stability → Grok
- Parallel execution for speed (asyncio.gather for 6 images)

---

## UI REDESIGN — ALL DECISIONS FINALIZED

### Single Next.js App (replaces 4 separate servers)

### 4 Business Tabs
1. **MAX** (gold) — GOD VIEW, sees all data, personal conversations
2. **Empire Workroom** (green) — FILTERED, only Workroom data/chats/inbox
3. **CraftForge** (yellow) — FILTERED, only CraftForge data/chats/inbox
4. **Empire Platform** (blue) — FILTERED, only Platform data

### Key Design Rules
- Conversations: one MAX brain, messages tagged by business, filtered per tab
- **Notifications** (🔔 global): Real-time alerts grouped by business, visible from any tab
- **Inbox** (per business tab): Action items specific to that business
- Center canvas: 6 modes (Chat, Quote Review, Document, Research, Video Call, Dashboard)
- Global sidebar: Chat, Dashboard, Desks, Inbox, Files, Search, Voice, Settings
- Business sidebar (inside tabs): Quotes, Customers, Inventory, Finance, Shipping, AI Tools, SocialForge, Support, Reports
- Inventory/Customers/Finance are NOT standalone — live inside business tabs
- Touch-friendly: all buttons min 40-44px for tablet
- Lighter warm theme (#f5f3ef background, white panels, gold accents)
- Ctrl+K quick switch, EN/ES toggle, Client View mode, collapsible ticker bar
- Video call popup with doc sharing
- Active desks: show top 6, expand for all 12
- Inpainting cost shown on YOUR screen, never on client quotes

### Voice
- Dashboard mic: voice message to MAX (STT)
- Grok TTS Rex: audio responses on dashboard + Telegram voice notes
- $0.05/min, 100+ languages, 5 voices

### Mockup Files
- `Empire_Command_Center_v3_MultiScreen_2026-03-07.html` — CURRENT (6 screen modes, tab switching, filtered conversations, notification center)

---

## LUXEFORGE — CORRECTED DEFINITION

**NOT a marketing page.** It's a client/designer intake portal.

### LuxeForge FREE (Client version):
- Dumb intake form — NO AI on their end
- Upload photos (camera or gallery)
- Upload 3D scans (Polycam, GLB, OBJ)
- Input measurements manually
- Submit quote requests with notes
- View quote status + PDF proposals
- Approve/select proposal (A/B/C)
- Schedule installation
- Message workroom directly
- View project history
- Make payments/deposits
- NO measurement analysis disclosed to them
- NO AI tools — just data input that feeds Empire Workroom
- Cost to us: $0 (no AI calls)

### LuxeForge PAID (Designer version):
- Everything in free PLUS:
- AI measurement tools
- 3D viewer with measurement overlay
- Project management
- Client management
- Design tools
- Designers pay for the power tools

### Business Model:
```
Client (FREE) → uploads photos/data → feeds workroom (costs us $0)
Designer (PAID) → AI tools + project mgmt → feeds workroom qualified leads
Workroom (PAID) → full business operation (Empire Workroom / WorkroomForge)
```
Free tier is the funnel — captures data at zero cost. AI only runs on the workroom side.
- Built into Empire Workroom + CraftForge (not standalone)
- Also sold to subscribers
- Gateway to revenue — next priority after system fixes
- Was discussed at length in previous sessions — search copilotforge archives
- Both businesses going through Zero to Hero pipeline

---

## NEXT SESSION PRIORITIES (in order)

1. **Fix git push** — New PAT token from GitHub, update remote URL
2. **Commit everything** — Vision router, TTS, PDF fixes, all uncommitted changes
3. **Paste inpaint prompt into Claude Code** — File: claude_code_inpaint_prompt_2026-03-08_0015.md
4. **Fix quote PDF bugs** — $0.00, duplicate photo, fabric color SVG, measurement accuracy
5. **Chain measurement tools** — Grok estimate → LuxeForge calibration → refined dims
6. **Build unified Next.js app** — Single app, 4 tabs, keep backend, rebuild UI layer only
7. **Empire Workroom page** — QB-style dashboard with all 8 daily tools wired to real APIs
8. **Zero to Hero interview** — Where are both businesses in the pipeline?
9. **SocialForge** — Find specs, plan MVP
10. **Brave Search API key** — DDG rate-limited
11. **GPU driver fix** — `sudo ubuntu-drivers autoinstall` when convenient

---

## INPAINTING DECISIONS

### Smart Cost Router (YOUR screen only, never on client PDF)
1. **Pixazo FREE API** → try first (completely free SD inpainting)
2. **Stability AI** → fallback (free under $1M revenue Community License)
3. **Grok image gen** → last resort (generates new room, no inpainting)

### Each Tier Shows BOTH:
- Inpainted customer photo ("Your Room" — treatment overlaid on actual photo)
- Clean professional mockup ("Inspiration" — aspirational magazine-style image)

### Style Selector ACTUALLY Changes:
- AI mockup look (farmhouse, mid-century modern, coastal, etc.)
- AI commentary text matches selected style

### Scope Selector ACTUALLY Changes:
- Line items (full reno vs fabric-only vs hardware-upgrade)
- What gets inpainted

### PDF Card Layout (compact, one card per tier):
- page-break-inside: avoid
- Two images side by side (inpainted + clean mockup)
- AI commentary: max 3 sentences
- Line items compact table
- Totals on one line
- No duplicates, no wasted space

### Full Claude Code prompt saved: claude_code_inpaint_prompt_2026-03-08_0015.md

---

## EMPIRE WORKROOM PAGE — Research Complete

### Approach: Keep ALL existing backend, rebuild UI layer only
- 50+ API endpoints already exist and work
- CRM, tasks, desks, quotes, memory — all functional backend
- Problem is UI doesn't expose most features (only ~15 of 50+ endpoints used)
- Desk components show hardcoded mock data instead of live API calls

### Layout (QB-inspired but better):
- Left sidebar: Dashboard, Quotes, Customers, Inventory, Finance, Calendar, Jobs & Orders, Photo Gallery, Measurements, SocialForge, Support, Reports
- Main content changes based on sidebar selection
- Dashboard default: KPI cards + today's agenda + activity feed + customizable widgets
- Every section has MAX AI built in (summarize customer, flag low stock, suggest follow-ups)

### What QB does right (copy):
- Customizable dashboard widgets (drag/rearrange)
- AI agents for accounting, payments, customers
- Search bar that navigates to modules
- Key metrics at fingertips (P&L, receivables, payables, overdue)

### What QB does wrong (avoid):
- Burying features 3 layers deep
- Forced UI changes with no revert
- Breaking graphs and widgets in updates

### 8 Daily Tools to Wire:
1. Quote Builder (create/edit with AI)
2. Customer list + detail view
3. Inventory management (stock, reorder)
4. Finance dashboard (invoices, P&L, deposits)
5. Job/order tracking (in progress, completed)
6. Calendar/scheduling (installations, consultations)
7. Photo gallery (customer photos, mockups)
8. Measurement tools (calibrate, calculate, 3D viewer)

---

## FILE NAMING CONVENTION
All files: `Name_YYYY-MM-DD_HHMM.ext` (include time)

## KEY FILE LOCATIONS
- Backend: ~/empire-repo/backend/app/
- Vision router: ~/empire-repo/backend/app/routers/vision.py
- TTS service: ~/empire-repo/backend/app/services/max/tts_service.py
- Tool executor: ~/empire-repo/backend/app/services/max/tool_executor.py (22 tools)
- Quote router: ~/empire-repo/backend/app/routers/quotes.py (1874+ lines)
- Telegram bot: ~/empire-repo/backend/app/services/max/telegram_bot.py
- Desks: ~/empire-repo/backend/app/services/max/desks/
- Memory: ~/empire-repo/backend/app/services/max/brain/memory_store.py
- CraftForge specs: ~/empire-repo/docs/CRAFTFORGE_SPEC.md
- Data: ~/empire-repo/backend/data/ (brain/, chats/, quotes/, uploads/)
