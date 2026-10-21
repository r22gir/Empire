'use client';

import { useEffect, useState } from 'react';
import { API } from '../../lib/api';

type SafeCreds = {
  phone_number_id_set?: boolean;
  phone_number_id_last4?: string;
  access_token_set?: boolean;
  app_secret_set?: boolean;
  verify_token?: string;
  webhook_url?: string;
  configured?: boolean;
};

export default function WhatsAppSecureKeys() {
  const [phoneId, setPhoneId] = useState('');
  const [token, setToken] = useState('');
  const [secret, setSecret] = useState('');
  const [owners, setOwners] = useState('');
  const [safe, setSafe] = useState<SafeCreds | null>(null);
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState(false);

  function loadSafe() {
    fetch(`${API}/whatsapp/credentials`, { credentials: 'include' })
      .then((res) => (res.ok ? res.json() : null))
      .then((data) => setSafe(data))
      .catch(() => setSafe(null));
  }

  useEffect(() => {
    loadSafe();
  }, []);

  async function save(event: React.FormEvent) {
    event.preventDefault();
    setBusy(true);
    setNote('');
    try {
      const res = await fetch(`${API}/whatsapp/credentials`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          phone_number_id: phoneId,
          access_token: token,
          app_secret: secret,
          owner_numbers: owners ? owners.split(/[,\s]+/).filter(Boolean) : [],
        }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setNote(data.detail || 'No pude guardar. Entra como dueño.');
        return;
      }
      setSafe(data.credentials || null);
      setToken('');
      setSecret('');
      setPhoneId('');
      setNote('Guardado. El token no se vuelve a mostrar.');
    } catch {
      setNote('No pude guardar. Revisa la sesión.');
    } finally {
      setBusy(false);
    }
  }

  async function testLink() {
    setBusy(true);
    setNote('');
    try {
      const res = await fetch(`${API}/whatsapp/test`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: '{}',
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        setNote(data.error || data.detail || 'La prueba no pasó. Nada se envió.');
        return;
      }
      const last4 = data.phone_number_id_last4 ? ` ···${data.phone_number_id_last4}` : '';
      setNote(`Conexión de solo lectura OK${last4}. No se envió ningún mensaje.`);
    } catch {
      setNote('No pude probar la conexión.');
    } finally {
      setBusy(false);
    }
  }

  return (
    <section
      data-wa-secure-keys="1"
      style={{
        maxWidth: 760,
        margin: '0 auto 48px',
        padding: '0 16px',
        fontFamily: 'Nunito, Inter, sans-serif',
        color: '#2D2A26',
      }}
    >
      <div
        style={{
          background: '#fff',
          border: '1px solid #F0E6D8',
          borderRadius: 18,
          padding: 18,
          boxShadow: '0 10px 28px rgba(45,42,38,.04)',
        }}
      >
        <h2 style={{ fontFamily: "'Playfair Display', Georgia, serif", fontSize: 22, margin: '0 0 8px' }}>
          Pantalla segura
        </h2>
        <p style={{ fontSize: 15, lineHeight: 1.55, margin: '0 0 12px' }}>
          Pega aquí el Phone Number ID, el token permanente y el App Secret de <strong>tu</strong> Meta.
          Nunca en el chat. Este número es de Juan, no el de Rafael.
        </p>
        {safe?.phone_number_id_last4 ? (
          <p style={{ fontSize: 13, color: '#6F685F' }}>
            Guardado ···{safe.phone_number_id_last4}
            {safe.configured ? ' · listo' : ' · incompleto'}
          </p>
        ) : null}
        {safe?.webhook_url ? (
          <p style={{ fontSize: 13, wordBreak: 'break-all' }}>
            Webhook: <code>{safe.webhook_url}</code>
          </p>
        ) : null}
        {safe?.verify_token ? (
          <p style={{ fontSize: 13 }}>
            Verify token para Meta: <code>{safe.verify_token}</code>
          </p>
        ) : null}
        <form onSubmit={save}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 700, marginTop: 10 }}>
            Phone Number ID
            <input
              value={phoneId}
              onChange={(e) => setPhoneId(e.target.value)}
              autoComplete="off"
              style={fieldStyle}
            />
          </label>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 700, marginTop: 10 }}>
            Access token
            <input
              type="password"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              autoComplete="new-password"
              style={fieldStyle}
            />
          </label>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 700, marginTop: 10 }}>
            App Secret
            <input
              type="password"
              value={secret}
              onChange={(e) => setSecret(e.target.value)}
              autoComplete="new-password"
              style={fieldStyle}
            />
          </label>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 700, marginTop: 10 }}>
            Tu número (dueño)
            <input
              value={owners}
              onChange={(e) => setOwners(e.target.value)}
              placeholder="57300…"
              autoComplete="off"
              style={fieldStyle}
            />
          </label>
          <div style={{ display: 'flex', gap: 8, marginTop: 14, flexWrap: 'wrap' }}>
            <button type="submit" disabled={busy} style={btnStyle}>
              Guardar
            </button>
            <button type="button" disabled={busy} onClick={testLink} style={{ ...btnStyle, background: '#2D2A26' }}>
              Probar conexión
            </button>
          </div>
        </form>
        {note ? <p style={{ fontSize: 14, marginTop: 12 }}>{note}</p> : null}
      </div>
    </section>
  );
}

const fieldStyle: React.CSSProperties = {
  display: 'block',
  width: '100%',
  marginTop: 6,
  padding: '10px 12px',
  borderRadius: 10,
  border: '1px solid #E8DCC8',
  background: '#FFF9F0',
  fontSize: 14,
  boxSizing: 'border-box',
};

const btnStyle: React.CSSProperties = {
  background: '#D4A030',
  color: '#2D2A26',
  border: 0,
  borderRadius: 10,
  padding: '10px 14px',
  fontWeight: 800,
  cursor: 'pointer',
};
