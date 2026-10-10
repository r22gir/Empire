'use client';
/**
 * Max home (v3 personal center) — "/" with no query.
 * Hero (abstract orb, greeting, brief from real figures, ask bar), business Pulse (real DB figures),
 * Research interests (user-defined, stored per user; no feed exists, so no headlines are shown),
 * Growth (goals / learning / projects stored per user, Max suggestions and Improvements from real data),
 * Today (schedule from job dates, pending approvals, reminders from tasks). Businesses live in the rail.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import {
  ArrowRight, Send, Mic, Pencil, Plus, X, Check, Cpu, TrendingUp, Wrench, Home as HomeIcon, Heart, Layers, BookOpen, Target, Sparkles,
  CalendarDays, Bell, Minus, Search, Globe,
} from 'lucide-react';
import { NAV_GROUPS } from '../layout/LeftNav';
import type { NavItem } from '../layout/LeftNav';
import { Orb, Wave, RingProgress, Backdrop, Empty } from '../../v3/ui';
import { V3Band, V3Rail, BusinessesSheet, V3TabBar } from '../../v3/Shell';
import type { SheetGroup } from '../../v3/Shell';
import { EDITION } from '../../v3/edition';
import { useHomeData, dayLabel } from './useHomeData';
import type { PulseItem } from './useHomeData';
import { useHomeStore, newId } from './useHomeStore';
import type { HomeItem, HomeKind } from './useHomeStore';
import './home3.css';

const ICONS: Record<string, ReactNode> = {
  cpu: <Cpu size={15} strokeWidth={1.5} />, trend: <TrendingUp size={15} strokeWidth={1.5} />, tool: <Wrench size={15} strokeWidth={1.5} />,
  home: <HomeIcon size={15} strokeWidth={1.5} />, heart: <Heart size={15} strokeWidth={1.5} />, layers: <Layers size={15} strokeWidth={1.5} />,
  book: <BookOpen size={15} strokeWidth={1.5} />, globe: <Globe size={15} strokeWidth={1.5} />, search: <Search size={15} strokeWidth={1.5} />,
};
const icon = (k?: string) => ICONS[k || ''] || ICONS.search;

// a question (or anything long) is sent to Max as typed instead of being saved as an interest
const looksLikeQuestion = (t: string) => { const s = t.trim(); return /[?¿]/.test(s) || s.split(/\s+/).length > 6 || s.length > 60; };
const askHref = (q: string) => `/?product=owner&ask=${encodeURIComponent(q.slice(0, 2000))}`;

function navHref(item: NavItem): string {
  if (item.kind === 'daily-summary') return '/?product=owner&screen=dashboard';
  if (item.kind === 'screen' && item.screen) return `/?screen=${encodeURIComponent(item.screen)}`;
  return `/?product=${encodeURIComponent(item.id)}`;
}
export function sheetGroups(onPick?: (item: NavItem) => void, activeId?: string | null): SheetGroup[] {
  return NAV_GROUPS.map(g => ({
    key: g.key, label: g.label,
    items: g.items.map(it => ({ id: it.id, name: it.name, icon: it.icon, status: it.status, href: navHref(it), on: activeId === it.id, onPick: onPick ? () => onPick(it) : undefined })),
  }));
}

function greeting(now: Date | null): string {
  const h = now ? now.getHours() : 12;
  return h < 5 ? 'Good evening' : h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
}
const pct = (it: HomeItem) => (it.total ? Math.min(1, (it.done || 0) / it.total) : Math.min(1, (it.progress || 0) / 100));

/* ---------------------------------------------------------------- hero */

function Hero({ d, interests }: { d: ReturnType<typeof useHomeData>; interests: HomeItem[] }) {
  const [q, setQ] = useState('');
  const [narrow, setNarrow] = useState(false);
  useEffect(() => { const mq = window.matchMedia('(max-width: 760px)'); const on = () => setNarrow(mq.matches); on(); mq.addEventListener('change', on); return () => mq.removeEventListener('change', on); }, []);
  const f = d.figures;
  const brief: ReactNode[] = [];
  if (f.approvals) brief.push(<span key="a"><b>{f.approvals} approval{f.approvals === 1 ? '' : 's'}</b> wait for you</span>);
  if (f.overdueCount) brief.push(<span key="o"><b>{d.pulse.find(p => p.key === 'finance')?.value?.replace(' overdue', '')}</b> is overdue</span>);
  if (f.installs) brief.push(<span key="i"><b>{f.installs} install{f.installs === 1 ? '' : 's'}</b> this week</span>);
  if (f.wrJobs !== null) brief.push(<span key="w"><b>{f.wrJobs}</b> Workroom job{f.wrJobs === 1 ? '' : 's'} in motion</span>);
  const kicker = d.now ? d.now.toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' }).toUpperCase() + ' · ' + d.now.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) + ' ET' : '\u00a0';
  const chips = [...EDITION.askChips];
  if (interests[0]) chips[2] = `What's new in ${interests[0].name}?`;
  const ask = (e: React.FormEvent) => { e.preventDefault(); const t = q.trim(); window.location.href = t ? askHref(t) : '/?product=owner'; };
  const status = d.maxOk === null ? (d.loading ? 'CHECKING' : 'NO SIGNAL') : d.maxOk ? 'ONLINE' : 'DEGRADED';
  return (
    <div className="mh-hero-top">
      <div className="mh-orbcol">
        <a href="/?product=owner" aria-label={`Talk to ${EDITION.assistantName}`} className="mh-orb"><Orb size={176} /></a>
        <Wave n={30} h={20} />
        <div className="mh-listen"><span className={`v3-dot ${d.maxOk === false ? 'bad' : d.maxOk ? 'on' : ''}`} />{EDITION.assistantName.toUpperCase()} · {status}</div>
      </div>
      <div className="mh-center">
        <div className="v3-kick mh-kicker">{kicker}</div>
        <h1 className="v3-disp mh-greet">{greeting(d.now)}, <em>{EDITION.ownerName}.</em></h1>
        <p className="mh-brief">
          {d.loading ? 'Gathering your day…' : brief.length ? <>{brief.map((b, i) => <span key={i}>{i ? (i === brief.length - 1 ? ', and ' : ', ') : ''}{b}</span>)}.</> : 'All quiet. Nothing needs you right now.'}
          {!d.loading && interests.length > 0 && <> You follow {interests.slice(0, 2).map(i => i.name).join(' and ')}{interests.length > 2 ? ` and ${interests.length - 2} more` : ''}.</>}
        </p>
        <form className="mh-ask" onSubmit={ask} role="search">
          <Sparkles size={15} strokeWidth={1.5} className="sp" aria-hidden="true" />
          <input value={q} onChange={e => setQ(e.target.value)} placeholder={narrow ? `Ask ${EDITION.assistantName} anything…` : `Ask ${EDITION.assistantName} anything — research, plans, ideas, or any business`} aria-label={`Ask ${EDITION.assistantName} anything`} maxLength={2000} />
          {q.trim() ? <button type="submit" className="mic" aria-label="Send"><Send size={15} /></button>
            : <a href="/?product=owner" className="mic" aria-label={`Open ${EDITION.assistantName} chat`}><Mic size={15} /></a>}
        </form>
        <div className="mh-chips">{chips.map(c => <a key={c} href={askHref(c)} className="v3-chip">{c}</a>)}</div>
      </div>
      <aside className="mh-working" aria-label={`${EDITION.assistantName} is working on`}>
        <div className="mh-wh"><span className="v3-kick">{EDITION.assistantName} is working on</span></div>
        {d.working === null ? <div className="mh-mut">{d.loading ? 'Checking…' : 'No data'}</div>
          : d.working.length === 0 ? <Empty title="Nothing in progress">Tasks you hand to {EDITION.assistantName} show up here while they run.</Empty>
          : d.working.map(w => (
            <a key={w.key} href={w.href} className="mh-wi">
              <div className="t"><b>{w.title}</b><span className="v3-mono">{w.status}</span></div>
              <div className="s">{w.detail}</div>
              <div className="v3-bar"><i style={{ width: w.status === 'in progress' ? '55%' : '20%' }} /></div>
            </a>
          ))}
      </aside>
    </div>
  );
}

function Pulse({ items, onAll }: { items: PulseItem[]; onAll: () => void }) {
  return (
    <div className="mh-pulse" role="list" aria-label="Business pulse">
      <span className="lbl"><span className="v3-dot ok" />PULSE</span>
      {items.map(p => (
        <a key={p.key} href={p.href} className="it" role="listitem" title={p.value === null ? `No data${p.why ? ` (${p.why})` : ''}` : undefined}>
          {p.label} <b className={p.tone || ''}>{p.value ?? '—'}</b>
        </a>
      ))}
      <button type="button" className="all" onClick={onAll}>All businesses <ArrowRight size={12} /></button>
    </div>
  );
}

/* ------------------------------------------------------------- research */

function Research({ items, save, ready }: { items: HomeItem[]; save: (k: HomeKind, i: HomeItem[]) => void; ready: boolean }) {
  const [edit, setEdit] = useState(false);
  const [name, setName] = useState('');
  const add = (n: string, ic = 'search') => { const t = n.trim(); if (!t || items.some(i => i.name.toLowerCase() === t.toLowerCase())) return; save('interests', [...items, { id: newId(), name: t.slice(0, 80), icon: ic }]); setName(''); };
  const remove = (id: string) => save('interests', items.filter(i => i.id !== id));
  const sugg = EDITION.interestSuggestions.filter(s => !items.some(i => i.name.toLowerCase() === s.name.toLowerCase()));
  return (
    <section className="v3-panel mh-col" id="research" aria-labelledby="h-research">
      <div className="v3-ph"><h2 className="v3-disp" id="h-research">Research</h2><span className="v3-kick">Your interests</span>
        <span className="r"><button type="button" className="v3-btn sm" onClick={() => setEdit(e => !e)} aria-pressed={edit}>{edit ? <><Check size={12} /> Done</> : <><Pencil size={12} /> Edit</>}</button></span></div>
      {!ready ? <div className="mh-mut">Loading…</div> : (
        <>
          {items.length > 0 && (
            <div className="mh-icards">
              {items.map(i => (
                <div key={i.id} className="v3-card mh-icard">
                  <div className="t"><span className="gl">{icon(i.icon)}</span><b>{i.name}</b>
                    {edit && <button type="button" className="v3-ib x" onClick={() => remove(i.id)} aria-label={`Remove ${i.name}`}><X size={12} /></button>}</div>
                  <a href={askHref(i.name)} className="go">Ask {EDITION.assistantName} <ArrowRight size={11} /></a>
                </div>
              ))}
            </div>
          )}
          {(edit || items.length === 0) && (
            <div className="mh-iadd">
              {items.length === 0 && <Empty title="No interests yet">Add the topics you want {EDITION.assistantName} to watch for you. They are saved to your profile.</Empty>}
              {/* A question goes to Max exactly as typed (no wrapper); a short topic is saved as an interest. */}
              <form onSubmit={e => { e.preventDefault(); if (looksLikeQuestion(name)) window.location.href = askHref(name.trim()); else add(name); }} className="mh-addrow">
                <input className="v3-input" value={name} onChange={e => setName(e.target.value)} placeholder={`Add a topic, or ask ${EDITION.assistantName}`} aria-label="New interest or question" maxLength={2000} />
                {looksLikeQuestion(name)
                  ? <button type="submit" className="v3-btn pri sm"><ArrowRight size={12} /> Ask</button>
                  : <button type="submit" className="v3-btn pri sm" disabled={!name.trim()}><Plus size={12} /> Add</button>}
              </form>
              {sugg.length > 0 && <div className="mh-chips">{sugg.map(s => <button key={s.name} type="button" className="v3-chip" onClick={() => add(s.name, s.icon)}><Plus size={11} /> {s.name}</button>)}</div>}
            </div>
          )}
          <div className="mh-feed">
            <Empty title="No research feed connected"
              action={<a className="v3-btn sm" href={askHref(items.length ? `Research what's new in ${items.map(i => i.name).join(', ')} and give me the 3 things worth my time.` : 'Research a topic for me.')}><Sparkles size={12} /> Ask {EDITION.assistantName} to research</a>}>
              {EDITION.assistantName} doesn&apos;t invent headlines. Ask for a briefing and the sourced answer opens in chat.
            </Empty>
          </div>
        </>
      )}
    </section>
  );
}

/* --------------------------------------------------------------- growth */

function ListBlock({ kind, label, items, save, unitTotal, placeholder }: { kind: HomeKind; label: string; items: HomeItem[]; save: (k: HomeKind, i: HomeItem[]) => void; unitTotal?: boolean; placeholder: string }) {
  const [adding, setAdding] = useState(false);
  const [name, setName] = useState(''); const [total, setTotal] = useState('');
  const put = (next: HomeItem[]) => save(kind, next);
  const step = (it: HomeItem, dir: number) => put(items.map(x => x.id !== it.id ? x : x.total
    ? { ...x, done: Math.max(0, Math.min(x.total, (x.done || 0) + dir)) }
    : { ...x, progress: Math.max(0, Math.min(100, (x.progress || 0) + dir * 10)) }));
  const add = (e: React.FormEvent) => {
    e.preventDefault(); const n = name.trim(); if (!n) return;
    const t = Math.round(Number(total));
    put([...items, unitTotal && t > 0 ? { id: newId(), name: n, done: 0, total: t } : { id: newId(), name: n, progress: 0 }]);
    setName(''); setTotal(''); setAdding(false);
  };
  return (
    <div className="mh-blk">
      <div className="v3-sec">{label}<button type="button" className="v3-ib" onClick={() => setAdding(a => !a)} aria-label={`Add to ${label}`} aria-expanded={adding}>{adding ? <X size={11} /> : <Plus size={11} />}</button></div>
      {items.length === 0 && !adding && <div className="mh-mut">None yet. <button type="button" className="mh-link" onClick={() => setAdding(true)}>Add one</button></div>}
      {items.map(it => (
        <div key={it.id} className="mh-gi">
          {kind === 'learning' ? <RingProgress value={pct(it)} size={40} /> : null}
          <div className="b">
            <div className="t"><span>{it.name}</span><span className="v3-mono">{it.total ? `${it.done || 0} / ${it.total}` : `${Math.round(it.progress || 0)}%`}</span></div>
            {kind !== 'learning' && <div className="v3-bar"><i style={{ width: `${pct(it) * 100}%` }} /></div>}
          </div>
          <div className="ctl">
            <button type="button" className="v3-ib" onClick={() => step(it, -1)} aria-label={`Less progress on ${it.name}`}><Minus size={11} /></button>
            <button type="button" className="v3-ib" onClick={() => step(it, 1)} aria-label={`More progress on ${it.name}`}><Plus size={11} /></button>
            <button type="button" className="v3-ib" onClick={() => put(items.filter(x => x.id !== it.id))} aria-label={`Remove ${it.name}`}><X size={11} /></button>
          </div>
        </div>
      ))}
      {adding && (
        <form onSubmit={add} className="mh-addrow">
          <input className="v3-input" value={name} onChange={e => setName(e.target.value)} placeholder={placeholder} aria-label={`New ${label.toLowerCase()} item`} maxLength={80} autoFocus />
          {unitTotal && <input className="v3-input n" value={total} onChange={e => setTotal(e.target.value.replace(/\D/g, ''))} placeholder="steps" aria-label="Number of steps (optional)" inputMode="numeric" />}
          <button type="submit" className="v3-btn pri sm" disabled={!name.trim()}>Add</button>
        </form>
      )}
    </div>
  );
}

function Growth({ st, save, d }: { st: Record<HomeKind, HomeItem[]>; save: (k: HomeKind, i: HomeItem[]) => void; d: ReturnType<typeof useHomeData> }) {
  return (
    <section className="v3-panel mh-col" id="growth" aria-labelledby="h-growth">
      <div className="v3-ph"><h2 className="v3-disp" id="h-growth">Growth</h2><span className="v3-kick">{d.now ? d.now.getFullYear() : ''}</span></div>
      <ListBlock kind="goals" label="Goals" items={st.goals} save={save} unitTotal placeholder={EDITION.goalSuggestions[0]} />
      <ListBlock kind="learning" label="Learning" items={st.learning} save={save} unitTotal placeholder="Course or book, e.g. CNC toolpaths" />
      <ListBlock kind="projects" label="Projects" items={st.projects} save={save} placeholder="Personal project" />
      <div className="mh-blk">
        <div className="v3-sec">{EDITION.assistantName} suggests</div>
        {d.suggestions === null ? <div className="mh-mut">Analyzing…</div> : d.suggestions.length === 0 ? <div className="mh-mut">Nothing needs attention.</div> : d.suggestions.map(s => (
          <div key={s.key} className={`mh-sg ${s.tone}`}>
            <span className="gl"><Target size={13} strokeWidth={1.6} /></span>
            <div className="b"><b>{s.title}</b><span>{s.detail}</span></div>
            <a href={s.href} className="v3-btn sm">{s.action}</a>
          </div>
        ))}
      </div>
      <div className="mh-blk">
        <div className="v3-sec">Improvements<a href="/?product=improvements" className="mh-link r">Open</a></div>
        {d.improvements === null ? <div className="mh-mut">{d.errors.improvements ? 'No data' : 'Loading…'}</div>
          : d.improvements.length === 0 ? <div className="mh-mut">No improvement requests yet. {EDITION.assistantName} files them here; builds start only on your tap.</div>
          : d.improvements.slice(0, 3).map((i: any) => (
            <a key={i.id} href="/?product=improvements" className="mh-row"><span>{i.title || 'Improvement'}</span><span className="v3-pill">{String(i.status || 'requested').replace(/_/g, ' ')}</span></a>
          ))}
      </div>
    </section>
  );
}

/* ---------------------------------------------------------------- today */

function Today({ d }: { d: ReturnType<typeof useHomeData> }) {
  const now = d.now;
  return (
    <section className="v3-panel mh-col" id="today" aria-labelledby="h-today">
      <div className="v3-ph"><h2 className="v3-disp" id="h-today">Today</h2>
        <span className="r v3-mono mh-date">{now ? now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }).toUpperCase() : ''}</span></div>
      <div className="mh-blk">
        <div className="v3-sec">Schedule</div>
        {d.schedule === null ? <div className="mh-mut">{d.errors.jobs ? 'No data' : 'Loading…'}</div>
          : d.schedule.length === 0 ? <Empty title="No calendar connected">Nothing scheduled on jobs in the next 7 days.</Empty>
          : <>
            {d.schedule.map(s => (
              <a key={s.key} href={s.href} className="mh-ev">
                <span className="tm v3-mono">{now ? (dayLabel(s.date, now) === 'Today' ? (s.time || 'Today') : dayLabel(s.date, now)) : s.date}</span>
                <span className="b"><b>{s.title}</b><span>{s.detail}</span></span>
              </a>
            ))}
            <div className="mh-mut sm">From job dates · no calendar connected</div>
          </>}
      </div>
      <div className="mh-blk">
        <div className="v3-sec">Approvals {d.approvals?.length ? <span className="v3-cnt">{d.approvals.length}</span> : null}
          <a href="/?product=lead&section=approvals" className="mh-link r">Review</a></div>
        {d.approvals === null ? <div className="mh-mut">{d.errors.approvals ? 'No data' : 'Loading…'}</div>
          : d.approvals.length === 0 ? <div className="mh-mut">Nothing waiting for approval.</div>
          : d.approvals.slice(0, 4).map(a => (
            <a key={a.id} href="/?product=lead&section=approvals" className="mh-ap">
              <span className="b"><span className="v3-kick">{a.channel || a.kind}</span><b>{a.title}</b>{a.to ? <span>{a.to}</span> : null}</span>
              <ArrowRight size={13} />
            </a>
          ))}
        {d.approvals && d.approvals.length > 4 && <a href="/?product=lead&section=approvals" className="mh-link">+{d.approvals.length - 4} more</a>}
      </div>
      <div className="mh-blk">
        <div className="v3-sec">Reminders<a href="/?screen=tasks" className="mh-link r">Tasks</a></div>
        {d.reminders === null ? <div className="mh-mut">{d.errors.tasks ? 'No data' : 'Loading…'}</div>
          : d.reminders.length === 0 ? <div className="mh-mut">No open tasks.</div>
          : d.reminders.map(r => (
            <a key={r.id} href={r.href} className="mh-rm">
              <Bell size={12} strokeWidth={1.6} aria-hidden="true" /><span className="t">{r.title}</span>
              <span className={`w v3-mono ${r.due && now && r.due.slice(0, 10) < now.toISOString().slice(0, 10) ? 'late' : ''}`}>{r.due && now ? dayLabel(r.due.slice(0, 10), now) : ''}</span>
            </a>
          ))}
      </div>
    </section>
  );
}

/* ----------------------------------------------------------------- page */

export default function MaxHome() {
  const d = useHomeData();
  const store = useHomeStore(EDITION.homeUser);
  const [sheet, setSheet] = useState(false);
  const [tab, setTab] = useState('max');
  const closeSheet = useCallback(() => setSheet(false), []);
  // Old hash deep links (/#presentation, /#pricing-studio …) belong to the classic app.
  useEffect(() => { const h = window.location.hash; if (h && h.length > 1 && window.location.pathname === '/') window.location.replace(`/classic${h}`); }, []);
  const groups = useMemo(() => sheetGroups(), []);
  const go = (k: string) => {
    if (k === 'businesses') { setSheet(true); return; }
    setTab(k);
    const el = document.getElementById(k === 'max' ? 'max' : k);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };
  const badges = { finance: !!d.figures.overdueCount, lead: !!d.figures.approvals };
  return (
    <div className="v3 mh-root" data-max-home>
      <Backdrop />
      <V3Band active={tab} notifications={d.figures.approvals || 0} tabs={[
        { key: 'max', label: EDITION.assistantName, onClick: () => go('max') },
        { key: 'research', label: 'Research', onClick: () => go('research') },
        { key: 'growth', label: 'Growth', onClick: () => go('growth') },
        { key: 'today', label: 'Today', onClick: () => go('today') },
        { key: 'businesses', label: 'Businesses', onClick: () => go('businesses') },
      ]} />
      <V3Rail active="max" onAll={() => setSheet(true)} badges={badges} />
      <main className="mh-main">
        <section className="v3-glass mh-hero" id="max" aria-label={`${EDITION.assistantName}`}>
          <Hero d={d} interests={store.state.interests} />
          <Pulse items={d.pulse} onAll={() => setSheet(true)} />
        </section>
        {store.error && <div className="mh-err" role="status">{store.error}</div>}
        <div className="mh-cols">
          <Research items={store.state.interests} save={store.save} ready={store.ready} />
          <Growth st={store.state} save={store.save} d={d} />
          <Today d={d} />
        </div>
      </main>
      <V3TabBar active={tab} onPick={go} todayBadge={d.figures.approvals || 0} />
      <BusinessesSheet open={sheet} onClose={closeSheet} groups={groups} />
    </div>
  );
}
