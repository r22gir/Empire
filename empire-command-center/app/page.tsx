// Command Center home — one Studio shell for "/" and "/?product=…".
// Tab / product / screen changes stay in-app (no remount). The previous
// two-shell split (MaxHome vs CommandCenterApp) is gone. Classic chrome
// remains at /classic. Preview ring/cockpit are gated separately.
import CommandCenterApp from './CommandCenterApp';
import StudioAuthGate from './components/auth/StudioAuthGate';

export default function Home() {
  return (
    <StudioAuthGate>
      <CommandCenterApp variant="studio" />
    </StudioAuthGate>
  );
}
