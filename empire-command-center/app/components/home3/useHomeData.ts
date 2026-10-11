'use client';
// Real figures for the Max home. Same sources (and same rules) as the module ring:
// every number comes from an existing backend endpoint; a failed source stays "no data".
import { useCallback, useEffect, useMemo, useState } from 'react';
import { API } from '../../lib/api';
import { jobHubHref } from '../jobhub/href';
import { EDITION, T, LOCALE } from '../../v3/edition';

const ES = EDITION.lang === 'es';
const plural = (n: number, en: string, es: string, enP = `${en}s`, esP = `${es}s`) => (n === 1 ? (ES ? es : en) : (ES ? esP : enP));

type Res = { ok: true; data: any } | { ok: false; error: string };

async function getJson(url: string): Promise<Res> {
  try {
    const res = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(12000) });
    if (!res.ok) return { ok: false, error: `HTTP ${res.status}` };
    return { ok: true, data: await res.json() };
  } catch (e: any) {
    return { ok: false, error: e?.name === 'TimeoutError' ? 'timeout' : 'unreachable' };
  }
}

export function ymd(d: Date): string { return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`; }
export function addDays(d: Date, n: number): Date { return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n); }
function parseDate(s: any): Date | null { if (!s || typeof s !== 'string') return null; const t = Date.parse(s.includes('T') ? s : s.replace(' ', 'T')); return Number.isFinite(t) ? new Date(t) : null; }
function ageDays(s: any): number | null { const d = parseDate(s); return d ? Math.max(0, (Date.now() - d.getTime()) / 86_400_000) : null; }
export function num(n: any): number { const v = Number(n); return Number.isFinite(v) ? v : 0; }
const usd0 = new Intl.NumberFormat(LOCALE, { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
export function money(n: number): string { return usd0.format(n); }
export function compact(n: number): string { return Math.abs(n) >= 1000 ? `$${(n / 1000).toFixed(n >= 100_000 ? 0 : 1)}k` : usd0.format(n); }
function titleCase(s: string): string { return s.replace(/[_-]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }
export function dayLabel(d: string, now: Date): string {
  const today = ymd(now), tomorrow = ymd(addDays(now, 1));
  if (d === today) return T('Today'); if (d === tomorrow) return T('Tomorrow');
  return new Date(`${d}T12:00:00`).toLocaleDateString(LOCALE, { weekday: 'short', month: 'short', day: 'numeric' });
}

const CLOSED_QUOTE = new Set(['accepted', 'approved', 'cancelled', 'canceled', 'declined', 'rejected', 'expired', 'converted', 'won', 'lost', 'archived', 'void']);
const AWAITING_REPLY = new Set(['sent', 'proposal', 'viewed']);
const CLOSED_JOB = new Set(['completed', 'complete', 'cancelled', 'canceled', 'closed', 'archived', 'done']);
const CLOSED_LEAD = new Set(['won', 'lost', 'closed', 'converted', 'archived', 'disqualified', 'dead']);
const OPEN_TASK = new Set(['todo', 'in_progress', 'waiting', 'blocked', 'open', 'pending']);

export type PulseItem = { key: string; label: string; value: string | null; tone?: 'bad' | 'warn' | 'ok'; href: string; why?: string };
export type Suggestion = { key: string; tone: 'urgent' | 'warn' | 'info'; title: string; detail: string; href: string; action: string; src: string };
export type ScheduleItem = { key: string; date: string; time: string | null; title: string; detail: string; href: string };
export type Reminder = { id: string; title: string; due: string | null; priority: string; href: string };
export type Working = { key: string; title: string; detail: string; status: string; href: string };
export type Approval = { id: string; kind: string; channel: string; title: string; to: string };

export function useHomeData() {
  const [data, setData] = useState<Record<string, Res | undefined>>({});
  const [now, setNow] = useState<Date | null>(null);
  const load = useCallback(async () => {
    const origin = typeof window !== 'undefined' ? window.location.origin : '';
    const eps: Record<string, string> = {
      quotes: `${API}/quotes-v2?limit=500`,
      jobs: `${API}/jobs?limit=500`,
      leadPipeline: `${API}/leads/pipeline`,
      staleLeads: `${API}/leads/stale`,
      followups: `${API}/leads/followups/queue`,
      prospectStats: `${API}/leads/leadforge/prospects/stats`,
      finance: `${API}/finance/dashboard`,
      overdue: `${API}/payments/overdue`,
      maxHealth: `${API}/max/health`,
      dailyActions: `${API}/lifecycle/daily-actions`,
      approvals: `${API}/growth/approvals?status=pending`,
      tasks: `${origin}/api/v1/tasks?limit=200`,
    };
    if (EDITION.id === 'empire') {
      // Main studio only: host health and the Improvements (Cursor build) queue.
      eps.construction = `${API}/construction/projects`;
      eps.sysHealth = `${API}/system/health`;
      eps.improvements = `${API}/growth/improvements`;
    } else if (EDITION.id === 'amp') {
      // Max-e: AMP coaching and the businesses in this instance (Cibernettic IT and others).
      eps.ampStats = `${API}/amp/admin/stats`;
      eps.ampCourses = `${API}/amp/courses`;
      eps.businesses = `${API}/businesses`;
      eps.cibernettic = `${API}/businesses/cibernettic`;
    } else if (EDITION.id === 'maxine') {
      // Maxine: ConstructionForge portfolio (projects, lots, buyers).
      eps.construction = `${API}/construction/projects`;
      eps.buyers = `${API}/construction/buyers`;
    }
    const entries = await Promise.all(Object.entries(eps).map(async ([k, u]) => [k, await getJson(u)] as const));
    setData(Object.fromEntries(entries));
    setNow(new Date());
  }, []);
  useEffect(() => { load(); const t = setInterval(load, 60_000); return () => clearInterval(t); }, [load]);

  return useMemo(() => {
    const ok = (k: string): any => (data[k]?.ok ? (data[k] as { ok: true; data: any }).data : null);
    const err = (k: string): string | null => (data[k] && !data[k]!.ok ? (data[k] as { ok: false; error: string }).error : null);
    const loading = !now;

    const quotes: any[] | null = ok('quotes')?.quotes ?? null;
    const jobs: any[] | null = ok('jobs')?.jobs ?? null;
    const activeJobs = jobs ? jobs.filter(j => !CLOSED_JOB.has(String(j.status || '').toLowerCase())) : null;
    const openQuotes = quotes ? quotes.filter(q => !CLOSED_QUOTE.has(String(q.status || '').toLowerCase())) : null;
    const staleQuotes = quotes ? quotes.filter(q => AWAITING_REPLY.has(String(q.status || '').toLowerCase()) && (ageDays(q.sent_at || q.updated_at || q.created_at) ?? 0) >= 7) : null;
    const wrJobs = activeJobs ? activeJobs.filter(j => (j.business_unit || 'workroom') === 'workroom') : null;
    const wcJobs = activeJobs ? activeJobs.filter(j => j.business_unit === 'woodcraft') : null;
    const wrQuotes = openQuotes ? openQuotes.filter(q => (q.business_unit || 'workroom') === 'workroom') : null;
    const wrQuoteTotal = wrQuotes ? wrQuotes.reduce((a, q) => a + num(q.total), 0) : 0;
    const pstats = ok('prospectStats');
    const fin = ok('finance');
    const od = ok('overdue');
    const overdueCount = od ? num(od.count) : null;
    const overdueTotal = od ? num(od.total_outstanding) : 0;
    const cprojects: any[] | null = ok('construction')?.projects ?? null;
    const cActive = cprojects ? cprojects.filter(p => String(p.status).toLowerCase() === 'active') : null;
    const lots = cActive ? cActive.reduce((a, p) => a + num(p.total_lots), 0) : 0;
    const sysH = ok('sysHealth');
    const services = sysH?.services ? Object.entries(sysH.services) : null;
    const integrity = services && services.length ? Math.round((services.filter(([, v]) => v === true).length / services.length) * 100) : null;
    const mh = ok('maxHealth');
    const maxOk = mh ? ['healthy', 'ok'].includes(String(mh.status).toLowerCase()) : null;
    const leadPipe: any[] | null = ok('leadPipeline')?.pipeline ?? null;
    const newLeadCount = leadPipe ? num(leadPipe.find(r => String(r.status || '').toLowerCase() === 'new')?.count) : 0;
    const openLeadCount = leadPipe ? leadPipe.filter(r => !CLOSED_LEAD.has(String(r.status || '').toLowerCase())).reduce((a, r) => a + num(r.count), 0) : null;

    const financeItem: PulseItem = { key: 'finance', label: T('Finance'), value: od ? (overdueCount ? `${money(overdueTotal)} ${ES ? 'vencido' : 'overdue'}` : fin?.outstanding ? `${compact(num(fin.outstanding.total))} ${ES ? 'por cobrar' : 'A/R'}` : (ES ? 'nada vencido' : 'none overdue')) : null, tone: overdueCount ? 'bad' : undefined, href: '/?screen=invoices', why: err('overdue') || undefined };
    const ampStats = ok('ampStats');
    const ampCourses: any[] | null = Array.isArray(ok('ampCourses')) ? ok('ampCourses') : (ok('ampCourses')?.courses ?? null);
    const businesses: any[] | null = ok('businesses')?.businesses ?? null;
    const ciber = ok('cibernettic');
    const ciberContacts: any[] | null = ciber ? (Array.isArray(ciber.contacts) ? ciber.contacts : []) : null;
    const buyersRaw = ok('buyers');
    const buyers: any[] | null = buyersRaw ? (Array.isArray(buyersRaw) ? buyersRaw : (buyersRaw.buyers ?? [])) : null;
    const familyPulse: PulseItem[] | null = EDITION.id === 'amp' ? [
      { key: 'amp', label: 'AMP', value: ampStats || ampCourses ? [ampStats ? `${num(ampStats.total_users)} ${plural(num(ampStats.total_users), 'coachee', 'coachee')}` : null, ampCourses ? `${ampCourses.length} ${plural(ampCourses.length, 'course', 'curso')}` : null].filter(Boolean).join(' · ') : null, href: '/?product=amp', why: err('ampStats') || err('ampCourses') || undefined },
      { key: 'cibernettic', label: 'Cibernettic', value: ciberContacts ? `${ciberContacts.length} ${plural(ciberContacts.length, 'contact', 'contacto')}` : null, href: '/amp/empresas/cibernettic', why: err('cibernettic') || undefined },
      { key: 'empresas', label: ES ? 'Empresas' : 'Businesses', value: businesses ? `${businesses.length}` : null, href: '/amp/empresas', why: err('businesses') || undefined },
      financeItem,
      { key: 'lead', label: ES ? 'Ingreso' : 'Leads', value: pstats ? `${num(pstats.total_prospects)} ${plural(num(pstats.total_prospects), 'prospect', 'prospecto')}` : null, href: '/?product=lead', why: err('prospectStats') || undefined },
    ] : EDITION.id === 'maxine' ? [
      { key: 'construction', label: 'Portafolio', value: cActive ? `${cActive.length} ${plural(cActive.length, 'active', 'activo')} · ${lots} ${plural(lots, 'lot', 'lote')}` : null, href: '/?product=construction', why: err('construction') || undefined },
      { key: 'buyers', label: 'Compradores', value: buyers ? `${buyers.length}` : null, href: '/?product=construction&section=buyers', why: err('buyers') || undefined },
      financeItem,
      { key: 'lead', label: 'Prospectos', value: pstats ? `${num(pstats.total_prospects)} ${plural(num(pstats.total_prospects), 'prospect', 'prospecto')}` : null, href: '/?product=lead', why: err('prospectStats') || undefined },
    ] : null;

    const pulse: PulseItem[] = familyPulse ?? [
      { key: 'workroom', label: 'Workroom', value: wrJobs ? `${wrJobs.length} job${wrJobs.length === 1 ? '' : 's'}${wrQuotes ? ` · ${compact(wrQuoteTotal)} open` : ''}` : null, href: '/?product=workroom', why: err('jobs') || undefined },
      { key: 'finance', label: 'Finance', value: od ? (overdueCount ? `${money(overdueTotal)} overdue` : fin?.outstanding ? `${compact(num(fin.outstanding.total))} A/R` : 'none overdue') : null, tone: overdueCount ? 'bad' : undefined, href: '/?screen=invoices', why: err('overdue') || undefined },
      { key: 'construction', label: 'Construction', value: cActive ? `${cActive.length} active · ${lots} lots` : null, href: '/?product=construction', why: err('construction') || undefined },
      { key: 'lead', label: 'LeadForge', value: pstats ? `${num(pstats.total_prospects)} prospects` : null, href: '/?product=lead', why: err('prospectStats') || undefined },
      { key: 'craft', label: 'WoodCraft', value: wcJobs ? `${wcJobs.length} job${wcJobs.length === 1 ? '' : 's'}` : null, href: '/?product=craft', why: err('jobs') || undefined },
      { key: 'system', label: 'System', value: integrity !== null ? `${integrity}% health` : null, tone: integrity !== null && integrity < 100 ? 'warn' : undefined, href: '/?product=system', why: err('sysHealth') || undefined },
    ];

    const apprRaw: any[] | null = ok('approvals')?.items ?? null;
    const approvals: Approval[] | null = apprRaw ? apprRaw.map(a => ({ id: String(a.id), kind: String(a.kind || ''), channel: String(a.channel || a.kind || ''), title: String(a.title || a.subject || 'Approval'), to: String(a.to_name || '') })) : null;
    const improvements: any[] | null = ok('improvements')?.items ?? null;
    const tasks: any[] | null = ok('tasks')?.tasks ?? null;
    const openTasks = tasks ? tasks.filter(t => OPEN_TASK.has(String(t.status || '').toLowerCase())) : null;

    const reminders: Reminder[] | null = openTasks ? openTasks
      .map(t => ({ id: String(t.id), title: String(t.title || 'Task'), due: (t.follow_up_date || t.due_date || null) as string | null, priority: String(t.priority || 'normal'), href: '/?screen=tasks' }))
      .sort((a, b) => (a.due || '9999').localeCompare(b.due || '9999')).slice(0, 6) : null;

    const working: Working[] | null = (tasks || improvements) ? [
      ...(tasks || []).filter(t => String(t.status).toLowerCase() === 'in_progress').slice(0, 3)
        .map(t => ({ key: `t-${t.id}`, title: String(t.title || (ES ? 'Tarea' : 'Task')), detail: [t.desk, t.business].filter(Boolean).join(' · ') || (ES ? 'tarea' : 'task'), status: ES ? 'en curso' : 'in progress', href: '/?screen=tasks' })),
      ...(improvements || []).filter(i => !['merged', 'done', 'rejected', 'declined', 'closed'].includes(String(i.status || '').toLowerCase())).slice(0, 3)
        .map(i => ({ key: `i-${i.id}`, title: String(i.title || 'Improvement'), detail: 'Improvement request', status: String(i.status || 'requested').replace(/_/g, ' '), href: '/?product=improvements' })),
    ].slice(0, 4) : null;

    let schedule: ScheduleItem[] | null = null;
    let suggestions: Suggestion[] | null = null;
    if (now) {
      const today = ymd(now), horizon = ymd(addDays(now, 7));
      if (activeJobs) {
        const up: ScheduleItem[] = [];
        activeJobs.forEach(j => (['install_date', 'site_visit_date', 'scheduled_date'] as const).forEach(f => {
          const v = j[f] ? String(j[f]) : ''; const d = v.slice(0, 10);
          if (v && d >= today && d <= horizon) {
            const t = v.includes('T') ? parseDate(v) : null;
            up.push({ key: `${j.id}-${f}`, date: d, time: t ? t.toLocaleTimeString(LOCALE, { hour: 'numeric', minute: '2-digit' }) : null,
              title: `${f === 'install_date' ? (ES ? 'Instalación' : 'Install') : f === 'site_visit_date' ? (ES ? 'Visita' : 'Site visit') : (ES ? 'Agendado' : 'Scheduled')} · ${j.client_name || j.title || j.job_number || (ES ? 'trabajo' : 'job')}`,
              detail: [j.job_number, EDITION.family ? '' : (j.business_unit === 'woodcraft' ? 'WoodCraft' : 'Workroom')].filter(Boolean).join(' · '),
              href: jobHubHref({ job: j.id }) });
          }
        }));
        schedule = up.sort((a, b) => (a.date + (a.time || '')).localeCompare(b.date + (b.time || ''))).slice(0, 5);
      }
      const out: Suggestion[] = [];
      if (od && num(od.count) > 0) {
        const list: any[] = od.overdue_invoices || [];
        const oldest = [...list].sort((a, b) => String(a.due_date || '').localeCompare(String(b.due_date || '')))[0];
        out.push({ key: 'overdue', tone: 'urgent', title: T('Invoice recovery'), action: T('Review'), src: 'payments/overdue',
          detail: ES
            ? `${num(od.count)} ${plural(num(od.count), 'invoice', 'factura vencida', 'invoices', 'facturas vencidas')} · ${money(overdueTotal)}${oldest ? ` · la más antigua ${oldest.invoice_number || ''}` : ''}`
            : `${num(od.count)} overdue invoice${num(od.count) === 1 ? '' : 's'} · ${money(overdueTotal)}${oldest ? ` · oldest ${oldest.invoice_number || ''}` : ''}`,
          href: oldest?.id ? `/?screen=invoice&id=${encodeURIComponent(oldest.id)}` : '/?screen=invoices' });
      }
      if (staleQuotes && staleQuotes.length) {
        out.push({ key: 'stale', tone: 'warn', title: T('Quote follow-up'), action: T('Open'), src: 'quotes-v2',
          detail: ES
            ? `${staleQuotes.length} ${plural(staleQuotes.length, '', 'cotización enviada', '', 'cotizaciones enviadas')} sin respuesta hace 7+ días (${money(staleQuotes.reduce((a, q) => a + num(q.total), 0))})`
            : `${staleQuotes.length} sent quote${staleQuotes.length === 1 ? '' : 's'} unanswered 7+ days (${money(staleQuotes.reduce((a, q) => a + num(q.total), 0))})`,
          href: EDITION.family ? '/?screen=jobs' : '/?product=workroom&section=quotes' });
      }
      const da = ok('dailyActions');
      if (da && Array.isArray(da.actions) && da.actions.length) {
        const byType: Record<string, any[]> = {};
        da.actions.forEach((a: any) => { const t = String(a.type || 'action'); (byType[t] = byType[t] || []).push(a); });
        Object.entries(byType).slice(0, 2).forEach(([t, list]) => {
          const f = list[0];
          out.push({ key: `da-${t}`, tone: 'info', title: t === 'send_quote' ? T('Quotes ready to send') : t === 'send_reminder' ? T('Payment reminders') : titleCase(t), action: T('Open'), src: 'lifecycle/daily-actions',
            detail: ES ? `${list.length} ${plural(list.length, '', 'pendiente', '', 'pendientes')} · siguiente: ${f.label || ''}` : `${list.length} item${list.length === 1 ? '' : 's'} · next: ${f.label || ''}`,
            href: f.entity_type === 'invoice' ? '/?screen=invoices' : f.entity_type === 'quote' ? (EDITION.family ? '/?screen=jobs' : '/?product=workroom&section=quotes') : f.entity_type === 'lead' ? '/?product=lead' : '/?product=owner&screen=dashboard' });
        });
      }
      const fq = ok('followups'), sl = ok('staleLeads');
      const leadN = Math.max(newLeadCount, num(fq?.total), num(sl?.total));
      if (leadN > 0) out.push({ key: 'leads', tone: 'warn', title: T('Lead follow-up'), action: T('Open'), src: 'leads', detail: ES ? `${leadN} ${plural(leadN, '', 'prospecto espera', '', 'prospectos esperan')} contacto` : `${leadN} lead${leadN === 1 ? '' : 's'} waiting for contact`, href: '/?product=lead' });
      const rank = { urgent: 0, warn: 1, info: 2 } as const;
      suggestions = out.sort((a, b) => rank[a.tone] - rank[b.tone]).slice(0, 4);
    }

    return {
      loading, now, pulse, approvals, improvements, reminders, working, schedule, suggestions, maxOk,
      figures: { approvals: approvals?.length ?? null, overdueTotal: od ? overdueTotal : null, overdueCount, wrJobs: wrJobs?.length ?? null, installs: schedule?.filter(s => s.title.startsWith(ES ? 'Instalación' : 'Install')).length ?? null, openLeadCount,
        coachees: ampStats ? num(ampStats.total_users) : null, ciberContacts: ciberContacts?.length ?? null, cProjects: cActive?.length ?? null, lots: cActive ? lots : null, buyers: buyers?.length ?? null },
      errors: { approvals: err('approvals'), tasks: err('tasks'), improvements: err('improvements'), jobs: err('jobs') },
      reload: load,
    };
  }, [data, now, load]);
}
