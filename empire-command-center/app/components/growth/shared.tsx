'use client';
import React, { useEffect, useState } from 'react';

export function useIsMobile(bp = 767) {
  const [m, setM] = useState(false);
  useEffect(() => {
    const q = window.matchMedia(`(max-width: ${bp}px)`);
    const on = () => setM(q.matches);
    on(); q.addEventListener('change', on);
    return () => q.removeEventListener('change', on);
  }, [bp]);
  return m;
}

export const card: React.CSSProperties = { background: '#fff', border: '1px solid #e5e2dc', borderRadius: 12, padding: 14 };
export const muted: React.CSSProperties = { fontSize: 12, color: '#888' };

export type BtnKind = 'primary' | 'ok' | 'info' | 'danger' | 'accent' | 'ghost';

const KIND_FROM_BG: Record<string, BtnKind> = {
  '#1a1a1a': 'primary',
  '#16a34a': 'ok',
  '#15803d': 'ok',
  '#1d4ed8': 'info',
  '#b91c1c': 'danger',
  '#dc2626': 'danger',
  '#7c3aed': 'accent',
};

export function btnKind(bg: string): BtnKind {
  return KIND_FROM_BG[bg.trim().toLowerCase()] || 'primary';
}

export function btnClass(kind: BtnKind | string = 'primary'): string {
  const k = kind.startsWith('#') ? btnKind(kind) : (kind || 'primary');
  return `gf-btn gf-btn--${k}`;
}

/**
 * Layout fallback for leftover style={btn()} callers.
 * Never emits color:#fff — gold theme remaps that to dark ink, which
 * disappears on the old #1a1a1a primary fill. Colors live on .gf-btn.
 */
export function btn(bg: string, color?: string): React.CSSProperties {
  const kind = KIND_FROM_BG[bg.trim().toLowerCase()];
  const keepColor = color && color !== '#fff';
  return {
    display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 14px', minHeight: 40,
    borderRadius: 8, border: 'none', fontSize: 13, fontWeight: 600, cursor: 'pointer',
    background: kind ? `var(--gf-${kind}-bg, var(--v-ink, #1a1a1a))` : bg,
    color: keepColor ? color : (kind ? `var(--gf-${kind}-fg, var(--v-page, #f7f3ea))` : 'var(--v-page, #f7f3ea)'),
    WebkitTextFillColor: keepColor ? color : (kind ? `var(--gf-${kind}-fg, var(--v-page, #f7f3ea))` : 'var(--v-page, #f7f3ea)'),
  };
}

export const ghost: React.CSSProperties = { ...btn('transparent', 'inherit'), border: '1px solid #e5e2dc', WebkitTextFillColor: 'inherit' };
export const input: React.CSSProperties = { width: '100%', boxSizing: 'border-box', padding: '9px 10px', border: '1px solid #e5e2dc',
  borderRadius: 8, fontSize: 14, background: '#fff', color: 'inherit' };

type BtnProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  kind?: BtnKind;
  loading?: boolean;
};

export function Btn({ kind = 'primary', loading, className, disabled, children, type = 'button', ...rest }: BtnProps) {
  return (
    <button
      type={type}
      className={[btnClass(kind), className].filter(Boolean).join(' ')}
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      {...rest}
    >
      {children}
    </button>
  );
}

export function Badge({ text, bg = '#f5f3ef', color = '#555', wrap = false }: { text: string; bg?: string; color?: string; wrap?: boolean }) {
  return <span style={{ fontSize: 11, fontWeight: 700, padding: '3px 8px', borderRadius: 999, background: bg, color,
    whiteSpace: wrap ? 'normal' : 'nowrap', overflowWrap: wrap ? 'anywhere' : undefined, minWidth: 0, maxWidth: '100%' }}>{text}</span>;
}

export function Header({ title, subtitle, right }: { title: string; subtitle?: string; right?: React.ReactNode }) {
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 10, justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
      <div style={{ minWidth: 0 }}>
        <h2 style={{ fontSize: 20, fontWeight: 700, margin: 0, color: '#1a1a1a' }}>{title}</h2>
        {subtitle && <p style={{ ...muted, marginTop: 4, marginBottom: 0, maxWidth: 720 }}>{subtitle}</p>}
      </div>
      {right}
    </div>
  );
}

export const money = (n: number | null | undefined) =>
  n == null ? '—' : `$${Number(n).toLocaleString(undefined, { maximumFractionDigits: 0 })}`;
