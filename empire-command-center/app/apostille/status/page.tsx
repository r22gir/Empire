import ApostilleStatusForm from '../../components/public/ApostilleStatusForm';

export const metadata = {
  title: 'Track Your Apostille — EmpireBox',
  description: 'Check the status of your apostille request.',
};

export default function ApostilleStatusPage() {
  return (
    <main style={{ maxWidth: 640, margin: '0 auto', padding: '32px 16px', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#1a1a1a' }}>
      <h1 style={{ fontSize: 28, fontWeight: 900, marginTop: 0, marginBottom: 8 }}>Track your apostille</h1>
      <p style={{ fontSize: 15, color: '#525252', marginTop: 0, marginBottom: 20 }}>
        Enter the order ID and the email address you used when you submitted your request.
      </p>
      <ApostilleStatusForm />
      <p style={{ fontSize: 13, color: '#737373', marginTop: 24, textAlign: 'center' }}>
        Need help? Contact us at <a href="mailto:apostille@empirebox.store" style={{ color: '#0ea5e9' }}>apostille@empirebox.store</a>.
      </p>
    </main>
  );
}
