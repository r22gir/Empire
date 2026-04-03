# RelistApp Revenue Scenarios (April 2026)

> All calculations use real fee data from platform_fee_analysis.md.
> Assumes a solo operator with RelistApp automation tooling.

---

## Common Assumptions

- **Primary selling platforms**: eBay (14.6% effective), Mercari (10%), FB Marketplace (10% shipped / 0% local), TikTok Shop (7%)
- **Blended platform fee estimate**: 11% (weighted average across channels)
- **Shipping cost per item**: $5.50 average (USPS Ground Advantage, under 1 lb, commercial rate)
- **Packaging materials**: $0.50/item (poly mailer, label, tape)
- **Payment processing**: Included in platform fees for all major platforms
- **Returns rate**: 5% (industry average; returned items are a total loss at this scale)
- **RelistApp software cost**: $0/month (internal tool)
- **Working hours**: Solo operator, ~4-6 hours/day

---

## Scenario A: Ultra-Low Margin, High Volume

**Target: $0.25 net profit/unit x 1,000 units/day = $7,500/month**

### Product Profile
- **What fits**: Phone cases, charging cables, screen protectors, cheap jewelry, hair accessories, small kitchen gadgets
- **Source**: AliExpress/Temu at $1-3/unit; Amazon Warehouse at $3-5/unit
- **Average buy price**: $2.50
- **Average sell price**: $8.99

### Unit Economics (per item sold on eBay at 14.6%)

| Line Item | Amount |
|---|---|
| Sale price | $8.99 |
| - Platform fee (14.6%) | -$1.31 |
| - Per-order fee | -$0.30 |
| - Cost of goods | -$2.50 |
| - Shipping | -$5.09 |
| - Packaging | -$0.50 |
| **Gross profit per unit** | **-$0.71** |

**PROBLEM: At $8.99 sale price on eBay, this is a LOSS.** Let's try Mercari (10%):

| Line Item | Amount |
|---|---|
| Sale price | $8.99 |
| - Platform fee (10%) | -$0.90 |
| - Cost of goods | -$2.50 |
| - Shipping (prepaid label) | -$5.25 |
| - Packaging | -$0.50 |
| **Gross profit per unit** | **-$0.16** |

**Still a loss.** Let's try TikTok Shop (7%):

| Line Item | Amount |
|---|---|
| Sale price | $8.99 |
| - Platform fee (7%) | -$0.63 |
| - Cost of goods | -$2.50 |
| - Shipping | -$5.09 |
| - Packaging | -$0.50 |
| **Gross profit per unit** | **$0.27** |

### Adjusted Monthly Projection (TikTok Shop only)

| Metric | Value |
|---|---|
| Units sold/day | 1,000 |
| Gross profit/unit | $0.27 |
| Gross profit/day | $270 |
| Returns (5% = 50 units/day, total loss) | -$2.50 x 50 = -$125/day |
| Net profit/day | $145 |
| **Net profit/month (30 days)** | **$4,350** |

### Capital Requirements
- Inventory float (7-day supply): 7,000 units x $2.50 = **$17,500**
- Shipping supplies: **$500**
- Total starting capital: **$18,000**

### Break-Even Timeline
- At $145/day net: ~124 days to recoup capital
- **4+ months to break even**

### Feasibility Rating: 1/5 -- NOT REALISTIC

**Why this fails:**
- 1,000 units/day = 1,000 packages to ship per day. A solo operator cannot pack and ship 1,000 packages daily. That's 125/hour in an 8-hour day.
- Shipping costs consume 57% of revenue at this price point.
- Only viable on TikTok Shop (lowest fees), and even then margins are razor-thin.
- One bad return day wipes out a week of profit.
- AliExpress shipping time (15-45 days) means you need huge upfront inventory.
- 2026 tariffs on Chinese imports (10-25%) push COGS higher.
- $4,350/month for full-time work = ~$18/hour equivalent. A regular job pays more.

---

## Scenario B: Low Margin, High Volume

**Target: $0.50 net profit/unit x 1,000 units/day = $15,000/month**

### Product Profile
- **What fits**: Branded clearance items, seasonal goods, Amazon Warehouse electronics accessories, Walmart clearance home goods
- **Source**: Amazon Warehouse (30-50% off retail), Walmart clearance
- **Average buy price**: $5.00
- **Average sell price**: $14.99

### Unit Economics (per item sold on eBay at 14.6%)

| Line Item | Amount |
|---|---|
| Sale price | $14.99 |
| - Platform fee (14.6%) | -$2.19 |
| - Per-order fee | -$0.40 |
| - Cost of goods | -$5.00 |
| - Shipping | -$5.50 |
| - Packaging | -$0.50 |
| **Gross profit per unit** | **$1.40** |

### On Mercari (10%)

| Line Item | Amount |
|---|---|
| Sale price | $14.99 |
| - Platform fee (10%) | -$1.50 |
| - Cost of goods | -$5.00 |
| - Shipping (prepaid) | -$5.25 |
| - Packaging | -$0.50 |
| **Gross profit per unit** | **$2.74** |

### Blended (50% eBay, 30% Mercari, 20% FB Marketplace shipped)

| Channel | Units/Day | Profit/Unit | Daily Profit |
|---|---|---|---|
| eBay | 500 | $1.40 | $700 |
| Mercari | 300 | $2.74 | $822 |
| FB Marketplace | 200 | $2.70 | $540 |
| **Total** | **1,000** | **$2.06 avg** | **$2,062** |

### Monthly Projection

| Metric | Value |
|---|---|
| Gross profit/day | $2,062 |
| Returns (5% = 50 units, COGS + shipping lost) | -$525/day |
| Net profit/day | $1,537 |
| **Net profit/month** | **$46,110** |

Wait -- that looks too good. But 1,000 units/day is the problem.

### Operational Reality Check

- 1,000 packages/day is a **warehouse operation**, not a solo gig
- At 2 minutes per package (pick, pack, label, stage): 2,000 minutes = **33 hours/day**
- You need 4-5 employees or a 3PL
- Employee cost (~3 packers at $15/hr x 8 hrs): $360/day = $10,800/month
- Warehouse rent: ~$1,500-3,000/month
- Revised net: $46,110 - $10,800 - $2,000 = **~$33,310/month**

### Realistic Solo Operator Scale: 50-100 units/day

| Metric | 50/day | 100/day |
|---|---|---|
| Gross profit/day | $103 | $206 |
| Returns loss/day | -$26 | -$53 |
| Net profit/day | $77 | $153 |
| **Net profit/month** | **$2,310** | **$4,590** |
| Capital needed (7-day inventory) | $1,750 | $3,500 |
| Break-even | ~23 days | ~23 days |

### Feasibility Rating: 2/5 -- MARGINALLY VIABLE (at 50-100 units/day)

**Why it's hard:**
- At solo scale (50-100/day), you're earning $2,300-$4,600/month for 4-6 hours/day of work.
- Sourcing 50-100 profitable items DAILY from Amazon Warehouse/Walmart clearance is inconsistent.
- You're competing with thousands of other arbitrage sellers for the same deals.
- Inventory risk: clearance items don't always sell; you may be stuck with dead stock.

---

## Scenario C: Moderate Margin, Moderate Volume

**Target: $2.00 net profit/unit x 250 units/day = $15,000/month**

### Product Profile
- **What fits**: Name-brand clothing (clearance), electronics accessories (OEM), home decor, beauty/skincare, books, specialty kitchen tools
- **Source**: Amazon Warehouse (40-50% off), Walmart clearance, retail arbitrage (Target/TJMaxx), wholesale lots
- **Average buy price**: $8.00
- **Average sell price**: $24.99

### Unit Economics (per item sold on eBay at 14.6%)

| Line Item | Amount |
|---|---|
| Sale price | $24.99 |
| - Platform fee (14.6%) | -$3.65 |
| - Per-order fee | -$0.40 |
| - Cost of goods | -$8.00 |
| - Shipping | -$5.50 |
| - Packaging | -$0.75 |
| **Gross profit per unit** | **$6.69** |

### On Mercari (10%)

| Line Item | Amount |
|---|---|
| Sale price | $24.99 |
| - Platform fee (10%) | -$2.50 |
| - Cost of goods | -$8.00 |
| - Shipping | -$5.25 |
| - Packaging | -$0.75 |
| **Gross profit per unit** | **$8.49** |

### Blended Multi-Channel

| Channel | Units/Day | Profit/Unit | Daily Profit |
|---|---|---|---|
| eBay | 100 | $6.69 | $669 |
| Mercari | 60 | $8.49 | $509 |
| FB Marketplace (shipped) | 50 | $8.24 | $412 |
| TikTok Shop | 40 | $9.24 | $370 |
| **Total** | **250** | **$7.84 avg** | **$1,960** |

### Monthly Projection

| Metric | Value |
|---|---|
| Gross profit/day | $1,960 |
| Returns (5% = ~13 units, COGS + shipping lost) | -$175/day |
| eBay Store subscription (Basic) | -$0.73/day ($21.95/mo) |
| Net profit/day | $1,784 |
| **Net profit/month** | **$53,520** |

### But again -- can a solo operator do 250 units/day?

At 3 minutes per package (these are slightly larger/heavier items): 750 minutes = **12.5 hours/day**. No.

### Realistic Solo Operator Scale: 30-60 units/day

| Metric | 30/day | 60/day |
|---|---|---|
| Gross profit/day | $235 | $470 |
| Returns loss/day | -$20 | -$40 |
| Net profit/day | $215 | $430 |
| **Net profit/month** | **$6,450** | **$12,900** |
| Capital needed (10-day inventory) | $2,400 | $4,800 |
| Break-even | ~11 days | ~11 days |

### Feasibility Rating: 4/5 -- MOST REALISTIC SCENARIO

**Why this works:**
- 30-60 items/day is achievable for a solo operator (2-3 hours packing).
- $6,450-$12,900/month is real income.
- $25 price point items sell well across all platforms.
- Sourcing 30-60 items/day with $8 cost and $25 sale is doable through:
  - Amazon Warehouse Deals (automated scanning with RelistApp)
  - Walmart.com clearance alerts
  - Weekly retail arbitrage runs (Target, TJMaxx, Ross)
  - Wholesale lot purchases
- Break-even in under 2 weeks.
- The $8 buy / $25 sell ratio (3.1x markup) is sustainable.

---

## Scenario D: Mixed Portfolio

**Target: 500 x $0.25 + 200 x $1.00 + 50 x $5.00 = $575/day = $17,250/month**

### Portfolio Breakdown

#### Tier 1: Micro-Margin (500 units/day @ $0.25 profit)
- Products: Phone accessories, cheap gadgets, commodity items
- Buy: $2.50 / Sell: $8.99 (TikTok Shop only -- only platform where this works)
- Daily gross: $135 (before returns)

#### Tier 2: Low-Margin (200 units/day @ $1.00 profit)
- Products: Clearance branded goods, seasonal items
- Buy: $5.00 / Sell: $14.99 (eBay/Mercari)
- Daily gross: $200 (before returns)

#### Tier 3: Quality-Margin (50 units/day @ $5.00 profit)
- Products: Name-brand electronics accessories, premium home goods, specialty items
- Buy: $10.00 / Sell: $29.99 (all platforms)
- Daily gross: $250 (before returns)

### Combined Monthly Projection

| Tier | Units/Day | Gross/Day | Returns Loss/Day | Net/Day |
|---|---|---|---|---|
| Micro ($0.25) | 500 | $135 | -$62 | $73 |
| Low ($1.00) | 200 | $200 | -$53 | $147 |
| Quality ($5.00) | 50 | $250 | -$50 | $200 |
| **Total** | **750** | **$585** | **-$165** | **$420** |

| Metric | Value |
|---|---|
| Net profit/day | $420 |
| **Net profit/month** | **$12,600** |

### Capital Requirements

| Tier | Inventory (10-day float) | Cost |
|---|---|---|
| Micro | 5,000 units x $2.50 | $12,500 |
| Low | 2,000 units x $5.00 | $10,000 |
| Quality | 500 units x $10.00 | $5,000 |
| Supplies & buffer | | $2,500 |
| **Total** | | **$30,000** |

### Solo Operator Reality: 750 units/day is IMPOSSIBLE solo

Realistic solo scale for mixed portfolio:

| Tier | Realistic Units/Day | Net/Day |
|---|---|---|
| Micro | 0 (drop this entirely) | $0 |
| Low | 30 | $22 |
| Quality | 25 | $100 |
| **Total** | **55** | **$122** |

| Metric | Value |
|---|---|
| **Adjusted net/month** | **$3,660** |
| Capital needed | $4,000 |
| Break-even | ~33 days |

### Feasibility Rating: 2/5 -- OVERCOMPLICATED

**Why the mixed model is problematic:**
- Managing 3 tiers of inventory = 3x the sourcing work, storage complexity, and listing effort.
- The micro-margin tier ($0.25/unit) is never worth a solo operator's time.
- Time spent on 30 micro-margin items could be spent sourcing 5 more quality-margin items at $5 profit each.
- Focus beats diversification at solo scale.

---

## FINAL RECOMMENDATION

### The Only Scenario That Makes Sense for a Solo Operator

**Scenario C (Moderate Margin) is the clear winner.** Here's the optimized version:

| Parameter | Value |
|---|---|
| Daily volume | 40-60 units |
| Average buy price | $7-10 |
| Average sell price | $22-30 |
| Gross margin per unit | $6-9 |
| Net after returns | $5.50-8.00 |
| Monthly net profit | **$6,600-$14,400** |
| Starting capital | **$3,000-$5,000** |
| Break-even | **10-15 days** |
| Daily time commitment | **3-4 hours** |

### RelistApp Automation Opportunities

Where RelistApp adds the most value in Scenario C:

1. **Source scanning**: Auto-monitor Amazon Warehouse, Walmart clearance for items matching profit threshold ($6+ margin)
2. **Cross-listing**: One listing creation pushes to eBay + Mercari + FB + TikTok simultaneously
3. **Price optimization**: Auto-adjust sell price based on platform fee differences (price lower on TikTok, higher on eBay)
4. **Inventory sync**: Prevent overselling when listed on 4 platforms
5. **Profit tracking**: Real-time dashboard showing true margin after all fees per platform
6. **Shipping label generation**: Auto-select cheapest carrier (USPS vs Pirate Ship vs platform label)

### What NOT to Build

- Do not optimize for Scenario A (micro-margin). The math never works for a solo operator.
- Do not build complex multi-tier portfolio management (Scenario D). Focus beats complexity.
- Do not prioritize Poshmark integration unless specifically targeting fashion. The 20% fee is brutal.
- Do not build FBA integration initially. FBA fees ($3-6/unit) destroy margins on items under $30.

### Platform Priority for RelistApp Integration

1. **eBay** -- largest resale audience, most arbitrage volume
2. **Mercari** -- 10% fee, simple API, growing user base
3. **Facebook Marketplace** -- 10% shipped / 0% local, huge audience
4. **TikTok Shop** -- 7% fee, fastest growing, best for new sellers
5. **Walmart Marketplace** -- 8-15%, no monthly fee, worth testing
6. **Etsy** -- only if niche categories (vintage, craft supplies)
7. **Amazon** -- as SOURCE only, not as selling destination at this scale
8. **Poshmark** -- fashion-only, last priority

---

## Sources

All fee data sourced from platform_fee_analysis.md. Additional references:

- [Dropshipping Profit Margins 2026 - SparkShipping](https://www.sparkshipping.com/blog/dropshipping-margins-complete-guide)
- [Is Dropshipping Profitable 2026 - eCommerce Today](https://ecommerce-today.com/is-dropshipping-still-profitable-in-2026-the-senior-operators-guide-to-roi/)
- [Make Money Dropshipping 2026 - USAdrop](https://usadrop.com/make-money-dropshipping-real-earnings-margins/)
- [Average Dropshipping Income 2026 - TrueProfit](https://trueprofit.io/blog/average-dropshipping-income)
- [Amazon Warehouse Deals Guide](https://amzprep.com/amazon-warehouse-deals/)
- [USPS Ground Advantage Rates - Pirate Ship](https://www.pirateship.com/usps/ground-advantage)
