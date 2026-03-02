# Empire Box Hardware Spec

**Version:** 1.0
**Date:** February 28, 2026
**Status:** Product Specification — Ready for Sourcing

---

## What Is Empire Box?

Empire Box is a physical product — a pre-configured device sold with Empire software and a monthly subscription. The all-in-one AI business solution.

**"Shopify gave every business an online store. Empire Box gives every business an AI operations center."**

No other product ships a physical device with a local AI brain that knows your business, manages your customers, and runs your operations. CRMs track contacts. Empire Box runs your business.

---

## Hardware Tiers

### 1. Empire Box Mini — $299–399 + subscription

**The office brain. Always on, always learning.**

| Spec | Details |
|------|---------|
| Form Factor | Beelink-class mini PC |
| CPU | AMD Ryzen 5 5560U or Ryzen 7 5825U |
| RAM | 16–32 GB DDR4 |
| Storage | 256–500 GB NVMe SSD |
| External | Samsung T7 500GB USB brain drive |
| OS | Ubuntu 24.04 LTS (pre-installed) |
| Network | Gigabit Ethernet + Wi-Fi 6 |
| Power | 15–45W TDP |

**Pre-loaded software:**
- Empire Platform (all services via Docker)
- Ollama + local models (Llama 3.1 8B, nomic-embed-text)
- OpenClaw AI layer
- MAX Brain (persistent memory on USB brain drive)
- Founder Dashboard (port 3009)
- WorkroomForge / MarketForge / all Forge apps

**For:** Shop owners, service businesses, contractors, custom workrooms.
Sits in office/shop, always on, runs MAX 24/7. USB brain drive is portable — take your business memory anywhere.

**Recommended units:**
| Model | CPU | RAM | Price |
|-------|-----|-----|-------|
| Beelink Mini S12 Pro | Intel N100 | 8–16 GB | ~$169 |
| Beelink SER5 | Ryzen 5 5560U | 16 GB | ~$259 |
| Beelink EQR5 | Ryzen 7 5825U | 32 GB | ~$349 |

**BOM (Bill of Materials) — Starter Config:**
| Component | Model | Cost |
|-----------|-------|------|
| Mini PC | Beelink SER5 (Ryzen 5, 16GB, 500GB) | $259 |
| Brain Drive | Samsung T7 500GB | $60 |
| UPS | APC BE425M (425VA) | $50 |
| HDMI Cable | 6ft HDMI 2.0 | $8 |
| Quick Start Card | Laminated QR card | $2 |
| Packaging | Branded box + foam insert | $15 |
| **Total COGS** | | **$394** |
| **Retail Price** | | **$399** |
| **Margin** | | **$5 + subscription** |

---

### 2. Empire Box Tablet — $199–299 + subscription

**The field companion. Measure, photograph, quote on-site.**

| Spec | Details |
|------|---------|
| Device | Samsung Galaxy Tab A9+ or equivalent |
| Display | 10.1"+ LCD, 1920×1200 |
| CPU | Snapdragon 695 or better |
| RAM | 8 GB |
| Storage | 128–256 GB |
| Camera | 13MP+ rear (room photos, measurements) |
| LiDAR | Available on select models (SpaceScan compatible) |
| OS | Android 14 |

**Pre-installed:**
- Empire mobile app
- MarketForge camera listing
- CraftForge photo → CNC pipeline
- Visual Mockup Engine (room photo → treatment overlay)
- SpaceScan (LiDAR models — room scanning, auto-measurements)
- Telegram MAX integration

**For:** Field use — consultations, in-home measurements, customer presentations, photo-based quoting. Syncs to Empire Box Mini back at the shop.

---

### 3. Empire Box Phone — $149–199 + subscription

**MAX in your pocket. Run your business from anywhere.**

| Spec | Details |
|------|---------|
| Device | Android phone (Xiaomi Redmi Note 13 or Solana Seeker) |
| Display | 6.5"+ AMOLED |
| Camera | 50MP+ main |
| Network | 5G, unlocked all US carriers |
| Special | Solana Seeker includes Seed Vault hardware wallet |

**Pre-configured:**
- Empire mobile app
- Telegram MAX integration (text, voice, photo)
- Quick photo → listing pipeline
- Voice commands to MAX while driving
- Push notifications for escalated tasks, quote approvals
- CraftForge photo capture

**For:** On-the-go — text MAX, get morning briefings, approve quotes, snap photos for listings, voice commands while driving.

---

### 4. Empire Box Pro — $599–799 + subscription

**The powerhouse. Multiple users, larger models, serious AI.**

| Spec | Details |
|------|---------|
| Form Factor | High-spec mini PC |
| CPU | AMD Ryzen 9 7940HS or Intel i7-1360P |
| RAM | 64 GB DDR5 |
| Storage | 1 TB NVMe SSD |
| External | Samsung T7 Shield 2TB brain drive |
| GPU | Integrated Radeon 780M (or dedicated GPU option) |
| OS | Ubuntu 24.04 LTS |
| Network | 2.5GbE Ethernet + Wi-Fi 6E |

**Capabilities:**
- Runs larger local models (Llama 70B, Mixtral 8x7B)
- Supports multiple concurrent users (up to 5)
- All AI Desks active simultaneously
- Local Whisper STT (no cloud dependency for voice)
- AI image generation (Stable Diffusion with GPU option)
- Agent Framework with concurrent agent workflows

**For:** Multi-location businesses, power users, teams.

**Recommended units:**
| Model | CPU | RAM | Price |
|-------|-----|-----|-------|
| Beelink SER7 | Ryzen 7 7840HS | 32–64 GB | ~$499 |
| Beelink GTR7 Pro | Ryzen 9 7940HS | 64 GB | ~$599 |
| Intel NUC 13 Pro | i7-1360P | 32–64 GB | ~$799 |

**BOM — Pro Config:**
| Component | Model | Cost |
|-----------|-------|------|
| Mini PC | Beelink GTR7 Pro (Ryzen 9, 64GB, 1TB) | $599 |
| Brain Drive | Samsung T7 Shield 2TB | $169 |
| UPS | CyberPower CP600LCD (600VA) | $80 |
| HDMI Cable | 6ft HDMI 2.0 | $8 |
| Quick Start Card | Laminated QR card | $2 |
| Packaging | Branded box + foam insert | $20 |
| **Total COGS** | | **$878** |
| **Retail Price** | | **$799 + subscription** |
| **Margin** | | **-$79 (subscription recovers)** |

---

## Subscription Tiers

All subscriptions include OTA software updates and MAX AI cloud access.

### Empire Starter — $49/month

| Feature | Included |
|---------|----------|
| MAX AI Assistant | Cloud LLM (Grok primary) |
| Business Apps | 1 app (WorkroomForge OR MarketForge OR ContractorForge) |
| CRM | Basic customer management |
| Telegram | MAX integration |
| AI Requests | 500/month |
| AI Desks | None (manual routing) |
| Support | Email |

### Empire Pro — $99/month

| Feature | Included |
|---------|----------|
| MAX AI Assistant | Priority cloud models |
| Business Apps | All apps unlocked |
| CraftForge | Design tools + templates |
| Visual Mockup Engine | Room photo → treatment overlay |
| AI Requests | Unlimited |
| AI Desks | 1 active desk (e.g., ForgeDesk) |
| Brain Memory | Full persistent memory |
| Support | Email + chat |

### Empire Business — $199/month

| Feature | Included |
|---------|----------|
| Everything in Pro | ✓ |
| AI Desks | All desks active (Forge, Market, Social, Support) |
| CraftForge Marketplace | Buy/sell CNC designs |
| SpaceScan/LiDAR | Room scanning integration |
| Multi-user | Up to 5 users |
| Custom Branding | White-label dashboards |
| API Access | REST API for integrations |
| Support | Priority email + chat |

### Empire Enterprise — $499/month

| Feature | Included |
|---------|----------|
| Everything in Business | ✓ |
| Users | Unlimited |
| White Label | Full white-label deployment |
| Custom AI Desks | Custom desk development |
| On-Premise LLM | No cloud dependency option |
| SLA | 99.9% uptime guarantee |
| Support | Dedicated account manager + phone |

### Founder Lifetime — $2,500 one-time

- Everything in Enterprise, forever
- Exclusive Founder NFT license (gold border)
- Periodic $EMPIRE token airdrops
- Limited to first 1,000 customers

---

## What Ships in the Box

### Empire Box Mini / Pro

- [ ] Mini PC (pre-configured, Ubuntu + Empire installed)
- [ ] USB brain drive (Samsung T7, pre-formatted with MAX Brain)
- [ ] Power adapter
- [ ] HDMI cable (6ft)
- [ ] Quick Start Card (laminated, QR code → setup wizard)
- [ ] "Welcome to Empire" insert
- [ ] Ethernet cable (6ft Cat6)

### Empire Box Tablet

- [ ] Android tablet (Empire app pre-installed)
- [ ] USB-C charging cable + wall adapter
- [ ] Protective case
- [ ] Quick Start Card (QR code)
- [ ] Screen protector (pre-applied)

### Empire Box Phone

- [ ] Android phone (Empire app + Telegram pre-configured)
- [ ] USB-C charging cable + wall adapter
- [ ] Phone case
- [ ] Quick Start Card (QR code)
- [ ] Screen protector (pre-applied)

---

## Setup Wizard — MAX Onboarding

First boot → 15 minutes to fully operational.

### Flow

```
1. CONNECT
   └─ Connect to Wi-Fi (or Ethernet auto-detected)
   └─ Device checks for updates

2. CREATE ACCOUNT
   └─ Enter name, email, business name
   └─ Set admin password
   └─ Create founder profile

3. CHOOSE YOUR BUSINESS
   └─ Business type selector:
      • Window treatments / custom drapery
      • General contracting
      • Interior design
      • Custom furniture / woodworking
      • Service business (plumbing, electrical, HVAC)
      • Reseller / marketplace seller
      • Document services (apostille, notary)
      • Wellness / coaching
      • Other
   └─ Seeds MAX Brain with industry-specific knowledge

4. CONFIGURE FIRST APP
   └─ Based on business type, recommend primary app
   └─ Quick walkthrough of core features
   └─ Import sample data (optional)

5. CONNECT TELEGRAM
   └─ Scan QR code to link Telegram
   └─ Test message: MAX says hello
   └─ Voice note test (optional)

6. MEET MAX
   └─ First conversation with MAX
   └─ MAX asks about your business, goals, customers
   └─ Configures AI Desks based on responses
   └─ Sets up morning briefing schedule

7. IMPORT CUSTOMERS (optional)
   └─ CSV upload
   └─ Google Contacts sync
   └─ Manual entry
   └─ Skip for later
```

### What MAX Learns During Setup

- Business type and industry
- Primary services/products offered
- Pricing model (hourly, per-project, retail)
- Geographic area served
- Number of employees/contractors
- Current pain points
- Tools currently in use

All stored in MAX Brain → immediately useful in first real conversation.

---

## Target Markets

### Primary (Launch)

| Market | Key App | Pain Point Solved |
|--------|---------|-------------------|
| Window treatment / custom drapery shops | WorkroomForge | Quote generation, fabric lookup, follow-up tracking |
| General contractors | ContractorForge | Job management, photo measurements, invoicing |
| Interior designers | LuxeForge + Mockup Engine | Client presentations, room visualization |
| Marketplace sellers / resellers | MarketForge | Multi-platform listing, shipping, inventory |

### Secondary (Year 1)

| Market | Key App | Pain Point Solved |
|--------|---------|-------------------|
| Custom furniture / woodworkers | CraftForge | CNC design, production tracking |
| Service businesses (HVAC, plumbing, electrical) | ContractorForge | Scheduling, invoicing, customer management |
| Document services (apostille, notary, translation) | ApostApp | Document intake, status tracking |
| Wellness / coaching businesses | AMP | Client engagement, content delivery |

---

## Manufacturing & Sourcing

### Mini PC Sourcing

| Supplier | Model | MOQ | Unit Cost | Lead Time |
|----------|-------|-----|-----------|-----------|
| Beelink (direct) | SER5 / EQR5 | 20 units | $259–349 | 2–3 weeks |
| Beelink (Amazon B2B) | SER5 / EQR5 | 5 units | $279–369 | 3–5 days |
| TRIGKEY (Alibaba) | various | 50 units | $149–249 | 30 days |
| MINISFORUM (direct) | UM690 / UN100 | 20 units | $159–329 | 2–3 weeks |

### Phone Sourcing

| Supplier | Model | MOQ | Unit Cost | Lead Time |
|----------|-------|-----|-----------|-----------|
| Xiaomi (Alibaba verified) | Redmi Note 13 | 100 units | $180 FOB | 30 days (sea) |
| Solana Foundation | Seeker | 50 units | $350 (partnership) | 2–4 weeks |

### Brain Drive Sourcing

| Supplier | Model | MOQ | Unit Cost |
|----------|-------|-----|-----------|
| Samsung (Amazon B2B) | T7 500GB | 10 units | $55 |
| Samsung (Amazon B2B) | T7 1TB | 10 units | $85 |
| Samsung (Amazon B2B) | T7 Shield 2TB | 10 units | $155 |

### Software Provisioning

Each device is flashed with a provisioning image:

1. **Base image** — Ubuntu 24.04 LTS + Docker + Ollama
2. **Empire stack** — All services as Docker containers
3. **Brain seed** — Industry-specific knowledge base
4. **First-boot script** — Triggers setup wizard on first power-on

Provisioning time: ~30 minutes per device (parallelizable with USB cloning).

---

## Margins Analysis

### Hardware Margins

| Tier | COGS | Retail | Hardware Margin | Break-Even |
|------|------|--------|----------------|------------|
| Mini ($399) | $394 | $399 | $5 (1%) | Month 1 sub |
| Tablet ($249) | $210 | $249 | $39 (16%) | Immediate |
| Phone ($199) | $215 | $199 | -$16 (loss leader) | Month 1 sub |
| Pro ($799) | $878 | $799 | -$79 (loss leader) | Month 2 sub |

### Subscription Margins

| Tier | Monthly | Cloud AI Cost | Infra | Margin |
|------|---------|--------------|-------|--------|
| Starter $49 | $49 | ~$8 | ~$5 | $36 (73%) |
| Pro $99 | $99 | ~$15 | ~$8 | $76 (77%) |
| Business $199 | $199 | ~$25 | ~$12 | $162 (81%) |
| Enterprise $499 | $499 | ~$40 | ~$20 | $439 (88%) |

**Strategy:** Hardware is break-even or slight loss leader. All profit comes from recurring subscriptions at 73–88% gross margin.

**LTV calculation (Pro tier):**
- Monthly revenue: $99
- Average retention: 18 months
- LTV: $99 × 18 = $1,782
- CAC (hardware subsidy): $79
- LTV:CAC ratio: 22.6:1

---

## Fulfillment

### Phase 1: Self-Fulfillment (Launch — first 100 units)

- Store inventory at home/office
- Flash devices in batches (USB cloning, 10 at a time)
- Pack and ship via EmpireBox ShipForge integration
- USPS Priority Mail or FedEx Ground
- Estimated shipping cost: $12–18 per box (Mini PC tier)

### Phase 2: 3PL (100+ units/month)

| Provider | Receiving | Storage | Pick & Pack | Shipping |
|----------|-----------|---------|-------------|----------|
| ShipBob | $0.50/unit | $0.75/unit/mo | $3/order | Market rate |
| ShipMonk | Free | $1/unit/mo | $2.50/order | Market rate |

### Phase 3: Direct-from-Manufacturer (1000+ units)

- Partner with Beelink/MINISFORUM for co-branded devices
- Factory flashes provisioning image
- Ships direct to customer or regional warehouse
- Per-unit cost drops 15–20%

---

## Warranty & Support

### Hardware Warranty

| Component | Coverage | Provider |
|-----------|----------|----------|
| Mini PC | 1 year manufacturer + 1 year Empire | Beelink / Empire |
| Tablet | 1 year manufacturer | Samsung |
| Phone | 1 year manufacturer | Xiaomi / Solana |
| Brain Drive (SSD) | 3 years manufacturer | Samsung |
| UPS (if included) | 2 years manufacturer | APC / CyberPower |

### Empire Guarantee

- **30-day money back** — no questions asked
- Full refund if device never activated
- 15% restocking fee if activated
- No long-term subscription commitment — cancel anytime

### Support Model

| Tier | Support Level |
|------|--------------|
| Starter | Email (48hr response) |
| Pro | Email + chat (24hr response) |
| Business | Priority email + chat (4hr response) |
| Enterprise | Dedicated account manager + phone (1hr response) |

All tiers include:
- MAX AI self-service (ask MAX for help)
- Knowledge base articles
- Community forum
- Video tutorials

---

## Updates & OTA Mechanism

### Software Updates

Empire Box receives automatic over-the-air updates:

```
┌─────────────────────────────────────────────┐
│  Empire Update Server (cloud)                │
│  └─ Pushes update manifests every 6 hours    │
└──────────────┬──────────────────────────────┘
               │
               ▼
┌─────────────────────────────────────────────┐
│  Empire Box (local)                          │
│  1. Check manifest → compare versions        │
│  2. Download changed Docker images           │
│  3. Stop services (maintenance window)       │
│  4. Pull new images + migrate DB if needed   │
│  5. Restart services                         │
│  6. Health check → rollback on failure       │
│  7. Report status to cloud                   │
└─────────────────────────────────────────────┘
```

**Update types:**
| Type | Frequency | Downtime |
|------|-----------|----------|
| Security patches | As needed | < 1 min |
| Feature updates | Monthly | 2–5 min |
| Model updates (Ollama) | Quarterly | 5–15 min (download) |
| Major version | Annually | 10–30 min |

**Rollback:** Every update creates a snapshot. If health check fails after update, auto-rollback to previous version within 60 seconds.

**Offline mode:** Empire Box works fully offline. Updates download when internet is available and apply during configured maintenance window (default: 3 AM local time).

### Brain Drive Portability

The USB brain drive contains:
- MAX memories database (SQLite)
- Ollama model weights
- Customer data backups
- Conversation history
- Business knowledge base

Plug the brain drive into any Empire Box → your business memory follows you. Lost a device? Plug brain into new Empire Box → back online in minutes.

---

## Competitive Positioning

### What Exists Today

| Product | What It Does | What It Doesn't Do |
|---------|-------------|-------------------|
| Shopify | Online store | Run your operations |
| HubSpot | CRM | Know your business |
| QuickBooks | Accounting | Manage customers |
| ChatGPT | Answer questions | Remember your business |
| Siri/Alexa | Smart home | Run a business |

### What Empire Box Does

- Ships a physical device that runs in your shop
- Local AI brain that **learns your business** over time
- Manages customers, quotes, scheduling, inventory
- AI Desks that autonomously handle routine tasks
- Escalates important decisions to you (Telegram, voice)
- Works offline — no internet dependency for core functions
- One subscription covers everything — no tool sprawl

### The Pitch

> "You hire employees to run your business. Empire Box is the employee that never sleeps, never forgets, and costs $99 a month."

> "Your Empire Box knows every customer, every quote, every conversation. It follows up when you forget. It catches the leads you'd miss. It runs while you sleep."

---

## Appendix: Port Map (Pre-Configured)

| Port | Service | Auto-Start |
|------|---------|------------|
| 3009 | Founder Dashboard | Yes |
| 8000 | Backend API | Yes |
| 8080 | Homepage / Hub | Yes |
| 7878 | OpenClaw AI | Yes |
| 11434 | Ollama | Yes |
| 3001 | WorkroomForge | On-demand |
| 3002 | LuxeForge | On-demand |
| 8010 | MarketForge | On-demand |
| 8020 | ContractorForge | On-demand |
| 8040 | SupportForge | On-demand |
| 8060 | ShipForge | On-demand |
| 8090 | SocialForge | On-demand |
| 8100 | LLCFactory | On-demand |

---

## Appendix: Software Bundles by Business Type

| Business Type | Primary Apps | Recommended Tier |
|---------------|-------------|-----------------|
| Window treatments | WorkroomForge, LuxeForge, CraftForge | Pro |
| General contractor | ContractorForge, LeadForge, CRM | Pro |
| Interior designer | LuxeForge, Mockup Engine, CRM | Business |
| Marketplace seller | MarketForge, ShipForge, RelistApp | Starter |
| Custom furniture | CraftForge, MarketForge, ShipForge | Pro |
| Service business | ContractorForge, CRM, EmpireAssist | Starter |
| Document services | ApostApp, CRM, EmpireAssist | Starter |
| Wellness / coaching | AMP, CRM, SocialForge | Pro |

---

## Appendix: Crypto Payment Options

| Method | Discount | NFT License |
|--------|----------|-------------|
| Fiat (Stripe / PayPal) | 0% | Minted on Solana |
| Crypto (SOL, BNB, ADA, ETH) | 15% off | Minted on Solana |
| $EMPIRE Token | 20% off | Minted on Solana |

All licenses are Solana NFTs regardless of payment method. Transferable, verifiable on-chain.

---

*Last updated: February 28, 2026*
*Source: Full Empire codebase review + founder specifications*
