'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  CalendarDays, Camera, Check, Inbox, Mic, Plus, Scissors, Crown, Home,
  Sparkles, Rocket, Target, CircleDot, AlertTriangle, Banknote, Briefcase,
  Search, Clock, ListChecks, Moon,
} from 'lucide-react';
import { API } from '../../../lib/api';
import {
  addMinutesIso, DAY_END_MIN, DAY_START_MIN, eventLayout,
  filterItems, filterPendingMail, formatMoney, formatOrganizerDate, formatOrganizerTime, groupActions,
  inferSpaceClient, itemsInColumn, itemsOnDay, isOrganizerCommand, jobProgressFromItems,
  KIND_COLOR, KIND_LABEL, monthCells, ORG_THEME_STORAGE, ORG_THEMES, organizerKpis,
  overdueItems, PX_PER_MIN, resolveOrgTheme, shouldOfferCrewDraft, showsWorkroomJobs,
  STATUS_COLUMNS, themedSpaceStyle, timeFromOffset, weekDays, ymd,
  type OrganizerAction, type OrganizerItem, type OrganizerSpace, type OrgTheme, type TodayBucket,
} from '../../../lib/organizer-logic';
import EveningShutdown from './EveningShutdown';
import WeeklyReviewScreen from './WeeklyReviewScreen';
import SprintMRail from './SprintMRail';
import './organizer.css';
import './organizer-themes.css';

const SPACE_LUCIDE: Record<string, typeof Scissors> = {
  workroom: Scissors, empire: Crown, family: Home, personal: Sparkles, ventures: Rocket, amp: Target,
};

function readTheme(): OrgTheme {
  if (typeof window === 'undefined') return 'a';
  const q = new URLSearchParams(window.location.search).get('orgTheme');
  const stored = window.localStorage.getItem(ORG_THEME_STORAGE);
  return resolveOrgTheme(q, stored);
}

type View = 'today' | 'board' | 'day' | 'week' | 'month' | 'lanes' | 'agenda' | 'mail' | 'review' | 'shutdown';

const KINDS = Object.keys(KIND_LABEL);

function initialJob(): string {
  if (typeof window === 'undefined') return '';
  return new URLSearchParams(window.location.search).get('job') || '';
}

export default function WorkroomOrganizer({ business, initialJobId }: { business?: string; initialJobId?: string }) {
  const [view, setView] = useState<View>('today');
  const [anchor, setAnchor] = useState(() => new Date());
  const [board, setBoard] = useState<OrganizerItem[]>([]);
  const [overdue, setOverdue] = useState<OrganizerItem[]>([]);
  const [resources, setResources] = useState<any[]>([]);
  const [jobs, setJobs] = useState<any[]>([]);
  const [plan, setPlan] = useState<any>(null);
  const [route, setRoute] = useState<any>(null);
  const [followups, setFollowups] = useState<any[]>([]);
  const [meta, setMeta] = useState<any>(null);
  const [jobFilter, setJobFilter] = useState(initialJobId || initialJob());
  const [personFilter, setPersonFilter] = useState('');
  const [kindFilter, setKindFilter] = useState('');
  const [spaceFilter, setSpaceFilter] = useState('');
  const [usage, setUsage] = useState<any>(null);
  const [q, setQ] = useState('');
  const [quick, setQuick] = useState('');
  const [drafts, setDrafts] = useState<any[]>([]);
  const [conflict, setConflict] = useState<any>(null);
  const [form, setForm] = useState<any>(null);
  const [timeline, setTimeline] = useState<any>(null);
  const [icsNote, setIcsNote] = useState('');
  const [peopleOpen, setPeopleOpen] = useState(false);
  const [personForm, setPersonForm] = useState({ name: '', role: 'other', phone: '', availability_json: '{"days":["mon","tue","wed","thu","fri"],"start":"08:00","end":"17:00"}' });
  const [listening, setListening] = useState(false);
  const [toast, setToast] = useState('');
  const [crewPrompt, setCrewPrompt] = useState<OrganizerItem | null>(null);
  const [captures, setCaptures] = useState<any[]>([]);
  const [pendingMail, setPendingMail] = useState<any[]>([]);
  const [mailNote, setMailNote] = useState('');
  const [mailAccounts, setMailAccounts] = useState<any>(null);
  const [todayPack, setTodayPack] = useState<{ overdue: OrganizerItem[]; today: OrganizerItem[]; upcoming: OrganizerItem[] }>({ overdue: [], today: [], upcoming: [] });
  const [photoName, setPhotoName] = useState('');
  const [photoB64, setPhotoB64] = useState('');
  const [photoMime, setPhotoMime] = useState('image/jpeg');
  const [spaceEdit, setSpaceEdit] = useState<OrganizerSpace | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [theme, setTheme] = useState<OrgTheme>('a');
  const [completedId, setCompletedId] = useState('');
  const [dragOverCol, setDragOverCol] = useState('');
  const [suggestions, setSuggestions] = useState<any[]>([]);
  const [templates, setTemplates] = useState<any[]>([]);
  const [review, setReview] = useState<any>(null);
  const [shutdown, setShutdown] = useState<any>(null);
  const [searchHits, setSearchHits] = useState<any>(null);
  const [searchOpen, setSearchOpen] = useState(false);
  const [planOpen, setPlanOpen] = useState(false);
  const [cartPreview, setCartPreview] = useState<any>(null);
  const [nudgeDraft, setNudgeDraft] = useState<any>(null);
  const [workOrderSheet, setWorkOrderSheet] = useState(false);
  const dragRef = useRef<{ id: string; mode: 'move' | 'resize'; startY: number; origStart: string; origEnd: string } | null>(null);
  const cardDragRef = useRef<{ id: string } | null>(null);
  const fileRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    setTheme(readTheme());
    if (typeof window === 'undefined') return;
    const qs = new URLSearchParams(window.location.search);
    const v = qs.get('orgView');
    if (v && ['today', 'board', 'day', 'week', 'month', 'lanes', 'agenda', 'mail', 'review', 'shutdown'].includes(v)) {
      setView(v as View);
    }
    const sheet = qs.get('orgSheet');
    if (sheet === 'plan') setPlanOpen(true);
    if (sheet === 'search') setSearchOpen(true);
    const q0 = qs.get('orgQ');
    if (q0) { setQ(q0); setSearchOpen(true); }
  }, []);

  function applyTheme(next: OrgTheme) {
    setTheme(next);
    try { window.localStorage.setItem(ORG_THEME_STORAGE, next); } catch { /* ignore */ }
    if (typeof window !== 'undefined') {
      const url = new URL(window.location.href);
      url.searchParams.set('orgTheme', next);
      window.history.replaceState({}, '', url);
    }
  }

  const day = ymd(anchor);
  const edition = meta?.edition || {};
  const spaces: OrganizerSpace[] = edition.spaces || meta?.spaces || [];
  const showJobs = showsWorkroomJobs(edition, spaceFilter);
  const assistant = edition.assistant || 'Max';
  const filtered = useMemo(
    () => filterItems(board, {
      jobId: jobFilter || undefined,
      resourceId: personFilter || undefined,
      kind: kindFilter || undefined,
      query: q || undefined,
      spaceId: spaceFilter || undefined,
    }),
    [board, jobFilter, personFilter, kindFilter, q, spaceFilter],
  );
  const kpis = useMemo(() => organizerKpis({
    overdue: todayPack.overdue.length,
    today: todayPack.today.length,
    followups,
    doing: itemsInColumn(filtered, 'doing').length,
    jobs,
    moneyItems: [...todayPack.overdue, ...todayPack.today, ...todayPack.upcoming, ...board],
  }), [todayPack, followups, filtered, jobs, board]);
  const daylineItems = useMemo(() => {
    const fromToday = (todayPack.today || []).filter((it) => !spaceFilter || it.space_id === spaceFilter);
    return (fromToday.length ? fromToday : itemsOnDay(filtered, day)).slice(0, 8);
  }, [todayPack.today, filtered, day, spaceFilter]);
  const jobRings = useMemo(() => {
    const ids = [...new Set(filtered.map((it) => it.job_id).filter(Boolean))] as string[];
    return ids.slice(0, 4).map((id) => {
      const job = jobs.find((j) => String(j.id) === String(id));
      const prog = jobProgressFromItems(board, id);
      return { id, label: job?.client_name || job?.title || 'Job', progress: prog };
    }).filter((j) => j.progress);
  }, [filtered, jobs, board]);
  const mailRows = useMemo(
    () => filterPendingMail(pendingMail, { spaceId: spaceFilter || undefined, query: q || undefined }),
    [pendingMail, spaceFilter, q],
  );

  const load = useCallback(async () => {
    const from = new Date(anchor); from.setDate(from.getDate() - 31);
    const to = new Date(anchor); to.setDate(to.getDate() + 40);
    const spaceQs = spaceFilter ? `&space_id=${encodeURIComponent(spaceFilter)}` : '';
    const qs = `start_date=${ymd(from)}&end_date=${ymd(to)}${spaceQs}`;
    const [b, r, p, rt, m, caps, u, pm, td, sg, tpl, rv, sd] = await Promise.all([
      fetch(`${API}/organizer/board?${qs}`).then((x) => x.json()).catch(() => ({ items: [], overdue: [] })),
      fetch(`${API}/organizer/resources`).then((x) => x.json()).catch(() => ({ resources: [] })),
      fetch(`${API}/organizer/day-plan?plan_date=${day}`).then((x) => x.json()).catch(() => null),
      fetch(`${API}/organizer/route?plan_date=${day}`).then((x) => x.json()).catch(() => null),
      fetch(`${API}/organizer/meta`).then((x) => x.json()).catch(() => null),
      fetch(`${API}/organizer/captures`).then((x) => x.json()).catch(() => ({ captures: [] })),
      fetch(`${API}/organizer/usage`).then((x) => x.json()).catch(() => null),
      fetch(`${API}/organizer/pending-mail`).then((x) => x.json()).catch(() => ({ items: [] })),
      fetch(`${API}/organizer/today`).then((x) => x.json()).catch(() => ({ overdue: [], today: [], upcoming: [], items: [] })),
      fetch(`${API}/organizer/suggestions`).then((x) => x.json()).catch(() => ({ suggestions: [] })),
      fetch(`${API}/organizer/templates`).then((x) => x.json()).catch(() => ({ templates: [] })),
      fetch(`${API}/organizer/review/weekly`).then((x) => x.json()).catch(() => null),
      fetch(`${API}/organizer/review/shutdown?plan_date=${day}`).then((x) => x.json()).catch(() => null),
    ]);
    const allowsJobs = !!(m?.edition?.allows_workroom_jobs);
    const jobSpace = showsWorkroomJobs(m?.edition, spaceFilter);
    const [j, f] = await Promise.all([
      jobSpace ? fetch(`${API}/jobs?limit=200`).then((x) => x.json()).catch(() => ({ jobs: [] })) : Promise.resolve({ jobs: [] }),
      allowsJobs ? fetch(`${API}/organizer/follow-ups`).then((x) => x.json()).catch(() => ({ drafts: [] })) : Promise.resolve({ drafts: [] }),
    ]);
    setBoard(b.items || []);
    setOverdue(td.overdue || b.overdue || overdueItems(b.items || [], `${day}T00:00:00`));
    setTodayPack({
      overdue: td.overdue || [],
      today: td.today || td.items || [],
      upcoming: td.upcoming || [],
    });
    setResources([...(r.resources || []), ...((r.directory || []).slice(0, 40))]);
    setJobs(j.jobs || []);
    setPlan(p);
    setRoute(rt);
    setFollowups(f.drafts || []);
    setMeta(m);
    setCaptures(caps.captures || []);
    setUsage(u);
    setPendingMail(pm.items || []);
    setMailNote(pm.note || '');
    setMailAccounts(pm.accounts || null);
    setSuggestions(sg.suggestions || []);
    setTemplates(tpl.templates || []);
    setReview(rv);
    setShutdown(sd);
    setLoaded(true);
    if (jobFilter && jobSpace) {
      const tl = await fetch(`${API}/organizer/jobs/${jobFilter}/timeline`).then((x) => x.ok ? x.json() : null).catch(() => null);
      setTimeline(tl);
    } else setTimeline(null);
  }, [anchor, day, jobFilter, spaceFilter]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    const query = q.trim();
    if (query.length < 2) { setSearchHits(null); return; }
    const t = window.setTimeout(async () => {
      const data = await fetch(`${API}/organizer/search?q=${encodeURIComponent(query)}`).then((x) => x.json()).catch(() => null);
      setSearchHits(data);
    }, 220);
    return () => window.clearTimeout(t);
  }, [q]);

  async function saveEvent(payload: any, confirm = false) {
    const body = { ...payload, confirm_conflicts: confirm, space_id: payload.space_id || spaceFilter || undefined };
    const isNew = !payload.id || String(payload.id).startsWith('new');
    const asItem = !body.start_time || ['todo', 'reminder', 'deadline', 'followup'].includes(String(body.kind || body.type || ''));
    const url = asItem
      ? (isNew ? `${API}/organizer/items` : `${API}/organizer/items/${payload.id}`)
      : (isNew ? `${API}/schedule/events` : `${API}/schedule/events/${payload.id}`);
    const res = await fetch(url, { method: isNew ? 'POST' : 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) });
    if (res.status === 409) {
      const err = await res.json();
      setConflict({ payload: body, detail: err.detail || err });
      return null;
    }
    if (res.status === 429) {
      const err = await res.json();
      setToast(err.detail?.message || 'Usage cap reached for this edition.');
      return null;
    }
    if (!res.ok) throw new Error(await res.text());
    const saved = await res.json();
    const item = saved.item || saved;
    if (body.reminder_at || body.due_at) {
      await fetch(`${API}/organizer/reminder-draft`, {
        method: 'POST', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: body.title || 'Reminder',
          due_at: body.reminder_at || body.due_at,
          body: body.notes || body.title || 'Due in Organizer',
          channel: 'max',
          job_id: body.job_id || undefined,
          space_id: body.space_id,
          item_id: item?.id,
        }),
      }).catch(() => null);
    }
    setConflict(null);
    setForm(null);
    await load();
    return saved;
  }

  async function moveEvent(id: string, start: string, end: string, confirm = false) {
    const res = await fetch(`${API}/schedule/events/${id}/move`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ start_time: start, end_time: end, confirm_conflicts: confirm }),
    });
    if (res.status === 409) {
      const err = await res.json();
      setConflict({ payload: { id, start_time: start, end_time: end }, detail: err.detail || err, move: true });
      return;
    }
    setConflict(null);
    await load();
    const moved = board.find((x) => x.id === id) || { id, start_time: start, end_time: end, title: 'Event' };
    if (shouldOfferCrewDraft(true, false)) setCrewPrompt({ ...moved, start_time: start, end_time: end });
  }

  async function runAction(action: string, item: Partial<OrganizerItem>, extra: Record<string, any> = {}) {
    const act = (item.actions || []).find((a) => a.id === action);
    if (act?.href && ['navigate', 'call', 'ask_max', 'open_quote', 'open_invoice', 'mark_paid'].includes(action)) {
      window.open(act.href, action === 'call' ? '_self' : '_blank');
      return;
    }
    const res = await fetch(`${API}/organizer/actions`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action, item_id: item.id, item, confirm: !!extra.confirm,
        confirm_conflicts: !!extra.confirm_conflicts,
        start_time: extra.start_time, end_time: extra.end_time,
        body: extra.body, job_id: extra.job_id || item.job_id, approval_id: extra.approval_id,
      }),
    });
    if (res.status === 409) {
      const err = await res.json();
      setConflict({ payload: { ...item, ...extra, action }, detail: err.detail || err, action: true });
      return;
    }
    if (res.status === 429) {
      const err = await res.json();
      setToast(err.detail?.message || 'Usage cap reached for this edition.');
      return;
    }
    const data = await res.json();
    if (action === 'supplier_cart') setCartPreview(data.created || data);
    if (action === 'waiting_nudge' || action === 'remind') setNudgeDraft(data.approval || data.created || data);
    if (data.href && action !== 'attach_file' && !['supplier_cart', 'snooze', 'remind'].includes(action)) {
      window.open(data.href, action === 'call' ? '_self' : '_blank');
    }
    setToast(data.message || (data.sent ? 'Sent after founder tap.' : 'Draft ready. Approve & Send still required for anything outbound.'));
    setCrewPrompt(null);
    await load();
    return data;
  }

  async function runMailAction(action: string, item: any) {
    if (action === 'open' && item.open_href) {
      window.open(item.open_href, '_blank');
      return;
    }
    const res = await fetch(`${API}/organizer/pending-mail/actions`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        action, source: item.source, message_id: item.message_id,
        body: item.suggested_reply,
      }),
    });
    if (res.status === 429) {
      const err = await res.json();
      setToast(err.detail?.message || 'Usage cap reached for this edition.');
      return;
    }
    const data = await res.json().catch(() => ({}));
    setToast(data.message || (data.sent ? 'Sent after owner tap.' : 'Draft only. Nothing sent.'));
    await load();
    return data;
  }

  async function runCommand(text: string, confirm = false) {
    const res = await fetch(`${API}/organizer/command`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, confirm }),
    });
    if (res.status === 409) {
      const err = await res.json();
      setConflict({ payload: { text }, detail: err.detail || err, command: true });
      return;
    }
    const data = await res.json();
    setToast(data.message || 'Command ran. Nothing sent.');
    setQuick('');
    await load();
    return data;
  }

  function onPointerDown(e: React.PointerEvent, item: OrganizerItem, mode: 'move' | 'resize') {
    if (item.read_only) return;
    (e.target as HTMLElement).setPointerCapture?.(e.pointerId);
    dragRef.current = {
      id: item.id, mode, startY: e.clientY,
      origStart: item.start_time || `${day}T09:00:00`,
      origEnd: item.end_time || addMinutesIso(item.start_time || `${day}T09:00:00`, 60),
    };
  }
  function onPointerMove(e: React.PointerEvent) {
    const d = dragRef.current; if (!d) return;
    const deltaMin = Math.round((e.clientY - d.startY) / PX_PER_MIN);
    const el = document.querySelector(`[data-ev="${d.id}"]`) as HTMLElement | null;
    if (!el) return;
    if (d.mode === 'move') el.style.transform = `translateY(${deltaMin * PX_PER_MIN}px)`;
    if (d.mode === 'resize') el.style.height = `${Math.max(22, (60 + deltaMin) * PX_PER_MIN)}px`;
  }
  async function onPointerUp(e: React.PointerEvent) {
    const d = dragRef.current; if (!d) return;
    dragRef.current = null;
    const deltaMin = Math.round((e.clientY - d.startY) / PX_PER_MIN / 15) * 15;
    if (!deltaMin) { await load(); return; }
    if (d.mode === 'move') await moveEvent(d.id, addMinutesIso(d.origStart, deltaMin), addMinutesIso(d.origEnd, deltaMin));
    else await moveEvent(d.id, d.origStart, addMinutesIso(d.origEnd, deltaMin));
  }

  async function moveCard(id: string, column: string) {
    const res = await fetch(`${API}/organizer/items/${encodeURIComponent(id)}/move`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ column }),
    });
    if (!res.ok) {
      setToast('Could not move that card.');
      return;
    }
    if (column === 'done') {
      setCompletedId(id);
      window.setTimeout(() => setCompletedId((cur) => (cur === id ? '' : cur)), 700);
    }
    await load();
  }

  function onCardPointerDown(e: React.PointerEvent, id: string) {
    (e.currentTarget as HTMLElement).setPointerCapture?.(e.pointerId);
    cardDragRef.current = { id };
    (e.currentTarget as HTMLElement).dataset.dragging = '1';
  }
  function onCardPointerUp(e: React.PointerEvent, column: string) {
    const d = cardDragRef.current;
    (e.currentTarget as HTMLElement).dataset.dragging = '';
    if (!d) return;
    cardDragRef.current = null;
    if (d.id) moveCard(d.id, column);
  }
  function onColumnPointerUp(e: React.PointerEvent, column: string) {
    const d = cardDragRef.current;
    if (!d) return;
    cardDragRef.current = null;
    moveCard(d.id, column);
  }

  async function submitQuick(text: string, confirm = false) {
    if (isOrganizerCommand(text) && !photoB64) {
      await runCommand(text, confirm);
      return;
    }
    const guessed = inferSpaceClient(text, spaces.map((s) => s.slug));
    const res = await fetch(`${API}/organizer/quick-add`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        text, confirm,
        space_id: spaceFilter || guessed || undefined,
        photo_b64: photoB64 || undefined,
        filename: photoName || undefined,
        mime: photoMime || undefined,
      }),
    });
    const data = await res.json();
    if (!confirm) setDrafts(data.drafts || []);
    else {
      setDrafts([]); setQuick(''); setPhotoB64(''); setPhotoName('');
      await load();
    }
  }

  function onPickPhoto(file: File | null) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const result = String(reader.result || '');
      setPhotoB64(result.includes(',') ? result.split(',')[1] : result);
      setPhotoName(file.name);
      setPhotoMime(file.type || 'image/jpeg');
    };
    reader.readAsDataURL(file);
  }

  function RecordLinks({ item }: { item: Partial<OrganizerItem> }) {
    const links = item.record_links || [];
    if (!links.length) return null;
    return (
      <div className="org-links" onClick={(e) => e.stopPropagation()}>
        {links.map((l) => (
          <a key={`${l.kind}-${l.id}`} href={l.href}>{l.label}</a>
        ))}
      </div>
    );
  }

  function MoneyStrip({ item }: { item: Partial<OrganizerItem> }) {
    const mny = item.money;
    if (!mny || !item.job_id) return null;
    return (
      <div className="org-money" data-money="1" title="Read-only from quotes and invoices">
        <span>Dep {formatMoney(mny.deposit)}</span>
        <span>Paid {formatMoney(mny.paid)}</span>
        <span>Bal {formatMoney(mny.balance)}</span>
        <span>Mgn {formatMoney(mny.margin)}</span>
        <em>{mny.collected_fraction}</em>
      </div>
    );
  }

  function WaitingChip({ item }: { item: Partial<OrganizerItem> }) {
    if (!item.waiting_on) return null;
    return (
      <div className="org-wait" data-waiting="1">
        Waiting on {item.waiting_on}
        {item.nudge_after_days ? ` · nudge ${item.nudge_after_days}d` : ''}
      </div>
    );
  }

  function ProgressBar({ item }: { item: Partial<OrganizerItem> }) {
    const p = item.progress;
    if (!p || !p.total) return null;
    return (
      <div className="org-progress" title={`${p.done} of ${p.total} tasks`}>
        <span className="org-progress-bar"><i style={{ width: `${p.percent}%` }} /></span>
        <em>{p.fraction}</em>
      </div>
    );
  }

  function SpaceGlyph({ slug, accent, size = 14 }: { slug: string; accent: string; size?: number }) {
    const Icon = SPACE_LUCIDE[slug] || CircleDot;
    return <span className="org-space-ico" style={{ color: accent }}><Icon size={size} strokeWidth={1.75} /></span>;
  }

  function EmptyState({ title, body, icon }: { title: string; body: string; icon?: React.ReactNode }) {
    return (
      <div className="org-empty">
        <div className="org-empty-ico">{icon || <Inbox size={18} />}</div>
        <b>{title}</b>
        <p>{body}</p>
      </div>
    );
  }

  function ProgressRing({ percent, label, fraction }: { percent: number; label: string; fraction: string }) {
    const r = 16;
    const circ = 2 * Math.PI * r;
    const offset = circ - (Math.max(0, Math.min(100, percent)) / 100) * circ;
    return (
      <div className="org-kpi" title={label}>
        <svg className="org-ring" viewBox="0 0 44 44" aria-hidden>
          <circle className="bg" cx="22" cy="22" r={r} />
          <circle className="fg" cx="22" cy="22" r={r} strokeDasharray={circ} strokeDashoffset={offset} transform="rotate(-90 22 22)" />
        </svg>
        <div>
          <strong>{fraction}</strong>
          <span>{label}</span>
        </div>
      </div>
    );
  }

  function OrgCard({ item, column }: { item: OrganizerItem; column: string }) {
    const style = themedSpaceStyle(spaces.find((s) => s.slug === item.space_id) || item.space_id, theme);
    return (
      <div
        className={`org-kanban-card${completedId === item.id ? ' is-complete' : ''}`}
        style={{ borderLeftColor: style.accent }}
        draggable
        onDragStart={(e) => { e.dataTransfer.setData('text/plain', item.id); e.dataTransfer.effectAllowed = 'move'; }}
        onPointerDown={(e) => onCardPointerDown(e, item.id)}
        onClick={() => setForm({ ...item, assigned_resource_ids: item.assigned_resource_ids || [] })}
      >
        <div className="org-kanban-space" style={{ color: style.accent }}>
          <SpaceGlyph slug={style.slug} accent={style.accent} /> {style.label}
        </div>
        <b>{item.title}</b>
        <small>{KIND_LABEL[item.kind || item.type || ''] || item.kind} · {formatOrganizerTime(item.start_time || item.due_at) || 'no date'}</small>
        <WaitingChip item={item} />
        <ProgressBar item={item} />
        <MoneyStrip item={item} />
        <RecordLinks item={item} />
        <ActionBar item={item} compact />
      </div>
    );
  }

  function ActionBar({ item, compact }: { item: Partial<OrganizerItem>; compact?: boolean }) {
    const groups = groupActions(item.actions);
    const order = compact ? ['stop', 'job', 'followup'] : ['stop', 'job', 'followup', 'file', 'move'];
    const flat = order.flatMap((g) => groups[g] || []);
    if (!flat.length) return null;
    return (
      <div className="org-abar" onClick={(e) => e.stopPropagation()}>
        {flat.map((a: OrganizerAction) => (
          a.href && ['navigate', 'call', 'ask_max', 'open_quote', 'open_invoice', 'mark_paid'].includes(a.id) ? (
            <a key={a.id} href={a.href} target={a.id === 'call' ? undefined : '_blank'} rel="noreferrer">{a.label}</a>
          ) : (
            <button
              key={a.id}
              className={a.id === 'approve_send' ? 'gold' : ''}
              onClick={() => runAction(a.id, item, { confirm: a.id === 'approve_send' })}
            >{a.label}</button>
          )
        ))}
      </div>
    );
  }

  async function startVoice() {
    if (navigator.mediaDevices?.getUserMedia) {
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
        const rec = new MediaRecorder(stream);
        const chunks: BlobPart[] = [];
        rec.ondataavailable = (ev) => { if (ev.data.size) chunks.push(ev.data); };
        rec.onstop = async () => {
          stream.getTracks().forEach((t) => t.stop());
          setListening(false);
          const blob = new Blob(chunks, { type: rec.mimeType || 'audio/webm' });
          const fd = new FormData();
          fd.append('audio', blob, 'quick-add.webm');
          const res = await fetch(`${API}/organizer/transcribe`, { method: 'POST', body: fd });
          if (res.ok) {
            const data = await res.json();
            const said = data.text || data.transcript || '';
            if (said) { setQuick(said); submitQuick(said); }
            else setToast('Heard nothing. Type it instead.');
            return;
          }
          setToast('Voice transcription is not configured. Type instead.');
        };
        setListening(true);
        rec.start();
        window.setTimeout(() => { try { rec.stop(); } catch { /* already stopped */ } }, 6000);
        return;
      } catch { /* fall through to browser STT */ }
    }
    const SR: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { setQuick((t) => t || ''); setToast('Voice typing is not available. Type instead.'); return; }
    const rec = new SR();
    rec.lang = 'en-US';
    rec.onresult = (ev: any) => {
      const said = ev.results?.[0]?.[0]?.transcript || '';
      setQuick(said);
      if (said) submitQuick(said);
    };
    rec.onend = () => setListening(false);
    setListening(true);
    rec.start();
  }

  async function approvePlan() {
    const res = await fetch(`${API}/organizer/day-plan/approve?plan_date=${day}`, { method: 'POST' });
    const data = await res.json().catch(() => ({}));
    setToast(data.message || 'Plan saved. Nothing was sent.');
    setPlanOpen(false);
    await load();
  }

  async function acceptSuggestion(id: string) {
    const res = await fetch(`${API}/organizer/suggestions/${encodeURIComponent(id)}/accept`, { method: 'POST' });
    const data = await res.json().catch(() => ({}));
    setToast(data.message || 'To-do saved. Nothing was sent.');
    await load();
  }

  async function dismissSuggestion(id: string) {
    const res = await fetch(`${API}/organizer/suggestions/${encodeURIComponent(id)}/dismiss`, { method: 'POST' });
    const data = await res.json().catch(() => ({}));
    setToast(data.message || 'Dismissed. Nothing was created.');
    await load();
  }

  async function applyTemplate(id: string) {
    const res = await fetch(`${API}/organizer/templates/${encodeURIComponent(id)}/apply`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ space_id: spaceFilter || undefined, job_id: jobFilter || undefined }),
    });
    const data = await res.json().catch(() => ({}));
    setToast(data.fraction ? `Checklist ${data.fraction}. Nothing sent.` : (data.message || 'Template applied.'));
    await load();
  }

  async function saveWaiting(item: any) {
    if (!item?.id || !item.waiting_on) return;
    const res = await fetch(`${API}/organizer/items/${encodeURIComponent(item.id)}/waiting`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ who: item.waiting_on, nudge_after_days: Number(item.nudge_after_days || 3) }),
    });
    const data = await res.json().catch(() => ({}));
    setForm(data.item || { ...item, status: 'waiting_on' });
    setToast('Waiting-on saved. Draft nudge only — nothing sent.');
    await load();
  }

  async function completeShutdown(payload: {
    notes: string;
    tomorrow_focus: string;
    tomorrow_space_id: string;
    moves: { id: string; destination: string; due_at?: string }[];
  }) {
    const res = await fetch(`${API}/organizer/review/shutdown/complete`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ date: day, ...payload }),
    });
    const data = await res.json().catch(() => ({}));
    setToast(data.sent === false ? 'Day closed. Unfinished items moved. Nothing sent.' : (data.detail || 'Shutdown saved.'));
    setView('today');
    await load();
  }

  async function addPerson() {
    await fetch(`${API}/organizer/resources`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(personForm),
    });
    setPeopleOpen(false);
    await load();
  }

  async function exportIcs() {
    const tok = await fetch(`${API}/organizer/subscribe-token?label=founder`, { method: 'POST' }).then((r) => r.json());
    setIcsNote(`${API.replace(/\/api\/v1$/, '')}${tok.subscribe_path} — read-only subscribe link. Google Calendar sync is not connected in this repo.`);
    window.open(`${API}/organizer/export.ics`, '_blank');
  }

  const hours = [];
  for (let m = DAY_START_MIN; m < DAY_END_MIN; m += 60) hours.push(Math.floor(m / 60));

  function EventBlock({ item, dayStr }: { item: OrganizerItem; dayStr: string }) {
    const lay = eventLayout(item, dayStr);
    if (!lay) return null;
    const color = KIND_COLOR[item.kind || item.type || 'other'] || '#52525b';
    return (
      <div
        data-ev={item.id}
        className="org-ev"
        style={{ top: lay.top, height: lay.height, background: color }}
        onPointerDown={(e) => onPointerDown(e, item, 'move')}
        onPointerMove={onPointerMove}
        onPointerUp={onPointerUp}
        onClick={(e) => { e.stopPropagation(); setForm({ ...item, assigned_resource_ids: item.assigned_resource_ids || [] }); }}
      >
        <b>{item.title}</b>
        <div>{KIND_LABEL[item.kind || item.type || ''] || item.kind}</div>
        <div className="rsz" onPointerDown={(e) => { e.stopPropagation(); onPointerDown(e, item, 'resize'); }} />
      </div>
    );
  }

  return (
    <div
      className="org-root"
      data-organizer
      data-org-theme={theme}
      data-organizer-loaded={loaded ? '1' : '0'}
      data-today-count={todayPack.overdue.length + todayPack.today.length + todayPack.upcoming.length}
    >
      <div className="org-top">
        <div className="org-title">
          Organizer
          {edition.label && <span className="org-ed">{edition.label}</span>}
          <span>all life &amp; business areas · nothing sent without {edition.owner || 'the owner'}&apos;s tap</span>
          <div className="org-themes" role="radiogroup" aria-label="Organizer look">
            {ORG_THEMES.map((t) => (
              <button
                key={t.id}
                role="radio"
                aria-checked={theme === t.id}
                className={theme === t.id ? 'on' : ''}
                onClick={() => applyTheme(t.id)}
                title={t.name}
              >{t.label}</button>
            ))}
          </div>
        </div>
        <div className="org-spaces" role="tablist" aria-label="Areas">
          <button className={!spaceFilter ? 'on' : ''} onClick={() => setSpaceFilter('')}>All areas</button>
          {spaces.map((s) => {
            const st = themedSpaceStyle(s, theme);
            const on = spaceFilter === s.slug;
            return (
              <button
                key={s.slug}
                className={on ? 'on' : ''}
                style={{
                  borderColor: st.accent,
                  background: on ? st.accent : `${st.accent}22`,
                  color: on ? (theme === 'b' ? '#fffdf8' : '#0c0d11') : undefined,
                }}
                onClick={() => setSpaceFilter(s.slug)}
                onDoubleClick={() => setSpaceEdit(s)}
              >
                <SpaceGlyph slug={st.slug} accent={on ? (theme === 'b' ? '#fffdf8' : '#0c0d11') : st.accent} /> {st.label}
              </button>
            );
          })}
        </div>
        <div className="org-toolbar">
          {(['today', 'board', 'day', 'week', 'month', 'lanes', 'agenda', 'mail', 'review', 'shutdown'] as View[]).map((v) => (
            <button key={v} className={view === v ? 'on' : ''} onClick={() => setView(v)}>
              {v === 'mail' ? 'messages' : v === 'review' ? 'weekly review' : v === 'shutdown' ? 'evening shutdown' : v}
            </button>
          ))}
          <button onClick={() => setAnchor(new Date())}>Today</button>
          <button onClick={() => setAnchor((d) => { const n = new Date(d); n.setDate(n.getDate() - (view === 'month' ? 30 : view === 'week' ? 7 : 1)); return n; })}>‹</button>
          <button onClick={() => setAnchor((d) => { const n = new Date(d); n.setDate(n.getDate() + (view === 'month' ? 30 : view === 'week' ? 7 : 1)); return n; })}>›</button>
          <span style={{ fontSize: 12, fontWeight: 600 }}>{anchor.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })}</span>
          {showJobs && (
            <select value={jobFilter} onChange={(e) => setJobFilter(e.target.value)}>
              <option value="">All jobs</option>
              {jobs.map((j) => <option key={j.id} value={j.id}>{j.client_name || j.title || j.job_number}</option>)}
            </select>
          )}
          <select value={personFilter} onChange={(e) => setPersonFilter(e.target.value)}>
            <option value="">All people</option>
            {resources.map((r) => <option key={r.id} value={r.id}>{r.name} · {r.role}</option>)}
          </select>
          <select value={kindFilter} onChange={(e) => setKindFilter(e.target.value)}>
            <option value="">All types</option>
            {KINDS.map((k) => <option key={k} value={k}>{KIND_LABEL[k]}</option>)}
          </select>
          <input
            placeholder="Search items, jobs, clients, estimates"
            value={q}
            onChange={(e) => { setQ(e.target.value); setSearchOpen(true); }}
            onFocus={() => setSearchOpen(true)}
            aria-label="Smart search"
          />
          <button className="org-btn-gold" onClick={() => { setPlanOpen(true); }} data-plan-open="1">
            <CalendarDays size={14} /> Plan my day
          </button>
          <button className="org-btn-gold" onClick={() => setView('shutdown')} data-shutdown-open="1">
            <Moon size={14} /> Shutdown
          </button>
          <button onClick={() => setView('review')} data-weekly-open="1">
            <ListChecks size={14} /> Weekly
          </button>
          <button className="org-btn-gold" onClick={() => setWorkOrderSheet(true)} data-sprint-m-open="1">
            <Briefcase size={14} /> Work orders
          </button>
          {templates[0] && (
            <select aria-label="Apply checklist" defaultValue="" onChange={(e) => { if (e.target.value) applyTemplate(e.target.value); e.target.value = ''; }}>
              <option value="">Apply checklist…</option>
              {templates.map((t) => <option key={t.id} value={t.id}>{t.label}</option>)}
            </select>
          )}
          <button className="org-btn-gold" onClick={() => setForm({
            title: '', type: 'appointment', start_time: `${day}T10:00:00`, end_time: `${day}T11:00:00`,
            job_id: showJobs ? jobFilter : '', assigned_resource_ids: personFilter ? [personFilter] : [],
            space_id: spaceFilter || (spaces[0]?.slug),
          })}><Plus size={14} /> Add</button>
          <button onClick={() => setPeopleOpen(true)}>People</button>
          <button onClick={exportIcs}>ICS</button>
        </div>
        <div className="org-qa" style={{ marginTop: 8 }}>
          <input
            value={quick}
            onChange={(e) => setQuick(e.target.value)}
            placeholder="Quick-add: text, voice, or a photo. Space is picked when it's obvious."
            onKeyDown={(e) => { if (e.key === 'Enter' && (quick.trim() || photoB64)) submitQuick(quick.trim() || photoName || 'photo'); }}
          />
          <input ref={fileRef} type="file" accept="image/*" hidden onChange={(e) => onPickPhoto(e.target.files?.[0] || null)} />
          <button onClick={() => fileRef.current?.click()}>{photoName ? <><Check size={14} /> Photo</> : <><Camera size={14} /> Photo</>}</button>
          <button onClick={() => (quick.trim() || photoB64) && submitQuick(quick.trim() || photoName || 'photo')}>Draft</button>
          <button onClick={startVoice}>{listening ? 'Listening…' : <><Mic size={14} /> Voice</>}</button>
        </div>
      </div>

      <div className="org-hero">
        <h2>{formatOrganizerDate(anchor)}</h2>
        <p>
          {kpis.overdue ? `${kpis.overdue} overdue · ` : 'Caught up on overdue · '}
          {kpis.dueToday} on the board today · nothing sent without {edition.owner || 'the owner'}&apos;s tap
        </p>
      </div>
      <div className="org-kpis" aria-label="Today at a glance">
        <div className="org-kpi"><AlertTriangle size={18} /><div><strong>{kpis.overdue}</strong><span>Overdue</span></div></div>
        <div className="org-kpi"><CalendarDays size={18} /><div><strong>{kpis.dueToday}</strong><span>Due today</span></div></div>
        <div className="org-kpi"><Banknote size={18} /><div><strong>{kpis.moneyWaiting}</strong><span>Money waiting</span></div></div>
        {jobRings[0] ? (
          <ProgressRing percent={jobRings[0].progress!.percent} label={jobRings[0].label} fraction={jobRings[0].progress!.fraction} />
        ) : (
          <div className="org-kpi"><Briefcase size={18} /><div><strong>{kpis.jobsInProgress}</strong><span>Jobs in progress</span></div></div>
        )}
      </div>
      <div className="org-dayline" aria-label="Day timeline">
        {daylineItems.length === 0 && (
          <div className="org-dayline-slot"><em>Open</em><b>Quiet day</b></div>
        )}
        {daylineItems.map((it) => {
          const st = themedSpaceStyle(spaces.find((s) => s.slug === it.space_id) || it.space_id, theme);
          return (
            <button key={it.id} className="org-dayline-slot" onClick={() => setForm({ ...it })} style={{ borderColor: st.accent }}>
              <em>{formatOrganizerTime(it.start_time || it.due_at) || 'Anytime'}</em>
              <b>{it.title}</b>
            </button>
          );
        })}
      </div>

      {conflict && (
        <div className="org-warn" role="alert">
          <b>Not saved — conflict.</b> {(conflict.detail?.conflicts || []).map((c: any) => c.message).join(' ')}
          <div className="org-actions">
            <button className="org-btn-gold" onClick={() => conflict.command
              ? runCommand(conflict.payload.text, true)
              : conflict.action
                ? runAction(conflict.payload.action, conflict.payload, { confirm_conflicts: true })
                : conflict.move
                  ? moveEvent(conflict.payload.id, conflict.payload.start_time, conflict.payload.end_time, true)
                  : saveEvent(conflict.payload, true)}>Keep anyway</button>
            <button onClick={() => { setConflict(null); load(); }}>Cancel</button>
          </div>
        </div>
      )}

      <div className="org-body">
        <aside className="org-side">
          <div className="org-card" data-suggested-tray="1">
            <h3>Suggested</h3>
            <div className="org-note">From mail, WhatsApp, voice notes, and approved estimates. Accept or dismiss — nothing is created silently.</div>
            {suggestions.length === 0 && <EmptyState title="No suggestions" body="Incoming mail and notes will appear here for a tap." icon={<Inbox size={18} />} />}
            {suggestions.slice(0, 8).map((s) => (
              <div className="org-row" key={s.id} data-suggestion={s.source}>
                <span className="tm">{s.source}</span>
                <span>
                  <b>{s.title}</b>
                  <small>{s.body}</small>
                  <div className="org-abar" onClick={(e) => e.stopPropagation()}>
                    <button className="gold" onClick={() => acceptSuggestion(s.id)}>Accept</button>
                    <button onClick={() => dismissSuggestion(s.id)}>Dismiss</button>
                  </div>
                </span>
              </div>
            ))}
          </div>
          <div className="org-card">
            <h3>{assistant}’s proposed day</h3>
            <div style={{ fontSize: 12 }}>{plan?.headline || 'Loading…'}</div>
            {(plan?.proposed_order || []).slice(0, 6).map((s: any) => (
              <div className="org-row" key={s.id || s.title}><span className="tm">{(s.suggested_start || '').slice(11, 16)}</span><span><b>{s.title}</b><small>{s.location_address}</small></span></div>
            ))}
            <button className="org-btn-gold" style={{ marginTop: 8 }} onClick={() => setPlanOpen(true)}>
              Plan my day
            </button>
            <button className="org-home-btn" style={{ marginTop: 8 }} disabled={plan?.approved} onClick={approvePlan}>
              {plan?.approved ? 'Approved' : 'Approve today'}
            </button>
            <div className="org-note">{plan?.note}</div>
          </div>
          <div className="org-card">
            <h3>Pending messages</h3>
            <div className="org-note">{mailNote || 'Unanswered or waiting mail from this edition’s connected accounts. Reading only.'}</div>
            {mailRows.length === 0 && <div className="org-note">Nothing waiting.</div>}
            {mailRows.slice(0, 6).map((m) => (
              <div className="org-row" key={m.id}>
                <span className="tm">{m.account || m.source}</span>
                <span>
                  <b>{m.subject}</b>
                  <small>{m.from_name || m.from} · {m.space_id}{m.job_title ? ` · ${m.job_title}` : ''}{m.person_name ? ` · ${m.person_name}` : ''}</small>
                  {m.suggested_reply && <small>{String(m.suggested_reply).slice(0, 120)}</small>}
                  <div className="org-abar" onClick={(e) => e.stopPropagation()}>
                    {m.open_href && <a href={m.open_href} target="_blank" rel="noreferrer">Open</a>}
                    <button onClick={() => runMailAction('draft_reply', m)}>Draft reply</button>
                    <button onClick={() => runMailAction('snooze', m)}>Snooze</button>
                    <button onClick={() => runMailAction('todo', m)}>To-do</button>
                    <button onClick={() => runMailAction('followup', m)}>Follow-up</button>
                  </div>
                </span>
              </div>
            ))}
            {mailRows.length > 6 && (
              <button className="org-home-btn" onClick={() => setView('mail')}>See all {mailRows.length}</button>
            )}
          </div>
          <div className="org-card">
            <h3>Overdue</h3>
            {overdue.length === 0 && <div className="org-note">Nothing overdue.</div>}
            {overdue.slice(0, 8).map((it) => (
              <div className="org-row" key={it.id} onClick={() => setForm(it)}>
                <span className="tm">!</span>
                <span><b>{it.title}</b><small>{it.due_at || it.start_time}</small><ProgressBar item={it} /><RecordLinks item={it} /><ActionBar item={it} compact /></span>
              </div>
            ))}
          </div>
          <div className="org-card">
            <h3>Today’s agenda</h3>
            {itemsOnDay(filtered, day).map((it) => (
              <div className="org-row" key={it.id} onClick={() => setForm(it)}>
                <span className="tm">{(it.start_time || it.due_at || '').slice(11, 16) || '—'}</span>
                <span><b>{it.title}</b><small>{KIND_LABEL[it.kind || it.type || '']}</small><ProgressBar item={it} /><RecordLinks item={it} /><ActionBar item={it} compact /></span>
              </div>
            ))}
          </div>
          <div className="org-card">
            <h3>Route</h3>
            <div className="org-note">{route?.note}</div>
            {(route?.stops || []).map((s: any) => (
              <div className="org-row" key={s.id || s.stop_index}>
                <span className="tm">{s.stop_index}</span>
                <span>
                  <b>{s.title}</b>
                  <small>{s.drive_minutes_from_previous} min drive · {s.location_address}</small>
                  <div className="org-abar">
                    {s.location_address && <a href={`https://maps.google.com/?q=${encodeURIComponent(s.location_address)}`} target="_blank" rel="noreferrer">Navigate</a>}
                    {s.phone && <a href={`tel:${s.phone}`}>Call</a>}
                  </div>
                </span>
              </div>
            ))}
            {route?.maps_url && <a className="org-home-btn" href={route.maps_url} target="_blank" rel="noreferrer">Open maps</a>}
          </div>
          {showJobs && timeline && (
            <div className="org-card">
              <h3>Job timeline</h3>
              <div className="org-strip">
                {timeline.strip?.map((s: any) => (
                  <div key={s.key} className={`org-step ${s.state}`}>{s.label}</div>
                ))}
              </div>
              <div className="org-note">Next: {timeline.next_step}</div>
              <ActionBar item={{
                id: jobFilter, job_id: jobFilter, title: timeline.client || 'Job',
                kind: 'install', actions: [
                  { id: 'send_quote', label: 'Send quote', group: 'job', draft: true },
                  { id: 'order_fabric', label: 'Order fabric', group: 'job', draft: true },
                  { id: 'request_deposit', label: 'Request deposit', group: 'job', draft: true },
                  { id: 'book_install', label: 'Book install', group: 'job' },
                ],
              }} />
              {(timeline.blockers || []).map((b: any, i: number) => <div key={i} className="org-warn" style={{ margin: '6px 0' }}>{b.message}</div>)}
            </div>
          )}
          {showJobs && (
          <div className="org-card">
            <h3>Smart follow-ups</h3>
            <div className="org-note">Pre-written nudge. Approve & Send is the owner&apos;s tap — nothing goes out without it.</div>
            {followups.slice(0, 6).map((d, i) => (
              <div className="org-row" key={i}>
                <span className="tm">{d.followup_kind}</span>
                <span>
                  <b>{d.title}</b>
                  <small>{d.reason || d.reminder_draft}</small>
                  <ActionBar item={d} />
                </span>
              </div>
            ))}
          </div>
          )}
          <div className="org-card">
            <h3>Files</h3>
            <div className="org-note">Attach to an email/quote draft or ask {assistant}. No public links.</div>
            {captures.length === 0 && <div className="org-note">No captures yet.</div>}
            {captures.slice(0, 6).map((c) => (
              <div className="org-row" key={c.id}>
                <span className="tm">file</span>
                <span>
                  <b>{c.caption || c.filename}</b>
                  <ActionBar item={{
                    id: c.id, capture_id: c.id, title: c.caption || c.filename, kind: 'material_order', job_id: c.job_id,
                    actions: [
                      { id: 'attach_file', label: 'Attach to email/quote', group: 'file', draft: true },
                      { id: 'ask_max', label: `Ask ${assistant}`, group: 'file', href: `/?product=owner&ask=${encodeURIComponent(c.caption || c.filename || 'this file')}` },
                    ],
                  }} />
                </span>
              </div>
            ))}
          </div>
        </aside>

        <section>
          {(view === 'today' || view === 'board' || view === 'agenda') && (
            <div className="org-card org-suggested-main" data-suggested-tray="1">
              <h3>Suggested</h3>
              <div className="org-note">From mail, WhatsApp, voice notes, and approved estimates. Accept or dismiss — nothing is created silently.</div>
              {suggestions.length === 0 && <div className="org-note">No suggestions waiting.</div>}
              <div className="org-suggested-grid">
                {suggestions.slice(0, 8).map((s) => (
                  <div className="org-row" key={s.id} data-suggestion={s.source}>
                    <span className="tm">{s.source}</span>
                    <span>
                      <b>{s.title}</b>
                      <small>{s.body}</small>
                      <div className="org-abar">
                        <button className="gold" onClick={() => acceptSuggestion(s.id)}>Accept</button>
                        <button onClick={() => dismissSuggestion(s.id)}>Dismiss</button>
                      </div>
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}
          {view === 'today' && (
            <div className="org-kanban" data-today-board>
              {([
                ['overdue', 'Overdue', todayPack.overdue],
                ['today', 'Today', todayPack.today],
                ['upcoming', 'Upcoming', todayPack.upcoming],
              ] as [TodayBucket, string, OrganizerItem[]][]).map(([col, label, rows]) => {
                const shown = filterItems(rows, {
                  jobId: jobFilter || undefined,
                  resourceId: personFilter || undefined,
                  kind: kindFilter || undefined,
                  query: q || undefined,
                  spaceId: spaceFilter || undefined,
                });
                return (
                  <div
                    key={col}
                    className={`org-kanban-col${dragOverCol === col ? ' is-over' : ''}`}
                    data-column={col}
                    onDragOver={(e) => { e.preventDefault(); setDragOverCol(col); }}
                    onDragLeave={() => setDragOverCol((c) => (c === col ? '' : c))}
                    onDrop={(e) => { e.preventDefault(); setDragOverCol(''); const id = e.dataTransfer.getData('text/plain'); if (id) moveCard(id, col); }}
                    onPointerUp={(e) => onColumnPointerUp(e, col)}
                  >
                    <h3>{label} <span>{shown.length}</span></h3>
                    {shown.length === 0 && (
                      <EmptyState
                        title={col === 'overdue' ? 'Caught up' : col === 'today' ? 'A clear day' : 'Nothing queued'}
                        body={col === 'overdue' ? 'No overdue items across any area.' : col === 'today' ? 'Add a note, a photo, or a voice capture when something comes up.' : 'Upcoming work across Workroom, Empire, family and personal will land here.'}
                        icon={col === 'overdue' ? <Sparkles size={18} /> : col === 'today' ? <CalendarDays size={18} /> : <Inbox size={18} />}
                      />
                    )}
                    {shown.map((it) => <OrgCard key={it.id} item={it} column={col} />)}
                  </div>
                );
              })}
            </div>
          )}
          {view === 'board' && (
            <div className="org-kanban" data-status-board>
              {STATUS_COLUMNS.map((col) => {
                const rows = itemsInColumn(filtered, col.id);
                return (
                  <div
                    key={col.id}
                    className={`org-kanban-col${dragOverCol === col.id ? ' is-over' : ''}`}
                    data-column={col.id}
                    onDragOver={(e) => { e.preventDefault(); setDragOverCol(col.id); }}
                    onDragLeave={() => setDragOverCol((c) => (c === col.id ? '' : c))}
                    onDrop={(e) => { e.preventDefault(); setDragOverCol(''); const id = e.dataTransfer.getData('text/plain'); if (id) moveCard(id, col.id); }}
                    onPointerUp={(e) => onColumnPointerUp(e, col.id)}
                  >
                    <h3>{col.label} <span>{rows.length}</span></h3>
                    {rows.length === 0 && (
                      <EmptyState
                        title={col.id === 'done' ? 'Nothing finished yet' : 'Drop a card here'}
                        body={col.id === 'doing' ? 'Drag work you have started. Progress updates from linked tasks.' : 'Cards from every area can live in this column.'}
                        icon={col.id === 'done' ? <Check size={18} /> : <Inbox size={18} />}
                      />
                    )}
                    {rows.map((it) => <OrgCard key={it.id} item={it} column={col.id} />)}
                  </div>
                );
              })}
            </div>
          )}
          {view === 'day' && (
            <div className="org-grid-day" onDoubleClick={(e) => {
              const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
              const start = timeFromOffset(day, e.clientY - rect.top - 8);
              setForm({ title: '', type: 'appointment', start_time: start, end_time: addMinutesIso(start, 60), job_id: showJobs ? jobFilter : '', space_id: spaceFilter || spaces[0]?.slug });
            }}>
              <div className="org-hours" style={{ height: (DAY_END_MIN - DAY_START_MIN) * PX_PER_MIN }}>
                {hours.map((h) => <div key={h} className="org-hour">{h}:00</div>)}
                {itemsOnDay(filtered, day).map((it) => <EventBlock key={it.id} item={it} dayStr={day} />)}
              </div>
            </div>
          )}
          {view === 'week' && (
            <div className="org-week">
              <div className="org-hours">{hours.map((h) => <div key={h} className="org-hour">{h}</div>)}</div>
              {weekDays(anchor).map((d) => {
                const ds = ymd(d);
                return (
                  <div key={ds} className="org-week-col">
                    <div style={{ fontSize: 11, textAlign: 'center', padding: 4, fontWeight: ds === ymd(new Date()) ? 800 : 500 }}>{d.toLocaleDateString('en-US', { weekday: 'short', day: 'numeric' })}</div>
                    {itemsOnDay(filtered, ds).map((it) => <EventBlock key={it.id} item={it} dayStr={ds} />)}
                  </div>
                );
              })}
            </div>
          )}
          {view === 'month' && (
            <div className="org-month">
              {monthCells(anchor).map((c, i) => (
                <div key={i} className={`org-mcell ${c.dateStr === ymd(new Date()) ? 'today' : ''}`}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={async (e) => {
                    const id = e.dataTransfer.getData('text/plain');
                    const it = board.find((x) => x.id === id);
                    if (!it || !c.dateStr) return;
                    const time = (it.start_time || '').slice(11) || '09:00:00';
                    const dur = 60;
                    await moveEvent(id, `${c.dateStr}T${time}`, addMinutesIso(`${c.dateStr}T${time}`, dur));
                  }}
                >
                  <b>{c.date?.getDate() || ''}</b>
                  {c.dateStr && itemsOnDay(filtered, c.dateStr).slice(0, 3).map((it) => (
                    <span key={it.id} draggable className="org-mchip"
                      style={{ background: KIND_COLOR[it.kind || it.type || 'other'] }}
                      onDragStart={(e) => e.dataTransfer.setData('text/plain', it.id)}
                      onClick={() => setForm(it)}>{it.title}</span>
                  ))}
                </div>
              ))}
            </div>
          )}
          {view === 'lanes' && (
            <div>
              {resources.filter((r) => !r.directory).map((r) => (
                <div className="org-lane" key={r.id}>
                  <div className="org-lane-name">{r.name}<div className="org-note">{r.role}</div></div>
                  <div className="org-grid-day" style={{ minHeight: 80 }}>
                    {itemsOnDay(filtered.filter((it) => (it.assigned_resource_ids || []).includes(r.id)), day).map((it) => (
                      <div key={it.id} className="org-row" onClick={() => setForm(it)}><span className="tm">{(it.start_time || '').slice(11, 16)}</span><b>{it.title}</b></div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          )}
          {view === 'agenda' && (
            <div className="org-card">
              {filtered.slice(0, 80).map((it) => (
                <div className="org-row" key={it.id} onClick={() => setForm(it)}>
                  <span className="tm">{(it.start_time || it.due_at || '').slice(5, 16)}</span>
                  <span>
                    <b>{it.title}</b>
                    <small>{it.customer_vendor} · {it.location_address}</small>
                    <ProgressBar item={it} />
                    <RecordLinks item={it} />
                    <ActionBar item={it} />
                  </span>
                </div>
              ))}
            </div>
          )}
          {view === 'mail' && (
            <div className="org-mail org-card">
              <h3>Pending messages</h3>
              <div className="org-note">
                Reading only. {edition.assistant || 'This edition'} sees only {edition.owner || 'this owner'}&apos;s connected mailboxes
                {mailAccounts?.connected?.length ? ` (${mailAccounts.connected.join(', ')})` : ' (none connected yet)'}.
                Draft reply goes to the approval queue — nothing is sent without {edition.owner || 'the owner'}&apos;s tap.
              </div>
              {mailRows.length === 0 && <div className="org-note">Nothing waiting in this area.</div>}
              {mailRows.map((m) => (
                <div className="org-mail-item" key={m.id}>
                  <div className="org-mail-head">
                    <span className="org-wait">{m.waiting || (m.unread ? 'unanswered' : 'waiting')}</span>
                    <span className="tm">{m.account || m.source}</span>
                  </div>
                  <b>{m.subject}</b>
                  <small>
                    {m.from_name || m.from}{m.from_email ? ` · ${m.from_email}` : ''} · {m.space_id || 'area'}
                    {m.job_title ? ` · ${m.job_title}` : ''}
                    {m.person_name ? ` · ${m.person_name}` : ''}
                  </small>
                  {m.preview && <small>{m.preview}</small>}
                  {m.suggested_reply && <pre className="org-mail-reply">{m.suggested_reply}</pre>}
                  <div className="org-abar" onClick={(e) => e.stopPropagation()}>
                    {m.open_href && <a href={m.open_href} target="_blank" rel="noreferrer">Open</a>}
                    <button onClick={() => runMailAction('draft_reply', m)}>Draft reply</button>
                    <button onClick={() => runMailAction('snooze', m)}>Snooze</button>
                    <button onClick={() => runMailAction('todo', m)}>Turn into to-do</button>
                    <button onClick={() => runMailAction('followup', m)}>Turn into follow-up</button>
                  </div>
                </div>
              ))}
              <div className="org-note">{mailNote}</div>
            </div>
          )}
          {view === 'review' && (
            <WeeklyReviewScreen
              items={filtered}
              day={day}
              pack={review}
              spaces={spaces}
              theme={theme}
              onOpenItem={(it) => setForm(it)}
              renderExtra={(it) => (
                <>
                  <WaitingChip item={it} />
                  <MoneyStrip item={it} />
                  <ActionBar item={it} compact />
                </>
              )}
            />
          )}
          {view === 'shutdown' && (
            <EveningShutdown
              items={filtered}
              day={day}
              pack={shutdown}
              spaces={spaces}
              theme={theme}
              owner={edition.owner}
              assistant={assistant}
              onComplete={completeShutdown}
              onOpenItem={(it) => setForm(it)}
            />
          )}
          <div className="org-note">{meta?.google_calendar?.note} {meta?.outbound_policy} {usage ? `Today ${edition.assistant || 'this edition'}: ${usage.used?.items || 0}/${usage.caps?.items || 0} items.` : ''}</div>
          {icsNote && <div className="org-note">{icsNote}</div>}
        </section>
      </div>

      {drafts.length > 0 && (
        <div className="org-modal" onClick={() => setDrafts([])}>
          <div className="org-sheet" onClick={(e) => e.stopPropagation()}>
            <h3>Confirm drafts</h3>
            <p className="org-note">Nothing is on the calendar yet. Nothing is sent to a customer.</p>
            {drafts.map((d, i) => (
              <div key={i} className="org-row"><span className="tm">{d.kind}</span><span><b>{d.title}</b><small>{d.start_time || d.due_at} · job {d.job_title || d.job_id || '—'}</small></span></div>
            ))}
            <div className="org-actions">
              <button className="org-btn-gold" onClick={() => submitQuick(quick || drafts[0]?.original_text || drafts[0]?.title, true)}>Save drafts</button>
              <button onClick={() => setDrafts([])}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {form && (
        <div className="org-modal" onClick={() => setForm(null)}>
          <div className="org-sheet" onClick={(e) => e.stopPropagation()}>
            <h3>{form.id ? 'Item' : 'New item'}</h3>
            <label>Title</label>
            <input value={form.title || ''} onChange={(e) => setForm({ ...form, title: e.target.value })} />
            <label>Type</label>
            <select value={form.type || form.kind || 'appointment'} onChange={(e) => setForm({ ...form, type: e.target.value, kind: e.target.value })}>
              {KINDS.map((k) => <option key={k} value={k}>{KIND_LABEL[k]}</option>)}
            </select>
            <label>Area</label>
            <select value={form.space_id || spaceFilter || spaces[0]?.slug || ''} onChange={(e) => setForm({ ...form, space_id: e.target.value })}>
              {spaces.map((s: any) => <option key={s.slug} value={s.slug}>{s.label}</option>)}
            </select>
            {showJobs && (
              <>
                <label>Job</label>
                <select value={form.job_id || ''} onChange={(e) => setForm({ ...form, job_id: e.target.value })}>
                  <option value="">—</option>
                  {jobs.map((j) => <option key={j.id} value={j.id}>{j.client_name || j.title}</option>)}
                </select>
              </>
            )}
            <label>Person</label>
            <select value={(form.assigned_resource_ids || [])[0] || ''} onChange={(e) => setForm({ ...form, assigned_resource_ids: e.target.value ? [e.target.value] : [] })}>
              <option value="">—</option>
              {resources.filter((r) => !String(r.id).startsWith('cust-')).map((r) => <option key={r.id} value={r.id}>{r.name} · {r.role}</option>)}
            </select>
            <label>Start</label>
            <input value={(form.start_time || '').slice(0, 16)} type="datetime-local" onChange={(e) => setForm({ ...form, start_time: e.target.value.length === 16 ? `${e.target.value}:00` : e.target.value })} />
            <label>End</label>
            <input value={(form.end_time || '').slice(0, 16)} type="datetime-local" onChange={(e) => setForm({ ...form, end_time: e.target.value.length === 16 ? `${e.target.value}:00` : e.target.value })} />
            <label>Due</label>
            <input value={(form.due_at || '').slice(0, 16)} type="datetime-local" onChange={(e) => setForm({ ...form, due_at: e.target.value.length === 16 ? `${e.target.value}:00` : e.target.value })} />
            <label>Remind Max at</label>
            <input value={(form.reminder_at || form.due_at || '').slice(0, 16)} type="datetime-local" onChange={(e) => setForm({ ...form, reminder_at: e.target.value.length === 16 ? `${e.target.value}:00` : e.target.value })} />
            <label>Waiting on</label>
            <input value={form.waiting_on || ''} placeholder="Who" onChange={(e) => setForm({ ...form, waiting_on: e.target.value })} />
            <label>Nudge after (days)</label>
            <input type="number" min={1} max={90} value={form.nudge_after_days || 3} onChange={(e) => setForm({ ...form, nudge_after_days: Number(e.target.value || 3) })} />
            {form.id && form.waiting_on && (
              <button onClick={() => saveWaiting(form)}>Save waiting-on (draft nudge only)</button>
            )}
            <label>Repeat</label>
            <select value={form.recurrence_freq || ''} onChange={async (e) => {
              const freq = e.target.value;
              setForm({ ...form, recurrence_freq: freq });
              if (form.id && freq) {
                await fetch(`${API}/organizer/items/${encodeURIComponent(form.id)}/recurrence`, {
                  method: 'POST', headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ freq }),
                });
                setToast('Recurring copy will spawn when due. Nothing sent.');
              }
            }}>
              <option value="">One-time</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
            <RecordLinks item={form} />
            <ProgressBar item={form} />
            <MoneyStrip item={form} />
            <WaitingChip item={form} />
            <label>Address</label>
            <input value={form.location_address || ''} onChange={(e) => setForm({ ...form, location_address: e.target.value })} />
            <label>Phone</label>
            <input value={form.phone || ''} onChange={(e) => setForm({ ...form, phone: e.target.value })} />
            <label>Notes</label>
            <textarea rows={3} value={form.notes || ''} onChange={(e) => setForm({ ...form, notes: e.target.value })} />
            <ActionBar item={form} />
            <div className="org-note">Text / email / quote / deposit / crew notes are drafts. Approve & Send is the only outbound tap.</div>
            <div className="org-actions">
              <button className="org-btn-gold" onClick={() => saveEvent(form)}>{form.read_only ? 'Close' : 'Save'}</button>
              <button onClick={() => setForm(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {toast && (
        <div className="org-toast" role="status" onClick={() => setToast('')}>{toast}</div>
      )}

      {crewPrompt && (
        <div className="org-modal" onClick={() => setCrewPrompt(null)}>
          <div className="org-sheet" onClick={(e) => e.stopPropagation()}>
            <h3>Tell the crew?</h3>
            <p className="org-note">The calendar already moved. This only prepares a message. Approve & Send is still required.</p>
            <div className="org-actions">
              <button className="org-btn-gold" onClick={() => runAction('notify_crew', crewPrompt)}>Draft crew text</button>
              <button onClick={() => setCrewPrompt(null)}>Skip</button>
            </div>
          </div>
        </div>
      )}

      {spaceEdit && (
        <div className="org-modal" onClick={() => setSpaceEdit(null)}>
          <div className="org-sheet" onClick={(e) => e.stopPropagation()}>
            <h3>Area look</h3>
            <p className="org-note">Icon and accent color for this life or business area. Isolated to {edition.label || 'this edition'}.</p>
            <label>Icon</label>
            <input value={spaceEdit.icon || ''} onChange={(e) => setSpaceEdit({ ...spaceEdit, icon: e.target.value })} />
            <label>Accent color</label>
            <input value={spaceEdit.accent_color || ''} onChange={(e) => setSpaceEdit({ ...spaceEdit, accent_color: e.target.value })} />
            <label>Label</label>
            <input value={spaceEdit.label || ''} onChange={(e) => setSpaceEdit({ ...spaceEdit, label: e.target.value })} />
            <div className="org-actions">
              <button className="org-btn-gold" onClick={async () => {
                await fetch(`${API}/organizer/spaces/${encodeURIComponent(spaceEdit.slug)}`, {
                  method: 'PATCH', headers: { 'Content-Type': 'application/json' },
                  body: JSON.stringify({ icon: spaceEdit.icon, accent_color: spaceEdit.accent_color, label: spaceEdit.label }),
                });
                setSpaceEdit(null);
                await load();
              }}>Save area</button>
              <button onClick={() => setSpaceEdit(null)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {planOpen && (
        <div className="org-modal" onClick={() => setPlanOpen(false)}>
          <div className="org-sheet" data-plan-sheet="1" onClick={(e) => e.stopPropagation()}>
            <h3>Plan my day</h3>
            <p className="org-note">{assistant} proposes time blocks for installs, orders, and follow-ups. Approve to save. Nothing is sent.</p>
            <div className="org-note">{plan?.headline}</div>
            {(plan?.proposed_order || []).map((s: any) => (
              <div className="org-row" key={s.id || s.title}>
                <span className="tm">{(s.suggested_start || '').slice(11, 16)}</span>
                <span><b>{s.title}</b><small>{s.kind || s.type} · {s.location_address || s.space_id || ''}</small></span>
              </div>
            ))}
            {!(plan?.proposed_order || []).length && <EmptyState title="Nothing to place" body="Add installs, orders, or follow-ups and Max will propose blocks." icon={<Clock size={18} />} />}
            <div className="org-actions">
              <button className="org-btn-gold" disabled={plan?.approved} onClick={approvePlan}>{plan?.approved ? 'Already approved' : 'Approve & save blocks'}</button>
              <button onClick={() => setPlanOpen(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      {searchOpen && q.trim().length >= 2 && (
        <div className="org-modal" onClick={() => setSearchOpen(false)}>
          <div className="org-sheet" data-search-hits="1" onClick={(e) => e.stopPropagation()}>
            <h3><Search size={16} /> Search</h3>
            <p className="org-note">Items, jobs, clients, and estimates in this edition only.</p>
            {(['items', 'jobs', 'clients', 'estimates'] as const).map((bucket) => (
              <div key={bucket}>
                <h4 style={{ textTransform: 'uppercase', fontSize: 11, color: 'var(--org-mut)' }}>{bucket}</h4>
                {!(searchHits?.[bucket] || []).length && <div className="org-note">No {bucket}.</div>}
                {(searchHits?.[bucket] || []).map((hit: any) => (
                  <div className="org-row" key={`${bucket}-${hit.id}`}>
                    <span className="tm">{bucket.slice(0, 3)}</span>
                    <span>
                      <b>{hit.title || hit.name || hit.quote_number || hit.id}</b>
                      <small>{hit.status || hit.phone || hit.client_name || ''}</small>
                    </span>
                  </div>
                ))}
              </div>
            ))}
            <div className="org-actions"><button onClick={() => setSearchOpen(false)}>Close</button></div>
          </div>
        </div>
      )}

      {cartPreview && (
        <div className="org-modal" onClick={() => setCartPreview(null)}>
          <div className="org-sheet" data-supplier-cart="1" onClick={(e) => e.stopPropagation()}>
            <h3>Supplier cart</h3>
            <p className="org-note">Prepared only. Never checks out or pays.</p>
            {(cartPreview.lines || []).map((ln: any, i: number) => (
              <div className="org-row" key={i}><span className="tm">{ln.qty || 1}</span><span><b>{ln.title}</b><small>{ln.note}</small></span></div>
            ))}
            <div className="org-note">checked_out={String(!!cartPreview.checked_out)} · paid={String(!!cartPreview.paid)}</div>
            <div className="org-actions"><button onClick={() => setCartPreview(null)}>Close</button></div>
          </div>
        </div>
      )}

      {nudgeDraft && (
        <div className="org-modal" onClick={() => setNudgeDraft(null)}>
          <div className="org-sheet" data-nudge-draft="1" onClick={(e) => e.stopPropagation()}>
            <h3>Draft for review</h3>
            <p className="org-note">Nothing was sent. Approve & Send is still required for anything outbound.</p>
            <pre className="org-mail-reply">{nudgeDraft.body || nudgeDraft.reminder_draft || JSON.stringify(nudgeDraft, null, 2)}</pre>
            <div className="org-actions"><button onClick={() => setNudgeDraft(null)}>Close</button></div>
          </div>
        </div>
      )}

      {peopleOpen && (
        <div className="org-modal" onClick={() => setPeopleOpen(false)}>
          <div className="org-sheet" onClick={(e) => e.stopPropagation()}>
            <h3>People</h3>
            <p className="org-note">Anyone this edition needs: family, friends, crew, doctors, teachers, partners. Isolated to {edition.label || 'this edition'}.</p>
            {resources.filter((r) => !r.directory).map((r) => (
              <div className="org-row" key={r.id}><span className="tm">{r.role}</span><span><b>{r.name}</b><small>{r.phone}</small></span></div>
            ))}
            <label>Name</label><input value={personForm.name} onChange={(e) => setPersonForm({ ...personForm, name: e.target.value })} />
            <label>Role</label>
            <select value={personForm.role} onChange={(e) => setPersonForm({ ...personForm, role: e.target.value })}>
              {(meta?.roles || ['family', 'friend', 'partner', 'doctor', 'teacher', 'coach', 'teammate', 'installer', 'other']).map((r: string) => <option key={r}>{r}</option>)}
            </select>
            <label>Phone</label><input value={personForm.phone} onChange={(e) => setPersonForm({ ...personForm, phone: e.target.value })} />
            <div className="org-actions">
              <button className="org-btn-gold" onClick={addPerson}>Add person</button>
              <button onClick={() => setPeopleOpen(false)}>Close</button>
            </div>
          </div>
        </div>
      )}
      {workOrderSheet && (
        <div className="org-modal" role="dialog" aria-label="Work orders">
          <div className="org-sheet" style={{ maxWidth: 1100, width: 'min(1100px, 96vw)', maxHeight: '90vh', overflow: 'auto' }}>
            <SprintMRail onClose={() => setWorkOrderSheet(false)} jobId={jobFilter} />
          </div>
        </div>
      )}
    </div>
  );
}
