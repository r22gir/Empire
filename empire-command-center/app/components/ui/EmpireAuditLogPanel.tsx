'use client';
import React from 'react';

interface AuditEntry {
  id: string;
  timestamp: string;
  user: string;
  action: string;
  detail?: string;
  severity?: 'info' | 'warning' | 'error';
}

interface EmpireAuditLogPanelProps {
  logs: AuditEntry[];
  title?: string;
  filter?: string;
  maxHeight?: number;
}

const severityColors: Record<string, string> = {
  error: 'var(--error)',
  warning: 'var(--warning)',
  info: 'var(--accent-primary)',
};

export function EmpireAuditLogPanel({ logs, title = 'Audit Log', filter, maxHeight = 400 }: EmpireAuditLogPanelProps) {
  const filtered = filter
    ? logs.filter(l => l.action.toLowerCase().includes(filter.toLowerCase()) || l.user.toLowerCase().includes(filter.toLowerCase()))
    : logs;

  return (
    <div style={{
      background: 'var(--panel-bg)',
      border: '1px solid var(--border-subtle)',
      borderRadius: 'var(--radius-lg)',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
    }}>
      <div style={{
        padding: 'var(--space-4) var(--space-5)',
        borderBottom: '1px solid var(--border-subtle)',
      }}>
        <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-primary)' }}>{title}</h3>
        {filter && <p style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)', marginTop: '2px' }}>Filtered: &quot;{filter}&quot;</p>}
      </div>

      <div style={{ overflowY: 'auto', maxHeight }}>
        {filtered.length === 0 ? (
          <div style={{ padding: 'var(--space-8)', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--text-sm)' }}>
            No log entries
          </div>
        ) : (
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                {['Time', 'User', 'Action', 'Detail'].map(h => (
                  <th key={h} style={{
                    textAlign: 'left',
                    padding: '8px var(--space-4)',
                    fontSize: 'var(--text-xs)',
                    fontWeight: 600,
                    color: 'var(--text-muted)',
                    textTransform: 'uppercase',
                    letterSpacing: '0.5px',
                  }}>{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((log) => (
                <tr key={log.id} style={{ borderBottom: '1px solid var(--border-subtle)' }}>
                  <td style={{ padding: '9px var(--space-4)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)', fontFamily: 'var(--font-mono)' }}>
                    {new Date(log.timestamp).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                  </td>
                  <td style={{ padding: '9px var(--space-4)', fontSize: 'var(--text-xs)', color: 'var(--text-secondary)', fontWeight: 500 }}>
                    {log.user}
                  </td>
                  <td style={{ padding: '9px var(--space-4)' }}>
                    <span style={{
                      fontSize: 'var(--text-xs)',
                      fontWeight: 500,
                      color: log.severity ? severityColors[log.severity] : 'var(--text-primary)',
                    }}>
                      {log.action}
                    </span>
                  </td>
                  <td style={{ padding: '9px var(--space-4)', fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                    {log.detail || '—'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}