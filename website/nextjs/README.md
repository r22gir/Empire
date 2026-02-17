# EmpireBox Website - Next.js

Modern, responsive marketing website for EmpireBox built with Next.js 14, TypeScript, and Tailwind CSS.

## Features

- ⚡️ Next.js 15 with App Router (Security Patched)
- 🎨 Tailwind CSS for styling
- 🎭 Framer Motion for animations
- 📱 Fully responsive design
- ♿️ SEO optimized
- 🚀 Fast page loads
- 🎯 TypeScript for type safety
- 🔒 Security vulnerabilities addressed

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

3. Run the development server:
```bash
npm run dev
```

4. Open [http://localhost:3000](http://localhost:3000) in your browser

## Project Structure

```
nextjs/
├── src/
│   ├── app/              # Next.js 14 App Router pages
│   │   ├── layout.tsx    # Root layout
│   │   ├── page.tsx      # Home page
│   │   ├── about/        # About page
│   │   ├── pricing/      # Pricing page
│   │   └── faq/          # FAQ page
│   ├── components/       # React components
│   │   ├── Navbar.tsx
│   │   ├── Hero.tsx
│   │   ├── Features.tsx
│   │   ├── Testimonials.tsx
│   │   ├── HowItWorks.tsx
│   │   ├── Pricing.tsx
│   │   ├── FAQ.tsx
│   │   ├── CTA.tsx
│   │   ├── Footer.tsx
│   │   └── EmailForm.tsx
│   └── lib/              # Utilities and constants
│       └── constants.ts  # App-wide constants
└── public/               # Static assets
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

The `out` directory can be deployed to any static hosting service (Netlify, AWS S3, etc.)

## Environment Variables

Currently no environment variables are required. If you add features like form submissions or analytics, create a `.env.local` file:

```
NEXT_PUBLIC_API_URL=your_api_url
NEXT_PUBLIC_GA_ID=your_google_analytics_id
```

## Customization

### Colors

Edit `tailwind.config.js` to change the color scheme:

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

- Uses Next.js 14 App Router for optimal performance
- Automatic code splitting
- Image optimization (when images are added)
- Font optimization with next/font

## Browser Support

- Chrome (latest)
- Firefox (latest)
- Safari (latest)
- Edge (latest)
- Mobile browsers

## Contributing

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request

## License

Proprietary - EmpireBox © 2026

## Support

For questions or issues:
- Email: hello@empirebox.com
- Website: https://empirebox.com
