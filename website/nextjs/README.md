# EmpireBox Website

Next.js website for EmpireBox hardware bundles setup portal and pre-orders.

## Features

- **Setup Portal** (`/setup/[licenseKey]`): Guided setup flow for hardware bundle activation
- **Bundles Page** (`/bundles`): Hardware bundle showcase and pre-orders
- QR code scanning support
- Device detection (Android/iOS/Desktop)
- Wallet setup guide for Solana Seeker
- License key validation and activation
- Pre-order checkout integration

## Getting Started

1. Install dependencies:
```bash
npm install
```

2. Set environment variables:
```bash
# Create .env.local file
NEXT_PUBLIC_API_URL=http://localhost:8000
```

3. Run development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000)

## Pages

### Setup Portal
- `/setup` - Landing page with QR scanner
- `/setup/[licenseKey]` - Step-by-step setup flow

### Hardware Bundles
- `/bundles` - Bundle showcase and pre-orders

## Components

### Setup Components
- `DeviceDetector` - Detects user device type
- `SetupProgress` - Progress stepper
- `AppDownloadButtons` - Platform-specific download links
- `WalletSetupGuide` - Solana wallet creation guide
- `LicenseActivation` - License activation flow

### Bundle Components
- `BundleCard` - Individual bundle display
- `PreOrderForm` - Pre-order checkout form

## API Integration

The website connects to the FastAPI backend at `NEXT_PUBLIC_API_URL`.

Endpoints used:
- `GET /licenses/{key}/validate` - Validate license key
- `POST /licenses/{key}/activate` - Activate license
- `POST /preorders/` - Create pre-order

## Styling

Uses Tailwind CSS with custom EmpireBox theme colors:
- Empire Blue: `#1E40AF`
- Empire Orange: `#F97316`

## Build for Production

```bash
npm run build
npm start
```

## QR Code Format

QR codes should link to: `https://empirebox.store/setup/EMPIRE-XXXX-XXXX-XXXX`
