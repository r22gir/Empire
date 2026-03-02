# Amazon SP-API Compliance Checklist

Operational checklist for MarketF's Amazon Seller Platform integration.
Review this checklist before going live and periodically during operation.

## Pre-Launch Checklist

### Account Setup
- [ ] Amazon Professional Seller account active ($39.99/mo)
- [ ] Tax information and bank account verified in Seller Central
- [ ] Business address and contact info complete
- [ ] Brand Registry completed (if selling branded products)
- [ ] Seller profile note added: "Products aggregated from trusted partners — fulfillment and support handled by MarketF"

### SP-API App Registration
- [ ] Private developer app registered in Seller Central
- [ ] App type set to **Private** (not listed, no $1,400/yr fee)
- [ ] Client ID and Client Secret generated and stored securely in environment variables
- [ ] Refresh Token generated via self-authorization OAuth flow
- [ ] All credentials added to `.env` — **never committed to source code**

### Compliance Module
- [ ] `AMAZON_SELF_ID_STRING` environment variable set (e.g., `Automated by MarketF/EmpireBox v1.0`)
- [ ] Self-identification headers included in every SP-API request
- [ ] Kill switch tested: `AMAZON_KILL_SWITCH_ENABLED=true` halts all operations immediately
- [ ] Kill switch admin endpoint accessible: `POST /admin/amazon/kill-switch`
- [ ] Rate limiting enabled (≤1 req/sec default, exponential backoff on 429)
- [ ] Audit logging active — all API calls logged to `amazon_sync_log` table

### Product Data Validation
- [ ] UPC/EAN/GTIN validation enabled (Luhn checksum, 12–14 digits)
- [ ] Title validation: ≤200 chars, no spam characters
- [ ] Bullet points: max 5, each ≤300 chars
- [ ] Description: ≤1,000 chars
- [ ] Image requirements enforced: 7+ images, main = white background, ≥1,000px
- [ ] Price format validation: positive decimal
- [ ] Required fields enforced: brand, manufacturer, weight, dimensions, category

### Database
- [ ] `amazon_listings` table created with all indexes
- [ ] `amazon_sync_log` table created for audit trail
- [ ] Database migrations applied in production

## Ongoing Compliance

### Daily
- [ ] Check `amazon_sync_log` for unexpected error responses (4xx, 5xx)
- [ ] Monitor account health metrics in Seller Central
- [ ] Verify inventory sync is current (no stale counts)

### Weekly
- [ ] Review listing suppression notices in Seller Central
- [ ] Check for Amazon policy update emails
- [ ] Audit rate limiting logs for throttle events

### Monthly
- [ ] Review Amazon Agent Policy updates at [Seller Central](https://sellercentral.amazon.com/help/hub/reference/external/G200386250)
- [ ] Update `AMAZON_SELF_ID_STRING` version if major platform update released
- [ ] Review and rotate SP-API credentials if needed
- [ ] Reconcile payout reports with partner store payouts

## Prohibited Actions (Never Do)

- ❌ Scrape Seller Central or Amazon product pages
- ❌ Use browser automation against Seller Central UI
- ❌ Exceed API rate limits intentionally
- ❌ Manipulate prices, rankings, or review systems
- ❌ List products without valid UPC/GTIN
- ❌ Use fake or recycled GTINs (GS1 exemption required for truly generic products)
- ❌ List products without brand authorization (if Brand Registry protected)
- ❌ Commit SP-API credentials to source code
- ❌ Disable kill switch capability
- ❌ Disable audit logging

## Incident Response

### If Amazon Throttles API (429 Response)
1. Exponential backoff kicks in automatically
2. Review rate limiting logs to identify cause
3. Reduce concurrent listing update jobs if throttling persists

### If Amazon Flags Account
1. Immediately enable kill switch: `AMAZON_KILL_SWITCH_ENABLED=true`
2. Review `amazon_sync_log` for the flagged time period
3. Identify and pause the partner store responsible
4. Respond to Amazon's Performance Notification within 48 hours

### If Kill Switch Is Activated by Amazon Request
1. Set `AMAZON_KILL_SWITCH_ENABLED=true` in production environment
2. Verify all SP-API calls halt (check logs)
3. Notify affected partner stores
4. Contact Amazon Seller Support for reinstatement guidance

## Amazon Policy References

| Policy | URL |
|--------|-----|
| SP-API Developer Documentation | https://developer-docs.amazon.com/sp-api/ |
| Agent/Automation Policy (Mar 4, 2026) | Seller Central > Help > G200386250 |
| Acceptable Use Policy | Seller Central > Help > G521 |
| Listing Quality Requirements | Seller Central > Help > G200390640 |
| Image Requirements | Seller Central > Help > G1881 |

## Contact & Escalation

- **Amazon Seller Support**: Via Seller Central case system
- **SP-API Issues**: developer-docs.amazon.com/sp-api/docs/report-an-issue
- **Internal Kill Switch**: `POST /admin/amazon/kill-switch` (admin credentials required)
