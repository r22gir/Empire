# MarketForge Setup Guide

This guide will walk you through setting up the complete MarketForge application from scratch.

## Prerequisites

### Backend Requirements
- Python 3.8 or higher
- pip (Python package manager)
- Virtual environment tool (venv or virtualenv)

### Frontend Requirements
- Flutter SDK 3.0 or higher
- Android Studio (for Android development)
- Xcode (for iOS development, macOS only)
- A physical device or emulator

### External Services
- Stripe account (for payment processing)
- eBay Developer account (optional)
- Facebook Developer account (optional)
- Poshmark credentials (optional)
- Mercari credentials (optional)

## Step-by-Step Setup

### Part 1: Backend Setup (15 minutes)

1. **Clone the repository**
   ```bash
   git clone https://github.com/r22gir/Empire.git
   cd Empire/backend
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   
   # On macOS/Linux:
   source venv/bin/activate
   
   # On Windows:
   venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables**
   ```bash
   cp .env.example .env
   ```
   
   Edit `.env` and set the following:
   ```env
   # Required
   SECRET_KEY=your-random-secret-key-min-32-characters
   
   # Stripe (get from https://dashboard.stripe.com/apikeys)
   STRIPE_SECRET_KEY=sk_test_your_key_here
   STRIPE_WEBHOOK_SECRET=whsec_your_secret_here
   
   # Optional marketplace credentials (can be added later)
   EBAY_APP_ID=your_ebay_app_id
   FACEBOOK_APP_ID=your_facebook_app_id
   ```

5. **Initialize the database**
   ```bash
   # The database will be created automatically when you first run the server
   ```

6. **Run the backend server**
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

7. **Verify backend is running**
   - Open browser to http://localhost:8000
   - You should see: `{"message": "MarketForge API", "version": "1.0.0"}`
   - Visit http://localhost:8000/docs for interactive API documentation

### Part 2: Flutter App Setup (15 minutes)

1. **Install Flutter SDK**
   
   If you haven't installed Flutter yet:
   - Visit https://flutter.dev/docs/get-started/install
   - Follow instructions for your operating system
   - Run `flutter doctor` to verify installation

2. **Navigate to app directory**
   ```bash
   cd ../market_forge_app
   ```

3. **Get Flutter dependencies**
   ```bash
   flutter pub get
   ```

4. **Configure API endpoint**
   
   Edit `lib/services/api_service.dart`:
   ```dart
   // For Android emulator:
   static const String baseUrl = 'http://10.0.2.2:8000';
   
   // For iOS simulator:
   static const String baseUrl = 'http://localhost:8000';
   
   // For physical device (replace with your computer's IP):
   static const String baseUrl = 'http://192.168.1.XXX:8000';
   ```

5. **Run the app**
   ```bash
   # Check available devices
   flutter devices
   
   # Run on specific device
   flutter run -d <device-id>
   
   # Or just run (it will ask which device to use)
   flutter run
   ```

### Part 3: Testing the App (10 minutes)

1. **Create a test account**
   - Open the app
   - Click "Don't have an account? Register"
   - Enter email: test@example.com
   - Enter password: test123
   - Click "Register"

2. **Create your first listing**
   - Click the "New Listing" button
   - Tap "Tap to add photo" and select an image
   - Enter title: "Test Product"
   - Enter description: "This is a test listing"
   - Enter price: 10.00
   - Select one or more platforms (checkboxes)
   - Click "Post to All Selected Platforms"

3. **View your listings**
   - You should see your new listing in the dashboard
   - The listing is saved in the database
   - Platform posting will show "Not posted" until marketplace APIs are configured

## Part 4: Marketplace API Setup (Variable Time)

### eBay Setup

1. Register at https://developer.ebay.com
2. Create an application
3. Get your App ID, Cert ID, and Dev ID
4. Add to `.env`:
   ```env
   EBAY_APP_ID=your_app_id
   EBAY_CERT_ID=your_cert_id
   EBAY_DEV_ID=your_dev_id
   EBAY_OAUTH_REDIRECT_URI=http://localhost:8000/auth/ebay/callback
   ```
5. Implement OAuth flow in `backend/app/services/marketplace_service.py`

### Facebook Marketplace Setup

1. Register at https://developers.facebook.com
2. Create an app with Marketplace permissions
3. Add to `.env`:
   ```env
   FACEBOOK_APP_ID=your_app_id
   FACEBOOK_APP_SECRET=your_app_secret
   ```
4. Implement posting in `backend/app/services/marketplace_service.py`

### Stripe Setup

1. Create account at https://stripe.com
2. Get API keys from dashboard
3. Add webhook endpoint: `http://your-domain.com/webhooks/stripe`
4. Update `.env` with your keys

## Troubleshooting

### Backend Issues

**Error: ModuleNotFoundError**
- Make sure virtual environment is activated
- Run `pip install -r requirements.txt` again

**Error: Database locked**
- Stop any other instances of the server
- Delete `marketforge.db` and restart

**Error: Port 8000 already in use**
- Change port: `uvicorn app.main:app --reload --port 8001`
- Update Flutter app's `baseUrl` accordingly

### Flutter Issues

**Error: SDK version mismatch**
- Update Flutter: `flutter upgrade`
- Update packages: `flutter pub upgrade`

**Error: Cannot connect to backend**
- Verify backend is running
- Check `baseUrl` in `api_service.dart`
- For physical device, use your computer's local IP
- Ensure firewall allows connections on port 8000

**Error: Camera permission denied**
- Add permissions to AndroidManifest.xml (Android)
- Add permissions to Info.plist (iOS)

### Platform-Specific Permissions

**Android** (`android/app/src/main/AndroidManifest.xml`):
```xml
<uses-permission android:name="android.permission.CAMERA" />
<uses-permission android:name="android.permission.READ_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.WRITE_EXTERNAL_STORAGE" />
<uses-permission android:name="android.permission.INTERNET" />
```

**iOS** (`ios/Runner/Info.plist`):
```xml
<key>NSCameraUsageDescription</key>
<string>We need camera access to take photos of products</string>
<key>NSPhotoLibraryUsageDescription</key>
<string>We need photo library access to select product images</string>
```

## Next Steps

1. Complete marketplace API integrations
2. Test posting to live marketplaces (in sandbox/test mode)
3. Set up Stripe webhooks for sale notifications
4. Recruit beta testers
5. Monitor first real transaction
6. Iterate based on feedback

## Getting Help

- Check API documentation: http://localhost:8000/docs
- Review logs: Backend console output
- Flutter debugging: Use `flutter run --verbose`
- Open an issue on GitHub for bugs or feature requests

## Production Deployment

When ready for production:

1. **Backend**
   - Deploy to cloud (AWS, GCP, Heroku, DigitalOcean)
   - Use PostgreSQL instead of SQLite
   - Set up HTTPS with SSL certificate
   - Configure production environment variables
   - Set up monitoring and logging

2. **Flutter App**
   - Build release version: `flutter build apk` or `flutter build ios`
   - Submit to Google Play Store and/or Apple App Store
   - Update `baseUrl` to production API endpoint

3. **Stripe**
   - Switch to live API keys
   - Configure production webhooks
   - Test payment flow thoroughly

Good luck with your MarketForge MVP! 🚀
