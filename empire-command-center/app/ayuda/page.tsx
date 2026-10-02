import Link from 'next/link';

const ARTICLES = [
  { href: '/ayuda/voz', title: 'Cómo usar la voz', note: 'Dicta, revisa y aprueba el borrador.' },
  { href: '/ayuda/dispositivos', title: 'Cómo conectarte desde tus dispositivos', note: 'Sitio web, pantalla de inicio y acceso privado.' },
];

export default function AyudaMenu() {
  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: '32px 20px', fontFamily: 'Inter, sans-serif', color: '#1a1a1a' }}>
      <p style={{ fontSize: 12, letterSpacing: 0.4, color: '#b8960c', fontWeight: 700, margin: 0 }}>CENTRO DE MANDO</p>
      <h1 style={{ fontSize: 32, margin: '8px 0' }}>Ayuda</h1>
      <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>
        {ARTICLES.map((article) => (
          <li key={article.href} style={{ borderTop: '1px solid #e5e2dc', padding: '14px 0' }}>
            <Link href={article.href} style={{ color: '#1a1a1a', fontWeight: 700, fontSize: 18 }}>
              {article.title}
            </Link>
            <p style={{ margin: '6px 0 0', color: '#444' }}>{article.note}</p>
          </li>
        ))}
      </ul>
      <p style={{ marginTop: 24 }}>
        <Link href="/" style={{ color: '#b8960c', fontWeight: 700 }}>Volver al centro de mando</Link>
      </p>
    </main>
  );
}
