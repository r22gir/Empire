'use client';
import React, { useCallback, useEffect, useState } from 'react';
import { Trash2, Plus, MapPin } from 'lucide-react';
import { API } from '../../lib/api';
import { Header, btn, card, ghost, input, money, muted, useIsMobile } from './shared';

const G = `${API}/growth`;
const CHANNELS = ['google_ads', 'instagram', 'facebook', 'google_maps', 'website', 'referral', 'prospecting', 'houzz', 'yelp', 'email', 'print', 'events'];

function Kpi({ label, value }: { label: string; value: string | number }) {
  return (
    <div style={{ ...card, flex: '1 1 140px', minWidth: 0 }}>
      <div style={{ fontSize: 11, fontWeight: 700, color: '#888', textTransform: 'uppercase' }}>{label}</div>
      <div style={{ fontSize: 24, fontWeight: 800, marginTop: 4 }}>{value}</div>
    </div>
  );
}

export default function RoiDashboard() {
  const [months, setMonths] = useState(12);
  const [d, setD] = useState<any>(null);
  const [usage, setUsage] = useState<any>(null);
  const [form, setForm] = useState({ month: new Date().toISOString().slice(0, 7), channel: 'google_ads', amount: '', notes: '' });
  const [msg, setMsg] = useState('');
  const [busy, setBusy] = useState(false);
  const mobile = useIsMobile();
  const load = useCallback(() => {
    fetch(`${G}/roi?months=${months}`).then(r => r.json()).then(setD).catch(() => {});
    fetch(`${G}/place-details/usage`).then(r => r.json()).then(setUsage).catch(() => {});
  }, [months]);
  useEffect(() => { load(); }, [load]);

  const save = async () => {
    if (!form.amount) return;
    const r = await fetch(`${G}/spend`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ ...form, amount: Number(form.amount) }) });
    const j = await r.json();
    setMsg(r.ok ? `Saved ${money(j.amount)} for ${j.channel} in ${j.month}` : j.detail || 'Error');
    setForm({ ...form, amount: '', notes: '' }); load();
  };
  const del = async (id: number) => { await fetch(`${G}/spend/${id}`, { method: 'DELETE' }); load(); };
  const runPlaces = async () => {
    setBusy(true);
    const r = await fetch(`${G}/place-details/enrich`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ limit: 25 }) });
    const j = await r.json(); setBusy(false);
    setMsg(j.status === 'needs_key' ? 'Google key needed' : `Place Details: ${j.processed} checked, ${j.filled_website} websites, ${j.filled_phone} phones`);
    load();
  };

  const t = d?.totals || {};
  return (
    <div>
      <Header title="ROI by channel" subtitle="Lead source → quotes → paid invoices. Spend is entered by hand per month and channel. Test and mock records are left out."
        right={<select value={months} onChange={e => setMonths(Number(e.target.value))} style={{ ...input, width: 'auto' }}>
          {[3, 6, 12, 24].map(m => <option key={m} value={m}>Last {m} months</option>)}</select>} />
      <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginBottom: 16 }}>
        <Kpi label="Leads" value={t.leads ?? '—'} />
        <Kpi label="Quotes" value={`${t.quotes ?? 0} · ${money(t.quote_value)}`} />
        <Kpi label="Paid revenue" value={money(t.revenue)} />
        <Kpi label="Spend" value={money(t.spend)} />
        <Kpi label="ROI" value={t.roi_pct == null ? '—' : `${t.roi_pct}%`} />
      </div>

      {mobile ? (
        <div style={{ display: 'grid', gap: 10, marginBottom: 16 }}>
          {(d?.channels || []).map((c: any) => (
            <div key={c.channel} style={card}>
              <div style={{ display: 'flex', justifyContent: 'space-between', fontWeight: 700, fontSize: 15 }}>
                <span>{c.channel}</span><span>{money(c.revenue)}</span></div>
              <div style={{ ...muted, marginTop: 6, lineHeight: 1.6 }}>
                {c.leads} leads · {c.won_leads} won · {c.quotes} quotes ({money(c.quote_value)}) · {c.paid_invoices} paid<br />
                Spend {money(c.spend)} · cost/lead {money(c.cost_per_lead)} · ROI {c.roi_pct == null ? '—' : `${c.roi_pct}%`}
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ ...card, padding: 0, overflowX: 'auto', marginBottom: 16 }}>
          <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: 13 }}>
            <thead><tr style={{ textAlign: 'left', color: '#888', fontSize: 11, textTransform: 'uppercase' }}>
              {['Channel', 'Leads', 'Won', 'Quotes', 'Quote $', 'Paid inv.', 'Revenue', 'Spend', 'Cost/lead', 'Cost/won', 'ROI'].map(h =>
                <th key={h} style={{ padding: '10px 12px', borderBottom: '1px solid #e5e2dc' }}>{h}</th>)}
            </tr></thead>
            <tbody>{(d?.channels || []).map((c: any) => (
              <tr key={c.channel} style={{ borderBottom: '1px solid #f0ede8' }}>
                <td style={{ padding: '10px 12px', fontWeight: 600 }}>{c.channel}</td>
                <td style={{ padding: '10px 12px' }}>{c.leads}</td><td style={{ padding: '10px 12px' }}>{c.won_leads}</td>
                <td style={{ padding: '10px 12px' }}>{c.quotes}</td><td style={{ padding: '10px 12px' }}>{money(c.quote_value)}</td>
                <td style={{ padding: '10px 12px' }}>{c.paid_invoices}</td><td style={{ padding: '10px 12px', fontWeight: 700 }}>{money(c.revenue)}</td>
                <td style={{ padding: '10px 12px' }}>{money(c.spend)}</td><td style={{ padding: '10px 12px' }}>{money(c.cost_per_lead)}</td>
                <td style={{ padding: '10px 12px' }}>{money(c.cost_per_won)}</td>
                <td style={{ padding: '10px 12px' }}>{c.roi_pct == null ? '—' : `${c.roi_pct}%`}</td>
              </tr>))}</tbody>
          </table>
        </div>
      )}

      <div style={{ display: 'grid', gap: 12, gridTemplateColumns: mobile ? 'minmax(0, 1fr)' : '1fr 1fr' }}>
        <div style={card}>
          <div style={{ fontWeight: 700, marginBottom: 10 }}>Enter spend</div>
          <div style={{ display: 'grid', gap: 8, gridTemplateColumns: '1fr 1fr' }}>
            <input type="month" style={input} value={form.month} onChange={e => setForm({ ...form, month: e.target.value })} />
            <input list="lf-channels" style={input} value={form.channel} onChange={e => setForm({ ...form, channel: e.target.value })} />
            <datalist id="lf-channels">{CHANNELS.map(c => <option key={c} value={c} />)}</datalist>
            <input type="number" inputMode="decimal" placeholder="Amount $" style={input} value={form.amount} onChange={e => setForm({ ...form, amount: e.target.value })} />
            <input placeholder="Notes" style={input} value={form.notes} onChange={e => setForm({ ...form, notes: e.target.value })} />
          </div>
          <button onClick={save} style={{ ...btn('#1d4ed8'), marginTop: 10 }}><Plus size={15} /> Save spend</button>
          {msg && <div style={{ ...muted, marginTop: 8 }}>{msg}</div>}
          <div style={{ marginTop: 12, display: 'grid', gap: 6 }}>
            {(d?.spend_entries || []).map((s: any) => (
              <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 8, fontSize: 13 }}>
                <span style={{ width: 70 }}>{s.month}</span><span style={{ flex: 1 }}>{s.channel}</span><b>{money(s.amount)}</b>
                <button onClick={() => del(s.id)} style={{ ...ghost, padding: 6, minHeight: 30 }} aria-label="Delete"><Trash2 size={14} /></button>
              </div>))}
            {!d?.spend_entries?.length && <div style={muted}>No spend entered yet.</div>}
          </div>
        </div>
        <div style={card}>
          <div style={{ fontWeight: 700, marginBottom: 10, display: 'flex', gap: 6, alignItems: 'center' }}><MapPin size={16} /> Google Place Details (website + phone)</div>
          {usage ? (
            <div style={{ fontSize: 13, lineHeight: 1.7 }}>
              {usage.key_configured ? 'Key configured.' : 'No Google key configured.'} This month ({usage.month}): <b>{usage.calls}</b> calls,
              {' '}{usage.free_left} free left of {usage.free_calls}. Hard cap {usage.hard_cap} calls (${usage.budget_usd}/month).
              Estimated cost: <b>${usage.est_cost_usd}</b>.
            </div>
          ) : <div style={muted}>Loading…</div>}
          <button disabled={busy} onClick={runPlaces} style={{ ...ghost, marginTop: 10 }}>{busy ? 'Working…' : 'Fill 25 prospects (free tier)'}</button>
          <div style={{ ...muted, marginTop: 8 }}>Runs weekly on its own (Mondays). Batch runs stop at the free 1,000 calls.</div>
        </div>
      </div>
      <div style={{ ...muted, marginTop: 12 }}>{(d?.notes || []).join(' ')}</div>
    </div>
  );
}
