# Empire Product Directory

**Last Updated:** February 28, 2026
**Source:** Full scan of BACKUP11/EMPIRE/docs/, ~/Empire/ codebase, and all spec documents
**Total Products:** 30+ across 8 categories

---

## Table of Contents

1. [Core Platform](#1-core-platform)
2. [Forge Products (Business Tools)](#2-forge-products)
3. [Revenue Generator Products](#3-revenue-generator-products)
4. [Service & Specialized Products](#4-service--specialized-products)
5. [Tokenomics & Web3](#5-tokenomics--web3)
6. [Hardware](#6-hardware)
7. [Infrastructure & AI](#7-infrastructure--ai)
8. [Content & Media](#8-content--media)
9. [Revenue Projections Summary](#9-revenue-projections-summary)
10. [File Location Index](#10-file-location-index)

---

## 1. Core Platform

### EmpireBox (Central SaaS Platform)
| Field | Detail |
|-------|--------|
| **Description** | Central subscription platform — billing, user management, unified dashboard, license system |
| **Status** | Active Development |
| **Tech Stack** | FastAPI backend (Python 3.12) + Next.js 14 frontend |
| **Ports** | Backend: 8000, Founder Dashboard: 3009, Empire App: 3000 |
| **Code** | `~/Empire/backend/`, `~/Empire/empire-app/`, `~/Empire/founder_dashboard/` |
| **Docs** | `ECOSYSTEM.md`, `DEPLOYMENT.md`, `SETUP.md` |
| **Subscription Tiers** | Solo ($79/mo), Pro ($249/mo), Enterprise ($599/mo), Founder Lifetime ($2,500) |

### MAX (AI Assistant Manager)
| Field | Detail |
|-------|--------|
| **Description** | Central AI assistant — multi-model routing (Grok → Claude → Ollama), brain memory, task delegation, Telegram bot, TTS voice |
| **Status** | Active Development — fully functional |
| **Tech Stack** | FastAPI router, SSE streaming, edge-tts voice, Whisper transcription |
| **Code** | `~/Empire/backend/app/routers/max/`, `~/Empire/backend/app/services/max/` |
| **Docs** | `MAX_BRAIN_SPEC.md`, `TELEGRAM_SETUP.md` |
| **Key Features** | Brain memory (ChromaDB + Ollama embeddings), AI Desk delegation, token/cost tracking, guardrails, tool execution |
| **Endpoints** | `/max/chat`, `/max/chat/stream`, `/max/tts`, `/max/brain/status`, `/max/ai-desks/*`, `/max/tokens/*` |

### OpenClaw (AI Brain Engine)
| Field | Detail |
|-------|--------|
| **Description** | Skills-augmented local AI engine — Ollama wrapper powering all AI features across the ecosystem |
| **Status** | Active — running on port 7878 |
| **Tech Stack** | Python, Ollama integration |
| **Code** | `~/Empire/openclaw/` |
| **Docs** | `ECOSYSTEM.md` |
| **Key Features** | Natural language conversation intake, cross-product intelligence, image analysis, learning system |

### Founder Dashboard (Command Center)
| Field | Detail |
|-------|--------|
| **Description** | Founder-focused interface for MAX AI chat, system monitoring, desk management, token tracking |
| **Status** | Active Development — fully functional |
| **Tech Stack** | Next.js 14, Tailwind CSS, SSE streaming |
| **Port** | 3009 |
| **Code** | `~/Empire/founder_dashboard/` |
| **Key Features** | Chat with MAX, AI Desk grid, Ollama/Brain status, token cost panel, voice playback, conversation history |

### Empire App (Unified Dashboard)
| Field | Detail |
|-------|--------|
| **Description** | All-in-one business management dashboard with full modules |
| **Status** | Active Development |
| **Tech Stack** | Next.js 14 |
| **Port** | 3000 |
| **Code** | `~/Empire/empire-app/` |
| **Modules** | `/inventory`, `/finance`, `/customers`, `/workroom`, `/creations`, `/tasks`, `/shipping`, `/max`, `/settings` |

---

## 2. Forge Products

### WorkroomForge (CraftForge)
| Field | Detail |
|-------|--------|
| **Description** | Quote builder + AI photo analysis for custom window treatments, furniture, upholstery |
| **Status** | Active Development |
| **Tech Stack** | Next.js |
| **Port** | 3001 |
| **Code** | `~/Empire/workroomforge/` |
| **Docs** | `CRAFTFORGE_SPEC.md`, `CRAFTFORGE_SPACESCAN_ADDENDUM.md` |
| **Key Features** | AI-powered measurements from photos, quote generation, material tracking, job scheduling |

### LuxeForge
| Field | Detail |
|-------|--------|
| **Description** | Designer portal for high-end service businesses — luxury branding, premium client management |
| **Status** | Active Development |
| **Tech Stack** | Next.js 15 |
| **Port** | 3002 |
| **Code** | `~/Empire/luxeforge_web/` |
| **Docs** | `ECOSYSTEM.md`, `LEADFORGE_SPEC.md` (LeadForge is embedded) |

### MarketForge
| Field | Detail |
|-------|--------|
| **Description** | Intelligent listing creation — AI descriptions, photo enhancement, multi-marketplace publishing |
| **Status** | Planned — Flutter mobile app + backend models exist |
| **Tech Stack** | Flutter (mobile), FastAPI (backend) |
| **Code** | `~/Empire/market_forge_app/` (Flutter), BACKUP11: `backend/app/models/marketplace/` |
| **Docs** | `MARKETF_OVERVIEW.md`, `MARKETF_API.md`, `MARKETF_FEES.md`, `MARKETF_SELLER_GUIDE.md`, `MARKETF_AMAZON_SPEC.md`, `MARKETFORGE_AD_STUDY.md` |
| **Revenue Y3** | $1.9M (11%) |
| **Pricing** | Free (5 listings), Starter $19/mo, Pro $39/mo, Business $99/mo |
| **Killer Feature** | "Snap, List, Done!" — barcode scan or photo → AI auto-fills complete listing |

### ContractorForge
| Field | Detail |
|-------|--------|
| **Description** | Project/contract management for service contractors — job management, scheduling, quotes, invoicing |
| **Status** | Backend exists on BACKUP11 |
| **Code** | BACKUP11: `contractorforge_backend/`, `contractorforge_web/` |
| **Docs** | `INDUSTRY_TEMPLATES.md`, `ECOSYSTEM.md` |
| **Key Features** | Photo measurements, material tracking, customizable industry templates (plumbing, electrical, landscaping) |

### SupportForge
| Field | Detail |
|-------|--------|
| **Description** | AI-powered customer support — ticket management, multi-channel support, knowledge base |
| **Status** | Database models exist, AI desk placeholder built |
| **Code** | BACKUP11: `backend/app/models/supportforge_*.py` (8 model files), `backend/alembic/versions/supportforge_001_*.py` |
| **Docs** | Root-level `SUPPORTFORGE_*.md` files on BACKUP11 |
| **DB Models** | `supportforge_ticket`, `supportforge_customer`, `supportforge_agent`, `supportforge_kb`, `supportforge_message`, `supportforge_automation`, `supportforge_integration`, `supportforge_tenant` |

### SocialForge
| Field | Detail |
|-------|--------|
| **Description** | Social media management and automation — multi-platform posting, content calendar, analytics |
| **Status** | AI Desk placeholder built, full product planned |
| **Code** | `~/Empire/backend/app/services/max/desks/social_desk.py` |
| **Docs** | `ECOSYSTEM.md`, `ZERO_TO_HERO_SPEC.md` |
| **Revenue Y3** | $800K (5%) |
| **Pricing** | Starter $19/mo, Pro $49/mo, Business $99/mo |
| **Platforms** | Facebook, Instagram, Twitter, LinkedIn |
| **Approach** | Semi-automatic — user confirms each platform creation |

### ShipForge
| Field | Detail |
|-------|--------|
| **Description** | Shipping solutions — rate comparison, label generation, package tracking |
| **Status** | Planned |
| **Docs** | `SHIPPING_INTEGRATION.md`, `ECOSYSTEM.md` |
| **Integration** | EasyPost API for discounted carrier rates |

### LeadForge
| Field | Detail |
|-------|--------|
| **Description** | AI-powered lead generation — embedded inside ContractorForge & LuxeForge (not standalone) |
| **Status** | Spec complete, not yet built |
| **Docs** | `LEADFORGE_SPEC.md` |
| **Key Features** | Scrape directories, AI lead scoring (1-100), automated outreach, appointment booking, CRM integration |
| **Lead Sources** | ASID directory, Houzz Pro, AIA, builder associations, Zillow, WeddingWire |
| **Tier Access** | Solo: 50 leads/mo, Pro: full access, Enterprise: unlimited |

### ForgeCRM
| Field | Detail |
|-------|--------|
| **Description** | CRM integrated across all Forge products — contacts, pipeline, campaigns |
| **Status** | Planned — freemium model |
| **Docs** | `ECOSYSTEM.md` |

### ElectricForge / LandscapeForge
| Field | Detail |
|-------|--------|
| **Description** | Industry-specific templates for ContractorForge |
| **Status** | Template specs exist |
| **Docs** | `INDUSTRY_TEMPLATES.md` |

---

## 3. Revenue Generator Products

### MarketF (P2P Marketplace)
| Field | Detail |
|-------|--------|
| **Description** | Peer-to-peer marketplace with escrow, Stripe Connect payments, ratings, dispute resolution |
| **Status** | Database models exist on BACKUP11 |
| **Code** | BACKUP11: `backend/app/models/marketplace/` (category, dispute, escrow, order, product, review), `marketf_web/` |
| **Docs** | `MARKETF_OVERVIEW.md`, `MARKETF_FEES.md`, `MARKETF_API.md`, `MARKETF_SELLER_GUIDE.md`, `MARKETF_AMAZON_SPEC.md` |
| **Revenue Y3** | $8.65M (50% of total — primary revenue driver) |
| **Business Model** | 5-10% seller fee, 2-3% buyer protection, premium subscriptions $29-99/mo |

### LLCFactory
| Field | Detail |
|-------|--------|
| **Description** | Automated LLC formation service + ongoing compliance |
| **Status** | Planned — part of Zero to Hero flow |
| **Docs** | `ZERO_TO_HERO_SPEC.md`, `REVENUE_MODEL.md` |
| **Revenue Y3** | $2M (12%) |
| **Business Model** | Formation $149 + state fees, registered agent $100/yr, compliance $49/yr, amendments $99 |
| **Partner** | Northwest Registered Agents for state filings |

### RelistApp
| Field | Detail |
|-------|--------|
| **Description** | Automated relisting for expired marketplace listings — smart scheduling, bulk operations |
| **Status** | Planned |
| **Docs** | `REVENUE_MODEL.md`, `ECOSYSTEM.md` |
| **Revenue Y3** | $1.5M (9%) |
| **Pricing** | Basic $19/mo (100 listings), Pro $39/mo (500), Business $79/mo (unlimited) |

### ApostApp
| Field | Detail |
|-------|--------|
| **Description** | Document apostille and authentication service — international documents, notarization, translation |
| **Status** | Planned — shared document filler with LLCFactory |
| **Docs** | `REVENUE_MODEL.md`, `ECOSYSTEM.md` |
| **Revenue Y3** | $1.5M (9%) |
| **Pricing** | Single doc $149, package $299, rush +$100, translation $0.15/word |

---

## 4. Service & Specialized Products

### VeteranForge (VA Disability App)
| Field | Detail |
|-------|--------|
| **Description** | VA disability claim assistance via telehealth — licensed provider evaluations, HIPAA-compliant |
| **Status** | Legal compliance spec complete, no code yet |
| **Docs** | `VA_APP_TELEHEALTH.md` (544 lines — comprehensive legal framework) |
| **Files** | BACKUP11: `VetForge-PandT.pptx` (PowerPoint deck) |
| **Name Options** | VeteranForge (recommended), VetHelp Assist, ClaimForge |
| **Compliance** | HIPAA, 38 CFR VA regulations, state telehealth parity, multi-state provider licensing |
| **Conditions** | Best for: PTSD, depression, anxiety, dermatological, chronic pain. Requires in-person: musculoskeletal, cardiovascular, neurological |
| **Requirements** | HIPAA-compliant video (Doxy.me recommended), BAAs with all vendors, provider credentialing, malpractice insurance ($1M min) |

### RecoveryForge
| Field | Detail |
|-------|--------|
| **Description** | Addiction recovery support platform — daily check-ins, support groups, crisis tools |
| **Status** | Concept — mentioned in ecosystem docs |
| **Docs** | `ECOSYSTEM.md` |
| **Key Features** | Progress tracking, resource directory, crisis intervention, anonymous options |
| **Privacy** | HIPAA-compliant required |

### EmpireAssist
| Field | Detail |
|-------|--------|
| **Description** | AI-powered messenger integration — manage business via Telegram/WhatsApp/SMS |
| **Status** | Telegram bot active (part of MAX), WhatsApp/SMS planned |
| **Code** | `~/Empire/backend/app/services/max/telegram_bot.py` |
| **Docs** | `EMPIRE_ASSIST_SPEC.md` |
| **Pricing** | Basic (free, Telegram, 100 msg/mo), Pro ($19/mo + WhatsApp), Business ($49/mo + SMS + voice) |
| **Key Features** | Check orders/inventory via chat, create listings from photos, shipping labels, task management, voice notes |

---

## 5. Tokenomics & Web3

### EMPIRE Token ($EMPIRE)
| Field | Detail |
|-------|--------|
| **Description** | Solana SPL utility + governance token |
| **Status** | Spec complete, not minted |
| **Docs** | `EMPIRE_TOKEN_SPEC.md` |
| **Supply** | 1,000,000,000 (1 billion), 9 decimals |
| **Distribution** | Community 40%, Rewards 30%, Team 15% (2yr vest), Liquidity 10%, Treasury 5% |
| **Utility** | 20% subscription discount, 6% marketplace fee (vs 8%), staking, governance, referral rewards, NFT license purchases |
| **DEX Strategy** | Raydium/Orca → Jupiter → CoinGecko/CMC → CEX (if volume warrants) |

### NFT License System
| Field | Detail |
|-------|--------|
| **Description** | All EmpireBox licenses are Solana NFTs — transferable, verifiable, upgradeable |
| **Status** | Spec complete, not implemented |
| **Docs** | `EMPIRE_LICENSE_NFT_SPEC.md` |
| **Tiers** | Solo $79/mo, Pro $249/mo, Enterprise $599/mo, Founder Lifetime $2,500 |
| **Discounts** | Crypto 15% off, EMPIRE token 20% off |
| **Royalties** | 5% on all secondary market resales |
| **Metadata** | On-chain: tier, products, billing, issue/expiry dates, transfer count |
| **Editions** | Standard, Founder (first 1K, gold art), OG (first 100, platinum), Partner (top referrers) |
| **Secondary** | Magic Eden, Tensor, wallet-to-wallet, EmpireBox official resale |

### Multi-Chain Crypto Payments
| Field | Detail |
|-------|--------|
| **Description** | Optional crypto checkout with per-order HD wallet addresses |
| **Status** | Spec + DB schema complete |
| **Docs** | `CRYPTO_PAYMENTS_SPEC.md` |
| **Chains** | Solana (#1), BNB Chain (#2), Cardano (#3), Ethereum (#4) |
| **Discounts** | 15% off crypto, 20% off $EMPIRE |
| **Architecture** | HD wallet per order, blockchain monitoring, transparency ledger |
| **DB Tables** | `crypto_payments`, `crypto_ledger` |

### Empire Wallet
| Field | Detail |
|-------|--------|
| **Description** | Custodial Solana wallet for non-crypto users — seamless crypto payments without complexity |
| **Status** | Planned |
| **Docs** | `ECOSYSTEM.md` |

---

## 6. Hardware

### Full specs: `EMPIRE_BOX_HARDWARE_SPEC.md` (608 lines) + `HARDWARE_BUNDLES.md`

### Budget Mobile Bundle — $349
| Field | Detail |
|-------|--------|
| **Phone** | Xiaomi Redmi Note 13 (6.67" AMOLED, 120Hz, Snapdragon 685, 8GB/256GB, 108MP) |
| **Software** | MarketForge Lite (12 months, $29/mo value) |
| **Target** | Entry-level resellers, students, side hustlers |
| **Margin** | Loss leader (-$204), break-even month 7 |
| **Sourcing** | Alibaba (Shenzhen Global Tech), MOQ 100, $180/unit FOB |

### Seeker Pro Bundle — $599 (Flagship)
| Field | Detail |
|-------|--------|
| **Phone** | Solana Seeker (6.53" OLED, Snapdragon 765G, 12GB/512GB, Seed Vault hardware wallet) |
| **Software** | MarketForge Pro (12 months, $59/mo value) |
| **Target** | Serious resellers, crypto enthusiasts |
| **Margin** | Loss leader (-$499), break-even month 9 |
| **Sourcing** | Direct from Solana Foundation/OSOM, $350 partnership pricing |

### Full Empire Bundle — $899
| Field | Detail |
|-------|--------|
| **Phone** | Solana Seeker (same as Pro) |
| **Mini PC** | Beelink Mini S12 Pro (Intel N100, 16GB, 500GB NVMe, WiFi 6) |
| **Software** | MarketForge Empire (12 months, $99/mo value) |
| **Target** | Professional power sellers ($10K+/mo) |
| **Pre-configured Agents** | Price Optimizer, Inventory Scout, Smart Crosslister, Message Responder, Analytics Dashboard |
| **Margin** | Loss leader (-$879), break-even month 9 |

### Accessories
| Item | Detail |
|------|--------|
| **Quick Start Card** | 3.5"x2" laminated with QR → `empirebox.store/setup/[LICENSE-KEY]` |
| **Inventory Scanner** | Bluetooth/USB barcode/QR scanner add-on |
| **Empire Tablet** | Larger screen for ContractorForge, warehouse management |

---

## 7. Infrastructure & AI

### AI Desk Delegation System
| Field | Detail |
|-------|--------|
| **Description** | AI-powered task routing to specialized desks — ForgeDesk, MarketDesk, SocialDesk, SupportDesk |
| **Status** | Active — ForgeDesk fully functional, others placeholder |
| **Code** | `~/Empire/backend/app/services/max/desks/` |
| **Docs** | `AI_DESK_DELEGATION_PLAN.md` |
| **Routing** | LLM classification (Ollama Mistral, >=0.6 confidence) + keyword fallback |

### MAX Brain (Memory System)
| Field | Detail |
|-------|--------|
| **Description** | Persistent memory for MAX — ChromaDB vector store, Ollama embeddings, context-aware retrieval |
| **Status** | Active |
| **Code** | `~/Empire/backend/app/services/max/brain/` |
| **Docs** | `MAX_BRAIN_SPEC.md` |
| **Storage** | External drive `/media/rg/BACKUP11/ollama/brain/` |

### Token/Cost Tracker
| Field | Detail |
|-------|--------|
| **Description** | Track API token usage, costs, budget alerts, auto-switch to local models |
| **Status** | Active |
| **Code** | `~/Empire/backend/app/services/max/token_tracker.py` |

### TTS Service
| Field | Detail |
|-------|--------|
| **Description** | Text-to-speech for MAX — edge-tts (free, no API key), en-US-GuyNeural voice |
| **Status** | Active |
| **Code** | `~/Empire/backend/app/services/max/tts_service.py` |
| **Outputs** | MP3 for web playback, MP3 for Telegram voice notes |

### Agent Safeguards
| Field | Detail |
|-------|--------|
| **Description** | Production safety for autonomous agents — rate limiting, emergency stop, approval workflows, audit logging |
| **Status** | Active |
| **Code** | `~/Empire/backend/app/services/max/guardrails.py` |

### Homepage (Navigation Hub)
| Field | Detail |
|-------|--------|
| **Description** | Static HTML hub linking all Empire services |
| **Port** | 8080 |
| **Code** | `~/Empire/homepage/` |

---

## 8. Content & Media

### AMP (Actitud Mental Positiva)
| Field | Detail |
|-------|--------|
| **Description** | Spanish-language personal development platform — hybrid of Mindvalley + PuraMente + John Maxwell |
| **Status** | Next.js scaffolding exists, needs revival |
| **Domain** | actitudmentalpositiva.com |
| **Tech Stack** | Next.js 14, Tailwind CSS |
| **Port** | 3003 |
| **Code** | `~/Empire/amp/` (scaffolded, default README) |
| **Docs** | `AMP_BUILD_PROMPT.md` (250 lines — full build specification) |
| **Business Model** | Freemium: Free daily content, Premium $4.99/mo, Pro $14.99/mo (+ 1:1 coaching), Empresas B2B custom |
| **Content** | 21-day challenges ("Retos"), guided meditations, leadership masterclasses, Coach AMP certification |
| **Three Pillars** | Mentalidad (mindset), Bienestar (wellness), Liderazgo (leadership) |
| **Revenue Y2** | Target $25K MRR (50K free users, 2.5K premium, 200 pro, 20 B2B) |

### EmpireBox Website
| Field | Detail |
|-------|--------|
| **Description** | Marketing website with legal pages, pricing, contact |
| **Status** | Exists on BACKUP11 |
| **Code** | BACKUP11: `website/` |
| **Legal Pages** | Privacy, Terms, Refund Policy, Contact — all present and Stripe-compliant |

---

## 9. Revenue Projections Summary

### Year 3 Projections (from REVENUE_MODEL.md)

| Product | Conservative | Moderate | Aspirational |
|---------|-------------|----------|-------------|
| **MarketF** | $1.7-2.6M | $4.3M | $8.65M |
| **LLCFactory** | $400-600K | $1M | $2M |
| **MarketForge** | $380-570K | $950K | $1.9M |
| **RelistApp** | $300-450K | $750K | $1.5M |
| **ApostApp** | $300-450K | $750K | $1.5M |
| **SocialForge** | $160-240K | $400K | $800K |
| **Other** | $170-255K | $425K | $850K |
| **TOTAL** | **$3.4-5.2M** | **$8.6M** | **$17.2M** |

### Growth Trajectory
- **Year 1:** $500K-750K ARR (product-market fit)
- **Year 2:** $1.5M-2.5M ARR (scale what works)
- **Year 3:** $3.4M-17.2M ARR (depending on scenario)

### Gross Margins
- SaaS Products: 70-80%
- Marketplace (MarketF): 60-70%
- Service Products (LLCFactory, ApostApp): 50-60%

---

## 10. File Location Index

### Spec Documents (`~/Empire/docs/`)
| Document | Content |
|----------|---------|
| `ECOSYSTEM.md` | Master product catalog (23+ products) |
| `REVENUE_MODEL.md` | Full revenue projections, cost structure, fundraising |
| `ZERO_TO_HERO_SPEC.md` | Complete business automation flow (676 lines) |
| `EMPIRE_BOX_HARDWARE_SPEC.md` | 4-tier hardware spec, BOM, margins (608 lines) |
| `HARDWARE_BUNDLES.md` | Original 3-bundle hardware spec with sourcing |
| `EMPIRE_TOKEN_SPEC.md` | $EMPIRE token details, distribution, DEX |
| `EMPIRE_LICENSE_NFT_SPEC.md` | NFT license tiers, metadata, secondary market |
| `CRYPTO_PAYMENTS_SPEC.md` | Multi-chain payments, DB schema, architecture |
| `LEADFORGE_SPEC.md` | Lead generation module spec |
| `VA_APP_TELEHEALTH.md` | VeteranForge legal/HIPAA compliance (544 lines) |
| `AMP_BUILD_PROMPT.md` | AMP platform full build spec (250 lines) |
| `STRIPE_COMPLIANCE_CHECKLIST.md` | Stripe merchant approval checklist |
| `LEGAL_COMPLIANCE_AUDIT.md` | Full legal audit — FTC, GDPR, CCPA, IP |
| `MARKETFORGE_AD_STUDY.md` | $5K ad budget allocation, CAC benchmarks |
| `CRAFTFORGE_SPEC.md` | WorkroomForge/CraftForge spec |
| `MAX_BRAIN_SPEC.md` | MAX memory and brain architecture |
| `AI_DESK_DELEGATION_PLAN.md` | AI desk system design |
| `EMPIRE_ASSIST_SPEC.md` | EmpireAssist messenger integration |
| `INDUSTRY_TEMPLATES.md` | ContractorForge template system |
| `MARKETF_OVERVIEW.md` | MarketF marketplace overview |
| `MARKETF_API.md` | MarketF API spec |
| `MARKETF_FEES.md` | MarketF fee structure |
| `MARKETF_SELLER_GUIDE.md` | MarketF seller guide |
| `MARKETF_AMAZON_SPEC.md` | Amazon compliance for MarketF |
| `SHIPPING_INTEGRATION.md` | ShipForge shipping spec |
| `SOLANA_PARTNERSHIP.md` | Solana ecosystem partnerships |
| `BRAND_GUIDELINES.md` | Branding standards |

### Code Directories (Active — `~/Empire/`)
| Directory | Product | Port |
|-----------|---------|------|
| `backend/` | FastAPI backend + MAX | 8000 |
| `founder_dashboard/` | Founder Command Center | 3009 |
| `empire-app/` | Unified Dashboard | 3000 |
| `workroomforge/` | WorkroomForge/CraftForge | 3001 |
| `luxeforge_web/` | LuxeForge Designer Portal | 3002 |
| `openclaw/` | OpenClaw AI Engine | 7878 |
| `homepage/` | Static Navigation Hub | 8080 |
| `amp/` | AMP Personal Development | 3003 |
| `market_forge_app/` | MarketForge Flutter App | — |
| `max/` | MAX persistent memory | — |

### Code Directories (BACKUP11 Only)
| Directory | Product |
|-----------|---------|
| `contractorforge_backend/` | ContractorForge API |
| `contractorforge_web/` | ContractorForge Frontend |
| `marketf_web/` | MarketF Marketplace Frontend |
| `website/` | EmpireBox Marketing Website |
| `command_center/` | Old Command Center (replaced by founder_dashboard) |
| `empire-control/` | Old Empire Control |
| `empirebox_setup/` | EmpireBox Setup Wizard |
| `founders_usb_installer/` | USB installer for hardware bundles |
| `empirebox_installer/` | EmpireBox installer |
| `empire_box_agents/` | Agent system |
| `hardware/` | Hardware specs and designs |

### Key Backend Files (SupportForge — BACKUP11)
```
backend/app/models/supportforge_ticket.py
backend/app/models/supportforge_customer.py
backend/app/models/supportforge_agent.py
backend/app/models/supportforge_kb.py
backend/app/models/supportforge_message.py
backend/app/models/supportforge_automation.py
backend/app/models/supportforge_integration.py
backend/app/models/supportforge_tenant.py
backend/alembic/versions/supportforge_001_add_supportforge_tables.py
```

### Other Notable Files
| File | Location | Content |
|------|----------|---------|
| `VetForge-PandT.pptx` | BACKUP11 root + versions/ | VeteranForge pitch deck |
| `Idea started after video from Alex Fin.pdf` | BACKUP11/EMPIRE/Empire/ | Original inspiration doc |
| `ZERO_TO_HERO_SPECIFICATION_Version7.md` | BACKUP11/EMPIRE/Empire/ | Older version of Zero to Hero |

---

## Compliance & Legal Status

| Area | Status | Key Doc |
|------|--------|---------|
| Stripe/Payments | Strong (placeholders need replacing) | `STRIPE_COMPLIANCE_CHECKLIST.md` |
| Privacy (GDPR/CCPA) | Strong (cookie banner needed) | `LEGAL_COMPLIANCE_AUDIT.md` |
| Terms of Service | Strong | `LEGAL_COMPLIANCE_AUDIT.md` |
| FTC Compliance | Needs earnings disclaimers | `LEGAL_COMPLIANCE_AUDIT.md` |
| Copyright/IP | Needs trademark registration | `LEGAL_COMPLIANCE_AUDIT.md` |
| DMCA Policy | Missing — needs creation | `LEGAL_COMPLIANCE_AUDIT.md` |
| Open Source Licenses | All deps are MIT/BSD/Apache (safe) | `LEGAL_COMPLIANCE_AUDIT.md` |
| HIPAA (VeteranForge) | Full compliance framework documented | `VA_APP_TELEHEALTH.md` |
| Amazon Marketplace | Compliance checklist exists | `AMAZON_COMPLIANCE_CHECKLIST.md` |
| Marketplace APIs | eBay (low risk), Poshmark (high risk — no API) | `LEGAL_COMPLIANCE_AUDIT.md` |

---

## Ad Budget & Marketing

From `MARKETFORGE_AD_STUDY.md`:

| Channel | Budget | CPC | CAC Target |
|---------|--------|-----|------------|
| Meta (FB/IG) | $1,600 | $0.97-$2.50 | $50-$200 |
| Google Ads | $1,200 | $2.70-$5.30 | $75-$200 |
| TikTok | $800 | $0.20-$0.50 | $80-$250 |
| YouTube | $600 | $0.50-$2 | $100-$300 |
| Reddit | $400 | $0.50-$2 | $50-$150 |
| **Total** | **$5,000** | | |

**Decision Rules:** Kill channel if CAC > $150. Scale 2x if CAC < $50.

---

*This directory consolidates ALL Empire products, specs, code, and docs from both the active repo (`~/Empire/`) and backup drive (`/media/rg/BACKUP11/EMPIRE/`). All BACKUP11 docs already exist in the active repo — no missing specs to copy.*
