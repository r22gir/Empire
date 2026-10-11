'use client';

import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { API } from '../../../lib/api';
import {
  addMinutesIso, DAY_END_MIN, DAY_START_MIN, eventLayout, filterItems, filterPendingMail,
  groupActions, itemsOnDay, isOrganizerCommand, KIND_COLOR, KIND_LABEL, monthCells, overdueItems,
  PX_PER_MIN, shouldOfferCrewDraft, showsWorkroomJobs, timeFromOffset, weekDays, ymd,
  type OrganizerAction, type OrganizerItem,
} from '../../../lib/organizer-logic';
import './organizer.css';

type View = 'day' | 'week' | 'month' | 'lanes' | 'agenda' | 'mail';

const KINDS = Object.keys(KIND_LABEL);

function initialJob(): string {
  if (typeof window === 'undefined') return '';
  return new URLSearchParams(window.location.search).get('job') || '';
}

export default function WorkroomOrganizer({ business, initialJobId }: { business?: string; initialJobId?: string }) {
  const [view, setView] = useState<View>('day');
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
  const dragRef = useRef<{ id: string; mode: 'move' | 'resize'; startY: number; origStart: string; origEnd: string } | null>(null);

  const day = ymd(anchor);
  const edition = meta?.edition || {};
  const spaces = edition.spaces || meta?.spaces || [];
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
  const mailRows = useMemo(
    () => filterPendingMail(pendingMail, { spaceId: spaceFilter || undefined, query: q || undefined }),
    [pendingMail, spaceFilter, q],
  );

  const load = useCallback(async () => {
    const from = new Date(anchor); from.setDate(from.getDate() - 31);
    const to = new Date(anchor); to.setDate(to.getDate() + 40);
    const spaceQs = spaceFilter ? `&space_id=${encodeURIComponent(spaceFilter)}` : '';
    const qs = `start_date=${ymd(from)}&end_date=${ymd(to)}${spaceQs}`;
    const [b, r, p, rt, m, caps, u, pm] = await Promise.all([
      fetch(`${API}/organizer/board?${qs}`).then((x) => x.json()).catch(() => ({ items: [], overdue: [] })),
      fetch(`${API}/organizer/resources`).then((x) => x.json()).catch(() => ({ resources: [] })),
      fetch(`${API}/organizer/day-plan?plan_date=${day}`).then((x) => x.json()).catch(() => null),
      fetch(`${API}/organizer/route?plan_date=${day}`).then((x) => x.json()).catch(() => null),
      fetch(`${API}/organizer/meta`).then((x) => x.json()).catch(() => null),
      fetch(`${API}/organizer/captures`).then((x) => x.json()).catch(() => ({ captures: [] })),
      fetch(`${API}/organizer/usage`).then((x) => x.json()).catch(() => null),
      fetch(`${API}/organizer/pending-mail`).then((x) => x.json()).catch(() => ({ items: [] })),
    ]);
    const allowsJobs = !!(m?.edition?.allows_workroom_jobs);
    const jobSpace = showsWorkroomJobs(m?.edition, spaceFilter);
    const [j, f] = await Promise.all([
      jobSpace ? fetch(`${API}/jobs?limit=200`).then((x) => x.json()).catch(() => ({ jobs: [] })) : Promise.resolve({ jobs: [] }),
      allowsJobs ? fetch(`${API}/organizer/follow-ups`).then((x) => x.json()).catch(() => ({ drafts: [] })) : Promise.resolve({ drafts: [] }),
    ]);
    setBoard(b.items || []);
    setOverdue(b.overdue || overdueItems(b.items || [], `${day}T00:00:00`));
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
    if (jobFilter && jobSpace) {
      const tl = await fetch(`${API}/organizer/jobs/${jobFilter}/timeline`).then((x) => x.ok ? x.json() : null).catch(() => null);
      setTimeline(tl);
    } else setTimeline(null);
  }, [anchor, day, jobFilter, spaceFilter]);

  useEffect(() => { load(); }, [load]);

  async function saveEvent(payload: any, confirm = false) {
    const body = { ...payload, confirm_conflicts: confirm, space_id: payload.space_id || spaceFilter || undefined };
    const isNew = !payload.id || String(payload.id).startsWith('new');
    const url = isNew ? `${API}/schedule/events` : `${API}/schedule/events/${payload.id}`;
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
    setConflict(null);
    setForm(null);
    await load();
    return res.json();
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
    if (act?.href && ['navigate', 'call', 'ask_max'].includes(action)) {
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
    if (data.href && action !== 'attach_file') window.open(data.href, action === 'call' ? '_self' : '_blank');
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

  async function submitQuick(text: string, confirm = false) {
    if (isOrganizerCommand(text)) {
      await runCommand(text, confirm);
      return;
    }
    const res = await fetch(`${API}/organizer/quick-add`, {
      method: 'POST', headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ text, confirm }),
    });
    const data = await res.json();
    if (!confirm) setDrafts(data.drafts || []);
    else { setDrafts([]); setQuick(''); await load(); }
  }

  function ActionBar({ item, compact }: { item: Partial<OrganizerItem>; compact?: boolean }) {
    const groups = groupActions(item.actions);
    const order = compact ? ['stop', 'job', 'followup'] : ['stop', 'job', 'followup', 'file', 'move'];
    const flat = order.flatMap((g) => groups[g] || []);
    if (!flat.length) return null;
    return (
      <div className="org-abar" onClick={(e) => e.stopPropagation()}>
        {flat.map((a: OrganizerAction) => (
          a.href && ['navigate', 'call', 'ask_max'].includes(a.id) ? (
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

  function startVoice() {
    const SR: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) { setQuick((t) => t || ''); alert('Voice typing is not available on this browser. Type instead.'); return; }
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
    await fetch(`${API}/organizer/day-plan/approve?plan_date=${day}`, { method: 'POST' });
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
    <div className="org-root" data-organizer>
      <div className="org-top">
        <div className="org-title">
          Organizer
          {edition.label && <span className="org-ed">{edition.label}</span>}
          <span>all life &amp; business areas · nothing sent without {edition.owner || 'the owner'}&apos;s tap</span>
        </div>
        <div className="org-spaces" role="tablist" aria-label="Areas">
          <button className={!spaceFilter ? 'on' : ''} onClick={() => setSpaceFilter('')}>All areas</button>
          {spaces.map((s: any) => (
            <button key={s.slug} className={spaceFilter === s.slug ? 'on' : ''} onClick={() => setSpaceFilter(s.slug)}>
              {s.label}
            </button>
          ))}
        </div>
        <div className="org-toolbar">
          {(['day', 'week', 'month', 'lanes', 'agenda', 'mail'] as View[]).map((v) => (
            <button key={v} className={view === v ? 'on' : ''} onClick={() => setView(v)}>{v === 'mail' ? 'messages' : v}</button>
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
          <input placeholder="Search" value={q} onChange={(e) => setQ(e.target.value)} />
          <button className="org-btn-gold" onClick={() => setForm({
            title: '', type: 'appointment', start_time: `${day}T10:00:00`, end_time: `${day}T11:00:00`,
            job_id: showJobs ? jobFilter : '', assigned_resource_ids: personFilter ? [personFilter] : [],
            space_id: spaceFilter || (spaces[0]?.slug),
          })}>+ Add</button>
          <button onClick={() => setPeopleOpen(true)}>People</button>
          <button onClick={exportIcs}>ICS</button>
        </div>
        <div className="org-qa" style={{ marginTop: 8 }}>
          <input
            value={quick}
            onChange={(e) => setQuick(e.target.value)}
            placeholder="Quick-add or command: move Marley's install to Friday and tell the crew"
            onKeyDown={(e) => { if (e.key === 'Enter' && quick.trim()) submitQuick(quick.trim()); }}
          />
          <button onClick={() => quick.trim() && submitQuick(quick.trim())}>Draft</button>
          <button onClick={startVoice}>{listening ? 'Listening…' : 'Voice'}</button>
        </div>
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
          <div className="org-card">
            <h3>{assistant}’s proposed day</h3>
            <div style={{ fontSize: 12 }}>{plan?.headline || 'Loading…'}</div>
            {(plan?.proposed_order || []).slice(0, 6).map((s: any) => (
              <div className="org-row" key={s.id || s.title}><span className="tm">{(s.suggested_start || '').slice(11, 16)}</span><span><b>{s.title}</b><small>{s.location_address}</small></span></div>
            ))}
            <button className="org-btn-gold" style={{ marginTop: 8 }} disabled={plan?.approved} onClick={approvePlan}>
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
                <span><b>{it.title}</b><small>{it.due_at || it.start_time}</small><ActionBar item={it} compact /></span>
              </div>
            ))}
          </div>
          <div className="org-card">
            <h3>Today’s agenda</h3>
            {itemsOnDay(filtered, day).map((it) => (
              <div className="org-row" key={it.id} onClick={() => setForm(it)}>
                <span className="tm">{(it.start_time || it.due_at || '').slice(11, 16) || '—'}</span>
                <span><b>{it.title}</b><small>{KIND_LABEL[it.kind || it.type || '']}</small><ActionBar item={it} compact /></span>
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
    </div>
  );
}
