'use client';

const BUSINESSES = [
  {
    href: '/amp',
    name: 'AMP',
    line: 'Coaching, cursos y membresías. Actitud Mental Positiva.',
  },
  {
    href: '/amp/empresas/cibernettic',
    name: 'Cibernettic',
    line: 'Ciberseguridad, datos, bases de datos, redes, GIS y ERP.',
  },
];

export default function MaxeBusinesses() {
  return (
    <div style={{ marginTop: 16 }}>
      <div style={{ fontSize: 12, fontWeight: 700, letterSpacing: 0.4, color: '#888', marginBottom: 8 }}>EMPRESAS DE MAX-E</div>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
        {BUSINESSES.map((business) => (
          <a key={business.name} href={business.href} style={{ display: 'block', background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14, textDecoration: 'none', color: '#1a1a1a' }}>
            <div style={{ fontWeight: 700 }}>{business.name}</div>
            <p style={{ fontSize: 13, color: '#444', margin: '6px 0 0' }}>{business.line}</p>
          </a>
        ))}
      </div>
      <p style={{ fontSize: 12, color: '#888' }}>
        Ninguna de las dos es el centro de mando. Max-e opera las dos. El archivo de cada persona va a su propio Google Drive.
        {' '}<a href="/archivo" style={{ color: '#b8960c' }}>Archivo</a>
      </p>
    </div>
  );
}
