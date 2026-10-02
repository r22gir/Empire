'use client';

import { useEffect, useState } from 'react';
import { API_BASE } from '../lib/api';

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
};

export default function UsageCard() {
  const [usage, setUsage] = useState<Usage | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetch(`${API_BASE}/api/v1/edition/usage`, { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (!cancelled && data && data.enforced !== false && data.edition !== 'workroom') setUsage(data);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, []);

  if (!usage || usage.enforced === false && usage.level === 'ok' && !usage.month) return null;
  if (!usage.month && !usage.cap_percent) return null;

  const ratio = typeof usage.ratio === 'number' ? Math.round(usage.ratio * 100) : null;
  const warn = usage.level === 'warn' || usage.level === 'blocked';
  const money = (value?: number) =>
    typeof value === 'number' ? `$${value.toLocaleString('en-US', { maximumFractionDigits: 4 })}` : '—';

  return (
    <section
      aria-label="Uso"
      style={{
        background: warn ? '#fff7ed' : '#fff',
        border: `1px solid ${usage.level === 'blocked' ? '#c2410c' : warn ? '#fdba74' : '#e5e2dc'}`,
        borderRadius: 12,
        padding: '12px 14px',
        minWidth: 220,
      }}
    >
      <div style={{ fontSize: 11, fontWeight: 800, letterSpacing: 0.6, color: '#9a7b2f' }}>USO</div>
      <div style={{ display: 'flex', gap: 16, marginTop: 6, fontSize: 13, color: '#2D2A26' }}>
        <div>
          <div style={{ color: '#888', fontSize: 11 }}>Hoy</div>
          <strong>{usage.day?.tokens ?? 0}</strong>
          <span style={{ color: '#888' }}> tok</span>
        </div>
        <div>
          <div style={{ color: '#888', fontSize: 11 }}>Este mes</div>
          <strong>{usage.month?.tokens ?? 0}</strong>
          <span style={{ color: '#888' }}> tok · {money(usage.month?.cost_usd)}</span>
        </div>
      </div>
      <div style={{ marginTop: 6, fontSize: 12, color: '#5C5650' }}>
        Tope {usage.cap_percent ?? 20}% de EmpireBox
        {ratio !== null ? ` · ${ratio}% usado` : ''}
        {usage.baseline_basis && usage.baseline_basis !== 'none' ? ` · base ${usage.baseline_basis}` : ''}
      </div>
      {usage.message ? (
        <p style={{ margin: '8px 0 0', fontSize: 12, color: usage.level === 'blocked' ? '#9a3412' : '#9a7b2f' }}>
          {usage.message}
        </p>
      ) : null}
    </section>
  );
}
