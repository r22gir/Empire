import type { Metadata } from 'next';
import './globals.css';
import Footer from '@/components/Footer';

export const metadata: Metadata = {
  title: 'EmpireBox - Complete Reselling Business in a Box',
  description: 'Hardware bundles with MarketForge subscription for resellers. Post to eBay, Poshmark, Facebook in 30 seconds. Join 50+ resellers already making more money.',
  keywords: 'reselling, eBay, Poshmark, multi-platform listing, automation, hardware bundles, MarketForge',
  openGraph: {
    title: 'EmpireBox - Operating System for Resellers',
    description: 'Post to eBay, Poshmark, Facebook in 30 seconds.',
    url: 'https://empirebox.store',
    siteName: 'EmpireBox',
    type: 'website',
  },
  icons: {
    icon: '/favicon.ico',
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="scroll-smooth">
      <body className="font-sans">
        {children}
        <Footer />
      </body>
    </html>
  );
}