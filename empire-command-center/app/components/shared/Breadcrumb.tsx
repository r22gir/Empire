'use client';
import React, { useState, useEffect } from 'react';
import { ChevronRight, ArrowLeft } from 'lucide-react';
import { readTheme } from '../ThemeToggle';

export interface BreadcrumbItem {
  label: string;
  onClick?: () => void;
  active?: boolean;
}

interface BreadcrumbProps {
  items: BreadcrumbItem[];
  onBack?: () => void;
  backLabel?: string;
  theme?: 'dark' | 'gold' | 'light';
  style?: React.CSSProperties;
  className?: string;
}

export default function Breadcrumb({ items, onBack, backLabel = 'Back', theme: propTheme, style: propStyle, className = '' }: BreadcrumbProps) {
  const [theme, setTheme] = useState<'dark' | 'gold'>(readTheme());
  useEffect(() => {
    setTheme(readTheme());
    const sync = () => setTheme(readTheme());
    window.addEventListener('empire-theme', sync);
    return () => window.removeEventListener('empire-theme', sync);
  }, []);
  const activeTheme = propTheme === 'dark' ? 'dark' : propTheme === 'light' || propTheme === 'gold' ? 'gold' : theme;
  const isDark = activeTheme === 'dark';

  return (
    <div
      className={className}
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 8,
        padding: '8px 12px',
        marginBottom: 16,
        borderRadius: 10,
        background: isDark ? 'rgba(18, 24, 33, 0.7)' : '#ffffff',
        border: `1px solid ${isDark ? 'rgba(255, 255, 255, 0.08)' : '#ece8e0'}`,
        ...propStyle,
      }}
    >
      <nav aria-label="Breadcrumb" style={{ display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap', fontSize: 13 }}>
        {items.map((item, idx) => {
          const isLast = idx === items.length - 1;
          return (
            <React.Fragment key={idx}>
              {idx > 0 && <ChevronRight size={14} style={{ color: isDark ? '#6b7682' : '#999' }} />}
              {item.onClick && !isLast ? (
                <button
                  type="button"
                  onClick={item.onClick}
                  style={{
                    background: 'none',
                    border: 'none',
                    padding: '4px 6px',
                    borderRadius: 6,
                    color: isDark ? '#22d3ee' : '#b8960c',
                    cursor: 'pointer',
                    fontWeight: 600,
                    fontSize: 13,
                    display: 'inline-flex',
                    alignItems: 'center',
                  }}
                >
                  {item.label}
                </button>
              ) : (
                <span
                  style={{
                    padding: '4px 6px',
                    color: isLast ? (isDark ? '#f4f7fa' : '#1a1a1a') : (isDark ? '#8b96a3' : '#666'),
                    fontWeight: isLast ? 700 : 500,
                  }}
                  aria-current={isLast ? 'page' : undefined}
                >
                  {item.label}
                </span>
              )}
            </React.Fragment>
          );
        })}
      </nav>

      {onBack && (
        <button
          type="button"
          onClick={onBack}
          style={{
            minHeight: 44,
            minWidth: 44,
            display: 'inline-flex',
            alignItems: 'center',
            gap: 6,
            padding: '6px 14px',
            borderRadius: 8,
            background: isDark ? 'rgba(255, 255, 255, 0.05)' : '#faf9f7',
            border: `1px solid ${isDark ? 'rgba(255, 255, 255, 0.12)' : '#ece8e0'}`,
            color: isDark ? '#e6edf3' : '#555',
            fontSize: 12,
            fontWeight: 600,
            cursor: 'pointer',
          }}
        >
          <ArrowLeft size={14} /> {backLabel}
        </button>
      )}
    </div>
  );
}
