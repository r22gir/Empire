'use client';
import { useState, useEffect, useCallback } from 'react';
import { API } from '../../lib/api';
import {
  Plus, Search, CheckCircle2, Circle, Clock,
  ChevronDown, ChevronUp, X, Loader2, Trash2, MessageSquare,
  ListTodo, ArrowRight, Flag, Calendar, User, Briefcase, Send,
  ChevronLeft, RefreshCw,
} from 'lucide-react';

// ── Types ────────────────────────────────────────────────────────

interface Task {
  id: string;
  title: string;
  description?: string;
  status: string;
  priority: string;
  desk: string;
  assigned_to?: string;
  created_by?: string;
  due_date?: string;
  tags: string[];
  metadata: Record<string, any>;
  created_at?: string;
  updated_at?: string;
  completed_at?: string;
  activity?: ActivityEntry[];
  subtasks?: Task[];
}

interface ActivityEntry {
  id?: string;
  task_id?: string;
  actor: string;
  action: string;
  detail?: string;
  metadata?: Record<string, any>;
  created_at?: string;
}

interface DashboardData {
  desks: Record<string, Record<string, number>>;
  totals: Record<string, number>;
}

// ── Constants ────────────────────────────────────────────────────

const STATUS_OPTIONS = [
  { value: 'todo', label: 'To Do', color: '#d97706', bg: '#fffbeb', icon: Circle },
  { value: 'in_progress', label: 'In Progress', color: '#2563eb', bg: '#eff6ff', icon: Clock },
  { value: 'waiting', label: 'Waiting', color: '#7c3aed', bg: '#faf5ff', icon: Clock },
  { value: 'done', label: 'Done', color: '#16a34a', bg: '#f0fdf4', icon: CheckCircle2 },
];

const PRIORITY_OPTIONS = [
  { value: 'urgent', label: 'Urgent', color: '#dc2626', bg: '#fef2f2' },
  { value: 'high', label: 'High', color: '#d97706', bg: '#fffbeb' },
  { value: 'normal', label: 'Normal', color: '#2563eb', bg: '#eff6ff' },
  { value: 'low', label: 'Low', color: '#999', bg: '#f5f3ef' },
];

const DESK_OPTIONS = [
  'forge', 'market', 'marketing', 'support', 'sales', 'finance',
  'clients', 'contractors', 'it', 'website', 'legal', 'lab', 'innovation',
];

// ── Helpers ──────────────────────────────────────────────────────

function statusConfig(status: string) {
  return STATUS_OPTIONS.find(s => s.value === status) || STATUS_OPTIONS[0];
}
function priorityConfig(priority: string) {
  return PRIORITY_OPTIONS.find(p => p.value === priority) || PRIORITY_OPTIONS[2];
}
function timeAgo(dateStr?: string): string {
  if (!dateStr) return '';
  const d = new Date(dateStr + (dateStr.includes('Z') || dateStr.includes('+') ? '' : 'Z'));
  const diff = Date.now() - d.getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  return d.toLocaleDateString();
}

// ── Main Component ───────────────────────────────────────────────

export default function TasksScreen() {
  // State
  const [tasks, setTasks] = useState<Task[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);

  // Filters
  const [filterDesk, setFilterDesk] = useState('');
  const [filterStatus, setFilterStatus] = useState('');
  const [filterPriority, setFilterPriority] = useState('');
  const [searchText, setSearchText] = useState('');

  // UI state
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [showCreateDialog, setShowCreateDialog] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // ── Fetch tasks ──
  const fetchTasks = useCallback(async () => {
    setLoading(true);
    try {
      const params = new URLSearchParams();
      if (filterDesk) params.set('desk', filterDesk);
      if (filterStatus) params.set('status', filterStatus);
      if (filterPriority) params.set('priority', filterPriority);
      params.set('limit', '100');

      const res = await fetch(`${API}/tasks/?${params}`);
      if (res.ok) {
        const data = await res.json();
        let items: Task[] = data.tasks || [];
        // Client-side text filter
        if (searchText.trim()) {
          const q = searchText.toLowerCase();
          items = items.filter(t =>
            t.title.toLowerCase().includes(q) ||
            (t.description || '').toLowerCase().includes(q) ||
            (t.assigned_to || '').toLowerCase().includes(q)
          );
        }
        setTasks(items);
        setTotal(data.total || items.length);
      }
    } catch { /* offline */ }
    setLoading(false);
  }, [filterDesk, filterStatus, filterPriority, searchText]);

  // ── Fetch dashboard ──
  const fetchDashboard = useCallback(async () => {
    try {
      const res = await fetch(`${API}/tasks/dashboard`);
      if (res.ok) setDashboard(await res.json());
    } catch { /* offline */ }
  }, []);

  useEffect(() => { fetchTasks(); fetchDashboard(); }, [fetchTasks, fetchDashboard]);

  // ── Task detail ──
  const openTaskDetail = async (taskId: string) => {
    try {
      const res = await fetch(`${API}/tasks/${taskId}`);
      if (res.ok) {
        const data = await res.json();
        setSelectedTask(data.task);
      }
    } catch { /* offline */ }
  };

  // ── Quick actions ──
  const updateTaskStatus = async (taskId: string, newStatus: string) => {
    setActionLoading(taskId);
    try {
      const res = await fetch(`${API}/tasks/${taskId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      });
      if (res.ok) {
        fetchTasks();
        fetchDashboard();
        if (selectedTask?.id === taskId) {
          const data = await res.json();
          setSelectedTask(data.task);
        }
      }
    } catch { /* offline */ }
    setActionLoading(null);
  };

  const deleteTask = async (taskId: string) => {
    setActionLoading(taskId);
    try {
      const res = await fetch(`${API}/tasks/${taskId}`, { method: 'DELETE' });
      if (res.ok) {
        fetchTasks();
        fetchDashboard();
        if (selectedTask?.id === taskId) setSelectedTask(null);
      }
    } catch { /* offline */ }
    setActionLoading(null);
    setConfirmDelete(null);
  };

  const addComment = async (taskId: string, detail: string) => {
    try {
      await fetch(`${API}/tasks/${taskId}/comment`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ actor: 'rg', action: 'comment', detail }),
      });
      openTaskDetail(taskId);
    } catch { /* offline */ }
  };

  const handleTaskCreated = () => {
    setShowCreateDialog(false);
    fetchTasks();
    fetchDashboard();
  };

  // ── Render ──
  if (selectedTask) {
    return (
      <TaskDetailView
        task={selectedTask}
        onBack={() => setSelectedTask(null)}
        onStatusChange={(s) => updateTaskStatus(selectedTask.id, s)}
        onDelete={() => deleteTask(selectedTask.id)}
        onComment={(detail) => addComment(selectedTask.id, detail)}
        actionLoading={actionLoading === selectedTask.id}
      />
    );
  }

  const totalTodo = dashboard?.totals?.todo || 0;
  const totalInProgress = dashboard?.totals?.in_progress || 0;
  const totalWaiting = dashboard?.totals?.waiting || 0;
  const totalDone = dashboard?.totals?.done || 0;
  const totalAll = totalTodo + totalInProgress + totalWaiting + totalDone;

  return (
    <div className="flex-1 overflow-y-auto" style={{ background: '#f5f2ed', padding: '24px 36px' }}>
      {/* Header */}
      <div className="flex items-center justify-between mb-5">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-[#fdf8eb] flex items-center justify-center">
            <ListTodo size={20} className="text-[#b8960c]" />
          </div>
          <div>
            <h1 style={{ fontSize: 22, fontWeight: 600, color: '#1a1a1a', margin: 0 }}>Tasks</h1>
            <p style={{ fontSize: 13, color: '#aaa', margin: 0 }}>
              {totalAll} tasks across all desks
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => { fetchTasks(); fetchDashboard(); }}
            style={{
              height: 44, padding: '0 16px', borderRadius: 12,
              border: '1px solid var(--border)', background: 'var(--panel)',
              color: 'var(--text-secondary)', fontSize: 13, fontWeight: 500,
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            <RefreshCw size={14} /> Refresh
          </button>
          <button
            onClick={() => setShowCreateDialog(true)}
            style={{
              height: 44, padding: '0 20px', borderRadius: 12,
              border: 'none', background: '#1a1a1a', color: '#fff',
              fontSize: 13, fontWeight: 600, cursor: 'pointer',
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            <Plus size={16} /> New Task
          </button>
        </div>
      </div>

      {/* Dashboard Summary KPIs */}
      <div className="grid grid-cols-4 gap-3 mb-5">
        <DashKPI label="To Do" value={totalTodo} color="#d97706" bg="#fffbeb"
          active={filterStatus === 'todo'} onClick={() => setFilterStatus(filterStatus === 'todo' ? '' : 'todo')} />
        <DashKPI label="In Progress" value={totalInProgress} color="#2563eb" bg="#eff6ff"
          active={filterStatus === 'in_progress'} onClick={() => setFilterStatus(filterStatus === 'in_progress' ? '' : 'in_progress')} />
        <DashKPI label="Waiting" value={totalWaiting} color="#7c3aed" bg="#faf5ff"
          active={filterStatus === 'waiting'} onClick={() => setFilterStatus(filterStatus === 'waiting' ? '' : 'waiting')} />
        <DashKPI label="Done" value={totalDone} color="#16a34a" bg="#f0fdf4"
          active={filterStatus === 'done'} onClick={() => setFilterStatus(filterStatus === 'done' ? '' : 'done')} />
      </div>

      {/* Desk breakdown (collapsible) */}
      {dashboard && Object.keys(dashboard.desks).length > 0 && (
        <DeskBreakdown desks={dashboard.desks} filterDesk={filterDesk} onDeskFilter={setFilterDesk} />
      )}

      {/* Filter bar */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        <div className="relative flex-1 min-w-[200px]" style={{ maxWidth: 320 }}>
          <Search size={14} style={{ position: 'absolute', left: 12, top: '50%', transform: 'translateY(-50%)', color: '#bbb' }} />
          <input
            type="text"
            placeholder="Search tasks..."
            value={searchText}
            onChange={e => setSearchText(e.target.value)}
            className="form-input"
            style={{ paddingLeft: 34, height: 44 }}
          />
        </div>

        <SelectFilter
          label="Desk"
          value={filterDesk}
          onChange={setFilterDesk}
          options={[{ value: '', label: 'All Desks' }, ...DESK_OPTIONS.map(d => ({ value: d, label: d.charAt(0).toUpperCase() + d.slice(1) }))]}
        />
        <SelectFilter
          label="Status"
          value={filterStatus}
          onChange={setFilterStatus}
          options={[{ value: '', label: 'All Status' }, ...STATUS_OPTIONS.map(s => ({ value: s.value, label: s.label }))]}
        />
        <SelectFilter
          label="Priority"
          value={filterPriority}
          onChange={setFilterPriority}
          options={[{ value: '', label: 'All Priority' }, ...PRIORITY_OPTIONS.map(p => ({ value: p.value, label: p.label }))]}
        />

        {(filterDesk || filterStatus || filterPriority || searchText) && (
          <button
            onClick={() => { setFilterDesk(''); setFilterStatus(''); setFilterPriority(''); setSearchText(''); }}
            style={{
              height: 44, padding: '0 14px', borderRadius: 10,
              border: '1px solid var(--border)', background: 'var(--panel)',
              color: '#dc2626', fontSize: 12, fontWeight: 500,
              cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 4,
            }}
          >
            <X size={12} /> Clear
          </button>
        )}
      </div>

      {/* Task list */}
      {loading ? (
        <div className="flex items-center justify-center py-20">
          <Loader2 size={24} className="text-[#b8960c] animate-spin" />
        </div>
      ) : tasks.length === 0 ? (
        <div className="flex flex-col items-center justify-center py-20 gap-3">
          <div className="w-16 h-16 rounded-2xl bg-[#fdf8eb] flex items-center justify-center">
            <ListTodo size={28} className="text-[#d4b84a]" />
          </div>
          <p style={{ fontSize: 14, color: '#999' }}>No tasks found</p>
          <button
            onClick={() => setShowCreateDialog(true)}
            style={{
              height: 44, padding: '0 20px', borderRadius: 12,
              border: '1px solid var(--gold-border)', background: 'var(--gold-light)',
              color: 'var(--gold)', fontSize: 13, fontWeight: 600, cursor: 'pointer',
            }}
          >
            Create your first task
          </button>
        </div>
      ) : (
        <div className="flex flex-col gap-2">
          {tasks.map(task => (
            <TaskRow
              key={task.id}
              task={task}
              onClick={() => openTaskDetail(task.id)}
              onStatusChange={(s) => updateTaskStatus(task.id, s)}
              onDelete={() => {
                if (confirmDelete === task.id) deleteTask(task.id);
                else setConfirmDelete(task.id);
              }}
              confirmingDelete={confirmDelete === task.id}
              onCancelDelete={() => setConfirmDelete(null)}
              actionLoading={actionLoading === task.id}
            />
          ))}
          {tasks.length < total && (
            <p style={{ fontSize: 12, color: '#999', textAlign: 'center', padding: 12 }}>
              Showing {tasks.length} of {total} tasks
            </p>
          )}
        </div>
      )}

      {/* Create dialog */}
      {showCreateDialog && (
        <CreateTaskDialog
          onClose={() => setShowCreateDialog(false)}
          onCreated={handleTaskCreated}
        />
      )}
    </div>
  );
}

// ── Sub-components ───────────────────────────────────────────────

function DashKPI({ label, value, color, bg, active, onClick }: {
  label: string; value: number; color: string; bg: string; active: boolean; onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="empire-card"
      style={{
        cursor: 'pointer',
        border: active ? `2px solid ${color}` : '1px solid var(--border)',
        background: active ? bg : 'var(--card-bg)',
        textAlign: 'left',
        padding: '14px 16px',
      }}
    >
      <div className="kpi-value" style={{ color, fontSize: 24 }}>{value}</div>
      <div className="kpi-label">{label}</div>
    </button>
  );
}

function DeskBreakdown({ desks, filterDesk, onDeskFilter }: {
  desks: Record<string, Record<string, number>>; filterDesk: string; onDeskFilter: (d: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const entries = Object.entries(desks).sort((a, b) => {
    const totalA = Object.values(a[1]).reduce((s, n) => s + n, 0);
    const totalB = Object.values(b[1]).reduce((s, n) => s + n, 0);
    return totalB - totalA;
  });

  return (
    <div className="mb-5">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2 mb-2 cursor-pointer"
        style={{ background: 'none', border: 'none', padding: 0 }}
      >
        <span className="section-label">By Desk</span>
        {expanded ? <ChevronUp size={12} className="text-[#ccc]" /> : <ChevronDown size={12} className="text-[#ccc]" />}
        <span style={{ fontSize: 10, color: '#bbb' }}>{entries.length} desks</span>
      </button>
      {expanded && (
        <div className="grid grid-cols-3 gap-2">
          {entries.map(([desk, counts]) => {
            const deskTotal = Object.values(counts).reduce((s, n) => s + n, 0);
            const isActive = filterDesk === desk;
            return (
              <button
                key={desk}
                onClick={() => onDeskFilter(isActive ? '' : desk)}
                className="empire-card"
                style={{
                  cursor: 'pointer', textAlign: 'left',
                  border: isActive ? '2px solid var(--gold)' : '1px solid var(--border)',
                  background: isActive ? 'var(--gold-light)' : 'var(--card-bg)',
                  padding: '10px 14px',
                }}
              >
                <div className="flex items-center justify-between mb-1">
                  <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--text)', textTransform: 'capitalize' }}>{desk}</span>
                  <span style={{ fontSize: 14, fontWeight: 700, color: 'var(--gold)' }}>{deskTotal}</span>
                </div>
                <div className="flex gap-2">
                  {counts.todo > 0 && <MiniCount label="todo" count={counts.todo} color="#d97706" />}
                  {counts.in_progress > 0 && <MiniCount label="prog" count={counts.in_progress} color="#2563eb" />}
                  {counts.waiting > 0 && <MiniCount label="wait" count={counts.waiting} color="#7c3aed" />}
                  {counts.done > 0 && <MiniCount label="done" count={counts.done} color="#16a34a" />}
                </div>
              </button>
            );
          })}
        </div>
      )}
    </div>
  );
}

function MiniCount({ label, count, color }: { label: string; count: number; color: string }) {
  return (
    <span style={{ fontSize: 9, fontWeight: 600, color, background: `${color}11`, padding: '2px 6px', borderRadius: 6 }}>
      {count} {label}
    </span>
  );
}

function SelectFilter({ label, value, onChange, options }: {
  label: string; value: string; onChange: (v: string) => void;
  options: { value: string; label: string }[];
}) {
  return (
    <select
      value={value}
      onChange={e => onChange(e.target.value)}
      className="form-input"
      style={{ width: 'auto', height: 44, minWidth: 120, paddingRight: 32, cursor: 'pointer' }}
      aria-label={label}
    >
      {options.map(o => (
        <option key={o.value} value={o.value}>{o.label}</option>
      ))}
    </select>
  );
}

// ── Task Row ─────────────────────────────────────────────────────

function TaskRow({ task, onClick, onStatusChange, onDelete, confirmingDelete, onCancelDelete, actionLoading }: {
  task: Task; onClick: () => void; onStatusChange: (s: string) => void;
  onDelete: () => void; confirmingDelete: boolean; onCancelDelete: () => void; actionLoading: boolean;
}) {
  const sc = statusConfig(task.status);
  const pc = priorityConfig(task.priority);
  const StatusIcon = sc.icon;

  return (
    <div
      className="empire-card"
      style={{ padding: '12px 16px', display: 'flex', alignItems: 'center', gap: 12 }}
    >
      {/* Status toggle */}
      <button
        onClick={(e) => { e.stopPropagation(); onStatusChange(task.status === 'done' ? 'todo' : 'done'); }}
        style={{
          width: 28, height: 28, borderRadius: 8, border: `2px solid ${sc.color}`,
          background: task.status === 'done' ? sc.bg : 'transparent',
          cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
          flexShrink: 0,
        }}
        title={task.status === 'done' ? 'Mark incomplete' : 'Mark complete'}
        disabled={actionLoading}
      >
        {actionLoading ? (
          <Loader2 size={14} className="animate-spin" style={{ color: sc.color }} />
        ) : (
          <StatusIcon size={14} style={{ color: sc.color }} />
        )}
      </button>

      {/* Main content (clickable) */}
      <div className="flex-1 min-w-0 cursor-pointer" onClick={onClick}>
        <div className="flex items-center gap-2">
          <span style={{
            fontSize: 13, fontWeight: 600, color: task.status === 'done' ? '#999' : '#1a1a1a',
            textDecoration: task.status === 'done' ? 'line-through' : 'none',
          }} className="truncate">
            {task.title}
          </span>
        </div>
        <div className="flex items-center gap-3 mt-1">
          <span style={{
            fontSize: 10, fontWeight: 600, textTransform: 'capitalize',
            color: sc.color, background: sc.bg, padding: '2px 8px', borderRadius: 6,
          }}>{sc.label}</span>
          <span style={{
            fontSize: 10, fontWeight: 600,
            color: pc.color, background: pc.bg, padding: '2px 8px', borderRadius: 6,
          }}>{pc.label}</span>
          <span style={{ fontSize: 10, color: '#999', textTransform: 'capitalize' }}>
            <Briefcase size={10} className="inline mr-1" style={{ verticalAlign: -1 }} />
            {task.desk}
          </span>
          {task.assigned_to && (
            <span style={{ fontSize: 10, color: '#999' }}>
              <User size={10} className="inline mr-1" style={{ verticalAlign: -1 }} />
              {task.assigned_to}
            </span>
          )}
          {task.due_date && (
            <span style={{ fontSize: 10, color: '#999' }}>
              <Calendar size={10} className="inline mr-1" style={{ verticalAlign: -1 }} />
              {task.due_date}
            </span>
          )}
          <span style={{ fontSize: 10, color: '#ccc' }}>
            {timeAgo(task.created_at)}
          </span>
        </div>
      </div>

      {/* Quick actions */}
      <div className="flex items-center gap-1" style={{ flexShrink: 0 }}>
        {task.status !== 'done' && task.status !== 'in_progress' && (
          <button
            onClick={(e) => { e.stopPropagation(); onStatusChange('in_progress'); }}
            title="Start task"
            disabled={actionLoading}
            style={{
              width: 32, height: 32, borderRadius: 8,
              border: '1px solid var(--border)', background: 'var(--panel)',
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >
            <ArrowRight size={14} style={{ color: '#2563eb' }} />
          </button>
        )}
        {confirmingDelete ? (
          <div className="flex items-center gap-1">
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(); }}
              style={{
                height: 32, padding: '0 10px', borderRadius: 8,
                border: 'none', background: '#dc2626', color: '#fff',
                fontSize: 11, fontWeight: 600, cursor: 'pointer',
              }}
            >
              Confirm
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onCancelDelete(); }}
              style={{
                height: 32, padding: '0 8px', borderRadius: 8,
                border: '1px solid var(--border)', background: 'var(--panel)',
                cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}
            >
              <X size={14} style={{ color: '#999' }} />
            </button>
          </div>
        ) : (
          <button
            onClick={(e) => { e.stopPropagation(); onDelete(); }}
            title="Delete task"
            style={{
              width: 32, height: 32, borderRadius: 8,
              border: '1px solid var(--border)', background: 'var(--panel)',
              cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}
          >
            <Trash2 size={14} style={{ color: '#999' }} />
          </button>
        )}
      </div>
    </div>
  );
}

// ── Task Detail View ─────────────────────────────────────────────

function TaskDetailView({ task, onBack, onStatusChange, onDelete, onComment, actionLoading }: {
  task: Task; onBack: () => void; onStatusChange: (s: string) => void;
  onDelete: () => void; onComment: (detail: string) => void; actionLoading: boolean;
}) {
  const [commentText, setCommentText] = useState('');
  const [confirmDel, setConfirmDel] = useState(false);
  const sc = statusConfig(task.status);
  const pc = priorityConfig(task.priority);

  const handleSubmitComment = () => {
    if (!commentText.trim()) return;
    onComment(commentText.trim());
    setCommentText('');
  };

  return (
    <div className="flex-1 overflow-y-auto" style={{ background: '#f5f2ed', padding: '24px 36px' }}>
      {/* Back button */}
      <button
        onClick={onBack}
        style={{
          height: 44, padding: '0 16px', borderRadius: 12,
          border: '1px solid var(--border)', background: 'var(--panel)',
          color: 'var(--text-secondary)', fontSize: 13, fontWeight: 500,
          cursor: 'pointer', display: 'flex', alignItems: 'center', gap: 6,
          marginBottom: 16,
        }}
      >
        <ChevronLeft size={16} /> Back to tasks
      </button>

      {/* Task header */}
      <div className="empire-card flat" style={{ padding: '20px 24px', marginBottom: 16 }}>
        <div className="flex items-start justify-between gap-4">
          <div className="flex-1">
            <h2 style={{ fontSize: 20, fontWeight: 700, color: '#1a1a1a', margin: '0 0 8px' }}>{task.title}</h2>
            {task.description && (
              <p style={{ fontSize: 14, color: '#555', lineHeight: 1.6, margin: 0 }}>{task.description}</p>
            )}
          </div>
          <div className="flex items-center gap-2" style={{ flexShrink: 0 }}>
            {confirmDel ? (
              <>
                <button
                  onClick={onDelete}
                  style={{
                    height: 44, padding: '0 16px', borderRadius: 12,
                    border: 'none', background: '#dc2626', color: '#fff',
                    fontSize: 13, fontWeight: 600, cursor: 'pointer',
                  }}
                >
                  Confirm Delete
                </button>
                <button
                  onClick={() => setConfirmDel(false)}
                  style={{
                    height: 44, padding: '0 16px', borderRadius: 12,
                    border: '1px solid var(--border)', background: 'var(--panel)',
                    color: 'var(--text-secondary)', fontSize: 13, cursor: 'pointer',
                  }}
                >
                  Cancel
                </button>
              </>
            ) : (
              <button
                onClick={() => setConfirmDel(true)}
                style={{
                  height: 44, padding: '0 16px', borderRadius: 12,
                  border: '1px solid var(--border)', background: 'var(--panel)',
                  color: '#dc2626', fontSize: 13, fontWeight: 500, cursor: 'pointer',
                  display: 'flex', alignItems: 'center', gap: 6,
                }}
              >
                <Trash2 size={14} /> Delete
              </button>
            )}
          </div>
        </div>

        {/* Metadata grid */}
        <div className="grid grid-cols-4 gap-3 mt-4">
          <MetaField label="Status">
            <span style={{ color: sc.color, background: sc.bg, padding: '4px 12px', borderRadius: 8, fontSize: 12, fontWeight: 600 }}>
              {sc.label}
            </span>
          </MetaField>
          <MetaField label="Priority">
            <span style={{ color: pc.color, background: pc.bg, padding: '4px 12px', borderRadius: 8, fontSize: 12, fontWeight: 600 }}>
              {pc.label}
            </span>
          </MetaField>
          <MetaField label="Desk">
            <span style={{ fontSize: 13, fontWeight: 600, color: '#555', textTransform: 'capitalize' }}>{task.desk}</span>
          </MetaField>
          <MetaField label="Assigned To">
            <span style={{ fontSize: 13, fontWeight: 600, color: '#555' }}>{task.assigned_to || 'Unassigned'}</span>
          </MetaField>
        </div>

        <div className="grid grid-cols-4 gap-3 mt-3">
          <MetaField label="Created">
            <span style={{ fontSize: 12, color: '#777' }}>{timeAgo(task.created_at)}</span>
          </MetaField>
          <MetaField label="Updated">
            <span style={{ fontSize: 12, color: '#777' }}>{timeAgo(task.updated_at)}</span>
          </MetaField>
          <MetaField label="Due Date">
            <span style={{ fontSize: 12, color: task.due_date ? '#555' : '#ccc' }}>{task.due_date || 'None'}</span>
          </MetaField>
          <MetaField label="Tags">
            <div className="flex gap-1 flex-wrap">
              {task.tags.length > 0 ? task.tags.map(t => (
                <span key={t} style={{ fontSize: 10, fontWeight: 600, color: '#b8960c', background: '#fdf8eb', padding: '2px 8px', borderRadius: 6 }}>{t}</span>
              )) : <span style={{ fontSize: 12, color: '#ccc' }}>None</span>}
            </div>
          </MetaField>
        </div>

        {/* Status change buttons */}
        <div className="flex gap-2 mt-4 pt-4" style={{ borderTop: '1px solid var(--border)' }}>
          <span className="section-label" style={{ alignSelf: 'center', marginRight: 8 }}>Change Status:</span>
          {STATUS_OPTIONS.map(s => (
            <button
              key={s.value}
              onClick={() => onStatusChange(s.value)}
              disabled={task.status === s.value || actionLoading}
              style={{
                height: 44, padding: '0 16px', borderRadius: 10,
                border: task.status === s.value ? `2px solid ${s.color}` : '1px solid var(--border)',
                background: task.status === s.value ? s.bg : 'var(--panel)',
                color: task.status === s.value ? s.color : '#777',
                fontSize: 12, fontWeight: 600, cursor: task.status === s.value ? 'default' : 'pointer',
                opacity: task.status === s.value ? 1 : 0.8,
              }}
            >
              {actionLoading && task.status !== s.value ? <Loader2 size={14} className="animate-spin" /> : s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Subtasks */}
      {task.subtasks && task.subtasks.length > 0 && (
        <div className="empire-card flat" style={{ padding: '16px 20px', marginBottom: 16 }}>
          <div className="section-label mb-3">Subtasks ({task.subtasks.length})</div>
          <div className="flex flex-col gap-2">
            {task.subtasks.map(st => {
              const stc = statusConfig(st.status);
              return (
                <div key={st.id} className="flex items-center gap-3" style={{ padding: '8px 12px', borderRadius: 10, background: '#faf9f7', border: '1px solid #ece8e0' }}>
                  <stc.icon size={14} style={{ color: stc.color, flexShrink: 0 }} />
                  <span style={{ fontSize: 12, fontWeight: 500, color: st.status === 'done' ? '#999' : '#1a1a1a', textDecoration: st.status === 'done' ? 'line-through' : 'none' }}>{st.title}</span>
                  <span style={{ fontSize: 10, color: stc.color, marginLeft: 'auto' }}>{stc.label}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Activity log + Comments */}
      <div className="empire-card flat" style={{ padding: '16px 20px' }}>
        <div className="section-label mb-3">Activity Log</div>

        {/* Comment input */}
        <div className="flex gap-2 mb-4">
          <input
            type="text"
            placeholder="Add a comment..."
            value={commentText}
            onChange={e => setCommentText(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleSubmitComment(); }}
            className="form-input"
            style={{ flex: 1, height: 44 }}
          />
          <button
            onClick={handleSubmitComment}
            disabled={!commentText.trim()}
            style={{
              height: 44, padding: '0 16px', borderRadius: 10,
              border: 'none', background: commentText.trim() ? '#1a1a1a' : '#ddd',
              color: '#fff', fontSize: 13, fontWeight: 600, cursor: commentText.trim() ? 'pointer' : 'default',
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            <Send size={14} /> Send
          </button>
        </div>

        {/* Activity entries */}
        {task.activity && task.activity.length > 0 ? (
          <div className="flex flex-col gap-2">
            {task.activity.map((entry, i) => (
              <div key={entry.id || i} className="flex gap-3" style={{ padding: '10px 12px', borderRadius: 10, background: entry.action === 'comment' ? '#faf9f7' : 'transparent', border: entry.action === 'comment' ? '1px solid #ece8e0' : 'none' }}>
                <div style={{
                  width: 28, height: 28, borderRadius: 8, flexShrink: 0,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  background: entry.action === 'comment' ? '#fdf8eb' : entry.action === 'created' ? '#f0fdf4' : '#eff6ff',
                }}>
                  {entry.action === 'comment' ? <MessageSquare size={12} style={{ color: '#b8960c' }} /> :
                   entry.action === 'created' ? <Plus size={12} style={{ color: '#16a34a' }} /> :
                   <Flag size={12} style={{ color: '#2563eb' }} />}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span style={{ fontSize: 12, fontWeight: 600, color: '#1a1a1a' }}>{entry.actor}</span>
                    <span style={{ fontSize: 10, color: '#bbb' }}>{entry.action.replace(/_/g, ' ')}</span>
                    <span style={{ fontSize: 10, color: '#ddd', marginLeft: 'auto' }}>{timeAgo(entry.created_at)}</span>
                  </div>
                  {entry.detail && (
                    <p style={{ fontSize: 12, color: '#555', margin: '4px 0 0', lineHeight: 1.5 }}>{entry.detail}</p>
                  )}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ fontSize: 12, color: '#ccc', textAlign: 'center', padding: 16 }}>No activity yet</p>
        )}
      </div>
    </div>
  );
}

function MetaField({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <div style={{ fontSize: 9, fontWeight: 700, color: '#999', textTransform: 'uppercase', letterSpacing: '0.05em', marginBottom: 4 }}>{label}</div>
      {children}
    </div>
  );
}

// ── Create Task Dialog ───────────────────────────────────────────

function CreateTaskDialog({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [desk, setDesk] = useState('forge');
  const [priority, setPriority] = useState('normal');
  const [status, setStatus] = useState('todo');
  const [assignedTo, setAssignedTo] = useState('');
  const [dueDate, setDueDate] = useState('');
  const [tagsInput, setTagsInput] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  const handleSubmit = async () => {
    if (!title.trim()) { setError('Title is required'); return; }
    setSubmitting(true);
    setError('');

    try {
      const body: any = {
        title: title.trim(),
        description: description.trim() || undefined,
        desk,
        priority,
        status,
        assigned_to: assignedTo.trim() || undefined,
        due_date: dueDate || undefined,
        tags: tagsInput.trim() ? tagsInput.split(',').map(t => t.trim()).filter(Boolean) : undefined,
      };

      const res = await fetch(`${API}/tasks/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        onCreated();
      } else {
        const data = await res.json().catch(() => ({}));
        setError(data.detail || `Error ${res.status}`);
      }
    } catch {
      setError('Failed to connect to server');
    }
    setSubmitting(false);
  };

  return (
    <div
      style={{
        position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.4)',
        display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000,
      }}
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
    >
      <div style={{
        background: '#fff', borderRadius: 20, padding: '28px 32px', width: 520, maxHeight: '85vh',
        overflow: 'auto', boxShadow: '0 20px 60px rgba(0,0,0,0.15)',
      }}>
        <div className="flex items-center justify-between mb-5">
          <h3 style={{ fontSize: 18, fontWeight: 700, color: '#1a1a1a', margin: 0 }}>New Task</h3>
          <button onClick={onClose} style={{ width: 36, height: 36, borderRadius: 10, border: '1px solid #ece8e0', background: '#faf9f7', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <X size={16} style={{ color: '#999' }} />
          </button>
        </div>

        {error && (
          <div style={{ padding: '10px 14px', borderRadius: 10, background: '#fef2f2', border: '1px solid #fecaca', color: '#dc2626', fontSize: 12, fontWeight: 500, marginBottom: 12 }}>
            {error}
          </div>
        )}

        <div className="flex flex-col gap-3">
          <div>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#777', display: 'block', marginBottom: 4 }}>Title *</label>
            <input
              type="text"
              value={title}
              onChange={e => setTitle(e.target.value)}
              placeholder="What needs to be done?"
              className="form-input"
              style={{ height: 44 }}
              autoFocus
            />
          </div>

          <div>
            <label style={{ fontSize: 11, fontWeight: 600, color: '#777', display: 'block', marginBottom: 4 }}>Description</label>
            <textarea
              value={description}
              onChange={e => setDescription(e.target.value)}
              placeholder="Add details..."
              className="form-input"
              style={{ height: 80, resize: 'vertical' }}
            />
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#777', display: 'block', marginBottom: 4 }}>Desk *</label>
              <select value={desk} onChange={e => setDesk(e.target.value)} className="form-input" style={{ height: 44, cursor: 'pointer' }}>
                {DESK_OPTIONS.map(d => (
                  <option key={d} value={d}>{d.charAt(0).toUpperCase() + d.slice(1)}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#777', display: 'block', marginBottom: 4 }}>Priority</label>
              <select value={priority} onChange={e => setPriority(e.target.value)} className="form-input" style={{ height: 44, cursor: 'pointer' }}>
                {PRIORITY_OPTIONS.map(p => (
                  <option key={p.value} value={p.value}>{p.label}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#777', display: 'block', marginBottom: 4 }}>Status</label>
              <select value={status} onChange={e => setStatus(e.target.value)} className="form-input" style={{ height: 44, cursor: 'pointer' }}>
                {STATUS_OPTIONS.map(s => (
                  <option key={s.value} value={s.value}>{s.label}</option>
                ))}
              </select>
            </div>
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#777', display: 'block', marginBottom: 4 }}>Assigned To</label>
              <input
                type="text"
                value={assignedTo}
                onChange={e => setAssignedTo(e.target.value)}
                placeholder="Person or desk agent"
                className="form-input"
                style={{ height: 44 }}
              />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#777', display: 'block', marginBottom: 4 }}>Due Date</label>
              <input
                type="date"
                value={dueDate}
                onChange={e => setDueDate(e.target.value)}
                className="form-input"
                style={{ height: 44 }}
              />
            </div>
            <div>
              <label style={{ fontSize: 11, fontWeight: 600, color: '#777', display: 'block', marginBottom: 4 }}>Tags (comma separated)</label>
              <input
                type="text"
                value={tagsInput}
                onChange={e => setTagsInput(e.target.value)}
                placeholder="e.g. follow-up, urgent"
                className="form-input"
                style={{ height: 44 }}
              />
            </div>
          </div>
        </div>

        <div className="flex justify-end gap-2 mt-6">
          <button
            onClick={onClose}
            style={{
              height: 44, padding: '0 20px', borderRadius: 12,
              border: '1px solid var(--border)', background: 'var(--panel)',
              color: 'var(--text-secondary)', fontSize: 13, fontWeight: 500, cursor: 'pointer',
            }}
          >
            Cancel
          </button>
          <button
            onClick={handleSubmit}
            disabled={submitting || !title.trim()}
            style={{
              height: 44, padding: '0 24px', borderRadius: 12,
              border: 'none', background: title.trim() ? '#1a1a1a' : '#ddd',
              color: '#fff', fontSize: 13, fontWeight: 600,
              cursor: title.trim() ? 'pointer' : 'default',
              display: 'flex', alignItems: 'center', gap: 6,
            }}
          >
            {submitting ? <Loader2 size={14} className="animate-spin" /> : <Plus size={16} />}
            Create Task
          </button>
        </div>
      </div>
    </div>
  );
}
