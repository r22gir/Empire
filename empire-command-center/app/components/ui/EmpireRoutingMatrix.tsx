'use client';
import React from 'react';

interface Provider {
  id: string;
  name: string;
  status: 'online' | 'degraded' | 'offline';
  latency?: string;
  cost?: string;
  model?: string;
}

interface EmpireRoutingMatrixProps {
  providers: Provider[];
  title?: string;
  subtitle?: string;
}

export function EmpireRoutingMatrix({ providers, title = 'AI Provider Routing', subtitle }: EmpireRoutingMatrixProps) {
  const activeProviders = providers.filter(p => p.status !== 'offline');
  const inactiveProviders = providers.filter(p => p.status === 'offline');

  return (
    <div style={{
      background: 'var(--panel-bg)',
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-lg)',
      overflow: 'hidden',
    }}>
      {/* Header */}
      <div style={{
        padding: 'var(--space-4) var(--space-5)',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>{title}</h3>
        {subtitle && <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: '2px' }}>{subtitle}</p>}
      </div>

      {/* Flow visualization */}
      <div style={{ padding: 'var(--space-5)' }}>
        {/* Chain visualization */}
        <div style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0',
          overflowX: 'auto',
          paddingBottom: 'var(--space-2)',
        }}>
          {providers.map((provider, i) => (
            <React.Fragment key={provider.id}>
              {/* Provider node */}
              <div style={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                minWidth: '80px',
              }}>
                <div style={{
                  width: '48px',
                  height: '48px',
                  borderRadius: 'var(--radius-md)',
                  background: provider.status === 'online' ? 'var(--success-bg)' :
                             provider.status === 'degraded' ? 'var(--warning-bg)' :
                             'rgba(255,255,255,0.03)',
                  border: `2px solid ${provider.status === 'online' ? 'var(--success-border)' :
                                        provider.status === 'degraded' ? 'var(--warning-border)' :
                                        'var(--border-subtle)'}`,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  position: 'relative',
                }}>
                  <span style={{
                    fontSize: 'var(--text-xs)',
                    fontWeight: 700,
                    color: provider.status === 'online' ? 'var(--success)' :
                           provider.status === 'degraded' ? 'var(--warning)' :
                           'var(--text-muted)',
                  }}>
                    {provider.name.slice(0, 2).toUpperCase()}
                  </span>
                  {provider.status === 'online' && (
                    <span style={{
                      position: 'absolute',
                      top: '-3px',
                      right: '-3px',
                      width: '10px',
                      height: '10px',
                      background: 'var(--success)',
                      borderRadius: '50%',
                      border: '2px solid var(--panel-bg)',
                      animation: 'status-pulse 2s ease-in-out infinite',
                    }} />
                  )}
                </div>
                <p style={{
                  fontSize: 'var(--text-xs)',
                  fontWeight: 600,
                  color: provider.status === 'online' ? 'var(--text-primary)' : 'var(--text-muted)',
                  marginTop: '6px',
                  textAlign: 'center',
                }}>{provider.name}</p>
                {provider.latency && (
                  <p style={{ fontSize: '10px', color: 'var(--text-muted)', marginTop: '2px' }}>
                    {provider.latency}
                  </p>
                )}
                {provider.model && (
                  <p style={{
                    fontSize: '10px',
                    color: 'var(--accent-secondary)',
                    marginTop: '1px',
                    maxWidth: '72px',
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}>
                    {provider.model}
                  </p>
                )}
              </div>

              {/* Connector arrow */}
              {i < providers.length - 1 && (
                <div style={{
                  display: 'flex',
                  alignItems: 'center',
                  padding: '0 4px',
                  color: providers[i + 1].status !== 'offline' ? 'var(--success)' : 'var(--text-faint)',
                  flexShrink: 0,
                }}>
                  <svg width="20" height="12" viewBox="0 0 20 12" fill="none">
                    <path d="M0 6H16M16 6L11 1M16 6L11 11" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round"/>
                  </svg>
                </div>
              )}
            </React.Fragment>
          ))}
        </div>

        {/* Legend */}
        <div style={{
          display: 'flex',
          gap: 'var(--space-4)',
          marginTop: 'var(--space-4)',
          paddingTop: 'var(--space-3)',
          borderTop: '1px solid var(--border-subtle)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--success)' }} />
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Online</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--warning)' }} />
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Degraded</span>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
            <span style={{ width: '8px', height: '8px', borderRadius: '50%', background: 'var(--text-faint)' }} />
            <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>Offline/Fallback</span>
          </div>
        </div>
      </div>
    </div>
  );
}