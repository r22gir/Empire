'use client';
/**
 * /preview/ring — "module ring" home PREVIEW (2026-10-03).
 *
 * Does not replace the current home (app/page.tsx) or /preview/cockpit.
 * Every number comes from an existing backend endpoint (or open-meteo for the
 * install-day forecast). Missing sources render "SIN DATOS · NO DATA".
 *
 * Sources (GET, same-origin /api/v1 proxy or localhost:8000 via lib/api):
 *   quotes-v2, jobs, leads/pipeline, leads/stale, leads/followups/queue,
 *   leads/leadforge/prospects/stats, leads/leadforge/prospect-pipeline,
 *   finance/dashboard, finance/payments (7d), finance/expenses (7d),
 *   payments/overdue, crm/customers, construction/projects, system/health,
 *   max/health, max/voice/status, max/status (running commit),
 *   lifecycle/daily-actions (Max's founder action list).
 * Trailing-slash list endpoints (/leads/, /tasks/) are avoided: through the
 * studio proxy they end in a redirect to https://127.0.0.1:8000.
 */
import { cloneElement, isValidElement, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { API } from '../../lib/api';
import { NAV_GROUPS } from '../../components/layout/LeftNav';
import type { NavItem } from '../../components/layout/LeftNav';
import LiveVoiceCall from '../../components/LiveVoiceCall';
import {
  CircleDot, ArrowLeft, ArrowRight, Send, Scissors, Users, Target, DollarSign, Building2, TreePine, Activity,
  AlertTriangle, FileText, CloudSun, UsersRound, Sparkles, Zap, Receipt, CalendarClock, Mic, Radar,
} from 'lucide-react';
import './ring.css';

/* ------------------------------------------------------------------ data */

type Res = { ok: true; data: any } | { ok: false; error: string };
type Loaded = Record<string, Res | undefined>;

async function getJson(url: string): Promise<Res> {
  try {
    const res = await fetch(url, { cache: 'no-store', signal: AbortSignal.timeout(12000) });
    if (!res.ok) return { ok: false, error: `HTTP ${res.status}` };
    return { ok: true, data: await res.json() };
  } catch (e: any) {
    return { ok: false, error: e?.name === 'TimeoutError' ? 'timeout' : 'unreachable' };
  }
}

function ymd(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function addDays(d: Date, n: number): Date { return new Date(d.getFullYear(), d.getMonth(), d.getDate() + n); }
function parseDate(s: any): Date | null {
  if (!s || typeof s !== 'string') return null;
  const t = Date.parse(s.includes('T') ? s : s.replace(' ', 'T'));
  return Number.isFinite(t) ? new Date(t) : null;
}
function ageDays(s: any): number | null { const d = parseDate(s); return d ? Math.max(0, (Date.now() - d.getTime()) / 86_400_000) : null; }
function num(n: any): number { const v = Number(n); return Number.isFinite(v) ? v : 0; }
const usd0 = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
const usd2 = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 });
function money(n: number): string { return Math.abs(n) >= 10_000 ? usd0.format(n) : usd2.format(n); }
function compact(n: number): string { return Math.abs(n) >= 1000 ? `$${(n / 1000).toFixed(n >= 100_000 ? 0 : 1)}k` : usd0.format(n); }
function titleCase(s: string): string { return s.replace(/[_-]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }

const CLOSED_QUOTE = new Set(['accepted', 'approved', 'cancelled', 'canceled', 'declined', 'rejected', 'expired', 'converted', 'won', 'lost', 'archived', 'void']);
const AWAITING_REPLY = new Set(['sent', 'proposal', 'viewed']);
const CLOSED_JOB = new Set(['completed', 'complete', 'cancelled', 'canceled', 'closed', 'archived', 'done']);
const CLOSED_LEAD = new Set(['won', 'lost', 'closed', 'converted', 'archived', 'disqualified', 'dead']);

function useRingData() {
  const [data, setData] = useState<Loaded>({});
  const [loadedAt, setLoadedAt] = useState<Date | null>(null);
  const load = useCallback(async () => {
    const now = new Date();
    const from = ymd(addDays(now, -6)), to = ymd(now);
    const eps: Record<string, string> = {
      quotes: '/quotes-v2?limit=500',
      jobs: '/jobs?limit=500',
      leadPipeline: '/leads/pipeline',
      staleLeads: '/leads/stale',
      followups: '/leads/followups/queue',
      prospectStats: '/leads/leadforge/prospects/stats',
      prospectPipeline: '/leads/leadforge/prospect-pipeline?limit=50',
      finance: '/finance/dashboard',
      payments7: `/finance/payments?date_from=${from}&date_to=${to}&limit=500`,
      expenses7: `/finance/expenses?date_from=${from}&date_to=${to}&limit=500`,
      overdue: '/payments/overdue',
      customers: '/crm/customers?limit=1',
      construction: '/construction/projects',
      sysHealth: '/system/health',
      maxHealth: '/max/health',
      maxVoice: '/max/voice/status',
      maxStatus: '/max/status',
      dailyActions: '/lifecycle/daily-actions',
    };
    const entries = await Promise.all(Object.entries(eps).map(async ([k, p]) => [k, await getJson(`${API}${p}`)] as const));
    setData(Object.fromEntries(entries));
    setLoadedAt(new Date());
  }, []);
  useEffect(() => { load(); const t = setInterval(load, 60_000); return () => clearInterval(t); }, [load]);
  return { data, loadedAt };
}

function useReducedMotion(): boolean {
  const [r, setR] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const on = () => setR(mq.matches); on();
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);
  return r;
}

function useCountUp(target: number | null, reduced: boolean, ms = 1300): number {
  const [v, setV] = useState(0);
  const from = useRef(0);
  useEffect(() => {
    if (target === null) return;
    if (reduced) { setV(target); from.current = target; return; }
    const start = performance.now(); const a = from.current; let raf = 0;
    const step = (t: number) => {
      const p = Math.min(1, (t - start) / ms); const e = 1 - Math.pow(1 - p, 3);
      setV(a + (target - a) * e);
      if (p < 1) raf = requestAnimationFrame(step); else from.current = target;
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, reduced, ms]);
  return v;
}

function CountMoney({ value, reduced }: { value: number; reduced: boolean }) { const v = useCountUp(value, reduced); return <>{money(v)}</>; }
function CountInt({ value, reduced }: { value: number; reduced: boolean }) { const v = useCountUp(value, reduced); return <>{Math.round(v).toLocaleString('en-US')}</>; }

/* --------------------------------------------------------------- weather */

const WX: Record<number, string> = {
  0: 'Clear', 1: 'Mostly clear', 2: 'Partly cloudy', 3: 'Overcast', 45: 'Fog', 48: 'Fog', 51: 'Light drizzle', 53: 'Drizzle', 55: 'Heavy drizzle',
  61: 'Light rain', 63: 'Rain', 65: 'Heavy rain', 66: 'Freezing rain', 67: 'Freezing rain', 71: 'Light snow', 73: 'Snow', 75: 'Heavy snow',
  80: 'Rain showers', 81: 'Rain showers', 82: 'Violent showers', 95: 'Thunderstorm', 96: 'Thunderstorm + hail', 99: 'Thunderstorm + hail',
};
// Washington, DC area (Empire Workroom service area)
const WX_LAT = 38.9072, WX_LON = -77.0369;

type Install = { date: string; job: any } | null;
function useInstallWeather(install: Install | undefined) {
  const [wx, setWx] = useState<Res | null>(null);
  useEffect(() => {
    if (!install) { setWx(null); return; }
    const days = (new Date(`${install.date}T12:00:00`).getTime() - Date.now()) / 86_400_000;
    if (days > 15) { setWx({ ok: false, error: 'beyond the 16-day forecast window' }); return; }
    const url = `https://api.open-meteo.com/v1/forecast?latitude=${WX_LAT}&longitude=${WX_LON}&daily=weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max,wind_speed_10m_max&temperature_unit=fahrenheit&wind_speed_unit=mph&timezone=America%2FNew_York&start_date=${install.date}&end_date=${install.date}`;
    let alive = true;
    getJson(url).then(r => { if (alive) setWx(r); });
    return () => { alive = false; };
  }, [install?.date]); // eslint-disable-line react-hooks/exhaustive-deps
  return wx;
}

/* ------------------------------------------------------------------- menu */

function navHref(item: NavItem): string {
  if (item.kind === 'daily-summary') return '/?product=owner&screen=dashboard';
  if (item.kind === 'screen' && item.screen) return `/?screen=${encodeURIComponent(item.screen)}`;
  return `/?product=${encodeURIComponent(item.id)}`;
}
function sizedIcon(icon: ReactNode, size: number): ReactNode {
  return isValidElement(icon) ? cloneElement(icon as ReactElement<{ size?: number }>, { size }) : icon;
}

function CyberMenu({ sysLine }: { sysLine: ReactNode }) {
  let n = 0;
  return (
    <nav className="rg-menu" aria-label="Empire modules">
      <div className="rg-brand">
        <div><b>EMPIRE</b><small>AI COMMAND · MODULE RING</small></div>
      </div>
      <div className="rg-sys">{sysLine}</div>
      <div className="rg-tabs">
        <a href="/preview/ring" className="rg-tab is-active" aria-current="page">
          <span className="rg-tab-ico"><CircleDot size={15} /></span><span className="rg-tab-name">Ring (preview)</span>
        </a>
        {NAV_GROUPS.map(g => (
          <div key={g.key} style={{ display: 'contents' }}>
            <div className="rg-tabgroup">{g.label}</div>
            {g.items.map(item => {
              n++;
              return (
                <a key={item.id} href={navHref(item)} className={`rg-tab ${item.status === 'planned' ? 'is-planned' : ''}`} title={item.name}>
                  <span className="rg-tab-ico" style={{ color: item.color }}>{sizedIcon(item.icon, 15)}</span>
                  <span className="rg-tab-name">{item.name}</span>
                  {item.status !== 'active' && <span className="rg-tab-st">{item.status}</span>}
                  {n % 5 === 2 && <span className="rg-glitch" style={{ animationDelay: `${(n * 1.3) % 7}s` }} />}
                </a>
              );
            })}
          </div>
        ))}
      </div>
      <div className="rg-menu-foot">EMPIRE OS · MODULE RING PREVIEW<br />CLOUDFLARE ACCESS / TAILSCALE ONLY</div>
    </nav>
  );
}

/* ------------------------------------------------------------------- ring */

type Tone = 'ok' | 'warn' | 'alert' | 'nd';
type Segment = { key: string; name: string; icon: ReactNode; value: string | null; sub: string; tone: Tone; href: string; why?: string };
const TONE_COLOR: Record<Tone, string> = { ok: '#00e5ff', warn: '#ffc857', alert: '#ff2bd6', nd: '#4a5a63' };

function ModuleRing({ segs, maxOk, maxLabel }: { segs: Segment[]; maxOk: boolean | null; maxLabel: string }) {
  const C = 300, RO = 272, RI = 178, GAP = 1.4;
  const n = Math.max(1, segs.length), span = 360 / n;
  const pt = (deg: number, r: number) => [C + Math.cos((deg * Math.PI) / 180) * r, C + Math.sin((deg * Math.PI) / 180) * r];
  const arcPath = (a0: number, a1: number) => {
    const [x1, y1] = pt(a0, RO), [x2, y2] = pt(a1, RO), [x3, y3] = pt(a1, RI), [x4, y4] = pt(a0, RI);
    const large = a1 - a0 > 180 ? 1 : 0;
    return `M ${x1} ${y1} A ${RO} ${RO} 0 ${large} 1 ${x2} ${y2} L ${x3} ${y3} A ${RI} ${RI} 0 ${large} 0 ${x4} ${y4} Z`;
  };
  return (
    <div className="rg-ring">
      <svg className="rg-ring-svg" viewBox="0 0 600 600" role="group" aria-label="Module ring">
        <defs>
          <filter id="rgGlow" x="-30%" y="-30%" width="160%" height="160%"><feGaussianBlur stdDeviation="4" result="b" /><feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge></filter>
        </defs>
        <g className="rg-spin">
          <circle cx={C} cy={C} r={292} fill="none" stroke="rgba(0,229,255,0.35)" strokeWidth="1" strokeDasharray="2 10" />
        </g>
        {Array.from({ length: 120 }, (_, i) => {
          const a = i * 3; const long = i % 10 === 0; const [x1, y1] = pt(a, 280); const [x2, y2] = pt(a, long ? 288 : 284);
          return <line key={i} x1={x1} y1={y1} x2={x2} y2={y2} stroke="rgba(0,229,255,0.5)" strokeWidth={long ? 1.4 : 0.6} />;
        })}
        {segs.map((s, i) => {
          const a0 = -90 - span / 2 + i * span + GAP / 2, a1 = a0 + span - GAP;
          const col = TONE_COLOR[s.tone];
          return (
            <a key={s.key} href={s.href} className="rg-seg" aria-label={`${s.name}: ${s.value ?? 'no data'} ${s.sub}`} style={{ color: col }}>
              <title>{`${s.name} — ${s.value ?? 'SIN DATOS'} ${s.sub}`}</title>
              <path className="rg-seg-fill" d={arcPath(a0, a1)} fill={s.tone === 'alert' ? 'rgba(255,43,214,0.16)' : s.tone === 'warn' ? 'rgba(255,200,87,0.10)' : s.tone === 'nd' ? 'rgba(74,90,99,0.12)' : 'rgba(0,229,255,0.10)'} stroke={col} strokeWidth="1.6" />
              <path d={arcPath(a0 + 0.8, a1 - 0.8).split(' L ')[0]} fill="none" stroke={col} strokeWidth="4" opacity="0.9" filter="url(#rgGlow)" />
            </a>
          );
        })}
        <g className="rg-spin-rev">
          <circle cx={C} cy={C} r={166} fill="none" stroke="rgba(0,229,255,0.45)" strokeWidth="1.2" strokeDasharray="30 8 4 8" />
        </g>
        <circle cx={C} cy={C} r={150} fill="rgba(0,20,30,0.55)" stroke="rgba(0,229,255,0.2)" />
      </svg>
      {segs.map((s, i) => {
        const mid = -90 + i * span; const r = (RO + RI) / 2;
        const [x, y] = pt(mid, r);
        return (
          <div key={s.key} className="rg-label" style={{ left: `${(x / 600) * 100}%`, top: `${(y / 600) * 100}%` }}>
            <i style={{ color: TONE_COLOR[s.tone] }}>{s.icon}</i>
            <b>{s.name}</b>
            <strong style={{ color: s.tone === 'nd' ? '#ffc857' : s.tone === 'alert' ? '#ff8ae9' : '#eaffff', textShadow: `0 0 10px ${TONE_COLOR[s.tone]}` }}>{s.value ?? 'NO DATA'}</strong>
            <small>{s.value === null ? s.why : s.sub}</small>
          </div>
        );
      })}
      <a href="/?product=owner" className="rg-core" aria-label="Open Max chat">
        <div className="rg-orb"><span>MAX</span></div>
        <div className={`rg-core-status ${maxOk ? 'is-ok' : 'is-bad'}`}>{maxLabel}</div>
      </a>
    </div>
  );
}

/* ------------------------------------------------------------- suggestions */

type Suggestion = { key: string; tone: 'urgent' | 'warn' | 'info'; icon: ReactNode; title: string; detail: string; href: string; action: string; src: string };

function SuggestionStack({ items, failed }: { items: Suggestion[] | null; failed: string[] }) {
  const [q, setQ] = useState('');
  const ask = (e: React.FormEvent) => {
    e.preventDefault();
    const t = q.trim();
    window.location.href = t ? `/?product=owner&ask=${encodeURIComponent(t.slice(0, 2000))}` : '/?product=owner';
  };
  return (
    <section className="rg-hud">
      <div className="rg-h"><h2><Sparkles size={14} /> Max suggestions</h2><span className="rg-src">real data only</span></div>
      {items === null ? <div className="rg-loading">ANALYZING…</div> : items.length === 0 ? (
        <div className="rg-nodata" style={{ color: 'var(--rg-teal)', borderColor: 'var(--rg-line)' }}>NOTHING NEEDS ATTENTION<span>Checked overdue invoices, quotes, installs, leads and Max daily actions.</span></div>
      ) : (
        <ul className="rg-sugg">
          {items.map(s => (
            <li key={s.key} className={`is-${s.tone}`}>
              <div className="rg-sugg-t">{s.icon}<span>{s.title}</span></div>
              <div className="rg-sugg-d">{s.detail}</div>
              <div className="rg-sugg-f"><small>{s.src}</small><a href={s.href} className="rg-act">{s.action} <ArrowRight size={11} /></a></div>
            </li>
          ))}
        </ul>
      )}
      {failed.length > 0 && <div className="rg-src" style={{ color: 'var(--rg-amber)', marginTop: 6 }}>Sin datos: {failed.join(', ')}</div>}
      <form className="rg-ask" onSubmit={ask} role="search">
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Ask Max anything…" aria-label="Ask Max anything" maxLength={2000} />
        <button type="submit" aria-label="Open Max chat with this question"><Send size={15} /></button>
      </form>
    </section>
  );
}

function VoiceChannel({ voice }: { voice: Res | undefined }) {
  const [open, setOpen] = useState(false);
  const v = voice?.ok ? voice.data : null;
  const parts = v ? Object.values(v).filter((x: any) => x && typeof x === 'object') as any[] : [];
  const verified = parts.filter(p => p.verified === true).length;
  const tts = parts.find(p => p.tts_provider)?.tts_provider?.provider;
  return (
    <section className="rg-hud">
      <div className="rg-h"><h2><Mic size={14} /> Voice channel</h2><span className="rg-src">max/voice/status</span></div>
      <button type="button" className="rg-wave" onClick={() => setOpen(o => !o)} aria-expanded={open} aria-label="Open live voice with Max">
        {Array.from({ length: 44 }, (_, i) => {
          const t = i / 43; const col = t < 0.5 ? '#00e5ff' : t < 0.75 ? '#a46bff' : '#ff2bd6';
          return <i key={i} style={{ background: col, boxShadow: `0 0 6px ${col}`, animationDelay: `${((i * 53) % 13) / 10}s` }} />;
        })}
      </button>
      <div className="rg-kv"><span>Status</span><b style={{ color: voice === undefined ? undefined : v ? 'var(--rg-teal)' : 'var(--rg-amber)' }}>{voice === undefined ? '…' : v ? (verified ? 'READY' : 'NOT VERIFIED') : 'SIN DATOS'}</b></div>
      {v && <div className="rg-kv"><span>Checks verified</span><b>{verified} / {parts.length}</b></div>}
      {tts && <div className="rg-kv"><span>Voice</span><b>{tts}</b></div>}
      <div style={{ display: 'flex', justifyContent: 'center' }}>
        <button type="button" className="rg-btn" onClick={() => setOpen(o => !o)}>{open ? 'HIDE LIVE VOICE' : 'OPEN LIVE VOICE'}</button>
      </div>
      {open && <div className="rg-voice-pop"><LiveVoiceCall variant="inline" /></div>}
    </section>
  );
}

function NoData({ why }: { why: string }) { return <div className="rg-nodata">SIN DATOS · NO DATA<span>{why}</span></div>; }

/* ------------------------------------------------------------------- page */

export default function RingPreview() {
  const { data, loadedAt } = useRingData();
  const reduced = useReducedMotion();
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => { setNow(new Date()); const t = setInterval(() => setNow(new Date()), 30_000); return () => clearInterval(t); }, []);

  const ok = (k: string): any => (data[k]?.ok ? (data[k] as { ok: true; data: any }).data : null);
  const err = (k: string): string | null => (data[k] && !data[k]!.ok ? (data[k] as { ok: false; error: string }).error : null);
  const loading = Object.keys(data).length === 0;

  const quotes: any[] | null = ok('quotes')?.quotes ?? null;
  const jobs: any[] | null = ok('jobs')?.jobs ?? null;
  const activeJobs = jobs ? jobs.filter(j => !CLOSED_JOB.has(String(j.status || '').toLowerCase())) : null;
  const leadPipe: any[] | null = ok('leadPipeline')?.pipeline ?? null;
  const openLeadCount = leadPipe ? leadPipe.filter(r => !CLOSED_LEAD.has(String(r.status || '').toLowerCase())).reduce((a, r) => a + num(r.count), 0) : null;
  const newLeadCount = leadPipe ? num(leadPipe.find(r => String(r.status || '').toLowerCase() === 'new')?.count) : 0;
  const pstats = ok('prospectStats');
  const pipe: any[] | null = Array.isArray(ok('prospectPipeline')) ? ok('prospectPipeline') : null;
  const untouched = pipe ? pipe.filter(p => !p.status && !p.next_action && !p.notes) : null;
  const fin = ok('finance');
  const od = ok('overdue');
  const overdueCount = od ? num(od.count) : null;
  const sysH = ok('sysHealth');
  const services = sysH?.services ? Object.entries(sysH.services) : null;
  const integrity = services && services.length ? Math.round((services.filter(([, v]) => v === true).length / services.length) * 100) : null;
  const mh = ok('maxHealth');
  const maxOk = mh ? String(mh.status).toLowerCase() === 'healthy' || String(mh.status).toLowerCase() === 'ok' : null;
  const maxLabel = loading ? 'MAX CORE · CHECKING' : mh ? (maxOk ? 'MAX CORE ONLINE' : `MAX CORE ${String(mh.status).toUpperCase()}`) : 'MAX CORE · NO DATA';
  const commit = ok('maxStatus')?.current_commit?.hash as string | undefined;

  const openQuotes = quotes ? quotes.filter(q => !CLOSED_QUOTE.has(String(q.status || '').toLowerCase())) : null;
  const awaiting = quotes ? quotes.filter(q => AWAITING_REPLY.has(String(q.status || '').toLowerCase())) : null;
  const staleQuotes = awaiting ? awaiting.filter(q => (ageDays(q.sent_at || q.updated_at || q.created_at) ?? 0) >= 7) : null;

  const wrJobs = activeJobs ? activeJobs.filter(j => (j.business_unit || 'workroom') === 'workroom') : null;
  const wcJobs = activeJobs ? activeJobs.filter(j => j.business_unit === 'woodcraft') : null;
  const wrQuotes = openQuotes ? openQuotes.filter(q => (q.business_unit || 'workroom') === 'workroom') : null;
  const wrStale = staleQuotes ? staleQuotes.filter(q => (q.business_unit || 'workroom') === 'workroom').length : 0;
  const cprojects: any[] | null = ok('construction')?.projects ?? null;
  const cActive = cprojects ? cprojects.filter(p => String(p.status).toLowerCase() === 'active') : null;

  const segs: Segment[] = [
    { key: 'workroom', name: 'Workroom', icon: <Scissors size={16} />, value: wrJobs ? `${wrJobs.length}` : null, sub: wrQuotes ? `active jobs · ${wrQuotes.length} open quotes${wrStale ? ` · ${wrStale} stale` : ''}` : '', tone: !wrJobs ? 'nd' : wrStale ? 'warn' : 'ok', href: '/?product=workroom', why: err('jobs') || '' },
    { key: 'crm', name: 'CRM', icon: <Users size={16} />, value: ok('customers') ? `${num(ok('customers').total)}` : null, sub: `customers · ${openLeadCount ?? '—'} open leads`, tone: ok('customers') ? 'ok' : 'nd', href: '/?product=crm', why: err('customers') || '' },
    { key: 'lead', name: 'LeadForge', icon: <Target size={16} />, value: pstats ? `${num(pstats.in_pipeline)}` : null, sub: pstats ? `in pipeline · ${num(pstats.total_prospects)} prospects${untouched?.length ? ` · ${untouched.length} uncontacted` : ''}` : '', tone: !pstats ? 'nd' : untouched?.length ? 'warn' : 'ok', href: '/?product=lead', why: err('prospectStats') || '' },
    { key: 'finance', name: 'Finance', icon: <DollarSign size={16} />, value: fin?.outstanding ? compact(num(fin.outstanding.total)) : null, sub: fin?.outstanding ? `A/R · ${overdueCount ? `${overdueCount} overdue` : 'none overdue'}` : '', tone: !fin?.outstanding ? 'nd' : overdueCount ? 'alert' : 'ok', href: '/?screen=invoices', why: err('finance') || '' },
    { key: 'construction', name: 'Construction', icon: <Building2 size={16} />, value: cprojects ? `${cActive!.length}` : null, sub: cprojects ? `active of ${cprojects.length} projects · ${cActive!.reduce((a, p) => a + num(p.total_lots), 0)} lots` : '', tone: cprojects ? 'ok' : 'nd', href: '/?product=construction', why: err('construction') || '' },
    { key: 'craft', name: 'WoodCraft', icon: <TreePine size={16} />, value: wcJobs ? `${wcJobs.length}` : null, sub: 'active jobs', tone: wcJobs ? 'ok' : 'nd', href: '/?product=craft', why: err('jobs') || '' },
    { key: 'system', name: 'System', icon: <Activity size={16} />, value: integrity !== null ? `${integrity}%` : null, sub: services ? services.filter(([, v]) => v !== true).map(([k]) => `${k} down`).join(' · ') || 'all services up' : '', tone: integrity === null ? 'nd' : integrity < 100 ? 'warn' : 'ok', href: '/?product=system', why: err('sysHealth') || '' },
  ];

  // money in vs out, last 7 days (payment_date / expense_date)
  const flow = useMemo(() => {
    if (!now || loading) return null;
    const pays: any[] | null = ok('payments7')?.payments ?? null;
    const exps: any[] | null = ok('expenses7')?.expenses ?? null;
    const days = Array.from({ length: 7 }, (_, i) => ymd(addDays(now, i - 6)));
    const inBy = days.map(d => (pays || []).filter(p => String(p.payment_date || '').startsWith(d)).reduce((a, p) => a + num(p.amount), 0));
    const outBy = days.map(d => (exps || []).filter(e => String(e.expense_date || e.date || '').startsWith(d)).reduce((a, e) => a + num(e.amount), 0));
    return { days, inBy, outBy, hasIn: pays !== null, hasOut: exps !== null, totalIn: inBy.reduce((a, b) => a + b, 0), totalOut: outBy.reduce((a, b) => a + b, 0) };
  }, [now, loading, data]); // eslint-disable-line react-hooks/exhaustive-deps
  const flowMax = flow ? Math.max(1, ...flow.inBy, ...flow.outBy) : 1;

  // next install day (install_date on open jobs, today or later)
  const install: Install | undefined = useMemo(() => {
    if (!now || !activeJobs) return undefined;
    const today = ymd(now);
    const c = activeJobs.filter(j => j.install_date && String(j.install_date).slice(0, 10) >= today)
      .sort((a, b) => String(a.install_date).localeCompare(String(b.install_date)))[0];
    return c ? { date: String(c.install_date).slice(0, 10), job: c } : null;
  }, [now, activeJobs]);
  const wx = useInstallWeather(install);

  const suggestions: Suggestion[] | null = useMemo(() => {
    if (loading || !now) return null;
    const out: Suggestion[] = [];
    const today = ymd(now);
    if (od && num(od.count) > 0) {
      const list: any[] = od.overdue_invoices || [];
      const oldest = [...list].sort((a, b) => String(a.due_date || '').localeCompare(String(b.due_date || '')))[0];
      out.push({ key: 'overdue', tone: 'urgent', icon: <AlertTriangle size={14} />, title: 'Invoice recovery', action: 'REVIEW',
        detail: `${num(od.count)} overdue invoice${num(od.count) === 1 ? '' : 's'} totaling ${money(num(od.total_outstanding))}${oldest ? ` · oldest ${oldest.invoice_number || ''} due ${oldest.due_date || '?'}` : ''}.`, href: '/?screen=invoices', src: 'payments/overdue' });
    }
    if (staleQuotes && staleQuotes.length) {
      const o = [...staleQuotes].sort((a, b) => (ageDays(b.sent_at || b.updated_at) ?? 0) - (ageDays(a.sent_at || a.updated_at) ?? 0))[0];
      out.push({ key: 'stale', tone: 'warn', icon: <Zap size={14} />, title: 'Quote follow-up', action: 'FOLLOW UP',
        detail: `${staleQuotes.length} sent quote${staleQuotes.length === 1 ? '' : 's'} with no answer in 7+ days (${money(staleQuotes.reduce((a, q) => a + num(q.total), 0))}). Oldest: ${o.quote_number || ''} ${o.customer_name || ''}.`, href: '/?product=workroom&section=quotes', src: 'quotes-v2' });
    }
    const da = ok('dailyActions');
    if (da && Array.isArray(da.actions)) {
      const byType: Record<string, any[]> = {};
      da.actions.forEach((a: any) => { const t = String(a.type || 'action'); (byType[t] = byType[t] || []).push(a); });
      Object.entries(byType).forEach(([t, list]) => {
        const f = list[0];
        const href = f.entity_type === 'invoice' ? '/?screen=invoices' : f.entity_type === 'quote' ? '/?product=workroom&section=quotes' : f.entity_type === 'job' ? '/?product=workroom&section=jobs' : f.entity_type === 'lead' ? '/?product=lead' : '/?product=owner&screen=dashboard';
        out.push({ key: `da-${t}`, tone: 'info', icon: t === 'send_reminder' ? <Receipt size={14} /> : <FileText size={14} />,
          title: t === 'send_quote' ? 'Quotes ready to send' : t === 'send_reminder' ? 'Payment reminders' : titleCase(t),
          action: t === 'send_quote' ? 'OPEN QUOTES' : 'OPEN',
          detail: `${list.length} item${list.length === 1 ? '' : 's'} in Max's daily actions. Next: ${f.label || ''}${f.detail ? ` — ${f.detail}` : ''}`, href, src: 'lifecycle/daily-actions' });
      });
    }
    if (activeJobs) {
      const horizon = ymd(addDays(now, 7)), tomorrow = ymd(addDays(now, 1));
      const up: { j: any; f: string; v: string }[] = [];
      activeJobs.forEach(j => (['install_date', 'site_visit_date', 'scheduled_date'] as const).forEach(f => { const v = j[f] ? String(j[f]) : ''; if (v && v.slice(0, 10) >= today && v.slice(0, 10) <= horizon) up.push({ j, f, v }); }));
      up.sort((a, b) => a.v.localeCompare(b.v)).slice(0, 2).forEach(({ j, f, v }) => {
        const d = v.slice(0, 10); const when = d === today ? 'today' : d === tomorrow ? 'tomorrow' : new Date(`${d}T12:00:00`).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        const t = v.includes('T') ? parseDate(v) : null;
        out.push({ key: `up-${j.id}-${f}`, tone: d === today ? 'urgent' : 'info', icon: <CalendarClock size={14} />, action: 'OPEN JOB',
          title: `${f === 'install_date' ? 'Install' : f === 'site_visit_date' ? 'Site visit' : 'Scheduled'} ${when}${t ? ` ${t.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}` : ''}`,
          detail: `${j.job_number || ''} ${j.title || j.client_name || ''}`.trim(), href: j.business_unit === 'woodcraft' ? '/?product=craft&section=jobs' : '/?product=workroom&section=jobs', src: 'jobs' });
      });
    }
    const fq = ok('followups'), sl = ok('staleLeads');
    const leadN = Math.max(newLeadCount, num(fq?.total), num(sl?.total));
    if (leadN > 0) out.push({ key: 'leads', tone: 'warn', icon: <Target size={14} />, title: 'Lead follow-up', action: 'PRIORITIZE', detail: `${leadN} lead${leadN === 1 ? '' : 's'} waiting for contact (${newLeadCount} new · ${num(fq?.total)} queued · ${num(sl?.total)} stale).`, href: '/?product=lead', src: 'leads/pipeline · followups · stale' });
    if (untouched && untouched.length) {
      const top = [...untouched].sort((a, b) => num(b.score) - num(a.score))[0];
      out.push({ key: 'lf', tone: 'info', icon: <Radar size={14} />, title: 'LeadForge outreach', action: 'PRIORITIZE', detail: `${untouched.length} pipeline prospect${untouched.length === 1 ? '' : 's'} with no status, note or next action. Top score: ${top.business_name || ''} (${num(top.score)}).`, href: '/?product=lead', src: 'leadforge/prospect-pipeline' });
    }
    const rank = { urgent: 0, warn: 1, info: 2 } as const;
    return out.sort((a, b) => rank[a.tone] - rank[b.tone]).slice(0, 6);
  }, [loading, now, data, staleQuotes?.length, activeJobs?.length, newLeadCount, untouched?.length]); // eslint-disable-line react-hooks/exhaustive-deps
  const suggFailed = [['dailyActions', 'Max daily actions'], ['overdue', 'payments/overdue'], ['followups', 'followups'], ['staleLeads', 'leads/stale'], ['leadPipeline', 'leads/pipeline'], ['quotes', 'quotes'], ['jobs', 'jobs']]
    .filter(([k]) => err(k)).map(([, l]) => l);

  const sysLine = loading ? <>SYS · CHECKING…</> : <>SYS <b>{sysH ? String(sysH.status).toUpperCase() : 'NO DATA'}</b>{commit ? <> · BUILD {commit}</> : null}{integrity !== null ? <> · {integrity}% UP</> : null}</>;

  return (
    <div className="rg-root" data-ring-page>
      <div className="rg-floor" aria-hidden="true" />
      <div className="rg-scan" aria-hidden="true" />
      <div className="rg-shell">
        <CyberMenu sysLine={sysLine} />

        <main className="rg-center">
          <header className="rg-top">
            <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
              <div><h1>EMPIRE · MODULE RING</h1><small>LIVE BACKEND DATA · {loadedAt ? `SYNCED ${loadedAt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}` : 'SYNCING…'}</small></div>
              <span className="rg-badge">PREVIEW</span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
              <a href="/preview/cockpit" className="rg-btn">COCKPIT PREVIEW</a>
              <a href="/" className="rg-btn"><ArrowLeft size={13} /> CURRENT HOME</a>
            </div>
          </header>

          <div className="rg-stage">
            <div className="rg-a-ring">
              {loading ? <div className="rg-loading" style={{ padding: '120px 0' }}>INITIALIZING RING…</div> : <ModuleRing segs={segs} maxOk={maxOk} maxLabel={maxLabel} />}
            </div>

            <section className="rg-hud is-alert rg-a-overdue">
              <div className="rg-h"><h2><AlertTriangle size={14} /> Overdue invoices</h2></div>
              {loading ? <div className="rg-loading">…</div> : !od ? <NoData why={`payments/overdue ${err('overdue') || ''}`} /> : (
                <>
                  <div className="rg-big"><CountMoney value={num(od.total_outstanding)} reduced={reduced} /></div>
                  <div className="rg-sub">{num(od.count)} invoice{num(od.count) === 1 ? '' : 's'} past due</div>
                  <a href="/?screen=invoices" className="rg-link">{num(od.count) ? 'ACTION RECOMMENDED' : 'VIEW INVOICES'} <ArrowRight size={11} /></a>
                  <div className="rg-src" style={{ marginTop: 6 }}>payments/overdue · sent/partial invoices past due date</div>
                </>
              )}
            </section>

            <section className="rg-hud rg-a-quotes">
              <div className="rg-h"><h2><FileText size={14} /> Quotes awaiting reply</h2></div>
              {loading ? <div className="rg-loading">…</div> : !awaiting ? <NoData why={`quotes-v2 ${err('quotes') || ''}`} /> : (
                <>
                  <div className="rg-big"><CountInt value={awaiting.length} reduced={reduced} /></div>
                  <div className="rg-kv"><span>Total</span><b>{money(awaiting.reduce((a, q) => a + num(q.total), 0))}</b></div>
                  <div className="rg-kv"><span>7+ days, no answer</span><b>{staleQuotes!.length}</b></div>
                  <a href="/?product=workroom&section=quotes" className="rg-link">VIEW ALL <ArrowRight size={11} /></a>
                  <div className="rg-src" style={{ marginTop: 6 }}>quotes-v2 · status sent / proposal</div>
                </>
              )}
            </section>

            <section className="rg-hud rg-a-money">
              <div className="rg-h"><h2><DollarSign size={14} /> Money in vs out</h2><span className="rg-src">last 7 days</span></div>
              {!flow ? <div className="rg-loading">…</div> : !flow.hasIn && !flow.hasOut ? <NoData why="finance/payments and finance/expenses unavailable" /> : (
                <>
                  <div className="rg-bars" role="img" aria-label={`Money in ${money(flow.totalIn)}, out ${money(flow.totalOut)} over 7 days`}>
                    {flow.days.map((d, i) => (
                      <div key={d} className="rg-day" title={`${d}: in ${money(flow.inBy[i])} · out ${flow.hasOut ? money(flow.outBy[i]) : 'no data'}`}>
                        <i className="rg-in" style={{ height: `${(flow.inBy[i] / flowMax) * 100}%` }} />
                        {flow.hasOut && <i className="rg-out" style={{ height: `${(flow.outBy[i] / flowMax) * 100}%` }} />}
                      </div>
                    ))}
                  </div>
                  <div className="rg-days">{flow.days.map(d => <span key={d}>{new Date(`${d}T12:00:00`).toLocaleDateString('en-US', { weekday: 'narrow' })}</span>)}</div>
                  <div className="rg-kv" style={{ marginTop: 6 }}><span style={{ color: 'var(--rg-cyan)' }}>IN (payments)</span><b>{flow.hasIn ? money(flow.totalIn) : 'SIN DATOS'}</b></div>
                  <div className="rg-kv"><span style={{ color: 'var(--rg-mag)' }}>OUT (expenses)</span><b>{flow.hasOut ? money(flow.totalOut) : 'SIN DATOS'}</b></div>
                  <div className="rg-kv"><span>NET</span><b>{flow.hasIn && flow.hasOut ? `${flow.totalIn - flow.totalOut >= 0 ? '+' : ''}${money(flow.totalIn - flow.totalOut)}` : 'SIN DATOS'}</b></div>
                  <div className="rg-src" style={{ marginTop: 4 }}>finance/payments · finance/expenses (recorded expenses only)</div>
                </>
              )}
            </section>

            <section className="rg-hud rg-a-weather">
              <div className="rg-h"><h2><CloudSun size={14} /> Weather · install day</h2></div>
              {install === undefined ? <div className="rg-loading">…</div> : install === null ? <NoData why="No upcoming install date on open jobs" /> : (
                <>
                  <div className="rg-sub">{new Date(`${install.date}T12:00:00`).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })} · {install.job.job_number || install.job.title}</div>
                  {!wx ? <div className="rg-loading">…</div> : !wx.ok ? <NoData why={`Forecast: ${wx.error}`} /> : (() => {
                    const d = wx.data?.daily || {};
                    return (
                      <>
                        <div className="rg-wx"><CloudSun size={34} color="#00e5ff" /><div><div className="rg-big">{Math.round(num(d.temperature_2m_max?.[0]))}°F</div><div className="rg-sub">{WX[num(d.weather_code?.[0])] || `code ${d.weather_code?.[0]}`}</div></div></div>
                        <div className="rg-kv"><span>Low</span><b>{Math.round(num(d.temperature_2m_min?.[0]))}°F</b></div>
                        <div className="rg-kv"><span>Wind · precip</span><b>{Math.round(num(d.wind_speed_10m_max?.[0]))} mph · {num(d.precipitation_probability_max?.[0])}%</b></div>
                      </>
                    );
                  })()}
                  <div className="rg-src" style={{ marginTop: 4 }}>open-meteo · Washington, DC area</div>
                </>
              )}
            </section>

            <section className="rg-hud rg-a-headline rg-headline">
              <div className="rg-h" style={{ justifyContent: 'center' }}><h2>Today&apos;s headline</h2></div>
              {loading ? <div className="rg-loading">…</div> : !fin?.outstanding ? <NoData why={`finance/dashboard ${err('finance') || ''}`} /> : (
                <>
                  <div className="rg-big"><CountMoney value={num(fin.outstanding.total)} reduced={reduced} /></div>
                  <div className="rg-sub" style={{ letterSpacing: '0.16em', textTransform: 'uppercase' }}>Owed to Empire · {num(fin.outstanding.count)} open invoices</div>
                  <div className="rg-sub" style={{ marginTop: 4, color: overdueCount ? 'var(--rg-mag)' : 'var(--rg-teal)' }}>
                    {overdueCount ? `${money(num(od.total_outstanding))} of it overdue` : 'Nothing overdue'} · collected this month {money(num(fin.revenue?.mtd))}
                  </div>
                  <div className="rg-src" style={{ marginTop: 4 }}>finance/dashboard · payments/overdue</div>
                </>
              )}
            </section>

            <section className="rg-hud rg-a-team">
              <div className="rg-h"><h2><UsersRound size={14} /> Team status</h2></div>
              <NoData why="No crew / presence source in the backend (no on-site, in-office or offline data)" />
              {mh && <div className="rg-kv" style={{ marginTop: 8 }}><span>AI desks online (Max, not people)</span><b>{num(mh.desks_online)}</b></div>}
            </section>
          </div>
        </main>

        <aside className="rg-right">
          <section className="rg-hud">
            <div className="rg-max-top">
              <div><b>MAX AI · {mh ? (maxOk ? 'ACTIVE' : String(mh.status).toUpperCase()) : loading ? '…' : 'NO DATA'}</b><div className="rg-src">{mh ? `${num(mh.desks_online)} desks · Telegram ${mh.telegram_configured ? 'on' : 'off'}` : 'max/health'}</div></div>
              {now && <div className="rg-clock">{now.toLocaleDateString('en-US', { weekday: 'short', month: '2-digit', day: '2-digit', year: 'numeric' })}<br />{now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</div>}
            </div>
          </section>
          <SuggestionStack items={suggestions} failed={suggFailed} />
          <VoiceChannel voice={data.maxVoice} />
        </aside>
      </div>
    </div>
  );
}
