# RelistApp - Competitor Monitoring & Intelligence

> Systematic competitive intelligence for drop-ship arbitrage. Track sellers, detect trends, exploit gaps.

---

## Why Competitor Monitoring Matters

In arbitrage, speed is everything. The seller who spots a trending product first and lists it at the right price wins the buy box and the sales volume. Monitoring competitors gives you:

- Early warning on trending products (list before saturation)
- Pricing intelligence (avoid undercutting wars, find premium niches)
- Template and strategy insights (what listing formats convert)
- Saturation signals (when to exit a product category)

---

## 1. Who to Monitor

### eBay - Phone Accessories (Top 50 Sellers)

Track these seller archetypes on eBay. Identify the top 50 by searching "phone case iPhone 16" or "phone accessories" and sorting by best-selling stores.

| Seller Tier | Profile | Example Count | What to Watch |
|-------------|---------|--------------|---------------|
| Power Sellers (100k+ feedback) | Wholesale dropshippers, often China-based | ~15 sellers | New SKUs, pricing floors, shipping speed |
| Mid-Tier (10k-100k feedback) | Domestic resellers, mixed inventory | ~20 sellers | Product selection, bundle strategies |
| Rising Stars (1k-10k feedback) | Active arbitrage players like us | ~15 sellers | What they source, how fast they move |

#### Key eBay Categories to Monitor

- Cell Phone Cases, Covers & Skins (category 20349)
- Cell Phone Screen Protectors (category 58540)
- Cell Phone Chargers & Holders (category 96394)
- Smartwatch Bands (category 182064)
- Tablet Cases & Covers (category 176973)

### Mercari - Electronics Sellers

Mercari's algorithm rewards fresh listings and competitive pricing. Track these seller types:

| Seller Type | How to Find | Count to Track |
|-------------|------------|---------------|
| Top Rated Sellers | Search category, filter by seller rating 5 stars | 20 sellers |
| High Volume | Sellers with 500+ completed sales | 15 sellers |
| Fast Movers | Sellers who list and sell within 48 hours | 15 sellers |

#### Key Mercari Categories

- Electronics > Phone Accessories
- Electronics > Headphones & Earbuds
- Electronics > Chargers & Cables
- Home > Smart Home Devices
- Beauty > Skincare Devices

### TikTok Shop - Trending Sellers

TikTok Shop is the fastest-growing arbitrage platform in 2026. Monitor:

| Seller Type | Signal | Count |
|-------------|--------|-------|
| Viral Product Sellers | Products with 1000+ orders in 7 days | 10 sellers |
| Affiliate Heavy | Sellers using 20+ creator affiliates | 10 sellers |
| Flash Sale Specialists | Running daily limited-time offers | 10 sellers |

---

## 2. What to Track

### Per-Seller Tracking Dashboard

For each monitored seller, RelistApp captures:

| Data Point | Frequency | Storage |
|-----------|-----------|---------|
| New listings (title, price, images) | Every 6 hours | `relist_competitor_listings` |
| Sold item count (rolling 7-day) | Daily | `relist_competitor_metrics` |
| Average selling price by category | Daily | `relist_competitor_metrics` |
| Shipping strategy (free vs paid, speed) | Weekly | `relist_competitor_profiles` |
| Listing template format | Weekly | `relist_competitor_profiles` |
| Return/refund rate (where visible) | Weekly | `relist_competitor_profiles` |
| Price changes on active listings | Every 12 hours | `relist_competitor_prices` |

### Product-Level Tracking

For products that appear across multiple sellers:

| Metric | What It Tells You |
|--------|------------------|
| Seller count for same product | Saturation level -- more sellers = lower margin |
| Price range (min/avg/max) | Where to position your price |
| Sell-through rate | Demand strength -- high rate = safe to list |
| Average days to sell | How fast inventory turns |
| Review/rating distribution | Quality signals -- low ratings = opportunity to differentiate |

### Listing Template Analysis

Capture and analyze high-converting listing formats:

- **Title structure**: keyword order, character count, emoji usage
- **Description format**: bullet points vs paragraphs, feature emphasis
- **Image count and style**: white background, lifestyle, infographic
- **Pricing psychology**: $X.99 vs $X.97 vs round numbers
- **Bundle strategies**: "Buy 2 Get 1 Free", multi-pack pricing
- **Shipping strategy**: free shipping baked into price vs separate

---

## 3. RelistApp Competitor Tracker Feature

### Setup

```
1. Navigate to Command Center > RelistApp > Competitors
2. Click "Add Seller"
3. Enter:
   - Platform (eBay / Mercari / TikTok Shop)
   - Seller username or store URL
   - Category focus (optional)
   - Priority (High / Medium / Low)
4. System begins tracking immediately
```

### Input: Seller Usernames

Add sellers to monitor by platform:

```json
{
  "ebay": [
    {"username": "seller123", "category": "phone_accessories", "priority": "high"},
    {"username": "techdeals2026", "category": "electronics", "priority": "medium"}
  ],
  "mercari": [
    {"username": "quickflips", "category": "electronics", "priority": "high"}
  ],
  "tiktok_shop": [
    {"store_id": "store_abc", "category": "trending", "priority": "high"}
  ]
}
```

### Output: Competitor Intelligence Report

#### New Listings Feed

Updated every 6 hours. Shows what competitors just listed.

| Time | Seller | Platform | Product | Price | Est. Margin | Action |
|------|--------|----------|---------|-------|-------------|--------|
| 2h ago | seller123 | eBay | iPhone 16 Pro MagSafe Case | $14.99 | 45% | [Copy] [Source] |
| 3h ago | techdeals2026 | eBay | USB-C Fast Charger 65W | $12.99 | 38% | [Copy] [Source] |
| 5h ago | quickflips | Mercari | AirPods Pro 2 Silicone Case | $8.99 | 52% | [Copy] [Source] |

The **[Copy]** button clones the listing format into your RelistApp queue.
The **[Source]** button searches AliExpress/Temu for the source product.

#### Top Sellers by Competitor

Weekly report showing each competitor's best-performing products.

```
=== seller123 (eBay) - Week of Mar 30, 2026 ===

Rank | Product                           | Sold | Price  | Revenue
1    | iPhone 16 Clear Case MagSafe      | 87   | $11.99 | $1,043
2    | Samsung S25 Screen Protector 3-pk  | 64   | $9.99  | $639
3    | USB-C to Lightning Adapter         | 51   | $7.99  | $407
4    | Apple Watch Ultra Band Titanium    | 43   | $16.99 | $731
5    | AirTag Leather Holder 4-Pack       | 38   | $13.99 | $532

Total estimated weekly revenue: $3,352
New listings this week: 23
Avg days to first sale: 1.8
```

#### Pricing Changes

Track when competitors adjust prices -- signals market movement.

```
=== Price Changes Detected (Last 24h) ===

Seller       | Product                    | Old Price | New Price | Change
techdeals2026 | 65W USB-C Charger         | $14.99    | $12.99    | -13%
seller123     | iPhone 16 Pro Case        | $12.99    | $11.99    | -8%
quickflips    | Wireless Earbuds Case     | $9.99     | $7.99     | -20%

⚠ Pattern: 3 sellers dropped prices on USB-C accessories this week.
   Signal: Possible oversaturation. Review your listings in this category.
```

---

## 4. Alert System

### Alert Types

| Alert | Trigger | Delivery | Priority |
|-------|---------|----------|----------|
| Hot Product | Competitor lists product with 50+ sales in 7 days | Telegram + Dashboard | High |
| Price War | 3+ competitors drop price on same product category | Telegram | High |
| New Competitor | New seller enters your category with 20+ listings | Dashboard | Medium |
| Trending Category | Category volume up 50%+ week-over-week | Dashboard | Medium |
| Saturation Warning | 10+ sellers listing identical product | Telegram | High |
| Opportunity Gap | Product with high demand but few sellers | Telegram + Dashboard | High |

### Alert Examples

```
🔴 HOT PRODUCT ALERT
Competitor: seller123 (eBay)
Product: "iPhone 16 Pro MagSafe Clear Case - Shockproof"
Sales this week: 87 units
Price: $11.99
Source cost (est.): $2.50 (AliExpress)
Estimated margin: 65%
Sellers in category: 4 (LOW competition)
Action: List immediately at $12.49

---

🟡 SATURATION WARNING
Category: USB-C Fast Chargers
Sellers in last 7 days: 14 (was 6 last week)
Average price: $12.99 (was $15.99 last week)
Average margin: 22% (was 38% last week)
Action: Consider delisting or repricing. Margin compression likely.

---

🟢 OPPORTUNITY GAP
Category: Apple Watch Ultra 3 Bands
Demand signal: 2,400 searches/day on eBay
Active sellers: 3
Average price: $18.99
Source cost: $3.50 (AliExpress)
Estimated margin: 72%
Action: High-opportunity gap. List 5+ variations immediately.
```

### Alert Configuration

```
Settings > RelistApp > Competitor Alerts

Channels:
  ☑ Telegram (@Empire_Max_Bot)
  ☑ Command Center notifications
  ☐ Email

Thresholds:
  Hot Product: Sales > [50] in [7] days
  Price War: [3]+ sellers drop price by [10]%+
  Saturation: [10]+ sellers on identical product
  Opportunity: Demand/seller ratio > [5:1]

Quiet Hours: 11pm - 7am EST
Max alerts/day: 20
```

---

## 5. How to Use Intelligence

### Strategy 1: Follow Fast Sellers

When a competitor lists a product and sells 20+ units in 48 hours:

1. Identify the source product (use image search on AliExpress/Temu)
2. Verify margin (source cost + shipping + platform fee < 60% of sell price)
3. Create listing within 2 hours of alert
4. Price 5% below the competitor to capture buy box
5. Monitor for 48 hours -- if sales velocity > 3/day, scale to other platforms

### Strategy 2: Avoid Saturated Products

When saturation warning triggers:

1. Check your active listings in that category
2. If margin < 25%, delist immediately
3. If margin 25-35%, reprice to match lowest competitor
4. If margin > 35%, hold but stop relisting when sold
5. Redirect inventory budget to opportunity gap categories

### Strategy 3: Find Gaps

Opportunity gaps are the highest-ROI finds in arbitrage.

1. Review gap alerts daily (morning routine)
2. Cross-reference with Google Trends for demand validation
3. Source product from 2+ suppliers for price comparison
4. List on lowest-competition platform first
5. If sell-through > 50% in 7 days, expand to all platforms
6. Monitor for competitor entry -- expect 2-4 weeks before saturation

### Strategy 4: Template Intelligence

When a competitor's listing converts significantly better:

1. Analyze their title keyword structure
2. Note image style and count
3. Study description format and bullet points
4. A/B test their format against yours on 10 listings
5. Adopt the winning format across your catalog

### Strategy 5: Seasonal Pre-Positioning

Use competitor data to predict seasonal trends:

1. Track what competitors start listing 30 days before major events
2. When 3+ competitors list seasonal items, begin sourcing
3. List 14 days before the event (beat the rush)
4. Price 10% above the wave -- early birds pay premium
5. Drop price to market on event week for volume

---

## 6. Competitive Intelligence Workflow

### Daily Routine (15 minutes)

```
Morning (9am):
  1. Check overnight alerts in Telegram (2 min)
  2. Review new listings feed in Command Center (5 min)
  3. Check opportunity gap alerts (3 min)
  4. Action: list top 3 opportunities (5 min via batch listing)

Evening (6pm):
  1. Review price change report (3 min)
  2. Check saturation warnings (2 min)
  3. Adjust tomorrow's listing queue based on intel (5 min)
```

### Weekly Routine (30 minutes)

```
Sunday evening:
  1. Review weekly competitor performance report (10 min)
  2. Identify top 5 products across all competitors (5 min)
  3. Update seller watch list (add/remove) (5 min)
  4. Plan next week's listing categories based on intel (10 min)
```

### Monthly Routine (1 hour)

```
First Monday of month:
  1. Full competitor landscape review (20 min)
  2. Identify new competitors entering your categories (10 min)
  3. Analyze your win rate vs competitors by category (10 min)
  4. Adjust strategy: double down on wins, exit losses (10 min)
  5. Update alert thresholds based on market conditions (10 min)
```

---

## 7. Data Retention & Privacy

- Competitor data stored locally in Empire database
- No personal information collected -- only public listing data
- Data retained for 90 days (configurable)
- All scraping respects platform Terms of Service and rate limits
- Rate limits: eBay API (5,000 calls/day), Mercari (polite scraping, 1 req/3 sec), TikTok Shop API (varies)

---

## 8. Competitor Tracker API

For programmatic access and custom integrations:

```
GET  /api/v1/relist/competitors                    # List all tracked sellers
POST /api/v1/relist/competitors                    # Add seller to track
GET  /api/v1/relist/competitors/{id}/listings       # Recent listings by seller
GET  /api/v1/relist/competitors/{id}/top-products   # Top sellers by seller
GET  /api/v1/relist/competitors/alerts              # Recent alerts
GET  /api/v1/relist/competitors/gaps                # Current opportunity gaps
GET  /api/v1/relist/competitors/saturation          # Saturation report
POST /api/v1/relist/competitors/scan                # Trigger manual scan
```
