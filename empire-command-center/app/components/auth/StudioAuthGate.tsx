'use client';

import { useEffect, useState } from 'react';
import { getStudioSession } from '../../lib/studio-auth';

export default function StudioAuthGate({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    let cancelled = false;
    getStudioSession()
      .then((session) => {
        if (cancelled) return;
        if (!session?.user) {
          const next = encodeURIComponent(window.location.pathname + window.location.search);
          window.location.replace(`/signin?next=${next}`);
          return;
        }
        setReady(true);
      })
      .catch(() => {
        if (cancelled) return;
        window.location.replace('/signin');
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) {
    return (
      <div className="signin-gate" data-signin-page>
        <img src="/brand/empire-mark.svg" alt="Empire" width={48} height={48} />
        <p>Opening Studio…</p>
      </div>
    );
  }

  return <>{children}</>;
}
