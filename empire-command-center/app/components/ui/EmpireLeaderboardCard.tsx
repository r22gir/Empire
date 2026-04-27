'use client';
import React from 'react';

interface EmpireLeaderboardItem {
  id: string;
  title: string;
  subtitle?: string;
  status?: 'success' | 'warning' | 'error' | 'pending' | 'neutral';
  statusLabel?: string;
  badge?: string;
  onClick?: () => void;
}

interface EmpireLeaderboardCardProps {
  title: string;
  subtitle?: string;
  items: EmpireLeaderboardItem[];
  maxItems?: number;
  emptyMessage?: string;
  onItemClick?: (item: EmpireLeaderboardItem) => void;
  actions?: React.ReactNode;
}

export function EmpireLeaderboardCard({
  title,
  subtitle,
  items,
  maxItems,
  emptyMessage = 'No items',
  onItemClick,
  actions,
}: EmpireLeaderboardCardProps) {
  const displayItems = maxItems ? items.slice(0, maxItems) : items;

  return (
    <div style={{
      background: 'var(--panel-bg)',
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-lg)',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: 'var(--space-4) var(--space-5)',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <div>
          <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>
            {title}
          </h3>
          {subtitle && (
            <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: '2px' }}>{subtitle}</p>
          )}
        </div>
        {actions && <div>{actions}</div>}
      </div>

      {/* List */}
      <div style={{ overflowY: 'auto', maxHeight: '320px' }}>
        {displayItems.length === 0 ? (
          <div style={{
            padding: 'var(--space-8) var(--space-5)',
            textAlign: 'center',
            color: 'var(--text-muted)',
            fontSize: 'var(--text-sm)',
          }}>
            {emptyMessage}
          </div>
        ) : (
          displayItems.map((item, i) => (
            <div
              key={item.id}
              onClick={() => onItemClick?.(item)}
              style={{
                display: 'flex',
                alignItems: 'center',
                gap: 'var(--space-3)',
                padding: 'var(--space-3) var(--space-5)',
                borderBottom: i < displayItems.length - 1 ? '1px solid var(--border-subtle)' : 'none',
                cursor: onItemClick ? 'pointer' : 'default',
                transition: 'background var(--transition-fast)',
                background: 'transparent',
              }}
              onMouseEnter={(e) => {
                e.currentTarget.style.background = 'var(--panel-hover)';
              }}
              onMouseLeave={(e) => {
                e.currentTarget.style.background = 'transparent';
              }}
            >
              {/* Rank number */}
              <span style={{
                fontSize: 'var(--text-xs)',
                fontWeight: 700,
                color: i < 3 ? 'var(--accent-primary)' : 'var(--text-muted)',
                minWidth: '20px',
                fontFamily: 'var(--font-mono)',
              }}>
                {String(i + 1).padStart(2, '0')}
              </span>

              {/* Content */}
              <div style={{ flex: 1, minWidth: 0 }}>
                <p style={{
                  fontSize: 'var(--text-sm)',
                  fontWeight: 500,
                  color: 'var(--text-primary)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                }}>{item.title}</p>
                {item.subtitle && (
                  <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>{item.subtitle}</p>
                )}
              </div>

              {/* Badge + status */}
              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', flexShrink: 0 }}>
                {item.badge && (
                  <span style={{
                    fontSize: 'var(--text-xs)',
                    background: 'var(--accent-primary-bg)',
                    color: 'var(--accent-primary)',
                    padding: '2px 8px',
                    borderRadius: 'var(--radius-full)',
                    fontWeight: 500,
                  }}>
                    {item.badge}
                  </span>
                )}
                {item.status && item.statusLabel && (
                  <span style={{
                    fontSize: 'var(--text-xs)',
                    fontWeight: 600,
                    padding: '2px 8px',
                    borderRadius: 'var(--radius-full)',
                    background: item.status === 'success' ? 'var(--success-bg)' :
                               item.status === 'warning' ? 'var(--warning-bg)' :
                               item.status === 'error' ? 'var(--error-bg)' :
                               item.status === 'pending' ? 'var(--pending-bg)' :
                               'rgba(255,255,255,0.04)',
                    color: item.status === 'success' ? 'var(--success)' :
                           item.status === 'warning' ? 'var(--warning)' :
                           item.status === 'error' ? 'var(--error)' :
                           item.status === 'pending' ? 'var(--pending)' :
                           'var(--text-muted)',
                    border: `1px solid ${item.status === 'success' ? 'var(--success-border)' :
                                    item.status === 'warning' ? 'var(--warning-border)' :
                                    item.status === 'error' ? 'var(--error-border)' :
                                    item.status === 'pending' ? 'var(--pending-border)' :
                                    'var(--border-default)'}`,
                  }}>
                    {item.statusLabel}
                  </span>
                )}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}