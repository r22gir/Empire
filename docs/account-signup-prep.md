# Empire Account Signup Prep

**Generated**: 2026-03-16
**Purpose**: Pre-filled guide for manual account signups. Complete each in order, then run `scripts/add-api-keys.sh`.

---

## Instagram Business
- **Signup URL**: https://business.instagram.com/getting-started
- **Business Name**: Empire Workroom
- **Category**: Home Decor / Interior Design / Custom Window Treatments
- **Email**: (use existing business email from .env or personal)
- **Phone**: ASK FOUNDER
- **What to fill**:
  1. Log in with personal Instagram account
  2. Go to Settings → Account → Switch to Professional Account
  3. Choose "Business" (not Creator)
  4. Select category: "Home Decor" or "Interior Design"
  5. Connect to Facebook Business Page (create one if needed)
  6. Go to https://developers.facebook.com → Create App → Business type
  7. Add Instagram Graph API product
  8. Generate long-lived access token
- **Expected .env var**: `INSTAGRAM_API_TOKEN`
- **After signup**: Add token to .env, restart backend. SocialForge Instagram features will activate.
- **Status**: READY FOR MANUAL SIGNUP

---

## Facebook Business Page
- **Signup URL**: https://www.facebook.com/pages/create
- **Business Name**: Empire Workroom
- **Category**: Home Decor / Interior Design
- **Email**: (same as Instagram)
- **Phone**: ASK FOUNDER
- **Address**: ASK FOUNDER
- **What to fill**:
  1. Create Page → Business or Brand
  2. Name: "Empire Workroom"
  3. Category: "Interior Designer" or "Home Decor"
  4. Add profile photo, cover photo (use brand assets)
  5. Go to https://developers.facebook.com
  6. Create App (if not done for Instagram)
  7. Add Pages API
  8. Generate Page Access Token (long-lived)
- **Expected .env var**: `FACEBOOK_PAGE_TOKEN`
- **After signup**: Add token to .env. SocialForge Facebook posting will activate.
- **Status**: READY FOR MANUAL SIGNUP

---

## Google Business Profile
- **Signup URL**: https://business.google.com/create
- **Business Name**: Empire Workroom
- **Category**: Window Treatment Store / Interior Designer
- **Email**: (Google account)
- **Phone**: ASK FOUNDER
- **Address**: ASK FOUNDER (physical business address required)
- **What to fill**:
  1. Search for your business or add new
  2. Business name: "Empire Workroom"
  3. Category: "Window Treatment Store" (primary), "Interior Designer" (secondary)
  4. Enter service area (if not storefront)
  5. Add phone number, website (studio.empirebox.store)
  6. Verify via postcard, phone, or email
  7. For API access: https://console.cloud.google.com → Enable "My Business" API
  8. Create API key or OAuth credentials
- **Expected .env var**: `GOOGLE_BUSINESS_API_KEY`
- **After signup**: Verification may take 5-14 days (postcard). API key works immediately.
- **Status**: READY FOR MANUAL SIGNUP

---

## Pinterest Business
- **Signup URL**: https://www.pinterest.com/business/create/
- **Business Name**: Empire Workroom
- **Category**: Home Decor
- **Email**: (business email)
- **What to fill**:
  1. Create business account (or convert personal)
  2. Business name: "Empire Workroom"
  3. Select "Home Decor" category
  4. Claim website: studio.empirebox.store
  5. Go to https://developers.pinterest.com
  6. Create App
  7. Generate API token
- **Expected .env var**: `PINTEREST_API_TOKEN`
- **After signup**: Add token. SocialForge Pinterest pinning will activate.
- **Status**: READY FOR MANUAL SIGNUP

---

## ShipStation
- **Signup URL**: https://www.shipstation.com/pricing/
- **Business Name**: Empire Workroom
- **Free Trial**: 30 days, no credit card required for trial
- **Email**: (business email)
- **What to fill**:
  1. Sign up for Starter plan ($9.99/mo) or free trial
  2. Business name: "Empire Workroom"
  3. Set up shipping origins (business address)
  4. Connect carriers (USPS, UPS, FedEx as needed)
  5. Go to Settings → Account → API Settings
  6. Generate API Key and API Secret
- **Expected .env vars**: `SHIPSTATION_API_KEY`, `SHIPSTATION_API_SECRET`
- **After signup**: Add both keys. ShipForge rate/label endpoints will use real rates.
- **Status**: READY FOR MANUAL SIGNUP

---

## Shippo (backup shipping)
- **Signup URL**: https://goshippo.com/
- **Business Name**: Empire Workroom
- **Free Tier**: 30 free shipments/month
- **Email**: (business email)
- **What to fill**:
  1. Sign up for free account
  2. Go to Settings → API → Generate Token
  3. Use "Test" token first, switch to "Live" when ready
- **Expected .env var**: `SHIPPO_API_TOKEN`
- **After signup**: Alternative to ShipStation. Add token to .env.
- **Status**: READY FOR MANUAL SIGNUP

---

## eBay Developer
- **Signup URL**: https://developer.ebay.com/signin
- **Business Name**: Empire Workroom
- **Email**: (eBay account email)
- **What to fill**:
  1. Sign in with eBay account
  2. Go to https://developer.ebay.com/my/keys
  3. Create Application (Production keys)
  4. App Name: "EmpireWorkroom"
  5. Note the App ID (Client ID), Cert ID, Dev ID
  6. Set OAuth redirect URI: https://api.empirebox.store/api/v1/marketplace/ebay/callback
  7. Request production access (may need eBay review)
- **Expected .env vars**: `EBAY_APP_ID`, `EBAY_CERT_ID`, `EBAY_DEV_ID`
- **After signup**: Add all 3 keys. MarketForge eBay integration will activate.
- **Status**: READY FOR MANUAL SIGNUP

---

## Etsy Developer
- **Signup URL**: https://www.etsy.com/developers/register
- **Business Name**: Empire Workroom
- **Email**: (Etsy account email)
- **What to fill**:
  1. Sign in with Etsy account
  2. Register as developer
  3. Create new App
  4. App name: "EmpireWorkroom"
  5. Description: "Inventory sync and listing management"
  6. Copy API Key (keystring)
- **Expected .env var**: `ETSY_API_KEY`
- **After signup**: Add key. MarketForge Etsy features will activate.
- **Status**: READY FOR MANUAL SIGNUP

---

## SendGrid
- **Signup URL**: https://signup.sendgrid.com/
- **Business Name**: Empire Workroom
- **Free Tier**: 100 emails/day forever
- **Email**: (business email)
- **What to fill**:
  1. Create account
  2. Verify email address
  3. Go to Settings → API Keys → Create API Key
  4. Give "Full Access" permissions
  5. Copy the API key (shown only once!)
  6. Set up Sender Authentication:
     - Settings → Sender Authentication → Single Sender Verification
     - Or domain authentication for studio.empirebox.store
- **Expected .env var**: `SENDGRID_API_KEY`
- **After signup**: Add key. All email endpoints (quote, invoice, receipt) will send real emails.
- **Status**: READY FOR MANUAL SIGNUP

---

## Twilio
- **Signup URL**: https://www.twilio.com/try-twilio
- **Business Name**: Empire Workroom
- **Free Trial**: $15 credit, no credit card required
- **Email**: (business email)
- **Phone**: ASK FOUNDER (for verification)
- **What to fill**:
  1. Create account, verify phone
  2. Get a Twilio phone number (free with trial)
  3. Note Account SID from dashboard
  4. Note Auth Token from dashboard
  5. Note your Twilio phone number
- **Expected .env vars**: `TWILIO_SID`, `TWILIO_AUTH_TOKEN`, `TWILIO_PHONE`
- **After signup**: Add all 3 values. SMS notifications will activate.
- **Status**: READY FOR MANUAL SIGNUP

---

## Quick Reference

| Service | Free Tier | Signup Time | Priority |
|---------|-----------|-------------|----------|
| SendGrid | 100/day | 5 min | HIGH (unlocks email) |
| ShipStation | 30-day trial | 5 min | HIGH (unlocks shipping) |
| eBay Developer | Free | 10 min | MEDIUM |
| Instagram/Facebook | Free | 15 min | MEDIUM |
| Google Business | Free | 5 min + verify | MEDIUM |
| Twilio | $15 credit | 5 min | LOW |
| Pinterest | Free | 5 min | LOW |
| Etsy | Free | 5 min | LOW |
| Shippo | 30 free/mo | 3 min | BACKUP |

**Total estimated time: 30-45 minutes**

After all signups, run: `~/empire-repo/scripts/add-api-keys.sh`
