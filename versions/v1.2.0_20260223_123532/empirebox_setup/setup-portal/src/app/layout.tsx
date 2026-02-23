import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'EmpireBox Setup',
  description: 'Set up your EmpireBox Mini PC',
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="bg-charcoal text-white min-h-screen">{children}</body>
    </html>
  );
}
