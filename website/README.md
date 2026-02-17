# EmpireBox Website

This directory contains the EmpireBox website built with Next.js 14, including all Stripe-compliant legal pages required for merchant account approval.

## Structure

```
website/
├── nextjs/               # Next.js application
│   ├── src/
│   │   ├── app/         # App Router pages
│   │   │   ├── contact/
│   │   │   ├── pricing/
│   │   │   ├── privacy/
│   │   │   ├── refund-policy/
│   │   │   ├── terms/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx
│   │   │   └── globals.css
│   │   └── components/  # Reusable components
│   │       ├── Footer.tsx
│   │       └── LegalPageLayout.tsx
│   ├── package.json
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   └── next.config.js
└── static/              # Static HTML files
    └── index.html       # Simple static landing page
```

## Getting Started

### Prerequisites

- Node.js 18+ and npm

### Installation

1. Navigate to the Next.js directory:
```bash
cd website/nextjs
```

2. Install dependencies:
```bash
npm install
```

### Development

Run the development server:
```bash
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser.

### Building for Production

Build the application:
```bash
npm run build
```

Start the production server:
```bash
npm start
```

### Linting

Check code quality:
```bash
npm run lint
```

## Pages

### Legal Pages (Stripe-Compliant)

All legal pages are accessible and include all required disclosures for Stripe merchant account approval:

- **Privacy Policy** (`/privacy`) - GDPR and CCPA compliant privacy policy
- **Terms of Service** (`/terms`) - Complete terms with subscription and commission details
- **Refund Policy** (`/refund-policy`) - Clear refund and cancellation policy
- **Contact** (`/contact`) - Contact form and business information

### Other Pages

- **Home** (`/`) - Landing page
- **Pricing** (`/pricing`) - Subscription plans with Stripe-required disclosures

## Important Notes

### Placeholders

Before deploying or applying for Stripe, replace these placeholders with actual information:

- `[YOUR BUSINESS ADDRESS]` - Replace with your actual physical business address
- `[CITY, STATE ZIP]` - Replace with your city, state, and ZIP code
- `[YOUR STATE]` - Replace with your state for governing law

### Stripe Requirements

All pages meet Stripe's requirements:
- ✅ Privacy Policy with payment processor disclosure
- ✅ Terms of Service with auto-renewal disclosure
- ✅ Refund Policy with clear timeframes
- ✅ Contact information with physical address
- ✅ Pricing transparency
- ✅ Legal links in footer on all pages

See `docs/STRIPE_COMPLIANCE_CHECKLIST.md` for the complete checklist.

## Deployment

### Vercel (Recommended)

1. Connect your GitHub repository to Vercel
2. Set root directory to `website/nextjs`
3. Vercel will auto-detect Next.js and deploy

### Other Platforms

The app can be deployed to any platform that supports Next.js:
- Netlify
- AWS Amplify
- DigitalOcean App Platform
- Railway
- Self-hosted with Docker

## Customization

### Styling

The app uses Tailwind CSS. Colors and styles can be customized in:
- `tailwind.config.ts` - Theme configuration
- `src/app/globals.css` - Global styles

### Content

Update legal pages content in:
- `src/app/privacy/page.tsx`
- `src/app/terms/page.tsx`
- `src/app/refund-policy/page.tsx`

### Footer

Update footer links and information in:
- `src/components/Footer.tsx`

## License

See the LICENSE file in the repository root.
