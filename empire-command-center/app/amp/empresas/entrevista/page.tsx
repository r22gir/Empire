'use client';

import { useEffect, useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { API_BASE } from '../../../lib/api';
import { useTranslation } from '../../../lib/i18n';
import { useAssistantName } from '../../../lib/assistant';
import { useEdition } from '../../../lib/edition';
import { ARGOS_OPTIONS, interviewSteps, welcomeCopy } from '../../../lib/interviewWelcome';

type Template = { id: string; label: string; description: string };
type Item = { name: string; kind: 'servicio' | 'producto'; price: string };
type Answers = {
  legal_name: string;
  trade_name: string;
  country: string;
  city: string;
  email: string;
  phone: string;
  website: string;
  template: string;
  industry_description: string;
  sells: 'servicios' | 'productos' | 'ambos';
  items: Item[];
  customer_who: string;
  customer_type: 'b2b' | 'b2c' | 'ambos';
  first_customer: { name: string; email: string; phone: string };
  currency: 'COP' | 'USD';
  fiscal_year_start: string;
  tax_id: string;
  charges_iva: boolean;
  payment_methods: string[];
  team_mode: 'solo' | 'equipo';
  roles: string[];
  modules: Record<string, boolean>;
  fact_visibility: Record<string, 'public' | 'confidential'>;
  phase_name: string;
  lots: { lot_number: string; status: string; area_m2: string; price: string }[];
  argos_consent: '' | 'all' | 'public' | 'later';
};

const MODULES = [
  { id: 'crm', es: 'CRM — contactos y clientes', en: 'CRM — contacts and customers' },
  { id: 'quotes', es: 'Cotizaciones', en: 'Quotes' },
  { id: 'invoices', es: 'Facturas', en: 'Invoices' },
  { id: 'socialforge', es: 'SocialForge — redes, con tu aprobación antes de publicar', en: 'SocialForge — social posts, with your approval' },
  { id: 'leadforge', es: 'LeadForge — prospectos', en: 'LeadForge — prospects' },
  { id: 'courses', es: 'Cursos', en: 'Courses' },
];

const PAYMENTS = [
  { id: 'efectivo', es: 'Efectivo', en: 'Cash' },
  { id: 'transferencia', es: 'Transferencia', en: 'Transfer' },
  { id: 'tarjeta', es: 'Tarjeta', en: 'Card' },
  { id: 'nequi', es: 'Nequi', en: 'Nequi' },
  { id: 'daviplata', es: 'Daviplata', en: 'Daviplata' },
  { id: 'pse', es: 'PSE', en: 'PSE' },
];

const MONTHS = [
  ['01-01', 'Enero', 'January'],
  ['02-01', 'Febrero', 'February'],
  ['03-01', 'Marzo', 'March'],
  ['04-01', 'Abril', 'April'],
  ['05-01', 'Mayo', 'May'],
  ['06-01', 'Junio', 'June'],
  ['07-01', 'Julio', 'July'],
  ['08-01', 'Agosto', 'August'],
  ['09-01', 'Septiembre', 'September'],
  ['10-01', 'Octubre', 'October'],
  ['11-01', 'Noviembre', 'November'],
  ['12-01', 'Diciembre', 'December'],
] as const;

type ArgosItem = { key: string; label: string; value: string; text: string };

function emptyAnswers(): Answers {
  return {
    legal_name: '',
    trade_name: '',
    country: 'Colombia',
    city: '',
    email: '',
    phone: '',
    website: '',
    template: '',
    industry_description: '',
    sells: 'ambos',
    items: [{ name: '', kind: 'servicio', price: '' }],
    customer_who: '',
    customer_type: 'b2b',
    first_customer: { name: '', email: '', phone: '' },
    currency: 'COP',
    fiscal_year_start: '01-01',
    tax_id: '',
    charges_iva: false,
    payment_methods: [],
    team_mode: 'solo',
    roles: [],
    modules: Object.fromEntries(MODULES.map((mod) => [mod.id, false])),
    fact_visibility: {},
    phase_name: '',
    lots: [],
    argos_consent: '',
  };
}

function parsePrice(raw: string): number | null {
  const text = raw.trim().replace(/\s/g, '').replace(/\$/g, '');
  if (!text) return null;
  const numeric = text.replace(/[^\d.]/g, '');
  if (!numeric) return null;
  const value = Number(numeric);
  if (!Number.isFinite(value) || value < 0) return null;
  return value;
}

function fromServer(raw: Partial<Answers> | undefined): Answers {
  const base = emptyAnswers();
  if (!raw) return base;
  const items = Array.isArray(raw.items) ? raw.items : [];
  const cleanItems: Item[] = items.map((item) => ({
    name: item.name || '',
    kind: item.kind === 'producto' ? 'producto' : 'servicio',
    price: item.price == null || String(item.price) === '' ? '' : String(item.price),
  }));
  return {
    ...base,
    ...raw,
    country: raw.country || 'Colombia',
    currency: raw.currency === 'USD' ? 'USD' : 'COP',
    sells: raw.sells === 'servicios' || raw.sells === 'productos' ? raw.sells : 'ambos',
    customer_type: raw.customer_type === 'b2c' || raw.customer_type === 'ambos' ? raw.customer_type : 'b2b',
    team_mode: raw.team_mode === 'equipo' ? 'equipo' : 'solo',
    fiscal_year_start: raw.fiscal_year_start || '01-01',
    items: cleanItems.length ? cleanItems : [{ name: '', kind: 'servicio', price: '' }],
    first_customer: { ...base.first_customer, ...(raw.first_customer || {}) },
    payment_methods: Array.isArray(raw.payment_methods) ? raw.payment_methods : [],
    roles: Array.isArray(raw.roles) ? raw.roles : [],
    modules: { ...base.modules, ...(raw.modules || {}) },
    charges_iva: Boolean(raw.charges_iva),
    fact_visibility: { ...base.fact_visibility, ...(raw.fact_visibility || {}) },
    phase_name: raw.phase_name || '',
    argos_consent: raw.argos_consent === 'all' || raw.argos_consent === 'public' || raw.argos_consent === 'later' ? raw.argos_consent : '',
    lots: Array.isArray(raw.lots)
      ? raw.lots.map((lot) => ({
          lot_number: lot.lot_number || '',
          status: lot.status || 'available',
          area_m2: lot.area_m2 == null || String(lot.area_m2) === '' ? '' : String(lot.area_m2),
          price: lot.price == null || String(lot.price) === '' ? '' : String(lot.price),
        }))
      : [],
  };
}

function confirmRows(answers: Answers): { key: string; label: string; value: string }[] {
  const rows: { key: string; label: string; value: string }[] = [];
  const push = (key: string, label: string, value: string) => {
    const text = (value || '').trim();
    if (!text) return;
    rows.push({ key, label, value: text });
  };
  push('legal_name', 'Nombre legal', answers.legal_name);
  push('trade_name', 'Nombre comercial', answers.trade_name);
  push('city', 'Ciudad', answers.city);
  push('email', 'Correo', answers.email);
  push('phone', 'Teléfono', answers.phone);
  push('website', 'Sitio web', answers.website);
  push('tax_id', 'NIT', answers.tax_id);
  push('industry_description', 'Actividad', answers.industry_description);
  push('customer_who', 'Clientes', answers.customer_who);
  push('first_customer', 'Primer cliente', answers.first_customer.name);
  answers.items.forEach((item) => {
    if (item.name.trim() && item.price.trim()) push(`price:${item.name.trim()}`, `Precio de ${item.name.trim()}`, item.price.trim());
  });
  return rows;
}

function toPayload(answers: Answers) {
  return {
    ...answers,
    items: answers.items
      .filter((item) => item.name.trim())
      .map((item) => ({
        name: item.name.trim(),
        kind: item.kind,
        price: parsePrice(item.price),
      })),
  };
}

const inputStyle: React.CSSProperties = {
  display: 'block',
  width: '100%',
  marginTop: 6,
  padding: '12px',
  fontSize: 16,
  borderRadius: 10,
  border: '1px solid #E7E0D6',
  background: '#fff',
  color: '#2D2A26',
  fontFamily: 'Nunito, sans-serif',
};

const cardStyle: React.CSSProperties = {
  background: '#fff',
  border: '1px solid #F0E6D8',
  borderRadius: 16,
  padding: 16,
  marginTop: 16,
};

export default function EntrevistaPage() {
  const router = useRouter();
  const { locale, setLocale } = useTranslation();
  const assistant = useAssistantName();
  const constructionShell = useEdition() === 'maxine';
  const es = locale !== 'en';
  const t = (spanish: string, english: string) => (es ? spanish : english);
  const [step, setStep] = useState(0);
  const [reached, setReached] = useState(0);
  const [answers, setAnswers] = useState<Answers>(emptyAnswers);
  const [templates, setTemplates] = useState<Template[]>([]);
  const [roleDraft, setRoleDraft] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [resumed, setResumed] = useState(false);
  const [argosCatalog, setArgosCatalog] = useState<{ public: ArgosItem[]; all: ArgosItem[] }>({ public: [], all: [] });
  const steps = interviewSteps(constructionShell ? 'maxine' : 'amp');
  const welcome = welcomeCopy(constructionShell ? 'maxine' : 'amp');
  const last = steps.length - 1;
  const currentId = steps[Math.min(step, last)]?.id || 'bienvenida';

  useEffect(() => {
    let cancelled = false;
    Promise.all([
      fetch(`${API_BASE}/api/v1/businesses/interview`, { credentials: 'include' }),
      fetch(`${API_BASE}/api/v1/businesses/templates`, { credentials: 'include' }),
    ]).then(async ([draftRes, tplRes]) => {
      if (cancelled) return;
      if (draftRes.status === 403 || tplRes.status === 403) {
        setError(t('Sin acceso. Entra con tu correo autorizado.', 'No access. Sign in with an authorized email.'));
        setLoading(false);
        return;
      }
      if (tplRes.ok) {
        const data = await tplRes.json();
        setTemplates(data.templates || []);
      }
      if (draftRes.ok) {
        const draft = await draftRes.json();
        setAnswers(fromServer(draft.answers));
        if (draft.argos_catalog) {
          setArgosCatalog({
            public: Array.isArray(draft.argos_catalog.public) ? draft.argos_catalog.public : [],
            all: Array.isArray(draft.argos_catalog.all) ? draft.argos_catalog.all : [],
          });
        }
        if (draft.status === 'draft') {
          const savedStep = typeof draft.step === 'number' ? draft.step : 0;
          setStep(savedStep);
          setReached(savedStep);
          setResumed(true);
        }
      }
      setLoading(false);
    }).catch(() => {
      if (!cancelled) {
        setError(t('No pude conectar con el servidor.', 'Could not reach the server.'));
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
    // Load once. The language toggle only changes labels.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function scrollTop() {
    window.scrollTo(0, 0);
    document.documentElement.scrollTop = 0;
    document.body.scrollTop = 0;
  }

  async function persist(nextStep: number, nextAnswers: Answers): Promise<boolean> {
    setBusy(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/v1/businesses/interview`, {
        method: 'PUT',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step: nextStep, answers: toPayload(nextAnswers) }),
      });
      const body = await res.json().catch(() => ({}));
      if (res.status === 403) {
        setError(body.detail || t('Sin acceso. Entra con tu correo autorizado.', 'No access. Sign in with an authorized email.'));
        return false;
      }
      if (!res.ok) {
        setError(body.detail || t('No pude guardar. Inténtalo de nuevo.', 'Could not save. Try again.'));
        return false;
      }
      return true;
    } catch {
      setError(t('No pude conectar con el servidor.', 'Could not reach the server.'));
      return false;
    } finally {
      setBusy(false);
    }
  }

  function validate(): boolean {
    if (currentId === 'empresa' && !answers.legal_name.trim()) {
      setError(t('Escribe el nombre legal para seguir.', 'Enter the legal name to continue.'));
      return false;
    }
    if (currentId === 'argos' && !answers.argos_consent) {
      setError(t('Elige si cargo Argos Campestre.', 'Choose whether I load Argos Campestre.'));
      return false;
    }
    setError('');
    return true;
  }

  async function onNext() {
    if (!validate()) return;
    const next = Math.min(step + 1, last);
    const ok = await persist(next, answers);
    if (!ok) return;
    setStep(next);
    setReached((current) => Math.max(current, next));
    scrollTop();
  }

  async function onBack() {
    const next = Math.max(step - 1, 0);
    await persist(next, answers);
    setStep(next);
    scrollTop();
  }

  async function onSaveLater() {
    const ok = await persist(step, answers);
    if (!ok) return;
    router.push('/amp/empresas?borrador=1');
  }

  async function jump(index: number) {
    if (index > reached || index === step) return;
    const ok = await persist(index, answers);
    if (!ok) return;
    setStep(index);
    scrollTop();
  }

  async function finish() {
    if (!answers.legal_name.trim()) {
      setError(t('Escribe el nombre legal antes de crear la empresa.', 'Enter the legal name before creating the company.'));
      setStep(Math.max(steps.findIndex((item) => item.id === 'empresa'), 0));
      return;
    }
    setBusy(true);
    setError('');
    try {
      const res = await fetch(`${API_BASE}/api/v1/businesses/interview/finish`, {
        method: 'POST',
        credentials: 'include',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ step: last, answers: toPayload(answers) }),
      });
      const body = await res.json().catch(() => ({}));
      if (res.status === 403) {
        setError(body.detail || t('Sin acceso. Entra con tu correo autorizado.', 'No access.'));
        return;
      }
      if (!res.ok) {
        setError(body.detail || t('No pude crear la empresa.', 'Could not create the company.'));
        return;
      }
      router.push(`/amp/empresas/${body.slug}`);
    } catch {
      setError(t('No pude conectar con el servidor.', 'Could not reach the server.'));
    } finally {
      setBusy(false);
    }
  }

  function setItem(index: number, patch: Partial<Item>) {
    setAnswers((prev) => ({
      ...prev,
      items: prev.items.map((item, i) => (i === index ? { ...item, ...patch } : item)),
    }));
  }

  const label = (id: string) => {
    const row = steps.find((item) => item.id === id);
    return row ? (es ? row.es : row.en) : id;
  };
  const argosRows: ArgosItem[] = answers.argos_consent === 'all'
    ? argosCatalog.all
    : answers.argos_consent === 'public'
      ? argosCatalog.public
      : [];

  const progress = Math.round((step / last) * 100);

  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: '20px 16px 72px', fontFamily: 'Nunito, sans-serif', color: '#2D2A26', background: '#FFF9F0', minHeight: '100vh', boxSizing: 'border-box' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 12 }}>
        <a href="/amp/empresas" style={{ color: '#9B9590', fontSize: 14, textDecoration: 'none' }}>{t('← Empresas', '← Companies')}</a>
        <button type="button" onClick={() => setLocale(es ? 'en' : 'es')} style={{ border: '1px solid #e5e2dc', background: '#fff', borderRadius: 6, padding: '4px 8px', cursor: 'pointer', minHeight: 36 }}>
          {es ? 'EN' : 'ES'}
        </button>
      </div>
      <p style={{ letterSpacing: 1, color: '#D4A030', fontWeight: 800, fontSize: 12, margin: '16px 0 4px' }}>{assistant.toUpperCase()} · CENTRO DE MANDO</p>
      <h1 style={{ fontFamily: 'Playfair Display, serif', fontSize: 32, margin: '0 0 8px' }}>{t('Entrevista de la empresa', 'Company interview')}</h1>
      <p style={{ color: '#5C5650', marginTop: 0 }}>{t(`Paso ${Math.min(step, last) + 1} de ${steps.length}`, `Step ${Math.min(step, last) + 1} of ${steps.length}`)} · {es ? steps[Math.min(step, last)].es : steps[Math.min(step, last)].en}</p>
      <div role="progressbar" aria-valuenow={Math.min(step, last) + 1} aria-valuemin={1} aria-valuemax={steps.length} aria-label={t('Progreso de la entrevista', 'Interview progress')} style={{ height: 8, borderRadius: 99, background: '#F0E6D8', overflow: 'hidden' }}>
        <div style={{ width: `${progress}%`, height: '100%', background: '#D4A030' }} />
      </div>
      <ol style={{ display: 'flex', gap: 8, listStyle: 'none', padding: 0, margin: '12px 0 0', overflowX: 'auto' }}>
        {steps.map((item, index) => (
          <li key={item.id}>
            <button
              type="button"
              onClick={() => jump(index)}
              disabled={index > reached}
              aria-current={index === step ? 'step' : undefined}
              style={{
                border: 'none',
                background: index === step ? '#D4A030' : index <= reached ? '#2D2A26' : '#F3EDE3',
                color: index <= reached ? '#fff' : '#9B9590',
                borderRadius: 999,
                padding: '8px 12px',
                fontSize: 12,
                fontWeight: 700,
                whiteSpace: 'nowrap',
                cursor: index <= reached ? 'pointer' : 'default',
                minHeight: 36,
              }}
            >
              {index + 1}. {es ? item.es : item.en}
            </button>
          </li>
        ))}
      </ol>
      {resumed && step > 0 && (
        <p style={{ background: '#fff', border: '1px solid #F0E6D8', borderRadius: 12, padding: 12 }}>
          {t('Retomamos tu entrevista donde la dejaste.', 'We picked up your interview where you left it.')}
        </p>
      )}
      {error && <p role="alert" style={{ color: '#9b2c2c' }}>{error} {error.toLowerCase().includes('acceso') || error.toLowerCase().includes('access') ? <a href="/login" style={{ color: '#D4A030', fontWeight: 800 }}>{t('Iniciar sesión', 'Sign in')}</a> : null}</p>}
      {loading ? <p>{t('Cargando tu entrevista…', 'Loading your interview…')}</p> : (
        <section style={cardStyle}>
          {currentId === 'bienvenida' && (
            <>
              <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: 28, marginTop: 0 }}>{t(`Hola, soy ${assistant}.`, `Hi, I'm ${assistant}.`)}</h2>
              <p style={{ lineHeight: 1.6, fontSize: 17 }}>{es ? welcome.introEs : welcome.introEn}</p>
              <p style={{ fontWeight: 800, marginBottom: 8 }}>{t('Vamos a pasar por:', 'We will cover:')}</p>
              <ol style={{ lineHeight: 1.6, paddingLeft: 20, marginTop: 0 }}>
                {welcome.sections.map((section) => (
                  <li key={section.es}>{es ? section.es : section.en}</li>
                ))}
              </ol>
              {welcome.argosNoteEs && (
                <p style={{ lineHeight: 1.6, fontSize: 17 }}>{es ? welcome.argosNoteEs : welcome.argosNoteEn}</p>
              )}
            </>
          )}
          {currentId === 'argos' && (
            <>
              <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: 26, marginTop: 0 }}>{t('¿Cargo la información de Argos Campestre que Rafael ya tiene?', 'Should I load the Argos Campestre information Rafael already has?')}</h2>
              <p style={{ color: '#5C5650', lineHeight: 1.5 }}>{t('Queda Confidencial hasta que la apruebes en Confirmar datos. No invento precios ni datos legales.', 'It stays confidential until you approve it on Confirm facts. I do not invent prices or legal details.')}</p>
              <div style={{ display: 'grid', gap: 8 }}>
                {ARGOS_OPTIONS.map((option) => {
                  const selected = answers.argos_consent === option.id;
                  return (
                    <button key={option.id} type="button" onClick={() => setAnswers({ ...answers, argos_consent: option.id === 'all' || option.id === 'public' || option.id === 'later' ? option.id : '' })} style={{ textAlign: 'left', borderRadius: 12, border: selected ? '2px solid #D4A030' : '1px solid #E7E0D6', background: selected ? '#FFF9F0' : '#fff', padding: 12, cursor: 'pointer', minHeight: 48 }}>
                      <strong>{es ? option.es : option.en}</strong>
                      <div style={{ color: '#5C5650', fontSize: 14, marginTop: 4 }}>{es ? option.detailEs : option.detailEn}</div>
                    </button>
                  );
                })}
              </div>
            </>
          )}
          {currentId === 'empresa' && (
            <>
              <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: 26, marginTop: 0 }}>{t('¿Cómo se llama tu empresa?', 'What is your company called?')}</h2>
              <label>{t('Nombre legal', 'Legal name')}
                <input required value={answers.legal_name} onChange={(e) => setAnswers({ ...answers, legal_name: e.target.value })} style={inputStyle} />
              </label>
              <label style={{ display: 'block', marginTop: 12 }}>{t('Nombre comercial', 'Trade name')}
                <input value={answers.trade_name} onChange={(e) => setAnswers({ ...answers, trade_name: e.target.value })} placeholder={t('Si tus clientes te conocen con otro nombre', 'If customers know you by another name')} style={inputStyle} />
              </label>
              <label style={{ display: 'block', marginTop: 12 }}>{t('País', 'Country')}
                <input value={answers.country} onChange={(e) => setAnswers({ ...answers, country: e.target.value })} style={inputStyle} />
              </label>
              <label style={{ display: 'block', marginTop: 12 }}>{t('Ciudad', 'City')}
                <input value={answers.city} onChange={(e) => setAnswers({ ...answers, city: e.target.value })} style={inputStyle} />
              </label>
              <label style={{ display: 'block', marginTop: 12 }}>{t('Correo', 'Email')}
                <input type="email" value={answers.email} onChange={(e) => setAnswers({ ...answers, email: e.target.value })} style={inputStyle} />
              </label>
              <label style={{ display: 'block', marginTop: 12 }}>{t('Teléfono', 'Phone')}
                <input value={answers.phone} onChange={(e) => setAnswers({ ...answers, phone: e.target.value })} style={inputStyle} />
              </label>
              <label style={{ display: 'block', marginTop: 12 }}>{t('Sitio web', 'Website')}
                <input value={answers.website} onChange={(e) => setAnswers({ ...answers, website: e.target.value })} style={inputStyle} />
              </label>
            </>
          )}
          {currentId === 'industria' && (
            <>
              <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: 26, marginTop: 0 }}>{t('¿A qué te dedicas?', 'What do you do?')}</h2>
              <p style={{ color: '#5C5650' }}>{t('Elige una plantilla o empieza en blanco. El precio no se inventa.', 'Pick a template or start blank. Prices are never invented.')}</p>
              <div style={{ display: 'grid', gap: 8 }}>
                <button type="button" onClick={() => setAnswers({ ...answers, template: '' })} style={{ textAlign: 'left', borderRadius: 12, border: answers.template ? '1px solid #E7E0D6' : '2px solid #D4A030', background: answers.template ? '#fff' : '#FFF9F0', padding: 12, cursor: 'pointer', minHeight: 48 }}>
                  <strong>{t('En blanco', 'Blank')}</strong>
                  <div style={{ color: '#5C5650', fontSize: 14 }}>{t('Sin categorías de otra industria.', 'No categories from another industry.')}</div>
                </button>
                {templates.map((tpl) => (
                  <button key={tpl.id} type="button" onClick={() => setAnswers({ ...answers, template: tpl.id })} style={{ textAlign: 'left', borderRadius: 12, border: answers.template === tpl.id ? '2px solid #D4A030' : '1px solid #E7E0D6', background: answers.template === tpl.id ? '#FFF9F0' : '#fff', padding: 12, cursor: 'pointer' }}>
                    <strong>{tpl.label}</strong>
                    <div style={{ color: '#5C5650', fontSize: 14 }}>{tpl.description}</div>
                  </button>
                ))}
              </div>
              <label style={{ display: 'block', marginTop: 16 }}>{t('Cuéntame, en tus palabras, qué hace la empresa.', 'In your own words, what does the company do?')}
                <textarea value={answers.industry_description} onChange={(e) => setAnswers({ ...answers, industry_description: e.target.value })} rows={4} style={inputStyle} />
              </label>
            </>
          )}
          {currentId === 'oferta' && (
            <>
              <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: 26, marginTop: 0 }}>{t('¿Qué vendes?', 'What do you sell?')}</h2>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {(['servicios', 'productos', 'ambos'] as const).map((option) => (
                  <button key={option} type="button" onClick={() => setAnswers({ ...answers, sells: option })} style={{ borderRadius: 999, border: 'none', background: answers.sells === option ? '#D4A030' : '#F3EDE3', color: answers.sells === option ? '#fff' : '#2D2A26', padding: '8px 14px', fontWeight: 700, cursor: 'pointer', minHeight: 40 }}>
                    {option === 'servicios' ? t('Servicios', 'Services') : option === 'productos' ? t('Productos', 'Products') : t('Los dos', 'Both')}
                  </button>
                ))}
              </div>
              <p style={{ color: '#5C5650' }}>{t('Agrega algunos para empezar. El precio lo pones tú. Si lo dejas vacío, queda sin definir.', 'Add a few to start. You set the price. If you leave it empty, it stays unset.')}</p>
              {answers.items.map((item, index) => (
                <div key={index} style={{ display: 'grid', gap: 8, marginTop: 12, gridTemplateColumns: '1fr', }}>
                  <input aria-label={t('Nombre del ítem', 'Item name')} value={item.name} onChange={(e) => setItem(index, { name: e.target.value })} placeholder={t('Nombre', 'Name')} style={inputStyle} />
                  <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                    <select aria-label={t('Tipo', 'Type')} value={item.kind} onChange={(e) => setItem(index, { kind: e.target.value === 'producto' ? 'producto' : 'servicio' })} style={{ ...inputStyle, marginTop: 0, flex: '1 1 140px' }}>
                      <option value="servicio">{t('Servicio', 'Service')}</option>
                      <option value="producto">{t('Producto', 'Product')}</option>
                    </select>
                    <input aria-label={t('Precio', 'Price')} value={item.price} onChange={(e) => setItem(index, { price: e.target.value })} inputMode="decimal" placeholder={t('Precio, si ya lo tienes', 'Price, if you have it')} style={{ ...inputStyle, marginTop: 0, flex: '1 1 140px' }} />
                  </div>
                </div>
              ))}
              {constructionShell && (
                <div style={{ marginTop: 20 }}>
                  <h3 style={{ fontSize: 16 }}>{t('Etapa y lotes', 'Phase and lots')}</h3>
                  <p style={{ color: '#5C5650' }}>{t('Solo guarda el área o el precio si tú los escribes. Si los dejas vacíos, quedan sin definir.', 'Area and price are saved only if you type them. Empty stays unset.')}</p>
                  <label>{t('Nombre de la etapa', 'Phase name')}
                    <input value={answers.phase_name} onChange={(e) => setAnswers({ ...answers, phase_name: e.target.value })} style={inputStyle} />
                  </label>
                  {answers.lots.map((lot, index) => (
                    <div key={index} style={{ display: 'grid', gap: 8, marginTop: 12 }}>
                      <input aria-label={t('Número de lote', 'Lot number')} value={lot.lot_number} onChange={(e) => {
                        const lots = answers.lots.map((row, i) => i === index ? { ...row, lot_number: e.target.value } : row);
                        setAnswers({ ...answers, lots });
                      }} placeholder={t('Número', 'Number')} style={inputStyle} />
                      <select aria-label={t('Estado del lote', 'Lot status')} value={lot.status} onChange={(e) => {
                        const lots = answers.lots.map((row, i) => i === index ? { ...row, status: e.target.value } : row);
                        setAnswers({ ...answers, lots });
                      }} style={inputStyle}>
                        <option value="available">{t('Disponible', 'Available')}</option>
                        <option value="reserved">{t('Separado', 'Reserved')}</option>
                        <option value="sold">{t('Vendido', 'Sold')}</option>
                        <option value="under_construction">{t('En obra', 'Under construction')}</option>
                        <option value="consultar">{t('Consultar', 'Ask')}</option>
                      </select>
                      <input aria-label={t('Área m²', 'Area m²')} value={lot.area_m2} onChange={(e) => {
                        const lots = answers.lots.map((row, i) => i === index ? { ...row, area_m2: e.target.value } : row);
                        setAnswers({ ...answers, lots });
                      }} placeholder={t('Área m², si la tienes', 'Area m², if you have it')} style={inputStyle} />
                      <input aria-label={t('Precio del lote', 'Lot price')} value={lot.price} onChange={(e) => {
                        const lots = answers.lots.map((row, i) => i === index ? { ...row, price: e.target.value } : row);
                        setAnswers({ ...answers, lots });
                      }} placeholder={t('Precio, si ya lo tienes', 'Price, if you have it')} style={inputStyle} />
                    </div>
                  ))}
                  <button type="button" onClick={() => setAnswers({ ...answers, lots: [...answers.lots, { lot_number: '', status: 'available', area_m2: '', price: '' }] })} style={{ marginTop: 12, background: 'transparent', border: '1px dashed #D4A030', color: '#2D2A26', borderRadius: 10, padding: '10px 12px', cursor: 'pointer', minHeight: 44 }}>
                    {t('Agregar lote', 'Add lot')}
                  </button>
                </div>
              )}
              {answers.items.length < 8 && (
                <button type="button" onClick={() => setAnswers({ ...answers, items: [...answers.items, { name: '', kind: 'servicio', price: '' }] })} style={{ marginTop: 12, background: 'transparent', border: '1px dashed #D4A030', color: '#2D2A26', borderRadius: 10, padding: '10px 12px', cursor: 'pointer', minHeight: 44 }}>
                  {t('Agregar otro', 'Add another')}
                </button>
              )}
            </>
          )}
          {currentId === 'clientes' && (
            <>
              <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: 26, marginTop: 0 }}>{t('¿Quiénes son tus clientes?', 'Who are your customers?')}</h2>
              <textarea value={answers.customer_who} onChange={(e) => setAnswers({ ...answers, customer_who: e.target.value })} rows={3} placeholder={t('Por ejemplo, pymes de tu ciudad', 'For example, local small businesses')} style={inputStyle} />
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
                {(['b2b', 'b2c', 'ambos'] as const).map((option) => (
                  <button key={option} type="button" onClick={() => setAnswers({ ...answers, customer_type: option })} style={{ borderRadius: 999, border: 'none', background: answers.customer_type === option ? '#D4A030' : '#F3EDE3', color: answers.customer_type === option ? '#fff' : '#2D2A26', padding: '8px 14px', fontWeight: 700, cursor: 'pointer', minHeight: 40 }}>
                    {option === 'ambos' ? t('Los dos', 'Both') : option.toUpperCase()}
                  </button>
                ))}
              </div>
              <h3 style={{ fontSize: 16, marginTop: 18 }}>{t('Primer cliente, si quieres', 'First customer, if you want')}</h3>
              <p style={{ color: '#5C5650', marginTop: 0 }}>{t('Puedes saltarte este paso.', 'You can skip this step.')}</p>
              <input aria-label={t('Nombre del cliente', 'Customer name')} value={answers.first_customer.name} onChange={(e) => setAnswers({ ...answers, first_customer: { ...answers.first_customer, name: e.target.value } })} placeholder={t('Nombre', 'Name')} style={inputStyle} />
              <input aria-label={t('Correo del cliente', 'Customer email')} value={answers.first_customer.email} onChange={(e) => setAnswers({ ...answers, first_customer: { ...answers.first_customer, email: e.target.value } })} placeholder={t('Correo', 'Email')} style={inputStyle} />
              <input aria-label={t('Teléfono del cliente', 'Customer phone')} value={answers.first_customer.phone} onChange={(e) => setAnswers({ ...answers, first_customer: { ...answers.first_customer, phone: e.target.value } })} placeholder={t('Teléfono', 'Phone')} style={inputStyle} />
            </>
          )}
          {currentId === 'dinero' && (
            <>
              <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: 26, marginTop: 0 }}>{t('¿Cómo manejas el dinero?', 'How do you handle money?')}</h2>
              <label>{t('Moneda', 'Currency')}
                <select value={answers.currency} onChange={(e) => setAnswers({ ...answers, currency: e.target.value === 'USD' ? 'USD' : 'COP' })} style={inputStyle}>
                  <option value="COP">COP</option>
                  <option value="USD">USD</option>
                </select>
              </label>
              <label style={{ display: 'block', marginTop: 12 }}>{t('El año fiscal empieza en', 'The fiscal year starts in')}
                <select value={answers.fiscal_year_start} onChange={(e) => setAnswers({ ...answers, fiscal_year_start: e.target.value })} style={inputStyle}>
                  {MONTHS.map(([value, spanish, english]) => (
                    <option key={value} value={value}>{es ? spanish : english}</option>
                  ))}
                </select>
              </label>
              <label style={{ display: 'block', marginTop: 12 }}>{t('NIT', 'Tax ID (NIT)')}
                <input value={answers.tax_id} onChange={(e) => setAnswers({ ...answers, tax_id: e.target.value })} style={inputStyle} />
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: 10, marginTop: 16, minHeight: 44 }}>
                <input type="checkbox" checked={answers.charges_iva} onChange={(e) => setAnswers({ ...answers, charges_iva: e.target.checked })} />
                {t('¿Cobras IVA?', 'Do you charge IVA?')}
              </label>
              <p style={{ fontWeight: 700 }}>{t('Formas de pago', 'Payment methods')}</p>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {PAYMENTS.map((method) => {
                  const on = answers.payment_methods.includes(method.id);
                  return (
                    <button key={method.id} type="button" onClick={() => setAnswers({
                      ...answers,
                      payment_methods: on ? answers.payment_methods.filter((id) => id !== method.id) : [...answers.payment_methods, method.id],
                    })} style={{ borderRadius: 999, border: 'none', background: on ? '#2D2A26' : '#F3EDE3', color: on ? '#fff' : '#2D2A26', padding: '8px 14px', fontWeight: 700, cursor: 'pointer', minHeight: 40 }}>
                      {es ? method.es : method.en}
                    </button>
                  );
                })}
              </div>
            </>
          )}
          {currentId === 'equipo' && (
            <>
              <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: 26, marginTop: 0 }}>{t('¿Trabajas solo o con equipo?', 'Do you work alone or with a team?')}</h2>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                <button type="button" onClick={() => setAnswers({ ...answers, team_mode: 'solo' })} style={{ borderRadius: 999, border: 'none', background: answers.team_mode === 'solo' ? '#D4A030' : '#F3EDE3', color: answers.team_mode === 'solo' ? '#fff' : '#2D2A26', padding: '8px 14px', fontWeight: 700, minHeight: 40, cursor: 'pointer' }}>{t('Solo', 'Solo')}</button>
                <button type="button" onClick={() => setAnswers({ ...answers, team_mode: 'equipo' })} style={{ borderRadius: 999, border: 'none', background: answers.team_mode === 'equipo' ? '#D4A030' : '#F3EDE3', color: answers.team_mode === 'equipo' ? '#fff' : '#2D2A26', padding: '8px 14px', fontWeight: 700, minHeight: 40, cursor: 'pointer' }}>{t('Con equipo', 'With a team')}</button>
              </div>
              {answers.team_mode === 'equipo' && (
                <div style={{ marginTop: 16 }}>
                  <label>{t('Roles', 'Roles')}
                    <input value={roleDraft} onChange={(e) => setRoleDraft(e.target.value)} placeholder={t('Por ejemplo, contador', 'For example, accountant')} style={inputStyle} />
                  </label>
                  <button type="button" onClick={() => {
                    const role = roleDraft.trim();
                    if (!role) return;
                    setAnswers({ ...answers, roles: answers.roles.includes(role) ? answers.roles : [...answers.roles, role] });
                    setRoleDraft('');
                  }} style={{ marginTop: 8, background: '#2D2A26', color: '#fff', border: 'none', borderRadius: 10, padding: '10px 14px', minHeight: 44, cursor: 'pointer' }}>
                    {t('Agregar rol', 'Add role')}
                  </button>
                  <ul>
                    {answers.roles.map((role) => (
                      <li key={role} style={{ marginTop: 8 }}>
                        {role}{' '}
                        <button type="button" onClick={() => setAnswers({ ...answers, roles: answers.roles.filter((item) => item !== role) })} style={{ border: 'none', background: 'transparent', color: '#9b2c2c', cursor: 'pointer' }}>{t('Quitar', 'Remove')}</button>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </>
          )}
          {currentId === 'herramientas' && (
            <>
              <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: 26, marginTop: 0 }}>{t('¿Qué herramientas enciendo?', 'Which tools should I turn on?')}</h2>
              <p style={{ color: '#5C5650' }}>{t('Todas quedan apagadas hasta que tú las elijas.', 'They all stay off until you choose them.')}</p>
              <div style={{ display: 'grid', gap: 8 }}>
                {MODULES.map((mod) => (
                  <label key={mod.id} style={{ display: 'flex', alignItems: 'center', gap: 12, background: '#FFF9F0', borderRadius: 12, padding: 12, minHeight: 48 }}>
                    <input type="checkbox" checked={Boolean(answers.modules[mod.id])} onChange={(e) => setAnswers({ ...answers, modules: { ...answers.modules, [mod.id]: e.target.checked } })} />
                    <span>{es ? mod.es : mod.en}</span>
                  </label>
                ))}
              </div>
            </>
          )}
          {currentId === 'confirmar' && (
            <>
              <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: 26, marginTop: 0 }}>{t('Confirmar datos', 'Confirm facts')}</h2>
              <p style={{ color: '#5C5650' }}>{t('Cada dato queda confidencial hasta que lo marques como Publicar. Lo confidencial no entra en redes ni en contenido público.', 'Each fact stays confidential until you mark it Publicar. Confidential facts stay out of social posts and public content.')}</p>
              {[...confirmRows(answers), ...argosRows.map((item) => ({ key: item.key, label: item.label, value: item.value }))].map((row) => {
                const visibility = answers.fact_visibility[row.key] || 'confidential';
                return (
                  <div key={row.key} style={{ borderTop: '1px solid #F0E6D8', padding: '12px 0' }}>
                    <strong>{row.label}</strong>
                    <p style={{ margin: '4px 0 8px', color: '#5C5650' }}>{row.value}</p>
                    <div style={{ display: 'flex', gap: 8 }}>
                      {(['confidential', 'public'] as const).map((option) => (
                        <button key={option} type="button" onClick={() => setAnswers({ ...answers, fact_visibility: { ...answers.fact_visibility, [row.key]: option } })} style={{ borderRadius: 999, border: 'none', background: visibility === option ? '#D4A030' : '#F3EDE3', color: visibility === option ? '#fff' : '#2D2A26', padding: '8px 14px', fontWeight: 700, cursor: 'pointer', minHeight: 40 }}>
                          {option === 'public' ? t('Publicar', 'Publish') : t('Confidencial', 'Confidential')}
                        </button>
                      ))}
                    </div>
                  </div>
                );
              })}
            </>
          )}
          {currentId === 'revision' && (
            <>
              <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: 26, marginTop: 0 }}>{t('Revisa antes de crear la empresa', 'Review before creating the company')}</h2>
              {[
                ...(constructionShell ? [{ id: 'argos', title: label('argos'), body: ARGOS_OPTIONS.find((option) => option.id === answers.argos_consent)?.[es ? 'es' : 'en'] || t('Sin elegir', 'Not chosen') }] : []),
                { id: 'empresa', title: label('empresa'), body: [answers.legal_name, answers.trade_name, answers.city, answers.country, answers.email, answers.phone, answers.website].filter(Boolean).join(' · ') || t('Sin datos', 'No details') },
                { id: 'industria', title: label('industria'), body: [answers.template || t('En blanco', 'Blank'), answers.industry_description].filter(Boolean).join(' — ') },
                { id: 'oferta', title: label('oferta'), body: answers.items.filter((item) => item.name.trim()).map((item) => `${item.name}${item.price ? ` (${item.price})` : ''}`).join(', ') || t('Sin ítems', 'No items') },
                { id: 'clientes', title: label('clientes'), body: [answers.customer_type.toUpperCase(), answers.customer_who, answers.first_customer.name].filter(Boolean).join(' · ') },
                { id: 'dinero', title: label('dinero'), body: [answers.currency, answers.fiscal_year_start, answers.tax_id && `NIT ${answers.tax_id}`, answers.charges_iva ? 'IVA' : t('Sin IVA', 'No IVA'), answers.payment_methods.join(', ')].filter(Boolean).join(' · ') },
                { id: 'equipo', title: label('equipo'), body: answers.team_mode === 'equipo' ? `${t('Con equipo', 'With a team')}: ${answers.roles.join(', ') || t('sin roles', 'no roles')}` : t('Solo', 'Solo') },
                { id: 'herramientas', title: label('herramientas'), body: MODULES.filter((mod) => answers.modules[mod.id]).map((mod) => (es ? mod.es : mod.en)).join(' · ') || t('Ninguna encendida', 'None turned on') },
              ].map((section) => (
                <div key={section.id} style={{ borderTop: '1px solid #F0E6D8', padding: '12px 0' }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', gap: 12, alignItems: 'baseline' }}>
                    <strong>{section.title}</strong>
                    <button type="button" onClick={() => { setStep(Math.max(steps.findIndex((item) => item.id === section.id), 0)); scrollTop(); }} style={{ border: 'none', background: 'transparent', color: '#D4A030', fontWeight: 800, cursor: 'pointer', minHeight: 44 }}>
                      {t('Editar', 'Edit')}
                    </button>
                  </div>
                  <p style={{ margin: '4px 0 0', color: '#5C5650' }}>{section.body}</p>
                </div>
              ))}
              <p style={{ marginTop: 16, lineHeight: 1.5 }}>
                {t('Cuando termines, mira cómo entrar desde el celular, la tableta o el computador.', 'When you finish, see how to open this on a phone, tablet, or computer.')}{' '}
                <Link href="/ayuda/dispositivos" style={{ color: '#D4A030', fontWeight: 800 }}>Cómo conectarte desde tus dispositivos</Link>
              </p>
            </>
          )}
        </section>
      )}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, marginTop: 16 }}>
        {step > 0 && (
          <button type="button" onClick={onBack} disabled={busy} style={{ flex: '1 1 140px', minHeight: 48, borderRadius: 12, border: '1px solid #E7E0D6', background: '#fff', fontWeight: 700, cursor: 'pointer' }}>
            {t('Atrás', 'Back')}
          </button>
        )}
        <button type="button" onClick={onSaveLater} disabled={busy || loading} style={{ flex: '1 1 180px', minHeight: 48, borderRadius: 12, border: '1px solid #E7E0D6', background: '#fff', fontWeight: 700, cursor: 'pointer' }}>
          {t('Guardar y seguir después', 'Save and continue later')}
        </button>
        {step < last ? (
          <button type="button" onClick={onNext} disabled={busy || loading} style={{ flex: '1 1 140px', minHeight: 48, borderRadius: 12, border: 'none', background: '#D4A030', color: '#fff', fontWeight: 800, cursor: 'pointer' }}>
            {currentId === 'bienvenida' ? t('Empezar', 'Start') : t('Siguiente', 'Next')}
          </button>
        ) : (
          <button type="button" onClick={finish} disabled={busy || loading} style={{ flex: '1 1 180px', minHeight: 48, borderRadius: 12, border: 'none', background: '#2D2A26', color: '#fff', fontWeight: 800, cursor: 'pointer' }}>
            {busy ? t('Creando…', 'Creating…') : t('Crear empresa', 'Create company')}
          </button>
        )}
      </div>
    </main>
  );
}
