# Setup Flow Documentation

## Overview

The EmpireBox setup flow guides customers from unboxing their hardware bundle to making their first sale. The entire process takes 10-15 minutes and is designed to be mobile-first, friendly, and foolproof.

## Flow Diagram

```
┌─────────────┐
│   Unbox     │
│   Package   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Find Quick  │
│ Start Card  │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ Scan QR Code│  ← Opens browser
└──────┬──────┘
       │
       ▼
┌──────────────────────────────────────────┐
│  empirebox.store/setup/EMPIRE-XXX...     │
└──────┬───────────────────────────────────┘
       │
       ▼
┌─────────────────────┐
│ License Validation  │  ← Backend API call
└──────┬──────────────┘
       │
       ▼
┌─────────────────────┐
│ Device Detection    │  ← Android/iOS/Desktop
└──────┬──────────────┘
       │
       ├───────────────────────┐
       │                       │
       ▼                       ▼
  ┌─────────┐         ┌──────────────┐
  │ Android │         │     iOS      │
  │ Detected│         │   Detected   │
  └────┬────┘         └──────┬───────┘
       │                     │
       └──────────┬──────────┘
                  │
                  ▼
        ┌─────────────────┐
        │  STEP 1:        │
        │  Download App   │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  User clicks    │
        │  "Downloaded"   │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  STEP 2:        │
        │  Wallet Setup   │  ← Only for Seeker bundles
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  User creates   │
        │  wallet or skips│
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  STEP 3:        │
        │  Activate       │
        │  License        │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  API Call:      │
        │  POST /activate │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  STEP 4:        │
        │  Success! 🎉    │
        └────────┬────────┘
                 │
                 ▼
        ┌─────────────────┐
        │  Deep Link to   │
        │  App            │
        └─────────────────┘
```

---

## Detailed Step-by-Step

### Pre-Setup: Unboxing

**Customer Experience:**
1. Receives package from shipping carrier
2. Opens outer shipping box
3. Sees premium product box (branded for Pro/Empire)
4. Opens product box
5. **First item visible**: Quick Start Card in protective sleeve

**Quick Start Card Text:**
```
📱 Welcome to EmpireBox!

Follow these steps to activate:
1. Scan this QR code
2. Follow the on-screen instructions
3. Start selling in 10 minutes!

[QR CODE]

License: EMPIRE-XXXX-XXXX-XXXX
```

**Important Notes:**
- QR code should be LARGE and centered
- Instructions should be minimal (details are in the web flow)
- License key visible for manual entry if QR scan fails

---

### Step 1: Scan QR Code

**Action**: Customer scans QR code with phone camera

**QR Code URL**: `https://empirebox.store/setup/EMPIRE-XXXX-XXXX-XXXX`

**What Happens:**
1. Phone camera detects QR code
2. Shows notification: "Open empirebox.store"
3. Customer taps notification
4. Browser opens to setup portal

**Error Handling:**
- If QR code won't scan: Provide manual URL entry option
- If customer doesn't have QR scanner: Instructions to type URL manually

---

### Step 2: License Validation

**Backend Process** (invisible to user):

```javascript
// Frontend makes API call
GET /licenses/EMPIRE-XXXX-XXXX-XXXX/validate

// Response
{
  "valid": true,
  "plan": "pro",
  "duration_months": 12,
  "hardware_bundle": "seeker_pro",
  "status": "pending"
}
```

**UI States:**

**Loading State:**
```
┌────────────────────────────────┐
│   🔄 Validating License...     │
└────────────────────────────────┘
```

**Success State:**
- Proceed to device detection

**Error States:**

1. **Invalid License**:
```
┌────────────────────────────────────────┐
│   ❌ Invalid License Key                │
│                                         │
│   This license key doesn't exist.      │
│   Please check the key on your card.   │
│                                         │
│   [Try Again] [Contact Support]        │
└────────────────────────────────────────┘
```

2. **Already Activated**:
```
┌────────────────────────────────────────┐
│   ⚠️  License Already Activated         │
│                                         │
│   This license was activated on:       │
│   January 15, 2026                     │
│                                         │
│   [Contact Support if this is wrong]   │
└────────────────────────────────────────┘
```

3. **Network Error**:
```
┌────────────────────────────────────────┐
│   📶 Connection Error                   │
│                                         │
│   Please check your internet           │
│   connection and try again.            │
│                                         │
│   [Retry]                               │
└────────────────────────────────────────┘
```

---

### Step 3: Device Detection

**Purpose**: Show appropriate app download options

**Detection Logic**:
```javascript
const userAgent = navigator.userAgent.toLowerCase();

if (/android/.test(userAgent)) {
  deviceType = 'android';
} else if (/iphone|ipad|ipod/.test(userAgent)) {
  deviceType = 'ios';
} else {
  deviceType = 'desktop';
}
```

**UI Adaptation:**
- **Android**: Show Play Store button prominently
- **iOS**: Show App Store button prominently
- **Desktop**: Show both + web app option

---

### Step 4: Download MarketForge App

**UI Layout:**

```
┌──────────────────────────────────────────────┐
│   📱 Step 1 of 4: Download MarketForge        │
├──────────────────────────────────────────────┤
│                                               │
│   Get the MarketForge app to manage your     │
│   listings, track sales, and grow your       │
│   reselling business.                         │
│                                               │
│   ┌──────────────────────────────────────┐  │
│   │  📱 Download from Play Store         │  │
│   │                                      │  │
│   │  [Large Button]                      │  │
│   └──────────────────────────────────────┘  │
│                                               │
│   OR                                          │
│                                               │
│   ┌──────────────────────────────────────┐  │
│   │  🌐 Open Web App                     │  │
│   └──────────────────────────────────────┘  │
│                                               │
│   ─────────────────────────────────────────  │
│                                               │
│   ✓ I've downloaded the app                  │
│   [Continue to Next Step]                    │
│                                               │
└──────────────────────────────────────────────┘
```

**Button Actions:**
- Play Store: Opens `market://details?id=com.empirebox.marketforge`
- App Store: Opens `https://apps.apple.com/app/marketforge`
- Web App: Opens `https://app.empirebox.store`

**Progress Indicator**: Shows user is on step 1 of 4

---

### Step 5: Wallet Setup (Seeker Only)

**Conditional**: Only shown if `hardware_bundle` includes "seeker"

**UI Layout:**

```
┌──────────────────────────────────────────────┐
│   💳 Step 2 of 4: Create Your Wallet         │
├──────────────────────────────────────────────┤
│                                               │
│   Your Solana Seeker has a built-in          │
│   hardware wallet (Seed Vault) for           │
│   ultimate crypto security.                   │
│                                               │
│   ┌──────────────────────────────────────┐  │
│   │  1. Open Seed Vault app               │  │
│   │  2. Tap "Create New Wallet"           │  │
│   │  3. Write down seed phrase on paper   │  │
│   │  4. Verify seed phrase                │  │
│   └──────────────────────────────────────┘  │
│                                               │
│   ⚠️  IMPORTANT: Write down your seed         │
│   phrase! It's the ONLY way to recover       │
│   your wallet if you lose your phone.        │
│                                               │
│   Never share it with anyone.                │
│   Never store it digitally.                  │
│                                               │
│   [Wallet Created ✓] [Skip - No Crypto]     │
│                                               │
└──────────────────────────────────────────────┘
```

**Skip Option**: For users who don't want to use crypto features

**Detailed Guide**: Expandable section with step-by-step screenshots

---

### Step 6: Activate License

**UI Layout:**

```
┌──────────────────────────────────────────────┐
│   ⭐ Step 3 of 4: Activate Subscription       │
├──────────────────────────────────────────────┤
│                                               │
│   What's included in your subscription:      │
│                                               │
│   ✓ MarketForge Pro (12 months)             │
│   ✓ Unlimited listings                       │
│   ✓ AI photo enhancement                     │
│   ✓ Multi-marketplace integration            │
│   ✓ Advanced analytics                       │
│   ✓ Priority support                         │
│                                               │
│   ─────────────────────────────────────────  │
│                                               │
│   Value: $708                                │
│   You paid: $0 (included with bundle!)       │
│                                               │
│   ─────────────────────────────────────────  │
│                                               │
│   [🎉 Activate Now]                          │
│                                               │
│   By activating, you agree to Terms of       │
│   Service and Privacy Policy                 │
│                                               │
└──────────────────────────────────────────────┘
```

**On Click**:
1. Show loading spinner
2. Make API call: `POST /licenses/{key}/activate`
3. Create user account (or link to existing)
4. Enable subscription features in app

**API Request:**
```javascript
POST /licenses/EMPIRE-XXXX-XXXX-XXXX/activate
{
  "user_id": "generated_or_existing_user_id"
}
```

**API Response:**
```javascript
{
  "success": true,
  "message": "License activated successfully",
  "subscription_details": {
    "plan": "pro",
    "expires_at": "2027-02-17T00:00:00Z",
    "features": [...]
  }
}
```

---

### Step 7: Success! 🎉

**UI Layout:**

```
┌──────────────────────────────────────────────┐
│         🎊 You're All Set! 🎊                 │
├──────────────────────────────────────────────┤
│                                               │
│   Your EmpireBox is ready to start making    │
│   you money!                                  │
│                                               │
│   Next steps:                                 │
│                                               │
│   ✅ Open MarketForge app                     │
│   ✅ Complete quick tutorial (3 min)          │
│   ✅ Connect your first marketplace           │
│   ✅ Create your first listing                │
│                                               │
│   ─────────────────────────────────────────  │
│                                               │
│   [🚀 Open MarketForge App]                  │
│                                               │
│   Resources:                                  │
│   • Watch tutorial videos                    │
│   • Read beginner's guide                    │
│   • Join our community                       │
│   • Contact support                          │
│                                               │
└──────────────────────────────────────────────┘
```

**Open App Button**: 
- Uses deep link: `marketforge://app/home`
- Fallbacks to app store if app not installed

**Confetti Animation**: Show celebratory animation when page loads

---

## Mobile Responsiveness

All screens are designed **mobile-first**:

### Design Principles
- Large touch targets (min 44px x 44px)
- Readable font sizes (min 16px body text)
- Single column layout
- Generous padding and spacing
- Progress indicator always visible
- Back button to return to previous step

### Breakpoints
- **Mobile**: < 768px (primary focus)
- **Tablet**: 768px - 1024px
- **Desktop**: > 1024px

---

## Error Handling

### Common Errors & Solutions

1. **QR Code Won't Scan**
   - Solution: Provide manual URL entry
   - Fallback: Text license key entry

2. **Internet Connection Lost**
   - Solution: Cache progress, resume when online
   - Show friendly "Check your connection" message

3. **App Not Installing**
   - Solution: Provide troubleshooting guide
   - Offer web app as alternative

4. **License Already Used**
   - Solution: Contact support flow
   - Check if user owns the license (show account email)

---

## Analytics & Tracking

### Events to Track

```javascript
// Step completion
analytics.track('Setup Step Completed', {
  step: 1, // 1-4
  step_name: 'Download App',
  license_key: 'EMPIRE-XXX...',
  bundle_type: 'seeker_pro'
});

// Drop-off points
analytics.track('Setup Abandoned', {
  last_step: 2,
  bundle_type: 'seeker_pro'
});

// Full completion
analytics.track('Setup Completed', {
  duration_seconds: 420,
  bundle_type: 'seeker_pro'
});
```

### Metrics to Monitor
- **Completion Rate**: % who finish all steps
- **Time to Complete**: Average duration
- **Drop-off Points**: Where users abandon
- **Error Rate**: Frequency of errors

**Target KPIs**:
- Completion rate: > 85%
- Average time: < 15 minutes
- Drop-off on any step: < 5%

---

## A/B Testing Opportunities

### Test 1: Video vs. Text Instructions
- **Variant A**: Text-based steps
- **Variant B**: Video walkthrough
- **Metric**: Completion rate

### Test 2: Wallet Setup Optional vs. Required
- **Variant A**: Required for all Seeker users
- **Variant B**: Optional with "Skip" button
- **Metric**: Completion rate + crypto adoption

### Test 3: Progress Indicator Style
- **Variant A**: Numbered steps (1/4, 2/4, etc.)
- **Variant B**: Progress bar
- **Metric**: User preference survey

---

## Localization (Future)

Currently English-only, but designed for easy translation:

### Text Strings
All text stored in separate files:
- `en-US.json` - English (US)
- `es-ES.json` - Spanish
- `fr-FR.json` - French

### Date/Time Formats
Use locale-aware formatting:
```javascript
new Date().toLocaleDateString('en-US'); // 2/17/2026
new Date().toLocaleDateString('es-ES'); // 17/2/2026
```

---

## Support & Help

### In-Flow Help
- **Help icon** (?) in top-right of each step
- Clicking opens modal with detailed instructions
- Option to chat with support

### Post-Setup Support
- **Email**: support@empirebox.store
- **Phone**: 1-800-EMPIRE-BOX
- **Chat**: In-app support widget
- **Knowledge Base**: empirebox.store/help

---

*Document Version: 1.0*
*Last Updated: 2026-02-17*
*Owner: EmpireBox Product Team*
