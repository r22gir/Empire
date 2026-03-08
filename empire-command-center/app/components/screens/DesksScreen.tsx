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
      <div className="flex-1 overflow-y-auto">
        {/* Desk header */}
        <div className="px-10 pt-8 pb-6" style={{ background: cfg.bg }}>
          <div className="max-w-5xl mx-auto">
            <button onClick={() => setOpenDesk(null)}
              className="flex items-center gap-1.5 text-xs font-semibold text-[#777] hover:text-[#1a1a1a] cursor-pointer mb-4 transition-colors">
              <ArrowLeft size={14} /> Back to All Desks
            </button>
            <div className="flex items-start gap-4">
              <div className="w-14 h-14 rounded-2xl flex items-center justify-center shrink-0"
                style={{ background: cfg.text + '18' }}>
                <DeskIcon size={28} style={{ color: cfg.text }} />
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-3">
                  <h1 className="text-2xl font-bold" style={{ color: cfg.text }}>
                    {deskData.agent_name || desk.name}
                  </h1>
                  <span className="text-xs font-mono text-[#999] bg-white/60 px-2 py-0.5 rounded">{desk.id}</span>
                  <span className="flex items-center gap-1.5 text-[10px] font-bold ml-2">
                    <span className={`w-2.5 h-2.5 rounded-full ${desk.status === 'busy' ? 'bg-[#d97706]' : 'bg-[#16a34a]'}`} />
                    <span style={{ color: desk.status === 'busy' ? '#d97706' : '#16a34a' }}>
                      {(desk.status || 'idle').toUpperCase()}
                    </span>
                  </span>
                </div>
                <p className="text-sm text-[#555] mt-1 max-w-2xl">
                  {desk.persona || deskData.description}
                </p>
                {deskData.domains && (
                  <div className="flex flex-wrap gap-1.5 mt-3">
                    {(deskData.domains as string[]).slice(0, 12).map(dom => (
                      <span key={dom} className="text-[10px] px-2.5 py-1 rounded-full font-medium"
                        style={{ background: 'white', color: cfg.text, border: `1px solid ${cfg.border}` }}>
                        {dom.replace(/_/g, ' ')}
                      </span>
                    ))}
                    {(deskData.domains as string[]).length > 12 && (
                      <span className="text-[10px] text-[#999] self-center">+{(deskData.domains as string[]).length - 12} more</span>
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
        <div className="px-10 py-5 border-b border-[#ece8e1] bg-white">
          <div className="max-w-5xl mx-auto">
            <div className="flex gap-3">
              <input
                value={taskInput}
                onChange={e => setTaskInput(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && submitTask(desk.id)}
                placeholder={`Assign a task to ${deskData.agent_name || desk.name}...`}
                className="flex-1 px-4 py-3 border-2 rounded-xl text-sm outline-none transition-all focus:shadow-[0_0_0_3px]"
                style={{ borderColor: cfg.border }}
              />
              <button
                onClick={() => submitTask(desk.id)}
                disabled={submitting || !taskInput.trim()}
                className="px-6 py-3 rounded-xl text-white text-sm font-bold flex items-center gap-2 disabled:opacity-40 transition-all cursor-pointer hover:opacity-90"
                style={{ background: cfg.text }}>
                {submitting ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
                Send
              </button>
            </div>
            {/* Quick tasks */}
            <div className="flex flex-wrap gap-2 mt-3">
              {getQuickTasks(desk.id).map((qt, i) => (
                <button key={i} onClick={() => setTaskInput(qt.task)}
                  className="text-[11px] px-3 py-1.5 rounded-lg border font-medium cursor-pointer transition-all hover:shadow-sm"
                  style={{ borderColor: cfg.border, color: cfg.text, background: cfg.bg }}>
                  {qt.label}
                </button>
              ))}
            </div>
          </div>
        </div>

        {/* Task result banner */}
        {taskResult && (
          <div className="px-10 pt-4">
            <div className={`max-w-5xl mx-auto p-4 rounded-xl border-2 ${taskResult.success ? 'bg-[#f0fdf4] border-[#bbf7d0]' : 'bg-[#fef2f2] border-[#fecaca]'}`}>
              <div className="flex items-center gap-2 mb-2">
                {taskResult.success ? <CheckCircle size={16} className="text-[#16a34a]" /> : <XCircle size={16} className="text-[#dc2626]" />}
                <span className="text-sm font-bold">{taskResult.success ? 'Task Completed' : 'Task Failed'}</span>
                <button onClick={() => setTaskResult(null)} className="ml-auto text-xs text-[#aaa] hover:text-[#555] cursor-pointer">dismiss</button>
              </div>
              <div className="text-xs text-[#555] whitespace-pre-wrap max-h-[300px] overflow-y-auto leading-relaxed">{taskResult.result}</div>
            </div>
          </div>
        )}

        {/* Tabs + content */}
        <div className="px-10 pt-6 pb-8">
          <div className="max-w-5xl mx-auto">
            <div className="flex items-center gap-2 mb-5 border-b border-[#ece8e1] pb-3">
              {([
                { key: 'active' as const, label: 'Active Tasks', icon: CircleDot, count: activeTasks.length + escalatedTasks.length },
                { key: 'completed' as const, label: 'Completed', icon: CheckCircle, count: completedTasks.length },
                { key: 'all' as const, label: 'All Tasks (DB)', icon: ListTodo, count: tasks.length },
                { key: 'brain' as const, label: 'Brain Logs', icon: Brain, count: brainLogs.length },
              ]).map(t => (
                <button key={t.key} onClick={() => setActiveTab(t.key)}
                  className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-bold cursor-pointer transition-all border ${
                    activeTab === t.key
                      ? 'text-white border-transparent shadow-sm'
                      : 'bg-white text-[#777] border-[#ece8e1] hover:bg-[#f5f3ef] hover:text-[#555]'
                  }`}
                  style={activeTab === t.key ? { background: cfg.text, borderColor: cfg.text } : {}}>
                  <t.icon size={14} />
                  {t.label}
                  <span className={`text-[10px] px-1.5 py-0.5 rounded-full font-bold ${
                    activeTab === t.key ? 'bg-white/25 text-white' : 'bg-[#f5f3ef] text-[#999]'
                  }`}>
                    {t.count}
                  </span>
                </button>
              ))}
              <button onClick={() => fetchDeskStatus(desk.id)}
                className="ml-auto p-2 rounded-lg text-[#aaa] hover:text-[#555] hover:bg-[#f5f3ef] cursor-pointer transition-all"
                title="Refresh">
                <RefreshCw size={14} className={isLoading ? 'animate-spin' : ''} />
              </button>
            </div>

            {isLoading && !status && (
              <div className="text-center py-16">
                <Loader2 size={24} className="text-[#aaa] mx-auto animate-spin" />
                <div className="text-sm text-[#aaa] mt-2">Loading desk data...</div>
              </div>
            )}

            {/* Brain logs tab */}
            {activeTab === 'brain' && (
              <div className="space-y-2">
                {brainLogs.length === 0 && !isLoading && (
                  <div className="text-center py-16 text-sm text-[#aaa]">No brain activity logged yet</div>
                )}
                {brainLogs.map((log: any, i: number) => (
                  <div key={i} className="p-4 rounded-xl border border-[#ece8e1] bg-white">
                    <div className="flex items-start gap-3">
                      <Brain size={16} className="text-[#7c3aed] mt-0.5 shrink-0" />
                      <div className="flex-1 min-w-0">
                        <div className="text-xs text-[#555] leading-relaxed">{log.content}</div>
                        <div className="flex items-center gap-3 mt-2">
                          <span className="text-[9px] font-mono text-[#ccc]" suppressHydrationWarning>{formatRelative(log.created_at)}</span>
                          <span className="text-[9px] font-bold" style={{ color: log.importance >= 7 ? '#d97706' : '#aaa' }}>
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
                  <div className="text-center py-16 text-sm text-[#aaa]">
                    {activeTab === 'active' ? 'No active tasks' : activeTab === 'completed' ? 'No completed tasks yet' : 'No tasks in database'}
                  </div>
                )}

                {/* Escalated section */}
                {activeTab === 'active' && escalatedTasks.length > 0 && (
                  <div className="mb-3 p-3 rounded-xl bg-[#fef3c7] border border-[#fde68a]">
                    <div className="text-[10px] font-bold text-[#d97706] flex items-center gap-1 mb-1">
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
    <div className="flex-1 overflow-y-auto">
      <div className="max-w-5xl mx-auto px-10 py-8">
        <div className="flex items-center gap-3 mb-6">
          <div className="w-10 h-10 rounded-xl bg-[#ede9fe] flex items-center justify-center">
            <Bot size={20} className="text-[#7c3aed]" />
          </div>
          <div>
            <h1 className="text-xl font-bold text-[#1a1a1a]">AI Desks</h1>
            <p className="text-xs text-[#777]">{desks.length} agents ready · Click to open</p>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-3 gap-4">
          {desks.map(d => {
            const cfg = DESK_CONFIG[d.id] || DESK_CONFIG.lab;
            const DeskIcon = cfg.Icon;
            const deskData = d as any;
            return (
              <div key={d.id}
                onClick={() => handleOpenDesk(d.id)}
                className="rounded-xl border-2 p-5 cursor-pointer transition-all hover:shadow-lg hover:scale-[1.01] group"
                style={{ borderColor: cfg.border, background: 'white' }}>
                <div className="flex items-start gap-3">
                  <div className="w-11 h-11 rounded-xl flex items-center justify-center shrink-0 transition-colors"
                    style={{ background: cfg.bg }}>
                    <DeskIcon size={22} style={{ color: cfg.text }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="text-sm font-bold text-[#1a1a1a] group-hover:underline">{deskData.agent_name || d.name}</span>
                    </div>
                    <span className="text-[10px] font-mono text-[#bbb]">{d.id}</span>
                  </div>
                  <span className="flex items-center gap-1 text-[9px] font-bold shrink-0 mt-1">
                    <span className={`w-2 h-2 rounded-full ${d.status === 'busy' ? 'bg-[#d97706]' : 'bg-[#16a34a]'}`} />
                    <span style={{ color: d.status === 'busy' ? '#d97706' : '#16a34a' }}>{(d.status || 'idle').toUpperCase()}</span>
                  </span>
                </div>
                <p className="text-[11px] text-[#777] mt-2 line-clamp-2 leading-relaxed">
                  {d.persona || (deskData.description || '').slice(0, 100)}
                </p>
                {deskData.stats && (
                  <div className="flex items-center gap-3 mt-3 pt-3 border-t border-[#f0ede8]">
                    <span className="text-[10px] text-[#16a34a] font-bold">{deskData.stats.completed} done</span>
                    {deskData.stats.failed > 0 && (
                      <span className="text-[10px] text-[#dc2626] font-bold">{deskData.stats.failed} failed</span>
                    )}
                  </div>
                )}
              </div>
            );
          })}
        </div>

        {desks.length === 0 && (
          <div className="text-center py-20">
            <Bot size={48} className="text-[#d8d3cb] mx-auto mb-3" />
            <div className="text-base font-semibold text-[#aaa]">Loading AI Desks...</div>
            <div className="text-xs text-[#ccc] mt-1">Connecting to /api/v1/max/desks</div>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Mini stat card ──────────────────────────────────────────────────────

function MiniStat({ label, value, color }: { label: string; value: string; color: string }) {
  return (
    <div className="bg-white rounded-xl border border-[#ece8e1] px-4 py-2.5 text-center min-w-[72px]">
      <div className="text-lg font-bold font-mono" style={{ color }}>{value}</div>
      <div className="text-[9px] font-semibold text-[#999] uppercase tracking-wider">{label}</div>
    </div>
  );
}

// ── Task row (full-width) ───────────────────────────────────────────────

function TaskRow({ task, color, onView }: { task: DeskTask; color: string; onView: () => void }) {
  const state = task.state || task.status || 'pending';
  const priority = task.priority || 'normal';
  return (
    <div className="p-4 rounded-xl border border-[#ece8e1] bg-white hover:border-[#b8960c] transition-all cursor-pointer group"
      onClick={onView}>
      <div className="flex items-start gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="text-sm font-bold text-[#1a1a1a]">{task.title}</span>
            <StatusBadge state={state} />
            <PriorityBadge priority={priority} />
          </div>
          {task.description && (
            <p className="text-xs text-[#777] mt-1.5 line-clamp-2 leading-relaxed">{task.description}</p>
          )}
          <div className="flex items-center gap-4 mt-2">
            {task.source && <span className="text-[10px] text-[#bbb]">via {task.source}</span>}
            {task.assigned_to && <span className="text-[10px] text-[#bbb]">assigned to {task.assigned_to}</span>}
            {task.created_at && (
              <span className="text-[10px] font-mono text-[#ccc]" suppressHydrationWarning>{formatRelative(task.created_at)}</span>
            )}
          </div>
        </div>
        <Eye size={16} className="text-[#ddd] group-hover:text-[#777] mt-1 shrink-0 transition-colors" />
      </div>
    </div>
  );
}

// ── Task Detail Modal ──────────────────────────────────────────────────

function TaskDetailModal({ task, onClose }: { task: DeskTask; onClose: () => void }) {
  const state = task.state || task.status || 'pending';
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-8" onClick={onClose}>
      <div className="bg-white rounded-2xl shadow-2xl max-w-2xl w-full max-h-[85vh] overflow-y-auto"
        onClick={e => e.stopPropagation()}>
        <div className="p-6 border-b border-[#ece8e1] flex items-start justify-between">
          <div className="flex-1 min-w-0 pr-4">
            <h3 className="text-lg font-bold text-[#1a1a1a]">{task.title}</h3>
            <div className="flex items-center gap-2 mt-2">
              <StatusBadge state={state} />
              <PriorityBadge priority={task.priority || 'normal'} />
              {task.desk && <span className="text-[10px] font-mono text-[#999]">{task.desk}</span>}
            </div>
          </div>
          <button onClick={onClose} className="p-2 rounded-lg hover:bg-[#f5f3ef] cursor-pointer text-[#aaa] hover:text-[#555] transition-colors">
            <X size={20} />
          </button>
        </div>

        <div className="p-6 space-y-5">
          {task.description && (
            <div>
              <label className="text-[10px] font-bold text-[#aaa] uppercase tracking-wider block mb-1.5">Description</label>
              <p className="text-sm text-[#555] leading-relaxed">{task.description}</p>
            </div>
          )}

          {task.result && (
            <div>
              <label className="text-[10px] font-bold text-[#aaa] uppercase tracking-wider block mb-1.5">Result</label>
              <div className="text-sm text-[#555] p-4 rounded-xl bg-[#f5f3ef] whitespace-pre-wrap max-h-[300px] overflow-y-auto leading-relaxed">
                {task.result}
              </div>
            </div>
          )}

          {task.escalation_reason && (
            <div className="p-4 rounded-xl bg-[#fef3c7] border border-[#fde68a]">
              <div className="text-[10px] font-bold text-[#d97706] mb-1.5 flex items-center gap-1.5">
                <AlertTriangle size={12} /> ESCALATION REASON
              </div>
              <div className="text-sm text-[#555]">{task.escalation_reason}</div>
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
              <label className="text-[10px] font-bold text-[#aaa] uppercase tracking-wider block mb-2">Activity Log</label>
              <div className="space-y-1.5">
                {task.actions.map((a, i) => (
                  <div key={i} className="flex items-start gap-3 p-3 rounded-xl bg-[#faf9f7]">
                    <span className={`w-2 h-2 rounded-full mt-1.5 shrink-0 ${a.success ? 'bg-[#16a34a]' : 'bg-[#dc2626]'}`} />
                    <div className="flex-1 min-w-0">
                      <span className="text-xs font-bold text-[#555]">{a.action}</span>
                      <div className="text-xs text-[#777] mt-0.5">{a.detail}</div>
                      <div className="text-[9px] font-mono text-[#ccc] mt-1" suppressHydrationWarning>{formatRelative(a.timestamp)}</div>
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
    in_progress: { bg: '#dbeafe', text: '#2563eb' }, completed: { bg: '#dcfce7', text: '#16a34a' },
    done: { bg: '#dcfce7', text: '#16a34a' }, failed: { bg: '#fee2e2', text: '#dc2626' },
    escalated: { bg: '#fef3c7', text: '#d97706' }, waiting: { bg: '#ede9fe', text: '#7c3aed' },
  };
  const c = colors[state] || colors.pending;
  return (
    <span className="text-[9px] font-bold px-2.5 py-1 rounded-full" style={{ background: c.bg, color: c.text }}>
      {state.replace('_', ' ').toUpperCase()}
    </span>
  );
}

function PriorityBadge({ priority }: { priority: string }) {
  const colors: Record<string, string> = { urgent: '#dc2626', high: '#d97706', normal: '#777', low: '#aaa' };
  const c = colors[priority] || '#777';
  return (
    <span className="text-[9px] font-bold px-2.5 py-1 rounded-full" style={{ color: c, background: c + '15' }}>
      {priority.toUpperCase()}
    </span>
  );
}

function InfoField({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[9px] font-bold text-[#aaa] uppercase tracking-wider">{label}</div>
      <div className="text-sm text-[#555] mt-1" suppressHydrationWarning>{value}</div>
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
