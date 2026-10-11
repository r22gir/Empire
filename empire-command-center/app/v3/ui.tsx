'use client';
// Empire design system v3: shared primitives (orb, wave, progress ring, backdrop, panel header, empty state).
// Colors come from CSS variables in v3/tokens.css, so every piece follows Dark / Gold automatically.
import { useId } from 'react';
import type { ReactNode } from 'react';

function arcPath(rx: number, ry: number, a0: number, a1: number) {
  const p = (a: number) => [100 + rx * Math.cos((a * Math.PI) / 180), 100 + ry * Math.sin((a * Math.PI) / 180)];
  const [x0, y0] = p(a0); const [x1, y1] = p(a1);
  return { d: `M ${x0.toFixed(1)} ${y0.toFixed(1)} A ${rx} ${ry} 0 0 0 ${x1.toFixed(1)} ${y1.toFixed(1)}`, x1, y1 };
}

/** Abstract Max orb (no face): shaded sphere, meridians, two orbit trails. */
export function Orb({ size = 176, className = '' }: { size?: number; className?: string }) {
  const uid = useId().replace(/[^a-zA-Z0-9]/g, '');
  const a1 = arcPath(84, 30, 168, 78);
  const a2 = arcPath(74, 44, -15, -72);
  const stop = (offset: string, color: string, opacity?: number) => <stop offset={offset} style={{ stopColor: color, stopOpacity: opacity ?? 1 }} />;
  return (
    <svg width={size} height={size} viewBox="0 0 200 200" className={`v3-orb ${className}`} style={{ flex: 'none', overflow: 'visible' }} aria-hidden="true">
      <defs>
        <radialGradient id={`${uid}s`} cx="36%" cy="30%" r="75%">{stop('0', 'var(--v-o1)')}{stop('.38', 'var(--v-o2)')}{stop('.78', 'var(--v-o3)')}{stop('1', 'var(--v-o4)')}</radialGradient>
        <radialGradient id={`${uid}h`} cx="50%" cy="50%" r="50%">{stop('.55', 'var(--v-o3)', 0.18)}{stop('1', 'var(--v-o3)', 0)}</radialGradient>
        <linearGradient id={`${uid}t`} x1="0" x2="1">{stop('0', 'var(--v-acc)', 0)}{stop('1', 'var(--v-acc)', 0.95)}</linearGradient>
        <linearGradient id={`${uid}t2`} x1="1" x2="0">{stop('0', 'var(--v-acc)', 0)}{stop('1', 'var(--v-acc)', 0.95)}</linearGradient>
        <radialGradient id={`${uid}sp`} cx="50%" cy="50%" r="50%"><stop offset="0" stopColor="#fff" stopOpacity=".85" /><stop offset="1" stopColor="#fff" stopOpacity="0" /></radialGradient>
        <clipPath id={`${uid}c`}><circle cx="100" cy="100" r="52" /></clipPath>
      </defs>
      <circle cx="100" cy="100" r="96" fill={`url(#${uid}h)`} />
      <circle cx="100" cy="100" r="88" fill="none" style={{ stroke: 'var(--v-orbline)' }} strokeWidth=".5" strokeDasharray="1 4" />
      <ellipse cx="100" cy="100" rx="84" ry="30" fill="none" style={{ stroke: 'var(--v-orbline)' }} strokeWidth=".7" transform="rotate(-18 100 100)" />
      <ellipse cx="100" cy="100" rx="74" ry="44" fill="none" style={{ stroke: 'var(--v-orbline)' }} strokeWidth=".5" transform="rotate(32 100 100)" />
      <circle cx="100" cy="100" r="52" fill={`url(#${uid}s)`} />
      <g clipPath={`url(#${uid}c)`} fill="none" stroke="#fff" strokeOpacity=".28" strokeWidth=".7">
        <ellipse cx="100" cy="100" rx="52" ry="14" /><ellipse cx="100" cy="100" rx="52" ry="30" /><ellipse cx="100" cy="100" rx="20" ry="52" /><ellipse cx="100" cy="100" rx="38" ry="52" />
      </g>
      <ellipse cx="82" cy="76" rx="22" ry="13" fill={`url(#${uid}sp)`} transform="rotate(-25 82 76)" />
      <g transform="rotate(-18 100 100)"><path d={a1.d} fill="none" stroke={`url(#${uid}t)`} strokeWidth="1.6" strokeLinecap="round" /><circle cx={a1.x1} cy={a1.y1} r="3" style={{ fill: 'var(--v-acc)' }} /></g>
      <g transform="rotate(32 100 100)"><path d={a2.d} fill="none" stroke={`url(#${uid}t2)`} strokeWidth="1.2" strokeLinecap="round" /><circle cx={a2.x1} cy={a2.y1} r="2.2" style={{ fill: 'var(--v-ink)' }} /></g>
    </svg>
  );
}

/** Decorative voice wave (static, deterministic). */
export function Wave({ n = 30, h = 20, seed = 6 }: { n?: number; h?: number; seed?: number }) {
  let s = seed * 9301 + 49297;
  const rnd = () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
  return (
    <div className="v3-wave" aria-hidden="true" style={{ height: h }}>
      {Array.from({ length: n }, (_, i) => {
        const env = Math.pow(Math.sin((Math.PI * (i + 0.5)) / n), 1.4);
        const v = Math.max(0.08, env * (0.3 + 0.7 * rnd()));
        return <i key={i} style={{ display: 'block', width: 2, height: `${(v * h).toFixed(1)}px`, borderRadius: 2, background: 'var(--v-acc)', opacity: 0.35 + 0.65 * env }} />;
      })}
    </div>
  );
}

/** Circular progress (0..1) with the percentage in the middle. */
export function RingProgress({ value, size = 46, label }: { value: number; size?: number; label?: string }) {
  const r = 19; const c = 2 * Math.PI * r; const p = Math.max(0, Math.min(1, value));
  return (
    <svg width={size} height={size} viewBox="0 0 46 46" style={{ flex: 'none' }} role="img" aria-label={label || `${Math.round(p * 100)}%`}>
      <circle cx="23" cy="23" r={r} fill="none" style={{ stroke: 'var(--v-line)' }} strokeWidth="3" />
      <circle cx="23" cy="23" r={r} fill="none" style={{ stroke: 'var(--v-acc)' }} strokeWidth="3" strokeLinecap="round" strokeDasharray={`${(c * p).toFixed(1)} ${c.toFixed(1)}`} transform="rotate(-90 23 23)" />
      <text x="23" y="24" textAnchor="middle" dominantBaseline="middle" style={{ fill: 'var(--v-ink)', fontFamily: 'var(--v-mono)', fontSize: 10 }}>{Math.round(p * 100)}%</text>
    </svg>
  );
}

/** Soft blobs + fine grain behind the page (no scan lines, no grid floor). */
export function Backdrop() {
  return (
    <div className="v3-backdrop" aria-hidden="true">
      <i className="b1" /><i className="b2" /><i className="b3" />
      <svg><filter id="v3grain"><feTurbulence type="fractalNoise" baseFrequency=".85" numOctaves="2" stitchTiles="stitch" /><feColorMatrix values="0 0 0 0 .5 0 0 0 0 .5 0 0 0 0 .5 0 0 0 1 0" /></filter><rect width="100%" height="100%" filter="url(#v3grain)" /></svg>
    </div>
  );
}

export function PanelHead({ title, kicker, right, as = 'h2' }: { title: ReactNode; kicker?: ReactNode; right?: ReactNode; as?: 'h1' | 'h2' }) {
  const H = as;
  return (
    <div className="v3-ph">
      <H className="v3-disp">{title}</H>
      {kicker && <span className="v3-kick" style={{ marginLeft: 6 }}>{kicker}</span>}
      {right && <span className="r">{right}</span>}
    </div>
  );
}

export function Empty({ title, children, action }: { title: ReactNode; children?: ReactNode; action?: ReactNode }) {
  return <div className="v3-empty"><b>{title}</b>{children}{action && <div>{action}</div>}</div>;
}
