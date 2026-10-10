'use client';

import { useEffect, useState } from 'react';
import AmpNav from '../../../components/amp/AmpNav';
import { API } from '../../../lib/api';
import { useEdition } from '../../../lib/edition';

type Conversation = {
  wa_id: string;
  last4?: string;
  preview?: string;
  count?: number;
  last_at?: number;
};

type Message = {
  id: number;
  direction: string;
  kind: string;
  body?: string;
  created_at?: number;
};

export default function AmpWhatsAppChatsPage() {
  const edition = useEdition();
  const [rows, setRows] = useState<Conversation[]>([]);
  const [active, setActive] = useState<string>('');
  const [messages, setMessages] = useState<Message[]>([]);
  const [error, setError] = useState('');

  useEffect(() => {
    fetch(`${API}/whatsapp/chats`, { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('no se pudieron leer los chats'))))
      .then((data) => setRows(data.conversations || []))
      .catch((err) => setError(err.message || 'Error'));
  }, []);

  useEffect(() => {
    if (!active) return;
    fetch(`${API}/whatsapp/chats/${encodeURIComponent(active)}/messages`, { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : Promise.reject(new Error('no se pudo abrir el hilo'))))
      .then((data) => setMessages(data.messages || []))
      .catch((err) => setError(err.message || 'Error'));
  }, [active]);

  return (
    <div data-amp-page style={{ minHeight: '100vh', background: '#FFF9F0', fontFamily: 'Nunito, sans-serif', color: '#2D2A26' }}>
      <AmpNav />
      <main style={{ maxWidth: 720, margin: '0 auto', padding: '20px 16px 72px' }}>
        <p style={{ letterSpacing: 1, color: '#D4A030', fontWeight: 800, fontSize: 12 }}>WHATSAPP · SOLO LECTURA</p>
        <h1 style={{ fontFamily: 'Playfair Display, serif', fontSize: 32, margin: '8px 0' }}>Chats</h1>
        <p style={{ fontSize: 15, lineHeight: 1.5 }}>
          Esta pantalla no envía mensajes. {edition === 'maxine' ? 'Maxine' : 'Max-e'} guarda solo lo de esta instancia.
        </p>
        {error ? <p style={{ color: '#E07A5F' }}>{error}</p> : null}
        {!rows.length && !error ? (
          <div style={{ background: '#fff', border: '1px solid #F0E6D8', borderRadius: 16, padding: 16, marginTop: 16 }}>
            Aún no hay conversaciones en esta instancia.
          </div>
        ) : (
          <ul style={{ listStyle: 'none', padding: 0 }}>
            {rows.map((row) => (
              <li key={row.wa_id}>
                <button
                  type="button"
                  onClick={() => setActive(row.wa_id)}
                  style={{
                    display: 'block',
                    width: '100%',
                    textAlign: 'left',
                    background: active === row.wa_id ? '#FFF4D6' : '#fff',
                    border: '1px solid #F0E6D8',
                    borderRadius: 16,
                    padding: 16,
                    marginTop: 12,
                    cursor: 'pointer',
                    fontFamily: 'inherit',
                    color: 'inherit',
                  }}
                >
                  <strong>···{row.last4 || row.wa_id.slice(-4)}</strong>
                  <span style={{ color: '#9B9590' }}> · {row.count || 0}</span>
                  <div style={{ marginTop: 6, color: '#444' }}>{row.preview || '—'}</div>
                </button>
              </li>
            ))}
          </ul>
        )}
        {active ? (
          <div style={{ background: '#fff', border: '1px solid #F0E6D8', borderRadius: 16, padding: 16, marginTop: 20 }}>
            {messages.map((msg) => (
              <p key={msg.id} style={{ margin: '0 0 12px' }}>
                <strong>{msg.direction === 'out' ? 'Tú / asistente' : 'Entrante'}</strong>
                {' · '}
                {msg.kind}
                <br />
                {msg.body || '—'}
              </p>
            ))}
          </div>
        ) : null}
        <p style={{ marginTop: 24 }}>
          <a href="/amp/whatsapp" style={{ color: '#D4A030', fontWeight: 700 }}>Volver a la guía</a>
        </p>
      </main>
    </div>
  );
}
