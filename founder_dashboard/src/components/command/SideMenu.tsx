'use client';
import { useState } from 'react';
import { ChatSession } from '@/lib/types';
import { MessageSquare, Trash2, Pencil, Check, X, ChevronDown, ChevronRight, Sparkles } from 'lucide-react';

interface Props {
  conversations: ChatSession[];
  activeConversationId: string | null;
  onSelectConversation: (id: string) => void;
  onNewChat: () => void;
  onDeleteConversation: (id: string) => void;
  onRenameConversation: (id: string, title: string) => void;
  onSuggest: (prompt: string) => void;
  onOpenWorkspace?: (id: string) => void;
}

const EMPIRE_APPS = [
  { name: 'WorkroomForge',  id: 'workroomforge', icon: '🪡', ready: true },
  { name: 'MarketForge',    id: 'marketforge',   icon: '🛒', ready: false },
  { name: 'AMP',            id: 'amp',            icon: '📢', ready: false },
  { name: 'SocialForge',    id: 'socialforge',    icon: '🌐', ready: false },
  { name: 'LuxeForge',      id: 'luxeforge',      icon: '💎', ready: false },
  { name: 'RecoveryForge',  id: 'recoveryforge',  icon: '🔄', ready: false },
  { name: 'CRM',            id: 'crm',            icon: '👥', ready: false },
];

const SUGGESTIONS = [
  { label: 'Check system health', prompt: 'Run a full system health check — CPU, RAM, disk, and all services.' },
  { label: 'Review open tasks', prompt: 'Show me all open and in-progress tasks across all desks.' },
  { label: 'Create a quote', prompt: 'Help me create a new quote for a client in WorkroomForge.' },
  { label: 'Summarize today', prompt: 'Give me a summary of today\'s activity across all desks.' },
];

export default function SideMenu({
  conversations, activeConversationId, onSelectConversation,
  onNewChat, onDeleteConversation, onRenameConversation, onSuggest,
  onOpenWorkspace,
}: Props) {
  const [showConvos, setShowConvos] = useState(true);
  const [showApps, setShowApps] = useState(false);
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

  return (
    <div className="space-y-3">
      {/* Suggestions */}
      <div>
        <div className="flex items-center gap-1.5 mb-2">
          <Sparkles className="w-3 h-3" style={{ color: 'var(--gold)' }} />
          <span className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
            Quick Actions
          </span>
        </div>
        <div className="grid grid-cols-2 gap-1.5">
          {SUGGESTIONS.map(s => (
            <button
              key={s.label}
              onClick={() => onSuggest(s.prompt)}
              className="text-left px-3 py-2 rounded-lg text-xs transition"
              style={{ background: 'var(--raised)', color: 'var(--text-secondary)', border: '1px solid var(--border)' }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold-border)'; e.currentTarget.style.color = 'var(--text-primary)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.color = 'var(--text-secondary)'; }}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>

      {/* Conversations */}
      <div>
        <button
          onClick={() => setShowConvos(!showConvos)}
          className="w-full flex items-center justify-between mb-2"
        >
          <span className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
            Conversations ({conversations.length})
          </span>
          {showConvos
            ? <ChevronDown className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
            : <ChevronRight className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
          }
        </button>
        {showConvos && (
          <div className="space-y-0.5 max-h-56 overflow-y-auto">
            {conversations.length === 0 && (
              <p className="text-xs text-center py-4" style={{ color: 'var(--text-muted)' }}>No conversations yet</p>
            )}
            {conversations.slice(0, 10).map(c => {
              const active = activeConversationId === c.id;
              return (
                <div
                  key={c.id}
                  onClick={() => { if (editingId !== c.id) onSelectConversation(c.id); }}
                  className="group flex items-center gap-2 px-2.5 py-2 rounded-lg cursor-pointer transition-all"
                  style={{
                    background: active ? 'var(--gold-pale)' : 'transparent',
                    borderLeft: `2px solid ${active ? 'var(--gold)' : 'transparent'}`,
                  }}
                  onMouseEnter={e => { if (!active) e.currentTarget.style.background = 'var(--hover)'; }}
                  onMouseLeave={e => { if (!active) e.currentTarget.style.background = 'transparent'; }}
                >
                  <MessageSquare className="w-3 h-3 shrink-0" style={{ color: active ? 'var(--gold)' : 'var(--text-muted)' }} />
                  <div className="flex-1 min-w-0">
                    {editingId === c.id ? (
                      <div className="flex items-center gap-1">
                        <input
                          value={editTitle}
                          onChange={e => setEditTitle(e.target.value)}
                          onKeyDown={e => { if (e.key === 'Enter') saveEdit(c.id); if (e.key === 'Escape') setEditingId(null); }}
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
                      ><Pencil className="w-3 h-3" /></button>
                      <button
                        onClick={e => { e.stopPropagation(); if (confirm('Delete?')) onDeleteConversation(c.id); }}
                        className="p-1 rounded transition"
                        style={{ color: 'var(--text-muted)' }}
                      ><Trash2 className="w-3 h-3" /></button>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Empire Apps */}
      <div>
        <button
          onClick={() => setShowApps(!showApps)}
          className="w-full flex items-center justify-between mb-2"
        >
          <span className="text-[10px] font-semibold uppercase tracking-widest" style={{ color: 'var(--text-muted)' }}>
            Empire Apps
          </span>
          {showApps
            ? <ChevronDown className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
            : <ChevronRight className="w-3 h-3" style={{ color: 'var(--text-muted)' }} />
          }
        </button>
        {showApps && (
          <div className="space-y-0.5">
            {EMPIRE_APPS.map(app => (
              <button
                key={app.name}
                onClick={() => onOpenWorkspace?.(app.id)}
                className="w-full flex items-center gap-2.5 px-2.5 py-2 rounded-lg text-left transition"
                onMouseEnter={e => (e.currentTarget.style.background = 'var(--hover)')}
                onMouseLeave={e => (e.currentTarget.style.background = 'transparent')}
              >
                <span className="text-sm">{app.icon}</span>
                <span className="flex-1 text-xs" style={{ color: 'var(--text-primary)' }}>{app.name}</span>
                {app.ready
                  ? <span className="dot-online" />
                  : <span className="text-[8px] px-1 py-0.5 rounded font-bold" style={{ color: 'var(--text-muted)', background: 'var(--elevated)' }}>SOON</span>
                }
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
