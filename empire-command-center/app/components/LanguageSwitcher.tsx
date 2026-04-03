'use client';
import { useState, useRef, useEffect } from 'react';
import { useTranslation } from '../lib/i18n';
import { SUPPORTED_LOCALES } from '../lib/i18n/types';

export default function LanguageSwitcher() {
  const { locale, setLocale } = useTranslation();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener('mousedown', handler);
    return () => document.removeEventListener('mousedown', handler);
  }, []);

  const current = SUPPORTED_LOCALES.find(l => l.code === locale) || SUPPORTED_LOCALES[0];

  return (
    <div ref={ref} style={{ position: 'relative', display: 'inline-block' }}>
      <button
        onClick={() => setOpen(!open)}
        style={{
          display: 'flex', alignItems: 'center', gap: 4,
          background: 'none', border: '1px solid #e5e2dc', borderRadius: 6,
          padding: '4px 8px', cursor: 'pointer', fontSize: 12, color: '#666',
          fontWeight: 600, minHeight: 32,
        }}
        title="Change language"
      >
        <span>{current.flag}</span>
        <span>{current.code.toUpperCase()}</span>
      </button>
      {open && (
        <div style={{
          position: 'absolute', top: '100%', right: 0, marginTop: 4,
          background: '#fff', border: '1px solid #e5e2dc', borderRadius: 8,
          boxShadow: '0 4px 12px rgba(0,0,0,0.1)', zIndex: 1000,
          minWidth: 150, overflow: 'hidden',
        }}>
          {SUPPORTED_LOCALES.map(l => (
            <button
              key={l.code}
              onClick={() => { setLocale(l.code); setOpen(false); }}
              style={{
                display: 'flex', alignItems: 'center', gap: 8, width: '100%',
                padding: '10px 14px', border: 'none', cursor: 'pointer',
                background: locale === l.code ? '#f5f3ef' : '#fff',
                fontSize: 13, color: '#333', fontWeight: locale === l.code ? 600 : 400,
                textAlign: 'left',
              }}
            >
              <span style={{ fontSize: 16 }}>{l.flag}</span>
              <span>{l.label}</span>
              {locale === l.code && <span style={{ marginLeft: 'auto', color: '#b8960c' }}>✓</span>}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
