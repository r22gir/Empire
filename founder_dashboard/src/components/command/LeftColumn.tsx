'use client';
import { ChatSession } from '@/lib/types';
import {
  LayoutGrid, Plus, ChevronDown, ChevronRight, MessageSquare, Trash2,
  Pencil, Check, X, Rocket, PanelLeftClose, PanelLeft, Zap, ListTodo,
  FileText, CalendarDays, History, Receipt
} from 'lucide-react';
import { useState } from 'react';

const SUGGESTIONS = [
  { label: 'Health', icon: Zap,          prompt: 'Run a full system health check — CPU, RAM, disk, and all services.' },
  { label: 'Tasks',  icon: ListTodo,     prompt: 'Show me all open and in-progress tasks across all desks.' },
  { label: 'Quote',  icon: FileText,     prompt: 'Help me create a new quote for a client in WorkroomForge.' },
  { label: 'Today',  icon: CalendarDays, prompt: 'Give me a summary of today\'s activity across all desks.' },
];

interface Props {
  onOpenDeskGrid: () => void;
  conversations: ChatSession[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onDeleteConversation: (id: string) => void;
  onRenameConversation: (id: string, title: string) => void;
  onSuggest: (prompt: string) => void;
  onOpenWorkspaces?: () => void;
  onOpenWorkspace?: (id: string) => void;
  onQuickQuote?: () => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export default function LeftColumn({
  onOpenDeskGrid,
  conversations, activeConversationId, onSelectConversation, onNewChat,
  onDeleteConversation, onRenameConversation, onSuggest,
  onOpenWorkspaces, onOpenWorkspace, onQuickQuote,
  collapsed = false, onToggleCollapse,
}: Props) {
  const [showConvos, setShowConvos] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const startEdit = (id: string, title: string) => { setEditingId(id); setEditTitle(title); };
  const saveEdit = (id: string) => { if (editTitle.trim()) onRenameConversation(id, editTitle.trim()); setEditingId(null); };

  const formatTime = (iso: string) => {
    const d = new Date(iso);
    const diff = Date.now() - d.getTime();
    if (diff < 86_400_000) return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (diff < 604_800_000) return d.toLocaleDateString([], { weekday: 'short' });
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  /* ── Collapsed icon sidebar ─────────────────────────────── */
  if (collapsed) {
    return (
      <div
        className="sidebar-collapsed flex flex-col items-center py-3 gap-1 shrink-0"
        style={{
          background: 'var(--glass-bg-solid)',
          borderRight: '1px solid var(--glass-border)',
          backdropFilter: 'blur(24px)',
        }}
      >
        {/* Expand toggle */}
        <button
          onClick={onToggleCollapse}
          className="w-10 h-10 rounded-xl flex items-center justify-center transition mb-2"
          style={{ color: 'var(--text-secondary)' }}
          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = 'var(--cyan)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
          title="Expand sidebar"
        >
          <PanelLeft className="w-5 h-5" />
        </button>

        <div className="w-8 h-px mb-1" style={{ background: 'var(--glass-border)' }} />

        {/* Desks */}
        <button
          onClick={onOpenDeskGrid}
          className="w-10 h-10 rounded-xl flex items-center justify-center transition"
          style={{ color: 'var(--gold)' }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--gold-pale)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          title="Desks"
        >
          <LayoutGrid className="w-5 h-5" />
        </button>

        {/* Apps */}
        {onOpenWorkspaces && (
          <button
            onClick={onOpenWorkspaces}
            className="w-10 h-10 rounded-xl flex items-center justify-center transition"
            style={{ color: 'var(--purple)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'var(--purple-pale)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
            title="Apps"
          >
            <Rocket className="w-5 h-5" />
          </button>
        )}

        {/* New chat */}
        <button
          onClick={onNewChat}
          className="w-10 h-10 rounded-xl flex items-center justify-center transition"
          style={{ color: 'var(--cyan)' }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--cyan-pale)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          title="New chat"
        >
          <Plus className="w-5 h-5" />
        </button>

        {/* Quick Quote */}
        {onQuickQuote && (
          <button
            onClick={onQuickQuote}
            className="w-10 h-10 rounded-xl flex items-center justify-center transition"
            style={{ color: 'var(--fuchsia)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(236,72,153,0.1)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
            title="Quick Quote"
          >
            <Receipt className="w-5 h-5" />
          </button>
        )}

        <div className="w-8 h-px my-1" style={{ background: 'var(--glass-border)' }} />

        {/* Quick action icons */}
        {SUGGESTIONS.map(s => (
          <button
            key={s.label}
            onClick={() => onSuggest(s.prompt)}
            className="w-10 h-10 rounded-xl flex items-center justify-center transition"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}
            title={s.label}
          >
            <s.icon className="w-4.5 h-4.5" />
          </button>
        ))}

        {/* Spacer */}
        <div className="flex-1" />

        {/* History */}
        {conversations.length > 0 && (
          <button
            onClick={() => { onToggleCollapse?.(); setTimeout(() => setShowConvos(true), 300); }}
            className="w-10 h-10 rounded-xl flex items-center justify-center transition relative"
            style={{ color: 'var(--text-muted)' }}
            onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
            onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-muted)'; }}
            title={`${conversations.length} conversations`}
          >
            <History className="w-4.5 h-4.5" />
            <span
              className="absolute -top-0.5 -right-0.5 w-4 h-4 rounded-full flex items-center justify-center text-[8px] font-bold"
              style={{ background: 'var(--cyan)', color: '#0a0a0a' }}
            >
              {conversations.length > 9 ? '9+' : conversations.length}
            </span>
          </button>
        )}
      </div>
    );
  }

  /* ── Expanded full sidebar ──────────────────────────────── */
  return (
    <div
      className="sidebar-expanded flex flex-col min-h-0 overflow-hidden shrink-0"
      style={{
        background: 'var(--glass-bg-solid)',
        borderRight: '1px solid var(--glass-border)',
        backdropFilter: 'blur(24px)',
      }}
    >
      {/* Sidebar header */}
      <div className="shrink-0 px-3 py-2.5 flex items-center justify-between" style={{ borderBottom: '1px solid var(--glass-border)' }}>
        <span className="text-xs font-semibold tracking-wider" style={{ color: 'var(--gold)' }}>COMMAND</span>
        <button
          onClick={onToggleCollapse}
          className="w-7 h-7 rounded-lg flex items-center justify-center transition"
          style={{ color: 'var(--text-secondary)' }}
          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
          title="Collapse sidebar"
        >
          <PanelLeftClose className="w-4 h-4" />
        </button>
      </div>

      {/* Navigation buttons */}
      <div className="shrink-0 px-2 py-2 space-y-0.5">
        <button onClick={onOpenDeskGrid} className="sidebar-icon-btn">
          <LayoutGrid className="icon" style={{ color: 'var(--gold)' }} />
          <span className="label" style={{ color: 'var(--gold)' }}>Desks</span>
        </button>
        {onOpenWorkspaces && (
          <button onClick={onOpenWorkspaces} className="sidebar-icon-btn">
            <Rocket className="icon" style={{ color: 'var(--purple)' }} />
            <span className="label" style={{ color: 'var(--purple)' }}>Apps</span>
          </button>
        )}
        <button onClick={onNewChat} className="sidebar-icon-btn">
          <Plus className="icon" style={{ color: 'var(--cyan)' }} />
          <span className="label" style={{ color: 'var(--cyan)' }}>New Chat</span>
        </button>
        {onQuickQuote && (
          <button onClick={onQuickQuote} className="sidebar-icon-btn">
            <Receipt className="icon" style={{ color: 'var(--fuchsia)' }} />
            <span className="label" style={{ color: 'var(--fuchsia)' }}>Quick Quote</span>
          </button>
        )}
      </div>

      <div className="w-full h-px" style={{ background: 'var(--glass-border)' }} />

      {/* Quick actions */}
      <div className="shrink-0 px-2 py-2 space-y-0.5">
        <p className="px-3 text-[9px] font-semibold uppercase tracking-widest mb-1" style={{ color: 'var(--text-muted)' }}>Quick Actions</p>
        {SUGGESTIONS.map(s => (
          <button key={s.label} onClick={() => onSuggest(s.prompt)} className="sidebar-icon-btn">
            <s.icon className="icon" />
            <span className="label">{s.label}</span>
          </button>
        ))}
      </div>

      {/* Spacer */}
      <div className="flex-1" />

      {/* Conversations accordion */}
      {conversations.length > 0 && (
        <div className="shrink-0 px-2 pb-2" style={{ borderTop: '1px solid var(--glass-border)' }}>
          <button
            onClick={() => setShowConvos(!showConvos)}
            className="flex items-center gap-2 w-full py-2 px-1"
          >
            {showConvos
              ? <ChevronDown className="w-3 h-3" style={{ color: 'var(--cyan)' }} />
              : <ChevronRight className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
            }
            <History className="w-3.5 h-3.5" style={{ color: showConvos ? 'var(--cyan)' : 'var(--text-muted)' }} />
            <span className="text-[11px] font-medium" style={{ color: showConvos ? 'var(--cyan)' : 'var(--text-muted)' }}>
              {conversations.length} conversation{conversations.length !== 1 ? 's' : ''}
            </span>
          </button>
          {showConvos && (
            <div className="space-y-0.5 max-h-36 overflow-y-auto">
              {conversations.slice(0, 10).map(c => {
                const active = activeConversationId === c.id;
                return (
                  <div
                    key={c.id}
                    onClick={() => { if (editingId !== c.id) onSelectConversation(c.id); }}
                    className="group flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition"
                    style={{
                      background: active ? 'var(--cyan-pale)' : 'transparent',
                      borderLeft: `2px solid ${active ? 'var(--cyan)' : 'transparent'}`,
                    }}
                    onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                    onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
                  >
                    <MessageSquare className="w-3 h-3 shrink-0" style={{ color: active ? 'var(--cyan)' : 'var(--text-muted)' }} />
                    {editingId === c.id ? (
                      <div className="flex items-center gap-1 flex-1">
                        <input
                          value={editTitle}
                          onChange={e => setEditTitle(e.target.value)}
                          onKeyDown={e => { if (e.key === 'Enter') saveEdit(c.id); if (e.key === 'Escape') setEditingId(null); }}
                          className="w-full rounded px-1.5 py-0.5 text-[11px] outline-none"
                          style={{ background: 'var(--raised)', border: '1px solid var(--glass-border)', color: 'var(--text-primary)' }}
                          autoFocus
                          onClick={e => e.stopPropagation()}
                        />
                        <button onClick={e => { e.stopPropagation(); saveEdit(c.id); }} style={{ color: '#22c55e' }}><Check className="w-3 h-3" /></button>
                        <button onClick={e => { e.stopPropagation(); setEditingId(null); }} style={{ color: 'var(--text-secondary)' }}><X className="w-3 h-3" /></button>
                      </div>
                    ) : (
                      <>
                        <span className="flex-1 text-[11px] truncate" style={{ color: active ? 'var(--cyan)' : 'var(--text-primary)' }}>{c.title}</span>
                        <span className="text-[9px] shrink-0" style={{ color: 'var(--text-muted)' }}>{formatTime(c.updated_at)}</span>
                        <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                          <button onClick={e => { e.stopPropagation(); startEdit(c.id, c.title); }} className="p-0.5" style={{ color: 'var(--text-muted)' }}><Pencil className="w-3 h-3" /></button>
                          <button onClick={e => { e.stopPropagation(); if (confirm('Delete?')) onDeleteConversation(c.id); }} className="p-0.5" style={{ color: 'var(--text-muted)' }}><Trash2 className="w-3 h-3" /></button>
                        </div>
                      </>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
