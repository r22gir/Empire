'use client';
import React, { useState } from 'react';
import { API } from '../../../lib/api';
import { Loader2, Plus, Trash2, ShoppingCart } from 'lucide-react';

interface Line {
  title: string;
  qty: string;
  unit: string;
  note: string;
}

const emptyLine = (): Line => ({ title: '', qty: '1', unit: 'ea', note: '' });

export default function SupplierCartSection() {
  const [jobId, setJobId] = useState('');
  const [supplier, setSupplier] = useState('');
  const [lines, setLines] = useState<Line[]>([emptyLine()]);
  const [cart, setCart] = useState<any>(null);
  const [ownerYes, setOwnerYes] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [lookupId, setLookupId] = useState('');
  const [pos, setPos] = useState<any[]>([]);

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid #ece8e0',
    fontSize: 13, background: '#fff',
  };

  const call = async (path: string, body?: any) => {
    const resp = await fetch(`${API}${path}`, {
      method: body ? 'POST' : 'GET',
      headers: { 'Content-Type': 'application/json' },
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await resp.json().catch(() => ({}));
    if (!resp.ok) throw new Error(typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail || data));
    return data;
  };

  const build = async () => {
    setBusy(true); setError(''); setOwnerYes(false);
    try {
      const data = await call('/supplier-carts', {
        job_id: jobId || undefined,
        supplier_name: supplier,
        lines: lines.filter(l => l.title).map(l => ({ ...l })),
      });
      setCart(data);
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  const request = async () => {
    if (!cart?.id) return;
    setBusy(true); setError('');
    try { setCart(await call(`/supplier-carts/${cart.id}/request-approval`, {})); }
    catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  const approve = async () => {
    if (!cart?.id) return;
    setBusy(true); setError('');
    try {
      const data = await call(`/supplier-carts/${cart.id}/approve`, { owner_yes: ownerYes, job_id: jobId || undefined });
      setCart(data);
      if (data.purchase_order?.job_id) {
        const listed = await call(`/jobs/${data.purchase_order.job_id}/purchase-orders`);
        setPos(listed.purchase_orders || []);
      }
    } catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  const tryPay = async () => {
    if (!cart?.id) return;
    setBusy(true); setError('');
    try { setCart(await call(`/supplier-carts/${cart.id}/pay`, { owner_yes: ownerYes })); }
    catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  const load = async () => {
    if (!lookupId) return;
    setBusy(true); setError('');
    try { setCart(await call(`/supplier-carts/${lookupId}`)); }
    catch (e: any) { setError(e.message); }
    finally { setBusy(false); }
  };

  return (
    <div style={{ maxWidth: 880, margin: '0 auto', padding: '24px 28px' }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>Supplier cart</h1>
      <p style={{ fontSize: 13, color: '#777', marginTop: 6 }}>
        Prepare the list, ask the owner, then issue a purchase order linked to the job.
        Checkout and pay never run without the owner&apos;s explicit yes — and this screen never charges a supplier.
      </p>

      <div className="grid grid-cols-2 gap-3 mt-4">
        <label style={{ fontSize: 12, color: '#555' }}>Job id
          <input style={inputStyle} value={jobId} onChange={e => setJobId(e.target.value)} placeholder="required before a PO" />
        </label>
        <label style={{ fontSize: 12, color: '#555' }}>Supplier
          <input style={inputStyle} value={supplier} onChange={e => setSupplier(e.target.value)} />
        </label>
      </div>

      {lines.map((line, i) => (
        <div key={i} className="grid grid-cols-6 gap-2 mt-2">
          <input style={{ ...inputStyle, gridColumn: 'span 2' }} placeholder="Item" value={line.title}
            onChange={e => setLines(prev => prev.map((l, idx) => idx === i ? { ...l, title: e.target.value } : l))} />
          <input style={inputStyle} placeholder="Qty (1 or 1 1/2)" value={line.qty}
            onChange={e => setLines(prev => prev.map((l, idx) => idx === i ? { ...l, qty: e.target.value } : l))} />
          <input style={inputStyle} placeholder="unit" value={line.unit}
            onChange={e => setLines(prev => prev.map((l, idx) => idx === i ? { ...l, unit: e.target.value } : l))} />
          <input style={inputStyle} placeholder="note" value={line.note}
            onChange={e => setLines(prev => prev.map((l, idx) => idx === i ? { ...l, note: e.target.value } : l))} />
          <button type="button" onClick={() => setLines(prev => prev.filter((_, idx) => idx !== i))}
            style={{ border: 'none', background: 'transparent', color: '#b91c1c', cursor: 'pointer' }}>
            <Trash2 size={16} />
          </button>
        </div>
      ))}

      <div className="flex flex-wrap gap-2 mt-4 mb-4">
        <button type="button" onClick={() => setLines(prev => [...prev, emptyLine()])}
          style={{ padding: '8px 12px', borderRadius: 10, border: '1px solid #ece8e0', background: '#fff', fontSize: 13, cursor: 'pointer' }}>
          <Plus size={14} style={{ display: 'inline', marginRight: 4 }} /> Line
        </button>
        <button type="button" onClick={build} disabled={busy}
          style={{ padding: '8px 14px', borderRadius: 10, border: 'none', background: '#b8960c', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
          {busy ? <Loader2 size={14} className="animate-spin" /> : <ShoppingCart size={14} style={{ display: 'inline', marginRight: 6 }} />}
          Build cart
        </button>
        <button type="button" onClick={request} disabled={busy || !cart}
          style={{ padding: '8px 12px', borderRadius: 10, border: '1px solid #ece8e0', background: '#fff', fontSize: 13, cursor: cart ? 'pointer' : 'not-allowed' }}>
          Request owner approval
        </button>
      </div>

      <label style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13, marginBottom: 10 }}>
        <input type="checkbox" checked={ownerYes} onChange={e => setOwnerYes(e.target.checked)} />
        I am the owner and I approve this purchase order (explicit yes)
      </label>

      <div className="flex flex-wrap gap-2 mb-4">
        <button type="button" onClick={approve} disabled={busy || !cart || !ownerYes}
          style={{ padding: '8px 14px', borderRadius: 10, border: 'none', background: ownerYes ? '#166534' : '#bbb', color: '#fff', fontSize: 13, fontWeight: 700, cursor: ownerYes && cart ? 'pointer' : 'not-allowed' }}>
          Create job PO
        </button>
        <button type="button" onClick={tryPay} disabled={busy || !cart}
          style={{ padding: '8px 12px', borderRadius: 10, border: '1px solid #fecaca', background: '#fef2f2', color: '#991b1b', fontSize: 13, cursor: 'pointer' }}>
          Try pay (must refuse live charge)
        </button>
      </div>

      <div className="flex gap-2 mb-4">
        <input style={inputStyle} placeholder="Load cart id" value={lookupId} onChange={e => setLookupId(e.target.value)} />
        <button type="button" onClick={load} style={{ padding: '8px 12px', borderRadius: 10, border: '1px solid #ece8e0', background: '#fff', fontSize: 13 }}>Load</button>
      </div>

      {error && <div style={{ color: '#b91c1c', fontSize: 13, marginBottom: 12 }}>{error}</div>}

      {cart && (
        <div className="empire-card flat" style={{ padding: 16, fontSize: 13 }}>
          <div style={{ fontWeight: 700 }}>Cart {cart.id}</div>
          <div>Status {cart.status} · prepared {String(cart.prepared)} · checked out {String(cart.checked_out)} · paid {String(cart.paid)}</div>
          <div style={{ color: '#555', marginTop: 6 }}>{cart.message}</div>
          <ul style={{ marginTop: 8 }}>
            {(cart.lines || []).map((ln: any) => (
              <li key={ln.id || ln.title}>{ln.qty} {ln.unit} {ln.title} {ln.note ? `— ${ln.note}` : ''}</li>
            ))}
          </ul>
          {cart.purchase_order && (
            <div style={{ marginTop: 8, fontWeight: 700, color: '#166534' }}>
              PO {cart.purchase_order.po_number} linked to job {cart.purchase_order.job_id}
            </div>
          )}
        </div>
      )}

      {pos.length > 0 && (
        <div className="mt-4" style={{ fontSize: 13 }}>
          <div style={{ fontWeight: 700 }}>Job purchase orders</div>
          {pos.map((po: any) => (
            <div key={po.id}>{po.po_number} · job {po.job_id} · paid {String(po.paid)}</div>
          ))}
        </div>
      )}
    </div>
  );
}
