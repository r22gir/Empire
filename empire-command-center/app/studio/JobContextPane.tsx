'use client';
import { useEffect, useState } from 'react';
import { formatInches } from '../lib/formatInches';
import { useJob } from '../hooks/useJob';
import { EXAMPLE_JOB_CONTEXT, EXAMPLE_MARK, useExampleMode } from './exampleData';

const TABS = ['Quote', 'Drawing', 'Cut list', 'Invoice', 'Photos'] as const;
type JobTab = (typeof TABS)[number];

export default function JobContextPane({
  open,
  onToggle,
  onOpen,
}: {
  open: boolean;
  onToggle: () => void;
  onOpen: (href: string) => void;
}) {
  const { activeJob } = useJob();
  const example = useExampleMode();
  const [tab, setTab] = useState<JobTab>('Quote');
  const [quote, setQuote] = useState<any>(null);

  useEffect(() => {
    if (example || !activeJob?.quote_id) return;
    let cancelled = false;
    fetch(`/api/v1/quotes-v2/${activeJob.quote_id}`, { cache: 'no-store' })
      .then((r) => (r.ok ? r.json() : null))
      .then((data) => { if (!cancelled) setQuote(data); })
      .catch(() => {});
    return () => { cancelled = true; };
  }, [activeJob?.quote_id, example]);

  if (!example && !activeJob) return null;

  const title = example
    ? `${EXAMPLE_JOB_CONTEXT.number} · ${EXAMPLE_JOB_CONTEXT.client}`
    : `${activeJob?.job_number || 'JOB'} · ${activeJob?.client_name || 'Client'}`;
  const status = example ? EXAMPLE_JOB_CONTEXT.status : (activeJob?.pipeline_stage || activeJob?.status || '');
  const lines: { area: string; qty: string; sqft: string; total: string }[] = example
    ? EXAMPLE_JOB_CONTEXT.lines
    : (quote?.areas || quote?.items || []).slice(0, 6).map((a: any) => ({
      area: a.area || a.name || a.description || 'Line',
      qty: a.qty != null ? String(a.qty) : '—',
      sqft: a.width_in != null ? formatInches(a.width_in) : '—',
      total: a.total != null ? `$${a.total}` : '$—',
    }));

  return (
    <aside
      className={`studio-job drawer${open ? '' : ' shut'}`}
      data-testid="studio-job-pane"
      aria-label="Job context"
    >
      <button
        type="button"
        onClick={onToggle}
        style={{
          display: 'block', width: '100%', background: 'none', border: 0, color: 'var(--st-mut)',
          font: '500 11px/1 var(--font-ibm-plex-mono, ui-monospace)', letterSpacing: '0.12em',
          textTransform: 'uppercase', padding: '10px 16px', cursor: 'pointer', textAlign: 'left',
        }}
      >
        Job context {example ? `· ${EXAMPLE_MARK}` : ''} · {open ? 'pull down' : 'pull up for full job'}
      </button>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '0 16px 8px' }}>
        <h3 style={{ margin: 0 }}>{title}</h3>
        <span className="studio-ex">{status}</span>
      </div>
      <div className="studio-jtabs">
        {TABS.map((t) => (
          <button key={t} type="button" className={tab === t ? 'on' : ''} onClick={() => setTab(t)}>{t}</button>
        ))}
      </div>
      {tab === 'Quote' || tab === 'Cut list' || tab === 'Invoice' ? (
        <div>
          {lines.length === 0 && <p className="studio-ex" style={{ padding: 16 }}>No lines on this job yet.</p>}
          {lines.map((ln, i) => (
            <div key={`${ln.area}-${i}`} className="studio-jline">
              <span>{ln.area}</span>
              <span>{ln.total}</span>
            </div>
          ))}
        </div>
      ) : (
        <p className="studio-ex" style={{ padding: 16 }}>
          {tab === 'Drawing' ? 'Drawing preview' : 'Photos'} {example ? EXAMPLE_MARK : 'opens the existing module.'}
        </p>
      )}
      <div className="studio-jacts">
        <button type="button" onClick={() => onOpen('/?tab=max&screen=chat&ask=Send%20me%20a%20link')}>Send me a link</button>
        <button type="button" className="ghost" onClick={() => onOpen('/?product=workroom&section=jobhub')}>Open in Studio</button>
      </div>
    </aside>
  );
}
