'use client';

import { useEffect, useState } from 'react';
import { editionFromEnv } from '../lib/edition';
import { isFamilyPublicPath } from '../lib/familyChrome.mjs';
import {
  FAMILY_LOGIN_PATH,
  familyAuthFailedStatus,
  shouldGateFamilyShell,
} from '../lib/familyAuth';

/** Do not paint the Max-e shell until the AMP session is real. */
export default function FamilyAuthGate({ children }: { children: React.ReactNode }) {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const host = typeof window !== 'undefined' ? window.location.hostname : '';
    const path = typeof window !== 'undefined' ? window.location.pathname : '/';
    if (!shouldGateFamilyShell(editionFromEnv(), host) || isFamilyPublicPath(path)) {
      setReady(true);
      return;
    }
    let cancelled = false;
    fetch('/api/v1/amp/me', { credentials: 'include', cache: 'no-store' })
      .then((res) => {
        if (cancelled) return;
        if (familyAuthFailedStatus(res.status)) {
          window.location.replace(FAMILY_LOGIN_PATH);
          return;
        }
        if (!res.ok) {
          window.location.replace(FAMILY_LOGIN_PATH);
          return;
        }
        setReady(true);
      })
      .catch(() => {
        if (!cancelled) window.location.replace(FAMILY_LOGIN_PATH);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (!ready) {
    return (
      <div
        data-testid="family-auth-gate"
        style={{ minHeight: '100vh', background: '#2D2A26' }}
      />
    );
  }
  return <>{children}</>;
}
