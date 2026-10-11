import Link from 'next/link';

export default function HelpMenu() {
  return (
    <nav aria-label="Ayuda" style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 16, maxWidth: 520 }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: '#1a1a1a' }}>Ayuda</div>
      <ul style={{ listStyle: 'none', padding: 0, margin: '8px 0 0' }}>
        <li>
          <Link href="/ayuda/voz" style={{ fontSize: 13, fontWeight: 700, color: '#b8960c' }}>Cómo usar la voz</Link>
        </li>
        <li style={{ marginTop: 6 }}>
          <Link href="/ayuda/dispositivos" style={{ fontSize: 13, fontWeight: 700, color: '#b8960c' }}>Cómo conectarte desde tus dispositivos</Link>
        </li>
        <li style={{ marginTop: 6 }}>
          <Link href="/amp/whatsapp" style={{ fontSize: 13, fontWeight: 700, color: '#b8960c' }}>Cómo configurar WhatsApp</Link>
        </li>
      </ul>
    </nav>
  );
}
