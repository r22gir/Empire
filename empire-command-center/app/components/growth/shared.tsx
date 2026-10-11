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

export function btn(bg: string, color = '#fff'): React.CSSProperties {
  return { display: 'inline-flex', alignItems: 'center', gap: 6, padding: '10px 14px', minHeight: 40, borderRadius: 8,
    border: 'none', background: bg, color, fontSize: 13, fontWeight: 600, cursor: 'pointer' };
}
export const ghost: React.CSSProperties = { ...btn('transparent', 'inherit'), border: '1px solid #e5e2dc' };
export const input: React.CSSProperties = { width: '100%', boxSizing: 'border-box', padding: '9px 10px', border: '1px solid #e5e2dc',
  borderRadius: 8, fontSize: 14, background: '#fff', color: 'inherit' };

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
