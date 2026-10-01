'use client';

import { useEffect, useState, type FormEvent } from 'react';
import { API_BASE } from '../../lib/api';
import { useTranslation } from '../../lib/i18n';

type Template = { id: string; label: string; description: string };
type Business = { slug: string; name: string; industry?: string; description?: string; template?: string | null };

const COPY = {
  es: {
    title: 'Nueva empresa',
    intro: 'Crea un espacio en blanco dentro de esta instancia. Max-e lo opera con CRM, ingreso, redes (con aprobación), paquetes, agenda y finanzas. Sin módulos de otra industria y sin precios inventados.',
    name: 'Nombre',
    industry: 'Industria',
    description: 'Descripción',
    template: 'Plantilla (opcional)',
    none: 'En blanco',
    create: 'Crear empresa',
    yours: 'Empresas',
    empty: 'Todavía no hay empresas adicionales.',
    denied: 'Sin acceso. Esta edición solo está disponible para cuentas autorizadas.',
    email: 'Tu email (cuenta autorizada)',
  },
  en: {
    title: 'New company',
    intro: 'Create a blank workspace in this instance. Max-e runs it with CRM, intake, social (approval required), packages, scheduling, and finance. No industry-specific modules and no invented prices.',
    name: 'Name',
    industry: 'Industry',
    description: 'Description',
    template: 'Template (optional)',
    none: 'Blank',
    create: 'Create company',
    yours: 'Companies',
    empty: 'No additional companies yet.',
    denied: 'No access. This edition is only available to authorized accounts.',
    email: 'Your email (authorized account)',
  },
};

export default function NuevaEmpresaPage() {
  const { locale, setLocale } = useTranslation();
  const text = locale === 'en' ? COPY.en : COPY.es;
  const [email, setEmail] = useState('');
  const [name, setName] = useState('');
  const [industry, setIndustry] = useState('');
  const [description, setDescription] = useState('');
  const [template, setTemplate] = useState('');
  const [templates, setTemplates] = useState<Template[]>([]);
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const headers = (): HeadersInit => {
    const h: Record<string, string> = { 'Content-Type': 'application/json' };
    if (email.trim()) h['X-User-Email'] = email.trim();
    return h;
  };

  async function load() {
    const [tplRes, bizRes] = await Promise.all([
      fetch(`${API_BASE}/api/v1/businesses/templates`, { headers: headers() }),
      fetch(`${API_BASE}/api/v1/businesses`, { headers: headers() }),
    ]);
    if (tplRes.status === 403 || bizRes.status === 403) {
      setError(text.denied);
      return;
    }
    setError('');
    if (tplRes.ok) {
      const data = await tplRes.json();
      setTemplates(data.templates || []);
    }
    if (bizRes.ok) {
      const data = await bizRes.json();
      setBusinesses(data.businesses || []);
    }
  }

  useEffect(() => {
    load().catch(() => setError(text.denied));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [locale]);

  async function onSubmit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/v1/businesses`, {
        method: 'POST',
        headers: headers(),
        body: JSON.stringify({
          name,
          industry,
          description,
          template: template || null,
        }),
      });
      const body = await res.json().catch(() => ({}));
      if (res.status === 403) {
        setError(body.detail || text.denied);
        return;
      }
      if (!res.ok) {
        setError(body.detail || 'Error');
        return;
      }
      setName('');
      setIndustry('');
      setDescription('');
      setTemplate('');
      await load();
    } finally {
      setBusy(false);
    }
  }

  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: 24, fontFamily: 'Nunito, sans-serif', color: '#2D2A26' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <p style={{ margin: 0, letterSpacing: 1, color: '#D4A030', fontWeight: 700, fontSize: 12 }}>EL PORTAL DE LA ALEGRÍA</p>
        <button type="button" onClick={() => setLocale(locale === 'es' ? 'en' : 'es')} style={{ border: '1px solid #e5e2dc', background: '#fff', borderRadius: 6, padding: '4px 8px', cursor: 'pointer' }}>
          {locale === 'es' ? 'EN' : 'ES'}
        </button>
      </div>
      <h1 style={{ fontFamily: 'Playfair Display, serif', fontSize: 36, margin: '0 0 8px' }}>{text.title}</h1>
      <p style={{ color: '#5C5650', lineHeight: 1.5 }}>{text.intro}</p>
      <label style={{ display: 'block', fontSize: 13, marginBottom: 12 }}>
        {text.email}
        <input value={email} onChange={(e) => setEmail(e.target.value)} onBlur={() => load()} style={{ display: 'block', width: '100%', marginTop: 4, padding: 8 }} />
      </label>
      {error && <p role="alert" style={{ color: '#9b2c2c' }}>{error}</p>}
      <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12, marginTop: 8 }}>
        <label style={{ fontSize: 13 }}>
          {text.name}
          <input required value={name} onChange={(e) => setName(e.target.value)} style={{ display: 'block', width: '100%', marginTop: 4, padding: 8 }} />
        </label>
        <label style={{ fontSize: 13 }}>
          {text.industry}
          <input value={industry} onChange={(e) => setIndustry(e.target.value)} style={{ display: 'block', width: '100%', marginTop: 4, padding: 8 }} />
        </label>
        <label style={{ fontSize: 13 }}>
          {text.description}
          <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} style={{ display: 'block', width: '100%', marginTop: 4, padding: 8 }} />
        </label>
        <label style={{ fontSize: 13 }}>
          {text.template}
          <select value={template} onChange={(e) => setTemplate(e.target.value)} style={{ display: 'block', width: '100%', marginTop: 4, padding: 8 }}>
            <option value="">{text.none}</option>
            {templates.map((tpl) => (
              <option key={tpl.id} value={tpl.id}>{tpl.label}</option>
            ))}
          </select>
        </label>
        <button type="submit" disabled={busy} style={{ background: '#D4A030', color: '#fff', border: 'none', borderRadius: 8, padding: '12px 16px', fontWeight: 700, cursor: 'pointer' }}>
          {text.create}
        </button>
      </form>
      <h2 style={{ marginTop: 32, fontSize: 18 }}>{text.yours}</h2>
      {businesses.length === 0 ? <p>{text.empty}</p> : (
        <ul>
          {businesses.map((biz) => (
            <li key={biz.slug}>
              <strong>{biz.name}</strong>
              {biz.industry ? ` — ${biz.industry}` : ''}
              {biz.template ? ` (${biz.template})` : ''}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}
