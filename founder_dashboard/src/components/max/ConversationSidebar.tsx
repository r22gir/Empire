'use client';
import { useState } from 'react';
import { ChatSession } from '@/lib/types';
import { DeskId, BUSINESS_DESKS } from '@/lib/deskData';
import { Plus, MessageSquare, Trash2, Pencil, Check, X, LayoutDashboard } from 'lucide-react';

interface ConversationSidebarProps {
  conversations: ChatSession[];
  activeId: string | null;
  onSelect: (id: string) => void;
  onNew: () => void;
  onDelete: (id: string) => void;
  onRename: (id: string, title: string) => void;
  activeDesk: DeskId | null;
  onDeskSelect: (id: DeskId) => void;
  onDeskClose: () => void;
}

const EMPIRE_APPS = [
  { name: 'WorkroomForge', port: 3001, icon: '🪡', live: true },
  { name: 'LuxeForge',     port: 3002, icon: '💎', live: true },
  { name: 'Homepage',      port: 8080, icon: '🏠', live: true },
  { name: 'API Docs',      port: 8000, icon: '⚡', live: true, path: '/docs' },
  { name: 'MarketForge',   port: null, icon: '🛒', live: false },
];

export default function ConversationSidebar({
  conversations, activeId, onSelect, onNew, onDelete, onRename,
  activeDesk, onDeskSelect, onDeskClose,
}: ConversationSidebarProps) {
  const [editingId, setEditingId] = useState<string | null>(null);
  const [editTitle, setEditTitle] = useState('');

  const startEdit = (id: string, title: string) => { setEditingId(id); setEditTitle(title); };
  const saveEdit  = (id: string) => { if (editTitle.trim()) onRename(id, editTitle.trim()); setEditingId(null); };

  const formatTime = (iso: string) => {
    const d    = new Date(iso);
    const diff = Date.now() - d.getTime();
    if (diff < 86_400_000)  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    if (diff < 604_800_000) return d.toLocaleDateString([], { weekday: 'short' });
    return d.toLocaleDateString([], { month: 'short', day: 'numeric' });
  };

  return (
    <div
      className="w-[240px] flex flex-col shrink-0"
      style={{ background: 'var(--void)', borderRight: '1px solid var(--border)' }}
    >
      {/* New Chat */}
      <div className="p-3 pb-2">
        <button
          onClick={onNew}
          className="w-full flex items-center justify-center gap-2 px-3 py-2.5 rounded-xl text-sm font-semibold transition"
          style={{ background: 'var(--gold)', color: '#0a0a0a' }}
          onMouseEnter={e => (e.currentTarget.style.background = 'var(--gold-bright)')}
          onMouseLeave={e => (e.currentTarget.style.background = 'var(--gold)')}
        >
          <Plus className="w-4 h-4" /> New Chat
        </button>
      </div>

      {/* ── AI Desks ── */}
      <div className="px-3 py-2" style={{ borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-1.5 mb-2">
          <LayoutDashboard className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
          <span className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
            AI Desks
          </span>
        </div>
        <div className="space-y-0.5">
          {BUSINESS_DESKS.map(desk => {
            const isActive = activeDesk === desk.id;
            return (
              <button
                key={desk.id}
                onClick={() => isActive ? onDeskClose() : onDeskSelect(desk.id)}
                className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-left transition-all"
                style={{
                  background: isActive ? 'var(--gold-pale)' : 'transparent',
                  borderLeft: `2px solid ${isActive ? 'var(--gold)' : 'transparent'}`,
                }}
                onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'var(--hover)'; }}
                onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
              >
                <span className="text-sm">{desk.icon}</span>
                <div className="flex-1 min-w-0">
                  <p className="text-[11px] font-medium truncate" style={{ color: isActive ? 'var(--gold)' : 'var(--text-primary)' }}>{desk.name}</p>
                </div>
                {isActive && (
                  <span className="w-1.5 h-1.5 rounded-full" style={{ background: 'var(--gold)', animation: 'pulse-online 2.2s infinite' }} />
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* Conversation label */}
      <div className="px-3 py-1.5">
        <span className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
          Conversations
        </span>
      </div>

      {/* List */}
      <div className="flex-1 overflow-y-auto px-2 pb-2">
        {conversations.length === 0 && (
          <p className="text-xs text-center py-8" style={{ color: 'var(--text-muted)' }}>No conversations yet</p>
        )}
        {conversations.map(c => {
          const active = activeId === c.id;
          return (
            <div
              key={c.id}
              onClick={() => { if (editingId !== c.id) onSelect(c.id); }}
              className="group flex items-center gap-2 px-2.5 py-2 rounded-lg mb-0.5 cursor-pointer transition-all"
              style={{
                background:   active ? 'var(--gold-pale)'   : 'transparent',
                borderLeft:   `2px solid ${active ? 'var(--gold)' : 'transparent'}`,
                paddingLeft:  active ? '8px' : '10px',
              }}
              onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--hover)'; }}
              onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
            >
              <MessageSquare
                className="w-3.5 h-3.5 shrink-0"
                style={{ color: active ? 'var(--gold)' : 'var(--text-muted)' }}
              />
              <div className="flex-1 min-w-0">
                {editingId === c.id ? (
                  <div className="flex items-center gap-1">
                    <input
                      value={editTitle}
                      onChange={e => setEditTitle(e.target.value)}
                      onKeyDown={e => {
                        if (e.key === 'Enter') saveEdit(c.id);
                        if (e.key === 'Escape') setEditingId(null);
                      }}
                      className="w-full rounded px-1.5 py-0.5 text-xs outline-none"
                      style={{ background: 'var(--raised)', border: '1px solid var(--border)', color: 'var(--text-primary)' }}
                      autoFocus
                      onClick={e => e.stopPropagation()}
                    />
                    <button onClick={e => { e.stopPropagation(); saveEdit(c.id); }} style={{ color: '#22c55e' }}><Check className="w-3 h-3" /></button>
                    <button onClick={e => { e.stopPropagation(); setEditingId(null); }} style={{ color: 'var(--text-secondary)' }}><X className="w-3 h-3" /></button>
                  </div>
                ) : (
                  <>
                    <p className="text-xs truncate font-medium" style={{ color: active ? 'var(--gold)' : 'var(--text-primary)' }}>{c.title}</p>
                    <p className="text-[10px] mt-0.5" style={{ color: 'var(--text-muted)' }}>
                      {formatTime(c.updated_at)} · {c.message_count} msgs
                      {c.id.startsWith('local-') && <span className="ml-1 opacity-60">· local</span>}
                    </p>
                  </>
                )}
              </div>
              {editingId !== c.id && (
                <div className="flex gap-0.5 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
                  <button
                    onClick={e => { e.stopPropagation(); startEdit(c.id, c.title); }}
                    className="p-1 rounded transition"
                    style={{ color: 'var(--text-muted)' }}
                    onMouseEnter={e => (e.currentTarget.style.color = 'var(--gold)')}
                    onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
                  >
                    <Pencil className="w-3 h-3" />
                  </button>
                  <button
                    onClick={e => { e.stopPropagation(); if (confirm('Delete this conversation?')) onDelete(c.id); }}
                    className="p-1 rounded transition"
                    style={{ color: 'var(--text-muted)' }}
                    onMouseEnter={e => (e.currentTarget.style.color = '#ef4444')}
                    onMouseLeave={e => (e.currentTarget.style.color = 'var(--text-muted)')}
                  >
                    <Trash2 className="w-3 h-3" />
                  </button>
                </div>
              )}
            </div>
          );
        })}
      </div>

      {/* Empire Apps */}
      <div style={{ borderTop: '1px solid var(--border)' }} className="p-3">
        <p className="text-[10px] font-semibold uppercase tracking-widest mb-2" style={{ color: 'var(--text-muted)' }}>
          Empire Apps
        </p>
        <div className="space-y-0.5">
          {EMPIRE_APPS.map(app => (
            <button
              key={app.name}
              onClick={() => app.live && app.port && window.open(`http://localhost:${app.port}${(app as any).path || ''}`, '_blank')}
              disabled={!app.live}
              className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left transition-all"
              style={{ opacity: app.live ? 1 : 0.35, cursor: app.live ? 'pointer' : 'default' }}
              onMouseEnter={e => { if (app.live) e.currentTarget.style.background = 'var(--hover)'; }}
              onMouseLeave={e => { e.currentTarget.style.background = 'transparent'; }}
            >
              <span className="text-sm">{app.icon}</span>
              <span className="flex-1 text-xs" style={{ color: app.live ? 'var(--text-primary)' : 'var(--text-muted)' }}>{app.name}</span>
              {app.live
                ? <span className="dot-online" />
                : <span className="text-[10px]" style={{ color: 'var(--text-muted)' }}>soon</span>
              }
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
