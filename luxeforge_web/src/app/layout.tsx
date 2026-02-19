import type { Metadata } from 'next';
import './globals.css';

export const metadata: Metadata = {
  title: 'LuxeForge — AI-Powered Custom Workroom Software',
  description:
    'The complete software platform for custom workroom businesses. AI chat intake, photo measurements, auto-quotes, and production queue management.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
