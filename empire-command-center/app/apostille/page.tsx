import ApostilleIntakeForm from '../components/public/ApostilleIntakeForm';

export const metadata = {
  title: 'ApostApp — Apostille & Document Legalization Support',
  description: 'ApostApp prepares, submits, and tracks your apostille request. DC, MD, VA, and Federal apostilles supported. Powered by EmpireBox.',
};

export default function PublicApostillePage() {
  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: '32px 16px', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#1a1a1a' }}>
      <header style={{ marginBottom: 24 }}>
        <h1 style={{ fontSize: 32, fontWeight: 900, marginTop: 0, marginBottom: 4 }}>ApostApp</h1>
        <p style={{ fontSize: 15, color: '#525252', margin: 0, fontStyle: 'italic' }}>
          Apostille &amp; Document Legalization Support
        </p>
        <p style={{ fontSize: 12, color: '#737373', marginTop: 4 }}>
          Powered by <a href="https://empirebox.store" style={{ color: '#0ea5e9', textDecoration: 'none' }}>EmpireBox</a>
        </p>
      </header>

      <p style={{ fontSize: 16, color: '#525252', marginTop: 0, marginBottom: 20 }}>
        We prepare, submit, and track your apostille request — for use in foreign countries.
        Support for DC, MD, VA, and Federal (US Department of State) apostilles.
      </p>

      <section style={{ background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 6, padding: 14, marginBottom: 20, fontSize: 14, lineHeight: 1.55, color: '#0c4a6e' }}>
        <strong>What is an apostille?</strong>
        <p style={{ margin: '6px 0 0' }}>
          An apostille is a certificate that authenticates the origin of a public document (birth
          certificate, diploma, corporate filing, etc.) for use in another country that is part of
          the 1961 Hague Convention. Apostilles are different from notarization: notarization confirms
          a signature is real, while an apostille confirms the document itself is genuine.
        </p>
      </section>

      <ApostilleIntakeForm />

      <footer style={{ marginTop: 32, paddingTop: 16, borderTop: '1px solid #e5e5e5', fontSize: 12, color: '#737373', textAlign: 'center' }}>
        ApostApp is a service of EmpireBox. <a href="https://empirebox.store" style={{ color: '#0ea5e9' }}>empirebox.store</a>
      </footer>
    </main>
  );
}
