// Command Center home.
// - "/" with no query: the module ring home (components/ring/RingHome).
// - "/?product=…", "/?screen=…", "/?section=…", "/?ask=…" (any app query
//   param): the classic Command Center app, so every existing deep link, chat
//   link and bookmark keeps working. Hash links (/#presentation, …) are
//   forwarded to /classic by RingHome on mount.
// - The classic app is also reachable directly at /classic.
import CommandCenterApp from './CommandCenterApp';
import RingHome from './components/ring/RingHome';

type SP = Record<string, string | string[] | undefined>;

export default async function Home({ searchParams }: { searchParams: Promise<SP> }) {
  const sp = await searchParams;
  const deepLink = Object.keys(sp).some(k => !k.startsWith('utm_') && k !== '_v' && k !== 'fbclid' && k !== 'gclid');
  return deepLink ? <CommandCenterApp /> : <RingHome />;
}
