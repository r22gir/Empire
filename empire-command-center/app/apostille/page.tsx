import ApostilleIntakeForm from '../components/public/ApostilleIntakeForm';

export const metadata = {
  title: 'Apostille Fast Lane — EmpireBox',
  description: 'We prepare, submit, and track your apostille request. DC, MD, VA, and Federal apostilles supported.',
};

export default function PublicApostillePage() {
  return (
    <main style={{ maxWidth: 720, margin: '0 auto', padding: '32px 16px', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#1a1a1a' }}>
      <h1 style={{ fontSize: 32, fontWeight: 900, marginTop: 0, marginBottom: 8 }}>Apostille Fast Lane</h1>
      <p style={{ fontSize: 16, color: '#525252', marginTop: 0, marginBottom: 24 }}>
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
    </main>
  );
}
