'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { ampSignup } from '../../lib/amp-auth';
import { Flame, User, Mail, Lock, ArrowRight } from 'lucide-react';

export default function AmpSignup() {
  const router = useRouter();
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 6) { setError('La contraseña debe tener al menos 6 caracteres'); return; }
    setLoading(true); setError('');
    try {
      await ampSignup({ name, email, password });
      router.push('/amp/dashboard');
    } catch (err: any) { setError(err.message); }
    setLoading(false);
  };

  const inputStyle = { flex: 1, border: 'none', background: 'none', padding: '12px 10px', fontSize: 14, outline: 'none', color: '#2D2A26' };
  const fieldStyle = { display: 'flex', alignItems: 'center', border: '1px solid #F5EDE0', borderRadius: 10, padding: '0 12px', background: '#FFF9F0' };

  return (
    <div style={{ minHeight: '100vh', background: 'linear-gradient(135deg, #2D2A26, #3d3530)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}>
      <div style={{ width: '100%', maxWidth: 400 }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{ width: 48, height: 48, borderRadius: 14, background: '#D4A030', display: 'inline-flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
            <Flame size={24} color="#fff" />
          </div>
          <h1 style={{ fontFamily: "'Playfair Display', serif", fontSize: 24, color: '#FFF9F0', margin: '0 0 4px' }}>Únete a AMP</h1>
          <p style={{ fontSize: 13, color: '#9B9590' }}>Comienza tu transformación hoy</p>
        </div>
        <form onSubmit={handleSubmit} style={{ background: '#fff', borderRadius: 16, padding: 28, boxShadow: '0 8px 32px rgba(0,0,0,0.2)' }}>
          {error && <div style={{ background: '#fef2f2', color: '#dc2626', borderRadius: 8, padding: '8px 12px', fontSize: 12, marginBottom: 16 }}>{error}</div>}
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: '#5C5650', letterSpacing: 0.5, display: 'block', marginBottom: 6 }}>Nombre</label>
            <div style={fieldStyle}><User size={14} color="#9B9590" /><input value={name} onChange={e => setName(e.target.value)} required placeholder="Tu nombre" style={inputStyle} /></div>
          </div>
          <div style={{ marginBottom: 16 }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: '#5C5650', letterSpacing: 0.5, display: 'block', marginBottom: 6 }}>Email</label>
            <div style={fieldStyle}><Mail size={14} color="#9B9590" /><input type="email" value={email} onChange={e => setEmail(e.target.value)} required placeholder="tu@email.com" style={inputStyle} /></div>
          </div>
          <div style={{ marginBottom: 24 }}>
            <label style={{ fontSize: 11, fontWeight: 700, color: '#5C5650', letterSpacing: 0.5, display: 'block', marginBottom: 6 }}>Contraseña</label>
            <div style={fieldStyle}><Lock size={14} color="#9B9590" /><input type="password" value={password} onChange={e => setPassword(e.target.value)} required placeholder="Mínimo 6 caracteres" style={inputStyle} /></div>
          </div>
          <button type="submit" disabled={loading}
            style={{ width: '100%', background: '#D4A030', color: '#fff', border: 'none', borderRadius: 12, padding: '14px', fontSize: 14, fontWeight: 700, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8, opacity: loading ? 0.6 : 1 }}>
            {loading ? 'Creando cuenta...' : <>Crear Cuenta Gratis <ArrowRight size={16} /></>}
          </button>
          <p style={{ textAlign: 'center', fontSize: 13, color: '#9B9590', marginTop: 16 }}>
            ¿Ya tienes cuenta? <a href="/amp/login" style={{ color: '#D4A030', fontWeight: 700, textDecoration: 'none' }}>Ingresar</a>
          </p>
        </form>
        <p style={{ textAlign: 'center', marginTop: 20 }}>
          <a href="/amp" style={{ fontSize: 12, color: '#9B9590', textDecoration: 'none' }}>← Volver al inicio</a>
        </p>
      </div>
    </div>
  );
}
