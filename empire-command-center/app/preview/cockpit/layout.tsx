import type { Metadata } from 'next';
import StudioAuthGate from '../../components/auth/StudioAuthGate';

// Preview-only route. Must use the same Studio sign-in as "/".
export const metadata: Metadata = {
  title: 'Empire Command Center · Cockpit (preview)',
  robots: { index: false, follow: false },
};

export default function CockpitPreviewLayout({ children }: { children: React.ReactNode }) {
  return <StudioAuthGate>{children}</StudioAuthGate>;
}
