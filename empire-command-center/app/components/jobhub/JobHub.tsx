'use client';
/**
 * Job hub: everything about one job on one page (design system v3).
 * Client · Quotes · Invoices · Payments · Drawings · Photos · Documents · Tasks · Calendar · Messages · Notes · Phase history.
 * Open with /?product=workroom&section=jobhub&job=<jobId> (or &quote=<quoteId> when no job exists yet).
 * Reads existing job/quote/doc stores. The only write is PATCH /jobs/{id}/stage.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Search, ArrowRight, FileText, Receipt, PenTool, Image as ImageIcon, MessageSquare, StickyNote, History, Briefcase, Phone, Mail, MessageCircle, X, Users, CheckSquare, Calendar, DollarSign, LayoutGrid } from 'lucide-react';
import { API } from '../../lib/api';
import JobHeader from '../docs/JobHeader';
import DocCard, { thumbUrl, toRef } from '../docs/DocCard';
import { useQuoteDocs } from '../docs/DocsTab';
import { openDocViewer } from '../docs/viewerBus';
import { docViewerTarget, invoicePdfSrc, quotePdfSrc, visualsFromJob, visualsToGroups } from '../../lib/docs-hub/jobVisuals';
import { Empty } from '../../v3/ui';
import { jobHubHref } from './href';
import PhaseStepper from '../../studio/PhaseStepper';
import PhaseToast from '../../studio/PhaseToast';
import { formatInches } from '../../lib/formatInches';
import {
  businessLabel,
  jobContacts,
  movedToast,
  phaseHistoryFromEvents,
  stageLabel,
  stagePatchRequest,
} from '../../studio/jobStages';
import './jobhub.css';

type Any = Record<string, any>;
const num = (n: any) => { const v = Number(n); return Number.isFinite(v) ? v : 0; };
const money = (n: any) => `$${num(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const day = (s?: string | null) => { if (!s) return ''; const d = new Date(String(s).includes('T') ? String(s) : String(s).replace(' ', 'T')); return isNaN(d.getTime()) ? String(s).slice(0, 10) : d.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }); };
const label = (s?: string | null) => (s || '').replace(/_/g, ' ').replace(/^\w/, c => c.toUpperCase());
const pillTone = (s?: string | null) => { const v = (s || '').toLowerCase(); return ['paid', 'accepted', 'approved', 'completed', 'won'].includes(v) ? 'ok' : ['overdue', 'cancelled', 'canceled', 'declined', 'void'].includes(v) ? 'bad' : ['partial', 'sent', 'viewed', 'pending'].includes(v) ? 'warn' : ''; };

async function getJson(url: string): Promise<any | null> {
  try { const r = await fetch(url, { cache: 'no-store' }); return r.ok ? await r.json() : null; } catch { return null; }
}

function readTarget(): { job: string | null; quote: string | null } {
  if (typeof window === 'undefined') return { job: null, quote: null };
  const sp = new URLSearchParams(window.location.search);
  return { job: sp.get('job'), quote: sp.get('quote') };
}

function measureText(m: Any): string {
  if (!m) return '';
  if (typeof m === 'string' || typeof m === 'number') return formatInches(m);
  const parts = ['width', 'height', 'length', 'finished_width', 'finished_length', 'w', 'h']
    .map((k) => m[k] != null && m[k] !== '' ? `${k[0].toUpperCase()}: ${formatInches(m[k])}` : '')
    .filter(Boolean);
  return parts.join(' · ');
}

interface HubData {
  job: Any | null;
  quote: Any | null;
  quotes: Any[];
  invoices: Any[];
  payments: Any[];
  events: Any[];
  customer: Any | null;
  todos: Any[];
  calendar: Any[];
  documents: Any[];
  items: Any[];
  missing?: string;
}

function useHub(target: { job: string | null; quote: string | null }, reload: number) {
  const [data, setData] = useState<HubData | null>(null);
  useEffect(() => {
    if (!target.job && !target.quote) { setData(null); return; }
    let dead = false;
    (async () => {
      setData(null);
      let job: Any | null = null; let quote: Any | null = null;
      const jobRes = target.job ? await getJson(`${API}/jobs/${encodeURIComponent(target.job)}`) : null;
      if (target.job) job = jobRes?.job ?? (jobRes?.id ? jobRes : null);
      const qid = job?.quote_id || target.quote;
      if (qid) { const q = await getJson(`${API}/quotes-v2/${encodeURIComponent(qid)}`); quote = q?.quote ?? (q?.id ? q : null); }
      const allQuotes: Any[] = (await getJson(`${API}/quotes-v2?limit=500`))?.quotes ?? [];
      if (!job) {
        const jid = quote?.job_id;
        if (jid) job = (await getJson(`${API}/jobs/${encodeURIComponent(jid)}`))?.job ?? null;
        if (!job && quote) { const js: Any[] = (await getJson(`${API}/jobs?limit=500`))?.jobs ?? []; job = js.find(j => j.quote_id === quote!.id) ?? null; }
      }
      const cid = job?.customer_id || quote?.customer_id || null;
      const [byJob, byCust, timeline, cust, org] = await Promise.all([
        job ? getJson(`${API}/invoices?job_id=${encodeURIComponent(job.id)}&limit=100`) : null,
        cid ? getJson(`${API}/invoices?customer_id=${encodeURIComponent(cid)}&limit=100`) : null,
        job ? getJson(`${API}/jobs/${encodeURIComponent(job.id)}/timeline`) : null,
        cid ? getJson(`${API}/crm/customers/${encodeURIComponent(cid)}`) : null,
        job ? getJson(`${API}/organizer/jobs/${encodeURIComponent(job.id)}/todos`) : null,
      ]);
      const inv = new Map<string, Any>();
      [...(byJob?.invoices ?? []), ...(byCust?.invoices ?? []), ...(job?.invoices ?? [])].forEach((i: Any) => inv.set(i.id, i));
      const quotes = allQuotes.filter(q => (cid && q.customer_id === cid) || (quote && q.id === quote.id) || (job && q.job_id === job.id))
        .sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')));
      const events = timeline?.events ?? job?.events ?? [];
      const todos = org?.todos ?? org?.items ?? [];
      const calendar = [...(org?.events ?? []), ...(org?.job_dates ?? [])];
      if (dead) return;
      setData({
        job, quote, quotes,
        invoices: [...inv.values()].sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || ''))),
        payments: job?.payments ?? [],
        events,
        customer: cust?.customer ?? null,
        todos,
        calendar,
        documents: job?.documents ?? [],
        items: job?.items ?? [],
        missing: !job && !quote ? 'not found' : undefined,
      });
    })();
    return () => { dead = true; };
  }, [target.job, target.quote, reload]);
  return data;
}

/* ------------------------------------------------------------ picker */

function JobPicker({ onPick }: { onPick: (t: { job?: string; quote?: string }) => void }) {
  const [q, setQ] = useState('');
  const [rows, setRows] = useState<Any[] | null>(null);
  useEffect(() => {
    let dead = false;
    const t = setTimeout(async () => {
      const d = q.trim().length >= 2 ? await getJson(`${API}/jobs/search?q=${encodeURIComponent(q.trim())}`) : await getJson(`${API}/jobs?limit=60`);
      const testy = (j: Any) => /^MOCK-|TEST RESIDUE|^E2E\b|^Test$|Pipeline Test/i.test(String(j.client_name || j.customer_name || ''));
      if (!dead) setRows((d?.jobs ?? []).filter((j: Any) => q.trim().length >= 2 ? !/^MOCK-/i.test(String(j.client_name || '')) : !testy(j)));
    }, q ? 250 : 0);
    return () => { dead = true; clearTimeout(t); };
  }, [q]);
  return (
    <div className="v3 jh">
      <div className="v3-ph"><h1 className="v3-disp">Job hub</h1><span className="v3-kick">Pick a job</span></div>
      <div className="jh-search"><Search size={15} /><input className="v3-input" value={q} onChange={e => setQ(e.target.value)} placeholder="Search client, job number, quote, fabric…" aria-label="Search jobs" autoFocus /></div>
      {rows === null ? <div className="jh-mut">Loading jobs…</div> : rows.length === 0 ? <Empty title="No jobs found">Try a client name or a job number.</Empty> : (
        <div className="jh-list">
          {rows.map(j => (
            <a key={j.id} href={jobHubHref({ job: j.id })} className="v3-card jh-row" onClick={e => { e.preventDefault(); onPick({ job: j.id }); }}>
              <Briefcase size={15} />
              <span className="b"><b>{j.client_name || j.customer_name || j.title || 'Job'}</b><span>{[j.job_number, label(j.business_unit), j.title].filter(Boolean).join(' · ')}</span></span>
              <span className={`v3-pill ${pillTone(j.status)}`}>{label(j.pipeline_stage || j.status)}</span>
              <ArrowRight size={14} />
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

/* --------------------------------------------------------------- hub */

function Sec({ id, icon, title, count, children }: { id: string; icon: ReactNode; title: string; count?: number; children: ReactNode }) {
  return (
    <section className="v3-glass jh-sec" id={`jh-${id}`} aria-labelledby={`jh-h-${id}`}>
      <div className="v3-ph"><span className="jh-ico">{icon}</span><h2 className="v3-disp" id={`jh-h-${id}`}>{title}</h2>{count !== undefined && <span className="v3-cnt">{count}</span>}</div>
      {children}
    </section>
  );
}

export default function JobHub({ initial }: { initial?: { job?: string | null; quote?: string | null } }) {
  const [target, setTarget] = useState<{ job: string | null; quote: string | null }>(() => ({ job: initial?.job ?? null, quote: initial?.quote ?? null }));
  const [reload, setReload] = useState(0);
  const [moving, setMoving] = useState(false);
  const [toast, setToast] = useState<string | null>(null);
  useEffect(() => { if (!initial?.job && !initial?.quote) { const t = readTarget(); if (t.job || t.quote) setTarget(t); } }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const pick = useCallback((t: { job?: string | null; quote?: string | null }) => {
    const next = { job: t.job ?? null, quote: t.quote ?? null };
    setTarget(next);
    try { window.history.pushState(null, '', jobHubHref(next)); } catch { /* */ }
  }, []);
  const d = useHub(target, reload);
  const quoteId = d?.quote?.id || d?.job?.quote_id || target.quote || null;
  const jobKey = d?.job?.job_number || d?.job?.id || target.job || null;
  const docs = useQuoteDocs(quoteId, jobKey);
  const [related, setRelated] = useState<Any | null>(null);
  useEffect(() => {
    const id = d?.job?.id || target.job;
    if (!id) { setRelated(null); return; }
    let dead = false;
    getJson(`${API}/jobs/${encodeURIComponent(id)}/related`).then((r) => { if (!dead) setRelated(r); });
    return () => { dead = true; };
  }, [d?.job?.id, target.job, reload]);
  const visualGroups = visualsToGroups(visualsFromJob(d?.job));
  const groups = [...(docs.data?.groups ?? [])];
  const seenKeys = new Set(groups.map(g => g.key));
  for (const g of visualGroups) {
    if (!seenKeys.has(g.key) && !groups.some(x => x.final.src && x.final.src === g.final.src)) {
      groups.push(g); seenKeys.add(g.key);
    }
  }
  if (related?.groups) {
    for (const g of related.groups) {
      const src = g?.final?.src;
      if (!src || groups.some(x => x.final.src === src || x.final.id === g.final.id)) continue;
      groups.push({ key: `${g.type}|related|${src}`, type: g.type, title: g.title, final: { id: '', type: g.type, kind: g.final.kind || 'pdf', title: g.title, filename: g.title, version: 'original', versionRank: 1, isFinal: true, groupKey: `${g.type}|related|${src}`, source: g.source || 'related', location: src, modified: '', src }, older: [] });
    }
  }
  const drawings = groups.filter(g => g.type === 'drawing');
  const photos = groups.filter(g => g.type === 'photo').flatMap(g => [g.final, ...g.older]);
  const otherDocs = groups.filter(g => g.type !== 'drawing' && g.type !== 'photo');
  const quotes = (d?.quotes?.length ? d.quotes : related?.quotes) || [];
  const invoices = (d?.invoices?.length ? d.invoices : related?.invoices) || [];

  const timeline = useMemo(() => {
    if (!d) return [];
    const t: { at: string; what: string; detail?: string }[] = [];
    d.events.forEach(e => t.push({ at: e.created_at, what: e.summary || label(e.event_type), detail: e.actor && e.actor !== 'system' ? `by ${e.actor}` : undefined }));
    d.quotes.forEach(q => {
      if (q.created_at) t.push({ at: q.created_at, what: `Quote ${q.quote_number || ''} created`, detail: money(q.total) });
      if (q.sent_at) t.push({ at: q.sent_at, what: `Quote ${q.quote_number || ''} sent` });
      if (q.accepted_at) t.push({ at: q.accepted_at, what: `Quote ${q.quote_number || ''} accepted` });
    });
    d.invoices.forEach(i => { if (i.created_at) t.push({ at: i.created_at, what: `Invoice ${i.invoice_number || ''} created`, detail: money(i.total) }); if (i.paid_at) t.push({ at: i.paid_at, what: `Invoice ${i.invoice_number || ''} paid` }); });
    const j = d.job || {};
    ([['site_visit_date', 'Site visit'], ['approved_date', 'Approved'], ['production_start', 'Production started'], ['install_date', 'Install'], ['completed_date', 'Completed']] as const)
      .forEach(([k, l]) => { if (j[k]) t.push({ at: j[k], what: l }); });
    return t.filter(x => x.at).sort((a, b) => String(b.at).localeCompare(String(a.at)));
  }, [d]);

  const phases = useMemo(() => phaseHistoryFromEvents(d?.events), [d]);

  const movePhase = async (stage: string) => {
    const job = d?.job;
    if (!job?.id || moving) return;
    const from = job.canonical_stage || job.pipeline_stage || job.status;
    setMoving(true);
    try {
      const req = stagePatchRequest(String(job.id), stage);
      const r = await fetch(`${API}${req.path}`, { method: req.method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(req.body) });
      if (!r.ok) throw new Error('move failed');
      setToast(movedToast(job.title || job.job_number || 'Job', from, stage));
      setReload((n) => n + 1);
    } catch {
      setToast('Could not move the phase. Try again.');
    } finally {
      setMoving(false);
      setTimeout(() => setToast(null), 4000);
    }
  };

  if (!target.job && !target.quote) return <JobPicker onPick={pick} />;
  const job = d?.job; const quote = d?.quote;
  const notes = d ? [
    job?.notes && { src: `Job ${job.job_number || ''}`.trim(), text: job.notes },
    quote?.notes && { src: `Quote ${quote.quote_number || ''}`.trim(), text: quote.notes },
    quote?.project_description && { src: 'Project', text: quote.project_description },
    d.customer?.notes && { src: 'Customer', text: d.customer.notes },
  ].filter(Boolean) as { src: string; text: string }[] : [];
  const msgEvents = timeline.filter(t => /email|sms|whatsapp|message|call|sent/i.test(t.what));
  const phone = quote?.customer_phone || job?.client_phone || d?.customer?.phone || '';
  const email = quote?.customer_email || job?.client_email || d?.customer?.email || '';
  const tel = phone.replace(/[^\d+]/g, ''); const wa = (() => { const x = phone.replace(/\D/g, ''); return x.length === 10 ? `1${x}` : x; })();
  const contacts = job || d?.customer ? jobContacts(job || {}, d?.customer) : [];
  const calendarRows = [
    ...(d?.calendar || []).map((c: Any) => ({ at: c.start_time || c.due_at || c.date, title: c.title || label(c.kind || c.type), detail: c.location_address || c.notes })),
    ...(job
      ? ([['scheduled_date', 'Scheduled'], ['install_date', 'Install'], ['due_date', 'Due'], ['site_visit_date', 'Site visit'], ['production_start', 'Production']] as const)
        .filter(([k]) => job[k])
        .map(([k, l]) => ({ at: job[k], title: l, detail: '' }))
      : []),
  ].filter((r) => r.at);
  const nav = [
    ['client', 'Client'], ['quotes', 'Quotes'], ['invoices', 'Invoices'], ['payments', 'Payments'],
    ['drawings', 'Drawings'], ['photos', 'Photos'], ['docs', 'Documents'], ['tasks', 'Tasks'],
    ['calendar', 'Calendar'], ['messages', 'Messages'], ['notes', 'Notes'], ['phases', 'Phase history'],
  ];

  return (
    <div className="v3 jh" data-testid="job-hub">
      <JobHeader quote={quoteId} job={quoteId ? null : (job?.id || target.job)} className="jh-head" hubLink={false} />
      <div className="jh-top">
        <button type="button" className="v3-btn sm" onClick={() => pick({})}><X size={12} /> All jobs</button>
        <h1 className="v3-disp">{job?.client_name || quote?.project_name || quote?.customer_name || 'Job'}</h1>
        <span className="v3-kick">{[job?.job_number, quote?.quote_number, businessLabel(job?.business_unit || quote?.business_unit)].filter(Boolean).join(' · ')}</span>
        {job && <span className={`v3-pill ${pillTone(job.status)}`} data-testid="job-current-phase">{stageLabel(job.canonical_stage || job.pipeline_stage || job.status)}</span>}
        <a className="v3-btn sm" href="/?screen=jobs" onClick={(e) => { e.preventDefault(); window.location.assign('/?screen=jobs'); }}><LayoutGrid size={12} /> Board</a>
      </div>
      {job && (
        <PhaseStepper
          currentStage={job.canonical_stage || job.pipeline_stage || job.status}
          onMove={movePhase}
          moving={moving}
        />
      )}
      <nav className="jh-nav" aria-label="Job sections">{nav.map(([k, l]) => <a key={k} href={`#jh-${k}`} className="v3-chip">{l}</a>)}</nav>
      {!d ? <div className="jh-mut">Loading job…</div> : d.missing ? <Empty title="Job not found">The link may be old. <button type="button" className="v3-btn sm" onClick={() => pick({})}>Pick a job</button></Empty> : (
        <>
          <div className="jh-kpis">
            <div className="v3-card"><span className="v3-kick">Quoted</span><b className="v3-mono">{money(job?.quoted_amount || quote?.total)}</b></div>
            <div className="v3-card"><span className="v3-kick">Invoiced</span><b className="v3-mono">{money(d.invoices.reduce((a, i) => a + num(i.total), 0))}</b></div>
            <div className="v3-card"><span className="v3-kick">Paid</span><b className="v3-mono">{money(d.invoices.reduce((a, i) => a + num(i.amount_paid), 0) || quote?.deposit_paid)}</b></div>
            <div className="v3-card"><span className="v3-kick">Balance</span><b className="v3-mono">{money(d.invoices.length ? d.invoices.reduce((a, i) => a + num(i.balance_due), 0) : quote?.balance_due)}</b></div>
          </div>
          <div className="jh-grid">
            <div className="jh-col">
              <Sec id="client" icon={<Users size={15} />} title="Client & contacts" count={contacts.length}>
                {contacts.length === 0 ? <div className="jh-mut">No client on this job yet.</div> : contacts.map((c, i) => (
                  <div key={i} className="jh-note">
                    <span className="v3-kick">{c.role || 'Contact'}</span>
                    <p><b>{c.name}</b>{c.phone ? ` · ${c.phone}` : ''}{c.email ? ` · ${c.email}` : ''}{c.address ? `\n${c.address}` : ''}</p>
                  </div>
                ))}
                {d.items.length > 0 && (
                  <div style={{ marginTop: 10 }}>
                    <span className="v3-kick">Items</span>
                    {d.items.map((it: Any) => (
                      <div key={it.id || it.name} className="jh-tl">
                        <span className="v3-mono">{it.qty || 1}×</span>
                        <b>{it.name || it.item_name || 'Item'}</b>
                        <span>{measureText(it.measurements) || it.description || ''}</span>
                      </div>
                    ))}
                  </div>
                )}
              </Sec>
              <Sec id="quotes" icon={<FileText size={15} />} title="Estimates / quotes" count={quotes.length}>
                {quotes.length === 0 ? <div className="jh-mut">No quotes linked.</div> : (
                  <table className="v3-table"><thead><tr><th>Quote</th><th>Project</th><th>Status</th><th className="num">Total</th></tr></thead><tbody>
                    {quotes.map((q: Any) => (
                      <tr key={q.id} className="jh-click" data-testid={`jh-quote-${q.id}`}>
                        <td>
                          <button type="button" className="jh-a v3-mono" onClick={() => openDocViewer({ src: quotePdfSrc(q.id), title: q.quote_number || 'Estimate', kind: 'pdf' })}>{q.quote_number || q.id}</button>
                          <a href={`/?screen=quote&id=${encodeURIComponent(q.id)}`} className="jh-sub">Edit</a>
                        </td>
                        <td className="jh-ell">{q.project_name || q.customer_name}</td>
                        <td><span className={`v3-pill ${pillTone(q.status)}`}>{label(q.status)}</span></td>
                        <td className="num">{money(q.total)}</td>
                      </tr>
                    ))}
                  </tbody></table>
                )}
              </Sec>
              <Sec id="invoices" icon={<Receipt size={15} />} title="Invoices" count={invoices.length}>
                {invoices.length === 0 ? <div className="jh-mut">No invoices yet.</div> : (
                  <table className="v3-table"><thead><tr><th>Invoice</th><th>Status</th><th className="num">Total</th><th className="num">Balance</th></tr></thead><tbody>
                    {invoices.map((i: Any) => (
                      <tr key={i.id} className="jh-click" data-testid={`jh-invoice-${i.id}`}>
                        <td>
                          <button type="button" className="jh-a v3-mono" onClick={() => openDocViewer({ src: invoicePdfSrc(i.id), title: i.invoice_number || 'Invoice', kind: 'pdf' })}>{i.invoice_number || i.id}</button>
                          <a href={`/?screen=invoice&id=${encodeURIComponent(i.id)}`} className="jh-sub">Edit</a>
                        </td>
                        <td><span className={`v3-pill ${pillTone(i.status)}`}>{label(i.status)}</span></td>
                        <td className="num">{money(i.total)}</td>
                        <td className="num">{money(i.balance_due)}</td>
                      </tr>
                    ))}
                  </tbody></table>
                )}
              </Sec>
              <Sec id="payments" icon={<DollarSign size={15} />} title="Payments" count={d.payments.length}>
                {d.payments.length === 0 ? <div className="jh-mut">No payments recorded.</div> : (
                  <table className="v3-table"><thead><tr><th>Date</th><th>Method</th><th className="num">Amount</th></tr></thead><tbody>
                    {d.payments.map((p: Any, i: number) => <tr key={p.id || i}><td>{day(p.payment_date || p.created_at)}</td><td>{label(p.method || p.payment_method)}</td><td className="num">{money(p.amount)}</td></tr>)}
                  </tbody></table>
                )}
              </Sec>
              <Sec id="drawings" icon={<PenTool size={15} />} title="Drawings" count={drawings.length}>
                {!docs.data && !docs.err && drawings.length === 0 ? <div className="jh-mut">Loading…</div> : drawings.length === 0 ? <div className="jh-mut">No drawings saved for this job.</div> : drawings.map(g => <DocCard key={g.key} group={g} phone={phone} email={email} />)}
              </Sec>
              <Sec id="photos" icon={<ImageIcon size={15} />} title="Photos" count={photos.length}>
                {!docs.data && !docs.err && photos.length === 0 ? <div className="jh-mut">Loading…</div> : photos.length === 0 ? <div className="jh-mut">No photos saved for this job.</div> : (
                  <div className="jh-photos">{photos.map(p => <button key={p.id} type="button" style={{ backgroundImage: `url("${thumbUrl(p)}")` }} onClick={() => openDocViewer(toRef(p))} aria-label={`Open ${p.title}`} title={p.filename} />)}</div>
                )}
              </Sec>
              <Sec id="docs" icon={<FileText size={15} />} title="Documents" count={otherDocs.length + (d.documents?.length || 0)}>
                {docs.err && otherDocs.length === 0 && !d.documents.length ? <div className="jh-mut">{docs.err}</div> : !docs.data && otherDocs.length === 0 && !d.documents.length ? <div className="jh-mut">Loading…</div> : otherDocs.length === 0 && !d.documents.length ? <div className="jh-mut">No estimates, presentations or invoice PDFs saved yet.</div> : otherDocs.map(g => <DocCard key={g.key} group={g} phone={phone} email={email} />)}
                {d.documents.map((doc: Any) => {
                  const target = docViewerTarget(doc);
                  return (
                    <button key={doc.id} type="button" className="jh-tl jh-docbtn" data-testid={`jh-doc-${doc.id}`} onClick={() => target.src ? openDocViewer(target) : undefined}>
                      <span className="v3-mono">{label(doc.document_type)}</span>
                      <b>{doc.filename || doc.title || 'File'}</b>
                      <span>{target.src ? 'Open' : ''}</span>
                    </button>
                  );
                })}
              </Sec>
            </div>
            <div className="jh-col">
              <Sec id="tasks" icon={<CheckSquare size={15} />} title="Tasks" count={d.todos.length}>
                {d.todos.length === 0 ? <div className="jh-mut">No tasks linked to this job.</div>
                  : d.todos.map((t: Any, i: number) => <div key={t.id || i} className="jh-tl"><span className="v3-mono">{label(t.status || t.kind)}</span><b>{t.title || 'Task'}</b>{t.due_at && <span>{day(t.due_at)}</span>}</div>)}
              </Sec>
              <Sec id="calendar" icon={<Calendar size={15} />} title="Calendar" count={calendarRows.length}>
                {calendarRows.length === 0 ? <div className="jh-mut">No calendar dates on this job.</div>
                  : calendarRows.map((c, i) => <div key={i} className="jh-tl"><span className="v3-mono">{day(c.at)}</span><b>{c.title}</b>{c.detail && <span>{c.detail}</span>}</div>)}
              </Sec>
              <Sec id="messages" icon={<MessageSquare size={15} />} title="Messages" count={msgEvents.length}>
                <div className="jh-contact">
                  {tel && <a className="v3-btn sm" href={`tel:${tel}`}><Phone size={12} /> Call</a>}
                  {wa && <a className="v3-btn sm" href={`https://wa.me/${wa}`} target="_blank" rel="noreferrer"><MessageCircle size={12} /> WhatsApp</a>}
                  {email && <a className="v3-btn sm" href={`mailto:${email}`}><Mail size={12} /> Email</a>}
                </div>
                {msgEvents.length === 0 ? <div className="jh-mut">No messages are linked to this job yet. Sent quotes, emails and calls logged on the job show up here.</div>
                  : msgEvents.map((m, i) => <div key={i} className="jh-tl"><span className="v3-mono">{day(m.at)}</span><b>{m.what}</b></div>)}
              </Sec>
              <Sec id="notes" icon={<StickyNote size={15} />} title="Notes" count={notes.length}>
                {notes.length === 0 ? <div className="jh-mut">No notes yet.</div> : notes.map((n, i) => <div key={i} className="jh-note"><span className="v3-kick">{n.src}</span><p>{n.text}</p></div>)}
              </Sec>
              <Sec id="phases" icon={<History size={15} />} title="Phase history" count={phases.length}>
                {phases.length === 0 ? <div className="jh-mut">No phase moves yet. Use Move to next phase above — every change is logged here.</div>
                  : phases.map((p, i) => <div key={i} className="jh-tl" data-testid="phase-history-row"><span className="v3-mono">{day(p.at)}</span><b>{p.summary}</b>{p.actor && <span>by {p.actor}</span>}</div>)}
              </Sec>
              <Sec id="timeline" icon={<History size={15} />} title="Timeline" count={timeline.length}>
                {timeline.length === 0 ? <div className="jh-mut">No events yet.</div> : timeline.map((t, i) => <div key={i} className="jh-tl"><span className="v3-mono">{day(t.at)}</span><b>{t.what}</b>{t.detail && <span>{t.detail}</span>}</div>)}
              </Sec>
            </div>
          </div>
        </>
      )}
      <PhaseToast message={toast} onDismiss={() => setToast(null)} />
    </div>
  );
}
