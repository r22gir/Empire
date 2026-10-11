'use client';
/** Docs tab for a quote or job: latest FINAL of each doc type + older versions + photos. */
import { useEffect, useState } from 'react';
import { Loader2 } from 'lucide-react';
import type { DocGroup, DocType, JobContext } from '../../lib/docs-hub/types';
import { DOCS_API, DOC_TYPES } from '../../lib/docs-hub/types';
import DocCard, { thumbUrl, toRef } from './DocCard';
import { openDocViewer } from './viewerBus';
import './docs.css';

export function useQuoteDocs(quote?: string | null, job?: string | null) {
  const [data, setData] = useState<{ groups: DocGroup[]; context?: JobContext | null } | null>(null);
  const [err, setErr] = useState<string | null>(null);
  useEffect(() => {
    if (!quote && !job) return;
    let dead = false;
    const p = new URLSearchParams({ group: '1' });
    if (quote) p.set('quote', quote); else if (job) p.set('job', job);
    fetch(`${DOCS_API}?${p}`).then(r => r.ok ? r.json() : Promise.reject(r.status)).then(d => { if (!dead) setData({ groups: d.groups || [], context: d.context }); })
      .catch(() => { if (!dead) setErr('Could not load documents.'); });
    return () => { dead = true; };
  }, [quote, job]);
  return { data, err };
}

export default function DocsTab({ quote, job, context }: { quote?: string | null; job?: string | null; context?: JobContext | null }) {
  const { data, err } = useQuoteDocs(quote, job);
  if (err) return <div className="dh dh-empty">{err}</div>;
  if (!data) return <div className="dh dh-empty"><Loader2 size={18} className="animate-spin" style={{ color: '#00e5ff' }} /> Loading documents…</div>;
  const ctx = context || data.context;
  const byType = new Map<DocType, DocGroup[]>();
  for (const g of data.groups) { const a = byType.get(g.type) || []; a.push(g); byType.set(g.type, a); }
  if (!data.groups.length) return <div className="dh dh-empty">No documents found for this job yet. Estimates, presentations, invoices, drawings and photos show up here as soon as they are saved.</div>;
  return (
    <div className="dh" style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
      {DOC_TYPES.map(t => {
        const gs = byType.get(t.id); if (!gs?.length) return null;
        if (t.id === 'photo') {
          const photos = gs.flatMap(g => [g.final, ...g.older]);
          return (
            <section key={t.id} className="dh-section">
              <div className="dh-section-h">{t.plural} <span>{photos.length}</span></div>
              <div className="dh-photos">
                {photos.map(p => <button key={p.id} type="button" style={{ backgroundImage: `url("${thumbUrl(p)}")` }} onClick={() => openDocViewer(toRef(p))} aria-label={`Open ${p.title}`} title={p.filename} />)}
              </div>
            </section>
          );
        }
        return (
          <section key={t.id} className="dh-section">
            <div className="dh-section-h">{t.plural} <span>{gs.length}</span></div>
            {gs.map(g => <DocCard key={g.key} group={g} phone={ctx?.phone} email={ctx?.email} />)}
          </section>
        );
      })}
    </div>
  );
}
