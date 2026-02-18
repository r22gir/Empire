import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'EmpireBox - Operating System for Resellers',
  description: 'Post to eBay, Poshmark, Facebook in 30 seconds. Join 50+ resellers already making more money.',
  keywords: 'reselling, eBay, Poshmark, multi-platform listing, automation',
  openGraph: {
    title: 'EmpireBox - Operating System for Resellers',
    description: 'Post to eBay, Poshmark, Facebook in 30 seconds.',
    url: 'https://empirebox.com',
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
      <body>{children}</body>
    </html>
  );
}
