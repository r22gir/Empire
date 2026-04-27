'use client';
import React from 'react';
import { ChevronRight } from 'lucide-react';

interface Breadcrumb {
  label: string;
  href?: string;
}

interface EmpireModuleHeaderProps {
  title: string;
  subtitle?: string;
  breadcrumbs?: Breadcrumb[];
  actions?: React.ReactNode;
  badge?: string;
}

export function EmpireModuleHeader({ title, subtitle, breadcrumbs, actions, badge }: EmpireModuleHeaderProps) {
  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: 'var(--space-5) var(--space-6)',
      borderBottom: '1px solid var(--border-subtle)',
      background: 'var(--panel-bg)',
    }}>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-1)' }}>
        {/* Breadcrumbs */}
        {breadcrumbs && breadcrumbs.length > 0 && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '4px', marginBottom: '4px' }}>
            {breadcrumbs.map((crumb, i) => (
              <React.Fragment key={i}>
                {i > 0 && <ChevronRight size={12} style={{ color: 'var(--text-faint)' }} />}
                <span style={{
                  fontSize: 'var(--text-xs)',
                  color: i === breadcrumbs.length - 1 ? 'var(--text-secondary)' : 'var(--text-muted)',
                  fontWeight: i === breadcrumbs.length - 1 ? 500 : 400,
                }}>
                  {crumb.label}
                </span>
              </React.Fragment>
            ))}
          </div>
        )}

        {/* Title row */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)' }}>
          <h1 style={{
            fontSize: 'var(--text-xl)',
            fontWeight: 700,
            color: 'var(--text-primary)',
            letterSpacing: '-0.3px',
          }}>{title}</h1>
          {badge && (
            <span style={{
              background: 'var(--accent-primary-bg)',
              color: 'var(--accent-primary)',
              border: '1px solid var(--border-accent)',
              borderRadius: 'var(--radius-full)',
              padding: '2px 10px',
              fontSize: 'var(--text-xs)',
              fontWeight: 600,
            }}>
              {badge}
            </span>
          )}
        </div>

        {subtitle && (
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)' }}>{subtitle}</p>
        )}
      </div>

      {actions && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          {actions}
        </div>
      )}
    </div>
  );
}