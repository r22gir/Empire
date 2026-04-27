'use client';
import React from 'react';

interface EmpireDataPanelProps {
  title: string;
  subtitle?: string;
  actions?: Array<{ label: string; onClick: () => void; variant?: 'primary' | 'secondary' | 'ghost' }>;
  children: React.ReactNode;
  footer?: React.ReactNode;
  noPadding?: boolean;
}

export function EmpireDataPanel({ title, subtitle, actions, children, footer, noPadding }: EmpireDataPanelProps) {
  return (
    <div style={{
      background: 'linear-gradient(145deg, rgba(51,65,85,0.6) 0%, rgba(30,41,59,0.5) 100%)',
      border: '1px solid var(--border-default)',
      boxShadow: 'var(--shadow-card)',
      borderRadius: 'var(--radius-lg)',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: 'var(--space-4) var(--space-5)',
        borderBottom: '1px solid var(--border-subtle)',
        flexShrink: 0,
      }}>
        <div>
          <h3 style={{
            fontSize: 'var(--text-sm)',
            fontWeight: 600,
            color: 'var(--text-primary)',
            marginBottom: subtitle ? '2px' : 0,
          }}>{title}</h3>
          {subtitle && (
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{subtitle}</p>
          )}
        </div>
        {actions && actions.length > 0 && (
          <div style={{ display: 'flex', gap: 'var(--space-2)' }}>
            {actions.map((action, i) => (
              <button
                key={i}
                onClick={action.onClick}
                style={{
                  padding: '5px 12px',
                  fontSize: 'var(--text-xs)',
                  fontWeight: 500,
                  borderRadius: 'var(--radius-sm)',
                  cursor: 'pointer',
                  transition: 'all var(--transition-fast)',
                  background: action.variant === 'primary' ? 'var(--accent-primary)' :
                             action.variant === 'ghost' ? 'transparent' : 'var(--panel-hover)',
                  color: action.variant === 'primary' ? '#fff' : 'var(--text-secondary)',
                  border: action.variant === 'ghost' ? 'none' : '1px solid var(--border-default)',
                }}
              >
                {action.label}
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflow: 'auto', padding: noPadding ? 0 : 'var(--space-4) var(--space-5)' }}>
        {children}
      </div>

      {/* Footer */}
      {footer && (
        <div style={{
          padding: 'var(--space-3) var(--space-5)',
          borderTop: '1px solid var(--border-subtle)',
          flexShrink: 0,
        }}>
          {footer}
        </div>
      )}
    </div>
  );
}