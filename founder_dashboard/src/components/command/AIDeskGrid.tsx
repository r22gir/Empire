'use client';
import { useState } from 'react';
import {
  ChevronDown, ChevronRight, Zap, AlertTriangle, Clock, CheckCircle,
  Activity, XCircle, ArrowUpRight, User, Play, Pause
} from 'lucide-react';
import { AIDeskStatus, DeskTaskDetail } from '@/lib/types';

interface Props {
  aiDeskStatuses: AIDeskStatus[];
  backendOnline: boolean;
}

const DESK_ICONS: Record<string, string> = {
  forge: '🪟', market: '🏪', marketing: '📣', support: '🎧',
  sales: '💰', finance: '📊', clients: '👥', contractors: '🔨',
  it: '🖥️', website: '🌐', legal: '⚖️', lab: '🧪',
  social: '📱',
};

function timeAgo(iso: string | undefined | null): string {
  if (!iso) return 'never';
  const diff = Date.now() - new Date(iso).getTime();
  if (diff < 60000) return 'just now';
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
  return `${Math.floor(diff / 86400000)}d ago`;
}

function stateColor(state: string): string {
  switch (state) {
    case 'completed': return '#22c55e';
    case 'in_progress': return '#3b82f6';
    case 'escalated': return '#f59e0b';
    case 'failed': return '#ef4444';
    default: return 'var(--text-muted)';
  }
}

function priorityLabel(p: string): { color: string; text: string } {
  switch (p) {
    case 'urgent': return { color: '#ef4444', text: 'URG' };
    case 'high': return { color: '#f59e0b', text: 'HIGH' };
    case 'normal': return { color: 'var(--text-muted)', text: '' };
    case 'low': return { color: '#6b7280', text: 'LOW' };
    default: return { color: 'var(--text-muted)', text: '' };
  }
}

/* ── Single task row ──────────────────────────────────────────── */
function TaskRow({ task, expanded, onToggle }: { task: DeskTaskDetail; expanded: boolean; onToggle: () => void }) {
  const pri = priorityLabel(task.priority);
  return (
    <div>
      <button onClick={onToggle} className="w-full text-left px-2 py-1 rounded transition hover:bg-[var(--elevated)]">
        <div className="flex items-center gap-1.5">
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: stateColor(task.state), flexShrink: 0 }} />
          <span className="text-[10px] flex-1 truncate" style={{ color: 'var(--text-primary)' }}>{task.title}</span>
          {pri.text && <span className="text-[7px] font-bold px-1 rounded" style={{ color: pri.color }}>{pri.text}</span>}
          <span className="text-[8px] font-mono" style={{ color: 'var(--text-muted)' }}>{timeAgo(task.completed_at || task.created_at)}</span>
        </div>
      </button>
      {expanded && (
        <div className="ml-4 mr-1 mb-1 p-2 rounded text-[9px] space-y-1" style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}>
          {task.customer_name && (
            <div className="flex items-center gap-1" style={{ color: 'var(--gold)' }}>
              <User className="w-2.5 h-2.5" /> {task.customer_name}
            </div>
          )}
          {task.result && (
            <div style={{ color: 'var(--text-secondary)', lineHeight: '1.4' }}>
              {task.result.length > 300 ? task.result.slice(0, 300) + '…' : task.result}
            </div>
          )}
          {task.escalation_reason && (
            <div className="flex items-center gap-1" style={{ color: '#f59e0b' }}>
              <AlertTriangle className="w-2.5 h-2.5" /> {task.escalation_reason}
            </div>
          )}
          {/* Action log */}
          {task.actions.length > 0 && (
            <div className="pt-1 space-y-0.5" style={{ borderTop: '1px solid var(--border)' }}>
              {task.actions.slice(-5).map((a, i) => (
                <div key={i} className="flex items-center gap-1 text-[8px]" style={{ color: a.success ? 'var(--text-muted)' : '#ef4444' }}>
                  {a.success ? <CheckCircle className="w-2 h-2" /> : <XCircle className="w-2 h-2" />}
                  <span className="font-mono">{a.action}</span>
                  <span className="flex-1 truncate">{a.detail}</span>
                  <span className="font-mono">{timeAgo(a.timestamp)}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

/* ── Expanded desk detail ─────────────────────────────────────── */
function DeskDetail({ desk }: { desk: AIDeskStatus }) {
  const [expandedTask, setExpandedTask] = useState<string | null>(null);
  const [tab, setTab] = useState<'active' | 'completed' | 'escalated'>('active');

  const activeTasks = desk.active_task_details || [];
  const completedTasks = desk.recent_completed || [];
  const escalatedTasks = desk.escalated_task_details || [];

  const tabs = [
    { key: 'active' as const, label: 'Active', count: activeTasks.length, color: '#3b82f6' },
    { key: 'completed' as const, label: 'Done', count: completedTasks.length, color: '#22c55e' },
    { key: 'escalated' as const, label: 'Escalated', count: escalatedTasks.length, color: '#f59e0b' },
  ];

  const currentTasks = tab === 'active' ? activeTasks : tab === 'completed' ? completedTasks : escalatedTasks;

  return (
    <div className="mt-2 rounded-lg overflow-hidden" style={{ background: 'var(--elevated)', border: '1px solid var(--gold-border)' }}>
      {/* Header */}
      <div className="px-3 py-2 flex items-center gap-2" style={{ borderBottom: '1px solid var(--border)' }}>
        <span className="text-sm">{DESK_ICONS[desk.desk_id] || '📋'}</span>
        <div className="flex-1 min-w-0">
          <div className="text-[11px] font-bold" style={{ color: 'var(--gold)' }}>{desk.desk_name}</div>
          <div className="text-[8px]" style={{ color: 'var(--text-muted)' }}>
            Last activity: {timeAgo(desk.last_activity)}
            {desk.completed_total ? ` · ${desk.completed_total} total tasks` : ''}
          </div>
        </div>
        <span
          className="text-[8px] px-1.5 py-0.5 rounded font-mono font-bold"
          style={{
            background: desk.status === 'busy' ? 'rgba(34,197,94,0.15)' : 'var(--surface)',
            color: desk.status === 'busy' ? '#22c55e' : 'var(--text-muted)',
          }}
        >
          {desk.status.toUpperCase()}
        </span>
      </div>

      {/* Stat counters */}
      <div className="grid grid-cols-4 gap-0.5 px-2 py-1.5" style={{ background: 'var(--surface)' }}>
        {[
          { label: 'Active', val: desk.active_tasks, color: '#3b82f6' },
          { label: 'Today', val: desk.completed_today, color: '#22c55e' },
          { label: 'Escalated', val: desk.escalated, color: '#f59e0b' },
          { label: 'Total', val: desk.completed_total || 0, color: 'var(--text-secondary)' },
        ].map(s => (
          <div key={s.label} className="text-center">
            <div className="text-[12px] font-mono font-bold" style={{ color: s.val > 0 ? s.color : 'var(--text-muted)' }}>{s.val}</div>
            <div className="text-[7px]" style={{ color: 'var(--text-muted)' }}>{s.label}</div>
          </div>
        ))}
      </div>

      {/* Tab bar */}
      <div className="flex gap-0.5 px-2 pt-1.5">
        {tabs.map(t => (
          <button
            key={t.key}
            onClick={() => setTab(t.key)}
            className="flex-1 text-center py-1 rounded text-[9px] font-medium transition"
            style={{
              background: tab === t.key ? 'var(--surface)' : 'transparent',
              color: tab === t.key ? t.color : 'var(--text-muted)',
              border: tab === t.key ? '1px solid var(--border)' : '1px solid transparent',
            }}
          >
            {t.label} {t.count > 0 && <span className="font-mono">({t.count})</span>}
          </button>
        ))}
      </div>

      {/* Task list */}
      <div className="px-1 py-1.5 max-h-[240px] overflow-auto space-y-0.5">
        {currentTasks.length === 0 ? (
          <div className="text-center py-3 text-[9px]" style={{ color: 'var(--text-muted)' }}>
            No {tab} tasks
          </div>
        ) : (
          currentTasks.map(task => (
            <TaskRow
              key={task.id}
              task={task}
              expanded={expandedTask === task.id}
              onToggle={() => setExpandedTask(expandedTask === task.id ? null : task.id)}
            />
          ))
        )}
      </div>

      {/* Capabilities footer */}
      <div className="px-2 py-1.5 flex gap-1 flex-wrap" style={{ borderTop: '1px solid var(--border)' }}>
        {desk.capabilities.slice(0, 6).map(cap => (
          <span key={cap} className="text-[7px] px-1 py-0.5 rounded font-mono"
            style={{ background: 'var(--surface)', color: 'var(--text-muted)', border: '1px solid var(--border)' }}>
            {cap.replace(/_/g, ' ')}
          </span>
        ))}
        {desk.capabilities.length > 6 && (
          <span className="text-[7px] px-1 py-0.5 font-mono" style={{ color: 'var(--text-muted)' }}>
            +{desk.capabilities.length - 6}
          </span>
        )}
      </div>
    </div>
  );
}

/* ── Main Grid Component ──────────────────────────────────────── */
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
      : `${aiDeskStatuses.length} desks · ${totalActive} active · ${totalCompleted} done today`;

  const dotClass = !backendOnline ? 'dot-offline'
    : totalEscalated > 0 ? 'dot-warning'
    : busyCount > 0 ? 'dot-online'
    : 'dot-unknown';

  return (
    <div className="cc-panel" style={{ padding: '8px 10px' }}>
      <button onClick={() => setOpen(!open)} className="w-full flex items-center gap-2">
        <span className={dotClass} />
        <Activity className="w-3 h-3" style={{ color: summaryColor }} />
        <span className="flex-1 text-[11px] font-mono text-left truncate" style={{ color: summaryColor }}>
          {summary}
        </span>
        {totalEscalated > 0 && (
          <span className="text-[8px] px-1.5 rounded font-bold" style={{ background: 'rgba(245,158,11,0.15)', color: '#f59e0b' }}>
            {totalEscalated} ESC
          </span>
        )}
        {open
          ? <ChevronDown className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
          : <ChevronRight className="w-3 h-3 shrink-0" style={{ color: 'var(--text-muted)' }} />
        }
      </button>

      {open && aiDeskStatuses.length > 0 && (
        <div className="mt-2 pt-2" style={{ borderTop: '1px solid var(--border)' }}>
          {/* Desk rows — all 12 desks, compact */}
          <div className="space-y-0.5">
            {aiDeskStatuses.map(desk => {
              const isExpanded = expandedDesk === desk.desk_id;
              const icon = DESK_ICONS[desk.desk_id] || '📋';
              const hasActive = desk.active_tasks > 0;
              const hasEscalated = desk.escalated > 0;
              const statusColor = hasActive ? '#22c55e' : hasEscalated ? '#f59e0b' : 'var(--text-muted)';
              const activeTitle = desk.active_task_details?.[0]?.title;

              return (
                <div key={desk.desk_id}>
                  <button
                    onClick={() => setExpandedDesk(isExpanded ? null : desk.desk_id)}
                    className="w-full flex items-center gap-1.5 px-2 py-1 rounded transition"
                    style={{
                      background: isExpanded ? 'var(--elevated)' : 'transparent',
                      border: isExpanded ? '1px solid var(--gold-border)' : '1px solid transparent',
                    }}
                  >
                    <span className="text-[10px]">{icon}</span>
                    <span className="text-[10px] font-semibold w-[70px] text-left truncate" style={{ color: 'var(--text-primary)' }}>
                      {desk.desk_name.replace(' Desk', '').replace('Desk', '')}
                    </span>
                    <span style={{ width: 5, height: 5, borderRadius: '50%', background: statusColor, flexShrink: 0 }} />

                    {/* Current task preview */}
                    {activeTitle ? (
                      <span className="flex-1 text-[8px] truncate font-mono" style={{ color: '#3b82f6' }}>
                        ▶ {activeTitle}
                      </span>
                    ) : (
                      <span className="flex-1" />
                    )}

                    {/* Activity badges */}
                    <div className="flex gap-1 shrink-0">
                      {desk.completed_today > 0 && (
                        <span className="text-[7px] px-1 rounded font-mono" style={{ background: 'rgba(34,197,94,0.1)', color: '#22c55e' }}>
                          {desk.completed_today}✓
                        </span>
                      )}
                      {hasEscalated && (
                        <span className="text-[7px] px-1 rounded font-mono" style={{ background: 'rgba(245,158,11,0.1)', color: '#f59e0b' }}>
                          {desk.escalated}⚠
                        </span>
                      )}
                    </div>

                    <span className="text-[7px] font-mono w-[32px] text-right" style={{ color: 'var(--text-muted)' }}>
                      {timeAgo(desk.last_activity)}
                    </span>
                  </button>

                  {/* Expanded detail panel */}
                  {isExpanded && <DeskDetail desk={desk} />}
                </div>
              );
            })}
          </div>

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
