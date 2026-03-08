'use client';
import { useState, useEffect, useCallback } from 'react';
import { API } from '../../lib/api';
import { Desk } from '../../lib/types';
import {
  Bot, Send, Loader2, CheckCircle, XCircle, ChevronDown, ChevronUp,
  Hammer, ShoppingBag, Megaphone, Headphones, BadgeDollarSign, PieChart,
  Users, Wrench, Monitor, Globe, Scale, FlaskConical, RefreshCw,
  Clock, AlertTriangle, CircleDot, ListTodo, Eye, X
} from 'lucide-react';

// Unified Lucide icons + colors for every desk
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
  active_task_details?: DeskTask[];
  recent_completed?: DeskTask[];
  escalated_task_details?: DeskTask[];
  completed_today?: number;
  completed_total?: number;
  last_activity?: string;
}

interface Props {
  desks: Desk[];
  onSendTask: (msg: string) => void;
}

export default function DesksScreen({ desks, onSendTask }: Props) {
  const [expandedDesk, setExpandedDesk] = useState<string | null>(null);
  const [taskInput, setTaskInput] = useState('');
  const [taskDesk, setTaskDesk] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [taskResult, setTaskResult] = useState<{ desk: string; result: string; success: boolean } | null>(null);
  const [deskStatuses, setDeskStatuses] = useState<Record<string, DeskStatus>>({});
  const [dbTasks, setDbTasks] = useState<Record<string, DeskTask[]>>({});
  const [viewingTask, setViewingTask] = useState<DeskTask | null>(null);
  const [activeTaskTab, setActiveTaskTab] = useState<Record<string, 'active' | 'completed' | 'db'>>({});
  const [loadingStatus, setLoadingStatus] = useState<Record<string, boolean>>({});

  // Fetch desk status (in-memory tasks) when expanded
  const fetchDeskStatus = useCallback(async (deskId: string) => {
    setLoadingStatus(s => ({ ...s, [deskId]: true }));
    try {
      const [statusRes, tasksRes] = await Promise.allSettled([
        fetch(`${API}/max/ai-desks/${deskId}/detail`),
        fetch(`${API}/tasks?desk=${deskId}&limit=20`),
      ]);
      if (statusRes.status === 'fulfilled' && statusRes.value.ok) {
        const data = await statusRes.value.json();
        setDeskStatuses(s => ({ ...s, [deskId]: data }));
      }
      if (tasksRes.status === 'fulfilled' && tasksRes.value.ok) {
        const data = await tasksRes.value.json();
        setDbTasks(s => ({ ...s, [deskId]: data.tasks || [] }));
      }
    } catch { /* silent */ }
    setLoadingStatus(s => ({ ...s, [deskId]: false }));
  }, []);

  const handleExpand = (deskId: string) => {
    if (expandedDesk === deskId) {
      setExpandedDesk(null);
    } else {
      setExpandedDesk(deskId);
      if (!deskStatuses[deskId]) fetchDeskStatus(deskId);
      if (!activeTaskTab[deskId]) setActiveTaskTab(s => ({ ...s, [deskId]: 'active' }));
    }
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
      // Refresh task list after submission
      fetchDeskStatus(deskId);
    } catch (e: any) {
      setTaskResult({ desk: deskId, result: e.message, success: false });
    }
    setSubmitting(false);
  };

  const quickTask = (deskId: string, task: string) => {
    setTaskDesk(deskId);
    setExpandedDesk(deskId);
    setTaskInput(task);
  };

  return (
    <div className="flex-1 overflow-y-auto p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-10 h-10 rounded-xl bg-[#ede9fe] flex items-center justify-center">
          <Bot size={20} className="text-[#7c3aed]" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-[#1a1a1a]">AI Desks</h1>
          <p className="text-xs text-[#777]">{desks.length} agents ready · Click to assign tasks</p>
        </div>
      </div>

      {/* Task result banner */}
      {taskResult && (
        <div className={`mb-4 p-4 rounded-xl border-2 ${taskResult.success ? 'bg-[#f0fdf4] border-[#bbf7d0]' : 'bg-[#fef2f2] border-[#fecaca]'}`}>
          <div className="flex items-center gap-2 mb-1">
            {taskResult.success ? <CheckCircle size={16} className="text-[#16a34a]" /> : <XCircle size={16} className="text-[#dc2626]" />}
            <span className="text-sm font-bold">{taskResult.success ? 'Task Completed' : 'Task Failed'}</span>
            <button onClick={() => setTaskResult(null)} className="ml-auto text-xs text-[#aaa] hover:text-[#555] cursor-pointer">dismiss</button>
          </div>
          <div className="text-xs text-[#555] whitespace-pre-wrap max-h-[200px] overflow-y-auto">{taskResult.result}</div>
        </div>
      )}

      {/* Desk Grid */}
      <div className="grid grid-cols-2 gap-3">
        {desks.map(d => {
          const cfg = DESK_CONFIG[d.id] || DESK_CONFIG.lab;
          const DeskIcon = cfg.Icon;
          const isExpanded = expandedDesk === d.id;
          const deskData = d as any;
          const status = deskStatuses[d.id];
          const tasks = dbTasks[d.id] || [];
          const tab = activeTaskTab[d.id] || 'active';
          const isLoading = loadingStatus[d.id];

          return (
            <div key={d.id}
              className="rounded-xl border-2 transition-all overflow-hidden"
              style={{ borderColor: isExpanded ? cfg.text : cfg.border, background: 'white' }}>

              {/* Header */}
              <div className="p-4 cursor-pointer flex items-start gap-3"
                style={{ background: cfg.bg }}
                onClick={() => handleExpand(d.id)}>
                <div className="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
                  style={{ background: cfg.text + '18' }}>
                  <DeskIcon size={20} style={{ color: cfg.text }} />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-bold" style={{ color: cfg.text }}>{deskData.agent_name || d.name}</span>
                    <span className="text-[10px] font-mono text-[#999]">{d.id}</span>
                  </div>
                  <div className="text-[11px] text-[#555] mt-0.5 line-clamp-2">{d.persona || (deskData.description || '').slice(0, 80)}</div>
                  <div className="flex items-center gap-2 mt-1.5">
                    <span className="flex items-center gap-1 text-[9px] font-bold">
                      <span className={`w-2 h-2 rounded-full ${d.status === 'busy' ? 'bg-[#d97706]' : 'bg-[#16a34a]'}`} />
                      <span style={{ color: d.status === 'busy' ? '#d97706' : '#16a34a' }}>{(d.status || 'idle').toUpperCase()}</span>
                    </span>
                    {deskData.stats && (
                      <span className="text-[9px] text-[#aaa]">{deskData.stats.completed} done · {deskData.stats.failed} failed</span>
                    )}
                  </div>
                </div>
                {isExpanded ? <ChevronUp size={16} className="text-[#aaa] mt-1" /> : <ChevronDown size={16} className="text-[#aaa] mt-1" />}
              </div>

              {/* Expanded Content */}
              {isExpanded && (
                <div className="border-t" style={{ borderColor: cfg.border }}>
                  {/* Domains */}
                  {deskData.domains && (
                    <div className="flex flex-wrap gap-1 px-4 pt-3">
                      {(deskData.domains as string[]).slice(0, 8).map(dom => (
                        <span key={dom} className="text-[9px] px-2 py-0.5 rounded-full font-mono"
                          style={{ background: cfg.bg, color: cfg.text, border: `1px solid ${cfg.border}` }}>
                          {dom.replace(/_/g, ' ')}
                        </span>
                      ))}
                      {(deskData.domains as string[]).length > 8 && (
                        <span className="text-[9px] text-[#aaa]">+{(deskData.domains as string[]).length - 8} more</span>
                      )}
                    </div>
                  )}

                  {/* Task tabs */}
                  <div className="flex items-center gap-1 px-4 pt-3 pb-2">
                    {([
                      { key: 'active', label: 'Active', icon: CircleDot },
                      { key: 'completed', label: 'Completed', icon: CheckCircle },
                      { key: 'db', label: 'All Tasks', icon: ListTodo },
                    ] as const).map(t => (
                      <button key={t.key} onClick={() => setActiveTaskTab(s => ({ ...s, [d.id]: t.key }))}
                        className={`flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-[10px] font-bold cursor-pointer transition-all border ${
                          tab === t.key
                            ? 'text-white border-transparent'
                            : 'bg-white text-[#777] border-[#ece8e1] hover:bg-[#f5f3ef]'
                        }`}
                        style={tab === t.key ? { background: cfg.text, borderColor: cfg.text } : {}}>
                        <t.icon size={12} />
                        {t.label}
                      </button>
                    ))}
                    <button onClick={() => fetchDeskStatus(d.id)}
                      className="ml-auto p-1.5 rounded-lg text-[#aaa] hover:text-[#555] hover:bg-[#f5f3ef] cursor-pointer transition-all"
                      title="Refresh tasks">
                      <RefreshCw size={12} className={isLoading ? 'animate-spin' : ''} />
                    </button>
                  </div>

                  {/* Task list */}
                  <div className="px-4 pb-3 max-h-[280px] overflow-y-auto">
                    {isLoading && !status && (
                      <div className="text-center py-4">
                        <Loader2 size={16} className="text-[#aaa] mx-auto animate-spin" />
                        <div className="text-[10px] text-[#aaa] mt-1">Loading tasks...</div>
                      </div>
                    )}

                    {tab === 'active' && (
                      <>
                        {(status?.active_task_details || []).length === 0 && !isLoading && (
                          <div className="text-center py-4 text-[10px] text-[#aaa]">No active tasks</div>
                        )}
                        {(status?.active_task_details || []).map(t => (
                          <TaskCard key={t.id} task={t} color={cfg.text} onView={() => setViewingTask(t)} />
                        ))}
                        {(status?.escalated_task_details || []).length > 0 && (
                          <>
                            <div className="text-[9px] font-bold text-[#dc2626] mt-2 mb-1 flex items-center gap-1">
                              <AlertTriangle size={10} /> ESCALATED
                            </div>
                            {(status?.escalated_task_details || []).map(t => (
                              <TaskCard key={t.id} task={t} color="#dc2626" onView={() => setViewingTask(t)} />
                            ))}
                          </>
                        )}
                      </>
                    )}

                    {tab === 'completed' && (
                      <>
                        {(status?.recent_completed || []).length === 0 && !isLoading && (
                          <div className="text-center py-4 text-[10px] text-[#aaa]">No completed tasks yet</div>
                        )}
                        {(status?.recent_completed || []).map(t => (
                          <TaskCard key={t.id} task={t} color={cfg.text} onView={() => setViewingTask(t)} />
                        ))}
                      </>
                    )}

                    {tab === 'db' && (
                      <>
                        {tasks.length === 0 && !isLoading && (
                          <div className="text-center py-4 text-[10px] text-[#aaa]">No tasks in database</div>
                        )}
                        {tasks.map(t => (
                          <TaskCard key={t.id} task={t} color={cfg.text} onView={() => setViewingTask(t)} />
                        ))}
                      </>
                    )}
                  </div>

                  {/* Quick tasks */}
                  <div className="flex flex-wrap gap-1.5 px-4 pb-3">
                    {getQuickTasks(d.id).map((qt, i) => (
                      <button key={i} onClick={() => quickTask(d.id, qt.task)}
                        className="text-[10px] px-2.5 py-1.5 rounded-lg border font-medium cursor-pointer transition-all hover:shadow-sm"
                        style={{ borderColor: cfg.border, color: cfg.text, background: 'white' }}>
                        {qt.label}
                      </button>
                    ))}
                  </div>

                  {/* Task input */}
                  <div className="flex gap-2 px-4 pb-4">
                    <input
                      value={taskDesk === d.id ? taskInput : ''}
                      onChange={e => { setTaskDesk(d.id); setTaskInput(e.target.value); }}
                      onFocus={() => setTaskDesk(d.id)}
                      onKeyDown={e => e.key === 'Enter' && submitTask(d.id)}
                      placeholder={`Assign task to ${deskData.agent_name || d.name}...`}
                      className="flex-1 px-3 py-2.5 border rounded-lg text-xs outline-none min-h-[40px] focus:shadow-[0_0_0_3px] transition-all"
                      style={{ borderColor: cfg.border, background: 'white' }}
                    />
                    <button
                      onClick={() => submitTask(d.id)}
                      disabled={submitting || !(taskDesk === d.id && taskInput.trim())}
                      className="px-4 py-2.5 rounded-lg text-white text-xs font-bold min-h-[40px] flex items-center gap-1.5 disabled:opacity-40 transition-all cursor-pointer"
                      style={{ background: cfg.text }}>
                      {submitting && taskDesk === d.id ? <Loader2 size={14} className="animate-spin" /> : <Send size={14} />}
                      Go
                    </button>
                  </div>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {desks.length === 0 && (
        <div className="text-center py-16">
          <Bot size={48} className="text-[#d8d3cb] mx-auto mb-3" />
          <div className="text-base font-semibold text-[#aaa]">Loading AI Desks...</div>
          <div className="text-xs text-[#ccc] mt-1">Connecting to /api/v1/max/desks</div>
        </div>
      )}

      {/* Task Detail Modal */}
      {viewingTask && (
        <TaskDetailModal task={viewingTask} onClose={() => setViewingTask(null)} />
      )}
    </div>
  );
}

// ── Task Card ────────────────────────────────────────────────────────────

function TaskCard({ task, color, onView }: { task: DeskTask; color: string; onView: () => void }) {
  const state = task.state || task.status || 'pending';
  const stateColors: Record<string, { bg: string; text: string }> = {
    pending:     { bg: '#f5f3ef', text: '#777' },
    todo:        { bg: '#f5f3ef', text: '#777' },
    in_progress: { bg: '#dbeafe', text: '#2563eb' },
    completed:   { bg: '#dcfce7', text: '#16a34a' },
    done:        { bg: '#dcfce7', text: '#16a34a' },
    failed:      { bg: '#fee2e2', text: '#dc2626' },
    escalated:   { bg: '#fef3c7', text: '#d97706' },
    waiting:     { bg: '#ede9fe', text: '#7c3aed' },
  };
  const sc = stateColors[state] || stateColors.pending;
  const priority = task.priority || 'normal';
  const priorityColors: Record<string, string> = {
    urgent: '#dc2626', high: '#d97706', normal: '#777', low: '#aaa',
  };

  return (
    <div className="p-2.5 rounded-lg border border-[#ece8e1] mb-1.5 hover:border-[#b8960c] transition-all bg-white group cursor-pointer"
      onClick={onView}>
      <div className="flex items-start gap-2">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-[11px] font-bold text-[#1a1a1a] truncate">{task.title}</span>
            <span className="text-[8px] font-bold px-1.5 py-0.5 rounded-full shrink-0"
              style={{ background: sc.bg, color: sc.text }}>
              {state.replace('_', ' ').toUpperCase()}
            </span>
          </div>
          {task.description && (
            <div className="text-[10px] text-[#777] mt-0.5 line-clamp-1">{task.description}</div>
          )}
          <div className="flex items-center gap-2 mt-1">
            <span className="text-[8px] font-bold" style={{ color: priorityColors[priority] || '#777' }}>
              {priority.toUpperCase()}
            </span>
            {task.source && <span className="text-[8px] text-[#bbb]">via {task.source}</span>}
            {task.created_at && (
              <span className="text-[8px] font-mono text-[#ccc]" suppressHydrationWarning>
                {formatRelative(task.created_at)}
              </span>
            )}
          </div>
        </div>
        <Eye size={12} className="text-[#ccc] group-hover:text-[#777] mt-1 shrink-0 transition-colors" />
      </div>
    </div>
  );
}

// ── Task Detail Modal ────────────────────────────────────────────────────

function TaskDetailModal({ task, onClose }: { task: DeskTask; onClose: () => void }) {
  const state = task.state || task.status || 'pending';

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-6" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl max-w-lg w-full max-h-[80vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}>
        <div className="p-5 border-b border-[#ece8e1] flex items-start justify-between">
          <div className="flex-1 min-w-0 pr-3">
            <h3 className="text-base font-bold text-[#1a1a1a]">{task.title}</h3>
            <div className="flex items-center gap-2 mt-1">
              <StatusBadge state={state} />
              <PriorityBadge priority={task.priority || 'normal'} />
              {task.desk && <span className="text-[9px] font-mono text-[#999]">{task.desk}</span>}
            </div>
          </div>
          <button onClick={onClose} className="p-1.5 rounded-lg hover:bg-[#f5f3ef] cursor-pointer text-[#aaa] hover:text-[#555] transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {task.description && (
            <div>
              <label className="text-[10px] font-bold text-[#aaa] uppercase tracking-wider">Description</label>
              <p className="text-xs text-[#555] mt-1 leading-relaxed">{task.description}</p>
            </div>
          )}

          {task.result && (
            <div>
              <label className="text-[10px] font-bold text-[#aaa] uppercase tracking-wider">Result</label>
              <div className="text-xs text-[#555] mt-1 p-3 rounded-lg bg-[#f5f3ef] whitespace-pre-wrap max-h-[200px] overflow-y-auto leading-relaxed">
                {task.result}
              </div>
            </div>
          )}

          {task.escalation_reason && (
            <div className="p-3 rounded-lg bg-[#fef3c7] border border-[#fde68a]">
              <div className="text-[10px] font-bold text-[#d97706] mb-1 flex items-center gap-1">
                <AlertTriangle size={10} /> ESCALATION REASON
              </div>
              <div className="text-xs text-[#555]">{task.escalation_reason}</div>
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            {task.source && (
              <InfoField label="Source" value={task.source} />
            )}
            {task.assigned_to && (
              <InfoField label="Assigned To" value={task.assigned_to} />
            )}
            {task.created_at && (
              <InfoField label="Created" value={new Date(task.created_at).toLocaleString()} />
            )}
            {task.completed_at && (
              <InfoField label="Completed" value={new Date(task.completed_at).toLocaleString()} />
            )}
          </div>

          {/* Action log */}
          {task.actions && task.actions.length > 0 && (
            <div>
              <label className="text-[10px] font-bold text-[#aaa] uppercase tracking-wider">Activity Log</label>
              <div className="mt-1 space-y-1">
                {task.actions.map((a, i) => (
                  <div key={i} className="flex items-start gap-2 p-2 rounded-lg bg-[#faf9f7]">
                    <span className={`w-1.5 h-1.5 rounded-full mt-1.5 shrink-0 ${a.success ? 'bg-[#16a34a]' : 'bg-[#dc2626]'}`} />
                    <div className="flex-1 min-w-0">
                      <span className="text-[10px] font-bold text-[#555]">{a.action}</span>
                      <div className="text-[10px] text-[#777] line-clamp-2">{a.detail}</div>
                      <div className="text-[8px] font-mono text-[#ccc] mt-0.5" suppressHydrationWarning>{formatRelative(a.timestamp)}</div>
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
    pending:     { bg: '#f5f3ef', text: '#777' },
    todo:        { bg: '#f5f3ef', text: '#777' },
    in_progress: { bg: '#dbeafe', text: '#2563eb' },
    completed:   { bg: '#dcfce7', text: '#16a34a' },
    done:        { bg: '#dcfce7', text: '#16a34a' },
    failed:      { bg: '#fee2e2', text: '#dc2626' },
    escalated:   { bg: '#fef3c7', text: '#d97706' },
    waiting:     { bg: '#ede9fe', text: '#7c3aed' },
  };
  const c = colors[state] || colors.pending;
  return (
    <span className="text-[9px] font-bold px-2 py-0.5 rounded-full" style={{ background: c.bg, color: c.text }}>
      {state.replace('_', ' ').toUpperCase()}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = { urgent: '#dc2626', high: '#d97706', normal: '#777', low: '#aaa' };
  const c = colors[priority] || '#777';
  return (
    <span className="text-[9px] font-bold px-2 py-0.5 rounded-full" style={{ color: c, background: c + '15' }}>
      {priority.toUpperCase()}
    </span>
  );
}

function InfoField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[9px] font-bold text-[#aaa] uppercase tracking-wider">{label}</div>
      <div className="text-xs text-[#555] mt-0.5" suppressHydrationWarning>{value}</div>
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
