# MAX AI — COMPLETE BRAIN v5.1
## Last Updated: 2026-03-18

## FIRST RUN PROTOCOL
On every new session MAX must:
1. State key facts it remembers
2. Ask Founder to confirm or correct
3. Ask what changed since last update
4. Ask for today priority

## THE FOUNDER
- Name: RG (GitHub: r22gir)
- Languages: English + Spanish
- Business: Custom drapery / window treatments (Empire Workroom) + woodwork (WoodCraft)
- Vision: EmpireBox = OS for resellers and service businesses
- Style: Direct, fast-moving, ambitious. Builds late at night.
- Preference: Dark UI, gold/amber accents, no fluff

## THE HARDWARE — EmpireDell (Primary Dev Machine)
- Device: Dell PowerEdge (EmpireDell)
- CPU: Intel Xeon E5-2650 v3 (10-core, 20 threads)
- RAM: 32 GB
- GPU: Quadro K600 (nouveau driver — UNSTABLE)
- OS: Ubuntu 24.04 (kernel 6.17.0-19-generic)
- NOTE: Data migrated FROM Beelink EQR5 TO EmpireDell. Beelink retired.

## CRITICAL BANS
1. sensors-detect — CRASHES the machine
2. pkill node — too broad, use pkill -f next-server
3. Broad pkill -f in scripts — use port-specific kills (caused system crash Feb 24, 2026)

## SERVICES AND PORTS (CURRENT — March 2026)
| Service | Port | Systemd | Status |
|---------|------|---------|--------|
| Backend API (FastAPI) | 8000 | empire-backend | Active |
| Command Center (Next.js) | 3005 | empire-cc | Active |
| OpenClaw AI | 7878 | empire-openclaw | Available |
| Ollama LLM | 11434 | ollama | Available |
| RecoveryForge | 3077 | — | Running |
| RelistApp | 3007 | — | Dev |
| AMP | 3003 | — | Dev |

### RETIRED / LEGACY Ports
- 3000: Empire App (replaced by Command Center 3005)
- 3001: WorkroomForge (merged into CC)
- 3002: LuxeForge (merged into CC)
- 3009: Founder Dashboard (replaced by CC)
- 3006: RESERVED (do not use)

## TECH STACK
- Frontend: Next.js 14, React 18, TypeScript, Tailwind CSS
- Backend: FastAPI, Python 3.12, SQLite
- AI: xAI Grok (primary) → Claude → Groq → OpenClaw → Ollama
- Icons: lucide-react across all apps
- Fonts: Outfit (UI) + JetBrains Mono (code)
- Repo: github.com/r22gir/Empire (private, main branch)
- Cloudflare Tunnel: studio.empirebox.store, api.empirebox.store

## AI MODEL ROUTING
- Default: xAI Grok (all general tasks)
- Atlas (CodeForge): Claude Opus 4.6
- Raven (Analytics), Phoenix (Quality): Claude Sonnet 4.6
- Fallback chain: Grok → Claude → Groq → OpenClaw → Ollama

## 18 AI DESKS
1. Kai (Forge) — Workroom operations, quotes
2. Sofia (Market) — Marketplace ops, eBay, Facebook
3. Nova (Marketing) — Social media, content
4. Luna (Support) — Customer support, tickets
5. Aria (Sales) — Sales pipeline, leads
6. Sage (Finance) — Invoices, payments, P&L
7. Elena (Clients) — CRM, client relationships
8. Marcus (Contractors) — Contractor management
9. Orion (IT) — Infrastructure, services, monitoring
10. Atlas (CodeForge) — Code agent (Claude Opus 4.6)
11. Zara (Website/Intake) — Website + LuxeForge intake
12. Raven (Legal/Analytics) — Business metrics, forecasting
13. Phoenix (Lab/Quality) — AI accuracy monitoring
14. Spark (Innovation) — Market scanning
15. CostTrackerDesk — Token usage monitoring
16. LeadForge — Lead capture
17. ShipForge — Shipping management
18. EmpirePay — Payment processing

## 37 TOOLS (v5.1 — post Phase 0 fix)
### Data Tools
file_read, file_write, file_edit, file_append, search_quotes, get_quote, get_tasks, get_desk_status

### Action Tools
create_task, run_desk_task, create_quick_quote, select_proposal, open_quote_builder, photo_to_quote

### Communication Tools
send_telegram, send_quote_telegram, send_email, send_quote_email

### Research Tools
web_search, web_read, search_images

### System Tools
shell_execute, git_ops, service_manager, get_services_health, get_system_stats, env_get, env_set, db_query

### Dev Tools
create_contact, search_contacts

### Tool Access Levels
- L1: Auto-execute (file_read, shell safe commands, get_services_health)
- L2: Telegram confirm (file_write, service restart)
- L3: PIN required (destructive operations)

## COMMAND CENTER (port 3005 — empire-command-center)
Unified Next.js dashboard replacing all legacy apps.
- 4 main tabs: MAX (gold), Workroom (green), CraftForge (yellow), Platform (blue)
- 44 screen components
- SSE streaming for MAX chat
- Quote Builder: 5-step wizard (Customer → Photos → Rooms → Options → Review)
- Vision Analysis: Photo analyzer with multi-tier mockup generation
- Chat History: Save, load, rename, delete conversations

## QUOTE INTELLIGENCE SYSTEM (QIS)
### Track 1 — Quick Quote
Instant ballpark from dimensions + material + complexity → 3 tiers (Essential/Designer/Premium)

### Track 2 — Multi-Phase Pipeline (6 phases)
0. Intake (auto-approved)
1. AI Vision Analysis → founder review
2. Measurements & Materials → founder review (EDITABLE)
3. Pricing & Labor → founder review
4. Profit & Margin → founder review
5. Client Quote PDF → founder approve to send

### Pricing Engine
- 17 item types in quick price table
- 4 complexity multipliers (simple→luxury: 1.0→2.25x)
- 4 fabric grades: A ($15/yd) → D ($120/yd)
- 25+ labor rate categories
- 8 upgrade types (tufting, welting, nailhead, motorized, etc.)
- Tax rates: DC 6%, MD 6%, VA 5.3%
- Deposit: 50%
- Tier multipliers: A (1.0x), B (2.0x fabric), C (3.5x fabric)

## BUSINESS NAMES (CANONICAL)
- **Empire Workroom** = drapery & upholstery business (NOT "RG's Drapery")
- **WoodCraft** = woodwork & CNC business
- **WorkroomForge** = quote builder software
- **CraftForge** = woodwork software module
- **LuxeForge** = client/designer intake portal
- **MarketForge** = marketplace operations
- **SocialForge** = social media management
- **SupportForge** = customer support & ticketing
- **RecoveryForge** = AI file recovery tool
- **OpenClaw** = skills-augmented local AI

## DATABASE (empire.db)
- customers: 113 rows
- inventory_items: 156 rows
- tasks: 139 rows
- vendors: 51 rows
- invoices: 9
- payments: 2
- expenses: 6
- jobs: 4
- memories: 3041
- ai_calls: 1049+
- Total tables: 38

## FINANCE SYSTEM (QB Replacement)
- P&L dashboard, invoices, payments, expenses
- Auto-generate invoice from quote
- Revenue pipeline: $1,900 verified
- Stripe wired (test keys active)

## DESIGN SYSTEM
- Background: #05050d void black
- Gold: #D4AF37 primary accent
- Purple: #8B5CF6 MAX/AI accent
- Fonts: Outfit (UI) + JetBrains Mono (code)
- Dark theme ONLY

## SAAS TIERS
- Lite $29/mo — 50K tokens
- Pro $79/mo — 200K tokens
- Empire $199/mo — 1M tokens
- Founder — Unlimited

## RECENT SESSION LOG
- v5.0 (Mar 18 AM): CRM bug fix, inventory categorization, yardage calc, Kanban job board, dashboard KPIs
- v5.0 (Mar 18 PM): Tool execution fix — shell allowlist, file_edit fuzzy+line mode, env/db tools, 12/12 tests passing (commit ec0a091)
- v5.1 (Mar 18 EVE): Knowledge build, quote pipeline API, system prompt update, vision+chat enhancements

## AUTO-SYNC (updated nightly by brain_sync)
Last sync: 2026-04-25 23:00

### Database Counts (empire.db)
- tasks: 606
- customers: 144
- invoices: 17
- payments: 1
- expenses: 6
- inventory_items: 155
- vendors: 51
- contacts: 2
- desk_configs: 15
- task_activity: 349

### File Storage
- Quote JSONs: 143
- Inbox messages: 187
- Brain memories: 11061

### Finance Snapshot
- Revenue: $100 | Expenses: $5,380 | Outstanding: $4,175 | Net: $-5,280

### Active Tasks by Desk
- forge: 1

### System
- CPU: 0.4% | RAM: 14.5% (4GB/31GB) | Disk: 63.7% (55GB/91GB)
- Backend routers loaded: 84
