# RelistApp — Full Development Plan
> Generated: March 9, 2026 | Status: PLAN — Awaiting Approval Before Build

---

## 1. WHAT WAS FOUND (All Sources)

### Existing Code & References

| Location | What Exists |
|----------|-------------|
| `modules/relist/README.md` | Product spec: "Cross-platform relisting tool", status: Planned |
| `docs/ECOSYSTEM.md` | Revenue projection Y3: $1.5M (9%), feature list |
| `docs/ZERO_TO_HERO_SPEC.md` | Listed as activated tool in automation flow |
| `docs/PRODUCT_DECISIONS.md` | Confirmed as planned product |
| `docs/EMPIRE_BOX_HARDWARE_SPEC.md` | Marketplace seller tier includes RelistApp |
| `app/lib/types.ts` | `'relist'` in EcosystemProduct type |
| `LeftNav.tsx` | Nav entry: `{ id: 'relist', icon: Repeat, status: 'planned', color: '#6b7280' }` |
| `page.tsx` | Routes to generic `EcosystemProductPage` (placeholder) |
| `backend/app/routers/listings.py` | Full CRUD + publish-to-marketplaces endpoint |
| `backend/app/routers/marketplaces.py` | Marketplace connect/disconnect (eBay, Facebook, Craigslist) |
| `backend/app/services/marketplace/` | Base class, eBay scaffolding, fee service (8%), product/order services |
| `backend/app/models/listing.py` | Listing model with `marketplace_listings` JSON field |
| `backend/app/services/max/desks/market_desk.py` | MarketDesk (Sofia) handles "relist" keyword, channels include RelistApp |
| `founders_usb_installer/empirebox/products/relistapp/` | Docker compose for deployment |
| `market_forge_app/` | Flutter mobile app with marketplace picker |
| `MarketForgePage.tsx` | Dashboard with mock data for 5 marketplaces |

### What's Ready to Build On
- ✅ Listing CRUD with cross-posting scaffolding
- ✅ Marketplace connection management
- ✅ Product/Order/Review models (MarketForge)
- ✅ Fee calculation service (8% + Stripe 2.9% + $0.30)
- ✅ Escrow payment flow
- ✅ Inventory & vendor management
- ✅ Shipping/fulfillment endpoints
- ✅ AI desk agent (MarketDesk/Sofia) ready to handle relist tasks
- ✅ eBay webhook endpoint (needs implementation)
- ⏳ External marketplace OAuth flows (scaffolded but TODO)
- ⏳ Cross-marketplace sync logic (mock)
- ❌ RelistApp frontend page (only generic placeholder)
- ❌ Scheduling/automation engine
- ❌ Pricing intelligence
- ❌ AI description generation for listings

---

## 2. COMPETITIVE LANDSCAPE

| Tool | Price | Platforms | Key Feature | Our Advantage |
|------|-------|-----------|-------------|---------------|
| **List Perfectly** | $29-249/mo | 10+ | Wide platform coverage | Cheaper, AI-powered, integrated ecosystem |
| **Vendoo** | $0-69.99/mo | 11 | Analytics + bulk ops | No per-listing caps, built-in AI vision |
| **Crosslist** | $0-49.99/mo | 11 | Single dynamic form | Cloud-native (not Chrome extension) |
| **Flyp** | $9/mo | 6 | Cheapest option | More platforms, AI features |
| **OneShop** | $45/mo flat | 9 | Mobile-first | Desktop + mobile, AI pricing |
| **Nifty AI** | $39.99-59.99/mo | 5 | AI listing creation | More platforms, ecosystem integration |
| **PrimeLister** | $29.99-49.99/mo | 8 | Poshmark automation | Cross-platform not bolted on |
| **JoeLister** | $25-139/mo | 2 (Amazon→eBay) | Arbitrage sync | Multi-platform, not just Amazon→eBay |

### Key Gaps We Can Fill
1. **No tool has integrated AI vision** — we have photo analysis, measurement, mockups already built
2. **No tool has integrated inventory management** — we have full inventory system
3. **No tool has integrated shipping** — we have shipping/label endpoints
4. **Amazon SP-API is now $1,400/yr** — barrier creates moat for whoever integrates it
5. **Sold comps/pricing intelligence** is always a separate tool — we integrate it
6. **No tool has CRM integration** — we have ForgeCRM
7. **Cloud-native 24/7 automation** — most competitors are Chrome extensions

---

## 3. FEATURE LIST — MVP (Phase 1)

### Core Features
1. **Multi-Platform Listing Manager**
   - Create listing once, publish to multiple marketplaces
   - Platform-specific field optimization (title, description, category mapping)
   - Photo management with drag-and-drop upload
   - Bulk import from CSV/spreadsheet

2. **Cross-Post Engine**
   - One-click cross-post to connected marketplaces
   - Auto-map categories, conditions, shipping options per platform
   - Platform-specific character limits and formatting
   - Queue system for rate-limited platforms

3. **Inventory Sync**
   - Real-time stock sync across all platforms
   - Auto-delist when item sells on any platform
   - Low-stock alerts
   - Integration with Empire inventory module

4. **Marketplace Connections**
   - eBay (Official API — free, 2M calls/day)
   - Etsy (Official API — free, 10K calls/day)
   - Shopify (Official API — free with plan)
   - Manual import for platforms without APIs

5. **Dashboard & Analytics**
   - Active listings by platform
   - Sales performance per platform
   - Revenue tracking and profit calculation
   - Listing age and freshness metrics

6. **AI-Enhanced Listings** (Empire integration)
   - AI-generated titles and descriptions (via MAX/Grok)
   - AI photo enhancement (via Vision API)
   - Background removal
   - SEO keyword suggestions

### MVP Endpoints Needed
```
POST   /api/v1/relist/listings              — Create multi-platform listing
GET    /api/v1/relist/listings              — List all with filters
GET    /api/v1/relist/listings/{id}         — Get listing detail
PATCH  /api/v1/relist/listings/{id}         — Update listing
DELETE /api/v1/relist/listings/{id}         — Delete/archive
POST   /api/v1/relist/listings/{id}/crosspost   — Cross-post to platforms
POST   /api/v1/relist/listings/{id}/relist       — Relist expired listing
POST   /api/v1/relist/listings/bulk-import       — CSV/spreadsheet import
GET    /api/v1/relist/platforms             — Connected platforms
POST   /api/v1/relist/platforms/{name}/connect    — OAuth connect
DELETE /api/v1/relist/platforms/{name}/disconnect  — Disconnect
GET    /api/v1/relist/dashboard             — Stats overview
GET    /api/v1/relist/analytics             — Performance data
POST   /api/v1/relist/ai/describe           — AI-generate listing text
POST   /api/v1/relist/ai/price             — AI pricing suggestion
POST   /api/v1/relist/ai/enhance-photos    — AI photo enhancement
GET    /api/v1/relist/sync/status           — Cross-platform sync status
POST   /api/v1/relist/sync/trigger          — Force sync all platforms
```

---

## 4. FEATURE LIST — FULL (Future Phases)

### Phase 2: Platform Expansion
- Poshmark (browser automation / unofficial)
- Mercari (browser automation / unofficial)
- Facebook Marketplace (browser automation)
- Depop, Grailed, Whatnot
- Amazon SP-API ($1,400/yr — premium tier)

### Phase 3: AI & Intelligence
- **AI Auto-Pricing**: Real-time comp analysis, sold price research, optimal pricing
- **AI Demand Forecasting**: Predict what will sell and when
- **Auto-Relist Scheduler**: Smart scheduling based on platform algorithms
- **Auto-Share/Refresh**: Poshmark sharing automation, eBay listing refresh
- **Offer Management**: Auto-send offers to watchers/likers across platforms
- **AI Image Staging**: Virtual staging, lifestyle mockups for product photos

### Phase 4: Scale & Monetize
- White-label solution for reselling businesses
- Wholesale sourcing integration
- Tax/bookkeeping integration (1099 prep, COGS tracking)
- Mobile app (React Native)
- Team/employee accounts
- API access for power sellers

---

## 5. TECHNICAL ARCHITECTURE

### Where It Lives in Empire Ecosystem
```
empire-repo/
├── backend/app/routers/relist.py          ← NEW: RelistApp API endpoints
├── backend/app/services/relist/           ← NEW: Business logic
│   ├── listing_manager.py                 — Multi-platform listing CRUD
│   ├── crosspost_engine.py                — Cross-posting logic
│   ├── platform_sync.py                   — Inventory sync across platforms
│   ├── pricing_intelligence.py            — AI pricing + comp analysis
│   └── scheduler.py                       — Auto-relist scheduling
├── backend/app/services/marketplace/      ← EXISTING: Extend
│   ├── base.py                            — Abstract marketplace class
│   ├── ebay.py                            — eBay integration (implement OAuth)
│   ├── etsy.py                            ← NEW: Etsy integration
│   └── shopify_integration.py             ← NEW: Shopify integration
├── empire-command-center/
│   └── app/components/screens/
│       └── RelistAppPage.tsx              ← NEW: Full RelistApp UI
```

### Database Schema Extensions

```sql
-- Extend existing listings table
ALTER TABLE listings ADD COLUMN relist_schedule TEXT;    -- JSON: {frequency, next_relist, platforms}
ALTER TABLE listings ADD COLUMN last_relisted TIMESTAMP;
ALTER TABLE listings ADD COLUMN platform_status TEXT;    -- JSON: {ebay: {id, url, status, listed_at}, ...}
ALTER TABLE listings ADD COLUMN source_platform TEXT;    -- Where item was originally listed
ALTER TABLE listings ADD COLUMN purchase_price NUMERIC(10,2);  -- For profit calculation
ALTER TABLE listings ADD COLUMN sold_price NUMERIC(10,2);
ALTER TABLE listings ADD COLUMN sold_platform TEXT;
ALTER TABLE listings ADD COLUMN tags TEXT;               -- JSON array for search/filter

-- New: Relist history/audit table
CREATE TABLE relist_history (
    id TEXT PRIMARY KEY,
    listing_id TEXT REFERENCES listings(id),
    platform TEXT NOT NULL,
    action TEXT NOT NULL,        -- 'listed', 'relisted', 'delisted', 'sold', 'price_updated'
    old_price NUMERIC(10,2),
    new_price NUMERIC(10,2),
    platform_listing_id TEXT,
    platform_url TEXT,
    status TEXT DEFAULT 'success',
    error TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- New: Platform connections (OAuth tokens)
CREATE TABLE platform_connections (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,      -- 'ebay', 'etsy', 'shopify', 'poshmark', etc.
    account_name TEXT,
    access_token TEXT,           -- Encrypted
    refresh_token TEXT,          -- Encrypted
    token_expires_at TIMESTAMP,
    shop_url TEXT,               -- For Shopify
    seller_id TEXT,              -- Platform-specific seller ID
    status TEXT DEFAULT 'active',
    connected_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_sync_at TIMESTAMP
);

-- New: Pricing comps cache
CREATE TABLE pricing_comps (
    id TEXT PRIMARY KEY,
    query TEXT NOT NULL,
    platform TEXT,
    avg_sold_price NUMERIC(10,2),
    min_price NUMERIC(10,2),
    max_price NUMERIC(10,2),
    num_comps INTEGER,
    comps_data TEXT,             -- JSON array of comparable sales
    fetched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- New: Relist schedules
CREATE TABLE relist_schedules (
    id TEXT PRIMARY KEY,
    listing_id TEXT REFERENCES listings(id),
    platforms TEXT NOT NULL,     -- JSON array of target platforms
    frequency TEXT NOT NULL,     -- 'daily', 'weekly', 'biweekly', 'monthly', 'custom'
    custom_days INTEGER,
    next_run_at TIMESTAMP,
    last_run_at TIMESTAMP,
    enabled BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Frontend Page Structure (RelistAppPage.tsx)

```
RelistAppPage
├── Sidebar Nav
│   ├── Dashboard (overview KPIs)
│   ├── Listings (all listings manager)
│   ├── Cross-Post (bulk cross-posting tool)
│   ├── Platforms (connected marketplaces)
│   ├── Pricing (AI pricing intelligence)
│   ├── Scheduler (auto-relist schedules)
│   ├── Analytics (performance charts)
│   └── Settings (preferences, API keys)
├── Dashboard Section
│   ├── KPI Cards (active listings, total value, sold this month, avg days to sell)
│   ├── Platform Distribution (pie chart)
│   ├── Recent Activity feed
│   └── Quick Actions (New Listing, Bulk Import, Cross-Post All)
├── Listings Section
│   ├── Grid/List toggle view
│   ├── Filter by platform, status, category, price range
│   ├── Sort by date, price, views, age
│   ├── Bulk actions (select all → cross-post, delist, relist, price update)
│   ├── Individual listing card with platform badges
│   └── Listing detail modal with edit + cross-post
├── Cross-Post Section
│   ├── Select source listings
│   ├── Choose target platforms
│   ├── Field mapping preview (shows how listing looks on each platform)
│   ├── Bulk cross-post queue with progress bar
│   └── History of cross-post actions
├── Platforms Section
│   ├── Connected marketplace cards (with sync status, last sync time)
│   ├── OAuth connect buttons
│   ├── Per-platform listing count
│   └── Sync controls (force sync, auto-sync toggle)
├── Pricing Intelligence Section
│   ├── Price check tool (search by title/barcode → sold comps)
│   ├── AI pricing recommendation per listing
│   ├── Margin calculator (purchase price → platform fees → profit)
│   └── Price history charts
├── Scheduler Section
│   ├── Active schedules list
│   ├── Create schedule form (select listings, frequency, platforms)
│   ├── Next relist queue preview
│   └── Schedule history/audit log
└── Analytics Section
    ├── Revenue by platform (bar chart)
    ├── Sell-through rate
    ├── Average days to sell
    ├── Best performing categories
    ├── Listing age distribution
    └── Monthly trends
```

### API Integrations Required

| Platform | API Type | Auth | Rate Limit | Cost | Priority |
|----------|----------|------|-----------|------|----------|
| **eBay** | REST (Inventory API) | OAuth 2.0 | 2M calls/day | Free | P1 |
| **Etsy** | REST (Open API v3) | OAuth 2.0 | 10K/24hr | Free | P1 |
| **Shopify** | REST + GraphQL | OAuth 2.0 | 4 req/min REST | Free w/plan | P1 |
| **Poshmark** | Browser automation | Cookie-based | N/A | Free (risk) | P2 |
| **Mercari** | Browser automation | Cookie-based | N/A | Free (risk) | P2 |
| **Facebook MP** | Graph API (limited) | OAuth 2.0 | Restricted | Free | P2 |
| **Amazon** | SP-API | OAuth 2.0 | 2.5M GET/mo | $1,400/yr | P3 |
| **Depop** | Browser automation | Cookie-based | N/A | Free (risk) | P3 |

### AI Features Integration

| Feature | Empire Service | How |
|---------|---------------|-----|
| AI Descriptions | MAX (Grok/Claude) | `/api/v1/max/chat/stream` with listing-specific prompt |
| AI Photo Enhancement | Vision API | `/api/v1/vision/enhance` + background removal |
| AI Pricing | MAX + External comps | Query sold comps → feed to AI → get recommendation |
| AI Category Mapping | MAX | Map source category → target platform categories |
| AI SEO Tags | MAX | Generate platform-specific keywords and hashtags |

---

## 6. MONETIZATION STRATEGY

### Subscription Tiers

| Tier | Price | Listings | Platforms | AI Credits | Features |
|------|-------|---------|-----------|------------|----------|
| **Free** | $0/mo | 25/mo | 3 | 10/mo | Basic crosspost, manual relist |
| **Starter** | $9.99/mo | 100/mo | 5 | 50/mo | + Bulk operations, basic analytics |
| **Pro** | $19.99/mo | Unlimited | All | 200/mo | + AI descriptions, auto-relist scheduler |
| **Business** | $39.99/mo | Unlimited | All | Unlimited | + AI pricing, full analytics, priority support, team accounts |

### Additional Revenue Streams
- **Per-listing overage**: $0.05/listing beyond tier (Free/Starter only)
- **Premium AI credits**: $4.99 for 100 extra AI credits
- **Amazon SP-API pass-through**: $9.99/mo add-on (covers $1,400/yr API cost)
- **White-label licensing**: Custom pricing for reselling businesses
- **Featured placement**: Pay to boost listings on MarketForge

### Revenue Projections (Conservative)

| Metric | Month 3 | Month 6 | Year 1 | Year 2 |
|--------|---------|---------|--------|--------|
| Free users | 500 | 2,000 | 5,000 | 15,000 |
| Paying users | 50 | 300 | 1,500 | 5,000 |
| Avg revenue/user | $15 | $20 | $25 | $28 |
| MRR | $750 | $6,000 | $37,500 | $140,000 |
| ARR | $9,000 | $72,000 | $450,000 | $1,680,000 |

---

## 7. PLATFORM SUPPORT PRIORITY

### Phase 1 (MVP) — Official APIs Only
1. **eBay** — Largest reselling platform, official free API, 2M calls/day
2. **Etsy** — Strong handmade/vintage market, official free API
3. **Shopify** — Seller's own store, official API, good for brand building

### Phase 2 — Browser Automation (Higher Risk)
4. **Poshmark** — 130M+ users, no official API, requires browser automation
5. **Mercari** — Growing fast, no official API
6. **Facebook Marketplace** — 1.1B monthly users, limited API access

### Phase 3 — Premium Platforms
7. **Amazon** — $1,400/yr API cost, premium tier feature
8. **Depop** — Gen Z market, no official API
9. **Grailed** — Menswear niche
10. **Whatnot** — Live selling platform

### Why This Order
- Phase 1 uses only official, free APIs = lowest risk, fastest to build
- Phase 2 platforms have no APIs but huge user bases = higher risk, higher reward
- Phase 3 platforms either cost money (Amazon) or serve niche markets

---

## 8. INTEGRATION WITH EMPIRE ECOSYSTEM

### MarketForge Connection
- RelistApp listings can originate from MarketForge products
- `marketforge_listing_id` field already exists in product model
- Cross-post MarketForge → external platforms in one click
- Shared inventory prevents double-selling

### Inventory Module
- Link listings to inventory items via SKU
- Auto-decrement stock on sale
- Low-stock alerts trigger "pause listing" across platforms
- Vendor/supply chain integration for restocking

### Shipping Module (ShipForge)
- Generate labels directly from RelistApp when item sells
- Auto-calculate shipping costs per platform
- Tracking sync back to marketplace
- Bulk label printing for power sellers

### AI Vision Module
- One-click photo enhancement from listing manager
- Background removal for professional-looking photos
- AI measurement for sizing information
- Style detection for category suggestions

### MAX AI
- Generate SEO-optimized titles and descriptions
- Platform-specific copywriting (Poshmark style vs eBay style vs Etsy style)
- Answer buyer questions via AI
- Daily/weekly analytics summaries via Telegram

### ForgeCRM
- Track buyers across platforms
- Repeat customer identification
- Customer lifetime value calculation
- Cross-platform messaging history

### EmpirePay
- Unified payout tracking across all platforms
- Profit/loss per item (purchase price - platform fees - shipping = profit)
- Tax-ready reports (1099 preparation)
- Monthly P&L by platform

---

## 9. BUILD PHASES

### Phase 1: MVP (Target: 2-3 weeks)
**Backend:**
- [ ] Create `backend/app/routers/relist.py` with all listing/crosspost/platform endpoints
- [ ] Create `backend/app/services/relist/` service directory
- [ ] Extend database with relist-specific tables
- [ ] Implement eBay OAuth 2.0 flow + listing publish
- [ ] Implement Etsy OAuth 2.0 flow + listing publish
- [ ] Implement Shopify OAuth 2.0 flow + listing publish
- [ ] AI description generation endpoint (leverage MAX)
- [ ] AI photo enhancement endpoint (leverage Vision API)
- [ ] Cross-platform inventory sync service
- [ ] Dashboard/analytics aggregation endpoint

**Frontend:**
- [ ] Build `RelistAppPage.tsx` with full sidebar navigation
- [ ] Dashboard section with KPIs and recent activity
- [ ] Listings section with grid/list view, filters, bulk actions
- [ ] Cross-Post section with platform mapping preview
- [ ] Platforms section with OAuth connect flow
- [ ] Pricing tool with margin calculator

**Integration:**
- [ ] Update LeftNav status from 'planned' to 'active'
- [ ] Update page.tsx routing from EcosystemProductPage to RelistAppPage
- [ ] Wire MarketDesk to handle relist-specific tasks
- [ ] Connect to existing inventory module

### Phase 2: Platform Expansion (2-4 weeks after MVP)
- [ ] Poshmark browser automation service
- [ ] Mercari browser automation service
- [ ] Facebook Marketplace integration
- [ ] Auto-share/refresh for Poshmark
- [ ] Bulk import from CSV/spreadsheet
- [ ] Listing templates (save and reuse)

### Phase 3: AI & Intelligence (2-4 weeks after Phase 2)
- [ ] AI pricing engine (sold comps analysis)
- [ ] AI demand forecasting
- [ ] Auto-relist scheduler with smart timing
- [ ] Offer management (auto-send offers to likers)
- [ ] AI category mapping across platforms
- [ ] Performance-based listing optimization

### Phase 4: Scale (Ongoing)
- [ ] Amazon SP-API integration (premium tier)
- [ ] Mobile app (React Native)
- [ ] Team/employee accounts
- [ ] White-label solution
- [ ] Tax/bookkeeping integration
- [ ] Wholesale sourcing module
- [ ] Public API for power sellers

---

## 10. DESK AGENT ASSIGNMENTS

| Desk | Agent | Task | Status |
|------|-------|------|--------|
| **Nexus** (Research) | Research | Competitive analysis: top 10 tools, features, pricing, API docs | Delegated |
| **Vanguard** (Strategy) | Strategy | Market positioning, pricing tiers, target market, revenue projections | Delegated |
| **Aria** (Marketing) | Marketing | Landing page copy, SEO keywords, social media plan, influencer outreach | Delegated |
| **Atlas** (Forge) | Build | Technical architecture, API integrations, database schema, MVP features | Delegated |
| **Cipher** (Finance) | Finance | Cost analysis, break-even, subscription pricing, revenue model | Delegated |

---

## 11. CRITICAL LEGAL NOTES

⚠️ **Amazon-to-eBay dropship arbitrage is explicitly prohibited** by both platforms as of 2025. RelistApp should NOT facilitate this.

✅ **Legitimate use cases:**
- Sellers listing their OWN inventory on multiple platforms
- Cross-posting items they physically possess
- Wholesale/bulk sellers distributing across channels
- Small businesses expanding marketplace presence

✅ **Platform TOS compliance:**
- eBay: Official API = fully compliant
- Etsy: Official API = fully compliant
- Shopify: Official API = fully compliant
- Poshmark/Mercari: Browser automation = gray area, common industry practice
- Facebook Marketplace: Limited API, automation restricted

---

## 12. SUCCESS METRICS

| Metric | Month 1 | Month 3 | Month 6 | Year 1 |
|--------|---------|---------|---------|--------|
| Registered users | 100 | 500 | 2,000 | 5,000 |
| Paying subscribers | 10 | 50 | 300 | 1,500 |
| Listings created | 1,000 | 10,000 | 50,000 | 200,000 |
| Cross-posts completed | 500 | 5,000 | 25,000 | 100,000 |
| Items sold via RelistApp | 50 | 500 | 2,500 | 10,000 |
| MRR | $150 | $750 | $6,000 | $37,500 |

---

## APPROVAL REQUIRED

**This plan is ready for review.** No code will be written until approved.

Key decisions needed:
1. ✅ / ❌ Proceed with Phase 1 MVP?
2. Which platforms to prioritize? (Recommended: eBay, Etsy, Shopify)
3. Pricing tiers acceptable? (Free → $9.99 → $19.99 → $39.99)
4. Should RelistApp be separate from MarketForge or merged?
5. Build as Next.js page in Command Center or standalone app?

---

*Desk agents have been delegated tasks. Reports will arrive in the task queue.*
*All competitive research data sourced March 2026.*
