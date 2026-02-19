# EmpireBox Website - Next.js

Modern, responsive website for EmpireBox built with Next.js 15, TypeScript, and Tailwind CSS. Includes Setup Portal for hardware bundle activation, pre-orders, and marketing pages.

## Features

- ⚡️ Next.js 15 with App Router (Security Patched)
- 🎨 Tailwind CSS for styling
- 🎭 Framer Motion for animations
- 📱 Fully responsive design
- ♿️ SEO optimized
- 🚀 Fast page loads
- 🎯 TypeScript for type safety
- 🔒 Security vulnerabilities addressed
- 📦 Hardware bundle showcase and pre-orders
- 🔑 License key validation and activation
- 📲 QR code scanning support
- 📱 Device detection (Android/iOS/Desktop)
- 💼 Solana wallet setup guide

## Getting Started

### Prerequisites

- Node.js 18+ installed
- npm or yarn package manager

### Installation

1. Navigate to the nextjs directory:
```bash
cd website/nextjs
```

2. Install dependencies:
```bash
npm install
```

3. Set environment variables:
```bash
# Create .env.local file
NEXT_PUBLIC_API_URL=http://localhost:8000
```

4. Run the development server:
```bash
npm run dev
```

5. Open [http://localhost:3000](http://localhost:3000) in your browser

## Project Structure

```
nextjs/
├── src/
│   ├── app/                    # Next.js App Router pages
│   │   ├── layout.tsx          # Root layout
│   │   ├── page.tsx            # Home page
│   │   ├── about/              # About page
│   │   ├── pricing/            # Pricing page
│   │   ├── faq/                # FAQ page
│   │   ├── privacy/            # Privacy Policy
│   │   ├── terms/              # Terms of Service
│   │   ├── refund-policy/      # Refund Policy
│   │   ├── contact/            # Contact page
│   │   ├── setup/              # Setup portal pages
│   │   │   ├── page.tsx        # Landing page with QR scanner
│   │   │   └── [licenseKey]/   # Step-by-step setup flow
│   │   └── bundles/            # Hardware bundles showcase
│   ├── components/             # React components
│   │   ├── Navbar.tsx
│   │   ├── Hero.tsx
│   │   ├── Features.tsx
│   │   ├── Testimonials.tsx
│   │   ├── HowItWorks.tsx
│   │   ├── Pricing.tsx
│   │   ├── FAQ.tsx
│   │   ├── CTA.tsx
│   │   ├── Footer.tsx
│   │   ├── EmailForm.tsx
│   │   ├── LegalPageLayout.tsx
│   │   ├── setup/              # Setup flow components
│   │   │   ├── DeviceDetector.tsx
│   │   │   ├── SetupProgress.tsx
│   │   │   ├── AppDownloadButtons.tsx
│   │   │   ├── WalletSetupGuide.tsx
│   │   │   └── LicenseActivation.tsx
│   │   └── bundles/            # Bundle components
│   │       ├── BundleCard.tsx
│   │       └── PreOrderForm.tsx
│   └── lib/                    # Utilities and constants
│       ├── constants.ts        # App-wide constants
│       └── api.ts              # API client
└── public/                     # Static assets
```

## Pages

### Marketing Pages
- `/` - Home page
- `/about` - About EmpireBox
- `/pricing` - Subscription pricing
- `/faq` - Frequently asked questions

### Legal Pages (Stripe-Compliant)
- `/privacy` - Privacy Policy
- `/terms` - Terms of Service
- `/refund-policy` - Refund Policy
- `/contact` - Contact form and information

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
- Primary: `#0066FF`
- Secondary: `#FF6600`

Edit `tailwind.config.js` to customize:

```js
colors: {
  primary: {
    DEFAULT: '#0066FF',
    dark: '#0052CC',
  },
  secondary: {
    DEFAULT: '#FF6600',
    dark: '#E55A00',
  },
}
```

## Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run start` - Start production server
- `npm run lint` - Run ESLint

## Building for Production

```bash
npm run build
npm run start
```

## Deployment

### Deploy to Vercel (Recommended)

1. Push your code to GitHub
2. Go to [vercel.com](https://vercel.com)
3. Import your repository
4. Vercel will auto-detect Next.js and deploy

Or use the Vercel CLI:

```bash
npm i -g vercel
vercel
```

### Deploy to Other Platforms

Build the static export:

```bash
npm run build
```

The output can be deployed to any static hosting service (Netlify, AWS S3, etc.)

## Environment Variables

Create a `.env.local` file:

```
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_GA_ID=your_google_analytics_id
```

## QR Code Format

QR codes should link to: `https://empirebox.store/setup/EMPIRE-XXXX-XXXX-XXXX`

## Customization

### Content

Edit `src/lib/constants.ts` to update:
- Pricing tiers
- FAQ questions
- Features list
- Testimonials
- How It Works steps

### Components

All components are in `src/components/`. They use Framer Motion for animations and Tailwind CSS for styling.

## Performance

- Uses Next.js 15 App Router for optimal performance
- Automatic code splitting
- Image optimization
- Font optimization with next/font

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers

## License

Proprietary - EmpireBox © 2026

## Support

For questions or issues:
- Email: support@empirebox.store
- Website: https://empirebox.store