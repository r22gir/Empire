# RelistApp Daily Operations Playbook

## Drop-Ship Arbitrage: Hour-by-Hour Operator Guide

> Last updated: April 2026 | RelistApp v1.0
> Target: solo operator running 200-500 active listings across eBay, Mercari, and Poshmark

---

## Philosophy

The daily routine exists to protect two things: **cash flow** and **account health**. Every task below maps to one of those. If you skip order processing, you get late shipment defects. If you skip repricing, your margins erode overnight. The playbook is designed so the highest-risk tasks happen first, and creative/growth tasks happen after the fire is out.

---

## Morning Block: 7:00 AM - 10:30 AM (Core Operations)

### 7:00 AM - Check Overnight Sales (15 min)

**What you do:**
- Open RelistApp Dashboard > Sales Feed
- Review all orders that came in between your last session and now
- Flag any orders with notes, special requests, or bundled items
- Check for any out-of-stock alerts from source tracking

**What RelistApp automates:**
- Pulls all new orders from eBay, Mercari, Poshmark APIs into a single feed
- Cross-references each sold SKU against the source product's current price and availability
- Flags orders where the source price has increased above your minimum margin threshold
- Color-codes: green (clear to process), yellow (margin squeezed), red (source unavailable or price spike)

**Priority triage:**
| Priority | Condition | Action |
|----------|-----------|--------|
| P0 - Critical | Source item out of stock | Cancel within 1 hour, message buyer, offer alternative |
| P1 - Urgent | Source price increased, margin < $0.15 | Decide: eat the loss or cancel. Under $3 loss, eat it for account health |
| P2 - Normal | Green status, margins healthy | Queue for processing in next block |

**Human touch required:** Decision-making on P0/P1 items. RelistApp flags them but you decide whether to cancel or absorb the hit.

---

### 7:15 AM - Process Orders (30 min)

**What you do:**
- For each green-status order, click "Process" in RelistApp
- Confirm the source purchase (Amazon/Walmart) using the buyer's shipping address
- Enter the order confirmation number back into RelistApp
- For gift-wrap: always select NO gift receipt, NO gift wrap, NO packing slip with price

**What RelistApp automates:**
- Pre-fills the source platform's checkout with the buyer's shipping address (via browser extension)
- Calculates exact cost breakdown: source price + tax + shipping - cashback = true cost
- Logs the source order ID and links it to the marketplace sale
- Sets a tracking number watch — polls the source platform every 2 hours for tracking updates
- Auto-uploads tracking to the selling platform once detected

**Step-by-step for each order:**
1. Open source product link (stored in RelistApp listing record)
2. Verify item is still available at expected price
3. Add to cart, proceed to checkout
4. Enter buyer's shipping address (RelistApp copies it to clipboard)
5. Select standard shipping (unless expedited margin allows upgrade)
6. Pay with your dedicated arbitrage credit card (cashback card preferred — 2-5% back)
7. Copy order confirmation number into RelistApp
8. Mark order as "Sourced"

**Time estimate:** ~3 minutes per order. At 10 overnight sales = 30 minutes.

**Critical rules:**
- NEVER ship to yourself and re-ship. That kills your margins and adds 3-5 days.
- ALWAYS use a payment method that earns cashback. At volume, 2% cashback on $500/day source purchases = $300/month found money.
- NEVER include a packing slip from the source. If the platform allows invoice-free shipping, enable it.

---

### 7:45 AM - Check Price Alerts (15 min)

**What you do:**
- Open RelistApp > Price Monitor
- Review items where source price changed overnight
- Adjust your listing price up or down to maintain target margin
- Kill listings where the source price rose above your sell price

**What RelistApp automates:**
- Runs price checks on all active source products every 6 hours
- Calculates new margin based on current source price + platform fees + estimated tax
- Auto-adjusts listing price if within your configured "auto-reprice" band (e.g., +/- 10%)
- Flags items outside the auto-reprice band for manual review
- Tracks price history so you can see trends (is this item trending up or was it a spike?)

**Priority triage:**
| Condition | Action |
|-----------|--------|
| Source price dropped | Lower your listing price to stay competitive, or keep price and enjoy wider margin |
| Source price rose 5-15% | Raise listing price if market supports it |
| Source price rose >15% | Pause or kill the listing — margin likely gone |
| Source went out of stock | End listing immediately, note in inventory |

**Human touch required:** Deciding whether to raise prices (market sensitivity) or kill a listing vs. waiting for the source price to drop back.

---

### 8:00 AM - Review Product Scout Feed (30 min)

**What you do:**
- Open RelistApp > Product Scout
- Review the top 20 product opportunities ranked by estimated margin and sell-through rate
- Evaluate each: Does this product have legs? Is the margin real after all fees? Is the category risky for returns?
- Star the top 10 for listing

**What RelistApp automates:**
- Scans Amazon Movers & Shakers, Walmart Clearance, and trending searches on eBay
- Cross-references against eBay completed listings to estimate actual sell price
- Calculates projected margin after all fees (platform fee, payment processing, estimated tax, shipping if applicable)
- Filters out restricted categories, known IP-complaint brands, and hazmat items
- Ranks by a composite score: margin x sell-through-rate x return-risk-inverse

**Evaluation criteria for each product:**
| Factor | Green Light | Red Flag |
|--------|-------------|----------|
| Margin after fees | > $1.50 | < $0.50 |
| Sell-through rate | > 60% in 30 days | < 30% |
| Return rate (category avg) | < 8% | > 15% |
| Competition (same item on eBay) | < 10 sellers | > 50 sellers |
| Brand risk | Generic/no-name | Nike, Disney, luxury (IP complaints) |
| Weight | < 2 lbs | > 5 lbs (shipping cost risk) |

**Human touch required:** Final judgment on product selection. RelistApp provides data but you know your niche, your buyer base, and what sells on your specific stores.

---

### 8:30 AM - List Top 10 New Products (60 min)

**What you do:**
- For each starred product from the Scout feed, create listings on your target platforms
- Write or review the title, description, and select photos
- Set pricing based on RelistApp's margin calculator
- Cross-list to 2-3 platforms per product

**What RelistApp automates:**
- Pulls product images from the source listing (Amazon/Walmart)
- Generates SEO-optimized title suggestions based on eBay search trends
- Pre-fills item specifics (brand, size, color, UPC) from source product data
- Calculates optimal price per platform (accounting for different fee structures)
- Cross-lists to multiple platforms with one click (adapts formatting per platform)
- Schedules listings to go live at peak traffic times (Sunday 6-9 PM for eBay, evenings for Mercari)

**Listing quality checklist:**
- [ ] Title uses all 80 characters (eBay) with top search keywords
- [ ] At least 5 photos, first photo is clean product-on-white
- [ ] Item specifics fully filled in (eBay search ranking factor)
- [ ] Description includes dimensions, materials, use case — NOT copy-pasted from Amazon
- [ ] Price set at target margin with room for offers (list 10-15% above target to allow Best Offer)
- [ ] Shipping set to free (baked into price) on eBay; buyer-pays on Mercari if under $3
- [ ] Returns policy: 30-day returns on eBay (required for Top Rated Seller), case-by-case on Mercari

**Time estimate:** ~6 minutes per listing across 2 platforms = 60 minutes for 10 products.

**Human touch required:** Writing compelling descriptions, choosing the best photos, adjusting titles for your store's voice.

---

### 9:00 AM - Check Messages (15 min)

**What you do:**
- Open RelistApp > Inbox (unified messages from all platforms)
- Respond to buyer questions, offer requests, and return inquiries
- Flag any messages that indicate a problem (wrong item, not received, complaint)

**What RelistApp automates:**
- Aggregates messages from eBay, Mercari, Poshmark into one inbox
- Auto-responds to common questions with templates (shipping time, item condition, bundle offers)
- Flags messages with negative sentiment for priority response
- Tracks response time per platform (eBay requires < 24 hour response for Top Rated)

**Response time targets:**
| Platform | Target | Why |
|----------|--------|-----|
| eBay | < 12 hours | Affects seller performance metrics |
| Mercari | < 4 hours | Buyers move fast, they'll buy elsewhere |
| Poshmark | < 2 hours | Community-driven, fast response = more sales |

**Message templates (customize to your voice):**
- Shipping inquiry: "Thanks for your interest! This item ships within 1-2 business days. You'll receive tracking as soon as it ships."
- Offer response: "Thanks for the offer! I can do $X — would that work for you?"
- Return request: "I'm sorry this didn't work out. I'll send you a return label right away."

**Human touch required:** Personalized responses to complex questions. Templates handle the 80% — you handle the 20% that need a real human.

---

### 9:30 AM - Content Creation (30 min)

**What you do:**
- Record 1-2 TikTok/Instagram Reels showing product finds, unboxings, or day-in-the-life
- Post to your reseller social accounts
- Engage with reseller community (comment on others' posts, join lives)

**What RelistApp automates:**
- Suggests trending audio and hashtags for reseller content
- Tracks engagement metrics across platforms
- Schedules posts for optimal times

**Content ideas that work:**
| Format | Example | Why It Works |
|--------|---------|--------------|
| "I found this for $X, selling for $Y" | Show the Amazon price vs. your eBay listing | People love seeing the margin |
| Packing orders | ASMR-style order fulfillment | Satisfying, builds trust |
| Monthly income report | "I made $X in March 2026" | Aspirational, drives followers |
| Product fail | "This item had a 20% return rate" | Honest content builds credibility |
| Tool demo | Show RelistApp in action | Positions you as sophisticated |

**Human touch required:** All of it. This is pure human creativity and personality. RelistApp provides data points you can feature in content but the creation is yours.

**Why bother:** Social media drives 10-20% of serious resellers' traffic. A TikTok showing a $3 Amazon find selling for $15 on eBay can go viral and drive hundreds of watchers to your store.

---

### 10:00 AM - Review Analytics (30 min)

**What you do:**
- Open RelistApp > Analytics Dashboard
- Review key metrics from the past 7 days
- Identify trends: which categories are hot, which platforms are performing, where margins are tightest
- Make strategic decisions based on data

**What RelistApp automates:**
- Calculates and displays all metrics in real-time
- Generates trend graphs (sales velocity, margin trends, inventory aging)
- Compares current week vs. previous week performance
- Produces automated weekly summary report

**Key metrics to review:**

| Metric | Healthy Range | Action If Outside |
|--------|---------------|-------------------|
| Gross margin % | 25-40% | Below 25%: reprice or cut low-margin items |
| Sell-through rate | 50-70% in 30 days | Below 50%: titles need SEO work or prices too high |
| Average days to sell | 7-21 days | Above 30 days: stale inventory, reprice or remove |
| Return rate | < 8% overall | Above 8%: investigate categories, check descriptions |
| Messages response time | < 12 hours avg | Above 12h: set up more auto-responses |
| Active listing count | 200-500 | Below 200: list more. Above 500: quality may suffer |
| Daily revenue | Per your goals | Track trend, not single days |
| Cost of goods as % of revenue | 55-70% | Above 75%: margins too thin |

**Human touch required:** Interpreting the data and making strategic pivots. The numbers tell you what; you decide what to do about it.

---

### 10:30 AM - Kill Underperformers (15 min)

**What you do:**
- Open RelistApp > Inventory > Sort by "Days Listed" descending
- Review all items listed more than 30 days without a sale
- Decision for each: reprice, relist (refresh the listing), or remove

**What RelistApp automates:**
- Flags listings older than 30 days with zero sales
- Shows each item's view count, watcher count, and offer history
- Suggests action based on engagement data:
  - High views + no sales = price too high, suggest reduction
  - Low views + no sales = bad title/photos, suggest relist with new keywords
  - Zero views = dead listing, suggest removal
- Batch-removes dead listings and logs them to the "Graveyard" for learning

**Decision framework:**

| Views (30 days) | Watchers | Offers | Action |
|-----------------|----------|--------|--------|
| > 50 | > 3 | Yes | Reduce price 10-15% |
| > 50 | > 3 | No | Reduce price 20% or add Best Offer |
| 20-50 | 1-2 | No | Relist with new title and photos |
| < 20 | 0 | No | Remove — product or listing is dead |

**Human touch required:** Final call on each item. Sometimes a seasonal product is worth keeping through a slow period. RelistApp doesn't know it's about to be summer and pool accessories will spike.

---

## Evening Block: 6:00 PM - 8:00 PM (Catch-Up & Growth)

### 6:00 PM - Process Afternoon Sales (30 min)

Same as 7:15 AM block. Process any orders that came in during the day.

**What RelistApp automates:**
- Same as morning: flags, color-codes, pre-fills checkout
- Additionally, by evening, some morning orders may have tracking — auto-uploads them

---

### 6:30 PM - Reprice Active Inventory (30 min)

**What you do:**
- Open RelistApp > Repricer
- Review suggested price changes based on competition monitoring
- Approve batch reprices or adjust individually
- Focus on items with upcoming eBay "promote" opportunities

**What RelistApp automates:**
- Monitors competitor pricing on eBay for your exact items (same UPC/title match)
- Suggests price adjustments to stay in the buy-box competitive range
- Applies approved reprices in batch across all platforms
- Adjusts promoted listing ad rate based on competition density

**Repricing rules:**
- Never go below your minimum margin ($0.15/unit absolute floor)
- Match lowest competitor only if they have >90% feedback score
- If you're the only seller, hold your price — no reason to cut
- Weekend repricing: slightly higher prices (impulse buying increases)

---

### 7:00 PM - Scout Trending Products (45 min)

**What you do:**
- Browse Amazon Movers & Shakers, Walmart rollbacks, trending TikTok products
- Check Google Trends for seasonal spikes
- Review RelistApp's automated scout results from the day
- Build tomorrow's listing queue

**What RelistApp automates:**
- Continuous scanning of deal feeds throughout the day
- Cross-referencing with eBay demand data
- Filtering out products you've already listed or previously rejected
- Building a ranked queue of opportunities for the next morning

**Seasonal awareness calendar:**

| Month | Trending Categories |
|-------|-------------------|
| Jan-Feb | Fitness equipment, organization, Valentine's gifts |
| Mar-Apr | Garden supplies, outdoor gear, spring cleaning |
| May-Jun | Pool/beach, camping, graduation gifts |
| Jul-Aug | Back to school, dorm essentials, cooling products |
| Sep-Oct | Halloween costumes/decor, fall fashion, early holiday |
| Nov-Dec | Holiday gifts, stocking stuffers, winter gear |

---

### 7:45 PM - End-of-Day Review (15 min)

**What you do:**
- Check all platforms for any unresolved issues
- Review the day's P&L in RelistApp
- Note tomorrow's priorities

**What RelistApp automates:**
- Daily P&L summary: revenue, COGS, fees, net profit
- Unresolved issues list (open returns, unanswered messages, pending tracking)
- Tomorrow's auto-generated task list based on inventory age, pending orders, and scheduled promotions

---

## Weekly Tasks

| Day | Task | Time | RelistApp Support |
|-----|------|------|-------------------|
| Monday | Deep analytics review, set weekly goals | 30 min | Weekly report auto-generated |
| Wednesday | Inventory health audit, kill 30+ day items | 30 min | Aging report with recommendations |
| Friday | Test 5 new product categories | 45 min | Category margin analysis |
| Saturday | Content batch creation (3-5 videos) | 60 min | Performance data for content topics |
| Sunday | Competitor analysis, strategy adjustment | 30 min | Competitor tracking dashboard |

---

## Time Budget Summary

| Block | Daily Time | Automatable | Human Required |
|-------|-----------|-------------|----------------|
| Morning operations | 3.5 hours | ~40% (alerts, cross-referencing, listing pre-fill) | 60% (decisions, purchasing, content) |
| Evening operations | 2 hours | ~50% (repricing, scouting, reporting) | 50% (strategy, product selection) |
| **Total** | **5.5 hours** | **~45%** | **~55%** |

Without RelistApp, the same workload takes approximately 9-10 hours. The automation saves 3.5-4.5 hours daily by eliminating manual price checking, cross-platform listing, tracking uploads, and report generation.

---

## Emergency Protocols

| Emergency | Action | Time Limit |
|-----------|--------|------------|
| Item Not Received claim | Check source tracking, provide to buyer, escalate if lost | 24 hours |
| Negative feedback | Contact buyer, resolve issue, request revision | 48 hours |
| Account suspension notice | Stop all activity, read notice carefully, file appeal | Immediate |
| Source platform account flagged | Switch to backup account, diversify sources | Immediate |
| Payment hold extended | Do not over-invest, reduce daily sourcing budget by 50% | Same day |

---

*This playbook is a living document. Adjust times and priorities based on your sales volume, platform mix, and personal schedule. The key principle: protect account health first, then optimize for profit.*
