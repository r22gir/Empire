'use client';
/**
 * Job hub: everything about one job on one page (design system v3).
 * Quotes · Invoices · Drawings · Photos · Documents · Messages · Notes · Timeline.
 * Open with /?product=workroom&section=jobhub&job=<jobId> (or &quote=<quoteId> when no job exists yet).
 * Read-only: every number and row comes from existing endpoints; nothing is sent from here.
 */
import { useCallback, useEffect, useMemo, useState } from 'react';
import type { ReactNode } from 'react';
import { Search, ArrowRight, FileText, Receipt, PenTool, Image as ImageIcon, MessageSquare, StickyNote, History, Briefcase, Phone, Mail, MessageCircle, X } from 'lucide-react';
import { API } from '../../lib/api';
import JobHeader from '../docs/JobHeader';
import DocCard, { thumbUrl, toRef } from '../docs/DocCard';
import { useQuoteDocs } from '../docs/DocsTab';
import { openDocViewer } from '../docs/viewerBus';
import { Empty } from '../../v3/ui';
import { jobHubHref } from './href';
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

interface HubData { job: Any | null; quote: Any | null; quotes: Any[]; invoices: Any[]; events: Any[]; customer: Any | null; missing?: string }

function useHub(target: { job: string | null; quote: string | null }) {
  const [data, setData] = useState<HubData | null>(null);
  useEffect(() => {
    if (!target.job && !target.quote) { setData(null); return; }
    let dead = false;
    (async () => {
      setData(null);
      let job: Any | null = null; let quote: Any | null = null;
      if (target.job) job = (await getJson(`${API}/jobs/${encodeURIComponent(target.job)}`))?.job ?? null;
      const qid = job?.quote_id || target.quote;
      if (qid) { const q = await getJson(`${API}/quotes-v2/${encodeURIComponent(qid)}`); quote = q?.quote ?? (q?.id ? q : null); }
      const allQuotes: Any[] = (await getJson(`${API}/quotes-v2?limit=500`))?.quotes ?? [];
      if (!job) {
        const jid = quote?.job_id;
        if (jid) job = (await getJson(`${API}/jobs/${encodeURIComponent(jid)}`))?.job ?? null;
        if (!job && quote) { const js: Any[] = (await getJson(`${API}/jobs?limit=500`))?.jobs ?? []; job = js.find(j => j.quote_id === quote!.id) ?? null; }
      }
      const cid = job?.customer_id || quote?.customer_id || null;
      const [byJob, byCust, timeline, cust] = await Promise.all([
        job ? getJson(`${API}/invoices?job_id=${encodeURIComponent(job.id)}&limit=100`) : null,
        cid ? getJson(`${API}/invoices?customer_id=${encodeURIComponent(cid)}&limit=100`) : null,
        job ? getJson(`${API}/jobs/${encodeURIComponent(job.id)}/timeline`) : null,
        cid ? getJson(`${API}/crm/customers/${encodeURIComponent(cid)}`) : null,
      ]);
      const inv = new Map<string, Any>();
      [...(byJob?.invoices ?? []), ...(byCust?.invoices ?? [])].forEach((i: Any) => inv.set(i.id, i));
      const quotes = allQuotes.filter(q => (cid && q.customer_id === cid) || (quote && q.id === quote.id) || (job && q.job_id === job.id))
        .sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || '')));
      if (dead) return;
      setData({ job, quote, quotes, invoices: [...inv.values()].sort((a, b) => String(b.created_at || '').localeCompare(String(a.created_at || ''))),
        events: timeline?.events ?? [], customer: cust?.customer ?? null, missing: !job && !quote ? 'not found' : undefined });
    })();
    return () => { dead = true; };
  }, [target.job, target.quote]);
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
      // Default list hides obvious test/mock records; typing a search shows everything that matches.
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
  useEffect(() => { if (!initial?.job && !initial?.quote) { const t = readTarget(); if (t.job || t.quote) setTarget(t); } }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const pick = useCallback((t: { job?: string | null; quote?: string | null }) => {
    const next = { job: t.job ?? null, quote: t.quote ?? null };
    setTarget(next);
    try { window.history.pushState(null, '', jobHubHref(next)); } catch { /* */ }
  }, []);
  const d = useHub(target);
  const quoteId = d?.quote?.id || d?.job?.quote_id || target.quote || null;
  const docs = useQuoteDocs(quoteId, quoteId ? null : (d?.job?.job_number || d?.job?.id || target.job));
  const groups = docs.data?.groups ?? [];
  const drawings = groups.filter(g => g.type === 'drawing');
  const photos = groups.filter(g => g.type === 'photo').flatMap(g => [g.final, ...g.older]);
  const otherDocs = groups.filter(g => g.type !== 'drawing' && g.type !== 'photo');

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
  const nav = [['quotes', 'Quotes'], ['invoices', 'Invoices'], ['drawings', 'Drawings'], ['photos', 'Photos'], ['docs', 'Documents'], ['messages', 'Messages'], ['notes', 'Notes'], ['timeline', 'Timeline']];

  return (
    <div className="v3 jh">
      <JobHeader quote={quoteId} job={quoteId ? null : (job?.id || target.job)} className="jh-head" hubLink={false} />
      <div className="jh-top">
        <button type="button" className="v3-btn sm" onClick={() => pick({})}><X size={12} /> All jobs</button>
        <h1 className="v3-disp">{job?.client_name || quote?.project_name || quote?.customer_name || 'Job'}</h1>
        <span className="v3-kick">{[job?.job_number, quote?.quote_number, label(job?.business_unit || quote?.business_unit)].filter(Boolean).join(' · ')}</span>
        {job && <span className={`v3-pill ${pillTone(job.status)}`}>{label(job.pipeline_stage || job.status)}</span>}
      </div>
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
              <Sec id="quotes" icon={<FileText size={15} />} title="Quotes" count={d.quotes.length}>
                {d.quotes.length === 0 ? <div className="jh-mut">No quotes linked.</div> : (
                  <table className="v3-table"><thead><tr><th>Quote</th><th>Project</th><th>Status</th><th className="num">Total</th></tr></thead><tbody>
                    {d.quotes.map(q => <tr key={q.id}><td><a href={`/?screen=quote&id=${encodeURIComponent(q.id)}`} className="jh-a v3-mono">{q.quote_number || q.id}</a></td><td className="jh-ell">{q.project_name || q.customer_name}</td><td><span className={`v3-pill ${pillTone(q.status)}`}>{label(q.status)}</span></td><td className="num">{money(q.total)}</td></tr>)}
                  </tbody></table>
                )}
              </Sec>
              <Sec id="invoices" icon={<Receipt size={15} />} title="Invoices" count={d.invoices.length}>
                {d.invoices.length === 0 ? <div className="jh-mut">No invoices yet.</div> : (
                  <table className="v3-table"><thead><tr><th>Invoice</th><th>Status</th><th className="num">Total</th><th className="num">Balance</th></tr></thead><tbody>
                    {d.invoices.map(i => <tr key={i.id}><td><a href={`/?screen=invoice&id=${encodeURIComponent(i.id)}`} className="jh-a v3-mono">{i.invoice_number || i.id}</a></td><td><span className={`v3-pill ${pillTone(i.status)}`}>{label(i.status)}</span></td><td className="num">{money(i.total)}</td><td className="num">{money(i.balance_due)}</td></tr>)}
                  </tbody></table>
                )}
              </Sec>
              <Sec id="drawings" icon={<PenTool size={15} />} title="Drawings" count={drawings.length}>
                {!docs.data && !docs.err ? <div className="jh-mut">Loading…</div> : drawings.length === 0 ? <div className="jh-mut">No drawings saved for this job.</div> : drawings.map(g => <DocCard key={g.key} group={g} phone={phone} email={email} />)}
              </Sec>
              <Sec id="photos" icon={<ImageIcon size={15} />} title="Photos" count={photos.length}>
                {!docs.data && !docs.err ? <div className="jh-mut">Loading…</div> : photos.length === 0 ? <div className="jh-mut">No photos saved for this job.</div> : (
                  <div className="jh-photos">{photos.map(p => <button key={p.id} type="button" style={{ backgroundImage: `url("${thumbUrl(p)}")` }} onClick={() => openDocViewer(toRef(p))} aria-label={`Open ${p.title}`} title={p.filename} />)}</div>
                )}
              </Sec>
              <Sec id="docs" icon={<FileText size={15} />} title="Documents" count={otherDocs.length}>
                {docs.err ? <div className="jh-mut">{docs.err}</div> : !docs.data ? <div className="jh-mut">Loading…</div> : otherDocs.length === 0 ? <div className="jh-mut">No estimates, presentations or invoice PDFs saved yet.</div> : otherDocs.map(g => <DocCard key={g.key} group={g} phone={phone} email={email} />)}
              </Sec>
            </div>
            <div className="jh-col">
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
              <Sec id="timeline" icon={<History size={15} />} title="Timeline" count={timeline.length}>
                {timeline.length === 0 ? <div className="jh-mut">No events yet.</div> : timeline.map((t, i) => <div key={i} className="jh-tl"><span className="v3-mono">{day(t.at)}</span><b>{t.what}</b>{t.detail && <span>{t.detail}</span>}</div>)}
              </Sec>
            </div>
          </div>
        </>
      )}
    </div>
  );
}
