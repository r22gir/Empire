# Empire Product Directory

**Generated:** February 28, 2026
**Source:** Full codebase scan of `~/Empire/`

---

## Active Development (Code Exists + In Use)

### 1. Founder Dashboard
- **Directory:** `founder_dashboard/`
- **Port:** 3009
- **Stack:** Next.js 14, TypeScript, Tailwind CSS, Recharts
- **Status:** **ACTIVE — Primary UI**
- **Description:** Empire Founders Edition command center. Three-panel layout with MAX AI chat, conversation history, system sidebar. Includes Response Canvas (charts, media, comms, workspace), file browser, task manager, AI desk grid, quote builder workspace. All AI-focused founder operations.

### 2. Backend API
- **Directory:** `backend/`
- **Port:** 8000
- **Stack:** Python 3.12, FastAPI, SQLAlchemy, SQLite, httpx
- **Status:** **ACTIVE — Core API**
- **Description:** Central API for all Empire services. Routes: `/api/v1/max/*` (AI chat, desks, tasks, brain, tokens), `/api/v1/chats/*`, `/api/v1/files/*`, `/api/v1/system/*`, `/api/v1/ollama/*`, `/api/v1/notifications/*`, `/api/v1/customers/*`, `/api/v1/kb/*`. AI routing: xAI Grok → Claude → OpenClaw → Ollama. Includes MAX Brain (portable persistent memory on BACKUP11), token tracking, guardrails, tool execution.

### 3. WorkroomForge
- **Directory:** `workroomforge/`
- **Port:** 3001
- **Stack:** Next.js 14, TypeScript
- **Status:** **ACTIVE — Production**
- **Description:** Standalone quote builder + AI photo analysis for custom window treatments (drapes, shades, cornices, valances, bedding, upholstery). Fabric markup 2x wholesale, $50/hr labor. DC area business. Primary revenue product.

### 4. LuxeForge Web
- **Directory:** `luxeforge_web/`
- **Port:** 3002
- **Stack:** Next.js 15, TypeScript, Tailwind CSS
- **Status:** **ACTIVE — Live**
- **Description:** Designer portal and marketing site for LuxeForge — AI-powered software for custom workroom businesses. Pages: homepage, pricing (Solo $79, Pro $249, Enterprise $599), features, contact/demo request.

### 5. Empire App (Unified Dashboard)
- **Directory:** `empire-app/`
- **Port:** 3000
- **Stack:** Next.js 14, TypeScript
- **Status:** **ACTIVE**
- **Description:** Unified all-in-one dashboard with full modules: `/inventory`, `/finance`, `/customers`, `/workroom`, `/creations`, `/tasks`, `/shipping`, `/max`, `/settings`. Distinct from founder_dashboard (which is MAX AI-focused).

### 6. OpenClaw AI
- **Directory:** `openclaw/`
- **Port:** 7878
- **Stack:** Python, FastAPI
- **Status:** **ACTIVE**
- **Description:** Skills-augmented local AI service wrapping Ollama. Multi-model support (Ollama, Claude, OpenAI, xAI Grok, Gemini). Natural language conversation, cross-product intelligence, voice support.

### 7. Homepage
- **Directory:** `homepage/`
- **Port:** 8080
- **Stack:** Static HTML
- **Status:** **ACTIVE**
- **Description:** Static HTML navigation hub with 3 variants (agent, command, standard). Links to all Empire services by port.

---

## Built but Not Primary (Code Exists, Lower Priority)

### 8. AMP (Actitud Mental Positiva)
- **Directory:** `amp/`
- **Port:** 3003
- **Stack:** Next.js 14
- **Status:** **PAUSED**
- **Description:** Spanish-language personal development platform. Hybrid of Mindvalley + PuraMente + John Maxwell. Features: 21-day challenges ("Retos AMP"), guided meditations, leadership masterclasses, community. Freemium + Premium ($4.99/mo) + Pro ($14.99/mo) + B2B. Domain: actitudmentalpositiva.com.
- **Spec:** `docs/AMP_BUILD_PROMPT.md`

### 9. ContractorForge Web
- **Directory:** `contractorforge_web/`
- **Port:** 3001 (shares with WorkroomForge)
- **Stack:** Next.js 15
- **Status:** **BUILT**
- **Description:** Contractor/quote management portal. Universal SaaS for service businesses — AI intake forms, photo-based measurements, smart quoting, job management, scheduling, invoicing.

### 10. ContractorForge Backend
- **Directory:** `contractorforge_backend/`
- **Stack:** Python, FastAPI, OpenCV, ML models, Stripe
- **Status:** **BUILT**
- **Description:** Backend for ContractorForge with ML-based measurement from photos, email service, Stripe payments.

### 11. MarketForge App (Mobile)
- **Directory:** `market_forge_app/`
- **Stack:** Flutter (Dart)
- **Status:** **BUILT**
- **Description:** Flutter mobile app for multi-marketplace listing. Camera integration, AI-powered suggestions, ShipForge shipping (rate comparison, label purchase, tracking). Facebook Marketplace fully implemented; eBay, Craigslist, Amazon, Etsy coming.
- **Roadmap:** Q1 2026 skeleton → Q4 2026 app store release.

### 12. MarketF Web
- **Directory:** `marketf_web/`
- **Port:** 3001
- **Stack:** Next.js 15, Stripe
- **Status:** **BUILT**
- **Description:** P2P marketplace platform (alternative to eBay). Stripe Connect payments, buyer/seller matching, 8% fees (vs eBay 12.9%). Projected Y3 revenue: $8.65M (50% of total).
- **Spec:** `docs/MARKETF_OVERVIEW.md`

### 13. Command Center
- **Directory:** `command_center/`
- **Stack:** Static HTML, Docker
- **Status:** **BUILT**
- **Description:** Earlier version of command center UI (29KB HTML). Has Dockerfile for containerized deployment.

### 14. Empire Control
- **Directory:** `empire-control/`
- **Port:** 3000
- **Stack:** Next.js 14
- **Status:** **BUILT**
- **Description:** Control/administration interface. Separate from founder_dashboard and empire-app.

---

## Standalone Modules (Part of Empire App)

### 15. Inventory Module
- **Directory:** `inventory/`
- **Port:** 3004
- **Stack:** Next.js 14
- **Status:** **MODULE**
- **Description:** Inventory management. 33 pre-loaded items, categories, low-stock alerts. Also accessible at `empire-app/inventory`.

### 16. Finance Module
- **Directory:** `finance/`
- **Port:** 3005
- **Stack:** Next.js 14
- **Status:** **MODULE**
- **Description:** Income/expense tracking, quote tracking, invoice generation, profit margins. Also at `empire-app/finance`.

### 17. Creations Module
- **Directory:** `creations/`
- **Port:** 3006
- **Stack:** Next.js 14
- **Status:** **MODULE**
- **Description:** R&D and innovation ideas lab. Also at `empire-app/creations`.

### 18. CRM Module
- **Directory:** `crm/`
- **Port:** 3007
- **Stack:** Next.js 14
- **Status:** **MODULE**
- **Description:** Customer relationship management. Also at `empire-app/customers`.

---

## Infrastructure & Tooling

### 19. EmpireBox Installer (Founders USB)
- **Directory:** `founders_usb_installer/`
- **Stack:** Shell, Docker Compose, JSON config
- **Status:** **INTERNAL ONLY**
- **Description:** Master control USB installer for Beelink EQR5 (Ryzen 7 5825U, 32GB RAM). Installs Ubuntu 24.04, Docker, Ollama, OpenClaw, all 13 products. Ventoy USB, unattended install. Default SSH: `empirebox@empirebox.local`.
- **Contains:** `config.json` defining all 13 products, bundles, Docker services.

### 20. EmpireBox Setup Portal
- **Directory:** `empirebox_setup/`
- **Stack:** Next.js, Shell, systemd
- **Status:** **BUILT**
- **Description:** Headless setup system for EmpireBox Mini PCs. Discovery via QR code, mDNS, Bluetooth LE, USB config. No monitor needed.

### 21. EmpireBox Installer (Generic)
- **Directory:** `empirebox_installer/`
- **Stack:** Shell, Docker
- **Status:** **BUILT**
- **Description:** Automated installer with contracts, installation scripts, empirebox setup.

### 22. Agent Framework
- **Directory:** `agents/`
- **Stack:** Python
- **Status:** **BUILT**
- **Description:** Agent orchestrator framework with memory, config, and built-in agent definitions.

### 23. Empire Box Agents (Safeguards)
- **Directory:** `empire_box_agents/`
- **Stack:** Python
- **Status:** **BUILT**
- **Description:** Agent safeguards and emergency stop system. Rate limiting, budget management, action whitelisting, state preservation, admin alerting, thread safety.

### 24. Hardware Documentation
- **Directory:** `hardware/`
- **Status:** **DOCS**
- **Description:** BOM, assembly guides, Mini PC options for 3 tiers: Starter ($299, Intel N100), Business ($599, Ryzen 7 6800H), Enterprise ($1,299, Core i7). BIOS settings, Ubuntu installation, networking.

### 25. EmpireBox Website
- **Directory:** `website/`
- **Stack:** Static HTML + Next.js 15
- **Status:** **BUILT**
- **Description:** Marketing website — "The Operating System for Resellers". Hero, features, pricing tiers, testimonials, FAQ. Vercel deployment ready.

---

## Browser Extensions / External Tools

### 26. ClaudeForge
- **Directory:** `products/claudeforge/`
- **Status:** **DEVELOPMENT**
- **Description:** Persistent chat storage with session management for Claude. Contains chat history archives.

### 27. CoPilotForge
- **Directory:** `products/copilotforge/`
- **Stack:** Firefox extension (XPI), native bridge
- **Status:** **DEVELOPMENT**
- **Description:** Browser extension for AI coding session management. Firefox-compatible with native bridge component.

---

## Spec-Only Products (No Codebase Yet)

### 28. CraftForge
- **Spec:** `docs/CRAFTFORGE_SPEC.md` (804 lines)
- **Status:** **SPEC READY**
- **Description:** AI-powered CNC design platform. Text→CNC, Photo→CNC, 3D Scan→CNC, Template Library. G-code generation, machine profiles, cost estimation, CNC simulation, marketplace for buying/selling plans. SaaS: Free, Hobby ($29/mo), Pro ($79/mo), Business ($199/mo).
- **Addendum:** `docs/CRAFTFORGE_SPACESCAN_ADDENDUM.md`

### 29. SocialForge
- **Port:** 3004 (planned), Docker 8090
- **Status:** **PLANNED**
- **Description:** Social media management and automated posting across Facebook, Instagram, Twitter, LinkedIn. Y3 revenue projection: $800K.

### 30. SupportForge
- **Status:** **PLANNED**
- **Description:** AI-powered customer support and ticketing. Multi-channel with automated responses. Backend already has `/api/v1/tickets/*` routes.

### 31. LLCFactory
- **Port:** 8100 (Docker)
- **Status:** **PLANNED**
- **Description:** Automated LLC formation and business registration. Partner with Northwest Registered Agents. Y3 revenue: $2M.

### 32. ApostApp
- **Port:** 8110 (Docker)
- **Status:** **PLANNED**
- **Description:** Document apostille and legalization services. Shared document filler with LLCFactory. Y3 revenue: $1.5M.

### 33. ShipForge
- **Port:** 8060 (Docker)
- **Status:** **INTEGRATED**
- **Description:** Shipping integration via EasyPost. Rate comparison (USPS, FedEx, UPS), label purchase, tracking. Embedded in MarketForge and MarketF, not standalone.
- **Spec:** `docs/SHIPPING_INTEGRATION.md`

### 34. EmpireAssist
- **Port:** 8120 (Docker)
- **Spec:** `docs/EMPIRE_ASSIST_SPEC.md`
- **Status:** **SPECIFIED**
- **Description:** Telegram/WhatsApp messenger integration. Manage business via chat: orders, inventory, revenue, photo listings, shipping labels, calendar, support tickets, voice notes.

### 35. EmpirePay / CryptoPay
- **Port:** 8130 (Docker)
- **Spec:** `docs/CRYPTO_PAYMENTS_SPEC.md`
- **Status:** **SPECIFIED**
- **Description:** Multi-gateway payments. Stripe, PayPal, multi-chain crypto (Solana priority, BNB, Cardano, ETH). 15% crypto discount, 20% for $EMPIRE token. NFT license minting.

### 36. VetForge (VA Disability App)
- **Spec:** `docs/VA_APP_TELEHEALTH.md`
- **Status:** **SPECIFIED**
- **Description:** VA disability claim assistance with telehealth consultations. HIPAA-compliant, licensed providers.

### 37. RecoveryForge
- **Status:** **CONCEPT**
- **Description:** Addiction recovery support. Daily check-ins, support groups, resource directory, crisis intervention. HIPAA-compliant.

---

## Shared / Utility Directories

| Directory | Purpose |
|-----------|---------|
| `shared/` | Shared React components (TopNav.tsx) |
| `max/` | MAX persistent memory (memory.md) |
| `config/` | Service configurations |
| `scripts/` | Utility scripts (seed_brain.py, start_brain.sh) |
| `uploads/` | Uploaded files (images, documents, code, audio) |
| `logs/` | Session logs by date |
| `docs/` | All specs and documentation |
| `data/` | Runtime data (chats, quotes) |
| `icons/` | App icons and assets |
| `assets/` | Shared assets |
| `issues/` | Issue tracking |
| `saves/` | Session snapshots |
| `versions/` | Version archives (v1.0.0 through v2.0.0) |
| `venv/` | Shared Python virtualenv |

---

## Port Map

| Port | Service | Status |
|------|---------|--------|
| 3000 | Empire App (unified) | Active |
| 3001 | WorkroomForge | Active |
| 3002 | LuxeForge Web | Active |
| 3003 | AMP | Paused |
| 3004 | Inventory / SocialForge | Module |
| 3005 | Finance | Module |
| 3006 | Creations | Module |
| 3007 | CRM | Module |
| 3009 | Founder Dashboard | Active |
| 7878 | OpenClaw AI | Active |
| 8000 | Backend API (FastAPI) | Active |
| 8080 | Homepage (static) | Active |
| 11434 | Ollama | Active |
| 8010 | MarketForge (Docker) | Planned |
| 8020 | ContractorForge (Docker) | Built |
| 8030 | LuxeForge (Docker) | Planned |
| 8040 | SupportForge (Docker) | Planned |
| 8050 | LeadForge (Docker) | Planned |
| 8060 | ShipForge (Docker) | Integrated |
| 8070 | ForgeCRM (Docker) | Planned |
| 8080 | RelistApp (Docker) | Planned |
| 8090 | SocialForge (Docker) | Planned |
| 8100 | LLCFactory (Docker) | Planned |
| 8110 | ApostApp (Docker) | Planned |
| 8120 | EmpireAssist (Docker) | Planned |
| 8130 | EmpirePay (Docker) | Planned |

---

## Crypto / Tokenomics

- **$EMPIRE Token:** Solana SPL, 1B supply, utility + governance
- **Spec:** `docs/EMPIRE_TOKEN_SPEC.md`
- **NFT Licenses:** All EmpireBox licenses minted as Solana NFTs
- **Spec:** `docs/EMPIRE_LICENSE_NFT_SPEC.md`
- **Revenue Model:** `docs/REVENUE_MODEL.md` — Y3 aspirational $17.2M

---

## Key Specs Index

| Spec | File |
|------|------|
| MAX Brain | `docs/MAX_BRAIN_SPEC.md` |
| CraftForge | `docs/CRAFTFORGE_SPEC.md` |
| CraftForge SpaceScan | `docs/CRAFTFORGE_SPACESCAN_ADDENDUM.md` |
| Visual Mockup Engine | `docs/VISUAL_MOCKUP_ENGINE_SPEC.md` |
| MAX Response Canvas v2 | `docs/MAX_RESPONSE_CANVAS_SPEC_v2.md` |
| LeadForge | `docs/LEADFORGE_SPEC.md` |
| EmpireAssist | `docs/EMPIRE_ASSIST_SPEC.md` |
| AMP Build | `docs/AMP_BUILD_PROMPT.md` |
| Crypto Payments | `docs/CRYPTO_PAYMENTS_SPEC.md` |
| EMPIRE Token | `docs/EMPIRE_TOKEN_SPEC.md` |
| NFT Licenses | `docs/EMPIRE_LICENSE_NFT_SPEC.md` |
| Revenue Model | `docs/REVENUE_MODEL.md` |
| MarketF Overview | `docs/MARKETF_OVERVIEW.md` |
| Shipping Integration | `docs/SHIPPING_INTEGRATION.md` |
| VA Telehealth | `docs/VA_APP_TELEHEALTH.md` |
| Ecosystem | `docs/ECOSYSTEM.md` |
| Zero to Hero | `docs/ZERO_TO_HERO_SPEC.md` |
