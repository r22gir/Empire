'use client';

import { useEffect, useState } from 'react';
import { API_BASE } from '../lib/api';

type Usage = {
  cap_percent?: number;
  level?: string;
  message?: string;
  limit_note_es?: string;
  ratio?: number | null;
  allowance?: number | null;
  baseline_basis?: string;
  day?: { tokens?: number; input_tokens?: number; output_tokens?: number; cost_usd?: number };
  month?: { tokens?: number; input_tokens?: number; output_tokens?: number; cost_usd?: number };
};

export default function UsoPage() {
  const [usage, setUsage] = useState<Usage | null>(null);
  const [denied, setDenied] = useState(false);

  useEffect(() => {
    fetch(`${API_BASE}/api/v1/edition/usage`, { credentials: 'include' })
      .then(async (res) => {
        if (res.status === 403) {
          setDenied(true);
          return null;
        }
        return res.ok ? res.json() : null;
      })
      .then((data) => {
        if (data) setUsage(data);
      })
      .catch(() => {});
  }, []);

  const money = (value?: number) =>
    typeof value === 'number' ? `$${value.toLocaleString('en-US', { maximumFractionDigits: 4 })}` : '—';

  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: 24, fontFamily: 'Inter, sans-serif', color: '#1a1a1a' }}>
      <p style={{ color: '#b8960c', fontWeight: 700, fontSize: 12 }}>USO</p>
      <h1>Uso de este mes</h1>
      <p>
        {usage?.limit_note_es || 'Tu uso está limitado al 20% del uso total de MiniMax.'}
      </p>
      {denied ? <p>Esta página es solo para el dueño de esta edición.</p> : null}
      {usage ? (
        <>
          <p>
            Hoy: {usage.day?.input_tokens ?? 0} tokens de entrada, {usage.day?.output_tokens ?? 0} de salida
            {' '}({usage.day?.tokens ?? 0} en total, {money(usage.day?.cost_usd)}).
          </p>
          <p>
            Este mes: {usage.month?.input_tokens ?? 0} tokens de entrada, {usage.month?.output_tokens ?? 0} de salida
            {' '}({usage.month?.tokens ?? 0} en total, {money(usage.month?.cost_usd)}).
          </p>
          <p>
            Tope {usage.cap_percent ?? 20}%
            {usage.allowance != null ? ` · cupo ${usage.allowance}` : ' · falta la base del mes para aplicar el tope'}
            {typeof usage.ratio === 'number' ? ` · ${Math.round(usage.ratio * 100)}% usado` : ''}
            {usage.level ? ` · ${usage.level}` : ''}
          </p>
          {usage.message ? <p>{usage.message}</p> : null}
        </>
      ) : null}
    </main>
  );
}
