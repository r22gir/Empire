'use client';
import { useState } from 'react';
import { Plus, X, Circle, Clock, CheckCircle2, AlertTriangle, WifiOff, Loader2 } from 'lucide-react';
import { useDeskData } from '@/hooks/useDeskData';
import type { Task } from '@/lib/types';
import type { DeskId } from '@/lib/deskData';

const PRIORITY_COLORS: Record<string, string> = {
  urgent: '#ef4444',
  high: '#f97316',
  normal: 'var(--gold)',
  low: '#6b7280',
};

const STATUS_ICONS: Record<string, typeof Circle> = {
  todo: Circle,
  in_progress: Clock,
  waiting: AlertTriangle,
  done: CheckCircle2,
};

const NEXT_STATUS: Record<string, string> = {
  todo: 'in_progress',
  in_progress: 'done',
  waiting: 'in_progress',
  done: 'todo',
};

interface TaskListProps {
  desk: DeskId;
  compact?: boolean;
  maxHeight?: string;
}

export default function TaskList({ desk, compact = false, maxHeight }: TaskListProps) {
  const { tasks, isOnline, isLoading, createTask, updateTask, deleteTask } = useDeskData(desk);
  const [showAdd, setShowAdd] = useState(false);
  const [newTitle, setNewTitle] = useState('');
  const [newPriority, setNewPriority] = useState<string>('normal');
  const [newDueDate, setNewDueDate] = useState('');

  const activeTasks = tasks.filter(t => t.status !== 'cancelled');
  const today = new Date().toISOString().split('T')[0];

  const handleAdd = async () => {
    if (!newTitle.trim()) return;
    await createTask({
      title: newTitle.trim(),
      priority: newPriority,
      due_date: newDueDate || undefined,
    });
    setNewTitle('');
    setNewPriority('normal');
    setNewDueDate('');
    setShowAdd(false);
  };

  const cycleStatus = (task: Task) => {
    const next = NEXT_STATUS[task.status] || 'todo';
    updateTask(task.id, { status: next });
  };

  return (
    <div
      className="rounded-xl flex flex-col"
      style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2.5 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold" style={{ color: 'var(--gold)' }}>Tasks</span>
          <span className="text-[10px] px-1.5 py-0.5 rounded-full font-mono" style={{ background: 'var(--raised)', color: 'var(--text-muted)' }}>
            {activeTasks.length}
          </span>
        </div>
        <div className="flex items-center gap-2">
          {!isOnline && (
            <span className="flex items-center gap-1 text-[10px]" style={{ color: '#f59e0b' }}>
              <WifiOff className="w-3 h-3" /> Offline
            </span>
          )}
          {isOnline && (
            <button
              onClick={() => setShowAdd(!showAdd)}
              className="flex items-center gap-1 px-2 py-1 rounded-lg text-[10px] font-medium transition"
              style={{
                background: showAdd ? 'var(--gold-pale)' : 'transparent',
                color: showAdd ? 'var(--gold)' : 'var(--text-muted)',
                border: '1px solid var(--border)',
              }}
            >
              {showAdd ? <X className="w-3 h-3" /> : <Plus className="w-3 h-3" />}
              {showAdd ? 'Cancel' : 'Add'}
            </button>
          )}
        </div>
      </div>

      {/* Add form */}
      {showAdd && (
        <div className="px-4 py-3 space-y-2 shrink-0" style={{ borderBottom: '1px solid var(--border)' }}>
          <input
            type="text"
            value={newTitle}
            onChange={e => setNewTitle(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') handleAdd(); }}
            placeholder="Task title..."
            autoFocus
            className="w-full px-3 py-1.5 rounded-lg text-xs outline-none"
            style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
          />
          <div className="flex items-center gap-2">
            <div className="flex gap-1">
              {(['urgent', 'high', 'normal', 'low'] as const).map(p => (
                <button
                  key={p}
                  onClick={() => setNewPriority(p)}
                  className="px-2 py-0.5 rounded text-[10px] font-medium capitalize transition"
                  style={{
                    background: newPriority === p ? PRIORITY_COLORS[p] + '20' : 'transparent',
                    color: newPriority === p ? PRIORITY_COLORS[p] : 'var(--text-muted)',
                    border: newPriority === p ? `1px solid ${PRIORITY_COLORS[p]}40` : '1px solid transparent',
                  }}
                >
                  {p}
                </button>
              ))}
            </div>
            <input
              type="date"
              value={newDueDate}
              onChange={e => setNewDueDate(e.target.value)}
              className="px-2 py-0.5 rounded text-[10px] outline-none ml-auto"
              style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-muted)' }}
            />
            <button
              onClick={handleAdd}
              disabled={!newTitle.trim()}
              className="px-3 py-1 rounded-lg text-[10px] font-semibold transition"
              style={{
                background: newTitle.trim() ? 'var(--gold)' : 'var(--raised)',
                color: newTitle.trim() ? '#000' : 'var(--text-muted)',
              }}
            >
              Add
            </button>
          </div>
        </div>
      )}

      {/* Task list */}
      <div className="flex-1 overflow-y-auto" style={{ maxHeight: maxHeight || (compact ? '240px' : '360px') }}>
        {isLoading ? (
          <div className="flex items-center justify-center py-8">
            <Loader2 className="w-4 h-4 animate-spin" style={{ color: 'var(--text-muted)' }} />
          </div>
        ) : activeTasks.length === 0 ? (
          <p className="text-[10px] text-center py-6" style={{ color: 'var(--text-muted)' }}>
            No tasks for this desk
          </p>
        ) : (
          <div className="divide-y" style={{ borderColor: 'var(--border)' }}>
            {activeTasks.map(task => {
              const StatusIcon = STATUS_ICONS[task.status] || Circle;
              const isOverdue = task.due_date && task.due_date < today && task.status !== 'done';
              return (
                <div
                  key={task.id}
                  className="flex items-center gap-2.5 px-4 py-2 transition group"
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--hover)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  {/* Status toggle */}
                  <button onClick={() => cycleStatus(task)} className="shrink-0">
                    <StatusIcon
                      className="w-4 h-4 transition"
                      style={{
                        color: task.status === 'done' ? '#22c55e' : task.status === 'in_progress' ? 'var(--gold)' : 'var(--text-muted)',
                      }}
                    />
                  </button>

                  {/* Priority dot */}
                  <span
                    className="w-1.5 h-1.5 rounded-full shrink-0"
                    style={{ background: PRIORITY_COLORS[task.priority] || 'var(--text-muted)' }}
                  />

                  {/* Title */}
                  <span
                    className="flex-1 text-xs truncate"
                    style={{
                      color: task.status === 'done' ? 'var(--text-muted)' : 'var(--text-primary)',
                      textDecoration: task.status === 'done' ? 'line-through' : 'none',
                    }}
                  >
                    {task.title}
                  </span>

                  {/* Due date */}
                  {task.due_date && !compact && (
                    <span
                      className="text-[10px] font-mono shrink-0"
                      style={{ color: isOverdue ? '#ef4444' : 'var(--text-muted)' }}
                    >
                      {task.due_date}
                    </span>
                  )}

                  {/* Assignee */}
                  {task.assigned_to && !compact && (
                    <span className="text-[10px] shrink-0" style={{ color: 'var(--text-muted)' }}>
                      {task.assigned_to}
                    </span>
                  )}

                  {/* Delete */}
                  <button
                    onClick={() => deleteTask(task.id)}
                    className="opacity-0 group-hover:opacity-100 transition shrink-0"
                  >
                    <X className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
                  </button>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
