'use client';
import React, { useState } from 'react';
import { API } from '../../../lib/api';
import { Loader2, Plus, Trash2, FileDown, LayoutGrid, ShoppingCart } from 'lucide-react';

type Grain = 'with' | 'free';

interface NestPart {
  name: string;
  woodW: string;
  woodL: string;
  fabricW: string;
  fabricL: string;
  grain: Grain;
  qty: string;
}

const emptyPart = (): NestPart => ({
  name: '',
  woodW: '',
  woodL: '',
  fabricW: '',
  fabricL: '',
  grain: 'with',
  qty: '1',
});

export default function CncNestingSection() {
  const [title, setTitle] = useState('CNC cut list');
  const [jobId, setJobId] = useState('');
  const [kerf, setKerf] = useState('1/8');
  const [parts, setParts] = useState<NestPart[]>([emptyPart()]);
  const [result, setResult] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [cartMsg, setCartMsg] = useState('');

  const updatePart = (i: number, patch: Partial<NestPart>) => {
    setParts(prev => prev.map((p, idx) => (idx === i ? { ...p, ...patch } : p)));
  };

  const payload = () => ({
    title,
    job_id: jobId || undefined,
    kerf,
    machine_width: '29 1/2',
    tile_length: '29 1/2',
    parts: parts
      .filter(p => p.woodW && p.woodL)
      .map(p => ({
        name: p.name || 'Part',
        wood: { width: p.woodW, length: p.woodL },
        fabric: p.fabricW && p.fabricL ? { width: p.fabricW, length: p.fabricL } : undefined,
        grain: p.grain,
        qty: Number(p.qty) || 1,
      })),
  });

  const nest = async () => {
    setBusy(true);
    setError('');
    setCartMsg('');
    try {
      const resp = await fetch(`${API}/cnc/nest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload()),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Nest failed');
      setResult(data);
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  const downloadPdf = async () => {
    setBusy(true);
    setError('');
    try {
      const resp = await fetch(`${API}/cnc/nest/pdf`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload()),
      });
      if (!resp.ok) {
        const data = await resp.json().catch(() => ({}));
        throw new Error(data.detail || 'PDF failed');
      }
      const blob = await resp.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'cnc-cut-list.pdf';
      a.click();
      URL.revokeObjectURL(url);
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  const buildCart = async () => {
    if (!result) return;
    setBusy(true);
    setCartMsg('');
    setError('');
    try {
      const resp = await fetch(`${API}/supplier-carts/from-nest`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ nest: result, job_id: jobId || result.job_id }),
      });
      const data = await resp.json();
      if (!resp.ok) throw new Error(data.detail || 'Cart failed');
      setCartMsg(`${data.message} Cart ${data.id}. Status: ${data.status}. Not paid.`);
    } catch (e: any) {
      setError(e.message || String(e));
    } finally {
      setBusy(false);
    }
  };

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '8px 10px', borderRadius: 8, border: '1px solid #ece8e0',
    fontSize: 13, background: '#fff',
  };

  return (
    <div style={{ maxWidth: 1040, margin: '0 auto', padding: '24px 28px' }}>
      <h1 style={{ fontSize: 22, fontWeight: 600, margin: 0 }}>X-Carve cut list</h1>
      <p style={{ fontSize: 13, color: '#777', marginTop: 6 }}>
        Width max 29 1/2&quot;. Any length via tiling with registration marks.
        Wood is true size. Foam equals wood. Fabric is a separate labeled size.
        Sizes as fractions only — never decimals.
      </p>

      <div className="grid grid-cols-3 gap-3 mt-4 mb-4">
        <label style={{ fontSize: 12, color: '#555' }}>Title
          <input style={inputStyle} value={title} onChange={e => setTitle(e.target.value)} />
        </label>
        <label style={{ fontSize: 12, color: '#555' }}>Job id
          <input style={inputStyle} value={jobId} onChange={e => setJobId(e.target.value)} placeholder="optional" />
        </label>
        <label style={{ fontSize: 12, color: '#555' }}>Kerf / blade
          <input style={inputStyle} value={kerf} onChange={e => setKerf(e.target.value)} placeholder="1/8" />
        </label>
      </div>

      {parts.map((p, i) => (
        <div key={i} className="empire-card flat" style={{ marginBottom: 10, padding: 12 }}>
          <div className="grid grid-cols-7 gap-2 items-end">
            <label style={{ fontSize: 11, color: '#555', gridColumn: 'span 2' }}>Part
              <input style={inputStyle} value={p.name} onChange={e => updatePart(i, { name: e.target.value })} />
            </label>
            <label style={{ fontSize: 11, color: '#555' }}>Wood W
              <input style={inputStyle} value={p.woodW} onChange={e => updatePart(i, { woodW: e.target.value })} placeholder="12 1/2" />
            </label>
            <label style={{ fontSize: 11, color: '#555' }}>Wood L
              <input style={inputStyle} value={p.woodL} onChange={e => updatePart(i, { woodL: e.target.value })} placeholder="24" />
            </label>
            <label style={{ fontSize: 11, color: '#555' }}>Fabric W
              <input style={inputStyle} value={p.fabricW} onChange={e => updatePart(i, { fabricW: e.target.value })} placeholder="15" />
            </label>
            <label style={{ fontSize: 11, color: '#555' }}>Fabric L
              <input style={inputStyle} value={p.fabricL} onChange={e => updatePart(i, { fabricL: e.target.value })} placeholder="27" />
            </label>
            <button type="button" onClick={() => setParts(prev => prev.filter((_, idx) => idx !== i))}
              style={{ height: 36, border: 'none', background: 'transparent', color: '#b91c1c', cursor: 'pointer' }}>
              <Trash2 size={16} />
            </button>
          </div>
          <div className="flex gap-3 mt-2" style={{ fontSize: 12 }}>
            <label>Qty <input style={{ ...inputStyle, width: 64, display: 'inline-block' }} value={p.qty} onChange={e => updatePart(i, { qty: e.target.value })} /></label>
            <label>Grain
              <select style={{ ...inputStyle, width: 120, display: 'inline-block', marginLeft: 6 }}
                value={p.grain} onChange={e => updatePart(i, { grain: e.target.value as Grain })}>
                <option value="with">with (no rotate)</option>
                <option value="free">free</option>
              </select>
            </label>
            <span style={{ color: '#999' }}>Foam = wood {p.woodW && p.woodL ? `${p.woodW} x ${p.woodL}` : ''}</span>
          </div>
        </div>
      ))}

      <div className="flex flex-wrap gap-2 mb-4">
        <button type="button" onClick={() => setParts(prev => [...prev, emptyPart()])}
          className="flex items-center gap-2" style={{ padding: '8px 12px', borderRadius: 10, border: '1px solid #ece8e0', background: '#fff', fontSize: 13, cursor: 'pointer' }}>
          <Plus size={14} /> Add part
        </button>
        <button type="button" onClick={nest} disabled={busy}
          className="flex items-center gap-2" style={{ padding: '8px 14px', borderRadius: 10, border: 'none', background: '#b8960c', color: '#fff', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
          {busy ? <Loader2 size={14} className="animate-spin" /> : <LayoutGrid size={14} />} Nest
        </button>
        <button type="button" onClick={downloadPdf} disabled={busy}
          className="flex items-center gap-2" style={{ padding: '8px 14px', borderRadius: 10, border: '1px solid #f0e6c0', background: '#fdf8eb', color: '#b8960c', fontSize: 13, fontWeight: 700, cursor: 'pointer' }}>
          <FileDown size={14} /> PDF yield
        </button>
        <button type="button" onClick={buildCart} disabled={busy || !result}
          className="flex items-center gap-2" style={{ padding: '8px 14px', borderRadius: 10, border: '1px solid #ece8e0', background: '#fff', fontSize: 13, cursor: result ? 'pointer' : 'not-allowed' }}>
          <ShoppingCart size={14} /> Build supplier cart
        </button>
      </div>

      {error && <div style={{ color: '#b91c1c', fontSize: 13, marginBottom: 12 }}>{error}</div>}
      {cartMsg && <div style={{ color: '#166534', fontSize: 13, marginBottom: 12 }}>{cartMsg}</div>}

      {result && (
        <div className="empire-card flat" style={{ padding: 16 }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 8 }}>
            {result.machine} · width {result.machine_width} · kerf {result.kerf}
          </div>
          <table style={{ width: '100%', fontSize: 12, borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ textAlign: 'left', color: '#777' }}>
                <th style={{ padding: '4px 6px' }}>Part</th>
                <th>Wood (true)</th>
                <th>Foam (= wood)</th>
                <th>Fabric (labeled)</th>
                <th>Grain</th>
              </tr>
            </thead>
            <tbody>
              {(result.cut_list || []).map((row: any) => (
                <tr key={row.id} style={{ borderTop: '1px solid #f0ebe3' }}>
                  <td style={{ padding: '6px' }}>{row.name}</td>
                  <td>{row.wood_width} × {row.wood_length}</td>
                  <td>{row.foam_width} × {row.foam_length}</td>
                  <td>{row.fabric_width ? `${row.fabric_width} × ${row.fabric_length}` : '—'}</td>
                  <td>{row.grain}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="mt-4" style={{ fontSize: 12 }}>
            {(result.yields?.wood || []).map((y: any) => (
              <div key={`w-${y.index}`}>Wood sheet {y.index}: {y.sheet_width} × {y.sheet_length} · yield {y.yield}{y.tiled ? ` · tile ${y.tile_index}/${y.tile_count}` : ''}</div>
            ))}
            {(result.yields?.foam || []).map((y: any) => (
              <div key={`f-${y.index}`}>Foam sheet {y.index}: yield {y.yield}</div>
            ))}
            {(result.yields?.fabric || []).map((y: any) => (
              <div key={`c-${y.index}`}>Fabric: {y.sheet_width} usable · yield {y.yield}</div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
