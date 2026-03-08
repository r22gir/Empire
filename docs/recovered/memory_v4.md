# MAX AI — COMPLETE BRAIN v4.0
## Last Updated: 2026-03-06

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

## THE HARDWARE

### Primary: Empire Dell (ACTIVE)
- Hostname: EmpireDell
- Device: Dell Precision Tower 5810
- CPU: Intel Xeon E5-2650 v3 (10-core, 20 threads @ 2.30GHz)
- RAM: 32 GB
- GPU: NVIDIA Quadro K600 (dedicated, 1GB GDDR3, compute capability 3.0)
- GPU Note: Below Ollama GPU threshold (needs 5.0+). Ollama runs CPU-only.
- Disk: 92GB SSD (24GB used, 64GB free)
- Swap: 8GB configured
- OS: Ubuntu 24.04.4 LTS (kernel 6.17.0-14-generic)
- Stability: ZERO crashes since deployment. Rock solid.
- Firmware: Dell BIOS A30 (2019-03-27)

### Future Test Device: Beelink Mini PC
- Purpose: Light modules only (testing later)
- Status: Not yet deployed
- Plan: Run lightweight Forge apps that don't need heavy compute

### Retired: AZW EQ Mini PC
- CPU: AMD Ryzen 7 5825U (8-core, 16 threads)
- RAM: 27 GB
- GPU: AMD Barcelo (integrated)
- Disk: 465GB NVMe
- Status: RETIRED — suffered multiple crashes (Ollama OOM, USB power surges, kernel issues)
- Kept as reference only

## CRITICAL BANS — EMPIRE DELL
1. pkill node — too broad, use pkill -f next-server
2. Broad pkill -f in scripts — use port-specific kills
3. Running more than 3 Next.js dev servers simultaneously — resource hog
4. USB external drive for live I/O — use for backup only, not live read/write

### Bans Retired (AZW-specific, not applicable to Dell)
- sensors-detect — was incompatible with AZW AMD chip. Dell Intel Xeon likely safe, but test with caution.
- amdgpu.gpu_recovery — not applicable, Dell uses NVIDIA
- Ollama + USB simultaneous — crashed on AZW due to RAM limits. Dell has more headroom but still avoid.

## SERVICES AND PORTS
- 3000: Empire App (unified dashboard) ~/empire-repo/empire-app
- 3001: WorkroomForge ~/empire-repo/workroomforge
- 3002: LuxeForge ~/empire-repo/luxeforge_web
- 3009: Founder Dashboard (MAX command center) ~/empire-repo/founder_dashboard
- 7878: OpenClaw AI ~/empire-repo/openclaw
- 8000: FastAPI Backend ~/empire-repo/backend
- 8080: Homepage ~/empire-repo/homepage
- 11434: Ollama (CPU-only mode, CUDA_VISIBLE_DEVICES=-1)

## TECH STACK
- Frontend: Next.js 14+ React/TypeScript
- Backend: FastAPI Python 3.12
- Database: SQLite (brain), PostgreSQL 14+ (Docker, stopped)
- Cache: Redis 6+ (Docker, stopped)
- AI Cloud: xAI Grok (primary), Claude (secondary)
- AI Local: Ollama CPU-only (EMERGENCY FALLBACK — only if both cloud APIs down)
- Mobile: Flutter (MarketForge app)
- Repo: github.com/r22gir/Empire (ACTIVE — push confirmed Mar 2)
- Branch: main (all work merged)
- Version: 4.0

## OLLAMA STRATEGY (Updated Mar 6)
- Role: EMERGENCY FALLBACK ONLY — if Grok AND Claude APIs both go down
- Mode: CPU-only (CUDA_VISIBLE_DEVICES=-1)
- Why CPU: Quadro K600 compute capability 3.0 < Ollama minimum 5.0
- Speed: ~5-15 tokens/sec on Xeon CPU (vs 30-50+ on GPU). Slow but functional.
- Safe models: 7B parameter (Llama 3.1 8B, Qwen 3 8B, Mistral 7B)
- NOT for daily use — cloud AI (Grok/Claude) handles all normal traffic
- GPU upgrade path: Used GTX 1070/1080 (~$100-150) fits Dell PCIe x16 slot, would unlock full GPU speed

## BACKUP STRATEGY (as of Mar 2)
- GitHub: r22gir/Empire — main branch, all work merged and pushed
- Google Drive: empirebox2026@gmail.com — rclone configured, full sync done
- Local SSD: primary working copy (fast, reliable)
- External USB 1TB: backup-only (NOT for live operations)
- Scripts: ~/empire-repo/scripts/backup-gdrive.sh, ~/empire-repo/scripts/backup-check.sh

## MAX BRAIN STORAGE
- Location: ~/empire-repo/backend/data/brain/memories.db (LOCAL SSD)
- 205 memories, 156KB — SQLite, grows safely
- Batch learning: DISABLED (was causing crashes on AZW — safe to re-test on Dell)
- Real-time learning: DISABLED (needs cloud LLM or CPU Ollama alternative)
- brain_config.py updated to local-first (no external drive dependency)
- PRIORITY: Re-enable learning using cloud LLM (Grok/Claude) or CPU Ollama

## MEMORY FRAGMENTATION — CRITICAL ISSUE (Mar 6 Audit)
Four separate memory systems that don't talk to each other:
1. max/memory.md — Flat markdown, manual edits only, no search/query
2. memories.db — SQLite 205 entries, learning disabled, best foundation
3. _telegram_history — In-memory Python dict, last 10 only, lost on restart
4. Claude.ai context — No persistence, manual push via claude-context bridge

### What's Needed
- Unified memory API: Single /api/v1/memory/* endpoint all clients read/write
- Re-enable memories.db learning with cloud LLM (not Ollama initially)
- Telegram bot persistence: Save history to DB, not in-memory dict
- Context Bridge automation: Current claude-context push is manual
- Memory search: Query by topic, date, customer, product
- Cross-session continuity: Auto-load relevant context on new session

## ALL PRODUCTS (27+ confirmed from GitHub PRs + local code)

### Core Platform
- EmpireBox: The platform/hardware/brand (Core)
- OpenClaw: Central AI brain local LLM (exists ~/empire-repo/openclaw)
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
- 4 unmerged copilot branches: docs salvaged to ~/empire-repo/docs/salvaged/
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

### Empire Dell (Current) — ZERO CRASHES
- Deployed and running stable
- Kernel 6.17 works fine on Intel Xeon (unlike AMD on AZW)

### AZW EQ Mini PC / Beelink (Retired) — ~100 CRASHES
- Extremely unstable machine. Roughly 100 crashes over its lifetime.
- Root causes: Ollama OOM, USB power surges, kernel incompatibilities, aggressive pkill, too many Next.js servers
- Notable incidents:
  - Feb 23: Ollama LLaVA OOM — removed Ollama temporarily
  - Feb 24: Aggressive pkill in launch-all.sh — fixed to safe port kills
  - Feb 25: Too many Next.js servers — max 3 at a time
  - Mar 2: System crash — suspected USB power surge during Ollama writes
- Final fixes before retirement: kernel downgraded to 6.8 LTS, amdgpu.gpu_recovery=1, brain moved to local NVMe
- Status: RETIRED. Replaced by Empire Dell.

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
- AMP Project Actitud Mental Positiva: files at ~/empire-repo/amp/
- ContentForge: Referenced in GitHub Issue #42 but no code yet
- Docker: 32 containers ALL STOPPED — need control panel per product
- Learning strategy: Re-enable with cloud LLM (Grok/Claude). Ollama is emergency fallback only, not for learning.
- External drive: inventory contents next time plugged in
- GPU Upgrade: Used GTX 1070/1080 (~$100-150) would enable GPU Ollama on Dell
- Version tracking: Platform is v4.0 but VERSION file still says 2.1.0 — needs update

## COPILOTFORGE CHAT SAVING
- Need to save Claude chats same as CoPilotForge saves chats
- Archive location: ~/empire-repo/docs/CHAT_ARCHIVE/
- Salvaged chat summaries: ~/empire-repo/docs/salvaged/ (Feb 16-18)
- Always save session summary before closing
