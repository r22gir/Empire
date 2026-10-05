import type { Metadata } from 'next';

// Preview-only route ("module ring" home). Same host + same Cloudflare Access /
// Tailscale gate as the rest of the studio.
export const metadata: Metadata = {
  title: 'Empire Command Center · Module Ring',
  robots: { index: false, follow: false },
};

export default function RingPreviewLayout({ children }: { children: React.ReactNode }) {
  return children;
}
