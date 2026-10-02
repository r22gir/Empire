'use client';

import { useEffect, useState } from 'react';
import { Flame, Mail, KeyRound, ArrowRight } from 'lucide-react';
import { useAssistantName } from '../lib/assistant';
import { isFamilyEdition } from '../lib/edition';

export default function AmpEditionLogin() {
  const [email, setEmail] = useState('');
  const [code, setCode] = useState('');
  const [info, setInfo] = useState('');
  const [error, setError] = useState('');
  const [ready, setReady] = useState(false);
  const [sending, setSending] = useState(false);
  const [entering, setEntering] = useState(false);
  const assistant = useAssistantName();
  const family = isFamilyEdition();
  const title = family ? `${assistant} · Centro de mando` : 'Empire Command Center';

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    if (params.get('listo') === '1') setReady(true);
  }, []);

  async function requestCode(e: React.FormEvent) {
    e.preventDefault();
    setSending(true);
    setError('');
    setInfo('');
    try {
      const res = await fetch('/api/v1/amp/auth/request', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(body.detail || 'No se pudo pedir el código.');
        return;
      }
      setInfo(body.detail || 'Si el correo está autorizado, enviamos un código.');
    } catch {
      setError('No se pudo conectar con el servidor.');
    } finally {
      setSending(false);
    }
  }

  async function verifyCode(e: React.FormEvent) {
    e.preventDefault();
    setEntering(true);
    setError('');
    try {
      const res = await fetch('/api/v1/amp/auth/verify', {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, code }),
      });
      const body = await res.json().catch(() => ({}));
      if (!res.ok) {
        setError(body.detail || 'Código inválido o vencido.');
        return;
      }
      window.location.href = '/';
    } catch {
      setError('No se pudo conectar con el servidor.');
    } finally {
      setEntering(false);
    }
  }

  return (
    <div data-amp-page style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #2D2A26, #3d3530)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
      <div style={{ width: '100%', maxWidth: 440 }}>
        <div style={{ textAlign: 'center', marginBottom: 28 }}>
          <div style={{ width: 48, height: 48, borderRadius: 14, background: '#D4A030', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
            <Flame size={24} color="#fff" />
          </div>
          <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: 26, color: '#FFF9F0', margin: '0 0 6px' }}>{family ? `Hola, soy ${assistant}` : 'Sign in'}</h1>
          <p style={{ fontSize: 14, color: '#C8C2BA', margin: 0 }}>{title}. Solo cuentas autorizadas.</p>
        </div>
        <div style={{ background: '#fff', borderRadius: 16, padding: 28, boxShadow: '0 8px 32px rgba(0,0,0,0.2)' }}>
          {ready && (
            <div style={{ background: '#f3faf4', color: '#24663a', borderRadius: 8, padding: '10px 12px', fontSize: 13, marginBottom: 16 }}>
              Sesión iniciada. <a href="/" style={{ color: '#D4A030', fontWeight: 700 }}>Entrar al centro de mando</a>
            </div>
          )}
          {error && <div style={{ background: '#fef2f2', color: '#dc2626', borderRadius: 8, padding: '8px 12px', fontSize: 13, marginBottom: 16 }}>{error}</div>}
          {info && <div style={{ background: '#FFF9F0', color: '#5C5650', borderRadius: 8, padding: '8px 12px', fontSize: 13, marginBottom: 16 }}>{info}</div>}
          <form onSubmit={requestCode} style={{ marginBottom: 20 }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: '#5C5650', letterSpacing: 0.5, display: 'block', marginBottom: 6 }}>Correo</label>
            <div style={{ display: 'flex', alignItems: 'center', border: '1px solid #F5EDE0', borderRadius: 10, padding: '0 12px', background: '#FFF9F0' }}>
              <Mail size={14} color="#9B9590" />
              <input
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                autoComplete="email"
                placeholder="tu@correo.com"
                style={{ flex: 1, border: 'none', background: 'none', padding: '12px 10px', fontSize: 14, outline: 'none', color: '#2D2A26' }}
              />
            </div>
            <button type="submit" disabled={sending} style={{ width: '100%', marginTop: 12, background: '#2D2A26', color: '#fff', border: 'none', borderRadius: 12, padding: '12px', fontSize: 14, fontWeight: 700, cursor: 'pointer', minHeight: 44 }}>
              {sending ? 'Enviando...' : 'Enviar código'}
            </button>
          </form>
          <form onSubmit={verifyCode}>
            <label style={{ fontSize: 11, fontWeight: 700, color: '#5C5650', letterSpacing: 0.5, display: 'block', marginBottom: 6 }}>Código de un solo uso</label>
            <div style={{ display: 'flex', alignItems: 'center', border: '1px solid #F5EDE0', borderRadius: 10, padding: '0 12px', background: '#FFF9F0' }}>
              <KeyRound size={14} color="#9B9590" />
              <input
                inputMode="numeric"
                autoComplete="one-time-code"
                value={code}
                onChange={(e) => setCode(e.target.value)}
                required
                placeholder="000000"
                style={{ flex: 1, border: 'none', background: 'none', padding: '12px 10px', fontSize: 14, outline: 'none', color: '#2D2A26', letterSpacing: 2 }}
              />
            </div>
            <button type="submit" disabled={entering} style={{ width: '100%', marginTop: 12, background: '#D4A030', color: '#fff', border: 'none', borderRadius: 12, padding: '14px', fontSize: 14, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, minHeight: 44 }}>
              {entering ? 'Entrando...' : <>Entrar <ArrowRight size={16} /></>}
            </button>
          </form>
          <p style={{ fontSize: 12, color: '#9B9590', marginTop: 16, lineHeight: 1.5 }}>
            Si el correo no está configurado para enviar, pide a un administrador el enlace de acceso. El enlace es de un solo uso.
          </p>
        </div>
      </div>
    </div>
  );
}
