'use client';

import { Suspense, useEffect, useState, type FormEvent } from 'react';
import { useSearchParams } from 'next/navigation';
import { API_BASE } from '../../lib/api';
import { useTranslation } from '../../lib/i18n';
import { useAssistantName } from '../../lib/assistant';

type Template = { id: string; label: string; description: string };
type Business = { slug: string; name: string; industry?: string; description?: string; template?: string | null };

const COPY = {
  es: {
    title: 'Empresas',
    intro: 'te hace una pregunta por pantalla y arma la empresa con tus respuestas. Puedes guardar y seguir después.',
    primary: 'Nueva empresa (entrevista guiada)',
    quick: 'Configuración rápida',
    back: 'Volver a la entrevista guiada',
    saved: 'Guardamos tu entrevista. Ábrela de nuevo cuando quieras.',
    resume: 'Tienes una entrevista a medias. El botón de arriba la retoma donde la dejaste.',
    quickTitle: 'Configuración rápida',
    quickIntro: 'Un formulario corto, si ya sabes los datos. La entrevista guiada sigue siendo el camino principal.',
    name: 'Nombre',
    industry: 'Industria',
    description: 'Descripción',
    template: 'Plantilla (opcional)',
    none: 'En blanco',
    create: 'Crear empresa',
    yours: 'Tus empresas',
    empty: 'Todavía no hay empresas adicionales.',
    denied: 'Sin acceso. Entra con tu correo autorizado.',
    login: 'Iniciar sesión',
  },
  en: {
    title: 'Companies',
    intro: 'asks one question per screen and builds the company from your answers. You can save and come back.',
    primary: 'New company (guided interview)',
    quick: 'Quick setup',
    back: 'Back to the guided interview',
    saved: 'We saved your interview. Open it again whenever you want.',
    resume: 'You have an interview in progress. The button above picks it up where you left it.',
    quickTitle: 'Quick setup',
    quickIntro: 'A short form, if you already know the details. The guided interview is still the main path.',
    name: 'Name',
    industry: 'Industry',
    description: 'Description',
    template: 'Template (optional)',
    none: 'Blank',
    create: 'Create company',
    yours: 'Your companies',
    empty: 'No additional companies yet.',
    denied: 'No access. Sign in with an authorized email.',
    login: 'Sign in',
  },
};

function EmpresasPage() {
  const { locale, setLocale } = useTranslation();
  const assistant = useAssistantName();
  const params = useSearchParams();
  const text = locale === 'en' ? COPY.en : COPY.es;
  const quick = params.get('rapida') === '1';
  const justSaved = params.get('borrador') === '1';
  const [name, setName] = useState('');
  const [industry, setIndustry] = useState('');
  const [description, setDescription] = useState('');
  const [template, setTemplate] = useState('');
  const [templates, setTemplates] = useState<Template[]>([]);
  const [businesses, setBusinesses] = useState<Business[]>([]);
  const [hasDraft, setHasDraft] = useState(false);
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const headers = (): HeadersInit => ({ 'Content-Type': 'application/json' });

  async function load() {
    const [tplRes, bizRes, draftRes] = await Promise.all([
      fetch(`${API_BASE}/api/v1/businesses/templates`, { headers: headers(), credentials: 'include' }),
      fetch(`${API_BASE}/api/v1/businesses`, { headers: headers(), credentials: 'include' }),
      fetch(`${API_BASE}/api/v1/businesses/interview`, { headers: headers(), credentials: 'include' }),
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
    if (draftRes.ok) {
      const draft = await draftRes.json();
      const answers = draft.answers || {};
      setHasDraft(draft.status === 'draft' && Boolean(answers.legal_name || answers.trade_name || draft.step > 0));
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
        credentials: 'include',
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
      if (body.slug) {
        window.location.href = `/amp/empresas/${body.slug}`;
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
    <main style={{ maxWidth: 720, margin: '0 auto', padding: '24px 16px 64px', fontFamily: 'Nunito, sans-serif', color: '#2D2A26', background: '#FFF9F0', minHeight: '100vh', boxSizing: 'border-box' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16, gap: 12 }}>
        <p style={{ margin: 0, letterSpacing: 1, color: '#D4A030', fontWeight: 700, fontSize: 12 }}>EL PORTAL DE LA ALEGRÍA</p>
        <button type="button" onClick={() => setLocale(locale === 'es' ? 'en' : 'es')} style={{ border: '1px solid #e5e2dc', background: '#fff', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', minHeight: 36 }}>
          {locale === 'es' ? 'EN' : 'ES'}
        </button>
      </div>
      <h1 style={{ fontFamily: 'Playfair Display, serif', fontSize: 36, margin: '0 0 8px' }}>{text.title}</h1>
      <p style={{ color: '#5C5650', lineHeight: 1.5 }}>{assistant} {text.intro}</p>
      {justSaved && <p style={{ background: '#fff', border: '1px solid #F0E6D8', borderRadius: 12, padding: 12 }}>{text.saved}</p>}
      {hasDraft && !justSaved && <p style={{ color: '#5C5650' }}>{text.resume}</p>}
      {error && (
        <p role="alert" style={{ color: '#9b2c2c' }}>
          {error}{' '}
          <a href="/login" style={{ color: '#D4A030', fontWeight: 700 }}>{text.login}</a>
        </p>
      )}
      <a href="/amp/empresas/entrevista" style={{ display: 'block', textAlign: 'center', textDecoration: 'none', background: '#D4A030', color: '#fff', borderRadius: 12, padding: '14px 16px', fontWeight: 800, marginTop: 16, minHeight: 48 }}>
        {text.primary}
      </a>
      <p style={{ marginTop: 12 }}>
        {quick ? (
          <a href="/amp/empresas" style={{ color: '#9B9590', fontSize: 14 }}>{text.back}</a>
        ) : (
          <a href="/amp/empresas?rapida=1" style={{ color: '#9B9590', fontSize: 14 }}>{text.quick}</a>
        )}
      </p>
      {quick && (
        <form onSubmit={onSubmit} style={{ display: 'grid', gap: 12, marginTop: 8, background: '#fff', border: '1px solid #F0E6D8', borderRadius: 16, padding: 16 }}>
          <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: 22, margin: 0 }}>{text.quickTitle}</h2>
          <p style={{ color: '#5C5650', margin: 0 }}>{text.quickIntro}</p>
          <label style={{ fontSize: 13 }}>
            {text.name}
            <input required value={name} onChange={(e) => setName(e.target.value)} style={{ display: 'block', width: '100%', marginTop: 4, padding: 12, fontSize: 16, borderRadius: 10, border: '1px solid #E7E0D6' }} />
          </label>
          <label style={{ fontSize: 13 }}>
            {text.industry}
            <input value={industry} onChange={(e) => setIndustry(e.target.value)} style={{ display: 'block', width: '100%', marginTop: 4, padding: 12, fontSize: 16, borderRadius: 10, border: '1px solid #E7E0D6' }} />
          </label>
          <label style={{ fontSize: 13 }}>
            {text.description}
            <textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={3} style={{ display: 'block', width: '100%', marginTop: 4, padding: 12, fontSize: 16, borderRadius: 10, border: '1px solid #E7E0D6' }} />
          </label>
          <label style={{ fontSize: 13 }}>
            {text.template}
            <select value={template} onChange={(e) => setTemplate(e.target.value)} style={{ display: 'block', width: '100%', marginTop: 4, padding: 12, fontSize: 16, borderRadius: 10, border: '1px solid #E7E0D6' }}>
              <option value="">{text.none}</option>
              {templates.map((tpl) => (
                <option key={tpl.id} value={tpl.id}>{tpl.label}</option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={busy} style={{ background: '#2D2A26', color: '#fff', border: 'none', borderRadius: 10, padding: '12px 16px', fontWeight: 700, cursor: 'pointer', minHeight: 48 }}>
            {text.create}
          </button>
        </form>
      )}
      <h2 style={{ marginTop: 32, fontSize: 18 }}>{text.yours}</h2>
      {businesses.length === 0 ? <p>{text.empty}</p> : (
        <ul style={{ listStyle: 'none', padding: 0, display: 'grid', gap: 8 }}>
          {businesses.map((biz) => (
            <li key={biz.slug} style={{ background: '#fff', border: '1px solid #F0E6D8', borderRadius: 12, padding: '12px 14px' }}>
              <a href={`/amp/empresas/${biz.slug}`} style={{ color: '#2D2A26', fontWeight: 800, textDecoration: 'none' }}>{biz.name}</a>
              {biz.industry ? <span style={{ color: '#5C5650' }}> — {biz.industry}</span> : null}
              {biz.template ? <span style={{ color: '#9B9590' }}> ({biz.template})</span> : null}
            </li>
          ))}
        </ul>
      )}
    </main>
  );
}

export default function NuevaEmpresaPage() {
  return (
    <Suspense fallback={<main style={{ padding: 24, background: '#FFF9F0', minHeight: '100vh' }}>…</main>}>
      <EmpresasPage />
    </Suspense>
  );
}
