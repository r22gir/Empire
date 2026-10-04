'use client';
import React, { useCallback, useEffect, useState } from 'react';
import { Lightbulb, CheckCircle, XCircle, RefreshCw, GitPullRequest, FileText, Copy, Plus, Rocket } from 'lucide-react';
import { API } from '../../lib/api';
import { Badge, Header, btn, card, ghost, input, muted, useIsMobile } from './shared';

const G = `${API}/growth/improvements`;
const STATUS: Record<string, { label: string; bg: string; color: string }> = {
  proposed: { label: 'Waiting for you', bg: '#fef3c7', color: '#b45309' },
  awaiting_build: { label: 'Awaiting build', bg: '#e0f2fe', color: '#0369a1' },
  building: { label: 'Building', bg: '#ede9fe', color: '#6d28d9' },
  pr_open: { label: 'PR ready to review', bg: '#dbeafe', color: '#1d4ed8' },
  merge_approved: { label: 'Merge approved', bg: '#dcfce7', color: '#15803d' },
  build_failed: { label: 'Build failed', bg: '#fee2e2', color: '#b91c1c' },
  rejected: { label: 'Rejected', bg: '#f5f3ef', color: '#666' },
  done: { label: 'Done', bg: '#dcfce7', color: '#15803d' },
};
const RISK: Record<string, string> = { low: '#16a34a', medium: '#d97706', high: '#dc2626' };

async function post(url: string, body: any = {}) {
  const r = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
  const j = await r.json();
  if (!r.ok) throw new Error(j.detail || 'Failed');
  return j;
}

function Req({ r, onChange }: { r: any; onChange: () => void }) {
  const [spec, setSpec] = useState<string | null>(null);
  const [pr, setPr] = useState(''); const [preview, setPreview] = useState('');
  const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  const s = STATUS[r.status] || STATUS.proposed;
  const act = async (fn: () => Promise<any>) => { setBusy(true); setErr(''); try { await fn(); onChange(); } catch (e: any) { setErr(e.message); } finally { setBusy(false); } };
  const showSpec = async () => { const j = await (await fetch(`${G}/${r.id}`)).json(); setSpec(j.spec); };

  return (
    <div style={{ ...card, display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0 }} data-imp-id={r.id}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ ...muted, fontWeight: 700 }}>IMP-{String(r.id).padStart(4, '0')}</span>
        <span style={{ fontWeight: 700, fontSize: 16, flex: 1, minWidth: 0, overflowWrap: 'anywhere' }}>{r.title}</span>
        <Badge text={s.label} bg={s.bg} color={s.color} />
      </div>
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
        <Badge text={`Risk: ${r.risk}`} bg="#fff" color={RISK[r.risk] || '#555'} />
        {(r.affected_modules || []).map((m: string) => <Badge key={m} text={m} wrap />)}
        <span style={muted}>via {r.requested_via} · {(r.created_at || '').slice(0, 16)}</span>
      </div>
      <div><div style={{ ...muted, fontWeight: 700 }}>Problem</div><div style={{ fontSize: 14, whiteSpace: 'pre-wrap' }}>{r.problem}</div></div>
      <div><div style={{ ...muted, fontWeight: 700 }}>Proposed change</div><div style={{ fontSize: 14, whiteSpace: 'pre-wrap' }}>{r.proposed_change}</div></div>
      {r.build_note && <div style={{ ...muted }}>{r.build_note}{r.branch ? ` · branch: ${r.branch}` : ''}</div>}
      {(r.pr_url || r.preview_url || r.agent_url) && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {r.pr_url && <a href={r.pr_url} target="_blank" rel="noreferrer" style={ghost}><GitPullRequest size={15} /> Open PR</a>}
          {r.preview_url && <a href={r.preview_url} target="_blank" rel="noreferrer" style={ghost}>Open preview</a>}
          {r.agent_url && <a href={r.agent_url} target="_blank" rel="noreferrer" style={ghost}>Cloud agent</a>}
        </div>
      )}
      <div style={{ ...muted, fontStyle: 'italic' }}>{r.next_step}</div>
      {err && <div style={{ color: '#dc2626', fontSize: 13 }}>{err}</div>}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {['proposed', 'build_failed', 'awaiting_build'].includes(r.status) && (
          <button disabled={busy} onClick={() => act(() => post(`${G}/${r.id}/approve`, { confirm: true }))} style={btn('#16a34a')}>
            <Rocket size={15} /> {r.status === 'proposed' ? 'Approve build' : 'Build again'}
          </button>)}
        {r.status === 'proposed' && <button disabled={busy} onClick={() => act(() => post(`${G}/${r.id}/reject`, { confirm: true }))} style={ghost}><XCircle size={15} /> Reject</button>}
        {r.status === 'building' && <button disabled={busy} onClick={() => act(() => post(`${G}/${r.id}/refresh`))} style={ghost}><RefreshCw size={15} /> Check for PR</button>}
        {r.status === 'pr_open' && (
          <button disabled={busy} onClick={() => act(() => post(`${G}/${r.id}/approve-merge`, { confirm: true }))} style={btn('#1d4ed8')}>
            <CheckCircle size={15} /> I reviewed it: approve merge
          </button>)}
        {r.spec_path && <button onClick={spec ? () => setSpec(null) : showSpec} style={ghost}><FileText size={15} /> {spec ? 'Hide spec' : 'View spec'}</button>}
      </div>
      {['awaiting_build', 'building'].includes(r.status) && (
        <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap' }}>
          <input style={{ ...input, flex: '1 1 160px', width: 'auto' }} placeholder="PR link" value={pr} onChange={e => setPr(e.target.value)} />
          <input style={{ ...input, flex: '1 1 160px', width: 'auto' }} placeholder="Preview link" value={preview} onChange={e => setPreview(e.target.value)} />
          <button disabled={busy || (!pr && !preview)} onClick={() => act(() => post(`${G}/${r.id}/links`, { pr_url: pr, preview_url: preview }))} style={ghost}>Save</button>
        </div>)}
      {spec && (
        <div style={{ position: 'relative' }}>
          <button onClick={() => navigator.clipboard?.writeText(spec)} style={{ ...ghost, position: 'absolute', right: 6, top: 6, padding: 6, minHeight: 30 }}><Copy size={14} /></button>
          <pre style={{ fontSize: 12, whiteSpace: 'pre-wrap', background: '#f5f3ef', padding: 12, borderRadius: 8, maxHeight: 360, overflow: 'auto', margin: 0 }}>{spec}</pre>
          <div style={{ ...muted, marginTop: 4 }}>File: {r.spec_path}</div>
        </div>)}
    </div>
  );
}

export default function ImprovementsPage() {
  const [data, setData] = useState<any>({ items: [] });
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ title: '', problem: '', proposed_change: '', affected_modules: '', risk: 'medium' });
  const mobile = useIsMobile();
  const load = useCallback(() => { fetch(G).then(r => r.json()).then(setData).catch(() => {}); }, []);
  useEffect(() => { load(); }, [load]);
  const create = async () => {
    await post(G, { ...f, affected_modules: f.affected_modules.split(',').map(s => s.trim()).filter(Boolean), requested_via: 'studio' });
    setF({ title: '', problem: '', proposed_change: '', affected_modules: '', risk: 'medium' }); setOpen(false); load();
  };
  return (
    <div className="cy-module-main" style={{ padding: mobile ? '16px 14px' : '20px 24px', height: '100%', overflowY: 'auto', boxSizing: 'border-box' }}>
      <Header title="Improvements" subtitle="Ask Max (chat or voice) for a system improvement. He writes the change request here. You tap Approve to start the build; it opens a PR on its own branch. Merge and deploy need a second approval after you see the PR or preview. Max never edits his own code or deploys."
        right={<button onClick={() => setOpen(!open)} style={btn('#1d4ed8')}><Plus size={15} /> New request</button>} />
      <div style={{ ...card, marginBottom: 14, display: 'flex', gap: 8, alignItems: 'center', fontSize: 13 }}>
        <Lightbulb size={16} />
        {data.cursor_configured ? <span>Approve build starts a Cursor cloud agent on <b>{data.repo}</b> ({data.models?.default}; small fixes {data.models?.small_fix}). It opens a PR on its own branch. Nothing merges until you tap Approve merge.</span>
          : <span>No Cursor API key on the Dell yet. Approving writes a ready-to-run spec file and marks it <b>awaiting build</b>.</span>}
      </div>
      {open && (
        <div style={{ ...card, display: 'grid', gap: 8, marginBottom: 14 }}>
          <input style={input} placeholder="Title" value={f.title} onChange={e => setF({ ...f, title: e.target.value })} />
          <textarea style={{ ...input, minHeight: 70 }} placeholder="Problem" value={f.problem} onChange={e => setF({ ...f, problem: e.target.value })} />
          <textarea style={{ ...input, minHeight: 70 }} placeholder="Proposed change" value={f.proposed_change} onChange={e => setF({ ...f, proposed_change: e.target.value })} />
          <div style={{ display: 'grid', gap: 8, gridTemplateColumns: '2fr 1fr' }}>
            <input style={input} placeholder="Modules (comma separated)" value={f.affected_modules} onChange={e => setF({ ...f, affected_modules: e.target.value })} />
            <select style={input} value={f.risk} onChange={e => setF({ ...f, risk: e.target.value })}>{['low', 'medium', 'high'].map(r => <option key={r}>{r}</option>)}</select>
          </div>
          <button disabled={!f.title || !f.problem || !f.proposed_change} onClick={create} style={btn('#16a34a')}>Save request</button>
        </div>)}
      <div style={{ display: 'grid', gap: 12, gridTemplateColumns: mobile ? 'minmax(0, 1fr)' : 'repeat(auto-fill, minmax(min(460px, 100%), 1fr))' }}>
        {data.items.map((r: any) => <Req key={`${r.id}-${r.status}`} r={r} onChange={load} />)}
        {!data.items.length && <div style={{ ...card, color: '#888' }}>No requests yet. Ask Max: “Max, I want …”.</div>}
      </div>
    </div>
  );
}
