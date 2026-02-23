# MarketForge App Flow Diagram

## User Journey

```
┌─────────────────────────────────────────────────────────────┐
│                    MarketForge App Flow                     │
└─────────────────────────────────────────────────────────────┘

┌──────────────┐
│ Home Screen  │ ◄─── Entry point
│ (Dashboard)  │
│              │
│ • Stats      │
│ • Listings   │
│ • FAB (+)    │
└──────┬───────┘
       │ Tap FAB
       ▼
┌──────────────┐
│ Camera       │
│ Screen       │
│              │
│ • Capture    │
│ • Gallery    │
│ • Thumbnails │
└──────┬───────┘
       │ Continue (with photos)
       ▼
┌──────────────┐
│ Product Form │
│ Screen       │
│              │
│ • Title 🤖   │
│ • Price      │
│ • Category   │
│ • Condition  │
│ • Desc 🤖    │
│ • Location   │
└──────┬───────┘
       │ Continue
       ▼
┌──────────────┐
│ Marketplace  │
│ Picker       │
│              │
│ ☑ Facebook   │
│ ☐ eBay       │
│ ☐ Craigslist │
│ ☐ Amazon     │
│ ☐ Etsy       │
│ ☐ Mercari    │
└──────┬───────┘
       │ Continue
       ▼
┌──────────────┐
│ Preview      │
│ Screen       │
│              │
│ • Photos     │
│ • Details    │
│ • Markets    │
│ [Post Button]│
└──────┬───────┘
       │ Post
       ▼
┌──────────────┐
│ Status       │
│ Screen       │
│              │
│ ✓ Facebook   │
│ ⏳ eBay       │
│ ❌ Error?     │
└──────┬───────┘
       │ Done
       ▼
┌──────────────┐
│ Home Screen  │ ◄─── Back to dashboard
│ (Updated)    │
└──────────────┘
```

## Settings Access

```
Bottom Nav → Settings Tab
       │
       ▼
┌──────────────┐
│ Settings     │
│ Screen       │
│              │
│ • Profile    │
│ • Subscription
│ • Marketplace│
│   Connections│
│ • Preferences│
│ • About      │
│ • Sign Out   │
└──────────────┘
```

## State Management Flow

```
┌─────────────┐
│   Screen    │ ◄──────┐
└──────┬──────┘        │
       │               │
       │ Interacts     │ Notifies
       ▼               │
┌─────────────┐        │
│  Provider   │ ───────┘
└──────┬──────┘
       │
       │ Calls
       ▼
┌─────────────┐
│  Service    │
└──────┬──────┘
       │
       │ Accesses
       ▼
┌─────────────┐
│ API/Storage │
└─────────────┘
```

## Key Components

### Providers (State Management)
- **ProductProvider**: Draft products management
- **ListingProvider**: Active listing flow + history
- **UserProvider**: User auth + preferences

### Services (Business Logic)
- **ApiService**: HTTP client base
- **MarketplaceService**: Abstract interface
  - FacebookMarketplaceService ✅
  - EbayService 🚧
  - CraigslistService 🚧
  - AmazonService 🚧
  - EtsyService 🚧
  - MercariService 🚧
- **AiService**: AI suggestions
- **StorageService**: Local persistence

### Models (Data)
- **Product**: Product details
- **Listing**: Multi-marketplace listing
- **Marketplace**: Marketplace config
- **User**: User + subscription

### Widgets (UI Components)
- **ProductCard**: Product display
- **MarketplaceChip**: Marketplace selector
- **PhotoThumbnail**: Photo preview
- **LoadingOverlay**: Loading state
- **StatusBadge**: Status indicator

## Features by Screen

### Home Screen
- Dashboard with statistics
- Recent listings grid
- Pull-to-refresh
- FAB for new listing

### Camera Screen
- Live camera preview placeholder
- Capture button
- Gallery picker
- Photo thumbnails with delete
- Continue button

### Product Form
- All required fields
- AI title suggestions 🤖
- AI description enhancement ��
- Category dropdown
- Condition picker
- Auto-location detection

### Marketplace Picker
- Grid of all marketplaces
- Visual selection
- "Coming Soon" badges
- Connection status
- Multi-select support

### Preview Screen
- Photo carousel
- All details review
- Edit buttons for each section
- Post to N marketplaces button

### Status Screen
- Overall success indicator
- Per-marketplace status
- Error messages
- View on marketplace links
- Retry option

### Settings Screen
- User profile
- Subscription management
- Marketplace connections
- Preferences (notifications, location)
- About & support

## Color Scheme

```
Primary:    Deep Purple (#673AB7)
Secondary:  Deep Purple Accent
Background: Dark (#121212)
Surface:    Dark Grey (#1E1E1E)

Status Colors:
✓ Success:  Green
⏳ Pending: Orange
❌ Failed:  Red
💰 Sold:    Blue
```

## Navigation

### Bottom Navigation
- Home (Dashboard)
- New Listing (Camera)
- Settings

### Screen Stack
- Navigation uses standard push/pop
- Preview screen can edit and return
- Status screen clears stack on done
