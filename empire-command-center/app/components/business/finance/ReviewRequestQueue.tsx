'use client';

import { useEffect, useState } from 'react';
import { API } from '../../../lib/api';

interface ReviewRequest {
  id: string;
  invoice_number?: string;
  customer_id?: string;
  status: string;
  sendable?: boolean;
}

export default function ReviewRequestQueue() {
  const [items, setItems] = useState<ReviewRequest[]>([]);
  const [message, setMessage] = useState('Google review requests wait for owner approval. Nothing is sent automatically.');

  const load = () => {
    fetch(`${API}/workroom/quotes-commerce/review-requests`)
      .then((r) => r.json())
      .then((d) => setItems(d.items || []))
      .catch(() => setItems([]));
  };

  useEffect(() => { load(); }, []);

  const approve = async (id: string) => {
    const res = await fetch(`${API}/workroom/quotes-commerce/review-requests/${id}/approve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approved_by: 'owner' }),
    });
    if (res.ok) {
      setMessage('Owner approved. You can send the review request now.');
      load();
    }
  };

  const send = async (id: string) => {
    const res = await fetch(`${API}/workroom/quotes-commerce/review-requests/${id}/send`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ confirm: true }),
    });
    const data = await res.json().catch(() => ({}));
    if (data.sent) {
      setMessage('Review request sent.');
    } else {
      setMessage(data.reason === 'owner_approval_required'
        ? 'Owner approval is required before sending.'
        : data.reason === 'review_url_not_configured'
          ? 'Approved, but GOOGLE_REVIEW_URL is not configured so nothing was sent.'
          : data.reason || 'Not sent.');
    }
    load();
  };

  if (items.length === 0) {
    return (
      <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: '12px 14px', marginBottom: 16, fontSize: 12, color: '#666' }}>
        {message}
      </div>
    );
  }

  return (
    <div style={{ background: '#fff', border: '1px solid #e5e2dc', borderRadius: 10, padding: 14, marginBottom: 16 }}>
      <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 8 }}>Google review requests</div>
      <div style={{ fontSize: 11, color: '#777', marginBottom: 10 }}>{message}</div>
      {items.map((item) => (
        <div key={item.id} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: 8, padding: '8px 0', borderTop: '1px solid #f3efe8', fontSize: 12 }}>
          <div>
            <div style={{ fontWeight: 700 }}>{item.invoice_number || item.id}</div>
            <div style={{ color: '#888' }}>{item.status.replace(/_/g, ' ')}</div>
          </div>
          <div style={{ display: 'flex', gap: 6 }}>
            {item.status === 'pending_owner_approval' && (
              <button type="button" onClick={() => approve(item.id)} style={{ fontSize: 11, fontWeight: 700, background: '#fdf8eb', border: '1px solid #ead889', borderRadius: 8, padding: '6px 10px', cursor: 'pointer' }}>
                Approve
              </button>
            )}
            {item.status === 'owner_approved' && (
              <button type="button" onClick={() => send(item.id)} style={{ fontSize: 11, fontWeight: 700, background: '#16a34a', color: '#fff', border: 'none', borderRadius: 8, padding: '6px 10px', cursor: 'pointer' }}>
                Send review request
              </button>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}
