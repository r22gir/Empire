import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'MAX — Empire AI Brain',
  description: 'MAX coordinates Empire chat, voice, image and document analysis, Code Mode, AI desks, and OpenClaw execution.',
  openGraph: {
    title: 'MAX — Empire AI Brain',
    description: 'Founder-led AI orchestration for Empire operations.',
    type: 'website',
    url: 'https://studio.empirebox.store/max',
  },
};

const capabilities = [
  'Chat for founder requests',
  'Voice input with truthful TTS status',
  'Image and document analysis',
  'Code Mode under MAX',
  'AI desk delegation',
  'OpenClaw execution visibility',
  'Memory Bank across web, Telegram, and email',
];

export default function MaxLanding() {
  return (
    <main style={{ minHeight: '100vh', background: '#f7f8f5', color: '#171717', fontFamily: "'Inter', 'Segoe UI', sans-serif" }}>
      <nav style={{ display: 'flex', gap: 14, alignItems: 'center', justifyContent: 'center', padding: '14px 20px', borderBottom: '1px solid #d9ded5', background: '#fff' }}>
        <a href="/max" style={navLink}>MAX</a>
        <a href="/workroom" style={navLink}>Workroom</a>
        <a href="/woodcraft" style={navLink}>WoodCraft</a>
        <a href="/" style={navLink}>Command Center</a>
      </nav>

      <section style={{ display: 'grid', gridTemplateColumns: 'minmax(0, 1.1fr) minmax(300px, 0.9fr)', gap: 28, alignItems: 'center', maxWidth: 1120, margin: '0 auto', padding: '54px 24px 40px' }}>
        <div>
          <p style={{ margin: '0 0 10px', fontSize: 12, fontWeight: 800, letterSpacing: 1.4, textTransform: 'uppercase', color: '#4b7f52' }}>Founder {'>'} MAX {'>'} Desks {'>'} OpenClaw</p>
          <h1 style={{ margin: 0, fontSize: 'clamp(34px, 6vw, 64px)', lineHeight: 1.02, letterSpacing: 0, fontWeight: 900 }}>
            Empire&apos;s AI brain for work that has to move.
          </h1>
          <p style={{ margin: '18px 0 0', maxWidth: 660, color: '#4d564d', fontSize: 18, lineHeight: 1.6 }}>
            MAX sits below the Founder and above Code Mode, AI desks, and OpenClaw. It keeps routing, memory, execution, and degraded-mode truth visible.
          </p>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 26 }}>
            <a href="/" style={primaryCta}>Open Command Center</a>
            <a href="mailto:max@empirebox.store" style={secondaryCta}>Email MAX</a>
          </div>
        </div>
        <div style={{ border: '1px solid #d9ded5', borderRadius: 8, background: '#fff', minHeight: 360, overflow: 'hidden' }}>
          <iframe src="/avatar.html" title="MAX avatar" style={{ width: '100%', height: 360, border: 0, display: 'block', background: '#f7f8f5' }} />
        </div>
      </section>

      <section style={{ maxWidth: 1120, margin: '0 auto', padding: '24px 24px 64px' }}>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 12 }}>
          {capabilities.map(item => (
            <div key={item} style={{ border: '1px solid #d9ded5', borderRadius: 8, background: '#fff', padding: 18, fontSize: 15, fontWeight: 700 }}>
              {item}
            </div>
          ))}
        </div>
      </section>

      <section style={{ borderTop: '1px solid #d9ded5', background: '#fff', padding: '44px 24px' }}>
        <div style={{ maxWidth: 900, margin: '0 auto', display: 'grid', gridTemplateColumns: '90px minmax(0, 1fr)', gap: 20, alignItems: 'center' }}>
          <img src="/globe.svg" alt="" style={{ width: 80, height: 80 }} />
          <div>
            <h2 style={{ margin: '0 0 8px', fontSize: 26, fontWeight: 900 }}>Founder-visible status first.</h2>
            <p style={{ margin: 0, color: '#4d564d', fontSize: 16, lineHeight: 1.6 }}>
              Cloud fallback, voice status, Memory Bank items, desk delegation, Code Mode, and OpenClaw execution stay visible so degraded mode is clear.
            </p>
          </div>
        </div>
      </section>
    </main>
  );
}

const navLink = {
  color: '#171717',
  textDecoration: 'none',
  fontSize: 13,
  fontWeight: 800,
} as const;

const primaryCta = {
  display: 'inline-block',
  borderRadius: 8,
  padding: '13px 20px',
  background: '#171717',
  color: '#fff',
  textDecoration: 'none',
  fontWeight: 800,
} as const;

const secondaryCta = {
  display: 'inline-block',
  borderRadius: 8,
  padding: '13px 20px',
  border: '1px solid #9ba794',
  color: '#171717',
  textDecoration: 'none',
  fontWeight: 800,
} as const;
