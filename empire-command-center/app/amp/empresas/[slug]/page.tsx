'use client';

import { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import { API_BASE } from '../../../lib/api';
import { useAssistantName } from '../../../lib/assistant';

type Category = { name?: string; description?: string; price?: number | null };
type Contact = { name?: string; email?: string; phone?: string };
type Business = {
  name?: string;
  legal_name?: string;
  trade_name?: string;
  industry?: string;
  description?: string;
  template?: string | null;
  country?: string;
  city?: string;
  contact_email?: string;
  contact_phone?: string;
  website?: string;
  currency?: string;
  fiscal_year_start?: string;
  tax_id?: string;
  charges_iva?: boolean;
  payment_methods?: string[];
  customer_type?: string;
  customer_who?: string;
  team_mode?: string;
  roles?: string[];
  sells?: string;
  modules?: string[];
  starter_items?: { name: string; kind?: string; price?: number | null }[];
  service_categories?: Category[];
  contacts?: Contact[];
  assistant?: string;
  setup?: string;
};

const MODULE_LABELS: Record<string, string> = {
  crm: 'CRM',
  quotes: 'Cotizaciones',
  invoices: 'Facturas',
  socialforge: 'SocialForge',
  leadforge: 'LeadForge',
  courses: 'Cursos',
  scheduling: 'Agenda',
  finance: 'Finanzas',
  max: 'Asistente',
};

function money(price: number | null | undefined, currency: string): string {
  if (price == null) return 'Sin precio';
  try {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: currency || 'COP',
      maximumFractionDigits: Number.isInteger(price) ? 0 : 2,
    }).format(price);
  } catch {
    return String(price);
  }
}

export default function EmpresaPage() {
  const params = useParams();
  const slug = typeof params.slug === 'string' ? params.slug : '';
  const assistant = useAssistantName();
  const [business, setBusiness] = useState<Business | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    if (!slug) return;
    let cancelled = false;
    fetch(`${API_BASE}/api/v1/businesses/${encodeURIComponent(slug)}`, { credentials: 'include' })
      .then(async (res) => {
        const body = await res.json().catch(() => ({}));
        if (cancelled) return;
        if (res.status === 403) {
          setError('Sin acceso. Entra con tu correo autorizado.');
          return;
        }
        if (!res.ok) {
          setError(body.detail || 'No encontré esa empresa.');
          return;
        }
        setBusiness(body);
      })
      .catch(() => {
        if (!cancelled) setError('No pude conectar con el servidor.');
      });
    return () => {
      cancelled = true;
    };
  }, [slug]);

  const currency = business?.currency || 'COP';
  const items = (business?.service_categories || []).filter((row) => row.name);
  const modules = business?.modules || [];

  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: '24px 16px 64px', fontFamily: 'Nunito, sans-serif', color: '#2D2A26', background: '#FFF9F0', minHeight: '100vh' }}>
      <p style={{ margin: '0 0 12px', letterSpacing: 1, color: '#D4A030', fontWeight: 700, fontSize: 12 }}>EL PORTAL DE LA ALEGRÍA</p>
      <a href="/amp/empresas" style={{ color: '#9B9590', fontSize: 14 }}>← Empresas</a>
      {error && (
        <p role="alert" style={{ color: '#9b2c2c' }}>
          {error}{' '}
          {error.includes('acceso') && <a href="/login" style={{ color: '#D4A030', fontWeight: 700 }}>Iniciar sesión</a>}
        </p>
      )}
      {!business && !error && <p>Cargando…</p>}
      {business && (
        <>
          <h1 style={{ fontFamily: 'Playfair Display, serif', fontSize: 36, margin: '12px 0 4px' }}>{business.name}</h1>
          {business.trade_name && business.trade_name !== business.name && (
            <p style={{ color: '#5C5650', marginTop: 0 }}>Nombre comercial: {business.trade_name}</p>
          )}
          <p style={{ color: '#5C5650', lineHeight: 1.5 }}>
            {[business.city, business.country].filter(Boolean).join(', ') || 'Sin ciudad todavía'}
            {business.industry ? ` · ${business.industry}` : ''}
          </p>
          {business.description && <p style={{ lineHeight: 1.5 }}>{business.description}</p>}
          <section style={{ background: '#fff', border: '1px solid #F0E6D8', borderRadius: 16, padding: 16, marginTop: 16 }}>
            <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: 22, margin: '0 0 8px' }}>Dinero</h2>
            <p style={{ margin: '4px 0' }}>Moneda: {currency}</p>
            {business.fiscal_year_start && <p style={{ margin: '4px 0' }}>Año fiscal desde: {business.fiscal_year_start}</p>}
            {business.tax_id && <p style={{ margin: '4px 0' }}>NIT: {business.tax_id}</p>}
            {business.charges_iva != null && <p style={{ margin: '4px 0' }}>{business.charges_iva ? 'Cobras IVA.' : 'No marcas IVA.'}</p>}
            {business.payment_methods && business.payment_methods.length > 0 && (
              <p style={{ margin: '4px 0' }}>Pagos: {business.payment_methods.join(', ')}</p>
            )}
          </section>
          <section style={{ background: '#fff', border: '1px solid #F0E6D8', borderRadius: 16, padding: 16, marginTop: 12 }}>
            <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: 22, margin: '0 0 8px' }}>Qué ofreces</h2>
            {items.length === 0 ? <p>Todavía no hay servicios ni productos.</p> : (
              <ul style={{ paddingLeft: 18, margin: 0 }}>
                {items.map((row) => (
                  <li key={row.name} style={{ marginBottom: 6 }}>
                    <strong>{row.name}</strong>
                    {row.description ? ` — ${row.description}` : ''} · {money(row.price, currency)}
                  </li>
                ))}
              </ul>
            )}
          </section>
          <section style={{ background: '#fff', border: '1px solid #F0E6D8', borderRadius: 16, padding: 16, marginTop: 12 }}>
            <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: 22, margin: '0 0 8px' }}>Clientes</h2>
            {business.customer_who && <p>{business.customer_who}</p>}
            {business.customer_type && <p>Tipo: {business.customer_type.toUpperCase()}</p>}
            {(business.contacts || []).length === 0 ? <p>Sin contactos todavía.</p> : (
              <ul style={{ paddingLeft: 18 }}>
                {(business.contacts || []).map((person) => (
                  <li key={`${person.name}-${person.email}`}>{person.name}{person.email ? ` · ${person.email}` : ''}</li>
                ))}
              </ul>
            )}
          </section>
          <section style={{ background: '#fff', border: '1px solid #F0E6D8', borderRadius: 16, padding: 16, marginTop: 12 }}>
            <h2 style={{ fontFamily: 'Playfair Display, serif', fontSize: 22, margin: '0 0 8px' }}>Herramientas</h2>
            {modules.length === 0 ? (
              <p>Ninguna herramienta está encendida. Puedes dejarla así.</p>
            ) : (
              <p>{modules.map((id) => MODULE_LABELS[id] || id).join(' · ')}</p>
            )}
            {business.team_mode && (
              <p>{business.team_mode === 'equipo' ? 'Trabajas con equipo.' : 'Trabajas solo.'} {(business.roles || []).join(', ')}</p>
            )}
          </section>
          {business.setup === 'entrevista' && (
            <p style={{ color: '#9B9590', fontSize: 13, marginTop: 20 }}>
              {business.assistant || assistant} dejó esta ficha a partir de la entrevista.
            </p>
          )}
          <a href="/amp/dashboard" style={{ display: 'inline-block', marginTop: 8, color: '#D4A030', fontWeight: 800 }}>Ir al panel</a>
        </>
      )}
    </main>
  );
}
