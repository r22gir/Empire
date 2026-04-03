# RelistApp Financial Controls

## Cash Flow Management for Drop-Ship Arbitrage

> Last updated: April 2026 | RelistApp v1.0
> For operators running sub-$1 to mid-margin arbitrage at scale

---

## The Core Problem

Drop-ship arbitrage has a brutal cash flow dynamic: **you pay the source immediately, but the selling platform holds your money for days to weeks.** If you don't manage this carefully, you can be profitable on paper and broke in reality.

This document provides the financial framework to prevent that.

---

## 1. Payment Hold Timelines by Platform

Understanding when you actually receive money is the single most important financial concept in this business.

### eBay (2026 Rules)

| Seller Status | Payment Timeline | Conditions |
|---------------|-----------------|------------|
| New seller (0-90 days) | 21 days after delivery OR buyer feedback | Whichever comes first |
| Below Standard | 21 days hold | Plus additional manual review possible |
| Established (90+ days, 25+ sales) | 1-3 business days after delivery confirmed | Must maintain Above Standard metrics |
| Top Rated Seller | 1 business day after delivery confirmed | Requires: 100+ items/year, $1000+ sales, <0.5% defect rate |
| Managed Payments reserve | 5-10% of rolling revenue held in reserve | Applied to some accounts based on risk assessment |

**Key eBay financial notes:**
- eBay charges final value fee (13.25% for most categories) + $0.30 per order
- Promoted listings cost an additional 2-15% of sale price (ad rate varies)
- International sales: additional 1.65% international fee
- eBay may extend holds if buyer opens a case during hold period

### Mercari (2026 Rules)

| Condition | Payment Timeline |
|-----------|-----------------|
| Standard | 3 business days after buyer rates OR 3 days after auto-rate (day 4 after delivery) |
| Direct deposit | Instant transfer available for $2 fee, or free standard transfer (3-5 business days) |
| New account | First 2 weeks: additional review may add 1-2 days |

**Key Mercari financial notes:**
- Selling fee: 10% of sale price
- Payment processing: 2.9% + $0.50 per transaction
- Effective total fee: ~13.4% on a $20 item
- No promoted listings fee (organic only)
- Mercari credits from returns are locked to the platform

### Poshmark (2026 Rules)

| Sale Amount | Fee | Payment Timeline |
|-------------|-----|-----------------|
| Under $15 | Flat $2.95 | 3 days after delivery confirmed |
| $15 and over | 20% of sale price | 3 days after delivery confirmed |
| Posh Remit (new 2026) | Variable | Same as above |

**Key Poshmark financial notes:**
- Poshmark controls the shipping label ($7.67 priority mail, buyer pays)
- No additional payment processing fees
- But 20% is the highest marketplace fee — factor this into pricing
- Cash out: minimum $15, no fee for direct deposit

### Facebook Marketplace (2026 Rules)

| Seller Status | Payment Timeline |
|---------------|-----------------|
| New seller | 15-20 business days after delivery confirmed |
| Established | 5 business days after delivery confirmed |
| Verified business | 1-3 business days |

**Key Facebook financial notes:**
- Selling fee: 5% per shipment (or $0.40 minimum for items under $8)
- Among the lowest fees of any platform
- But the long payment holds for new sellers make it a cash flow trap
- Recommendation: use Facebook once established elsewhere, not as a starting platform

### Amazon Seller (for reference — source platform awareness)

| Factor | Detail |
|--------|--------|
| Disbursement cycle | Every 14 days |
| Reserve | Amazon holds a rolling reserve based on return rate and account age |
| Typical reserve | 7-14 days of sales revenue |
| New seller reserve | Up to 50% of revenue held for 90 days |

**Why this matters for sourcing:** If you're buying on Amazon with a credit card, you typically have 25-30 days before the bill is due. If you're selling on eBay as an established seller, you get paid in 1-3 days after delivery. This creates a positive float — you get paid before your credit card bill is due.

---

## 2. Working Capital Model

### Day 1-30 Cash Flow Projection (New Operator)

Starting capital: **$500**

| Day | Action | Cash Out | Cash In | Balance | Notes |
|-----|--------|----------|---------|---------|-------|
| 1 | Source 10 items @ $8 avg | -$80 | $0 | $420 | Using 16% of capital |
| 2 | Source 10 items | -$80 | $0 | $340 | |
| 3 | Source 10 items | -$80 | $0 | $260 | |
| 4 | First 2 sales ship | $0 | $0 | $260 | Items in transit |
| 5 | Source 5 items | -$40 | $0 | $220 | Slowing down, conserving cash |
| 7 | First deliveries confirmed | $0 | $0 | $220 | eBay hold starts |
| 8-14 | Source 3-5 items/day | -$200 | $0 | $20 | Cash getting tight |
| 14 | **DANGER ZONE** | $0 | $0 | $20 | Minimum cash, maximum exposure |
| 15-21 | NO new sourcing | $0 | $0 | $20 | Wait for payments to clear |
| 21 | Mercari payments start | $0 | +$60 | $80 | First real cash inflow |
| 22-25 | Trickle of payments | $0 | +$120 | $200 | eBay holds releasing |
| 28 | First eBay holds release | $0 | +$180 | $380 | Big release day |
| 30 | End of month | $0 | +$100 | $480 | Almost back to starting capital |

**Key insight:** You will feel broke around day 14. This is normal. Do not panic-source or over-invest. The cash is coming — it's just locked in payment holds.

### Mature Operator Cash Flow (Month 3+, Established Accounts)

At 10 sales/day, $15 average sale price, 30% gross margin:

| Metric | Daily | Weekly | Monthly |
|--------|-------|--------|---------|
| Revenue | $150 | $1,050 | $4,500 |
| COGS (source cost) | -$95 | -$665 | -$2,850 |
| Platform fees (~13%) | -$19.50 | -$136.50 | -$585 |
| Gross profit | $35.50 | $248.50 | $1,065 |
| Cash received (1-3 day delay) | $130 | $910 | $3,900 |
| Net cash position | Positive | Positive | Positive |

Once established on eBay, cash flow becomes positive because your payment cycle (1-3 days) is faster than your credit card cycle (25-30 days).

---

## 3. Break-Even Analysis at Different Daily Volumes

### Assumptions
- Average source cost: $8.00
- Average sell price: $15.00
- eBay fees: 13.25% + $0.30 = $2.29
- Estimated sales tax on source: 7% = $0.56
- Cashback on source purchase: 2% = -$0.16
- Shipping: free (baked into price) for most items

### Per-Unit Economics

| Component | Amount |
|-----------|--------|
| Sell price | $15.00 |
| - Source cost | -$8.00 |
| - Source sales tax (7%) | -$0.56 |
| - eBay final value fee (13.25%) | -$1.99 |
| - eBay per-order fee | -$0.30 |
| - Promoted listing (avg 5%) | -$0.75 |
| + Cashback (2%) | +$0.16 |
| **Net profit per unit** | **$3.56** |
| **Net margin** | **23.7%** |

### Volume-Based Break-Even

Monthly fixed costs for a serious operator:

| Expense | Monthly Cost |
|---------|-------------|
| eBay Store subscription (Basic) | $21.95 |
| Listing software/tools | $30.00 |
| Dedicated phone line | $15.00 |
| Shipping supplies (labels, tape) | $20.00 |
| RelistApp subscription | $29.00 |
| Accounting software | $15.00 |
| **Total fixed costs** | **$130.95** |

| Daily Volume | Monthly Sales | Monthly Revenue | Monthly COGS | Monthly Fees | Monthly Profit | After Fixed Costs |
|-------------|---------------|-----------------|-------------|-------------|----------------|-------------------|
| 2 sales/day | 60 | $900 | -$514 | -$183 | $203 | $72 |
| 5 sales/day | 150 | $2,250 | -$1,284 | -$456 | $510 | $379 |
| 10 sales/day | 300 | $4,500 | -$2,568 | -$912 | $1,020 | $889 |
| 20 sales/day | 600 | $9,000 | -$5,136 | -$1,824 | $2,040 | $1,909 |
| 50 sales/day | 1,500 | $22,500 | -$12,840 | -$4,560 | $5,100 | $4,969 |

**Break-even point: approximately 2 sales per day** covers fixed costs. Everything above that is profit.

---

## 4. Financial Rules (Non-Negotiable)

These rules prevent the two ways arbitrage operators go broke: over-investing and under-reserving.

### Rule 1: 30% Maximum Daily Investment

**Never invest more than 30% of your available cash in a single day.**

| Available Cash | Max Daily Investment | Why |
|---------------|---------------------|-----|
| $500 | $150 | Leaves $350 for emergencies and holds |
| $1,000 | $300 | |
| $2,000 | $600 | |
| $5,000 | $1,500 | At this level, you're doing 150+ items/day |

**RelistApp enforcement:** Set your daily budget cap in Settings > Financial Controls. RelistApp will warn you when you approach 30% and block sourcing suggestions past the limit.

### Rule 2: 20% Return Reserve

**Hold 20% of every payment received as a return/refund reserve.**

When a $15 sale pays out $12.71 after fees:
- $10.17 goes to available cash (80%)
- $2.54 goes to return reserve (20%)

The reserve covers:
- Refunds to buyers when source return window has closed
- Partial refunds for item-not-as-described claims
- eBay defect-related costs
- Unexpected fee increases or tax adjustments

**Release schedule:** Review the reserve monthly. If actual return costs were less than the reserve, release the excess back to working capital. Never let the reserve drop below one week's average refund costs.

### Rule 3: $0.15 Minimum Margin Per Unit

**Never list an item with less than $0.15 projected profit after ALL costs.**

This seems absurdly low, but it exists as a floor, not a target. Items with $0.15 margins should be high-volume, zero-touch items where the automation does everything.

**Why $0.15 and not $0.00:** Even "break-even" items have hidden costs — your time reviewing them, the risk of a return, the opportunity cost of a listing slot. The $0.15 floor ensures you're never truly losing money.

**RelistApp enforcement:** The listing tool will not allow you to publish a listing with projected margin below $0.15. It will show a red warning and block the "Publish" button.

### Rule 4: Separate Bank Account

**Open a dedicated checking account for your arbitrage business. Do not mix personal and business finances.**

Recommended setup:

| Account | Purpose |
|---------|---------|
| Business checking | All platform payouts deposit here, all source purchases come from here |
| Business savings | Return reserve fund (20% auto-transfer) |
| Business credit card | All source purchases (2%+ cashback), paid from business checking |
| Personal account | Pay yourself a fixed amount monthly |

**Benefits:**
- Clean tax records (every transaction is business-related)
- Easy to calculate true profit (ending balance - starting balance + owner draws)
- Required if you form an LLC (commingling funds pierces the corporate veil)
- Makes bookkeeping and tax prep 10x faster

**Recommended banks (2026):**
- Mercury (free business checking, integrates with accounting software)
- Relay (multiple checking accounts for budgeting, free)
- Chase Business Complete (if you want a physical branch)

---

## 5. Credit Card Strategy

Your source purchasing credit card is a profit center, not just a payment method.

### Recommended Cards for Arbitrage (2026)

| Card | Cashback Rate | Annual Fee | Best For |
|------|-------------|------------|----------|
| Chase Ink Business Unlimited | 1.5% flat | $0 | Starting out, all purchases |
| Capital One Spark Cash Plus | 2% flat | $150 | Volume sourcing ($7,500+/mo pays for the fee) |
| Amazon Prime Rewards Visa | 5% on Amazon | $139 (Prime) | If Amazon is your primary source |
| Citi Double Cash | 2% flat | $0 | Personal card if no business entity yet |
| Walmart Rewards Card | 5% on Walmart.com | $0 | If Walmart is primary source |

### Credit Card Cash Flow Hack

The statement cycle creates free float:

1. Purchase on Day 1 of billing cycle
2. Statement closes Day 30
3. Payment due Day 55 (25-day grace period)
4. You've already been paid by the selling platform on Day 4-25

**Result:** You're using the bank's money for 25-55 days, getting 2-5% cashback, and collecting your sales revenue before the bill is due. At $5,000/month source purchases, 2% cashback = $100/month in found money.

### Credit Utilization Warning

Keep your utilization below 30% of your credit limit. If you have a $5,000 limit, don't carry more than $1,500 in charges at any time. High utilization hurts your credit score, which limits your ability to get higher limits and better cards.

**Solution:** Make mid-cycle payments. Pay off part of the balance every week rather than waiting for the due date.

---

## 6. Fee Quick-Reference by Platform

### eBay Fee Structure (2026)

| Fee Type | Rate | Notes |
|----------|------|-------|
| Final value fee (most categories) | 13.25% | On total sale amount including shipping |
| Per-order fee | $0.30 | Per transaction |
| Promoted listings (standard) | 2-15% | Only charged on sales from promoted exposure |
| Promoted listings (advanced/PPC) | Per click, $0.01-$2.00 | Bid-based, charged per click |
| International fee | 1.65% | On international sales |
| Store subscription (Basic) | $21.95/mo | Includes 250 free listings/month |
| Store subscription (Premium) | $59.95/mo | 1,000 free listings, lower FVF in some categories |
| Insertion fee (over free allotment) | $0.35/listing | Per listing per category |

### Mercari Fee Structure (2026)

| Fee Type | Rate |
|----------|------|
| Selling fee | 10% |
| Payment processing | 2.9% + $0.50 |
| Instant pay (optional) | $2.00 per transfer |
| Shipping label (prepaid, optional) | Varies by weight ($4.99-$18.00) |

### Poshmark Fee Structure (2026)

| Fee Type | Rate |
|----------|------|
| Commission (sales under $15) | Flat $2.95 |
| Commission (sales $15+) | 20% |
| Shipping label | $7.67 (buyer pays, included in listing) |
| No listing fees | $0 |

---

## 7. Monthly P&L Template

RelistApp auto-generates this report, but here's the structure for manual tracking:

```
MONTHLY P&L - [MONTH] 2026
================================

REVENUE
  eBay sales                    $________
  Mercari sales                 $________
  Poshmark sales                $________
  Facebook Marketplace sales    $________
  TOTAL REVENUE                 $________

COST OF GOODS SOLD
  Source purchases (Amazon)     $________
  Source purchases (Walmart)    $________
  Source purchases (other)      $________
  Source shipping costs          $________
  Source sales tax paid          $________
  TOTAL COGS                    $________

GROSS PROFIT                    $________
GROSS MARGIN %                  ________%

PLATFORM FEES
  eBay fees                     $________
  Mercari fees                  $________
  Poshmark fees                 $________
  Facebook fees                 $________
  TOTAL PLATFORM FEES           $________

OPERATING EXPENSES
  Store subscriptions           $________
  Software/tools                $________
  Shipping supplies             $________
  Phone/internet (business %)   $________
  RelistApp subscription        $________
  Accounting/bookkeeping        $________
  TOTAL OPERATING EXPENSES      $________

RETURNS & ADJUSTMENTS
  Refunds issued                $________
  Return shipping costs         $________
  Unsellable returns (write-off)$________
  TOTAL RETURNS COST            $________

NET PROFIT BEFORE TAX           $________
NET MARGIN %                    ________%

CASH FLOW
  Starting cash balance         $________
  Cash received from platforms  $________
  Cash spent on sourcing        $________
  Cash spent on expenses        $________
  Ending cash balance           $________

RESERVES
  Return reserve balance        $________
  Tax reserve (25% of net)      $________
```

---

## 8. RelistApp Financial Dashboard

RelistApp tracks all of the above automatically when you process orders through the system:

| Feature | What It Does |
|---------|-------------|
| Real-time P&L | Updates with every sale and source purchase |
| Cash flow forecast | Projects next 30 days based on pending holds and scheduled payments |
| Margin alerts | Notifies when any SKU drops below minimum margin |
| Daily budget tracker | Shows how much of your 30% daily budget remains |
| Return reserve calculator | Tracks reserve vs. actual return costs |
| Tax estimate | Running quarterly tax estimate based on net profit |
| Platform fee breakdown | Shows effective fee rate per platform per month |
| Cashback tracker | Logs credit card rewards earned from source purchases |

---

## 9. Financial Red Flags

Stop sourcing immediately if any of these are true:

| Red Flag | Threshold | Action |
|----------|-----------|--------|
| Available cash below 2x daily sourcing budget | < 2x | Pause sourcing until payments clear |
| Return rate exceeding reserve | Reserve < actual returns | Increase reserve %, investigate categories |
| Average margin trending below 15% | < 15% for 2 weeks | Reprice inventory, cut low-margin items |
| Credit card utilization above 50% | > 50% | Make immediate payment, reduce sourcing |
| Platform account at risk of suspension | Any warning | Stop all activity, address the issue |
| More than 20% of inventory aged 30+ days | > 20% | Aggressive repricing, remove dead stock |

---

## 10. Scaling Financial Controls

As you grow, your financial controls tighten, not loosen.

| Revenue Tier | Additional Controls |
|-------------|-------------------|
| $0-$1,000/mo | Basic spreadsheet tracking is fine. Build habits. |
| $1,000-$5,000/mo | Dedicated bank account required. Monthly P&L required. |
| $5,000-$10,000/mo | Accounting software (Wave, QuickBooks). Quarterly tax payments. |
| $10,000-$30,000/mo | LLC formation. Bookkeeper or accountant. Weekly cash flow review. |
| $30,000+/mo | CPA required. Payroll if hiring. Insurance. Annual audit of procedures. |

---

*Cash flow kills more arbitrage businesses than bad products. Respect the holds, maintain the reserves, and never invest more than 30% of available cash in a single day. RelistApp's financial controls are guardrails, not suggestions.*
