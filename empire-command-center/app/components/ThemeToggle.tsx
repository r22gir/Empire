'use client';
// Dark / Gold theme switch. Dark (cyan) is the default; Gold is the gold-standard docs palette
// (colors only). The choice is stored per device in localStorage("empire.theme") and applied by
// the early script in app/layout.tsx on every page, so there is no flash on reload.
import { useEffect, useState } from 'react';

export type EmpireTheme = 'dark' | 'gold';
const KEY = 'empire.theme';

export function readTheme(): EmpireTheme {
  if (typeof document === 'undefined') return 'dark';
  return document.documentElement.getAttribute('data-theme') === 'gold' ? 'gold' : 'dark';
}

export function applyTheme(t: EmpireTheme) {
  try { if (t === 'gold') localStorage.setItem(KEY, 'gold'); else localStorage.removeItem(KEY); } catch { /* private mode */ }
  if (t === 'gold') document.documentElement.setAttribute('data-theme', 'gold');
  else document.documentElement.removeAttribute('data-theme');
  window.dispatchEvent(new CustomEvent('empire-theme', { detail: t }));
}

export default function ThemeToggle({ variant = 'bar' }: { variant?: 'bar' | 'ring' }) {
  const [theme, setTheme] = useState<EmpireTheme>('dark');
  useEffect(() => {
    setTheme(readTheme());
    const sync = () => setTheme(readTheme());
    const onStorage = (e: StorageEvent) => { if (e.key === KEY) { applyTheme(e.newValue === 'gold' ? 'gold' : 'dark'); } };
    window.addEventListener('empire-theme', sync);
    window.addEventListener('storage', onStorage);
    return () => { window.removeEventListener('empire-theme', sync); window.removeEventListener('storage', onStorage); };
  }, []);
  const pick = (t: EmpireTheme) => { applyTheme(t); setTheme(t); };
  const next: EmpireTheme = theme === 'gold' ? 'dark' : 'gold';
  return (
    <div className={`th-toggle th-${variant}`} data-theme-toggle="">
      <div className="th-segs" role="radiogroup" aria-label="Color theme">
        {(['dark', 'gold'] as EmpireTheme[]).map(t => (
          <button key={t} type="button" role="radio" aria-checked={theme === t} className={`th-seg${theme === t ? ' is-on' : ''}`}
            onClick={() => pick(t)} title={t === 'dark' ? 'Dark theme (default)' : 'Gold theme (docs palette)'}>
            <i className={`th-dot th-dot-${t}`} aria-hidden="true" />{t === 'dark' ? 'Dark' : 'Gold'}
          </button>
        ))}
      </div>
      <button type="button" className="th-compact" onClick={() => pick(next)}
        aria-label={`Color theme: ${theme === 'gold' ? 'Gold' : 'Dark'}. Switch to ${next === 'gold' ? 'Gold' : 'Dark'}`} title={`Switch to ${next === 'gold' ? 'Gold' : 'Dark'} theme`}>
        <i className="th-dot th-dot-split" aria-hidden="true" />
      </button>
    </div>
  );
}
