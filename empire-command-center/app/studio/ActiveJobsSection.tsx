'use client';
import { useEffect, useMemo, useState } from 'react';
import { API } from '../lib/api';
import { jobHubHref } from '../components/jobhub/href';
import { EXAMPLE_JOBS, EXAMPLE_MARK, useExampleMode } from './exampleData';
import { activeJobCards, type HomeJobCard, type JobLike } from './jobStages';

function hrefFor(id: string) {
  return jobHubHref({ job: id });
}

export default function ActiveJobsSection({ onOpen }: { onOpen: (href: string) => void }) {
  const example = useExampleMode();
  const [jobs, setJobs] = useState<JobLike[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (example) {
      setJobs(null);
      setErr(null);
      return;
    }
    let dead = false;
    (async () => {
      try {
        const r = await fetch(`${API}/jobs/active`, { cache: 'no-store' });
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        const data = await r.json();
        if (!dead) setJobs(Array.isArray(data?.jobs) ? data.jobs : []);
      } catch {
        if (!dead) {
          setJobs([]);
          setErr('Jobs are unavailable right now.');
        }
      }
    })();
    return () => { dead = true; };
  }, [example]);

  const cards: HomeJobCard[] = useMemo(() => {
    if (example) return activeJobCards(EXAMPLE_JOBS, hrefFor);
    if (jobs == null) return [];
    return activeJobCards(jobs, hrefFor);
  }, [example, jobs]);

  const loading = !example && jobs == null && !err;

  return (
    <section className="studio-jobs" data-testid="studio-jobs" aria-label="Jobs">
      <header className="studio-jobs-head">
        <h2>Jobs</h2>
        <span className="kick">
          {example ? `${EXAMPLE_MARK} · ` : ''}
          {loading ? 'Loading…' : `${cards.length} active`}
          {' · Workroom, WoodCraft, and the rest'}
        </span>
      </header>
      {loading && <p className="studio-empty">Loading jobs…</p>}
      {!loading && err && cards.length === 0 && <p className="studio-empty">{err}</p>}
      {!loading && !err && cards.length === 0 && (
        <p className="studio-empty">No active jobs. New work from any business shows up here.</p>
      )}
      {cards.length > 0 && (
        <div className="studio-job-grid">
          {cards.map((c) => (
            <button
              key={c.id}
              type="button"
              className="studio-job-card"
              data-testid={`studio-job-card-${c.id}`}
              onClick={() => onOpen(c.href)}
            >
              <div className="studio-job-card-top">
                <b>{c.name}</b>
                <span className="biz">{c.business}</span>
              </div>
              <span className="client">{c.client}</span>
              <span className="phase" style={{ color: c.phaseColor, background: `${c.phaseColor}22` }}>{c.phase}</span>
              <div className="meta">
                {c.nextDateLabel ? <span>Next {c.nextDateLabel}</span> : <span>No date yet</span>}
                {c.totalLabel ? <strong>{c.totalLabel}</strong> : null}
              </div>
              <span className="open">Open job ›</span>
            </button>
          ))}
        </div>
      )}
    </section>
  );
}
