'use client';
import React from 'react';

interface EmpireMetricCardProps {
  title: string;
  value: string | number;
  trend?: string;
  icon?: React.ReactNode;
  color?: 'primary' | 'success' | 'warning' | 'error' | 'muted';
  subtitle?: string;
  onClick?: () => void;
}

const colorValueMap = {
  primary: 'var(--accent-primary)',
  success: 'var(--success)',
  warning: 'var(--warning)',
  error: 'var(--error)',
  muted: 'var(--text-secondary)',
};

export function EmpireMetricCard({
  title,
  value,
  trend,
  icon,
  color = 'primary',
  subtitle,
  onClick,
}: EmpireMetricCardProps) {
  return (
    <div
      onClick={onClick}
      style={{
        background: 'var(--panel-bg)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-lg)',
        padding: 'var(--space-5)',
        cursor: onClick ? 'pointer' : 'default',
        transition: 'all var(--transition-base)',
        position: 'relative',
        overflow: 'hidden',
      }}
      onMouseEnter={(e) => {
        if (onClick) {
          e.currentTarget.style.borderColor = 'var(--border-default)';
          e.currentTarget.style.boxShadow = 'var(--shadow-card)';
        }
      }}
      onMouseLeave={(e) => {
        if (onClick) {
          e.currentTarget.style.borderColor = 'var(--border-subtle)';
          e.currentTarget.style.boxShadow = 'none';
        }
      }}
    >
      {/* Accent bar */}
      <div style={{
        position: 'absolute',
        top: 0,
        left: 0,
        right: 0,
        height: '2px',
        background: `linear-gradient(90deg, ${colorValueMap[color]}, transparent)`,
        opacity: 0.6,
      }} />

      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 'var(--space-3)' }}>
        <span style={{ fontSize: 'var(--text-xs)', fontWeight: 500, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.8px' }}>
          {title}
        </span>
        {icon && (
          <span style={{ color: colorValueMap[color], opacity: 0.8 }}>{icon}</span>
        )}
      </div>

      <div style={{
        fontSize: 'var(--text-3xl)',
        fontWeight: 700,
        color: colorValueMap[color],
        lineHeight: 1,
        marginBottom: 'var(--space-2)',
      }}>
        {value}
      </div>

      {(trend || subtitle) && (
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)' }}>
          {trend && (
            <span style={{
              fontSize: 'var(--text-xs)',
              fontWeight: 500,
              color: trend.startsWith('+') ? 'var(--success)' : trend.startsWith('-') ? 'var(--error)' : 'var(--text-muted)',
            }}>
              {trend}
            </span>
          )}
          {subtitle && (
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{subtitle}</span>
          )}
        </div>
      )}
    </div>
  );
}