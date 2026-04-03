# RelistApp - Empire Box Integration Guide

> How RelistApp connects to the Empire Box ecosystem for unified drop-ship arbitrage management.

---

## Architecture Overview

RelistApp (port 3007) operates as a first-class module inside Empire Box, alongside Empire Workroom (drapery/upholstery) and WoodCraft (woodwork/CNC). All three revenue streams share the same backend (FastAPI, port 8000), the same AI routing layer (MAX), and the same Command Center dashboard (port 3005).

```
Command Center (3005)
├── Empire Workroom Module
├── WoodCraft Module
└── RelistApp Module (3007)
    ├── Listing Engine
    ├── Pricing Engine
    ├── Order Tracker
    ├── Analytics / P&L
    └── Competitor Monitor
```

---

## 1. Command Center Sidebar Integration

RelistApp adds three items to the Command Center left sidebar under the "Revenue Streams" group.

### Dashboard (`/relist/dashboard`)

| Widget | Data Source | Refresh |
|--------|-----------|---------|
| Today's Revenue | RelistApp orders API | 5 min |
| Active Listings | Listing engine count | 15 min |
| Pending Shipments | Order tracker | 5 min |
| Win Rate | Sold / listed ratio | Hourly |
| Top 5 Products | Analytics engine | Hourly |
| Margin Heatmap | Pricing engine | Hourly |

### Live Listings (`/relist/listings`)

- Real-time table of all active listings across platforms (eBay, Mercari, Poshmark, TikTok Shop)
- Columns: title, source price, list price, margin %, platform, status, days listed
- Bulk actions: reprice, delist, relist, clone to another platform
- Filter by platform, margin range, category, date listed

### Daily P&L (`/relist/pnl`)

- Revenue, COGS (source cost + shipping), platform fees, net profit
- Running 7-day and 30-day P&L charts
- Breakdown by platform and category
- Exportable to CSV for accounting

---

## 2. MAX AI Integration

MAX (the Empire AI assistant) can query RelistApp data through natural language commands via Telegram or the Command Center chat.

### Sample Commands and Responses

| User Says | MAX Action | Desk Used |
|-----------|-----------|-----------|
| "Show today's RelistApp profit" | Queries `/api/v1/relist/analytics/daily` | Finance Desk |
| "What's my best-selling product this week?" | Queries `/api/v1/relist/analytics/top-products` | Analytics Desk |
| "List 20 phone cases from my queue" | Triggers listing engine batch | Atlas Desk |
| "Reprice all items with margin below 25%" | Triggers pricing engine | Atlas Desk |
| "Draft a TikTok post for the LED desk lamp" | Generates content from listing data | Marketing Desk |
| "How many orders shipped today?" | Queries order tracker | Finance Desk |

### API Endpoints for MAX

```
GET  /api/v1/relist/analytics/daily          # Today's P&L summary
GET  /api/v1/relist/analytics/top-products    # Top sellers by volume/profit
GET  /api/v1/relist/analytics/margins         # Margin distribution
POST /api/v1/relist/listings/batch            # Create listings in bulk
POST /api/v1/relist/pricing/reprice           # Batch repricing
GET  /api/v1/relist/orders/pending            # Unfulfilled orders
GET  /api/v1/relist/orders/shipped            # Shipped today
```

---

## 3. Finance Desk Integration

RelistApp revenue flows directly into Empire's unified financial reporting.

### Revenue Classification

```
Empire Revenue
├── Empire Workroom (drapery/upholstery services)
├── WoodCraft (woodwork/CNC products)
└── RelistApp (drop-ship arbitrage)
    ├── eBay Revenue
    ├── Mercari Revenue
    ├── Poshmark Revenue
    └── TikTok Shop Revenue
```

### Data Flow

1. Order completes on platform (eBay, Mercari, etc.)
2. RelistApp order tracker records: sale price, source cost, platform fee, shipping cost
3. Net profit written to `/api/v1/costs/revenue` with category `relist`
4. Finance Desk aggregates across all Empire revenue streams
5. Monthly P&L report includes RelistApp as a line item

### Key Financial Metrics Tracked

- Gross merchandise volume (GMV)
- Cost of goods sold (COGS) -- source price + inbound shipping
- Platform fees (eBay ~13.25%, Mercari ~10%, Poshmark 20%, TikTok Shop ~5-8%)
- Net margin per item, per platform, per category
- Return/refund rate and cost
- AI API costs attributed to RelistApp operations

---

## 4. Marketing Desk Integration

The Marketing Desk generates promotional content for high-margin RelistApp products.

### Automated Content Pipeline

1. RelistApp flags products with margin > 40% and sales velocity > 3/week
2. Marketing Desk receives product data: title, images, price, category
3. AI generates platform-specific content:
   - Instagram carousel (product photos + pricing)
   - TikTok script (15-30 second product showcase)
   - Story template (swipe-up to listing)
4. Content queued in SocialForge for scheduling

### Content Types

| Format | Platform | Frequency | Purpose |
|--------|----------|-----------|---------|
| Carousel | Instagram | 3x/week | Showcase best-margin products |
| Short video | TikTok | Daily | Trending product reveals |
| Story | Instagram | Daily | Flash deals, limited stock alerts |
| Reel | Instagram | 2x/week | "Found this deal" format |

---

## 5. SocialForge Publishing

SocialForge handles automated publishing of RelistApp product content.

### Publishing Flow

```
RelistApp Product Data
  → Marketing Desk (content generation)
    → SocialForge Queue
      → Instagram API (carousel, story, reel)
      → TikTok API (short video)
      → Scheduled posting (optimal times by platform)
```

### Optimal Posting Schedule

- Instagram: 11am, 2pm, 7pm EST
- TikTok: 9am, 12pm, 5pm, 9pm EST
- Content auto-generated from listing data -- no manual work required

---

## 6. ForgeCRM Buyer Integration

Buyer contact information flows from RelistApp orders into ForgeCRM.

### Data Captured

- Buyer username and email (where platform provides it)
- Purchase history (items, prices, dates)
- Platform preference
- Category interest tags (auto-assigned from purchase data)
- Repeat buyer flag

### CRM Actions

- Tag repeat buyers for priority fulfillment
- Send follow-up messages for review requests
- Identify cross-sell opportunities (buyer of phone case -> offer screen protector)
- Segment buyers by platform and category for future marketing

---

## 7. Cost Tracker Integration

All AI API costs generated by RelistApp operations are tracked in the Empire cost tracker.

### AI Operations That Incur Cost

| Operation | AI Model Used | Estimated Cost/Call |
|-----------|-------------|-------------------|
| Listing title optimization | Grok | $0.001 |
| Product description generation | Claude Sonnet | $0.003 |
| Competitor price analysis | Grok | $0.001 |
| Image background removal | Stability AI | $0.02 |
| Marketing content generation | Claude Sonnet | $0.005 |
| Trend analysis (daily) | Grok | $0.002 |

### Budget Tracking

- All calls logged to `/api/v1/costs/log` with tag `relist`
- Daily AI spend visible in Command Center cost dashboard
- Monthly budget cap configurable per operation type
- Alert when daily AI spend exceeds threshold (default: $2.00)

---

## 8. Jobs System Integration

Each batch of RelistApp listings is tracked as a Job in the Empire Jobs system.

### Job Types

| Job Type | Trigger | Tracked Metrics |
|----------|---------|----------------|
| `relist_batch_list` | Batch listing creation | Items listed, time, errors |
| `relist_batch_reprice` | Batch repricing | Items repriced, avg change |
| `relist_competitor_scan` | Competitor monitoring | Sellers scanned, alerts generated |
| `relist_order_fulfill` | Order fulfillment batch | Orders processed, ship time |
| `relist_analytics_daily` | Daily analytics rollup | Revenue, margin, volume |

### Job Lifecycle

1. Job created with status `queued`
2. Processing begins -> status `running`
3. Progress tracked (e.g., "45/100 listings created")
4. Completion -> status `completed` with summary metrics
5. Failures logged with retry capability

---

## 9. SaaS Tier Structure

RelistApp is designed for future SaaS deployment to external users.

### Pricing Tiers

| Tier | Price | Listings/Day | Features |
|------|-------|-------------|----------|
| **Free** | $0/mo | 10 | Basic listing, manual pricing, 1 platform |
| **Pro** | $29/mo | 100 | AI pricing, 3 platforms, competitor alerts, analytics |
| **Empire** | $79/mo | Unlimited | All platforms, full automation, API access, priority AI |

### Feature Breakdown

#### Free Tier
- Manual listing creation (10/day cap)
- Single platform (eBay or Mercari)
- Basic profit calculator
- 7-day analytics history
- Community support

#### Pro Tier ($29/month)
- AI-optimized titles and descriptions
- Multi-platform listing (eBay, Mercari, Poshmark)
- Competitor monitoring (track 5 sellers)
- Smart repricing engine
- 90-day analytics with export
- Daily P&L dashboard
- Email support

#### Empire Tier ($79/month)
- Unlimited listings across all platforms (including TikTok Shop)
- Full competitor intelligence (unlimited sellers)
- Automated batch listing with queue
- AI-powered trend detection and product recommendations
- Marketing content generation (SocialForge integration)
- CRM integration for buyer management
- API access for custom integrations
- Real-time alerts (Telegram/email)
- Priority AI processing
- 1-on-1 onboarding call
- Dedicated support channel

### Revenue Projections

| Scenario | Free Users | Pro Users | Empire Users | MRR |
|----------|-----------|-----------|-------------|-----|
| Launch (Month 1) | 50 | 5 | 1 | $224 |
| Growth (Month 6) | 500 | 50 | 10 | $2,240 |
| Scale (Month 12) | 2,000 | 200 | 50 | $9,750 |
| Mature (Month 24) | 5,000 | 500 | 150 | $26,350 |

---

## 10. Technical Integration Points

### Shared Infrastructure

- **Database**: Same PostgreSQL instance as Empire (separate `relist_` prefixed tables)
- **Auth**: Empire user accounts with role-based access
- **API Gateway**: All endpoints under `/api/v1/relist/`
- **Background Workers**: Celery tasks for batch operations
- **File Storage**: Product images in Empire S3-compatible storage
- **Logging**: Unified Empire logging with `relist` namespace

### Environment Variables (backend/.env)

```
RELIST_EBAY_API_KEY=...
RELIST_EBAY_API_SECRET=...
RELIST_MERCARI_SESSION=...
RELIST_POSHMARK_SESSION=...
RELIST_TIKTOK_SHOP_KEY=...
RELIST_MAX_DAILY_LISTINGS=100
RELIST_MIN_MARGIN_PCT=20
RELIST_AI_BUDGET_DAILY=2.00
```

### Webhook Events

RelistApp emits events that other Empire modules can subscribe to:

```
relist.listing.created
relist.listing.sold
relist.order.fulfilled
relist.competitor.alert
relist.daily.summary
relist.margin.warning
```

---

## Integration Checklist

- [ ] Command Center sidebar entries added
- [ ] MAX natural language queries registered
- [ ] Finance Desk revenue pipeline connected
- [ ] Marketing Desk content templates created
- [ ] SocialForge publishing schedule configured
- [ ] ForgeCRM buyer sync enabled
- [ ] Cost Tracker tags registered
- [ ] Jobs system job types registered
- [ ] SaaS tier limits enforced in API middleware
- [ ] Webhook events emitting to Empire event bus
