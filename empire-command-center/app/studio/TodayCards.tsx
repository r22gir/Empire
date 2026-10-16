'use client';
import { useMemo } from 'react';
import { useHomeData, money as fmtMoney } from '../components/home3/useHomeData';
import { EDITION } from '../v3/edition';
import { EXAMPLE_MARK, EXAMPLE_MONEY, EXAMPLE_NEEDS, EXAMPLE_SCHEDULE, useExampleMode } from './exampleData';

function greeting(now: Date | null): string {
  const h = now ? now.getHours() : 12;
  return h < 5 ? 'Good evening' : h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
}

export default function TodayCards({
  onOpen,
  compact,
}: {
  onOpen: (href: string) => void;
  compact?: boolean;
}) {
  const d = useHomeData();
  const example = useExampleMode();
  const dateLine = d.now
    ? d.now.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' }).toUpperCase()
    : 'THURSDAY · OCTOBER 15';

  const needs = useMemo(() => {
    if (example) return EXAMPLE_NEEDS.map((n) => ({ ...n, href: '/?product=lead&section=approvals' }));
    const rows: { id: string; kind: string; title: string; mark?: string; href: string }[] = [];
    (d.approvals || []).slice(0, 4).forEach((a) => {
      rows.push({ id: `ap-${a.id}`, kind: 'APPROVAL', title: a.title, href: '/?product=lead&section=approvals' });
    });
    if (d.figures.overdueCount) {
      rows.push({
        id: 'od',
        kind: 'OVERDUE',
        title: `${d.figures.overdueCount} invoice${d.figures.overdueCount === 1 ? '' : 's'}`,
        href: '/?tab=money&screen=invoices',
      });
    }
    (d.reminders || []).slice(0, 3).forEach((r) => {
      rows.push({ id: `rm-${r.id}`, kind: 'TASK', title: r.title, href: r.href || '/?screen=tasks' });
    });
    return rows;
  }, [example, d.approvals, d.figures.overdueCount, d.reminders]);

  const schedule = example
    ? EXAMPLE_SCHEDULE.map((s) => ({ ...s, href: '/?screen=calendar' }))
    : (d.schedule || []).map((s) => ({
      id: s.key,
      time: s.time || '',
      title: s.title,
      detail: 'Navigate · Call · Do',
      href: s.href,
      map: s.map_link,
      call: s.call_link,
    }));

  const money = example
    ? EXAMPLE_MONEY
    : {
      toCollect: d.figures.overdueTotal != null ? fmtMoney(d.figures.overdueTotal) : '—',
      depositsDue: '—',
      paidMtd: '—',
      mark: '',
    };

  return (
    <section className="studio-today" data-testid="studio-today" aria-label="Today">
      {!compact && (
        <header style={{ marginBottom: 16 }}>
          <div className="studio-ex">{dateLine}</div>
          <h1 className="v3-disp" style={{ fontSize: 28, margin: '8px 0 0' }}>
            {greeting(d.now)}, <em style={{ color: 'var(--st-gold)', fontStyle: 'italic' }}>{EDITION.ownerName}.</em>
          </h1>
        </header>
      )}

      <div className="studio-cards">
        <article className="studio-card" data-testid="studio-card-needs">
          <h3><i /> Needs you <span className="kick">{needs.length} items</span></h3>
          {needs.length === 0 && <p className="studio-ex" style={{ marginTop: 10 }}>Nothing waiting.</p>}
          {needs.map((n) => (
            <button key={n.id} type="button" className="studio-row" onClick={() => onOpen(n.href)}>
              <span className="kind">{n.kind}</span>
              <span style={{ flex: 1 }}>
                <b>{n.title}</b>
                {n.mark ? <span> {n.mark}</span> : null}
              </span>
              <span>›</span>
            </button>
          ))}
        </article>

        <article className="studio-card" data-testid="studio-card-schedule">
          <h3><i style={{ background: '#d4af37' }} /> On the schedule <span className="kick">Organizer</span></h3>
          {schedule.length === 0 && <p className="studio-ex" style={{ marginTop: 10 }}>Nothing on today.</p>}
          {schedule.map((s) => (
            <div key={s.id}>
              <button type="button" className="studio-row" onClick={() => onOpen(('href' in s && s.href) || '/?screen=calendar')}>
                <span className="kind">{s.time || '—'}</span>
                <span style={{ flex: 1 }}>
                  <b>{s.title}</b>
                  {'mark' in s && s.mark ? <span> {EXAMPLE_MARK}</span> : null}
                  <span style={{ display: 'block' }}>{s.detail}</span>
                </span>
              </button>
            </div>
          ))}
        </article>

        <article className="studio-card" data-testid="studio-card-money">
          <h3><i style={{ background: '#5fc79a' }} /> Money <span className="kick">EmpirePay</span></h3>
          <div className="studio-money">
            <div><label>To collect</label><b>{money.toCollect}</b></div>
            <div><label>Deposits due</label><b>{money.depositsDue}</b></div>
            <div><label>Paid MTD</label><b>{money.paidMtd}</b></div>
          </div>
          <button type="button" className="studio-row" onClick={() => onOpen('/?tab=money')}>
            <span className="kind">OPEN</span>
            <span style={{ flex: 1 }}><b>Invoices, deposits, pay links</b></span>
            <span>›</span>
          </button>
        </article>
      </div>
    </section>
  );
}
