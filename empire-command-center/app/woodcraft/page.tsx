import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'WoodCraft — Handcrafted Woodwork & CNC',
  description: 'Custom furniture, CNC cutting, wood refinishing, and beam work. Precision craftsmanship for homes and businesses in the DC metro area.',
  openGraph: {
    title: 'WoodCraft — Handcrafted Woodwork & CNC',
    description: 'Custom furniture, CNC cutting, and wood refinishing. Free quotes available.',
    type: 'website',
    url: 'https://studio.empirebox.store/woodcraft',
  },
};

const services = [
  { name: 'Custom Furniture', desc: 'Tables, shelving, cabinets, and more — designed and built to your exact specifications.' },
  { name: 'CNC Cutting', desc: 'Precision computer-controlled cuts for signs, panels, artistic pieces, and production runs.' },
  { name: 'Wood Refinishing', desc: 'Restore and refinish existing furniture, doors, and wood surfaces to their original beauty.' },
  { name: 'Beam Work', desc: 'Decorative and structural wood beams — mantels, ceiling beams, and accent pieces.' },
];

export default function WoodcraftLanding() {
  return (
    <div style={{ minHeight: '100vh', backgroundColor: '#f5f3ef', fontFamily: "'Outfit', 'Segoe UI', sans-serif" }}>
      {/* Hero */}
      <header style={{
        background: 'linear-gradient(135deg, #2c1810 0%, #3d2817 100%)',
        padding: '80px 24px 72px',
        textAlign: 'center',
      }}>
        <div style={{ maxWidth: 800, margin: '0 auto' }}>
          <div style={{
            display: 'inline-block',
            background: 'linear-gradient(135deg, #d4a017, #e8b830)',
            color: '#2c1810',
            padding: '6px 20px',
            borderRadius: 20,
            fontSize: 13,
            fontWeight: 700,
            letterSpacing: 1.5,
            textTransform: 'uppercase',
            marginBottom: 24,
          }}>
            WoodCraft
          </div>
          <h1 style={{
            color: '#fff',
            fontSize: 'clamp(32px, 5vw, 52px)',
            fontWeight: 800,
            lineHeight: 1.15,
            margin: '0 0 16px',
            letterSpacing: -0.5,
          }}>
            Handcrafted Woodwork<br />& CNC
          </h1>
          <p style={{
            color: '#ccc',
            fontSize: 'clamp(16px, 2.5vw, 20px)',
            maxWidth: 560,
            margin: '0 auto 32px',
            lineHeight: 1.5,
          }}>
            Precision woodworking and CNC fabrication for homes, businesses, and creative projects.
          </p>
          <a
            href="/intake/signup"
            style={{
              display: 'inline-block',
              background: 'linear-gradient(135deg, #d4a017, #e8b830)',
              color: '#2c1810',
              padding: '16px 40px',
              borderRadius: 12,
              fontSize: 17,
              fontWeight: 700,
              textDecoration: 'none',
              minHeight: 48,
            }}
          >
            Get a Free Quote
          </a>
        </div>
      </header>

      {/* Services */}
      <section style={{ maxWidth: 1000, margin: '0 auto', padding: '64px 24px' }}>
        <h2 style={{
          textAlign: 'center',
          fontSize: 28,
          fontWeight: 700,
          color: '#2c1810',
          marginBottom: 48,
        }}>
          Our Services
        </h2>
        <div style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
          gap: 20,
        }}>
          {services.map((s) => (
            <div key={s.name} style={{
              background: '#fff',
              borderRadius: 14,
              padding: '28px 24px',
              border: '1px solid #ece8e0',
            }}>
              <h3 style={{
                fontSize: 18,
                fontWeight: 700,
                color: '#d4a017',
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
        background: 'linear-gradient(135deg, #d4a017, #e8b830)',
        padding: '56px 24px',
        textAlign: 'center',
      }}>
        <h2 style={{
          color: '#2c1810',
          fontSize: 26,
          fontWeight: 700,
          marginBottom: 16,
        }}>
          Bring Your Vision to Life
        </h2>
        <p style={{
          color: '#444',
          fontSize: 16,
          marginBottom: 28,
          maxWidth: 500,
          marginLeft: 'auto',
          marginRight: 'auto',
        }}>
          From concept to finished piece — we handle design, fabrication, and delivery.
        </p>
        <a
          href="/intake/signup"
          style={{
            display: 'inline-block',
            background: '#2c1810',
            color: '#e8b830',
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
        <h2 style={{ fontSize: 24, fontWeight: 700, color: '#2c1810', marginBottom: 20 }}>
          Contact Us
        </h2>
        <p style={{ color: '#555', fontSize: 15, margin: '8px 0' }}>
          <strong>Email:</strong>{' '}
          <a href="mailto:woodcraft@empirebox.store" style={{ color: '#d4a017' }}>
            woodcraft@empirebox.store
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
        background: '#2c1810',
        color: '#888',
        textAlign: 'center',
        padding: '24px',
        fontSize: 13,
      }}>
        &copy; {new Date().getFullYear()} WoodCraft by Empire. All rights reserved.
      </footer>
    </div>
  );
}
