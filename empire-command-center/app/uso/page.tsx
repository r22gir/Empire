'use client';

import { useEffect, useState } from 'react';
import { API_BASE } from '../lib/api';

type Usage = {
  cap_percent?: number;
  level?: string;
  message?: string;
  limit_note_es?: string;
  used_percent?: number | null;
  remaining_percent?: number | null;
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
            Tope {usage.cap_percent ?? 20}%
            {typeof usage.used_percent === 'number' ? ` · ${usage.used_percent}% usado` : ''}
            {typeof usage.remaining_percent === 'number' ? ` · queda ${usage.remaining_percent}%` : ''}
            {usage.level ? ` · ${usage.level}` : ''}
          </p>
          {usage.message ? <p>{usage.message}</p> : null}
        </>
      ) : null}
    </main>
  );
}
