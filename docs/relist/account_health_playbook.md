# RelistApp Account Health Playbook

> Last updated: April 2026
> Purpose: Keep seller accounts alive and scaling across Amazon, eBay, and other platforms.

---

## 1. Platform Policies on Drop-Shipping (2026)

### Amazon

- **Retail arbitrage is technically allowed** but Amazon rejects retail receipts as proof of authenticity. They require invoices or authorization letters from brand-authorized suppliers.
- **Drop-shipping is allowed** only if: you are the seller of record, you identify yourself on all packaging/invoices, you handle returns directly, and you remove all third-party branding.
- **Strictly prohibited**: purchasing from AliExpress, Walmart, or other retailers and shipping directly to customers. This is classified as retail arbitrage drop-shipping and violates Amazon's ToS.
- **Brand gating**: Restricted brands (LEGO, Nike, Apple, etc.) will trigger immediate suspension even with legitimate retail receipts. You must be an authorized reseller.
- **2026 enforcement**: Amazon is using AI to detect patterns of abuse and acting faster on violations. The gap between stated policy ("arbitrage is a valid sourcing method") and enforcement ("we reject retail receipts") continues to widen.

### eBay

- **Drop-shipping is allowed** only if products come directly from wholesale or manufacturer suppliers.
- **Retail arbitrage drop-shipping is explicitly banned**: buying from Amazon, Walmart, or any other retailer and shipping to eBay buyers is a policy violation.
- **Packaging rules**: Shipments must appear to come from you. Packages containing branded material, invoices, or packing slips from Amazon/Walmart/etc. will count as a policy breach.
- **Documentation**: You must produce fulfillment agreements, invoices, and product sourcing documents on request during performance reviews or buyer disputes.
- **2026 enforcement**: eBay has deployed new automated systems to detect retail arbitrage drop-shipping patterns. Enforcement has doubled down compared to prior years.
- **VeRO program**: Verified Rights Owner Program allows brand owners to report listings. Selling branded items without authorization risks VeRO takedowns and account strikes.

### Key Takeaway for RelistApp

The compliant path is **wholesale sourcing with legitimate invoices** or **retail arbitrage where you hold inventory yourself** (buy, store, ship from your own stock). Pure drop-shipping from retail sites is banned on both platforms. RelistApp should focus on the "buy low, store, relist" model rather than direct drop-ship fulfillment.

---

## 2. How to Avoid Suspension

### Amazon Suspension Prevention

1. **Source from authorized distributors** -- obtain proper invoices (not retail receipts) showing manufacturer/distributor name, your business name, quantities, and dates.
2. **Avoid restricted brands** -- check brand gating before listing. Use Amazon's Brand Registry lookup or third-party tools.
3. **Maintain product condition accuracy** -- never list used/refurbished items as "New." Amazon AI scans reviews for condition complaints.
4. **Respond to IP complaints within 24 hours** -- every unresolved complaint deducts 2-8 points from your Account Health Rating (AHR).
5. **Keep invoices on file for 365 days minimum** -- Amazon can request proof of authenticity at any time.
6. **Use FBA when possible** -- Fulfillment by Amazon removes shipping performance risk from your metrics.
7. **Monitor Account Health Dashboard weekly** -- do not wait for monthly reviews. AHR changes in real time.

### eBay Suspension Prevention

1. **Build account trust before listing** -- spend 10-15 days browsing, buying small items, reading policies. This establishes normal user behavior patterns in eBay's algorithms.
2. **Start with unbranded/generic products** -- avoid VeRO-listed brands entirely in the first 90 days.
3. **Ship within stated handling time** -- 1-day handling time improves visibility and keeps metrics clean.
4. **Upload tracking on every order** -- eBay's tracking upload rate is a key metric.
5. **Maintain <2% defect rate** -- this includes cases opened, returns for "not as described," and negative feedback.
6. **Respond to buyer messages within 24 hours** -- response time affects seller level.
7. **Never use multiple accounts without linking them** -- eBay detects device fingerprints, IP addresses, and payment method overlaps.
8. **Avoid sudden listing volume spikes** -- gradual scaling prevents automated review triggers.

---

## 3. Tracking Requirements

### Amazon

| Metric | Requirement |
|--------|------------|
| Valid Tracking Rate (VTR) | > 95% for all seller-fulfilled orders |
| On-Time Delivery Rate | > 97% |
| Tracking Upload Deadline | Before confirming shipment |
| Carrier Requirements | Must use Amazon-recognized carriers with scan-based tracking |

### eBay

| Metric | Requirement |
|--------|------------|
| Tracking Upload Rate | > 95% for Top Rated Seller status |
| On-Time Shipping | Ship within stated handling time |
| Tracking Validation | eBay cross-references tracking with carrier data |
| International Tracking | Required for Global Shipping Program orders |

### RelistApp Implementation

- Auto-upload tracking numbers as soon as carrier provides them
- Validate tracking numbers against carrier APIs before upload
- Alert seller if tracking shows delivery exception within 24 hours
- Flag orders approaching handling time deadline

---

## 4. Seller Metrics to Maintain

### Amazon Account Health Rating (AHR)

The AHR is scored 0-1,000. Every seller starts at 200.

- **Earning points**: +4 points per 200 fulfilled orders over trailing 180 days
- **Losing points**: -2 to -8 points per violation (IP complaints, authenticity issues, policy violations)
- **Suspension threshold**: AHR drops to critical zone (below 100)

**Critical Metrics (Must Stay Within Thresholds)**:

| Metric | Target | Suspension Threshold |
|--------|--------|---------------------|
| Order Defect Rate (ODR) | < 0.5% | > 1% |
| Late Shipment Rate | < 2% | > 4% |
| Pre-Fulfillment Cancel Rate | < 1% | > 2.5% |
| Valid Tracking Rate | > 98% | < 95% |
| A-to-Z Guarantee Claims | < 0.5% | Cumulative impact on ODR |
| Negative Feedback Rate | < 1% | Cumulative impact on ODR |

### eBay Seller Levels

| Level | Requirements | Benefits |
|-------|-------------|----------|
| Below Standard | Defect rate > 2%, late shipment > 10% | Listing restrictions, lower visibility |
| Above Standard | Defect rate < 2%, late shipment < 10% | Normal selling privileges |
| Top Rated | Defect rate < 0.5%, late shipment < 3%, tracking > 95% | 10% FVF discount, Top Rated Plus badge, priority search |
| Top Rated Plus | Top Rated + 1-day handling + 30-day returns | Maximum visibility boost |

### RelistApp Dashboard Metrics

The RelistApp analytics dashboard should track all of the above in real time with:
- Color-coded health indicators (green/yellow/red)
- Trend lines showing 7-day, 30-day, 90-day trajectories
- Automated alerts when any metric enters yellow zone (50% of threshold)
- Automated listing pause when any metric enters red zone (80% of threshold)

---

## 5. Volume Scaling Without Triggering Reviews

### The Scaling Problem

Both Amazon and eBay have automated systems that flag accounts showing unusual growth patterns. Rapid scaling triggers manual reviews, temporary holds, or outright suspensions.

### Amazon Scaling Strategy

1. **Month 1-2**: List 10-20 products. Focus on ungated categories (books, home & kitchen, toys without brand restrictions). Target 5-10 orders/day.
2. **Month 3-4**: Scale to 50-100 products. Begin FBA shipments. Target 20-50 orders/day. Request brand ungating for 2-3 categories.
3. **Month 5-6**: Scale to 200-500 products. Diversify categories. Target 50-150 orders/day.
4. **Month 7+**: Scale to 1000+ products. Target 150+ orders/day. By now AHR should be 400+ providing suspension buffer.

**Rules**:
- Never increase listing count by more than 100% in a single week
- Maintain ODR below 0.5% during scaling (tighter than Amazon's 1% threshold)
- Keep inventory depth at 3+ units per SKU to avoid cancellations
- Use FBA for at least 50% of volume to de-risk shipping metrics

### eBay Scaling Strategy

1. **Month 1**: Start with 10 items / $500 limit (new account default). Sell through inventory, get positive feedback.
2. **Month 2**: Request limit increase. Target 50-70 items / $3,500.
3. **Month 3-4**: Request another increase after demonstrating consistent sales and clean metrics. Target 200+ items.
4. **Month 5-6**: Apply for eBay Managed Payments if not already enrolled. Target 500+ items.
5. **Month 7+**: With Above Standard or Top Rated status, limits increase automatically each evaluation period.

**Rules**:
- Never list at more than 80% of your current limit (leaves buffer for relists)
- Request limit increases proactively -- don't wait for auto-increases
- Diversify across 3+ categories to avoid category-specific reviews
- Maintain 30-day return policy from day one (required for Top Rated Plus)

### Multi-Platform Scaling

- Stagger launches across platforms: start Amazon first, add eBay 30 days later, add Walmart/Mercari/Poshmark 60 days later
- Use different product mixes per platform to avoid cross-platform detection algorithms
- Maintain separate tracking and metrics dashboards per platform
- Never share the same product images across platforms without modification (some platforms detect this)

---

## 6. RelistApp Account Health Automation Features

### Automated Monitoring
- Pull seller metrics via platform APIs every 4 hours
- Calculate rolling averages for all key metrics
- Predict metric trajectory 7 days forward using trend analysis

### Automated Protection
- **Auto-pause listings** when defect rate exceeds 0.7% (before hitting 1% threshold)
- **Auto-extend handling time** when shipping backlog exceeds capacity
- **Auto-remove listings** for products receiving IP complaints
- **Auto-adjust pricing** to maintain minimum margin (prevents selling at a loss due to price race)

### Alert System
- Telegram/email alerts for: metric threshold warnings, new buyer cases, negative feedback, policy notifications
- Daily health summary digest
- Weekly trend report with recommendations

---

## Sources

- [Amazon Account Health 2026 Checklist](https://www.hrlinfotechs.com/blog/amazon-account-health-2026-the-must-follow-checklist-to-stay-safe-scale-your-business/)
- [Amazon Seller Performance Metrics 2026](https://feedvisor.com/university/seller-performance-measurements/)
- [Amazon Seller Suspended Account Recovery Guide 2026](https://ave7lift.ai/blog/how-to-recover-an-amazon-seller-suspended-account)
- [Retail Arbitrage on Amazon 2026](https://goaura.com/blog/retail-arbitrage-on-amazon)
- [eBay Selling Limits Guide 2026](https://sellbery.com/blog/ebay-selling-limits-guide-a-quick-way-to-increase-your-ebay-selling-limit/)
- [eBay Dropshipping Policy 2026 - ZIK Analytics](https://www.zikanalytics.com/blog/ebay-dropshipping-policy/)
- [How to Avoid eBay Suspension 2026 - AutoDS](https://www.autods.com/blog/dropshipping-tips-strategies/avoid-ebay-suspension/)
- [eBay Dropshipping Policy 2026 - SuperDS](https://super-ds.com/blog/ebay-dropshipping-policy-2025-you-must-know)
- [Amazon Metrics Guide - Canopy Management](https://canopymanagement.com/metrics-every-amazon-seller-should-track/)
- [eBay Selling Limits](https://www.ebay.com/help/selling/listings/selling-limits?id=4107)
