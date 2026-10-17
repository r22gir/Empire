'use client';

import { FormEvent, useEffect, useState } from 'react';
import { API_BASE } from '../lib/api';
import { useEdition } from '../lib/edition';
import {
  PEDIR_CURSOR_APPROVED,
  PEDIR_CURSOR_NOTE,
  PEDIR_CURSOR_PAUSED,
  statusChip,
} from '../lib/pedirCursorCopy';

type Usage = { level?: string; message?: string; overage_active?: boolean };
type CursorReq = {
  id: string;
  title: string;
  body: string;
  status: string;
  pr_url?: string | null;
  note_es?: string | null;
  cap_state?: string;
};

export default function PedirCursorPage() {
  const edition = useEdition();
  const [usage, setUsage] = useState<Usage | null>(null);
  const [items, setItems] = useState<CursorReq[]>([]);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [files, setFiles] = useState<FileList | null>(null);
  const [busy, setBusy] = useState(false);
  const [flash, setFlash] = useState('');
  const [error, setError] = useState('');

  const paused = usage?.level === 'paused';

  const reload = () => {
    fetch(`${API_BASE}/api/v1/edition/cursor-requests`, { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : { requests: [] }))
      .then((data) => setItems(data.requests || []))
      .catch(() => {});
    fetch(`${API_BASE}/api/v1/edition/usage`, { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data) setUsage(data);
      })
      .catch(() => {});
  };

  useEffect(() => {
    reload();
  }, []);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (paused || busy) return;
    setBusy(true);
    setError('');
    setFlash('');
    const form = new FormData();
    form.append('title', title);
    form.append('body', body);
    if (files) {
      Array.from(files).slice(0, 5).forEach((file) => form.append('files', file));
    }
    try {
      const res = await fetch(`${API_BASE}/api/v1/edition/cursor-requests`, {
        method: 'POST',
        credentials: 'include',
        body: form,
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(data.detail || PEDIR_CURSOR_PAUSED);
        return;
      }
      setTitle('');
      setBody('');
      setFlash('Quedó en cola, manito. Chief e lo revisa.');
      reload();
    } catch {
      setError('No pude guardar el pedido. Inténtalo de nuevo.');
    } finally {
      setBusy(false);
    }
  };

  const decide = async (id: string, decision: 'approve' | 'changes') => {
    setBusy(true);
    try {
      const res = await fetch(`${API_BASE}/api/v1/edition/cursor-requests/${id}/decision`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ decision, note: '' }),
      });
      const data = await res.json().catch(() => ({}));
      setFlash(data.message || (decision === 'approve' ? PEDIR_CURSOR_APPROVED : 'Pediste cambios.'));
      reload();
    } finally {
      setBusy(false);
    }
  };

  const editionLabel = edition === 'maxine' ? 'Maxine' : edition === 'amp' ? 'Max-e' : edition;

  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: 24, fontFamily: 'Inter, sans-serif', color: '#1a1a1a' }}>
      <p style={{ color: '#b8960c', fontWeight: 700, fontSize: 12 }}>PEDIR A CURSOR</p>
      <h1>Pedir a Cursor</h1>
      <p>Edición: {editionLabel}</p>
      <p style={{ color: '#5C5650' }}>{PEDIR_CURSOR_NOTE}</p>
      {paused ? <p style={{ color: '#9a3412' }}>{usage?.message || PEDIR_CURSOR_PAUSED}</p> : null}
      {flash ? <p style={{ color: '#166534' }}>{flash}</p> : null}
      {error ? <p style={{ color: '#9a3412' }}>{error}</p> : null}

      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12, marginTop: 16 }}>
        <label>
          Título
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={120}
            required
            disabled={paused || busy}
            style={{ display: 'block', width: '100%', marginTop: 4, padding: 8, borderRadius: 8, border: '1px solid #e5e2dc' }}
          />
        </label>
        <label>
          ¿Qué necesitas y por qué?
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            maxLength={4000}
            required
            rows={6}
            disabled={paused || busy}
            style={{ display: 'block', width: '100%', marginTop: 4, padding: 8, borderRadius: 8, border: '1px solid #e5e2dc' }}
          />
        </label>
        <label>
          Capturas (opcional)
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            multiple
            disabled={paused || busy}
            onChange={(e) => setFiles(e.target.files)}
            style={{ display: 'block', marginTop: 4 }}
          />
        </label>
        <button
          type="submit"
          disabled={paused || busy}
          style={{
            padding: '10px 16px',
            borderRadius: 8,
            border: 'none',
            background: paused ? '#e5e2dc' : '#b8960c',
            color: paused ? '#7a746c' : '#fff',
            fontWeight: 700,
            cursor: paused ? 'not-allowed' : 'pointer',
          }}
        >
          Pedir a Cursor
        </button>
      </form>

      <h2 style={{ marginTop: 32 }}>Tus pedidos</h2>
      <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: 12 }}>
        {items.map((item) => (
          <li key={item.id} style={{ border: '1px solid #e5e2dc', borderRadius: 12, padding: 14, background: '#fff' }}>
            <div style={{ fontSize: 11, fontWeight: 800, color: '#9a7b2f' }}>{statusChip(item.status)}</div>
            <strong>{item.title}</strong>
            <p style={{ margin: '6px 0 0', color: '#5C5650', fontSize: 13 }}>{item.body}</p>
            {item.note_es ? <p style={{ margin: '8px 0 0', fontSize: 13 }}>{item.note_es}</p> : null}
            {item.pr_url ? (
              <p>
                <a href={item.pr_url} target="_blank" rel="noreferrer">
                  Ver el PR
                </a>
              </p>
            ) : null}
            {item.status === 'pr_open' ? (
              <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                <button type="button" onClick={() => decide(item.id, 'approve')} disabled={busy}>
                  Aprobar
                </button>
                <button type="button" onClick={() => decide(item.id, 'changes')} disabled={busy}>
                  Pedir cambios
                </button>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </main>
  );
}
