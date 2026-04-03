# RelistApp Automation Requirements

> Last updated: April 2026
> Purpose: Define the features RelistApp needs to automate 1,000 sales/day across platforms.

---

## Scale Target: 1,000 Sales Per Day

At 1,000 sales/day across platforms, RelistApp must handle:
- 3,000-5,000 active listings (assuming 20-33% sell-through rate)
- 50,000+ price checks/day (each listing checked every 30 min)
- 1,000 order processing events/day
- 100-150 returns/refunds per day (10-15% return rate)
- 5,000+ inventory availability checks/day
- Real-time metric tracking across 3-5 platform accounts

This is not achievable manually. Every feature below must be automated with minimal human intervention.

---

## Feature 1: Product Scout

### What It Does
Continuously scans source marketplaces (Amazon, Walmart, Target, retail clearance sites) to identify products that can be resold profitably on destination platforms (eBay, Amazon, Walmart Marketplace, Mercari, Poshmark).

### Core Capabilities
- **BSR Scanner**: Monitor Amazon Best Sellers Rank across categories. Products with BSR 1-100K in main categories sell predictably. Flag items where source price + fees < destination selling price by 20%+.
- **Clearance/Deal Tracker**: Scan Amazon Warehouse, Walmart Clearance, Target Circle deals, and retail sites for markdowns. Alert when products hit profitability thresholds.
- **Category Sweeper**: Batch-scan entire categories on source sites, comparing against destination platform prices. Filter by minimum ROI, maximum competition, sales velocity.
- **Reverse Lookup**: Given a product selling well on eBay/Walmart, find the cheapest source to acquire it.
- **Deal Velocity Scoring**: Estimate how quickly a deal will be discovered by competitors. High-velocity deals (clearance, lightning deals) get priority alerts.

### Why It's Essential
Product sourcing is the bottleneck for every arbitrage operation. At 1,000 sales/day, you need to discover 50-100 new profitable products daily to replace sold-out and margin-collapsed SKUs. Manual sourcing caps out at 20-30 products/day for a skilled human.

### Build Priority: **P0 -- Must Have for Launch**

### Existing Tools That Do This
| Tool | Coverage | Limitation |
|------|----------|------------|
| Tactical Arbitrage | 1,400+ source sites to Amazon | Amazon-only destination, batch scans (not real-time), $59-129/mo |
| Helium 10 | Amazon product research | Amazon ecosystem only, no source-to-destination matching |
| Jungle Scout | Amazon opportunity finder | Amazon-only, no cross-platform |
| SourceMogul | Retail site scanning | Limited site coverage, Amazon-only destination |
| ZIK Analytics | eBay product research | eBay-only, research not sourcing |

**RelistApp advantage**: Cross-platform sourcing with real-time scanning and multi-destination profitability comparison.

---

## Feature 2: Profit Calculator

### What It Does
Real-time cross-platform profit calculation that accounts for every cost: source price, platform fees, shipping, packaging, returns allowance, tax, and payment processing.

### Core Capabilities
- **Fee Engine**: Maintain current fee schedules for Amazon (referral fee by category 8-45%, FBA fees by size/weight, storage fees), eBay (13.25% final value fee, promoted listing fees), Walmart (6-20% referral fee), Mercari (10%), Poshmark (20%).
- **Shipping Calculator**: Calculate actual shipping cost based on item dimensions, weight, origin/destination zip, and carrier rates (USPS, UPS, FedEx). Support FBA fee calculation.
- **Returns Allowance**: Auto-apply category-specific return rate (5% for electronics, 15% for home goods, 25% for apparel) as a cost factor.
- **Tax Impact**: Calculate sales tax obligations per state based on current nexus status.
- **Multi-Platform Comparison**: Show side-by-side profitability for the same product listed on Amazon vs eBay vs Walmart vs Mercari.
- **Break-Even Calculator**: Show minimum selling price needed to achieve target margin on each platform.
- **Bulk Calculator**: Process CSV uploads of 1,000+ products and return profitability analysis for each.

### Why It's Essential
Incorrect profit calculation is the #1 reason arbitrage sellers lose money. A product that looks profitable on Amazon may be unprofitable on eBay due to different fee structures. At 1,000 sales/day, even a 2% calculation error means 20 unprofitable sales daily.

### Build Priority: **P0 -- Must Have for Launch**

### Existing Tools That Do This
| Tool | Coverage | Limitation |
|------|----------|------------|
| BuyBotPro | Amazon fee calculation | Amazon-only, one product at a time, $29.95/mo |
| SellerAmp | Amazon profit calculator | Amazon-only, Chrome-only, $19/mo |
| Keepa | Price history (no profit calc) | No fee calculation, no cost basis input |
| Amazon Revenue Calculator | Amazon FBA fees | Amazon only, manual entry, no bulk |
| eBay Fee Calculator | eBay fees | eBay only, basic |

**RelistApp advantage**: Unified profit calculation across all platforms with bulk processing and real-time fee schedule updates.

---

## Feature 3: Bulk Cross-Lister

### What It Does
Takes a product from the source marketplace, pulls all listing data (title, images, description, specifications, UPC/EAN), optimizes it for each destination platform's search algorithm, and creates listings in bulk.

### Core Capabilities
- **Data Extraction**: Pull title, bullet points, description, images (all resolutions), dimensions, weight, UPC/EAN, brand, category from source listing.
- **Title Optimization**: Rewrite titles per platform. Amazon titles prioritize keywords (200 char max). eBay titles are 80 chars max with different keyword strategy. Walmart has its own requirements.
- **Image Processing**: Download source images, remove watermarks if present, resize to platform requirements, add white background if needed. Support custom photo uploads.
- **Description Generator**: Create platform-optimized descriptions. HTML support for eBay, A+ Content structure for Amazon, Walmart-format specs.
- **Category Mapping**: Auto-map source category to correct destination category on each platform.
- **Specification Extraction**: Pull item specifics (color, size, material, brand) and map to required fields on each platform.
- **Bulk Operations**: List 100+ products per batch. Queue management for API rate limits.
- **Template System**: Save listing templates per category for consistent formatting.
- **Duplicate Detection**: Prevent listing the same product twice on the same platform.

### Why It's Essential
Manually creating a listing takes 10-15 minutes per product per platform. At 100 new products/day across 3 platforms, that is 50-75 hours of daily labor. Automation reduces this to minutes.

### Build Priority: **P0 -- Must Have for Launch**

### Existing Tools That Do This
| Tool | Coverage | Limitation |
|------|----------|------------|
| AutoDS | Shopify, eBay, Wix, FB Marketplace | No Amazon support, drop-ship model only |
| Sellbrite | Amazon, eBay, Walmart, Etsy | Listing tool only, no sourcing or analytics, $29-179/mo |
| Listing Mirror | Amazon, eBay, Walmart, Etsy | Listing sync only, no profit calc, $25-99/mo |
| inkFrog | eBay listing tool | eBay-only, no cross-platform |
| Vendoo | Multi-platform crosslister | Focused on resale/thrift, limited bulk capability |

**RelistApp advantage**: Integrated cross-listing with profit-aware optimization. RelistApp only creates listings that meet profitability thresholds, and auto-optimizes titles/descriptions per platform's search algorithm.

---

## Feature 4: Order Router

### What It Does
When a sale comes in on any destination platform, automatically determines the best source to purchase from and either auto-purchases or queues for one-click fulfillment.

### Core Capabilities
- **Order Ingestion**: Monitor all platform seller accounts via API for new orders in real-time.
- **Source Selection**: For each order, determine the best source based on: price (lowest), availability (in stock), shipping speed (fastest to buyer), reliability (source success rate).
- **Auto-Purchase**: For approved sources, automatically place the purchase order with buyer's shipping address. Support Amazon, Walmart, and wholesale supplier ordering.
- **Gift Option**: Mark source orders as "gift" to suppress invoices/prices in the package (critical for retail arbitrage).
- **Multi-Source Fallback**: If primary source is OOS, automatically check secondary and tertiary sources.
- **Manual Queue**: For high-value orders or unverified sources, queue for human review before purchasing.
- **Order Tracking Bridge**: Capture tracking number from source order, upload to destination platform automatically.
- **Cost Logging**: Record actual purchase price for accurate profit calculation (source price may differ from estimated price at listing time).
- **Rate Limiting**: Manage purchase velocity to avoid triggering source platform fraud detection.

### Why It's Essential
At 1,000 sales/day, processing orders manually is impossible. Each order requires: check source availability, compare source prices, place purchase, enter shipping info, wait for tracking, upload tracking to selling platform. Manually this takes 5-10 minutes per order = 83-167 hours/day.

### Build Priority: **P1 -- Required for Scale**

Note: This feature carries legal/ToS risk. See Risk Analysis. The buy-and-hold model is safer than real-time drop-ship purchasing. Order Router should support both models:
- **Drop-ship mode**: auto-purchase from source when sale comes in (higher risk, lower capital)
- **Inventory mode**: purchase from source in advance, ship from own stock (lower risk, higher capital)

### Existing Tools That Do This
| Tool | Coverage | Limitation |
|------|----------|------------|
| AutoDS | Auto-fulfillment with credits | Requires per-order credits, reliability issues, no Amazon destination |
| DSM Tool | eBay auto-fulfillment | eBay-only, retail drop-ship model (policy violation risk) |
| Hustle Got Real | Manual order management | No automation, tracking tool only |

**RelistApp advantage**: Dual-mode fulfillment (drop-ship and inventory), multi-source failover, integrated tracking bridge, no per-order credit fees.

---

## Feature 5: Price Monitor

### What It Does
Continuously monitors both source prices and competitor prices on destination platforms. Auto-adjusts listing prices to maintain margins and competitiveness. Auto-pauses listings when profitability disappears.

### Core Capabilities
- **Source Price Tracking**: Check source product price every 15-30 minutes. Detect price increases that would eliminate margin.
- **Destination Price Tracking**: Monitor competitor prices on selling platform. Track Buy Box price on Amazon.
- **Auto-Reprice**: Adjust listing price based on rules:
  - Stay $0.01-$1.00 below lowest competitor while maintaining minimum margin
  - Match Buy Box price when margin allows
  - Increase price when competition decreases
- **Margin Floor**: Never auto-reprice below minimum margin threshold (configurable per product, default 15%).
- **Auto-Pause**: Immediately pause listing when:
  - Source price increases above break-even
  - Margin drops below minimum threshold
  - Source goes out of stock
  - Too many competitors enter the listing
- **Auto-Resume**: Re-activate paused listings when conditions improve.
- **Price Alerts**: Notify seller of significant price changes (>10% movement).
- **Historical Price Database**: Store price history for trend analysis and seasonal planning.

### Why It's Essential
Prices change constantly. Amazon has 2.5 million price changes per day. A product profitable at 9 AM may be unprofitable by noon. Without automated monitoring, sellers unknowingly sell at a loss. At 3,000-5,000 active listings, manual price checking is impossible.

### Build Priority: **P0 -- Must Have for Launch**

### Existing Tools That Do This
| Tool | Coverage | Limitation |
|------|----------|------------|
| Keepa | Amazon price tracking | Amazon-only, no auto-reprice, no margin calculation, ~$19/mo |
| RepricerExpress | Amazon auto-repricing | Amazon-only, $79-499/mo, no source price tracking |
| AutoDS | Price/stock monitoring | No Amazon, reliability issues, extra credits for automation |
| Informed.co | Amazon/eBay repricing | Repricing only, no source monitoring, $99-249/mo |

**RelistApp advantage**: Monitors BOTH source and destination prices (no competitor does both). Cross-platform repricing from a single dashboard. Integrated margin-floor protection.

---

## Feature 6: Inventory Sync

### What It Does
Monitors source product availability in real-time and automatically ends or pauses listings when the source goes out of stock. Prevents overselling and order cancellations.

### Core Capabilities
- **Availability Checker**: Check source product availability every 15-30 minutes per SKU.
- **Auto-End Listing**: When source goes OOS, immediately end or pause the listing on all destination platforms.
- **Auto-Relist**: When source comes back in stock, automatically relist (if still profitable).
- **Multi-Platform Sync**: If one source goes OOS but alternates are available, keep listing active and switch source.
- **Quantity Tracking**: For sellers holding inventory, track on-hand quantity and auto-end listing when quantity hits zero.
- **FBA Inventory Sync**: Monitor FBA inventory levels and reconcile with listing status.
- **Cross-Platform Quantity Sync**: If you have 5 units and list on 3 platforms, manage available quantity to prevent overselling (e.g., 2 on Amazon, 2 on eBay, 1 buffer).
- **Low Stock Alerts**: Notify when source or held inventory drops below reorder threshold.
- **OOS Analytics**: Track which products go OOS most frequently and which sources are least reliable.

### Why It's Essential
Order cancellations are the fastest path to account suspension. Amazon penalizes pre-fulfillment cancellations above 2.5%. At 1,000 sales/day, even a 1% OOS-cancellation rate = 10 cancellations/day, which will breach Amazon's threshold within weeks. Inventory sync is the primary defense.

### Build Priority: **P0 -- Must Have for Launch**

### Existing Tools That Do This
| Tool | Coverage | Limitation |
|------|----------|------------|
| AutoDS | Stock monitoring with auto-end | No Amazon, reliability issues, credit-based |
| Listing Mirror | Multi-channel inventory sync | Sync only (not source monitoring), $25-99/mo |
| Sellbrite | Inventory sync across channels | No source monitoring, listing tool focus |
| ChannelAdvisor | Enterprise inventory management | $1000+/mo, enterprise-only, overkill for most sellers |

**RelistApp advantage**: Monitors source availability (not just own inventory), auto-ends across all platforms simultaneously, and auto-relists when profitable again.

---

## Feature 7: Analytics Dashboard

### What It Does
Comprehensive profit tracking and business intelligence dashboard showing performance per product, per platform, per time period, with trend analysis and actionable insights.

### Core Capabilities

#### Profit Tracking
- **Per-Product P&L**: Revenue, source cost, platform fees, shipping cost, return costs, net profit, ROI, margin % -- for every single SKU.
- **Per-Platform P&L**: Total revenue, costs, and profit broken down by Amazon, eBay, Walmart, etc.
- **Per-Day P&L**: Daily profit and loss with trend lines.
- **Per-Category Analysis**: Which product categories are most/least profitable.
- **Real vs. Estimated Profit**: Compare estimated profit (at listing time) vs actual profit (after all costs including returns).

#### Performance Metrics
- **Sales Velocity**: Units sold per day/week/month per product and per platform.
- **Sell-Through Rate**: Percentage of listed products that sell within 30 days.
- **Average Days to Sell**: How long products sit before selling.
- **Return Rate**: Per product, per category, per platform.
- **Win Rate**: Percentage of sourced products that achieved target margin.

#### Account Health
- **Integrated AHR tracking** (Amazon) and Seller Level tracking (eBay).
- **Metric trend lines** with projected trajectory.
- **Red/yellow/green status** for every tracked metric.
- **Alert history**: log of all automated actions taken (paused listings, price changes, etc.).

#### Business Intelligence
- **Best Performers**: Top 10 products by profit, ROI, and volume.
- **Worst Performers**: Bottom 10 products requiring attention.
- **Source Reliability**: Success rate per source supplier.
- **Platform Comparison**: Which platform generates best margins for which categories.
- **Seasonal Trends**: Historical patterns for planning inventory purchases.
- **Tax Reporting**: Sales by state for nexus tracking and sales tax filing.

#### Export and Reporting
- CSV/PDF export for all reports.
- Scheduled email reports (daily summary, weekly deep-dive, monthly P&L).
- QuickBooks/Xero integration for accounting.
- Tax-ready reports for CPA.

### Why It's Essential
"What gets measured gets managed." At 1,000 sales/day, intuition fails. Sellers need data to answer: Which products should I restock? Which should I drop? Which platform should I focus on? Am I actually making money? Without analytics, sellers often discover they have been losing money only when they check their bank account.

### Build Priority: **P1 -- Required for Scale (basic version at launch, full version in v2)**

### Existing Tools That Do This
| Tool | Coverage | Limitation |
|------|----------|------------|
| Helium 10 (Profits) | Amazon profit tracking | Amazon-only, $39-279/mo for full suite |
| Sellerboard | Amazon profit analytics | Amazon-only, $15-63/mo |
| AutoDS | Basic revenue reporting | No per-product P&L, no cross-platform |
| QuickBooks Commerce | Financial reporting | Not arbitrage-specific, no platform integration |

**RelistApp advantage**: Cross-platform profit analytics with per-product granularity, integrated account health monitoring, and arbitrage-specific metrics (win rate, source reliability, margin trajectory).

---

## Build Priority Summary

| Priority | Feature | Justification |
|----------|---------|---------------|
| **P0** | Product Scout | Cannot operate without deal flow |
| **P0** | Profit Calculator | Cannot list without knowing profitability |
| **P0** | Bulk Cross-Lister | Cannot scale listing creation manually |
| **P0** | Price Monitor | Cannot protect margins without real-time monitoring |
| **P0** | Inventory Sync | Cannot avoid cancellations without availability tracking |
| **P1** | Order Router | Needed for scale but can be semi-manual initially |
| **P1** | Analytics Dashboard | Basic version at launch, full version post-launch |

### Recommended Build Order

**Phase 1 (MVP -- Weeks 1-8)**: Profit Calculator + Inventory Sync + Price Monitor
- Get the defensive systems working first. These prevent losses.

**Phase 2 (Core -- Weeks 9-16)**: Product Scout + Bulk Cross-Lister
- Add the offensive systems. These generate revenue.

**Phase 3 (Scale -- Weeks 17-24)**: Order Router + Analytics Dashboard
- Add the scale systems. These enable 1,000 sales/day.

**Phase 4 (Intelligence -- Weeks 25-32)**: Advanced analytics, ML-based deal scoring, predictive pricing, mobile app.

---

## Technical Infrastructure for 1,000 Orders/Day

### API Requirements
- Amazon SP-API (Selling Partner API): product data, orders, inventory, reports
- eBay Browse/Sell/Fulfillment APIs: listings, orders, inventory
- Walmart Marketplace APIs: listings, orders, inventory
- Carrier APIs (USPS, UPS, FedEx): rate calculation, tracking
- Payment APIs (Stripe, PayPal): payment processing for direct sales

### Processing Requirements
- Job queue system (Redis/Celery) for async price checks, inventory sync, order processing
- 50,000+ API calls/day across all platforms
- Sub-5-second response time for price lookups and profit calculations
- 99.9% uptime (1,000 sales/day means every minute of downtime = missed orders)
- Database capable of storing 100K+ product records with full price history

### Monitoring
- Real-time system health dashboard
- API rate limit tracking per platform
- Error rate monitoring with auto-alerting
- Queue depth monitoring (detect processing backlogs)

---

## Sources

- [Automated Order Fulfillment 2026 - Shopify](https://www.shopify.com/blog/automated-order-fulfillment)
- [Retail Arbitrage in 2026 - GoAura](https://goaura.com/blog/retail-arbitrage-on-amazon)
- [Best Retail Arbitrage Software 2026 - Gitnux](https://gitnux.org/best/retail-arbitrage-software/)
- [Top Online Arbitrage Software 2026](https://wifitalents.com/best/online-arbitrage-software/)
- [AutoDS Review 2026 - Closo](https://closo.co/blogs/dropshipping/autods-review-2026-the-automation-dream-vs-the-reality)
- [Best Amazon Seller Tools 2026 - The Selling Guys](https://www.thesellingguys.com/tools-supplies-use-succeed-amazon-fba/)
- [Tactical Arbitrage Review 2026](https://www.thesellingguys.com/tactical-arbitrage-review/)
- [Amazon Account Health 2026](https://www.hrlinfotechs.com/blog/amazon-account-health-2026-the-must-follow-checklist-to-stay-safe-scale-your-business/)
