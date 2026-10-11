'use client';
/**
 * Cyber HUD building blocks for the rebuilt module pages.
 * Presentational only — callers pass real values (null = no data, shown as
 * "—" / SIN DATOS). Motion (count-up, gauge draw, fade-in, pulses) is
 * skipped when the user prefers reduced motion.
 */
import '../../theme/cyber.css';
import '../../theme/cyber-hud.css';
import '../../theme/cyber-calm.css';
import { useEffect, useRef, useState, type CSSProperties, type ReactNode } from 'react';

export type Tone = 'cyan' | 'teal' | 'amber' | 'mag' | 'violet' | 'blue' | 'muted';
const t = (tone?: Tone) => (tone && tone !== 'cyan' ? ` t-${tone}` : '');

export function usePrefersReducedMotion() {
  const [reduced, setReduced] = useState(false);
  useEffect(() => {
    const mq = window.matchMedia('(prefers-reduced-motion: reduce)');
    const on = () => setReduced(mq.matches);
    on();
    mq.addEventListener?.('change', on);
    return () => mq.removeEventListener?.('change', on);
  }, []);
  return reduced;
}

/** Animates from the previous value to `target`; returns the target directly under reduced motion. */
export function useCountUp(target: number | null | undefined, ms = 900) {
  const reduced = usePrefersReducedMotion();
  const [v, setV] = useState<number>(0);
  const from = useRef(0);
  useEffect(() => {
    if (target == null || !isFinite(target)) return;
    if (reduced) { setV(target); from.current = target; return; }
    const start = performance.now(); const a = from.current; const b = target;
    let raf = 0;
    const step = (now: number) => {
      const p = Math.min(1, (now - start) / ms);
      const e = 1 - Math.pow(1 - p, 3);
      setV(a + (b - a) * e);
      if (p < 1) raf = requestAnimationFrame(step); else from.current = b;
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, ms, reduced]);
  return target == null ? null : v;
}

export const fmtMoney = (n: number, cents = false) =>
  '$' + n.toLocaleString('en-US', { minimumFractionDigits: cents ? 2 : 0, maximumFractionDigits: cents ? 2 : 0 });
export const fmtInt = (n: number) => Math.round(n).toLocaleString('en-US');

export function CountUp({ value, format = fmtInt, className }: { value: number | null | undefined; format?: (n: number) => string; className?: string }) {
  const v = useCountUp(value);
  return <span className={className}>{v == null ? '—' : format(v)}</span>;
}

/** Staggered fade-in wrapper. */
export function Fade({ i = 0, className = '', style, children, as: As = 'div' }:
  { i?: number; className?: string; style?: CSSProperties; children: ReactNode; as?: any }) {
  return <As className={`cy-fade ${className}`} style={{ ...style, ['--cy-d' as any]: `${i * 70}ms` }}>{children}</As>;
}

/** Page section with grid floor, perspective floor and scanlines. */
export function HudStage({ children, className = '', wide = false }: { children: ReactNode; className?: string; wide?: boolean }) {
  return (
    <div className={`cy-stage ${className}`}>
      <div className="cy-stage-floor" aria-hidden />
      <div className="cy-stage-scan" aria-hidden />
      <div className="cy-stage-inner" style={wide ? { maxWidth: 'none' } : undefined}>{children}</div>
    </div>
  );
}

export type HudChip = { label: ReactNode; tone?: Tone; live?: boolean; title?: string };

export function HudHeader({ icon, title, subtitle, chips = [], actions, back }:
  { icon?: ReactNode; title: ReactNode; subtitle?: ReactNode; chips?: HudChip[]; actions?: ReactNode; back?: ReactNode }) {
  return (
    <Fade i={0} className="cy-hudhead">
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8, minWidth: 0, flex: '1 1 320px' }}>
        {back}
        <div className="cy-plate">
          {icon && <span className="cy-plate-ico">{icon}</span>}
          <div style={{ minWidth: 0 }}>
            <h1>{title}</h1>
            {subtitle && <small>{subtitle}</small>}
          </div>
        </div>
      </div>
      <div className="cy-hudhead-side" style={{ flex: '1 1 300px' }}>
        {chips.length > 0 && (
          <div className="cy-chips" role="status" aria-live="polite">
            {chips.map((c, i) => (
              <span key={i} className={`cy-chip${t(c.tone)}${c.live ? ' is-live' : ''}`} title={c.title}><i aria-hidden />{c.label}</span>
            ))}
          </div>
        )}
        {actions && <div className="cy-actions">{actions}</div>}
      </div>
    </Fade>
  );
}

export function GaugeRow({ children }: { children: ReactNode }) {
  return <div className="cy-gauges">{children}</div>;
}

/**
 * Radial gauge tile. `fraction` (0..1) draws the arc; pass null when the
 * metric has no meaningful ratio — the ring then idles with dashed motion
 * and `ringLabel` is not shown as a percentage.
 */
export function RadialGauge({ label, value, format = fmtInt, fraction = null, ringLabel, sub, tone = 'cyan', icon, onClick, i = 0, title }:
  { label: ReactNode; value: number | null | undefined; format?: (n: number) => string; fraction?: number | null; ringLabel?: ReactNode;
    sub?: ReactNode; tone?: Tone; icon?: ReactNode; onClick?: () => void; i?: number; title?: string }) {
  const r = 34, C = 2 * Math.PI * r;
  const f = fraction == null || !isFinite(fraction) ? null : Math.max(0, Math.min(1, fraction));
  const [drawn, setDrawn] = useState(0);
  useEffect(() => { const id = requestAnimationFrame(() => setDrawn(f ?? 0)); return () => cancelAnimationFrame(id); }, [f]);
  const inner = (
    <>
      <div className="cy-gauge-ring" aria-hidden>
        <svg viewBox="0 0 86 86">
          <circle className="cy-gauge-ticks" cx="43" cy="43" r="41" />
          <circle className="cy-gauge-track" cx="43" cy="43" r={r} />
          <circle className={`cy-gauge-arc${f == null ? ' is-idle' : ''}`} cx="43" cy="43" r={r}
            strokeDasharray={C} strokeDashoffset={f == null ? 0 : C * (1 - drawn)} />
        </svg>
        {f != null ? <b>{ringLabel ?? `${Math.round(f * 100)}%`}</b> : icon ? <span className="cy-gauge-ico">{icon}</span> : null}
      </div>
      <div className="cy-gauge-body">
        <div className="cy-gauge-label">{label}</div>
        <div className="cy-gauge-value"><CountUp value={value} format={format} /></div>
        {sub && <div className="cy-gauge-sub">{sub}</div>}
      </div>
    </>
  );
  const cls = `cy-gauge cy-hud cy-fade${t(tone)}`;
  const style = { ['--cy-d' as any]: `${80 + i * 70}ms` };
  return onClick
    ? <button type="button" className={cls} style={style} onClick={onClick} title={title}>{inner}</button>
    : <div className={cls} style={style} title={title}>{inner}</div>;
}

export function HexTile({ label, value, tone = 'cyan', onClick, title }:
  { label: ReactNode; value: number | null | undefined; tone?: Tone; onClick?: () => void; title?: string }) {
  const inner = (<><b><CountUp value={value} /></b><span>{label}</span></>);
  return onClick
    ? <button type="button" className={`cy-hex${t(tone)}`} onClick={onClick} title={title}>{inner}</button>
    : <div className={`cy-hex${t(tone)}`} title={title}>{inner}</div>;
}

export type MaxSuggestion = { id: string; title: ReactNode; text: ReactNode; tone?: Tone; actionLabel: ReactNode; onAction?: () => void; href?: string; source?: ReactNode };

/** Small strip of Max suggestions built from the page's own live data. */
export function MaxStrip({ items, loading, empty = 'Nothing pending on this module right now.', i = 2 }:
  { items: MaxSuggestion[]; loading?: boolean; empty?: ReactNode; i?: number }) {
  return (
    <Fade i={i} className="cy-maxstrip cy-hud" as="section">
      <div className="cy-maxstrip-orb"><span className="cy-orb" aria-hidden>MAX</span><small>Suggests</small></div>
      <div className="cy-maxstrip-list" aria-label="Max suggestions">
        {loading && items.length === 0 && <div className="cy-maxstrip-empty">SCANNING LIVE DATA…</div>}
        {!loading && items.length === 0 && <div className="cy-maxstrip-empty">{empty}</div>}
        {items.map(s => (
          <article key={s.id} className={`cy-sugg${t(s.tone)}`}>
            <h4>{s.title}</h4>
            <p>{s.text}</p>
            <div className="cy-sugg-foot">
              <span className="cy-sugg-src">{s.source}</span>
              {s.href
                ? <a className="cy-btn is-sm" href={s.href}>{s.actionLabel} →</a>
                : <button type="button" className="cy-btn is-sm" onClick={s.onAction}>{s.actionLabel} →</button>}
            </div>
          </article>
        ))}
      </div>
    </Fade>
  );
}

/** Glass panel with HUD brackets + fade. */
export function HudPanel({ title, icon, actions, children, i = 3, className = '', style, tone }:
  { title?: ReactNode; icon?: ReactNode; actions?: ReactNode; children: ReactNode; i?: number; className?: string; style?: CSSProperties; tone?: 'alert' }) {
  return (
    <section className={`cy-panel cy-hud cy-glass cy-fade ${tone === 'alert' ? 'is-alert ' : ''}${className}`} style={{ ...style, ['--cy-d' as any]: `${i * 70}ms` }}>
      {(title || actions) && (
        <header className="cy-panel-head">
          {title && <h2 className="cy-panel-title">{icon}{title}</h2>}
          {actions}
        </header>
      )}
      {children}
    </section>
  );
}

const STATUS_TONE: Record<string, Tone> = {
  draft: 'muted', founder_review: 'amber', sent: 'blue', open: 'blue', viewed: 'blue', proposal: 'violet',
  accepted: 'teal', approved: 'teal', paid: 'teal', completed: 'teal', delivered: 'teal', active: 'teal',
  partial: 'amber', pending: 'amber', in_progress: 'amber', scheduled: 'blue',
  rejected: 'mag', declined: 'mag', overdue: 'mag', cancelled: 'mag', expired: 'mag', void: 'mag',
};
export function StatusPill({ status, label }: { status?: string | null; label?: ReactNode }) {
  const s = (status || 'draft').toLowerCase();
  return <span className={`cy-spill${t(STATUS_TONE[s] || 'cyan')}`}>{label ?? s.replace(/_/g, ' ')}</span>;
}

export function SectionLabel({ children }: { children: ReactNode }) {
  return <div className="cy-sect">{children}</div>;
}

export function BackButton({ onClick, href, children = 'Back' }: { onClick?: () => void; href?: string; children?: ReactNode }) {
  if (href) return <a className="cy-backbtn" href={href}>← {children}</a>;
  return <button type="button" className="cy-backbtn" onClick={onClick}>← {children}</button>;
}

/** Days between an ISO date and now (null when unparseable). */
export function daysSince(iso?: string | null) {
  if (!iso) return null;
  const d = new Date(iso).getTime();
  return isFinite(d) ? Math.floor((Date.now() - d) / 86_400_000) : null;
}
