# MarketForge App

Flutter mobile application for MarketForge reselling platform - the flagship product of EmpireBox. Post to multiple marketplaces with a single workflow, integrated shipping (ShipForge), and AI-powered features.

## Features

### Multi-Platform Listing
- 📸 **Camera Integration**: Capture or select up to 10 photos per listing
- ✍️ **Product Details**: Enter title, price, description, category, condition, and location
- 🤖 **AI-Powered**: Get AI suggestions for titles, descriptions, categories, and pricing
- 🏪 **Multi-Marketplace**: Post to multiple marketplaces simultaneously
- 📊 **Dashboard**: View all your listings and their status at a glance
- 🔔 **Status Tracking**: Track posting success/failure per marketplace
- ⚙️ **Settings**: Manage account, subscription, and marketplace connections

### Shipping Integration (ShipForge)
- **Compare Rates**: Get real-time shipping rates from USPS, FedEx, and UPS
- **Purchase Labels**: Buy shipping labels directly in the app
- **Print Labels**: Print labels from your phone using AirPrint (iOS) or Android Print Service
- **Email Labels**: Email label PDFs to yourself or others
- **Save Labels**: Save labels to your photo gallery
- **Track Shipments**: Real-time tracking for all your shipments
- **Shipment History**: View all past shipments with filtering options

### Deep Linking
- Handle setup portal deep links from empirebox.store
- Automatic license activation flow

## Implementation Status

### ✅ Fully Implemented
- **Facebook Marketplace**: Complete implementation with OAuth, posting, status checking
- **All Screens**: Home, Camera, Product Form, Marketplace Picker, Preview, Status, Settings
- **Shipping**: Rate comparison, label purchase, printing, tracking
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
- Android Studio / Xcode for mobile development
- Backend API running (see backend/README.md)

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

3. **Configure API endpoint**
   Edit `lib/services/shipping_service.dart` and update the `baseUrl`:
   ```dart
   ShippingService({
     this.baseUrl = 'https://your-api-domain.com', // Update this
     ...
   })
   ```

4. **Run the app**
   ```bash
   flutter run
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
│   │   ├── shipment.dart              # Shipping data models
│   │   └── user.dart                  # User/subscription model
│   ├── screens/
│   │   ├── home_screen.dart           # Dashboard with recent listings
│   │   ├── camera_screen.dart         # Camera capture + gallery picker
│   │   ├── product_form_screen.dart   # Title, price, description, category
│   │   ├── marketplace_picker_screen.dart  # Select target marketplaces
│   │   ├── listing_preview_screen.dart     # Review before posting
│   │   ├── listing_status_screen.dart      # Success/failure per marketplace
│   │   ├── settings_screen.dart       # Account, subscription, API keys
│   │   ├── shipping_screen.dart       # Main shipping hub
│   │   └── shipping/
│   │       ├── create_shipment_screen.dart
│   │       ├── rate_comparison_screen.dart
│   │       ├── label_preview_screen.dart
│   │       └── shipment_history_screen.dart
│   ├── services/
│   │   ├── api_service.dart           # Base API client
│   │   ├── shipping_service.dart      # API client for shipping endpoints
│   │   ├── deep_link_service.dart     # Deep linking handler
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
│   │   ├── status_badge.dart          # Posted/Pending/Failed badge
│   │   └── shipping/
│   │       ├── address_form.dart
│   │       ├── package_dimensions.dart
│   │       └── rate_card.dart
│   └── providers/
│       ├── product_provider.dart      # State management for products
│       ├── listing_provider.dart      # State for active listing flow
│       ├── shipping_provider.dart     # State management for shipping
│       └── user_provider.dart         # User/auth state
├── pubspec.yaml                       # Dependencies
└── README.md                          # This file
```

## Shipping Features

### Creating a Shipment

1. Tap "New Shipment" button
2. Fill in FROM address (saved for convenience)
3. Fill in TO address
4. Enter package dimensions and weight
5. Compare rates from different carriers
6. Select the best rate
7. Purchase and receive your label

### Printing Labels

The app supports multiple printing methods:
- **iOS**: AirPrint to any compatible printer
- **Android**: Android Print Service
- **Email**: Send PDF to yourself and print from computer
- **Save**: Save image to gallery for later printing

### Supported Carriers

- **USPS**: First Class, Priority Mail, Priority Express
- **UPS**: Ground, 3 Day Select, 2nd Day Air, Next Day Air
- **FedEx**: Ground, Home Delivery, 2Day, Overnight

## Deep Linking

The app can be opened from web links:

```
empirebox.store/setup/EMPIRE-XXXX-XXXX-XXXX
```

This will open the app and prompt the user to activate their license.

### Configuring Deep Links

#### iOS (Info.plist)
```xml
<key>CFBundleURLTypes</key>
<array>
  <dict>
    <key>CFBundleURLSchemes</key>
    <array>
      <string>marketforge</string>
    </array>
  </dict>
</array>
```

#### Android (AndroidManifest.xml)
```xml
<intent-filter>
  <action android:name="android.intent.action.VIEW" />
  <category android:name="android.intent.category.DEFAULT" />
  <category android:name="android.intent.category.BROWSABLE" />
  <data
    android:scheme="https"
    android:host="empirebox.store"
    android:pathPrefix="/setup" />
</intent-filter>
```

## API Integration

The app connects to the backend API for various operations:

### Shipping Endpoints
- `POST /shipping/rates` - Get shipping rates
- `POST /shipping/labels` - Purchase label
- `GET /shipping/labels/{id}` - Get label details
- `GET /shipping/track/{tracking}` - Track shipment
- `GET /shipping/history` - Get shipment history

### Listing Endpoints
- `GET /listings` - Get user listings
- `POST /listings` - Create listing
- `PUT /listings/{id}` - Update listing
- `POST /listings/{id}/publish` - Publish to marketplaces

## Dependencies

Key dependencies:
- `provider` - State management
- `http` - API communication
- `printing` - Print labels from device
- `image_gallery_saver` - Save labels to gallery
- `share_plus` - Share label files
- `uni_links` - Deep linking support
- `qr_flutter` - QR code display
- `camera` - Camera access
- `image_picker` - Gallery photo selection
- `shared_preferences` - Local data persistence
- `cached_network_image` - Image caching

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

## Theme & Design

- **Dark Theme**: Primary color is deep purple
- **Material 3**: Modern design language
- **Status Colors**:
  - Green: Success/Posted
  - Orange: Pending
  - Red: Failed
  - Blue: Sold
  - Grey: Deleted

## Development

### Running in Test Mode

The shipping service uses test mode by default with simulated rates and tracking numbers. No real charges are made.

To use production mode:
1. Update backend to use real EasyPost API key
2. Change `baseUrl` in shipping service to production API

### Adding New Features

1. Create models in `lib/models/`
2. Add services in `lib/services/`
3. Create providers in `lib/providers/` for state management
4. Build UI in `lib/screens/` and `lib/widgets/`

## Testing

```bash
# Run tests
flutter test

# Run with coverage
flutter test --coverage
```

## Building for Production

### Android
```bash
flutter build apk --release
```

### iOS
```bash
flutter build ios --release
```

## Troubleshooting

### Label printing not working
- Ensure printer is connected and supports AirPrint (iOS) or Android Print Service
- Try emailing label PDF as alternative

### Deep links not working
- Verify AndroidManifest.xml / Info.plist configuration
- Check that app is set as default handler for empirebox.store domain

### API connection errors
- Verify backend API is running
- Check baseUrl in shipping_service.dart
- Ensure device/emulator can reach the API (use actual IP, not localhost)

## Roadmap

### Q1 2026
- ✅ Complete Flutter app skeleton
- ✅ Shipping integration (ShipForge)
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

## License

Copyright © 2026 EmpireBox. All rights reserved.

## Support

For issues and questions:
- Email: support@empirebox.store
- GitHub Issues: https://github.com/r22gir/Empire/issues