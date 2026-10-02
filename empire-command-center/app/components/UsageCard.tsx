'use client';

import { useEffect, useState } from 'react';
import { API_BASE } from '../lib/api';
import { isFamilyEdition } from '../lib/edition';

type Usage = {
  enforced?: boolean;
  cap_percent?: number;
  level?: string;
  message?: string;
  ratio?: number | null;
  day?: { tokens?: number; cost_usd?: number };
  month?: { tokens?: number; cost_usd?: number };
  allowance?: number | null;
  baseline_basis?: string;
  limit_note_es?: string;
};

export default function UsageCard() {
  const family = isFamilyEdition();
  const [usage, setUsage] = useState<Usage | null>(null);

  useEffect(() => {
    if (!family) return;
    let cancelled = false;
    fetch(`${API_BASE}/api/v1/edition/usage`, { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!cancelled && data) setUsage(data);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [family]);

  if (!family) return null;
  const note = usage?.limit_note_es || `Tu uso está limitado al ${usage?.cap_percent ?? 20}% del uso total de MiniMax.`;

  const ratio = typeof usage?.ratio === 'number' ? Math.round(usage.ratio * 100) : null;
  const warn = usage?.level === 'warn' || usage?.level === 'blocked';
  const money = (value?: number) =>
    typeof value === 'number' ? `$${value.toLocaleString('en-US', { maximumFractionDigits: 4 })}` : '—';

  return (
    <section
      aria-label="Uso"
      style={{
        background: warn ? '#fff7ed' : '#fff',
        border: `1px solid ${usage?.level === 'blocked' ? '#c2410c' : warn ? '#fdba74' : '#e5e2dc'}`,
        borderRadius: 12,
        padding: '12px 14px',
        minWidth: 220,
      }}
    >
      <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 0.6, color: '#9a7b2f' }}>USO</div>
      <div style={{ display: 'flex', gap: 16, marginTop: 6, fontSize: 13, color: '#2D2A26' }}>
        <div>
          <div style={{ color: '#888', fontSize: 11 }}>Hoy</div>
          <strong>{usage?.day?.tokens ?? 0}</strong>
          <span style={{ color: '#888' }}> tok</span>
        </div>
        <div>
          <div style={{ color: '#888', fontSize: 11 }}>Este mes</div>
          <strong>{usage?.month?.tokens ?? 0}</strong>
          <span style={{ color: '#888' }}> tok · {money(usage?.month?.cost_usd)}</span>
        </div>
      </div>
      <div style={{ marginTop: 6, fontSize: 12, color: '#5C5650' }}>
        {note}
        {ratio !== null ? ` · ${ratio}% usado` : ''}
        {usage?.baseline_basis && usage.baseline_basis !== 'none' ? ` · base ${usage.baseline_basis}` : ''}
      </div>
      <a href="/uso" style={{ display: 'inline-block', marginTop: 8, fontSize: 12, color: '#9a7b2f', fontWeight: 700 }}>
        Ver el uso del mes
      </a>
      {usage?.message ? (
        <p style={{ margin: '8px 0 0', fontSize: 12, color: usage.level === 'blocked' ? '#9a3412' : '#9a7b2f' }}>
          {usage.message}
        </p>
      ) : null}
    </section>
  );
}
