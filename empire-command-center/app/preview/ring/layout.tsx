import type { Metadata } from 'next';
import StudioAuthGate from '../../components/auth/StudioAuthGate';

// Preview-only route. Same Studio sign-in as "/".
export const metadata: Metadata = {
  title: 'Empire Command Center · Module Ring',
  robots: { index: false, follow: false },
};

export default function RingPreviewLayout({ children }: { children: React.ReactNode }) {
  return <StudioAuthGate>{children}</StudioAuthGate>;
}
