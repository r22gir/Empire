import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Empire Workroom — Custom Drapery & Upholstery',
  description: 'Transform your space with custom drapery, upholstery, pillows, cornices, banquette seating, and roman shades. Serving the DC metro area.',
  openGraph: {
    title: 'Empire Workroom — Custom Drapery & Upholstery',
    description: 'Transform your space with custom drapery, upholstery, and more. Free quotes available.',
    type: 'website',
    url: 'https://studio.empirebox.store/workroom',
  },
};

const services = [
  { name: 'Custom Drapery', desc: 'Ripplefold, pinch pleat, rod pocket, and grommet styles crafted to your exact specifications.' },
  { name: 'Upholstery', desc: 'Breathe new life into furniture with premium fabrics and expert craftsmanship.' },
  { name: 'Decorative Pillows', desc: 'Custom throw pillows, bolsters, and accent pieces to complete your design.' },
  { name: 'Cornices & Valances', desc: 'Elegant window toppers that frame your view with style.' },
  { name: 'Banquette Seating', desc: 'Custom-built bench seating with tailored cushions for dining and nook spaces.' },
  { name: 'Roman Shades', desc: 'Flat, hobbled, or relaxed roman shades in your choice of fabric and lining.' },
];

export default function WorkroomLanding() {
  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f3ef', fontFamily: "'Outfit', 'Segoe UI', sans-serif" }}>
      {/* Hero */}
      <header style={{
        background: 'linear-gradient(135deg, #1a1a2e 0%, #2d2d44 100%)',
        padding: '80px 24px 72px',
        textAlign: 'center',
      }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          <div style={{
            display: 'inline-block',
            background: 'linear-gradient(135deg, #b8960c, #d4af37)',
            color: '#1a1a2e',
            padding: '6px 20px',
            borderRadius: 20,
            fontSize: 13,
            fontWeight: 700,
            letterSpacing: 1.5,
            textTransform: 'uppercase',
            marginBottom: 24,
          }}>
            Empire Workroom
          </div>
          <h1 style={{
            color: '#fff',
            fontSize: 'clamp(32px, 5vw, 52px)',
            fontWeight: 800,
            lineHeight: 1.15,
            margin: '0 0 16px',
            letterSpacing: -0.5,
          }}>
            Custom Drapery &<br />Upholstery
          </h1>
          <p style={{
            color: '#ccc',
            fontSize: 'clamp(16px, 2.5vw, 20px)',
            maxWidth: 560,
            margin: '0 auto 32px',
            lineHeight: 1.5,
          }}>
            Handcrafted window treatments and upholstery for homes and businesses in the DC metro area.
          </p>
          <a
            href="/intake/signup"
            style={{
              display: 'inline-block',
              background: 'linear-gradient(135deg, #b8960c, #d4af37)',
              color: '#1a1a2e',
              padding: '16px 40px',
              borderRadius: 12,
              fontSize: 17,
              fontWeight: 700,
              textDecoration: 'none',
              minHeight: 48,
              transition: 'transform 0.15s',
            }}
          >
            Get a Free Quote
          </a>
        </div>
      </header>

      {/* Services */}
      <section style={{ maxWidth: 1100, margin: '0 auto', padding: '64px 24px' }}>
        <h2 style={{
          textAlign: 'center',
          fontSize: 28,
          fontWeight: 700,
          color: '#1a1a2e',
          marginBottom: 48,
        }}>
          Our Services
        </h2>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(300px, 1fr))',
          gap: 20,
        }}>
          {services.map((s) => (
            <div key={s.name} style={{
              background: '#fff',
              borderRadius: 14,
              padding: '28px 24px',
              border: '1px solid #ece8e0',
              transition: 'box-shadow 0.2s',
            }}>
              <h3 style={{
                fontSize: 18,
                fontWeight: 700,
                color: '#b8960c',
                margin: '0 0 8px',
              }}>
                {s.name}
              </h3>
              <p style={{
                color: '#555',
                fontSize: 15,
                lineHeight: 1.5,
                margin: 0,
              }}>
                {s.desc}
              </p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section style={{
        background: 'linear-gradient(135deg, #b8960c, #d4af37)',
        padding: '56px 24px',
        textAlign: 'center',
      }}>
        <h2 style={{
          color: '#1a1a2e',
          fontSize: 26,
          fontWeight: 700,
          marginBottom: 16,
        }}>
          Ready to Transform Your Space?
        </h2>
        <p style={{
          color: '#333',
          fontSize: 16,
          marginBottom: 28,
          maxWidth: 500,
          marginLeft: 'auto',
          marginRight: 'auto',
        }}>
          Get a free consultation and estimate. We&apos;ll measure, design, and install — you just enjoy the result.
        </p>
        <a
          href="/intake/signup"
          style={{
            display: 'inline-block',
            background: '#1a1a2e',
            color: '#d4af37',
            padding: '16px 40px',
            borderRadius: 12,
            fontSize: 17,
            fontWeight: 700,
            textDecoration: 'none',
            minHeight: 48,
          }}
        >
          Request a Quote
        </a>
      </section>

      {/* Contact */}
      <section style={{
        maxWidth: 600,
        margin: '0 auto',
        padding: '56px 24px',
        textAlign: 'center',
      }}>
        <h2 style={{ fontSize: 24, fontWeight: 700, color: '#1a1a2e', marginBottom: 20 }}>
          Contact Us
        </h2>
        <p style={{ color: '#555', fontSize: 15, margin: '8px 0' }}>
          <strong>Email:</strong>{' '}
          <a href="mailto:workroom@empirebox.store" style={{ color: '#b8960c' }}>
            workroom@empirebox.store
          </a>
        </p>
        <p style={{ color: '#555', fontSize: 15, margin: '8px 0' }}>
          <strong>Hours:</strong> Monday – Friday, 9 AM – 5 PM EST
        </p>
        <p style={{ color: '#555', fontSize: 15, margin: '8px 0' }}>
          <strong>Service Area:</strong> Washington DC, Maryland, Virginia
        </p>
      </section>

      {/* Footer */}
      <footer style={{
        background: '#1a1a2e',
        color: '#888',
        textAlign: 'center',
        padding: '24px',
        fontSize: 13,
      }}>
        &copy; {new Date().getFullYear()} Empire Workroom. All rights reserved.
      </footer>
    </div>
  );
}
