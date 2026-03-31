'use client';
import { useState, useEffect, useCallback } from 'react';

const API = typeof window !== 'undefined' && window.location.hostname !== 'localhost'
  ? 'https://api.empirebox.store/api/v1'
  : 'http://localhost:8000/api/v1';

interface Task {
  id: number;
  title: string;
  description: string;
  desk: string;
  priority: number;
  status: string;
  source: string;
  created_at: string;
  started_at: string | null;
  completed_at: string | null;
  result: string | null;
  error: string | null;
  files_modified: string | null;
  commit_hash: string | null;
  retry_count: number;
}

const STATUS_COLORS: Record<string, { bg: string; text: string; label: string }> = {
  queued: { bg: '#f3f4f6', text: '#6b7280', label: 'Queued' },
  running: { bg: '#dbeafe', text: '#2563eb', label: 'Running' },
  done: { bg: '#dcfce7', text: '#16a34a', label: 'Done' },
  failed: { bg: '#fee2e2', text: '#dc2626', label: 'Failed' },
  paused: { bg: '#fef3c7', text: '#d97706', label: 'Needs Approval' },
  cancelled: { bg: '#e5e7eb', text: '#9ca3af', label: 'Cancelled' },
};

const DESKS = [
  'general', 'CodeForge', 'ITDesk', 'ForgeDesk', 'MarketingDesk', 'SupportDesk',
  'FinanceDesk', 'WebsiteDesk', 'AnalyticsDesk', 'QualityDesk', 'SalesDesk',
  'ClientsDesk', 'ContractorsDesk', 'LegalDesk', 'InnovationDesk', 'LabDesk',
  'IntakeDesk', 'CostTracker',
];

export default function OpenClawTasksPage() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [stats, setStats] = useState<Record<string, number>>({});
  const [selectedTask, setSelectedTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState('');

  // New task form
  const [showForm, setShowForm] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newDesc, setNewDesc] = useState('');
  const [newDesk, setNewDesk] = useState('general');
  const [newPriority, setNewPriority] = useState(5);
  const [creating, setCreating] = useState(false);

  const fetchTasks = useCallback(async () => {
    try {
      const params = statusFilter ? `?status=${statusFilter}` : '';
      const [tasksRes, statsRes] = await Promise.all([
        fetch(`${API}/openclaw/tasks${params}`),
        fetch(`${API}/openclaw/tasks/stats`),
      ]);
      if (tasksRes.ok) {
        const data = await tasksRes.json();
        setTasks(data.tasks || []);
      }
      if (statsRes.ok) {
        const data = await statsRes.json();
        const { total, ...rest } = data;
        setStats(rest);
      }
    } catch { /* ignore */ }
    setLoading(false);
  }, [statusFilter]);

  useEffect(() => {
    fetchTasks();
    const interval = setInterval(fetchTasks, 30000);
    return () => clearInterval(interval);
  }, [fetchTasks]);

  const createTask = async () => {
    if (!newTitle.trim()) return;
    setCreating(true);
    try {
      const res = await fetch(`${API}/openclaw/tasks`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: newTitle, description: newDesc || newTitle,
          desk: newDesk, priority: newPriority,
        }),
      });
      if (res.ok) {
        setNewTitle(''); setNewDesc(''); setShowForm(false);
        fetchTasks();
      }
    } catch { /* ignore */ }
    setCreating(false);
  };

  const taskAction = async (id: number, action: string) => {
    const methods: Record<string, { method: string; path: string }> = {
      retry: { method: 'POST', path: `/${id}/retry` },
      cancel: { method: 'DELETE', path: `/${id}` },
      approve: { method: 'POST', path: `/${id}/approve` },
      reject: { method: 'POST', path: `/${id}/reject` },
    };
    const { method, path } = methods[action] || {};
    if (!method) return;
    try {
      await fetch(`${API}/openclaw/tasks${path}`, { method });
      fetchTasks();
      if (selectedTask?.id === id) setSelectedTask(null);
    } catch { /* ignore */ }
  };

  const fmtDate = (d: string | null) => {
    if (!d) return '—';
    try {
      const dt = new Date(d);
      return dt.toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch { return d; }
  };

  const priorityLabel = (p: number) => {
    if (p <= 1) return { text: 'CRITICAL', color: '#dc2626' };
    if (p <= 3) return { text: 'HIGH', color: '#f59e0b' };
    if (p <= 5) return { text: 'NORMAL', color: '#6b7280' };
    return { text: 'LOW', color: '#9ca3af' };
  };

  const inputStyle: React.CSSProperties = {
    width: '100%', padding: '12px 14px', borderRadius: 10,
    border: '1.5px solid #e5e0d8', fontSize: 15, background: '#fff',
    color: '#333', outline: 'none', minHeight: 44,
  };
  const btnBase: React.CSSProperties = {
    padding: '10px 18px', borderRadius: 10, border: 'none', fontSize: 14,
    fontWeight: 700, cursor: 'pointer', minHeight: 44, minWidth: 44,
    transition: 'all 0.15s', display: 'inline-flex', alignItems: 'center',
    justifyContent: 'center', gap: 6,
  };

  return (
    <div style={{ padding: '20px 24px', maxWidth: 1200, margin: '0 auto' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 20, flexWrap: 'wrap', gap: 12 }}>
        <div>
          <div style={{
            display: 'inline-block', background: 'linear-gradient(135deg, #b8960c, #d4af37)',
            color: '#1a1a2e', padding: '4px 14px', borderRadius: 16, fontSize: 11,
            fontWeight: 700, letterSpacing: 1.2, textTransform: 'uppercase', marginBottom: 8,
          }}>OpenClaw Tasks</div>
          <h1 style={{ fontSize: 24, fontWeight: 800, color: '#1a1a2e', margin: 0 }}>
            Autonomous Task Queue
          </h1>
        </div>
        <button onClick={() => setShowForm(!showForm)} style={{
          ...btnBase, background: 'linear-gradient(135deg, #b8960c, #d4af37)', color: '#1a1a2e',
        }}>
          {showForm ? 'Cancel' : '+ New Task'}
        </button>
      </div>

      {/* Stats bar */}
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginBottom: 16 }}>
        <button onClick={() => setStatusFilter('')} style={{
          ...btnBase, padding: '6px 14px', fontSize: 12,
          background: !statusFilter ? '#1a1a2e' : '#f3f4f6',
          color: !statusFilter ? '#d4af37' : '#666',
        }}>
          All ({Object.values(stats).reduce((a, b) => a + b, 0)})
        </button>
        {Object.entries(STATUS_COLORS).map(([key, { bg, text, label }]) => (
          stats[key] ? (
            <button key={key} onClick={() => setStatusFilter(statusFilter === key ? '' : key)} style={{
              ...btnBase, padding: '6px 14px', fontSize: 12,
              background: statusFilter === key ? text : bg,
              color: statusFilter === key ? '#fff' : text,
            }}>
              {label} ({stats[key] || 0})
            </button>
          ) : null
        ))}
      </div>

      {/* New task form */}
      {showForm && (
        <div style={{ background: '#fff', borderRadius: 14, padding: 20, border: '1.5px solid #b8960c', marginBottom: 16 }}>
          <div style={{ display: 'flex', gap: 10, marginBottom: 10, flexWrap: 'wrap' }}>
            <div style={{ flex: 2, minWidth: 200 }}>
              <input value={newTitle} onChange={e => setNewTitle(e.target.value)} placeholder="Task title..." style={inputStyle} />
            </div>
            <div style={{ flex: 1, minWidth: 120 }}>
              <select value={newDesk} onChange={e => setNewDesk(e.target.value)} style={{ ...inputStyle, cursor: 'pointer' }}>
                {DESKS.map(d => <option key={d} value={d}>{d}</option>)}
              </select>
            </div>
            <div style={{ width: 80 }}>
              <input type="number" value={newPriority} onChange={e => setNewPriority(Number(e.target.value))}
                min={1} max={10} style={inputStyle} title="Priority (1=critical, 5=normal, 10=low)" />
            </div>
          </div>
          <textarea value={newDesc} onChange={e => setNewDesc(e.target.value)} placeholder="Description (what should OpenClaw do?)..."
            style={{ ...inputStyle, minHeight: 70, resize: 'vertical', fontFamily: 'inherit', marginBottom: 10 }} />
          <button onClick={createTask} disabled={creating || !newTitle.trim()} style={{
            ...btnBase, width: '100%', background: newTitle.trim() ? 'linear-gradient(135deg, #b8960c, #d4af37)' : '#eee',
            color: newTitle.trim() ? '#1a1a2e' : '#999',
          }}>
            {creating ? 'Creating...' : 'Queue Task'}
          </button>
        </div>
      )}

      {/* Task list + detail split */}
      <div style={{ display: 'grid', gridTemplateColumns: selectedTask ? '1fr 1fr' : '1fr', gap: 16 }}>
        {/* Task list */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {loading ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>Loading...</div>
          ) : tasks.length === 0 ? (
            <div style={{ textAlign: 'center', padding: 40, color: '#999' }}>
              No tasks{statusFilter ? ` with status "${statusFilter}"` : ''}. Create one above.
            </div>
          ) : tasks.map(task => {
            const sc = STATUS_COLORS[task.status] || STATUS_COLORS.queued;
            const pl = priorityLabel(task.priority);
            const isSelected = selectedTask?.id === task.id;
            return (
              <div key={task.id} onClick={() => setSelectedTask(isSelected ? null : task)} style={{
                background: isSelected ? '#fdf8eb' : '#fff', borderRadius: 12, padding: '14px 16px',
                border: isSelected ? '2px solid #b8960c' : '1px solid #ece8e0',
                cursor: 'pointer', transition: 'all 0.1s',
              }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 6 }}>
                  <span style={{
                    background: sc.bg, color: sc.text, padding: '2px 10px', borderRadius: 12,
                    fontSize: 11, fontWeight: 700, textTransform: 'uppercase',
                    animation: task.status === 'running' ? 'pulse 2s infinite' : 'none',
                  }}>
                    {sc.label}
                  </span>
                  <span style={{ fontSize: 10, fontWeight: 700, color: pl.color }}>{pl.text}</span>
                  <span style={{ fontSize: 11, color: '#999', marginLeft: 'auto' }}>#{task.id}</span>
                </div>
                <div style={{ fontSize: 15, fontWeight: 700, color: '#1a1a2e', marginBottom: 4 }}>{task.title}</div>
                <div style={{ display: 'flex', gap: 12, fontSize: 12, color: '#888' }}>
                  <span>{task.desk}</span>
                  <span>{fmtDate(task.created_at)}</span>
                  {task.completed_at && <span>{fmtDate(task.completed_at)}</span>}
                </div>
              </div>
            );
          })}
        </div>

        {/* Task detail */}
        {selectedTask && (
          <div style={{ background: '#fff', borderRadius: 14, padding: 20, border: '1px solid #ece8e0', position: 'sticky', top: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <h3 style={{ margin: 0, fontSize: 18, fontWeight: 700, color: '#1a1a2e' }}>Task #{selectedTask.id}</h3>
              <button onClick={() => setSelectedTask(null)} style={{
                background: 'none', border: 'none', fontSize: 20, cursor: 'pointer', color: '#999',
              }}>x</button>
            </div>

            <div style={{ fontSize: 16, fontWeight: 700, marginBottom: 8 }}>{selectedTask.title}</div>
            <p style={{ fontSize: 13, color: '#666', marginBottom: 16, lineHeight: 1.5 }}>{selectedTask.description}</p>

            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8, marginBottom: 16 }}>
              {[
                ['Status', STATUS_COLORS[selectedTask.status]?.label || selectedTask.status],
                ['Desk', selectedTask.desk],
                ['Priority', priorityLabel(selectedTask.priority).text],
                ['Source', selectedTask.source],
                ['Created', fmtDate(selectedTask.created_at)],
                ['Started', fmtDate(selectedTask.started_at)],
                ['Completed', fmtDate(selectedTask.completed_at)],
                ['Retries', `${selectedTask.retry_count}`],
              ].map(([label, val]) => (
                <div key={label as string}>
                  <div style={{ fontSize: 10, fontWeight: 600, color: '#999', textTransform: 'uppercase' }}>{label}</div>
                  <div style={{ fontSize: 13, fontWeight: 600, color: '#333' }}>{val}</div>
                </div>
              ))}
            </div>

            {selectedTask.result && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#16a34a', textTransform: 'uppercase', marginBottom: 4 }}>Result</div>
                <pre style={{
                  fontSize: 12, background: '#f8f6f2', padding: 12, borderRadius: 8,
                  whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 200, overflow: 'auto',
                  border: '1px solid #ece8e0', margin: 0,
                }}>{selectedTask.result}</pre>
              </div>
            )}

            {selectedTask.error && (
              <div style={{ marginBottom: 12 }}>
                <div style={{ fontSize: 11, fontWeight: 600, color: '#dc2626', textTransform: 'uppercase', marginBottom: 4 }}>Error</div>
                <pre style={{
                  fontSize: 12, background: '#fef2f2', padding: 12, borderRadius: 8,
                  whiteSpace: 'pre-wrap', wordBreak: 'break-word', maxHeight: 150, overflow: 'auto',
                  border: '1px solid #fecaca', margin: 0,
                }}>{selectedTask.error}</pre>
              </div>
            )}

            {selectedTask.commit_hash && (
              <div style={{ fontSize: 12, color: '#666', marginBottom: 8 }}>
                Commit: <code style={{ background: '#f3f4f6', padding: '2px 6px', borderRadius: 4 }}>{selectedTask.commit_hash.slice(0, 8)}</code>
              </div>
            )}

            {/* Action buttons */}
            <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', marginTop: 12 }}>
              {selectedTask.status === 'failed' && (
                <button onClick={() => taskAction(selectedTask.id, 'retry')} style={{
                  ...btnBase, background: '#f59e0b', color: '#fff', flex: 1,
                }}>Retry</button>
              )}
              {selectedTask.status === 'paused' && (
                <>
                  <button onClick={() => taskAction(selectedTask.id, 'approve')} style={{
                    ...btnBase, background: '#16a34a', color: '#fff', flex: 1,
                  }}>Approve</button>
                  <button onClick={() => taskAction(selectedTask.id, 'reject')} style={{
                    ...btnBase, background: '#dc2626', color: '#fff', flex: 1,
                  }}>Reject</button>
                </>
              )}
              {['queued', 'running'].includes(selectedTask.status) && (
                <button onClick={() => taskAction(selectedTask.id, 'cancel')} style={{
                  ...btnBase, background: '#6b7280', color: '#fff', flex: 1,
                }}>Cancel</button>
              )}
            </div>
          </div>
        )}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 100% { opacity: 1; }
          50% { opacity: 0.5; }
        }
        @media (max-width: 768px) {
          div[style*="grid-template-columns: 1fr 1fr"] {
            grid-template-columns: 1fr !important;
          }
        }
      `}</style>
    </div>
  );
}
