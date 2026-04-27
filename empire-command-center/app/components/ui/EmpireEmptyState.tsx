'use client';
import React from 'react';

interface EmpireEmptyStateProps {
  icon?: React.ReactNode;
  title: string;
  description?: string;
  action?: { label: string; onClick: () => void };
}

export function EmpireEmptyState({ icon, title, description, action }: EmpireEmptyStateProps) {
  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      alignItems: 'center',
      justifyContent: 'center',
      padding: 'var(--space-12) var(--space-6)',
      textAlign: 'center',
      gap: 'var(--space-4)',
    }}>
      {icon && (
        <div style={{
          color: 'var(--text-faint)',
          opacity: 0.6,
        }}>
          {icon}
        </div>
      )}
      <div>
        <h3 style={{
          fontSize: 'var(--text-base)',
          fontWeight: 600,
          color: 'var(--text-secondary)',
          marginBottom: description ? 'var(--space-2)' : 0,
        }}>{title}</h3>
        {description && (
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>{description}</p>
        )}
      </div>
      {action && (
        <button
          onClick={action.onClick}
          style={{
            marginTop: 'var(--space-2)',
            padding: '8px 20px',
            background: 'var(--accent-primary)',
            color: '#fff',
            border: 'none',
            borderRadius: 'var(--radius-md)',
            fontSize: 'var(--text-sm)',
            fontWeight: 500,
            cursor: 'pointer',
            transition: 'all var(--transition-fast)',
          }}
        >
          {action.label}
        </button>
      )}
    </div>
  );
}