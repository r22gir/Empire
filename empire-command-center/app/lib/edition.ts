'use client';

import { useEffect, useState } from 'react';
import { API_BASE } from './api';

/** Hidden in Juan's instance. Shared base modules stay. */
export const AMP_HIDDEN_NAV = new Set(['workroom', 'craft', 'luxe', 'drawings']);

export const AMP_NAV_LABELS: Record<string, string> = {
  amp: 'AMP',
  crm: 'Coachees',
  lead: 'Ingreso',
  social: 'SocialForge',
  'nueva-empresa': 'Nueva empresa',
};

export function editionFromEnv(): string {
  return (process.env.NEXT_PUBLIC_EMPIRE_EDITION || 'workroom').toLowerCase();
}

export function useEdition(): string {
  const [edition, setEdition] = useState(editionFromEnv);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/api/v1/edition`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!cancelled && data?.edition) setEdition(String(data.edition));
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  return edition;
}
