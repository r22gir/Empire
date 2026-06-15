'use client';

import { useEffect, useState } from 'react';

export default function ApostilleConfirmationContent() {
  const [orderId, setOrderId] = useState('');
  const [testMode, setTestMode] = useState(true);

  useEffect(function () {
    var params = new URLSearchParams(window.location.search);
    setOrderId(params.get('order_id') || '');
    fetch('/api/v1/apostapp/public/config')
      .then(function (r) { return r.json(); })
      .then(function (d) { setTestMode(d.test_mode); })
      .catch(function () {});
  }, []);

  return (
    <div>
      {testMode && (
        <div style={{ background: '#fef3c7', color: '#92400e', padding: 10, textAlign: 'center', fontSize: 13, marginBottom: 16, border: '1px solid #fcd34d', borderRadius: 4 }}>
          <strong>TEST MODE</strong> — No real payments will be charged. Stripe is in test mode.
        </div>
      )}

      <div style={{ textAlign: 'center', marginBottom: 24 }}>
        <div style={{ width: 64, height: 64, borderRadius: '50%', background: '#dcfce7', color: '#16a34a', fontSize: 32, fontWeight: 900, display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 12px' }}>
          ✓
        </div>
        <h1 style={{ fontSize: 28, fontWeight: 900, margin: 0 }}>Request received</h1>
        <p style={{ fontSize: 15, color: '#525252', marginTop: 8 }}>
          Thank you. We have your apostille request and will review your documents within 1 business day.
        </p>
      </div>

      {orderId && (
        <div data-testid="order-id" style={{ background: '#fafafa', border: '1px solid #e5e5e5', borderRadius: 6, padding: 16, marginBottom: 20, textAlign: 'center' }}>
          <div style={{ fontSize: 12, fontWeight: 'bold', color: '#737373', textTransform: 'uppercase', marginBottom: 4 }}>
            Your order ID
          </div>
          <div style={{ fontSize: 22, fontWeight: 900, color: '#0ea5e9', fontFamily: 'monospace' }}>
            {orderId}
          </div>
        </div>
      )}

      <div style={{ background: '#fafafa', border: '1px solid #e5e5e5', borderRadius: 6, padding: 16, marginBottom: 20 }}>
        <h2 style={{ fontSize: 16, fontWeight: 'bold', marginTop: 0, marginBottom: 8 }}>What happens next</h2>
        <ol style={{ margin: 0, paddingLeft: 20, fontSize: 14, color: '#404040', lineHeight: 1.6 }}>
          <li>We review your documents and confirm eligibility (1 business day).</li>
          <li>We email you with submission instructions and any clarifications.</li>
          <li>We submit to the issuing authority.</li>
          <li>When the apostille is issued, we ship it back to you.</li>
        </ol>
      </div>

      <div style={{ textAlign: 'center' }}>
        <a
          href={orderId ? '/apostille/status?order_id=' + orderId : '/apostille/status'}
          data-testid="status-link"
          style={{ display: 'inline-block', padding: '12px 24px', background: '#0ea5e9', color: '#fff', borderRadius: 6, textDecoration: 'none', fontSize: 15, fontWeight: 'bold' }}
        >
          Track your order
        </a>
      </div>

      {testMode && (
        <div style={{ background: '#fffbeb', border: '1px solid #fcd34d', borderRadius: 4, padding: 12, fontSize: 12, color: '#92400e', marginTop: 20 }}>
          <strong>Operator note (dev only):</strong> This is a test-mode request. No real payment
          has been processed. Set <code>APOSTILLE_TEST_MODE=0</code> in the environment to switch
          to live payments.
        </div>
      )}
    </div>
  );
}
