# RelistApp Risk Analysis

> Last updated: April 2026
> Purpose: Comprehensive risk register for cross-platform arbitrage operations with mitigation strategies.

---

## Risk Summary Matrix

| Category | Risk Level | Impact | Likelihood | Mitigation Difficulty |
|----------|-----------|--------|------------|----------------------|
| Account Suspension | CRITICAL | High | Medium | Medium |
| Price Race / Margin Collapse | HIGH | High | High | Low (automatable) |
| Returns & Refunds | HIGH | Medium | High | Medium |
| Payment Holds | MEDIUM | Medium | Medium | Low |
| Out-of-Stock (OOS) | HIGH | Medium | High | Low (automatable) |
| Wrong Item Shipped | MEDIUM | High | Low | Medium |
| Shipping Delays | HIGH | Medium | High | Low |
| ToS Violations | CRITICAL | High | Medium | Medium |
| Trademark / IP Issues | HIGH | High | Medium | Medium |
| Sales Tax Compliance | MEDIUM | Medium | Medium | Low (automatable) |
| Chargeback Fraud | MEDIUM | Medium | Medium | Low |

---

## 1. Account Risks

### 1.1 Platform Suspension

**Risk**: Account permanently suspended for policy violations, killing all active listings and held funds.

**Triggers**:
- Retail arbitrage drop-shipping detected (eBay bans this entirely; Amazon rejects retail receipts)
- Brand gating violations (listing restricted brands without authorization)
- VeRO/IP complaints accumulating without resolution
- Metrics falling below thresholds (ODR > 1%, late shipment > 4%)
- Multiple accounts detected without proper linking

**Impact**: Loss of all active listings, held funds (up to 90 days on Amazon), destroyed seller history, potential permanent ban from platform.

**Mitigation**:
- Hold inventory yourself -- do not drop-ship from retail sites
- Maintain invoice documentation from wholesale/authorized suppliers
- Check brand restrictions before listing any product
- Monitor Account Health Rating (AHR) daily via RelistApp dashboard
- Auto-pause listings when metrics approach danger zones
- Maintain backup accounts on secondary platforms (diversification)
- Keep less than 60% of revenue on any single platform

### 1.2 Selling Limit Restrictions

**Risk**: eBay caps new accounts at 10 items / $500 in month one. Amazon may gate categories or require approval.

**Impact**: Revenue bottleneck during growth phase, inability to capitalize on time-sensitive deals.

**Mitigation**:
- Start account building 30-60 days before planned launch
- Request limit increases proactively with clean metrics
- Use graduated scaling strategy (see Account Health Playbook)
- Build multiple platform presences to distribute volume

### 1.3 Review/Feedback Manipulation Detection

**Risk**: Platforms detect artificial review patterns or feedback solicitation, resulting in suspension.

**Impact**: Account suspension, listing removal, loss of organic ranking.

**Mitigation**:
- Never solicit reviews outside platform-approved channels
- Use Amazon's "Request a Review" button only
- Do not offer incentives for positive feedback
- Let reviews accumulate organically

---

## 2. Financial Risks

### 2.1 Price Race / Margin Collapse

**Risk**: Competitors match or undercut your price, collapsing margins to zero or negative. Amazon's Buy Box algorithm accelerates this by rewarding lower prices.

**Impact**: Selling at a loss, inventory becoming unprofitable, wasted capital.

**Likelihood**: HIGH -- this is the most common financial risk in arbitrage. Multiple sellers source the same clearance/deal items.

**Mitigation**:
- **Real-time price monitoring**: RelistApp must check source and destination prices every 15-30 minutes
- **Auto-pause listings** when margin drops below minimum threshold (e.g., 15%)
- **Minimum margin rules**: never list items with less than 20% gross margin to absorb price drops
- **Avoid saturated products**: skip items with 10+ FBA sellers on the same listing
- **Speed advantage**: list and sell before competition catches up (24-48 hour window on deals)
- **Diversify across 200+ SKUs** so no single product's margin collapse is catastrophic

### 2.2 Returns and Refunds

**Risk**: Buyer returns product, you absorb shipping costs and restocking. In drop-ship model, you may not be able to return to original source.

**Impact**: Direct financial loss of product cost + shipping + restocking fee. Return rates in ecommerce average 15-30% for apparel, 5-10% for electronics/home goods.

**Likelihood**: HIGH -- returns are guaranteed at scale.

**Mitigation**:
- Factor 8-12% return rate into profit calculations from day one
- Avoid high-return categories (clothing, shoes) unless margins exceed 40%
- Write accurate, detailed listings to reduce "not as described" returns
- Photograph actual product condition for used/refurbished items
- Build return cost into pricing model
- For FBA: Amazon handles returns but charges fees; factor these in
- Track return rate per product -- auto-delist products with >15% return rate

### 2.3 Payment Holds

**Risk**: Platforms hold funds for new sellers or during disputes. Amazon holds funds for 14 days for new sellers. eBay/PayPal may hold funds for 21 days. Payment processor freezes for high chargeback ratios.

**Impact**: Cash flow crunch -- you pay for inventory but cannot access revenue for 2-3 weeks.

**Mitigation**:
- Maintain 60-90 days of operating capital as cash reserve
- Use business credit lines for inventory purchases (not personal funds)
- Start with low-cost inventory to minimize capital at risk during hold periods
- Upload tracking immediately to accelerate eBay payment releases
- Maintain chargeback ratio below 0.5% (well under the 0.9% danger threshold)
- Diversify payment processors

### 2.4 Chargebacks

**Risk**: Buyers dispute charges with their bank/credit card company. You lose the sale amount plus $20-50 chargeback fee per incident. Chargeback ratio above 0.9% triggers payment processor penalties or account termination.

**Impact**: Double loss (product + payment + fee). At scale, even 1% chargeback rate on 1000 orders/day = 10 chargebacks/day = $300-500/day in fees alone.

**Mitigation**:
- Ship with tracking and signature confirmation for orders over $100
- Provide proactive shipping updates (reduces "where is my order" disputes)
- Respond to customer inquiries within 4 hours
- Issue refunds proactively when shipping is significantly delayed
- Use fraud detection tools to flag suspicious orders (mismatched billing/shipping, high-risk zip codes)
- Maintain clear, visible return/refund policy

### 2.5 Currency and Fee Changes

**Risk**: Platform fee increases, shipping rate changes, or category commission adjustments erode margins.

**Impact**: Products that were profitable become unprofitable overnight.

**Mitigation**:
- Build 5% buffer into profit calculations for fee changes
- Monitor platform announcements for fee schedule updates
- Recalculate profitability across all SKUs quarterly
- RelistApp should auto-recalculate when fee structures change

---

## 3. Operational Risks

### 3.1 Out-of-Stock at Source (OOS)

**Risk**: You list a product, buyer purchases, but the source is now out of stock. You must cancel the order, damaging metrics.

**Impact**: Pre-fulfillment cancellation (Amazon penalizes > 2.5%), negative feedback, defect rate increase.

**Likelihood**: HIGH -- retail clearance and deal items go OOS rapidly.

**Mitigation**:
- **Inventory sync every 30 minutes**: RelistApp checks source availability and auto-ends listings when OOS
- **Hold inventory model**: buy and hold stock rather than listing items you do not possess
- **Multi-source mapping**: map each product to 2-3 alternative sources for failover
- **Buffer stock**: maintain 2+ units per SKU to absorb demand spikes
- **Predictive OOS alerts**: if source inventory drops below 3 units, flag for review

### 3.2 Wrong Item Shipped

**Risk**: Supplier ships wrong item, wrong variant (size/color), or damaged product. Buyer opens case.

**Impact**: Return costs, negative feedback, A-to-Z claim, defect rate increase.

**Mitigation**:
- If using drop-ship model: vet suppliers rigorously, use only suppliers with <1% error rate
- If holding inventory: implement barcode scanning for pick/pack accuracy
- Include packing slip with correct item details
- Respond to wrong-item complaints within 4 hours with prepaid return label
- Track error rate per supplier -- drop suppliers with >2% error rate

### 3.3 Shipping Delays

**Risk**: Carrier delays cause late delivery, triggering buyer complaints and metric damage.

**Impact**: Late shipment rate increase, negative feedback, A-to-Z claims.

**Likelihood**: HIGH -- carrier delays are common, especially during peak seasons (Q4, Prime Day).

**Mitigation**:
- Use 2-3 day handling time buffer (list 3-day handling, ship in 1 day)
- Use multiple carriers (USPS, UPS, FedEx) and route based on speed/cost
- Ship same day or next day for all orders
- Upgrade shipping method proactively if delay detected
- Auto-message buyer if tracking shows delivery exception
- Avoid listing items requiring cross-country ground shipping with tight delivery windows

### 3.4 Listing Hijacking / Competition

**Risk**: Competitors jump on your profitable listings, undercut price, or worse -- list counterfeit items that generate complaints attributed to all sellers on the listing.

**Impact**: Lost Buy Box, price erosion, association with counterfeit complaints.

**Mitigation**:
- Monitor competitor count on each listing
- Auto-adjust price to maintain Buy Box when competition increases
- Report counterfeit sellers to platform
- Consider private label for high-volume products to control listing

---

## 4. Legal Risks

### 4.1 Terms of Service Violations

**Risk**: Operating outside platform ToS, even unintentionally. Both Amazon and eBay have complex, evolving policies.

**Impact**: Account suspension, fund holds, permanent ban.

**Specific Violations to Avoid**:
- Drop-shipping from retail sites (eBay: explicit ban; Amazon: technically allowed but practically penalized)
- Multiple accounts without disclosure
- Review manipulation or incentivized feedback
- Listing counterfeit or inauthentic items
- Price gouging during emergencies (both platforms have policies)
- Selling restricted/regulated items without proper authorization

**Mitigation**:
- Review platform policy updates monthly
- Subscribe to Seller Central / eBay Seller Hub announcements
- RelistApp should flag listings that match known restricted product patterns
- Consult ecommerce attorney for annual ToS compliance review

### 4.2 Trademark and Intellectual Property

**Risk**: Listing products that infringe trademarks, use copyrighted images, or violate brand restrictions.

**Impact**: VeRO takedowns (eBay), IP complaint deductions (Amazon AHR), legal cease-and-desist letters, potential lawsuits.

**Common Traps**:
- Using brand names in titles for unbranded compatible products
- Using manufacturer images without permission
- Listing restricted brands without authorization
- Creating listings that imply brand endorsement or authorization

**Mitigation**:
- Maintain a "banned brands" list in RelistApp (all VeRO-listed brands + known litigious brands)
- Auto-flag listings containing trademarked terms
- Take your own product photos when possible
- Use generic descriptions for compatible/replacement products
- Remove listings within 24 hours of any IP complaint

### 4.3 Sales Tax Compliance

**Risk**: Failure to collect and remit sales tax in states where you have economic nexus. Post-Wayfair (2018), all states with sales tax have economic nexus laws.

**2026 Updates**:
- Most states count marketplace facilitator sales toward your nexus threshold, even though the marketplace collects tax on your behalf
- Illinois removed transaction thresholds in 2026, increasing exposure for high-ticket sellers
- Florida is the notable exception: marketplace facilitator sales do NOT count toward nexus threshold
- Common threshold: $100,000 in sales or 200 transactions in a state (varies by state)

**Impact**: Back taxes, penalties, interest. Multi-state exposure grows rapidly at 1000 orders/day.

**Mitigation**:
- Use tax automation software (TaxJar, Avalara, TaxCloud) integrated with RelistApp
- Monitor cumulative sales by state across all channels
- Register for sales tax permits in states where nexus is triggered
- Marketplace facilitator laws mean Amazon/eBay collect tax on their platforms, but you are still responsible for your own website sales and tracking nexus
- Budget for quarterly tax compliance review with CPA

### 4.4 Consumer Protection Laws

**Risk**: Violating state or federal consumer protection laws through misleading listings, failure to honor warranties, or deceptive pricing.

**Impact**: FTC enforcement, state attorney general investigations, civil lawsuits.

**Mitigation**:
- Accurate product descriptions and condition grading
- Honor all stated return policies
- Do not use deceptive pricing (fake "was" prices, fake discounts)
- Comply with product safety regulations for applicable categories

---

## 5. Technology Risks

### 5.1 API Rate Limits and Breakage

**Risk**: Platform APIs change, rate limits tighten, or access is revoked. RelistApp functionality degrades.

**Impact**: Inability to sync inventory, update prices, or process orders automatically.

**Mitigation**:
- Build API abstraction layers to isolate platform-specific changes
- Implement graceful degradation (fall back to manual workflows)
- Monitor API health and rate limit consumption
- Maintain relationships with platform developer programs

### 5.2 Data Loss

**Risk**: Loss of product data, pricing history, order records, or analytics data.

**Impact**: Inability to operate, loss of historical insights, compliance gaps.

**Mitigation**:
- Daily automated backups of all databases
- Multi-region backup storage
- Disaster recovery plan with <4 hour RTO
- Export critical data to offline storage weekly

---

## 6. Risk Scoring for RelistApp Decision Engine

RelistApp should calculate a composite risk score for every product/listing:

```
Risk Score = Account Risk Weight (0.3) + Financial Risk Weight (0.3) + Operational Risk Weight (0.25) + Legal Risk Weight (0.15)

Account Risk Factors:
- Is brand restricted? (+40 points)
- Has brand received IP complaints in last 90 days? (+30 points)
- Is category gated? (+20 points)

Financial Risk Factors:
- Margin < 20%? (+30 points)
- Price volatility > 15% in last 30 days? (+25 points)
- Return rate for category > 15%? (+20 points)
- Number of competing sellers > 10? (+15 points)

Operational Risk Factors:
- Source inventory < 5 units? (+30 points)
- Source reliability score < 95%? (+25 points)
- Shipping distance > 3 zones? (+15 points)

Legal Risk Factors:
- Brand on VeRO list? (+50 points)
- Product in regulated category? (+30 points)
- Listing contains trademark terms? (+20 points)

Total: 0-100 scale
0-25: LOW RISK (green) -- auto-list
26-50: MEDIUM RISK (yellow) -- list with monitoring
51-75: HIGH RISK (orange) -- manual review required
76-100: CRITICAL RISK (red) -- do not list
```

---

## Sources

- [Amazon Account Health 2026 Checklist](https://www.hrlinfotechs.com/blog/amazon-account-health-2026-the-must-follow-checklist-to-stay-safe-scale-your-business/)
- [Amazon Seller Performance Metrics 2026](https://feedvisor.com/university/seller-performance-measurements/)
- [Dropshipping Chargebacks - Chargebacks911](https://chargebacks911.com/dropshipping-chargebacks/)
- [Dropshipping Chargebacks Prevention 2026 - AutoDS](https://www.autods.com/blog/dropshipping-tips-strategies/dropshipping-chargebacks/)
- [eBay Dropshipping Policy 2026 - ZIK Analytics](https://www.zikanalytics.com/blog/ebay-dropshipping-policy/)
- [eBay Dropshipping Policy 2026 - SuperDS](https://super-ds.com/blog/ebay-dropshipping-policy-2025-you-must-know)
- [Sales Tax Changes 2026 - TaxCloud](https://taxcloud.com/blog/sales-tax-changes-2026/)
- [Economic Nexus 2026 State-by-State - Numeral](https://www.numeral.com/blog/economic-nexus)
- [Sales Tax Compliance Checklist 2026 - TaxJar](https://www.taxjar.com/blog/sales-tax-compliance-checklist-for-2026)
- [Dropshipping Returns & Refunds](https://dodropshipping.com/refunds-and-returns-dropshipping/)
- [Retail Arbitrage Policy vs Enforcement - Amazon Seller Forums](https://sellercentral.amazon.com/seller-forums/discussions/t/17dfd504-d2c2-4551-86a6-fd1cf3df88ce)
