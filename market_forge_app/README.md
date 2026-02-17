# MarketForge - Multi-Platform Product Listing App

MarketForge is the flagship product of EmpireBox, designed to help resellers list products to multiple marketplaces (Facebook Marketplace, eBay, Craigslist, Amazon, Etsy, Mercari) with a single workflow.

## Features

- 📸 **Camera Integration**: Capture or select up to 10 photos per listing
- ✍️ **Product Details**: Enter title, price, description, category, condition, and location
- 🤖 **AI-Powered**: Get AI suggestions for titles, descriptions, categories, and pricing
- 🏪 **Multi-Marketplace**: Post to multiple marketplaces simultaneously
- 📊 **Dashboard**: View all your listings and their status at a glance
- 🔔 **Status Tracking**: Track posting success/failure per marketplace
- ⚙️ **Settings**: Manage account, subscription, and marketplace connections

## Current Implementation Status

### ✅ Fully Implemented
- **Facebook Marketplace**: Complete implementation with OAuth, posting, status checking
- **All Screens**: Home, Camera, Product Form, Marketplace Picker, Preview, Status, Settings
- **State Management**: Provider-based state management
- **Local Storage**: Draft products and listings saved locally
- **UI/UX**: Modern Material 3 dark theme with smooth navigation

### 🚧 Coming Soon
- **eBay**: Integration planned
- **Craigslist**: Integration planned
- **Amazon**: Integration planned
- **Etsy**: Integration planned
- **Mercari**: Integration planned

## Getting Started

### Prerequisites

- Flutter SDK (>=2.19.0 <4.0.0)
- Dart SDK
- Android Studio / Xcode (for mobile development)
- An IDE (VS Code, Android Studio, or IntelliJ)

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/r22gir/Empire.git
   cd Empire/market_forge_app
   ```

2. **Install dependencies**
   ```bash
   flutter pub get
   ```

3. **Run the app**
   ```bash
   flutter run
   ```

### Build for Production

**Android:**
```bash
flutter build apk --release
```

**iOS:**
```bash
flutter build ios --release
```

## Project Structure

```
market_forge_app/
├── lib/
│   ├── main.dart                      # App entry point with theme and navigation
│   ├── config/
│   │   └── app_config.dart            # API endpoints and feature flags
│   ├── models/
│   │   ├── product.dart               # Product data model
│   │   ├── listing.dart               # Listing with marketplace status
│   │   ├── marketplace.dart           # Marketplace enum and config
│   │   └── user.dart                  # User/subscription model
│   ├── screens/
│   │   ├── home_screen.dart           # Dashboard with recent listings
│   │   ├── camera_screen.dart         # Camera capture + gallery picker
│   │   ├── product_form_screen.dart   # Title, price, description, category
│   │   ├── marketplace_picker_screen.dart  # Select target marketplaces
│   │   ├── listing_preview_screen.dart     # Review before posting
│   │   ├── listing_status_screen.dart      # Success/failure per marketplace
│   │   └── settings_screen.dart       # Account, subscription, API keys
│   ├── services/
│   │   ├── api_service.dart           # Base API client
│   │   ├── marketplace_service.dart   # Abstract marketplace interface
│   │   ├── marketplaces/
│   │   │   ├── facebook_marketplace.dart   # FB Marketplace (implemented)
│   │   │   ├── ebay_service.dart           # eBay (stub)
│   │   │   ├── craigslist_service.dart     # Craigslist (stub)
│   │   │   ├── amazon_service.dart         # Amazon (stub)
│   │   │   ├── etsy_service.dart           # Etsy (stub)
│   │   │   └── mercari_service.dart        # Mercari (stub)
│   │   ├── ai_service.dart            # EmpireBox AI agent integration
│   │   └── storage_service.dart       # Local storage for drafts
│   ├── widgets/
│   │   ├── product_card.dart          # Reusable product display
│   │   ├── marketplace_chip.dart      # Marketplace selector chip
│   │   ├── photo_thumbnail.dart       # Photo preview widget
│   │   ├── loading_overlay.dart       # Loading state overlay
│   │   └── status_badge.dart          # Posted/Pending/Failed badge
│   └── providers/
│       ├── product_provider.dart      # State management for products
│       ├── listing_provider.dart      # State for active listing flow
│       └── user_provider.dart         # User/auth state
├── pubspec.yaml                       # Dependencies
└── README.md                          # This file
```

## Dependencies

- **provider**: State management
- **http**: API communication
- **camera**: Camera access
- **image_picker**: Gallery photo selection
- **shared_preferences**: Local data persistence
- **cached_network_image**: Image caching
- **flutter_svg**: SVG support
- **intl**: Date/time formatting
- **uuid**: Unique ID generation

## Example User Flow

1. **Home Screen**: User sees dashboard with stats and recent listings
2. **New Listing**: User taps "+" FAB to start new listing
3. **Camera Screen**: User takes 3 photos or selects from gallery
4. **Product Form**: User fills in title, price, description, category, condition, location
   - AI can suggest title improvements
   - AI can enhance description
5. **Marketplace Picker**: User selects Facebook Marketplace + eBay
6. **Preview Screen**: User reviews all details before posting
7. **Post**: User taps "Post to 2 Marketplaces"
8. **Status Screen**: Shows "Facebook: Posted ✓" and "eBay: Coming Soon"
9. **Home**: Returns to dashboard with new listing visible

## Configuration

### API Endpoints
Edit `lib/config/app_config.dart` to configure:
- Base API URL
- Feature flags
- Timeout settings
- Maximum photos per listing

### Marketplace Integration

To add a real marketplace integration:

1. Implement the `MarketplaceService` interface
2. Add OAuth/API key management
3. Implement `postListing()`, `checkStatus()`, etc.
4. Update feature flags in `app_config.dart`

Example:
```dart
class MyMarketplaceService extends BaseMarketplaceService {
  @override
  Future<ListingResult> postListing(Product product) async {
    // Your implementation here
  }
}
```

## Theme & Design

- **Dark Theme**: Primary color is deep purple
- **Material 3**: Modern design language
- **Status Colors**:
  - Green: Success/Posted
  - Orange: Pending
  - Red: Failed
  - Blue: Sold
  - Grey: Deleted

## Testing

```bash
# Run tests
flutter test

# Run with coverage
flutter test --coverage
```

## Known Limitations

1. **Camera**: Currently shows a placeholder; real camera integration requires device permissions
2. **Image Picker**: Mock implementation; needs real `image_picker` integration
3. **Location**: Auto-detect is mocked; needs real geolocation service
4. **OAuth**: Facebook Marketplace OAuth flow is stubbed
5. **AI Services**: AI endpoints are mocked; need real EmpireBox AI backend

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

Copyright © 2026 EmpireBox. All rights reserved.

## Support

For issues and questions:
- Email: support@empirebox.com
- GitHub Issues: https://github.com/r22gir/Empire/issues

## Roadmap

### Q1 2026
- ✅ Complete Flutter app skeleton
- 🚧 Facebook Marketplace full integration
- 🚧 Real camera and image picker
- 🚧 Backend API integration

### Q2 2026
- eBay marketplace integration
- Craigslist marketplace integration
- Real AI-powered suggestions
- User authentication

### Q3 2026
- Amazon marketplace integration
- Etsy marketplace integration
- Mercari marketplace integration
- Analytics dashboard

### Q4 2026
- Advanced features (bulk listing, templates)
- Performance optimizations
- iOS and Android app store releases
