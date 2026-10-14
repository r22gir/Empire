'use client';

import { GUIDE_LINKS } from '../../lib/companySetupLinks';

export default function CompanySetupGuide({ locale = 'en' }: { locale?: 'en' | 'es' }) {
  const es = locale === 'es';
  return (
    <div style={{ minHeight: '100vh', background: '#f5f2ed', color: '#1a1a1a', padding: '40px 20px' }}>
      <div style={{ maxWidth: 720, margin: '0 auto' }}>
        <div style={{ fontSize: 12, letterSpacing: 1.6, textTransform: 'uppercase', color: '#b8960c', fontWeight: 700 }}>
          {es ? 'Max · Ayuda' : 'Max Studio · Help'}
        </div>
        <h1 style={{ fontFamily: 'Georgia, serif', fontSize: 36, fontWeight: 600, margin: '10px 0 8px' }}>
          {es ? '¡Quiubo manito!' : 'Company setup'}
        </h1>
        <p style={{ fontSize: 16, lineHeight: 1.55, color: '#444', marginTop: 0 }}>
          {es
            ? 'Esta guía camina la configuración de la empresa. Max cubre la vida completa, no solo el Workroom. Los datos de familia no se mezclan con el taller.'
            : 'Walk through company setup. Max covers whole life, not only the Workroom. Family data stays out of Workroom files.'}
        </p>

        <ol style={{ padding: 0, listStyle: 'none', display: 'grid', gap: 12, margin: '28px 0' }}>
          {(es ? STEPS_ES : STEPS_EN).map((step, i) => (
            <li key={step.title} style={{ background: '#fff', border: '1px solid #e8e4de', borderRadius: 14, padding: '16px 18px' }}>
              <div style={{ fontSize: 11, color: '#b8960c', fontWeight: 700 }}>0{i + 1}</div>
              <div style={{ fontSize: 17, fontWeight: 700, margin: '2px 0 6px' }}>{step.title}</div>
              <p style={{ margin: 0, fontSize: 14, color: '#555', lineHeight: 1.5 }}>{step.body}</p>
            </li>
          ))}
        </ol>

        <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 10 }}>{es ? 'Abrir cada pantalla' : 'Open each screen'}</div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
          {GUIDE_LINKS.map((link) => (
            <a
              key={link.id}
              href={link.href}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                minHeight: 40,
                padding: '0 14px',
                borderRadius: 10,
                background: '#fff',
                border: '1px solid #e5e2dc',
                color: '#1a1a1a',
                textDecoration: 'none',
                fontWeight: 600,
                fontSize: 13,
              }}
            >
              {es ? link.labelEs : link.label}
            </a>
          ))}
        </div>

        <p style={{ marginTop: 28, fontSize: 13 }}>
          {es ? (
            <>Versión en inglés para Studio: <a href="/help/company" style={{ color: '#b8960c' }}>/help/company</a></>
          ) : (
            <>Spanish family guide: <a href="/ayuda/empresa" style={{ color: '#b8960c' }}>/ayuda/empresa</a></>
          )}
        </p>
      </div>
    </div>
  );
}

const STEPS_EN = [
  { title: 'Legal name vs DBA, then brands', body: 'Start Company Setup. Empire Workroom is the default brand. Add Nelma’s Workroom or any other brand under the same owner. Saves merge into business.json — phones already on file stay.' },
  { title: 'Address, phone, email for documents', body: 'These print on quotes, invoices, and letterhead. Do not wipe founder numbers.' },
  { title: 'Tax, deposits, and numbering', body: 'EIN, sales tax by state and county, Stripe Payment Links or Square per brand, deposit percent, quote/invoice prefix and start.' },
  { title: 'Pricing Studio catalog', body: 'Services and rate cards feed Pricing Studio. Measurement rule is fractions only. Fabric codes stay V###-Color. Foam allowance is per side.' },
  { title: 'Team, channels, calendar', body: 'Record invites (Max never emails). Put WhatsApp keys in the founder-only form. Hours go on the calendar. Suppliers and COI stay internal.' },
  { title: 'Life areas and privacy', body: 'Max covers personal and family life too. Workroom does not see family data. Family editions do not see Workroom quotes or CRM. Review the recap, then confirm.' },
];

const STEPS_ES = [
  { title: 'Nombre legal, DBA y marcas', body: 'Abre Configuración de empresa. Empire Workroom es la marca por defecto. Puedes agregar Nelma’s Workroom u otras marcas del mismo dueño. Se fusiona en business.json: los teléfonos que ya están se quedan.' },
  { title: 'Dirección, teléfono y correo', body: 'Salen en cotizaciones, facturas y membrete. No borres los números del fundador.' },
  { title: 'Impuestos, depósitos y numeración', body: 'EIN, impuesto por estado y condado, Stripe Payment Links o Square por marca, porcentaje de depósito, prefijo y número inicial.' },
  { title: 'Catálogo de Pricing Studio', body: 'Servicios y tarifas alimentan Pricing Studio. Las medidas van en fracciones. Los códigos de tela son V###-Color. La merma de foam es por cada lado.' },
  { title: 'Equipo, canales y calendario', body: 'Las invitaciones se anotan (Max no manda correo). Las llaves de WhatsApp van en el formulario del fundador. Horarios en el calendario. Proveedores y COI son internos.' },
  { title: 'Vida personal y privacidad', body: 'Max cubre la vida completa, no solo el taller. El Workroom no ve lo familiar. Las ediciones de familia no ven cotizaciones ni CRM. Revisa y confirma.' },
];
