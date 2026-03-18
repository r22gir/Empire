# Empire v5.0 — Complete Ecosystem Report
Generated: 2026-03-18
Source: Full codebase scan (396 commits, 44 screens, 35 tools, 18 desks, 7 databases)

## Executive Summary

Empire (EmpireBox) is a comprehensive AI-powered business automation platform built by founder RG. It runs on a self-hosted Dell PowerEdge server ("EmpireDell") and serves as the command center for multiple businesses: Empire Workroom (custom drapery & upholstery), WoodCraft (woodwork & CNC, planned), and a SaaS platform selling the same tools to other business owners.

The system is anchored by MAX, an AI orchestrator with 18 specialized desks, 35 tools, and 3,041 persistent memories. MAX routes through a multi-provider AI chain (Grok → Claude → Groq → OpenClaw → Ollama) and communicates via a web-based Command Center and Telegram bot. The platform has processed 1,049 AI API calls, manages 113 customers, 156 inventory items, and 139 tasks.

As of v5.0, Empire has 22 products (8 active, 12 in development, 2 placeholder), with the core WorkroomForge QB replacement fully operational (43 endpoints, invoices, payments, expenses, CRM, inventory). The biggest gap is CraftForge (15 backend endpoints, zero frontend) and several Forge products with screen stubs but limited backend functionality.

---

## Company Overview

| Field | Value |
|-------|-------|
| **Name** | Empire Box / EmpireBox |
| **Tagline** | Founder's Command Center |
| **Founder** | RG |
| **Domain** | empirebox.store |
| **Studio URL** | studio.empirebox.store (Cloudflare tunnel) |
| **API URL** | api.empirebox.store |
| **Repo** | github.com/r22gir/Empire (private, main branch) |
| **Server** | EmpireDell — Dell PowerEdge, Intel Xeon E5-2650 v3, 32GB RAM, 20 cores |
| **GPU** | Quadro K600 (nouveau driver — unstable) |
| **OS** | Ubuntu 24.04, kernel 6.17.0 |
| **Origin** | Inspired by Alex Finn (AI YouTuber) — adapted from Mac Mini concept to Beelink EQR5, then EmpireDell |

### Businesses

1. **Empire Workroom** — Custom drapery & upholstery (active, 113 customers, $31.9K pipeline)
2. **WoodCraft** — Woodwork & CNC (planned, full spec exists, no frontend)
3. **Empire Platform** — SaaS ecosystem (Lite $29, Pro $79, Empire $199/month)

### Email Addresses
- workroom@empirebox.store
- woodcraft@empirebox.store
- info@empirebox.store
- support@empirebox.store

---

## Products & Applications (22 total)

### Active (8)

| Product | Port | Description | CC Screen |
|---------|------|-------------|-----------|
| **Command Center** | 3005 | Unified Next.js dashboard — 4 tabs, 44 screens | DashboardScreen.tsx |
| **WorkroomForge** | 3001 | QB replacement — quotes, invoices, payments, CRM, inventory | WorkroomPage.tsx |
| **LuxeForge** | 3002 | Client/designer intake portal with auth flow | LuxeForgePage.tsx |
| **ForgeCRM** | — | Customer relationship management | ForgeCRMPage.tsx |
| **RecoveryForge** | 3077 | File recovery with AI image classification | RecoveryForgeScreen.tsx |
| **Vision Analysis** | — | AI-powered image analysis and measurements | VisionAnalysisPage.tsx |
| **Telegram Bot** | — | @Empire_Max_Bot — notifications, PDFs, voice | (embedded) |
| **Cost Tracker** | — | AI cost monitoring dashboard (11 endpoints) | (in Workroom tab) |

### In Development (12)

| Product | Description | CC Screen |
|---------|-------------|-----------|
| **CraftForge** | WoodCraft business module (15 endpoints, 0 frontend) | CraftForgePage.tsx |
| **MarketForge** | Multi-marketplace listing & inventory | MarketForgePage.tsx |
| **SocialForge** | Social media management | SocialForgePage.tsx |
| **SupportForge** | Customer support & ticketing | SupportForgePage.tsx |
| **ShipForge** | Shipping management | ShipForgePage.tsx |
| **LeadForge** | Lead generation & nurturing | LeadForgePage.tsx |
| **ContractorForge** | Universal SaaS for service businesses | ContractorForgePage.tsx |
| **LLCFactory** | LLC formation & compliance (nationwide docs exist) | LLCFactoryPage.tsx |
| **ApostApp** | Document apostille services | ApostAppPage.tsx |
| **EmpireAssist** | AI assistant for all products | EmpireAssistPage.tsx |
| **EmpirePay** | Crypto payments & EMPIRE token | EmpirePayPage.tsx |
| **RelistApp** | Cross-platform relisting tool | RelistAppScreen.tsx |

### Placeholder (2)

| Product | Description | CC Screen |
|---------|-------------|-----------|
| **VetForge** | Veterinary practice management | VetForgePage.tsx |
| **PetForge** | Pet services management | PetForgePage.tsx |

### Standalone Apps

| App | Port | Description | Status |
|-----|------|-------------|--------|
| **AMP** | 3003 | Portal de la Alegria — Spanish personal dev platform | Dev |
| **Smart Lister** | — | AI-assisted product listing | Dev |

---

## AI Desks (18 total)

| # | Desk | Agent | Role | Model |
|---|------|-------|------|-------|
| 1 | ForgeDesk | **Kai** | Workroom operations, quotes, follow-up | Grok (default) |
| 2 | MarketDesk | **Sofia** | Marketplace operations, listings, shipping | Grok (default) |
| 3 | MarketingDesk | **Nova** | Social media, content, campaigns | Grok (default) |
| 4 | SupportDesk | **Luna** | Customer support, tickets, escalation | Grok (default) |
| 5 | SalesDesk | **Aria** | Sales pipeline, leads, proposals | Grok (default) |
| 6 | FinanceDesk | **Sage** | Invoices, payments, expenses, P&L | Grok (default) |
| 7 | ClientsDesk | **Elena** | Client relationships, preferences | Grok (default) |
| 8 | ContractorsDesk | **Marcus** | Installers, scheduling, assignments | Grok (default) |
| 9 | ITDesk | **Orion** | Systems admin, services, monitoring | Grok (default) |
| 10 | CodeForge | **Atlas** | Code creation, editing, testing, git | **Claude Opus 4.6** |
| 11 | WebsiteDesk | **Zara** | Website, SEO, portfolio | Grok (default) |
| 12 | IntakeDesk | **Zara** | LuxeForge submissions, routing | Grok (default) |
| 13 | LegalDesk | **Raven** | Contracts, compliance, legal docs | Grok (default) |
| 14 | AnalyticsDesk | **Raven** | Business intelligence, reports | **Claude Sonnet 4.6** |
| 15 | QualityDesk | **Phoenix** | AI accuracy monitoring, digests | **Claude Sonnet 4.6** |
| 16 | LabDesk | **Phoenix** | R&D sandbox, prototyping | Grok (default) |
| 17 | InnovationDesk | **Spark** | Market scanning, competitor watch | Grok (default) |
| 18 | CostTrackerDesk | **CostTracker** | Token usage, budget monitoring | Grok (default) |

### Desk Scheduler
Autonomous desk tasks run daily 8:00AM-10:30AM:
- Morning briefing
- Overdue check
- Follow-ups

---

## Tools & Capabilities (35 total)

### Data Tools (L1 — Auto)
| Tool | Description |
|------|-------------|
| search_quotes | Search quotes by customer or status |
| get_quote | Get full quote details by ID |
| search_contacts | Search customers, contractors, vendors |
| create_contact | Add a new contact |
| get_tasks | Get tasks (filter by desk/status) |
| get_desk_status | Get task counts across all desks |

### Action Tools (L1 — Auto)
| Tool | Description |
|------|-------------|
| create_quick_quote | Create 3-option proposal (Essential/Designer/Premium) |
| select_proposal | Finalize a quote by selecting A/B/C |
| open_quote_builder | Open QuoteBuilder inline |
| create_task | Create task for any desk |
| run_desk_task | Delegate to AI desk system |

### Communication Tools (L1 — Auto)
| Tool | Description |
|------|-------------|
| send_telegram | Send message to founder via Telegram |
| send_quote_telegram | Generate quote PDF and send via Telegram |
| send_email | Send email with attachments |
| send_quote_email | Generate quote PDF and email |

### Research Tools (L1 — Auto)
| Tool | Description |
|------|-------------|
| web_search | Search web via DuckDuckGo |
| web_read | Fetch and read a web page |
| search_images | Search Unsplash for images |
| photo_to_quote | Create quote from photo analysis |

### System Tools
| Tool | Description | Level |
|------|-------------|-------|
| get_system_stats | CPU, RAM, disk, temp | L1 |
| get_weather | Live weather data | L1 |
| get_services_health | Check running services | L1 |
| present | Generate PDF report | L1 |
| shell_execute | Safe shell command | L3 |
| dispatch_to_openclaw | Send to OpenClaw | L3 |

### Dev Tools (Atlas/Orion)
| Tool | Description | Level |
|------|-------------|-------|
| file_read | Read file with line range | L1 |
| file_write | Write file (truncation protection) | L2 |
| file_edit | Replace string or append | L2 |
| file_append | Append to file (never truncates) | L2 |
| git_ops | Git operations | L2 |
| service_manager | Systemd service management | L1/L3 |
| package_manager | pip/npm install/build | L2 |
| test_runner | Run tests and health checks | L1 |
| project_scaffold | Create from templates | L2 |

---

## Architecture

### Service Map

| Service | Port | Systemd Unit | Status |
|---------|------|-------------|--------|
| Backend API (FastAPI) | 8000 | empire-backend | Active |
| Command Center (Next.js) | 3005 | empire-cc | Active |
| OpenClaw AI | 7878 | empire-openclaw | Available |
| Ollama LLM Server | 11434 | ollama | Running |
| RecoveryForge | 3077 | — | Available |
| RelistApp | 3007 | — | Dev |
| AMP | 3003 | — | Dev |
| Cloudflare Tunnel | — | cloudflared | Active |
| Telegram Bot | — | — | Embedded in backend |

### AI Model Routing

**Fallback Chain:** Grok (15s) → Claude Sonnet (30s) → Groq (10s) → OpenClaw (30s) → Ollama (30s)

| Model | Provider | Input $/1M | Output $/1M | Used By |
|-------|----------|-----------|------------|---------|
| grok-3-fast | xAI | $5.00 | $15.00 | Default for all desks |
| claude-sonnet-4-6 | Anthropic | $3.00 | $15.00 | Raven (Analytics), Phoenix (Quality) |
| claude-opus-4-6 | Anthropic | $15.00 | $75.00 | Atlas (CodeForge) |
| groq-llama-3.3-70b | Groq | $0.59 | $0.79 | Fallback |
| openclaw | Local | $0 | $0 | Autonomous tasks |
| ollama-llama3.1 | Local | $0 | $0 | Last resort |

### Key Design Decisions
1. Single Next.js app (CC) replaces 4 legacy servers
2. 4 tabs: MAX (gold), Workroom (green), CraftForge (yellow), Platform (blue)
3. Warm off-white theme (#f5f3ef), gold accents (#b8960c)
4. All buttons 44px+ for tablet use
5. Dual-use: RG dogfoods products first, then sells as SaaS
6. Iframe rule: external apps embedded via iframe in CC
7. Tool blocks are the ONLY way MAX executes actions
8. File safety: truncation protection, auto-backup .bak, critical file guard
9. Cost tracking: every AI call auto-logged
10. Grok TTS Rex for all voice ($0.05/min)
11. Founder Override Protocol: founder commands execute immediately

### Access Control (3 levels)
- **L1 (Auto):** Read operations, basic actions — executes immediately
- **L2 (Confirm):** Delete, modify, bulk operations — requires Telegram confirmation
- **L3 (PIN):** Shell execute, deploy, erase — requires 4-6 digit PIN

### Roles
- **Founder/Admin:** Full access (L1 auto, L2 confirm, L3 PIN)
- **Manager:** L1 auto, L2 confirm, L3 denied
- **Operator:** L1 auto, L2 own desk only, L3 denied
- **Viewer:** Read-only L1, everything else denied

---

## Database Schema

### empire.db (16 tables)

| Table | Rows | Purpose |
|-------|------|---------|
| tasks | 139 | All desk tasks with full lifecycle tracking |
| task_activity | 165 | Task history and changelog |
| desk_configs | 15 | AI desk configuration and system prompts |
| customers | 113 | Customer CRM (name, email, phone, type, revenue) |
| invoices | 9 | Invoice records with line items |
| payments | 2 | Payment records (cash/check/card/zelle/venmo/wire) |
| expenses | 6 | Expense tracking by category |
| inventory_items | 156 | Materials/hardware (fabric, hardware, motors, etc.) |
| vendors | 51 | Vendor directory with lead times |
| jobs | 4 | Job tracking (title, customer, status, hours, costs) |
| contacts | 0 | Contact directory (unused — customers table used instead) |
| max_response_audit | 94 | AI response quality tracking |
| access_users | 5 | User accounts with roles and PINs |
| access_sessions | 0 | Tool authorization sessions |
| access_audit | 0 | Tool execution audit log |

### intake.db (2 tables)

| Table | Rows | Purpose |
|-------|------|---------|
| intake_users | 3 | LuxeForge portal user accounts |
| intake_projects | 5 | Client project submissions with rooms, photos, measurements |

### brain/memories.db (6 tables)

| Table | Rows | Purpose |
|-------|------|---------|
| memories | 3,041 | MAX persistent memory entries |
| conversation_summaries | 99 | Chat conversation summaries |
| customers | 0 | Brain customer context (unused) |
| customer_interactions | 0 | Brain interaction tracking (unused) |
| knowledge | 0 | Brain knowledge base (unused) |

### brain/token_usage.db (3 tables)

| Table | Rows | Purpose |
|-------|------|---------|
| token_usage | 1,049 | Every AI API call logged (model, tokens, cost, feature) |
| budget_config | 1 | Monthly budget ($50 default, 80% alert threshold) |

### tool_audit.db (2 tables)

| Table | Rows | Purpose |
|-------|------|---------|
| tool_executions | 46 | Tool execution history with duration |

### amp.db (4 tables) — All empty

### empirebox.db (5 tables) — All empty (SupportForge)

---

## External Integrations

| Integration | Env Var | Status | Purpose |
|-------------|---------|--------|---------|
| xAI Grok | XAI_API_KEY | ✅ Configured | Primary AI (chat + vision + TTS) |
| Anthropic Claude | ANTHROPIC_API_KEY | ✅ Configured | Secondary AI (Sonnet + Opus) |
| Groq | GROQ_API_KEY | ✅ Configured | Fast inference (Llama 3.3 70B + Whisper) |
| Telegram Bot | TELEGRAM_BOT_TOKEN | ✅ Configured | Founder notifications |
| Stability AI | STABILITY_API_KEY | ✅ Configured | Image inpainting |
| Stripe | STRIPE_SECRET_KEY | ✅ Configured | Payments (test keys, 3 tiers) |
| Instagram | INSTAGRAM_API_TOKEN | ✅ Configured | Social media |
| Facebook | FACEBOOK_PAGE_TOKEN | ✅ Configured | Social media |
| Brave Search | BRAVE_API_KEY | ✅ Configured | Web search fallback |
| OpenClaw | OPENCLAW_GATEWAY_TOKEN | ✅ Configured | Local AI gateway |
| OpenAI | OPENAI_API_KEY | ❌ Empty | Not used (replaced by Grok TTS) |

---

## Security

### File Safety (v5.0)
- **Truncation protection:** Blocks writes that reduce file size by >50%
- **Auto-backup:** Creates .bak before any file overwrite
- **Critical file guard:** Blocks file_write for tool_executor.py, main.py, system_prompt.py, ai_router.py, tool_safety.py, tool_audit.py — must use file_edit
- **Path validation:** Blocks access outside ~/empire-repo/

### Shell Safety
- Allowlist: ls, cat, head, tail, wc, echo, df, du, free, ps, uptime, date, whoami, pwd, find, grep, git (status/log/diff/branch), curl, wget, pip list, npm list, systemctl (status/restart/is-active), journalctl, ollama (list/ps), docker (ps/images)
- Blocked: rm -rf, rm -r, pkill -f, kill -9, killall, dd, mkfs, fdisk, sudo rm, chmod 777, sensors-detect, eval, exec, pipe to sh/bash

### Hardware Warnings
- DO NOT run `sensors-detect` — crashes EmpireDell
- DO NOT use `pkill -f` with broad patterns — caused system crash Feb 24
- GPU nouveau driver unstable — no heavy CUDA operations

---

## Build History (Key Sessions)

| Date | Session | Key Work |
|------|---------|----------|
| 2026-02 | Project start | Empire founded on Beelink EQR5 |
| 2026-03-06 | Path migration | ~/Empire/ → ~/empire-repo/, 228 files, launch scripts |
| 2026-03-08 | v4.0 marathon | 110 files, 21,656 insertions, Command Center born, 10+ hours |
| 2026-03-09 | Payment modules | All 17 modules, marathon commit (170 files), RelistApp |
| 2026-03-10 | Cost tracker | 11 endpoints shipped, context bridge tools finalized |
| 2026-03-11 | Refinements | Bug fixes, polish |
| 2026-03-14 | Database work | Purge + backup system, access control |
| 2026-03-15 | RecoveryForge L3 | 18,472 image classification started, quality desk |
| 2026-03-16 | App audit | start-empire.sh cleanup, endpoint fixes, full audit |
| 2026-03-17 | v5.0 fixes | File safety, 3D avatar, timeouts, port refs, systemd services |
| 2026-03-18 | Knowledge build | Ecosystem catalog, comprehensive report, per-desk routing |

Total: 396 commits across ~3 weeks of development.

---

## Current Status

### Working
- Backend API (FastAPI) on port 8000 via systemd
- Command Center (Next.js) on port 3005 via systemd
- MAX AI chat with streaming (SSE)
- Quote system (3-option proposals, PDF generation, Telegram delivery)
- Finance dashboard (P&L, invoices, payments, expenses)
- CRM (113 customers imported)
- Inventory management (156 items, 51 vendors)
- Cost tracking (1,049 API calls logged)
- Cloudflare tunnel (studio.empirebox.store)
- LuxeForge intake portal (signup, login, project submission)
- 18 AI desks with task routing
- Telegram bot notifications
- Access control (3-level system, 5 users)

### In Progress
- RecoveryForge Layer 3 (18,472 images, LLaVA classification)
- 3D avatar (TalkingHead via iframe, needs live testing)

### Not Yet Built
- CraftForge frontend (spec + 15 endpoints ready, zero UI)
- SocialForge, SupportForge, MarketForge, ShipForge (screens exist, limited backend)
- AMP rebuild (current version doesn't match vision)
- LLCFactory, ApostApp, EmpirePay (concept stage)
- Email sending (SendGrid not configured)

---

## Known Issues & Bugs

1. **GPU nouveau driver unstable** — needs `sudo ubuntu-drivers autoinstall`
2. **CraftForge frontend gap** — 15 backend endpoints, zero frontend
3. **contacts table empty** — customers table used instead (possible migration needed)
4. **access_audit table empty** — audit logging may not be fully wired
5. **Duplicate agent names** — Zara (website + intake), Raven (legal + analytics), Phoenix (quality + lab)
6. **3D avatar untested** — TalkingHead iframe needs browser testing
7. **Ollama no production models** — only LLaVA for classification
8. **AMP needs rebuild** — current version "didn't capture the idea"
9. **Email not configured** — OpenAI key empty (was for TTS, not email), SendGrid not set up
10. **CLAUDE.md outdated** — still references ~/Empire/ paths and old hardware info

---

## Recommendations

### Priority 1 (This Week)
1. Fix CLAUDE.md — update paths, hardware info, port registry
2. Fix duplicate agent names across desks
3. Wire access_audit logging to actually record tool executions
4. Test 3D avatar in browser

### Priority 2 (This Month)
5. Build CraftForge frontend (biggest product gap)
6. Set up email sending (SendGrid or SMTP)
7. Install proper GPU driver for CUDA support
8. Rebuild AMP to match real vision
9. Pull Ollama production models (llama3.1:8b)

### Priority 3 (Next Quarter)
10. Build out SocialForge with real Instagram/Facebook posting
11. Build out MarketForge with eBay API integration
12. Launch SaaS platform with Stripe subscriptions
13. Zero-to-Hero automated business setup flow
14. Resolve agent name conflicts (unique names per desk)

---

## Appendix: File Structure

```
~/empire-repo/
├── backend/
│   ├── app/
│   │   ├── main.py                    # FastAPI entry point
│   │   ├── config/
│   │   │   ├── business_config.py     # Business settings loader
│   │   │   ├── business.json          # Business config values
│   │   │   └── pricing_tiers.py       # SaaS tier definitions
│   │   ├── db/
│   │   │   └── database.py            # SQLite connection manager
│   │   ├── routers/                   # 50+ API router files
│   │   │   ├── costs.py               # Token/cost tracking (11 endpoints)
│   │   │   ├── finance.py             # QB replacement
│   │   │   ├── customer_mgmt.py       # CRM
│   │   │   ├── inventory.py           # Inventory management
│   │   │   ├── jobs.py                # Job tracking
│   │   │   └── ...                    # 45+ more routers
│   │   └── services/
│   │       └── max/
│   │           ├── system_prompt.py    # MAX's brain (identity + rules)
│   │           ├── ai_router.py        # Multi-provider AI routing
│   │           ├── tool_executor.py    # 35 tools (2860+ lines)
│   │           ├── tool_safety.py      # Path/command validation
│   │           ├── tool_audit.py       # Execution logging
│   │           ├── access_control.py   # 3-level security
│   │           ├── token_tracker.py    # Cost tracking
│   │           ├── ecosystem_catalog.py # Product/desk/tool catalog (NEW v5.0)
│   │           ├── telegram_bot.py     # Telegram integration
│   │           ├── tts_service.py      # Grok TTS Rex
│   │           ├── stt_service.py      # Groq Whisper STT
│   │           ├── inpaint_service.py  # Design mockups
│   │           ├── brain/              # Memory system
│   │           │   ├── memory_store.py
│   │           │   └── context_builder.py
│   │           └── desks/              # 18 desk implementations
│   │               ├── desk_manager.py
│   │               ├── desk_router.py
│   │               ├── desk_scheduler.py
│   │               ├── forge_desk.py   # Kai
│   │               ├── codeforge_desk.py # Atlas
│   │               └── ...             # 15 more desks
│   ├── data/                          # SQLite databases
│   │   ├── empire.db                  # Main database (16 tables)
│   │   ├── intake.db                  # LuxeForge intake (2 tables)
│   │   ├── brain/                     # Brain databases
│   │   │   ├── memories.db            # 3,041 memories
│   │   │   └── token_usage.db         # 1,049 API calls
│   │   ├── tool_audit.db             # 46 tool executions
│   │   ├── amp.db                     # AMP (empty)
│   │   └── empirebox.db              # SupportForge (empty)
│   └── .env                           # API keys and config
├── empire-command-center/             # Next.js frontend (port 3005)
│   ├── app/
│   │   ├── page.tsx                   # Main dashboard
│   │   ├── components/
│   │   │   └── screens/               # 44 screen components
│   │   ├── intake/                    # LuxeForge intake pages
│   │   ├── amp/                       # AMP pages
│   │   └── services/llc/             # LLCFactory page
│   ├── public/                        # Static assets
│   └── package.json
├── docs/                              # 70+ documentation files
├── scripts/                           # Utility scripts
├── systemd/                           # Systemd service files
├── start-empire.sh                    # Launch script
├── stop-empire.sh                     # Shutdown script
└── CLAUDE.md                          # Claude Code instructions
```

---

## Appendix: Environment Variables

| Variable | Purpose |
|----------|---------|
| XAI_API_KEY | xAI Grok API (chat, vision, TTS) |
| ANTHROPIC_API_KEY | Claude API (Sonnet + Opus) |
| OPENAI_API_KEY | Not used (was for TTS) |
| GROQ_API_KEY | Groq API (Llama 3.3 + Whisper STT) |
| BRAVE_API_KEY | Brave Search API |
| TELEGRAM_BOT_TOKEN | Telegram Bot API |
| TELEGRAM_FOUNDER_CHAT_ID | Founder's Telegram chat ID |
| API_HOST | Backend API host |
| API_PORT | Backend API port |
| CORS_ORIGINS | Allowed CORS origins |
| STABILITY_API_KEY | Stability AI (inpainting) |
| OPENCLAW_GATEWAY_TOKEN | OpenClaw gateway auth |
| STRIPE_SECRET_KEY | Stripe payments (test) |
| STRIPE_PUBLISHABLE_KEY | Stripe frontend key |
| STRIPE_WEBHOOK_SECRET | Stripe webhook verification |
| STRIPE_PRICE_LITE | Lite tier Stripe price ID |
| STRIPE_PRICE_PRO | Pro tier Stripe price ID |
| STRIPE_PRICE_EMPIRE | Empire tier Stripe price ID |
| INSTAGRAM_API_TOKEN | Instagram API |
| FACEBOOK_PAGE_TOKEN | Facebook Pages API |

---

*Report generated by Claude Opus 4.6 during MAX Total Knowledge Build v5.0*
