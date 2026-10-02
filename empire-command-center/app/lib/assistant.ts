'use client';

import { useEffect, useState } from 'react';
import { API_BASE } from './api';

/** Workroom label. The identity API says "Max"; the shell already says MAX. */
export const WORKROOM_ASSISTANT_LABEL = 'MAX';

export function assistantNameFromEnv(): string {
  const fromEnv = process.env.NEXT_PUBLIC_ASSISTANT_NAME?.trim();
  if (fromEnv) return fromEnv;
  const edition = (process.env.NEXT_PUBLIC_EMPIRE_EDITION || '').toLowerCase();
  if (edition === 'amp') return 'Max-e';
  if (edition === 'maxine') return 'Maxine';
  return WORKROOM_ASSISTANT_LABEL;
}

/** Display name for this instance. Workroom stays MAX unless the API or env says otherwise. */
export function useAssistantName(): string {
  const [name, setName] = useState(assistantNameFromEnv);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/api/v1/edition`)
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (cancelled || !data?.assistant?.name) return;
        const apiName = String(data.assistant.name);
        if (apiName === 'Max' && !process.env.NEXT_PUBLIC_ASSISTANT_NAME) return;
        setName(apiName);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  return name;
}
