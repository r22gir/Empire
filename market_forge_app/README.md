# MarketForge Mobile App

Flutter mobile application for creating marketplace listings across multiple platforms.

## Features

### Implemented ✅
- User authentication (login/register)
- Photo capture (camera + gallery)
- Listing creation form
- Multi-platform selection
- Dashboard with listing overview
- Pull-to-refresh
- Secure token storage

### Coming Soon 🔄
- Real-time sales notifications
- Earnings dashboard
- Marketplace account linking
- Order tracking
- Payout history
- Settings and profile management

## Prerequisites

- Flutter SDK 3.0 or higher
- Dart SDK 3.0 or higher
- Android Studio / Xcode
- Physical device or emulator

## Installation

1. **Install Flutter**
   
   Follow the official guide: https://flutter.dev/docs/get-started/install

2. **Clone the repository**
   ```bash
   git clone https://github.com/r22gir/Empire.git
   cd Empire/market_forge_app
   ```

3. **Get dependencies**
   ```bash
   flutter pub get
   ```

4. **Configure API endpoint**
   
   Edit `lib/services/api_service.dart` and update the `baseUrl`:
   
   ```dart
   // For Android emulator
   static const String baseUrl = 'http://10.0.2.2:8000';
   
   // For iOS simulator
   static const String baseUrl = 'http://localhost:8000';
   
   // For physical device (replace with your computer's IP)
   static const String baseUrl = 'http://192.168.1.XXX:8000';
   ```

5. **Run the app**
   ```bash
   flutter run
   ```

## Project Structure

```
lib/
├── main.dart                      # App entry point
├── models/
│   └── models.dart               # Data models (User, Listing, Sale)
├── screens/
│   ├── login_screen.dart         # Login/Register screen
│   ├── dashboard_screen.dart     # Main dashboard
│   └── create_listing_screen.dart # Create new listing
├── services/
│   └── api_service.dart          # Backend API integration
└── widgets/                       # Reusable UI components (future)
```

## Screens

### 1. Login/Register Screen
- Email/password authentication
- Toggle between login and register modes
- Form validation
- Error handling

### 2. Dashboard Screen
- View all user listings
- Pull-to-refresh
- Navigate to create listing
- See platform posting status
- Logout functionality

### 3. Create Listing Screen
- Photo capture (camera or gallery)
- Title, description, and price input
- Platform selection (checkboxes)
- Form validation
- Submit to backend

## Dependencies

```yaml
dependencies:
  flutter:
    sdk: flutter
  
  # UI
  cupertino_icons: ^1.0.6
  
  # State Management
  provider: ^6.1.1
  
  # Network
  http: ^1.1.0
  dio: ^5.4.0
  
  # Storage
  shared_preferences: ^2.2.2
  
  # Camera & Image
  image_picker: ^1.0.5
  camera: ^0.10.5+7
  
  # Forms
  flutter_form_builder: ^9.1.1
  
  # Authentication
  flutter_secure_storage: ^9.0.0
```

## Platform-Specific Configuration

### Android

**Minimum SDK**: 21 (Android 5.0)

Required permissions in `android/app/src/main/AndroidManifest.xml`:
```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
```

### iOS

**Minimum iOS**: 12.0

Required permissions in `ios/Runner/Info.plist`:
```xml
<key>NSCameraUsageDescription</key>
<string>We need camera access to take photos of products</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>We need photo library access to select product images</string>
```

## API Integration

The app communicates with the FastAPI backend using the `ApiService` class.

### Authentication Flow

1. User enters email and password
2. App sends credentials to `/auth/login` or `/auth/register`
3. Backend returns JWT token
4. Token is stored securely using `flutter_secure_storage`
5. Token is included in all subsequent requests

### Creating a Listing

1. User takes/selects photo
2. User fills in title, description, price
3. User selects platforms
4. App sends multipart form data to `/listings/`
5. Backend processes and saves listing
6. App navigates back to dashboard

## Development

### Running in Debug Mode
```bash
flutter run --debug
```

### Building for Release

**Android:**
```bash
flutter build apk --release
```

**iOS:**
```bash
flutter build ios --release
```

### Testing
```bash
flutter test
```

### Code Generation
```bash
flutter pub run build_runner build
```

## Troubleshooting

### Cannot connect to backend
- Verify backend is running
- Check `baseUrl` in `api_service.dart`
- For Android emulator, use `10.0.2.2` instead of `localhost`
- For physical device, use your computer's local IP address
- Ensure no firewall is blocking the connection

### Camera permission denied
- Check AndroidManifest.xml has camera permissions
- Check Info.plist has camera usage description
- Reinstall the app after adding permissions

### Build errors
- Run `flutter clean`
- Delete `pubspec.lock`
- Run `flutter pub get`
- Restart IDE

### Image picker not working
- Ensure camera permissions are granted
- Try using `ImageSource.gallery` instead of `ImageSource.camera`
- Check device camera app works independently

## Customization

### Changing App Name
1. Edit `android/app/src/main/AndroidManifest.xml`:
   ```xml
   android:label="YourAppName"
   ```

2. Edit `ios/Runner/Info.plist`:
   ```xml
   <key>CFBundleDisplayName</key>
   <string>YourAppName</string>
   ```

### Changing App Icon
Use the `flutter_launcher_icons` package:

1. Add to `pubspec.yaml`:
   ```yaml
   dev_dependencies:
     flutter_launcher_icons: ^0.13.1
   
   flutter_icons:
     android: true
     ios: true
     image_path: "assets/icon.png"
   ```

2. Run:
   ```bash
   flutter pub run flutter_launcher_icons
   ```

### Changing Theme Colors
Edit `lib/main.dart`:
```dart
theme: ThemeData(
  colorScheme: ColorScheme.fromSeed(seedColor: Colors.yourColor),
  useMaterial3: true,
),
```

## Future Enhancements

- [ ] Push notifications for sales
- [ ] In-app messaging with buyers
- [ ] Analytics dashboard
- [ ] Listing templates
- [ ] Bulk upload
- [ ] Price suggestions based on AI
- [ ] Auto-reposting for expired listings
- [ ] Multi-language support
- [ ] Dark mode
- [ ] Tablet optimization

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## License

See LICENSE file in the root directory.

## Support

For issues or questions:
1. Check the troubleshooting section
2. Review the SETUP_GUIDE.md
3. Open an issue on GitHub
