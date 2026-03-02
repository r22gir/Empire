# MarketForge Ad Cost Study

## Executive Summary

This document serves as the living record for all MarketForge advertising campaign planning, cost benchmarks, budget allocation, and bi-weekly performance tracking.

**Purpose:** MarketForge launch campaign planning and ongoing EmpireBox ecosystem ad spend management.

| Item | Detail |
|------|--------|
| Initial Budget Cap | $5,000 |
| MarketForge Launch Split | $2,500 (main launch blast) |
| EmpireBox Ecosystem Split | $2,500 (staggered with subproduct launches) |

Reference: See Issue #18 for the master business plan.

---

## 1. Ad Channel Cost Benchmarks (2025-2026)

*Sources: Webtools.co, SmartyAds, AWISEE, Madgicx*

| Channel | CPM | CPC | CAC | CTR | Conversion Rate | Notes |
|---------|-----|-----|-----|-----|-----------------|-------|
| Facebook | $7–$8 | $0.97–$1.88 | $50–$150 | 0.9%–1.5% | 1%–3% | Spikes Q4 |
| Instagram | $8–$11 | $1–$2.50 | $75–$200 | 0.7%–1.2% | 1%–2.5% | Reels/Stories |
| Google Ads | $2–$6 (display) | $2.70–$5.30 | $75–$200 | 3%–5% | 3%–5% | High intent |
| TikTok | $6–$8 | $0.20–$0.50 | $80–$250 | 0.5%–1.5% | 0.5%–1.5% | Rising costs |
| YouTube | $3.70–$10 | $0.50–$2 | $100–$300 | 0.5%–2% | 1%–3% | Good for demos |
| LinkedIn | $25–$70 | $4–$15 | $150–$500 | 0.3%–0.8% | 2%–5% | B2B/LLCFactory |
| Reddit | $3–$8 | $0.50–$2 | $50–$150 | 0.3%–1% | 0.5%–2% | Community targeting |

---

## 2. Budget Allocation Strategy

**Total Cap: $5,000**

- $2,500 → MarketForge (main launch blast)
- $2,500 → EmpireBox ecosystem (staggered with subproduct launches)

| Channel | MarketForge | EmpireBox | Total |
|---------|-------------|-----------|-------|
| Meta (FB/IG) | $800 | $800 | $1,600 |
| Google | $600 | $600 | $1,200 |
| TikTok | $400 | $400 | $800 |
| YouTube | $200 | $400 | $600 |
| Reddit | $250 | $150 | $400 |
| Misc/Reserve | $250 | $150 | $400 |
| **Total** | **$2,500** | **$2,500** | **$5,000** |

---

## 3. Staggered Launch Timeline

| Phase | Weeks | Budget | Focus |
|-------|-------|--------|-------|
| MarketForge Launch Blast | 1–2 | $1,500 | Concentrated launch push across all channels |
| Optimization + Retargeting | 3–4 | $1,000 | Double down on top performers, retarget visitors |
| EmpireBox Brand Introduction | 5–6 | $800 | Introduce EmpireBox brand to warm audience |
| Subproduct Teasers | 7–8 | $700 | Tease upcoming subproducts and build waitlists |
| Next Product Launch Support | 9–12 | Remaining | Support next product launch with lessons learned |

---

## 4. Bi-Weekly Tracking Template

Update this table every two weeks. Compare to previous cycle and note significant changes.

| Cycle | Date Range | FB CAC | Google CAC | TikTok CAC | YT CAC | IG CAC | Reddit CAC | Signups | Blended CAC | Δ vs Prev | Notes |
|-------|------------|--------|------------|------------|--------|--------|------------|---------|-------------|-----------|-------|
| C1 | Week 1–2 | | | | | | | | | N/A | Launch |
| C2 | Week 3–4 | | | | | | | | | | |
| C3 | Week 5–6 | | | | | | | | | | |
| C4 | Week 7–8 | | | | | | | | | | |
| C5 | Week 9–10 | | | | | | | | | | |
| C6 | Week 11–12 | | | | | | | | | | |

---

## 5. MarketForge "Analyze Image for Description" Feature

### The Killer Feature — "Snap, List, Done!"

This feature allows users to instantly generate a complete marketplace listing from either a barcode scan or a photo of the product.

**User Flow:**

1. User starts a new listing
2. **Option A**: Scan barcode → Query Barcode Lookup API (https://www.barcodelookup.com)
3. **Option B**: Take picture → OpenClaw AI image analysis
4. System retrieves: UPC, EAN, ISBN data, product name, description, images, pricing, reviews
5. Listing Agent auto-fills: title, description, category, suggested price
6. User reviews and confirms → **Listed!**

**Implementation (Pseudo-code):**

```python
import requests
from openclaw import ImageAnalyzer

class ListingAgent:
    def __init__(self):
        self.barcode_api = "https://api.barcodelookup.com/v3/products"
        self.image_analyzer = ImageAnalyzer()
    
    def analyze_product(self, barcode=None, image=None):
        product_info = {}
        
        # Try barcode lookup first
        if barcode:
            response = requests.get(
                self.barcode_api,
                params={"barcode": barcode, "key": API_KEY}
            )
            if response.ok:
                data = response.json()
                products = data.get("products", [])
                if products:
                    product = products[0]
                    stores = product.get("stores", [])
                    product_info = {
                        "title": product["title"],
                        "description": product["description"],
                        "category": product["category"],
                        "brand": product["brand"],
                        "images": product["images"],
                        "avg_price": stores[0]["price"] if stores else None,
                        "source": "barcode_lookup"
                    }
        
        # Fallback to image analysis
        if not product_info and image:
            analysis = self.image_analyzer.analyze(image)
            product_info = {
                "title": analysis.suggested_title,
                "description": analysis.generated_description,
                "category": analysis.detected_category,
                "brand": analysis.detected_brand,
                "condition": analysis.estimated_condition,
                "source": "openclaw_vision"
            }
        
        return product_info
    
    def create_listing(self, product_info):
        listing = Listing()
        listing.title = product_info["title"]
        listing.description = self.enhance_description(product_info["description"])
        listing.category = product_info["category"]
        listing.suggested_price = self.calculate_price(product_info)
        return listing
```

---

## 6. Decision Rules for Budget Reallocation

Review and reallocate budget every 2 weeks based on the following rules:

| Condition | Action |
|-----------|--------|
| CAC < $50 | Scale that channel 2× |
| CAC > $150 | Kill that channel immediately |
| Total signups < 20 after $1,500 spent | Pause all spend and review product-market fit |
| A channel's CAC drops 20%+ from prior cycle | Increase allocation by 50% |
| A channel's CAC rises 30%+ from prior cycle | Reduce allocation by 50% |

---

## 7. ROI & LTV Analysis

### Subscription Tiers

| Product | Monthly Price | Annual LTV | Target CAC | LTV:CAC Ratio |
|---------|--------------|------------|------------|---------------|
| MarketForge Lite | $29 | $348 | $75 | 4.6:1 |
| MarketForge Pro | $59 | $708 | $125 | 5.7:1 |
| MarketForge Empire | $99 | $1,188 | $200 | 5.9:1 |
| EmpireBox Ecosystem (avg) | $59 | $708 | $150 | 4.7:1 |

### Healthy Benchmarks
- **Minimum acceptable LTV:CAC**: 3:1
- **Target LTV:CAC**: 5:1+
- **Payback period target**: < 6 months

---

## 8. Sample Ad Creative

### MarketForge — "Snap, List, Done!" Campaign

**Platform:** TikTok / Instagram Reels (15–30 sec video)

**Hook (0–3 sec):**
> "I listed 47 items in one hour using this app…"

**Body (3–20 sec):**
> Show phone scanning a barcode → listing appears instantly → "Listed on eBay, Poshmark, and Mercari at the same time."
> Voice over: "MarketForge does the work. You just confirm and collect."

**CTA (20–30 sec):**
> "Try MarketForge free for 14 days. Link in bio."

---

**Platform:** Google Search Ad

**Headline 1:** List Items 10× Faster with AI
**Headline 2:** Snap a Photo — We Write the Listing
**Headline 3:** Sell on eBay, Poshmark & More
**Description:** MarketForge scans barcodes and analyzes photos to auto-fill your listings. Start free. No credit card required.

---

**Platform:** Reddit (r/Flipping, r/Entrepreneur)

**Sponsored Post Title:** "We built an app that writes marketplace listings from a photo — here's how it works"

**Body:** Short demo GIF + explanation of the "Snap, List, Done!" workflow + link to free trial.

---

## 9. Update Protocol

- **Frequency**: Update the Bi-Weekly Tracking table (Section 4) every 2 weeks.
- **Process**:
  1. Pull CAC data from each ad platform dashboard
  2. Calculate blended CAC = total spend ÷ total signups
  3. Apply decision rules from Section 6
  4. Document changes and reasoning in the Notes column
  5. Reference updates in Issue #18 comments
- **Owner**: Marketing lead / campaign manager
- **Review meeting**: Every other Monday, 30 min

---

*Document Version: 1.0*
*Last Updated: 2026-02-19*
*Owner: EmpireBox Marketing Team*
*Reference: Issue #18 — Master Business Plan*
