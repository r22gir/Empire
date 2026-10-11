// Command Center home.
// - "/" with no query: the Max personal center (components/home3/MaxHome, design
//   system v3). The previous module ring stays at /preview/ring.
// - "/?product=…", "/?screen=…", "/?section=…", "/?ask=…" (any app query
//   param): the Command Center app, so every existing deep link, chat
//   link and bookmark keeps working. Hash links (/#presentation, …) are
//   forwarded to /classic by MaxHome on mount.
// - The classic app is also reachable directly at /classic.
// Family editions wrap this tree in FamilyAuthGate (layout.tsx): signed-out
// visitors never render the dashboard or the coach name.
import CommandCenterApp from './CommandCenterApp';
import MaxHome from './components/home3/MaxHome';

type SP = Record<string, string | string[] | undefined>;

export default async function Home({ searchParams }: { searchParams: Promise<SP> }) {
  const sp = await searchParams;
  const deepLink = Object.keys(sp).some(k => !k.startsWith('utm_') && k !== '_v' && k !== 'theme' && k !== 'fbclid' && k !== 'gclid');
  return deepLink ? <CommandCenterApp /> : <MaxHome />;
}
