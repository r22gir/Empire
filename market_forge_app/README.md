# MarketForge App

Flutter mobile application for MarketForge reselling platform with integrated shipping features (ShipForge).

## Features

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

## Getting Started

### Prerequisites
- Flutter SDK (>=2.12.0 <3.0.0)
- Android Studio / Xcode for mobile development
- Backend API running (see backend/README.md)

### Installation

1. Install Flutter dependencies:
```bash
cd market_forge_app
flutter pub get
```

2. Configure API endpoint:
Edit `lib/services/shipping_service.dart` and update the `baseUrl`:
```dart
ShippingService({
  this.baseUrl = 'https://your-api-domain.com', // Update this
  ...
})
```

3. Run the app:
```bash
flutter run
```

## Project Structure

```
lib/
├── main.dart                     # App entry point with navigation
├── models/
│   └── shipment.dart            # Data models for shipping
├── services/
│   ├── shipping_service.dart    # API client for shipping endpoints
│   └── deep_link_service.dart   # Deep linking handler
├── providers/
│   └── shipping_provider.dart   # State management for shipping
├── screens/
│   ├── shipping_screen.dart     # Main shipping hub
│   └── shipping/
│       ├── create_shipment_screen.dart
│       ├── rate_comparison_screen.dart
│       ├── label_preview_screen.dart
│       └── shipment_history_screen.dart
└── widgets/
    └── shipping/
        ├── address_form.dart
        ├── package_dimensions.dart
        └── rate_card.dart
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

The app connects to the backend API for shipping operations:

- `POST /shipping/rates` - Get shipping rates
- `POST /shipping/labels` - Purchase label
- `GET /shipping/labels/{id}` - Get label details
- `GET /shipping/track/{tracking}` - Track shipment
- `GET /shipping/history` - Get shipment history

## Dependencies

Key dependencies:
- `provider` - State management
- `http` - API communication
- `printing` - Print labels from device
- `image_gallery_saver` - Save labels to gallery
- `share_plus` - Share label files
- `uni_links` - Deep linking support
- `qr_flutter` - QR code display

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

Run tests:
```bash
flutter test
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

## License

Copyright © 2026 EmpireBox. All rights reserved.
