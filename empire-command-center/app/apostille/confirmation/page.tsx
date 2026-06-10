import ApostilleConfirmationContent from '../../components/public/ApostilleConfirmationContent';

export const metadata = {
  title: 'Request Received — EmpireBox Apostille',
  description: 'Your apostille request has been received.',
};

export default function ApostilleConfirmationPage() {
  return (
    <main style={{ maxWidth: 560, margin: '0 auto', padding: '32px 16px', fontFamily: 'system-ui, -apple-system, sans-serif', color: '#1a1a1a' }}>
      <ApostilleConfirmationContent />
    </main>
  );
}
