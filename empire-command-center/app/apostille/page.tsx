import ApostilleIntakeForm from '../components/public/ApostilleIntakeForm';
import ApostilleServiceNavigator from '../components/public/ApostilleServiceNavigator';

export const metadata = {
  title: 'ApostApp — Apostille & Document Legalization Support',
  description: 'ApostApp prepares, submits, and tracks your apostille request. DC, MD, VA, and Federal apostilles supported. Powered by EmpireBox.',
};

// R1D-PUB-NAV-3: Public ApostApp scroll + readability fix.
// 1. `data-intake-page` on the <main> element activates the existing
//    `body:has([data-intake-page]) { overflow: auto; height: auto; }` rule
//    in globals.css — that rule is the intended scroll fix but it only
//    triggers if a DOM ancestor has the [data-intake-page] attribute.
//    Without this attribute, the global `body { height: 100vh; overflow: hidden; }`
//    rule (set for the Command Center's fixed-viewport app) clips the
//    public page and customers cannot scroll to see the full Navigator.
// 2. The sticky mini-nav at the top gives anchor links to the 8
//    Navigator sections + the intake form, so customers can jump around
//    without scrolling through every section.
// 3. The two prominent "Start my request" / "Not sure? Submit for review"
//    buttons above the fold give customers a clear path to the intake
//    form, even if they don't read the full Navigator.
const SECTIONS = [
  { id: 'nav-services',  label: 'Services' },
  { id: 'nav-notary',    label: 'Notary' },
  { id: 'nav-business',  label: 'Business' },
  { id: 'nav-pricing',   label: 'Pricing' },
  { id: 'nav-shipping',  label: 'Shipping' },
  { id: 'nav-upload',    label: 'Upload' },
  { id: 'nav-faq',       label: 'FAQ' },
  { id: 'intake-form',   label: 'Intake' },
];

export default function PublicApostillePage() {
  return (
    <main
      data-intake-page
      style={{ maxWidth: 720, margin: '0 auto', padding: '32px 16px 96px', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#1a1a1a' }}
    >
      <header id="nav-start" style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 32, fontWeight: 900, marginTop: 0, marginBottom: 4 }}>ApostApp</h1>
        <p style={{ fontSize: 15, color: '#525252', margin: 0, fontStyle: 'italic' }}>
          Apostille &amp; Document Legalization Support
        </p>
        <p style={{ fontSize: 12, color: '#737373', marginTop: 4 }}>
          Powered by <a href="https://empirebox.store" style={{ color: '#0ea5e9', textDecoration: 'none' }}>EmpireBox</a>
        </p>
      </header>

      <p style={{ fontSize: 16, color: '#525252', marginTop: 0, marginBottom: 16 }}>
        We prepare, submit, and track your apostille request — for use in foreign countries.
        Support for DC, MD, VA, and Federal (US Department of State) apostilles.
      </p>

      {/* R1D-PUB-NAV-3: two prominent jump-to-intake buttons above the fold.
          These give customers a clear, fast path to the intake form without
          having to scroll through the full Navigator. */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 20 }} data-testid="cta-buttons">
        <a
          href="#intake-form"
          data-testid="cta-start"
          style={{
            display: 'block', textAlign: 'center', padding: '14px 18px',
            background: '#0ea5e9', color: '#fff', borderRadius: 8, fontWeight: 700,
            fontSize: 16, textDecoration: 'none', cursor: 'pointer',
            boxShadow: '0 2px 8px rgba(14,165,233,0.18)',
          }}
        >
          Start my request →
        </a>
        <a
          href="#intake-form"
          data-testid="cta-not-sure"
          style={{
            display: 'block', textAlign: 'center', padding: '10px 18px',
            background: '#fff', color: '#0ea5e9', border: '1px solid #0ea5e9',
            borderRadius: 8, fontWeight: 600, fontSize: 14, textDecoration: 'none',
            cursor: 'pointer',
          }}
        >
          Not sure? Submit for review
        </a>
      </div>

      <section style={{ background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 6, padding: 14, marginBottom: 16, fontSize: 14, lineHeight: 1.55, color: '#0c4a6e' }}>
        <strong>What is an apostille?</strong>
        <p style={{ margin: '6px 0 0' }}>
          An apostille is a certificate that authenticates the origin of a public document (birth
          certificate, diploma, corporate filing, etc.) for use in another country that is part of
          the 1961 Hague Convention. Apostilles are different from notarization: notarization confirms
          a signature is real, while an apostille confirms the document itself is genuine.
        </p>
      </section>

      {/* R1D-PUB-NAV-3: sticky mini-nav for in-page anchor jumping.
          Sticks to the top of the viewport so customers can always reach
          any section without scrolling back up. */}
      <nav
        aria-label="Page sections"
        data-testid="mini-nav"
        style={{
          position: 'sticky', top: 0, zIndex: 50,
          background: '#fff', borderTop: '1px solid #e5e5e5', borderBottom: '1px solid #e5e5e5',
          marginBottom: 16, padding: '8px 0',
        }}
      >
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 4, alignItems: 'center' }}>
          <span style={{ fontSize: 11, fontWeight: 700, color: '#737373', textTransform: 'uppercase', letterSpacing: 0.5, marginRight: 6, padding: '0 4px' }}>
            Jump to
          </span>
          {SECTIONS.map((s) => (
            <a
              key={s.id}
              href={`#${s.id}`}
              data-testid={`mini-nav-${s.id}`}
              style={{
                fontSize: 12, color: '#0ea5e9', textDecoration: 'none',
                padding: '4px 8px', borderRadius: 4,
              }}
            >
              {s.label}
            </a>
          ))}
        </div>
      </nav>

      <ApostilleServiceNavigator />

      <ApostilleIntakeForm />

      <footer style={{ marginTop: 32, paddingTop: 16, borderTop: '1px solid #e5e5e5', fontSize: 12, color: '#737373', textAlign: 'center' }}>
        ApostApp is a service of EmpireBox. <a href="https://empirebox.store" style={{ color: '#0ea5e9' }}>empirebox.store</a>
      </footer>
    </main>
  );
}
