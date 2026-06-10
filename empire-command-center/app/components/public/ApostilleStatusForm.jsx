'use client';

import { useState } from 'react';

export default function ApostilleStatusForm() {
  const [orderId, setOrderId] = useState('');
  const [email, setEmail] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [status, setStatus] = useState(null);

  function submit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setStatus(null);
    fetch('/api/v1/apostapp/public/verify', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ order_id: orderId.trim(), email: email.trim() }),
    })
      .then(function (r) { return r.json().then(function (body) { return { ok: r.ok, body: body }; }); })
      .then(function (res) {
        if (r = res, !r.ok) {
          if (r.body && typeof r.body.detail === 'string') throw new Error(r.body.detail);
          throw new Error('Request failed (' + (r.body ? JSON.stringify(r.body) : 'unknown') + ')');
        }
        setStatus(res.body);
        setLoading(false);
      })
      .catch(function (err) {
        setError(err.message || 'Request failed');
        setLoading(false);
      });
  }

  return (
    <div>
      <form onSubmit={submit} data-testid="status-form" style={{ background: '#fff', padding: 20, borderRadius: 6, border: '1px solid #e5e5e5' }}>
        <div style={{ marginBottom: 12 }}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 'bold', marginBottom: 4 }}>Order ID *</label>
          <input
            type="text"
            required
            value={orderId}
            onChange={function (e) { setOrderId(e.target.value); }}
            placeholder="e.g. ba62cb53"
            style={{ width: '100%', padding: 8, fontSize: 14, border: '1px solid #d4d4d4', borderRadius: 4, boxSizing: 'border-box' }}
          />
        </div>
        <div style={{ marginBottom: 12 }}>
          <label style={{ display: 'block', fontSize: 13, fontWeight: 'bold', marginBottom: 4 }}>Email *</label>
          <input
            type="email"
            required
            value={email}
            onChange={function (e) { setEmail(e.target.value); }}
            placeholder="you@example.com"
            style={{ width: '100%', padding: 8, fontSize: 14, border: '1px solid #d4d4d4', borderRadius: 4, boxSizing: 'border-box' }}
          />
        </div>
        {error && (
          <div data-testid="error" style={{ background: '#fee2e2', color: '#991b1b', padding: 10, borderRadius: 4, fontSize: 14, marginBottom: 12 }}>
            {error}
          </div>
        )}
        <button
          type="submit"
          disabled={loading}
          data-testid="submit"
          style={{
            padding: '10px 20px',
            background: loading ? '#a3a3a3' : '#0ea5e9',
            color: '#fff',
            border: 'none',
            borderRadius: 6,
            fontSize: 14,
            fontWeight: 'bold',
            cursor: loading ? 'not-allowed' : 'pointer',
            width: '100%',
          }}
        >
          {loading ? 'Checking…' : 'Check status'}
        </button>
      </form>

      {status && (
        <div data-testid="status-result" style={{ marginTop: 20, background: '#fff', borderRadius: 6, border: '1px solid #e5e5e5', padding: 20 }}>
          <h2 style={{ fontSize: 20, marginTop: 0 }}>Order {status.order_id}</h2>
          <div style={{ fontSize: 13, color: '#737373', marginBottom: 16 }}>
            Created {new Date(status.created_at).toLocaleDateString()} • Last updated {new Date(status.last_updated).toLocaleDateString()}
            {' • '}
            <span style={{
              background: status.paid ? '#dcfce7' : '#fef3c7',
              color: status.paid ? '#166534' : '#92400e',
              padding: '2px 8px',
              borderRadius: 4,
              fontSize: 12,
              fontWeight: 'bold',
            }}>
              {status.paid ? 'paid' : 'awaiting payment'}
            </span>
          </div>

          <div data-testid="timeline">
            {status.timeline.map(function (step, i) {
              return (
                <div key={i} style={{ display: 'flex', gap: 12, marginBottom: 12, alignItems: 'flex-start' }}>
                  <div style={{
                    width: 28, height: 28, borderRadius: '50%',
                    background: step.reached ? '#16a34a' : '#f5f5f5',
                    color: step.reached ? '#fff' : '#a3a3a3',
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    fontSize: 13, fontWeight: 'bold', flexShrink: 0,
                  }}>
                    {step.reached ? '✓' : (i + 1)}
                  </div>
                  <div>
                    <div style={{ fontSize: 15, fontWeight: 'bold' }}>{step.label}</div>
                    <div style={{ fontSize: 13, color: '#525252' }}>{step.description}</div>
                  </div>
                </div>
              );
            })}
          </div>

          <div style={{ background: '#f0f9ff', border: '1px solid #bae6fd', borderRadius: 4, padding: 12, fontSize: 14, color: '#0c4a6e', marginTop: 16 }}>
            <strong>Next step:</strong> {status.next_step_message}
          </div>
        </div>
      )}
    </div>
  );
}
