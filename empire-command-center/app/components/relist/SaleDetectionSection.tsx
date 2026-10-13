'use client';

import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, CheckCircle, RefreshCw, Shield } from 'lucide-react';
import { API } from '../../lib/api';

const SD = `${API}/relist/sale-detection`;

type Listing = {
  id: string;
  source_product_id: string;
  platform: string;
  title: string;
  status: string;
};

type EventRow = {
  id: string;
  listing_id: string;
  platform: string;
  action: string;
  status: string;
  title?: string;
};

export default function SaleDetectionSection() {
  const [settings, setSettings] = useState<{ owner_confirm_required: boolean; sandbox_mode: boolean } | null>(null);
  const [listings, setListings] = useState<Listing[]>([]);
  const [pending, setPending] = useState<EventRow[]>([]);
  const [events, setEvents] = useState<EventRow[]>([]);
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [form, setForm] = useState({ source_product_id: 'demo-sku', platform: 'ebay', title: 'Sandbox listing' });

  const load = useCallback(async () => {
    const [s, l, p, e] = await Promise.all([
      fetch(`${SD}/settings`).then(r => r.json()),
      fetch(`${SD}/sandbox/listings`).then(r => r.json()),
      fetch(`${SD}/confirmations`).then(r => r.json()),
      fetch(`${SD}/events`).then(r => r.json()),
    ]);
    setSettings(s);
    setListings(l.items || []);
    setPending(p.items || []);
    setEvents(e.items || []);
  }, []);

  useEffect(() => { load().catch(() => setMessage('Could not load sandbox sale detection.')); }, [load]);

  const toggleConfirm = async () => {
    if (!settings) return;
    setBusy(true);
    await fetch(`${SD}/settings`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ owner_confirm_required: !settings.owner_confirm_required }),
    });
    await load();
    setBusy(false);
  };

  const addListing = async () => {
    setBusy(true);
    await fetch(`${SD}/sandbox/listings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(form),
    });
    await load();
    setBusy(false);
  };

  const recordSale = async (listingId: string) => {
    setBusy(true);
    const res = await fetch(`${SD}/sandbox/sales`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ listing_id: listingId, sale_price: 0, note: 'sandbox-detected' }),
    });
    const body = await res.json();
    setMessage(body.message || 'Sale recorded in sandbox.');
    await load();
    setBusy(false);
  };

  const resolve = async (eventId: string, approve: boolean) => {
    setBusy(true);
    await fetch(`${SD}/confirmations/${eventId}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ approve }),
    });
    await load();
    setBusy(false);
  };

  return (
    <div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 16 }}>
        <div>
          <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: '#1a1a1a' }}>Sale Detection</h2>
          <p style={{ fontSize: 12, color: '#888', margin: '4px 0 0' }}>
            Vendoo-style sibling delist — sandbox only. Live marketplaces are never written.
          </p>
        </div>
        <button onClick={() => load()} style={{ border: '1px solid #ece8e0', background: '#fff', borderRadius: 8, padding: '6px 10px', cursor: 'pointer' }}>
          <RefreshCw size={14} />
        </button>
      </div>

      <div style={{ padding: 12, borderRadius: 12, background: '#ecfeff', border: '1px solid #a5f3fc', marginBottom: 16, fontSize: 12, color: '#0e7490', display: 'flex', gap: 8 }}>
        <Shield size={14} style={{ marginTop: 2 }} />
        Test/sandbox mode is locked on. Delists update isolated sandbox copies only — not `ra_listings` and not eBay/Poshmark/Mercari.
      </div>

      {message && (
        <div style={{ padding: 10, borderRadius: 10, background: '#f0fdf4', border: '1px solid #bbf7d0', color: '#166534', fontSize: 12, marginBottom: 12 }}>
          {message}
        </div>
      )}

      <div className="empire-card" style={{ marginBottom: 16, padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <div style={{ fontSize: 13, fontWeight: 700 }}>Owner confirm before delist</div>
            <div style={{ fontSize: 11, color: '#888' }}>When on, sibling delists wait for you. When off, sandbox auto-delists them.</div>
          </div>
          <button
            onClick={toggleConfirm}
            disabled={busy || !settings}
            style={{
              minWidth: 64, height: 32, borderRadius: 999, border: 'none', cursor: 'pointer',
              background: settings?.owner_confirm_required ? '#06b6d4' : '#d4d4d4',
              color: '#fff', fontWeight: 700, fontSize: 12,
            }}
          >
            {settings?.owner_confirm_required ? 'ON' : 'OFF'}
          </button>
        </div>
      </div>

      <div className="empire-card" style={{ marginBottom: 16, padding: 16 }}>
        <div style={{ fontSize: 12, fontWeight: 700, marginBottom: 10 }}>Add sandbox listing</div>
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          <input value={form.source_product_id} onChange={e => setForm({ ...form, source_product_id: e.target.value })} placeholder="Source SKU"
            style={{ padding: '8px 10px', border: '1px solid #ece8e0', borderRadius: 8, fontSize: 12 }} />
          <input value={form.platform} onChange={e => setForm({ ...form, platform: e.target.value })} placeholder="platform"
            style={{ padding: '8px 10px', border: '1px solid #ece8e0', borderRadius: 8, fontSize: 12 }} />
          <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })} placeholder="Title"
            style={{ padding: '8px 10px', border: '1px solid #ece8e0', borderRadius: 8, fontSize: 12, flex: 1 }} />
          <button onClick={addListing} disabled={busy} style={{ background: '#06b6d4', color: '#fff', border: 'none', borderRadius: 8, padding: '8px 12px', fontWeight: 700, fontSize: 12, cursor: 'pointer' }}>
            Add
          </button>
        </div>
      </div>

      <div className="empire-card" style={{ marginBottom: 16, padding: 0, overflow: 'hidden' }}>
        <div style={{ padding: 12, fontSize: 12, fontWeight: 700, borderBottom: '1px solid #ece8e0' }}>Sandbox listings</div>
        <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
          <thead>
            <tr style={{ color: '#999', textAlign: 'left' }}>
              <th style={{ padding: 8 }}>Title</th>
              <th style={{ padding: 8 }}>SKU</th>
              <th style={{ padding: 8 }}>Platform</th>
              <th style={{ padding: 8 }}>Status</th>
              <th style={{ padding: 8 }}></th>
            </tr>
          </thead>
          <tbody>
            {listings.map(l => (
              <tr key={l.id} style={{ borderTop: '1px solid #f3f0ea' }}>
                <td style={{ padding: 8 }}>{l.title}</td>
                <td style={{ padding: 8 }}>{l.source_product_id}</td>
                <td style={{ padding: 8 }}>{l.platform}</td>
                <td style={{ padding: 8 }}>{l.status}</td>
                <td style={{ padding: 8 }}>
                  {['active', 'listed'].includes(l.status) && (
                    <button onClick={() => recordSale(l.id)} disabled={busy}
                      style={{ fontSize: 11, border: '1px solid #06b6d4', color: '#06b6d4', background: '#fff', borderRadius: 8, padding: '4px 8px', cursor: 'pointer' }}>
                      Detect sale
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {listings.length === 0 && (
              <tr><td colSpan={5} style={{ padding: 16, color: '#aaa' }}>No sandbox listings yet. Add the same SKU on two platforms to demo sibling delist.</td></tr>
            )}
          </tbody>
        </table>
      </div>

      {pending.length > 0 && (
        <div className="empire-card" style={{ marginBottom: 16, padding: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 700, marginBottom: 10 }}>
            <AlertTriangle size={14} color="#d97706" /> Pending owner confirm
          </div>
          {pending.map(ev => (
            <div key={ev.id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '8px 0', borderTop: '1px solid #f3f0ea' }}>
              <div style={{ fontSize: 12 }}>Delist {ev.title || ev.listing_id} on {ev.platform}</div>
              <div style={{ display: 'flex', gap: 6 }}>
                <button onClick={() => resolve(ev.id, true)} style={{ background: '#16a34a', color: '#fff', border: 'none', borderRadius: 8, padding: '4px 10px', fontSize: 11, cursor: 'pointer' }}>Confirm delist</button>
                <button onClick={() => resolve(ev.id, false)} style={{ background: '#fff', color: '#666', border: '1px solid #ece8e0', borderRadius: 8, padding: '4px 10px', fontSize: 11, cursor: 'pointer' }}>Keep listed</button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="empire-card" style={{ padding: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: 12, fontWeight: 700, marginBottom: 10 }}>
          <CheckCircle size={14} color="#16a34a" /> Recent sandbox events
        </div>
        {events.length === 0 && <div style={{ fontSize: 12, color: '#aaa' }}>No delist events yet.</div>}
        {events.map(ev => (
          <div key={ev.id} style={{ fontSize: 11, color: '#555', padding: '6px 0', borderTop: '1px solid #f3f0ea' }}>
            {ev.platform} · {ev.action} · {ev.status}
          </div>
        ))}
      </div>
    </div>
  );
}
