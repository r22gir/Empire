'use client';
import { useState } from 'react';
import { ChevronDown, ChevronRight, PanelRightClose, PanelRightOpen, Bell, BellOff } from 'lucide-react';
import {
  Desk, UploadedFile, MaxTask, Reminder, AINotification,
  ServiceHealth, SystemStats, AIModel,
} from '@/lib/types';
import ModelSelector from './ModelSelector';

/* ── Service definitions (checked via direct port probing) ── */
const SERVICES = [
  { key: 'backend',       label: 'FastAPI Backend', port: 8000, path: '/docs',  icon: '⚡' },
  { key: 'workroomforge', label: 'WorkroomForge',   port: 3001, path: '/',      icon: '🪡' },
  { key: 'luxeforge',     label: 'LuxeForge',       port: 3002, path: '/',      icon: '💎' },
  { key: 'homepage',      label: 'Homepage',        port: 8080, path: '/',      icon: '🏠' },
  { key: 'openclaw',      label: 'OpenClaw AI',     port: 7878, path: '/health',icon: '🧠' },
  { key: 'ollama',        label: 'Ollama',          port: 11434,path: '/',      icon: '🦙' },
] as const;

interface SystemSidebarProps {
  desks: Desk[];
  models: AIModel[];
  selectedModel: string;
  onModelChange: (m: string) => void;
  stats: { total_completed: number; active_tasks: number; pending_tasks: number; total_failed: number };
  files: UploadedFile[];
  tasks: MaxTask[];
  reminders: Reminder[];
  aiNotifications: AINotification[];
  serviceHealth: ServiceHealth;
  systemStats: SystemStats | null;
  backendOnline: boolean;
  onSelectImage: (name: string, category: string) => void;
  onOpenTasks: () => void;
  onAddReminder: (text: string, dueDate: string, priority: 'low' | 'medium' | 'high') => void;
  onToggleReminder: (id: string) => void;
  onDeleteReminder: (id: string) => void;
  onMarkNotifRead: (id: string) => void;
  onDismissNotif: (id: string) => void;
  onRespondNotif: (id: string, action: string) => void;
  onSelectNotif: (n: AINotification) => void;
  onDeleteFile: (category: string, filename: string) => void;
  onOpenFile: (category: string, filename: string) => void;
}

/* ── Sub-components ─────────────────────────────────────── */
function SectionHeader({
  label, count, open, onToggle,
}: { label: string; count?: number; open: boolean; onToggle: () => void }) {
  return (
    <button
      onClick={onToggle}
      className="w-full flex items-center justify-between text-left transition px-1 py-0.5"
    >
      <span className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
        {label}{count !== undefined && ` (${count})`}
      </span>
      {open
        ? <ChevronDown  className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
        : <ChevronRight className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
      }
    </button>
  );
}

function StatBar({ label, value, extra }: { label: string; value: number; extra?: string }) {
  const color = value > 80 ? '#ef4444' : value > 60 ? '#f59e0b' : '#22c55e';
  return (
    <div>
      <div className="flex justify-between text-xs mb-1">
        <span style={{ color: 'var(--text-secondary)' }}>{label}</span>
        <span style={{ color: 'var(--text-primary)' }}>{extra || `${value}%`}</span>
      </div>
      <div className="h-1 rounded-full overflow-hidden" style={{ background: 'var(--elevated)' }}>
        <div className="h-full rounded-full transition-all" style={{ width: `${value}%`, background: color }} />
      </div>
    </div>
  );
}

/* ── Main component ─────────────────────────────────────── */
export default function SystemSidebar(props: SystemSidebarProps) {
  const [collapsed,     setCollapsed]     = useState(false);
  const [showFiles,     setShowFiles]     = useState(false);
  const [showReminders, setShowReminders] = useState(false);
  const [showDesks,     setShowDesks]     = useState(false);
  const [newReminder,   setNewReminder]   = useState({ text: '', dueDate: '', priority: 'medium' as 'low'|'medium'|'high' });

  const formatSize = (b: number) =>
    b > 1_048_576 ? (b / 1_048_576).toFixed(1) + ' MB' :
    b > 1_024     ? (b / 1_024).toFixed(1)     + ' KB' : b + ' B';

  const priorityColor = (p: string) =>
    p === 'high' ? '#ef4444' : p === 'medium' ? '#f59e0b' : '#22c55e';

  const deskDot = (s: string) =>
    s === 'idle' ? '#22c55e' : s === 'busy' ? '#f59e0b' : 'var(--text-muted)';

  /* ── Collapsed strip ─────────────────────────────────── */
  if (collapsed) {
    return (
      <div
        className="w-10 flex flex-col items-center py-3 shrink-0"
        style={{ background: 'var(--void)', borderLeft: '1px solid var(--border)' }}
      >
        <button
          onClick={() => setCollapsed(false)}
          className="p-2 rounded-lg transition"
          style={{ color: 'var(--text-muted)' }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--gold)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
          title="Expand panel"
        >
          <PanelRightOpen className="w-4 h-4" />
        </button>
        {/* Notification dot */}
        {props.aiNotifications.filter(n => !n.read).length > 0 && (
          <div className="w-2 h-2 rounded-full mt-2" style={{ background: 'var(--gold)' }} />
        )}
      </div>
    );
  }

  /* ── Expanded panel ──────────────────────────────────── */
  return (
    <div
      className="w-[260px] flex flex-col shrink-0 overflow-hidden"
      style={{ background: 'var(--void)', borderLeft: '1px solid var(--border)' }}
    >

      {/* ══ Header ══════════════════════════════════════════ */}
      <div
        className="flex items-center justify-between px-3 py-2.5 shrink-0"
        style={{ borderBottom: '1px solid var(--border)' }}
      >
        <div>
          <p className="text-xs font-bold text-gold-shimmer tracking-wide">Empire System</p>
          <div className="flex items-center gap-1.5 mt-1">
            <span className={props.serviceHealth.backend ? 'dot-online' : 'dot-offline'} />
            <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>
              {props.serviceHealth.backend ? 'Backend online' : 'Backend offline'}
            </span>
          </div>
        </div>
        <button
          onClick={() => setCollapsed(true)}
          className="p-1.5 rounded-lg transition"
          style={{ color: 'var(--text-muted)' }}
          onMouseEnter={e => (e.currentTarget.style.color = 'var(--gold)')}
          onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
          title="Collapse"
        >
          <PanelRightClose className="w-4 h-4" />
        </button>
      </div>

      {/* ══ Scrollable body ══════════════════════════════════ */}
      <div className="flex-1 overflow-y-auto">

        {/* ── Model selector ─────────────────────────────── */}
        <div className="px-3 pt-3 pb-2.5" style={{ borderBottom: '1px solid var(--border)' }}>
          <ModelSelector models={props.models} selectedModel={props.selectedModel} onSelect={props.onModelChange} />
        </div>

        {/* ── SERVICE STATUS ──────────────────────────────── */}
        <div className="px-3 py-2.5" style={{ borderBottom: '1px solid var(--border)' }}>
          <p className="text-[10px] font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
            Services
          </p>
          <div className="space-y-1.5">
            {SERVICES.map(svc => {
              const online = props.serviceHealth[svc.key as keyof ServiceHealth];
              return (
                <div key={svc.key} className="flex items-center gap-2">
                  <span className="text-sm">{svc.icon}</span>
                  <span
                    className="flex-1 text-xs truncate"
                    style={{ color: online ? 'var(--text-primary)' : 'var(--text-muted)' }}
                  >
                    {svc.label}
                  </span>
                  <span
                    className="text-[10px] font-mono tabular-nums"
                    style={{ color: 'var(--text-muted)' }}
                  >
                    :{svc.port}
                  </span>
                  <span className={online ? 'dot-online' : 'dot-offline'} />
                  {online && (
                    <a
                      href={`http://localhost:${svc.port}${svc.path}`}
                      target="_blank"
                      rel="noreferrer"
                      className="text-[10px] px-1.5 py-0.5 rounded transition"
                      style={{
                        color:      'var(--gold)',
                        background: 'var(--gold-pale)',
                        border:     '1px solid var(--gold-border)',
                      }}
                    >
                      Open
                    </a>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* ── Task stats ─────────────────────────────────── */}
        <div className="px-3 py-2.5" style={{ borderBottom: '1px solid var(--border)' }}>
          <button onClick={props.onOpenTasks} className="w-full grid grid-cols-2 gap-2 hover:opacity-80 transition-opacity">
            {[
              { label: 'Done',   val: props.stats.total_completed, color: '#22c55e' },
              { label: 'Active', val: props.stats.active_tasks,    color: '#f59e0b' },
            ].map(s => (
              <div
                key={s.label}
                className="rounded-xl p-2.5 text-center"
                style={{ background: 'var(--surface)', border: '1px solid var(--border)' }}
              >
                <p className="text-[10px] uppercase tracking-wider" style={{ color: 'var(--text-muted)' }}>{s.label}</p>
                <p className="text-xl font-bold mt-0.5" style={{ color: s.color }}>{s.val}</p>
              </div>
            ))}
          </button>
          <p className="text-center text-[10px] mt-1.5" style={{ color: 'var(--text-muted)' }}>Click to manage tasks</p>
        </div>

        {/* ── System stats ───────────────────────────────── */}
        {props.systemStats && (
          <div className="px-3 py-2.5" style={{ borderBottom: '1px solid var(--border)' }}>
            <p className="text-[10px] font-semibold uppercase tracking-widest mb-2.5" style={{ color: 'var(--text-muted)' }}>
              System
            </p>
            <div className="space-y-2.5">
              <StatBar label="CPU" value={props.systemStats.cpu.percent} />
              <StatBar
                label="RAM"
                value={props.systemStats.memory.percent}
                extra={`${props.systemStats.memory.used_gb}/${props.systemStats.memory.total_gb} GB`}
              />
              <StatBar
                label="Disk"
                value={props.systemStats.disk.percent}
                extra={`${props.systemStats.disk.used_gb}/${props.systemStats.disk.total_gb} GB`}
              />
              {/* Temps */}
              {Object.entries(props.systemStats.temperatures).slice(0, 2).map(([name, sensors]) =>
                sensors.slice(0, 1).map((s, i) => (
                  <div key={name + i} className="flex justify-between text-xs">
                    <span style={{ color: 'var(--text-secondary)' }}>{s.label || name}</span>
                    <span style={{ color: s.current > 80 ? '#ef4444' : s.current > 65 ? '#f59e0b' : '#22c55e' }}>
                      {s.current.toFixed(0)}°C
                    </span>
                  </div>
                ))
              )}
            </div>
          </div>
        )}

        {/* ── AI Notifications ───────────────────────────── */}
        {props.aiNotifications.filter(n => !n.read).length > 0 && (
          <div className="px-3 py-2.5" style={{ borderBottom: '1px solid var(--border)' }}>
            <div className="flex items-center gap-1.5 mb-2">
              <Bell className="w-3 h-3" style={{ color: 'var(--gold)' }} />
              <span className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
                Alerts ({props.aiNotifications.filter(n => !n.read).length})
              </span>
            </div>
            <div className="space-y-1">
              {props.aiNotifications.filter(n => !n.read).slice(0, 4).map(n => (
                <button
                  key={n.id}
                  onClick={() => props.onSelectNotif(n)}
                  className="w-full text-left flex items-center gap-2 px-2 py-1.5 rounded-lg transition"
                  style={{
                    background: n.priority === 'high' ? 'rgba(239,68,68,0.08)' : 'var(--gold-pale)',
                    border:     n.priority === 'high' ? '1px solid rgba(239,68,68,0.2)' : '1px solid var(--gold-border)',
                  }}
                >
                  <span className="text-sm">{n.source === 'MAX' ? '🧠' : n.source === 'System' ? '⚙️' : '💰'}</span>
                  <span className="flex-1 text-xs truncate" style={{ color: 'var(--text-primary)' }}>{n.title}</span>
                  {n.priority === 'high' && (
                    <span className="w-1.5 h-1.5 rounded-full animate-pulse" style={{ background: '#ef4444' }} />
                  )}
                </button>
              ))}
            </div>
          </div>
        )}

        {/* ── Reminders ──────────────────────────────────── */}
        <div className="px-3 py-2.5" style={{ borderBottom: '1px solid var(--border)' }}>
          <SectionHeader
            label="Reminders"
            count={props.reminders.filter(r => !r.completed).length}
            open={showReminders}
            onToggle={() => setShowReminders(!showReminders)}
          />
          {showReminders && (
            <div className="mt-2 space-y-2">
              {/* Add form */}
              <div className="flex gap-1">
                <input
                  type="text"
                  value={newReminder.text}
                  onChange={e => setNewReminder({ ...newReminder, text: e.target.value })}
                  placeholder="Add reminder…"
                  className="flex-1 rounded-lg px-2.5 py-1.5 text-xs outline-none"
                  style={{ background: 'var(--surface)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                  onFocus={e => (e.currentTarget.style.borderColor = 'var(--gold-border)')}
                  onBlur={e => (e.currentTarget.style.borderColor = 'var(--border)')}
                  onKeyDown={e => {
                    if (e.key === 'Enter' && newReminder.text.trim()) {
                      props.onAddReminder(newReminder.text, newReminder.dueDate, newReminder.priority);
                      setNewReminder({ text: '', dueDate: '', priority: 'medium' });
                    }
                  }}
                />
                <button
                  onClick={() => {
                    if (newReminder.text.trim()) {
                      props.onAddReminder(newReminder.text, newReminder.dueDate, newReminder.priority);
                      setNewReminder({ text: '', dueDate: '', priority: 'medium' });
                    }
                  }}
                  className="px-2.5 rounded-lg text-xs font-semibold transition"
                  style={{ background: 'var(--gold)', color: '#0a0a0a' }}
                >
                  +
                </button>
              </div>
              {/* List */}
              <div className="max-h-32 overflow-y-auto space-y-1">
                {props.reminders
                  .slice()
                  .sort((a, b) => Number(a.completed) - Number(b.completed))
                  .map(r => (
                    <div
                      key={r.id}
                      className="flex items-center gap-2 p-1.5 rounded-lg group"
                      style={{
                        background: 'var(--surface)',
                        opacity: r.completed ? 0.45 : 1,
                      }}
                    >
                      <input
                        type="checkbox"
                        checked={r.completed}
                        onChange={() => props.onToggleReminder(r.id)}
                        className="rounded shrink-0 cursor-pointer"
                        style={{ accentColor: 'var(--gold)' }}
                      />
                      <span className={`flex-1 text-xs ${r.completed ? 'line-through' : ''}`} style={{ color: 'var(--text-primary)' }}>
                        {r.text}
                      </span>
                      <span className="w-1.5 h-1.5 rounded-full shrink-0" style={{ background: priorityColor(r.priority) }} />
                      <button
                        onClick={() => props.onDeleteReminder(r.id)}
                        className="opacity-0 group-hover:opacity-100 text-sm leading-none transition"
                        style={{ color: '#ef4444' }}
                      >
                        ×
                      </button>
                    </div>
                  ))}
                {props.reminders.length === 0 && (
                  <p className="text-xs text-center py-2" style={{ color: 'var(--text-muted)' }}>No reminders</p>
                )}
              </div>
            </div>
          )}
        </div>

        {/* ── Files ──────────────────────────────────────── */}
        <div className="px-3 py-2.5" style={{ borderBottom: '1px solid var(--border)' }}>
          <SectionHeader
            label="Files"
            count={props.files.length}
            open={showFiles}
            onToggle={() => setShowFiles(!showFiles)}
          />
          {showFiles && (
            <div className="mt-2 max-h-36 overflow-y-auto space-y-0.5">
              {props.files.map((f, i) => (
                <div
                  key={i}
                  className="flex items-center gap-1.5 p-1.5 rounded-lg group transition"
                  style={{ cursor: 'pointer' }}
                  onMouseEnter={e => (e.currentTarget.style.background = 'var(--surface)')}
                  onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
                >
                  <span
                    className="flex-1 text-xs truncate"
                    style={{ color: 'var(--text-primary)' }}
                    onClick={() => props.onOpenFile(f.category, f.name)}
                  >
                    {f.name}
                  </span>
                  {f.category === 'images' && (
                    <button
                      onClick={() => props.onSelectImage(f.name, f.category)}
                      className="text-sm opacity-70 hover:opacity-100 transition"
                      title="Analyze"
                    >
                      📐
                    </button>
                  )}
                  <button
                    onClick={() => props.onDeleteFile(f.category, f.name)}
                    className="opacity-0 group-hover:opacity-100 text-sm leading-none transition"
                    style={{ color: '#ef4444' }}
                  >
                    ×
                  </button>
                </div>
              ))}
              {props.files.length === 0 && (
                <p className="text-xs text-center py-2" style={{ color: 'var(--text-muted)' }}>No uploaded files</p>
              )}
            </div>
          )}
        </div>

        {/* ── AI Desks ───────────────────────────────────── */}
        <div className="px-3 py-2.5">
          <SectionHeader
            label="AI Desks"
            count={props.desks.length}
            open={showDesks}
            onToggle={() => setShowDesks(!showDesks)}
          />
          {showDesks && (
            <div className="mt-2 space-y-1">
              {props.desks.map(desk => (
                <div key={desk.id} className="flex items-center gap-2 px-1.5 py-1.5 rounded-lg">
                  <div className="relative shrink-0">
                    <div
                      className="w-7 h-7 rounded-lg flex items-center justify-center text-xs font-bold"
                      style={{ background: 'var(--raised)', color: 'var(--gold)', border: '1px solid var(--border)' }}
                    >
                      {desk.name.charAt(0)}
                    </div>
                    <div
                      className="absolute -bottom-0.5 -right-0.5 w-2 h-2 rounded-full"
                      style={{ background: deskDot(desk.status), border: '1.5px solid var(--void)' }}
                    />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-xs font-medium truncate" style={{ color: 'var(--text-primary)' }}>{desk.name}</p>
                    <p className="text-[10px] truncate" style={{ color: 'var(--text-muted)' }}>{desk.description}</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

      </div>
    </div>
  );
}
