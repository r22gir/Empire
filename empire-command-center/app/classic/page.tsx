// /classic — the previous Command Center home, kept as a fallback.
// All in-app deep links keep working here (/classic?product=workroom, ...),
// and "/?<param>" still opens this same app (see app/page.tsx).
import CommandCenterApp from '../CommandCenterApp';

export default function ClassicHome() {
  return <CommandCenterApp />;
}
