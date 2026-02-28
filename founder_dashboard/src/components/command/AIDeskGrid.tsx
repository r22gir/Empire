'use client';
import { useState } from 'react';
import { ChevronDown, ChevronRight, Zap, AlertTriangle, Clock, CheckCircle } from 'lucide-react';
import { AIDeskStatus } from '@/lib/types';

interface Props {
  aiDeskStatuses: AIDeskStatus[];
  backendOnline: boolean;
}

const DESK_ICONS: Record<string, string> = {
  forge: '🪟',
  market: '🏪',
  social: '📱',
  support: '🎧',
};

const DESK_SHORT: Record<string, string> = {
  forge: 'Forge',
  market: 'Market',
  social: 'Social',
  support: 'Support',
};

export default function AIDeskGrid({ aiDeskStatuses, backendOnline }: Props) {
  const [open, setOpen] = useState(true);
  const [expandedDesk, setExpandedDesk] = useState<string | null>(null);

  const totalActive = aiDeskStatuses.reduce((s, d) => s + d.active_tasks, 0);
  const totalEscalated = aiDeskStatuses.reduce((s, d) => s + d.escalated, 0);
  const totalCompleted = aiDeskStatuses.reduce((s, d) => s + d.completed_today, 0);
  const busyCount = aiDeskStatuses.filter(d => d.status === 'busy').length;

  const summaryColor = !backendOnline
    ? 'var(--text-muted)'
    : totalEscalated > 0 ? '#f59e0b'
    : busyCount > 0 ? '#22c55e'
    : 'var(--text-secondary)';

  const summary = !backendOnline
    ? 'Backend offline'
    : aiDeskStatuses.length === 0
      ? 'Loading desks...'
      : totalEscalated > 0
        ? `${aiDeskStatuses.length} desks | ${totalEscalated} escalated`
        : totalActive > 0
          ? `${aiDeskStatuses.length} desks | ${totalActive} active`
          : `${aiDeskStatuses.length} desks | idle`;

  const dotClass = !backendOnline ? 'dot-offline'
    : totalEscalated > 0 ? 'dot-warning'
    : busyCount > 0 ? 'dot-online'
    : 'dot-unknown';

  return (
    <div className="cc-panel" style={{ padding: '8px 10px' }}>
      <button
        onClick={() => setOpen(!open)}
        className="w-full flex items-center gap-2"
      >
        <span className={dotClass} />
        <span className="flex-1 text-[11px] font-mono text-left truncate" style={{ color: summaryColor }}>
          {summary}
        </span>
        {open
          ? <ChevronDown className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
          : <ChevronRight className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
        }
      </button>

      {open && aiDeskStatuses.length > 0 && (
        <div className="mt-2 pt-2" style={{ borderTop: '1px solid var(--border)' }}>
          {/* 2x2 desk grid */}
          <div className="grid grid-cols-2 gap-1.5">
            {aiDeskStatuses.map(desk => {
              const isExpanded = expandedDesk === desk.desk_id;
              const icon = DESK_ICONS[desk.desk_id] || '📋';
              const short = DESK_SHORT[desk.desk_id] || desk.desk_id;
              const hasActivity = desk.active_tasks > 0 || desk.escalated > 0 || desk.completed_today > 0;
              const statusColor = desk.status === 'busy' ? '#22c55e'
                : desk.escalated > 0 ? '#f59e0b'
                : 'var(--text-muted)';

              return (
                <button
                  key={desk.desk_id}
                  onClick={() => setExpandedDesk(isExpanded ? null : desk.desk_id)}
                  className="rounded-lg p-1.5 text-left transition"
                  style={{
                    background: isExpanded ? 'var(--elevated)' : 'var(--raised)',
                    border: `1px solid ${isExpanded ? 'var(--gold-border)' : 'var(--border)'}`,
                  }}
                >
                  <div className="flex items-center gap-1.5">
                    <span className="text-[11px]">{icon}</span>
                    <span className="text-[10px] font-semibold flex-1 truncate" style={{ color: 'var(--text-primary)' }}>
                      {short}
                    </span>
                    <span
                      style={{
                        width: '5px', height: '5px', borderRadius: '50%',
                        background: statusColor, flexShrink: 0,
                      }}
                    />
                  </div>

                  {/* Activity badges */}
                  {hasActivity && (
                    <div className="flex gap-1 mt-1">
                      {desk.active_tasks > 0 && (
                        <span className="text-[8px] px-1 rounded font-mono"
                          style={{ background: 'rgba(34,197,94,0.12)', color: '#22c55e' }}>
                          {desk.active_tasks} active
                        </span>
                      )}
                      {desk.escalated > 0 && (
                        <span className="text-[8px] px-1 rounded font-mono"
                          style={{ background: 'rgba(245,158,11,0.12)', color: '#f59e0b' }}>
                          {desk.escalated} esc
                        </span>
                      )}
                      {desk.completed_today > 0 && !desk.active_tasks && !desk.escalated && (
                        <span className="text-[8px] px-1 rounded font-mono"
                          style={{ background: 'rgba(96,165,250,0.12)', color: '#60a5fa' }}>
                          {desk.completed_today} done
                        </span>
                      )}
                    </div>
                  )}
                </button>
              );
            })}
          </div>

          {/* Expanded desk detail */}
          {expandedDesk && (() => {
            const desk = aiDeskStatuses.find(d => d.desk_id === expandedDesk);
            if (!desk) return null;
            return (
              <div className="mt-2 p-2 rounded-lg space-y-1.5" style={{ background: 'var(--elevated)', border: '1px solid var(--border)' }}>
                <div className="text-[10px] font-semibold" style={{ color: 'var(--gold)' }}>
                  {desk.desk_name}
                </div>
                <div className="text-[9px] leading-tight" style={{ color: 'var(--text-muted)' }}>
                  {desk.description.length > 120 ? desk.description.slice(0, 120) + '…' : desk.description}
                </div>

                {/* Stats row */}
                <div className="grid grid-cols-3 gap-1 pt-1">
                  <div className="text-center rounded py-0.5" style={{ background: 'var(--surface)' }}>
                    <div className="text-[10px] font-mono" style={{ color: desk.active_tasks > 0 ? '#22c55e' : 'var(--text-muted)' }}>
                      {desk.active_tasks}
                    </div>
                    <div className="text-[7px]" style={{ color: 'var(--text-muted)' }}>active</div>
                  </div>
                  <div className="text-center rounded py-0.5" style={{ background: 'var(--surface)' }}>
                    <div className="text-[10px] font-mono" style={{ color: desk.escalated > 0 ? '#f59e0b' : 'var(--text-muted)' }}>
                      {desk.escalated}
                    </div>
                    <div className="text-[7px]" style={{ color: 'var(--text-muted)' }}>escalated</div>
                  </div>
                  <div className="text-center rounded py-0.5" style={{ background: 'var(--surface)' }}>
                    <div className="text-[10px] font-mono" style={{ color: desk.completed_today > 0 ? '#60a5fa' : 'var(--text-muted)' }}>
                      {desk.completed_today}
                    </div>
                    <div className="text-[7px]" style={{ color: 'var(--text-muted)' }}>today</div>
                  </div>
                </div>

                {/* ForgeDesk extras */}
                {desk.pending_followups !== undefined && (desk.pending_followups > 0 || (desk.pending_reminders ?? 0) > 0) && (
                  <div className="flex gap-2 pt-0.5">
                    {desk.pending_followups > 0 && (
                      <div className="flex items-center gap-1 text-[9px]" style={{ color: '#fb923c' }}>
                        <Clock className="w-2.5 h-2.5" />
                        {desk.pending_followups} follow-up{desk.pending_followups !== 1 ? 's' : ''}
                      </div>
                    )}
                    {(desk.pending_reminders ?? 0) > 0 && (
                      <div className="flex items-center gap-1 text-[9px]" style={{ color: '#a78bfa' }}>
                        <AlertTriangle className="w-2.5 h-2.5" />
                        {desk.pending_reminders} reminder{desk.pending_reminders !== 1 ? 's' : ''}
                      </div>
                    )}
                  </div>
                )}

                {/* Capabilities */}
                <div className="flex gap-1 pt-1 flex-wrap">
                  {desk.capabilities.slice(0, 4).map(cap => (
                    <span
                      key={cap}
                      className="text-[8px] px-1 py-0.5 rounded font-mono"
                      style={{
                        background: 'var(--surface)',
                        color: 'var(--text-muted)',
                        border: '1px solid var(--border)',
                      }}
                    >
                      {cap.replace(/_/g, ' ')}
                    </span>
                  ))}
                  {desk.capabilities.length > 4 && (
                    <span className="text-[8px] px-1 py-0.5 rounded font-mono" style={{ color: 'var(--text-muted)' }}>
                      +{desk.capabilities.length - 4}
                    </span>
                  )}
                </div>
              </div>
            );
          })()}

          {/* Footer summary */}
          <div className="flex justify-between text-[9px] pt-1.5 mt-1.5 font-mono" style={{ borderTop: '1px solid var(--border)', color: 'var(--text-muted)' }}>
            <span>{totalCompleted} done today</span>
            <span>{totalActive} active</span>
            <span>{totalEscalated} escalated</span>
          </div>
        </div>
      )}
    </div>
  );
}
