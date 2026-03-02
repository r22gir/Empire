# Marketplace Integration Guide

This guide provides detailed information on integrating with each marketplace platform.

## Overview

MarketForge supports posting to 5 marketplace platforms:
1. eBay
2. Facebook Marketplace
3. Poshmark
4. Mercari
5. Craigslist

## Integration Status

| Platform | Status | API Available | OAuth Required | Documentation |
|----------|--------|---------------|----------------|---------------|
| eBay | 🔄 Framework Ready | ✅ Yes | ✅ Yes | [Link](https://developer.ebay.com) |
| Facebook | 🔄 Framework Ready | ✅ Yes | ✅ Yes | [Link](https://developers.facebook.com/docs/marketplace) |
| Poshmark | 🔄 Framework Ready | ❌ Limited | ❓ Research Needed | Partner API |
| Mercari | 🔄 Framework Ready | ❓ Research Needed | ❓ Research Needed | Research needed |
| Craigslist | 🔄 Framework Ready | ❌ No | ❌ No | Automation required |

---

## 1. eBay Integration

### Overview
eBay provides a comprehensive REST API for listing items, managing inventory, and receiving order notifications.

### Prerequisites
1. eBay developer account: https://developer.ebay.com/
2. Create an application
3. Get sandbox credentials for testing
4. Get production credentials when ready

### Required Credentials
```env
EBAY_APP_ID=your_app_id
EBAY_CERT_ID=your_cert_id
EBAY_DEV_ID=your_dev_id
EBAY_OAUTH_REDIRECT_URI=http://localhost:8000/auth/ebay/callback
```

### Implementation Steps

#### Step 1: OAuth 2.0 Setup
```python
# backend/app/routers/ebay_auth.py
from fastapi import APIRouter, HTTPException
import requests

router = APIRouter(prefix="/auth/ebay", tags=["ebay"])

@router.get("/authorize")
async def ebay_authorize():
    """Redirect user to eBay OAuth page"""
    auth_url = (
        f"https://auth.ebay.com/oauth2/authorize"
        f"?client_id={EBAY_APP_ID}"
        f"&response_type=code"
        f"&redirect_uri={EBAY_OAUTH_REDIRECT_URI}"
        f"&scope=https://api.ebay.com/oauth/api_scope/sell.inventory"
    )
    return {"authorization_url": auth_url}

@router.get("/callback")
async def ebay_callback(code: str, db: Session = Depends(get_db)):
    """Handle OAuth callback and exchange code for token"""
    # Exchange authorization code for access token
    token_response = requests.post(
        "https://api.ebay.com/identity/v1/oauth2/token",
        headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Authorization": f"Basic {base64_credentials}"
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": EBAY_OAUTH_REDIRECT_URI
        }
    )
    
    # Save token to user's account (encrypted)
    # ...
```

#### Step 2: Create Listing
```python
# backend/app/services/marketplace_service.py
async def post_to_ebay(self, listing: models.Listing) -> Dict:
    """Post listing to eBay"""
    if not self.user.ebay_token:
        return {"success": False, "message": "eBay not connected"}
    
    # Prepare listing data in eBay format
    ebay_listing = {
        "SKU": f"MF-{listing.id}",
        "product": {
            "title": listing.title,
            "description": listing.description,
            "imageUrls": [listing.photo_url],
            "aspects": {}
        },
        "condition": "NEW",
        "availability": {
            "shipToLocationAvailability": {
                "quantity": 1
            }
        },
        "pricingSummary": {
            "price": {
                "value": str(listing.price),
                "currency": "USD"
            }
        }
    }
    
    # Post to eBay API
    response = requests.post(
        "https://api.ebay.com/sell/inventory/v1/inventory_item",
        headers={
            "Authorization": f"Bearer {decrypt(self.user.ebay_token)}",
            "Content-Type": "application/json"
        },
        json=ebay_listing
    )
    
    if response.status_code == 201:
        return {
            "success": True,
            "listing_id": response.json().get("SKU")
        }
    else:
        return {
            "success": False,
            "message": response.text
        }
```

### Resources
- **Documentation**: https://developer.ebay.com/api-docs/sell/inventory/overview.html
- **OAuth Guide**: https://developer.ebay.com/api-docs/static/oauth-tokens.html
- **Sandbox**: https://developer.ebay.com/my/keys

---

## 2. Facebook Marketplace Integration

### Overview
Facebook Marketplace can be accessed via the Facebook Graph API for Business.

### Prerequisites
1. Facebook Developer account: https://developers.facebook.com/
2. Create a Facebook App
3. Request Marketplace permissions
4. Get Page access token

### Required Credentials
```env
FACEBOOK_APP_ID=your_app_id
FACEBOOK_APP_SECRET=your_app_secret
FACEBOOK_PAGE_ID=your_page_id
```

### Implementation Steps

#### Step 1: OAuth Setup
```python
@router.get("/auth/facebook/authorize")
async def facebook_authorize():
    auth_url = (
        f"https://www.facebook.com/v18.0/dialog/oauth"
        f"?client_id={FACEBOOK_APP_ID}"
        f"&redirect_uri={FACEBOOK_REDIRECT_URI}"
        f"&scope=pages_manage_posts,marketplace_management"
    )
    return {"authorization_url": auth_url}
```

#### Step 2: Create Listing
```python
async def post_to_facebook(self, listing: models.Listing) -> Dict:
    """Post listing to Facebook Marketplace"""
    
    # Upload photo first
    photo_response = requests.post(
        f"https://graph.facebook.com/v18.0/{PAGE_ID}/photos",
        params={
            "access_token": self.user.facebook_token,
            "published": False
        },
        files={"source": open(listing.photo_url, "rb")}
    )
    
    photo_id = photo_response.json().get("id")
    
    # Create marketplace listing
    listing_data = {
        "name": listing.title,
        "description": listing.description,
        "price": int(listing.price * 100),  # In cents
        "currency": "USD",
        "condition": "NEW",
        "photos": [{"id": photo_id}]
    }
    
    response = requests.post(
        f"https://graph.facebook.com/v18.0/{PAGE_ID}/marketplace_listings",
        params={"access_token": self.user.facebook_token},
        json=listing_data
    )
    
    # Return result
```

### Resources
- **Documentation**: https://developers.facebook.com/docs/marketplace
- **Graph API Explorer**: https://developers.facebook.com/tools/explorer/

---

## 3. Poshmark Integration

### Overview
Poshmark does not have a public API. Integration options:

1. **Partner API**: Apply for Poshmark partner program
2. **Browser Automation**: Use Selenium/Playwright
3. **Manual Posting**: User posts manually, we track

### Recommended Approach: Partner API

#### Step 1: Apply for Partnership
1. Contact: https://poshmark.com/business
2. Explain your use case
3. Request API access

#### Step 2: If API Unavailable - Browser Automation
```python
from playwright.async_api import async_playwright

async def post_to_poshmark(self, listing: models.Listing) -> Dict:
    """Automated posting to Poshmark using browser automation"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Login
        await page.goto("https://poshmark.com/login")
        # Fill credentials from encrypted storage
        
        # Navigate to create listing
        await page.goto("https://poshmark.com/create-listing")
        
        # Upload photo
        await page.set_input_files('input[type="file"]', listing.photo_url)
        
        # Fill form
        await page.fill('input[name="title"]', listing.title)
        await page.fill('textarea[name="description"]', listing.description)
        await page.fill('input[name="price"]', str(listing.price))
        
        # Submit
        await page.click('button[type="submit"]')
        
        # Get listing ID from URL
        await page.wait_for_url("**/listing/*")
        listing_url = page.url
        
        await browser.close()
        
        return {
            "success": True,
            "listing_id": listing_url.split("/")[-1]
        }
```

### Resources
- **Poshmark**: https://poshmark.com
- **Playwright**: https://playwright.dev/python/

---

## 4. Mercari Integration

### Overview
Research needed for Mercari API availability.

### Steps to Research
1. Check if Mercari has a public API
2. Look for developer documentation
3. Contact Mercari business team
4. Consider automation if no API

### Potential Implementation
```python
async def post_to_mercari(self, listing: models.Listing) -> Dict:
    """Post to Mercari - implementation depends on API availability"""
    
    # Option 1: If API exists
    # Use REST API similar to eBay
    
    # Option 2: If no API
    # Use browser automation similar to Poshmark
    
    # For now, return not implemented
    return {
        "success": False,
        "message": "Mercari integration requires API research"
    }
```

### Resources
- **Mercari**: https://www.mercari.com
- Check for seller API or business program

---

## 5. Craigslist Integration

### Overview
Craigslist has no official API. Integration must use automation.

### Approach: Browser Automation

```python
async def post_to_craigslist(self, listing: models.Listing) -> Dict:
    """Post to Craigslist using browser automation"""
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Navigate to posting page
        await page.goto("https://post.craigslist.org/")
        
        # Select category
        # Fill location
        # Upload images
        # Fill title and description
        # Set price
        # Submit
        
        # Handle CAPTCHA (may require manual intervention)
        
        await browser.close()
```

### Challenges
- No API available
- CAPTCHAs may block automation
- Terms of Service may prohibit automation
- Account verification required

### Alternative: Manual Posting Assistant
Instead of full automation, provide a "posting assistant" that:
1. Generates optimized listing text
2. Formats images
3. Provides copy-paste template
4. Guides user through manual posting

---

## General Integration Best Practices

### 1. Error Handling
```python
try:
    result = await post_to_platform(listing)
except APIError as e:
    # Log error
    # Notify user
    # Retry with exponential backoff
    pass
```

### 2. Rate Limiting
```python
from time import sleep
from functools import wraps

def rate_limit(calls_per_minute):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Implement rate limiting logic
            await asyncio.sleep(60 / calls_per_minute)
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

### 3. Token Refresh
```python
async def refresh_token_if_needed(user):
    if token_expired(user.ebay_token):
        new_token = await refresh_ebay_token(user)
        user.ebay_token = encrypt(new_token)
        db.commit()
```

### 4. Webhook Handling
```python
@router.post("/webhooks/ebay")
async def ebay_webhook(request: Request, db: Session = Depends(get_db)):
    """Handle eBay order notifications"""
    data = await request.json()
    
    # Verify webhook signature
    # Process order
    # Create sale record
    # Calculate commission
    # Notify user
```

---

## Testing

### Sandbox Testing
1. Use sandbox/test environments when available
2. Test OAuth flows
3. Test listing creation
4. Test webhook handling

### Test Checklist
- [ ] OAuth flow works
- [ ] Listing posts successfully
- [ ] Photos upload correctly
- [ ] Prices format correctly
- [ ] Descriptions render properly
- [ ] Tokens refresh automatically
- [ ] Webhooks process correctly
- [ ] Error handling works
- [ ] Rate limiting prevents issues

---

## Production Deployment

1. **Switch to Production APIs**
   - Use production credentials
   - Update API endpoints
   - Configure production webhooks

2. **Security**
   - Encrypt all tokens
   - Use HTTPS only
   - Validate webhook signatures
   - Implement rate limiting

3. **Monitoring**
   - Log all API calls
   - Track success/failure rates
   - Monitor webhook reliability
   - Alert on errors

4. **Compliance**
   - Review each platform's Terms of Service
   - Ensure compliance with listing policies
   - Handle user data appropriately
   - Respect rate limits

---

## Support Contacts

- **eBay**: https://developer.ebay.com/support
- **Facebook**: https://developers.facebook.com/support
- **Poshmark**: https://poshmark.com/business
- **Mercari**: Research needed
- **Craigslist**: No official support for automation

---

## Next Steps

1. Register for developer accounts on each platform
2. Complete OAuth implementations
3. Test in sandbox environments
4. Implement webhook handlers
5. Add error handling and retry logic
6. Deploy to production
7. Monitor and iterate
