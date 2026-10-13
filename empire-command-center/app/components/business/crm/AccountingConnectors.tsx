'use client';

import { useCallback, useEffect, useState } from 'react';
import { Loader2, RefreshCw, ShieldOff } from 'lucide-react';
import { API } from '../../../lib/api';

export default function AccountingConnectors() {
  const [status, setStatus] = useState<any>(null);
  const [qbo, setQbo] = useState<{ invoices: any[]; payments: any[] }>({ invoices: [], payments: [] });
  const [drafts, setDrafts] = useState<any[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    setError(null);
    try {
      const res = await fetch(`${API}/accounting/status`, { cache: 'no-store' });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail || 'Status failed');
      setStatus(data);
      if (data.flags?.qbo_sync?.enabled) {
        const [inv, pmt] = await Promise.all([
          fetch(`${API}/accounting/qbo/invoices`).then((r) => r.json()),
          fetch(`${API}/accounting/qbo/payments`).then((r) => r.json()),
        ]);
        setQbo({ invoices: inv.invoices || [], payments: pmt.payments || [] });
      }
      if (data.flags?.alegra_siigo?.enabled) {
        const dian = await fetch(`${API}/accounting/dian/drafts`).then((r) => r.json());
        setDrafts(dian.drafts || []);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to load accounting connectors');
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const syncQbo = async () => {
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`${API}/accounting/qbo/sync`, { method: 'POST' });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.detail || `Sync failed (${res.status})`);
      await load();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  const flags = status?.flags || {};
  const qboOn = !!flags.qbo_sync?.enabled;
  const dianOn = !!flags.alegra_siigo?.enabled;

  return (
    <div style={{ maxWidth: 900, margin: '0 auto' }}>
      <h2 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', marginBottom: 8 }}>Accounting connectors</h2>
      <p style={{ fontSize: 13, color: '#777', marginBottom: 16 }}>
        Sandbox credentials only. No live-data writes. QuickBooks Online is Studio/Empire. Alegra/Siigo DIAN is Maxine.
      </p>

      <div style={{ padding: '10px 12px', borderRadius: 10, background: '#fef2f2', border: '1px solid #fecaca', display: 'flex', gap: 8, marginBottom: 16 }}>
        <ShieldOff size={14} style={{ color: '#b91c1c', marginTop: 2 }} />
        <div style={{ fontSize: 12, color: '#7f1d1d' }}>
          Live QuickBooks, Alegra, Siigo, and DIAN submits are blocked. Staging tables only.
        </div>
      </div>

      {error && (
        <div style={{ padding: '8px 10px', borderRadius: 8, background: '#fff7ed', border: '1px solid #fed7aa', color: '#9a3412', fontSize: 12, marginBottom: 12 }}>
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 mb-4">
        <div className="empire-card flat" style={{ padding: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a' }}>QuickBooks Online</div>
          <div style={{ fontSize: 11, color: '#777', margin: '6px 0 12px' }}>
            Edition {flags.edition || '—'} · {qboOn ? 'sandbox pull enabled' : 'disabled'}
          </div>
          <button
            onClick={syncQbo}
            disabled={!qboOn || busy}
            className="flex items-center gap-1 cursor-pointer disabled:opacity-50"
            style={{ minHeight: 36, padding: '0 12px', borderRadius: 8, background: qboOn ? '#b8960c' : '#ece8e0', color: qboOn ? '#fff' : '#888', border: 'none', fontSize: 12, fontWeight: 700 }}
          >
            {busy ? <Loader2 size={12} className="animate-spin" /> : <RefreshCw size={12} />}
            Pull sandbox invoices/payments
          </button>
        </div>
        <div className="empire-card flat" style={{ padding: 16 }}>
          <div style={{ fontSize: 12, fontWeight: 700, color: '#1a1a1a' }}>Alegra / Siigo (DIAN)</div>
          <div style={{ fontSize: 11, color: '#777', marginTop: 6 }}>
            Maxine stub · {dianOn ? 'local drafts only' : 'disabled'} · live submit blocked
          </div>
        </div>
      </div>

      {qbo.invoices.length > 0 && (
        <div className="empire-card flat" style={{ padding: 16, marginBottom: 12 }}>
          <div className="section-label" style={{ marginBottom: 10 }}>QBO sandbox invoices</div>
          {qbo.invoices.map((inv) => (
            <div key={inv.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '6px 0', borderBottom: '1px solid #f5f3ef' }}>
              <span>{inv.doc_number} · {inv.customer_name}</span>
              <span style={{ fontWeight: 700 }}>${Number(inv.amount || 0).toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}

      {qbo.payments.length > 0 && (
        <div className="empire-card flat" style={{ padding: 16, marginBottom: 12 }}>
          <div className="section-label" style={{ marginBottom: 10 }}>QBO sandbox payments</div>
          {qbo.payments.map((pmt) => (
            <div key={pmt.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '6px 0', borderBottom: '1px solid #f5f3ef' }}>
              <span>{pmt.method} · {pmt.customer_name}</span>
              <span style={{ fontWeight: 700, color: '#16a34a' }}>${Number(pmt.amount || 0).toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}

      {drafts.length > 0 && (
        <div className="empire-card flat" style={{ padding: 16 }}>
          <div className="section-label" style={{ marginBottom: 10 }}>DIAN local drafts</div>
          {drafts.map((d) => (
            <div key={d.id} style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12, padding: '6px 0', borderBottom: '1px solid #f5f3ef' }}>
              <span>{d.provider} · {d.customer_name} · {d.status}</span>
              <span>{d.currency} {Number(d.amount || 0).toLocaleString()}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
