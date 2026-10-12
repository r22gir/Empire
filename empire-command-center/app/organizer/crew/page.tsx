'use client';

import { useEffect, useState } from 'react';
import { API } from '../../lib/api';

export default function CrewPhonePage() {
  const [token, setToken] = useState('');
  const [data, setData] = useState<any>(null);
  const [err, setErr] = useState('');

  useEffect(() => {
    const t = new URLSearchParams(window.location.search).get('token') || '';
    setToken(t);
    if (!t) return;
    fetch(`${API}/organizer/crew/${t}/today`)
      .then((r) => (r.ok ? r.json() : Promise.reject(r.status)))
      .then(setData)
      .catch(() => setErr('This crew link is not valid.'));
  }, []);

  async function checkIn(id: string) {
    await fetch(`${API}/organizer/crew/${token}/check-in?event_id=${encodeURIComponent(id)}`, { method: 'POST' });
    const next = await fetch(`${API}/organizer/crew/${token}/today`).then((r) => r.json());
    setData(next);
  }

  if (err) return <main style={{ padding: 20 }}>{err}</main>;
  if (!token) return <main style={{ padding: 20 }}>Missing crew token.</main>;
  if (!data) return <main style={{ padding: 20 }}>Loading…</main>;

  return (
    <main style={{ padding: 16, maxWidth: 480, margin: '0 auto', fontFamily: 'system-ui' }}>
      <h1 style={{ fontSize: 20 }}>Today · {data.crew?.name}</h1>
      <p style={{ color: '#666', fontSize: 13 }}>Only your stops. Check in, then mark done with a photo from the API if needed.</p>
      {(data.items || []).map((it: any) => (
        <section key={it.id} style={{ border: '1px solid #ece8e0', borderRadius: 12, padding: 12, marginBottom: 10 }}>
          <div style={{ fontWeight: 700 }}>{it.title}</div>
          <div style={{ fontSize: 13, color: '#666' }}>{(it.start_time || '').slice(11, 16)} · {it.location_address}</div>
          <div style={{ marginTop: 8, display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            {(it.actions || []).filter((a: any) => a.href && a.group === 'stop').map((a: any) => (
              <a key={a.id} href={a.href}>{a.label}</a>
            ))}
            {it.map_link && <a href={it.map_link}>Navigate</a>}
            {it.call_link && <a href={it.call_link}>Call</a>}
            {it.phone && <a href={`sms:${it.phone}`}>Text</a>}
            <button type="button" onClick={() => checkIn(it.id)}>Check in</button>
          </div>
          {it.notes && <p style={{ fontSize: 13 }}>{it.notes}</p>}
        </section>
      ))}
    </main>
  );
}
