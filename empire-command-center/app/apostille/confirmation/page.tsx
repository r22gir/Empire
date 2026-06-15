import ApostilleConfirmationContent from '../../components/public/ApostilleConfirmationContent';

export const metadata = {
  title: 'Request Received — ApostApp',
  description: 'ApostApp — Apostille & Document Legalization Support. Powered by EmpireBox.',
};

export default function ApostilleConfirmationPage() {
  return (
    <main style={{ maxWidth: 560, margin: '0 auto', padding: '32px 16px', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#1a1a1a' }}>
      <header style={{ marginBottom: 16, textAlign: 'center' }}>
        <h1 style={{ fontSize: 24, fontWeight: 900, margin: 0 }}>ApostApp</h1>
        <p style={{ fontSize: 12, color: '#525252', margin: '2px 0 0', fontStyle: 'italic' }}>
          Apostille &amp; Document Legalization Support
        </p>
        <p style={{ fontSize: 11, color: '#737373', marginTop: 2 }}>
          Powered by <a href="https://empirebox.store" style={{ color: '#0ea5e9', textDecoration: 'none' }}>EmpireBox</a>
        </p>
      </header>
      <ApostilleConfirmationContent />
      <footer style={{ marginTop: 24, paddingTop: 12, borderTop: '1px solid #e5e5e5', fontSize: 11, color: '#737373', textAlign: 'center' }}>
        ApostApp is a service of EmpireBox. <a href="https://empirebox.store" style={{ color: '#0ea5e9' }}>empirebox.store</a>
      </footer>
    </main>
  );
}
