'use client';

import { FormEvent, useEffect, useState } from 'react';
import { API_BASE } from '../lib/api';
import { PEDIR_CURSOR_COPY, pedirCursorStatusLabel } from '../lib/pedirCursorCopy';

type Item = {
  id: string;
  title: string;
  body: string;
  status: string;
  pr_url?: string | null;
  note_es?: string | null;
  owner_note?: string | null;
};

export default function PedirCursorPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [title, setTitle] = useState('');
  const [body, setBody] = useState('');
  const [files, setFiles] = useState<FileList | null>(null);
  const [capMessage, setCapMessage] = useState('');
  const [paused, setPaused] = useState(false);
  const [busy, setBusy] = useState(false);
  const [flash, setFlash] = useState('');

  const load = () => {
    fetch(`${API_BASE}/api/v1/edition/cursor-requests`, { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : { requests: [] }))
      .then((data) => setItems(data.requests || []))
      .catch(() => {});
  };

  useEffect(() => {
    load();
    fetch(`${API_BASE}/api/v1/edition/usage`, { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => {
        if (data?.level === 'paused') {
          setPaused(true);
          setCapMessage(data.message || PEDIR_CURSOR_COPY.paused);
        }
      })
      .catch(() => {});
  }, []);

  const onSubmit = async (event: FormEvent) => {
    event.preventDefault();
    if (paused) return;
    setBusy(true);
    setFlash('');
    const form = new FormData();
    form.append('title', title);
    form.append('body', body);
    if (files) {
      Array.from(files).slice(0, 5).forEach((file) => form.append('files', file));
    }
    const res = await fetch(`${API_BASE}/api/v1/edition/cursor-requests`, {
      method: 'POST',
      credentials: 'include',
      body: form,
    });
    const data = await res.json().catch(() => ({}));
    setBusy(false);
    if (!res.ok) {
      const detail = data.detail || PEDIR_CURSOR_COPY.paused;
      setCapMessage(detail);
      if (res.status === 429) setPaused(true);
      return;
    }
    setTitle('');
    setBody('');
    setFiles(null);
    load();
  };

  const decide = async (id: string, decision: 'approve' | 'changes') => {
    const res = await fetch(`${API_BASE}/api/v1/edition/cursor-requests/${id}/decision`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ decision, note: '' }),
    });
    const data = await res.json().catch(() => ({}));
    if (res.ok) setFlash(data.message || '');
    load();
  };

  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: 24, fontFamily: 'Inter, sans-serif', color: '#1a1a1a' }}>
      <p style={{ color: '#b8960c', fontWeight: 700, fontSize: 12 }}>MAX-E</p>
      <h1>{PEDIR_CURSOR_COPY.title}</h1>
      <p style={{ color: '#5C5650' }}>{PEDIR_CURSOR_COPY.editionLabel}</p>
      <p>{PEDIR_CURSOR_COPY.note}</p>
      {capMessage ? <p style={{ color: '#9a3412' }}>{capMessage}</p> : null}
      {flash ? <p style={{ color: '#166534' }}>{flash}</p> : null}

      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12, margin: '20px 0 32px' }}>
        <label>
          {PEDIR_CURSOR_COPY.fieldTitle}
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={120}
            required
            style={{ display: 'block', width: '100%', marginTop: 4, padding: 8 }}
          />
        </label>
        <label>
          {PEDIR_CURSOR_COPY.fieldBody}
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            maxLength={4000}
            required
            rows={6}
            style={{ display: 'block', width: '100%', marginTop: 4, padding: 8 }}
          />
        </label>
        <label>
          {PEDIR_CURSOR_COPY.fieldShots}
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            multiple
            onChange={(e) => setFiles(e.target.files)}
            style={{ display: 'block', marginTop: 4 }}
          />
        </label>
        <button
          type="submit"
          disabled={paused || busy}
          style={{
            background: paused ? '#d6d3d1' : '#b8960c',
            color: '#fff',
            border: 0,
            borderRadius: 8,
            padding: '10px 16px',
            fontWeight: 700,
            cursor: paused ? 'not-allowed' : 'pointer',
          }}
        >
          {PEDIR_CURSOR_COPY.submit}
        </button>
      </form>

      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {items.map((item) => (
          <li key={item.id} style={{ borderTop: '1px solid #e5e2dc', padding: '14px 0' }}>
            <strong>{item.title}</strong>
            <span
              style={{
                marginLeft: 8,
                fontSize: 12,
                fontWeight: 700,
                color: '#9a7b2f',
              }}
            >
              {pedirCursorStatusLabel(item.status)}
            </span>
            <p style={{ margin: '6px 0', color: '#444' }}>{item.body}</p>
            {item.pr_url ? (
              <p>
                <a href={item.pr_url} style={{ color: '#b8960c', fontWeight: 700 }}>
                  Ver el PR
                </a>
              </p>
            ) : null}
            {item.note_es ? <p style={{ color: '#5C5650' }}>{item.note_es}</p> : null}
            {item.status === 'pr_open' ? (
              <div style={{ display: 'flex', gap: 8 }}>
                <button type="button" onClick={() => decide(item.id, 'approve')}>
                  {PEDIR_CURSOR_COPY.approve}
                </button>
                <button type="button" onClick={() => decide(item.id, 'changes')}>
                  {PEDIR_CURSOR_COPY.changes}
                </button>
              </div>
            ) : null}
          </li>
        ))}
      </ul>
    </main>
  );
}
