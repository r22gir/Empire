# RelistApp Feature Requirements
## 6 Core Features for 1,000 Listings/Day Scale

*Created: April 2, 2026*

---

## Overview

These six features form the backbone of RelistApp's automation engine. Together, they enable a single operator to manage 1,000+ active listings per day across multiple platforms, process orders automatically, and maintain profitability without constant manual intervention.

**Architecture Note**: RelistApp lives at `~/empire-repo/relistapp/` (port 3007) and connects to the Empire backend at port 8000 for AI routing, cost tracking, and desk integration.

---

## Feature 1: Product Scout

### Purpose
Scan wholesale suppliers and deal sources automatically to find products with profitable arbitrage margins. Replaces hours of manual browsing with intelligent, continuous scanning.

### Requirements

#### Core Functionality
- **Source Scanning Engine**: Connect to wholesale supplier APIs and catalog feeds
  - Support minimum 5 supplier integrations (CJ Dropshipping, Alibaba, SaleHoo, Spocket, direct wholesale APIs)
  - Scan on configurable schedule (every 15 min / 1 hr / 4 hr / daily)
  - Filter by category, price range, shipping speed, and minimum margin
- **Deal Detection**: Identify products where sell price on target platform exceeds source price + all fees by minimum threshold
  - Default threshold: 30% net margin
  - Configurable per user/platform
- **Demand Validation**: Cross-reference found products against marketplace demand signals
  - eBay: sold listing count (last 30 days), average sell price, sell-through rate
  - Mercari: similar listings count, price range of sold items
  - Amazon: BSR (Best Seller Rank), review count as demand proxy
- **Competition Analysis**: Check how many active listings exist for same/similar products
  - Flag oversaturated products (>50 active sellers at same price point)
  - Highlight underserved niches (<10 active sellers with proven demand)

#### Margin Calculator (Integrated)
- Auto-calculate margin per platform using real-time fee data
- Include: source cost, platform fees, payment processing, estimated shipping, return allowance (5%)
- Display: gross profit, net profit, ROI percentage, break-even quantity

#### Output
- Daily deal digest: top 50 products sorted by estimated profit
- Product cards with: source link, recommended sell price per platform, estimated daily volume, margin breakdown
- One-click "Add to Listing Queue" action

#### Data Model
```
ProductScout {
  id: UUID
  source_url: string
  source_price: decimal
  source_supplier: string
  title: string
  category: string
  weight_lbs: decimal
  dimensions: {l, w, h}
  image_urls: string[]
  recommended_platforms: Platform[]
  margin_by_platform: {platform: MarginBreakdown}
  demand_score: int (1-100)
  competition_score: int (1-100)
  overall_score: int (1-100)
  scanned_at: datetime
  status: enum(new, listed, rejected, expired)
}
```

### Technical Notes
- Rate-limit all supplier API calls to avoid blocks
- Cache supplier catalogs locally, refresh on schedule
- Use Empire AI desk (Atlas/Raven) for product description enhancement
- Store scan results in PostgreSQL, expire after 7 days if not acted on

---

## Feature 2: Profit Calculator

### Purpose
Real-time, platform-specific profit calculation that accounts for every fee, cost, and variable. Ensures no listing goes live without a verified profit margin.

### Requirements

#### Fee Engines (Per Platform)

**eBay**
- Final Value Fee: 12-15.3% (category-dependent) + $0.30-0.40/order
- Promoted Listings: configurable ad rate (0-15%)
- International fee: +1.65% for international sales
- Store subscription offset (amortized across monthly sales)
- No separate payment processing fee (included in FVF since Managed Payments)

**Mercari**
- Selling fee: 10% flat on item price + buyer-paid shipping
- No payment processing fee for sellers (removed Jan 2026)

**Facebook Marketplace**
- Shipped items: 10% or $0.80 minimum
- Local pickup: 0%
- Shipping cost: seller-arranged (PirateShip rates)

**Poshmark**
- Under $15: flat $2.95
- $15 and above: 20%
- Shipping: paid by buyer (flat-rate USPS label)

**Etsy**
- Listing fee: $0.20
- Transaction fee: 6.5% on total (including shipping)
- Payment processing: 3% + $0.25
- Offsite Ads: 12-15% (mandatory over $10K annual)

**TikTok Shop**
- Referral fee: 6% (3% first 30 days for new sellers)
- Payment processing: ~2.9% + fixed fee
- Fulfillment: FBT required as of March 2026

**Walmart Marketplace**
- Referral fee: 6-15% (category-dependent)
- No monthly fee, no listing fee
- WFS fulfillment: from $3.45/unit (optional)

**Depop**
- US sellers: 3.3% + $0.45 per transaction (no selling fee since July 2024)
- Boosted listings: additional 8%

**StockX**
- Transaction fee: 7-9% (based on seller level)
- Payment processing: 3%
- Shipping fee: $4-5

**OfferUp**
- Shipped items: 12.9% (minimum $1.99)
- Local pickup: 0%

#### Calculator Features
- **Platform Comparison View**: Input source cost, show net profit on ALL platforms side by side
- **Best Platform Recommendation**: Highlight platform with highest net profit for each product
- **Bulk Calculator**: Upload CSV of products, get margin analysis for all platforms at once
- **Break-Even Calculator**: "What's the minimum sell price to hit X% margin on Platform Y?"
- **Scenario Modeling**: Toggle promoted listings, shipping methods, bundle pricing

#### Output Format
```
ProfitCalculation {
  source_cost: decimal
  sell_price: decimal
  platform: string
  platform_fees: {
    listing_fee: decimal
    transaction_fee: decimal
    payment_processing: decimal
    promotion_fee: decimal
    other_fees: decimal
    total_fees: decimal
  }
  shipping_cost: decimal
  return_allowance: decimal (5% default)
  gross_profit: decimal
  net_profit: decimal
  margin_percent: decimal
  roi_percent: decimal
  recommended: boolean
}
```

### Technical Notes
- Fee rates must be configurable and version-controlled (platforms change fees regularly)
- Pull fee schedule updates from a central config, not hardcoded
- Integrate with Product Scout for automatic margin calculation on scanned deals
- API endpoint: `POST /api/v1/relist/calculate-profit`

---

## Feature 3: Bulk Cross-Lister

### Purpose
Create one listing, publish to multiple platforms simultaneously. The single biggest time-saver for scaling to 1,000 listings/day.

### Requirements

#### Listing Creation
- **Universal Listing Form**: Single form that captures all data needed for all platforms
  - Title (80 chars for eBay, 40 chars for Mercari, etc. -- auto-truncate per platform)
  - Description (rich text, auto-format per platform requirements)
  - Photos (up to 24 for eBay, 12 for Mercari, 10 for FB)
  - Category mapping (auto-map from universal category to platform-specific categories)
  - Item specifics / attributes (auto-fill where possible)
  - Price (base price, with per-platform markup rules applied automatically)
  - Shipping (weight, dimensions, shipping profile per platform)
  - Condition (new, used, refurbished -- mapped to each platform's condition taxonomy)

#### Multi-Platform Publishing
- **One-Click Publish**: Select target platforms, hit publish, listings go live on all selected platforms
- **Platform-Specific Optimization**:
  - eBay: fill all item specifics, set Best Offer with auto-accept/decline thresholds
  - Mercari: optimize for mobile-first browsing, smart pricing enabled
  - FB Marketplace: tag relevant local groups, set shipping + local pickup
  - Poshmark: set appropriate brand/size fields, enable offers
- **Bulk Upload**: CSV/spreadsheet import for mass listing creation
  - Template download with all fields
  - Validation before publish (catch errors before they hit APIs)
  - Progress bar with per-platform status

#### Inventory Sync
- **Real-Time Sync**: When item sells on any platform, immediately deactivate on all others
  - Maximum sync delay: 60 seconds
  - Fallback: quantity monitoring every 5 minutes
- **Quantity Management**: Support multi-quantity listings with decremental sync
- **Re-Listing**: Auto-relist items that expire or get removed (with configurable rules)

#### Image Management
- **Image Optimization**: Auto-resize, compress, and format images per platform requirements
- **Watermark Removal Warning**: Flag potential watermarked supplier images
- **Background Removal**: Optional AI background removal for cleaner product photos
- **Gallery Order**: Set image order per platform

#### Template System
- Save listing templates by category
- Clone existing listings with modifications
- Bulk edit: update price/description across all platforms for existing listings

### Technical Notes
- Use platform APIs where available (eBay Browse/Sell API, Mercari internal, FB Commerce API)
- Queue system for bulk operations (Redis/Celery)
- Retry logic for failed platform publishes (exponential backoff)
- Rate limiting per platform API
- Store master listing in Empire DB, with per-platform listing IDs linked

---

## Feature 4: Order Router

### Purpose
When a sale comes in on any platform, automatically place the order with the source supplier and route it to the buyer. Eliminates manual order processing.

### Requirements

#### Sale Detection
- **Webhook Listeners**: Receive real-time sale notifications from all connected platforms
  - eBay: Notification API for item sold events
  - Mercari: Poll for new sales (no webhook available)
  - FB Marketplace: Commerce API order notifications
  - Poshmark: Poll for sales notifications
- **Polling Fallback**: Check for new sales every 5 minutes on platforms without webhooks
- **Deduplication**: Never process the same sale twice

#### Auto-Purchase Pipeline
```
Sale Detected
  -> Verify source product still available
  -> Verify source price still within margin threshold
  -> Place order with supplier (buyer's shipping address)
  -> Capture supplier order ID and tracking info
  -> Update selling platform with tracking number
  -> Send buyer shipping confirmation message
  -> Log transaction in Empire cost tracker
```

#### Safety Controls
- **Price Guard**: Do NOT auto-purchase if source price has increased beyond threshold
  - Default: pause if margin drops below 10%
  - Alert operator for manual review
- **Stock Guard**: If supplier shows out of stock, immediately alert operator
  - Auto-check backup suppliers for same product
  - If no backup: pause listing, message buyer about delay
- **Daily Spend Limit**: Configurable max daily auto-purchase spend
  - Default: $500/day (adjustable)
  - Hard stop when limit reached, queue remaining orders
- **Manual Override**: Flag any order for manual review before purchase
  - High-value orders (>$100) default to manual review
  - First-time supplier orders default to manual review

#### Address Handling
- Extract buyer shipping address from platform sale
- Format address for supplier's order system
- Handle international addresses (if applicable)
- Gift message handling (strip platform-specific messaging)

#### Tracking Integration
- Auto-upload tracking numbers to selling platform
- Support USPS, UPS, FedEx, DHL tracking formats
- Estimated delivery date calculation
- Buyer notification on shipping milestones

#### Error Handling
- Supplier order failed -> alert operator, do not mark as shipped
- Tracking number invalid -> retry after 2 hours, then alert
- Buyer address undeliverable -> contact buyer, hold order
- Platform API down -> queue operations, retry with backoff

### Technical Notes
- Critical path: this feature must be highly reliable. Use database transactions, not in-memory queues.
- Audit log for every auto-purchase (amount, supplier, tracking, timestamps)
- Integration with Empire token tracker for cost logging
- API endpoint: `POST /api/v1/relist/orders/route`

---

## Feature 5: Price Monitor

### Purpose
Continuously monitor source prices and competitor prices. Auto-adjust or auto-pause listings when margins evaporate.

### Requirements

#### Source Price Monitoring
- **Continuous Scanning**: Check source supplier prices for all active listings
  - Frequency: every 4 hours for active listings, every 12 hours for slow movers
  - Configurable per product or category
- **Price Change Detection**:
  - Source price increase -> recalculate margin -> alert if below threshold
  - Source price decrease -> opportunity to increase margin or lower sell price for more sales
- **Out-of-Stock Detection**: Flag when source supplier marks product unavailable
  - Auto-pause listing across all platforms
  - Auto-resume when back in stock (with price re-verification)

#### Competitor Price Monitoring
- **Competitor Tracking**: Monitor competitor prices on same platform for same/similar products
  - Track top 5 competitors per listing
  - Alert when competitor undercuts by >10%
- **Price Position**: Show where your listing ranks in price (cheapest, mid, premium)
- **Auto-Reprice Rules**:
  - Match lowest competitor minus $0.01 (aggressive)
  - Stay within top 3 lowest prices (moderate)
  - Maintain fixed margin regardless of competition (conservative)
  - Never go below minimum margin threshold

#### Auto-Actions
- **Auto-Pause**: Listing automatically paused if:
  - Source price increase makes margin < configurable minimum (default 10%)
  - Source product goes out of stock
  - Competitor price drops below your source cost
- **Auto-Resume**: Listing automatically reactivated if:
  - Source price drops back to profitable level
  - Source product comes back in stock
- **Auto-Reprice**: Adjust selling price based on rules:
  - Source price changed -> maintain target margin -> new sell price calculated
  - Competitor undercut -> match/beat if margin allows
  - Demand spike detected -> increase price by configurable percentage

#### Alerts & Notifications
- Telegram notification for margin alerts (via Empire @Empire_Max_Bot)
- Daily margin report: products at risk, products with improving margins
- Weekly price trend analysis per category

#### Dashboard View
- Heat map: all products colored by margin health (green >30%, yellow 15-30%, red <15%)
- Trend lines: source price history per product (7/30/90 day)
- At-a-glance: total active listings, paused listings, margin distribution

### Technical Notes
- Use background workers (Celery) for price scanning
- Cache competitor prices to reduce API calls
- Store price history in time-series format for trend analysis
- API endpoint: `GET /api/v1/relist/prices/monitor`

---

## Feature 6: Analytics Dashboard

### Purpose
Complete visibility into profit per product, per platform, per day. Know exactly what is making money and what is burning it.

### Requirements

#### Core Metrics

**Revenue Metrics**
- Total revenue (gross) by day/week/month
- Total revenue by platform
- Total revenue by category
- Average order value (AOV) by platform
- Orders per day trend

**Profit Metrics**
- Net profit by day/week/month (after ALL costs)
- Net profit by platform
- Net profit by product (individual product P&L)
- Net profit by category
- Profit margin distribution (histogram)
- Profit per hour worked (manual tracking input)

**Listing Metrics**
- Active listings by platform
- Views per listing (where platform provides data)
- Conversion rate (views to sales) by platform
- Sell-through rate by category
- Average days to sell
- Listing health score (views, watchers, offers)

**Operational Metrics**
- Orders processed per day
- Auto-routed vs. manual orders
- Average time from sale to tracking uploaded
- Return rate by platform/category
- Customer satisfaction scores (where available)

#### Views

**Overview Dashboard**
- Today's snapshot: revenue, profit, orders, active listings
- 7-day trend charts for key metrics
- Top 5 products by profit (today)
- Bottom 5 products by profit (today)
- Platform comparison bar chart

**Product Performance**
- Sortable table: all products with revenue, cost, profit, margin, sales count
- Drill-down to individual product: full P&L, sales history, price history
- Product lifecycle: when listed, first sale, total sales, current status
- Tag products as "winner" or "loser" for quick filtering

**Platform Performance**
- Side-by-side platform comparison
- Best platform per category (data-driven recommendation)
- Fee impact analysis: how much each platform takes in fees
- Platform health: account standing, defect rates, response time

**Trend Analysis**
- Category trends: which categories are growing/declining
- Seasonal patterns: day-of-week and time-of-day analysis
- Margin trends: are margins improving or compressing over time
- Volume trends: sales velocity changes

#### Export & Reporting
- CSV export for all data views
- Weekly automated report (email/Telegram)
- Tax report: total income, total costs, net by quarter
- Integration with Empire cost tracker (`/api/v1/costs/*`)

#### Real-Time Updates
- WebSocket connection for live order feed
- Dashboard auto-refreshes every 60 seconds
- Push notifications for milestone events (100th sale, $1K profit, etc.)

### Technical Notes
- Use Empire Command Center (port 3005) for dashboard UI or standalone at port 3007
- Backend aggregation via PostgreSQL materialized views for performance
- Cache dashboard queries with 5-minute TTL
- Historical data retention: 2 years minimum
- API endpoints:
  - `GET /api/v1/relist/analytics/overview`
  - `GET /api/v1/relist/analytics/products`
  - `GET /api/v1/relist/analytics/platforms`
  - `GET /api/v1/relist/analytics/trends`

---

## Implementation Priority

| Priority | Feature | Effort | Impact | Dependencies |
|----------|---------|--------|--------|-------------|
| P0 | Profit Calculator | 1 week | Critical -- nothing lists without margin verification | None |
| P0 | Bulk Cross-Lister | 2 weeks | Critical -- this is the core value prop | Profit Calculator |
| P1 | Order Router | 2 weeks | High -- eliminates manual order processing | Bulk Cross-Lister |
| P1 | Price Monitor | 1 week | High -- protects margins at scale | Profit Calculator |
| P2 | Product Scout | 2 weeks | Medium -- accelerates product research | Profit Calculator |
| P2 | Analytics Dashboard | 2 weeks | Medium -- enables data-driven decisions | All features feed data |

**Total estimated build time: 8-10 weeks for MVP of all 6 features**

---

## Integration Points with Empire

- **AI Routing**: Use Empire AI desks for product description generation (Raven desk)
- **Cost Tracker**: Log all platform fees and supplier costs via `/api/v1/costs/*`
- **Telegram Bot**: Send alerts and daily reports via @Empire_Max_Bot
- **Command Center**: Embed RelistApp dashboard in Empire Command Center (port 3005)
- **Scheduler**: Use Empire autonomous scheduler for scan jobs and price checks
