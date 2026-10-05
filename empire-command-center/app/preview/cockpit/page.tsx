'use client';
/**
 * /preview/cockpit — "cockpit radar" home PREVIEW (2026-10-03).
 *
 * Does not replace the current home (app/page.tsx). Every number on this page
 * comes from an existing backend endpoint; when a source is missing or fails,
 * the widget shows a labeled "SIN DATOS · NO DATA" state instead of a value.
 *
 * Sources (all GET, same-origin /api/v1 proxy or localhost:8000 via lib/api):
 *   quotes-v2            open quotes + pipeline donut (test quotes excluded by the API default)
 *   jobs, jobs/pipeline  active jobs, radar blips, stage bar meters
 *   jobs/calendar        today's schedule (+ job dates)
 *   leads/pipeline       CRM lead counts by status; leads/hot + leads/stale = lead blips
 *   NOTE: trailing-slash lists (/leads/, /tasks/) are avoided on purpose: through the
 *   studio proxy Next 308s them to no-slash and FastAPI then 307s to https://127.0.0.1:8000.
 *   leads/leadforge/...  LeadForge prospect pipeline (radar blips, tile)
 *   finance/dashboard    A/R outstanding
 *   finance/payments     collected this month / last month (revenue pace)
 *   crm/customers        customer count
 *   system/health, system/stats, max/health, max/voice/status
 *   lifecycle/daily-actions (Max's founder action list), payments/overdue,
 *   leads/followups/queue, leads/stale   -> Max Suggestions
 */
import { cloneElement, isValidElement, useCallback, useEffect, useMemo, useRef, useState } from 'react';
import type { ReactElement, ReactNode } from 'react';
import { API } from '../../lib/api';
import { NAV_GROUPS } from '../../components/layout/LeftNav';
import type { NavItem } from '../../components/layout/LeftNav';
import LiveVoiceCall from '../../components/LiveVoiceCall';
import { Radar, ArrowLeft, MessageSquare, Mic, Send, ChevronRight } from 'lucide-react';
import './cockpit.css';

/* ------------------------------------------------------------------ data */

type Res = { ok: true; data: any } | { ok: false; error: string };
type Loaded = Record<string, Res | undefined>;

const ENDPOINTS: Record<string, string> = {
  quotes: '/quotes-v2?limit=500',
  jobs: '/jobs?limit=500',
  jobPipeline: '/jobs/pipeline',
  leadPipeline: '/leads/pipeline',
  hotLeads: '/leads/hot?limit=100',
  prospectStats: '/leads/leadforge/prospects/stats',
  prospectPipeline: '/leads/leadforge/prospect-pipeline?limit=50',
  finance: '/finance/dashboard',
  payments: '/finance/payments?limit=500',
  customers: '/crm/customers?limit=1',
  sysHealth: '/system/health',
  sysStats: '/system/stats',
  maxHealth: '/max/health',
  maxVoice: '/max/voice/status',
  dailyActions: '/lifecycle/daily-actions',
  overdue: '/payments/overdue',
  followups: '/leads/followups/queue',
  staleLeads: '/leads/stale',
};

async function getJson(path: string): Promise<Res> {
  try {
    const res = await fetch(`${API}${path}`, { cache: 'no-store', signal: AbortSignal.timeout(12000) });
    if (!res.ok) return { ok: false, error: `HTTP ${res.status}` };
    return { ok: true, data: await res.json() };
  } catch (e: any) {
    return { ok: false, error: e?.name === 'TimeoutError' ? 'timeout' : 'unreachable' };
  }
}

function useCockpitData() {
  const [data, setData] = useState<Loaded>({});
  const [loadedAt, setLoadedAt] = useState<Date | null>(null);
  const load = useCallback(async () => {
    const today = ymd(new Date());
    const extra: Record<string, string> = { calendar: `/jobs/calendar?date_from=${today}&date_to=${today}` };
    const all = { ...ENDPOINTS, ...extra };
    const entries = await Promise.all(Object.entries(all).map(async ([k, p]) => [k, await getJson(p)] as const));
    setData(Object.fromEntries(entries));
    setLoadedAt(new Date());
  }, []);
  useEffect(() => {
    load();
    const t = setInterval(load, 60_000);
    return () => clearInterval(t);
  }, [load]);
  return { data, loadedAt };
}

/* --------------------------------------------------------------- helpers */

function ymd(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}
function parseDate(s: any): Date | null {
  if (!s || typeof s !== 'string') return null;
  const t = Date.parse(s.includes('T') ? s : s.replace(' ', 'T'));
  return Number.isFinite(t) ? new Date(t) : null;
}
function ageDays(s: any): number | null {
  const d = parseDate(s);
  return d ? Math.max(0, (Date.now() - d.getTime()) / 86_400_000) : null;
}
const usd0 = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', maximumFractionDigits: 0 });
const usd2 = new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD', minimumFractionDigits: 2, maximumFractionDigits: 2 });
function money(n: number): string { return Math.abs(n) >= 10_000 ? usd0.format(n) : usd2.format(n); }
function num(n: any): number { const v = Number(n); return Number.isFinite(v) ? v : 0; }
function hash01(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
  return ((h >>> 0) % 10_000) / 10_000;
}
function titleCase(s: string): string { return s.replace(/[_-]+/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }

const CLOSED_QUOTE = new Set(['accepted', 'approved', 'cancelled', 'canceled', 'declined', 'rejected', 'expired', 'converted', 'won', 'lost', 'archived', 'void']);
const CLOSED_JOB = new Set(['completed', 'complete', 'cancelled', 'canceled', 'closed', 'archived', 'done']);
const CLOSED_LEAD = new Set(['won', 'lost', 'closed', 'converted', 'archived', 'disqualified', 'dead']);
const DONE_TASK = new Set(['done', 'cancelled', 'canceled', 'completed']);

function useReducedMotion(): boolean {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const on = () => setReduced(mq.matches);
    on();
    mq.addEventListener('change', on);
    return () => mq.removeEventListener('change', on);
  }, []);
  return reduced;
}

function useCountUp(target: number | null, reduced: boolean, ms = 1300): number {
  const [v, setV] = useState(0);
  const from = useRef(0);
  useEffect(() => {
    if (target === null) return;
    if (reduced) { setV(target); from.current = target; return; }
    const start = performance.now();
    const a = from.current;
    let raf = 0;
    const step = (now: number) => {
      const p = Math.min(1, (now - start) / ms);
      const e = 1 - Math.pow(1 - p, 3);
      setV(a + (target - a) * e);
      if (p < 1) raf = requestAnimationFrame(step);
      else from.current = target;
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, reduced, ms]);
  return v;
}

/* -------------------------------------------------------------- nav links */

function navHref(item: NavItem): string {
  if (item.kind === 'daily-summary') return '/?product=owner&screen=dashboard';
  if (item.kind === 'screen' && item.screen) {
    if (item.screen === 'pricing-studio') return '/?screen=pricing-studio';
    return `/?screen=${encodeURIComponent(item.screen)}`;
  }
  if (item.id === 'workroom') return '/?product=workroom';
  if (item.id === 'craft') return '/?product=craft';
  return `/?product=${encodeURIComponent(item.id)}`;
}

function sizedIcon(icon: ReactNode, size: number): ReactNode {
  return isValidElement(icon) ? cloneElement(icon as ReactElement<{ size?: number }>, { size }) : icon;
}

const HEX_POINTS = '28,2 53,16.5 53,45.5 28,60 3,45.5 3,16.5';
const HEX_INNER = '28,8 48,19.5 48,42.5 28,54 8,42.5 8,19.5';

function HexButton({ href, label, icon, active, status, dot }: {
  href: string; label: string; icon: ReactNode; active?: boolean; status?: string; dot?: string;
}) {
  const cls = ['ck-hex', active ? 'is-active' : '', status === 'dev' ? 'is-dev' : '', status === 'planned' ? 'is-planned' : ''].join(' ');
  const tip = status && status !== 'active' ? `${label} · ${status}` : label;
  return (
    <a href={href} className={cls} aria-label={tip} aria-current={active ? 'page' : undefined}>
      <svg viewBox="0 0 56 62" aria-hidden="true">
        <polygon className="ck-hex-shape" points={HEX_POINTS} />
        <polygon className="ck-hex-inner" points={HEX_INNER} />
      </svg>
      <span className="ck-hex-icon">{sizedIcon(icon, 20)}</span>
      {dot && <span className="ck-hex-dot" style={{ background: dot, color: dot }} />}
      <span className="ck-hex-tip">{tip}</span>
    </a>
  );
}

function HexStrip() {
  return (
    <nav className="ck-strip" aria-label="Empire modules">
      <div className="ck-strip-head">EMPIRE</div>
      <div className="ck-strip-scroll">
        <HexButton href="/preview/cockpit" label="Cockpit (preview)" icon={<Radar size={20} />} active />
        {NAV_GROUPS.map(group => (
          <div key={group.key} style={{ display: 'contents' }}>
            <div className="ck-group-label">{group.label.split(' ')[0]}</div>
            {group.items.map(item => (
              <HexButton key={item.id} href={navHref(item)} label={item.name} icon={item.icon} status={item.status} dot={item.color} />
            ))}
          </div>
        ))}
      </div>
    </nav>
  );
}

/* ---------------------------------------------------------------- widgets */

function NoData({ why }: { why: string }) {
  return <div className="ck-nodata">SIN DATOS · NO DATA<span>{why}</span></div>;
}
function Panel({ title, src, className, children }: { title: string; src?: string; className?: string; children: ReactNode }) {
  return (
    <section className={`ck-panel ${className || ''}`}>
      <div className="ck-ph"><h2>{title}</h2>{src && <span className="ck-src">{src}</span>}</div>
      {children}
    </section>
  );
}

type TileSpec = { label: string; value: number | null; fmt: 'int' | 'money'; sub?: string; why?: string; href?: string };

function HexTile({ t, reduced }: { t: TileSpec; reduced: boolean }) {
  const v = useCountUp(t.value, reduced);
  const nd = t.value === null;
  const body = (
    <div className={`ck-tile ${nd ? 'is-nd' : ''}`}>
      <div className="ck-tile-o" />
      <div className="ck-tile-i">
        <div className="ck-tile-l">{t.label}</div>
        <div className="ck-tile-v">{nd ? 'SIN DATOS' : t.fmt === 'money' ? money(v) : Math.round(v).toLocaleString('en-US')}</div>
        <div className="ck-tile-s">{nd ? t.why : t.sub}</div>
      </div>
    </div>
  );
  return t.href ? <a href={t.href} title={t.label}>{body}</a> : body;
}

type Blip = { id: string; group: string; label: string; kind: 'job' | 'lead' | 'prospect'; age: number; value: number; detail: string; href: string };

const GROUP_COLORS = ['#00e5ff', '#14f1c6', '#a46bff', '#ffc857', '#ff6bd6', '#6be0ff'];

function RadarPanel({ blips, sources, reduced, note }: { blips: Blip[] | null; sources: { label: string; ok: boolean }[]; reduced: boolean; note?: string }) {
  const [focus, setFocus] = useState<Blip | null>(null);
  const groups = useMemo(() => {
    if (!blips) return [];
    const order: string[] = [];
    blips.forEach(b => { if (!order.includes(b.group)) order.push(b.group); });
    return order.map((g, i) => ({ g, color: GROUP_COLORS[i % GROUP_COLORS.length], count: blips.filter(b => b.group === g).length }));
  }, [blips]);
  const C = 200, R = 184;
  const maxVal = Math.max(1, ...(blips || []).map(b => b.value));
  const placed = useMemo(() => {
    if (!blips || groups.length === 0) return [];
    const span = 360 / groups.length;
    return blips.map(b => {
      const gi = groups.findIndex(x => x.g === b.group);
      const ang = (gi * span + span * (0.12 + 0.76 * hash01(b.id)) - 90) * Math.PI / 180;
      const dist = 0.14 + 0.82 * Math.min(1, Math.log1p(b.age) / Math.log1p(365));
      return { b, x: C + Math.cos(ang) * R * dist, y: C + Math.sin(ang) * R * dist, r: 3.5 + 5 * Math.sqrt(b.value / maxVal), color: groups[gi].color };
    });
  }, [blips, groups, maxVal]);
  const ticks = Array.from({ length: 72 }, (_, i) => i * 5);
  const span = groups.length ? 360 / groups.length : 0;
  const failed = sources.filter(s => !s.ok);

  return (
    <div className="ck-radar-wrap">
      <div className="ck-radar">
        <div className="ck-sweep" />
        <svg viewBox="0 0 400 400" role="img" aria-label={`Radar: ${blips ? blips.length : 0} open leads and jobs`}>
          <defs>
            <radialGradient id="ckRadarBg" cx="50%" cy="50%" r="50%">
              <stop offset="0%" stopColor="rgba(0,229,255,0.10)" />
              <stop offset="100%" stopColor="rgba(0,229,255,0.01)" />
            </radialGradient>
            <filter id="ckGlow" x="-200%" y="-200%" width="500%" height="500%">
              <feGaussianBlur stdDeviation="2.4" result="b" />
              <feMerge><feMergeNode in="b" /><feMergeNode in="SourceGraphic" /></feMerge>
            </filter>
          </defs>
          <circle cx={C} cy={C} r={R} fill="url(#ckRadarBg)" stroke="rgba(0,229,255,0.55)" strokeWidth="1.2" />
          {[0.25, 0.5, 0.75].map(f => <circle key={f} cx={C} cy={C} r={R * f} fill="none" stroke="rgba(0,229,255,0.18)" strokeDasharray="2 4" />)}
          <line x1={C - R} y1={C} x2={C + R} y2={C} stroke="rgba(0,229,255,0.15)" />
          <line x1={C} y1={C - R} x2={C} y2={C + R} stroke="rgba(0,229,255,0.15)" />
          {ticks.map(a => {
            const rad = (a - 90) * Math.PI / 180; const long = a % 30 === 0;
            return <line key={a} x1={C + Math.cos(rad) * R} y1={C + Math.sin(rad) * R} x2={C + Math.cos(rad) * (R + (long ? 9 : 4))} y2={C + Math.sin(rad) * (R + (long ? 9 : 4))} stroke="rgba(0,229,255,0.5)" strokeWidth={long ? 1.2 : 0.6} />;
          })}
          {/* sector dividers + labels (angle = type / source) */}
          {groups.length > 1 && groups.map((g, i) => {
            const rad = (i * span - 90) * Math.PI / 180;
            return <line key={g.g} x1={C} y1={C} x2={C + Math.cos(rad) * R} y2={C + Math.sin(rad) * R} stroke="rgba(164,107,255,0.25)" strokeDasharray="3 5" />;
          })}
          {[{ f: 0.14, t: 'NEW' }, { f: 0.55, t: '~1 MO' }, { f: 0.96, t: '1 YR+' }].map(r => (
            <text key={r.t} x={C + 4} y={C - R * r.f - 3} fill="rgba(111,151,166,0.9)" fontSize="8" fontFamily="monospace">{r.t}</text>
          ))}
          {placed.map(({ b, x, y, r, color }) => (
            <a key={b.id} href={b.href} className="ck-blip" onMouseEnter={() => setFocus(b)} onFocus={() => setFocus(b)} aria-label={`${b.label}: ${b.detail}`}>
              <title>{`${b.label} — ${b.detail}`}</title>
              {!reduced && <circle className="ck-ping" cx={x} cy={y} r={r} fill="none" stroke={color} strokeWidth="1" style={{ animationDelay: `${(hash01(b.id + 'd') * 2.6).toFixed(2)}s` }} />}
              <circle className="ck-core" cx={x} cy={y} r={r} fill={color} filter="url(#ckGlow)" opacity="0.95" />
            </a>
          ))}
          <circle cx={C} cy={C} r="3" fill="#00e5ff" filter="url(#ckGlow)" />
        </svg>
      </div>
      <div>
        {blips === null ? <div className="ck-loading">SCANNING…</div> : (
          <div className="ck-legend">
            {groups.length === 0 && <NoData why="No open leads or active jobs returned by the API" />}
            {groups.map(g => (
              <div key={g.g} className="ck-legend-row" style={{ color: g.color }}>
                <span className="ck-legend-dot" />
                <span style={{ color: 'var(--ck-text)' }}>{g.g}</span>
                <b style={{ marginLeft: 'auto', color: '#eaffff' }}>{g.count}</b>
              </div>
            ))}
            <small>Angle = type / source · distance = age (center = new) · size = value / score</small>
            {note && <small>{note}</small>}
            {failed.length > 0 && <small style={{ color: 'var(--ck-amber)' }}>Sin datos: {failed.map(f => f.label).join(', ')}</small>}
            <div className="ck-focus" aria-live="polite">
              {focus ? (<><b>{focus.label}</b><br />{focus.detail}<br /><span style={{ color: 'var(--ck-muted)' }}>{focus.group}</span></>)
                : <span style={{ color: 'var(--ck-muted)' }}>Hover a blip for details · tap to open</span>}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MaxOrb({ health, voice }: { health: Res | undefined; voice: Res | undefined }) {
  const [voiceOpen, setVoiceOpen] = useState(false);
  const meridians = [0, 30, 60, 90, 120, 150];
  const h = health?.ok ? health.data : null;
  const v = voice?.ok ? voice.data : null;
  const tts = v ? Object.values(v).find((x: any) => x && typeof x === 'object' && x.tts_provider) as any : null;
  const voiceReady = v ? Object.values(v).some((x: any) => x && typeof x === 'object' && x.verified === true) : null;
  return (
    <div className="ck-max">
      <a href="/?product=owner" className="ck-orb" aria-label="Open Max chat" title="Open Max chat">
        <svg viewBox="0 0 200 200" aria-hidden="true">
          <circle cx="100" cy="100" r="72" fill="none" stroke="rgba(0,229,255,0.85)" strokeWidth="1.2" />
          <g className="ck-orb-spin">
            {meridians.map(m => (
              <ellipse key={m} cx="100" cy="100" rx={Math.abs(Math.cos(m * Math.PI / 180)) * 72 + 0.5} ry="72" fill="none" stroke={m % 60 === 0 ? 'rgba(0,229,255,0.7)' : 'rgba(164,107,255,0.6)'} strokeWidth="0.8" />
            ))}
          </g>
          {[-48, -24, 0, 24, 48].map(y => (
            <ellipse key={y} cx="100" cy={100 + y} rx={Math.sqrt(72 * 72 - y * y)} ry={Math.sqrt(72 * 72 - y * y) * 0.18} fill="none" stroke="rgba(20,241,198,0.45)" strokeWidth="0.7" />
          ))}
          <circle cx="100" cy="100" r="16" fill="rgba(0,229,255,0.25)" />
          <circle cx="100" cy="100" r="6" fill="#bff8ff" />
          <text x="100" y="188" textAnchor="middle" fill="#00e5ff" fontSize="12" fontFamily="monospace" letterSpacing="4">MAX</text>
        </svg>
      </a>
      <div className="ck-wave" aria-hidden="true">
        {Array.from({ length: 22 }, (_, i) => <i key={i} style={{ animationDelay: `${((i * 37) % 14) / 10}s` }} />)}
      </div>
      <div className="ck-max-status">
        {health === undefined ? 'checking Max…' : h ? (
          <>Max <b>{String(h.status || 'unknown').toUpperCase()}</b> · {num(h.desks_online)} desks online<br />
            Telegram {h.telegram_configured ? <b>configured</b> : 'not configured'}
            {voiceReady !== null && <> · voice {voiceReady ? <b>ready</b> : 'not verified'}{tts?.tts_provider?.provider ? ` (${tts.tts_provider.provider})` : ''}</>}
          </>
        ) : <span style={{ color: 'var(--ck-amber)' }}>SIN DATOS · Max health {health && !health.ok ? health.error : ''}</span>}
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
        <a href="/?product=owner" className="ck-btn"><MessageSquare size={14} /> CHAT</a>
        <button type="button" className="ck-btn" onClick={() => setVoiceOpen(o => !o)} aria-expanded={voiceOpen}><Mic size={14} /> {voiceOpen ? 'HIDE VOICE' : 'LIVE VOICE'}</button>
      </div>
      {voiceOpen && <div className="ck-voice-pop"><LiveVoiceCall variant="inline" /></div>}
    </div>
  );
}

function Gauge({ pace, reduced }: { pace: number | null; reduced: boolean }) {
  const [shown, setShown] = useState(0);
  useEffect(() => {
    if (pace === null) return;
    const t = setTimeout(() => setShown(Math.min(200, Math.max(0, pace))), reduced ? 0 : 120);
    return () => clearTimeout(t);
  }, [pace, reduced]);
  const ang = -180 + (shown / 200) * 180; // 0% -> left, 100% -> top, 200% -> right
  const arc = (from: number, to: number, r: number) => {
    const p = (deg: number) => [150 + Math.cos(deg * Math.PI / 180) * r, 150 + Math.sin(deg * Math.PI / 180) * r];
    const [x1, y1] = p(from), [x2, y2] = p(to);
    return `M ${x1} ${y1} A ${r} ${r} 0 ${to - from > 180 ? 1 : 0} 1 ${x2} ${y2}`;
  };
  return (
    <svg className="ck-gauge" viewBox="0 0 300 175" role="img" aria-label={pace === null ? 'Revenue pace: no data' : `Revenue pace ${Math.round(pace)} percent`}>
      <path d={arc(-180, 0, 120)} fill="none" stroke="rgba(0,229,255,0.15)" strokeWidth="14" />
      <path d={arc(-180, -90, 120)} fill="none" stroke="rgba(164,107,255,0.55)" strokeWidth="3" />
      <path d={arc(-90, -36, 120)} fill="none" stroke="rgba(20,241,198,0.75)" strokeWidth="3" />
      <path d={arc(-36, 0, 120)} fill="none" stroke="rgba(0,229,255,0.9)" strokeWidth="3" />
      {Array.from({ length: 41 }, (_, i) => {
        const d = -180 + i * 4.5; const long = i % 5 === 0; const rad = d * Math.PI / 180;
        return <line key={i} x1={150 + Math.cos(rad) * 104} y1={150 + Math.sin(rad) * 104} x2={150 + Math.cos(rad) * (long ? 92 : 98)} y2={150 + Math.sin(rad) * (long ? 92 : 98)} stroke="rgba(0,229,255,0.6)" strokeWidth={long ? 1.4 : 0.7} />;
      })}
      {[0, 50, 100, 150, 200].map(v => {
        const rad = (-180 + v * 0.9) * Math.PI / 180;
        return <text key={v} x={150 + Math.cos(rad) * 78} y={150 + Math.sin(rad) * 78 + 3} textAnchor="middle" fill="rgba(111,151,166,0.95)" fontSize="9" fontFamily="monospace">{v}%</text>;
      })}
      {pace !== null && (
        <g className="ck-needle" style={{ transform: `rotate(${ang + 180}deg)` }}>
          <line x1="150" y1="150" x2="40" y2="150" stroke="#00e5ff" strokeWidth="2.5" strokeLinecap="round" style={{ filter: 'drop-shadow(0 0 6px #00e5ff)' }} />
        </g>
      )}
      <circle cx="150" cy="150" r="7" fill="#020407" stroke="#00e5ff" strokeWidth="2" />
      <text x="150" y="128" textAnchor="middle" fill={pace === null ? '#ffc857' : '#eaffff'} fontSize={pace === null ? 12 : 22} fontWeight="800" fontFamily="monospace">{pace === null ? 'SIN DATOS' : `${Math.round(pace)}%`}</text>
    </svg>
  );
}

function Donut({ segs, center, sub }: { segs: { label: string; value: number; color: string }[]; center: string; sub: string }) {
  const total = segs.reduce((a, s) => a + s.value, 0) || 1;
  const R = 58, L = 2 * Math.PI * R;
  let acc = 0;
  return (
    <svg className="ck-donut" viewBox="0 0 150 150" role="img" aria-label="Quote pipeline by status">
      <circle cx="75" cy="75" r={R} fill="none" stroke="rgba(0,229,255,0.1)" strokeWidth="14" />
      {segs.map(s => {
        const len = (s.value / total) * L; const off = acc; acc += len;
        return <circle key={s.label} className="ck-seg" cx="75" cy="75" r={R} fill="none" stroke={s.color} strokeWidth="14" strokeDasharray={`${Math.max(0, len - 1.5)} ${L}`} strokeDashoffset={-off} transform="rotate(-90 75 75)" style={{ filter: `drop-shadow(0 0 4px ${s.color})` }} />;
      })}
      <text x="75" y="74" textAnchor="middle" fill="#eaffff" fontSize="15" fontWeight="800" fontFamily="monospace">{center}</text>
      <text x="75" y="90" textAnchor="middle" fill="rgba(111,151,166,0.95)" fontSize="8" fontFamily="monospace">{sub}</text>
    </svg>
  );
}

type Suggestion = { key: string; tone: 'urgent' | 'warn' | 'info'; title: string; detail: string; href: string; src: string };

function MaxSuggestions({ items, failed }: { items: Suggestion[] | null; failed: string[] }) {
  const [q, setQ] = useState('');
  const ask = (e: React.FormEvent) => {
    e.preventDefault();
    const text = q.trim();
    window.location.href = text ? `/?product=owner&ask=${encodeURIComponent(text.slice(0, 2000))}` : '/?product=owner';
  };
  return (
    <div className="ck-sugg">
      {items === null ? <div className="ck-loading">ANALYZING…</div> : items.length === 0 ? (
        <div className="ck-sugg-empty">Nothing needs attention right now · nada pendiente<span>Checked overdue invoices, stale quotes, upcoming installs, uncontacted leads and Max daily actions.</span></div>
      ) : (
        <ul className="ck-sugg-list">
          {items.map(s => (
            <li key={s.key}>
              <a href={s.href} className={`ck-sugg-card is-${s.tone}`}>
                <span className="ck-sugg-hex" aria-hidden="true" />
                <span className="ck-sugg-body"><b>{s.title}</b><span>{s.detail}</span><small>{s.src}</small></span>
                <ChevronRight size={16} className="ck-sugg-go" />
              </a>
            </li>
          ))}
        </ul>
      )}
      {failed.length > 0 && <div className="ck-src" style={{ textAlign: 'left', color: 'var(--ck-amber)', marginTop: 6 }}>Sin datos: {failed.join(', ')}</div>}
      <form className="ck-ask" onSubmit={ask} role="search">
        <input value={q} onChange={e => setQ(e.target.value)} placeholder="Ask Max anything…" aria-label="Ask Max anything" maxLength={2000} />
        <button type="submit" aria-label="Open Max chat with this question"><Send size={15} /></button>
      </form>
    </div>
  );
}

/* ------------------------------------------------------------------- page */

const STATUS_COLORS: Record<string, string> = {
  draft: '#2a7f8f', sent: '#00e5ff', proposal: '#14f1c6', founder_review: '#a46bff', accepted: '#6bff9e', cancelled: '#3a4650',
};

export default function CockpitPreview() {
  const { data, loadedAt } = useCockpitData();
  const reduced = useReducedMotion();
  const [now, setNow] = useState<Date | null>(null);
  useEffect(() => { setNow(new Date()); const t = setInterval(() => setNow(new Date()), 30_000); return () => clearInterval(t); }, []);

  const ok = (k: string) => (data[k]?.ok ? (data[k] as { ok: true; data: any }).data : null);
  const err = (k: string) => (data[k] && !data[k]!.ok ? (data[k] as { ok: false; error: string }).error : null);
  const loading = Object.keys(data).length === 0;

  const quotes: any[] | null = ok('quotes')?.quotes ?? null;
  const jobs: any[] | null = ok('jobs')?.jobs ?? null;
  const leadPipe: any[] | null = ok('leadPipeline')?.pipeline ?? null;
  const openLeadCount = leadPipe ? leadPipe.filter(r => !CLOSED_LEAD.has(String(r.status || '').toLowerCase())).reduce((a, r) => a + num(r.count), 0) : null;
  const newLeadCount = leadPipe ? num(leadPipe.find(r => String(r.status || '').toLowerCase() === 'new')?.count) : 0;
  const leads: any[] | null = (ok('hotLeads') || ok('staleLeads'))
    ? Array.from(new Map([...(ok('hotLeads')?.leads || []), ...(ok('staleLeads')?.leads || [])].map((l: any) => [String(l.id), l])).values())
    : null;
  const pipe: any[] | null = Array.isArray(ok('prospectPipeline')) ? ok('prospectPipeline') : null;
  const payments: any[] | null = ok('payments')?.payments ?? null;

  const openQuotes = quotes ? quotes.filter(q => !CLOSED_QUOTE.has(String(q.status || '').toLowerCase())) : null;
  const activeJobs = jobs ? jobs.filter(j => !CLOSED_JOB.has(String(j.status || '').toLowerCase())) : null;
  const openLeads = leads ? leads.filter(l => !CLOSED_LEAD.has(String(l.status || '').toLowerCase())) : null;

  // money collected (finance/payments, by payment_date)
  const pay = useMemo(() => {
    if (!payments || !now) return null;
    const cur = ymd(now).slice(0, 7);
    const prevD = new Date(now.getFullYear(), now.getMonth() - 1, 1);
    const prev = ymd(prevD).slice(0, 7);
    const sum = (m: string) => payments.filter(p => String(p.payment_date || p.created_at || '').startsWith(m)).reduce((a, p) => a + num(p.amount), 0);
    const daysInMonth = new Date(now.getFullYear(), now.getMonth() + 1, 0).getDate();
    const mtd = sum(cur), last = sum(prev);
    const ref = last * (now.getDate() / daysInMonth);
    return { mtd, last, ref, pace: last > 0 ? (mtd / ref) * 100 : null, prevLabel: prevD.toLocaleString('en-US', { month: 'short' }), day: now.getDate(), daysInMonth };
  }, [payments, now]);

  const fin = ok('finance');
  const pstats = ok('prospectStats');

  const tiles: TileSpec[] = [
    { label: 'Open quotes', value: openQuotes ? openQuotes.length : null, fmt: 'int', sub: openQuotes ? `${money(openQuotes.reduce((a, q) => a + num(q.total), 0))} in pipeline` : '', why: err('quotes') || '', href: '/?product=workroom&section=quotes' },
    { label: 'Active jobs', value: activeJobs ? activeJobs.length : null, fmt: 'int', sub: jobs ? `${jobs.length - (activeJobs?.length || 0)} completed/closed` : '', why: err('jobs') || '', href: '/?product=workroom&section=jobs' },
    { label: 'Open leads', value: openLeadCount, fmt: 'int', sub: `CRM leads · ${newLeadCount} new`, why: err('leadPipeline') || '', href: '/?product=lead' },
    { label: 'LeadForge', value: pstats ? num(pstats.in_pipeline) : null, fmt: 'int', sub: pstats ? `in pipeline · ${num(pstats.total_prospects)} prospects` : '', why: err('prospectStats') || '', href: '/?product=lead' },
    { label: 'A/R outstanding', value: fin?.outstanding ? num(fin.outstanding.total) : null, fmt: 'money', sub: fin?.outstanding ? `${num(fin.outstanding.count)} open invoices` : '', why: err('finance') || 'no outstanding field', href: '/?screen=invoices' },
    { label: 'Collected MTD', value: pay ? pay.mtd : null, fmt: 'money', sub: pay ? `${pay.prevLabel}: ${money(pay.last)}` : '', why: err('payments') || '', href: '/?product=pay' },
    { label: 'Customers', value: ok('customers') ? num(ok('customers').total) : null, fmt: 'int', sub: 'CRM records', why: err('customers') || '', href: '/?product=crm' },
  ];

  const blips: Blip[] | null = useMemo(() => {
    if (loading) return null;
    const out: Blip[] = [];
    (activeJobs || []).forEach(j => {
      const bu = String(j.business_unit || j.job_type || 'other');
      const val = num(j.estimated_value) || num(j.quoted_amount) || num(j.invoiced_amount);
      const age = ageDays(j.created_at) ?? 0;
      out.push({
        id: `job-${j.id}`, group: `Jobs · ${titleCase(bu)}`, kind: 'job', age, value: val,
        label: j.job_number ? `${j.job_number} ${j.title || ''}`.trim() : (j.title || 'Job'),
        detail: `${titleCase(String(j.pipeline_stage || j.status || ''))} · ${Math.round(age)}d old${val ? ` · ${money(val)}` : ''}`,
        href: bu === 'woodcraft' ? '/?product=craft&section=jobs' : '/?product=workroom&section=jobs',
      });
    });
    (openLeads || []).forEach(l => {
      const src = String(l.source || l.capture_channel || 'unknown');
      const age = ageDays(l.created_at) ?? 0; const val = num(l.estimated_value) || num(l.value) || num(l.score);
      out.push({ id: `lead-${l.id}`, group: `Leads · ${titleCase(src)}`, kind: 'lead', age, value: val, label: l.name || l.company || 'Lead', detail: `${titleCase(String(l.status || 'open'))} · ${Math.round(age)}d old`, href: '/?product=lead' });
    });
    (pipe || []).forEach(p => {
      if (CLOSED_LEAD.has(String(p.status || '').toLowerCase())) return;
      const age = ageDays(p.created_at) ?? 0;
      out.push({ id: `pros-${p.id}`, group: 'LeadForge pipeline', kind: 'prospect', age, value: num(p.score), label: p.business_name || p.name || 'Prospect', detail: `Score ${num(p.score)} · ${p.outreach_priority || 'n/a'} priority · ${Math.round(age)}d in pipeline`, href: '/?product=lead' });
    });
    return out;
  }, [loading, activeJobs, openLeads, pipe]);

  const stages: { stage: string; label: string; count: number }[] | null = ok('jobPipeline')?.stages
    ? ok('jobPipeline').stages.map((s: any) => ({ stage: s.stage, label: s.label || titleCase(s.stage), count: Array.isArray(s.jobs) ? s.jobs.length : num(s.count) }))
    : null;
  const maxStage = Math.max(1, ...(stages || []).map(s => s.count));

  const donut = useMemo(() => {
    if (!quotes) return null;
    const by: Record<string, { n: number; v: number }> = {};
    quotes.forEach(q => { const s = String(q.status || 'unknown').toLowerCase(); by[s] = by[s] || { n: 0, v: 0 }; by[s].n++; by[s].v += num(q.total); });
    return Object.entries(by).sort((a, b) => b[1].n - a[1].n).map(([s, x], i) => ({ label: s, value: x.n, amount: x.v, color: STATUS_COLORS[s] || GROUP_COLORS[i % GROUP_COLORS.length] }));
  }, [quotes]);

  // today's schedule: jobs/calendar (today) + job dates equal to today
  const schedule = useMemo(() => {
    if (!now) return null;
    const today = ymd(now);
    const cal = ok('calendar');
    if (cal === null && !jobs) return null;
    const ev: { key: string; time: Date | null; title: string; kind: string }[] = [];
    (Array.isArray(cal) ? cal : cal?.events || []).forEach((e: any, i: number) => {
      const when = e.start || e.date || e.scheduled_date || e.install_date || e.site_visit_date;
      ev.push({ key: `cal-${e.id || i}`, time: when && String(when).includes('T') ? parseDate(when) : null, title: e.title || e.job_number || e.client_name || 'Event', kind: e.type || 'calendar' });
    });
    const seen = new Set(ev.map(e => e.key));
    (jobs || []).forEach(j => {
      (['site_visit_date', 'install_date', 'scheduled_date', 'production_start', 'due_date'] as const).forEach(f => {
        const v = j[f]; if (!v || !String(v).startsWith(today)) return;
        const key = `job-${j.id}-${f}`; if (seen.has(key)) return;
        ev.push({ key, time: String(v).includes('T') ? parseDate(v) : null, title: `${j.job_number || ''} ${j.title || ''}`.trim(), kind: titleCase(f.replace('_date', '')) });
      });
    });
    return ev;
  }, [now, data, jobs]); // eslint-disable-line react-hooks/exhaustive-deps

  // Max Suggestions: only items backed by real rows. No item = no card.
  const suggestions: Suggestion[] | null = useMemo(() => {
    if (loading || !now) return null;
    const out: Suggestion[] = [];
    const today = ymd(now);
    const od = ok('overdue');
    if (od && num(od.count) > 0) {
      const list: any[] = od.overdue_invoices || [];
      const oldest = [...list].sort((a, b) => String(a.due_date || '').localeCompare(String(b.due_date || '')))[0];
      out.push({ key: 'overdue', tone: 'urgent', title: `${num(od.count)} overdue invoice${num(od.count) === 1 ? '' : 's'} · ${money(num(od.total_outstanding))}`,
        detail: oldest ? `Oldest ${oldest.invoice_number || ''} due ${oldest.due_date || '?'} · ${money(num(oldest.balance_due))} open` : 'Past due date with a balance', href: '/?screen=invoices', src: 'payments/overdue' });
    }
    const da = ok('dailyActions');
    if (da && Array.isArray(da.actions)) {
      const byType: Record<string, any[]> = {};
      da.actions.forEach((a: any) => { const t = String(a.type || 'action'); (byType[t] = byType[t] || []).push(a); });
      Object.entries(byType).forEach(([t, list]) => {
        const first = list[0];
        const href = first.entity_type === 'invoice' ? '/?screen=invoices' : first.entity_type === 'quote' ? '/?product=workroom&section=quotes' : first.entity_type === 'job' ? '/?product=workroom&section=jobs' : first.entity_type === 'lead' ? '/?product=lead' : '/?product=owner&screen=dashboard';
        const title = t === 'send_quote' ? `${list.length} quote${list.length === 1 ? '' : 's'} ready to send`
          : t === 'send_reminder' ? `${list.length} payment reminder${list.length === 1 ? '' : 's'} suggested`
          : `${list.length} × ${titleCase(t)}`;
        out.push({ key: `da-${t}`, tone: list.some((a: any) => a.priority === 'urgent') ? 'warn' : 'info', title,
          detail: `Next: ${first.label || ''}${first.detail ? ` — ${first.detail}` : ''}`, href, src: 'Max daily actions (lifecycle/daily-actions)' });
      });
    }
    if (quotes) {
      const stale = quotes.filter(q => ['sent', 'proposal', 'viewed'].includes(String(q.status || '').toLowerCase()) && (ageDays(q.sent_at || q.updated_at || q.created_at) ?? 0) >= 7);
      if (stale.length) {
        const oldest = [...stale].sort((a, b) => (ageDays(b.sent_at || b.updated_at) ?? 0) - (ageDays(a.sent_at || a.updated_at) ?? 0))[0];
        out.push({ key: 'stale-quotes', tone: 'warn', title: `${stale.length} sent quote${stale.length === 1 ? '' : 's'} need follow-up`,
          detail: `No answer in 7+ days · oldest ${oldest.quote_number || ''} ${oldest.customer_name || ''} (${Math.round(ageDays(oldest.sent_at || oldest.updated_at) ?? 0)}d)`, href: '/?product=workroom&section=quotes', src: 'quotes-v2' });
      }
    }
    if (activeJobs) {
      const horizon = ymd(new Date(now.getFullYear(), now.getMonth(), now.getDate() + 7));
      const tomorrow = ymd(new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1));
      const upcoming: { j: any; f: string; v: string }[] = [];
      activeJobs.forEach(j => (['install_date', 'site_visit_date', 'scheduled_date'] as const).forEach(f => {
        const v = j[f] ? String(j[f]) : ''; if (v && v.slice(0, 10) >= today && v.slice(0, 10) <= horizon) upcoming.push({ j, f, v });
      }));
      upcoming.sort((a, b) => a.v.localeCompare(b.v)).slice(0, 3).forEach(({ j, f, v }) => {
        const d = v.slice(0, 10); const when = d === today ? 'today' : d === tomorrow ? 'tomorrow' : new Date(`${d}T12:00:00`).toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' });
        const t = v.includes('T') ? parseDate(v) : null;
        const kind = f === 'install_date' ? 'Install' : f === 'site_visit_date' ? 'Site visit' : 'Scheduled';
        out.push({ key: `up-${j.id}-${f}`, tone: d === today ? 'urgent' : 'info', title: `${kind} ${when}${t ? ` ${t.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' })}` : ''}`,
          detail: `${j.job_number || ''} ${j.title || j.client_name || ''}`.trim(), href: j.business_unit === 'woodcraft' ? '/?product=craft&section=jobs' : '/?product=workroom&section=jobs', src: 'jobs' });
      });
    }
    const fq = ok('followups'); const sl = ok('staleLeads');
    const leadN = Math.max(newLeadCount, num(fq?.total), num(sl?.total));
    if (leadN > 0) out.push({ key: 'leads', tone: 'warn', title: `${leadN} lead${leadN === 1 ? '' : 's'} waiting for first contact`, detail: `${newLeadCount} new · ${num(fq?.total)} in follow-up queue · ${num(sl?.total)} stale ${sl?.stale_days ? `(${sl.stale_days}d+)` : ''}`, href: '/?product=lead', src: 'leads/pipeline · followups/queue · leads/stale' });
    if (pipe) {
      const untouched = pipe.filter(p => !p.status && !p.next_action && !p.notes);
      if (untouched.length) out.push({ key: 'lf-untouched', tone: 'info', title: `${untouched.length} LeadForge prospect${untouched.length === 1 ? '' : 's'} not contacted yet`,
        detail: `In pipeline with no status, note or next action · top: ${[...untouched].sort((a, b) => num(b.score) - num(a.score))[0].business_name || ''}`, href: '/?product=lead', src: 'leadforge/prospect-pipeline' });
    }
    const rank = { urgent: 0, warn: 1, info: 2 } as const;
    return out.sort((a, b) => rank[a.tone] - rank[b.tone]).slice(0, 7);
  }, [loading, now, data, quotes, activeJobs, newLeadCount, pipe]); // eslint-disable-line react-hooks/exhaustive-deps
  const suggFailed = [['dailyActions', 'Max daily actions'], ['overdue', 'payments/overdue'], ['followups', 'followups'], ['staleLeads', 'leads/stale'], ['leadPipeline', 'leads/pipeline'], ['quotes', 'quotes'], ['jobs', 'jobs']]
    .filter(([k]) => err(k)).map(([, l]) => l);

  const sysH = ok('sysHealth'); const sysS = ok('sysStats');
  const services: { name: string; up: boolean }[] | null = sysH?.services ? Object.entries(sysH.services).map(([name, up]) => ({ name, up: up === true })) : null;
  const integrity = services && services.length ? (services.filter(s => s.up).length / services.length) * 100 : null;
  const integrityShown = useCountUp(integrity, reduced);

  const tlStart = 7, tlEnd = 20;
  const tlPos = (d: Date) => Math.min(100, Math.max(0, ((d.getHours() + d.getMinutes() / 60 - tlStart) / (tlEnd - tlStart)) * 100));

  return (
    <div className="ck-root" data-cockpit-page>
      <div className="ck-shell">
        <HexStrip />
        <main className="ck-main">
          <header className="ck-top">
            <div className="ck-title">
              <div>
                <h1>EMPIRE COMMAND · COCKPIT</h1>
                <small>LIVE BACKEND DATA · {loadedAt ? `SYNCED ${loadedAt.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}` : 'SYNCING…'}</small>
              </div>
              <span className="ck-badge">PREVIEW</span>
            </div>
            <div className="ck-top-right">
              {now && <span className="ck-clock">{now.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' })} · {now.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })}</span>}
              <a href="/" className="ck-btn"><ArrowLeft size={14} /> CURRENT HOME</a>
            </div>
          </header>

          <div className="ck-grid">
            <Panel title="Status" src="quotes-v2 · jobs · leads · leadforge · finance · crm" className="ck-span-12">
              {loading ? <div className="ck-loading">LOADING…</div> : (
                <div className="ck-tiles">{tiles.map(t => <HexTile key={t.label} t={t} reduced={reduced} />)}</div>
              )}
            </Panel>

            <div className="ck-span-8 ck-col">
              <Panel title="Radar · open leads & jobs" src="jobs · leads/hot+stale · leadforge pipeline">
                <RadarPanel blips={blips} reduced={reduced} note={openLeadCount !== null && openLeads && openLeadCount > openLeads.length ? `Lead blips = hot + stale leads (${openLeads.length} of ${openLeadCount} open)` : ''} sources={[
                  { label: 'jobs', ok: !err('jobs') }, { label: 'CRM leads', ok: !err('hotLeads') && !err('staleLeads') }, { label: 'LeadForge pipeline', ok: !err('prospectPipeline') },
                ]} />
              </Panel>
              <div className="ck-sub2">
                <Panel title="Job pipeline" src="jobs/pipeline">
                  {loading ? <div className="ck-loading">LOADING…</div> : !stages ? <NoData why={`jobs/pipeline ${err('jobPipeline') || 'no stages'}`} /> : (
                    <div className="ck-bars">
                      {stages.map(s => (
                        <a key={s.stage} href="/?product=workroom&section=jobs" className="ck-bar-row" title={`${s.label}: ${s.count}`}>
                          <span>{s.label}</span>
                          <span className="ck-bar"><i style={{ width: `${(s.count / maxStage) * 100}%` }} /></span>
                          <b>{s.count}</b>
                        </a>
                      ))}
                    </div>
                  )}
                </Panel>
                <Panel title="Quote pipeline" src="quotes-v2 (test quotes excluded)">
                  {loading ? <div className="ck-loading">LOADING…</div> : !donut ? <NoData why={`quotes-v2 ${err('quotes') || 'unavailable'}`} /> : donut.length === 0 ? <NoData why="No quotes returned" /> : (
                    <div className="ck-donut-wrap">
                      <Donut segs={donut} center={String(quotes!.length)} sub="QUOTES" />
                      <div className="ck-legend">
                        {donut.map(s => (
                          <div key={s.label} className="ck-legend-row" style={{ color: s.color }}>
                            <span className="ck-legend-dot" />
                            <span style={{ color: 'var(--ck-text)' }}>{titleCase(s.label)}</span>
                            <b style={{ marginLeft: 'auto', color: '#eaffff' }}>{s.value}</b>
                          </div>
                        ))}
                        <small>Open value {money((openQuotes || []).reduce((a, q) => a + num(q.total), 0))}</small>
                      </div>
                    </div>
                  )}
                </Panel>
              </div>
            </div>

            <div className="ck-span-4 ck-col">
              <Panel title="Max" src="max/health · max/voice/status">
                <MaxOrb health={data.maxHealth} voice={data.maxVoice} />
              </Panel>
              <Panel title="Max suggestions" src="real data only">
                <MaxSuggestions items={suggestions} failed={suggFailed} />
              </Panel>
              <Panel title="Revenue pace" src="finance/payments">
                {loading ? <div className="ck-loading">LOADING…</div> : !pay ? <NoData why={`finance/payments ${err('payments') || 'unavailable'}`} /> : (
                  <>
                    <Gauge pace={pay.pace} reduced={reduced} />
                    <div className="ck-kv"><span>Collected MTD</span><b>{money(pay.mtd)}</b></div>
                    <div className="ck-kv"><span>{pay.prevLabel} total</span><b>{money(pay.last)}</b></div>
                    <div className="ck-kv"><span>Pace ref (day {pay.day}/{pay.daysInMonth})</span><b>{pay.last > 0 ? money(pay.ref) : '—'}</b></div>
                    <div className="ck-kv"><span>Revenue goal</span><b style={{ color: 'var(--ck-amber)' }}>SIN DATOS</b></div>
                    <div className="ck-src" style={{ textAlign: 'left', marginTop: 4 }}>Pace = collected this month vs last month prorated to today. No revenue goal is configured in the backend.</div>
                  </>
                )}
              </Panel>
            </div>

            <Panel title="Today's schedule" src="jobs/calendar · job dates" className="ck-span-6">
              {!schedule ? (loading ? <div className="ck-loading">LOADING…</div> : <NoData why="jobs/calendar and jobs unavailable" />) : (
                <>
                  <div className="ck-timeline" aria-hidden="true">
                    <div className="ck-tl-axis" />
                    {Array.from({ length: tlEnd - tlStart + 1 }, (_, i) => tlStart + i).filter(h => h % 2 === 1 || h === tlEnd).map(h => (
                      <div key={h} className="ck-tl-tick" style={{ left: `${((h - tlStart) / (tlEnd - tlStart)) * 100}%` }}><span>{h > 12 ? `${h - 12}p` : `${h}${h === 12 ? 'p' : 'a'}`}</span></div>
                    ))}
                    {now && now.getHours() >= tlStart && now.getHours() < tlEnd && <div className="ck-tl-now" style={{ left: `${tlPos(now)}%` }} />}
                    {schedule.filter(e => e.time).map(e => (
                      <svg key={e.key} className="ck-tl-ev" style={{ left: `${tlPos(e.time!)}%` }} viewBox="0 0 24 24"><polygon points="12,1 22,6.5 22,17.5 12,23 2,17.5 2,6.5" fill="rgba(0,229,255,0.25)" stroke="#00e5ff" /></svg>
                    ))}
                  </div>
                  {schedule.length === 0 ? (
                    <div className="ck-src" style={{ textAlign: 'center', fontSize: 11, padding: '6px 0' }}>Nada programado hoy · nothing scheduled today</div>
                  ) : (
                    <ul className="ck-tl-list">
                      {schedule.map(e => (
                        <li key={e.key}><span style={{ color: 'var(--ck-teal)' }}>{e.time ? e.time.toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit' }) : 'ALL DAY'}</span> · {e.title} <span style={{ color: 'var(--ck-muted)' }}>({e.kind})</span></li>
                      ))}
                    </ul>
                  )}
                  <div className="ck-src" style={{ textAlign: 'left', marginTop: 6 }}>No external calendar is connected; this shows the jobs calendar plus site-visit, install, production and due dates on jobs.</div>
                </>
              )}
            </Panel>

            <Panel title="System integrity" src="system/health · system/stats" className="ck-span-6">
              {loading ? <div className="ck-loading">LOADING…</div> : integrity === null ? <NoData why={`system/health ${err('sysHealth') || 'no services'}`} /> : (
                <>
                  <div className="ck-integrity">
                    <div className="ck-int-bar">
                      {Array.from({ length: 40 }, (_, i) => <i key={i} className={(i + 0.5) / 40 * 100 <= integrityShown ? 'on' : (integrity < 100 ? 'off' : '')} />)}
                    </div>
                    <span className="ck-pct">{Math.round(integrityShown)}%</span>
                  </div>
                  <div className="ck-svc">
                    {services!.map(s => <span key={s.name}><i style={{ background: s.up ? 'var(--ck-teal)' : 'var(--ck-red)', boxShadow: `0 0 6px ${s.up ? 'var(--ck-teal)' : 'var(--ck-red)'}` }} />{s.name} {s.up ? 'UP' : 'DOWN'}</span>)}
                    {sysS && <>
                      <span style={{ color: 'var(--ck-muted)' }}>CPU {num(sysS.cpu?.percent).toFixed(0)}%</span>
                      <span style={{ color: 'var(--ck-muted)' }}>RAM {num(sysS.memory?.percent).toFixed(0)}%</span>
                      <span style={{ color: 'var(--ck-muted)' }}>DISK {num(sysS.disk?.percent).toFixed(0)}%</span>
                    </>}
                    {sysH?.uptime_seconds != null && <span style={{ color: 'var(--ck-muted)' }}>API UPTIME {(num(sysH.uptime_seconds) / 3600).toFixed(1)}h</span>}
                  </div>
                </>
              )}
            </Panel>
          </div>

          <p className="ck-foot">Preview of the cockpit home. The current home is unchanged at <a href="/" style={{ color: 'var(--ck-cyan)' }}>/</a>. Every figure comes from the Empire backend; widgets without a source say SIN DATOS · NO DATA.</p>
        </main>
      </div>
    </div>
  );
}
