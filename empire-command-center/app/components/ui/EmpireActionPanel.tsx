'use client';
import React from 'react';

interface EmpireAction {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger';
  icon?: React.ReactNode;
  disabled?: boolean;
  loading?: boolean;
}

interface EmpireActionPanelProps {
  actions: EmpireAction[];
  layout?: 'horizontal' | 'vertical';
}

export function EmpireActionPanel({ actions, layout = 'horizontal' }: EmpireActionPanelProps) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: layout === 'vertical' ? 'column' : 'row',
      flexWrap: 'wrap',
      gap: 'var(--space-2)',
      padding: 'var(--space-2) 0',
    }}>
      {actions.map((action, i) => {
        const isPrimary = action.variant === 'primary';
        const isDanger = action.variant === 'danger';
        const isGhost = action.variant === 'ghost';
        const isSecondary = !isPrimary && !isDanger && !isGhost;

        return (
          <button
            key={i}
            onClick={action.onClick}
            disabled={action.disabled || action.loading}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '6px',
              padding: isPrimary ? '9px 20px' : '7px 16px',
              fontSize: 'var(--text-sm)',
              fontWeight: 500,
              borderRadius: 'var(--radius-md)',
              cursor: action.disabled || action.loading ? 'not-allowed' : 'pointer',
              transition: 'all var(--transition-fast)',
              opacity: action.disabled ? 0.5 : 1,
              background: isPrimary ? 'var(--accent-primary)' :
                         isDanger ? 'var(--error)' :
                         isGhost ? 'transparent' : 'var(--panel-hover)',
              color: isPrimary ? '#fff' :
                     isDanger ? '#fff' :
                     isGhost ? 'var(--text-secondary)' : 'var(--text-primary)',
              border: isPrimary ? 'none' :
                      isDanger ? 'none' :
                      isGhost ? 'none' : '1px solid var(--border-default)',
              boxShadow: isPrimary ? '0 2px 8px rgba(99,102,241,0.3)' : 'none',
            }}
          >
            {action.loading ? (
              <span style={{
                width: '14px',
                height: '14px',
                border: '2px solid rgba(255,255,255,0.3)',
                borderTopColor: isPrimary || isDanger ? '#fff' : 'var(--accent-primary)',
                borderRadius: '50%',
                animation: 'spin 0.7s linear infinite',
              }} />
            ) : action.icon ? (
              <span style={{ display: 'flex', alignItems: 'center' }}>{action.icon}</span>
            ) : null}
            {action.label}
          </button>
        );
      })}
    </div>
  );
}