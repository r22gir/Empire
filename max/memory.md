# MAX AI — COMPLETE BRAIN v3.0
## Last Updated: 2026-03-02

## FIRST RUN PROTOCOL
On every new session MAX must:
1. State key facts it remembers
2. Ask Founder to confirm or correct
3. Ask what changed since last update
4. Ask for today priority

## THE FOUNDER
- Name: RG (GitHub: r22gir)
- Languages: English + Spanish
- Business: Custom drapery / window treatments (WorkroomForge)
- Vision: EmpireBox = OS for resellers and service businesses
- Style: Direct, fast-moving, ambitious. Builds late at night.
- Preference: Dark UI, gold/amber accents, no fluff

## THE HARDWARE — EmpireBox Server
- Device: AZW EQ Mini PC
- CPU: AMD Ryzen 7 5825U (8-core, 16 threads)
- RAM: 27 GB
- GPU: AMD Barcelo (integrated)
- Disk: 465GB NVMe (93GB used, 342GB free)
- Swap: 8GB configured
- OS: Ubuntu 24 (kernel 6.8.0-101-generic LTS)
- GRUB: amdgpu.gpu_recovery=1 enabled, kernel 6.8 default
- Previous kernel 6.17 available as fallback

## CRITICAL BANS
1. sensors-detect — BRICKS this machine (Super I/O scan incompatible)
2. pkill node — too broad, use pkill -f next-server
3. Broad pkill -f in scripts — use port-specific kills
4. USB external drive for live I/O — power surges cause crashes
5. Running Ollama + USB writes simultaneously

## SERVICES AND PORTS
- 3000: Empire App (unified dashboard) ~/Empire/empire-app
- 3001: WorkroomForge ~/Empire/workroomforge
- 3002: LuxeForge ~/Empire/luxeforge_web
- 3009: Founder Dashboard (MAX command center) ~/Empire/founder_dashboard
- 7878: OpenClaw AI ~/Empire/openclaw
- 8000: FastAPI Backend ~/Empire/backend
- 8080: Homepage ~/Empire/homepage
- 11434: Ollama (optional, disabled by default)

## TECH STACK
- Frontend: Next.js 14+ React/TypeScript
- Backend: FastAPI Python 3.12
- Database: SQLite (brain), PostgreSQL 14+ (Docker, stopped)
- Cache: Redis 6+ (Docker, stopped)
- AI: xAI Grok (cloud primary), Claude (cloud secondary), Ollama (local, optional)
- Mobile: Flutter (MarketForge app)
- Repo: github.com/r22gir/Empire (ACTIVE — push confirmed Mar 2)
- Branch: main (all work merged)

## BACKUP STRATEGY (as of Mar 2)
- GitHub: r22gir/Empire — main branch, all work merged and pushed
- Google Drive: empirebox2026@gmail.com — rclone configured, full sync done
- Local NVMe: primary working copy (fast, reliable)
- External USB 1TB: backup-only (NOT for live operations)
- Scripts: ~/Empire/scripts/backup-gdrive.sh, ~/Empire/scripts/backup-check.sh

## MAX BRAIN STORAGE
- Location: ~/Empire/backend/data/brain/memories.db (LOCAL NVMe)
- 205 memories, 156KB — SQLite, grows safely
- Batch learning: DISABLED (was causing crashes with Ollama + USB)
- Real-time learning: DISABLED (needs Ollama or cloud LLM alternative)
- brain_config.py updated to local-first (no external drive dependency)

## ALL PRODUCTS (27+ confirmed from GitHub PRs + local code)

### Core Platform
- EmpireBox: The platform/hardware/brand (Core)
- OpenClaw: Central AI brain local LLM (exists ~/Empire/openclaw)
- MAX: Founder AI assistant (LIVE — 12 desks, brain, tools)
- EmpireAssist: Telegram bot (LIVE — voice + text + documents)
- Setup Portal: Customer onboarding (PR #9 merged)
- License System: Subscription keys (PR #9 merged)

### Live Products
- WorkroomForge: Drapery workroom management (LIVE, port 3001)
- LuxeForge: Customer portal + AI photo + measurement tool (LIVE, port 3002)
- Founder Dashboard: MAX command center (LIVE, port 3009)
- Empire App: Unified all-in-one dashboard (port 3000)

### Built / Merged (on GitHub main)
- MarketForge: Multi-channel listing tool (PR #6, backend 28 endpoints)
- ContractorForge: Universal multi-tenant SaaS (PR #11 merged)
- SupportForge: AI customer support platform (PR #16 merged)
- MarketF: P2P marketplace 8% fees (PR #10 merged)
- ShipForge: Shipping via EasyPost (PR #9 merged)
- Economic Intelligence System: Cost tracking + quality eval (PR #14 merged)
- Empire Wallet: Crypto payments — Solana/USDC/EMPIRE token (PR #40 merged)
- Amazon SP-API: MarketF integration scaffolding (PR #38 merged)
- Voice Service: STT/TTS with Telegram + SDK (PR #31 merged)
- Chat Backup System: Auto backup + decision unification (PR #35 merged)
- Docker configs: Local-build Dockerfiles for all services (PR #32 merged)

### Specced / Planned
- LeadForge: AI lead gen in ContractorForge/LuxeForge
- VeteranForge: VA disability telehealth (legal done, pitch deck exists)
- ContentForge: Content management (referenced in Issue #42)
- ForgeCRM: CRM freemium model
- SocialForge: Social media semi-auto
- LLCFactory: Business formation (Northwest Agents)
- ApostApp: Document filler / forms
- RelistApp: Automated relisting
- RecoveryForge: AI hard drive file recovery
- ElectricForge: Electrician template
- LandscapeForge: Landscaping template

## GITHUB STATUS (as of Mar 2)
- Repo: ACTIVE, accepting pushes
- Default branch: main (fully merged with release/v1.0.0-alpha.1)
- Total merged PRs: 28 (#2–#48)
- Open PRs: 2 (#44 WorkroomForge wiring, #46 LuxeForge camera)
- Open Issues: 5 (#34, #41, #42, #43, #45)
- 4 unmerged copilot branches: docs salvaged to ~/Empire/docs/salvaged/
- 19 copilot/ branches total on remote

## ZERO TO HERO — The Killer Feature
Idea to operational business in 3-14 days:
1. OpenClaw conversation intake 30 min
2. LLCFactory formation (Northwest Registered Agents)
3. Stripe Connect onboarding
4. SocialForge semi-auto accounts (FB IG Twitter LinkedIn)
5. Business tools activation
6. EmpireAssist setup Telegram bot
7. HERO STATUS — taking orders

## HARDWARE BUNDLES
- Budget Mobile 349: Xiaomi Redmi Note 13 + Lite 12mo
- Seeker Pro 599: Solana Seeker + Pro 12mo (MOST POPULAR)
- Full Empire 899: Seeker + Beelink Mini PC + Empire 12mo
- All loss-leaders. Profit from subscription renewals.

## WORKROOMFORGE PRICING
Base per sqft: Ripplefold 45 | Pinch Pleat 38 | Rod Pocket 28 | Grommet 32 | Roman 55 | Roller 42
Lining per sqft: Unlined 0 | Standard 8 | Blackout 15 | Thermal 12 | Interlining 18
Hardware per window: Rod Std 45 | Rod Deco 85 | Track Basic 65 | Track Ripple 95
Motors per window: Somfy 285 | Lutron 425 | Generic 185
Formula: (base x sqft + lining x sqft + hardware + motor) x qty

## WORKROOM CUSTOMERS
- Emily Rodriguez: 22600 VIP Repeat High Value
- Sarah Mitchell: 12400 VIP Repeat
- Maria Gonzalez: 8900 Designer Referral
- David Chen: 4200 New
- James Wilson: 3100 Inactive
Vendors: Rowley Company, Somfy, Lutron, Kirsch
Pipeline: 31900 total

## REVENUE MODEL Year 3
- Conservative: 3.4M - 5.2M
- Moderate: 8.6M
- Aspirational: 17.2M

## CRASH HISTORY
- Feb 23: Ollama LLaVA OOM — removed Ollama temporarily
- Feb 24: Aggressive pkill in launch-all.sh — fixed to safe port kills
- Feb 25: Too many Next.js servers — max 3 at a time
- Mar 2: System crash — suspected USB power surge during Ollama writes
  - Fix: kernel downgraded to 6.8 LTS, amdgpu.gpu_recovery=1 added
  - Fix: brain storage moved to local NVMe (no USB dependency)

## DESIGN SYSTEM
- Background: 080810 void black
- Gold: C9A84C / D4AF37 primary accent
- Purple: 8B5CF6 MAX/AI accent
- Fonts: Outfit display + JetBrains Mono code
- Dark theme ONLY

## 12-TRACK MAX UPGRADE (completed Mar 1)
1. Chart rendering — ContentAnalyzer parses chart JSON blocks
2. Quick Quote — create_quick_quote tool, auto-prices by treatment
3. Mockup overlay SVG — before/after with retracted panels + hardware
4. Batch learning — every 5 messages triggers learn_from_exchange
5. Telegram memory — _telegram_history dict, last 10 exchanges
6. Inline PDF display — DocumentCanvas wired to quick quote
7. Stat-pill contrast — 0.04 → 0.08 opacity
8. Command bar — 3x bigger textarea, larger buttons, drag-drop files
9. Voice agent — AudioContext resume fix, better errors
10. Live ticker — Crypto, News, Sports below command bar
11. Web research images — search_images tool via Unsplash
12. Desk integration — ForgeDesk AI vision, run_desk_task tool

## OPEN QUESTIONS
- RecoveryForge: AI file recovery tool — RESEARCH NEEDED
- AMP Project Actitud Mental Positiva: files at ~/Empire/amp/
- ContentForge: Referenced in GitHub Issue #42 but no code yet
- Docker: 32 containers ALL STOPPED — need control panel per product
- Learning strategy: Need to choose cloud LLM vs Ollama vs pattern-matching
- External drive: inventory contents next time plugged in

## COPILOTFORGE CHAT SAVING
- Need to save Claude chats same as CoPilotForge saves chats
- Archive location: ~/Empire/docs/CHAT_ARCHIVE/
- Salvaged chat summaries: ~/Empire/docs/salvaged/ (Feb 16-18)
- Always save session summary before closing
