'use client';
import React, { useCallback, useEffect, useState } from 'react';
import {
  Lightbulb, CheckCircle, XCircle, RefreshCw, GitPullRequest, FileText, Copy, Plus, Rocket,
  RotateCcw, ExternalLink, AlertTriangle,
} from 'lucide-react';
import { API } from '../../lib/api';
import { IMPROVEMENT_PIPELINE, isRetryable, pipelineIndex, usageBarPct } from '../../lib/improvementPipeline';
import { Badge, Header, btn, card, ghost, input, muted, useIsMobile } from './shared';

const G = `${API}/growth/improvements`;
const STATUS: Record<string, { label: string; bg: string; color: string }> = {
  proposed: { label: 'Proposed', bg: '#fef3c7', color: '#b45309' },
  approved: { label: 'Approved', bg: '#e0e7ff', color: '#3730a3' },
  planning: { label: 'Planning', bg: '#ede9fe', color: '#6d28d9' },
  awaiting_build: { label: 'Awaiting build', bg: '#e0f2fe', color: '#0369a1' },
  building: { label: 'Building', bg: '#ede9fe', color: '#6d28d9' },
  pr_open: { label: 'PR open', bg: '#dbeafe', color: '#1d4ed8' },
  merge_approved: { label: 'Merge approved', bg: '#dcfce7', color: '#15803d' },
  deployed: { label: 'Deployed', bg: '#dcfce7', color: '#15803d' },
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

function Pipeline({ status }: { status: string }) {
  const idx = pipelineIndex(status);
  const failed = status === 'build_failed';
  return (
    <div style={{ display: 'flex', gap: 0, alignItems: 'center', flexWrap: 'wrap', marginTop: 4 }} aria-label="Status pipeline">
      {IMPROVEMENT_PIPELINE.map((step, i) => {
        const done = idx >= 0 && i <= idx;
        const current = idx === i || (failed && i === 2);
        return (
          <React.Fragment key={step.id}>
            {i > 0 && <span style={{ width: 18, height: 2, background: done ? '#c9a227' : '#e5e2dc', display: 'inline-block' }} />}
            <span style={{
              fontSize: 10, fontWeight: 700, letterSpacing: 0.3, textTransform: 'uppercase',
              padding: '4px 8px', borderRadius: 999,
              background: failed && i === 2 ? '#fee2e2' : current ? '#1a1a1a' : done ? '#f8efc8' : '#f5f3ef',
              color: failed && i === 2 ? '#b91c1c' : current ? '#f8efc8' : done ? '#7a5b12' : '#888',
            }}>{step.label}</span>
          </React.Fragment>
        );
      })}
    </div>
  );
}

function UsageMeter({ mm }: { mm: any }) {
  if (!mm) return null;
  const pct = usageBarPct(Number(mm.calls || 0), Number(mm.call_cap || 40));
  const stopped = !!mm.stopped;
  return (
    <div style={{ ...card, marginBottom: 14, display: 'grid', gap: 8 }} data-testid="minimax-usage">
      <div style={{ display: 'flex', justifyContent: 'space-between', gap: 8, flexWrap: 'wrap', alignItems: 'center' }}>
        <div style={{ fontWeight: 700, fontSize: 14 }}>MiniMax planner (included plan)</div>
        <Badge
          text={stopped ? 'Capped — no auto-credits' : `${mm.calls ?? 0} / ${mm.call_cap ?? 40} calls today`}
          bg={stopped ? '#fee2e2' : '#f8efc8'}
          color={stopped ? '#b91c1c' : '#7a5b12'}
        />
      </div>
      <div style={{ height: 8, borderRadius: 999, background: '#f5f3ef', overflow: 'hidden' }}>
        <div style={{
          width: `${pct}%`, height: '100%',
          background: stopped ? '#dc2626' : 'linear-gradient(90deg, #c9a227, #1a1a1a)',
        }} />
      </div>
      <div style={{ ...muted, display: 'flex', gap: 12, flexWrap: 'wrap' }}>
        <span>Model {mm.model || 'MiniMax-M2'}</span>
        <span>Tokens {mm.tokens ?? 0} / {mm.token_cap ?? 200000}</span>
        <span>Family editions: 20% text share each — this loop does not run on Max-e / Maxine</span>
        <span>UTC {mm.day}</span>
      </div>
    </div>
  );
}

function Req({ r, onChange }: { r: any; onChange: () => void }) {
  const [spec, setSpec] = useState<string | null>(null);
  const [pr, setPr] = useState(''); const [preview, setPreview] = useState('');
  const [err, setErr] = useState(''); const [busy, setBusy] = useState(false);
  const s = STATUS[r.status] || STATUS.proposed;
  const act = async (fn: () => Promise<any>) => { setBusy(true); setErr(''); try { await fn(); onChange(); } catch (e: any) { setErr(e.message); } finally { setBusy(false); } };
  const showSpec = async () => { const j = await (await fetch(`${G}/${r.id}`)).json(); setSpec(j.spec); };

  return (
    <div style={{ ...card, display: 'flex', flexDirection: 'column', gap: 10, minWidth: 0, borderColor: r.status === 'build_failed' ? '#fecaca' : '#e5e2dc' }} data-imp-id={r.id}>
      <div style={{ display: 'flex', gap: 8, alignItems: 'center', flexWrap: 'wrap' }}>
        <span style={{ ...muted, fontWeight: 700 }}>IMP-{String(r.id).padStart(4, '0')}</span>
        {r.kind && r.kind !== 'growth' && <Badge text={r.kind} bg="#ede9fe" color="#6d28d9" />}
        <span style={{ fontWeight: 700, fontSize: 16, flex: 1, minWidth: 0, overflowWrap: 'anywhere' }}>{r.title}</span>
        <Badge text={s.label} bg={s.bg} color={s.color} />
      </div>
      <Pipeline status={r.status} />
      <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', alignItems: 'center' }}>
        <Badge text={`Risk: ${r.risk}`} bg="#fff" color={RISK[r.risk] || '#555'} />
        {(r.affected_modules || []).map((m: string) => <Badge key={m} text={m} wrap />)}
        <span style={muted}>via {r.requested_via} · {(r.created_at || '').slice(0, 16)}</span>
      </div>
      <div><div style={{ ...muted, fontWeight: 700 }}>Problem</div><div style={{ fontSize: 14, whiteSpace: 'pre-wrap' }}>{r.problem}</div></div>
      <div><div style={{ ...muted, fontWeight: 700 }}>Proposed change</div><div style={{ fontSize: 14, whiteSpace: 'pre-wrap' }}>{r.proposed_change}</div></div>
      {r.build_note && <div style={{ ...muted }}>{r.build_note}{r.branch ? ` · branch: ${r.branch}` : ''}</div>}
      {(r.pr_url || r.preview_url || r.agent_url || r.issue_url) && (
        <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
          {r.issue_url && <a href={r.issue_url} target="_blank" rel="noreferrer" style={ghost}><ExternalLink size={15} /> GitHub issue</a>}
          {r.pr_url && <a href={r.pr_url} target="_blank" rel="noreferrer" style={ghost}><GitPullRequest size={15} /> Open PR</a>}
          {r.preview_url && <a href={r.preview_url} target="_blank" rel="noreferrer" style={ghost}>Open preview</a>}
          {r.agent_url && <a href={r.agent_url} target="_blank" rel="noreferrer" style={ghost}>Cloud agent</a>}
        </div>
      )}
      <div style={{ ...muted, fontStyle: 'italic' }}>{r.next_step}</div>
      {err && <div style={{ color: '#dc2626', fontSize: 13 }}>{err}</div>}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {r.status === 'proposed' && (
          <button disabled={busy} onClick={() => act(() => post(`${G}/${r.id}/approve`, { confirm: true }))} style={btn('#16a34a')}>
            <Rocket size={15} /> Approve
          </button>)}
        {isRetryable(r.status) && (
          <button disabled={busy} onClick={() => act(() => post(`${G}/${r.id}/retry`, { confirm: true }))} style={btn(r.status === 'build_failed' ? '#b91c1c' : '#1d4ed8')}>
            <RotateCcw size={15} /> Retry
          </button>)}
        {r.status === 'proposed' && <button disabled={busy} onClick={() => act(() => post(`${G}/${r.id}/reject`, { confirm: true }))} style={ghost}><XCircle size={15} /> Reject</button>}
        {(r.status === 'planning' || r.status === 'building') && <button disabled={busy} onClick={() => act(() => post(`${G}/${r.id}/refresh`))} style={ghost}><RefreshCw size={15} /> Check for PR</button>}
        {r.status === 'pr_open' && (
          <button disabled={busy} onClick={() => act(() => post(`${G}/${r.id}/approve-merge`, { confirm: true }))} style={btn('#1d4ed8')}>
            <CheckCircle size={15} /> I reviewed it: approve merge
          </button>)}
        {r.status === 'merge_approved' && (
          <button disabled={busy} onClick={() => act(() => post(`${G}/${r.id}/mark-deployed`, { confirm: true }))} style={btn('#15803d')}>
            <CheckCircle size={15} /> Record deploy (after Chief e)
          </button>)}
        {r.spec_path && <button onClick={spec ? () => setSpec(null) : showSpec} style={ghost}><FileText size={15} /> {spec ? 'Hide spec' : 'View spec'}</button>}
      </div>
      {['approved', 'planning', 'awaiting_build', 'building'].includes(r.status) && (
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
  const [data, setData] = useState<any>({ items: [], minimax: null });
  const [open, setOpen] = useState(false);
  const [f, setF] = useState({ title: '', problem: '', proposed_change: '', affected_modules: '', risk: 'medium' });
  const mobile = useIsMobile();
  const load = useCallback(() => { fetch(G).then(r => r.json()).then(setData).catch(() => {}); }, []);
  useEffect(() => { load(); }, [load]);
  useEffect(() => {
    const id = new URLSearchParams(window.location.search).get('id');
    if (!id || !data.items?.length) return;
    const el = document.querySelector(`[data-imp-id="${id}"]`);
    if (el) {
      el.scrollIntoView({ behavior: 'smooth', block: 'center' });
      (el as HTMLElement).style.outline = '2px solid #c9a227';
    }
  }, [data.items]);
  const create = async () => {
    await post(G, { ...f, affected_modules: f.affected_modules.split(',').map(s => s.trim()).filter(Boolean), requested_via: 'studio' });
    setF({ title: '', problem: '', proposed_change: '', affected_modules: '', risk: 'medium' }); setOpen(false); load();
  };
  const queued = data.queue?.queued_or_running || 0;
  return (
    <div className="cy-module-main" style={{ padding: mobile ? '16px 14px' : '20px 24px', height: '100%', overflowY: 'auto', boxSizing: 'border-box' }}>
      <Header title="Improvements" subtitle="Ask Max for a system change. Approve enqueues Atlas (CodeForge). MiniMax-M2 writes a plan, then a GitHub issue labeled max-improvement is opened for a grok-4.6 draft PR. Merge and deploy need you — after Chief e review. Max never deploys."
        right={<button onClick={() => setOpen(!open)} style={btn('#1a1a1a')}><Plus size={15} /> New request</button>} />
      <UsageMeter mm={data.minimax} />
      <div style={{ ...card, marginBottom: 14, display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 13 }}>
        <Lightbulb size={16} style={{ marginTop: 2, flexShrink: 0 }} />
        <span>
          Pipeline: <b>proposed → approved → planning → PR open → deployed</b>.
          {queued ? ` ${queued} job(s) in the Atlas queue.` : ''}
          {' '}Nothing merges or deploys from this screen. Gift credits are never spent.
          {data.github_configured ? ' GitHub issue filing is on.' : ' Add MAX_IMPROVE_GITHUB_TOKEN to file issues.'}
          {data.cursor_configured ? ' Cursor draft-PR agent is on.' : ' No Cursor key — issue/spec only.'}
        </span>
      </div>
      {data.minimax?.stopped && (
        <div style={{ ...card, marginBottom: 14, display: 'flex', gap: 8, alignItems: 'center', background: '#fff7ed', borderColor: '#fdba74' }}>
          <AlertTriangle size={16} color="#c2410c" />
          <span style={{ fontSize: 13 }}>MiniMax daily cap reached. Atlas stops. No auto-credits. Retry tomorrow or raise MAX_IMPROVE_MINIMAX_DAILY_CALLS.</span>
        </div>
      )}
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
