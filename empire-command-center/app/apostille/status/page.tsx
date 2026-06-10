import ApostilleStatusForm from '../../components/public/ApostilleStatusForm';

export const metadata = {
  title: 'Track Your Order — ApostApp',
  description: 'ApostApp — Apostille & Document Legalization Support. Powered by EmpireBox.',
};

export default function ApostilleStatusPage() {
  return (
    <main style={{ maxWidth: 640, margin: '0 auto', padding: '32px 16px', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#1a1a1a' }}>
      <header style={{ marginBottom: 20 }}>
        <h1 style={{ fontSize: 28, fontWeight: 900, marginTop: 0, marginBottom: 4 }}>ApostApp</h1>
        <p style={{ fontSize: 14, color: '#525252', margin: 0, fontStyle: 'italic' }}>
          Apostille &amp; Document Legalization Support
        </p>
        <p style={{ fontSize: 11, color: '#737373', marginTop: 4 }}>
          Powered by <a href="https://empirebox.store" style={{ color: '#0ea5e9', textDecoration: 'none' }}>EmpireBox</a>
        </p>
      </header>

      <p style={{ fontSize: 15, color: '#525252', marginTop: 0, marginBottom: 20 }}>
        Track your request. Enter the order ID and the email address you used when you submitted.
      </p>
      <ApostilleStatusForm />
      <p style={{ fontSize: 13, color: '#737373', marginTop: 24, textAlign: 'center' }}>
        Need help? Contact us at <a href="mailto:apostille@empirebox.store" style={{ color: '#0ea5e9' }}>apostille@empirebox.store</a>.
      </p>
      <footer style={{ marginTop: 32, paddingTop: 16, borderTop: '1px solid #e5e5e5', fontSize: 12, color: '#737373', textAlign: 'center' }}>
        ApostApp is a service of EmpireBox. <a href="https://empirebox.store" style={{ color: '#0ea5e9' }}>empirebox.store</a>
      </footer>
    </main>
  );
}
