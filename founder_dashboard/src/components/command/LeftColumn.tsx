'use client';
import { ChatSession } from '@/lib/types';
import {
  MessageSquare, Scissors, LayoutGrid, BookOpen, FolderOpen, Settings,
  Plus, ChevronDown, ChevronRight, Trash2, Pencil, Check, X,
  PanelLeftClose, PanelLeft, History,
} from 'lucide-react';
import { useState } from 'react';

type View = 'chat' | 'workroom' | 'desks' | 'research' | 'files' | 'settings';

const NAV_ITEMS: { id: View; label: string; icon: typeof MessageSquare; color: string }[] = [
  { id: 'chat',     label: 'MAX Chat',  icon: MessageSquare, color: 'var(--cyan)' },
  { id: 'workroom', label: 'Workroom',  icon: Scissors,      color: 'var(--fuchsia)' },
  { id: 'desks',    label: 'Desks',     icon: LayoutGrid,    color: 'var(--gold)' },
  { id: 'research', label: 'Research',  icon: BookOpen,      color: '#f59e0b' },
  { id: 'files',    label: 'Files',     icon: FolderOpen,    color: 'var(--purple)' },
  { id: 'settings', label: 'Settings',  icon: Settings,      color: 'var(--text-secondary)' },
];

interface Props {
  activeView: View;
  onChangeView: (view: View) => void;
  conversations: ChatSession[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onDeleteConversation: (id: string) => void;
  onRenameConversation: (id: string, title: string) => void;
  collapsed?: boolean;
  onToggleCollapse?: () => void;
}

export default function LeftColumn({
  activeView, onChangeView,
  conversations, activeConversationId, onSelectConversation, onNewChat,
  onDeleteConversation, onRenameConversation,
  collapsed = false, onToggleCollapse,
}: Props) {
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
        className="sidebar-collapsed flex flex-col items-center py-3 gap-0.5 shrink-0"
        style={{
          background: 'var(--glass-bg-solid)',
          borderRight: '1px solid var(--glass-border)',
          backdropFilter: 'blur(24px)',
        }}
      >
        <button
          onClick={onToggleCollapse}
          className="w-10 h-10 rounded-xl flex items-center justify-center transition mb-1"
          style={{ color: 'var(--text-secondary)' }}
          onMouseEnter={e => { e.currentTarget.style.background = 'rgba(255,255,255,0.04)'; e.currentTarget.style.color = 'var(--cyan)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
          title="Expand sidebar"
        >
          <PanelLeft className="w-5 h-5" />
        </button>

        <div className="w-8 h-px mb-1" style={{ background: 'var(--glass-border)' }} />

        {NAV_ITEMS.map(item => {
          const active = activeView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onChangeView(item.id)}
              className="w-10 h-10 rounded-xl flex items-center justify-center transition"
              style={{
                color: item.color,
                background: active ? `${item.color}15` : 'transparent',
                borderLeft: active ? `2px solid ${item.color}` : '2px solid transparent',
              }}
              onMouseEnter={e => { if (!active) e.currentTarget.style.background = `${item.color}10`; }}
              onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
              title={item.label}
            >
              <item.icon className="w-5 h-5" />
            </button>
          );
        })}

        <div className="w-8 h-px my-1" style={{ background: 'var(--glass-border)' }} />

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

        {/* Spacer */}
        <div className="flex-1" />

        {/* History badge */}
        {conversations.length > 0 && (
          <button
            onClick={() => { onToggleCollapse?.(); }}
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
      {/* Header */}
      <div className="shrink-0 px-3 py-2.5 flex items-center justify-between" style={{ borderBottom: '1px solid var(--glass-border)' }}>
        <span className="text-xs font-semibold tracking-wider" style={{ color: 'var(--gold)' }}>EMPIRE</span>
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

      {/* Navigation */}
      <div className="shrink-0 px-2 py-2 space-y-0.5">
        {NAV_ITEMS.map(item => {
          const active = activeView === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onChangeView(item.id)}
              className="sidebar-icon-btn w-full flex items-center gap-3 px-3 py-2 rounded-lg transition"
              style={{
                background: active ? `${item.color}12` : 'transparent',
                borderLeft: active ? `2px solid ${item.color}` : '2px solid transparent',
              }}
              onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
              onMouseLeave={e => { if (!active) e.currentTarget.style.background = active ? `${item.color}12` : 'transparent'; }}
            >
              <item.icon className="w-4.5 h-4.5 shrink-0" style={{ color: item.color }} />
              <span className="text-[12px] font-medium" style={{ color: active ? item.color : 'var(--text-primary)' }}>{item.label}</span>
            </button>
          );
        })}
      </div>

      <div className="w-full h-px" style={{ background: 'var(--glass-border)' }} />

      {/* New Chat button */}
      <div className="shrink-0 px-2 py-2">
        <button
          onClick={onNewChat}
          className="w-full flex items-center gap-3 px-3 py-2 rounded-lg transition"
          style={{ color: 'var(--cyan)' }}
          onMouseEnter={e => { e.currentTarget.style.background = 'var(--cyan-pale)'; }}
          onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
        >
          <Plus className="w-4.5 h-4.5 shrink-0" />
          <span className="text-[12px] font-medium">New Chat</span>
        </button>
      </div>

      {/* Conversations */}
      <div className="flex-1 min-h-0 overflow-hidden flex flex-col" style={{ borderTop: '1px solid var(--glass-border)' }}>
        <div className="px-3 py-2">
          <span className="text-[9px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
            Conversations ({conversations.length})
          </span>
        </div>
        <div className="flex-1 overflow-y-auto px-2 pb-2 space-y-0.5">
          {conversations.slice(0, 20).map(c => {
            const active = activeConversationId === c.id;
            return (
              <div
                key={c.id}
                onClick={() => { if (editingId !== c.id) { onSelectConversation(c.id); onChangeView('chat'); } }}
                className="group flex items-center gap-2 px-2 py-1.5 rounded-lg cursor-pointer transition"
                style={{
                  background: active ? 'var(--cyan-pale)' : 'transparent',
                  borderLeft: `2px solid ${active ? 'var(--cyan)' : 'transparent'}`,
                }}
                onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'rgba(255,255,255,0.03)'; }}
                onMouseLeave={e => { if (!active) e.currentTarget.style.background = active ? 'var(--cyan-pale)' : 'transparent'; }}
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
      </div>

      {/* Status bar */}
      <div className="shrink-0 px-3 py-1.5 flex items-center gap-2 text-[9px]" style={{ borderTop: '1px solid var(--glass-border)', color: 'var(--text-muted)' }}>
        <span className="w-1.5 h-1.5 rounded-full" style={{ background: '#22c55e' }} />
        <span>Grok</span>
        <span style={{ color: 'var(--glass-border)' }}>|</span>
        <span>12 desks</span>
      </div>
    </div>
  );
}
