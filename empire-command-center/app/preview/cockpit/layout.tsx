import type { Metadata } from 'next';

// Preview-only route. Same host + same Cloudflare Access / Tailscale gate as
// the rest of the studio (middleware passes studio paths straight through).
export const metadata: Metadata = {
  title: 'Empire Command Center · Cockpit (preview)',
  robots: { index: false, follow: false },
};

export default function CockpitPreviewLayout({ children }: { children: React.ReactNode }) {
  return children;
}
