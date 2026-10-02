'use client';

import { useEffect, useState } from 'react';
import { API_BASE } from './api';

/** Hidden in Juan's instance. Shared base modules stay. */
export const AMP_HIDDEN_NAV = new Set(['workroom', 'craft', 'luxe', 'drawings']);

/** Maxine's shell hides the same workroom tools, and the AMP product is not her home. */
export const MAXINE_HIDDEN_NAV = new Set<string>([...AMP_HIDDEN_NAV, 'amp']);

export const MAXINE_NAV_LABELS: Record<string, string> = {
  owner: 'Centro de mando',
  construction: 'Portafolio',
  crm: 'Compradores',
  lead: 'Prospectos',
  social: 'Contenido',
  pay: 'Planes de pago',
  'nueva-empresa': 'Nuevo proyecto',
  'daily-summary': 'Resumen',
};

export const AMP_NAV_LABELS: Record<string, string> = {
  owner: 'Centro de mando',
  amp: 'AMP',
  cibernettic: 'Cibernettic',
  crm: 'Coachees',
  lead: 'Ingreso',
  social: 'SocialForge',
  'nueva-empresa': 'Empresas',
};

export function editionFromEnv(): string {
  return (process.env.NEXT_PUBLIC_EMPIRE_EDITION || 'workroom').toLowerCase();
}

const FAMILY = new Set(['amp', 'maxine']);

export function isFamilyEdition(edition: string = editionFromEnv()): boolean {
  return FAMILY.has((edition || '').trim().toLowerCase());
}

/** Maxine opens on the ConstructionForge portfolio. Max-e opens the command center, not one business. */
export function homeProductForEdition(edition: string = editionFromEnv()): 'construction' | 'amp' | 'owner' {
  const name = (edition || '').trim().toLowerCase();
  if (name === 'maxine') return 'construction';
  return 'owner';
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
