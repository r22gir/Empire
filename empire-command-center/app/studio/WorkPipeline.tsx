'use client';
import { useEffect, useMemo, useState } from 'react';
import { API } from '../lib/api';
import { EXAMPLE_PIPELINE, EXAMPLE_WORK_ROWS, useExampleMode } from './exampleData';
import {
  PIPELINE_STAGES,
  STAGE_KICK,
  STAGE_LABEL,
  groupPipeline,
  type PipelineCard,
  type PipelineRecord,
  type PipelineStage,
} from './pipeline';

async function getJson(url: string): Promise<any | null> {
  try {
    const res = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(12000) });
    if (!res.ok) return null;
    return await res.json();
  } catch {
    return null;
  }
}

function ageDays(s: any): number {
  if (!s || typeof s !== 'string') return 0;
  const t = Date.parse(s.includes('T') ? s : s.replace(' ', 'T'));
  return Number.isFinite(t) ? Math.max(0, (Date.now() - t) / 86_400_000) : 0;
}

function recordsFromApi(quotes: any, jobs: any, leads: any): PipelineRecord[] {
  const out: PipelineRecord[] = [];
  const qlist: any[] = quotes?.quotes || [];
  qlist.forEach((q) => {
    out.push({
      id: String(q.id || q.quote_number || `q-${out.length}`),
      kind: 'quote',
      title: [q.quote_number || 'EST-####', q.customer_name || q.client_name || 'Client'].filter(Boolean).join(' · '),
      subtitle: [q.room || q.title, q.status].filter(Boolean).join(' · '),
      status: q.status,
      pipeline_stage: q.pipeline_stage,
      business: q.business_unit || 'workroom',
      amount: Number(q.total) || null,
      silentDays: ageDays(q.sent_at || q.updated_at),
      approved: ['approved', 'accepted'].includes(String(q.status || '').toLowerCase()),
    });
  });
  const jlist: any[] = jobs?.jobs || [];
  jlist.forEach((j) => {
    const st = String(j.pipeline_stage || j.status || '').toLowerCase();
    out.push({
      id: String(j.id || j.job_number || `j-${out.length}`),
      kind: 'job',
      title: [j.job_number || 'JOB-####', j.client_name || j.title || 'Client'].filter(Boolean).join(' · '),
      subtitle: [j.room || j.title, j.business_unit].filter(Boolean).join(' · '),
      status: j.status,
      pipeline_stage: j.pipeline_stage,
      business: j.business_unit || 'workroom',
      cutReady: /cut|yardage|work.?order/.test(st),
      scheduled: /install|schedul/.test(st) || !!j.install_date,
      paid: /paid|complete/.test(st),
    });
  });
  const plist: any[] = leads?.pipeline || leads?.leads || [];
  plist.forEach((l: any, i: number) => {
    if (l.count != null && l.status) return;
    out.push({
      id: String(l.id || `l-${i}`),
      kind: 'lead',
      title: l.name || l.company || l.business_name || 'Lead',
      subtitle: l.source || l.status || '',
      status: l.status || 'new',
      business: l.business_unit || 'workroom',
    });
  });
  return out;
}

function CardView({ card, onOpen }: { card: PipelineCard; onOpen: (href: string) => void }) {
  return (
    <article className="studio-pcard" data-testid="studio-pipe-card">
      <div className="nm">{card.title}</div>
      <div className="sub">{card.subtitle} · {card.badge}</div>
      <button type="button" className="pri" onClick={() => onOpen(card.href)}>{card.primaryLabel}</button>
      <button type="button" className="sec" onClick={() => onOpen(`/?product=${card.business === 'woodcraft' ? 'craft' : card.business === 'construction' ? 'construction' : 'workroom'}`)}>Open</button>
    </article>
  );
}

export default function WorkPipeline({
  onOpen,
  initialStage,
}: {
  onOpen: (href: string) => void;
  initialStage?: PipelineStage;
}) {
  const example = useExampleMode();
  const [stage, setStage] = useState<PipelineStage>(initialStage || 'quote');
  const [live, setLive] = useState<PipelineRecord[] | null>(null);

  useEffect(() => {
    if (example) return;
    let cancelled = false;
    Promise.all([
      getJson(`${API}/quotes-v2?limit=200`),
      getJson(`${API}/jobs?limit=200`),
      getJson(`${API}/leads/pipeline`),
    ]).then(([quotes, jobs, leads]) => {
      if (!cancelled) setLive(recordsFromApi(quotes, jobs, leads));
    });
    return () => { cancelled = true; };
  }, [example]);

  const grouped = useMemo(
    () => groupPipeline(example || !live ? EXAMPLE_PIPELINE : live),
    [example, live],
  );

  return (
    <section className="studio-work" data-testid="studio-work-pipeline" aria-label="Work pipeline">
      <header style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginBottom: 8 }}>
        <h1 className="v3-disp" style={{ fontSize: 28, margin: 0 }}>Flow</h1>
        <span className="studio-ex">Lead → Quote → Job → Cut → Install → Paid</span>
      </header>

      <div className="studio-stages" role="tablist">
        {PIPELINE_STAGES.map((s) => (
          <button
            key={s}
            type="button"
            className={`studio-stage${stage === s ? ' on' : ''}`}
            onClick={() => setStage(s)}
            data-testid={`studio-stage-${s}`}
          >
            {STAGE_LABEL[s]} {grouped[s].length}
          </button>
        ))}
      </div>

      <div className="studio-plist">
        <p className="studio-ex" style={{ marginBottom: 8 }}>{STAGE_KICK[stage]} · oldest first</p>
        {grouped[stage].length === 0 && <p className="studio-ex">No cards in this stage.</p>}
        {grouped[stage].map((c) => <CardView key={c.id} card={c} onOpen={onOpen} />)}
      </div>

      <div className="studio-kanban" data-testid="studio-kanban">
        {PIPELINE_STAGES.map((s) => (
          <div key={s} className="studio-col">
            <h4>{STAGE_LABEL[s]} <span>{grouped[s].length}</span></h4>
            {grouped[s].map((c) => <CardView key={c.id} card={c} onOpen={onOpen} />)}
          </div>
        ))}
      </div>

      {example && (
        <div className="studio-cards" style={{ marginTop: 18 }}>
          {EXAMPLE_WORK_ROWS.map((space) => (
            <article key={space.space} className="studio-card">
              <h3>{space.space} <span className="kick">EXAMPLE</span></h3>
              {space.items.map((it) => (
                <button key={it.title} type="button" className="studio-row" onClick={() => onOpen('/?tab=work')}>
                  <span style={{ flex: 1 }}><b>{it.title}</b><span style={{ display: 'block' }}>{it.detail}</span></span>
                  <span className="studio-ex">{it.badge}</span>
                </button>
              ))}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
