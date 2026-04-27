'use client';
import React from 'react';

interface EmpireStatusPillProps {
  status: 'success' | 'warning' | 'error' | 'info' | 'pending' | 'neutral';
  label: string;
  pulse?: boolean;
  size?: 'sm' | 'md';
}

const styles: Record<string, React.CSSProperties> = {
  base: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '6px',
    padding: '3px 10px',
    borderRadius: 'var(--radius-full)',
    fontSize: 'var(--text-xs)',
    fontWeight: 600,
    letterSpacing: '0.3px',
    border: '1px solid',
  },
  dot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    flexShrink: 0,
  },
};

const colorMap: Record<string, { color: string; bg: string; border: string }> = {
  success: { color: 'var(--success)', bg: 'var(--success-bg)', border: 'var(--success-border)' },
  warning: { color: 'var(--warning)', bg: 'var(--warning-bg)', border: 'var(--warning-border)' },
  error:   { color: 'var(--error)',   bg: 'var(--error-bg)',   border: 'var(--error-border)' },
  info:    { color: 'var(--info)',    bg: 'var(--info-bg)',    border: 'var(--info-border)' },
  pending: { color: 'var(--pending)', bg: 'var(--pending-bg)', border: 'var(--pending-border)' },
  neutral: { color: 'var(--text-muted)', bg: 'rgba(255,255,255,0.04)', border: 'var(--border-default)' },
};

export function EmpireStatusPill({ status, label, pulse = false, size = 'md' }: EmpireStatusPillProps) {
  const c = colorMap[status] || colorMap.neutral;
  return (
    <span style={{
      ...styles.base,
      color: c.color,
      background: c.bg,
      borderColor: c.border,
      padding: size === 'sm' ? '2px 8px' : '3px 10px',
    }}>
      {pulse && (
        <span style={{
          ...styles.dot,
          background: c.color,
          animation: 'status-pulse 2s ease-in-out infinite',
        }} />
      )}
      {label}
    </span>
  );
}