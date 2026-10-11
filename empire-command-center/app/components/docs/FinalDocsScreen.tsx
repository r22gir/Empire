'use client';
/**
 * Global "Final Docs" page: one place to find the final estimate, presentation, invoice,
 * drawings and photos for any client / job. Search by client, job or quote number and doc type.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { Search, RefreshCw, Loader2, FileStack } from 'lucide-react';
import type { DocGroup, DocType } from '../../lib/docs-hub/types';
import { DOCS_API, DOC_TYPES } from '../../lib/docs-hub/types';
import DocCard from './DocCard';
import './docs.css';

interface Resp { builtAt: string; tookMs: number; total: number; roots: { dir: string; files: number }[]; facets: { types: Record<string, number>; clients: string[] }; groups: DocGroup[]; dbError?: string }

export default function FinalDocsScreen() {
  const [q, setQ] = useState('');
  const [qd, setQd] = useState('');
  const [type, setType] = useState<DocType | ''>('');
  const [client, setClient] = useState('');
  const [finalOnly, setFinalOnly] = useState(true);
  const [data, setData] = useState<Resp | null>(null);
  const [loading, setLoading] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [refresh, setRefresh] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { // deep link: /?screen=final-docs&q=nehal
    const sp = new URLSearchParams(window.location.search);
    const iq = sp.get('q'); if (iq) { setQ(iq); setQd(iq); }
    const it = sp.get('type') as DocType | null; if (it && DOC_TYPES.some(t => t.id === it)) setType(it);
  }, []);
  useEffect(() => { const t = setTimeout(() => setQd(q.trim()), 250); return () => clearTimeout(t); }, [q]);

  useEffect(() => {
    let dead = false;
    setLoading(true); setErr(null);
    const p = new URLSearchParams({ group: '1' });
    if (qd) p.set('q', qd); if (type) p.set('type', type); if (client) p.set('client', client);
    if (refresh) p.set('refresh', '1');
    // Retry with backoff (1s, 2s, 4s, 8s, 15s): a portal restart or a slow first scan used to leave
    // "Could not load the document index" on screen until a manual reload.
    const DELAYS = [1000, 2000, 4000, 8000, 15000];
    let timer: ReturnType<typeof setTimeout> | undefined;
    const attempt = (n: number) => {
      fetch(`${DOCS_API}?${p}`).then(r => r.ok ? r.json() : Promise.reject(r.status))
        .then((d: Resp) => { if (!dead) { setData(d); setErr(null); setLoading(false); } })
        .catch(() => {
          if (dead) return;
          if (n < DELAYS.length) { setErr(`Reconnecting to the document index… (try ${n + 2} of ${DELAYS.length + 1})`); timer = setTimeout(() => attempt(n + 1), DELAYS[n]); }
          else { setErr('Could not load the document index. Tap Rescan to try again.'); setLoading(false); }
        });
    };
    attempt(0);
    return () => { dead = true; if (timer) clearTimeout(timer); };
  }, [qd, type, client, refresh]);

  const clients = useMemo(() => {
    if (!data) return [] as { name: string; groups: DocGroup[]; latest: string }[];
    const m = new Map<string, DocGroup[]>();
    for (const g of data.groups) {
      const name = g.final.client || g.final.designer || 'Unassigned';
      const a = m.get(name) || []; a.push(g); m.set(name, a);
    }
    return [...m.entries()].map(([name, groups]) => {
      groups.sort((a, b) => DOC_TYPES.findIndex(t => t.id === a.type) - DOC_TYPES.findIndex(t => t.id === b.type) || (b.final.modified || '').localeCompare(a.final.modified || ''));
      const shown = finalOnly ? groups : groups.flatMap(g => [g, ...g.older.map(o => ({ key: o.id, type: o.type, title: o.title, final: o, older: [] } as DocGroup))]);
      return { name, groups: shown, latest: groups.reduce((x, g) => (g.final.modified > x ? g.final.modified : x), '') };
    }).sort((a, b) => (a.name === 'Unassigned' ? 1 : b.name === 'Unassigned' ? -1 : b.latest.localeCompare(a.latest)));
  }, [data, finalOnly]);

  const typeCounts = data?.facets.types || {};
  const shownCount = clients.reduce((t, c) => t + c.groups.length, 0);

  return (
    <div className="dh dh-page" data-screen="final-docs">
      <div className="dh-page-h">
        <div>
          <h1><FileStack size={20} style={{ color: '#00e5ff', verticalAlign: '-3px', marginRight: 8 }} />Final Docs</h1>
          <p>The latest final estimate, presentation, invoice, drawings and photos for every job. Older versions are kept under each card.</p>
        </div>
        <button type="button" className="dh-act" onClick={() => setRefresh(r => r + 1)} disabled={loading}>
          {loading ? <Loader2 size={15} className="animate-spin" /> : <RefreshCw size={15} />} Rescan
        </button>
      </div>

      <div className="dh-filters">
        <label className="dh-search">
          <Search size={15} />
          <input ref={inputRef} className="dh-input" type="search" value={q} onChange={e => setQ(e.target.value)} placeholder="Search by client, job or quote # (e.g. Nehal, EST-2026-297, invoice)" aria-label="Search documents" />
        </label>
        <select className="dh-input" value={client} onChange={e => setClient(e.target.value)} aria-label="Client" style={{ maxWidth: 220 }}>
          <option value="">All clients</option>
          {(data?.facets.clients || []).map(c => <option key={c} value={c}>{c}</option>)}
        </select>
        <label className="dh-chip" style={{ cursor: 'pointer' }}>
          <input type="checkbox" checked={finalOnly} onChange={e => setFinalOnly(e.target.checked)} style={{ accentColor: '#00e5ff' }} /> Finals only
        </label>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, width: '100%' }} role="group" aria-label="Document type">
          <button type="button" className={`dh-chip${!type ? ' is-on' : ''}`} onClick={() => setType('')}>All</button>
          {DOC_TYPES.map(t => (
            <button key={t.id} type="button" className={`dh-chip${type === t.id ? ' is-on' : ''}`} onClick={() => setType(type === t.id ? '' : t.id)} aria-pressed={type === t.id}>
              {t.plural}{!type && typeCounts[t.id] ? <span>{typeCounts[t.id]}</span> : null}
            </button>
          ))}
        </div>
      </div>

      {err && <div className="dh-empty">{err}</div>}
      {!err && data && (
        <div className="dh-muted" style={{ fontSize: 12.5 }}>
          <span className="dh-num">{shownCount}</span> {finalOnly ? 'final documents' : 'documents incl. older versions'} across <span className="dh-num">{clients.length}</span> clients{qd ? <> for “{qd}”</> : null}
        </div>
      )}
      {!err && !data && <div className="dh-empty"><Loader2 size={18} className="animate-spin" style={{ color: '#00e5ff' }} /> Indexing documents…</div>}
      {data && !clients.length && <div className="dh-empty">No documents match. Try a client name, a quote number like EST-2026-297, or clear the filters.</div>}

      {clients.slice(0, 60).map(c => (
        <section key={c.name} className="dh-clientgroup">
          <header>
            <h2>{c.name}</h2>
            <small><span className="dh-num">{c.groups.length}</span> docs{c.groups[0]?.final.designer && c.groups[0].final.designer !== c.name ? ` · via ${c.groups[0].final.designer}` : ''}</small>
          </header>
          <div className="dh-grid">
            {c.groups.map(g => <DocCard key={g.key} group={finalOnly ? g : { ...g, older: [] }} />)}
          </div>
        </section>
      ))}
      {clients.length > 60 && <div className="dh-muted" style={{ fontSize: 12.5 }}>Showing the 60 most recent clients. Search to narrow down.</div>}

      {data && (
        <div className="dh-indexnote">
          Indexed in place (nothing moved): {data.roots.map(r => `${r.dir} (${r.files})`).join(' · ')}. Built {new Date(data.builtAt).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })} in <span className="dh-num">{data.tookMs}</span> ms.
          {data.dbError ? ` Database note: ${data.dbError}` : ''}
        </div>
      )}
    </div>
  );
}
