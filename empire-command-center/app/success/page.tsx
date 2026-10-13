'use client';

export default function CheckoutSuccessPage() {
  return (
    <div style={{ minHeight: '100vh', background: '#f5f3ef', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 24 }}>
      <div style={{ maxWidth: 480, background: '#fff', borderRadius: 16, padding: 32, border: '1px solid #ece8e0', textAlign: 'center' }}>
        <h1 style={{ margin: '0 0 12px', fontSize: 24 }}>You are in</h1>
        <p style={{ margin: 0, color: '#666', lineHeight: 1.6 }}>
          Stripe TEST checkout completed. Your subscription activates when the
          signed webhook arrives — this page does not flip billing state.
        </p>
      </div>
    </div>
  );
}
