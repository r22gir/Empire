'use client';
import { useState, useEffect, useCallback } from 'react';
import { API } from '../../lib/api';
import { Desk } from '../../lib/types';
import {
  Bot, Send, Loader2, CheckCircle, XCircle, ChevronDown, ChevronUp,
  Hammer, ShoppingBag, Megaphone, Headphones, BadgeDollarSign, PieChart,
  Users, Wrench, Monitor, Globe, Scale, FlaskConical, RefreshCw,
  Clock, AlertTriangle, CircleDot, ListTodo, Eye, X, ArrowLeft,
  FileText, Zap, Brain
} from 'lucide-react';

const DESK_CONFIG: Record<string, { bg: string; border: string; text: string; Icon: React.ComponentType<any> }> = {
  forge:       { bg: '#f0fdf4', border: '#bbf7d0', text: '#16a34a', Icon: Hammer },
  market:      { bg: '#eff6ff', border: '#93c5fd', text: '#2563eb', Icon: ShoppingBag },
  marketing:   { bg: '#fdf2f8', border: '#f9a8d4', text: '#ec4899', Icon: Megaphone },
  support:     { bg: '#faf5ff', border: '#e9d5ff', text: '#7c3aed', Icon: Headphones },
  sales:       { bg: '#fdf8eb', border: '#f5ecd0', text: '#b8960c', Icon: BadgeDollarSign },
  finance:     { bg: '#fffbeb', border: '#fde68a', text: '#d97706', Icon: PieChart },
  clients:     { bg: '#ecfeff', border: '#a5f3fc', text: '#0891b2', Icon: Users },
  contractors: { bg: '#fef3c7', border: '#fcd34d', text: '#b45309', Icon: Wrench },
  it:          { bg: '#f0f9ff', border: '#7dd3fc', text: '#0284c7', Icon: Monitor },
  website:     { bg: '#fdf2f8', border: '#fbcfe8', text: '#db2777', Icon: Globe },
  legal:       { bg: '#f5f3ef', border: '#d8d3cb', text: '#555',    Icon: Scale },
  lab:         { bg: '#fef9c3', border: '#fde047', text: '#a16207', Icon: FlaskConical },
};

interface DeskTask {
  id: string;
  title: string;
  description?: string;
  status?: string;
  state?: string;
  priority?: string;
  source?: string;
  created_at?: string;
  completed_at?: string;
  result?: string;
  escalation_reason?: string;
  desk?: string;
  assigned_to?: string;
  actions?: { action: string; detail: string; timestamp: string; success: boolean }[];
}

interface DeskStatus {
  desk_id: string;
  agent_name?: string;
  description?: string;
  capabilities?: string[];
  active_task_details?: DeskTask[];
  recent_completed?: DeskTask[];
  escalated_task_details?: DeskTask[];
  completed_today?: number;
  completed_total?: number;
  last_activity?: string;
  brain_logs?: { content: string; created_at: string; importance: number }[];
}

interface Props {
  desks: Desk[];
  onSendTask: (msg: string) => void;
}

export default function DesksScreen({ desks, onSendTask }: Props) {
  const [openDesk, setOpenDesk] = useState<string | null>(null);
  const [taskInput, setTaskInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [taskResult, setTaskResult] = useState<{ desk: string; result: string; success: boolean } | null>(null);
  const [deskStatuses, setDeskStatuses] = useState<Record<string, DeskStatus>>({});
  const [dbTasks, setDbTasks] = useState<Record<string, DeskTask[]>>({});
  const [viewingTask, setViewingTask] = useState<DeskTask | null>(null);
  const [activeTab, setActiveTab] = useState<'active' | 'completed' | 'all' | 'brain'>('active');
  const [loadingStatus, setLoadingStatus] = useState<Record<string, boolean>>({});

  const fetchDeskStatus = useCallback(async (deskId: string) => {
    setLoadingStatus(s => ({ ...s, [deskId]: true }));
    try {
      const [statusRes, tasksRes] = await Promise.allSettled([
        fetch(`${API}/max/ai-desks/${deskId}/detail`),
        fetch(`${API}/tasks?desk=${deskId}&limit=50`),
      ]);
      if (statusRes.status === 'fulfilled' && statusRes.value.ok) {
        const statusData = await statusRes.value.json();
        setDeskStatuses(s => ({ ...s, [deskId]: statusData }));
      }
      if (tasksRes.status === 'fulfilled' && tasksRes.value.ok) {
        const tasksData = await tasksRes.value.json();
        setDbTasks(s => ({ ...s, [deskId]: tasksData.tasks || [] }));
      }
    } catch { /* silent */ }
    setLoadingStatus(s => ({ ...s, [deskId]: false }));
  }, []);

  const handleOpenDesk = (deskId: string) => {
    setOpenDesk(deskId);
    setActiveTab('active');
    setTaskResult(null);
    setTaskInput('');
    fetchDeskStatus(deskId);
  };

  const submitTask = async (deskId: string) => {
    if (!taskInput.trim()) return;
    setSubmitting(true);
    setTaskResult(null);
    try {
      const res = await fetch(API + '/max/ai-desks/tasks', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ desk_id: deskId, task: taskInput }),
      });
      const data = await res.json();
      setTaskResult({
        desk: deskId,
        result: data.result || data.output || data.message || JSON.stringify(data),
        success: res.ok,
      });
      setTaskInput('');
      fetchDeskStatus(deskId);
    } catch (e: any) {
      setTaskResult({ desk: deskId, result: e.message, success: false });
    }
    setSubmitting(false);
  };

  // ── Full-page desk detail view ──────────────────────────────────────
  if (openDesk) {
    const desk = desks.find(d => d.id === openDesk);
    if (!desk) { setOpenDesk(null); return null; }
    const cfg = DESK_CONFIG[desk.id] || DESK_CONFIG.lab;
    const DeskIcon = cfg.Icon;
    const deskData = desk as any;
    const status = deskStatuses[desk.id];
    const tasks = dbTasks[desk.id] || [];
    const isLoading = loadingStatus[desk.id];

    const activeTasks = status?.active_task_details || [];
    const completedTasks = status?.recent_completed || [];
    const escalatedTasks = status?.escalated_task_details || [];
    const brainLogs = (status as any)?.brain_logs || [];

    const currentTasks = activeTab === 'active' ? [...activeTasks, ...escalatedTasks]
      : activeTab === 'completed' ? completedTasks
      : activeTab === 'all' ? tasks
      : [];

    return (
      <div className="flex-1 overflow-y-auto" style={{ background: 'var(--bg)' }}>
        {/* Desk header */}
        <div style={{ padding: '32px 36px 24px', background: cfg.bg }}>
          <div className="max-w-5xl mx-auto">
            <button onClick={() => setOpenDesk(null)}
              className="flex items-center gap-1.5 cursor-pointer mb-4 transition-colors"
              style={{ fontSize: 12, fontWeight: 600, color: 'var(--dim)', background: 'none', border: 'none' }}>
              <ArrowLeft size={14} /> Back to All Desks
            </button>
            <div className="flex items-start gap-4">
              <div className="w-14 h-14 rounded-[var(--radius)] flex items-center justify-center shrink-0"
                style={{ background: cfg.text + '18' }}>
                <DeskIcon size={28} style={{ color: cfg.text }} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <h1 style={{ fontSize: 22, fontWeight: 600, color: cfg.text }}>
                    {deskData.agent_name || desk.name}
                  </h1>
                  <span style={{ fontSize: 11, fontFamily: 'monospace', color: 'var(--muted)', background: 'rgba(255,255,255,0.6)', padding: '2px 8px', borderRadius: 6 }}>{desk.id}</span>
                  <span className="flex items-center gap-1.5" style={{ fontSize: 10, fontWeight: 700, marginLeft: 8 }}>
                    <span className="w-2.5 h-2.5 rounded-full" style={{ background: desk.status === 'busy' ? '#d97706' : 'var(--green)' }} />
                    <span style={{ color: desk.status === 'busy' ? '#d97706' : '#16a34a' }}>
                      {(desk.status || 'idle').toUpperCase()}
                    </span>
                  </span>
                </div>
                <p style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4, maxWidth: '42rem' }}>
                  {desk.persona || deskData.description}
                </p>
                {deskData.domains && (
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {(deskData.domains as string[]).slice(0, 12).map(dom => (
                      <span key={dom} style={{
                        fontSize: 10, padding: '4px 10px', borderRadius: 20, fontWeight: 500,
                        background: 'white', color: cfg.text, border: `1px solid ${cfg.border}`,
                      }}>
                        {dom.replace(/_/g, ' ')}
                      </span>
                    ))}
                    {(deskData.domains as string[]).length > 12 && (
                      <span style={{ fontSize: 10, color: 'var(--muted)', alignSelf: 'center' }}>+{(deskData.domains as string[]).length - 12} more</span>
                    )}
                  </div>
                )}
              </div>
              {/* Stats cards */}
              <div className="flex gap-3 shrink-0">
                <MiniStat label="Active" value={String(activeTasks.length)} color={cfg.text} />
                <MiniStat label="Done" value={String(status?.completed_total || deskData.stats?.completed || 0)} color="#16a34a" />
                <MiniStat label="Escalated" value={String(escalatedTasks.length)} color="#d97706" />
              </div>
            </div>
          </div>
        </div>

        {/* Task input bar */}
        <div style={{ padding: '20px 36px', borderBottom: '1px solid var(--border)', background: 'var(--panel)' }}>
          <div className="max-w-5xl mx-auto">
            <div className="empire-card flat" style={{ display: 'flex', gap: 12, padding: '12px 16px', alignItems: 'center' }}>
              <input
                value={taskInput}
                onChange={e => setTaskInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && submitTask(desk.id)}
                placeholder={`Assign a task to ${deskData.agent_name || desk.name}...`}
                style={{
                  flex: 1, padding: '10px 14px', border: `1px solid var(--border)`, borderRadius: 'var(--radius-sm)',
                  fontSize: 13, outline: 'none', background: 'white',
                }}
              />
              <button
                onClick={() => submitTask(desk.id)}
                disabled={submitting || !taskInput.trim()}
                className="flex items-center gap-2 transition-all"
                style={{
                  padding: '10px 20px', borderRadius: 'var(--radius-sm)', background: cfg.text, color: 'white',
                  fontSize: 13, fontWeight: 600, border: 'none', cursor: 'pointer', opacity: submitting || !taskInput.trim() ? 0.4 : 1,
                }}>
                {submitting ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                Send
              </button>
            </div>
            {/* Quick tasks */}
            <div className="flex flex-wrap gap-2 mt-3">
              {getQuickTasks(desk.id).map((qt, i) => (
                <button key={i} onClick={() => setTaskInput(qt.task)}
                  className="filter-tab"
                  style={{ fontSize: 11, padding: '5px 12px', borderColor: cfg.border, color: cfg.text, background: cfg.bg }}>
                  {qt.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Task result banner */}
        {taskResult && (
          <div style={{ padding: '16px 36px 0' }}>
            <div className="max-w-5xl mx-auto empire-card flat" style={{
              background: taskResult.success ? 'var(--green-bg)' : 'var(--red-bg)',
              borderColor: taskResult.success ? '#bbf7d0' : '#fecaca',
            }}>
              <div className="flex items-center gap-2 mb-2">
                {taskResult.success ? <CheckCircle size={16} style={{ color: 'var(--green)' }} /> : <XCircle size={16} style={{ color: 'var(--red)' }} />}
                <span style={{ fontSize: 13, fontWeight: 600 }}>{taskResult.success ? 'Task Completed' : 'Task Failed'}</span>
                <button onClick={() => setTaskResult(null)} style={{ marginLeft: 'auto', fontSize: 12, color: 'var(--muted)', background: 'none', border: 'none', cursor: 'pointer' }}>dismiss</button>
              </div>
              <div style={{ fontSize: 12, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', maxHeight: 300, overflowY: 'auto', lineHeight: 1.6 }}>{taskResult.result}</div>
            </div>
          </div>
        )}

        {/* Tabs + content */}
        <div style={{ padding: '24px 36px 32px' }}>
          <div className="max-w-5xl mx-auto">
            <div className="flex items-center gap-2 mb-5" style={{ borderBottom: '1px solid var(--border)', paddingBottom: 12 }}>
              {([
                { key: 'active' as const, label: 'Active Tasks', icon: CircleDot, count: activeTasks.length + escalatedTasks.length },
                { key: 'completed' as const, label: 'Completed', icon: CheckCircle, count: completedTasks.length },
                { key: 'all' as const, label: 'All Tasks (DB)', icon: ListTodo, count: tasks.length },
                { key: 'brain' as const, label: 'Brain Logs', icon: Brain, count: brainLogs.length },
              ]).map(t => (
                <button key={t.key} onClick={() => setActiveTab(t.key)}
                  className={`filter-tab ${activeTab === t.key ? 'active' : ''}`}
                  style={{
                    display: 'flex', alignItems: 'center', gap: 8,
                    ...(activeTab === t.key ? { background: cfg.text, borderColor: cfg.text } : {}),
                  }}>
                  <t.icon size={14} />
                  {t.label}
                  <span style={{
                    fontSize: 10, padding: '2px 8px', borderRadius: 20, fontWeight: 600,
                    ...(activeTab === t.key
                      ? { background: 'rgba(255,255,255,0.25)', color: 'white' }
                      : { background: 'var(--hover)', color: 'var(--muted)' }),
                  }}>
                    {t.count}
                  </span>
                </button>
              ))}
              <button onClick={() => fetchDeskStatus(desk.id)}
                style={{ marginLeft: 'auto', padding: 8, borderRadius: 'var(--radius-sm)', color: 'var(--muted)', background: 'none', border: 'none', cursor: 'pointer' }}
                className="hover:bg-[var(--hover)] transition-all"
                title="Refresh">
                <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
              </button>
            </div>

            {isLoading && !status && (
              <div className="text-center py-16">
                <Loader2 size={24} style={{ color: 'var(--muted)' }} className="mx-auto animate-spin" />
                <div style={{ fontSize: 14, color: 'var(--muted)', marginTop: 8 }}>Loading desk data...</div>
              </div>
            )}

            {/* Brain logs tab */}
            {activeTab === 'brain' && (
              <div className="space-y-2">
                {brainLogs.length === 0 && !isLoading && (
                  <div className="text-center py-16" style={{ fontSize: 14, color: 'var(--muted)' }}>No brain activity logged yet</div>
                )}
                {brainLogs.map((log: any, i: number) => (
                  <div key={i} className="empire-card flat">
                    <div className="flex items-start gap-3">
                      <Brain size={16} style={{ color: 'var(--purple)' }} className="mt-0.5 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div style={{ fontSize: 12, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{log.content}</div>
                        <div className="flex items-center gap-3 mt-2">
                          <span style={{ fontSize: 9, fontFamily: 'monospace', color: 'var(--faint)' }} suppressHydrationWarning>{formatRelative(log.created_at)}</span>
                          <span style={{ fontSize: 9, fontWeight: 700, color: log.importance >= 7 ? '#d97706' : 'var(--muted)' }}>
                            importance: {log.importance}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Task list */}
            {activeTab !== 'brain' && (
              <div className="space-y-2">
                {currentTasks.length === 0 && !isLoading && (
                  <div className="text-center py-16" style={{ fontSize: 14, color: 'var(--muted)' }}>
                    {activeTab === 'active' ? 'No active tasks' : activeTab === 'completed' ? 'No completed tasks yet' : 'No tasks in database'}
                  </div>
                )}

                {/* Escalated section */}
                {activeTab === 'active' && escalatedTasks.length > 0 && (
                  <div className="empire-card flat" style={{ background: 'var(--orange-bg)', borderColor: '#fde68a', marginBottom: 12 }}>
                    <div className="flex items-center gap-1" style={{ fontSize: 10, fontWeight: 700, color: '#d97706' }}>
                      <AlertTriangle size={12} /> {escalatedTasks.length} ESCALATED — needs your attention
                    </div>
                  </div>
                )}

                {currentTasks.map(t => (
                  <TaskRow key={t.id} task={t} color={cfg.text} onView={() => setViewingTask(t)} />
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Task Detail Modal */}
        {viewingTask && (
          <TaskDetailModal task={viewingTask} onClose={() => setViewingTask(null)} />
        )}
      </div>
    );
  }

  // ── Grid overview ───────────────────────────────────────────────────
  return (
    <div className="flex-1 overflow-y-auto" style={{ background: 'var(--bg)' }}>
      <div className="max-w-5xl mx-auto" style={{ padding: '28px 36px' }}>
        <div className="flex items-center gap-3 mb-2">
          <div className="w-10 h-10 rounded-[var(--radius)] flex items-center justify-center" style={{ background: 'var(--purple-bg)' }}>
            <Bot size={20} style={{ color: 'var(--purple)' }} />
          </div>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: 'var(--text)' }}>AI Desks</h1>
            <p style={{ fontSize: 13, color: 'var(--dim)' }}>{desks.length} agents ready · Click to open</p>
          </div>
        </div>

        <div className="section-label" style={{ marginBottom: 12, marginTop: 20 }}>All Desks</div>

        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          {desks.map(d => {
            const cfg = DESK_CONFIG[d.id] || DESK_CONFIG.lab;
            const DeskIcon = cfg.Icon;
            const deskData = d as any;
            return (
              <div key={d.id}
                onClick={() => handleOpenDesk(d.id)}
                className="empire-card group"
                style={{ padding: '18px 20px' }}>
                <div className="flex items-start gap-3">
                  <div className="w-11 h-11 rounded-[var(--radius-sm)] flex items-center justify-center shrink-0 transition-colors"
                    style={{ background: cfg.bg }}>
                    <DeskIcon size={22} style={{ color: cfg.text }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }} className="group-hover:underline">{deskData.agent_name || d.name}</span>
                    </div>
                    <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--faint)' }}>{d.id}</span>
                  </div>
                  <span className="flex items-center gap-1 shrink-0 mt-1" style={{ fontSize: 9, fontWeight: 700 }}>
                    <span className="w-2 h-2 rounded-full" style={{ background: d.status === 'busy' ? '#d97706' : 'var(--green)' }} />
                    <span style={{ color: d.status === 'busy' ? '#d97706' : '#16a34a' }}>{(d.status || 'idle').toUpperCase()}</span>
                  </span>
                </div>
                <p style={{ fontSize: 11, color: 'var(--dim)', marginTop: 8, lineHeight: 1.5 }} className="line-clamp-2">
                  {d.persona || (deskData.description || '').slice(0, 100)}
                </p>
                {deskData.stats && (
                  <div className="flex items-center gap-3 mt-3 pt-3" style={{ borderTop: '1px solid var(--border)' }}>
                    <span style={{ fontSize: 10, color: '#16a34a', fontWeight: 600 }}>{deskData.stats.completed} done</span>
                    {deskData.stats.failed > 0 && (
                      <span style={{ fontSize: 10, color: 'var(--red)', fontWeight: 600 }}>{deskData.stats.failed} failed</span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {desks.length === 0 && (
          <div className="text-center py-20">
            <Bot size={48} style={{ color: 'var(--faint)' }} className="mx-auto mb-3" />
            <div style={{ fontSize: 15, fontWeight: 600, color: 'var(--muted)' }}>Loading AI Desks...</div>
            <div style={{ fontSize: 12, color: 'var(--faint)', marginTop: 4 }}>Connecting to /api/v1/max/desks</div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Mini stat card ──────────────────────────────────────────────────────

function MiniStat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="empire-card flat" style={{ padding: '10px 16px', textAlign: 'center', minWidth: 72 }}>
      <div style={{ fontSize: 20, fontWeight: 700, fontFamily: 'monospace', color }}>{value}</div>
      <div className="section-label" style={{ letterSpacing: 1 }}>{label}</div>
    </div>
  );
}

// ── Task row (full-width) ───────────────────────────────────────────────

function TaskRow({ task, color, onView }: { task: DeskTask; color: string; onView: () => void }) {
  const state = task.state || task.status || 'pending';
  const priority = task.priority || 'normal';
  return (
    <div className="empire-card group" onClick={onView} style={{ padding: '14px 18px' }}>
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span style={{ fontSize: 14, fontWeight: 600, color: 'var(--text)' }}>{task.title}</span>
            <StatusBadge state={state} />
            <PriorityBadge priority={priority} />
          </div>
          {task.description && (
            <p style={{ fontSize: 12, color: 'var(--dim)', marginTop: 6, lineHeight: 1.6 }} className="line-clamp-2">{task.description}</p>
          )}
          <div className="flex items-center gap-4 mt-2">
            {task.source && <span style={{ fontSize: 10, color: 'var(--faint)' }}>via {task.source}</span>}
            {task.assigned_to && <span style={{ fontSize: 10, color: 'var(--faint)' }}>assigned to {task.assigned_to}</span>}
            {task.created_at && (
              <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--faint)' }} suppressHydrationWarning>{formatRelative(task.created_at)}</span>
            )}
          </div>
        </div>
        <Eye size={16} className="mt-1 shrink-0 transition-colors" style={{ color: 'var(--border)' }} />
      </div>
    </div>
  );
}

// ── Task Detail Modal ──────────────────────────────────────────────────

function TaskDetailModal({ task, onClose }: { task: DeskTask; onClose: () => void }) {
  const state = task.state || task.status || 'pending';
  return (
    <div className="fixed inset-0 flex items-center justify-center z-50 p-8" style={{ background: 'rgba(0,0,0,0.4)' }} onClick={onClose}>
      <div style={{ background: 'var(--panel)', borderRadius: 'var(--radius-lg)', maxWidth: '42rem', width: '100%', maxHeight: '85vh', overflowY: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,0.15)' }}
        onClick={e => e.stopPropagation()}>
        <div className="flex items-start justify-between" style={{ padding: '24px 24px 20px', borderBottom: '1px solid var(--border)' }}>
          <div className="flex-1 min-w-0 pr-4">
            <h3 style={{ fontSize: 18, fontWeight: 600, color: 'var(--text)' }}>{task.title}</h3>
            <div className="flex items-center gap-2 mt-2">
              <StatusBadge state={state} />
              <PriorityBadge priority={task.priority || 'normal'} />
              {task.desk && <span style={{ fontSize: 10, fontFamily: 'monospace', color: 'var(--muted)' }}>{task.desk}</span>}
            </div>
          </div>
          <button onClick={onClose} style={{ padding: 8, borderRadius: 'var(--radius-sm)', color: 'var(--muted)', background: 'none', border: 'none', cursor: 'pointer' }}
            className="hover:bg-[var(--hover)] transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="space-y-5" style={{ padding: 24 }}>
          {task.description && (
            <div>
              <label className="section-label" style={{ display: 'block', marginBottom: 6 }}>Description</label>
              <p style={{ fontSize: 13, color: 'var(--text-secondary)', lineHeight: 1.6 }}>{task.description}</p>
            </div>
          )}

          {task.result && (
            <div>
              <label className="section-label" style={{ display: 'block', marginBottom: 6 }}>Result</label>
              <div className="empire-card flat" style={{ fontSize: 13, color: 'var(--text-secondary)', whiteSpace: 'pre-wrap', maxHeight: 300, overflowY: 'auto', lineHeight: 1.6, cursor: 'default' }}>
                {task.result}
              </div>
            </div>
          )}

          {task.escalation_reason && (
            <div className="empire-card flat" style={{ background: 'var(--orange-bg)', borderColor: '#fde68a' }}>
              <div className="section-label flex items-center gap-1.5" style={{ color: '#d97706', marginBottom: 6 }}>
                <AlertTriangle size={12} /> Escalation Reason
              </div>
              <div style={{ fontSize: 13, color: 'var(--text-secondary)' }}>{task.escalation_reason}</div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-4">
            {task.source && <InfoField label="Source" value={task.source} />}
            {task.assigned_to && <InfoField label="Assigned To" value={task.assigned_to} />}
            {task.created_at && <InfoField label="Created" value={new Date(task.created_at).toLocaleString()} />}
            {task.completed_at && <InfoField label="Completed" value={new Date(task.completed_at).toLocaleString()} />}
          </div>

          {task.actions && task.actions.length > 0 && (
            <div>
              <label className="section-label" style={{ display: 'block', marginBottom: 8 }}>Activity Log</label>
              <div className="space-y-1.5">
                {task.actions.map((a, i) => (
                  <div key={i} className="empire-card flat" style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                    <span className="w-2 h-2 rounded-full mt-1.5 shrink-0" style={{ background: a.success ? 'var(--green)' : 'var(--red)' }} />
                    <div className="flex-1 min-w-0">
                      <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-secondary)' }}>{a.action}</span>
                      <div style={{ fontSize: 12, color: 'var(--dim)', marginTop: 2 }}>{a.detail}</div>
                      <div style={{ fontSize: 9, fontFamily: 'monospace', color: 'var(--faint)', marginTop: 4 }} suppressHydrationWarning>{formatRelative(a.timestamp)}</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function StatusBadge({ state }: { state: string }) {
  const colors: Record<string, { bg: string; text: string }> = {
    pending: { bg: '#f5f3ef', text: '#777' }, todo: { bg: '#f5f3ef', text: '#777' },
    in_progress: { bg: 'var(--blue-bg)', text: 'var(--blue)' }, completed: { bg: 'var(--green-bg)', text: '#16a34a' },
    done: { bg: 'var(--green-bg)', text: '#16a34a' }, failed: { bg: 'var(--red-bg)', text: 'var(--red)' },
    escalated: { bg: 'var(--orange-bg)', text: '#d97706' }, waiting: { bg: 'var(--purple-bg)', text: 'var(--purple)' },
  };
  const c = colors[state] || colors.pending;
  return (
    <span className="status-pill" style={{ background: c.bg, color: c.text, fontSize: 9, padding: '3px 10px', borderRadius: 20 }}>
      {state.replace('_', ' ').toUpperCase()}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = { urgent: '#dc2626', high: '#d97706', normal: '#777', low: '#aaa' };
  const c = colors[priority] || '#777';
  return (
    <span className="status-pill" style={{ color: c, background: c + '15', fontSize: 9, padding: '3px 10px', borderRadius: 20 }}>
      {priority.toUpperCase()}
    </span>
  );
}

function InfoField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="section-label">{label}</div>
      <div style={{ fontSize: 13, color: 'var(--text-secondary)', marginTop: 4 }} suppressHydrationWarning>{value}</div>
    </div>
  );
}

function formatRelative(ts: string): string {
  try {
    const d = new Date(ts);
    const now = new Date();
    const diff = now.getTime() - d.getTime();
    if (diff < 60000) return 'just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  } catch { return ts; }
}

function getQuickTasks(deskId: string): { label: string; task: string }[] {
  const tasks: Record<string, { label: string; task: string }[]> = {
    forge: [
      { label: 'List open quotes', task: 'List all open quotes with customer names and totals' },
      { label: 'Production status', task: 'Give me the current production status for all active jobs' },
      { label: 'Fabric lookup', task: 'Look up available fabrics for drapery' },
    ],
    market: [
      { label: 'Active listings', task: 'Show all active marketplace listings' },
      { label: 'Pricing check', task: 'Run a competitor pricing analysis' },
      { label: 'Pending orders', task: 'List all pending orders needing fulfillment' },
    ],
    marketing: [
      { label: 'Draft IG post', task: 'Draft an Instagram post for our latest project' },
      { label: 'Schedule content', task: 'Show content calendar for this week' },
      { label: 'Hashtag strategy', task: 'Suggest hashtags for home decor content' },
    ],
    support: [
      { label: 'Open tickets', task: 'List all open support tickets' },
      { label: 'Draft response', task: 'Draft a response for the most recent support ticket' },
      { label: 'Satisfaction', task: 'Show customer satisfaction summary' },
    ],
    sales: [
      { label: 'Hot leads', task: 'Show all hot leads that need follow-up' },
      { label: 'Follow-up', task: 'Draft follow-up emails for pending proposals' },
      { label: 'Pipeline', task: 'Give me the current sales pipeline summary' },
    ],
    finance: [
      { label: 'P&L summary', task: 'Generate a profit and loss summary for this month' },
      { label: 'Overdue invoices', task: 'List all overdue invoices' },
      { label: 'Revenue report', task: 'Generate a revenue report for this quarter' },
    ],
    clients: [
      { label: 'Recent clients', task: 'Show recent client interactions' },
      { label: 'Thank you note', task: 'Draft a thank you note for our latest completed project' },
      { label: 'Client lookup', task: 'Search for client information' },
    ],
    contractors: [
      { label: 'Availability', task: 'Check installer availability for next week' },
      { label: 'Top rated', task: 'Show top rated contractors by reliability score' },
      { label: 'Pay rates', task: 'List contractor pay rates by specialty' },
    ],
    it: [
      { label: 'Service health', task: 'Run a health check on all Empire services' },
      { label: 'Resource usage', task: 'Show current CPU, RAM, and disk usage' },
      { label: 'Recent logs', task: 'Show recent error logs' },
    ],
    website: [
      { label: 'SEO check', task: 'Run an SEO check on the website' },
      { label: 'Update portfolio', task: 'Suggest new portfolio entries from recent projects' },
      { label: 'Review response', task: 'Draft responses to recent Google reviews' },
    ],
    legal: [
      { label: 'Draft contract', task: 'Draft a standard client contract' },
      { label: 'Expiring docs', task: 'List documents expiring in the next 30 days' },
      { label: 'Compliance', task: 'Run a compliance check' },
    ],
    lab: [
      { label: 'Test vision', task: 'Run a test of the AI vision pipeline' },
      { label: 'Test TTS', task: 'Test text-to-speech with a sample' },
      { label: 'Suggest automation', task: 'Brainstorm new automation opportunities for the business' },
    ],
  };
  return tasks[deskId] || [{ label: 'Status', task: 'Give me your current status and what you can help with' }];
}
